import json
from sqlalchemy.orm import Session
from app import models, schemas

# In-memory & DB-based CRUD for resumes

def create_resume(db: Session, resume: schemas.ResumeCreate):
    db_obj = models.Resume(json_data=json.dumps(resume.data))
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return {"id": db_obj.id, **resume.data}


def get_resume(db: Session, resume_id: int):
    db_obj = db.query(models.Resume).filter(models.Resume.id == resume_id).first()
    if not db_obj:
        return None
    return {"id": db_obj.id, **json.loads(db_obj.json_data)}