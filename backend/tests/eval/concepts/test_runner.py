import json

import pytest

from app.config import settings
from app.services.embedding_service import FakeEmbedder, FastEmbedEmbedder
from tests.eval.concepts import runner
from tests.eval.concepts.labeled import LABELED_SET, LABELS, Label
from tests.eval.concepts.runner import evaluate, match, normalize, scripted_client

METRICS = (
    "labels",
    "concepts",
    "precision",
    "recall",
    "duplicates",
    "document_precision",
    "document_recall",
    "mentions",
    "dedup_rate",
    "merged_by_embedding",
    "chunks_sent",
    "chunks_too_short",
    "chunks_failed",
    "prerequisite_candidates",
    "prerequisite_edges",
    "related_edges",
    "cost_usd",
)


class TestMatching:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("The Krebs cycle", "krebs cycle"),
            ("Light-dependent reactions", "light dependent reactions"),
            ("Na+/K+ pump", "na+ k+ pump"),
            ("  ATP ", "atp"),
        ],
    )
    def test_names_are_normalized_before_comparing(self, name, expected):
        assert normalize(name) == expected

    def test_a_spelling_variant_or_an_alias_matches_its_label(self):
        labels = [LABELS["Krebs cycle"], LABELS["Mitochondrion"]]

        matching = match(["Citric acid cycle", "mitochondria"], labels)

        assert (matching.true_positives, matching.duplicates) == (2, 0)
        assert (matching.precision, matching.recall) == (1.0, 1.0)

    def test_a_second_name_for_a_taken_label_is_a_duplicate_not_a_match(self):
        matching = match(
            ["Mitochondrion", "Mitochondria", "Golgi apparatus"],
            [LABELS["Mitochondrion"], LABELS["Osmosis"]],
        )

        assert (matching.true_positives, matching.duplicates) == (1, 1)
        assert matching.precision == pytest.approx(1 / 3)
        assert matching.recall == 0.5

    def test_nothing_predicted_or_labeled_has_no_precision_or_recall(self):
        empty = match([], [])

        assert (empty.precision, empty.recall) == (None, None)
        assert match(["Osmosis"], [Label("Mitosis")]).true_positives == 0


def test_every_mention_names_a_label_and_every_section_heading_is_unique():
    headings = [
        section.heading
        for lecture in LABELED_SET.lectures
        for section in lecture.sections
    ]
    mentions = [
        mention.label
        for lecture in LABELED_SET.lectures
        for section in lecture.sections
        for mention in section.mentions
    ]

    assert len(headings) == len(set(headings))
    assert set(mentions) <= set(LABELS)
    assert len(LABELED_SET.lectures) == 5


async def test_the_scripted_fake_with_the_fake_embedder_misses_one_merge_and_makes_one_false_one(
    db_session, tmp_path
):
    results = await evaluate(db_session, scripted_client(), FakeEmbedder(), tmp_path)

    assert {key: results[key] for key in METRICS} == {
        "labels": 48,
        "concepts": 48,
        "precision": 0.979,
        "recall": 0.979,
        "duplicates": 1,
        "document_precision": 0.981,
        "document_recall": 0.981,
        "mentions": 54,
        "dedup_rate": 0.111,
        "merged_by_embedding": 2,
        "chunks_sent": 17,
        "chunks_too_short": 2,
        "chunks_failed": 0,
        "prerequisite_candidates": 176,
        "prerequisite_edges": 46,
        "related_edges": 0,
        "cost_usd": 0.0,
    }
    names = set(results["concept_names"])
    assert {"Mitochondria", "mitochondrion"} <= names
    # The hashed bag of words puts both one-word names in one bucket.
    assert "Osmosis" in names and "Cofactor" not in names
    per_chunk = results["list_price_per_chunk"]
    assert set(per_chunk["usd"]) == {"claude-haiku-5-5", "gpt-6-luna"}
    assert per_chunk["mean_input_tokens"] > per_chunk["mean_output_tokens"] > 0


def test_the_cli_rolls_back_and_writes_the_results(database, tmp_path, capsys):
    out = tmp_path / "results" / "fake.json"

    runner.main(["--scripted", "--embedder", "fake", "--out", str(out)])

    results = json.loads(out.read_text())
    assert results["precision"] == 0.979
    assert json.loads(capsys.readouterr().out) == results


@pytest.mark.slow
class TestWithTheLocalModel:
    @pytest.fixture(autouse=True)
    def network_guard(self):
        """Replaces the suite-wide guard: the first run downloads the model."""
        yield

    async def test_the_scripted_fake_with_bge_small_merges_every_variant(
        self, db_session, tmp_path
    ):
        embedder = FastEmbedEmbedder(
            settings.embedding_model, settings.embedding_cache_dir
        )

        results = await evaluate(db_session, scripted_client(), embedder, tmp_path)

        assert (results["concepts"], results["duplicates"]) == (48, 0)
        assert (results["precision"], results["recall"]) == (1.0, 1.0)
        assert results["merged_by_embedding"] == 2
        assert (results["prerequisite_edges"], results["related_edges"]) == (46, 4)
