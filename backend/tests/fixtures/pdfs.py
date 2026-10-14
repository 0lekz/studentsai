"""Builds PDFs in memory with PyMuPDF so the tests never depend on committed binaries."""

import io
from dataclasses import dataclass

import pymupdf

SLIDE_WIDTH = 960
SLIDE_HEIGHT = 540


@dataclass(frozen=True)
class Slide:
    title: str | None = None
    bullets: tuple[str, ...] = ()
    image: bool = False


def slide_deck(slides: list[Slide], footer: str | None = "CS101 - Lecture 4") -> bytes:
    """16:9 slides with a bold title at the top, bullets below, and a footer with the slide number."""
    pdf = pymupdf.open()
    for number, slide in enumerate(slides, 1):
        page = pdf.new_page(width=SLIDE_WIDTH, height=SLIDE_HEIGHT)
        if slide.title:
            page.insert_text((48, 72), slide.title, fontsize=36, fontname="hebo")
        if slide.bullets:
            bullets = "\n".join(f"- {bullet}" for bullet in slide.bullets)
            page.insert_textbox(pymupdf.Rect(48, 110, 912, 480), bullets, fontsize=22)
        if slide.image:
            page.insert_image(pymupdf.Rect(240, 120, 720, 440), pixmap=_gray_square())
        if footer:
            page.insert_text((48, 525), footer, fontsize=11)
            page.insert_text((900, 525), str(number), fontsize=11)
    return pdf.tobytes()


def prose_document(html: str, header: str | None = "BIO 101 - Lecture notes") -> bytes:
    """A4 pages laid out from HTML, so h1, h2 and h3 render larger than body paragraphs."""
    buffer = io.BytesIO()
    writer = pymupdf.DocumentWriter(buffer)
    story = pymupdf.Story(html=html)
    mediabox = pymupdf.paper_rect("a4")
    text_area = pymupdf.Rect(72, 72, mediabox.width - 72, mediabox.height - 72)
    more = True
    while more:
        device = writer.begin_page(mediabox)
        more, _ = story.place(text_area)
        story.draw(device)
        writer.end_page()
    writer.close()

    pdf = pymupdf.open(stream=buffer.getvalue(), filetype="pdf")
    for page in pdf:
        if header:
            page.insert_text((72, 40), header, fontsize=9)
        page.insert_text((290, 810), str(page.number + 1), fontsize=9)
    return pdf.tobytes()


def image_only_document(pages: int = 1) -> bytes:
    pdf = pymupdf.open()
    for _ in range(pages):
        pdf.new_page().insert_image(
            pymupdf.Rect(72, 72, 523, 523), pixmap=_gray_square()
        )
    return pdf.tobytes()


def empty_document() -> bytes:
    pdf = pymupdf.open()
    pdf.new_page()
    return pdf.tobytes()


def encrypted_document() -> bytes:
    pdf = pymupdf.open()
    pdf.new_page().insert_text((72, 72), "Exam answers", fontsize=12)
    return pdf.tobytes(
        encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="user", owner_pw="owner"
    )


def _gray_square() -> pymupdf.Pixmap:
    pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 16, 16), False)
    pixmap.clear_with(180)
    return pixmap
