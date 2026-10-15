import uuid
from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app import main
from app.config import settings
from app.models import Concept, ConceptEdge, Document, Flashcard, FlashcardSRS
from app.services.concepts import extraction
from app.services.concepts.extraction import PURPOSE
from app.services.embedding_service import FakeEmbedder
from app.services.llm import LLMUnavailableError
from app.services.llm.fake_client import FakeLLMClient
from tests.fixtures.pdfs import image_only_document, prose_document

MISSING_ID = "00000000-0000-0000-0000-000000000000"
PARAGRAPH = (
    "The lecture defines the idea precisely, contrasts it with the previous section,"
    " and works through an example that students should be able to reproduce on the exam."
)
CONCEPT_FIELDS = {
    "id",
    "name",
    "description",
    "order",
    "mastery",
    "question_count",
    "sources",
}


def lecture_pdf(*sections: str) -> bytes:
    body = "".join(
        f"<h2>{section}</h2><p>{section}. {PARAGRAPH}</p>" for section in sections
    )
    return prose_document(f"<h1>Cell biology</h1>{body}")


def concepts(*names: str) -> dict:
    return {
        "concepts": [
            {"name": name, "description": f"{name}, as taught."} for name in names
        ]
    }


def by_section(replies: dict[str, dict]) -> Callable:
    def reply(request):
        prompt = request.messages[0]["content"]
        for section, answer in replies.items():
            if f"<section>Cell biology > {section}</section>" in prompt:
                return answer
        return concepts()

    return reply


@pytest.fixture(autouse=True)
def storage_root(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "document_storage_dir", tmp_path)


@pytest.fixture
def scripted(monkeypatch) -> Callable[..., FakeLLMClient]:
    def script(reply) -> FakeLLMClient:
        fake = FakeLLMClient({PURPOSE: reply})
        monkeypatch.setattr(extraction, "get_llm_client", lambda: fake)
        return fake

    return script


@pytest.fixture
def course(auth_client, create_course) -> dict:
    return create_course(auth_client, "Cell biology")


def upload(client, course: dict, data: bytes) -> dict:
    response = client.post(
        "/documents",
        data={"course_id": course["id"]},
        files={"file": ("lecture.pdf", data, "application/pdf")},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def extracted(auth_client, course, scripted) -> list[dict]:
    """Membranes and Transport share the membrane; Nucleus stands apart."""
    upload(auth_client, course, lecture_pdf("Membranes", "Transport", "Nucleus"))
    scripted(
        by_section(
            {
                "Membranes": concepts("Cell membrane", "Phospholipid bilayer"),
                "Transport": concepts("Osmosis", "cell membrane"),
                "Nucleus": concepts("Nucleus"),
            }
        )
    )
    response = auth_client.post(f"/courses/{course['id']}/concepts/extract")
    assert response.status_code == 200, response.text
    return response.json()


def by_name(concepts: list[dict]) -> dict[str, dict]:
    return {concept["name"]: concept for concept in concepts}


def test_extraction_lists_concepts_in_order_with_their_sources(
    auth_client, course, extracted
):
    [document] = auth_client.get("/documents").json()
    membranes, transport, nucleus = auth_client.get(
        f"/documents/{document['id']}/chunks"
    ).json()

    assert [concept["name"] for concept in extracted] == [
        "Cell membrane",
        "Phospholipid bilayer",
        "Osmosis",
        "Nucleus",
    ]
    assert [concept["order"] for concept in extracted] == [0, 1, 2, 3]
    assert all(set(concept) == CONCEPT_FIELDS for concept in extracted)
    membrane = extracted[0]
    assert membrane["description"] == "Cell membrane, as taught."
    assert (membrane["mastery"], membrane["question_count"]) == (None, 0)
    assert membrane["sources"] == [
        {
            "document_id": document["id"],
            "chunk_id": chunk["id"],
            "page_start": chunk["page_start"],
            "page_end": chunk["page_end"],
        }
        for chunk in (membranes, transport)
    ]
    assert [source["chunk_id"] for source in extracted[3]["sources"]] == [nucleus["id"]]
    assert auth_client.get(f"/courses/{course['id']}/concepts").json() == extracted


def test_the_map_draws_nodes_and_the_reduced_prerequisite_chain(
    auth_client, course, extracted
):
    response = auth_client.get(f"/courses/{course['id']}/map")

    assert response.status_code == 200
    graph = response.json()
    assert graph["nodes"] == [
        {
            "id": concept["id"],
            "name": concept["name"],
            "mastery": None,
            "question_count": 0,
            "order": concept["order"],
        }
        for concept in extracted
    ]
    ids = by_name(extracted)
    membrane, bilayer, osmosis, nucleus = (
        ids[name]["id"]
        for name in ("Cell membrane", "Phospholipid bilayer", "Osmosis", "Nucleus")
    )
    assert graph["edges"] == [
        {"source": membrane, "target": bilayer, "kind": "prerequisite", "weight": 1.0},
        {
            "source": bilayer,
            "target": osmosis,
            "kind": "prerequisite",
            "weight": 0.3333,
        },
        {
            "source": osmosis,
            "target": nucleus,
            "kind": "prerequisite",
            "weight": 0.3333,
        },
    ]


def test_extracting_again_makes_no_model_calls(
    auth_client, course, extracted, scripted
):
    fake = scripted(concepts("Something new"))

    response = auth_client.post(f"/courses/{course['id']}/concepts/extract")

    assert response.status_code == 200
    assert response.json() == extracted
    assert fake.requests == []


def test_a_new_document_adds_its_concepts_after_the_existing_ones(
    auth_client, course, extracted, scripted
):
    upload(auth_client, course, lecture_pdf("Mitochondria"))
    scripted(by_section({"Mitochondria": concepts("Mitochondrion", "Osmosis")}))

    response = auth_client.post(f"/courses/{course['id']}/concepts/extract")

    concepts_after = response.json()
    assert [concept["name"] for concept in concepts_after][-1] == "Mitochondrion"
    assert len(by_name(concepts_after)["Osmosis"]["sources"]) == 2


@pytest.mark.parametrize(
    "documents",
    [[], [image_only_document()]],
    ids=["no-documents", "only-a-failed-document"],
)
def test_extracting_without_ready_documents_is_a_conflict(
    auth_client, course, documents
):
    for data in documents:
        assert upload(auth_client, course, data)["status"] == "failed"

    response = auth_client.post(f"/courses/{course['id']}/concepts/extract")

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "The course has no ready documents to extract concepts from."
    )


def test_an_unavailable_model_is_a_503(auth_client, course, scripted):
    upload(auth_client, course, lecture_pdf("Membranes"))

    def unavailable(request):
        raise LLMUnavailableError("overloaded")

    scripted(unavailable)

    response = auth_client.post(f"/courses/{course['id']}/concepts/extract")

    assert response.status_code == 503
    assert auth_client.get(f"/courses/{course['id']}/concepts").json() == []


def test_the_default_fake_provider_extracts_its_minimal_reply(auth_client, course):
    upload(auth_client, course, lecture_pdf("Membranes", "Nucleus"))

    response = auth_client.post(f"/courses/{course['id']}/concepts/extract")

    assert response.status_code == 200
    [concept] = response.json()
    assert (concept["name"], len(concept["sources"])) == ("x", 2)


def test_a_course_without_concepts_has_an_empty_list_and_map(auth_client, course):
    assert auth_client.get(f"/courses/{course['id']}/concepts").json() == []
    assert auth_client.get(f"/courses/{course['id']}/map").json() == {
        "nodes": [],
        "edges": [],
    }


@pytest.mark.parametrize(
    ("method", "suffix"),
    [
        ("GET", "/concepts"),
        ("POST", "/concepts/extract"),
        ("GET", "/map"),
        ("PATCH", "/concepts/{concept_id}"),
        ("DELETE", "/concepts/{concept_id}"),
    ],
)
def test_another_users_course_is_not_found(
    auth_client, other_auth_client, course, extracted, method, suffix
):
    path = f"/courses/{course['id']}" + suffix.format(concept_id=extracted[0]["id"])

    response = other_auth_client.request(method, path, json={"name": "Mine"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Course not found"
    assert auth_client.get(f"/courses/{course['id']}/concepts").json() == extracted


@pytest.mark.parametrize("method", ["PATCH", "DELETE"])
def test_a_concept_of_another_course_is_not_found(
    auth_client, create_course, extracted, method
):
    other_course = create_course(auth_client, "Genetics")

    response = auth_client.request(
        method,
        f"/courses/{other_course['id']}/concepts/{extracted[0]['id']}",
        json={"name": "Moved"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Concept not found"


def test_unknown_ids_are_not_found(auth_client, course):
    assert auth_client.get(f"/courses/{MISSING_ID}/concepts").status_code == 404
    response = auth_client.delete(f"/courses/{course['id']}/concepts/{MISSING_ID}")
    assert response.status_code == 404


class TestMastery:
    @pytest.fixture
    def add_question(self, db_session, auth_client, user, course, create_note):
        note = create_note(auth_client, course_id=course["id"])

        def add(concept: dict, srs: tuple[int, int] | None, *, reviews: int = 1):
            flashcard = Flashcard(
                question="Q?",
                answer="A.",
                note_id=uuid.UUID(note["id"]),
                user_id=uuid.UUID(user.id),
                course_id=uuid.UUID(course["id"]),
                concept_id=uuid.UUID(concept["id"]),
                review_count=reviews,
            )
            db_session.add(flashcard)
            db_session.flush()
            if srs is not None:
                repetitions, efactor = srs
                db_session.add(
                    FlashcardSRS(
                        flashcard_id=flashcard.id,
                        user_id=flashcard.user_id,
                        repetitions=repetitions,
                        efactor=efactor,
                        due_date=datetime.now(UTC).date(),
                    )
                )
            db_session.commit()
            return flashcard

        return add

    def test_mastery_averages_the_sm2_state_of_the_concepts_questions(
        self, auth_client, course, extracted, add_question
    ):
        membrane, bilayer, *_ = extracted
        add_question(membrane, (4, 250))
        add_question(membrane, (2, 190))
        add_question(membrane, None, reviews=0)
        add_question(bilayer, (0, 250), reviews=0)

        listed = by_name(auth_client.get(f"/courses/{course['id']}/concepts").json())
        nodes = {
            node["name"]: node
            for node in auth_client.get(f"/courses/{course['id']}/map").json()["nodes"]
        }

        expected = (1.0 + 0.375 + 0) / 3
        assert listed["Cell membrane"]["mastery"] == pytest.approx(expected)
        assert listed["Cell membrane"]["question_count"] == 3
        assert listed["Phospholipid bilayer"]["mastery"] == 0
        assert listed["Osmosis"]["mastery"] is None
        assert nodes["Cell membrane"]["mastery"] == pytest.approx(expected)
        assert nodes["Cell membrane"]["question_count"] == 3


class TestEditing:
    def test_renaming_returns_the_concept_and_re_embeds_its_name(
        self, auth_client, db_session, course, extracted
    ):
        osmosis = by_name(extracted)["Osmosis"]

        response = auth_client.patch(
            f"/courses/{course['id']}/concepts/{osmosis['id']}",
            json={"name": "  Osmotic   pressure ", "description": "Water moves."},
        )

        assert response.status_code == 200, response.text
        assert response.json() == {
            **osmosis,
            "name": "Osmotic pressure",
            "description": "Water moves.",
        }
        stored = db_session.get(Concept, uuid.UUID(osmosis["id"]))
        db_session.refresh(stored)
        assert list(stored.embedding) == pytest.approx(
            FakeEmbedder().embed(["Osmotic pressure"])[0]
        )

    def test_renaming_rebuilds_related_edges(
        self, auth_client, course, extracted, monkeypatch
    ):
        monkeypatch.setattr(settings, "concept_related_threshold", 0.6)
        nucleus = by_name(extracted)["Nucleus"]

        auth_client.patch(
            f"/courses/{course['id']}/concepts/{nucleus['id']}",
            json={"name": "Phospholipid bilayer structure"},
        )

        edges = auth_client.get(f"/courses/{course['id']}/map").json()["edges"]
        bilayer = by_name(extracted)["Phospholipid bilayer"]["id"]
        assert {
            "source": bilayer,
            "target": nucleus["id"],
            "kind": "related",
            "weight": pytest.approx(0.8165, abs=1e-4),
        } in edges

    def test_a_description_alone_can_be_edited(self, auth_client, course, extracted):
        concept = extracted[1]

        response = auth_client.patch(
            f"/courses/{course['id']}/concepts/{concept['id']}",
            json={"description": "Two layers of lipids."},
        )

        assert response.json() == {**concept, "description": "Two layers of lipids."}

    def test_changing_only_the_case_of_its_own_name_is_allowed(
        self, auth_client, course, extracted
    ):
        concept = extracted[0]

        response = auth_client.patch(
            f"/courses/{course['id']}/concepts/{concept['id']}",
            json={"name": "cell membrane"},
        )

        assert response.status_code == 200
        assert response.json()["name"] == "cell membrane"

    def test_a_name_another_concept_has_in_any_case_is_a_conflict(
        self, auth_client, course, extracted
    ):
        response = auth_client.patch(
            f"/courses/{course['id']}/concepts/{extracted[2]['id']}",
            json={"name": "NUCLEUS", "description": "Not saved."},
        )

        assert response.status_code == 409
        assert response.json()["detail"] == (
            "Another concept in this course already has that name."
        )
        assert auth_client.get(f"/courses/{course['id']}/concepts").json() == extracted

    @pytest.mark.parametrize(
        "payload",
        [
            {"name": ""},
            {"name": "   "},
            {"name": None},
            {"name": "x" * 121},
            {"description": None},
        ],
        ids=["empty", "blank", "null-name", "too-long", "null-description"],
    )
    def test_invalid_edits_are_rejected(self, auth_client, course, extracted, payload):
        response = auth_client.patch(
            f"/courses/{course['id']}/concepts/{extracted[0]['id']}", json=payload
        )

        assert response.status_code == 422

    def test_deleting_a_concept_keeps_its_questions_and_removes_its_edges(
        self, auth_client, db_session, user, course, extracted, create_note
    ):
        membrane = extracted[0]
        note = create_note(auth_client, course_id=course["id"])
        question = Flashcard(
            question="Q?",
            answer="A.",
            note_id=uuid.UUID(note["id"]),
            user_id=uuid.UUID(user.id),
            concept_id=uuid.UUID(membrane["id"]),
        )
        db_session.add(question)
        db_session.commit()
        path = f"/courses/{course['id']}/concepts/{membrane['id']}"

        response = auth_client.delete(path)

        assert response.status_code == 204
        remaining = auth_client.get(f"/courses/{course['id']}/concepts").json()
        assert [concept["name"] for concept in remaining] == [
            "Phospholipid bilayer",
            "Osmosis",
            "Nucleus",
        ]
        edges = auth_client.get(f"/courses/{course['id']}/map").json()["edges"]
        assert all(membrane["id"] not in (e["source"], e["target"]) for e in edges)
        db_session.expire_all()
        assert db_session.get(Flashcard, question.id).concept_id is None
        assert (
            db_session.scalars(
                select(ConceptEdge).where(
                    ConceptEdge.source_id == uuid.UUID(membrane["id"])
                )
            ).all()
            == []
        )
        assert auth_client.delete(path).status_code == 404


def test_deleting_a_document_prunes_concepts_left_without_sources_or_questions(
    auth_client, db_session, user, course, scripted, create_note
):
    week1 = upload(auth_client, course, lecture_pdf("Membranes", "Transport"))
    upload(auth_client, course, lecture_pdf("Genome"))
    db_session.get(Document, uuid.UUID(week1["id"])).created_at = datetime(
        2026, 9, 1, tzinfo=UTC
    )
    db_session.commit()
    scripted(
        by_section(
            {
                "Membranes": concepts("Cell membrane", "Nucleus"),
                "Transport": concepts("Osmosis"),
                "Genome": concepts("Nucleus", "Chromosome"),
            }
        )
    )
    ids = {
        concept["name"]: concept["id"]
        for concept in auth_client.post(
            f"/courses/{course['id']}/concepts/extract"
        ).json()
    }
    note = create_note(auth_client, course_id=course["id"])
    db_session.add(
        Flashcard(
            question="Q?",
            answer="A.",
            note_id=uuid.UUID(note["id"]),
            user_id=uuid.UUID(user.id),
            concept_id=uuid.UUID(ids["Osmosis"]),
        )
    )
    db_session.commit()

    def edges() -> set[tuple[str, str]]:
        names = {concept_id: name for name, concept_id in ids.items()}
        graph = auth_client.get(f"/courses/{course['id']}/map").json()
        return {(names[e["source"]], names[e["target"]]) for e in graph["edges"]}

    assert edges() == {
        ("Cell membrane", "Nucleus"),
        ("Nucleus", "Osmosis"),
        ("Nucleus", "Chromosome"),
    }

    response = auth_client.delete(f"/documents/{week1['id']}")

    assert response.status_code == 204
    remaining = by_name(auth_client.get(f"/courses/{course['id']}/concepts").json())
    assert list(remaining) == ["Nucleus", "Osmosis", "Chromosome"]
    assert remaining["Osmosis"]["sources"] == []
    assert remaining["Osmosis"]["question_count"] == 1
    assert {source["document_id"] for source in remaining["Nucleus"]["sources"]} == {
        remaining["Chromosome"]["sources"][0]["document_id"]
    }
    assert edges() == {("Nucleus", "Chromosome")}


def test_the_openapi_document_publishes_the_contract_the_map_screen_uses():
    spec = main.app.openapi()
    schemas = spec["components"]["schemas"]

    assert {"get", "post"} & set(spec["paths"]["/courses/{course_id}/concepts"]) == {
        "get"
    }
    assert "post" in spec["paths"]["/courses/{course_id}/concepts/extract"]
    assert "get" in spec["paths"]["/courses/{course_id}/map"]
    assert {"patch", "delete"} <= set(
        spec["paths"]["/courses/{course_id}/concepts/{concept_id}"]
    )
    assert set(schemas["ConceptResponse"]["required"]) == CONCEPT_FIELDS
    assert set(schemas["ConceptSourceResponse"]["required"]) == {
        "document_id",
        "chunk_id",
        "page_start",
        "page_end",
    }
    assert set(schemas["ConceptMapResponse"]["required"]) == {"nodes", "edges"}
    assert set(schemas["ConceptMapNode"]["required"]) == {
        "id",
        "name",
        "mastery",
        "question_count",
        "order",
    }
    assert set(schemas["ConceptMapEdge"]["required"]) == {
        "source",
        "target",
        "kind",
        "weight",
    }
    assert schemas["ConceptEdgeKind"]["enum"] == ["prerequisite", "related"]
