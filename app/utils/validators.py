import re


SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,98}[a-z0-9]$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_slug(value: str) -> bool:
    return bool(SLUG_RE.fullmatch(value.strip()))


def normalize_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "-", value.strip().lower()).strip("-")


def is_valid_email(value: str) -> bool:
    return bool(EMAIL_RE.fullmatch(value.strip()))


def parse_int_list(raw: str) -> list[int]:
    ids: list[int] = []
    for item in raw.replace("\n", ",").split(","):
        item = item.strip()
        if item.lstrip("-").isdigit():
            ids.append(int(item))
    return ids


def parse_str_list(raw: str) -> list[str]:
    return [item.strip() for item in raw.replace("\n", ",").split(",") if item.strip()]


def is_valid_telegram_id(value: str) -> bool:
    return value.strip().lstrip("-").isdigit()


def is_numeric_fb_id(value: str) -> bool:
    return value.strip().isdigit()
