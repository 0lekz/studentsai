import math
from itertools import pairwise

import pymupdf
import pytest

from app.models.document import DocumentKind
from app.services.ingestion import ExtractionError, extract_document
from app.services.ingestion.chunking import (
    CHARS_PER_TOKEN,
    MAX_CHUNK_TOKENS,
    Paragraph,
    Section,
    chunk_sections,
)
from tests.fixtures.pdfs import (
    Slide,
    empty_document,
    encrypted_document,
    image_only_document,
    prose_document,
    slide_deck,
)

DECK = [
    Slide("Shortest paths"),
    Slide(
        "Dijkstra's algorithm",
        ("Greedy shortest paths from one source", "Requires non-negative weights"),
    ),
    Slide(
        "Dijkstra's algorithm (cont.)",
        ("Priority queue keyed by tentative distance", "O((V + E) log V) with a heap"),
    ),
    Slide(image=True),
    Slide("Bellman-Ford", ("Handles negative weights", "Detects negative cycles")),
]

PHOTOSYNTHESIS_SENTENCES = [
    f"Sentence {n} explains how chloroplasts capture light for the plant."
    for n in range(1, 111)
]


def paragraphs(sentences: list[str], per_paragraph: int) -> str:
    return "".join(
        f"<p>{' '.join(sentences[start : start + per_paragraph])}</p>"
        for start in range(0, len(sentences), per_paragraph)
    )


PROSE_HTML = f"""
<h1>Plant biology</h1>
<p>Lecture notes for week 3.</p>
<h2>1. Photosynthesis</h2>
{paragraphs(PHOTOSYNTHESIS_SENTENCES, 12)}
<h3>1.1 Light reactions</h3>
<p>Light reactions happen in the thylakoid membranes.</p>
<h2>2. Respiration</h2>
<p>Respiration releases the energy stored in glucose.</p>
"""


@pytest.fixture(scope="module")
def deck():
    return extract_document(slide_deck(DECK))


@pytest.fixture(scope="module")
def prose():
    return extract_document(prose_document(PROSE_HTML))


def outline_shape(nodes) -> list:
    return [
        (node.title, node.level, node.page, outline_shape(node.children))
        for node in nodes
    ]


def chunk_text(result) -> str:
    return "\n".join(chunk.text for chunk in result.chunks)


def test_slide_deck_is_detected_as_slides(deck):
    assert deck.kind is DocumentKind.SLIDES
    assert deck.page_count == 5


def test_slide_titles_form_a_flat_outline_and_continuation_slides_merge(deck):
    assert outline_shape(deck.outline) == [
        ("Shortest paths", 1, 1, []),
        ("Dijkstra's algorithm", 1, 2, []),
        ("Bellman-Ford", 1, 5, []),
    ]


def test_slide_chunks_span_continued_slides_and_skip_the_image_only_slide(deck):
    assert [
        (chunk.index, chunk.heading_path, chunk.page_start, chunk.page_end)
        for chunk in deck.chunks
    ] == [
        (0, ["Dijkstra's algorithm"], 2, 3),
        (1, ["Bellman-Ford"], 5, 5),
    ]
    assert deck.chunks[0].text == (
        "- Greedy shortest paths from one source\n"
        "- Requires non-negative weights\n\n"
        "- Priority queue keyed by tentative distance\n"
        "- O((V + E) log V) with a heap"
    )


def test_slide_footer_and_numbers_are_not_part_of_the_text(deck):
    text = chunk_text(deck)

    assert "CS101" not in text
    assert all(not line.strip().isdigit() for line in text.splitlines())


def test_slide_titles_are_not_repeated_in_chunk_text(deck):
    assert "Dijkstra" not in chunk_text(deck)


def test_prose_is_detected_as_a_pdf_with_three_pages(prose):
    assert prose.kind is DocumentKind.PDF
    assert prose.page_count == 3


def test_prose_heading_sizes_become_a_nested_outline(prose):
    assert outline_shape(prose.outline) == [
        (
            "Plant biology",
            1,
            1,
            [
                ("1. Photosynthesis", 2, 1, [("1.1 Light reactions", 3, 3, [])]),
                ("2. Respiration", 2, 3, []),
            ],
        )
    ]


def test_prose_chunks_follow_the_heading_path(prose):
    paths = [chunk.heading_path for chunk in prose.chunks]

    assert paths[0] == ["Plant biology"]
    assert prose.chunks[0].text == "Lecture notes for week 3."
    assert paths[-2:] == [
        ["Plant biology", "1. Photosynthesis", "1.1 Light reactions"],
        ["Plant biology", "2. Respiration"],
    ]
    assert prose.chunks[-1].text == "Respiration releases the energy stored in glucose."


def test_a_long_section_is_split_under_the_cap_with_page_ranges(prose):
    section = [
        chunk
        for chunk in prose.chunks
        if chunk.heading_path == ["Plant biology", "1. Photosynthesis"]
    ]

    assert len(section) >= 2
    assert all(chunk.token_estimate <= MAX_CHUNK_TOKENS for chunk in section)
    assert section[0].page_start == 1
    assert section[-1].page_end == 3
    assert all(
        earlier.page_end <= later.page_end for earlier, later in pairwise(section)
    )


def test_split_chunks_overlap_and_keep_every_sentence_in_order(prose):
    section = [
        chunk.text
        for chunk in prose.chunks
        if chunk.heading_path == ["Plant biology", "1. Photosynthesis"]
    ]

    for earlier, later in pairwise(section):
        assert later[:40] in earlier
    joined = " ".join(section)
    positions = [joined.find(sentence) for sentence in PHOTOSYNTHESIS_SENTENCES]
    assert -1 not in positions
    assert positions == sorted(positions)


def test_repeated_running_header_and_page_numbers_are_removed(prose):
    text = chunk_text(prose)

    assert "BIO 101" not in text
    assert all(not line.strip().isdigit() for line in text.splitlines())


def test_page_number_is_removed_even_from_a_single_page():
    result = extract_document(
        prose_document("<p>Only one paragraph here.</p>", header=None)
    )

    assert [chunk.text for chunk in result.chunks] == ["Only one paragraph here."]


def test_a_portrait_page_with_a_large_title_is_not_a_slide_deck():
    result = extract_document(
        prose_document("<h1>Exam checklist</h1><p>Bring a pencil.</p>", header=None)
    )

    assert result.kind is DocumentKind.PDF
    assert outline_shape(result.outline) == [("Exam checklist", 1, 1, [])]


def test_landscape_pages_without_titles_are_not_a_slide_deck():
    result = extract_document(slide_deck([Slide(bullets=("One point",))] * 3))

    assert result.kind is DocumentKind.PDF
    assert result.outline == []


def test_bold_standalone_line_at_body_size_is_a_heading_but_a_label_is_not():
    result = extract_document(
        prose_document(
            "<h1>Genetics</h1>"
            "<p><b>Key terms</b></p><p>Alleles are variants of a gene.</p>"
            "<p><b>Remember:</b></p><p>Dominant alleles mask recessive ones.</p>",
            header=None,
        )
    )

    assert outline_shape(result.outline) == [
        ("Genetics", 1, 1, [("Key terms", 2, 1, [])])
    ]
    assert result.chunks[-1].text.startswith("Alleles are variants of a gene.")
    assert "Remember:" in result.chunks[-1].text


def test_table_of_contents_lines_with_dot_leaders_are_not_headings():
    result = extract_document(
        prose_document(
            "<h1>Contents</h1><h2>Introduction . . . . . . . 3</h2><p>Body text.</p>",
            header=None,
        )
    )

    assert outline_shape(result.outline) == [("Contents", 1, 1, [])]


def test_wrapped_lines_are_rejoined_and_hyphenation_is_undone():
    pdf = pymupdf.open()
    pdf.new_page().insert_textbox(
        pymupdf.Rect(72, 72, 523, 300),
        "Plants rely on photo-\nsynthesis to make sugar\nfrom light.",
        fontsize=12,
    )

    result = extract_document(pdf.tobytes())

    assert [chunk.text for chunk in result.chunks] == [
        "Plants rely on photosynthesis to make sugar from light."
    ]


def test_whitespace_only_lines_are_ignored():
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Mitochondria make ATP.", fontsize=12)
    page.insert_text((72, 120), "      ", fontsize=12)

    result = extract_document(pdf.tobytes())

    assert [chunk.text for chunk in result.chunks] == ["Mitochondria make ATP."]


@pytest.mark.parametrize(
    ("data", "reason"),
    [
        (image_only_document(), "No extractable text"),
        (empty_document(), "No extractable text"),
        (b"%PDF-1.7\nnot really a pdf", "not a readable PDF"),
        (b"", "not a readable PDF"),
        (encrypted_document(), "Password-protected"),
    ],
    ids=["image-only", "empty-page", "corrupt", "zero-bytes", "encrypted"],
)
def test_files_without_usable_text_raise_extraction_error(data, reason):
    with pytest.raises(ExtractionError, match=reason):
        extract_document(data)


def section(path: tuple[str, ...], *texts: str, page: int = 1) -> Section:
    return Section(path, [Paragraph(text, page) for text in texts])


def test_short_section_becomes_one_chunk_with_a_token_estimate():
    [chunk] = chunk_sections([section(("Intro",), "Cells are small.", page=4)])

    assert chunk.heading_path == ["Intro"]
    assert (chunk.page_start, chunk.page_end) == (4, 4)
    assert chunk.text == "Cells are small."
    assert chunk.token_estimate == math.ceil(len("Cells are small.") / CHARS_PER_TOKEN)


def test_chunks_break_at_paragraphs_and_carry_overlap_from_the_previous_chunk():
    first = "Alpha beta gamma delta epsilon zeta eta theta iota kappa."
    second = "Lambda mu nu xi omicron pi rho sigma tau upsilon phi."

    chunks = chunk_sections(
        [section((), first, second)], max_tokens=20, overlap_tokens=4
    )

    assert [chunk.text for chunk in chunks] == [first, f"iota kappa.\n\n{second}"]


def test_paragraph_cut_by_a_page_break_rejoins_with_a_space():
    [chunk] = chunk_sections(
        [
            Section(
                (),
                [
                    Paragraph("The membrane is", 1),
                    Paragraph("selectively permeable.", 2),
                ],
            )
        ]
    )

    assert chunk.text == "The membrane is selectively permeable."
    assert (chunk.page_start, chunk.page_end) == (1, 2)


def test_paragraph_over_the_cap_is_split_between_sentences():
    sentences = [f"Fact number {n} is short." for n in range(1, 9)]

    chunks = chunk_sections(
        [section((), " ".join(sentences))], max_tokens=20, overlap_tokens=0
    )

    assert [chunk.text for chunk in chunks] == [
        " ".join(sentences[0:3]),
        " ".join(sentences[3:6]),
        " ".join(sentences[6:8]),
    ]


def test_a_chunk_shorter_than_the_overlap_is_carried_over_whole():
    chunks = chunk_sections(
        [section((), "Ab.", "Cd.", "Y" * 71)], max_tokens=20, overlap_tokens=20
    )

    assert [chunk.text for chunk in chunks] == ["Ab.\n\nCd.", "Ab. Cd.\n\n" + "Y" * 71]


def test_long_paragraph_without_sentences_is_split_on_words_under_the_cap():
    words = " ".join(f"word{n}" for n in range(60))

    chunks = chunk_sections([section((), words)], max_tokens=20, overlap_tokens=3)

    assert len(chunks) > 1
    assert all(len(chunk.text) <= 20 * CHARS_PER_TOKEN for chunk in chunks)
    assert chunks[0].text.startswith("word0 ")
    assert chunks[-1].text.endswith(" word59")


def test_unbreakable_text_is_cut_at_the_cap():
    text = "See " + "x" * 200

    chunks = chunk_sections([section((), text)], max_tokens=20, overlap_tokens=0)

    assert [chunk.text for chunk in chunks] == ["See", "x" * 80, "x" * 80, "x" * 40]


def test_overlap_never_crosses_a_heading_and_indexes_continue_across_sections():
    chunks = chunk_sections(
        [section(("A",), "First section text."), section(("B",), "Second section.")],
        max_tokens=20,
        overlap_tokens=4,
    )

    assert [(chunk.index, chunk.heading_path, chunk.text) for chunk in chunks] == [
        (0, ["A"], "First section text."),
        (1, ["B"], "Second section."),
    ]


def test_sections_without_paragraphs_produce_no_chunks():
    assert chunk_sections([Section(("Empty",))]) == []
