"""Generate questions from the synthetic corpus and score them with the LLM judge.

    cd backend
    LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=... PYTHONPATH=. \
        venv/bin/python -m tests.eval.tutor.generation_eval --out results/questions-v1.json
    PYTHONPATH=. venv/bin/python -m tests.eval.tutor.generation_eval --fake --out results/fake.json

Each corpus note is one chunk under its title. Generation uses the production
prompt and validation; the judge is the harness in tests/eval/llm.
"""

import argparse
import asyncio
import json
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from statistics import fmean
from typing import Any

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.document import DocumentChunk
from app.services.ingestion.chunking import estimate_tokens
from app.services.llm import LLMClient, get_llm_client
from app.services.llm.fake_client import FakeLLMClient
from app.services.tutor.embeddings import chunk_text
from app.services.tutor.generation import (
    QUESTIONS_PROMPT_VERSION,
    QUESTIONS_PURPOSE,
    QuestionDraft,
    draft_questions,
)
from tests.eval.benchmark import load_corpus
from tests.eval.llm.judge import JUDGE_PURPOSE, EvalCase
from tests.eval.llm.runner import score_cases, write_results
from tests.eval.tutor import fakes
from tests.eval.tutor.recording import RecordingClient, per_item, usage


def corpus_chunks(limit: int | None = None) -> list[tuple[str, DocumentChunk]]:
    """Unsaved chunks, one per corpus note, keyed by the note id."""
    notes = load_corpus().notes[:limit]
    return [
        (
            note.id,
            DocumentChunk(
                heading_path=[note.title],
                page_start=1,
                page_end=1,
                text=note.content,
                token_estimate=estimate_tokens(note.content),
            ),
        )
        for note in notes
    ]


def eval_case(case_id: str, chunk: DocumentChunk, draft: QuestionDraft) -> EvalCase:
    question = draft.prompt
    if draft.choices:
        question += "\nChoices: " + " | ".join(draft.choices)
    return EvalCase(
        id=case_id,
        prompt_version=QUESTIONS_PROMPT_VERSION,
        chunk=chunk_text(chunk.heading_path, chunk.text),
        question=question,
        answer=draft.answer,
    )


async def evaluate(
    generator: LLMClient,
    judge: LLMClient,
    db: Session,
    chunks: Sequence[tuple[str, DocumentChunk]],
) -> dict[str, Any]:
    recorded = RecordingClient(generator)
    cases: list[EvalCase] = []
    kinds: Counter[str] = Counter()
    per_chunk = []
    for note_id, chunk in chunks:
        drafts = await draft_questions(db, chunk, None, client=recorded)
        per_chunk.append(len(drafts))
        kinds.update(str(draft.kind) for draft in drafts)
        cases += [
            eval_case(f"{note_id}-{number}", chunk, draft)
            for number, draft in enumerate(drafts, start=1)
        ]
    if not cases:
        raise ValueError("generation produced no valid questions to judge")

    judged = await score_cases(judge, db, cases)
    generation = usage(recorded.results)
    return {
        "prompt_version": QUESTIONS_PROMPT_VERSION,
        "generator_provider": str(generator.provider),
        "generator_model": generator.model,
        "chunk_count": len(chunks),
        "question_count": len(cases),
        "questions_per_chunk": round(fmean(per_chunk), 3),
        "chunks_without_questions": per_chunk.count(0),
        "kinds": dict(sorted(kinds.items())),
        "means": judged["means"],
        "judge_provider": judged["judge_provider"],
        "judge_model": judged["judge_model"],
        "generation_usage": generation,
        "list_price_usd_per_question": per_item(
            generation["list_price_usd"], len(cases)
        ),
        "judge_cost_usd": judged["cost_usd"],
        "cases": [
            case.model_dump() | scores
            for case, scores in zip(cases, judged["cases"], strict=True)
        ],
    }


def fake_clients() -> tuple[LLMClient, LLMClient]:
    return (
        FakeLLMClient({QUESTIONS_PURPOSE: fakes.question_writer}),
        FakeLLMClient({JUDGE_PURPOSE: fakes.judge}),
    )


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=None, help="first N corpus notes")
    parser.add_argument(
        "--fake", action="store_true", help="heuristic fakes instead of a model"
    )
    args = parser.parse_args(argv)

    generator, judge = (
        fake_clients() if args.fake else (get_llm_client(), get_llm_client())
    )
    with SessionLocal() as db:
        results = asyncio.run(evaluate(generator, judge, db, corpus_chunks(args.limit)))
    write_results(results, args.out)
    print(
        json.dumps(
            {
                "questions": results["question_count"],
                "means": results["means"],
                "list_price_usd_per_question": results["list_price_usd_per_question"],
            }
        )
    )


if __name__ == "__main__":
    main()
