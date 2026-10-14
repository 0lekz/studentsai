from collections import Counter

import numpy as np
import pytest

from tests.eval.benchmark import (
    bootstrap_interval,
    edge_scores,
    load_corpus,
    partner_rank,
    rank_neighbours,
    retrieval_scores,
    same_topic_matrix,
    tfidf_similarity,
)


@pytest.fixture(scope="module")
def corpus():
    return load_corpus()


class TestCorpus:
    def test_has_80_to_120_notes_with_unique_ids_across_6_to_8_subjects(self, corpus):
        ids = [note.id for note in corpus.notes]

        assert 80 <= len(ids) <= 120
        assert len(set(ids)) == len(ids)
        assert 6 <= len({note.subject for note in corpus.notes}) <= 8

    def test_every_topic_has_at_least_three_notes(self, corpus):
        assert min(Counter(corpus.topics).values()) >= 3

    def test_synonymy_pairs_share_a_topic_and_near_misses_do_not(self, corpus):
        def topic(note_id: str) -> str:
            return corpus.notes[corpus.position(note_id)].topic

        assert all(topic(a) == topic(b) for a, b in corpus.synonymy)
        assert all(topic(a) != topic(b) for a, b in corpus.near_miss)

    def test_the_production_tfidf_path_scores_every_pair(self, corpus):
        similarity = tfidf_similarity(corpus)

        assert similarity.shape == (len(corpus.notes), len(corpus.notes))
        assert np.allclose(np.diag(similarity), 1.0)


class TestMetrics:
    topics = ("a", "a", "b", "b", "b")
    similarity = np.array(
        [
            [1.0, 0.2, 0.9, 0.1, 0.0],
            [0.2, 1.0, 0.1, 0.3, 0.0],
            [0.9, 0.1, 1.0, 0.8, 0.7],
            [0.1, 0.3, 0.8, 1.0, 0.6],
            [0.0, 0.0, 0.7, 0.6, 1.0],
        ]
    )

    def test_neighbours_are_ranked_most_similar_first_without_the_query(self):
        assert rank_neighbours(self.similarity)[0].tolist() == [2, 1, 3, 4]

    def test_partner_rank_is_one_based(self):
        neighbours = rank_neighbours(self.similarity)

        assert partner_rank(neighbours, 0, 2) == 1
        assert partner_rank(neighbours, 0, 1) == 2

    def test_precision_and_recall_at_k(self):
        scores = retrieval_scores(rank_neighbours(self.similarity), self.topics, (1, 2))

        assert scores.precision[1] == pytest.approx((0 + 0 + 0 + 1 + 1) / 5)
        assert scores.recall[1] == pytest.approx((0 + 0 + 0 + 1 / 2 + 1 / 2) / 5)
        assert scores.precision[2] == pytest.approx((1 / 2 + 1 / 2 + 1 / 2 + 1 + 1) / 5)
        assert scores.recall[2] == pytest.approx((1 + 1 + 1 / 2 + 1 + 1) / 5)

    def test_a_perfect_ranking_reaches_the_ceiling(self):
        perfect = rank_neighbours(same_topic_matrix(self.topics))

        scores = retrieval_scores(perfect, self.topics, (1, 2))

        assert scores.precision == {
            1: 1.0,
            2: pytest.approx((1 / 2 + 1 / 2 + 1 + 1 + 1) / 5),
        }
        assert scores.recall == {
            1: pytest.approx((1 + 1 + 1 / 2 + 1 / 2 + 1 / 2) / 5),
            2: 1.0,
        }

    def test_ties_do_not_follow_corpus_order(self):
        tied = np.eye(40)

        first_neighbours = rank_neighbours(tied)[:, 0]

        assert not np.array_equal(first_neighbours[1:], np.zeros(39))

    def test_edge_scores_count_pairs_above_the_threshold(self):
        scores = edge_scores(self.similarity, self.topics, 0.5)

        assert scores.edges == 4
        assert scores.precision == pytest.approx(3 / 4)
        assert scores.recall == pytest.approx(3 / 4)
        assert scores.f1 == pytest.approx(3 / 4)


def test_bootstrap_interval_brackets_the_mean_gain():
    gains = np.array([0.0, 1.0] * 50)

    low, high = bootstrap_interval(gains)

    assert low < 0.5 < high
    assert bootstrap_interval(np.full(10, 0.25)) == pytest.approx((0.25, 0.25))
