import hashlib
import json
from collections.abc import Sequence
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.llm_call import LLMCacheEntry, LLMProvider


def cache_key(
    *,
    provider: LLMProvider,
    model: str,
    prompt_version: str,
    reasoning_effort: str | None,
    system: str,
    messages: Sequence[dict[str, str]],
    json_schema: dict[str, Any] | None,
    max_tokens: int,
    temperature: float | None,
) -> str:
    """A digest of every input that shapes the output, so a change to any of them misses."""
    payload = {
        "provider": str(provider),
        "model": model,
        "prompt_version": prompt_version,
        "reasoning_effort": reasoning_effort,
        "system": system,
        "messages": list(messages),
        "json_schema": json_schema,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def find_entry(session: Session, key: str) -> LLMCacheEntry | None:
    return session.get(LLMCacheEntry, key)


def store_entry(
    session: Session,
    *,
    key: str,
    provider: LLMProvider,
    model: str,
    prompt_version: str,
    text: str,
    parsed: Any | None,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """Insert unless a concurrent request already stored the same key."""
    session.execute(
        insert(LLMCacheEntry)
        .values(
            key=key,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            text=text,
            parsed=parsed,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        .on_conflict_do_nothing(index_elements=[LLMCacheEntry.key])
    )
