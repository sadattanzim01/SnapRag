# ─── Imports ──────────────────────────────────────────────────────────────────
import os
import re
import pdfplumber          # extracts text from PDF files
from PIL import Image      # opens and processes image files
import pytesseract         # runs OCR (optical character recognition) on images

# ─── PDF Text Extraction ──────────────────────────────────────────────────────
def extract_text_from_pdf(file_path):
    """
    Extracts all text from a PDF file page by page.
    
    How pdfplumber works:
    - Opens the PDF as a structured object
    - Each page has a .extract_text() method that reads the text layer
    - Some PDFs have no text layer (scanned documents) — for those,
      extract_text() returns None, so we use OCR as a fallback
    
    Args:
        file_path: path to the PDF file on disk
    Returns:
        A single string with all pages joined together
    """
    full_text = []

    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            # Try to extract the text layer first (fast, accurate)
            text = page.extract_text()

            if text and text.strip():
                # Text layer exists — use it directly
                full_text.append(f"[Page {page_num + 1}]\n{text}")
            else:
                # No text layer — this is a scanned page, use OCR instead
                # Convert the PDF page to an image, then run tesseract on it
                page_image = page.to_image(resolution=200).original
                ocr_text = pytesseract.image_to_string(page_image)
                if ocr_text.strip():
                    full_text.append(f"[Page {page_num + 1} - OCR]\n{ocr_text}")

    return "\n\n".join(full_text)

# ─── Image Text Extraction ────────────────────────────────────────────────────
def extract_text_from_image(file_path):
    """
    Runs OCR on an image file to extract any text in it.
    
    How pytesseract works:
    - Opens the image with Pillow (PIL)
    - Sends it to the tesseract engine installed on your Mac
    - Tesseract analyzes the pixel patterns and converts them to characters
    - Returns a plain string of the recognized text
    
    Args:
        file_path: path to the image file on disk
    Returns:
        A string of all text found in the image
    """
    # Open the image using Pillow
    image = Image.open(file_path)

    # Run tesseract OCR on it
    # lang='eng' tells tesseract to use English language data
    text = pytesseract.image_to_string(image, lang='eng')

    return text

# ─── Text Cleaning ────────────────────────────────────────────────────────────
def clean_text(text):
    """
    Cleans raw extracted text to remove noise before embedding.
    
    Why clean? Raw PDF/OCR text often contains:
    - Multiple blank lines in a row
    - Weird whitespace characters
    - Repeated spaces
    
    Cleaner text = better embeddings = more accurate search results
    
    Args:
        text: raw extracted text string
    Returns:
        Cleaned text string
    """
    if not text:
        return ""

    # Replace multiple spaces with a single space
    text = re.sub(r' +', ' ', text)

    # Replace 3+ consecutive newlines with just 2 (keep paragraph breaks)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Strip leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)

    # Final strip of the whole text
    return text.strip()

# ─── Main extraction function ─────────────────────────────────────────────────
def extract_text(file_path, file_type):
    """
    Routes the file to the correct extractor based on its type,
    then cleans and returns the result.
    
    Args:
        file_path: path to the file on disk
        file_type: 'pdf' or 'image'
    Returns:
        Cleaned extracted text string
    """
    if file_type == 'pdf':
        raw_text = extract_text_from_pdf(file_path)
    else:
        raw_text = extract_text_from_image(file_path)

    return clean_text(raw_text)