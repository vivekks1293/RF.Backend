from pydantic import BaseModel
from typing import Optional

class ContactInfo(BaseModel):
    email: str
    phone: Optional[str] = None
    linkedIn: Optional[str] = None
    location: Optional[str] = None

class ExperienceEntry(BaseModel):
    id: str
    company: str
    title: str
    startDate: str
    endDate: Optional[str] = None
    bullets: list[str]

class EducationEntry(BaseModel):
    id: str
    institution: str
    degree: str
    field: Optional[str]
    gradyear: str

class BaseResume(BaseModel):
    name: str
    contact: ContactInfo
    summary: str
    skills: list[str]
    experience: list[ExperienceEntry]
    education: list[EducationEntry]
    parseConfidence: float = 1.0
    sourceFile: Optional[str] = None