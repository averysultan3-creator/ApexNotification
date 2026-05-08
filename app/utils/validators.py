"""validators.py — input validation helpers."""
import re


def is_valid_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))


def is_valid_telegram_id(value: str) -> bool:
    try:
        int(value)
        return True
    except ValueError:
        return False


def is_numeric_fb_id(value: str) -> bool:
    return value.strip().isdigit()
