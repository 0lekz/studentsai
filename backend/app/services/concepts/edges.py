import uuid
from collections import defaultdict
from collections.abc import Collection, Sequence
from itertools import combinations

from sqlalchemy.orm import Session

from app.config import settings
from app.models.concept import ConceptEdge, ConceptEdgeKind
from app.repositories import concepts as repo
from app.repositories.concepts import Occurrence

SAME_CHUNK_SCORE = 1.0
ADJACENT_CHUNK_SCORE = 0.5
WEIGHT_DECIMALS = 4

Pair = tuple[uuid.UUID, uuid.UUID]
Rank = dict[uuid.UUID, tuple[int, uuid.UUID]]


def _ranks(occurrences: Sequence[Occurrence]) -> Rank:
    return {
        occurrence.concept_id: (occurrence.order, occurrence.concept_id)
        for occurrence in occurrences
    }


def cooccurrence_scores(occurrences: Sequence[Occurrence]) -> dict[Pair, float]:
    """Every candidate prerequisite pair, earlier concept first, with its score.

    A pair scores 1 for every chunk the two concepts share and 0.5 for every
    pair of adjacent chunks of one document that holds one of them each.
    """
    rank = _ranks(occurrences)
    chunks: dict[tuple[uuid.UUID, int], set[uuid.UUID]] = defaultdict(set)
    for occurrence in occurrences:
        chunks[(occurrence.document_id, occurrence.chunk_index)].add(
            occurrence.concept_id
        )

    def earlier_first(a: uuid.UUID, b: uuid.UUID) -> Pair:
        return (a, b) if rank[a] < rank[b] else (b, a)

    scores: dict[Pair, float] = defaultdict(float)
    for (document_id, index), concepts in chunks.items():
        for a, b in combinations(concepts, 2):
            scores[earlier_first(a, b)] += SAME_CHUNK_SCORE
        for a in concepts:
            for b in chunks.get((document_id, index + 1), ()):
                if a != b:
                    scores[earlier_first(a, b)] += ADJACENT_CHUNK_SCORE
    return dict(scores)


def prerequisite_weights(
    occurrences: Sequence[Occurrence], max_incoming: int
) -> dict[Pair, float]:
    """Prerequisite edges, thinned so the map stays readable.

    A concept first seen earlier is a prerequisite of one first seen later when
    both appear in the same chunk or in adjacent chunks of one document. The
    transitive reduction then drops every edge that a longer path already
    implies, and each concept keeps at most `max_incoming` prerequisites, the
    strongest first and the earlier concept on ties. Weights are the
    co-occurrence scores scaled so the strongest kept edge weighs 1.
    """
    rank = _ranks(occurrences)
    scores = cooccurrence_scores(occurrences)
    kept = _strongest_incoming(
        _transitive_reduction(scores, rank), scores, rank, max_incoming
    )
    if not kept:
        return {}
    strongest = max(scores[pair] for pair in kept)
    return {pair: round(scores[pair] / strongest, WEIGHT_DECIMALS) for pair in kept}


def _transitive_reduction(pairs: Collection[Pair], rank: Rank) -> list[Pair]:
    """Drops each edge whose ends a longer path already connects; edges point up in rank, so there are no cycles."""
    successors: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    for source, target in pairs:
        successors[source].append(target)
    nodes = sorted({node for pair in pairs for node in pair}, key=rank.__getitem__)
    bit = {node: 1 << position for position, node in enumerate(nodes)}

    descendants: dict[uuid.UUID, int] = {}
    kept: list[Pair] = []
    for node in reversed(nodes):
        beyond = 0
        for target in successors[node]:
            beyond |= descendants[target]
        kept.extend(
            (node, target) for target in successors[node] if not beyond & bit[target]
        )
        descendants[node] = beyond | sum(bit[target] for target in successors[node])
    return kept


def _strongest_incoming(
    pairs: Collection[Pair], scores: dict[Pair, float], rank: Rank, limit: int
) -> list[Pair]:
    sources: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    for source, target in pairs:
        sources[target].append(source)
    return [
        (source, target)
        for target, candidates in sources.items()
        for source in sorted(
            candidates, key=lambda source: (-scores[(source, target)], rank[source])
        )[:limit]
    ]


def rebuild_edges(db: Session, course_id: uuid.UUID, model_name: str) -> None:
    """Replaces the course's edges; a pair with a prerequisite edge gets no related edge.

    Related edges join concepts whose name embeddings from `model_name` are more
    similar than `concept_related_threshold`, weighted by that similarity. No
    language model is involved.
    """
    prerequisites = prerequisite_weights(
        repo.occurrences(db, course_id), settings.concept_max_prerequisites
    )
    similar = repo.similar_pairs(
        db, course_id, model_name, settings.concept_related_threshold
    )
    related = {
        (pair.source_id, pair.target_id): round(pair.similarity, WEIGHT_DECIMALS)
        for pair in similar
        if (pair.source_id, pair.target_id) not in prerequisites
    }
    repo.replace_edges(
        db,
        course_id,
        [
            *_edges(course_id, ConceptEdgeKind.PREREQUISITE, prerequisites),
            *_edges(course_id, ConceptEdgeKind.RELATED, related),
        ],
    )


def _edges(
    course_id: uuid.UUID, kind: ConceptEdgeKind, weights: dict[Pair, float]
) -> list[ConceptEdge]:
    return [
        ConceptEdge(
            course_id=course_id,
            source_id=source_id,
            target_id=target_id,
            kind=kind.value,
            weight=weight,
        )
        for (source_id, target_id), weight in weights.items()
    ]
