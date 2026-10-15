import uuid

from app.database import create_note as insert_note
from app.database import upsert_note_similarity


def edges(graph: dict) -> set[tuple[str, str, float, str]]:
    return {
        (c["source_id"], c["target_id"], c["similarity"], c["connection_type"])
        for c in graph["connections"]
    }


def get_graph(client, **params) -> dict:
    response = client.get("/graph", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_graph_without_notes_is_empty(auth_client):
    assert get_graph(auth_client) == {"nodes": [], "connections": [], "total_nodes": 0}


def test_graph_with_a_single_note_has_no_connections(auth_client, create_note, fake_ai):
    note = create_note(auth_client, "Solo", "Just one note here")

    graph = get_graph(auth_client)

    [node] = graph["nodes"]
    assert node["id"] == note["id"]
    assert node["title"] == "Solo"
    assert node["content_preview"] == "Just one note here"
    assert node["word_count"] == 4
    assert graph["connections"] == []
    assert graph["total_nodes"] == 1
    assert fake_ai.calls == []


def test_graph_returns_nodes_and_manual_link_edges(auth_client, create_note):
    a = create_note(auth_client, "A", "First note")
    b = create_note(auth_client, "B", "Second note")
    c = create_note(auth_client, "C", "Third note")
    auth_client.post(f"/notes/{a['id']}/links", params={"target_note_id": b["id"]})

    graph = get_graph(auth_client)

    assert {node["id"] for node in graph["nodes"]} == {a["id"], b["id"], c["id"]}
    assert graph["total_nodes"] == 3
    assert edges(graph) == {(a["id"], b["id"], 1.0, "manual")}


def test_graph_includes_wiki_link_edges(auth_client, create_note):
    target = create_note(auth_client, "Target", "Body")
    source = create_note(auth_client, "Source", "Body")
    auth_client.put(f"/notes/{source['id']}", json={"content": "See [[Target]]"})

    assert edges(get_graph(auth_client)) == {
        (source["id"], target["id"], 1.0, "manual")
    }


def test_graph_includes_similarity_edges_from_the_ai_service(
    auth_client, create_note, fake_ai
):
    a = create_note(auth_client, "A", "Cells divide")
    b = create_note(auth_client, "B", "Cells grow")
    fake_ai.similarities = [
        {
            "source_id": uuid.UUID(a["id"]),
            "target_id": uuid.UUID(b["id"]),
            "similarity": 0.75,
            "connection_type": "similarity",
        }
    ]

    graph = get_graph(auth_client)

    assert edges(graph) == {(a["id"], b["id"], 0.75, "similarity")}
    [(_, similarity_args)] = fake_ai.calls
    assert {str(n["id"]) for n in similarity_args["notes"]} == {a["id"], b["id"]}


def test_graph_includes_stored_similarities_scaled_from_thousandths(
    auth_client, create_note, db_session
):
    a = create_note(auth_client, "A", "Body")
    b = create_note(auth_client, "B", "Body")
    upsert_note_similarity(db_session, uuid.UUID(a["id"]), uuid.UUID(b["id"]), 0.42)
    low, high = sorted([a["id"], b["id"]])

    assert edges(get_graph(auth_client)) == {(low, high, 0.42, "similarity")}


def test_graph_truncates_content_preview_to_200_characters(auth_client, create_note):
    create_note(auth_client, "Long", "y" * 250)
    create_note(auth_client, "Short", "Body")

    previews = {
        n["title"]: n["content_preview"] for n in get_graph(auth_client)["nodes"]
    }

    assert previews == {"Long": "y" * 200 + "...", "Short": "Body"}


def test_graph_only_contains_the_callers_notes_and_links(
    auth_client, other_auth_client, create_note
):
    mine = [create_note(auth_client, f"Mine {n}", "Body") for n in range(2)]
    theirs = [create_note(other_auth_client, f"Theirs {n}", "Body") for n in range(2)]
    other_auth_client.post(
        f"/notes/{theirs[0]['id']}/links", params={"target_note_id": theirs[1]["id"]}
    )

    graph = get_graph(auth_client)

    assert {node["id"] for node in graph["nodes"]} == {note["id"] for note in mine}
    assert graph["connections"] == []


def test_graph_includes_every_note_not_only_the_first_hundred(
    auth_client, user, db_session
):
    for n in range(101):
        insert_note(db_session, f"Note {n}", "Body", uuid.UUID(user.id))

    graph = get_graph(auth_client)

    assert graph["total_nodes"] == 101
    assert len(graph["nodes"]) == 101


def test_graph_for_a_course_only_draws_that_courses_notes_and_edges(
    auth_client, create_course, create_note, db_session, fake_ai
):
    biology = create_course(auth_client, "Biology")
    cells = create_note(auth_client, "Cells", "Body", course_id=biology["id"])
    mitosis = create_note(auth_client, "Mitosis", "Body", course_id=biology["id"])
    loose = create_note(auth_client, "Loose", "Body")
    for source, target in ((cells, mitosis), (cells, loose)):
        auth_client.post(
            f"/notes/{source['id']}/links", params={"target_note_id": target["id"]}
        )
    upsert_note_similarity(
        db_session, uuid.UUID(mitosis["id"]), uuid.UUID(loose["id"]), 0.9
    )

    graph = get_graph(auth_client, course_id=biology["id"])

    assert {node["id"] for node in graph["nodes"]} == {cells["id"], mitosis["id"]}
    assert graph["total_nodes"] == 2
    assert edges(graph) == {(cells["id"], mitosis["id"], 1.0, "manual")}
    [(_, similarity_args)] = fake_ai.calls
    assert {str(n["id"]) for n in similarity_args["notes"]} == {
        cells["id"],
        mitosis["id"],
    }


def test_graph_for_another_users_course_returns_404(
    auth_client, other_auth_client, create_course
):
    theirs = create_course(other_auth_client)

    response = auth_client.get("/graph", params={"course_id": theirs["id"]})

    assert response.status_code == 404
    assert response.json() == {"detail": "Course not found"}
