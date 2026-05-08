from fastapi import APIRouter
from app.models.job import TailorRequest, TailorResponse
from app.models.resume import BaseResume, ContactInfo, ExperienceEntry, EducationEntry
from app.services.llm_provider import run_llm
import json
import re

router = APIRouter(prefix="/api/tailor", tags=["tailor"])

@router.post("/resume", response_model=TailorResponse)
async def tailor_resume(request: TailorRequest):
    """
    Takes the base resume + job description + analysis hints.
    Returns a tailored resume with rewritten bullets and summary.
    Only bullets and summary are changed — all other fields stay identical.
    """
    prompt = build_tailor_prompt(request)

    raw = run_llm(prompt)

    tailored = parse_tailor_response(raw, request)

    return TailorResponse(
        jobId=request.job.id,
        tailoredResume=tailored
    )
def build_tailor_prompt(request: TailorRequest) -> str:

    resume   = request.resume
    job      = request.job
    analysis = request.analysis

    # Serialise the full resume as JSON so LLM knows exact structure to return
    resume_json = json.dumps({
        "name": resume.name,
        "contact": {
            "email": resume.contact.email,
            "phone": resume.contact.phone,
            "linkedIn": resume.contact.linkedIn,
            "location": resume.contact.location,
        },
        "summary": resume.summary,
        "skills": resume.skills,
        "experience": [
            {
                "id": exp.id,
                "company": exp.company,
                "title": exp.title,
                "startDate": exp.startDate,
                "endDate": exp.endDate,
                "bullets": exp.bullets
            }
            for exp in resume.experience
        ],
        "education": [
            {
                "id": edu.id,
                "institution": edu.institution,
                "degree": edu.degree,
                "field": edu.field,
                "graduationYear": edu.graduationYear
            }
            for edu in resume.education
        ],
        "parseConfidence": resume.parseConfidence
    }, indent=2)

    return f"""
You are an expert resume writer and career coach.
Your task is to tailor a resume for a specific job description.

[TARGET JOB]
Company: {job.company}
Title: {job.title}
Label: {job.label}

[FULL JOB DESCRIPTION]
{job.rawText[:3000]}

[ANALYSIS HINTS]
Key skills to emphasise: {', '.join(analysis.jdSkills)}
Candidate gaps to bridge where possible: {', '.join(analysis.gaps)}
Match level: {analysis.matchLevel}

[ORIGINAL RESUME]
{resume_json}

[YOUR TASK]
Rewrite the resume to better match the job description above.

[STRICT RULES — READ CAREFULLY]
1. DO NOT change name, contact info, company names, job titles, or dates
2. DO NOT add skills, experience, or achievements that are not in the original
3. DO NOT remove any experience entries or education entries
4. DO NOT add new bullet points — only rewrite existing ones
5. ONLY rewrite: experience bullet points and the summary paragraph
6. Use keywords from the job description NATURALLY — do not keyword stuff
7. Keep the same number of bullet points per experience entry
8. Prioritise bullets that are most relevant to this role
9. Bridge gaps by highlighting transferable skills where genuinely applicable
10. Return ONLY valid JSON — no markdown, no explanation, no backticks

[OUTPUT FORMAT]
Return the complete resume JSON in exactly the same structure as the original.
Only the "summary" and "bullets" fields inside "experience" should be different.
Everything else must be identical to the original.

Return ONLY this JSON structure:
{{
  "name": "same as original",
  "contact": {{same as original}},
  "summary": "rewritten to target this role",
  "skills": [same as original],
  "experience": [
    {{
      "id": "same as original",
      "company": "same as original",
      "title": "same as original",
      "startDate": "same as original",
      "endDate": "same as original",
      "bullets": ["rewritten bullet 1", "rewritten bullet 2"]
    }}
  ],
  "education": [same as original],
  "parseConfidence": same as original
}}
"""

def parse_tailor_response(raw: str, request: TailorRequest) -> BaseResume:
    """
    Parses the LLM response into a BaseResume.
    Falls back to the original resume if parsing fails.
    """
    raw = raw.strip()

    # Strip markdown code blocks if LLM wraps response
    if "```" in raw:
        match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw)
        if match:
            raw = match.group(1).strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f">>> [TAILOR] JSON parse failed: {e}")
        print(f">>> [TAILOR] Falling back to original resume")
        return request.resume

    try:
        # Build tailored resume — preserve original structure
        # only allow summary and bullets to change
        original = request.resume

        tailored_experience = []
        for i, exp in enumerate(original.experience):
            # Get rewritten bullets from LLM response
            # Fall back to original bullets if not found
            try:
                llm_bullets = data["experience"][i]["bullets"]
                # Validate — must be list of strings, same count
                if (
                    isinstance(llm_bullets, list)
                    and len(llm_bullets) == len(exp.bullets)
                    and all(isinstance(b, str) for b in llm_bullets)
                ):
                    bullets = llm_bullets
                else:
                    print(f">>> [TAILOR] Bullet count mismatch for {exp.company}, using original")
                    bullets = exp.bullets
            except (IndexError, KeyError):
                bullets = exp.bullets

            tailored_experience.append(ExperienceEntry(
                id=exp.id,                    # preserved
                company=exp.company,          # preserved
                title=exp.title,              # preserved
                startDate=exp.startDate,      # preserved
                endDate=exp.endDate,          # preserved
                bullets=bullets               # rewritten
            ))

        # Get rewritten summary — fall back to original if missing
        new_summary = data.get("summary", original.summary)
        if not isinstance(new_summary, str) or len(new_summary.strip()) < 10:
            new_summary = original.summary

        return BaseResume(
            name=original.name,                    # preserved
            contact=original.contact,              # preserved
            summary=new_summary,                   # rewritten
            skills=original.skills,                # preserved
            experience=tailored_experience,        # bullets rewritten
            education=original.education,          # preserved
            parseConfidence=original.parseConfidence,
            sourceFile=None
        )

    except Exception as e:
        print(f">>> [TAILOR] Failed to build tailored resume: {e}")
        return request.resume