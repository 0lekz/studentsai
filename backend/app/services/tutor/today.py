import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.models.course import Course
from app.repositories import tutor as tutor_repository
from app.services.tutor.concept_links import ConceptStanding, concept_standings
from app.services.tutor.session import today_utc

WEAKEST_CONCEPTS_SHOWN = 3
DEFAULT_SUGGESTED_SIZE = 10
MAX_SUGGESTED_SIZE = 20


@dataclass(frozen=True)
class CourseToday:
    course: Course
    due_count: int
    weakest_concepts: list[ConceptStanding]


@dataclass(frozen=True)
class SuggestedSession:
    course_id: uuid.UUID
    size: int


@dataclass(frozen=True)
class Today:
    due_count: int
    courses: list[CourseToday]
    suggested: SuggestedSession | None


def today_overview(db: Session, user_id: uuid.UUID) -> Today:
    """Due cards and the weakest practiced, not yet mastered concepts of every active course, and one session to start."""
    courses = tutor_repository.active_courses(db, user_id)
    course_ids = [course.id for course in courses]
    due = tutor_repository.due_counts(db, user_id, course_ids, today_utc())
    standings: dict[uuid.UUID, list[ConceptStanding]] = {}
    for standing in concept_standings(db, user_id, course_ids):
        if standing.mastery is not None and standing.mastery < 1:
            standings.setdefault(standing.course_id, []).append(standing)

    rows = [
        CourseToday(
            course=course,
            due_count=due.get(course.id, 0),
            weakest_concepts=sorted(
                standings.get(course.id, []),
                key=lambda standing: (standing.mastery, standing.order),
            )[:WEAKEST_CONCEPTS_SHOWN],
        )
        for course in courses
    ]
    practicable = tutor_repository.courses_with_material(db, user_id, course_ids)
    return Today(
        due_count=sum(row.due_count for row in rows),
        courses=rows,
        suggested=suggest(
            [row for row in rows if row.course.id in practicable], today_utc()
        ),
    )


def suggest(rows: list[CourseToday], today: date) -> SuggestedSession | None:
    """The course with the most due cards; with none due, the one whose exam is nearest."""
    if not rows:
        return None

    def priority(row: CourseToday) -> tuple:
        exam = row.course.exam_date
        days_to_exam = (exam - today).days if exam and exam >= today else None
        return (
            -row.due_count,
            days_to_exam is None,
            days_to_exam or 0,
            row.course.name.lower(),
        )

    best = min(rows, key=priority)
    size = min(MAX_SUGGESTED_SIZE, max(DEFAULT_SUGGESTED_SIZE, best.due_count))
    return SuggestedSession(course_id=best.course.id, size=size)
