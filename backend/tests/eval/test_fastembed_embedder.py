import math

import pytest

from app.config import settings
from app.models.note_embedding import EMBEDDING_DIMENSIONS
from app.services.embedding_service import FastEmbedEmbedder

pytestmark = pytest.mark.slow


@pytest.fixture(autouse=True)
def network_guard():
    """Replaces the suite-wide guard: the first run downloads the model."""
    yield


@pytest.fixture(scope="module")
def embedder() -> FastEmbedEmbedder:
    return FastEmbedEmbedder(settings.embedding_model, settings.embedding_cache_dir)


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def test_vectors_are_unit_length_and_fit_the_column(embedder):
    vectors = embedder.embed(["Mitosis has four phases", "Supply meets demand"])

    assert [len(vector) for vector in vectors] == [EMBEDDING_DIMENSIONS] * 2
    assert all(math.isclose(cosine(v, v), 1.0, rel_tol=1e-4) for v in vectors)


def test_synonyms_are_closer_than_unrelated_text(embedder):
    mitosis, division, market = embedder.embed(
        [
            "Mitosis: prophase, metaphase, anaphase, telophase",
            "How one cell splits into two identical daughter cells",
            "Supply and demand set the market price",
        ]
    )

    assert cosine(mitosis, division) > cosine(mitosis, market) + 0.1
