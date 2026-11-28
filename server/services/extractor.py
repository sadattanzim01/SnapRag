import re

import pdfplumber
import pytesseract
from PIL import Image, ImageOps


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


def extract_text_from_image(file_path):
    """Run OCR on an image."""
    image = Image.open(file_path)
    # Apply the rotation stored in the photo so sideways phone pictures read correctly
    image = ImageOps.exif_transpose(image)
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