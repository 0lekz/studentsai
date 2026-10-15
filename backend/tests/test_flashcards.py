import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Document, DocumentChunk, Flashcard
from app.repositories.flashcards import create_flashcard
from app.repositories.notes import create_note as insert_note
from app.services.courses import create_course

MISSING_ID = "00000000-0000-0000-0000-000000000000"


@pytest.fixture
def note(auth_client, create_note) -> dict:
    return create_note(auth_client, "Cells", "The mitochondria is the powerhouse.")


@pytest.fixture
def flashcard(auth_client, note) -> dict:
    response = auth_client.post(
        f"/notes/{note['id']}/flashcards/generate", params={"count": 1}
    )
    assert response.status_code == 200, response.text
    return response.json()[0]


def user_cards(client, **params) -> list[dict]:
    response = client.get("/flashcards/user", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def review(client, card_id: str, quality: int):
    return client.post(
        f"/flashcards/{card_id}/review", json={"quality_rating": quality}
    )


def utc_days_from_today(days: int) -> str:
    return (datetime.now(UTC).date() + timedelta(days=days)).isoformat()


def test_generate_for_note_saves_the_ai_cards(auth_client, note, fake_ai):
    response = auth_client.post(
        f"/notes/{note['id']}/flashcards/generate", params={"count": 3}
    )

    assert response.status_code == 200
    cards = response.json()
    assert [(c["question"], c["answer"]) for c in cards] == [
        ("Question 1?", "Answer 1"),
        ("Question 2?", "Answer 2"),
        ("Question 3?", "Answer 3"),
    ]
    assert all(c["review_count"] == 0 for c in cards)
    assert all(c["course_id"] is None for c in cards)
    assert fake_ai.calls == [
        (
            "generate_flashcards_from_content",
            {"content": note["content"], "count": 3},
        )
    ]


def test_flashcards_carry_no_mastery_or_contextual_fields(flashcard):
    assert set(flashcard) == {
        "id",
        "question",
        "answer",
        "difficulty",
        "last_reviewed",
        "created_at",
        "tags",
        "review_count",
        "course_id",
        "kind",
        "choices",
        "source",
    }


def test_new_flashcards_are_user_recall_cards_without_choices(flashcard):
    assert (flashcard["kind"], flashcard["choices"], flashcard["source"]) == (
        "recall",
        None,
        "user",
    )


def test_generate_for_note_defaults_to_five_cards(auth_client, note):
    response = auth_client.post(f"/notes/{note['id']}/flashcards/generate")

    assert len(response.json()) == 5


def test_generate_for_another_users_note_returns_404(other_auth_client, note):
    response = other_auth_client.post(f"/notes/{note['id']}/flashcards/generate")

    assert response.status_code == 404


def test_note_flashcards_lists_cards_generated_for_that_note(
    auth_client, note, create_note
):
    auth_client.post(f"/notes/{note['id']}/flashcards/generate", params={"count": 2})
    unrelated = create_note(auth_client, "Other", "Body")
    auth_client.post(
        f"/notes/{unrelated['id']}/flashcards/generate", params={"count": 1}
    )

    response = auth_client.get(f"/notes/{note['id']}/flashcards")

    assert response.status_code == 200
    assert sorted(c["question"] for c in response.json()) == [
        "Question 1?",
        "Question 2?",
    ]


def test_user_flashcards_lists_only_the_callers_cards(
    auth_client, other_auth_client, flashcard
):
    assert [c["id"] for c in user_cards(auth_client)] == [flashcard["id"]]
    assert user_cards(other_auth_client) == []


def test_user_flashcards_search_matches_question_or_answer_case_insensitively(
    auth_client, note
):
    auth_client.post(f"/notes/{note['id']}/flashcards/generate", params={"count": 3})

    assert [c["question"] for c in user_cards(auth_client, search="question 2")] == [
        "Question 2?"
    ]
    assert [c["answer"] for c in user_cards(auth_client, search="ANSWER 3")] == [
        "Answer 3"
    ]


def test_user_flashcards_filters_by_tag(auth_client, note):
    cards = auth_client.post(
        f"/notes/{note['id']}/flashcards/generate", params={"count": 2}
    ).json()
    auth_client.post(f"/flashcards/{cards[0]['id']}/tags/visit_later")

    tagged = user_cards(auth_client, tags="visit_later,unused")

    assert [c["id"] for c in tagged] == [cards[0]["id"]]


def test_cards_generated_from_a_course_note_belong_to_that_course(
    auth_client, create_course, create_note
):
    biology = create_course(auth_client, "Biology")
    chemistry = create_course(auth_client, "Chemistry")
    cell_note = create_note(auth_client, "Cells", "Body", course_id=biology["id"])
    loose_note = create_note(auth_client, "Loose", "Body")
    auth_client.post(
        f"/notes/{cell_note['id']}/flashcards/generate", params={"count": 2}
    )
    auth_client.post("/flashcards/generate", json={"note_id": cell_note["id"]})
    auth_client.post(
        f"/notes/{loose_note['id']}/flashcards/generate", params={"count": 1}
    )

    in_biology = user_cards(auth_client, course_id=biology["id"])

    assert len(in_biology) == 7
    assert {c["course_id"] for c in in_biology} == {biology["id"]}
    assert user_cards(auth_client, course_id=chemistry["id"]) == []
    assert len(user_cards(auth_client)) == 8


def test_user_flashcards_for_another_users_course_returns_404(
    auth_client, other_auth_client, create_course
):
    theirs = create_course(other_auth_client)

    response = auth_client.get("/flashcards/user", params={"course_id": theirs["id"]})

    assert response.status_code == 404
    assert response.json() == {"detail": "Course not found"}


def test_new_cards_are_due_for_review_right_away(auth_client, note):
    cards = auth_client.post(
        f"/notes/{note['id']}/flashcards/generate", params={"count": 2}
    ).json()

    response = auth_client.get("/flashcards/due/srs")

    assert {c["id"] for c in response.json()} == {c["id"] for c in cards}


def test_ai_flashcards_returns_generated_cards_without_saving(auth_client, fake_ai):
    response = auth_client.post(
        "/ai/flashcards", json={"content": "Some study text", "count": 2}
    )

    assert response.status_code == 200
    assert response.json() == {
        "flashcards": [
            {"question": "Question 1?", "answer": "Answer 1"},
            {"question": "Question 2?", "answer": "Answer 2"},
        ],
        "count": 2,
    }
    assert user_cards(auth_client) == []


def test_generate_creates_a_set_of_cards_that_are_due(auth_client, note):
    response = auth_client.post(
        "/flashcards/generate", json={"note_id": note["id"], "count": 2}
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"flashcard_set_id", "cards"}
    assert len(body["cards"]) == 2
    [flashcard_set] = auth_client.get("/flashcards/sets").json()
    assert flashcard_set == {
        "id": body["flashcard_set_id"],
        "seed_note_id": note["id"],
        "created_at": flashcard_set["created_at"],
        "flashcard_count": 2,
    }
    due_ids = {c["id"] for c in auth_client.get("/flashcards/due/srs").json()}
    assert due_ids == {c["id"] for c in body["cards"]}


def test_generate_for_unknown_note_returns_404(auth_client):
    response = auth_client.post("/flashcards/generate", json={"note_id": MISSING_ID})

    assert response.status_code == 404


def test_review_returns_the_sm2_schedule(auth_client, flashcard):
    response = review(auth_client, flashcard["id"], 5)

    assert response.status_code == 200
    assert response.json() == {
        "flashcard_id": flashcard["id"],
        "quality_rating": 5,
        "repetitions": 1,
        "interval_days": 1,
        "efactor": 2.6,
        "due_date": utc_days_from_today(1),
    }
    [card] = user_cards(auth_client)
    assert card["review_count"] == 1
    assert card["last_reviewed"] is not None
    assert auth_client.get("/flashcards/due/srs").json() == []


def test_second_successful_review_moves_the_card_six_days_out(auth_client, flashcard):
    review(auth_client, flashcard["id"], 5)

    body = review(auth_client, flashcard["id"], 5).json()

    assert body["repetitions"] == 2
    assert body["interval_days"] == 6
    assert body["efactor"] == 2.7
    assert body["due_date"] == utc_days_from_today(6)


def test_failed_review_keeps_the_card_due_tomorrow(auth_client, flashcard):
    review(auth_client, flashcard["id"], 5)

    body = review(auth_client, flashcard["id"], 1).json()

    assert (body["repetitions"], body["interval_days"]) == (0, 1)
    assert body["efactor"] == 2.6
    assert body["due_date"] == utc_days_from_today(1)


@pytest.mark.parametrize("quality", [-1, 6])
def test_review_rejects_a_rating_outside_zero_to_five(auth_client, flashcard, quality):
    assert review(auth_client, flashcard["id"], quality).status_code == 422


def test_review_requires_a_rating(auth_client, flashcard):
    response = auth_client.post(
        f"/flashcards/{flashcard['id']}/review", json={"typed_answer": "Answer 1"}
    )

    assert response.status_code == 422


def test_review_of_unknown_flashcard_returns_404(auth_client):
    response = review(auth_client, MISSING_ID, 5)

    assert response.status_code == 404
    assert response.json() == {"detail": "Flashcard not found"}


def test_first_tag_on_a_flashcard_is_stored(auth_client, flashcard):
    response = auth_client.post(f"/flashcards/{flashcard['id']}/tags/visit_later")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Tag 'visit_later' added successfully",
        "tags": ["visit_later"],
    }
    assert user_cards(auth_client)[0]["tags"] == ["visit_later"]


def test_second_tag_on_a_flashcard_is_stored(auth_client, flashcard):
    auth_client.post(f"/flashcards/{flashcard['id']}/tags/visit_later")

    response = auth_client.post(f"/flashcards/{flashcard['id']}/tags/revisited")

    assert response.status_code == 200
    assert response.json()["tags"] == ["visit_later", "revisited"]
    assert user_cards(auth_client)[0]["tags"] == ["visit_later", "revisited"]


def test_adding_a_tag_twice_keeps_one(auth_client, flashcard):
    auth_client.post(f"/flashcards/{flashcard['id']}/tags/visit_later")

    response = auth_client.post(f"/flashcards/{flashcard['id']}/tags/visit_later")

    assert response.json()["tags"] == ["visit_later"]


def test_removing_a_flashcard_tag_is_stored(auth_client, flashcard):
    auth_client.post(f"/flashcards/{flashcard['id']}/tags/visit_later")
    auth_client.post(f"/flashcards/{flashcard['id']}/tags/revisited")

    response = auth_client.delete(f"/flashcards/{flashcard['id']}/tags/visit_later")

    assert response.json() == {
        "message": "Tag 'visit_later' removed successfully",
        "tags": ["revisited"],
    }
    assert user_cards(auth_client)[0]["tags"] == ["revisited"]


def test_tagging_unknown_flashcard_returns_404(auth_client):
    response = auth_client.post(f"/flashcards/{MISSING_ID}/tags/visit_later")

    assert response.status_code == 404


def test_another_users_flashcard_cannot_be_tagged_or_reviewed(
    auth_client, other_auth_client, flashcard
):
    card_url = f"/flashcards/{flashcard['id']}"

    assert other_auth_client.post(f"{card_url}/tags/bob_was_here").status_code == 404
    assert other_auth_client.delete(f"{card_url}/tags/bob_was_here").status_code == 404
    assert review(other_auth_client, flashcard["id"], 5).status_code == 404
    [card] = user_cards(auth_client)
    assert card["tags"] == []
    assert card["review_count"] == 0


def test_archiving_mastered_cards_keeps_their_existing_tags(auth_client, flashcard):
    auth_client.post(f"/flashcards/{flashcard['id']}/tags/visit_later")
    for _ in range(5):
        review(auth_client, flashcard["id"], 5)

    response = auth_client.post("/flashcards/archive/mastered")

    assert response.status_code == 200
    [archived] = response.json()["flashcards"]
    assert archived["tags"] == ["visit_later", "recently_learned"]
    assert user_cards(auth_client)[0]["tags"] == ["visit_later", "recently_learned"]


def test_archiving_ignores_cards_that_are_not_mastered_yet(auth_client, flashcard):
    for _ in range(4):
        review(auth_client, flashcard["id"], 5)

    response = auth_client.post("/flashcards/archive/mastered")

    assert response.json() == {
        "message": "Found 0 mastered flashcards",
        "flashcards": [],
    }
    assert user_cards(auth_client)[0]["tags"] == []


@pytest.fixture
def stored_card(db_session, user) -> Flashcard:
    note = insert_note(db_session, "Cells", "Body", uuid.UUID(user.id))
    return create_flashcard(db_session, "Q?", "A", note.id, note.user_id)


def test_deleting_a_cards_source_chunk_keeps_the_card(db_session, stored_card):
    course = create_course(
        db_session, stored_card.user_id, name="Biology", term=None, exam_date=None
    )
    chunk = DocumentChunk(
        index=0,
        heading_path=["Cells"],
        page_start=1,
        page_end=1,
        text="Cells",
        token_estimate=1,
    )
    document = Document(
        user_id=stored_card.user_id,
        course_id=course.id,
        filename="week1.pdf",
        content_type="application/pdf",
        size_bytes=1,
        storage_path="week1.pdf",
        chunks=[chunk],
    )
    db_session.add(document)
    db_session.flush()
    stored_card.chunk_id = chunk.id
    db_session.commit()

    db_session.delete(document)
    db_session.commit()

    db_session.expire_all()
    assert db_session.get(Flashcard, stored_card.id).chunk_id is None


@pytest.mark.parametrize(
    ("column", "value"), [("kind", "essay"), ("source", "imported")]
)
def test_flashcard_kind_and_source_are_constrained(
    db_session, stored_card, column, value
):
    setattr(stored_card, column, value)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
