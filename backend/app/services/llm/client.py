import functools
import json
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any, ClassVar, Literal, TypedDict

from sqlalchemy.orm import Session

from app.config import settings
from app.models.llm_call import LLMProvider
from app.services.llm.cache import cache_key, find_entry, store_entry
from app.services.llm.cost_log import record_call
from app.services.llm.pricing import estimate_cost

# The cheapest current model of each provider that handles short, focused
# generation and grading; both reason by default and share one list price.
DEFAULT_MODELS: dict[LLMProvider, str] = {
    LLMProvider.OPENAI: "gpt-6-luna",
    LLMProvider.ANTHROPIC: "claude-haiku-5-5",
    LLMProvider.FAKE: "fake",
}


class Message(TypedDict):
    role: Literal["user", "assistant"]
    content: str


class StopReason(StrEnum):
    END = "end"
    MAX_TOKENS = "max_tokens"
    REFUSAL = "refusal"


@dataclass(frozen=True)
class LLMRequest:
    system: str
    messages: tuple[Message, ...]
    max_tokens: int
    temperature: float | None
    json_schema: dict[str, Any] | None
    purpose: str
    user_id: uuid.UUID | None


@dataclass(frozen=True)
class Generation:
    """A provider's raw answer, before pricing, logging and caching."""

    text: str
    input_tokens: int
    output_tokens: int
    stop_reason: StopReason = StopReason.END


@dataclass(frozen=True)
class LLMResult:
    text: str
    parsed: Any | None
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal | None
    model: str
    provider: LLMProvider
    latency_ms: int
    cached: bool
    truncated: bool


class LLMError(Exception):
    pass


class LLMUnavailableError(LLMError):
    """The provider could not be reached or was overloaded after the SDK's retries; trying later may succeed."""


class LLMRequestError(LLMError):
    """The provider rejected the request itself; sending it again unchanged will fail again."""


class LLMRefusalError(LLMError):
    """The model declined to answer; the call is still logged because it was billed."""


def provider_status_error(status_code: int, message: str) -> LLMError:
    transient = status_code in (408, 409, 429) or status_code >= 500
    return (LLMUnavailableError if transient else LLMRequestError)(message)


class LLMClient(ABC):
    """The one way the product calls a language model.

    Subclasses implement `_generate` for a provider; `complete` adds the
    behavior every provider shares: validation, caching, pricing and logging.
    """

    provider: ClassVar[LLMProvider]

    def __init__(self, model: str, reasoning_effort: str | None = None) -> None:
        self.model = model
        self.reasoning_effort = reasoning_effort

    async def complete(
        self,
        db: Session,
        *,
        system: str,
        messages: Sequence[Message],
        max_tokens: int,
        purpose: str,
        temperature: float | None = None,
        json_schema: dict[str, Any] | None = None,
        user_id: uuid.UUID | None = None,
        cache_version: str | None = None,
    ) -> LLMResult:
        """Send one request and log it in `llm_calls`.

        `messages` must end with a user turn. With `json_schema`, the provider
        constrains the output to it and `parsed` holds the decoded JSON, or None
        when the text is not JSON (for example when it hit `max_tokens`).
        `temperature` is passed through untouched; the current reasoning models
        of both providers reject anything but their default, so leave it None
        unless the configured model accepts it.
        Passing `cache_version` (the prompt's version) opts in to the response
        cache: an identical earlier request returns its stored result at zero cost.

        Only the bind of `db` is used. The log and cache commit in their own short
        transactions, so a billed call stays recorded when the caller rolls back,
        and the caller's pending work is never flushed or committed here.
        """
        if not messages or messages[-1]["role"] != "user":
            raise ValueError("messages must be non-empty and end with a user turn")
        request = LLMRequest(
            system=system,
            messages=tuple(messages),
            max_tokens=max_tokens,
            temperature=temperature,
            json_schema=json_schema,
            purpose=purpose,
            user_id=user_id,
        )
        started = time.perf_counter()
        if cache_version is not None:
            hit = self._replay_cached(db, request, cache_version, started)
            if hit is not None:
                return hit

        generation = await self._generate(request)
        result = self._result(generation, request, started)
        reusable = generation.stop_reason is StopReason.END and (
            json_schema is None or result.parsed is not None
        )
        with _own_session(db) as session:
            _record(session, result, request)
            if cache_version is not None and reusable:
                store_entry(
                    session,
                    key=self._cache_key(request, cache_version),
                    provider=self.provider,
                    model=self.model,
                    prompt_version=cache_version,
                    text=result.text,
                    parsed=result.parsed,
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                )
            session.commit()

        if generation.stop_reason is StopReason.REFUSAL:
            raise LLMRefusalError(
                f"{self.provider} model {self.model} declined the {purpose!r} request"
            )
        return result

    def _replay_cached(
        self, db: Session, request: LLMRequest, cache_version: str, started: float
    ) -> LLMResult | None:
        with _own_session(db) as session:
            entry = find_entry(session, self._cache_key(request, cache_version))
            if entry is None:
                return None
            result = LLMResult(
                text=entry.text,
                parsed=entry.parsed,
                input_tokens=entry.input_tokens,
                output_tokens=entry.output_tokens,
                cost_usd=Decimal(0),
                model=entry.model,
                provider=self.provider,
                latency_ms=_elapsed_ms(started),
                cached=True,
                truncated=False,
            )
            _record(session, result, request)
            session.commit()
            return result

    def _cache_key(self, request: LLMRequest, cache_version: str) -> str:
        return cache_key(
            provider=self.provider,
            model=self.model,
            prompt_version=cache_version,
            reasoning_effort=self.reasoning_effort,
            system=request.system,
            messages=request.messages,
            json_schema=request.json_schema,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )

    def _result(
        self, generation: Generation, request: LLMRequest, started: float
    ) -> LLMResult:
        return LLMResult(
            text=generation.text,
            parsed=(
                _decode_json(generation.text)
                if request.json_schema is not None
                else None
            ),
            input_tokens=generation.input_tokens,
            output_tokens=generation.output_tokens,
            cost_usd=estimate_cost(
                self.provider,
                self.model,
                generation.input_tokens,
                generation.output_tokens,
            ),
            model=self.model,
            provider=self.provider,
            latency_ms=_elapsed_ms(started),
            cached=False,
            truncated=generation.stop_reason is StopReason.MAX_TOKENS,
        )

    @abstractmethod
    async def _generate(self, request: LLMRequest) -> Generation: ...


def _own_session(db: Session) -> Session:
    # Joining via a savepoint keeps this inside a test's outer transaction; on an
    # engine bind it is an ordinary independent transaction.
    return Session(bind=db.get_bind(), join_transaction_mode="create_savepoint")


def _record(session: Session, result: LLMResult, request: LLMRequest) -> None:
    record_call(
        session,
        user_id=request.user_id,
        provider=result.provider,
        model=result.model,
        purpose=request.purpose,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cost_usd=result.cost_usd,
        latency_ms=result.latency_ms,
        cached=result.cached,
    )


def _decode_json(text: str) -> Any | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _elapsed_ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)


@functools.cache
def get_llm_client() -> LLMClient:
    """The configured client, built once per process; SDKs load only when selected."""
    provider = LLMProvider(settings.llm_provider)
    model = settings.llm_model or DEFAULT_MODELS[provider]
    if provider is LLMProvider.OPENAI:
        from app.services.llm.openai_client import OpenAIClient

        return OpenAIClient.from_settings(model)
    if provider is LLMProvider.ANTHROPIC:
        from app.services.llm.anthropic_client import AnthropicClient

        return AnthropicClient.from_settings(model)
    from app.services.llm.fake_client import FakeLLMClient

    return FakeLLMClient(model=model)
