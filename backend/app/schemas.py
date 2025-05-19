from pydantic import BaseModel
from typing import Dict, Any


class ResumeCreate(BaseModel):
    data: Dict[str, Any]


class Resume(BaseModel):
    id: int
    data: Dict[str, Any]

    class Config:
        orm_mode = True