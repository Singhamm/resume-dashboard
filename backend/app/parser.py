import io
import re
from pdfminer.high_level import extract_text as extract_pdf_text
from docx import Document
from rapidfuzz import fuzz

# Month mapping for date sorting
MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "may": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12
}

def extract_text(file) -> str:
    """
    Extract text from FastAPI UploadFile or Streamlit UploadedFile.
    """
    try:
        content = file.file.read()
    except AttributeError:
        file.seek(0)
        content = file.read()

    name = getattr(file, 'filename', None) or getattr(file, 'name', '')
    name = name.lower()
    if name.endswith('.pdf'):
        return extract_pdf_text(io.BytesIO(content))
    elif name.endswith('.docx') or name.endswith('.doc'):
        doc = Document(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs)
    else:
        try:
            return content.decode('utf-8', errors='ignore')
        except:
            return str(content)

def parse_resume(text: str) -> dict:
    """
    Section-based parser producing a rich JSON structure:
      - personal: name, title, contact
      - summary
      - responsibilities, major_clients, certifications, achievements, skills
      - experience: list of {period, title, company, bullets, tools}
      - education
    """
    # 1) Name = first non-empty line
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    name = lines[0] if lines else ""

    # 2) Helper to pull out a block under a heading
    def section(key):
        pat = re.compile(rf"^{key}:?", re.IGNORECASE | re.MULTILINE)
        m = pat.search(text)
        if not m:
            return ""
        start = m.end()
        # find next heading
        nxt = re.search(r"^[A-Za-z][A-Za-z &]+:?", text[start:], re.MULTILINE)
        end = start + nxt.start() if nxt else len(text)
        return text[start:end].strip()

    summary = section("Professional Summary") or section("Objective")

    def bullets(block):
        return [l.strip("•*- ").strip() 
                for l in block.splitlines() if l.strip().startswith(("•","-","*"))]

    responsibilities  = bullets(section("Responsibilities"))
    major_clients     = bullets(section("Major Clients"))
    certifications    = bullets(section("Certifications"))
    achievements      = bullets(section("Achievements"))
    skills            = bullets(section("Main competence areas") or section("Skills"))
    education         = bullets(section("Education"))

    # 3) Experience: look under "Career and projects"
    exp_text = section("Career and projects") or text
    date_pat = r"([A-Za-z]{3,9}\s+\d{4})\s*[–-]\s*([A-Za-z]{3,9}\s+\d{4}|Present)"
    segments = []
    for m in re.finditer(date_pat, exp_text):
        seg_start = m.start()
        seg_end = exp_text.find("\n\n", seg_start)
        seg = exp_text[seg_start : (seg_end if seg_end>0 else len(exp_text))]

        period = f"{m.group(1)} – {m.group(2)}"
        first_line = seg.splitlines()[0]
        parts = first_line.split("–", 1)
        title   = parts[0].strip()
        company = parts[1].strip() if len(parts)>1 else ""

        lines_after = [l.strip() for l in seg.splitlines()[1:] if l.strip()]
        tools = []
        bullets_list = []
        for line in lines_after:
            if "tools & technology" in line.lower():
                tools = [t.strip() for t in line.split(":",1)[1].split(",")]
            else:
                bullets_list.append(line)

        segments.append({
            "period":   period,
            "title":    title,
            "company":  company,
            "bullets":  bullets_list,
            "tools":    tools
        })

    # sort newest → oldest
    def keyfn(x):
        mon, yr = x["period"].split("–")[0].split()
        return int(yr)*100 + MONTHS.get(mon[:3].lower(), 1)
    segments.sort(key=keyfn, reverse=True)

    return {
        "personal": {
            "name":    name,
            "title":   "",       # you can add logic to parse title if present
            "contact": ""        # same for email/phone
        },
        "summary":        summary,
        "responsibilities": responsibilities,
        "major_clients":  major_clients,
        "certifications": certifications,
        "achievements":   achievements,
        "skills":         skills,
        "experience":     segments,
        "education":      education
    }
