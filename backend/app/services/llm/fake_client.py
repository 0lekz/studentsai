import json
import math
from collections.abc import Callable, Mapping
from typing import Any

from app.models.llm_call import LLMProvider
from app.services.llm.client import Generation, LLMClient, LLMRequest

FakeReply = str | dict[str, Any] | Generation | Callable[[LLMRequest], Any]


class FakeLLMClient(LLMClient):
    """Deterministic replies scripted per `purpose`, recording every request it receives.

    A purpose maps to one reply or a list of replies used in order, the last
    one repeating. A reply is text, a dict sent as JSON, a full `Generation`
    (to script token counts or a stop reason), or a callable that receives the
    request and returns any of those. An unscripted purpose gets a minimal
    instance of its JSON schema, or a short placeholder text.
    """

    provider = LLMProvider.FAKE

    def __init__(
        self,
        replies: Mapping[str, FakeReply | list[FakeReply]] | None = None,
        model: str = "fake",
    ) -> None:
        super().__init__(model)
        self._replies = {
            purpose: list(reply) if isinstance(reply, list) else [reply]
            for purpose, reply in (replies or {}).items()
        }
        self.requests: list[LLMRequest] = []

    def requests_for(self, purpose: str) -> list[LLMRequest]:
        return [request for request in self.requests if request.purpose == purpose]

    async def _generate(self, request: LLMRequest) -> Generation:
        self.requests.append(request)
        reply = self._next_reply(request)
        while callable(reply):
            reply = reply(request)
        if isinstance(reply, Generation):
            return reply
        text = reply if isinstance(reply, str) else json.dumps(reply)
        prompt = request.system + "".join(m["content"] for m in request.messages)
        return Generation(
            text=text,
            input_tokens=_approximate_tokens(prompt),
            output_tokens=_approximate_tokens(text),
        )

    def _next_reply(self, request: LLMRequest) -> FakeReply:
        queue = self._replies.get(request.purpose)
        if queue:
            return queue.pop(0) if len(queue) > 1 else queue[0]
        if request.json_schema is not None:
            return example_from_schema(request.json_schema)
        return f"Fake reply for {request.purpose}."


def _approximate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 4))


def example_from_schema(
    schema: dict[str, Any], definitions: dict[str, Any] | None = None
) -> Any:
    """The simplest value that satisfies the common JSON Schema keywords."""
    definitions = schema.get("$defs", {}) if definitions is None else definitions
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        return example_from_schema(definitions[name], definitions)
    if "const" in schema:
        return schema["const"]
    if "enum" in schema:
        return schema["enum"][0]
    for combinator in ("anyOf", "oneOf"):
        if combinator in schema:
            return example_from_schema(schema[combinator][0], definitions)

    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        schema_type = schema_type[0]
    if schema_type == "object":
        return {
            name: example_from_schema(property_schema, definitions)
            for name, property_schema in schema.get("properties", {}).items()
        }
    if schema_type == "array":
        item = example_from_schema(schema.get("items", {}), definitions)
        return [item] * max(1, schema.get("minItems", 1))
    if schema_type == "string":
        return "x" * max(1, schema.get("minLength", 1))
    if schema_type in ("integer", "number"):
        return schema.get("minimum", 0)
    if schema_type == "boolean":
        return False
    return None
