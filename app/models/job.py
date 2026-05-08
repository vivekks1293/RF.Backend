from pydantic import BaseModel
from typing import Optional
from app.models.resume import BaseResume


# ── Analyse models ────────────────────────────────────────────────────────────

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
    status: str
    matchScore: int
    matchLevel: str
    summary: str
    jdSkills: list[str]
    yourSkills: list[str]
    gaps: list[str]
    reason: Optional[str] = None


class AnalyseResponse(BaseModel):
    results: list[JobAnalysisResult]


class TailorJobInput(BaseModel):
    id: str
    label: str
    company: str
    title: str
    rawText: str


class TailorAnalysisHints(BaseModel):
    jdSkills: list[str]
    gaps: list[str]
    matchLevel: str


class TailorRequest(BaseModel):
    resume: BaseResume
    job: TailorJobInput
    analysis: TailorAnalysisHints


class TailorResponse(BaseModel):
    jobId: str
    tailoredResume: BaseResume