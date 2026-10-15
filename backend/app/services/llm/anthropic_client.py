from typing import Any

from anthropic import (
    APIConnectionError,
    APIStatusError,
    AsyncAnthropic,
    transform_schema,
)

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

_STOP_REASONS = {"max_tokens": StopReason.MAX_TOKENS, "refusal": StopReason.REFUSAL}


class AnthropicClient(LLMClient):
    """The Messages API, with JSON output constrained through `output_config.format`."""

    provider = LLMProvider.ANTHROPIC

    def __init__(
        self, sdk: AsyncAnthropic, model: str, reasoning_effort: str | None = None
    ) -> None:
        super().__init__(model, reasoning_effort)
        self.sdk = sdk

    @classmethod
    def from_settings(cls, model: str) -> "AnthropicClient":
        sdk = AsyncAnthropic(
            api_key=settings.anthropic_api_key,
            base_url=settings.llm_base_url,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )
        return cls(sdk, model, settings.llm_reasoning_effort)

    async def _generate(self, request: LLMRequest) -> Generation:
        try:
            message = await self.sdk.messages.create(
                model=self.model,
                max_tokens=request.max_tokens,
                messages=list(request.messages),
                **self._options(request),
            )
        except APIConnectionError as error:
            raise LLMUnavailableError(str(error)) from error
        except APIStatusError as error:
            raise provider_status_error(error.status_code, str(error)) from error

        stop_reason = _STOP_REASONS.get(message.stop_reason or "", StopReason.END)
        text = "".join(block.text for block in message.content if block.type == "text")
        return Generation(
            text=text,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            stop_reason=stop_reason,
        )

    def _options(self, request: LLMRequest) -> dict[str, Any]:
        # No `thinking` parameter: current models think adaptively by default,
        # and `output_config.effort` is the setting that scales it.
        options: dict[str, Any] = {}
        if request.system:
            options["system"] = request.system
        if request.temperature is not None:
            options["temperature"] = request.temperature
        output_config: dict[str, Any] = {}
        if self.reasoning_effort is not None:
            output_config["effort"] = self.reasoning_effort
        if request.json_schema is not None:
            output_config["format"] = {
                "type": "json_schema",
                "schema": transform_schema(request.json_schema),
            }
        if output_config:
            options["output_config"] = output_config
        return options
