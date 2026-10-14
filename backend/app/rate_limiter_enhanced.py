"""
Enhanced rate limiting and cost control for StudentsAI MVP.
Implements per-user and per-IP rate limiting with different tiers and AI cost tracking.
"""

import contextlib
import logging
import time
from dataclasses import dataclass
from enum import Enum

import redis.asyncio as redis
from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


class UserTier(Enum):
    """User subscription tiers with different limits."""

    FREE = "free"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


@dataclass
class RateLimit:
    """Rate limit configuration."""

    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    ai_requests_per_day: int
    max_note_length: int
    max_notes_per_day: int
    max_flashcards_per_note: int


# Rate limits by user tier
TIER_LIMITS = {
    UserTier.FREE: RateLimit(
        requests_per_minute=10,
        requests_per_hour=100,
        requests_per_day=500,
        ai_requests_per_day=20,
        max_note_length=5000,
        max_notes_per_day=10,
        max_flashcards_per_note=10,
    ),
    UserTier.PREMIUM: RateLimit(
        requests_per_minute=30,
        requests_per_hour=500,
        requests_per_day=2000,
        ai_requests_per_day=100,
        max_note_length=20000,
        max_notes_per_day=50,
        max_flashcards_per_note=25,
    ),
    UserTier.ENTERPRISE: RateLimit(
        requests_per_minute=100,
        requests_per_hour=2000,
        requests_per_day=10000,
        ai_requests_per_day=500,
        max_note_length=50000,
        max_notes_per_day=200,
        max_flashcards_per_note=50,
    ),
}

# Default limits for anonymous/IP-based requests
ANONYMOUS_LIMITS = RateLimit(
    requests_per_minute=5,
    requests_per_hour=50,
    requests_per_day=200,
    ai_requests_per_day=5,
    max_note_length=2000,
    max_notes_per_day=3,
    max_flashcards_per_note=5,
)


class EnhancedRateLimiter:
    """Enhanced rate limiter with Redis backend and cost control."""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: redis.Redis | None = None
        self.local_cache: dict[str, dict] = {}
        self.cache_ttl = 60  # Local cache TTL in seconds
        # In-memory user tier overrides (user_id -> UserTier)
        self.user_tiers: dict[str, UserTier] = {}

    async def init_redis(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            await self.redis_client.ping()
            logger.info("Enhanced Redis connection established")
        except Exception as e:
            logger.warning(f"Enhanced Redis connection failed: {e}. Using local cache.")
            self.redis_client = None

    async def close_redis(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()

    def _get_cache_key(self, identifier: str, window: str) -> str:
        """Generate cache key for rate limiting."""
        return f"enhanced_ratelimit:{identifier}:{window}"

    def _get_current_windows(self) -> dict[str, int]:
        """Get current time windows for rate limiting."""
        now = int(time.time())
        return {"minute": now // 60, "hour": now // 3600, "day": now // 86400}

    async def _get_count(self, key: str) -> int:
        """Get current count from Redis or local cache."""
        if self.redis_client:
            try:
                count = await self.redis_client.get(key)
                return int(count) if count else 0
            except Exception as e:
                logger.warning(f"Redis get failed: {e}")

        # Fallback to local cache
        cache_entry = self.local_cache.get(key)
        if cache_entry and time.time() - cache_entry["timestamp"] < self.cache_ttl:
            return cache_entry["count"]
        return 0

    async def _increment_count(self, key: str, ttl: int) -> int:
        """Increment count in Redis or local cache."""
        if self.redis_client:
            try:
                pipe = self.redis_client.pipeline()
                pipe.incr(key)
                pipe.expire(key, ttl)
                results = await pipe.execute()
                return results[0]
            except Exception as e:
                logger.warning(f"Redis increment failed: {e}")

        # Fallback to local cache
        now = time.time()
        cache_entry = self.local_cache.get(key, {"count": 0, "timestamp": now})

        # Reset if expired
        if now - cache_entry["timestamp"] > ttl:
            cache_entry = {"count": 0, "timestamp": now}

        cache_entry["count"] += 1
        self.local_cache[key] = cache_entry

        # Clean old entries
        self._cleanup_local_cache()

        return cache_entry["count"]

    def _cleanup_local_cache(self):
        """Clean expired entries from local cache."""
        now = time.time()
        expired_keys = [
            key
            for key, entry in self.local_cache.items()
            if now - entry["timestamp"] > self.cache_ttl
        ]
        for key in expired_keys:
            del self.local_cache[key]

    def _get_user_tier(self, user_id: str | None) -> UserTier:
        """Get user tier. In MVP, all users are FREE tier."""
        if user_id and user_id in self.user_tiers:
            return self.user_tiers[user_id]
        return UserTier.FREE

    def set_user_tier(self, user_id: str, tier: UserTier):
        """Override a user's tier for rate limiting decisions."""
        with contextlib.suppress(Exception):
            self.user_tiers[user_id] = tier

    def _get_rate_limits(self, user_id: str | None) -> RateLimit:
        """Get rate limits for user or anonymous."""
        if user_id:
            tier = self._get_user_tier(user_id)
            return TIER_LIMITS[tier]
        return ANONYMOUS_LIMITS

    async def check_rate_limit(
        self,
        identifier: str,
        user_id: str | None = None,
        endpoint_type: str = "general",
    ) -> tuple[bool, dict[str, int]]:
        """
        Check if request is within rate limits.

        Args:
            identifier: IP address or user ID
            user_id: User ID if authenticated
            endpoint_type: Type of endpoint (general, ai, note_creation)

        Returns:
            Tuple of (is_allowed, remaining_limits)
        """
        limits = self._get_rate_limits(user_id)
        windows = self._get_current_windows()

        # Check different time windows
        checks = [
            ("minute", limits.requests_per_minute, 60),
            ("hour", limits.requests_per_hour, 3600),
            ("day", limits.requests_per_day, 86400),
        ]

        # Add AI-specific checks
        if endpoint_type == "ai":
            checks.append(("ai_day", limits.ai_requests_per_day, 86400))
        elif endpoint_type == "note_creation":
            checks.append(("notes_day", limits.max_notes_per_day, 86400))

        remaining = {}

        for window, limit, _ttl in checks:
            key = self._get_cache_key(
                identifier, f"{window}:{windows.get(window, windows['day'])}"
            )
            current_count = await self._get_count(key)

            remaining[window] = max(0, limit - current_count)

            if current_count >= limit:
                return False, remaining

        return True, remaining

    async def record_request(
        self,
        identifier: str,
        user_id: str | None = None,
        endpoint_type: str = "general",
    ) -> dict[str, int]:
        """
        Record a request and return updated remaining limits.

        Args:
            identifier: IP address or user ID
            user_id: User ID if authenticated
            endpoint_type: Type of endpoint

        Returns:
            Dictionary of remaining limits
        """
        limits = self._get_rate_limits(user_id)
        windows = self._get_current_windows()

        # Record in different time windows
        records = [
            ("minute", limits.requests_per_minute, 60),
            ("hour", limits.requests_per_hour, 3600),
            ("day", limits.requests_per_day, 86400),
        ]

        # Add specific endpoint records
        if endpoint_type == "ai":
            records.append(("ai_day", limits.ai_requests_per_day, 86400))
        elif endpoint_type == "note_creation":
            records.append(("notes_day", limits.max_notes_per_day, 86400))

        remaining = {}

        for window, limit, ttl in records:
            key = self._get_cache_key(
                identifier, f"{window}:{windows.get(window, windows['day'])}"
            )
            current_count = await self._increment_count(key, ttl)
            remaining[window] = max(0, limit - current_count)

        return remaining

    async def check_content_limits(
        self, content_length: int, user_id: str | None = None
    ) -> bool:
        """Check if content length is within limits."""
        limits = self._get_rate_limits(user_id)
        return content_length <= limits.max_note_length

    async def check_flashcard_limits(
        self, flashcard_count: int, user_id: str | None = None
    ) -> bool:
        """Check if flashcard count is within limits."""
        limits = self._get_rate_limits(user_id)
        return flashcard_count <= limits.max_flashcards_per_note

    async def get_usage_stats(
        self, identifier: str, user_id: str | None = None
    ) -> dict:
        """Get current usage statistics."""
        limits = self._get_rate_limits(user_id)
        windows = self._get_current_windows()

        stats = {
            "tier": self._get_user_tier(user_id).value if user_id else "anonymous",
            "limits": {
                "requests_per_minute": limits.requests_per_minute,
                "requests_per_hour": limits.requests_per_hour,
                "requests_per_day": limits.requests_per_day,
                "ai_requests_per_day": limits.ai_requests_per_day,
                "max_note_length": limits.max_note_length,
                "max_notes_per_day": limits.max_notes_per_day,
                "max_flashcards_per_note": limits.max_flashcards_per_note,
            },
            "usage": {},
            "remaining": {},
        }

        # Get current usage
        for window, limit in [
            ("minute", limits.requests_per_minute),
            ("hour", limits.requests_per_hour),
            ("day", limits.requests_per_day),
            ("ai_day", limits.ai_requests_per_day),
            ("notes_day", limits.max_notes_per_day),
        ]:
            key = self._get_cache_key(
                identifier,
                f"{window}:{windows.get(window.replace('_day', ''), windows['day'])}",
            )
            current_count = await self._get_count(key)
            stats["usage"][window] = current_count
            stats["remaining"][window] = max(0, limit - current_count)

        return stats


# Global enhanced rate limiter instance
enhanced_rate_limiter = EnhancedRateLimiter()


async def get_client_identifier(request: Request) -> str:
    """Get client identifier (IP address)."""
    # Try to get real IP from headers (for reverse proxy setups)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fallback to direct client IP
    return request.client.host if request.client else "unknown"


async def check_enhanced_rate_limit(
    request: Request, user_id: str | None = None, endpoint_type: str = "general"
):
    """Enhanced middleware function to check rate limits."""
    identifier = await get_client_identifier(request)

    # Use user ID as identifier if available, otherwise use IP
    rate_identifier = user_id if user_id else identifier

    allowed, remaining = await enhanced_rate_limiter.check_rate_limit(
        rate_identifier, user_id, endpoint_type
    )

    if not allowed:
        # Get usage stats for error message
        stats = await enhanced_rate_limiter.get_usage_stats(rate_identifier, user_id)

        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "message": "Too many requests. Please try again later.",
                "stats": stats,
                "retry_after": 60,  # Suggest retry after 1 minute
                "upgrade_message": "Upgrade to Premium for higher limits!"
                if not user_id
                else None,
            },
        )

    # Record the request
    await enhanced_rate_limiter.record_request(rate_identifier, user_id, endpoint_type)

    return remaining


async def check_content_length(content: str, user_id: str | None = None):
    """Check if content length is within limits."""
    content_length = len(content)

    if not await enhanced_rate_limiter.check_content_limits(content_length, user_id):
        limits = enhanced_rate_limiter._get_rate_limits(user_id)

        raise HTTPException(
            status_code=413,
            detail={
                "error": "Content too long",
                "message": f"Content exceeds maximum length of {limits.max_note_length} characters",
                "current_length": content_length,
                "max_length": limits.max_note_length,
                "upgrade_message": "Upgrade to Premium for longer notes!"
                if not user_id
                else None,
            },
        )


async def check_flashcard_count(count: int, user_id: str | None = None):
    """Check if flashcard count is within limits."""
    if not await enhanced_rate_limiter.check_flashcard_limits(count, user_id):
        limits = enhanced_rate_limiter._get_rate_limits(user_id)

        raise HTTPException(
            status_code=413,
            detail={
                "error": "Too many flashcards requested",
                "message": f"Maximum {limits.max_flashcards_per_note} flashcards per note",
                "requested_count": count,
                "max_count": limits.max_flashcards_per_note,
                "upgrade_message": "Upgrade to Premium for more flashcards!"
                if not user_id
                else None,
            },
        )
