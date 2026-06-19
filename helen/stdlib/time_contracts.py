"""Time module contracts for Helen stdlib.

Defines interfaces for time, date, and datetime operations.
"""

from __future__ import annotations


class TimeContract:
    """Contract for time operations."""

    @staticmethod
    def now() -> str:
        """Get current datetime as ISO 8601 string.

        Returns:
            ISO 8601 formatted datetime string (YYYY-MM-DDTHH:MM:SS)
        """
        ...

    @staticmethod
    def time() -> float:
        """Get current Unix timestamp.

        Returns:
            Seconds since epoch (float)
        """
        ...

    @staticmethod
    def sleep(seconds: float) -> str:
        """Pause execution for specified seconds.

        Args:
            seconds: Number of seconds to sleep

        Returns:
            Success message
        """
        ...


class DateContract:
    """Contract for date operations."""

    @staticmethod
    def date(year: int | None = None, month: int | None = None, day: int | None = None) -> str:
        """Create or get date.

        Args:
            year: Year (optional, defaults to today)
            month: Month (optional, defaults to today)
            day: Day (optional, defaults to today)

        Returns:
            Date string (YYYY-MM-DD)
        """
        ...

    @staticmethod
    def datetime(year: int | None = None, month: int | None = None,
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
        ...

    @staticmethod
    def date_format(date_str: str, format_str: str) -> str:
        """Format date string.

        Args:
            date_str: Input date string (ISO 8601)
            format_str: Format string (e.g., "%Y-%m-%d", "%d/%m/%Y")

        Returns:
            Formatted date string

        Raises:
            ValueError: If date format is invalid
        """
        ...

    @staticmethod
    def date_parse(date_str: str, format_str: str) -> str:
        """Parse date string to ISO 8601.

        Args:
            date_str: Input date string
            format_str: Format string to parse

        Returns:
            ISO 8601 formatted date string

        Raises:
            ValueError: If date cannot be parsed
        """
        ...

    @staticmethod
    def date_add(date_str: str, days: int = 0, hours: int = 0,
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
        ...

    @staticmethod
    def date_diff(date1: str, date2: str, unit: str = "days") -> float:
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
        ...

    @staticmethod
    def date_year(date_str: str) -> int:
        """Extract year from date.

        Args:
            date_str: Date string (ISO 8601)

        Returns:
            Year
        """
        ...

    @staticmethod
    def date_month(date_str: str) -> int:
        """Extract month from date.

        Args:
            date_str: Date string (ISO 8601)

        Returns:
            Month (1-12)
        """
        ...

    @staticmethod
    def date_day(date_str: str) -> int:
        """Extract day from date.

        Args:
            date_str: Date string (ISO 8601)

        Returns:
            Day (1-31)
        """
        ...

    @staticmethod
    def date_weekday(date_str: str) -> int:
        """Get day of week.

        Args:
            date_str: Date string (ISO 8601)

        Returns:
            Day of week (0=Monday, 6=Sunday)
        """
        ...
