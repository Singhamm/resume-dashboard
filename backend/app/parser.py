# backend/app/parser.py

import io
import re
from pdfminer.high_level import extract_text as extract_pdf_text
from docx import Document
from rapidfuzz import fuzz

# Month mapping for sorting experience
MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "may": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12
}

def extract_text(file) -> str:
    """Handle both FastAPI UploadFile (.file) and Streamlit UploadedFile (.read())."""
    try:
        content = file.file.read()
    except AttributeError:
        file.seek(0)
        content = file.read()
    name = getattr(file, 'filename', None) or getattr(file, 'name', '')
    name = name.lower()
    if name.endswith('.pdf'):
        return extract_pdf_text(io.BytesIO(content))
    elif name.endswith(('.docx','.doc')):
        doc = Document(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs)
    else:
        try:
            return content.decode('utf-8', errors='ignore')
        except:
            return str(content)

def parse_resume(text: str) -> dict:
    """
    Parses the resume text into a JSON:
      - personal: name, title, contact
      - summary (tries multiple headings)
      - responsibilities, major_clients, certifications, achievements, skills, education
      - experience list (detects any date-range heading)
    """
    # --- Header extraction ---
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    name  = lines[0] if len(lines)>0 else ""
    title = lines[1] if len(lines)>1 else ""
    # contact: phone, email, location
    phone_match = re.search(r'\+?\d[\d\s-]{7,}\d', text)
    phone = phone_match.group(0).strip() if phone_match else ""
    email_match = re.search(r'[\w\.-]+@[\w\.-]+', text)
    email = email_match.group(0).strip() if email_match else ""
    location = ""
    if email:
        for idx, ln in enumerate(lines):
            if email in ln and idx+1 < len(lines):
                location = lines[idx+1]
                break
    contact = " | ".join(filter(None, [phone, email, location]))

    # --- Section helper ---
    def section(key):
        pat = re.compile(rf"^{key}:?", re.IGNORECASE | re.MULTILINE)
        m = pat.search(text)
        if not m:
            return ""
        start = m.end()
        nxt = re.search(r"^[A-Za-z][A-Za-z &]+:?", text[start:], re.MULTILINE)
        end = start + nxt.start() if nxt else len(text)
        return text[start:end].strip()

    # --- Bullet extractor ---
    def bullets(block):
        items = []
        for ln in block.splitlines():
            m = re.match(r'^[•\-\*]\s*(.*)', ln.strip())
            if m:
                txt = m.group(1).strip()
                if txt:
                    items.append(txt)
        return items

    # --- Summary (try multiple keys) ---
    summary = ""
    for key in ["Professional Summary", "Summary", "Objective", "Profile"]:
        blk = section(key)
        if blk:
            summary = blk
            break

    # --- List sections with fallback keys ---
    def pick_list(keys):
        for key in keys:
            blk = section(key)
            if blk:
                return bullets(blk)
        return []

    responsibilities  = pick_list(["Responsibilities", 
                                   "Roles and Responsibilities", 
                                   "Key Responsibilities"])
    major_clients     = pick_list(["Major Clients", "Clients"])
    certifications    = pick_list(["Certifications"])
    achievements      = pick_list(["Achievements", "Awards"])
    skills            = pick_list(["Skills", "Main competence areas", "Technical Skills"])
    education         = pick_list(["Education", "Academic Qualification"])

    # --- Experience parsing ---
    exp_text = section("Experience") or section("Career and Projects") or text
    date_pat = r"([A-Za-z]{3,9}\s+\d{4})\s*[–-]\s*([A-Za-z]{3,9}\s+\d{4}|Present)"
    segments = []
    for m in re.finditer(date_pat, exp_text):
        seg_start = m.start()
        seg_end   = exp_text.find("\n\n", seg_start)
        seg       = exp_text[seg_start : seg_end if seg_end>0 else len(exp_text)]

        period = f"{m.group(1)} – {m.group(2)}"
        first_line = seg.splitlines()[0]
        parts = first_line.split("–", 1)
        job_title = parts[0].strip()
        company   = parts[1].strip() if len(parts)>1 else ""

        after = [ln.strip() for ln in seg.splitlines()[1:] if ln.strip()]
        tools_list, bullets_list = [], []
        for ln in after:
            if "tools & technology" in ln.lower():
                tools_list = [t.strip() for t in ln.split(":",1)[1].split(",")]
            else:
                bullets_list.append(ln)

        segments.append({
            "period":  period,
            "title":   job_title,
            "company": company,
            "bullets": bullets_list,
            "tools":   tools_list
        })

    # Sort newest→oldest
    def dt_key(x):
        mon, yr = x["period"].split("–")[0].split()
        return int(yr)*100 + MONTHS.get(mon[:3].lower(), 1)
    segments.sort(key=dt_key, reverse=True)

    return {
        "personal": {
            "name":    name,
            "title":   title,
            "contact": contact
        },
        "summary":          summary,
        "responsibilities": responsibilities,
        "major_clients":    major_clients,
        "certifications":   certifications,
        "achievements":     achievements,
        "skills":           skills,
        "experience":       segments,
        "education":        education
    }
