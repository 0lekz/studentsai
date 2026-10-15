from collections.abc import Iterable, Sequence

import numpy as np

from app.models.concept import CONCEPT_NAME_MAX_LENGTH, Concept

_TRAILING_PUNCTUATION = ".,;:"


def clean_name(raw: str) -> str | None:
    """Collapses whitespace and drops trailing punctuation; a blank or sentence-length name is rejected."""
    name = " ".join(raw.split()).rstrip(_TRAILING_PUNCTUATION).rstrip()
    if not name or len(name) > CONCEPT_NAME_MAX_LENGTH:
        return None
    return name


def name_key(name: str) -> str:
    """The identity behind the case-insensitive unique index on concept names."""
    return name.lower()


def _unit(vector: Sequence[float]) -> np.ndarray:
    array = np.asarray(vector, dtype=np.float64)
    norm = np.linalg.norm(array)
    return array / norm if norm else array


class ConceptMatcher:
    """Finds the course concept an extracted name refers to.

    A concept with the same name ignoring case wins; otherwise the concept whose
    name embedding is most similar, when the cosine is above `threshold`. The
    earlier concept keeps its name, and the merged spelling is remembered so its
    later mentions match by name.
    """

    def __init__(self, concepts: Iterable[Concept], threshold: float) -> None:
        self.threshold = threshold
        self._by_key: dict[str, Concept] = {}
        self._concepts: list[Concept] = []
        self._vectors: list[np.ndarray] = []
        for concept in concepts:
            self.add(concept)

    @property
    def concepts(self) -> list[Concept]:
        return list(self._concepts)

    def add(self, concept: Concept) -> None:
        self._by_key.setdefault(name_key(concept.name), concept)
        self._concepts.append(concept)
        self._vectors.append(_unit(concept.embedding))

    def by_name(self, name: str) -> Concept | None:
        return self._by_key.get(name_key(name))

    def by_embedding(self, name: str, vector: Sequence[float]) -> Concept | None:
        if not self._concepts:
            return None
        similarities = np.stack(self._vectors) @ _unit(vector)
        best = int(np.argmax(similarities))
        if similarities[best] <= self.threshold:
            return None
        concept = self._concepts[best]
        self._by_key.setdefault(name_key(name), concept)
        return concept
