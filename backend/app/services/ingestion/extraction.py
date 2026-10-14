"""Turns PDF bytes into a heading outline and page-referenced chunks, with no I/O beyond PyMuPDF."""

import re
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field, replace
from itertools import groupby
from operator import attrgetter

import pymupdf

from app.models.document import DocumentKind
from app.services.ingestion.chunking import Chunk, Paragraph, Section, chunk_sections

HEADING_SIZE_RATIO = 1.15
MAX_HEADING_CHARS = 120
MAX_HEADING_LEVELS = 4
SLIDE_TITLE_BAND = 0.3
SLIDE_TITLE_SHARE = 0.6
MARGIN_BAND = 0.1
RUNNING_TEXT_SHARE = 0.6
RUNNING_TEXT_MIN_PAGES = 3

_CONTINUATION_MARK = re.compile(
    r"\s*[(\[]?\s*(?:cont\.?|cont'd|contd\.?|continued)\s*[)\]]?\s*$", re.IGNORECASE
)
_DIGITS = re.compile(r"\d+")
_DOT_LEADER = re.compile(r"(?:\.\s?){4,}")
_CLAUSE_END = (".", ",", ";", ":")
_PAGE_NUMBER = re.compile(r"(?:page\s*)?\d+(?:\s*(?:/|of)\s*\d+)?", re.IGNORECASE)
_LIST_ITEM = re.compile(r"(?:[-*\u2013\u2022\u2023\u25aa\u25e6]|\d{1,2}[.)])\s")


class ExtractionError(Exception):
    """The file yields no usable text: unreadable, password-protected, or image-only."""


@dataclass(frozen=True)
class Line:
    text: str
    size: float
    bold: bool
    top: float
    bottom: float
    block: int


@dataclass(frozen=True)
class Page:
    number: int
    width: float
    height: float
    lines: list[Line]


@dataclass(frozen=True)
class Heading:
    level: int
    title: str
    page: int


@dataclass
class OutlineNode:
    title: str
    level: int
    page: int
    children: list["OutlineNode"] = field(default_factory=list)


@dataclass(frozen=True)
class ExtractionResult:
    kind: DocumentKind
    page_count: int
    outline: list[OutlineNode]
    chunks: list[Chunk]


def extract_document(data: bytes) -> ExtractionResult:
    pages = _strip_running_text(_read_pages(data))
    body_size = _body_size(pages)
    if body_size is None:
        raise ExtractionError(
            "No extractable text found. Scanned or image-only PDFs are not supported yet."
        )
    kind = _detect_kind(pages, body_size)
    elements = (
        list(_slide_elements(pages, body_size))
        if kind is DocumentKind.SLIDES
        else list(_document_elements(pages, body_size))
    )
    headings = [element for element in elements if isinstance(element, Heading)]
    return ExtractionResult(
        kind=kind,
        page_count=len(pages),
        outline=_outline(headings),
        chunks=chunk_sections(_sections(elements)),
    )


def _read_pages(data: bytes) -> list[Page]:
    try:
        pdf = pymupdf.open(stream=data, filetype="pdf")
    except pymupdf.FileDataError as error:
        raise ExtractionError("The file is not a readable PDF.") from error
    with pdf:
        if pdf.needs_pass:
            raise ExtractionError("Password-protected PDFs are not supported.")
        return [_read_page(page) for page in pdf]


def _read_page(page: pymupdf.Page) -> Page:
    lines = []
    content = page.get_text("dict", flags=pymupdf.TEXTFLAGS_TEXT)
    for block_number, block in enumerate(content["blocks"]):
        for line in block.get("lines", []):
            visible = [span for span in line["spans"] if span["text"].strip()]
            if not visible:
                continue
            dominant = max(visible, key=lambda span: len(span["text"].strip()))
            lines.append(
                Line(
                    text=" ".join(
                        "".join(span["text"] for span in line["spans"]).split()
                    ),
                    size=round(dominant["size"] * 2) / 2,
                    bold=all(
                        span["flags"] & pymupdf.TEXT_FONT_BOLD for span in visible
                    ),
                    top=line["bbox"][1],
                    bottom=line["bbox"][3],
                    block=block_number,
                )
            )
    return Page(page.number + 1, page.rect.width, page.rect.height, lines)


def _strip_running_text(pages: list[Page]) -> list[Page]:
    """Drops page numbers, and headers and footers that repeat in the page margins."""
    occurrences = Counter(
        key
        for page in pages
        for key in {_running_key(line) for line in page.lines if _in_margin(line, page)}
    )
    repeated = {
        key
        for key, count in occurrences.items()
        if len(pages) >= RUNNING_TEXT_MIN_PAGES
        and count >= RUNNING_TEXT_SHARE * len(pages)
    }

    def is_running(line: Line, page: Page) -> bool:
        return _in_margin(line, page) and (
            _PAGE_NUMBER.fullmatch(line.text) is not None
            or _running_key(line) in repeated
        )

    return [
        replace(page, lines=[line for line in page.lines if not is_running(line, page)])
        for page in pages
    ]


def _in_margin(line: Line, page: Page) -> bool:
    margin = page.height * MARGIN_BAND
    return line.bottom <= margin or line.top >= page.height - margin


def _running_key(line: Line) -> str:
    return _DIGITS.sub("#", line.text.casefold())


def _body_size(pages: list[Page]) -> float | None:
    """The font size carrying the most characters."""
    weights: Counter[float] = Counter()
    for page in pages:
        for line in page.lines:
            weights[line.size] += len(line.text)
    return weights.most_common(1)[0][0] if weights else None


def _detect_kind(pages: list[Page], body_size: float) -> DocumentKind:
    text_pages = [page for page in pages if page.lines]
    titled = sum(1 for page in text_pages if _slide_title(page, body_size))
    landscape = sum(1 for page in pages if page.width > page.height)
    if landscape * 2 > len(pages) and titled >= SLIDE_TITLE_SHARE * len(text_pages):
        return DocumentKind.SLIDES
    return DocumentKind.PDF


def _slide_title(page: Page, body_size: float) -> list[Line]:
    """The largest text on the page, when it starts near the top and stands out from the body."""
    if not page.lines:
        return []
    largest = max(line.size for line in page.lines)
    first = min(
        (line for line in page.lines if line.size == largest), key=attrgetter("top")
    )
    if (
        largest < body_size * HEADING_SIZE_RATIO
        or first.top > page.height * SLIDE_TITLE_BAND
    ):
        return []
    return [
        line
        for line in page.lines
        if line.block == first.block and line.size == largest
    ]


def _slide_elements(
    pages: list[Page], body_size: float
) -> Iterator[Heading | Paragraph]:
    """One heading per slide title; continuation slides and untitled slides extend the previous one."""
    previous_title = None
    for page in pages:
        title_lines = _slide_title(page, body_size)
        if title_lines:
            full_title = " ".join(line.text for line in title_lines)
            title = _CONTINUATION_MARK.sub("", full_title) or full_title
            if title.casefold() != previous_title:
                yield Heading(1, title, page.number)
                previous_title = title.casefold()
        body = [line for line in page.lines if line not in title_lines]
        for _, block_lines in groupby(body, key=attrgetter("block")):
            yield Paragraph(_join_lines(block_lines), page.number)


def _document_elements(
    pages: list[Page], body_size: float
) -> Iterator[Heading | Paragraph]:
    """Headings are short lines set larger than the body, or bold one-line blocks at body size.

    Distinct heading sizes map to levels, largest first.
    """

    def heading_size(line: Line, alone_in_block: bool) -> float | None:
        if (
            len(line.text) > MAX_HEADING_CHARS
            or _DOT_LEADER.search(line.text)
            or not any(character.isalpha() for character in line.text)
        ):
            return None
        larger = line.size >= body_size * HEADING_SIZE_RATIO
        bold_label = (
            alone_in_block
            and line.bold
            and line.size >= body_size
            and not line.text.endswith(_CLAUSE_END)
        )
        return line.size if larger or bold_label else None

    classified = []
    for page in pages:
        lines_per_block = Counter(line.block for line in page.lines)
        classified.append(
            (
                page.number,
                [
                    (line, heading_size(line, lines_per_block[line.block] == 1))
                    for line in page.lines
                ],
            )
        )
    sizes = sorted(
        {size for _, lines in classified for _, size in lines if size}, reverse=True
    )
    level_of = {
        size: min(rank, MAX_HEADING_LEVELS) for rank, size in enumerate(sizes, 1)
    }
    for page_number, lines in classified:
        grouped = groupby(lines, key=lambda pair: (pair[0].block, pair[1]))
        for (_, size), group in grouped:
            text = _join_lines(line for line, _ in group)
            if size is None:
                yield Paragraph(text, page_number)
            else:
                yield Heading(level_of[size], text, page_number)


def _join_lines(lines: Iterable[Line]) -> str:
    """Rejoins wrapped lines, undoing end-of-line hyphenation and keeping list items on their own lines."""
    text = ""
    for line in lines:
        if not text:
            text = line.text
        elif text.endswith("-") and text[-2:-1].isalpha() and line.text[:1].islower():
            text = text[:-1] + line.text
        elif _LIST_ITEM.match(line.text):
            text = f"{text}\n{line.text}"
        else:
            text = f"{text} {line.text}"
    return text


def _sections(elements: list[Heading | Paragraph]) -> list[Section]:
    path: list[Heading] = []
    sections = [Section(heading_path=())]
    for element in elements:
        if isinstance(element, Heading):
            while path and path[-1].level >= element.level:
                path.pop()
            path.append(element)
            sections.append(Section(tuple(heading.title for heading in path)))
        else:
            sections[-1].paragraphs.append(element)
    return [section for section in sections if section.paragraphs]


def _outline(headings: list[Heading]) -> list[OutlineNode]:
    roots: list[OutlineNode] = []
    open_nodes: list[OutlineNode] = []
    for heading in headings:
        node = OutlineNode(heading.title, heading.level, heading.page)
        while open_nodes and open_nodes[-1].level >= heading.level:
            open_nodes.pop()
        (open_nodes[-1].children if open_nodes else roots).append(node)
        open_nodes.append(node)
    return roots
