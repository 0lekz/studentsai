from collections.abc import Sequence
from dataclasses import dataclass

MIN_EFACTOR = 1.3
DEFAULT_EFACTOR = 2.5
REPETITIONS_FOR_FULL_CREDIT = 4


@dataclass(frozen=True)
class ReviewState:
    """A question's SM-2 state, with the E-Factor as a float such as 2.5."""

    repetitions: int
    efactor: float


def question_mastery(state: ReviewState | None) -> float:
    """One question's mastery in [0, 1]; `None` means never reviewed and counts as 0."""
    if state is None:
        return 0.0
    recall = min(1.0, state.repetitions / REPETITIONS_FOR_FULL_CREDIT)
    ease = (state.efactor - MIN_EFACTOR) / (DEFAULT_EFACTOR - MIN_EFACTOR)
    return recall * (0.5 + 0.5 * min(1.0, max(0.0, ease)))


def concept_mastery(questions: Sequence[ReviewState | None]) -> float | None:
    """The mean mastery of a concept's questions, or `None` when it has none.

    Per question: `min(1, repetitions / 4) * (0.5 + 0.5 * (efactor - 1.3) / 1.2)`.
    Four consecutive successful reviews earn full recall credit, and the
    E-Factor scales it from half credit at the SM-2 floor of 1.3 to full credit
    at the starting ease of 2.5; ease above 2.5 is capped so mastery stays in
    [0, 1]. A failed review resets repetitions, so the question drops to 0 until
    it is recalled again. This is a heuristic the product can tune.
    """
    if not questions:
        return None
    return sum(question_mastery(state) for state in questions) / len(questions)
