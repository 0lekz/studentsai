import uuid
from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth import get_current_user_id, get_verified_user_id
from app.db.session import get_db
from app.dependencies import enforce_rate_limit
from app.models.course import Course
from app.models.flashcard import Flashcard, FlashcardKind
from app.rate_limiter import check_ai_rate_limit
from app.repositories import tutor as tutor_repository
from app.schemas.tutor import (
    AnswerRequest,
    AnswerResponse,
    Citation,
    ConceptRef,
    GenerateQuestionsRequest,
    PracticeQuestion,
    PracticeSessionRequest,
    QuestionList,
    QuestionSource,
    SrsState,
)
from app.services.courses import get_course
from app.services.llm import LLMError, LLMUnavailableError
from app.services.tutor.answers import answer_question
from app.services.tutor.grading import InvalidAnswerError
from app.services.tutor.session import (
    build_session,
    generate_for_course,
    question_contexts,
)


def tutor_failure(error: LLMError) -> HTTPException:
    if isinstance(error, LLMUnavailableError):
        return HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The tutor is unavailable right now. Try again in a minute.",
        )
    return HTTPException(
        status.HTTP_502_BAD_GATEWAY,
        detail="The tutor could not produce a usable answer. Try again.",
    )


async def tutor_course(
    course_id: uuid.UUID,
    request: Request,
    user_id: uuid.UUID = Depends(get_verified_user_id),
    db: Session = Depends(get_db),
) -> Course:
    """A course the caller owns, for a route that may call a model; another user's course is a 404."""
    course = get_course(db, user_id, course_id)
    if course is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Course not found")
    await check_ai_rate_limit(request, str(user_id))
    return course


router = APIRouter(tags=["practice"], dependencies=[Depends(enforce_rate_limit)])


@router.post("/courses/{course_id}/questions/generate", response_model=QuestionList)
async def generate_course_questions(
    payload: GenerateQuestionsRequest,
    course: Course = Depends(tutor_course),
    user_id: uuid.UUID = Depends(get_verified_user_id),
    db: Session = Depends(get_db),
) -> QuestionList:
    """Generate questions from one chunk, one concept's chunks, or the course's chunks not yet used.

    Every valid question of each chunk visited is kept, so more than `count` can
    come back; a chunk already used at the current prompt version adds nothing.
    """
    if payload.chunk_id and payload.concept_id:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Give chunk_id or concept_id, not both.",
        )
    chunk = None
    if payload.chunk_id:
        chunk = tutor_repository.get_course_chunk(db, course.id, payload.chunk_id)
        if chunk is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Chunk not found")
    if payload.concept_id and not tutor_repository.get_course_concept(
        db, course.id, payload.concept_id
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Concept not found")
    try:
        questions = await generate_for_course(
            db,
            user_id,
            course.id,
            count=payload.count,
            chunk=chunk,
            concept_id=payload.concept_id,
        )
    except LLMError as error:
        raise tutor_failure(error) from error
    return _question_list(db, questions)


@router.post("/courses/{course_id}/practice/session", response_model=QuestionList)
async def start_practice_session(
    payload: PracticeSessionRequest | None = None,
    course: Course = Depends(tutor_course),
    user_id: uuid.UUID = Depends(get_verified_user_id),
    db: Session = Depends(get_db),
) -> QuestionList:
    """Due reviews, then unseen questions on the weakest concepts, then generated ones."""
    size = (payload or PracticeSessionRequest()).size
    try:
        questions = await build_session(db, user_id, course.id, size)
    except LLMError as error:
        raise tutor_failure(error) from error
    return _question_list(db, questions)


@router.get("/questions/{question_id}", response_model=PracticeQuestion)
def get_question(
    question_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> PracticeQuestion:
    """One question as a practice session shows it, for reloading a session screen."""
    flashcard = tutor_repository.get_user_question(db, user_id, question_id)
    if flashcard is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Question not found")
    [question] = _question_list(db, [flashcard]).questions
    return question


@router.post("/questions/{question_id}/answer", response_model=AnswerResponse)
async def answer(
    question_id: uuid.UUID,
    payload: AnswerRequest,
    request: Request,
    user_id: uuid.UUID = Depends(get_verified_user_id),
    db: Session = Depends(get_db),
) -> AnswerResponse:
    """Grade an answer and reschedule the question with SM-2."""
    flashcard = tutor_repository.get_user_question(db, user_id, question_id)
    if flashcard is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Question not found")
    await check_ai_rate_limit(request, str(user_id))
    try:
        outcome = await answer_question(
            db,
            flashcard,
            answer=payload.answer,
            choice_index=payload.choice_index,
            user_id=user_id,
        )
    except InvalidAnswerError as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    except LLMError as error:
        raise tutor_failure(error) from error

    grade = outcome.grade
    return AnswerResponse(
        verdict=grade.verdict,
        score=grade.score,
        feedback=grade.feedback,
        missing_points=grade.missing_points,
        reference_answer=outcome.reference_answer,
        source=(
            Citation(
                document_id=outcome.source.chunk.document_id,
                filename=outcome.source.chunk.filename,
                chunk_id=outcome.source.chunk.chunk_id,
                page_start=outcome.source.chunk.page_start,
                page_end=outcome.source.chunk.page_end,
                excerpt=outcome.source.excerpt,
            )
            if outcome.source
            else None
        ),
        srs=SrsState(
            due_date=outcome.srs.due_date,
            interval_days=outcome.srs.interval_days,
            repetitions=outcome.srs.repetitions,
        ),
    )


def _question_list(db: Session, flashcards: Sequence[Flashcard]) -> QuestionList:
    return QuestionList(
        questions=[
            PracticeQuestion(
                id=context.flashcard.id,
                kind=context.flashcard.kind,
                prompt=context.flashcard.question,
                choices=context.flashcard.choices,
                reference_answer=(
                    context.flashcard.answer
                    if context.flashcard.kind == FlashcardKind.RECALL
                    else None
                ),
                concept=(
                    ConceptRef(id=context.concept[0], name=context.concept[1])
                    if context.concept
                    else None
                ),
                source=(
                    QuestionSource(
                        document_id=context.source.document_id,
                        filename=context.source.filename,
                        page_start=context.source.page_start,
                        page_end=context.source.page_end,
                    )
                    if context.source
                    else None
                ),
            )
            for context in question_contexts(db, flashcards)
        ]
    )
