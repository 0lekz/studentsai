import json
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models import LLMCall
from app.services.llm.fake_client import FakeLLMClient
from tests.eval.llm import runner
from tests.eval.llm.judge import (
    CRITERIA,
    JUDGE_PROMPT_VERSION,
    JUDGE_PURPOSE,
    JUDGE_SYSTEM_PROMPT,
    JudgeVerdict,
)
from tests.eval.llm.runner import SAMPLE_CASES, load_cases


def verdict(*scores: int) -> dict:
    return {
        criterion: {"reasoning": f"{criterion} reasoning", "score": score}
        for criterion, score in zip(CRITERIA, scores, strict=True)
    }


def case_line(**overrides) -> str:
    case = {
        "id": "case-1",
        "prompt_version": "question-v1",
        "chunk": "Mitochondria produce most of a cell's ATP.",
        "question": "Which organelle produces most ATP?",
        "answer": "The mitochondrion.",
    }
    return json.dumps(case | overrides)


class TestLoadCases:
    def test_the_sample_file_holds_one_prompt_version_of_distinct_cases(self):
        cases = load_cases(SAMPLE_CASES)

        assert len(cases) == 5
        assert {case.prompt_version for case in cases} == {"handwritten-v0"}

    def test_blank_lines_are_ignored(self, tmp_path):
        path = tmp_path / "cases.jsonl"
        path.write_text(f"{case_line()}\n\n{case_line(id='case-2')}\n")

        assert [case.id for case in load_cases(path)] == ["case-1", "case-2"]

    @pytest.mark.parametrize(
        ("lines", "message"),
        [
            ([], "has no cases"),
            ([case_line(), "{"], r"cases.jsonl:2"),
            ([case_line(difficulty="easy")], r"cases.jsonl:1"),
            (
                [case_line(), case_line(id="case-2", prompt_version="question-v2")],
                "mixes prompt versions",
            ),
            ([case_line(), case_line()], "repeats case ids"),
        ],
        ids=["empty", "bad-json", "unknown-field", "mixed-versions", "duplicate-ids"],
    )
    def test_malformed_files_are_rejected_with_a_location(
        self, tmp_path, lines, message
    ):
        path = tmp_path / "cases.jsonl"
        path.write_text("\n".join(lines))

        with pytest.raises(ValueError, match=message):
            load_cases(path)


def test_the_judge_asks_for_a_strict_schema_scored_one_to_five():
    schema = JudgeVerdict.model_json_schema()
    criterion = schema["$defs"]["CriterionScore"]

    assert schema["required"] == list(CRITERIA)
    assert schema["additionalProperties"] is False
    assert criterion["required"] == ["reasoning", "score"]
    assert criterion["properties"]["score"]["enum"] == [1, 2, 3, 4, 5]


@pytest.mark.slow
def test_the_cli_scores_the_sample_cases_with_a_fake_judge(
    monkeypatch, db_session, tmp_path, capsys
):
    judge = FakeLLMClient(
        {
            JUDGE_PURPOSE: [
                verdict(5, 5, 5),
                verdict(1, 4, 4),
                verdict(4, 1, 3),
                verdict(5, 4, 2),
                verdict(5, 5, 5),
            ]
        }
    )

    def test_session():
        yield db_session

    monkeypatch.setattr(runner, "get_db", test_session)
    monkeypatch.setattr(runner, "get_llm_client", lambda: judge)
    out = tmp_path / "results" / "handwritten-v0.json"

    runner.main(["--out", str(out)])

    results = json.loads(out.read_text())
    cases = load_cases(SAMPLE_CASES)
    assert results["prompt_version"] == "handwritten-v0"
    assert results["judge_prompt_version"] == JUDGE_PROMPT_VERSION
    assert (results["judge_provider"], results["judge_model"]) == ("fake", "fake")
    assert results["case_count"] == len(cases)
    assert results["means"] == {
        "groundedness": 4.0,
        "atomicity": 3.8,
        "answerability": 3.8,
    }
    assert results["cost_usd"] == 0
    assert [case["id"] for case in results["cases"]] == [case.id for case in cases]
    assert results["cases"][1]["groundedness"] == {
        "reasoning": "groundedness reasoning",
        "score": 1,
    }
    assert json.loads(capsys.readouterr().out) == results["means"]

    for request, case in zip(judge.requests, cases, strict=True):
        assert request.system == JUDGE_SYSTEM_PROMPT
        [prompt] = request.messages
        assert case.chunk in prompt["content"]
        assert case.question in prompt["content"]
        assert case.answer in prompt["content"]
    logged = db_session.scalars(select(LLMCall.purpose)).all()
    assert logged == [JUDGE_PURPOSE] * len(cases)


def test_results_files_are_written_with_missing_directories(tmp_path):
    out = tmp_path / "nested" / "results.json"

    runner.write_results({"means": {}}, out)

    assert json.loads(Path(out).read_text()) == {"means": {}}
