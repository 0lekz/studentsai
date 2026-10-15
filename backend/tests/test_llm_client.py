import json
import logging
import uuid
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Literal

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from app.config import Settings, settings
from app.models import LLMCacheEntry, LLMCall
from app.models.llm_call import LLMProvider
from app.services.llm.anthropic_client import AnthropicClient
from app.services.llm.client import (
    DEFAULT_MODELS,
    Generation,
    LLMRefusalError,
    StopReason,
    get_llm_client,
)
from app.services.llm.fake_client import FakeLLMClient, example_from_schema
from app.services.llm.openai_client import OpenAIClient
from app.services.llm.pricing import PRICES, TAKEN_ON, _warn_unpriced, estimate_cost
from app.services.llm.structured import (
    StructuredOutput,
    StructuredOutputError,
    complete_structured,
)

SYSTEM = "Write one study question about the chunk."
ASK = [{"role": "user", "content": "Mitochondria produce most of a cell's ATP."}]


class PricedFake(FakeLLMClient):
    """The fake's scripting with a real provider's identity, so pricing applies."""

    provider = LLMProvider.ANTHROPIC


class Topic(StructuredOutput):
    name: str


class Flashcard(StructuredOutput):
    question: str
    answer: str
    difficulty: Literal["easy", "hard"]
    topics: list[Topic]


VALID_CARD = {
    "question": "Which organelle makes most ATP?",
    "answer": "The mitochondrion.",
    "difficulty": "easy",
    "topics": [{"name": "cell biology"}],
}


@pytest.fixture
def logged_calls(db_session) -> Callable[[], list[LLMCall]]:
    def fetch() -> list[LLMCall]:
        db_session.expire_all()
        return list(db_session.scalars(select(LLMCall)))

    return fetch


@pytest.fixture
def cache_size(db_session) -> Callable[[], int]:
    def count() -> int:
        return db_session.scalar(select(func.count()).select_from(LLMCacheEntry))

    return count


@pytest.fixture
def rebuilt_client():
    get_llm_client.cache_clear()
    yield
    get_llm_client.cache_clear()


async def ask(client, db, **overrides):
    request = {
        "system": SYSTEM,
        "messages": ASK,
        "max_tokens": 1000,
        "purpose": "question",
    }
    return await client.complete(db, **(request | overrides))


class TestSettings:
    def test_provider_defaults_to_fake_until_keys_are_configured(self):
        assert Settings.model_fields["llm_provider"].default == "fake"
        assert Settings.model_fields["llm_model"].default is None

    def test_provider_rejects_unknown_values(self):
        with pytest.raises(ValidationError):
            Settings(llm_provider="gemini")


class TestGetLLMClient:
    def test_tests_use_the_fake_client(self, rebuilt_client):
        client = get_llm_client()

        assert isinstance(client, FakeLLMClient)
        assert get_llm_client() is client

    @pytest.mark.parametrize(
        ("provider", "client_type"),
        [("openai", OpenAIClient), ("anthropic", AnthropicClient)],
    )
    def test_real_clients_take_endpoint_timeout_retries_and_effort_from_settings(
        self, monkeypatch, rebuilt_client, provider, client_type
    ):
        for name, value in {
            "llm_provider": provider,
            "llm_model": None,
            "llm_base_url": "http://127.0.0.1:8001/v1/",
            "llm_timeout_seconds": 12.5,
            "llm_max_retries": 4,
            "llm_reasoning_effort": "low",
            "anthropic_api_key": "test",
        }.items():
            monkeypatch.setattr(settings, name, value)

        client = get_llm_client()

        assert isinstance(client, client_type)
        assert client.model == DEFAULT_MODELS[LLMProvider(provider)]
        assert client.reasoning_effort == "low"
        assert str(client.sdk.base_url) == "http://127.0.0.1:8001/v1/"
        assert client.sdk.timeout == 12.5
        assert client.sdk.max_retries == 4

    def test_a_configured_model_overrides_the_provider_default(
        self, monkeypatch, rebuilt_client
    ):
        monkeypatch.setattr(settings, "llm_provider", "openai")
        monkeypatch.setattr(settings, "llm_model", "llama-3.3-70b-instruct")

        assert get_llm_client().model == "llama-3.3-70b-instruct"


class TestPricing:
    def test_every_default_model_has_a_dated_sourced_price(self):
        for provider, model in DEFAULT_MODELS.items():
            price = PRICES[(provider, model)]
            assert price.as_of == TAKEN_ON == date(2026, 10, 14)
            assert price.source

    def test_cost_is_tokens_times_the_per_million_rate(self):
        assert estimate_cost(LLMProvider.OPENAI, "gpt-6-luna", 2_000, 500) == Decimal(
            "0.00045"
        )
        assert estimate_cost(
            LLMProvider.ANTHROPIC, "claude-opus-5-5", 1_000_000, 1_000_000
        ) == Decimal("24")

    def test_a_prompt_over_the_threshold_bills_the_whole_request_at_long_rates(self):
        at_threshold = estimate_cost(
            LLMProvider.ANTHROPIC, "claude-haiku-5-5", 100_000, 1_000
        )
        over_threshold = estimate_cost(
            LLMProvider.ANTHROPIC, "claude-haiku-5-5", 100_001, 1_000
        )

        assert at_threshold == Decimal("0.0105")
        assert over_threshold == Decimal("0.0525005")

    def test_the_fake_never_costs_anything(self):
        assert estimate_cost(LLMProvider.FAKE, "fake", 10_000, 10_000) == 0

    def test_an_unknown_model_costs_none_and_warns_once(self, caplog):
        _warn_unpriced.cache_clear()

        with caplog.at_level(logging.WARNING, logger="app.services.llm.pricing"):
            first = estimate_cost(LLMProvider.OPENAI, "llama-3.3-70b", 10, 10)
            second = estimate_cost(LLMProvider.OPENAI, "llama-3.3-70b", 10, 10)

        assert first is second is None
        assert [record.levelname for record in caplog.records] == ["WARNING"]
        assert "llama-3.3-70b" in caplog.records[0].getMessage()


class TestFakeClient:
    async def test_replies_are_scripted_by_purpose_and_requests_recorded(
        self, db_session
    ):
        fake = FakeLLMClient({"question": "What makes ATP?", "grade": "Correct."})

        result = await ask(fake, db_session)

        assert result.text == "What makes ATP?"
        [request] = fake.requests_for("question")
        assert request.system == SYSTEM
        assert request.messages == tuple(ASK)
        assert fake.requests_for("grade") == []

    async def test_a_list_of_replies_is_used_in_order_and_the_last_repeats(
        self, db_session
    ):
        fake = FakeLLMClient({"question": ["first", "second"]})

        texts = [(await ask(fake, db_session)).text for _ in range(3)]

        assert texts == ["first", "second", "second"]

    async def test_a_callable_reply_receives_the_request(self, db_session):
        fake = FakeLLMClient(
            {"question": lambda request: request.messages[-1]["content"].upper()}
        )

        result = await ask(fake, db_session)

        assert result.text == ASK[0]["content"].upper()

    async def test_token_counts_are_deterministic(self, db_session):
        first = await ask(FakeLLMClient(), db_session)
        second = await ask(FakeLLMClient(), db_session)

        assert (first.input_tokens, first.output_tokens) == (
            second.input_tokens,
            second.output_tokens,
        )
        assert first.input_tokens > 0

    async def test_an_unscripted_purpose_gets_placeholder_text(self, db_session):
        result = await ask(FakeLLMClient(), db_session)

        assert result.text == "Fake reply for question."

    async def test_an_unscripted_schema_request_gets_a_valid_instance(self, db_session):
        result = await ask(
            FakeLLMClient(), db_session, json_schema=Flashcard.model_json_schema()
        )

        assert Flashcard.model_validate(result.parsed)

    def test_schema_examples_respect_bounds_and_combinators(self):
        schema = {
            "type": "object",
            "properties": {
                "score": {"type": "integer", "minimum": 1},
                "tags": {"type": "array", "items": {"type": "string"}, "minItems": 2},
                "note": {"anyOf": [{"type": "null"}, {"type": "string"}]},
                "kind": {"const": "card"},
            },
        }

        assert example_from_schema(schema) == {
            "score": 1,
            "tags": ["x", "x"],
            "note": None,
            "kind": "card",
        }


class TestComplete:
    async def test_every_call_is_logged_with_user_tokens_cost_and_latency(
        self, db_session, logged_calls, user
    ):
        user_id = uuid.UUID(user.id)
        fake = PricedFake(
            {"question": Generation("What makes ATP?", 1_200, 30)},
            model="claude-haiku-5-5",
        )

        result = await ask(fake, db_session, user_id=user_id)

        assert result.cost_usd == Decimal("0.000135")
        assert (result.provider, result.model, result.cached) == (
            LLMProvider.ANTHROPIC,
            "claude-haiku-5-5",
            False,
        )
        [call] = logged_calls()
        assert call.user_id == user_id
        assert (call.provider, call.model, call.purpose) == (
            "anthropic",
            "claude-haiku-5-5",
            "question",
        )
        assert (call.input_tokens, call.output_tokens) == (1_200, 30)
        assert call.cost_usd == Decimal("0.000135")
        assert call.latency_ms == result.latency_ms >= 0
        assert call.cached is False
        assert call.created_at is not None

    async def test_a_call_to_an_unpriced_model_is_logged_with_a_null_cost(
        self, db_session, logged_calls
    ):
        result = await ask(PricedFake(model="claude-unreleased"), db_session)

        assert result.cost_usd is None
        [call] = logged_calls()
        assert call.cost_usd is None

    async def test_the_log_survives_a_caller_rollback_and_leaves_caller_work_alone(
        self, db_session, logged_calls
    ):
        pending = LLMCall(
            provider="fake",
            model="pending",
            purpose="caller-work",
            input_tokens=0,
            output_tokens=0,
            latency_ms=0,
        )
        db_session.add(pending)

        await ask(FakeLLMClient(), db_session)
        db_session.rollback()

        assert [call.purpose for call in logged_calls()] == ["question"]

    @pytest.mark.parametrize(
        "messages",
        [[], [*ASK, {"role": "assistant", "content": "Prefilled"}]],
        ids=["empty", "ends-with-assistant"],
    )
    async def test_messages_must_end_with_a_user_turn(
        self, db_session, logged_calls, messages
    ):
        with pytest.raises(ValueError, match="end with a user turn"):
            await ask(FakeLLMClient(), db_session, messages=messages)

        assert logged_calls() == []

    async def test_a_schema_request_decodes_json_and_tolerates_non_json(
        self, db_session
    ):
        fake = FakeLLMClient({"question": [VALID_CARD, "not json"]})
        schema = Flashcard.model_json_schema()

        decoded = await ask(fake, db_session, json_schema=schema)
        undecodable = await ask(fake, db_session, json_schema=schema)

        assert decoded.parsed == VALID_CARD
        assert undecodable.parsed is None
        assert (await ask(fake, db_session)).parsed is None

    async def test_hitting_max_tokens_marks_the_result_truncated(self, db_session):
        fake = FakeLLMClient(
            {"question": Generation("What mak", 50, 1000, StopReason.MAX_TOKENS)}
        )

        result = await ask(fake, db_session)

        assert result.truncated is True

    async def test_a_refusal_is_logged_then_raised(self, db_session, logged_calls):
        fake = FakeLLMClient({"question": Generation("", 40, 2, StopReason.REFUSAL)})

        with pytest.raises(LLMRefusalError, match="question"):
            await ask(fake, db_session)

        [call] = logged_calls()
        assert (call.input_tokens, call.output_tokens) == (40, 2)


class TestCache:
    async def test_caching_is_opt_in(self, db_session, cache_size):
        fake = FakeLLMClient({"question": ["first", "second"]})

        texts = [(await ask(fake, db_session)).text for _ in range(2)]

        assert texts == ["first", "second"]
        assert cache_size() == 0

    async def test_a_hit_returns_the_stored_result_and_logs_a_free_cached_call(
        self, db_session, logged_calls
    ):
        fake = PricedFake(
            {"question": [Generation("first", 1_000, 20), "second"]},
            model="claude-haiku-5-5",
        )

        stored = await ask(fake, db_session, cache_version="question-v1")
        replayed = await ask(fake, db_session, cache_version="question-v1")

        assert len(fake.requests) == 1
        assert replayed.text == "first"
        assert replayed.cached is True
        assert replayed.cost_usd == 0
        assert (replayed.input_tokens, replayed.output_tokens) == (1_000, 20)
        assert sorted((call.cached, call.cost_usd) for call in logged_calls()) == [
            (False, stored.cost_usd),
            (True, Decimal(0)),
        ]

    async def test_a_hit_returns_the_stored_parsed_json(self, db_session):
        fake = FakeLLMClient({"question": VALID_CARD})
        schema = Flashcard.model_json_schema()

        await ask(fake, db_session, json_schema=schema, cache_version="card-v1")
        replayed = await ask(
            fake, db_session, json_schema=schema, cache_version="card-v1"
        )

        assert replayed.cached is True
        assert replayed.parsed == VALID_CARD

    @pytest.mark.parametrize(
        "change",
        [
            {"cache_version": "question-v2"},
            {"system": "Write two questions."},
            {"messages": [{"role": "user", "content": "Ribosomes make protein."}]},
            {"json_schema": {"type": "object", "properties": {}}},
            {"max_tokens": 2000},
            {"temperature": 0.2},
        ],
        ids=lambda change: next(iter(change)),
    )
    async def test_a_change_to_anything_that_shapes_the_output_misses(
        self, db_session, change
    ):
        fake = FakeLLMClient()
        cached = {"cache_version": "question-v1"}

        await ask(fake, db_session, **cached)
        await ask(fake, db_session, **(cached | change))

        assert len(fake.requests) == 2

    async def test_the_reasoning_effort_is_part_of_the_key(self, db_session):
        low, high = FakeLLMClient(), FakeLLMClient()
        low.reasoning_effort, high.reasoning_effort = "low", "high"

        await ask(low, db_session, cache_version="question-v1")
        await ask(high, db_session, cache_version="question-v1")
        await ask(low, db_session, cache_version="question-v1")

        assert (len(low.requests), len(high.requests)) == (1, 1)

    @pytest.mark.parametrize(
        ("reply", "json_schema"),
        [
            (Generation('{"question": "Wh', 50, 1000, StopReason.MAX_TOKENS), None),
            ("not json", {"type": "object", "properties": {}}),
        ],
        ids=["truncated", "invalid-json"],
    )
    async def test_unusable_answers_are_not_cached(
        self, db_session, cache_size, reply, json_schema
    ):
        fake = FakeLLMClient({"question": reply})

        for _ in range(2):
            await ask(fake, db_session, json_schema=json_schema, cache_version="v1")

        assert len(fake.requests) == 2
        assert cache_size() == 0

    async def test_refusals_are_not_cached(self, db_session, cache_size):
        fake = FakeLLMClient({"question": Generation("", 40, 2, StopReason.REFUSAL)})

        with pytest.raises(LLMRefusalError):
            await ask(fake, db_session, cache_version="v1")

        assert cache_size() == 0


class TestStructured:
    def test_response_models_produce_strict_schemas(self):
        schema = Flashcard.model_json_schema()

        for definition in [schema, *schema["$defs"].values()]:
            assert definition["additionalProperties"] is False
            assert set(definition["required"]) == set(definition["properties"])

    async def test_a_valid_answer_is_validated_into_the_model(self, db_session):
        fake = FakeLLMClient({"card": VALID_CARD})

        result = await complete_structured(
            fake,
            db_session,
            response_model=Flashcard,
            system=SYSTEM,
            messages=ASK,
            max_tokens=1000,
            purpose="card",
        )

        assert result.value == Flashcard.model_validate(VALID_CARD)
        assert len(result.calls) == 1
        assert result.cost_usd == 0
        [request] = fake.requests
        assert request.json_schema == Flashcard.model_json_schema()

    async def test_an_invalid_answer_is_retried_once_with_its_validation_errors(
        self, db_session, logged_calls
    ):
        invalid = VALID_CARD | {"difficulty": "medium"}
        fake = FakeLLMClient({"card": [invalid, VALID_CARD]})

        result = await complete_structured(
            fake,
            db_session,
            response_model=Flashcard,
            system=SYSTEM,
            messages=ASK,
            max_tokens=1000,
            purpose="card",
        )

        assert result.value.difficulty == "easy"
        assert len(result.calls) == 2
        first, retry = fake.requests
        assert retry.messages[: len(first.messages)] == first.messages
        echoed, feedback = retry.messages[len(first.messages) :]
        assert echoed == {"role": "assistant", "content": json.dumps(invalid)}
        assert feedback["role"] == "user"
        assert "- difficulty: Input should be 'easy' or 'hard'" in feedback["content"]
        assert len(logged_calls()) == 2

    async def test_a_second_invalid_answer_raises_with_both_calls(self, db_session):
        fake = FakeLLMClient({"card": "not json"})

        with pytest.raises(StructuredOutputError, match="Invalid JSON") as raised:
            await complete_structured(
                fake,
                db_session,
                response_model=Flashcard,
                system=SYSTEM,
                messages=ASK,
                max_tokens=1000,
                purpose="card",
            )

        assert len(raised.value.calls) == len(fake.requests) == 2

    async def test_an_empty_truncated_answer_is_not_echoed_back(self, db_session):
        cut_off = Generation("", 50, 1000, StopReason.MAX_TOKENS)
        fake = FakeLLMClient({"card": [cut_off, VALID_CARD]})

        await complete_structured(
            fake,
            db_session,
            response_model=Flashcard,
            system=SYSTEM,
            messages=ASK,
            max_tokens=1000,
            purpose="card",
        )

        assert [message["role"] for message in fake.requests[1].messages] == [
            "user",
            "user",
        ]

    async def test_cost_is_none_when_any_call_is_unpriced(self, db_session):
        fake = PricedFake({"card": VALID_CARD}, model="claude-unreleased")

        result = await complete_structured(
            fake,
            db_session,
            response_model=Flashcard,
            system=SYSTEM,
            messages=ASK,
            max_tokens=1000,
            purpose="card",
        )

        assert result.cost_usd is None
