import os

import services.db as db


def count_chunks():
    return db.execute_query('SELECT COUNT(*) AS n FROM document_chunks')[0]['n']


def test_health(client):
    assert client.get('/').status_code == 200


def test_list_starts_empty(client):
    res = client.get('/api/documents')
    assert res.status_code == 200
    assert res.get_json() == []


def test_upload_without_file(client):
    res = client.post('/api/documents/upload')
    assert res.status_code == 400
    assert res.get_json()['error'] == 'No file provided'


def test_upload_empty_filename(client, upload_doc):
    assert upload_doc(name='').status_code == 400


def test_upload_rejects_wrong_type(upload_doc):
    res = upload_doc(name='notes.txt')
    assert res.status_code == 400
    assert res.get_json()['error'] == 'File type not allowed'


def test_upload_success(client, upload_doc):
    res = upload_doc(name='notes.pdf')
    assert res.status_code == 201
    body = res.get_json()
    assert body['filename'] == 'notes.pdf'
    assert body['file_type'] == 'pdf'
    assert body['chunk_count'] >= 1

    listed = client.get('/api/documents').get_json()
    assert [d['filename'] for d in listed] == ['notes.pdf']


def test_image_upload_is_typed_as_image(upload_doc):
    assert upload_doc(name='photo.jpg').get_json()['file_type'] == 'image'


def test_same_filename_twice_keeps_both(client, upload_doc, uploads):
    first = upload_doc(name='notes.pdf', content=b'first').get_json()['document_id']
    second = upload_doc(name='notes.pdf', content=b'second').get_json()['document_id']

    assert first != second
    assert len(os.listdir(uploads)) == 2
    assert client.get(f'/api/documents/{first}/file').data == b'first'
    assert client.get(f'/api/documents/{second}/file').data == b'second'


def test_failed_extraction_leaves_nothing_behind(client, upload_doc, uploads, monkeypatch):
    import routes.documents as documents

    def boom(path, file_type):
        raise RuntimeError('bad pdf')

    monkeypatch.setattr(documents, 'extract_text', boom)
    res = upload_doc()

    assert res.status_code == 500
    assert client.get('/api/documents').get_json() == []
    assert os.listdir(uploads) == []


def test_empty_text_leaves_nothing_behind(client, upload_doc, uploads, monkeypatch):
    import routes.documents as documents

    monkeypatch.setattr(documents, 'extract_text', lambda path, file_type: '')
    res = upload_doc()

    assert res.status_code == 400
    assert client.get('/api/documents').get_json() == []
    assert os.listdir(uploads) == []


def test_delete_unknown_document_is_404(client):
    res = client.delete('/api/documents/9999')
    assert res.status_code == 404


def test_delete_removes_document_chunks_and_file(client, upload_doc, uploads):
    doc_id = upload_doc().get_json()['document_id']
    assert count_chunks() > 0
    assert len(os.listdir(uploads)) == 1

    assert client.delete(f'/api/documents/{doc_id}').status_code == 200

    assert client.get('/api/documents').get_json() == []
    assert count_chunks() == 0
    assert os.listdir(uploads) == []


def test_file_endpoint_returns_original_bytes(client, upload_doc):
    doc_id = upload_doc(content=b'original bytes').get_json()['document_id']
    res = client.get(f'/api/documents/{doc_id}/file')
    assert res.status_code == 200
    assert res.data == b'original bytes'


def test_file_endpoint_finds_files_saved_with_old_names(client, uploads):
    doc_id = db.execute_query(
        'INSERT INTO documents (filename, file_type) VALUES (?, ?)',
        ('old doc.pdf', 'pdf'),
        fetch=False,
    )
    (uploads / 'old_doc.pdf').write_bytes(b'legacy file')

    res = client.get(f'/api/documents/{doc_id}/file')
    assert res.status_code == 200
    assert res.data == b'legacy file'


def test_file_endpoint_unknown_document_is_404(client):
    assert client.get('/api/documents/9999/file').status_code == 404