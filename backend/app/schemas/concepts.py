import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.concept import CONCEPT_NAME_MAX_LENGTH, ConceptEdgeKind

CONCEPT_DESCRIPTION_MAX_LENGTH = 2000


class ConceptSourceResponse(BaseModel):
    document_id: uuid.UUID
    chunk_id: uuid.UUID
    page_start: int
    page_end: int


class ConceptResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    order: int
    mastery: float | None = Field(
        description="0 to 1 from the SM-2 state of the concept's questions; null without questions"
    )
    question_count: int
    sources: list[ConceptSourceResponse]


class ConceptUpdate(BaseModel):
    """Only the fields sent are changed."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(
        default=None, min_length=1, max_length=CONCEPT_NAME_MAX_LENGTH
    )
    description: str | None = Field(
        default=None, max_length=CONCEPT_DESCRIPTION_MAX_LENGTH
    )

    @field_validator("name", "description")
    @classmethod
    def reject_null(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("must not be null")
        return value

    @field_validator("name")
    @classmethod
    def collapse_whitespace(cls, value: str) -> str:
        return " ".join(value.split())


class ConceptMapNode(BaseModel):
    id: uuid.UUID
    name: str
    mastery: float | None
    question_count: int
    order: int


class ConceptMapEdge(BaseModel):
    source: uuid.UUID
    target: uuid.UUID
    kind: ConceptEdgeKind
    weight: float


class ConceptMapResponse(BaseModel):
    nodes: list[ConceptMapNode]
    edges: list[ConceptMapEdge]
