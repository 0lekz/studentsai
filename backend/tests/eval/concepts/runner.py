"""Measure concept extraction and deduplication against the labeled lectures in `labeled.py`.

    cd backend
    PYTHONPATH=. venv/bin/python -m tests.eval.concepts.runner --scripted --embedder fake
    PYTHONPATH=. venv/bin/python -m tests.eval.concepts.runner --scripted
    LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=... PYTHONPATH=. \\
        venv/bin/python -m tests.eval.concepts.runner --out results.json

`--scripted` answers every chunk with the fake client returning the labeled
concepts, which measures the plumbing and the deduplication rather than a model.
The lectures are ingested through the real PDF pipeline into the configured
database inside one transaction that is rolled back at the end.
"""

import argparse
import asyncio
import json
import re
import tempfile
import uuid
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from statistics import fmean
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import engine
from app.models import Concept, ConceptChunk, ConceptEdge, Course, LLMCall, User
from app.models.llm_call import LLMProvider
from app.repositories import concepts as concept_repository
from app.services.concepts.edges import cooccurrence_scores
from app.services.concepts.extraction import (
    PROMPT_VERSION,
    PURPOSE,
    extract_course_concepts,
)
from app.services.embedding_service import Embedder, FakeEmbedder, get_embedder
from app.services.ingestion import DocumentStorage, ingest_pdf
from app.services.llm import DEFAULT_MODELS, LLMClient, get_llm_client
from app.services.llm.client import LLMRequest
from app.services.llm.fake_client import FakeLLMClient
from app.services.llm.pricing import estimate_cost
from tests.eval.concepts.labeled import LABELED_SET, Label, LabeledSet
from tests.fixtures.pdfs import prose_document

MATCH_THRESHOLD = 0.85
UPLOADED = datetime(2026, 9, 1, tzinfo=UTC)
_SECTION = re.compile(r"<section>.* > (?P<heading>[^<]+)</section>")


def scripted_client(labeled: LabeledSet = LABELED_SET) -> FakeLLMClient:
    """A fake that answers each chunk with the concepts labeled for its section."""

    def reply(request: LLMRequest) -> dict[str, Any]:
        found = _SECTION.search(request.messages[0]["content"])
        section = labeled.section(found["heading"]) if found else None
        mentions = section.mentions if section else ()
        return {
            "concepts": [
                {"name": mention.extracted_as, "description": mention.description}
                for mention in mentions
            ]
        }

    return FakeLLMClient({PURPOSE: reply})


def normalize(name: str) -> str:
    words = re.sub(r"[^a-z0-9+]+", " ", name.lower()).split()
    if words and words[0] in ("the", "a", "an"):
        words = words[1:]
    return " ".join(words)


def similarity(predicted: str, label: Label) -> float:
    return max(
        SequenceMatcher(None, normalize(predicted), normalize(spelling)).ratio()
        for spelling in (label.name, *label.aliases)
    )


@dataclass(frozen=True)
class Matching:
    predicted: int
    labels: int
    true_positives: int
    duplicates: int

    @property
    def precision(self) -> float | None:
        return self.true_positives / self.predicted if self.predicted else None

    @property
    def recall(self) -> float | None:
        return self.true_positives / self.labels if self.labels else None


def match(predicted: Sequence[str], labels: Iterable[Label]) -> Matching:
    """Pairs predicted names with labels one to one, best fuzzy score first.

    A predicted name left unpaired because its label was already taken is a
    duplicate: a concept that deduplication should have merged.
    """
    labels = list(labels)
    candidates = sorted(
        (
            (score, index, label.name)
            for index, name in enumerate(predicted)
            for label in labels
            if (score := similarity(name, label)) >= MATCH_THRESHOLD
        ),
        reverse=True,
    )
    paired: set[int] = set()
    taken: set[str] = set()
    for _, index, label in candidates:
        if index not in paired and label not in taken:
            paired.add(index)
            taken.add(label)
    matched_somewhere = {index for _, index, _ in candidates}
    return Matching(
        predicted=len(predicted),
        labels=len(labels),
        true_positives=len(paired),
        duplicates=len(matched_somewhere - paired),
    )


def _micro(matchings: Sequence[Matching]) -> Matching:
    return Matching(
        predicted=sum(m.predicted for m in matchings),
        labels=sum(m.labels for m in matchings),
        true_positives=sum(m.true_positives for m in matchings),
        duplicates=sum(m.duplicates for m in matchings),
    )


def _rounded(value: float | None) -> float | None:
    return None if value is None else round(value, 3)


def _list_price_per_chunk(calls: Sequence[LLMCall]) -> dict[str, Any]:
    """The cost of one chunk's call at each provider's default model, from this run's token counts."""
    if not calls:
        return {}
    input_tokens = round(fmean(call.input_tokens for call in calls))
    output_tokens = round(fmean(call.output_tokens for call in calls))
    prices = {
        model: float(estimate_cost(provider, model, input_tokens, output_tokens))
        for provider, model in DEFAULT_MODELS.items()
        if provider is not LLMProvider.FAKE
    }
    return {
        "mean_input_tokens": input_tokens,
        "mean_output_tokens": output_tokens,
        "usd": prices,
    }


async def evaluate(
    db: Session,
    client: LLMClient,
    embedder: Embedder,
    storage_dir: Path,
    labeled: LabeledSet = LABELED_SET,
) -> dict[str, Any]:
    marker = uuid.uuid4().hex[:12]
    owner = User(
        email=f"concept-eval-{marker}@example.com",
        username=f"concept-eval-{marker}",
        verified=True,
    )
    db.add(owner)
    db.flush()
    course = Course(user_id=owner.id, name=labeled.course_name)
    db.add(course)
    db.commit()

    storage = DocumentStorage(storage_dir)
    lecture_of: dict[uuid.UUID, Any] = {}
    for position, lecture in enumerate(labeled.lectures):
        document = ingest_pdf(
            db,
            storage,
            user_id=owner.id,
            course_id=course.id,
            filename=lecture.filename,
            data=prose_document(lecture.html(), header=None),
        )
        document.created_at = UPLOADED + timedelta(minutes=position)
        lecture_of[document.id] = lecture
    db.commit()

    report = await extract_course_concepts(db, course, client=client, embedder=embedder)

    concepts = list(
        db.scalars(
            select(Concept)
            .where(Concept.course_id == course.id)
            .order_by(Concept.order)
        )
    )
    names_by_document: dict[uuid.UUID, set[str]] = defaultdict(set)
    for name, document_id in db.execute(
        select(Concept.name, ConceptChunk.document_id)
        .join(ConceptChunk, ConceptChunk.concept_id == Concept.id)
        .where(Concept.course_id == course.id)
    ):
        names_by_document[document_id].add(name)

    course_labels = {name for lecture in labeled.lectures for name in lecture.labels}
    overall = match(
        [c.name for c in concepts], [labeled.labels[n] for n in course_labels]
    )
    per_document = _micro(
        [
            match(
                sorted(names_by_document[document_id]),
                [labeled.labels[name] for name in lecture.labels],
            )
            for document_id, lecture in lecture_of.items()
        ]
    )
    edge_counts = dict(
        db.execute(
            select(ConceptEdge.kind, func.count())
            .where(ConceptEdge.course_id == course.id)
            .group_by(ConceptEdge.kind)
        ).all()
    )
    calls = list(
        db.scalars(
            select(LLMCall).where(
                LLMCall.user_id == owner.id, LLMCall.purpose == PURPOSE
            )
        )
    )
    costs = [call.cost_usd for call in calls]
    return {
        "prompt_version": PROMPT_VERSION,
        "provider": str(client.provider),
        "model": client.model,
        "embedder": embedder.model_name,
        "documents": len(labeled.lectures),
        "labels": len(course_labels),
        "concepts": len(concepts),
        "precision": _rounded(overall.precision),
        "recall": _rounded(overall.recall),
        "duplicates": overall.duplicates,
        "document_precision": _rounded(per_document.precision),
        "document_recall": _rounded(per_document.recall),
        "mentions": report.mentions,
        "dedup_rate": _rounded(report.dedup_rate),
        "merged_by_embedding": report.merged_by_embedding,
        "chunks_sent": report.chunks_sent,
        "chunks_too_short": report.chunks_too_short,
        "chunks_failed": report.chunks_failed,
        "prerequisite_candidates": len(
            cooccurrence_scores(concept_repository.occurrences(db, course.id))
        ),
        "prerequisite_edges": edge_counts.get("prerequisite", 0),
        "related_edges": edge_counts.get("related", 0),
        "cost_usd": None if None in costs else float(sum(costs)),
        "list_price_per_chunk": _list_price_per_chunk(calls),
        "concept_names": [concept.name for concept in concepts],
    }


def run(client: LLMClient, embedder: Embedder) -> dict[str, Any]:
    """Evaluates inside a transaction that is rolled back, leaving the database as it was."""
    with tempfile.TemporaryDirectory() as storage_dir, engine.connect() as connection:
        transaction = connection.begin()
        db = Session(bind=connection, join_transaction_mode="create_savepoint")
        try:
            return asyncio.run(evaluate(db, client, embedder, Path(storage_dir)))
        finally:
            db.close()
            transaction.rollback()


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--scripted",
        action="store_true",
        help="answer with the fake client scripted to return the labeled concepts",
    )
    parser.add_argument(
        "--embedder",
        choices=("configured", "fake"),
        default="configured",
        help="the configured embedder (bge-small by default) or the hashed bag of words",
    )
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    client = scripted_client() if args.scripted else get_llm_client()
    embedder = FakeEmbedder() if args.embedder == "fake" else get_embedder()
    results = run(client, embedder)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
