"""Tests for Time stdlib module.

Tests time, date, and datetime operations.
"""

import pytest
import time as _time
from helen.stdlib.time import (
    # Time
    _now, _time_func, _sleep,
    # Date
    _date, _datetime, _date_format, _date_parse,
    _date_add, _date_diff, _date_year, _date_month, _date_day, _date_weekday,
)


# ── Time Tests ─────────────────────────────────────────────────


class TestNow:
    """Tests for now."""

    def test_returns_string(self):
        result = _now()
        assert isinstance(result, str)

    def test_iso_format(self):
        result = _now()
        # Should be ISO 8601 format: YYYY-MM-DDTHH:MM:SS
        assert "T" in result
        assert len(result) >= 19

    def test_current_time(self):
        result = _now()
        # Should contain current year
        assert "2026" in result or "2025" in result


class TestTimeFunc:
    """Tests for time function."""

    def test_returns_float(self):
        result = _time_func()
        assert isinstance(result, float)

    def test_positive(self):
        result = _time_func()
        assert result > 0

    def test_monotonic(self):
        t1 = _time_func()
        t2 = _time_func()
        assert t2 >= t1


class TestSleep:
    """Tests for sleep."""

    def test_sleep_short(self):
        start = _time_func()
        result = _sleep(0.1)
        elapsed = _time_func() - start
        assert elapsed >= 0.1
        assert "Slept" in result

    def test_sleep_zero(self):
        result = _sleep(0)
        assert "Slept" in result


# ── Date Tests ─────────────────────────────────────────────────


class TestDate:
    """Tests for date."""

    def test_today(self):
        result = _date()
        # Should be YYYY-MM-DD format
        assert len(result) == 10
        assert result.count("-") == 2

    def test_specific_date(self):
        result = _date(2024, 6, 18)
        assert result == "2024-06-18"

    def test_partial_date(self):
        result = _date(2024, 1, 1)
        assert result == "2024-01-01"


class TestDatetime:
    """Tests for datetime."""

    def test_now(self):
        result = _datetime()
        # Should be ISO 8601 format
        assert "T" in result
        assert len(result) >= 19

    def test_specific_datetime(self):
        result = _datetime(2024, 6, 18, 14, 30, 45)
        assert result == "2024-06-18T14:30:45"

    def test_partial_datetime(self):
        result = _datetime(2024, 6, 18, 10, 0, 0)
        assert result == "2024-06-18T10:00:00"


class TestDateFormat:
    """Tests for date_format."""

    def test_basic_format(self):
        result = _date_format("2024-06-18", "%Y-%m-%d")
        assert result == "2024-06-18"

    def test_custom_format(self):
        result = _date_format("2024-06-18", "%d/%m/%Y")
        assert result == "18/06/2024"

    def test_with_time(self):
        result = _date_format("2024-06-18T14:30:45", "%Y-%m-%d %H:%M")
        assert result == "2024-06-18 14:30"

    def test_invalid_format(self):
        with pytest.raises(ValueError):
            _date_format("not-a-date", "%Y-%m-%d")


class TestDateParse:
    """Tests for date_parse."""

    def test_parse_custom_format(self):
        result = _date_parse("18/06/2024", "%d/%m/%Y")
        assert result == "2024-06-18"

    def test_parse_iso_format(self):
        result = _date_parse("2024-06-18", "%Y-%m-%d")
        assert result == "2024-06-18"

    def test_parse_with_time(self):
        result = _date_parse("18/06/2024 14:30", "%d/%m/%Y %H:%M")
        assert "2024-06-18" in result
        assert "14:30" in result

    def test_parse_invalid(self):
        with pytest.raises(ValueError):
            _date_parse("invalid", "%Y-%m-%d")


class TestDateAdd:
    """Tests for date_add."""

    def test_add_days(self):
        result = _date_add("2024-06-18", days=1)
        assert result == "2024-06-19"

    def test_add_negative_days(self):
        result = _date_add("2024-06-18", days=-1)
        assert result == "2024-06-17"

    def test_add_hours(self):
        result = _date_add("2024-06-18T10:00:00", hours=5)
        assert result == "2024-06-18T15:00:00"

    def test_add_cross_day(self):
        result = _date_add("2024-06-18T23:00:00", hours=2)
        assert result == "2024-06-19T01:00:00"

    def test_add_multiple(self):
        result = _date_add("2024-06-18T10:00:00", days=1, hours=2, minutes=30)
        assert "2024-06-19" in result
        assert "12:30:00" in result


class TestDateDiff:
    """Tests for date_diff."""

    def test_diff_days(self):
        result = _date_diff("2024-06-18", "2024-06-20", "days")
        assert result == 2.0

    def test_diff_hours(self):
        result = _date_diff("2024-06-18T10:00:00", "2024-06-18T15:00:00", "hours")
        assert result == 5.0

    def test_diff_minutes(self):
        result = _date_diff("2024-06-18T10:00:00", "2024-06-18T10:30:00", "minutes")
        assert result == 30.0

    def test_diff_seconds(self):
        result = _date_diff("2024-06-18T10:00:00", "2024-06-18T10:01:00", "seconds")
        assert result == 60.0

    def test_diff_negative(self):
        result = _date_diff("2024-06-20", "2024-06-18", "days")
        assert result == -2.0

    def test_diff_invalid_unit(self):
        with pytest.raises(ValueError):
            _date_diff("2024-06-18", "2024-06-20", "invalid")


class TestDateYear:
    """Tests for date_year."""

    def test_extract_year(self):
        result = _date_year("2024-06-18")
        assert result == 2024

    def test_extract_from_datetime(self):
        result = _date_year("2024-06-18T14:30:45")
        assert result == 2024


class TestDateMonth:
    """Tests for date_month."""

    def test_extract_month(self):
        result = _date_month("2024-06-18")
        assert result == 6

    def test_extract_from_datetime(self):
        result = _date_month("2024-06-18T14:30:45")
        assert result == 6


class TestDateDay:
    """Tests for date_day."""

    def test_extract_day(self):
        result = _date_day("2024-06-18")
        assert result == 18

    def test_extract_from_datetime(self):
        result = _date_day("2024-06-18T14:30:45")
        assert result == 18


class TestDateWeekday:
    """Tests for date_weekday."""

    def test_monday(self):
        # 2024-06-17 is Monday
        result = _date_weekday("2024-06-17")
        assert result == 0

    def test_sunday(self):
        # 2024-06-23 is Sunday
        result = _date_weekday("2024-06-23")
        assert result == 6

    def test_wednesday(self):
        # 2024-06-19 is Wednesday
        result = _date_weekday("2024-06-19")
        assert result == 2
