import pytest

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


def enhanced_review(client, card_id: str, typed_answer: str, quality=None):
    payload = {"flashcard_id": card_id, "typed_answer": typed_answer}
    if quality is not None:
        payload["quality_rating"] = quality
    return client.post(f"/flashcards/{card_id}/review/enhanced", json=payload)


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
    assert all(c["flashcard_type"] == "single_note" for c in cards)
    assert all(c["review_count"] == 0 and c["mastery_level"] == 0 for c in cards)
    assert fake_ai.calls == [
        (
            "generate_flashcards_from_content",
            {"content": note["content"], "count": 3},
        )
    ]


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


def test_due_flashcards_include_never_reviewed_cards(auth_client, flashcard):
    response = auth_client.get("/flashcards/due")

    assert [c["id"] for c in response.json()] == [flashcard["id"]]


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


def test_enhanced_generate_single_mode_creates_a_set_and_due_srs_entries(
    auth_client, note
):
    response = auth_client.post(
        "/flashcards/generate",
        json={"mode": "single", "note_id": note["id"], "count": 2},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["cards"]) == 2
    assert body["context_notes"] == [note["id"]]
    [flashcard_set] = auth_client.get("/flashcards/sets").json()
    assert flashcard_set["id"] == body["flashcard_set_id"]
    assert flashcard_set["mode"] == "single"
    assert flashcard_set["seed_note_id"] == note["id"]
    assert flashcard_set["flashcard_count"] == 2
    due_ids = {c["id"] for c in auth_client.get("/flashcards/due/srs").json()}
    assert due_ids == {c["id"] for c in body["cards"]}


def test_enhanced_generate_context_mode_only_searches_the_seed_note(
    auth_client, note, create_note, fake_ai
):
    create_note(auth_client, "Cell biology", "Mitochondria produce energy.")

    response = auth_client.post(
        "/flashcards/generate",
        json={"mode": "context", "note_id": note["id"], "count": 2},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["context_notes"] == []
    assert all(c["flashcard_type"] == "contextual" for c in body["cards"])
    assert all(c["tags"] == ["contextual"] for c in body["cards"])
    [(_, similarity_args)] = [
        call for call in fake_ai.calls if call[0] == "calculate_note_similarities"
    ]
    # Suspected bug: only the seed note is passed to the similarity search, so no neighbors are ever found.
    assert [str(n["id"]) for n in similarity_args["notes"]] == [note["id"]]


def test_enhanced_generate_with_unknown_mode_returns_500(auth_client, note):
    response = auth_client.post(
        "/flashcards/generate", json={"mode": "bogus", "note_id": note["id"]}
    )

    # Suspected bug: the 400 for an unknown mode is caught by the generic handler and becomes a 500.
    assert response.status_code == 500
    assert response.json()["detail"].startswith("Failed to generate flashcards")


def test_enhanced_generate_for_unknown_note_returns_404(auth_client):
    response = auth_client.post(
        "/flashcards/generate", json={"mode": "single", "note_id": MISSING_ID}
    )

    assert response.status_code == 404


def test_review_returns_500_but_still_records_progress(auth_client, flashcard):
    response = auth_client.post(
        f"/flashcards/{flashcard['id']}/review",
        json={
            "flashcard_id": flashcard["id"],
            "user_answer": "Answer 1",
            "performance_score": 90,
        },
    )

    # Suspected bug: the handler reads quality_rating, which FlashcardReview does not define.
    assert response.status_code == 500
    assert "quality_rating" in response.json()["detail"]
    [card] = user_cards(auth_client)
    assert card["review_count"] == 1
    assert card["mastery_level"] == 20
    assert card["last_performance"] == 90
    assert card["last_reviewed"] is not None


def test_review_of_unknown_flashcard_returns_404(auth_client):
    response = auth_client.post(
        f"/flashcards/{MISSING_ID}/review",
        json={"flashcard_id": MISSING_ID, "user_answer": "x", "performance_score": 90},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Flashcard not found"}


def test_enhanced_review_with_manual_rating_schedules_the_card(auth_client, flashcard):
    response = enhanced_review(auth_client, flashcard["id"], "anything", quality=5)

    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "correct"
    assert body["ai_score"] == 100
    assert body["srs_data"]["repetitions"] == 1
    assert body["srs_data"]["interval_days"] == 1
    assert body["srs_data"]["efactor"] == 2.6
    assert body["next_review_date"] == body["srs_data"]["due_date"]
    [card] = user_cards(auth_client)
    assert card["review_count"] == 1
    assert card["mastery_level"] == 20
    assert card["last_performance"] == 100


def test_second_successful_enhanced_review_moves_the_card_six_days_out(
    auth_client, flashcard
):
    enhanced_review(auth_client, flashcard["id"], "anything", quality=5)

    body = enhanced_review(auth_client, flashcard["id"], "anything", quality=5).json()

    assert body["srs_data"]["repetitions"] == 2
    assert body["srs_data"]["interval_days"] == 6
    assert body["srs_data"]["efactor"] == 2.7


def test_enhanced_review_scores_an_exact_answer_as_perfect(auth_client, flashcard):
    body = enhanced_review(auth_client, flashcard["id"], "  answer 1 ").json()

    assert body["verdict"] == "correct"
    assert body["ai_score"] == 100
    assert body["srs_data"]["repetitions"] == 1


def test_enhanced_review_scores_an_unrelated_answer_as_a_failure(
    auth_client, flashcard
):
    body = enhanced_review(auth_client, flashcard["id"], "banana").json()

    assert body["verdict"] == "incorrect"
    assert body["ai_score"] == 20
    assert body["srs_data"]["repetitions"] == 0
    assert body["srs_data"]["interval_days"] == 1
    assert body["srs_data"]["efactor"] == 2.5


def test_enhanced_review_of_unknown_flashcard_returns_404(auth_client):
    assert enhanced_review(auth_client, MISSING_ID, "x", quality=5).status_code == 404


def test_first_tag_on_a_flashcard_is_stored(auth_client, flashcard):
    response = auth_client.post(f"/flashcards/{flashcard['id']}/tags/visit_later")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Tag 'visit_later' added successfully",
        "tags": ["visit_later"],
    }
    assert user_cards(auth_client)[0]["tags"] == ["visit_later"]


def test_second_tag_on_a_flashcard_is_reported_but_not_stored(auth_client, flashcard):
    auth_client.post(f"/flashcards/{flashcard['id']}/tags/visit_later")

    response = auth_client.post(f"/flashcards/{flashcard['id']}/tags/revisited")

    # Suspected bug: tags.append mutates the ARRAY in place, so SQLAlchemy never flushes it.
    assert response.status_code == 200
    assert response.json()["tags"] == ["visit_later"]
    assert user_cards(auth_client)[0]["tags"] == ["visit_later"]


def test_removing_a_flashcard_tag_is_reported_but_not_stored(auth_client, flashcard):
    auth_client.post(f"/flashcards/{flashcard['id']}/tags/visit_later")

    response = auth_client.delete(f"/flashcards/{flashcard['id']}/tags/visit_later")

    # Suspected bug: tags.remove mutates the ARRAY in place, so SQLAlchemy never flushes it.
    assert response.json()["message"] == "Tag 'visit_later' removed successfully"
    assert user_cards(auth_client)[0]["tags"] == ["visit_later"]


def test_tagging_unknown_flashcard_returns_404(auth_client):
    response = auth_client.post(f"/flashcards/{MISSING_ID}/tags/visit_later")

    assert response.status_code == 404


def test_another_user_can_tag_and_review_someone_elses_flashcard(
    auth_client, other_auth_client, flashcard
):
    tag = other_auth_client.post(f"/flashcards/{flashcard['id']}/tags/bob_was_here")
    review = enhanced_review(other_auth_client, flashcard["id"], "x", quality=5)

    # Suspected bug: flashcard tag and review routes never check ownership.
    assert tag.status_code == 200
    assert review.status_code == 200
    [card] = user_cards(auth_client)
    assert card["tags"] == ["bob_was_here"]
    assert card["review_count"] == 1
