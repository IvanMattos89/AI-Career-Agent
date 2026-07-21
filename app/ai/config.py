import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
ENV_FILE = os.path.join(BASE_DIR, ".env")

load_dotenv(dotenv_path=ENV_FILE, override=True)

class AIConfig:

    PROVIDER = os.getenv("AI_PROVIDER", "auto").lower()

    OPENAI_MODEL = os.getenv(
        "OPENAI_MODEL",
        "gpt-4.1-mini"
    )

    OPENAI_API_KEY = os.getenv(
        "OPENAI_API_KEY",
        ""
    ).strip()

    OLLAMA_URL = os.getenv(
        "OLLAMA_URL",
        "http://localhost:11434"
    )

    OLLAMA_MODEL = os.getenv(
        "OLLAMA_MODEL",
        "llama3.1:8b"
    )

    # Mantém a aplicação responsiva: após um minuto o worker usa o fallback
    # local. O valor pode ser ajustado nas configurações para modelos lentos.
    OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "60"))
    OLLAMA_CONNECT_TIMEOUT = int(os.getenv("OLLAMA_CONNECT_TIMEOUT", "5"))
