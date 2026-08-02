import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
IS_PACKAGED = bool(getattr(sys, "frozen", False))
USER_DATA_ROOT = Path(
    os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local")
) / "AI Career Agent"

APP_NAME = "AI Career Agent"
APP_VERSION = "3.4.0"

DATA_DIR = (USER_DATA_ROOT / "data") if IS_PACKAGED else (BASE_DIR / "data")
DATABASE = DATA_DIR / "ai_career_agent.db"
REPORTS_DIR = DATA_DIR / "reports"
RESUMES_DIR = DATA_DIR / "resumes"
