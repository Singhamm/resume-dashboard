import io
import re
from pdfminer.high_level import extract_text as extract_pdf_text
from docx import Document


def extract_text(file):
    content = file.file.read()
    if file.filename.lower().endswith('.pdf'):
        return extract_pdf_text(io.BytesIO(content))
    else:
        doc = Document(io.BytesIO(content))
        return '\n'.join(p.text for p in doc.paragraphs)


def parse_resume(text: str) -> dict:
    # Stub parser: returns basic JSON model with full text as 'summary'
    return {
        "personal": {"name": "", "email": "", "phone": "", "location": "", "summary": text[:200]},
        "experience": [],
        "education": [],
        "skills": [],
        "certifications": []
    }