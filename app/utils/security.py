"""security.py — request validation helpers."""
import hashlib
import hmac
import re


def hash_ip(ip: str) -> str:
    return hashlib.sha256(ip.encode()).hexdigest()


def sanitize_slug(slug: str) -> str:
    """Keep only [a-z0-9-_] in slug."""
    return re.sub(r"[^a-z0-9\-_]", "", slug.lower().strip())[:100]
