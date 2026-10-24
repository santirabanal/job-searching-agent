import os
import sys
import argparse
import logging

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from dotenv import load_dotenv
from src.scraper import fetch_jobs
from src.evaluator import evaluate_job
from src.database import save_job, mark_alerted, get_top_matches
from src.notifier import send_telegram_alert, test_telegram_connection

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("JobAgent")

def run_pipeline(limit_per_query: int = 10, min_score: int = 70, dry_run: bool = False):
    print("=" * 60)
    print("🚀 STARTING JOB SEARCH AGENT (AI Internship / Junior Focus)")
    print(f"🎯 Target: Buenos Aires & Remote | Min Alert Score: {min_score}")
    print("=" * 60)

    # 1. Scrape candidates
    logger.info("Initiating multi-platform search...")
    candidates = fetch_jobs(limit_per_query=limit_per_query)

    if not candidates:
        print("\n🏁 No new unseen jobs found matching initial filters. Try again later or widen criteria.")
        return

    print(f"\n🧠 Evaluating {len(candidates)} new candidates with AI & Student Constraints...\n")

    alert_count = 0
    for idx, job in enumerate(candidates, start=1):
        print(f"[{idx}/{len(candidates)}] Evaluating: {job.get('title')} @ {job.get('company')} ({job.get('location')})")
        
        evaluation = evaluate_job(job)
        
        job["fit_score"] = evaluation.fit_score
        job["real_seniority"] = evaluation.real_seniority
        job["workload_fit"] = evaluation.workload_fit
        job["fit_reason"] = evaluation.fit_reason
        job["pros"] = "; ".join(evaluation.pros)
        job["cons"] = "; ".join(evaluation.cons)

        print(f"   -> Score: {evaluation.fit_score}/100 | Workload: {evaluation.workload_fit} | Rec: {evaluation.recommendation}")

        if not dry_run:
            # Save to SQLite
            save_job(job)

            # Check if alert threshold is met
            if evaluation.fit_score >= min_score:
                print(f"   🔔 High match! Sending notification...")
                sent = send_telegram_alert(job)
                if sent:
                    mark_alerted(job["id"])
                    alert_count += 1

    print("\n" + "=" * 60)
    print(f"🎉 Run Complete! Processed: {len(candidates)} jobs | Alerts Sent: {alert_count}")
    print("=" * 60)

def show_report(limit: int = 10):
    matches = get_top_matches(limit=limit)
    if not matches:
        print("No jobs currently in database.")
        return

    print("\n🏆 TOP MATCHES CURRENTLY IN DATABASE:")
    print("-" * 80)
    for m in matches:
        print(f"[{m['fit_score']}/100] {m['title']} @ {m['company']}")
        print(f"    📍 {m['location']} | ⏱️ {m['workload_fit']} | 🎓 {m['real_seniority']}")
        print(f"    💡 {m['fit_reason']}")
        print(f"    🔗 {m['job_url']}")
        print("-" * 80)

def main():
    parser = argparse.ArgumentParser(description="AI Job Searching Agent")
    parser.add_argument("--test-telegram", action="store_true", help="Send a test message to Telegram")
    parser.add_argument("--limit", type=int, default=5, help="Results to scrape per query")
    parser.add_argument("--min-score", type=int, default=int(os.getenv("MIN_ALERT_SCORE", 70)), help="Score threshold for alerts")
    parser.add_argument("--dry-run", action="store_true", help="Evaluate without saving or alerting")
    parser.add_argument("--report", action="store_true", help="Display top matches from database")

    args = parser.parse_args()

    if args.test_telegram:
        test_telegram_connection()
    elif args.report:
        show_report()
    else:
        run_pipeline(limit_per_query=args.limit, min_score=args.min_score, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
