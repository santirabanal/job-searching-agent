import sqlite3
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "jobs.db"

def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        site TEXT,
        title TEXT,
        company TEXT,
        location TEXT,
        job_url TEXT,
        description TEXT,
        date_posted TEXT,
        is_remote BOOLEAN,
        fit_score INTEGER DEFAULT 0,
        real_seniority TEXT,
        workload_fit TEXT,
        fit_reason TEXT,
        pros TEXT,
        cons TEXT,
        alerted INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs (fit_score DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_alerted ON jobs (alerted)")
    conn.commit()
    conn.close()

def generate_job_id(title: str, company: str, job_url: Optional[str] = None) -> str:
    """Generate a stable deterministic ID based on title, company, and URL."""
    base = f"{str(title).lower().strip()}_{str(company).lower().strip()}"
    if job_url:
        base += f"_{job_url.split('?')[0].strip()}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]

def is_seen(job_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def save_job(job_data: Dict[str, Any]):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO jobs (
        id, site, title, company, location, job_url, description,
        date_posted, is_remote, fit_score, real_seniority,
        workload_fit, fit_reason, pros, cons, alerted
    ) VALUES (
        :id, :site, :title, :company, :location, :job_url, :description,
        :date_posted, :is_remote, :fit_score, :real_seniority,
        :workload_fit, :fit_reason, :pros, :cons, :alerted
    )
    """, {
        "id": job_data["id"],
        "site": job_data.get("site", "unknown"),
        "title": job_data.get("title", ""),
        "company": job_data.get("company", ""),
        "location": job_data.get("location", ""),
        "job_url": job_data.get("job_url", ""),
        "description": job_data.get("description", ""),
        "date_posted": str(job_data.get("date_posted", "")),
        "is_remote": bool(job_data.get("is_remote", False)),
        "fit_score": int(job_data.get("fit_score", 0)),
        "real_seniority": job_data.get("real_seniority", "Unknown"),
        "workload_fit": job_data.get("workload_fit", "Unknown"),
        "fit_reason": job_data.get("fit_reason", ""),
        "pros": job_data.get("pros", ""),
        "cons": job_data.get("cons", ""),
        "alerted": int(job_data.get("alerted", 0))
    })
    conn.commit()
    conn.close()

def mark_alerted(job_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE jobs SET alerted = 1 WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()

def get_unalerted(min_score: int = 70) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM jobs 
    WHERE fit_score >= ? AND alerted = 0
    ORDER BY fit_score DESC
    """, (min_score,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_top_matches(limit: int = 15) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM jobs 
    ORDER BY fit_score DESC, created_at DESC 
    LIMIT ?
    """, (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

# Initialize DB when module loads
init_db()
