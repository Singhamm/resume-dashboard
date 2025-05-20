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

# Ensure database tables exist
Base.metadata.create_all(bind=engine)

# Configure Jinja2 to load templates from the correct path
BASE_DIR = os.path.dirname(__file__)
TEMPLATE_DIR = os.path.join(BASE_DIR, "app", "templates")
templates = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
templates.globals["datetime"] = datetime

# Streamlit page config
st.set_page_config(page_title="Resume Formatter Demo", layout="wide")
st.title("📝 Resume Formatter Demo (All-in-One)")

# DB session generator
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# File uploader
uploaded_file = st.file_uploader("Upload PDF or DOCX", type=["pdf", "docx"])
if uploaded_file:
    st.info("🔍 Parsing your resume…")

    # Extract text & parse
    text = parser.extract_text(uploaded_file)
    data = parser.parse_resume(text)

    # Save to DB
    db: Session = next(get_db())
    resume_record = crud.create_resume(db, schemas.ResumeCreate(data=data))

    st.success("✅ Parsed & saved!")

    # Show raw JSON\   
    st.subheader("Parsed Data")
    st.json(resume_record)

    # Live HTML Preview
    st.subheader("Live Preview")
    html = templates.get_template("resume.html").render(**resume_record)
    st.components.v1.html(html, height=400, scrolling=True)

    # Download PDF
    st.subheader("Download PDF")
    buffer = BytesIO()
    pdf = Canvas(buffer, pagesize=letter)
    # Title and contact
    pdf.drawString(50, 750, resume_record["personal"].get("name", "Your Name"))
    contact = f"{resume_record['personal'].get('email','')} | {resume_record['personal'].get('phone','')}"
    pdf.drawString(50, 735, contact)
    y = 710
    # Experience entries
    for exp in resume_record.get("experience", []):
        pdf.drawString(50, y, f"{exp.get('title')} at {exp.get('client')}")
        y -= 15
        dates = f"{exp.get('start_date')} - {exp.get('end_date')}"
        pdf.drawString(60, y, dates)
        y -= 15
        for bullet in exp.get("bullets", []):
            pdf.drawString(70, y, f"- {bullet}")
            y -= 15
        y -= 10
        if y < 100:
            pdf.showPage()
            y = 750
    pdf.save()
    buffer.seek(0)
    st.download_button(
        label="📄 Download Resume PDF",
        data=buffer,
        file_name="resume.pdf",
        mime="application/pdf"
    )
