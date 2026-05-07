"""Tests for utility functions."""
import pytest

from utils.validators import validate_phone, validate_telegram_username, validate_number, validate_date
from utils.pagination import paginate


def test_validate_phone_valid():
    assert validate_phone("+380971234567") == "+380971234567"
    assert validate_phone("380971234567") == "380971234567"
    assert validate_phone("+1 (800) 555-1234") == "+18005551234"


def test_validate_phone_invalid():
    assert validate_phone("abc") is None
    assert validate_phone("123") is None
    assert validate_phone("") is None


def test_validate_telegram_username_valid():
    assert validate_telegram_username("@johndoe") == "johndoe"
    assert validate_telegram_username("johndoe") == "johndoe"
    assert validate_telegram_username("john_doe_123") == "john_doe_123"


def test_validate_telegram_username_invalid():
    assert validate_telegram_username("@ab") is None   # too short
    assert validate_telegram_username("@1badstart") is None  # starts with digit
    assert validate_telegram_username("") is None


def test_validate_number():
    assert validate_number("42") == "42"
    assert validate_number("3.14") == "3.14"
    assert validate_number("3,14") == "3.14"
    assert validate_number("not a number") is None


def test_validate_date():
    assert validate_date("25.12.2024") == "2024-12-25"
    assert validate_date("2024-12-25") == "2024-12-25"
    assert validate_date("invalid") is None
    assert validate_date("32.13.2024") is None


def test_pagination():
    items = list(range(25))
    pr = paginate(items[:10], 25, 0, 10)
    assert pr.total == 25
    assert pr.total_pages == 3
    assert pr.has_prev is False
    assert pr.has_next is True
    assert pr.page == 0

    pr2 = paginate(items[10:20], 25, 1, 10)
    assert pr2.has_prev is True
    assert pr2.has_next is True

    pr3 = paginate(items[20:], 25, 2, 10)
    assert pr3.has_prev is True
    assert pr3.has_next is False
