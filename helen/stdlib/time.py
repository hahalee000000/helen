"""Time module for Helen stdlib.

Provides time, date, and datetime operations.
"""

from __future__ import annotations

import time as _time_module
from datetime import datetime, timedelta


# ── Time operations ────────────────────────────────────────────


def _now() -> str:
    """Get current datetime as ISO 8601 string.

    Returns:
        ISO 8601 formatted datetime string (YYYY-MM-DDTHH:MM:SS)
    """
    return datetime.now().isoformat(timespec="seconds")


def _time_func() -> float:
    """Get current Unix timestamp.

    Returns:
        Seconds since epoch (float)
    """
    return _time_module.time()


def _sleep(seconds: float) -> str:
    """Pause execution for specified seconds.

    Args:
        seconds: Number of seconds to sleep

    Returns:
        Success message
    """
    _time_module.sleep(seconds)
    return f"Slept for {seconds} seconds"


# ── Date operations ────────────────────────────────────────────


def _date(year: int | None = None, month: int | None = None,
          day: int | None = None) -> str:
    """Create or get date.

    Args:
        year: Year (optional, defaults to today)
        month: Month (optional, defaults to today)
        day: Day (optional, defaults to today)

    Returns:
        Date string (YYYY-MM-DD)
    """
    if year is None or month is None or day is None:
        # Return today's date
        return datetime.now().strftime("%Y-%m-%d")

    # Create specific date
    dt = datetime(year, month, day)
    return dt.strftime("%Y-%m-%d")


def _datetime(year: int | None = None, month: int | None = None,
              day: int | None = None, hour: int | None = None,
              minute: int | None = None, second: int | None = None) -> str:
    """Create or get datetime.

    Args:
        year: Year (optional, defaults to now)
        month: Month (optional, defaults to now)
        day: Day (optional, defaults to now)
        hour: Hour (optional, defaults to now)
        minute: Minute (optional, defaults to now)
        second: Second (optional, defaults to now)

    Returns:
        Datetime string (YYYY-MM-DDTHH:MM:SS)
    """
    if any(v is None for v in [year, month, day, hour, minute, second]):
        # Return current datetime
        return datetime.now().isoformat(timespec="seconds")

    # Create specific datetime (all values are guaranteed to be int here)
    dt = datetime(year, month, day, hour, minute, second)  # type: ignore[arg-type]
    return dt.isoformat(timespec="seconds")


def _date_format(date_str: str, format_str: str) -> str:
    """Format date string.

    Args:
        date_str: Input date string (ISO 8601)
        format_str: Format string (e.g., "%Y-%m-%d", "%d/%m/%Y")

    Returns:
        Formatted date string

    Raises:
        ValueError: If date format is invalid
    """
    try:
        # Try parsing as datetime first
        if "T" in date_str:
            dt = datetime.fromisoformat(date_str)
        else:
            dt = datetime.strptime(date_str, "%Y-%m-%d")

        return dt.strftime(format_str)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid date format: {e}") from e


def _date_parse(date_str: str, format_str: str) -> str:
    """Parse date string to ISO 8601.

    Args:
        date_str: Input date string
        format_str: Format string to parse

    Returns:
        ISO 8601 formatted date string

    Raises:
        ValueError: If date cannot be parsed
    """
    try:
        dt = datetime.strptime(date_str, format_str)
        # If format doesn't include time components, return date only
        if "%H" not in format_str and "%M" not in format_str and "%S" not in format_str:
            return dt.strftime("%Y-%m-%d")
        return dt.isoformat(timespec="seconds")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Cannot parse date: {e}") from e


def _date_add(date_str: str, days: int = 0, hours: int = 0,
              minutes: int = 0, seconds: int = 0) -> str:
    """Add time to date.

    Args:
        date_str: Input date string (ISO 8601)
        days: Days to add
        hours: Hours to add
        minutes: Minutes to add
        seconds: Seconds to add

    Returns:
        New date string (ISO 8601)

    Raises:
        ValueError: If date format is invalid
    """
    try:
        # Parse input date
        is_date_only = "T" not in date_str
        if is_date_only:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        else:
            dt = datetime.fromisoformat(date_str)

        # Add timedelta
        delta = timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
        result = dt + delta

        # Return date only if input was date only and no time was added
        if is_date_only and hours == 0 and minutes == 0 and seconds == 0:
            return result.strftime("%Y-%m-%d")
        return result.isoformat(timespec="seconds")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid date format: {e}") from e


def _date_diff(date1: str, date2: str, unit: str = "days") -> float:
    """Calculate difference between two dates.

    Args:
        date1: First date (ISO 8601)
        date2: Second date (ISO 8601)
        unit: Unit of difference ("seconds", "minutes", "hours", "days")

    Returns:
        Difference in specified unit

    Raises:
        ValueError: If date format is invalid or unit is invalid
    """
    try:
        # Parse dates
        if "T" in date1:
            dt1 = datetime.fromisoformat(date1)
        else:
            dt1 = datetime.strptime(date1, "%Y-%m-%d")

        if "T" in date2:
            dt2 = datetime.fromisoformat(date2)
        else:
            dt2 = datetime.strptime(date2, "%Y-%m-%d")

        # Calculate difference
        delta = dt2 - dt1

        # Convert to requested unit
        if unit == "seconds":
            return delta.total_seconds()
        elif unit == "minutes":
            return delta.total_seconds() / 60
        elif unit == "hours":
            return delta.total_seconds() / 3600
        elif unit == "days":
            return delta.total_seconds() / 86400
        else:
            raise ValueError(f"Invalid unit: {unit}. Must be 'seconds', 'minutes', 'hours', or 'days'")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid date format: {e}") from e


def _date_year(date_str: str) -> int:
    """Extract year from date.

    Args:
        date_str: Date string (ISO 8601)

    Returns:
        Year
    """
    try:
        if "T" in date_str:
            dt = datetime.fromisoformat(date_str)
        else:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.year
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid date format: {e}") from e


def _date_month(date_str: str) -> int:
    """Extract month from date.

    Args:
        date_str: Date string (ISO 8601)

    Returns:
        Month (1-12)
    """
    try:
        if "T" in date_str:
            dt = datetime.fromisoformat(date_str)
        else:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.month
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid date format: {e}") from e


def _date_day(date_str: str) -> int:
    """Extract day from date.

    Args:
        date_str: Date string (ISO 8601)

    Returns:
        Day (1-31)
    """
    try:
        if "T" in date_str:
            dt = datetime.fromisoformat(date_str)
        else:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.day
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid date format: {e}") from e


def _date_weekday(date_str: str) -> int:
    """Get day of week.

    Args:
        date_str: Date string (ISO 8601)

    Returns:
        Day of week (0=Monday, 6=Sunday)
    """
    try:
        if "T" in date_str:
            dt = datetime.fromisoformat(date_str)
        else:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.weekday()
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid date format: {e}") from e
