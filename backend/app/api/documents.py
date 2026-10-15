import os
import uuid
from collections.abc import Callable, Coroutine
from pathlib import PurePosixPath
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session
from starlette.types import Message, Receive

from app.auth import get_current_user_id
from app.config import settings
from app.db.session import get_db
from app.dependencies import (
    enforce_rate_limit,
    get_document_storage,
    optional_owned_course_id,
)
from app.models.document import Document, DocumentChunk
from app.schemas.documents import (
    DocumentChunkResponse,
    DocumentDetailResponse,
    DocumentResponse,
)
from app.services.courses import get_course
from app.services.ingestion import (
    DocumentStorage,
    delete_document,
    get_document,
    ingest_pdf,
    list_documents,
)

MULTIPART_OVERHEAD_BYTES = 64 * 1024
PDF_SIGNATURE = b"%PDF-"
PDF_SIGNATURE_WINDOW = 1024
ACCEPTED_CONTENT_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/octet-stream",
}


def _too_large() -> HTTPException:
    limit = settings.max_document_bytes / (1024 * 1024)
    return HTTPException(
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        detail=f"Documents are limited to {limit:g} MB.",
    )


def _capped(receive: Receive, max_bytes: int) -> Receive:
    received = 0

    async def capped_receive() -> Message:
        nonlocal received
        message = await receive()
        received += len(message.get("body", b""))
        if received > max_bytes:
            raise _too_large()
        return message

    return capped_receive


class SizeLimitedRoute(APIRoute):
    """Rejects oversized bodies while they stream in, before multipart parsing spools them to disk."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()

        async def size_limited_handler(request: Request) -> Response:
            max_body_bytes = settings.max_document_bytes + MULTIPART_OVERHEAD_BYTES
            declared = request.headers.get("content-length", "")
            if declared.isdigit() and int(declared) > max_body_bytes:
                raise _too_large()
            return await handler(
                Request(request.scope, _capped(request.receive, max_body_bytes))
            )

        return size_limited_handler


def owned_document(
    document_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Document:
    document = get_document(db, user_id, document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    dependencies=[Depends(enforce_rate_limit)],
    route_class=SizeLimitedRoute,
)


@router.post(
    "", response_model=DocumentDetailResponse, status_code=status.HTTP_201_CREATED
)
def upload_document(
    file: UploadFile = File(...),
    course_id: uuid.UUID = Form(...),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    storage: DocumentStorage = Depends(get_document_storage),
) -> Document:
    if get_course(db, user_id, course_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Course not found")
    if file.content_type and file.content_type not in ACCEPTED_CONTENT_TYPES:
        raise _unsupported_type()
    if _size_of(file) > settings.max_document_bytes:
        raise _too_large()
    data = file.file.read()
    if PDF_SIGNATURE not in data[:PDF_SIGNATURE_WINDOW]:
        raise _unsupported_type()
    return ingest_pdf(
        db,
        storage,
        user_id=user_id,
        course_id=course_id,
        filename=_display_name(file.filename),
        data=data,
    )


@router.get("", response_model=list[DocumentResponse])
def get_documents(
    user_id: uuid.UUID = Depends(get_current_user_id),
    course_id: uuid.UUID | None = Depends(optional_owned_course_id),
    db: Session = Depends(get_db),
) -> list[Document]:
    return list_documents(db, user_id, course_id)


@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document_detail(document: Document = Depends(owned_document)) -> Document:
    return document


@router.get("/{document_id}/chunks", response_model=list[DocumentChunkResponse])
def get_document_chunks(
    document: Document = Depends(owned_document),
) -> list[DocumentChunk]:
    return document.chunks


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_document(
    document: Document = Depends(owned_document),
    db: Session = Depends(get_db),
    storage: DocumentStorage = Depends(get_document_storage),
) -> None:
    delete_document(db, storage, document)


def _unsupported_type() -> HTTPException:
    return HTTPException(
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Only PDF files are supported."
    )


def _size_of(file: UploadFile) -> int:
    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)
    return size


def _display_name(filename: str | None) -> str:
    name = PurePosixPath((filename or "").replace("\\", "/")).name
    return name[:255] or "document.pdf"
