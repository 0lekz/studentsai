from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from app import database
from app.database import (
    FlashcardSRS,
    create_flashcard,
    create_note,
    create_user,
    get_or_create_srs_entry,
    update_srs_after_review,
)

DEFAULT_NOW = datetime(2026, 3, 10, 15, 30, tzinfo=UTC)


class FrozenDatetime(datetime):
    frozen_at = DEFAULT_NOW

    @classmethod
    def now(cls, tz=None):
        return cls.frozen_at.astimezone(tz)


@pytest.fixture
def clock(monkeypatch) -> type[FrozenDatetime]:
    monkeypatch.setattr(FrozenDatetime, "frozen_at", DEFAULT_NOW)
    monkeypatch.setattr(database, "datetime", FrozenDatetime)
    return FrozenDatetime


@pytest.fixture
def card(db_session) -> tuple:
    user = create_user(db_session, "srs@example.com", username="srs")
    note = create_note(db_session, "Note", "Body", user.id)
    flashcard = create_flashcard(db_session, "Question?", "Answer", note.id, user.id)
    return flashcard.id, user.id


@pytest.fixture
def review(db_session, card, clock) -> Callable[[int], FlashcardSRS]:
    flashcard_id, user_id = card

    def review(quality: int) -> FlashcardSRS:
        return update_srs_after_review(db_session, flashcard_id, user_id, quality)

    return review


def today() -> date:
    return FrozenDatetime.frozen_at.astimezone(UTC).date()


def test_new_entry_starts_with_default_efactor_and_is_due_today(
    db_session, card, clock
):
    entry = get_or_create_srs_entry(db_session, *card)

    assert entry.efactor == 250
    assert entry.interval_days == 1
    assert entry.repetitions == 0
    assert entry.due_date == today()


def test_first_successful_review_schedules_one_day_out(review):
    entry = review(4)

    assert entry.repetitions == 1
    assert entry.interval_days == 1
    assert entry.due_date == today() + timedelta(days=1)


def test_second_successful_review_schedules_six_days_out(review):
    review(4)

    entry = review(4)

    assert entry.repetitions == 2
    assert entry.interval_days == 6
    assert entry.due_date == today() + timedelta(days=6)


def test_later_reviews_multiply_the_interval_by_the_previous_efactor(review):
    intervals = [review(4).interval_days for _ in range(5)]

    # 6 * 2.5 = 15, 15 * 2.5 = 37.5 rounds half to even = 38, 38 * 2.5 = 95
    assert intervals == [1, 6, 15, 38, 95]


def test_third_review_uses_the_efactor_from_before_the_current_review(review):
    review(5)
    second = review(5)
    assert second.efactor == 270

    third = review(5)

    assert third.interval_days == round(6 * 2.7)
    assert third.efactor == 280


@pytest.mark.parametrize(
    ("quality", "expected_efactor"), [(5, 260), (4, 250), (3, 236)]
)
def test_passing_review_adjusts_efactor_by_quality(review, quality, expected_efactor):
    assert review(quality).efactor == expected_efactor


def test_quality_three_is_the_lowest_passing_grade(review):
    entry = review(3)

    assert entry.repetitions == 1


@pytest.mark.parametrize("quality", [0, 1, 2])
def test_failed_review_resets_repetitions_and_interval_but_keeps_efactor(
    review, quality
):
    for _ in range(3):
        review(5)

    entry = review(quality)

    assert entry.repetitions == 0
    assert entry.interval_days == 1
    assert entry.efactor == 280
    assert entry.due_date == today() + timedelta(days=1)


def test_efactor_never_drops_below_1_3(review):
    efactors = [review(3).efactor for _ in range(10)]

    assert efactors == [236, 222, 208, 194, 180, 166, 152, 138, 130, 130]


def test_efactor_keeps_growing_with_perfect_reviews(review):
    efactors = [review(5).efactor for _ in range(5)]

    assert efactors == [260, 270, 280, 290, 300]


def test_due_date_is_counted_from_the_current_utc_date(review, clock):
    eastern = timezone(timedelta(hours=-5))
    clock.frozen_at = datetime(2026, 12, 31, 21, 0, tzinfo=eastern)

    entry = review(4)

    assert entry.due_date == date(2027, 1, 2)


def test_review_persists_the_entry(db_session, card, review):
    review(5)
    review(5)

    db_session.expire_all()
    stored = db_session.get(FlashcardSRS, card[0])

    assert (stored.repetitions, stored.interval_days, stored.efactor) == (2, 6, 270)
