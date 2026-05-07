import re
from datetime import datetime
from typing import Optional


def validate_phone(text: str) -> Optional[str]:
    """Normalise and validate a phone number. Returns cleaned number or None."""
    cleaned = re.sub(r"[\s\-\(\)]", "", text.strip())
    if re.fullmatch(r"\+?[1-9]\d{6,14}", cleaned):
        return cleaned
    return None


def validate_telegram_username(text: str) -> Optional[str]:
    """Validate a Telegram @username. Returns username without @ or None."""
    raw = text.strip().lstrip("@")
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{4,31}", raw):
        return raw
    return None


def validate_number(text: str) -> Optional[str]:
    """Validate that the input is a numeric value. Returns the string or None."""
    cleaned = text.strip().replace(",", ".")
    try:
        float(cleaned)
        return cleaned
    except ValueError:
        return None


def validate_date(text: str) -> Optional[str]:
    """Validate date in dd.mm.yyyy or yyyy-mm-dd format. Returns ISO string or None."""
    text = text.strip()
    # Try dd.mm.yyyy
    m = re.fullmatch(r"(\d{2})\.(\d{2})\.(\d{4})", text)
    if m:
        d, mo, y = m.groups()
        try:
            datetime(int(y), int(mo), int(d))
            return f"{y}-{mo}-{d}"
        except ValueError:
            return None
    # Try yyyy-mm-dd
    m2 = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m2:
        y, mo, d = m2.groups()
        try:
            datetime(int(y), int(mo), int(d))
            return text
        except ValueError:
            return None
    return None
