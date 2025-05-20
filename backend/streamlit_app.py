import streamlit as st
from sqlalchemy.orm import Session
from io import BytesIO
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from app import parser, crud, schemas
from app.database import SessionLocal, Base, engine

# Create tables if they don’t exist
Base.metadata.create_all(bind=engine)

# Jinja2 template setup
templates = Environment(loader=FileSystemLoader("app/templates"))

st.set_page_config(page_title="Resume Demo", layout="wide")
st.title("📝 Resume Formatter Demo (All-in-One)")

# DB session factory
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

uploaded_file = st.file_uploader("Upload PDF or DOCX", type=["pdf", "docx"])
if uploaded_file:
    st.info("Parsing your resume…")

    # 1. Extract & parse locally
    text = parser.extract_text(uploaded_file)
    data = parser.parse_resume(text)

    # 2. Save to DB
    db: Session = next(get_db())
    resume = crud.create_resume(db, schemas.ResumeCreate(data=data))

    st.success("Parsed & saved successfully!")

    # 3. Show JSON
    st.subheader("Parsed Data")
    st.json(resume)

    # 4. Live HTML Preview
    st.subheader("Live Preview")
    html = templates.get_template("resume.html").render(**resume)
    st.components.v1.html(html, height=400, scrolling=True)

    # 5. Download PDF
    st.subheader("Download PDF")
    pdf_bytes = HTML(string=html).write_pdf()
    st.download_button(
        label="📄 Download PDF",
        data=pdf_bytes,
        file_name="resume.pdf",
        mime="application/pdf"
    )
