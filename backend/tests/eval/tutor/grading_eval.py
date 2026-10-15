"""Score the rubric grader against human verdicts on hand-written student answers.

    cd backend
    LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=... PYTHONPATH=. \
        venv/bin/python -m tests.eval.tutor.grading_eval --out results/grading-v1.json
    PYTHONPATH=. venv/bin/python -m tests.eval.tutor.grading_eval --fake --out results/fake.json

The grader runs exactly as in production, including the answers it grades
without a model; agreement is reported exactly, within one step, and as Cohen's kappa.
"""

import argparse
import asyncio
import json
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.flashcard import Flashcard
from app.services.llm import LLMClient, get_llm_client
from app.services.llm.fake_client import FakeLLMClient
from app.services.tutor.grading import (
    GRADING_PROMPT_VERSION,
    GRADING_PURPOSE,
    Verdict,
    grade_answer,
)
from tests.eval.llm.runner import write_results
from tests.eval.tutor import fakes
from tests.eval.tutor.recording import RecordingClient, per_item, usage

GRADING_SET = Path(__file__).with_name("grading_set.jsonl")
ORDINAL = {Verdict.INCORRECT: 0, Verdict.PARTIAL: 1, Verdict.CORRECT: 2}


class GradingCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    kind: Literal["recall", "short_answer"]
    question: str
    reference_answer: str
    excerpt: str
    student_answer: str
    human_verdict: Verdict
    note: str


def load_grading_cases(path: Path = GRADING_SET) -> list[GradingCase]:
    cases = [
        GradingCase.model_validate_json(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]
    ids = [case.id for case in cases]
    if len(set(ids)) != len(ids):
        raise ValueError(f"{path} repeats case ids")
    return cases


def cohen_kappa(pairs: Sequence[tuple[Verdict, Verdict]]) -> float | None:
    """Agreement beyond chance between two raters over the same items."""
    total = len(pairs)
    observed = sum(human == grader for human, grader in pairs) / total
    humans = Counter(human for human, _ in pairs)
    graders = Counter(grader for _, grader in pairs)
    expected = sum(humans[v] * graders[v] for v in Verdict) / total**2
    if expected == 1:
        return None
    return round((observed - expected) / (1 - expected), 3)


async def evaluate(
    client: LLMClient, db: Session, cases: Sequence[GradingCase]
) -> dict[str, Any]:
    recorded = RecordingClient(client)
    rows = []
    for case in cases:
        card = Flashcard(
            question=case.question,
            answer=case.reference_answer,
            excerpt=case.excerpt,
            kind=case.kind,
        )
        calls_before = len(recorded.results)
        grade = await grade_answer(
            db,
            card,
            answer=case.student_answer,
            choice_index=None,
            user_id=None,
            client=recorded,
        )
        rows.append(
            {
                "id": case.id,
                "human": str(case.human_verdict),
                "grader": str(grade.verdict),
                "score": grade.score,
                "quality": grade.quality,
                "feedback": grade.feedback,
                "missing_points": grade.missing_points,
                "graded_by_model": len(recorded.results) > calls_before,
            }
        )

    pairs = [(Verdict(row["human"]), Verdict(row["grader"])) for row in rows]
    spend = usage(recorded.results)
    return {
        "grading_prompt_version": GRADING_PROMPT_VERSION,
        "grader_provider": str(client.provider),
        "grader_model": client.model,
        "case_count": len(rows),
        "exact_agreement": round(sum(h == g for h, g in pairs) / len(pairs), 3),
        "within_one_step": round(
            sum(abs(ORDINAL[h] - ORDINAL[g]) <= 1 for h, g in pairs) / len(pairs), 3
        ),
        "cohen_kappa": cohen_kappa(pairs),
        "confusion": {
            str(human): {
                str(grader): pairs.count((human, grader)) for grader in Verdict
            }
            for human in Verdict
        },
        "usage": spend,
        "list_price_usd_per_model_graded_answer": per_item(
            spend["list_price_usd"], spend["calls"]
        ),
        "cases": rows,
    }


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--fake", action="store_true", help="a lexical-overlap fake instead of a model"
    )
    args = parser.parse_args(argv)

    client = (
        FakeLLMClient({GRADING_PURPOSE: fakes.grader})
        if args.fake
        else get_llm_client()
    )
    with SessionLocal() as db:
        results = asyncio.run(evaluate(client, db, load_grading_cases()))
    write_results(results, args.out)
    print(
        json.dumps(
            {
                key: results[key]
                for key in ("exact_agreement", "within_one_step", "cohen_kappa")
            }
        )
    )


if __name__ == "__main__":
    main()
