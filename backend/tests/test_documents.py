import logging
import shutil
import uuid
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app import main
from app.config import settings
from app.models.document import Document, DocumentChunk
from app.services.ingestion import DocumentStorage
from app.services.ingestion import documents as ingestion_documents
from tests.fixtures.pdfs import Slide, image_only_document, prose_document, slide_deck

MISSING_ID = "00000000-0000-0000-0000-000000000000"

DECK = [
    Slide("Sorting", ("Insertion sort", "Merge sort")),
    Slide("Merge sort", ("Divide and conquer", "O(n log n) comparisons")),
    Slide("Quicksort", ("Partition around a pivot", "O(n log n) on average")),
]


@pytest.fixture
def storage_root(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "document_storage_dir", tmp_path)
    return tmp_path


@pytest.fixture(scope="module")
def deck_pdf() -> bytes:
    return slide_deck(DECK)


@pytest.fixture(scope="module")
def prose_pdf() -> bytes:
    return prose_document(
        "<h1>Cell biology</h1>"
        "<h2>Membranes</h2><p>The membrane is a phospholipid bilayer.</p>"
        "<h2>Nucleus</h2><p>The nucleus stores DNA.</p>"
    )


def upload(client, data: bytes, filename="lecture.pdf", content_type="application/pdf"):
    return client.post("/documents", files={"file": (filename, data, content_type)})


def stored_files(root) -> list:
    return sorted(path for path in root.rglob("*") if path.is_file())


def test_upload_extracts_a_slide_deck_and_stores_the_file(
    auth_client, user, storage_root, deck_pdf
):
    response = upload(auth_client, deck_pdf, filename="week1.pdf")

    assert response.status_code == 201, response.text
    document = response.json()
    assert document["filename"] == "week1.pdf"
    assert document["content_type"] == "application/pdf"
    assert document["size_bytes"] == len(deck_pdf)
    assert document["kind"] == "slides"
    assert document["page_count"] == 3
    assert document["status"] == "ready"
    assert document["error"] is None
    assert [node["title"] for node in document["outline"]] == [
        "Sorting",
        "Merge sort",
        "Quicksort",
    ]
    assert "storage_path" not in document
    stored = storage_root / user.id / f"{document['id']}.pdf"
    assert stored_files(storage_root) == [stored]
    assert stored.read_bytes() == deck_pdf


def test_upload_extracts_a_prose_pdf_with_a_nested_outline(
    auth_client, storage_root, prose_pdf
):
    response = upload(auth_client, prose_pdf)

    assert response.status_code == 201
    document = response.json()
    assert document["kind"] == "pdf"
    assert document["outline"] == [
        {
            "title": "Cell biology",
            "level": 1,
            "page": 1,
            "children": [
                {"title": "Membranes", "level": 2, "page": 1, "children": []},
                {"title": "Nucleus", "level": 2, "page": 1, "children": []},
            ],
        }
    ]


def test_chunks_are_listed_in_order_with_heading_paths_and_pages(
    auth_client, storage_root, deck_pdf
):
    document = upload(auth_client, deck_pdf).json()

    response = auth_client.get(f"/documents/{document['id']}/chunks")

    assert response.status_code == 200
    chunks = response.json()
    assert [
        (chunk["index"], chunk["heading_path"], chunk["page_start"], chunk["page_end"])
        for chunk in chunks
    ] == [(0, ["Sorting"], 1, 1), (1, ["Merge sort"], 2, 2), (2, ["Quicksort"], 3, 3)]
    assert chunks[1]["text"] == "- Divide and conquer\n- O(n log n) comparisons"
    assert chunks[1]["token_estimate"] > 0
    uuid.UUID(chunks[1]["id"])


def test_get_document_returns_the_detail_with_outline(
    auth_client, storage_root, deck_pdf
):
    created = upload(auth_client, deck_pdf).json()

    response = auth_client.get(f"/documents/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_list_returns_only_the_callers_documents_without_outlines(
    auth_client, other_auth_client, storage_root, deck_pdf, prose_pdf
):
    mine = {upload(auth_client, pdf).json()["id"] for pdf in (deck_pdf, prose_pdf)}
    theirs = upload(other_auth_client, deck_pdf).json()["id"]

    my_list = auth_client.get("/documents").json()
    their_list = other_auth_client.get("/documents").json()

    assert {document["id"] for document in my_list} == mine
    assert [document["id"] for document in their_list] == [theirs]
    assert all("outline" not in document for document in my_list)


@pytest.mark.parametrize(
    ("method", "suffix"),
    [("GET", ""), ("GET", "/chunks"), ("DELETE", "")],
    ids=["detail", "chunks", "delete"],
)
def test_another_users_document_is_not_found(
    auth_client, other_auth_client, storage_root, deck_pdf, method, suffix
):
    document = upload(auth_client, deck_pdf).json()

    response = other_auth_client.request(method, f"/documents/{document['id']}{suffix}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Document not found"}
    assert auth_client.get(f"/documents/{document['id']}").status_code == 200
    assert len(stored_files(storage_root)) == 1


@pytest.mark.parametrize("suffix", ["", "/chunks"])
def test_missing_document_is_not_found(auth_client, suffix):
    assert auth_client.get(f"/documents/{MISSING_ID}{suffix}").status_code == 404


def test_delete_removes_the_document_its_chunks_and_its_file(
    auth_client, db_session, storage_root, deck_pdf
):
    document_id = upload(auth_client, deck_pdf).json()["id"]

    response = auth_client.delete(f"/documents/{document_id}")

    assert response.status_code == 204
    assert response.content == b""
    assert auth_client.get(f"/documents/{document_id}").status_code == 404
    assert stored_files(storage_root) == []
    remaining_chunks = db_session.scalar(
        select(func.count())
        .select_from(DocumentChunk)
        .where(DocumentChunk.document_id == uuid.UUID(document_id))
    )
    assert remaining_chunks == 0


@pytest.mark.parametrize(
    ("filename", "data", "content_type"),
    [
        ("notes.txt", b"plain text notes", "text/plain"),
        ("photo.png", b"\x89PNG\r\n\x1a\n" + bytes(64), "image/png"),
        ("fake.pdf", b"\x89PNG\r\n\x1a\n" + bytes(64), "application/pdf"),
        ("empty.pdf", b"", "application/pdf"),
    ],
    ids=["text", "image", "mislabelled-png", "empty"],
)
def test_non_pdf_uploads_are_rejected_with_415_and_not_stored(
    auth_client, storage_root, filename, data, content_type
):
    response = upload(auth_client, data, filename=filename, content_type=content_type)

    assert response.status_code == 415
    assert response.json() == {"detail": "Only PDF files are supported."}
    assert auth_client.get("/documents").json() == []
    assert stored_files(storage_root) == []


def test_pdf_sent_as_octet_stream_is_accepted(auth_client, storage_root, deck_pdf):
    response = upload(auth_client, deck_pdf, content_type="application/octet-stream")

    assert response.status_code == 201
    assert response.json()["content_type"] == "application/pdf"


def test_upload_exactly_at_the_size_limit_is_accepted(
    auth_client, storage_root, monkeypatch, deck_pdf
):
    monkeypatch.setattr(settings, "max_document_bytes", len(deck_pdf))

    assert upload(auth_client, deck_pdf).status_code == 201


def test_upload_one_byte_over_the_size_limit_is_rejected_with_413(
    auth_client, storage_root, monkeypatch, deck_pdf
):
    monkeypatch.setattr(settings, "max_document_bytes", len(deck_pdf) - 1)

    response = upload(auth_client, deck_pdf)

    assert response.status_code == 413
    assert auth_client.get("/documents").json() == []
    assert stored_files(storage_root) == []


def test_oversized_content_length_is_rejected_before_the_body_is_read(
    client, monkeypatch
):
    monkeypatch.setattr(settings, "max_document_bytes", 1024 * 1024)

    response = upload(client, b"%PDF-" + bytes(2 * 1024 * 1024))

    assert response.status_code == 413
    assert response.json() == {"detail": "Documents are limited to 1 MB."}


def test_oversized_streamed_body_without_content_length_is_cut_off(
    auth_client, monkeypatch
):
    monkeypatch.setattr(settings, "max_document_bytes", 1024)

    def body():
        for _ in range(64):
            yield bytes(16 * 1024)

    response = auth_client.post(
        "/documents",
        content=body(),
        headers={"Content-Type": "multipart/form-data; boundary=boundary"},
    )

    assert response.status_code == 413


def test_image_only_pdf_is_kept_as_failed_with_the_reason(auth_client, storage_root):
    response = upload(auth_client, image_only_document(pages=2), filename="scan.pdf")

    assert response.status_code == 201
    document = response.json()
    assert document["status"] == "failed"
    assert document["error"].startswith("No extractable text found.")
    assert document["kind"] is None
    assert document["page_count"] is None
    assert document["outline"] is None
    assert auth_client.get(f"/documents/{document['id']}/chunks").json() == []
    assert len(stored_files(storage_root)) == 1


def test_corrupt_pdf_is_kept_as_failed(auth_client, storage_root):
    response = upload(auth_client, b"%PDF-1.7\nthis is not a real pdf body")

    assert response.status_code == 201
    assert response.json()["status"] == "failed"
    assert response.json()["error"] == "The file is not a readable PDF."


def test_unexpected_extraction_error_is_recorded_without_leaking_details(
    auth_client, storage_root, monkeypatch, deck_pdf
):
    def explode(data):
        raise RuntimeError("internal detail")

    monkeypatch.setattr(ingestion_documents, "extract_document", explode)

    response = upload(auth_client, deck_pdf)

    assert response.status_code == 201
    assert response.json()["status"] == "failed"
    assert response.json()["error"] == "Text extraction failed unexpectedly."


def test_file_is_removed_when_the_database_write_fails(
    auth_client, db_session, storage_root, monkeypatch, deck_pdf
):
    def fail_commit():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(db_session, "commit", fail_commit)

    with pytest.raises(RuntimeError, match="database unavailable"):
        upload(auth_client, deck_pdf)
    assert stored_files(storage_root) == []


def test_client_supplied_path_is_reduced_to_the_file_name(
    auth_client, storage_root, deck_pdf
):
    response = upload(auth_client, deck_pdf, filename="C:\\Users\\me\\Week 1.pdf")

    assert response.json()["filename"] == "Week 1.pdf"


def test_document_storage_is_outside_the_public_uploads_mount():
    assert not settings.document_storage_dir.resolve().is_relative_to(
        Path(main.UPLOAD_DIR).resolve()
    )


def test_deleting_the_account_deletes_its_documents_and_their_files(
    auth_client,
    other_auth_client,
    user,
    other_user,
    client,
    db_session,
    fake_mailer,
    storage_root,
    deck_pdf,
):
    upload(auth_client, deck_pdf)
    upload(other_auth_client, deck_pdf)
    assert (storage_root / user.id).is_dir()
    assert auth_client.post("/auth/request-account-deletion").status_code == 200
    [deletion_email] = [
        email
        for email in fake_mailer.to(user.email)
        if email.kind == "account_deletion"
    ]
    token = deletion_email.link.split("/verify/")[1].split("?")[0]

    response = client.post("/auth/confirm-account-deletion", json={"token": token})

    assert response.status_code == 200
    db_session.expire_all()
    remaining = db_session.scalars(select(Document.user_id)).all()
    assert remaining == [uuid.UUID(other_user.id)]
    assert not (storage_root / user.id).exists()
    assert len(stored_files(storage_root / other_user.id)) == 1


def test_removing_files_of_a_user_without_documents_is_a_no_op(tmp_path):
    DocumentStorage(tmp_path).delete_user_files(uuid.uuid4())

    assert list(tmp_path.iterdir()) == []


def test_failure_to_remove_user_files_is_logged_not_raised(
    tmp_path, monkeypatch, caplog
):
    def refuse(path):
        raise PermissionError(path)

    monkeypatch.setattr(shutil, "rmtree", refuse)

    with caplog.at_level(logging.ERROR):
        DocumentStorage(tmp_path).delete_user_files("someone")

    assert "Could not remove stored documents of user someone" in caplog.text
