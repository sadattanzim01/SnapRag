import base64
import io
import os
import re

import pdfplumber
import pytesseract
from anthropic import Anthropic
from PIL import Image, ImageOps

VISION_MODEL = 'claude-sonnet-4-6'

# Claude shrinks bigger images itself, so sending more only wastes upload time
MAX_IMAGE_SIDE = 1568

VISION_PROMPT = (
    'Transcribe all text in this image exactly as written, in reading order. '
    'Then add a short section starting with "Image description:" that says what the '
    'image shows (layout, people, objects, logos, charts). '
    'Only include what is visible. Do not guess or add anything.'
)


def extract_text_from_pdf(file_path):
    """Read each page's text layer, and fall back to OCR for scanned pages."""
    pages = []

    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()

            if text and text.strip():
                pages.append(f'[Page {page_num}]\n{text}')
            else:
                # No text layer, so this page is a scan
                image = page.to_image(resolution=200).original
                ocr_text = pytesseract.image_to_string(image)
                if ocr_text.strip():
                    pages.append(f'[Page {page_num} - OCR]\n{ocr_text}')

    return '\n\n'.join(pages)


def prepare_for_claude(image):
    """Convert to RGB (transparency becomes white), shrink, and encode as base64 JPEG."""
    if image.mode != 'RGB':
        rgba = image.convert('RGBA')
        background = Image.new('RGB', rgba.size, 'white')
        background.paste(rgba, mask=rgba.split()[3])
        image = background

    image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))

    buffer = io.BytesIO()
    image.save(buffer, 'JPEG', quality=90)
    return base64.standard_b64encode(buffer.getvalue()).decode()


def read_image_with_claude(image):
    """Ask Claude for the image's text and a short description."""
    client = Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
    response = client.messages.create(
        model=VISION_MODEL,
        max_tokens=1500,
        messages=[{
            'role': 'user',
            'content': [
                {
                    'type': 'image',
                    'source': {
                        'type': 'base64',
                        'media_type': 'image/jpeg',
                        'data': prepare_for_claude(image),
                    },
                },
                {'type': 'text', 'text': VISION_PROMPT},
            ],
        }],
    )
    return response.content[0].text


def extract_text_from_image(file_path):
    """Read an image with Claude, or with OCR if the Claude call fails."""
    # Apply the rotation stored in the photo so sideways phone pictures read correctly
    image = ImageOps.exif_transpose(Image.open(file_path))

    try:
        return read_image_with_claude(image)
    except Exception as e:
        print(f'Claude vision failed, using OCR instead: {e}')
        return pytesseract.image_to_string(image, lang='eng')


def clean_text(text):
    """Remove extra spaces and blank lines before the text is chunked."""
    if not text:
        return ''

    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = '\n'.join(line.strip() for line in text.split('\n'))
    return text.strip()


def extract_text(file_path, file_type):
    """Pick the right extractor for the file type, then clean the result."""
    if file_type == 'pdf':
        raw_text = extract_text_from_pdf(file_path)
    else:
        raw_text = extract_text_from_image(file_path)

    return clean_text(raw_text)