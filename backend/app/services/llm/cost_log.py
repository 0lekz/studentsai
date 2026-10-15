import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.llm_call import LLMCall, LLMProvider


def record_call(
    session: Session,
    *,
    user_id: uuid.UUID | None,
    provider: LLMProvider,
    model: str,
    purpose: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: Decimal | None,
    latency_ms: int,
    cached: bool,
) -> None:
    session.add(
        LLMCall(
            user_id=user_id,
            provider=provider,
            model=model,
            purpose=purpose,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            cached=cached,
        )
    )
