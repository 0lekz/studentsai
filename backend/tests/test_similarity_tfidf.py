import pytest

from app.services.similarity_tfidf import calculate_similarity, find_note_connections


def note(note_id: str, title: str, content: str) -> dict:
    return {"id": note_id, "title": title, "content": content}


def test_one_text_is_only_similar_to_itself():
    assert calculate_similarity(["Mitosis"]).tolist() == [[1.0]]


def test_texts_of_only_stop_words_fall_back_to_no_similarity():
    assert calculate_similarity(["the and of", "a an it"]).tolist() == [
        [1.0, 0.0],
        [0.0, 1.0],
    ]


def test_similarities_are_boosted_square_roots_of_the_cosine():
    [[_, boosted], _] = calculate_similarity(["cells divide", "cells grow"])

    assert boosted == pytest.approx(0.4944, abs=1e-4)


def test_fewer_than_two_notes_have_no_connections():
    assert find_note_connections([]) == []
    assert find_note_connections([note("a", "Mitosis", "Cells split.")]) == []


def test_connections_are_the_pairs_above_the_threshold_strongest_first():
    notes = [
        note("mitosis", "Mitosis", "Mitosis splits one cell into two daughter cells."),
        note("markets", "Markets", "Supply and demand meet at the equilibrium price."),
        note("division", "Cell division", "One cell splits into two daughter cells."),
        note("copy", "Mitosis", "Mitosis splits one cell into two daughter cells."),
    ]

    connections = find_note_connections(notes)

    assert [(c["source_id"], c["target_id"]) for c in connections] == [
        ("mitosis", "copy"),
        ("mitosis", "division"),
        ("division", "copy"),
    ]
    assert connections[0]["similarity"] == pytest.approx(1.0)
    assert all(c["connection_type"] == "similarity" for c in connections)
    assert connections[1]["similarity"] == connections[2]["similarity"] > 0.6
    assert find_note_connections(notes, threshold=0.99) == connections[:1]
