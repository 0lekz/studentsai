import functools
import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.models.llm_call import LLMProvider

logger = logging.getLogger(__name__)

ANTHROPIC_PRICING_URL = "https://platform.claude.com/docs/en/about-claude/pricing"
OPENAI_PRICING_URL = "https://developers.openai.com/api/docs/pricing"
TAKEN_ON = date(2026, 10, 14)

_PER_MILLION = Decimal(1_000_000)
_COST_PRECISION = Decimal("1e-10")


@dataclass(frozen=True)
class Rates:
    input_per_mtok: Decimal
    output_per_mtok: Decimal


@dataclass(frozen=True)
class LongPromptRates:
    """Rates billed for the whole request once its input exceeds the threshold."""

    above_input_tokens: int
    rates: Rates


@dataclass(frozen=True)
class ModelPrice:
    """Standard-tier list prices in USD per million tokens."""

    rates: Rates
    as_of: date
    source: str
    long_prompt: LongPromptRates | None = None

    def rates_for(self, input_tokens: int) -> Rates:
        if self.long_prompt and input_tokens > self.long_prompt.above_input_tokens:
            return self.long_prompt.rates
        return self.rates


def _price(
    source: str,
    input_rate: str,
    output_rate: str,
    long_prompt: tuple[int, str, str] | None = None,
) -> ModelPrice:
    rates = Rates(Decimal(input_rate), Decimal(output_rate))
    if long_prompt is None:
        return ModelPrice(rates, TAKEN_ON, source)
    threshold, long_input_rate, long_output_rate = long_prompt
    long_rates = Rates(Decimal(long_input_rate), Decimal(long_output_rate))
    return ModelPrice(rates, TAKEN_ON, source, LongPromptRates(threshold, long_rates))


PRICES: dict[tuple[LLMProvider, str], ModelPrice] = {
    (LLMProvider.ANTHROPIC, "claude-haiku-5-5"): _price(
        ANTHROPIC_PRICING_URL, "0.10", "0.50", (100_000, "0.50", "2.50")
    ),
    (LLMProvider.ANTHROPIC, "claude-sonnet-5-5"): _price(
        ANTHROPIC_PRICING_URL, "2.00", "10.00"
    ),
    (LLMProvider.ANTHROPIC, "claude-opus-5-5"): _price(
        ANTHROPIC_PRICING_URL, "4.00", "20.00"
    ),
    (LLMProvider.OPENAI, "gpt-6-luna"): _price(
        OPENAI_PRICING_URL, "0.10", "0.50", (272_000, "0.20", "0.75")
    ),
    (LLMProvider.OPENAI, "gpt-6.1-sol"): _price(
        OPENAI_PRICING_URL, "2.00", "10.00", (272_000, "4.00", "15.00")
    ),
    (LLMProvider.OPENAI, "gpt-6-astra"): _price(
        OPENAI_PRICING_URL, "10.00", "50.00", (272_000, "20.00", "75.00")
    ),
    (LLMProvider.FAKE, "fake"): _price("the fake client never bills", "0", "0"),
}


def estimate_cost(
    provider: LLMProvider, model: str, input_tokens: int, output_tokens: int
) -> Decimal | None:
    """List-price cost of one call, or None for a model without a price.

    Provider-side prompt-cache discounts are not applied, so for a prompt the
    provider served partly from its own cache this is an upper bound.
    """
    price = PRICES.get((provider, model))
    if price is None:
        _warn_unpriced(provider, model)
        return None
    rates = price.rates_for(input_tokens)
    cost = (
        input_tokens * rates.input_per_mtok + output_tokens * rates.output_per_mtok
    ) / _PER_MILLION
    return cost.quantize(_COST_PRECISION)


@functools.cache
def _warn_unpriced(provider: LLMProvider, model: str) -> None:
    logger.warning(
        "No price for %s model %r; its calls are logged with a null cost",
        provider,
        model,
    )
