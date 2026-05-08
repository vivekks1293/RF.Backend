from fastapi import APIRouter
from app.models.job import AnalyseRequest, AnalyseResponse, JobAnalysisResult
from app.services.llm_provider import run_llm
from collections import Counter
import asyncio
import json
import re


router = APIRouter(prefix="/api/jobs", tags=["jobs"])

@router.post("/analyse", response_model=AnalyseResponse)
async def analyse_jobs(request: AnalyseRequest):
    tasks = [
        process_single_job(request.resume, job)
        for job in request.jobs
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    mainResult = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            mainResult.append(JobAnalysisResult(
                jobId=request.jobs[i].id,
                status="error",
                matchScore=0,
                matchLevel="none",
                summary="Analysis failed for this job.",
                jdSkills=[],
                yourSkills=[],
                gaps=[],
                reason=str(result)
            ))
        else:
            mainResult.append(result)

    return AnalyseResponse(results=mainResult)



async def process_single_job(resume, job) -> JobAnalysisResult:

    # Step 1 — rule-based validation (instant, no API cost)
    is_valid, reason = validate_jd_rules(job.rawText)

    if not is_valid:
        print(f">>> [VALIDATION] Job '{job.label}' failed rule check: {reason}")
        return JobAnalysisResult(
            jobId=job.id,
            status="invalid_jd",
            matchScore=0,
            matchLevel="none",
            summary="This does not appear to be a valid job description.",
            jdSkills=[],
            yourSkills=[],
            gaps=[],
            reason=reason
        )

    # Step 2 — LLM analysis (validates + scores in one call)
    print(f">>> [LLM] Analysing job: '{job.label}'")
    prompt = build_analyse_prompt(resume, job)

    # run_llm is sync — run in thread pool so parallel execution actually works
    loop = asyncio.get_event_loop()
    raw = await loop.run_in_executor(None, run_llm, prompt)

    # Clean markdown if LLM wraps response in code blocks
    raw = raw.strip()
    if "```" in raw:
        match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw)
        if match:
            raw = match.group(1).strip()

    # Parse JSON safely
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        print(f">>> [ERROR] JSON parse failed for job: '{job.label}'")
        return JobAnalysisResult(
            jobId=job.id,
            status="error",
            matchScore=0,
            matchLevel="none",
            summary="AI returned an unexpected response.",
            jdSkills=[],
            yourSkills=[],
            gaps=[],
            reason="JSON parse failed — AI did not return valid JSON"
        )

    # LLM may also flag invalid (catches subtler cases rules miss)
    return JobAnalysisResult(
        jobId=job.id,
        status="success" if parsed.get("isValidJD") else "invalid_jd",
        matchScore=int(parsed.get("matchScore", 0)),
        matchLevel=parsed.get("matchLevel", "none"),
        summary=parsed.get("summary", ""),
        jdSkills=parsed.get("jdSkills", []),
        yourSkills=parsed.get("yourSkills", []),
        gaps=parsed.get("gaps", []),
        reason=parsed.get("reason")
    )


def validate_jd_rules(text: str) -> tuple[bool, str]:
    """
    Fast rule-based check before sending to LLM.
    Catches obvious garbage without wasting API tokens.

    Returns (is_valid, reason)
    """

    cleaned = text.strip()

    # Check 1 — too short to be a real JD
    if len(cleaned) < 100:
        return False, "Job description is too short to be valid."

    # Check 2 — too few words
    words = cleaned.split()
    if len(words) < 30:
        return False, "Job description has too few words."

    # Check 3 — gibberish detection via average word length
    # Real text averages 4-8 chars per word
    # Random characters or encoded text averages much higher
    avg_word_len = sum(len(w) for w in words) / len(words)
    if avg_word_len > 15:
        return False, "Text does not appear to be readable content."

    # Check 4 — repetition detection
    # If one word makes up more than 20% of all words = spam or repeated text
    word_counts = Counter(w.lower() for w in words)
    most_common_word, most_common_count = word_counts.most_common(1)[0]
    if most_common_count / len(words) > 0.2:
        return False, f"Text appears repetitive or spam-like."

    # Check 5 — must contain at least 3 JD-related keywords
    # Covers English JDs across tech, finance, healthcare, etc.
    jd_keywords = [
        "experience", "skills", "responsibilities", "requirements",
        "qualifications", "role", "position", "team", "candidate",
        "developer", "engineer", "manager", "analyst", "design",
        "work", "job", "apply", "looking", "seeking", "preferred",
        "must", "will", "years", "degree", "knowledge", "ability",
        "communication", "proficient", "strong", "opportunity",
        "salary", "benefits", "remote", "hybrid", "onsite", "join",
        "hiring", "contract", "fulltime", "part-time", "startup"
    ]
    text_lower = cleaned.lower()
    keyword_hits = sum(1 for kw in jd_keywords if kw in text_lower)

    if keyword_hits < 3:
        return False, "Text does not appear to contain job-related content."

    return True, ""



def build_analyse_prompt(resume, job) -> str:

    condensed = condense_resume(resume)

    return f"""
You are an expert resume analyst and career advisor.

[CANDIDATE PROFILE]
{condensed}

[JOB DETAILS]
Company: {job.company}
Title: {job.title}
Job Description:
{job.rawText[:2000]}

[TASK]
1. First determine if the job description is genuine.
   A genuine JD contains role requirements, responsibilities, or skills.
   Random text, gibberish, or unrelated content is not a valid JD.

2. If valid, analyse how well the candidate matches this role.

3. Extract:
   - Key skills mentioned in the JD
   - Candidate skills that match or are transferable
   - Clear skill gaps the candidate has

4. Score the match from 0-100:
   75-100 = Strong match (same or very similar role/stack)
   40-74  = Medium match (same industry, different stack)
   15-39  = Weak match (transferable skills but significant gaps)
   0-14   = No match (unrelated field)

[RULES]
- Return ONLY valid JSON. No markdown. No explanation. No backticks.
- Use double quotes for all strings.
- jdSkills, yourSkills, gaps must be arrays of short skill strings.
- summary must be 1-2 sentences maximum.
- If isValidJD is false, set matchScore to 0 and populate reason.

[OUTPUT FORMAT]
{{
  "isValidJD": true or false,
  "matchScore": 0-100,
  "matchLevel": "strong" or "medium" or "weak" or "none",
  "summary": "1-2 sentence explanation of the match",
  "jdSkills": ["skill1", "skill2"],
  "yourSkills": ["skill1", "skill2"],
  "gaps": ["skill1", "skill2"],
  "reason": null or "explanation if invalid JD"
}}
"""

def condense_resume(resume) -> str:
    """
    Extracts only the relevant parts of the resume for JD matching.
    Reduces token usage by ~40% compared to sending the full resume.
    """
    lines = []

    # Summary
    if resume.summary:
        lines.append(f"SUMMARY:\n{resume.summary}\n")

    # Skills
    if resume.skills:
        lines.append(f"SKILLS:\n{', '.join(resume.skills)}\n")

    # Experience — title, company and bullets only (no IDs, no contact info)
    if resume.experience:
        lines.append("EXPERIENCE:")
        for exp in resume.experience:
            end = exp.endDate or "Present"
            lines.append(f"- {exp.title} at {exp.company} ({exp.startDate} - {end})")
            for bullet in exp.bullets[:4]:  # max 4 bullets per role
                lines.append(f"  . {bullet}")
        lines.append("")

    return "\n".join(lines)
