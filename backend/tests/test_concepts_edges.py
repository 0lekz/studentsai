import uuid

import pytest

from app.models.concept import Concept
from app.repositories.concepts import Occurrence
from app.services.concepts.dedup import ConceptMatcher, clean_name
from app.services.concepts.edges import cooccurrence_scores, prerequisite_weights

LECTURE_1 = uuid.uuid4()
LECTURE_2 = uuid.uuid4()
A, B, C, D = (uuid.uuid4() for _ in range(4))
ORDER = {A: 0, B: 1, C: 2, D: 3}


def seen(concept: uuid.UUID, document: uuid.UUID, chunk_index: int) -> Occurrence:
    return Occurrence(concept, ORDER[concept], document, chunk_index)


def weights(*occurrences: Occurrence, max_incoming: int = 2) -> dict:
    return prerequisite_weights(list(occurrences), max_incoming)


class TestCooccurrenceScores:
    def test_shared_chunks_score_one_and_adjacent_chunks_half(self):
        scores = cooccurrence_scores(
            [
                seen(B, LECTURE_1, 0),
                seen(A, LECTURE_1, 0),
                seen(C, LECTURE_1, 1),
                seen(D, LECTURE_1, 3),
            ]
        )

        assert scores == {(A, B): 1.0, (A, C): 0.5, (B, C): 0.5}

    def test_the_same_chunk_index_in_another_document_is_not_adjacent(self):
        assert cooccurrence_scores([seen(A, LECTURE_1, 0), seen(B, LECTURE_2, 1)]) == {}


class TestPrerequisiteWeights:
    def test_no_occurrences_draw_no_edges(self):
        assert weights() == {}

    def test_an_edge_implied_by_a_longer_path_is_dropped(self):
        result = weights(
            seen(B, LECTURE_1, 0), seen(A, LECTURE_1, 0), seen(C, LECTURE_1, 0)
        )

        assert result == {(A, B): 1.0, (B, C): 1.0}

    def test_the_reduction_ignores_strength(self):
        result = weights(
            *(
                seen(concept, LECTURE_1, index)
                for index in (0, 2, 4)
                for concept in (A, C)
            ),
            seen(A, LECTURE_2, 0),
            seen(B, LECTURE_2, 0),
            seen(B, LECTURE_2, 5),
            seen(C, LECTURE_2, 5),
        )

        assert result == {(A, B): 1.0, (B, C): 1.0}

    def test_a_chain_across_adjacent_chunks_keeps_only_its_links(self):
        result = weights(
            seen(A, LECTURE_1, 0),
            seen(B, LECTURE_1, 0),
            seen(C, LECTURE_1, 1),
            seen(D, LECTURE_1, 2),
        )

        assert result == {(A, B): 1.0, (B, C): 0.5, (C, D): 0.5}

    def test_order_not_chunk_position_decides_the_direction(self):
        result = weights(seen(C, LECTURE_2, 0), seen(A, LECTURE_2, 1))

        assert result == {(A, C): 1.0}

    def test_each_concept_keeps_its_strongest_prerequisites_and_the_earlier_on_ties(
        self,
    ):
        occurrences = [
            seen(A, LECTURE_1, 0),
            seen(D, LECTURE_1, 0),
            seen(A, LECTURE_1, 5),
            seen(D, LECTURE_1, 5),
            seen(C, LECTURE_1, 10),
            seen(D, LECTURE_1, 10),
            seen(B, LECTURE_2, 0),
            seen(D, LECTURE_2, 0),
        ]

        assert weights(*occurrences) == {(A, D): 1.0, (B, D): 0.5}
        assert weights(*occurrences, max_incoming=1) == {(A, D): 1.0}
        assert weights(*occurrences, max_incoming=3) == {
            (A, D): 1.0,
            (B, D): 0.5,
            (C, D): 0.5,
        }

    def test_weights_are_scaled_so_the_strongest_kept_edge_weighs_one(self):
        result = weights(
            seen(A, LECTURE_1, 0),
            seen(B, LECTURE_1, 0),
            seen(A, LECTURE_1, 5),
            seen(B, LECTURE_1, 5),
            seen(A, LECTURE_2, 0),
            seen(C, LECTURE_2, 1),
        )

        assert result == {(A, B): 1.0, (A, C): 0.25}


class TestCleanName:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("  Merge   sort ", "Merge sort"),
            ("Krebs cycle.", "Krebs cycle"),
            ("Big-O notation:", "Big-O notation"),
            ("C++", "C++"),
            ("   ", None),
            ("...", None),
            ("x" * 121, None),
        ],
    )
    def test_names_are_tidied_and_unusable_ones_rejected(self, raw, expected):
        assert clean_name(raw) == expected


def concept(name: str, vector: list[float]) -> Concept:
    return Concept(id=uuid.uuid4(), name=name, embedding=vector)


class TestConceptMatcher:
    def test_names_match_ignoring_case(self):
        mitosis = concept("Mitosis", [1.0, 0.0])
        matcher = ConceptMatcher([mitosis], threshold=0.9)

        assert matcher.by_name("MITOSIS") is mitosis
        assert matcher.by_name("Meiosis") is None

    def test_the_most_similar_concept_above_the_threshold_matches(self):
        pump = concept("Sodium-potassium pump", [1.0, 0.0])
        channel = concept("Ion channel", [0.6, 0.8])
        matcher = ConceptMatcher([channel, pump], threshold=0.9)

        assert matcher.by_embedding("Sodium potassium pump", [0.99, 0.1]) is pump
        assert matcher.by_name("sodium potassium pump") is pump

    def test_similarity_at_or_below_the_threshold_does_not_match(self):
        matcher = ConceptMatcher([concept("Mitosis", [1.0, 0.0])], threshold=0.8)

        assert matcher.by_embedding("Meiosis", [0.8, 0.6]) is None
        assert matcher.by_name("Meiosis") is None

    def test_an_empty_course_matches_nothing(self):
        assert ConceptMatcher([], threshold=0.5).by_embedding("Mitosis", [1.0]) is None

    def test_vectors_are_compared_by_cosine_whatever_their_length(self):
        mitosis = concept("Mitosis", [3.0, 0.0])
        matcher = ConceptMatcher([mitosis], threshold=0.99)

        assert matcher.by_embedding("Mitoses", [0.5, 0.0]) is mitosis
        assert matcher.by_embedding("Zero", [0.0, 0.0]) is None
