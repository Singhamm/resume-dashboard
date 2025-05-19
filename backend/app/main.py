from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session
from app import crud, parser, schemas
from app.database import Base, engine, get_db
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import io

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize app & templates
app = FastAPI(title="Resume Dashboard API")
templates = Environment(loader=FileSystemLoader("app/templates"))

@app.post("/upload-resume")
def upload_resume(
    file: UploadFile = File(...), db: Session = Depends(get_db)
):
    text = parser.extract_text(file)
    data = parser.parse_resume(text)
    resume = crud.create_resume(db, schemas.ResumeCreate(data=data))
    return resume

@app.get("/preview/{resume_id}", response_class=HTMLResponse)
def preview_resume(
    resume_id: int, db: Session = Depends(get_db)
):
    record = crud.get_resume(db, resume_id)
    if not record:
        raise HTTPException(status_code=404, detail="Resume not found")
    html = templates.get_template("resume.html").render(**record)
    return HTMLResponse(html)

@app.post("/generate-pdf/{resume_id}")
def generate_pdf(
    resume_id: int, db: Session = Depends(get_db)
):
    record = crud.get_resume(db, resume_id)
    if not record:
        raise HTTPException(status_code=404, detail="Resume not found")
    html = templates.get_template("resume.html").render(**record)
    pdf_bytes = HTML(string=html).write_pdf()
    return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf")