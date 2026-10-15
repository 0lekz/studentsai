import uuid

from fastapi import (
    APIRouter,
    Depends,
    Request,
)
from sqlalchemy.orm import Session

from app.ai_service import (
    calculate_note_similarities,
)
from app.auth import (
    get_current_user_id,
)
from app.config import settings
from app.db.session import get_db
from app.dependencies import optional_owned_course_id
from app.rate_limiter import check_rate_limit
from app.repositories.notes import (
    get_links_for_user_notes,
    get_notes_by_user,
    get_similarities_for_notes,
)
from app.schemas import (
    GraphNode,
    GraphResponse,
    NoteConnection,
)
from app.services.embedding_service import (
    find_embedding_connections,
)

router = APIRouter()


@router.get("/graph", response_model=GraphResponse)
async def get_notes_graph(
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
    course_id: uuid.UUID | None = Depends(optional_owned_course_id),
    db: Session = Depends(get_db),
):
    """Get graph visualization of all of a user's notes, optionally one course's"""
    await check_rate_limit(request, str(user_id))

    notes = get_notes_by_user(db, user_id, course_id=course_id)

    if len(notes) < 2:
        return GraphResponse(
            nodes=[
                GraphNode(
                    id=note.id,
                    title=note.title,
                    content_preview=note.content[:200] + "..."
                    if len(note.content) > 200
                    else note.content,
                    created_at=note.created_at,
                    word_count=len(note.content.split()),
                )
                for note in notes
            ],
            connections=[],
            total_nodes=len(notes),
        )

    # Prepare notes data for similarity calculation
    notes_data = [
        {"id": note.id, "title": note.title, "content": note.content} for note in notes
    ]
    note_ids = [note.id for note in notes]
    in_graph = set(note_ids)

    # Calculate connections
    if settings.similarity_backend == "embeddings":
        connections = find_embedding_connections(db, note_ids)
    else:
        connections = calculate_note_similarities(notes_data)

    # Create graph nodes
    nodes = [
        GraphNode(
            id=note.id,
            title=note.title,
            content_preview=note.content[:200] + "..."
            if len(note.content) > 200
            else note.content,
            created_at=note.created_at,
            word_count=len(note.content.split()),
        )
        for note in notes
    ]

    # Create graph connections
    graph_connections = [
        NoteConnection(
            source_id=conn["source_id"],
            target_id=conn["target_id"],
            similarity=conn["similarity"],
            connection_type=conn["connection_type"],
        )
        for conn in connections
    ]

    # Merge manual links that stay inside the graph
    links = get_links_for_user_notes(db, note_ids)
    for link_row in links:
        if link_row.to_note_id not in in_graph:
            continue
        graph_connections.append(
            NoteConnection(
                source_id=link_row.from_note_id,
                target_id=link_row.to_note_id,
                similarity=1.0,
                connection_type="manual",
            )
        )

    # Merge stored similarities (authoritative values for edge thickness)
    sims = get_similarities_for_notes(db, note_ids)
    for s in sims:
        if s.note_a_id not in in_graph or s.note_b_id not in in_graph:
            continue
        graph_connections.append(
            NoteConnection(
                source_id=s.note_a_id,
                target_id=s.note_b_id,
                similarity=float(s.similarity) / 1000.0,
                connection_type="similarity",
            )
        )

    return GraphResponse(
        nodes=nodes, connections=graph_connections, total_nodes=len(notes)
    )
