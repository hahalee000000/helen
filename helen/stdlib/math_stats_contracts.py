"""Math statistics contracts for Helen stdlib.

Defines interfaces for statistical operations.
"""


class MathStatsContract:
    """Contract for statistical operations."""

    @staticmethod
    def mean(numbers: list[float]) -> float:
        """Calculate arithmetic mean.

        Args:
            numbers: List of numbers

        Returns:
            Arithmetic mean

        Raises:
            ValueError: If list is empty
        """
        ...

    @staticmethod
    def median(numbers: list[float]) -> float:
        """Calculate median.

        Args:
            numbers: List of numbers

        Returns:
            Median value

        Raises:
            ValueError: If list is empty
        """
        ...

    @staticmethod
    def mode(numbers: list[float]) -> list[float]:
        """Calculate mode (most frequent values).

        Args:
            numbers: List of numbers

        Returns:
            List of mode values (may be multiple)

        Raises:
            ValueError: If list is empty
        """
        ...

    @staticmethod
    def variance(numbers: list[float], population: bool = True) -> float:
        """Calculate variance.

        Args:
            numbers: List of numbers
            population: If True, calculate population variance; otherwise sample variance

        Returns:
            Variance

        Raises:
            ValueError: If list is empty or too small for sample variance
        """
        ...

    @staticmethod
    def stddev(numbers: list[float], population: bool = True) -> float:
        """Calculate standard deviation.

        Args:
            numbers: List of numbers
            population: If True, calculate population stddev; otherwise sample stddev

        Returns:
            Standard deviation

        Raises:
            ValueError: If list is empty or too small for sample stddev
        """
        ...

    @staticmethod
    def correlation(x: list[float], y: list[float]) -> float:
        """Calculate Pearson correlation coefficient.

        Args:
            x: First list of numbers
            y: Second list of numbers

        Returns:
            Correlation coefficient (-1.0 to 1.0)

        Raises:
            ValueError: If lists are empty or different lengths
        """
        ...

    @staticmethod
    def percentile(numbers: list[float], p: float) -> float:
        """Calculate percentile.

        Args:
            numbers: List of numbers
            p: Percentile (0-100)

        Returns:
            Percentile value

        Raises:
            ValueError: If list is empty or p is out of range
        """
        ...

    @staticmethod
    def sum(numbers: list[float]) -> float:
        """Calculate sum of numbers.

        Args:
            numbers: List of numbers

        Returns:
            Sum
        """
        ...

    @staticmethod
    def product(numbers: list[float]) -> float:
        """Calculate product of numbers.

        Args:
            numbers: List of numbers

        Returns:
            Product
        """
        ...

    @staticmethod
    def min(numbers: list[float]) -> float:
        """Find minimum value.

        Args:
            numbers: List of numbers

        Returns:
            Minimum value

        Raises:
            ValueError: If list is empty
        """
        ...

    @staticmethod
    def max(numbers: list[float]) -> float:
        """Find maximum value.

        Args:
            numbers: List of numbers

        Returns:
            Maximum value

        Raises:
            ValueError: If list is empty
        """
        ...
