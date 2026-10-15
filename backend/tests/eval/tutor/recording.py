from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models.llm_call import LLMProvider
from app.services.llm import DEFAULT_MODELS, LLMClient, LLMResult
from app.services.llm.client import Generation, LLMRequest
from app.services.llm.pricing import estimate_cost

# Both providers' default models share one list price, so either prices a run.
LIST_PRICE_MODEL = (LLMProvider.ANTHROPIC, DEFAULT_MODELS[LLMProvider.ANTHROPIC])


class RecordingClient(LLMClient):
    """Delegates to another client and keeps every result, so a run can report its tokens."""

    def __init__(self, inner: LLMClient) -> None:
        super().__init__(inner.model, inner.reasoning_effort)
        self.inner = inner
        self.provider = inner.provider
        self.results: list[LLMResult] = []

    async def complete(self, db: Session, **request: Any) -> LLMResult:
        result = await self.inner.complete(db, **request)
        self.results.append(result)
        return result

    async def _generate(self, request: LLMRequest) -> Generation:
        raise NotImplementedError("RecordingClient delegates complete()")


def usage(results: Sequence[LLMResult]) -> dict[str, Any]:
    """Token totals of a run, priced as billed and at the default model's list price.

    The list price counts every call as uncached, which is what a first run
    over new material costs. Reasoning tokens are included when the provider
    reports them as output; the fake client reports none.
    """
    input_tokens = sum(result.input_tokens for result in results)
    output_tokens = sum(result.output_tokens for result in results)
    billed = [result.cost_usd for result in results]
    provider, model = LIST_PRICE_MODEL
    list_price = sum(
        (
            estimate_cost(provider, model, result.input_tokens, result.output_tokens)
            for result in results
        ),
        Decimal(0),
    )
    return {
        "calls": len(results),
        "cached_calls": sum(result.cached for result in results),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "billed_usd": None if None in billed else float(sum(billed, Decimal(0))),
        "list_price_model": model,
        "list_price_usd": float(list_price),
    }


def per_item(total_usd: float, count: int) -> float | None:
    return round(total_usd / count, 8) if count else None
