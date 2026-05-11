from __future__ import annotations

import json
import os
import sqlite3
import sys
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def load_env() -> dict[str, str]:
    env_path = ROOT / ".env"
    data: dict[str, str] = {}
    if not env_path.exists():
        return data
    for raw in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def admin_ids(env: dict[str, str]) -> list[int]:
    ids: set[int] = set()
    for item in env.get("ADMIN_IDS", "").replace(";", ",").split(","):
        item = item.strip()
        if item.isdigit():
            ids.add(int(item))

    db_path = ROOT / "apex_lead_router.db"
    if db_path.exists():
        try:
            conn = sqlite3.connect(db_path)
            for (tg_id,) in conn.execute("SELECT telegram_user_id FROM admins"):
                if tg_id:
                    ids.add(int(tg_id))
            conn.close()
        except Exception:
            pass
    return sorted(ids)


def send_message(token: str, chat_id: int, text: str) -> None:
    payload = urllib.parse.urlencode(
        {
            "chat_id": str(chat_id),
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    req = urllib.request.Request(url, data=payload, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        resp.read()


def main() -> int:
    env = load_env()
    token = env.get("BOT_TOKEN", "")
    if not token:
        return 2

    text = " ".join(sys.argv[1:]).strip() or "Apex Lead Router alert"
    text = "<b>Apex Lead Router ALERT</b>\n\n" + text
    ok = 0
    for chat_id in admin_ids(env):
        try:
            send_message(token, chat_id, text)
            ok += 1
        except Exception:
            pass
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
