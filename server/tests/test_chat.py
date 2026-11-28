import routes.chat as chat


def ask(client, **payload):
    return client.post('/api/chat/ask', json=payload)


def test_missing_question(client):
    assert ask(client).status_code == 400


def test_blank_question(client):
    assert ask(client, question='   ').status_code == 400


def test_document_ids_must_be_numbers(client):
    res = ask(client, question='hi', document_ids=['abc'])
    assert res.status_code == 400


def test_no_documents_ticked(client):
    res = ask(client, question='hi', document_ids=[])
    assert 'Select at least one document' in res.get_json()['answer']


def test_nothing_uploaded(client, fake_claude):
    res = ask(client, question='hi')
    assert 'No documents have been uploaded' in res.get_json()['answer']
    assert fake_claude.calls == []


def test_unknown_document_ids(client, fake_claude):
    res = ask(client, question='hi', document_ids=[9999])
    assert 'not found' in res.get_json()['answer']
    assert fake_claude.calls == []


def test_answer_comes_with_sources(client, upload_doc, fake_claude):
    doc_id = upload_doc(name='notes.pdf').get_json()['document_id']
    res = ask(client, question='What do cats do?', document_ids=[doc_id])

    assert res.status_code == 200
    body = res.get_json()
    assert body['answer'] == fake_claude.reply
    assert body['document'] is None
    assert body['sources'][0]['filename'] == 'notes.pdf'


def test_claude_receives_the_document_text(client, upload_doc, fake_claude):
    doc_id = upload_doc().get_json()['document_id']
    ask(client, question='What do cats do?', document_ids=[doc_id])

    sent = fake_claude.calls[0]['messages'][-1]['content']
    assert 'Cats purr and sleep all day.' in sent
    assert 'Question: What do cats do?' in sent


def test_generated_document_is_split_from_chat_text(client, upload_doc, fake_claude):
    doc_id = upload_doc().get_json()['document_id']
    fake_claude.reply = 'Done. <document title="Cats">\n# Cats\nThey purr.\n</document>'

    body = ask(client, question='Write a summary', document_ids=[doc_id]).get_json()

    assert body['answer'] == 'Done.'
    assert body['document']['title'] == 'Cats'
    assert '# Cats' in body['document']['content']


def test_document_only_reply_gets_a_default_message(client, upload_doc, fake_claude):
    doc_id = upload_doc().get_json()['document_id']
    fake_claude.reply = '<document title="Cats">\n# Cats\n</document>'

    body = ask(client, question='Write a summary', document_ids=[doc_id]).get_json()

    assert 'created the document' in body['answer']


def test_claude_failure_returns_500(client, upload_doc, fake_claude):
    doc_id = upload_doc().get_json()['document_id']
    fake_claude.error = RuntimeError('rate limited')

    res = ask(client, question='hi', document_ids=[doc_id])

    assert res.status_code == 500
    assert 'Claude API error' in res.get_json()['error']


def test_history_is_cleaned_before_sending(client, upload_doc, fake_claude):
    doc_id = upload_doc().get_json()['document_id']
    history = [
        {'role': 'assistant', 'content': 'leading assistant message'},
        {'role': 'user', 'content': 'q1'},
        {'role': 'bad-role', 'content': 'ignored'},
        {'role': 'assistant', 'content': 'a1'},
    ]
    ask(client, question='q2', document_ids=[doc_id], history=history)

    sent = fake_claude.calls[0]['messages']
    assert [m['role'] for m in sent] == ['user', 'assistant', 'user']
    assert sent[0]['content'] == 'q1'


def fake_chunks(similarities):
    return [
        {'content': f'chunk {i}', 'filename': 'a.pdf', 'document_id': 1,
         'chunk_index': i, 'similarity': s}
        for i, s in enumerate(similarities)
    ]


def test_weak_sources_are_hidden(client, fake_claude, monkeypatch):
    chunks = fake_chunks([0.5, 0.05, 0.02])
    monkeypatch.setattr(chat, 'find_relevant_chunks', lambda *a, **k: chunks)

    body = ask(client, question='hi').get_json()

    assert [s['similarity'] for s in body['sources']] == [0.5]


def test_best_source_is_kept_when_all_are_weak(client, fake_claude, monkeypatch):
    chunks = fake_chunks([0.05, 0.02])
    monkeypatch.setattr(chat, 'find_relevant_chunks', lambda *a, **k: chunks)

    body = ask(client, question='hi').get_json()

    assert [s['similarity'] for s in body['sources']] == [0.05]