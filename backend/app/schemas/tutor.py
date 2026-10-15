import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models.flashcard import FlashcardKind
from app.services.tutor.grading import Verdict

MAX_GENERATE_COUNT = 20
DEFAULT_GENERATE_COUNT = 5
MAX_SESSION_SIZE = 30
DEFAULT_SESSION_SIZE = 10
MAX_QUESTION_CHARS = 2000
MAX_ANSWER_CHARS = 4000


class GenerateQuestionsRequest(BaseModel):
    """Generate from one chunk, from one concept's chunks, or from the course's least-covered chunks."""

    concept_id: uuid.UUID | None = None
    chunk_id: uuid.UUID | None = None
    count: int = Field(default=DEFAULT_GENERATE_COUNT, ge=1, le=MAX_GENERATE_COUNT)


class PracticeSessionRequest(BaseModel):
    size: int = Field(default=DEFAULT_SESSION_SIZE, ge=1, le=MAX_SESSION_SIZE)


class AnswerRequest(BaseModel):
    """`choice_index` answers a multiple choice question, `answer` any other kind."""

    answer: str | None = Field(default=None, max_length=MAX_ANSWER_CHARS)
    choice_index: int | None = Field(default=None, ge=0)


class AskRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)


class ConceptRef(BaseModel):
    id: uuid.UUID
    name: str


class QuestionSource(BaseModel):
    document_id: uuid.UUID
    filename: str
    page_start: int
    page_end: int


class PracticeQuestion(BaseModel):
    """A question as practice shows it.

    `reference_answer` is set only for recall questions, which the student
    checks against it; other kinds reveal it in the answer's grade. `source` is
    null only for cards written from notes; deleting a document deletes the
    questions generated from it.
    """

    id: uuid.UUID
    kind: FlashcardKind
    prompt: str
    choices: list[str] | None
    reference_answer: str | None
    concept: ConceptRef | None
    source: QuestionSource | None


class QuestionList(BaseModel):
    questions: list[PracticeQuestion]


class Citation(BaseModel):
    document_id: uuid.UUID
    filename: str
    chunk_id: uuid.UUID
    page_start: int
    page_end: int
    excerpt: str


class SrsState(BaseModel):
    due_date: date
    interval_days: int
    repetitions: int


class AnswerResponse(BaseModel):
    verdict: Verdict
    score: int = Field(ge=0, le=100)
    feedback: str
    missing_points: list[str]
    reference_answer: str
    source: Citation | None
    srs: SrsState


class AskResponse(BaseModel):
    """`[n]` markers in the Markdown answer refer to `citations[n - 1]`.

    `covered` is true when the answer is grounded in cited course chunks, and
    false when the material does not cover the question.
    """

    answer: str
    covered: bool
    citations: list[Citation]


class CourseRef(BaseModel):
    id: uuid.UUID
    name: str


class ConceptMasteryItem(BaseModel):
    id: uuid.UUID
    name: str
    mastery: float


class TodayCourse(BaseModel):
    course: CourseRef
    due_count: int
    weakest_concepts: list[ConceptMasteryItem]


class SuggestedSession(BaseModel):
    course_id: uuid.UUID
    size: int


class TodayResponse(BaseModel):
    due_count: int
    courses: list[TodayCourse]
    suggested: SuggestedSession | None
