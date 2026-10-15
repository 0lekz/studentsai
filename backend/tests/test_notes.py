import uuid

MISSING_NOTE_ID = "00000000-0000-0000-0000-000000000000"


def backlink_ids(client, note_id: str) -> list[str]:
    response = client.get(f"/notes/{note_id}/backlinks")
    assert response.status_code == 200, response.text
    return [backlink["note_id"] for backlink in response.json()]


def link(client, source_id: str, target_id: str):
    return client.post(
        f"/notes/{source_id}/links", params={"target_note_id": target_id}
    )


def test_create_note_returns_the_stored_note(auth_client):
    response = auth_client.post(
        "/notes", json={"title": "  Photosynthesis  ", "content": "  Light to sugar.  "}
    )

    assert response.status_code == 200
    note = response.json()
    uuid.UUID(note["id"])
    assert note["title"] == "Photosynthesis"
    assert note["content"] == "Light to sugar."
    assert note["summary"] is None
    assert note["tags"] == []
    assert note["course_id"] is None


def test_create_note_with_blank_title_returns_422(auth_client):
    response = auth_client.post("/notes", json={"title": "   ", "content": "Body"})

    assert response.status_code == 422


def test_list_notes_returns_the_users_notes_with_paging_fields(
    auth_client, create_note
):
    first = create_note(auth_client, "First", "One")
    second = create_note(auth_client, "Second", "Two")

    response = auth_client.get("/notes")

    assert response.status_code == 200
    body = response.json()
    assert {note["id"] for note in body["notes"]} == {first["id"], second["id"]}
    assert body["total"] == 2
    assert body["page"] == 1
    assert body["per_page"] == 100


def test_list_notes_respects_skip_and_limit(auth_client, create_note):
    for n in range(3):
        create_note(auth_client, f"Note {n}", "Body")

    body = auth_client.get("/notes", params={"skip": 2, "limit": 2}).json()

    assert len(body["notes"]) == 1
    assert body["total"] == 3
    assert body["page"] == 2
    assert body["per_page"] == 2


def test_get_note_returns_the_note(auth_client, create_note):
    note = create_note(auth_client)

    response = auth_client.get(f"/notes/{note['id']}")

    assert response.status_code == 200
    assert response.json()["title"] == note["title"]
    assert response.json()["content"] == note["content"]


def test_get_note_returns_stored_tags(auth_client, create_note):
    note = create_note(auth_client)
    auth_client.put(f"/notes/{note['id']}/tags", json={"tags": ["biology"]})

    response = auth_client.get(f"/notes/{note['id']}")

    assert response.json()["tags"] == ["biology"]


def test_get_unknown_note_returns_404(auth_client):
    response = auth_client.get(f"/notes/{MISSING_NOTE_ID}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Note not found"}


def test_update_note_changes_only_the_given_fields(auth_client, create_note):
    note = create_note(auth_client, "Old title", "Old content")

    response = auth_client.put(
        f"/notes/{note['id']}", json={"title": "New title", "summary": "Short"}
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["title"] == "New title"
    assert updated["content"] == "Old content"
    assert updated["summary"] == "Short"
    assert auth_client.get(f"/notes/{note['id']}").json()["title"] == "New title"


def test_update_unknown_note_returns_404(auth_client):
    response = auth_client.put(f"/notes/{MISSING_NOTE_ID}", json={"title": "x"})

    assert response.status_code == 404


def test_delete_note_removes_it(auth_client, create_note):
    note = create_note(auth_client)

    response = auth_client.delete(f"/notes/{note['id']}")

    assert response.status_code == 200
    assert response.json() == {"message": "Note deleted successfully", "data": None}
    assert auth_client.get(f"/notes/{note['id']}").status_code == 404


def test_delete_note_removes_its_flashcards_and_links(auth_client, create_note):
    note = create_note(auth_client, "Doomed", "Body")
    other = create_note(auth_client, "Survivor", "Body")
    auth_client.post(f"/notes/{note['id']}/flashcards/generate", params={"count": 2})
    link(auth_client, note["id"], other["id"])

    assert auth_client.delete(f"/notes/{note['id']}").status_code == 200

    assert auth_client.get("/flashcards/user").json() == []
    assert backlink_ids(auth_client, other["id"]) == []


def test_delete_note_used_as_flashcard_set_seed_removes_the_set(
    auth_client, create_note
):
    note = create_note(auth_client)
    auth_client.post("/flashcards/generate", json={"note_id": note["id"]})

    response = auth_client.delete(f"/notes/{note['id']}")

    assert response.status_code == 200
    assert auth_client.get(f"/notes/{note['id']}").status_code == 404
    assert auth_client.get("/flashcards/sets").json() == []
    assert auth_client.get("/flashcards/user").json() == []


def test_delete_unknown_note_returns_404(auth_client):
    assert auth_client.delete(f"/notes/{MISSING_NOTE_ID}").status_code == 404


def test_put_tags_replaces_the_note_tags(auth_client, create_note):
    note = create_note(auth_client)
    auth_client.put(f"/notes/{note['id']}/tags", json={"tags": ["a", "b"]})

    response = auth_client.put(f"/notes/{note['id']}/tags", json={"tags": ["c"]})

    assert response.status_code == 200
    assert response.json()["tags"] == ["c"]
    [listed] = auth_client.get("/notes").json()["notes"]
    assert listed["tags"] == ["c"]


def test_summarize_note_stores_the_ai_summary(auth_client, create_note, fake_ai):
    note = create_note(auth_client)

    response = auth_client.post(f"/notes/{note['id']}/summarize")

    assert response.status_code == 200
    assert response.json()["summary"] == fake_ai.summary
    assert auth_client.get(f"/notes/{note['id']}").json()["summary"] == fake_ai.summary


def test_manual_link_shows_source_as_backlink_of_target(auth_client, create_note):
    source = create_note(auth_client, "Source", "Links out")
    target = create_note(auth_client, "Target", "Linked to")

    response = link(auth_client, source["id"], target["id"])

    assert response.status_code == 200
    assert response.json() == {"message": "Link created", "data": None}
    [backlink] = auth_client.get(f"/notes/{target['id']}/backlinks").json()
    assert backlink["note_id"] == source["id"]
    assert backlink["title"] == "Source"
    assert backlink["excerpt"] == "Links out"
    assert backlink_ids(auth_client, source["id"]) == []


def test_backlink_excerpt_truncates_long_content_to_120_characters(
    auth_client, create_note
):
    source = create_note(auth_client, "Source", "x" * 200)
    target = create_note(auth_client, "Target", "Body")
    link(auth_client, source["id"], target["id"])

    [backlink] = auth_client.get(f"/notes/{target['id']}/backlinks").json()

    assert backlink["excerpt"] == "x" * 120 + "..."


def test_delete_manual_link_removes_the_backlink(auth_client, create_note):
    source = create_note(auth_client, "Source", "Body")
    target = create_note(auth_client, "Target", "Body")
    link(auth_client, source["id"], target["id"])

    response = auth_client.delete(f"/notes/{source['id']}/links/{target['id']}")

    assert response.json() == {"message": "Link deleted", "data": None}
    assert backlink_ids(auth_client, target["id"]) == []


def test_link_to_unknown_note_returns_404(auth_client, create_note):
    source = create_note(auth_client)

    assert link(auth_client, source["id"], MISSING_NOTE_ID).status_code == 404


def test_wiki_link_in_updated_content_creates_a_backlink(auth_client, create_note):
    target = create_note(auth_client, "Chlorophyll", "Green pigment")
    source = create_note(auth_client, "Photosynthesis", "Body")

    auth_client.put(
        f"/notes/{source['id']}", json={"content": "Depends on [[Chlorophyll]]."}
    )

    assert backlink_ids(auth_client, target["id"]) == [source["id"]]


def test_updating_a_note_without_wiki_links_drops_its_manual_links(
    auth_client, create_note
):
    source = create_note(auth_client, "Source", "Body")
    target = create_note(auth_client, "Target", "Body")
    link(auth_client, source["id"], target["id"])

    auth_client.put(f"/notes/{source['id']}", json={"title": "Renamed source"})

    # Suspected bug: wiki-link sync deletes every outgoing link, including manual ones.
    assert backlink_ids(auth_client, target["id"]) == []


def test_notes_list_only_contains_the_callers_notes(
    auth_client, other_auth_client, create_note
):
    create_note(auth_client, "Alice note", "Body")
    bob_note = create_note(other_auth_client, "Bob note", "Body")

    bob_notes = other_auth_client.get("/notes").json()["notes"]

    assert [note["id"] for note in bob_notes] == [bob_note["id"]]


def test_other_users_note_is_invisible_and_immutable(
    auth_client, other_auth_client, create_note
):
    note = create_note(auth_client)
    note_url = f"/notes/{note['id']}"

    assert other_auth_client.get(note_url).status_code == 404
    assert (
        other_auth_client.put(note_url, json={"title": "Hijacked"}).status_code == 404
    )
    assert (
        other_auth_client.put(f"{note_url}/tags", json={"tags": ["x"]}).status_code
        == 404
    )
    assert other_auth_client.get(f"{note_url}/backlinks").status_code == 404
    assert other_auth_client.post(f"{note_url}/summarize").status_code == 404
    assert other_auth_client.delete(note_url).status_code == 404
    assert auth_client.get(note_url).json()["title"] == note["title"]


def test_cannot_link_own_note_to_another_users_note(
    auth_client, other_auth_client, create_note
):
    alice_note = create_note(auth_client)
    bob_note = create_note(other_auth_client)

    assert link(other_auth_client, bob_note["id"], alice_note["id"]).status_code == 404
    assert backlink_ids(auth_client, alice_note["id"]) == []


def test_create_note_in_a_course(auth_client, create_course):
    course = create_course(auth_client)

    response = auth_client.post(
        "/notes",
        json={"title": "Mitosis", "content": "Cells split.", "course_id": course["id"]},
    )

    assert response.status_code == 200
    note = response.json()
    assert note["course_id"] == course["id"]
    assert auth_client.get(f"/notes/{note['id']}").json()["course_id"] == course["id"]


def test_create_note_in_another_users_course_returns_404(
    auth_client, other_auth_client, create_course
):
    theirs = create_course(other_auth_client)

    response = auth_client.post(
        "/notes", json={"title": "Sneaky", "content": "Body", "course_id": theirs["id"]}
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Course not found"}
    assert auth_client.get("/notes").json()["notes"] == []


def test_list_notes_filters_by_course_and_counts_only_that_course(
    auth_client, create_course, create_note
):
    biology = create_course(auth_client, "Biology")
    chemistry = create_course(auth_client, "Chemistry")
    cells = create_note(auth_client, "Cells", "Body", course_id=biology["id"])
    create_note(auth_client, "Bonds", "Body", course_id=chemistry["id"])
    create_note(auth_client, "Loose", "Body")

    body = auth_client.get("/notes", params={"course_id": biology["id"]}).json()

    assert [note["id"] for note in body["notes"]] == [cells["id"]]
    assert body["total"] == 1
    assert auth_client.get("/notes").json()["total"] == 3


def test_list_notes_for_another_users_course_returns_404(
    auth_client, other_auth_client, create_course
):
    theirs = create_course(other_auth_client)

    response = auth_client.get("/notes", params={"course_id": theirs["id"]})

    assert response.status_code == 404
