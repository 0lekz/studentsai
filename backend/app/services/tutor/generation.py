import hashlib
import math
import random
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from app.models.document import DocumentChunk
from app.models.flashcard import Flashcard, FlashcardKind
from app.repositories import tutor as tutor_repository
from app.services.llm import (
    LLMClient,
    StructuredOutput,
    complete_structured,
    get_llm_client,
)
from app.services.tutor.concept_links import tag_concepts
from app.services.tutor.embeddings import chunk_text
from app.services.tutor.text import quotes, words

QUESTIONS_PROMPT_VERSION = "questions-v1"
QUESTIONS_PURPOSE = "tutor.questions"
QUESTIONS_MAX_TOKENS = 8_000
MIN_CHUNK_TOKENS = 15
TOKENS_PER_QUESTION = 100
MIN_QUESTIONS_PER_CHUNK = 2
MAX_QUESTIONS_PER_CHUNK = 5
MCQ_CHOICES = 4

QUESTIONS_SYSTEM_PROMPT = """\
You write practice questions for a university student from one passage of their course material.
The passage starts with the headings of the section it comes from, when it has any.
The questions are graded against your reference answers, so every question must have one clearly correct answer that the passage supports.

Each question:
- Tests one fact, definition, relationship or step that the passage states. Never test something the passage does not state, even if it is true.
- Makes sense on its own to a student who studied the material but cannot see the passage: never mention "the passage", "the text", "the slide", "the lecture", "the figure" or "the example above"; name the topic instead.
- Uses the course's own terms from the passage.

Fields, in order:
- excerpt: the shortest span of the passage, one to three sentences or bullets, that supports the answer, copied character for character. Do not fix, reorder, shorten mid-sentence or paraphrase it.
- kind: one of
  - recall: asks for a term, name, value or definition; the answer is a few words.
  - short_answer: asks why or how; the answer is one or two sentences.
  - mcq: a question with exactly four choices and one correct.
- prompt: the question.
- reference_answer: the complete correct answer in the passage's terms, at most two sentences.
- choices: for mcq, the four choices. Distractors are plausible to a student who half-knows the material: draw them from other terms, values or ideas in the passage where possible. All four have similar length and grammatical form. Never use joke options, "all of the above" or "none of the above". For recall and short_answer, an empty list.
- correct_choice: for mcq, the 0-based index of the correct choice; otherwise null.

Write at most {max_questions} questions, one per distinct idea worth testing, and mix the three kinds when the passage allows.
Fewer good questions beat padding: a passage with one testable idea gets one question, and two questions never test the same idea.
If the passage has nothing worth testing, such as a title page, an agenda or a reference list, return an empty list.
"""


class GeneratedQuestion(StructuredOutput):
    excerpt: str
    kind: Literal["recall", "short_answer", "mcq"]
    prompt: str
    reference_answer: str
    choices: list[str]
    correct_choice: int | None


class GeneratedQuestions(StructuredOutput):
    questions: list[GeneratedQuestion]


@dataclass(frozen=True)
class QuestionDraft:
    """A generated question that passed validation, ready to store."""

    kind: FlashcardKind
    prompt: str
    answer: str
    excerpt: str
    choices: list[str] | None


def max_questions(chunk: DocumentChunk) -> int:
    by_size = math.ceil(chunk.token_estimate / TOKENS_PER_QUESTION)
    return max(MIN_QUESTIONS_PER_CHUNK, min(MAX_QUESTIONS_PER_CHUNK, by_size))


def questions_message(chunk: DocumentChunk) -> str:
    return f"<passage>\n{chunk_text(chunk.heading_path, chunk.text)}\n</passage>"


async def draft_questions(
    db: Session,
    chunk: DocumentChunk,
    user_id: uuid.UUID | None,
    *,
    client: LLMClient | None = None,
) -> list[QuestionDraft]:
    """One cached structured call per chunk and prompt version; invalid questions are dropped."""
    limit = max_questions(chunk)
    result = await complete_structured(
        client or get_llm_client(),
        db,
        response_model=GeneratedQuestions,
        system=QUESTIONS_SYSTEM_PROMPT.format(max_questions=limit),
        messages=[{"role": "user", "content": questions_message(chunk)}],
        max_tokens=QUESTIONS_MAX_TOKENS,
        purpose=QUESTIONS_PURPOSE,
        user_id=user_id,
        cache_version=QUESTIONS_PROMPT_VERSION,
    )
    drafts = []
    seen: set[str] = set()
    for question in result.value.questions[:limit]:
        draft = validate_question(chunk, question)
        if draft is None or words(draft.prompt) in seen:
            continue
        seen.add(words(draft.prompt))
        drafts.append(draft)
    return drafts


def validate_question(
    chunk: DocumentChunk, question: GeneratedQuestion
) -> QuestionDraft | None:
    """Keep a question only if its excerpt quotes the chunk and a multiple choice question is well formed."""
    prompt = question.prompt.strip()
    answer = question.reference_answer.strip()
    excerpt = question.excerpt.strip()
    if not (
        prompt
        and answer
        and quotes(chunk_text(chunk.heading_path, chunk.text), excerpt)
    ):
        return None
    kind = FlashcardKind(question.kind)
    if kind is not FlashcardKind.MCQ:
        return QuestionDraft(kind, prompt, answer, excerpt, None)

    choices = [choice.strip() for choice in question.choices]
    distinct = {words(choice) for choice in choices}
    if (
        len(choices) != MCQ_CHOICES
        or "" in distinct
        or len(distinct) != MCQ_CHOICES
        or question.correct_choice not in range(MCQ_CHOICES)
    ):
        return None
    correct = choices[question.correct_choice]
    return QuestionDraft(kind, prompt, correct, excerpt, shuffled(choices, prompt))


def shuffled(choices: list[str], prompt: str) -> list[str]:
    """Models favor early positions for the correct choice, so the order is reshuffled, reproducibly per question."""
    seed = int.from_bytes(hashlib.sha256(prompt.encode()).digest()[:8], "big")
    order = list(choices)
    random.Random(seed).shuffle(order)
    return order


async def generate_questions(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
    chunks: Sequence[DocumentChunk],
    count: int,
) -> list[Flashcard]:
    """Generate from `chunks` in order until at least `count` new questions are stored.

    Every valid question of a visited chunk is stored, so the result can exceed
    `count` by the rest of the last chunk's batch. Questions already stored for
    a chunk are skipped, which makes a repeated request free and idempotent.
    The model and embedding calls run first; the duplicate check and the
    writes then run under a per-course lock, so concurrent requests for the
    same chunk cannot both store its questions.
    """
    created: list[Flashcard] = []
    for chunk in chunks:
        if len(created) >= count:
            break
        drafts = await draft_questions(db, chunk, user_id)
        concept_ids = await tag_concepts(
            db, chunk.id, [f"{draft.prompt}\n{draft.answer}" for draft in drafts]
        )

        tutor_repository.lock_course_questions(db, course_id)
        existing = {
            words(prompt)
            for prompt in tutor_repository.chunk_question_prompts(db, user_id, chunk.id)
        }
        created += tutor_repository.add_generated_questions(
            db,
            user_id=user_id,
            course_id=course_id,
            chunk_id=chunk.id,
            prompt_version=QUESTIONS_PROMPT_VERSION,
            questions=[
                tutor_repository.NewQuestion(
                    kind=draft.kind,
                    prompt=draft.prompt,
                    answer=draft.answer,
                    excerpt=draft.excerpt,
                    choices=draft.choices,
                    concept_id=concept_id,
                )
                for draft, concept_id in zip(drafts, concept_ids, strict=True)
                if words(draft.prompt) not in existing
            ],
        )
        tutor_repository.mark_chunk_generated(
            db, chunk.id, QUESTIONS_PROMPT_VERSION, len(drafts)
        )
        db.commit()
    return created
