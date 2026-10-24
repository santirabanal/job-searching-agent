import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

load_dotenv()
logger = logging.getLogger(__name__)

PROFILE_PATH = Path(__file__).resolve().parent.parent / "data" / "my_profile.md"

class JobEvaluation(BaseModel):
    fit_score: int = Field(ge=0, le=100, description="Match score from 0 to 100")
    real_seniority: str = Field(description="Detected seniority level: 'Intern/Trainee', 'Junior', 'Mid-level', or 'Senior (mislabeled)'")
    workload_fit: str = Field(description="Workload compatibility: 'Part-time / 4h / Pasantía (Ideal)', 'Flexible for students', 'Strict Full-Time 40h+', or 'Unspecified'")
    fit_reason: str = Field(description="Concise 1-2 sentence summary of why this role fits or does not fit")
    pros: list[str] = Field(default_factory=list, description="Top 2-3 positive matches or opportunities")
    cons: list[str] = Field(default_factory=list, description="Top 1-3 caveats, blockers, or mismatches")
    recommendation: str = Field(description="'Apply', 'Consider', or 'Skip'")

def load_candidate_profile() -> str:
    if PROFILE_PATH.exists():
        return PROFILE_PATH.read_text(encoding="utf-8")
    return "University student looking for an AI/ML internship or Junior position, ideally 4 hours daily (20h/week), in Buenos Aires or Remote."

def is_infeasible_location(job: Dict[str, Any]) -> bool:
    """Detect if a job requires physical presence outside Argentina."""
    if job.get("is_remote"):
        return False
    loc = str(job.get("location", "")).lower()
    if any(k in loc for k in ["remote", "remoto", "anywhere", "worldwide"]):
        return False
    if any(k in loc for k in ["buenos aires", "argentina", "caba", "gba"]):
        return False
    # If location is explicitly a foreign city/country and NOT remote
    if any(k in loc for k in ["usa", "united states", "ca, ", "ny, ", "md, ", "tx, ", "fl, ", "wa, ", "spain", "madrid", "barcelona", "uk", "london", "brazil", "chile", "colombia", "mexico"]):
        return True
    return False

def heuristic_evaluation(job: Dict[str, Any]) -> JobEvaluation:
    """Fallback evaluator when GEMINI_API_KEY is not available or rate limited."""
    text = (job.get("title", "") + " " + job.get("description", "")).lower()
    
    # Check if location is incompatible (on-site in USA/Europe for student in BA)
    if is_infeasible_location(job):
        return JobEvaluation(
            fit_score=20,
            real_seniority="Intern/Junior",
            workload_fit="On-site Abroad",
            fit_reason="Location mismatch: In-person role outside Argentina without verified remote option.",
            pros=[],
            cons=["Requires physical relocation outside Argentina"],
            recommendation="Skip"
        )

    score = 50
    pros = []
    cons = []
    workload = "Unspecified"
    seniority = "Junior"

    # Workload heuristics
    if any(k in text for k in ["pasantía", "pasantia", "intern", "internship", "trainee", "part-time", "part time", "medio tiempo", "20 horas", "4 horas"]):
        score += 25
        workload = "Part-time / 4h / Pasantía (Ideal)"
        seniority = "Intern/Trainee"
        pros.append("Matches student / pasantía / part-time availability")
    else:
        cons.append("Workload not explicitly listed as part-time/pasantía")

    # Tech heuristics
    if any(k in text for k in ["python", "ai", "machine learning", "llm", "inteligencia artificial", "genai"]):
        score += 15
        pros.append("Directly mentions Python / AI / Machine Learning")
    
    # Location
    if job.get("is_remote") or "remote" in text or "remoto" in text:
        score += 10
        pros.append("Offers remote work")
    elif "buenos aires" in text:
        pros.append("Located in Buenos Aires")

    # Anti-bait
    if any(k in text for k in ["3+ years", "4+ years", "5+ years", "3 a 5 años"]):
        score -= 30
        seniority = "Mid/Senior (demands 3+ years)"
        cons.append("Asks for 3+ years experience despite title")

    score = max(0, min(100, score))
    rec = "Apply" if score >= 75 else ("Consider" if score >= 50 else "Skip")
    
    return JobEvaluation(
        fit_score=score,
        real_seniority=seniority,
        workload_fit=workload,
        fit_reason=f"Heuristic estimate: {seniority} role, workload: {workload}.",
        pros=pros,
        cons=cons,
        recommendation=rec
    )

def evaluate_job(job: Dict[str, Any]) -> JobEvaluation:
    # First check physical location blocker
    if is_infeasible_location(job):
        return JobEvaluation(
            fit_score=15,
            real_seniority="Intern/Junior",
            workload_fit="On-site abroad",
            fit_reason=f"Physical location blocker: Requires on-site presence in {job.get('location')} (candidate is in Buenos Aires).",
            pros=[],
            cons=[f"Requires on-site attendance in {job.get('location')}"],
            recommendation="Skip"
        )

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "your_gemini_api_key_here":
        return heuristic_evaluation(job)

    try:
        from google import genai
        from google.genai import types

        profile_text = load_candidate_profile()
        client = genai.Client(api_key=api_key)

        prompt = f"""
You are an expert AI Career Coach evaluating a job opening specifically for a university student.

=== CANDIDATE PROFILE & CONSTRAINTS ===
{profile_text}

=== JOB DETAILS TO EVALUATE ===
Title: {job.get('title')}
Company: {job.get('company')}
Location: {job.get('location')} (Is Remote: {job.get('is_remote')})
Job URL: {job.get('job_url')}

Description:
{job.get('description', '')[:3000]}

=== EVALUATION CRITERIA ===
1. LOCATION FEASIBILITY (CRITICAL):
   - The candidate is based in Buenos Aires, Argentina.
   - VALID: Remote (Worldwide, LATAM, or US-remote with international contractors) OR Buenos Aires (Hybrid/Onsite).
   - INVALID: Strictly on-site roles in USA, Europe, or other foreign cities. If the job is on-site in a foreign city, penalize fit_score heavily (< 40) and recommend 'Skip'.
2. WORKLOAD & STUDENT FIT:
   - BEST CASE: 4 hours daily / 20 hours weekly / "Pasantía" / "Part-time" / flexible for university classes.
   - Good: Junior role with flexible hours.
   - Bad: Strict 9-hour on-site full-time job incompatible with attending classes.
3. SENIORITY REALITY CHECK:
   - Genuine Intern/Junior role vs. "bait" demanding 3+ years of commercial experience.
4. TECH STACK:
   - Alignment with Python, AI/ML, LLM, or Data Science.

Return a structured JSON output matching the schema.
"""

        # Small pause to respect free tier RPM limits
        time.sleep(2)

        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=JobEvaluation,
                temperature=0.2
            )
        )

        data = json.loads(response.text)
        return JobEvaluation(**data)

    except Exception as e:
        logger.warning(f"Gemini API rate limit or error for '{job.get('title')}': {e}. Using heuristics.")
        return heuristic_evaluation(job)
