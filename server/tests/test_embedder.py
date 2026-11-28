import pytest

import services.db as db
from services.embedder import (
    chunk_text,
    cosine_similarity,
    embed_and_store_document,
    find_relevant_chunks,
)


def test_chunks_overlap():
    text = ' '.join(str(n) for n in range(1, 11))
    assert chunk_text(text, chunk_size=5, overlap=2) == [
        '1 2 3 4 5',
        '4 5 6 7 8',
        '7 8 9 10',
    ]


def test_short_text_is_one_chunk():
    assert chunk_text('one two three', chunk_size=5, overlap=2) == ['one two three']


def test_exact_fit_has_no_extra_chunk():
    assert chunk_text('1 2 3 4 5', chunk_size=5, overlap=2) == ['1 2 3 4 5']


def test_empty_text_has_no_chunks():
    assert chunk_text('') == []


def test_identical_vectors_score_one():
    assert cosine_similarity([1, 2, 3], [1, 2, 3]) == pytest.approx(1.0)


def test_unrelated_vectors_score_zero():
    assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)


def test_zero_vector_scores_zero():
    assert cosine_similarity([0, 0], [1, 1]) == 0


def add_document(filename, text):
    doc_id = db.execute_query(
        'INSERT INTO documents (filename, file_type) VALUES (?, ?)',
        (filename, 'pdf'),
        fetch=False,
    )
    embed_and_store_document(doc_id, text)
    return doc_id


def test_most_relevant_document_ranks_first(isolated_db):
    add_document('cats.pdf', 'Cats purr, chase mice and sleep in the sun.')
    add_document('money.pdf', 'The stock market fell as interest rates rose.')

    results = find_relevant_chunks('what do kittens do?')

    assert results[0]['filename'] == 'cats.pdf'


def test_search_can_be_limited_to_chosen_documents(isolated_db):
    add_document('cats.pdf', 'Cats purr, chase mice and sleep in the sun.')
    money_id = add_document('money.pdf', 'The stock market fell as interest rates rose.')

    results = find_relevant_chunks('what do kittens do?', document_ids=[money_id])

    assert {r['filename'] for r in results} == {'money.pdf'}


def test_top_k_limits_results(isolated_db):
    add_document('a.pdf', 'first document text')
    add_document('b.pdf', 'second document text')

    assert len(find_relevant_chunks('document', top_k=1)) == 1