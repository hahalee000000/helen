"""Tests for Math statistics stdlib module.

Tests statistical operations.
"""

import pytest
from helen.stdlib.math_stats import (
    _mean, _median, _mode, _variance, _stddev,
    _correlation, _percentile, _sum, _product, _min, _max,
)


# ── Mean Tests ─────────────────────────────────────────────────


class TestMean:
    """Tests for mean."""

    def test_basic(self):
        result = _mean([1, 2, 3, 4, 5])
        assert result == 3.0

    def test_floats(self):
        result = _mean([1.5, 2.5, 3.5])
        assert result == 2.5

    def test_single(self):
        result = _mean([42])
        assert result == 42.0

    def test_negative(self):
        result = _mean([-1, 0, 1])
        assert result == 0.0

    def test_empty(self):
        with pytest.raises(ValueError):
            _mean([])


# ── Median Tests ───────────────────────────────────────────────


class TestMedian:
    """Tests for median."""

    def test_odd_count(self):
        result = _median([1, 2, 3, 4, 5])
        assert result == 3.0

    def test_even_count(self):
        result = _median([1, 2, 3, 4])
        assert result == 2.5

    def test_unsorted(self):
        result = _median([5, 2, 1, 4, 3])
        assert result == 3.0

    def test_single(self):
        result = _median([42])
        assert result == 42.0

    def test_empty(self):
        with pytest.raises(ValueError):
            _median([])


# ── Mode Tests ─────────────────────────────────────────────────


class TestMode:
    """Tests for mode."""

    def test_single_mode(self):
        result = _mode([1, 2, 2, 3, 4])
        assert result == [2]

    def test_multiple_modes(self):
        result = _mode([1, 1, 2, 2, 3])
        assert sorted(result) == [1, 2]

    def test_all_same(self):
        result = _mode([5, 5, 5])
        assert result == [5]

    def test_no_repeats(self):
        result = _mode([1, 2, 3])
        assert sorted(result) == [1, 2, 3]

    def test_empty(self):
        with pytest.raises(ValueError):
            _mode([])


# ── Variance Tests ─────────────────────────────────────────────


class TestVariance:
    """Tests for variance."""

    def test_population_variance(self):
        result = _variance([1, 2, 3, 4, 5], population=True)
        assert result == 2.0

    def test_sample_variance(self):
        result = _variance([1, 2, 3, 4, 5], population=False)
        assert result == 2.5

    def test_zero_variance(self):
        result = _variance([5, 5, 5, 5])
        assert result == 0.0

    def test_empty(self):
        with pytest.raises(ValueError):
            _variance([])

    def test_sample_too_small(self):
        with pytest.raises(ValueError):
            _variance([1], population=False)


# ── Standard Deviation Tests ───────────────────────────────────


class TestStddev:
    """Tests for stddev."""

    def test_population_stddev(self):
        result = _stddev([1, 2, 3, 4, 5], population=True)
        assert abs(result - 1.41421356) < 0.0001

    def test_sample_stddev(self):
        result = _stddev([1, 2, 3, 4, 5], population=False)
        assert abs(result - 1.58113883) < 0.0001

    def test_zero_stddev(self):
        result = _stddev([5, 5, 5, 5])
        assert result == 0.0

    def test_empty(self):
        with pytest.raises(ValueError):
            _stddev([])


# ── Correlation Tests ──────────────────────────────────────────


class TestCorrelation:
    """Tests for correlation."""

    def test_perfect_positive(self):
        result = _correlation([1, 2, 3, 4, 5], [2, 4, 6, 8, 10])
        assert abs(result - 1.0) < 0.0001

    def test_perfect_negative(self):
        result = _correlation([1, 2, 3, 4, 5], [10, 8, 6, 4, 2])
        assert abs(result - (-1.0)) < 0.0001

    def test_no_correlation(self):
        result = _correlation([1, 2, 3, 4, 5], [2, 1, 4, 3, 6])
        assert -1.0 <= result <= 1.0

    def test_different_lengths(self):
        with pytest.raises(ValueError):
            _correlation([1, 2, 3], [1, 2])

    def test_empty(self):
        with pytest.raises(ValueError):
            _correlation([], [])


# ── Percentile Tests ───────────────────────────────────────────


class TestPercentile:
    """Tests for percentile."""

    def test_median_percentile(self):
        result = _percentile([1, 2, 3, 4, 5], 50)
        assert result == 3.0

    def test_quartiles(self):
        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        q1 = _percentile(data, 25)
        q3 = _percentile(data, 75)
        assert q1 < q3

    def test_min_percentile(self):
        result = _percentile([1, 2, 3, 4, 5], 0)
        assert result == 1.0

    def test_max_percentile(self):
        result = _percentile([1, 2, 3, 4, 5], 100)
        assert result == 5.0

    def test_invalid_percentile(self):
        with pytest.raises(ValueError):
            _percentile([1, 2, 3], 101)

    def test_empty(self):
        with pytest.raises(ValueError):
            _percentile([], 50)


# ── Sum Tests ──────────────────────────────────────────────────


class TestSum:
    """Tests for sum."""

    def test_basic(self):
        result = _sum([1, 2, 3, 4, 5])
        assert result == 15.0

    def test_floats(self):
        result = _sum([1.5, 2.5, 3.0])
        assert result == 7.0

    def test_empty(self):
        result = _sum([])
        assert result == 0.0

    def test_negative(self):
        result = _sum([-1, -2, -3])
        assert result == -6.0


# ── Product Tests ──────────────────────────────────────────────


class TestProduct:
    """Tests for product."""

    def test_basic(self):
        result = _product([1, 2, 3, 4])
        assert result == 24.0

    def test_with_zero(self):
        result = _product([1, 2, 0, 4])
        assert result == 0.0

    def test_single(self):
        result = _product([5])
        assert result == 5.0

    def test_empty(self):
        result = _product([])
        assert result == 1.0


# ── Min Tests ──────────────────────────────────────────────────


class TestMin:
    """Tests for min."""

    def test_basic(self):
        result = _min([3, 1, 4, 1, 5])
        assert result == 1.0

    def test_negative(self):
        result = _min([-1, -5, -3])
        assert result == -5.0

    def test_single(self):
        result = _min([42])
        assert result == 42.0

    def test_empty(self):
        with pytest.raises(ValueError):
            _min([])


# ── Max Tests ──────────────────────────────────────────────────


class TestMax:
    """Tests for max."""

    def test_basic(self):
        result = _max([3, 1, 4, 1, 5])
        assert result == 5.0

    def test_negative(self):
        result = _max([-1, -5, -3])
        assert result == -1.0

    def test_single(self):
        result = _max([42])
        assert result == 42.0

    def test_empty(self):
        with pytest.raises(ValueError):
            _max([])
