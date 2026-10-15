import uuid

import pytest
from sqlalchemy import func, select

from app.config import settings
from app.database import FlashcardSRS, NoteLink
from app.models import Course, DocumentChunk, NoteEmbedding
from tests.fixtures.pdfs import Slide, slide_deck

MISSING_ID = "00000000-0000-0000-0000-000000000000"
COURSE_FIELDS = {
    "id",
    "name",
    "term",
    "exam_date",
    "archived",
    "created_at",
    "updated_at",
}
COUNT_FIELDS = {"documents_count", "notes_count", "flashcards_count"}


@pytest.fixture
def storage_root(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "document_storage_dir", tmp_path)
    return tmp_path


def list_courses(client) -> list[dict]:
    response = client.get("/courses")
    assert response.status_code == 200, response.text
    return response.json()


def upload(client, course: dict) -> dict:
    response = client.post(
        "/documents",
        data={"course_id": course["id"]},
        files={"file": ("week1.pdf", slide_deck([Slide("Cells")]), "application/pdf")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def count(db_session, model, *conditions) -> int:
    return db_session.scalar(select(func.count()).select_from(model).where(*conditions))


def test_create_course_returns_the_stored_course(auth_client):
    response = auth_client.post(
        "/courses",
        json={
            "name": "  Biology 101  ",
            "term": "Fall 2026",
            "exam_date": "2026-12-14",
        },
    )

    assert response.status_code == 201
    course = response.json()
    assert set(course) == COURSE_FIELDS
    uuid.UUID(course["id"])
    assert course["name"] == "Biology 101"
    assert course["term"] == "Fall 2026"
    assert course["exam_date"] == "2026-12-14"
    assert course["archived"] is False
    assert auth_client.get(f"/courses/{course['id']}").json() == course


def test_create_course_with_only_a_name_leaves_term_and_exam_date_empty(
    auth_client, create_course
):
    course = create_course(auth_client, "Chemistry", term="   ")

    assert (course["term"], course["exam_date"]) == (None, None)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"name": ""},
        {"name": "   "},
        {"name": "x" * 121},
        {"name": "Biology", "term": "t" * 61},
        {"name": "Biology", "exam_date": "next tuesday"},
    ],
    ids=["missing", "empty", "blank", "too-long", "term-too-long", "bad-date"],
)
def test_create_course_with_invalid_fields_returns_422(auth_client, payload):
    assert auth_client.post("/courses", json=payload).status_code == 422


def test_name_of_exactly_120_characters_is_accepted(auth_client, create_course):
    assert create_course(auth_client, "x" * 120)["name"] == "x" * 120


def test_list_puts_active_courses_first_each_group_alphabetical(
    auth_client, create_course
):
    for name in ("chemistry", "Algebra", "Biology", "Zoology"):
        create_course(auth_client, name)
    archived = create_course(auth_client, "Anatomy")
    auth_client.patch(f"/courses/{archived['id']}", json={"archived": True})

    names = [(c["name"], c["archived"]) for c in list_courses(auth_client)]

    assert names == [
        ("Algebra", False),
        ("Biology", False),
        ("chemistry", False),
        ("Zoology", False),
        ("Anatomy", True),
    ]


def test_list_counts_each_courses_documents_notes_and_flashcards(
    auth_client, create_course, create_note, storage_root
):
    biology = create_course(auth_client, "Biology")
    empty = create_course(auth_client, "Chemistry")
    upload(auth_client, biology)
    cells = create_note(auth_client, "Cells", "Body", course_id=biology["id"])
    create_note(auth_client, "Mitosis", "Body", course_id=biology["id"])
    create_note(auth_client, "Loose", "Body")
    auth_client.post(f"/notes/{cells['id']}/flashcards/generate", params={"count": 3})

    by_name = {c["name"]: c for c in list_courses(auth_client)}

    assert set(by_name["Biology"]) == COURSE_FIELDS | COUNT_FIELDS
    assert {field: by_name["Biology"][field] for field in COUNT_FIELDS} == {
        "documents_count": 1,
        "notes_count": 2,
        "flashcards_count": 3,
    }
    assert {field: by_name["Chemistry"][field] for field in COUNT_FIELDS} == {
        "documents_count": 0,
        "notes_count": 0,
        "flashcards_count": 0,
    }
    assert empty["id"] == by_name["Chemistry"]["id"]


def test_list_only_contains_the_callers_courses(
    auth_client, other_auth_client, create_course
):
    mine = create_course(auth_client, "Mine")
    create_course(other_auth_client, "Theirs")

    assert [c["id"] for c in list_courses(auth_client)] == [mine["id"]]


def test_patch_changes_only_the_fields_sent(auth_client, create_course):
    course = create_course(
        auth_client, "Biology", term="Fall 2026", exam_date="2026-12-14"
    )

    response = auth_client.patch(
        f"/courses/{course['id']}", json={"name": "Biology II", "archived": True}
    )

    assert response.status_code == 200
    updated = response.json()
    assert (updated["name"], updated["archived"]) == ("Biology II", True)
    assert (updated["term"], updated["exam_date"]) == ("Fall 2026", "2026-12-14")
    assert auth_client.get(f"/courses/{course['id']}").json() == updated


def test_patch_with_null_clears_term_and_exam_date(auth_client, create_course):
    course = create_course(
        auth_client, "Biology", term="Fall 2026", exam_date="2026-12-14"
    )

    updated = auth_client.patch(
        f"/courses/{course['id']}", json={"term": None, "exam_date": None}
    ).json()

    assert (updated["name"], updated["term"], updated["exam_date"]) == (
        "Biology",
        None,
        None,
    )


@pytest.mark.parametrize(
    "payload",
    [{"name": None}, {"name": "  "}, {"archived": None}, {"exam_date": "soon"}],
    ids=["null-name", "blank-name", "null-archived", "bad-date"],
)
def test_patch_with_invalid_fields_returns_422(auth_client, create_course, payload):
    course = create_course(auth_client)

    response = auth_client.patch(f"/courses/{course['id']}", json=payload)

    assert response.status_code == 422
    assert auth_client.get(f"/courses/{course['id']}").json() == course


@pytest.mark.parametrize(
    ("method", "body"),
    [("GET", None), ("PATCH", {"name": "Hijacked"}), ("DELETE", None)],
    ids=["get", "patch", "delete"],
)
def test_another_users_course_is_not_found(
    auth_client, other_auth_client, create_course, method, body
):
    course = create_course(auth_client)

    response = other_auth_client.request(method, f"/courses/{course['id']}", json=body)

    assert response.status_code == 404
    assert response.json() == {"detail": "Course not found"}
    assert auth_client.get(f"/courses/{course['id']}").json() == course


@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
def test_missing_course_is_not_found(auth_client, method):
    response = auth_client.request(method, f"/courses/{MISSING_ID}", json={})

    assert response.status_code == 404


def test_delete_removes_the_course_and_everything_in_it(
    auth_client, create_course, create_note, db_session, storage_root, user
):
    biology = create_course(auth_client, "Biology")
    kept = create_course(auth_client, "Chemistry")
    document = upload(auth_client, biology)
    kept_document = upload(auth_client, kept)
    cells = create_note(auth_client, "Cells", "Body", course_id=biology["id"])
    mitosis = create_note(auth_client, "Mitosis", "Body", course_id=biology["id"])
    bonds = create_note(auth_client, "Bonds", "Body", course_id=kept["id"])
    loose = create_note(auth_client, "Loose", "Body")
    auth_client.post(
        f"/notes/{cells['id']}/links", params={"target_note_id": mitosis["id"]}
    )
    auth_client.post(
        f"/notes/{loose['id']}/links", params={"target_note_id": cells["id"]}
    )
    auth_client.post("/flashcards/generate", json={"note_id": cells["id"], "count": 2})
    kept_card = auth_client.post(
        f"/notes/{bonds['id']}/flashcards/generate", params={"count": 1}
    ).json()[0]

    response = auth_client.delete(f"/courses/{biology['id']}")

    assert response.status_code == 204
    assert response.content == b""
    assert auth_client.get(f"/courses/{biology['id']}").status_code == 404
    assert [c["id"] for c in list_courses(auth_client)] == [kept["id"]]
    assert [d["id"] for d in auth_client.get("/documents").json()] == [
        kept_document["id"]
    ]
    assert sorted(path.name for path in (storage_root / user.id).iterdir()) == [
        f"{kept_document['id']}.pdf"
    ]
    assert {n["id"] for n in auth_client.get("/notes").json()["notes"]} == {
        bonds["id"],
        loose["id"],
    }
    assert [c["id"] for c in auth_client.get("/flashcards/user").json()] == [
        kept_card["id"]
    ]
    assert auth_client.get("/flashcards/sets").json() == []
    db_session.expire_all()
    assert (
        count(
            db_session,
            DocumentChunk,
            DocumentChunk.document_id == uuid.UUID(document["id"]),
        )
        == 0
    )
    assert count(db_session, NoteLink) == 0
    assert count(db_session, FlashcardSRS) == 1
    removed_notes = [uuid.UUID(cells["id"]), uuid.UUID(mitosis["id"])]
    assert (
        count(db_session, NoteEmbedding, NoteEmbedding.note_id.in_(removed_notes)) == 0
    )


def test_deleting_the_account_deletes_its_courses(
    auth_client, client, create_course, db_session, fake_mailer, user
):
    create_course(auth_client)
    auth_client.post("/auth/request-account-deletion")
    [email] = [e for e in fake_mailer.to(user.email) if e.kind == "account_deletion"]
    token = email.link.split("/verify/")[1].split("?")[0]

    response = client.post("/auth/confirm-account-deletion", json={"token": token})

    assert response.status_code == 200
    db_session.expire_all()
    assert count(db_session, Course) == 0


def test_course_routes_require_authentication(client):
    assert client.get("/courses").status_code in {401, 403}
    assert client.post("/courses", json={"name": "Biology"}).status_code in {401, 403}
