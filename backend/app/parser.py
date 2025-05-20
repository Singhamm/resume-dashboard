# backend/app/parser.py

import io
from pdfminer.high_level import extract_text as extract_pdf_text
from docx import Document

def extract_text(file) -> str:
    """
    Extracts text from a FastAPI UploadFile or a Streamlit UploadedFile.
    """
    # Read raw bytes from the file-like object
    try:
        # FastAPI UploadFile has a .file attribute
        content = file.file.read()
    except AttributeError:
        # Streamlit UploadedFile behaves like a BytesIO
        file.seek(0)
        content = file.read()

    # Figure out the filename (either .filename or .name)
    filename = getattr(file, 'filename', None) or getattr(file, 'name', '')
    filename = filename.lower()

    # Dispatch based on file extension
    if filename.endswith('.pdf'):
        return extract_pdf_text(io.BytesIO(content))
    elif filename.endswith('.docx') or filename.endswith('.doc'):
        doc = Document(io.BytesIO(content))
        return '\n'.join(p.text for p in doc.paragraphs)
    else:
        # Fallback: treat content as plain text
        try:
            return content.decode('utf-8', errors='ignore')
        except:
            return str(content)
