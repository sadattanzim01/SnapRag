import base64
import io
from types import SimpleNamespace

import pytest
from PIL import Image

import services.extractor as extractor


@pytest.fixture
def fake_vision(monkeypatch):
    """Replaces the Anthropic client. Tests set .reply or .error and read .calls."""
    state = SimpleNamespace(reply='Hello world\n\nImage description: a sign', error=None, calls=[])

    class FakeAnthropic:
        def __init__(self, api_key=None):
            self.messages = self

        def create(self, **kwargs):
            if state.error:
                raise state.error
            state.calls.append(kwargs)
            return SimpleNamespace(content=[SimpleNamespace(text=state.reply)])

    monkeypatch.setattr(extractor, 'Anthropic', FakeAnthropic)
    return state


def save_image(tmp_path, size=(200, 100), mode='RGB', name='pic.png'):
    path = tmp_path / name
    Image.new(mode, size, 'white').save(path)
    return str(path)


def sent_image(state):
    """The JPEG that was sent to Claude, opened again for inspection."""
    block = state.calls[0]['messages'][0]['content'][0]
    return block, Image.open(io.BytesIO(base64.b64decode(block['source']['data'])))


def test_image_text_comes_from_claude(tmp_path, fake_vision):
    result = extractor.extract_text(save_image(tmp_path), 'image')
    assert result == 'Hello world\n\nImage description: a sign'


def test_image_is_sent_as_jpeg_with_the_prompt(tmp_path, fake_vision):
    extractor.extract_text(save_image(tmp_path), 'image')

    block, _ = sent_image(fake_vision)
    prompt = fake_vision.calls[0]['messages'][0]['content'][1]['text']
    assert block['type'] == 'image'
    assert block['source']['media_type'] == 'image/jpeg'
    assert 'Transcribe' in prompt


def test_large_images_are_shrunk(tmp_path, fake_vision):
    extractor.extract_text(save_image(tmp_path, size=(3000, 2000)), 'image')

    _, image = sent_image(fake_vision)
    assert max(image.size) <= extractor.MAX_IMAGE_SIDE


def test_transparent_png_does_not_crash(tmp_path, fake_vision):
    path = tmp_path / 'logo.png'
    Image.new('RGBA', (50, 50), (0, 0, 0, 0)).save(path)

    extractor.extract_text(str(path), 'image')

    _, image = sent_image(fake_vision)
    assert image.mode == 'RGB'


def test_falls_back_to_ocr_when_claude_fails(tmp_path, fake_vision, monkeypatch):
    fake_vision.error = RuntimeError('no credits')
    monkeypatch.setattr(extractor.pytesseract, 'image_to_string', lambda *a, **k: 'ocr text')

    assert extractor.extract_text(save_image(tmp_path), 'image') == 'ocr text'