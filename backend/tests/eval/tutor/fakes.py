"""Deterministic stand-ins for the model, so the evals run end to end without keys.

They are heuristics, not graders: the numbers they produce prove the plumbing
and give a lexical floor that a real model must beat, nothing more.
"""

import re

from app.services.llm.client import LLMRequest
from app.services.tutor.text import quotes, words

_DEFINITION = re.compile(
    r"^(?P<term>[^:=]{2,60}?)\s*(?::|=|->| - )\s*(?P<definition>.{3,})$"
)
_DANGLING = re.compile(r"\b(this slide|the passage|the text|the figure|above)\b", re.I)
_STOPWORDS = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "so",
        "that",
        "the",
        "their",
        "them",
        "they",
        "this",
        "to",
        "was",
        "were",
        "when",
        "which",
        "with",
    ]
)


def _tag(content: str, name: str) -> str:
    match = re.search(rf"<{name}>\n(.*?)\n</{name}>", content, re.S)
    return match[1] if match else ""


def question_writer(request: LLMRequest) -> dict:
    """From "term: definition" lines: a multiple choice when there are four, then recall; otherwise one short answer."""
    passage = _tag(request.messages[0]["content"], "passage")
    topic, _, body = passage.partition("\n\n")
    lines = [
        line.strip().removeprefix("- ") for line in body.splitlines() if line.strip()
    ]
    definitions = [
        (m["term"].strip(), m["definition"].strip(), line)
        for line in lines
        if (m := _DEFINITION.match(line))
    ]

    questions = []
    if len(definitions) >= 4:
        term, definition, line = definitions[0]
        questions.append(
            {
                "excerpt": line,
                "kind": "mcq",
                "prompt": f"In {topic}, which describes {term}?",
                "reference_answer": definition,
                "choices": [definition] + [other for _, other, _ in definitions[1:4]],
                "correct_choice": 0,
            }
        )
    questions += [
        {
            "excerpt": line,
            "kind": "recall",
            "prompt": f"In {topic}, what is meant by {term}?",
            "reference_answer": definition,
            "choices": [],
            "correct_choice": None,
        }
        for term, definition, line in (
            definitions[1:3] if questions else definitions[:2]
        )
    ]
    if not questions and lines:
        questions.append(
            {
                "excerpt": lines[0],
                "kind": "short_answer",
                "prompt": f"In {topic}, what does the course say about {' '.join(lines[0].split()[:4])}?",
                "reference_answer": lines[0],
                "choices": [],
                "correct_choice": None,
            }
        )
    return {"questions": questions}


def judge(request: LLMRequest) -> dict:
    """Groundedness from word overlap with the chunk, atomicity from answer length, answerability from dangling references."""
    content = request.messages[0]["content"]
    chunk, question, answer = (
        _tag(content, name) for name in ("source_chunk", "question", "answer_key")
    )
    answer_words = _content_words(answer)
    overlap = len(answer_words & _content_words(chunk)) / max(1, len(answer_words))
    if quotes(chunk, answer):
        groundedness = 5
    elif overlap >= 0.8:
        groundedness = 4
    elif overlap >= 0.5:
        groundedness = 3
    else:
        groundedness = 1
    length = len(answer.split())
    atomicity = 5 if length <= 12 else 4 if length <= 25 else 3
    if answer.count(",") + answer.count(";") >= 3:
        atomicity = 2
    answerability = 2 if _DANGLING.search(question) else 5
    return {
        name: {"reasoning": f"heuristic {name}", "score": score}
        for name, score in (
            ("groundedness", groundedness),
            ("atomicity", atomicity),
            ("answerability", answerability),
        )
    }


def grader(request: LLMRequest) -> dict:
    """Correct, partial or incorrect by the share of the reference answer's content words the student used."""
    content = request.messages[0]["content"]
    reference = _content_words(_tag(content, "reference_answer"))
    student = _content_words(_tag(content, "student_answer"))
    missing = sorted(reference - student)
    share = 1 - len(missing) / max(1, len(reference))
    if share >= 0.6:
        verdict, score, quality = "correct", round(80 + 20 * share), 4
    elif share >= 0.3:
        verdict, score, quality = "partial", round(30 + 49 * share), 3
    else:
        verdict, score, quality = "incorrect", round(29 * share), 1
    return {
        "missing_points": missing,
        "feedback": f"You used {len(reference) - len(missing)} of {len(reference)} key words. Missing: {', '.join(missing) or 'nothing'}.",
        "verdict": verdict,
        "score": score,
        "quality": quality,
    }


def _content_words(text: str) -> set[str]:
    return {word for word in words(text).split() if word not in _STOPWORDS}
