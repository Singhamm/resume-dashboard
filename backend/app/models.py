from sqlalchemy import Column, Integer, Text
from app.database import Base


class Resume(Base):
    __tablename__ = "resumes"
    id = Column(Integer, primary_key=True, index=True)
    json_data = Column(Text)