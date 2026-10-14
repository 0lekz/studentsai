import math
import sys
import types
import uuid
from dataclasses import dataclass, field

import numpy as np
import pytest
from pydantic import ValidationError
from sqlalchemy import delete, update

from app.config import Settings, settings
from app.database import create_note, update_note
from app.models import NoteEmbedding
from app.services import embedding_service
from app.services.embedding_service import (
    FakeEmbedder,
    FastEmbedEmbedder,
    backfill_note_embeddings,
    content_hash,
    get_embedder,
    note_text,
)


@dataclass
class RecordingEmbedder:
    model_name: str = FakeEmbedder.model_name
    calls: list[list[str]] = field(default_factory=list)

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return FakeEmbedder().embed(texts)

    @property
    def embedded_texts(self) -> list[str]:
        return [text for call in self.calls for text in call]


class BrokenEmbedder:
    model_name = "broken"

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("model unavailable")


@pytest.fixture
def embedder(monkeypatch) -> RecordingEmbedder:
    recording = RecordingEmbedder()
    monkeypatch.setattr(embedding_service, "get_embedder", lambda: recording)
    return recording


def stored_embedding(db_session, note_id) -> NoteEmbedding | None:
    db_session.expire_all()
    return db_session.get(NoteEmbedding, uuid.UUID(str(note_id)))


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def test_tests_use_the_fake_embedder():
    assert isinstance(get_embedder(), FakeEmbedder)


def test_similarity_backend_defaults_to_tfidf():
    assert Settings.model_fields["similarity_backend"].default == "tfidf"


@pytest.mark.parametrize("field_name", ["similarity_backend", "embedding_backend"])
def test_backend_settings_reject_unknown_values(field_name):
    with pytest.raises(ValidationError):
        Settings(**{field_name: "word2vec"})


class TestFakeEmbedder:
    def test_vectors_are_deterministic_unit_length_and_384_wide(self):
        [first] = FakeEmbedder().embed(["Mitosis has four phases"])
        [again] = FakeEmbedder().embed(["Mitosis has four phases"])

        assert first == again
        assert len(first) == 384
        assert math.isclose(cosine(first, first), 1.0)

    def test_shared_words_make_vectors_closer(self):
        mitosis, division, market = FakeEmbedder().embed(
            [
                "Mitosis splits one cell into two daughter cells",
                "One cell splits into two daughter cells during mitosis",
                "Supply and demand set the market price",
            ]
        )

        assert cosine(mitosis, division) > 0.8
        assert cosine(mitosis, market) < 0.1

    def test_text_without_words_still_gets_a_unit_vector(self):
        [vector] = FakeEmbedder().embed([""])

        assert math.isclose(cosine(vector, vector), 1.0)


class TestFastEmbedEmbedder:
    def test_the_model_is_not_loaded_until_something_is_embedded(self):
        embedder = FastEmbedEmbedder("BAAI/bge-small-en-v1.5", "~/model-cache")

        assert embedder.embed([]) == []
        assert not embedder.is_loaded
        assert not embedder.cache_dir.startswith("~")

    def test_the_model_loads_once_and_is_reused(self, monkeypatch):
        loads = []

        class StubTextEmbedding:
            def __init__(self, model_name: str, cache_dir: str) -> None:
                loads.append((model_name, cache_dir))

            def embed(self, texts):
                return (np.full(3, len(text), dtype=np.float32) for text in texts)

        stub_module = types.ModuleType("fastembed")
        stub_module.TextEmbedding = StubTextEmbedding
        monkeypatch.setitem(sys.modules, "fastembed", stub_module)
        embedder = FastEmbedEmbedder("some/model", "/models")

        assert embedder.embed(["ab"]) == [[2.0, 2.0, 2.0]]
        assert embedder.embed(["abc", "a"]) == [[3.0, 3.0, 3.0], [1.0, 1.0, 1.0]]
        assert loads == [("some/model", "/models")]

    def test_the_fastembed_backend_builds_the_configured_model(self, monkeypatch):
        monkeypatch.setattr(settings, "embedding_backend", "fastembed")

        embedder = get_embedder.__wrapped__()

        assert isinstance(embedder, FastEmbedEmbedder)
        assert embedder.model_name == settings.embedding_model
        assert not embedder.is_loaded


class TestWritePath:
    def test_creating_a_note_stores_its_embedding(
        self, auth_client, create_note, db_session
    ):
        note = create_note(auth_client, "Mitosis", "Chromosomes condense and split.")

        stored = stored_embedding(db_session, note["id"])
        text = note_text("Mitosis", "Chromosomes condense and split.")
        assert stored.model_name == FakeEmbedder.model_name
        assert stored.content_hash == content_hash(text)
        assert stored.embedding == pytest.approx(
            FakeEmbedder().embed([text])[0], abs=1e-6
        )

    @pytest.mark.parametrize(
        "change",
        [{"content": "Cells divide in two."}, {"title": "Cell division"}],
        ids=["content", "title"],
    )
    def test_changing_the_note_text_refreshes_the_embedding(
        self, auth_client, create_note, db_session, embedder, change
    ):
        note = create_note(auth_client, "Mitosis", "Chromosomes condense and split.")

        response = auth_client.put(f"/notes/{note['id']}", json=change)

        assert response.status_code == 200, response.text
        updated = response.json()
        new_text = note_text(updated["title"], updated["content"])
        assert stored_embedding(db_session, note["id"]).content_hash == content_hash(
            new_text
        )
        assert embedder.embedded_texts == [
            note_text("Mitosis", "Chromosomes condense and split."),
            new_text,
        ]

    @pytest.mark.parametrize(
        "change",
        [
            {"summary": "Cells split."},
            {"title": "Mitosis", "content": "Chromosomes condense and split."},
        ],
        ids=["summary-only", "same-text"],
    )
    def test_an_update_that_keeps_the_text_does_not_re_embed(
        self, auth_client, create_note, embedder, change
    ):
        note = create_note(auth_client, "Mitosis", "Chromosomes condense and split.")

        response = auth_client.put(f"/notes/{note['id']}", json=change)

        assert response.status_code == 200, response.text
        assert len(embedder.calls) == 1

    def test_a_model_change_re_embeds_unchanged_text(
        self, auth_client, create_note, db_session, embedder
    ):
        note = create_note(auth_client, "Mitosis", "Chromosomes condense and split.")
        embedder.model_name = "next-model"

        auth_client.put(f"/notes/{note['id']}", json={"summary": "Cells split."})

        assert len(embedder.calls) == 2
        assert stored_embedding(db_session, note["id"]).model_name == "next-model"

    def test_an_embedding_failure_still_saves_the_note(
        self, auth_client, db_session, monkeypatch, caplog
    ):
        monkeypatch.setattr(embedding_service, "get_embedder", BrokenEmbedder)

        response = auth_client.post(
            "/notes", json={"title": "Mitosis", "content": "Cells split."}
        )

        assert response.status_code == 200, response.text
        note_id = response.json()["id"]
        assert auth_client.get(f"/notes/{note_id}").status_code == 200
        assert stored_embedding(db_session, note_id) is None
        assert f"Embedding refresh failed for note {note_id}" in caplog.text

    def test_deleting_a_note_deletes_its_embedding(
        self, auth_client, create_note, db_session
    ):
        note = create_note(auth_client)

        assert auth_client.delete(f"/notes/{note['id']}").status_code == 200

        assert stored_embedding(db_session, note["id"]) is None


class TestBackfill:
    @pytest.fixture
    def make_notes(self, db_session, user):
        def make(count: int) -> list:
            return [
                create_note(db_session, f"Note {n}", f"Body {n}", uuid.UUID(user.id))
                for n in range(count)
            ]

        return make

    def test_embeds_notes_without_embeddings_in_committed_batches(
        self, db_session, make_notes
    ):
        notes = make_notes(5)

        batches = list(backfill_note_embeddings(db_session, FakeEmbedder(), 2))

        assert [(batch.scanned, batch.embedded) for batch in batches] == [
            (2, 2),
            (2, 2),
            (1, 1),
        ]
        for note in notes:
            stored = stored_embedding(db_session, note.id)
            assert stored.content_hash == content_hash(
                note_text(note.title, note.content)
            )

    def test_re_embeds_only_missing_and_stale_notes(self, db_session, make_notes):
        edited, old_model, missing, _up_to_date = make_notes(4)
        list(backfill_note_embeddings(db_session, FakeEmbedder(), 10))
        update_note(db_session, edited, content="Edited body")
        db_session.execute(
            update(NoteEmbedding)
            .where(NoteEmbedding.note_id == old_model.id)
            .values(model_name="retired-model")
        )
        db_session.execute(
            delete(NoteEmbedding).where(NoteEmbedding.note_id == missing.id)
        )
        recording = RecordingEmbedder()

        [batch] = backfill_note_embeddings(db_session, recording, 10)

        assert (batch.scanned, batch.embedded) == (4, 3)
        assert sorted(recording.embedded_texts) == sorted(
            note_text(note.title, note.content) for note in (edited, old_model, missing)
        )
        assert stored_embedding(db_session, old_model.id).model_name == (
            FakeEmbedder.model_name
        )

    def test_a_second_run_embeds_nothing(self, db_session, make_notes):
        make_notes(3)
        list(backfill_note_embeddings(db_session, FakeEmbedder(), 2))
        recording = RecordingEmbedder()

        batches = list(backfill_note_embeddings(db_session, recording, 2))

        assert sum(batch.embedded for batch in batches) == 0
        assert recording.calls == []

    def test_an_interrupted_run_keeps_finished_batches_and_resumes(
        self, db_session, make_notes
    ):
        notes = make_notes(6)
        interrupted = backfill_note_embeddings(db_session, FakeEmbedder(), 2)
        next(interrupted)
        interrupted.close()
        finished = {note.id for note in notes if stored_embedding(db_session, note.id)}
        recording = RecordingEmbedder()

        list(backfill_note_embeddings(db_session, recording, 2))

        assert len(finished) == 2
        assert sorted(recording.embedded_texts) == sorted(
            note_text(note.title, note.content)
            for note in notes
            if note.id not in finished
        )
