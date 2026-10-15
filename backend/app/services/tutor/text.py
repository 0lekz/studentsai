import re
import unicodedata

_NON_WORD = re.compile(r"[^\w]+")
FALLBACK_EXCERPT_CHARS = 300


def words(text: str) -> str:
    """Lowercase words separated by single spaces, so quoting compares content, not punctuation or layout."""
    folded = unicodedata.normalize("NFKC", text).casefold()
    return _NON_WORD.sub(" ", folded).strip()


def quotes(source: str, excerpt: str) -> bool:
    """Whether `excerpt` is a word-for-word span of `source`, ignoring case, punctuation and line breaks."""
    needle = words(excerpt)
    return bool(needle) and f" {needle} " in f" {words(source)} "


def shorten(text: str, max_chars: int) -> str:
    """Collapse whitespace and cut at a word boundary, marking the cut with an ellipsis."""
    flat = " ".join(text.split())
    if len(flat) <= max_chars:
        return flat
    cut = flat[:max_chars].rsplit(" ", 1)[0] or flat[:max_chars]
    return f"{cut.rstrip(' ,;:')}…"


def fallback_excerpt(chunk_text: str) -> str:
    """The opening of a chunk, shown when no verified quote of it is available."""
    return shorten(chunk_text, FALLBACK_EXCERPT_CHARS)
