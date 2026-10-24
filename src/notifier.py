import os
import sys
import logging
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

load_dotenv()
logger = logging.getLogger(__name__)

REPORT_FILE = Path(__file__).resolve().parent.parent / "data" / "matches_report.md"

def escape_html(text: str) -> str:
    """Escape basic HTML special characters."""
    if not text:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def format_telegram_message(job: Dict[str, Any]) -> str:
    title = escape_html(job.get("title", "Untitled Role"))
    company = escape_html(job.get("company", "Unknown Company"))
    location = escape_html(job.get("location", "Location Not Listed"))
    workload = escape_html(job.get("workload_fit", "Unspecified"))
    seniority = escape_html(job.get("real_seniority", "Junior"))
    fit_score = job.get("fit_score", 0)
    job_url = job.get("job_url", "")
    reason = escape_html(job.get("fit_reason", ""))

    pros = job.get("pros", [])
    if isinstance(pros, str):
        pros = [p.strip() for p in pros.split(";") if p.strip()]

    cons = job.get("cons", [])
    if isinstance(cons, str):
        cons = [c.strip() for c in cons.split(";") if c.strip()]

    remote_badge = "🌐 Remoto" if job.get("is_remote") else "🏢 Presencial / Híbrido"

    msg = (
        f"🎯 <b>Match Score: {fit_score}/100</b>\n"
        f"💼 <b>{title}</b>\n"
        f"🏢 <i>{company}</i>\n\n"
        f"📍 <b>Modalidad:</b> {remote_badge} ({location})\n"
        f"⏱️ <b>Carga horaria:</b> {workload}\n"
        f"🎓 <b>Seniority real:</b> {seniority}\n\n"
        f"💡 <b>Evaluación:</b>\n{reason}\n"
    )

    if pros:
        msg += "\n✅ <b>Puntos a favor:</b>\n"
        for p in pros[:3]:
            msg += f"• {escape_html(p)}\n"

    if cons:
        msg += "\n⚠️ <b>A tener en cuenta:</b>\n"
        for c in cons[:2]:
            msg += f"• {escape_html(c)}\n"

    msg += f"\n🔗 <a href=\"{job_url}\"><b>Ver oferta y postularse 👉</b></a>"
    return msg

def send_telegram_alert(job: Dict[str, Any]) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    if not token or not chat_id or token == "your_telegram_bot_token_here":
        logger.info(f"Telegram not configured. Logging match to local report: {job.get('title')}")
        append_to_markdown_report(job)
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": format_telegram_message(job),
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }

    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            logger.info(f"✅ Telegram alert sent for '{job.get('title')}'")
            return True
        else:
            logger.error(f"Failed to send Telegram alert: {res.status_code} - {res.text}")
            append_to_markdown_report(job)
            return False
    except Exception as e:
        logger.error(f"Exception sending Telegram message: {e}")
        append_to_markdown_report(job)
        return False

def test_telegram_connection() -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    if not token or not chat_id or token == "your_telegram_bot_token_here":
        print("❌ TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing in your .env file!")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "🤖 <b>¡Hola Santi!</b> Tu Job Searching Agent está conectado y funcionando correctamente.",
        "parse_mode": "HTML"
    }

    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            print("✅ Test message successfully sent to your Telegram!")
            return True
        else:
            error_data = res.json() if res.headers.get("content-type") == "application/json" else {}
            description = error_data.get("description", res.text)
            print(f"❌ Telegram API returned error: {res.status_code} - {description}")
            if "chat not found" in description.lower():
                print("\n💡 TIP: En Telegram, un bot no puede enviarte mensajes hasta que le des 'Iniciar' ('Start').")
                print("1. Abre Telegram y busca a tu bot (o entra en https://t.me/Conseguidordelaburos_bot)")
                print("2. Presiona el botón 'Iniciar' o mándale un mensaje como /start")
                print("3. Vuelve a ejecutar este comando.\n")
            return False
    except Exception as e:
        print(f"❌ Connection error testing Telegram: {e}")
        return False

def append_to_markdown_report(job: Dict[str, Any]):
    """Saves high-match jobs to a local markdown file for easy viewing."""
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if REPORT_FILE.exists() else "w"
    with open(REPORT_FILE, mode, encoding="utf-8") as f:
        f.write(f"### [{job.get('fit_score', 0)}/100] {job.get('title')} @ {job.get('company')}\n")
        f.write(f"- **Modalidad:** {'Remoto' if job.get('is_remote') else 'Presencial/Híbrido'} ({job.get('location')})\n")
        f.write(f"- **Carga horaria:** {job.get('workload_fit')}\n")
        f.write(f"- **Seniority:** {job.get('real_seniority')}\n")
        f.write(f"- **Evaluación:** {job.get('fit_reason')}\n")
        f.write(f"- **Link:** [{job.get('job_url')}]({job.get('job_url')})\n\n---\n\n")
