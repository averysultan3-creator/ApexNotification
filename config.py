import os
from typing import List

from dotenv import load_dotenv

load_dotenv()


def _int_list(name: str) -> List[int]:
    raw = os.getenv(name, "")
    return [int(item.strip()) for item in raw.split(",") if item.strip().isdigit()]


BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_IDS: List[int] = _int_list("ADMIN_IDS")
BOT_USERNAME: str = os.getenv("BOT_USERNAME", "your_bot")

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./apex_lead_router.db")
PAGE_SIZE: int = int(os.getenv("PAGE_SIZE", "10"))
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

PUBLIC_BASE_URL: str = os.getenv("PUBLIC_BASE_URL", "https://your-domain.com").rstrip("/")
WEB_HOST: str = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT: int = int(os.getenv("WEB_PORT", "8000"))

FACEBOOK_VERIFY_TOKEN: str = os.getenv("FACEBOOK_VERIFY_TOKEN", "change_me_verify_token")
FACEBOOK_APP_SECRET: str = os.getenv("FACEBOOK_APP_SECRET", "")
FACEBOOK_PAGE_ACCESS_TOKEN: str = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "")
FACEBOOK_GRAPH_VERSION: str = os.getenv("FACEBOOK_GRAPH_VERSION", "v19.0")

EMAIL_ENABLED: bool = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM: str = os.getenv("SMTP_FROM", SMTP_USERNAME)

GOOGLE_SHEETS_ENABLED: bool = os.getenv("GOOGLE_SHEETS_ENABLED", "false").lower() == "true"
GOOGLE_SERVICE_ACCOUNT_JSON: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
