import os
from typing import List
from dotenv import load_dotenv

load_dotenv(encoding="utf-8-sig")


def _int_list(name: str) -> List[int]:
    raw = os.getenv(name, "")
    return [int(item.strip()) for item in raw.split(",") if item.strip().isdigit()]


def _int(name: str, default: int) -> int:
    raw = os.getenv(name, "")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_IDS: List[int] = _int_list("ADMIN_IDS")
ADMIN_SETUP_CODE: str = os.getenv("ADMIN_SETUP_CODE", "1234")
BOT_USERNAME: str = os.getenv("BOT_USERNAME", "your_bot")

DATABASE_URL: str = os.getenv("DATABASE_URL") or "sqlite+aiosqlite:///./apex_lead_router.db"
LOG_LEVEL: str = os.getenv("LOG_LEVEL") or "INFO"

PUBLIC_BASE_URL: str = (os.getenv("PUBLIC_BASE_URL") or "https://your-domain.com").rstrip("/")
WEB_HOST: str = os.getenv("WEB_HOST") or "0.0.0.0"
WEB_PORT: int = _int("WEB_PORT", 8000)

FACEBOOK_VERIFY_TOKEN: str = os.getenv("FACEBOOK_VERIFY_TOKEN", "change_me_verify_token")
FACEBOOK_APP_SECRET: str = os.getenv("FACEBOOK_APP_SECRET", "")
FACEBOOK_PAGE_ACCESS_TOKEN: str = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "")
FACEBOOK_GRAPH_VERSION: str = os.getenv("FACEBOOK_GRAPH_VERSION", "v19.0")

# Path to Google service account JSON file, or raw JSON string
GOOGLE_SERVICE_ACCOUNT_JSON: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
