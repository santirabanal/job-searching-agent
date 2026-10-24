# 🤖 AI Job Searching Agent (Internship & Junior Focus)

An intelligent agent designed to continuously hunt for **AI / Machine Learning internships (4 hours daily / pasantías)** and **Junior AI roles**, specifically tuned for university students in **Buenos Aires (Hybrid/Presencial)** and **Worldwide / LATAM (Remote)**.

---

## ⚡ How It Works

1. **Multi-Source Scraping**: Scrapes **LinkedIn, Indeed, Glassdoor, and Google Jobs** simultaneously without requiring paid scraping APIs.
2. **Rule-Based Pre-Filtering**: Instantly drops misaligned postings (e.g. "Senior", "Lead", "10+ years") before burning any LLM tokens.
3. **SQLite Deduplication**: Tracks every unique job ID so you never see or re-evaluate the same job twice.
4. **AI & Student Constraint Evaluation**: Evaluates each opening using **Google Gemini 2.5 Flash** against your profile:
   - **Workload Check**: Prioritizes 4 hours/day (20h/week), *pasantía*, and student-friendly flexible schedules.
   - **Anti-Bait Detection**: Exposes fake "Junior" listings that actually demand 3+ years of experience.
   - **Fit Score (0-100)**: Highlights why the job matches your skills and warns about potential caveats.
5. **Instant Telegram Alerts**: Sends high-match opportunities directly to your Telegram with direct application links.

---

## 🚀 Quick Setup

### 1. Configure Credentials in `.env`
Open `.env` and fill in:
```env
# Google AI Studio API Key (Free: https://aistudio.google.com/)
GEMINI_API_KEY=your_gemini_api_key_here

# Telegram Bot Token (Create via @BotFather on Telegram)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Your Telegram Chat ID (Get from @userinfobot on Telegram)
TELEGRAM_CHAT_ID=your_telegram_chat_id_here

# Minimum score to trigger a Telegram ping (0-100)
MIN_ALERT_SCORE=70
```

### 2. Verify Your Telegram Connection
Test that your Telegram bot can message you:
```powershell
.\.venv\Scripts\python main.py --test-telegram
```

### 3. Personalize Your Profile
Edit [`data/my_profile.md`](data/my_profile.md) with your current university progress, projects, GitHub link, and specific AI interests.

---

## 🛠️ Usage

### Run a Standard Search
```powershell
.\.venv\Scripts\python main.py
```

### Run a Dry Run (Scrapes & Scores without saving or messaging)
```powershell
.\.venv\Scripts\python main.py --dry-run
```

### View Top Stored Matches
```powershell
.\.venv\Scripts\python main.py --report
```

### Adjust Search Queries & Filters
You can customize search terms, locations, and negative keywords in [`config/search_config.yaml`](config/search_config.yaml).
