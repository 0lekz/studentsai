import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy.orm import Session

from app.services.llm.client import LLMClient, LLMError, LLMResult, Message

MAX_ATTEMPTS = 2


class StructuredOutput(BaseModel):
    """Base for response models.

    Strict structured output on both providers needs every object closed to
    extra keys and every property required, so subclasses forbid extras and
    give their fields no defaults.
    """

    model_config = ConfigDict(extra="forbid")


ModelT = TypeVar("ModelT", bound=BaseModel)


@dataclass(frozen=True)
class StructuredResult(Generic[ModelT]):
    value: ModelT
    calls: tuple[LLMResult, ...]

    @property
    def cost_usd(self) -> Decimal | None:
        costs = [call.cost_usd for call in self.calls]
        return None if None in costs else sum(costs, Decimal(0))


class StructuredOutputError(LLMError):
    def __init__(self, message: str, calls: Sequence[LLMResult]) -> None:
        super().__init__(message)
        self.calls = tuple(calls)


async def complete_structured(
    client: LLMClient,
    db: Session,
    *,
    response_model: type[ModelT],
    system: str,
    messages: Sequence[Message],
    max_tokens: int,
    purpose: str,
    temperature: float | None = None,
    user_id: uuid.UUID | None = None,
    cache_version: str | None = None,
) -> StructuredResult[ModelT]:
    """Ask for JSON matching `response_model` and validate it.

    An invalid answer is retried once, with the answer and its validation
    errors appended to the conversation; a second invalid answer raises
    `StructuredOutputError`.
    """
    schema = response_model.model_json_schema()
    conversation = list(messages)
    calls: list[LLMResult] = []
    while True:
        result = await client.complete(
            db,
            system=system,
            messages=conversation,
            max_tokens=max_tokens,
            purpose=purpose,
            temperature=temperature,
            json_schema=schema,
            user_id=user_id,
            cache_version=cache_version,
        )
        calls.append(result)
        try:
            value = response_model.model_validate_json(result.text)
        except ValidationError as error:
            problems = _describe(error)
        else:
            return StructuredResult(value, tuple(calls))

        if len(calls) == MAX_ATTEMPTS:
            raise StructuredOutputError(
                f"{purpose!r} returned invalid {response_model.__name__} "
                f"{MAX_ATTEMPTS} times:\n{problems}",
                calls,
            )
        conversation = [*conversation, *_correction(result.text, problems)]


def _describe(error: ValidationError) -> str:
    return "\n".join(
        f"- {'.'.join(str(part) for part in issue['loc']) or 'response'}: {issue['msg']}"
        for issue in error.errors()
    )


def _correction(previous_reply: str, problems: str) -> list[Message]:
    feedback: Message = {
        "role": "user",
        "content": (
            "Your reply did not match the required JSON schema:\n"
            f"{problems}\n"
            "Reply again with only a JSON object that matches the schema."
        ),
    }
    if not previous_reply:
        return [feedback]
    return [{"role": "assistant", "content": previous_reply}, feedback]
