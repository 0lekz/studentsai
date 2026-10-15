import logging
import uuid
from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk, DocumentStatus
from app.services.ingestion.extraction import (
    ExtractionError,
    ExtractionResult,
    extract_document,
)
from app.services.ingestion.storage import DocumentStorage

logger = logging.getLogger(__name__)

PDF_CONTENT_TYPE = "application/pdf"


def ingest_pdf(
    db: Session,
    storage: DocumentStorage,
    *,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
    filename: str,
    data: bytes,
) -> Document:
    """Extracts synchronously, then stores the file and the document together.

    A PDF that cannot be extracted is still kept, marked failed with the reason.
    """
    document_id = uuid.uuid4()
    document = Document(
        id=document_id,
        user_id=user_id,
        course_id=course_id,
        filename=filename,
        content_type=PDF_CONTENT_TYPE,
        size_bytes=len(data),
        storage_path=storage.path_for(user_id, document_id),
    )
    try:
        _apply_extraction(document, extract_document(data))
    except ExtractionError as error:
        _mark_failed(document, str(error))
    except Exception:
        logger.exception("Unexpected failure extracting document %s", document_id)
        _mark_failed(document, "Text extraction failed unexpectedly.")

    storage.save(document.storage_path, data)
    db.add(document)
    try:
        db.commit()
    except Exception:
        db.rollback()
        storage.delete(document.storage_path)
        raise
    db.refresh(document)
    return document


def list_documents(
    db: Session, user_id: uuid.UUID, course_id: uuid.UUID | None = None
) -> list[Document]:
    query = select(Document).where(Document.user_id == user_id)
    if course_id is not None:
        query = query.where(Document.course_id == course_id)
    return list(db.scalars(query.order_by(Document.created_at.desc(), Document.id)))


def get_document(
    db: Session, user_id: uuid.UUID, document_id: uuid.UUID
) -> Document | None:
    return db.scalar(
        select(Document).where(Document.id == document_id, Document.user_id == user_id)
    )


def delete_document(db: Session, storage: DocumentStorage, document: Document) -> None:
    db.delete(document)
    db.commit()
    storage.delete(document.storage_path)


def _apply_extraction(document: Document, result: ExtractionResult) -> None:
    document.kind = result.kind.value
    document.page_count = result.page_count
    document.outline = [asdict(node) for node in result.outline]
    document.status = DocumentStatus.READY.value
    document.chunks = [
        DocumentChunk(
            index=chunk.index,
            heading_path=chunk.heading_path,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            text=chunk.text,
            token_estimate=chunk.token_estimate,
        )
        for chunk in result.chunks
    ]


def _mark_failed(document: Document, reason: str) -> None:
    document.status = DocumentStatus.FAILED.value
    document.error = reason
