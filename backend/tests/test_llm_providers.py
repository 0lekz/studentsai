import json
from collections.abc import Callable
from decimal import Decimal

import httpx
import pytest
from anthropic import AsyncAnthropic, transform_schema
from openai import AsyncOpenAI
from sqlalchemy import select

from app.models import LLMCall
from app.services.llm.anthropic_client import AnthropicClient
from app.services.llm.client import (
    LLMRefusalError,
    LLMRequestError,
    LLMUnavailableError,
)
from app.services.llm.openai_client import OpenAIClient
from app.services.llm.structured import StructuredOutput

SYSTEM = "Write one study question about the chunk."
ASK = [{"role": "user", "content": "Mitochondria produce most of a cell's ATP."}]


class Card(StructuredOutput):
    question: str
    answer: str


class Provider:
    """An httpx transport that records each request and answers from a script."""

    def __init__(self, *replies: httpx.Response | Exception) -> None:
        self.replies = list(replies)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        request.read()
        self.requests.append(request)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    def http_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(self))

    @property
    def body(self) -> dict:
        [request] = self.requests
        return json.loads(request.content)


@pytest.fixture
def logged_calls(db_session) -> Callable[[], list[LLMCall]]:
    def fetch() -> list[LLMCall]:
        db_session.expire_all()
        return list(db_session.scalars(select(LLMCall)))

    return fetch


async def ask(client, db, **overrides):
    request = {
        "system": SYSTEM,
        "messages": ASK,
        "max_tokens": 1000,
        "purpose": "question",
    }
    return await client.complete(db, **(request | overrides))


def openai_client(provider: Provider, **options) -> OpenAIClient:
    sdk = AsyncOpenAI(
        api_key="sk-test",
        base_url="http://127.0.0.1:8001/v1",
        max_retries=0,
        http_client=provider.http_client(),
    )
    return OpenAIClient(sdk, options.pop("model", "gpt-6-luna"), **options)


def chat_completion(
    content: str | None,
    *,
    finish_reason: str = "stop",
    refusal: str | None = None,
    prompt_tokens: int = 120,
    completion_tokens: int = 40,
) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "chatcmpl-1",
            "object": "chat.completion",
            "created": 1_760_400_000,
            "model": "gpt-6-luna",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": finish_reason,
                    "message": {
                        "role": "assistant",
                        "content": content,
                        "refusal": refusal,
                    },
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "completion_tokens_details": {"reasoning_tokens": 16},
            },
        },
    )


def openai_error(status: int) -> httpx.Response:
    return httpx.Response(
        status, json={"error": {"message": "nope", "type": "error", "code": None}}
    )


def anthropic_client(provider: Provider, **options) -> AnthropicClient:
    sdk = AsyncAnthropic(
        api_key="test-key", max_retries=0, http_client=provider.http_client()
    )
    return AnthropicClient(sdk, options.pop("model", "claude-haiku-5-5"), **options)


def message(
    *content: dict,
    stop_reason: str = "end_turn",
    input_tokens: int = 150,
    output_tokens: int = 60,
    **extra,
) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "msg_1",
            "type": "message",
            "role": "assistant",
            "model": "claude-haiku-5-5",
            "content": list(content),
            "stop_reason": stop_reason,
            "stop_sequence": None,
            "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
            **extra,
        },
    )


def text_block(text: str) -> dict:
    return {"type": "text", "text": text}


THINKING_BLOCK = {"type": "thinking", "thinking": "", "signature": "c2lnbmF0dXJl"}


def anthropic_error(status: int, kind: str) -> httpx.Response:
    return httpx.Response(
        status, json={"type": "error", "error": {"type": kind, "message": "nope"}}
    )


class TestOpenAIClient:
    async def test_a_schema_request_uses_chat_completions_with_a_strict_schema(
        self, db_session
    ):
        provider = Provider(chat_completion('{"question": "Q", "answer": "A"}'))

        await ask(
            openai_client(provider),
            db_session,
            json_schema=Card.model_json_schema(),
        )

        [request] = provider.requests
        assert str(request.url) == "http://127.0.0.1:8001/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer sk-test"
        assert provider.body == {
            "model": "gpt-6-luna",
            "messages": [{"role": "system", "content": SYSTEM}, *ASK],
            "max_completion_tokens": 1000,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "response",
                    "schema": Card.model_json_schema(),
                    "strict": True,
                },
            },
        }

    async def test_temperature_and_reasoning_effort_are_sent_only_when_set(
        self, db_session
    ):
        provider = Provider(chat_completion("Q"))

        await ask(
            openai_client(provider, reasoning_effort="none"),
            db_session,
            system="",
            temperature=0.3,
        )

        assert provider.body == {
            "model": "gpt-6-luna",
            "messages": ASK,
            "max_completion_tokens": 1000,
            "temperature": 0.3,
            "reasoning_effort": "none",
        }

    async def test_the_answer_is_decoded_priced_and_logged(
        self, db_session, logged_calls
    ):
        provider = Provider(chat_completion('{"question": "Q", "answer": "A"}'))

        result = await ask(
            openai_client(provider),
            db_session,
            json_schema=Card.model_json_schema(),
        )

        assert result.parsed == {"question": "Q", "answer": "A"}
        assert (result.input_tokens, result.output_tokens) == (120, 40)
        assert result.cost_usd == Decimal("0.000032")
        assert result.truncated is False
        [call] = logged_calls()
        assert (call.provider, call.model, call.cost_usd) == (
            "openai",
            "gpt-6-luna",
            Decimal("0.000032"),
        )

    async def test_a_length_finish_marks_the_result_truncated(self, db_session):
        provider = Provider(chat_completion('{"question": "Wh', finish_reason="length"))

        result = await ask(openai_client(provider), db_session)

        assert result.truncated is True

    async def test_a_refusal_is_logged_then_raised(self, db_session, logged_calls):
        provider = Provider(chat_completion(None, refusal="I can't help with that."))

        with pytest.raises(LLMRefusalError):
            await ask(openai_client(provider), db_session)

        assert len(logged_calls()) == 1

    async def test_a_self_hosted_model_without_a_price_still_works(
        self, db_session, logged_calls
    ):
        provider = Provider(chat_completion("Q"))

        result = await ask(
            openai_client(provider, model="llama-3.3-70b-instruct"), db_session
        )

        assert result.text == "Q"
        assert result.cost_usd is None
        assert provider.body["model"] == "llama-3.3-70b-instruct"

    @pytest.mark.parametrize(
        ("reply", "error"),
        [
            (openai_error(503), LLMUnavailableError),
            (openai_error(429), LLMUnavailableError),
            (httpx.ConnectError("refused"), LLMUnavailableError),
            (openai_error(400), LLMRequestError),
            (openai_error(401), LLMRequestError),
        ],
        ids=["503", "429", "connection", "400", "401"],
    )
    async def test_provider_errors_map_to_transient_or_permanent(
        self, db_session, logged_calls, reply, error
    ):
        with pytest.raises(error):
            await ask(openai_client(Provider(reply)), db_session)

        assert logged_calls() == []


class TestAnthropicClient:
    async def test_a_schema_request_uses_the_messages_api_with_output_config(
        self, db_session
    ):
        provider = Provider(message(text_block('{"question": "Q", "answer": "A"}')))

        await ask(
            anthropic_client(provider),
            db_session,
            json_schema=Card.model_json_schema(),
        )

        [request] = provider.requests
        assert str(request.url) == "https://api.anthropic.com/v1/messages"
        assert request.headers["x-api-key"] == "test-key"
        assert request.headers["anthropic-version"]
        assert provider.body == {
            "model": "claude-haiku-5-5",
            "max_tokens": 1000,
            "system": SYSTEM,
            "messages": ASK,
            "output_config": {
                "format": {
                    "type": "json_schema",
                    "schema": transform_schema(Card.model_json_schema()),
                }
            },
        }
        assert (
            provider.body["output_config"]["format"]["schema"]["additionalProperties"]
            is False
        )

    async def test_effort_and_temperature_are_sent_only_when_set(self, db_session):
        provider = Provider(message(text_block("Q")))

        await ask(
            anthropic_client(provider, reasoning_effort="low"),
            db_session,
            system="",
            temperature=1.0,
        )

        assert provider.body == {
            "model": "claude-haiku-5-5",
            "max_tokens": 1000,
            "messages": ASK,
            "temperature": 1.0,
            "output_config": {"effort": "low"},
        }

    async def test_text_blocks_are_joined_past_thinking_and_priced(
        self, db_session, logged_calls
    ):
        provider = Provider(
            message(
                THINKING_BLOCK,
                text_block('{"question": "Q", '),
                text_block('"answer": "A"}'),
            )
        )

        result = await ask(
            anthropic_client(provider),
            db_session,
            json_schema=Card.model_json_schema(),
        )

        assert result.text == '{"question": "Q", "answer": "A"}'
        assert result.parsed == {"question": "Q", "answer": "A"}
        assert (result.input_tokens, result.output_tokens) == (150, 60)
        assert result.cost_usd == Decimal("0.000045")
        [call] = logged_calls()
        assert (call.provider, call.model) == ("anthropic", "claude-haiku-5-5")

    async def test_max_tokens_marks_the_result_truncated(self, db_session):
        provider = Provider(
            message(text_block('{"question": "Wh'), stop_reason="max_tokens")
        )

        result = await ask(anthropic_client(provider), db_session)

        assert result.truncated is True

    async def test_a_refusal_is_logged_then_raised(self, db_session, logged_calls):
        provider = Provider(
            message(
                stop_reason="refusal",
                stop_details={
                    "type": "refusal",
                    "category": "cyber",
                    "explanation": "Declined.",
                },
            )
        )

        with pytest.raises(LLMRefusalError):
            await ask(anthropic_client(provider), db_session)

        assert len(logged_calls()) == 1

    @pytest.mark.parametrize(
        ("reply", "error"),
        [
            (anthropic_error(529, "overloaded_error"), LLMUnavailableError),
            (anthropic_error(500, "api_error"), LLMUnavailableError),
            (anthropic_error(429, "rate_limit_error"), LLMUnavailableError),
            (httpx.ConnectError("refused"), LLMUnavailableError),
            (anthropic_error(400, "invalid_request_error"), LLMRequestError),
            (anthropic_error(404, "not_found_error"), LLMRequestError),
        ],
        ids=["529", "500", "429", "connection", "400", "404"],
    )
    async def test_provider_errors_map_to_transient_or_permanent(
        self, db_session, logged_calls, reply, error
    ):
        with pytest.raises(error):
            await ask(anthropic_client(Provider(reply)), db_session)

        assert logged_calls() == []
