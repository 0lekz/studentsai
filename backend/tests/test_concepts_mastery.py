import pytest

from app.services.concepts.mastery import ReviewState, concept_mastery, question_mastery


def test_a_concept_without_questions_has_no_mastery():
    assert concept_mastery([]) is None


def test_a_question_never_reviewed_counts_as_zero():
    assert question_mastery(None) == 0
    assert concept_mastery([None, None]) == 0


@pytest.mark.parametrize(
    ("repetitions", "efactor", "expected"),
    [
        (0, 2.5, 0.0),
        (1, 2.5, 0.25),
        (2, 2.5, 0.5),
        (4, 2.5, 1.0),
        (9, 2.5, 1.0),
        (4, 1.3, 0.5),
        (4, 1.9, 0.75),
        (2, 1.9, 0.375),
    ],
)
def test_recall_credit_grows_with_repetitions_and_is_scaled_by_ease(
    repetitions, efactor, expected
):
    assert question_mastery(ReviewState(repetitions, efactor)) == pytest.approx(
        expected
    )


def test_ease_above_the_starting_value_is_capped_so_mastery_stays_within_one():
    assert question_mastery(ReviewState(4, 2.8)) == 1.0


def test_concept_mastery_is_the_mean_over_its_questions():
    questions = [ReviewState(4, 2.5), ReviewState(2, 2.5), None]

    assert concept_mastery(questions) == pytest.approx((1.0 + 0.5 + 0) / 3)
