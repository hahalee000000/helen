"""Math statistics module for Helen stdlib.

Provides statistical operations.
"""

from __future__ import annotations

import math
from collections import Counter


# ── Statistical operations ─────────────────────────────────────


def _mean(numbers: list[float]) -> float:
    """Calculate arithmetic mean.

    Args:
        numbers: List of numbers

    Returns:
        Arithmetic mean

    Raises:
        ValueError: If list is empty
    """
    if not numbers:
        raise ValueError("Cannot calculate mean of empty list")
    return sum(numbers) / len(numbers)


def _median(numbers: list[float]) -> float:
    """Calculate median.

    Args:
        numbers: List of numbers

    Returns:
        Median value

    Raises:
        ValueError: If list is empty
    """
    if not numbers:
        raise ValueError("Cannot calculate median of empty list")

    sorted_nums = sorted(numbers)
    n = len(sorted_nums)
    mid = n // 2

    if n % 2 == 0:
        return (sorted_nums[mid - 1] + sorted_nums[mid]) / 2
    else:
        return sorted_nums[mid]


def _mode(numbers: list[float]) -> list[float]:
    """Calculate mode (most frequent values).

    Args:
        numbers: List of numbers

    Returns:
        List of mode values (may be multiple)

    Raises:
        ValueError: If list is empty
    """
    if not numbers:
        raise ValueError("Cannot calculate mode of empty list")

    counts = Counter(numbers)
    max_count = max(counts.values())
    return [num for num, count in counts.items() if count == max_count]


def _variance(numbers: list[float], population: bool = True) -> float:
    """Calculate variance.

    Args:
        numbers: List of numbers
        population: If True, calculate population variance; otherwise sample variance

    Returns:
        Variance

    Raises:
        ValueError: If list is empty or too small for sample variance
    """
    if not numbers:
        raise ValueError("Cannot calculate variance of empty list")

    if not population and len(numbers) < 2:
        raise ValueError("Sample variance requires at least 2 values")

    mean = _mean(numbers)
    squared_diffs = [(x - mean) ** 2 for x in numbers]

    if population:
        return sum(squared_diffs) / len(numbers)
    else:
        return sum(squared_diffs) / (len(numbers) - 1)


def _stddev(numbers: list[float], population: bool = True) -> float:
    """Calculate standard deviation.

    Args:
        numbers: List of numbers
        population: If True, calculate population stddev; otherwise sample stddev

    Returns:
        Standard deviation

    Raises:
        ValueError: If list is empty or too small for sample stddev
    """
    return math.sqrt(_variance(numbers, population))


def _correlation(x: list[float], y: list[float]) -> float:
    """Calculate Pearson correlation coefficient.

    Args:
        x: First list of numbers
        y: Second list of numbers

    Returns:
        Correlation coefficient (-1.0 to 1.0)

    Raises:
        ValueError: If lists are empty or different lengths
    """
    if not x or not y:
        raise ValueError("Cannot calculate correlation of empty lists")

    if len(x) != len(y):
        raise ValueError("Lists must have the same length")

    n = len(x)
    mean_x = _mean(x)
    mean_y = _mean(y)

    # Calculate covariance and standard deviations
    covariance = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / n
    std_x = _stddev(x, population=True)
    std_y = _stddev(y, population=True)

    if std_x == 0 or std_y == 0:
        return 0.0

    return covariance / (std_x * std_y)


def _percentile(numbers: list[float], p: float) -> float:
    """Calculate percentile.

    Args:
        numbers: List of numbers
        p: Percentile (0-100)

    Returns:
        Percentile value

    Raises:
        ValueError: If list is empty or p is out of range
    """
    if not numbers:
        raise ValueError("Cannot calculate percentile of empty list")

    if p < 0 or p > 100:
        raise ValueError(f"Percentile must be between 0 and 100, got {p}")

    sorted_nums = sorted(numbers)
    n = len(sorted_nums)

    if p == 0:
        return sorted_nums[0]
    if p == 100:
        return sorted_nums[-1]

    # Linear interpolation
    k = (n - 1) * (p / 100)
    f = math.floor(k)
    c = math.ceil(k)

    if f == c:
        return sorted_nums[int(k)]

    return sorted_nums[f] * (c - k) + sorted_nums[c] * (k - f)


def _sum(numbers: list[float]) -> float:
    """Calculate sum of numbers.

    Args:
        numbers: List of numbers

    Returns:
        Sum
    """
    return sum(numbers)


def _product(numbers: list[float]) -> float:
    """Calculate product of numbers.

    Args:
        numbers: List of numbers

    Returns:
        Product
    """
    if not numbers:
        return 1.0

    result = 1.0
    for num in numbers:
        result *= num
    return result


def _min(numbers: list[float]) -> float:
    """Find minimum value.

    Args:
        numbers: List of numbers

    Returns:
        Minimum value

    Raises:
        ValueError: If list is empty
    """
    if not numbers:
        raise ValueError("Cannot find minimum of empty list")
    return min(numbers)


def _max(numbers: list[float]) -> float:
    """Find maximum value.

    Args:
        numbers: List of numbers

    Returns:
        Maximum value

    Raises:
        ValueError: If list is empty
    """
    if not numbers:
        raise ValueError("Cannot find maximum of empty list")
    return max(numbers)
