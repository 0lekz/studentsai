import uuid

import pytest
from sqlalchemy import delete, update

from app.config import settings
from app.models import NoteEmbedding

MITOSIS = ("Mitosis", "Mitosis splits one cell into two identical daughter cells.")
CELL_DIVISION = (
    "Cell division",
    "In mitosis one cell splits into two identical daughter cells.",
)
MARKETS = (
    "Market equilibrium",
    "Supply and demand curves meet at the equilibrium price.",
)


@pytest.fixture
def embeddings_backend(monkeypatch) -> None:
    monkeypatch.setattr(settings, "similarity_backend", "embeddings")
    monkeypatch.setattr(settings, "embedding_similarity_threshold", 0.5)


def get_graph(client) -> dict:
    response = client.get("/graph")
    assert response.status_code == 200, response.text
    return response.json()


def edges(graph: dict) -> set[tuple[str, str, str]]:
    return {
        (c["source_id"], c["target_id"], c["connection_type"])
        for c in graph["connections"]
    }


def ordered(a: dict, b: dict) -> tuple[str, str]:
    low, high = sorted([a["id"], b["id"]])
    return low, high


@pytest.mark.usefixtures("embeddings_backend")
class TestGraphWithEmbeddings:
    def test_similar_notes_connect_and_unrelated_notes_do_not(
        self, auth_client, create_note, fake_ai
    ):
        mitosis = create_note(auth_client, *MITOSIS)
        division = create_note(auth_client, *CELL_DIVISION)
        markets = create_note(auth_client, *MARKETS)

        graph = get_graph(auth_client)

        assert {node["id"] for node in graph["nodes"]} == {
            mitosis["id"],
            division["id"],
            markets["id"],
        }
        [connection] = graph["connections"]
        assert connection.keys() == {
            "source_id",
            "target_id",
            "similarity",
            "connection_type",
        }
        assert (connection["source_id"], connection["target_id"]) == ordered(
            mitosis, division
        )
        assert connection["connection_type"] == "similarity"
        assert 0.5 < connection["similarity"] <= 1.0
        assert fake_ai.calls == []

    def test_the_threshold_decides_which_pairs_connect(
        self, auth_client, create_note, monkeypatch
    ):
        create_note(auth_client, *MITOSIS)
        create_note(auth_client, *CELL_DIVISION)
        monkeypatch.setattr(settings, "embedding_similarity_threshold", 0.99)

        assert get_graph(auth_client)["connections"] == []

    def test_connections_are_ordered_by_similarity(self, auth_client, create_note):
        create_note(auth_client, *MITOSIS)
        create_note(auth_client, *CELL_DIVISION)
        create_note(auth_client, "Mitosis again", MITOSIS[1])

        similarities = [c["similarity"] for c in get_graph(auth_client)["connections"]]

        assert len(similarities) == 3
        assert similarities == sorted(similarities, reverse=True)

    @pytest.mark.parametrize(
        "make_stale",
        [
            lambda note_id: delete(NoteEmbedding).where(
                NoteEmbedding.note_id == note_id
            ),
            lambda note_id: (
                update(NoteEmbedding)
                .where(NoteEmbedding.note_id == note_id)
                .values(model_name="retired-model")
            ),
        ],
        ids=["missing", "other-model"],
    )
    def test_notes_without_a_current_embedding_have_no_similarity_edges(
        self, auth_client, create_note, db_session, make_stale
    ):
        mitosis = create_note(auth_client, *MITOSIS)
        division = create_note(auth_client, *CELL_DIVISION)
        db_session.execute(make_stale(uuid.UUID(division["id"])))

        graph = get_graph(auth_client)

        assert {node["id"] for node in graph["nodes"]} == {
            mitosis["id"],
            division["id"],
        }
        assert graph["connections"] == []

    def test_only_the_callers_notes_connect(
        self, auth_client, other_auth_client, create_note
    ):
        create_note(auth_client, *MITOSIS)
        create_note(auth_client, *MARKETS)
        create_note(other_auth_client, *CELL_DIVISION)
        create_note(other_auth_client, *MARKETS)

        assert get_graph(auth_client)["connections"] == []

    def test_manual_links_are_still_merged(self, auth_client, create_note):
        mitosis = create_note(auth_client, *MITOSIS)
        markets = create_note(auth_client, *MARKETS)
        auth_client.post(
            f"/notes/{mitosis['id']}/links", params={"target_note_id": markets["id"]}
        )

        assert edges(get_graph(auth_client)) == {
            (mitosis["id"], markets["id"], "manual")
        }


def test_the_default_backend_still_uses_tfidf(auth_client, create_note, fake_ai):
    create_note(auth_client, *MITOSIS)
    create_note(auth_client, *CELL_DIVISION)

    get_graph(auth_client)

    assert [name for name, _ in fake_ai.calls] == ["calculate_note_similarities"]
