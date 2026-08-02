import logging
from logging.handlers import RotatingFileHandler

from app.config import DATA_DIR

LOG_DIR = DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger("ai_career_agent")
if not logger.handlers:
    handler = RotatingFileHandler(
        LOG_DIR / "ai_career_agent.log", maxBytes=2 * 1024 * 1024,
        backupCount=3, encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
