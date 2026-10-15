"""Where the tutor loop meets the concept engine: question tags and per-concept mastery."""

import asyncio
import uuid
from collections.abc import Collection, Sequence
from dataclasses import dataclass

import numpy as np
from sqlalchemy.orm import Session

from app.repositories import tutor as tutor_repository
from app.services.concepts.catalog import concept_progress
from app.services.embedding_service import get_embedder


@dataclass(frozen=True)
class ConceptStanding:
    id: uuid.UUID
    course_id: uuid.UUID
    name: str
    order: int
    mastery: float | None


async def tag_concepts(
    db: Session, chunk_id: uuid.UUID, questions: Sequence[str]
) -> list[uuid.UUID | None]:
    """The concept each question tests, among the concepts its chunk is linked to.

    A chunk with one concept tags every question with it. With several, each
    question goes to the concept whose name embedding is nearest to the
    question's text, which is local and free.
    """
    concepts = tutor_repository.chunk_concepts(db, chunk_id)
    if not questions or not concepts:
        return [None] * len(questions)
    embedder = get_embedder()
    comparable = [c for c in concepts if c.embedding_model == embedder.model_name]
    if len(concepts) == 1 or not comparable:
        return [concepts[0].id] * len(questions)

    vectors = await asyncio.to_thread(embedder.embed, list(questions))
    question_matrix = _unit_rows(np.asarray(vectors, dtype=float))
    concept_matrix = _unit_rows(
        np.asarray([concept.embedding for concept in comparable], dtype=float)
    )
    nearest = (question_matrix @ concept_matrix.T).argmax(axis=1)
    return [comparable[index].id for index in nearest]


def concept_standings(
    db: Session, user_id: uuid.UUID, course_ids: Collection[uuid.UUID]
) -> list[ConceptStanding]:
    """Every concept of the courses with the user's mastery, in course order."""
    concepts = tutor_repository.courses_concepts(db, course_ids)
    progress = concept_progress(db, user_id, [concept.id for concept in concepts])
    return [
        ConceptStanding(
            id=concept.id,
            course_id=concept.course_id,
            name=concept.name,
            order=concept.order,
            mastery=progress[concept.id].mastery,
        )
        for concept in concepts
    ]


def weakest_first(standings: Sequence[ConceptStanding]) -> list[ConceptStanding]:
    """Lowest mastery first; a concept without questions counts as unpracticed, and ties keep course order."""
    return sorted(
        standings,
        key=lambda standing: (standing.mastery or 0.0, standing.order),
    )


def _unit_rows(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.where(norms == 0, 1, norms)
