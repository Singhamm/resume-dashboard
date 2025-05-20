import os
import streamlit as st
from datetime import datetime
from sqlalchemy.orm import Session
from io import BytesIO
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import letter
from jinja2 import Environment, FileSystemLoader

from app import parser, crud, schemas
from app.database import SessionLocal, Base, engine

# 1. Ensure DB tables exist
Base.metadata.create_all(bind=engine)

# 2. Configure Jinja2 and inject datetime
BASE_DIR = os.path.dirname(__file__)                           # points to backend/
TEMPLATE_DIR = os.path.join(BASE_DIR, "app", "templates")      # backend/app/templates
templates = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
templates.globals["datetime"] = datetime                       # now {{ datetime.utcnow() }} works

# 3. Streamlit page config
st.set_page_config(page_title="Resume Formatter Demo", layout="wide")
st.title("📝 Resume Formatter Demo (All-in-One)")

# DB session generator
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 4. File uploader UI
uploaded_file = st.file_uploader("Upload PDF or DOCX", type=["pdf", "docx"])
if not uploaded_file:
    st.info("📂 Please upload a resume to get started.")
else:
    st.info("🔍 Parsing your resume…")

    # 5. Extract text & parse
    text = parser.extract_text(uploaded_file)
    data = parser.parse_resume(text)

    # 6. Save to DB
    db: Session = next(get_db())
    resume_record = crud.create_resume(db, schemas.ResumeCreate(data=data))

    st.success("✅ Parsed & saved!")

    # 7. Show raw JSON
    st.subheader("Parsed Data")
    st.json(resume_record)

    # 8. Live HTML Preview
    st.subheader("Live Preview")
    html = templates.get_template("resume.html").render(**resume_record)
    st.components.v1.html(html, height=400, scrolling=True)

    # 9. Download as PDF
    st.subheader("Download PDF")
    buffer = BytesIO()
    pdf = Canvas(buffer, pagesize=letter)

    # Header
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, 750, resume_record["personal"].get("name", "Your Name"))
    pdf.setFont("Helvetica", 10)
    contact = resume_record["personal"].get("contact", "")
    pdf.drawString(50, 735, contact)

    # Experience entries
    y = 710
    for exp in resume_record.get("experience", []):
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(50, y, f"{exp['period']} | {exp['title']}, {exp['company']}")
        y -= 15
        pdf.setFont("Helvetica", 10)
        for b in exp.get("bullets", []):
            pdf.drawString(60, y, f"• {b}")
            y -= 12
        if exp.get("tools"):
            tools_line = "Tools & Tech: " + ", ".join(exp["tools"])
            pdf.drawString(60, y, tools_line)
            y -= 15
        y -= 10
        if y < 100:
            pdf.showPage()
            y = 750

    # Footer with date
    pdf.setFont("Helvetica-Oblique", 8)
    footer_text = f"Printed on {datetime.utcnow().strftime('%d %b %Y')}"
    pdf.drawString(400, 20, footer_text)

    pdf.save()
    buffer.seek(0)

    st.download_button(
        label="📄 Download Resume PDF",
        data=buffer,
        file_name="resume.pdf",
        mime="application/pdf"
    )
