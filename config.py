import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.environ["BOT_TOKEN"]

_raw_ids = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: List[int] = [int(x.strip()) for x in _raw_ids.split(",") if x.strip().isdigit()]

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./leadform_hub.db")
BOT_USERNAME: str = os.getenv("BOT_USERNAME", "your_bot")
PAGE_SIZE: int = int(os.getenv("PAGE_SIZE", "10"))
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
