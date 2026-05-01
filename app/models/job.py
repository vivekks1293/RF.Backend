from pydantic import BaseModel
from typing import Optional
from app.models.resume import BaseResume


class JobInput(BaseModel):
    id: str
    label: str
    company: str
    title: str
    rawText: str
    sourceUrl: Optional[str] = None


class AnalyseRequest(BaseModel):
    resume: BaseResume
    jobs: list[JobInput]


class JobAnalysisResult(BaseModel):
    jobId: str
    status: str           # "success" | "invalid_jd" | "error"
    matchScore: int       # 0-100
    matchLevel: str       # "strong" | "medium" | "weak" | "none"
    summary: str
    jdSkills: list[str]
    yourSkills: list[str]
    gaps: list[str]
    reason: Optional[str] = None  # populated if invalid_jd


class AnalyseResponse(BaseModel):
    results: list[JobAnalysisResult]