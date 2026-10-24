import sys
import logging
import yaml
from pathlib import Path
from typing import List, Dict, Any
from jobspy import scrape_jobs
from src.database import generate_job_id, is_seen

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "search_config.yaml"

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found at {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def is_excluded_title(title: str, exclusions: List[str]) -> bool:
    title_lower = title.lower()
    for excl in exclusions:
        if excl.lower() in title_lower:
            return True
    return False

def fetch_jobs(limit_per_query: int = 10) -> List[Dict[str, Any]]:
    config = load_config()
    settings = config.get("settings", {})
    boards = settings.get("boards", ["linkedin", "indeed", "glassdoor", "google"])
    hours_old = settings.get("hours_old", 72)
    exclusions = config.get("title_exclusions", [])

    candidates: List[Dict[str, Any]] = []
    seen_in_batch = set()

    # 1. Local Searches (Buenos Aires)
    local_cfg = config.get("local_searches", {})
    local_location = local_cfg.get("location", "Buenos Aires, Argentina")
    for query in local_cfg.get("queries", []):
        logger.info(f"🔎 Scraping Local: '{query}' in '{local_location}'...")
        try:
            df = scrape_jobs(
                site_name=boards,
                search_term=query,
                location=local_location,
                results_wanted=limit_per_query,
                hours_old=hours_old,
                country_indeed="Argentina"
            )
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    process_row(row, exclusions, seen_in_batch, candidates, is_remote_default=False)
        except Exception as e:
            logger.warning(f"Error scraping query '{query}': {e}")

    # 2. Remote Searches
    remote_cfg = config.get("remote_searches", {})
    for query in remote_cfg.get("queries", []):
        logger.info(f"🔎 Scraping Remote: '{query}'...")
        try:
            df = scrape_jobs(
                site_name=boards,
                search_term=query,
                is_remote=True,
                results_wanted=limit_per_query,
                hours_old=hours_old,
            )
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    process_row(row, exclusions, seen_in_batch, candidates, is_remote_default=True)
        except Exception as e:
            logger.warning(f"Error scraping remote query '{query}': {e}")

    logger.info(f"✨ Found {len(candidates)} new candidates after deduplication and title filtering.")
    return candidates

def process_row(row, exclusions: List[str], seen_in_batch: set, candidates: List[Dict[str, Any]], is_remote_default: bool = False):
    title = str(row.get("title") or "").strip()
    company = str(row.get("company") or "").strip()
    job_url = str(row.get("job_url") or "").strip()
    description = str(row.get("description") or "").strip()

    if not title or not job_url:
        return

    # Check title exclusions (e.g. Senior, Lead)
    if is_excluded_title(title, exclusions):
        return

    job_id = generate_job_id(title, company, job_url)
    if job_id in seen_in_batch:
        return
    seen_in_batch.add(job_id)

    # Check if already in SQLite DB
    if is_seen(job_id):
        return

    # Handle is_remote detection
    is_remote = bool(row.get("is_remote")) if "is_remote" in row and row.get("is_remote") is not None else is_remote_default
    loc = str(row.get("location") or "")
    if "remote" in loc.lower() or "remoto" in loc.lower():
        is_remote = True

    candidates.append({
        "id": job_id,
        "site": str(row.get("site") or "unknown"),
        "title": title,
        "company": company,
        "location": loc,
        "job_url": job_url,
        "description": description,
        "date_posted": str(row.get("date_posted") or ""),
        "is_remote": is_remote
    })
