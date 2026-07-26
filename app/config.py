from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

APP_NAME = "AI Career Agent"
APP_VERSION = "3.1.0"

DATA_DIR = BASE_DIR / "data"
DATABASE = DATA_DIR / "ai_career_agent.db"
REPORTS_DIR = DATA_DIR / "reports"
RESUMES_DIR = DATA_DIR / "resumes"
CACHE_DIR = DATA_DIR / "cache"
