import uuid
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import asdict, dataclass

from sqlalchemy.orm import Session

from app.models.concept import Concept
from app.models.course import Course
from app.repositories import concepts as repo
from app.repositories.concepts import QuestionSchedule
from app.schemas.concepts import (
    ConceptMapEdge,
    ConceptMapNode,
    ConceptMapResponse,
    ConceptResponse,
    ConceptSourceResponse,
)
from app.services.concepts.edges import rebuild_edges
from app.services.concepts.mastery import ReviewState, concept_mastery
from app.services.embedding_service import Embedder, get_embedder


class ConceptNameTakenError(Exception):
    """Another concept in the course has this name, ignoring case."""


@dataclass(frozen=True)
class Progress:
    mastery: float | None
    question_count: int


def _review_state(schedule: QuestionSchedule) -> ReviewState | None:
    if schedule.repetitions is None or schedule.efactor_hundredths is None:
        return None
    return ReviewState(schedule.repetitions, schedule.efactor_hundredths / 100)


def concept_progress(
    db: Session, user_id: uuid.UUID, concept_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, Progress]:
    """Mastery and question count per concept, from the user's questions on it."""
    states: dict[uuid.UUID, list[ReviewState | None]] = defaultdict(list)
    for schedule in repo.question_schedules(db, user_id, concept_ids):
        states[schedule.concept_id].append(_review_state(schedule))
    return {
        concept_id: Progress(
            concept_mastery(states[concept_id]), len(states[concept_id])
        )
        for concept_id in concept_ids
    }


def list_concepts(db: Session, course: Course) -> list[ConceptResponse]:
    return _responses(db, course, repo.course_concepts(db, course.id))


def describe_concept(db: Session, course: Course, concept: Concept) -> ConceptResponse:
    [response] = _responses(db, course, [concept])
    return response


def _responses(
    db: Session, course: Course, concepts: Sequence[Concept]
) -> list[ConceptResponse]:
    concept_ids = [concept.id for concept in concepts]
    sources = repo.concept_sources(db, course.id, concept_ids)
    progress = concept_progress(db, course.user_id, concept_ids)
    return [
        ConceptResponse(
            id=concept.id,
            name=concept.name,
            description=concept.description,
            order=concept.order,
            mastery=progress[concept.id].mastery,
            question_count=progress[concept.id].question_count,
            sources=[
                ConceptSourceResponse(**asdict(source))
                for source in sources.get(concept.id, [])
            ],
        )
        for concept in concepts
    ]


def concept_map(db: Session, course: Course) -> ConceptMapResponse:
    concepts = repo.course_concepts(db, course.id)
    progress = concept_progress(db, course.user_id, [c.id for c in concepts])
    return ConceptMapResponse(
        nodes=[
            ConceptMapNode(
                id=concept.id,
                name=concept.name,
                mastery=progress[concept.id].mastery,
                question_count=progress[concept.id].question_count,
                order=concept.order,
            )
            for concept in concepts
        ],
        edges=[
            ConceptMapEdge(
                source=edge.source_id,
                target=edge.target_id,
                kind=edge.kind,
                weight=edge.weight,
            )
            for edge in repo.course_edges(db, course.id)
        ],
    )


def update_concept(
    db: Session,
    concept: Concept,
    changes: dict[str, str],
    embedder: Embedder | None = None,
) -> Concept:
    """Renaming re-embeds the name and rebuilds the course's edges; a taken name raises."""
    repo.lock_course(db, concept.course_id)
    name = changes.get("name")
    if name is not None and name != concept.name:
        _rename(db, concept, name, embedder or get_embedder())
    if "description" in changes:
        concept.description = changes["description"]
    db.commit()
    db.refresh(concept)
    return concept


def _rename(db: Session, concept: Concept, name: str, embedder: Embedder) -> None:
    clash = repo.find_concept_by_name(db, concept.course_id, name)
    if clash is not None and clash.id != concept.id:
        raise ConceptNameTakenError
    [vector] = embedder.embed([name])
    concept.name = name
    concept.embedding = vector
    concept.embedding_model = embedder.model_name
    db.flush()
    rebuild_edges(db, concept.course_id, embedder.model_name)


def delete_concept(db: Session, concept: Concept) -> None:
    """Its chunk links and edges go with it, its questions keep existing without a concept."""
    course_id = concept.course_id
    repo.lock_course(db, course_id)
    db.delete(concept)
    db.flush()
    rebuild_edges(db, course_id, get_embedder().model_name)
    db.commit()


def prune_orphan_concepts(db: Session, course_id: uuid.UUID) -> None:
    """Deletes concepts left without chunk links or questions and rebuilds the edges.

    Call it after deleting a document and before committing: it flushes the
    deletion so the database cascade has already dropped that document's links.
    """
    db.flush()
    repo.lock_course(db, course_id)
    repo.delete_orphan_concepts(db, course_id)
    rebuild_edges(db, course_id, get_embedder().model_name)
