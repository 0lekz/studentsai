"""TF-IDF note similarity: the production default and the baseline the embedding benchmark measures against."""

import logging
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


def calculate_similarity(texts: list[str]) -> np.ndarray:
    """Calculate similarity matrix between texts using TF-IDF"""
    if len(texts) < 2:
        return np.array([[1.0]])

    try:
        # More permissive vectorizer to make similarity matching easier
        vectorizer = TfidfVectorizer(
            max_features=3000,
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
            norm="l2",
        )

        tfidf_matrix = vectorizer.fit_transform(texts)

        similarity_matrix = cosine_similarity(tfidf_matrix)
        # Calibrate similarities to be less strict: boost medium sims upward
        # boosted = min(1, sqrt(sim) * 1.1)
        boosted = np.minimum(1.0, np.sqrt(np.maximum(similarity_matrix, 0.0)) * 1.1)

        return boosted

    except Exception as e:
        logger.error(f"Error calculating similarity: {e!s}")
        # Return identity matrix as fallback
        n = len(texts)
        return np.eye(n)


def find_note_connections(
    notes: list[dict[str, Any]], threshold: float = 0.6
) -> list[dict[str, Any]]:
    """Find connections between notes based on content similarity"""
    if len(notes) < 2:
        return []

    texts = [f"{note['title']} {note['content']}" for note in notes]

    similarity_matrix = calculate_similarity(texts)

    connections = []
    n = len(notes)

    for i in range(n):
        for j in range(i + 1, n):
            similarity = similarity_matrix[i][j]

            if similarity > threshold:
                connections.append(
                    {
                        "source_id": notes[i]["id"],
                        "target_id": notes[j]["id"],
                        "similarity": float(similarity),
                        "connection_type": "similarity",
                    }
                )

    connections.sort(key=lambda x: x["similarity"], reverse=True)

    return connections
