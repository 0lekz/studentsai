"""Grounded answers from the course material through the API."""

import re

import pytest
from sqlalchemy import select

from app.config import settings
from app.models import DocumentChunk
from app.services.llm import LLMUnavailableError
from app.services.tutor.ask import ASK_PURPOSE, NOT_COVERED_ANSWER
from tests.fixtures.pdfs import Slide, slide_deck

DECK = [
    Slide(
        "Merge sort",
        (
            "Merge sort splits the list into two halves and sorts each half recursively",
            "It performs O(n log n) comparisons in the worst case",
        ),
    ),
    Slide(
        "Quicksort",
        (
            "Quicksort partitions the list around a pivot element",
            "Its worst case running time is quadratic",
        ),
    ),
]


@pytest.fixture(scope="module")
def deck_pdf() -> bytes:
    return slide_deck(DECK)


@pytest.fixture
def course(auth_client, create_course) -> dict:
    return create_course(auth_client, "Algorithms")


@pytest.fixture
def document(auth_client, course, upload_pdf, deck_pdf) -> dict:
    return upload_pdf(auth_client, course["id"], deck_pdf, "week-3.pdf")


@pytest.fixture
def lexical_floor(monkeypatch):
    """The fake embedder is a bag of words, so a related question scores far below a real model."""
    monkeypatch.setattr(settings, "ask_min_similarity", 0.1)


def ask(client, course: dict, question: str):
    return client.post(f"/courses/{course['id']}/ask", json={"question": question})


def cite_quicksort_then_merge_sort(request) -> dict:
    """Cites by whatever numbers retrieval gave the two slides, plus a source that was never retrieved."""
    content = request.messages[0]["content"]
    quick, merge = (
        int(re.search(rf'<source number="(\d)"[^>]*section="{name}"', content)[1])
        for name in ("Quicksort", "Merge sort")
    )
    return {
        "covered": True,
        "answer": f"Quicksort partitions around a pivot [{quick}]; merge sort splits [{merge}][9].",
        "citations": [
            {"source": quick, "excerpt": "partitions the list around a pivot"},
            {"source": merge, "excerpt": "splits the list into two halves"},
            {"source": 9, "excerpt": "made up"},
        ],
    }


def test_the_answer_cites_only_retrieved_chunks_numbered_in_order_of_use(
    auth_client, course, document, tutor_llm, lexical_floor, db_session
):
    tutor_llm({ASK_PURPOSE: cite_quicksort_then_merge_sort})

    response = ask(
        auth_client, course, "How do quicksort and merge sort split the list?"
    )

    assert response.status_code == 200, response.text
    body = response.json()
    chunks = {
        chunk.index: chunk
        for chunk in db_session.scalars(
            select(DocumentChunk).where(DocumentChunk.document_id == document["id"])
        )
    }
    assert body["answer"] == (
        "Quicksort partitions around a pivot [1]; merge sort splits [2]."
    )
    assert body["covered"] is True
    assert body["citations"] == [
        {
            "document_id": document["id"],
            "filename": "week-3.pdf",
            "chunk_id": str(chunks[1].id),
            "page_start": 2,
            "page_end": 2,
            "excerpt": "partitions the list around a pivot",
        },
        {
            "document_id": document["id"],
            "filename": "week-3.pdf",
            "chunk_id": str(chunks[0].id),
            "page_start": 1,
            "page_end": 1,
            "excerpt": "splits the list into two halves",
        },
    ]


def test_a_question_the_material_does_not_cover_is_answered_without_a_model(
    auth_client, course, document, tutor_llm
):
    llm = tutor_llm()

    response = ask(auth_client, course, "Who painted the Mona Lisa?")

    assert response.json() == {
        "answer": NOT_COVERED_ANSWER,
        "covered": False,
        "citations": [],
    }
    assert llm.requests == []


def test_a_course_without_material_is_not_covered(auth_client, course, tutor_llm):
    llm = tutor_llm()

    body = ask(auth_client, course, "What is merge sort?").json()
    assert (body["covered"], body["citations"]) == (False, [])
    assert llm.requests == []


@pytest.mark.parametrize("question", ["", "   ", "x" * 2001])
def test_blank_and_oversized_questions_are_rejected(auth_client, course, question):
    assert ask(auth_client, course, question).status_code == 422


def test_another_users_course_is_not_found(other_auth_client, course):
    assert ask(other_auth_client, course, "What is merge sort?").status_code == 404


def test_a_model_outage_is_a_503(
    auth_client, course, document, tutor_llm, lexical_floor
):
    def outage(request):
        raise LLMUnavailableError("overloaded")

    tutor_llm({ASK_PURPOSE: outage})

    assert (
        ask(auth_client, course, "How does merge sort split the list?").status_code
        == 503
    )


def test_retrieved_material_that_does_not_answer_is_not_covered(
    auth_client, course, document, tutor_llm, lexical_floor
):
    tutor_llm(
        {
            ASK_PURPOSE: {
                "covered": False,
                "answer": "Your slides cover sorting but not its history.",
                "citations": [],
            }
        }
    )

    body = ask(auth_client, course, "Who invented merge sort?").json()

    assert body == {
        "answer": "Your slides cover sorting but not its history.",
        "covered": False,
        "citations": [],
    }
