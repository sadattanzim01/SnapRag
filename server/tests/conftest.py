import io
import os
import sys
from types import SimpleNamespace

import pytest

# Lets the tests import app.py, routes and services from the server folder
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import services.db as db
import routes.documents as documents
import routes.chat as chat
from app import app as flask_app


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """A fresh empty database for each test, so snaprag.db is never touched."""
    monkeypatch.setattr(db, 'DB_PATH', str(tmp_path / 'test.db'))
    db.init_db()
    return tmp_path


@pytest.fixture
def uploads(isolated_db, monkeypatch):
    """A fresh empty uploads folder for each test."""
    folder = isolated_db / 'uploads'
    folder.mkdir()
    monkeypatch.setitem(flask_app.config, 'UPLOAD_FOLDER', str(folder))
    return folder


@pytest.fixture
def client(uploads, monkeypatch):
    # Text extraction is replaced so tests don't need real PDFs or Tesseract
    monkeypatch.setattr(
        documents, 'extract_text', lambda path, file_type: 'Cats purr and sleep all day.'
    )
    with flask_app.test_client() as c:
        yield c


@pytest.fixture
def upload_doc(client):
    """Returns a function that uploads a fake file."""
    def _upload(name='notes.pdf', content=b'fake pdf bytes'):
        return client.post(
            '/api/documents/upload',
            data={'file': (io.BytesIO(content), name)},
            content_type='multipart/form-data',
        )
    return _upload


@pytest.fixture
def fake_claude(monkeypatch):
    """Replaces the Anthropic client. Tests set .reply or .error and read .calls."""
    state = SimpleNamespace(reply='Cats are mentioned [Source 1].', error=None, calls=[])

    class FakeAnthropic:
        def __init__(self, api_key=None):
            self.messages = self

        def create(self, **kwargs):
            if state.error:
                raise state.error
            state.calls.append(kwargs)
            return SimpleNamespace(content=[SimpleNamespace(text=state.reply)])

    monkeypatch.setattr(chat, 'Anthropic', FakeAnthropic)
    return state