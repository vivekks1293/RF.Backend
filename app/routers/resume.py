from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
from app.models.resume import BaseResume, ContactInfo, EducationEntry, ExperienceEntry
import pdfplumber
import io
import docx 
from dotenv import load_dotenv
from app.services.llm_provider import run_llm
import json
import re

load_dotenv()

router = APIRouter(prefix="/api/resume", tags = ["resume"])

@router.post("/parse")

async def parse_resume(file:UploadFile = File(...)):
    contents = await file.read()
    text = ""

    if file.filename.endswith(".pdf"):
        with pdfplumber.open(io.BytesIO(contents)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

    elif file.filename.endswith(".txt"):
        text = contents.decode("utf-8")

    elif file.filename.endswith(".docx"):
        doc = docx.Document(io.BytesIO(contents))
        for para in doc.paragraphs:
            if para.text.strip():
                text += para.text + "\n"
    resumePromt = getFinalPromt(text)
    raw = run_llm(resumePromt)
    raw = raw.strip()
    if "```" in raw:
        match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw)
        if match:
            raw = match.group(1).strip()

    parsed = json.loads(raw)

    allowed_fields = {
        "name", "contact", "summary",
        "skills", "experience", "education",
        "parseConfidence", "sourceFile"
    }
    parsed = {k: v for k, v in parsed.items() if k in allowed_fields}
    return parsed

def getFinalPromt(text: str) -> dict:

    finalPrompt = f"""
You are a resume parser. Extract the resume text below into JSON.

IMPORTANT RULES:
- Return ONLY valid JSON. No explanation. No markdown. No code blocks. No backticks.
- Use double quotes for all keys and string values.
- Only include these fields: name, contact, summary, skills, experience, education, parseConfidence.
- Do not add any extra fields like projects, certifications, achievements.
- parseConfidence should be a number between 0 and 1.

Follow EXACTLY this structure:
{json.dumps(exampleJson(), indent=2)}

Resume text:
{text}
"""
    return finalPrompt

   


def exampleJson():
    return {
        "name": "John Doe",
        "contact": {
            "email": "john@email.com",
            "phone": "+1 555 000 0000",
            "linkedin": "linkedin.com/in/johndoe",
            "location": "New York, NY"
        },
        "summary": "Software engineer with 5 years experience...",
        "skills": ["Python", "FastAPI", "Docker"],
        "experience": [
            {
                "id": "exp-1",
                "company": "Acme Corp",
                "title": "Senior Engineer",
                "startDate": "Jan 2020",
                "endDate": "Present",
                "bullets": ["Built X that improved Y by Z%"]
            }
        ],
        "education": [
            {
                "id": "edu-1",
                "institution": "MIT",
                "degree": "B.S.",
                "field": "Computer Science",
                "graduationYear": "2018"
            }
        ],
        "parseConfidence": 0.95
    }