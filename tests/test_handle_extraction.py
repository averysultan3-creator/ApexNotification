"""
Unit tests for _find_handle_in_raw and _looks_like_handle.
Tests use the REAL column names from Facebook Lead Ads exports to prevent regressions.
"""
import pytest
from app.services.google_sheet_service import _find_handle_in_raw, _looks_like_handle


# ---------------------------------------------------------------------------
# _looks_like_handle
# ---------------------------------------------------------------------------

class TestLooksLikeHandle:
    """Values that ARE valid handles."""

    @pytest.mark.parametrize("val", [
        "@jasper01r",
        "@Sol1459",
        "@stronggirl3579",
        "@VSPurple",
        "@ivannichai",
        "@M0artea",
        "skyx_may",         # plain word username (no @)
        "username_123",
        "https://t.me/+48884653707",
        "https://t.me/username",
        "t.me/username",
        "@a1b",             # short but valid (3 chars)
    ])
    def test_valid(self, val):
        assert _looks_like_handle(val) is True

    """Values that are NOT handles."""

    @pytest.mark.parametrize("val", [
        "c:120244727058410149",    # campaign_id — FB format
        "ag:120244727348130149",   # ad_id — FB format
        "as:120244727348120149",   # adset_id — FB format
        "f:1297809225097712",      # form_id — FB format
        "l:2111353626389845",      # lead_id — FB format
        "+48517591980",            # phone number
        "p:+48517591980",          # phone with prefix
        "+380971737371",
        "CREATED",                 # lead_status
        "false",                   # is_organic
        "fb",                      # platform
        "3543",                    # digits only
        "21",
        "",
        "Нова кампанія з ціллю «Ліди»",   # campaign name in Ukrainian
        "<test lead: dummy data for phone_number>",
    ])
    def test_invalid(self, val):
        assert _looks_like_handle(val) is False


# ---------------------------------------------------------------------------
# _find_handle_in_raw — realistic FB Lead Ads payloads
# ---------------------------------------------------------------------------

# This raw dict matches the REAL Facebook Lead Ads export format for our funnel.
REAL_LEAD_RAW = {
    "id": "l:2111353626389845",
    "created_time": "2026-05-11T15:39:07-05:00",
    "ad_id": "ag:120244727348130149",
    "ad_name": "Нова реклама з ціллю «Ліди»",
    "adset_id": "as:120244727348120149",
    "adset_name": "женщина",
    "campaign_id": "c:120244727058410149",   # contains "ig" in "campaign" — was false-positive before
    "campaign_name": "Нова кампанія з ціллю «Ліди»",
    "form_id": "f:1297809225097712",
    "form_name": "пл",
    "is_organic": "false",
    "platform": "fb",
    "твой_телеграмм_тег_через_@": "@Sol1459",  # the REAL telegram column
    "full_name": "Olha",
    "phone_number": "p:+48517591980",
    "lead_status": "CREATED",
}


def test_finds_telegram_from_cyrillic_column():
    """Must return @Sol1459, NOT c:120244727058410149 from campaign_id."""
    result = _find_handle_in_raw(REAL_LEAD_RAW)
    assert result == "@Sol1459"


def test_campaign_id_is_not_a_handle():
    """campaign_id value should never be returned as a handle."""
    raw = {
        "campaign_id": "c:120244727058410149",
        "form_name": "пл",
    }
    assert _find_handle_in_raw(raw) == ""


def test_ig_in_column_name_not_matched():
    """'ig' inside 'campaign' should NOT match the instagram keyword logic."""
    raw = {
        "campaign_id": "c:12345",          # 'ig' substring in column name via 'campa-ig-n' — must be ignored
        "twitter_handle": "@realuser",      # not in our keywords
    }
    # 'twitter_handle' is not in keywords; fallback via @-pattern
    result = _find_handle_in_raw(raw)
    assert result == "@realuser"


def test_at_sign_in_column_name():
    """Column literally named '@' or containing '@' captures the value."""
    raw = {
        "campaign_id": "c:12345",
        "your @ telegram": "@user123",
    }
    assert _find_handle_in_raw(raw) == "@user123"


def test_telegram_column_latin():
    raw = {"telegram": "@myuser", "phone": "+380971234567"}
    assert _find_handle_in_raw(raw) == "@myuser"


def test_telegram_column_cyrillic_short():
    raw = {"тг": "@Vasyl_ua", "phone": "+380971234567"}
    assert _find_handle_in_raw(raw) == "@Vasyl_ua"


def test_tme_link_in_phone_column():
    """t.me/ link in a non-keyword column → fallback detection."""
    raw = {
        "campaign_id": "c:999",
        "misc": "https://t.me/+48884653707",
    }
    assert _find_handle_in_raw(raw) == "https://t.me/+48884653707"


def test_fallback_at_pattern_no_keyword_column():
    """If no keyword column exists, pick up @handle from any cell value."""
    raw = {
        "campaign_id": "c:999",
        "question_1": "@jasper01r",
    }
    assert _find_handle_in_raw(raw) == "@jasper01r"


def test_empty_raw_returns_empty_string():
    assert _find_handle_in_raw({}) == ""


def test_all_null_values():
    raw = {"telegram": None, "phone": None}
    assert _find_handle_in_raw(raw) == ""


def test_handle_column_with_bad_value_skipped():
    """If keyword column has a non-handle value, skip it; use fallback."""
    raw = {
        "телеграм": "3543",          # looks like garbage — NOT a handle
        "misc": "@real_user",        # fallback via @-pattern
    }
    result = _find_handle_in_raw(raw)
    assert result == "@real_user"


def test_handle_column_with_phone_skipped():
    """Phone number in telegram column should not be returned as handle."""
    raw = {
        "telegram": "+380971234567",  # a phone, not a handle
    }
    assert _find_handle_in_raw(raw) == ""


def test_keyword_column_priority_over_fallback():
    """Keyword column with valid handle wins over @handle in non-keyword column."""
    raw = {
        "other": "@fallback_user",
        "телеграм": "@priority_user",
    }
    assert _find_handle_in_raw(raw) == "@priority_user"


def test_no_duplicate_false_positive_from_adset():
    """adset_id / adset_name must not trigger handle extraction."""
    raw = {
        "adset_id": "as:120244727348120149",
        "adset_name": "женщина",
    }
    assert _find_handle_in_raw(raw) == ""
