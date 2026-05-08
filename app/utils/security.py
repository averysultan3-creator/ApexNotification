import hashlib
import hmac
import re


def hash_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()


def verify_facebook_signature(app_secret: str, body: bytes, signature_header: str | None) -> bool:
    if not app_secret:
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    given = signature_header.split("=", 1)[1]
    return hmac.compare_digest(expected, given)


def sanitize_slug(slug: str) -> str:
    return re.sub(r"[^a-z0-9\-_]", "", slug.lower().strip())[:100]
