from typing import Literal

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.services.llm import LLMClient, StructuredOutput, complete_structured
from app.services.llm.structured import StructuredResult

JUDGE_PROMPT_VERSION = "judge-v1"
JUDGE_PURPOSE = "eval.judge"
JUDGE_MAX_TOKENS = 16_000
CRITERIA = ("groundedness", "atomicity", "answerability")

JUDGE_SYSTEM_PROMPT = """\
You grade study questions that were generated from course material.
You receive a source chunk, a question, and its answer key.
Score each criterion from 1 to 5 with the rubric below.
Judge only the question and answer key; do not reward style or length.
For each criterion, write your reasoning before you give the score.

Groundedness: are the question's premise and the answer key supported by the source chunk?
5: every claim in the question and the answer is stated in the chunk or follows directly from it.
4: supported, with one minor detail that paraphrases the chunk rather than restating it.
3: the core answer is supported, but the question or answer adds a claim the chunk does not make.
2: the answer depends mainly on knowledge from outside the chunk.
1: the answer contradicts the chunk or cannot be found in it.

Atomicity: does the question test exactly one fact, concept, or step?
5: one fact or idea, and a single short answer is complete.
4: one idea, but the expected answer bundles a closely related detail.
3: two related facts are needed for a complete answer.
2: several facts, or a list of more than three items.
1: a compound question that asks several unrelated things.

Answerability: can a student who studied this material answer it without seeing the chunk?
5: self-contained, unambiguous, with one clearly correct answer.
4: self-contained, with minor ambiguity about the form the answer should take.
3: answerable, but more than one answer could reasonably be accepted.
2: refers to context the student cannot see, such as "this slide", "the figure", or "the example above".
1: ambiguous or unanswerable as written.
"""


class EvalCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    prompt_version: str
    chunk: str
    question: str
    answer: str


class CriterionScore(StructuredOutput):
    reasoning: str
    score: Literal[1, 2, 3, 4, 5]


class JudgeVerdict(StructuredOutput):
    groundedness: CriterionScore
    atomicity: CriterionScore
    answerability: CriterionScore


def judge_message(case: EvalCase) -> str:
    return (
        f"<source_chunk>\n{case.chunk}\n</source_chunk>\n"
        f"<question>\n{case.question}\n</question>\n"
        f"<answer_key>\n{case.answer}\n</answer_key>"
    )


async def judge_case(
    client: LLMClient, db: Session, case: EvalCase
) -> StructuredResult[JudgeVerdict]:
    return await complete_structured(
        client,
        db,
        response_model=JudgeVerdict,
        system=JUDGE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": judge_message(case)}],
        max_tokens=JUDGE_MAX_TOKENS,
        purpose=JUDGE_PURPOSE,
    )
