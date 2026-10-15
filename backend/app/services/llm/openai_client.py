from typing import Any

from openai import APIConnectionError, APIStatusError, AsyncOpenAI

from app.config import settings
from app.models.llm_call import LLMProvider
from app.services.llm.client import (
    Generation,
    LLMClient,
    LLMRequest,
    LLMUnavailableError,
    StopReason,
    provider_status_error,
)

_STOP_REASONS = {"length": StopReason.MAX_TOKENS, "content_filter": StopReason.REFUSAL}


class OpenAIClient(LLMClient):
    """Chat Completions, the API that OpenAI-compatible servers such as vLLM and Ollama also serve.

    Point `llm_base_url` at such a server to run a self-hosted model with no code change.
    """

    provider = LLMProvider.OPENAI

    def __init__(
        self, sdk: AsyncOpenAI, model: str, reasoning_effort: str | None = None
    ) -> None:
        super().__init__(model, reasoning_effort)
        self.sdk = sdk

    @classmethod
    def from_settings(cls, model: str) -> "OpenAIClient":
        sdk = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.llm_base_url,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )
        return cls(sdk, model, settings.llm_reasoning_effort)

    async def _generate(self, request: LLMRequest) -> Generation:
        try:
            completion = await self.sdk.chat.completions.create(
                model=self.model,
                messages=self._messages(request),
                max_completion_tokens=request.max_tokens,
                **self._options(request),
            )
        except APIConnectionError as error:
            raise LLMUnavailableError(str(error)) from error
        except APIStatusError as error:
            raise provider_status_error(error.status_code, str(error)) from error

        choice = completion.choices[0]
        stop_reason = _STOP_REASONS.get(choice.finish_reason, StopReason.END)
        if choice.message.refusal:
            stop_reason = StopReason.REFUSAL
        usage = completion.usage
        return Generation(
            text=choice.message.content or "",
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            stop_reason=stop_reason,
        )

    @staticmethod
    def _messages(request: LLMRequest) -> list[Any]:
        system = (
            [{"role": "system", "content": request.system}] if request.system else []
        )
        return [*system, *request.messages]

    def _options(self, request: LLMRequest) -> dict[str, Any]:
        options: dict[str, Any] = {}
        if request.temperature is not None:
            options["temperature"] = request.temperature
        if self.reasoning_effort is not None:
            options["reasoning_effort"] = self.reasoning_effort
        if request.json_schema is not None:
            options["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "response",
                    "schema": request.json_schema,
                    "strict": True,
                },
            }
        return options
