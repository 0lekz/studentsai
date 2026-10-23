"""Score a JSONL file of generated questions with the LLM judge.

    cd backend
    LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=... PYTHONPATH=. \
        venv/bin/python -m tests.eval.llm.runner path/to/cases.jsonl --out results.json

Each line holds one case: id, prompt_version, chunk, question, answer.
"""

import argparse
import asyncio
import json
from collections.abc import Sequence
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from statistics import fmean
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.llm import LLMClient, get_llm_client
from tests.eval.llm.judge import (
    CRITERIA,
    JUDGE_PROMPT_VERSION,
    EvalCase,
    JudgeVerdict,
    judge_case,
)

SAMPLE_CASES = Path(__file__).with_name("cases.sample.jsonl")


def load_cases(path: Path) -> list[EvalCase]:
    """Every case in one file must come from the same generation prompt version."""
    cases = []
    for number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            cases.append(EvalCase.model_validate_json(line))
        except ValidationError as error:
            raise ValueError(f"{path}:{number}: {error}") from error
    if not cases:
        raise ValueError(f"{path} has no cases")
    versions = sorted({case.prompt_version for case in cases})
    if len(versions) > 1:
        raise ValueError(f"{path} mixes prompt versions {versions}")
    ids = [case.id for case in cases]
    if len(set(ids)) != len(ids):
        raise ValueError(f"{path} repeats case ids")
    return cases


async def score_cases(
    client: LLMClient, db: Session, cases: Sequence[EvalCase]
) -> dict[str, Any]:
    verdicts: list[JudgeVerdict] = []
    costs: list[Decimal | None] = []
    for case in cases:
        judged = await judge_case(client, db, case)
        verdicts.append(judged.value)
        costs.append(judged.cost_usd)
    return {
        "prompt_version": cases[0].prompt_version,
        "judge_prompt_version": JUDGE_PROMPT_VERSION,
        "judge_provider": str(client.provider),
        "judge_model": client.model,
        "case_count": len(cases),
        "means": {
            criterion: round(
                fmean(getattr(verdict, criterion).score for verdict in verdicts), 3
            )
            for criterion in CRITERIA
        },
        "cost_usd": None if None in costs else float(sum(costs, Decimal(0))),
        "cases": [
            {"id": case.id, **verdict.model_dump()}
            for case, verdict in zip(cases, verdicts, strict=True)
        ],
    }


def write_results(results: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2) + "\n")


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("cases", type=Path, nargs="?", default=SAMPLE_CASES)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    cases = load_cases(args.cases)
    with contextmanager(get_db)() as db:
        results = asyncio.run(score_cases(get_llm_client(), db, cases))
    write_results(results, args.out)
    print(json.dumps(results["means"]))


if __name__ == "__main__":
    main()
