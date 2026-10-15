"""The Today overview: due cards, weakest concepts and the suggested session."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models import Concept, Flashcard, FlashcardSRS
from app.services.embedding_service import FakeEmbedder
from tests.fixtures.pdfs import Slide, slide_deck


def today():
    return datetime.now(UTC).date()


@pytest.fixture
def add_card(db_session, user):
    def add(
        course: dict,
        *,
        due_in_days: int = 0,
        repetitions: int = 0,
        concept: Concept | None = None,
        owner_id: str | None = None,
    ) -> Flashcard:
        owner = uuid.UUID(owner_id or user.id)
        card = Flashcard(
            question="Q?",
            answer="A.",
            user_id=owner,
            course_id=course["id"],
            concept_id=concept.id if concept else None,
            review_count=repetitions,
        )
        db_session.add(card)
        db_session.flush()
        db_session.add(
            FlashcardSRS(
                flashcard_id=card.id,
                user_id=owner,
                efactor=250,
                interval_days=1,
                due_date=today() + timedelta(days=due_in_days),
                repetitions=repetitions,
            )
        )
        db_session.commit()
        return card

    return add


@pytest.fixture
def add_concept(db_session):
    orders = iter(range(100))

    def add(course: dict, name: str) -> Concept:
        [vector] = FakeEmbedder().embed([name])
        concept = Concept(
            course_id=course["id"],
            name=name,
            description=f"{name} as taught.",
            order=next(orders),
            embedding=vector,
            embedding_model=FakeEmbedder.model_name,
        )
        db_session.add(concept)
        db_session.commit()
        return concept

    return add


def get_today(client) -> dict:
    response = client.get("/today")
    assert response.status_code == 200, response.text
    return response.json()


def test_a_new_user_has_nothing_due_and_nothing_suggested(auth_client):
    assert get_today(auth_client) == {"due_count": 0, "courses": [], "suggested": None}


def test_due_cards_are_counted_per_active_course(
    auth_client, other_auth_client, other_user, create_course, add_card
):
    physics = create_course(auth_client, "Physics")
    biology = create_course(auth_client, "biology")
    archived = create_course(auth_client, "Ancient history")
    auth_client.patch(f"/courses/{archived['id']}", json={"archived": True})
    for due_in_days in (-3, 0, 1):
        add_card(physics, due_in_days=due_in_days)
    add_card(biology)
    add_card(archived)
    theirs = create_course(other_auth_client, "Physics")
    add_card(theirs, owner_id=other_user.id)

    overview = get_today(auth_client)

    assert overview["due_count"] == 3
    assert overview["courses"] == [
        {
            "course": {"id": biology["id"], "name": "biology"},
            "due_count": 1,
            "weakest_concepts": [],
        },
        {
            "course": {"id": physics["id"], "name": "Physics"},
            "due_count": 2,
            "weakest_concepts": [],
        },
    ]


def test_the_three_weakest_practiced_concepts_are_shown(
    auth_client, create_course, add_card, add_concept
):
    course = create_course(auth_client)
    add_concept(course, "Unpracticed")
    for repetitions, name in [
        (4, "Mastered"),
        (2, "Half"),
        (0, "New"),
        (3, "Most"),
        (1, "Quarter"),
    ]:
        add_card(
            course,
            due_in_days=1,
            repetitions=repetitions,
            concept=add_concept(course, name),
        )

    [row] = get_today(auth_client)["courses"]

    assert [(c["name"], c["mastery"]) for c in row["weakest_concepts"]] == [
        ("New", 0.0),
        ("Quarter", 0.25),
        ("Half", 0.5),
    ]


def test_the_course_with_the_most_due_cards_is_suggested(
    auth_client, create_course, add_card
):
    light = create_course(auth_client, "Light")
    heavy = create_course(auth_client, "Heavy")
    add_card(light)
    for _ in range(12):
        add_card(heavy)

    assert get_today(auth_client)["suggested"] == {"course_id": heavy["id"], "size": 12}


@pytest.mark.parametrize(("due", "size"), [(1, 10), (25, 20)])
def test_the_suggested_size_is_at_least_ten_and_at_most_twenty(
    auth_client, create_course, add_card, due, size
):
    course = create_course(auth_client)
    for _ in range(due):
        add_card(course)

    assert get_today(auth_client)["suggested"]["size"] == size


def test_with_nothing_due_the_nearest_upcoming_exam_is_suggested(
    auth_client, create_course, add_card
):
    past = create_course(
        auth_client, "Past", exam_date=(today() - timedelta(days=1)).isoformat()
    )
    later = create_course(
        auth_client, "Later", exam_date=(today() + timedelta(days=30)).isoformat()
    )
    sooner = create_course(
        auth_client, "Sooner", exam_date=(today() + timedelta(days=3)).isoformat()
    )
    for course in (past, later, sooner):
        add_card(course, due_in_days=2)

    assert get_today(auth_client)["suggested"] == {
        "course_id": sooner["id"],
        "size": 10,
    }


def test_a_course_without_material_is_never_suggested(
    auth_client, create_course, add_card
):
    create_course(
        auth_client, "Empty", exam_date=(today() + timedelta(days=1)).isoformat()
    )
    stocked = create_course(auth_client, "Stocked")
    add_card(stocked, due_in_days=5)

    assert get_today(auth_client)["suggested"]["course_id"] == stocked["id"]


def test_a_course_with_a_ready_document_can_be_suggested(
    auth_client, create_course, upload_pdf
):
    course = create_course(auth_client)
    upload_pdf(
        auth_client, course["id"], slide_deck([Slide("Cells", ("Cells divide",))])
    )

    assert get_today(auth_client)["suggested"] == {
        "course_id": course["id"],
        "size": 10,
    }


def test_today_needs_a_signed_in_user(client):
    assert client.get("/today").status_code in (401, 403)
