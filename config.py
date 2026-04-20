import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ruta absoluta al .env junto a este archivo.
# load_dotenv() sin argumentos busca en el CWD, que en cron es $HOME
# y nunca encuentra el .env → todas las variables quedan vacías.
_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(_ENV_PATH)


def _require(key: str) -> str:
    value = os.getenv(key, "").strip()
    if not value:
        print(f"[ERROR] Variable de entorno requerida no encontrada: {key}", file=sys.stderr)
        sys.exit(1)
    return value


# API de noticias
NEWS_API_KEY = _require("NEWS_API_KEY")
NEWS_API_URL = "https://newsapi.org/v2/everything"
NEWS_LANGUAGE = os.getenv("NEWS_LANGUAGE", "es,en")
MAX_ARTICLES_PER_CATEGORY = int(os.getenv("MAX_ARTICLES_PER_CATEGORY", "5"))

# SMTP
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = _require("SMTP_USER")
SMTP_PASSWORD = _require("SMTP_PASSWORD")

# Destinatarios (soporte para múltiples, separados por coma)
RECIPIENT_EMAIL_RAW = _require("RECIPIENT_EMAIL")
RECIPIENT_EMAILS = [e.strip() for e in RECIPIENT_EMAIL_RAW.split(",") if e.strip()]

# Newsletter
SEND_HOUR = int(os.getenv("SEND_HOUR", "8"))
TIMEZONE = os.getenv("TIMEZONE", "Europe/Madrid")

# Logs
LOG_FILE = os.getenv("LOG_FILE", "/var/log/newsletter.log")

# Queries por categoría
CATEGORY_QUERIES = {
    "urgente": (
        '"breaking news" AND (AI OR "artificial intelligence" OR OpenAI OR Anthropic '
        'OR "Google AI" OR "inteligencia artificial")'
    ),
    "ia": (
        '"inteligencia artificial" OR "artificial intelligence" OR "machine learning" '
        'OR "large language model" OR LLM OR "generative AI" OR "IA generativa"'
    ),
    "empresas": (
        "OpenAI OR Anthropic OR Claude OR ChatGPT OR Gemini OR DeepMind "
        'OR "Meta AI" OR "Microsoft AI" OR Grok OR xAI OR "GPT-5" OR "GPT-4"'
    ),
    "tecnologia": (
        "tecnología OR technology OR smartphone OR chip OR semiconductor "
        "OR ciberseguridad OR cybersecurity OR robotics OR robótica OR quantum"
    ),
}
