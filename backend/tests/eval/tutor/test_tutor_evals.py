import json
from collections import Counter

import pytest

from app.services.llm.client import LLMRequest
from app.services.llm.fake_client import FakeLLMClient
from app.services.tutor.generation import QUESTIONS_PROMPT_VERSION, QUESTIONS_PURPOSE
from app.services.tutor.grading import GRADING_PURPOSE, Verdict
from tests.eval.llm.judge import CRITERIA, JUDGE_PURPOSE
from tests.eval.tutor import generation_eval, grading_eval
from tests.eval.tutor.fakes import grader, judge, question_writer
from tests.eval.tutor.generation_eval import corpus_chunks, fake_clients
from tests.eval.tutor.grading_eval import cohen_kappa, load_grading_cases


@pytest.fixture
def session_local(monkeypatch, db_session):
    class TestSession:
        def __enter__(self):
            return db_session

        def __exit__(self, *exc):
            return False

    for module in (generation_eval, grading_eval):
        monkeypatch.setattr(module, "SessionLocal", TestSession)


class TestGenerationEval:
    def test_every_corpus_note_becomes_one_chunk_under_its_title(self):
        chunks = corpus_chunks()

        assert len(chunks) == 105
        note_id, chunk = chunks[0]
        assert note_id == "bio-mitosis"
        assert chunk.heading_path == ["Lec 7 - Mitosis (PMAT)"]
        assert chunk.token_estimate > 0

    async def test_generated_questions_are_judged_and_priced(self, db_session):
        generator, judge_client = fake_clients()

        results = await generation_eval.evaluate(
            generator, judge_client, db_session, corpus_chunks(12)
        )

        assert results["prompt_version"] == QUESTIONS_PROMPT_VERSION
        assert results["chunk_count"] == 12
        assert results["question_count"] == len(results["cases"]) > 12
        assert set(results["kinds"]) <= {"recall", "short_answer", "mcq"}
        assert all(1 <= results["means"][c] <= 5 for c in CRITERIA)
        assert results["generation_usage"]["calls"] == 12
        assert results["generation_usage"]["list_price_model"] == "claude-haiku-5-5"
        assert results["list_price_usd_per_question"] > 0
        assert (
            len(judge_client.requests_for(JUDGE_PURPOSE)) == results["question_count"]
        )
        multiple_choice = [
            c for c in results["cases"] if "\nChoices: " in c["question"]
        ]
        assert len(multiple_choice) == results["kinds"].get("mcq", 0)

    def test_the_cli_writes_results(self, session_local, tmp_path, capsys):
        out = tmp_path / "generation.json"

        generation_eval.main(["--fake", "--limit", "3", "--out", str(out)])

        results = json.loads(out.read_text())
        assert results["chunk_count"] == 3
        printed = json.loads(capsys.readouterr().out)
        assert printed["means"] == results["means"]

    async def test_a_run_without_valid_questions_fails_loudly(self, db_session):
        empty = FakeLLMClient({QUESTIONS_PURPOSE: {"questions": []}})

        with pytest.raises(ValueError, match="no valid questions"):
            await generation_eval.evaluate(empty, empty, db_session, corpus_chunks(1))


class TestGradingEval:
    def test_the_set_has_twenty_answers_across_all_verdicts(self):
        cases = load_grading_cases()

        assert len(cases) == 20
        assert len({case.id for case in cases}) == 20
        verdicts = Counter(case.human_verdict for case in cases)
        assert all(verdicts[verdict] >= 6 for verdict in Verdict)

    def test_repeated_ids_are_rejected(self, tmp_path):
        line = (grading_eval.GRADING_SET.read_text().splitlines()[0]) + "\n"
        path = tmp_path / "set.jsonl"
        path.write_text(line * 2)

        with pytest.raises(ValueError, match="repeats case ids"):
            load_grading_cases(path)

    def test_kappa_is_one_for_perfect_agreement_and_none_without_variation(self):
        c, p, i = Verdict.CORRECT, Verdict.PARTIAL, Verdict.INCORRECT

        assert cohen_kappa([(c, c), (p, p), (i, i)]) == 1.0
        assert cohen_kappa([(c, c), (c, c)]) is None
        assert cohen_kappa([(c, i), (i, c)]) == -1.0

    async def test_the_grader_is_scored_against_human_verdicts(self, db_session):
        client = FakeLLMClient({GRADING_PURPOSE: grader})

        results = await grading_eval.evaluate(client, db_session, load_grading_cases())

        assert results["case_count"] == 20
        assert results["usage"]["calls"] == 20
        assert all(case["graded_by_model"] for case in results["cases"])
        confusion = results["confusion"]
        assert sum(sum(row.values()) for row in confusion.values()) == 20
        agreed = sum(confusion[v][v] for v in confusion)
        assert results["exact_agreement"] == agreed / 20
        assert 0 <= results["within_one_step"] <= 1
        assert results["list_price_usd_per_model_graded_answer"] > 0
        [request, *_] = client.requests_for(GRADING_PURPOSE)
        assert (
            "<student_answer>\nmitochondria\n</student_answer>"
            in request.messages[0]["content"]
        )

    def test_the_cli_writes_results(self, session_local, tmp_path, capsys):
        out = tmp_path / "grading.json"

        grading_eval.main(["--fake", "--out", str(out)])

        results = json.loads(out.read_text())
        assert set(json.loads(capsys.readouterr().out)) == {
            "exact_agreement",
            "within_one_step",
            "cohen_kappa",
        }
        assert results["grader_provider"] == "fake"


class TestFakes:
    def test_the_question_writer_quotes_definition_lines(self):
        request = _request(
            "<passage>\nTopic\n\n- Alpha: one\n- Beta: two\n- Gamma: three\n- Delta: four\n</passage>"
        )

        questions = question_writer(request)["questions"]

        assert [q["kind"] for q in questions] == ["mcq", "recall", "recall"]
        assert questions[0]["choices"] == ["one", "two", "three", "four"]
        assert questions[1]["excerpt"] == "Beta: two"

    def test_the_question_writer_falls_back_to_a_short_answer(self):
        request = _request("<passage>\nTopic\n\nCells divide by mitosis.\n</passage>")

        [question] = question_writer(request)["questions"]

        assert question["kind"] == "short_answer"

    @pytest.mark.parametrize(
        ("question", "answer", "expected"),
        [
            ("What divides?", "Cells divide by mitosis", (5, 5, 5)),
            ("What does this slide show?", "Cells split by mitosis", (3, 5, 2)),
            (
                "What else?",
                "Photosynthesis, respiration, osmosis, diffusion, and growth",
                (1, 2, 5),
            ),
        ],
    )
    def test_the_judge_scores_overlap_length_and_dangling_references(
        self, question, answer, expected
    ):
        request = _request(
            "<source_chunk>\nCells divide by mitosis.\n</source_chunk>\n"
            f"<question>\n{question}\n</question>\n<answer_key>\n{answer}\n</answer_key>"
        )

        verdict = judge(request)

        assert tuple(verdict[c]["score"] for c in CRITERIA) == expected


def _request(content: str) -> LLMRequest:
    return LLMRequest(
        system="",
        messages=({"role": "user", "content": content},),
        max_tokens=1,
        temperature=None,
        json_schema=None,
        purpose="eval",
        user_id=None,
    )
