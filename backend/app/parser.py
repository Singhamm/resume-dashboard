# backend/app/parser.py

import io
import re
from pdfminer.high_level import extract_text as extract_pdf_text
from docx import Document
from rapidfuzz import fuzz

# Map month abbreviations to numbers for sorting
MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "may": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12
}

def extract_text(file) -> str:
    """
    Read raw bytes from either FastAPI UploadFile or Streamlit UploadedFile,
    then dispatch to PDF or DOCX extractor.
    """
    try:
        content = file.file.read()              # FastAPI UploadFile
    except AttributeError:
        file.seek(0)                            # Streamlit UploadedFile
        content = file.read()

    name = getattr(file, "filename", None) or getattr(file, "name", "")
    name = name.lower()

    if name.endswith(".pdf"):
        return extract_pdf_text(io.BytesIO(content))
    elif name.endswith(".docx") or name.endswith(".doc"):
        doc = Document(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs)
    else:
        try:
            return content.decode("utf-8", errors="ignore")
        except:
            return str(content)

def parse_resume(text: str) -> dict:
    """
    Parses the resume text into our JSON model:
    - Extracts name as the first non-empty line.
    - Finds all date-range anchors.
    - Splits into segments around each anchor.
    - For each segment, extracts:
        title, client, start_date, end_date, bullets.
    - Fuzzy-merges segments with identical dates & similar client.
    - Returns dict with personal info and sorted experience list.
    """
    # --- 1) Personal info (name) ---
    name = ""
    for line in text.splitlines():
        line = line.strip()
        if line:
            name = line
            break

    # --- 2) Find all date anchors ---
    date_pattern = r"([A-Za-z]{3,9}\s+\d{4})\s*[–-]\s*([A-Za-z]{3,9}\s+\d{4}|Present)"
    anchors = list(re.finditer(date_pattern, text))
    segments = []
    text_len = len(text)

    for i, m in enumerate(anchors):
        start_date, end_date = m.group(1), m.group(2)
        seg_start = m.start()
        seg_end = anchors[i+1].start() if i+1 < len(anchors) else text_len

        # 2a) Title extraction: take the line that contains this anchor
        line_start = text.rfind("\n", 0, seg_start)
        line_end = text.find("\n", m.end())
        title_line = text[line_start+1 : line_end].strip()
        # Remove the date chunk from that line
        title = re.sub(date_pattern, "", title_line).strip()

        # 2b) Client: first non-empty line after the date line
        after = text[line_end+1 : seg_end]
        client = ""
        for ln in after.splitlines():
            if ln.strip():
                client = ln.strip()
                break

        # 2c) Bullets: lines starting with •, -, ., or numbered
        bullets = []
        for ln in after.splitlines():
            ln_stripped = ln.strip()
            if re.match(r"^(\u2022|[-*.]|\d+\.)\s*", ln_stripped):
                bullet = re.sub(r"^(\u2022|[-*.]|\d+\.)\s*", "", ln_stripped)
                bullets.append(bullet)

        segments.append({
            "title": title,
            "client": client,
            "start_date": start_date,
            "end_date": end_date,
            "bullets": bullets
        })

    # --- 3) Fuzzy-merge segments with same dates + similar client ---
    merged = []
    for seg in segments:
        matched = False
        for mseg in merged:
            if (
                mseg["start_date"] == seg["start_date"]
                and mseg["end_date"] == seg["end_date"]
                and fuzz.ratio(mseg["client"], seg["client"]) > 90
            ):
                mseg["bullets"].extend(seg["bullets"])
                matched = True
                break
        if not matched:
            merged.append(seg)

    # --- 4) Sort newest → oldest by start_date ---
    def _key(dt_str):
        mon, yr = dt_str.split()[:2]
        m = MONTHS.get(mon[:3].lower(), 1)
        y = int(yr)
        return y*100 + m

    merged.sort(key=lambda x: _key(x["start_date"]), reverse=True)

    # --- 5) Construct final JSON model ---
    return {
        "personal": {
            "name": name,
            "email": "",
            "phone": "",
            "location": "",
            "summary": ""
        },
        "experience": merged,
        "education": [],
        "skills": [],
        "certifications": []
    }
