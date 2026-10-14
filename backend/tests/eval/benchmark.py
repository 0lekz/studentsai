"""Note-similarity benchmark: the production TF-IDF baseline against local embedding models.

Run from backend/: venv/bin/python -m tests.eval.benchmark
It loads the real models (downloading them on first use) and rewrites tests/eval/RESULTS.md.
"""

import datetime
import os
import platform
import statistics
import subprocess
import time
import tomllib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path

import numpy as np

from app.ai_service import ai_service
from app.config import settings
from app.services.embedding_service import FastEmbedEmbedder, note_text

EVAL_DIR = Path(__file__).parent
CORPUS_DIR = EVAL_DIR / "corpus"
RESULTS_PATH = EVAL_DIR / "RESULTS.md"
COMMAND = "cd backend && venv/bin/python -m tests.eval.benchmark"
KS = (1, 3, 5)
PAIR_WINDOW = 5
TFIDF_GRAPH_THRESHOLD = 0.6
THRESHOLD_GRID = tuple(round(0.2 + step / 100, 2) for step in range(76))
PRODUCTION_SWEEP = (0.55, 0.6, 0.65, 0.7, 0.75, 0.8)
BOOTSTRAP_RESAMPLES = 10_000
COMPARISON_MODELS = ("sentence-transformers/all-MiniLM-L6-v2",)


@dataclass(frozen=True)
class CorpusNote:
    id: str
    subject: str
    topic: str
    title: str
    content: str


@dataclass(frozen=True)
class Corpus:
    notes: list[CorpusNote]
    synonymy: list[tuple[str, str]]
    near_miss: list[tuple[str, str]]

    @property
    def topics(self) -> list[str]:
        return [note.topic for note in self.notes]

    def position(self, note_id: str) -> int:
        return next(i for i, note in enumerate(self.notes) if note.id == note_id)


def load_corpus(directory: Path = CORPUS_DIR) -> Corpus:
    notes = []
    for path in sorted(directory.glob("*.toml")):
        if path.name == "pairs.toml":
            continue
        subject_file = tomllib.loads(path.read_text())
        subject = subject_file["subject"]
        notes.extend(
            CorpusNote(
                id=note["id"],
                subject=subject,
                topic=f"{subject}/{note['topic']}",
                title=note["title"],
                content=note["content"].strip(),
            )
            for note in subject_file["notes"]
        )
    pairs = tomllib.loads((directory / "pairs.toml").read_text())
    return Corpus(
        notes=notes,
        synonymy=[(a, b) for a, b in pairs["synonymy"]],
        near_miss=[(a, b) for a, b in pairs["near_miss"]],
    )


def rank_neighbours(similarity: np.ndarray, seed: int = 0) -> np.ndarray:
    """Row i holds every other note, most similar to note i first.

    Ties are broken in a fixed random order, because corpus order groups notes by
    topic and would otherwise hand tied scores (TF-IDF's many exact zeros) to
    same-topic neighbours for free.
    """
    scores = np.array(similarity, dtype=float)
    np.fill_diagonal(scores, -np.inf)
    tiebreak = np.random.default_rng(seed).permutation(len(scores))
    order = np.lexsort((np.broadcast_to(tiebreak, scores.shape), -scores), axis=-1)
    return order[:, :-1]


@dataclass(frozen=True)
class RetrievalScores:
    per_query_precision: dict[int, np.ndarray]
    per_query_recall: dict[int, np.ndarray]

    @property
    def precision(self) -> dict[int, float]:
        return {k: float(np.mean(v)) for k, v in self.per_query_precision.items()}

    @property
    def recall(self) -> dict[int, float]:
        return {k: float(np.mean(v)) for k, v in self.per_query_recall.items()}


def retrieval_scores(
    neighbours: np.ndarray, topics: Sequence[str], ks: Sequence[int] = KS
) -> RetrievalScores:
    """Precision@k and recall@k per query, where a neighbour is relevant when it shares the query's topic."""
    precision: dict[int, list[float]] = {k: [] for k in ks}
    recall: dict[int, list[float]] = {k: [] for k in ks}
    for query, ranked in enumerate(neighbours):
        relevant = {
            other
            for other, topic in enumerate(topics)
            if topic == topics[query] and other != query
        }
        for k in ks:
            hits = sum(1 for other in ranked[:k] if other in relevant)
            precision[k].append(hits / k)
            recall[k].append(hits / len(relevant))
    return RetrievalScores(
        per_query_precision={k: np.array(v) for k, v in precision.items()},
        per_query_recall={k: np.array(v) for k, v in recall.items()},
    )


def bootstrap_interval(
    gains: np.ndarray, resamples: int = BOOTSTRAP_RESAMPLES, seed: int = 0
) -> tuple[float, float]:
    """95% interval of the mean per-query gain, resampling queries with replacement."""
    rng = np.random.default_rng(seed)
    means = rng.choice(gains, size=(resamples, len(gains))).mean(axis=1)
    low, high = np.percentile(means, [2.5, 97.5])
    return float(low), float(high)


def same_topic_matrix(topics: Sequence[str]) -> np.ndarray:
    labels = np.array(topics)
    return (labels[:, None] == labels[None, :]).astype(float)


def partner_rank(neighbours: np.ndarray, query: int, partner: int) -> int:
    return int(np.flatnonzero(neighbours[query] == partner)[0]) + 1


@dataclass(frozen=True)
class EdgeScores:
    edges: int
    precision: float
    recall: float

    @property
    def f1(self) -> float:
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * self.precision * self.recall / (self.precision + self.recall)


def edge_scores(
    similarity: np.ndarray, topics: Sequence[str], threshold: float
) -> EdgeScores:
    """Score the edge set /graph would draw: every pair above the threshold."""
    upper = np.triu_indices(len(topics), k=1)
    predicted = np.asarray(similarity)[upper] > threshold
    relevant = same_topic_matrix(topics)[upper] == 1
    true_edges = int(np.sum(predicted & relevant))
    return EdgeScores(
        edges=int(np.sum(predicted)),
        precision=true_edges / max(int(np.sum(predicted)), 1),
        recall=true_edges / int(np.sum(relevant)),
    )


def tfidf_similarity(corpus: Corpus) -> np.ndarray:
    """Exactly what /graph computes today: the production TF-IDF path and its text format."""
    return ai_service.calculate_similarity(
        [f"{note.title} {note.content}" for note in corpus.notes]
    )


@dataclass(frozen=True)
class EmbeddingRun:
    model_name: str
    similarity: np.ndarray
    load_seconds: float
    batch_ms_per_note: float
    single_note_ms: float


def embedding_run(model_name: str, corpus: Corpus) -> EmbeddingRun:
    embedder = FastEmbedEmbedder(model_name, settings.embedding_cache_dir)
    texts = [note_text(note.title, note.content) for note in corpus.notes]

    load_seconds = timed(lambda: embedder.embed(["warm up"]))
    started = time.perf_counter()
    vectors = np.array(embedder.embed(texts))
    batch_seconds = time.perf_counter() - started
    single_note_seconds = statistics.median(
        timed(lambda text=text: embedder.embed([text])) for text in texts
    )

    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    return EmbeddingRun(
        model_name=model_name,
        similarity=vectors @ vectors.T,
        load_seconds=load_seconds,
        batch_ms_per_note=1000 * batch_seconds / len(texts),
        single_note_ms=1000 * single_note_seconds,
    )


def timed(action: Callable[[], object]) -> float:
    started = time.perf_counter()
    action()
    return time.perf_counter() - started


def machine_description() -> str:
    cpu = platform.processor() or platform.machine()
    if platform.system() == "Darwin":
        cpu = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
    return f"{cpu}, {os.cpu_count()} cores, {platform.system()} {platform.machine()}, Python {platform.python_version()}"


@dataclass(frozen=True)
class Backend:
    label: str
    similarity: np.ndarray
    neighbours: np.ndarray
    scores: RetrievalScores


def scored_backend(
    label: str, similarity: np.ndarray, topics: Sequence[str]
) -> Backend:
    neighbours = rank_neighbours(similarity)
    return Backend(label, similarity, neighbours, retrieval_scores(neighbours, topics))


def percent(value: float) -> str:
    return f"{100 * value:.1f}"


def short_name(model_name: str) -> str:
    return model_name.split("/")[-1]


def render_results(
    corpus: Corpus, tfidf: np.ndarray, tfidf_seconds: float, runs: list[EmbeddingRun]
) -> str:
    topics = corpus.topics
    baseline = scored_backend("TF-IDF (production baseline)", tfidf, topics)
    embeddings = [
        scored_backend(
            f"Embeddings, {short_name(run.model_name)}", run.similarity, topics
        )
        for run in runs
    ]
    ceiling = scored_backend(
        "Ceiling (perfect ranking)", same_topic_matrix(topics), topics
    )
    sections = [
        header_section(corpus),
        retrieval_section([baseline, *embeddings, ceiling]),
        uncertainty_section(baseline, embeddings),
        pairs_section(corpus, [baseline, *embeddings]),
        graph_section(topics, baseline, embeddings),
        cost_section(len(topics), tfidf_seconds, runs),
    ]
    return "\n\n".join("\n".join(section) for section in sections) + "\n"


def header_section(corpus: Corpus) -> list[str]:
    topics = corpus.topics
    subjects = sorted({note.subject for note in corpus.notes})
    topic_sizes = [topics.count(topic) for topic in sorted(set(topics))]
    return [
        "# Note similarity benchmark",
        "",
        "Generated by `tests/eval/benchmark.py`; do not edit by hand.",
        "",
        f"Command: `{COMMAND}`",
        "",
        f"Run on {datetime.date.today().isoformat()}: {machine_description()}.",
        f"Packages: fastembed {metadata.version('fastembed')}, onnxruntime {metadata.version('onnxruntime')}, scikit-learn {metadata.version('scikit-learn')}.",
        "",
        "## Corpus",
        "",
        f"{len(corpus.notes)} synthetic lecture notes in `tests/eval/corpus/`, across {len(subjects)} subjects ({', '.join(subjects)}) and {len(topic_sizes)} topics of {min(topic_sizes)} to {max(topic_sizes)} notes each.",
        "No real user notes are used.",
        "Each note is one query; every other note is ranked by similarity, and a neighbour is relevant when it shares the query's topic.",
        "Precision@k and recall@k are averaged over all queries, and tied scores are broken in a fixed random order.",
        f"The ceiling row is a perfect ranking: with {min(topic_sizes) - 1} to {max(topic_sizes) - 1} relevant notes per query, precision@5 cannot reach 100.",
    ]


def retrieval_section(backends: list[Backend]) -> list[str]:
    lines = [
        "## Retrieval",
        "",
        "| Backend | "
        + " | ".join(f"P@{k}" for k in KS)
        + " | "
        + " | ".join(f"R@{k}" for k in KS)
        + " |",
        "|---|" + "---:|" * (2 * len(KS)),
    ]
    for backend in backends:
        precision, recall = backend.scores.precision, backend.scores.recall
        lines.append(
            f"| {backend.label} | "
            + " | ".join(percent(precision[k]) for k in KS)
            + " | "
            + " | ".join(percent(recall[k]) for k in KS)
            + " |"
        )
    return lines


def uncertainty_section(baseline: Backend, embeddings: list[Backend]) -> list[str]:
    comparisons = [(backend, baseline) for backend in embeddings]
    comparisons += [
        (later, earlier)
        for index, earlier in enumerate(embeddings)
        for later in embeddings[index + 1 :]
    ]
    lines = [
        "Paired bootstrap: the mean per-query difference in points, with a 95% interval "
        f"from {BOOTSTRAP_RESAMPLES:,} resamples of the queries.",
        "An interval that excludes 0 is a difference this corpus can detect.",
        "",
        "| Comparison | P@1 difference | R@5 difference |",
        "|---|---:|---:|",
    ]
    for better, worse in comparisons:
        precision_gain = (
            better.scores.per_query_precision[1] - worse.scores.per_query_precision[1]
        )
        recall_gain = (
            better.scores.per_query_recall[5] - worse.scores.per_query_recall[5]
        )
        lines.append(
            f"| {better.label} minus {worse.label} | "
            f"{difference_cell(precision_gain)} | {difference_cell(recall_gain)} |"
        )
    return lines


def difference_cell(gains: np.ndarray) -> str:
    low, high = bootstrap_interval(gains)
    return f"{100 * gains.mean():+.1f} [{100 * low:+.1f}, {100 * high:+.1f}]"


def pairs_section(corpus: Corpus, backends: list[Backend]) -> list[str]:
    lines = [
        "## Deliberate pairs",
        "",
        f"{len(corpus.synonymy)} synonymy pairs share a topic but little vocabulary, such as neural nets and deep learning, or mitosis and cell division.",
        f"{len(corpus.near_miss)} near-miss pairs share vocabulary but not a topic, such as neural and computer networks, or chemical and market equilibrium.",
        f"Each pair is checked in both directions: is the partner among the query's {PAIR_WINDOW} nearest neighbours?",
        "Higher is better for synonymy, lower is better for near misses.",
        "",
        f"| Backend | Synonym partner in top {PAIR_WINDOW} | Near-miss partner in top {PAIR_WINDOW} |",
        "|---|---:|---:|",
    ]
    for backend in backends:
        lines.append(
            f"| {backend.label} | "
            f"{percent(pair_hit_rate(corpus, backend.neighbours, corpus.synonymy))} | "
            f"{percent(pair_hit_rate(corpus, backend.neighbours, corpus.near_miss))} |"
        )
    lines += [
        "",
        "Rank of the partner among the query's neighbours, shown as `a -> b / b -> a` (1 is the nearest).",
        "",
        "| Kind | Pair | " + " | ".join(backend.label for backend in backends) + " |",
        "|---|---|" + "---:|" * len(backends),
    ]
    for kind, pairs in (("synonymy", corpus.synonymy), ("near miss", corpus.near_miss)):
        for a, b in pairs:
            i, j = corpus.position(a), corpus.position(b)
            ranks = [
                f"{partner_rank(backend.neighbours, i, j)} / {partner_rank(backend.neighbours, j, i)}"
                for backend in backends
            ]
            lines.append(f"| {kind} | {a}, {b} | " + " | ".join(ranks) + " |")
    return lines


def pair_hit_rate(
    corpus: Corpus, neighbours: np.ndarray, pairs: list[tuple[str, str]]
) -> float:
    hits = []
    for a, b in pairs:
        i, j = corpus.position(a), corpus.position(b)
        hits.append(partner_rank(neighbours, i, j) <= PAIR_WINDOW)
        hits.append(partner_rank(neighbours, j, i) <= PAIR_WINDOW)
    return statistics.fmean(hits)


def graph_section(
    topics: Sequence[str], baseline: Backend, embeddings: list[Backend]
) -> list[str]:
    production = embeddings[0]
    production_thresholds = {
        baseline.label: TFIDF_GRAPH_THRESHOLD,
        production.label: settings.embedding_similarity_threshold,
    }
    same_topic_pairs = int(np.sum(np.triu(same_topic_matrix(topics), k=1)))
    lines = [
        "## Graph edges",
        "",
        "`/graph` draws an edge for every pair of a user's notes above a similarity threshold, so this scores that edge set directly: precision and recall of same-topic pairs among the pairs above the threshold.",
        f"The corpus has {same_topic_pairs} same-topic pairs out of {len(topics) * (len(topics) - 1) // 2}.",
        f"TF-IDF scores are the production boosted values, `min(1, 1.1 * sqrt(cosine))`, and production draws edges above {TFIDF_GRAPH_THRESHOLD}.",
        f"Embedding scores are raw cosine similarity, and production draws edges above `EMBEDDING_SIMILARITY_THRESHOLD`, currently {settings.embedding_similarity_threshold}.",
        f"The best-F1 rows search thresholds from {THRESHOLD_GRID[0]} to {THRESHOLD_GRID[-1]} on this same corpus, so they are an optimistic ceiling for each backend rather than a held-out result.",
        "",
        "| Backend | Threshold | Edges | Precision | Recall | F1 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for backend in [baseline, *embeddings]:
        candidates = []
        if backend.label in production_thresholds:
            candidates.append(("production", production_thresholds[backend.label]))
        candidates.append(("best F1", best_f1_threshold(backend.similarity, topics)))
        for kind, threshold in candidates:
            scores = edge_scores(backend.similarity, topics, threshold)
            lines.append(
                f"| {backend.label}, {kind} | {threshold} | {edge_cells(scores)} |"
            )
    lines += [
        "",
        f"Precision and recall trade-off for {short_name(settings.embedding_model)}:",
        "",
        "| Threshold | Edges | Precision | Recall | F1 |",
        "|---:|---:|---:|---:|---:|",
    ]
    for threshold in PRODUCTION_SWEEP:
        scores = edge_scores(production.similarity, topics, threshold)
        lines.append(f"| {threshold} | {edge_cells(scores)} |")
    return lines


def best_f1_threshold(similarity: np.ndarray, topics: Sequence[str]) -> float:
    return max(
        THRESHOLD_GRID,
        key=lambda threshold: edge_scores(similarity, topics, threshold).f1,
    )


def edge_cells(scores: EdgeScores) -> str:
    if not scores.edges:
        return f"0 | - | {percent(scores.recall)} | -"
    return f"{scores.edges} | {percent(scores.precision)} | {percent(scores.recall)} | {percent(scores.f1)}"


def cost_section(
    note_count: int, tfidf_seconds: float, runs: list[EmbeddingRun]
) -> list[str]:
    lines = [
        "## Cost on this machine",
        "",
        "| Backend | Model load | Per note, batch of the corpus | Per note, one at a time (median) |",
        "|---|---:|---:|---:|",
        f"| TF-IDF | none | {1000 * tfidf_seconds / note_count:.2f} ms (whole matrix {1000 * tfidf_seconds:.0f} ms) | not applicable |",
    ]
    for run in runs:
        lines.append(
            f"| {short_name(run.model_name)} | {run.load_seconds:.2f} s | {run.batch_ms_per_note:.2f} ms | {run.single_note_ms:.2f} ms |"
        )
    lines += [
        "",
        "TF-IDF is refit on all of a user's notes on every `/graph` request.",
        "Embeddings are computed once per note on create or update, and `/graph` only compares stored vectors in Postgres.",
        "Model load is measured from the local cache and happens once per process; the first model listed also pays for importing fastembed.",
    ]
    return lines


def main() -> None:
    corpus = load_corpus()
    started = time.perf_counter()
    tfidf = tfidf_similarity(corpus)
    tfidf_seconds = time.perf_counter() - started
    runs = [
        embedding_run(model_name, corpus)
        for model_name in (settings.embedding_model, *COMPARISON_MODELS)
    ]
    report = render_results(corpus, tfidf, tfidf_seconds, runs)
    RESULTS_PATH.write_text(report)
    print(report)


if __name__ == "__main__":
    main()
