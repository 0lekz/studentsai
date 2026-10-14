"""Splits heading sections into size-capped, overlapping chunks that keep their page range."""

import math
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field

CHARS_PER_TOKEN = 4
MAX_CHUNK_TOKENS = 800
OVERLAP_TOKENS = 80

_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")
_SENTENCE_END = (".", "!", "?", ":", ";")


@dataclass(frozen=True)
class Paragraph:
    text: str
    page: int


@dataclass
class Section:
    heading_path: tuple[str, ...]
    paragraphs: list[Paragraph] = field(default_factory=list)


@dataclass(frozen=True)
class Chunk:
    index: int
    heading_path: list[str]
    page_start: int
    page_end: int
    text: str
    token_estimate: int


@dataclass(frozen=True)
class _Piece:
    text: str
    page: int
    continues_paragraph: bool


def estimate_tokens(text: str) -> int:
    """Approximates tokenizer output for English prose without depending on a tokenizer."""
    return math.ceil(len(text) / CHARS_PER_TOKEN)


def chunk_sections(
    sections: Iterable[Section],
    max_tokens: int = MAX_CHUNK_TOKENS,
    overlap_tokens: int = OVERLAP_TOKENS,
) -> list[Chunk]:
    max_chars = max_tokens * CHARS_PER_TOKEN
    overlap_chars = overlap_tokens * CHARS_PER_TOKEN
    chunks: list[Chunk] = []
    for section in sections:
        pieces = _section_pieces(section.paragraphs, max_chars)
        for group in _pack(pieces, max_chars, overlap_chars):
            text = _join(group)
            chunks.append(
                Chunk(
                    index=len(chunks),
                    heading_path=list(section.heading_path),
                    page_start=min(piece.page for piece in group),
                    page_end=max(piece.page for piece in group),
                    text=text,
                    token_estimate=estimate_tokens(text),
                )
            )
    return chunks


def _section_pieces(paragraphs: list[Paragraph], max_chars: int) -> Iterator[_Piece]:
    previous: Paragraph | None = None
    for paragraph in paragraphs:
        continues = previous is not None and _runs_on(previous, paragraph)
        for position, text in enumerate(_split_to_fit(paragraph.text, max_chars)):
            yield _Piece(text, paragraph.page, continues or position > 0)
        previous = paragraph


def _runs_on(previous: Paragraph, paragraph: Paragraph) -> bool:
    """A paragraph cut by a page or column break resumes mid-sentence in lowercase."""
    return not previous.text.endswith(_SENTENCE_END) and paragraph.text[:1].islower()


def _split_to_fit(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    parts: list[str] = []
    for sentence in _SENTENCE_BREAK.split(text):
        if len(sentence) <= max_chars:
            parts.append(sentence)
        else:
            parts.extend(_split_words(sentence, max_chars))
    return parts


def _split_words(text: str, max_chars: int) -> list[str]:
    parts: list[str] = []
    current = ""
    for word in text.split():
        while len(word) > max_chars:
            if current:
                parts.append(current)
                current = ""
            parts.append(word[:max_chars])
            word = word[max_chars:]
        candidate = f"{current} {word}" if current else word
        if len(candidate) <= max_chars:
            current = candidate
        else:
            parts.append(current)
            current = word
    if current:
        parts.append(current)
    return parts


def _pack(
    pieces: Iterable[_Piece], max_chars: int, overlap_chars: int
) -> Iterator[list[_Piece]]:
    group: list[_Piece] = []
    for piece in pieces:
        if group and len(_join([*group, piece])) > max_chars:
            yield group
            room_for_overlap = max_chars - len(piece.text) - len("\n\n")
            group = _overlap(group, min(overlap_chars, room_for_overlap))
        group.append(piece)
    if group:
        yield group


def _overlap(group: list[_Piece], max_chars: int) -> list[_Piece]:
    """The trailing words of a chunk, repeated at the start of the next one."""
    words: list[str] = []
    length = 0
    page = None
    for piece in reversed(group):
        for word in reversed(piece.text.split()):
            added = len(word) + (1 if words else 0)
            if length + added > max_chars:
                return _overlap_piece(words, page)
            words.append(word)
            length += added
            page = piece.page
    return _overlap_piece(words, page)


def _overlap_piece(words: list[str], page: int | None) -> list[_Piece]:
    if not words or page is None:
        return []
    return [_Piece(" ".join(reversed(words)), page, continues_paragraph=False)]


def _join(pieces: list[_Piece]) -> str:
    text = ""
    for piece in pieces:
        if not text:
            text = piece.text
        else:
            separator = " " if piece.continues_paragraph else "\n\n"
            text = f"{text}{separator}{piece.text}"
    return text
