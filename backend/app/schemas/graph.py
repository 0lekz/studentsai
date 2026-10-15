import uuid
from datetime import datetime

from app.schemas.common import BaseSchema


class NoteConnection(BaseSchema):
    source_id: uuid.UUID
    target_id: uuid.UUID
    similarity: float
    connection_type: str = "similarity"


class GraphNode(BaseSchema):
    id: uuid.UUID
    title: str
    content_preview: str
    created_at: datetime
    word_count: int


class GraphResponse(BaseSchema):
    nodes: list[GraphNode]
    connections: list[NoteConnection]
    total_nodes: int
