"""Tests for Math statistics stdlib module.

Tests statistical operations and bitwise operations (v1.39.4).
"""

import pytest
from helen.stdlib.math_stats import (
    _mean, _median, _mode, _variance, _stddev,
    _correlation, _percentile, _sum, _product, _min, _max,
    _bit_and, _bit_or, _bit_xor, _bit_not, _bit_shift_left, _bit_shift_right,
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


# ── Bitwise Operations Tests (v1.39.4) ─────────────────────────


class TestBitwiseAnd:
    """Tests for bit_and."""

    def test_basic(self):
        assert _bit_and(5, 3) == 1  # 101 & 011 = 001

    def test_with_zero(self):
        assert _bit_and(42, 0) == 0

    def test_same_number(self):
        assert _bit_and(42, 42) == 42

    def test_powers_of_two(self):
        assert _bit_and(12, 10) == 8  # 1100 & 1010 = 1000

    def test_negative_numbers(self):
        assert _bit_and(-1, 5) == 5  # -1 is all 1s in two's complement

    def test_type_error_float(self):
        with pytest.raises(TypeError):
            _bit_and(5.0, 3)

    def test_type_error_string(self):
        with pytest.raises(TypeError):
            _bit_and("5", 3)


class TestBitwiseOr:
    """Tests for bit_or."""

    def test_basic(self):
        assert _bit_or(5, 3) == 7  # 101 | 011 = 111

    def test_with_zero(self):
        assert _bit_or(42, 0) == 42

    def test_same_number(self):
        assert _bit_or(42, 42) == 42

    def test_powers_of_two(self):
        assert _bit_or(12, 10) == 14  # 1100 | 1010 = 1110

    def test_negative_numbers(self):
        assert _bit_or(-1, 5) == -1  # -1 is all 1s

    def test_type_error(self):
        with pytest.raises(TypeError):
            _bit_or(5.5, 3)


class TestBitwiseXor:
    """Tests for bit_xor."""

    def test_basic(self):
        assert _bit_xor(5, 3) == 6  # 101 ^ 011 = 110

    def test_with_zero(self):
        assert _bit_xor(42, 0) == 42

    def test_same_number(self):
        assert _bit_xor(42, 42) == 0

    def test_powers_of_two(self):
        assert _bit_xor(12, 10) == 6  # 1100 ^ 1010 = 0110

    def test_self_inverse(self):
        # XOR is self-inverse: (a ^ b) ^ b == a
        a, b = 42, 17
        assert _bit_xor(_bit_xor(a, b), b) == a

    def test_type_error(self):
        with pytest.raises(TypeError):
            _bit_xor(5, 3.0)


class TestBitwiseNot:
    """Tests for bit_not."""

    def test_basic(self):
        assert _bit_not(5) == -6  # ~5 = -6

    def test_zero(self):
        assert _bit_not(0) == -1

    def test_negative(self):
        assert _bit_not(-1) == 0

    def test_double_negation(self):
        # ~~a == a
        assert _bit_not(_bit_not(42)) == 42

    def test_type_error(self):
        with pytest.raises(TypeError):
            _bit_not(5.0)


class TestBitShiftLeft:
    """Tests for bit_shift_left."""

    def test_basic(self):
        assert _bit_shift_left(5, 2) == 20  # 5 << 2 = 20

    def test_by_zero(self):
        assert _bit_shift_left(42, 0) == 42

    def test_by_one(self):
        assert _bit_shift_left(5, 1) == 10  # 5 << 1 = 10 (doubling)

    def test_power_of_two(self):
        assert _bit_shift_left(1, 10) == 1024

    def test_large_shift(self):
        assert _bit_shift_left(1, 20) == 1048576

    def test_negative_shift_error(self):
        with pytest.raises(ValueError):
            _bit_shift_left(5, -1)

    def test_type_error(self):
        with pytest.raises(TypeError):
            _bit_shift_left(5.0, 2)


class TestBitShiftRight:
    """Tests for bit_shift_right."""

    def test_basic(self):
        assert _bit_shift_right(20, 2) == 5  # 20 >> 2 = 5

    def test_by_zero(self):
        assert _bit_shift_right(42, 0) == 42

    def test_by_one(self):
        assert _bit_shift_right(10, 1) == 5  # 10 >> 1 = 5 (halving)

    def test_power_of_two(self):
        assert _bit_shift_right(1024, 10) == 1

    def test_negative_number(self):
        # Arithmetic right shift preserves sign
        assert _bit_shift_right(-20, 2) == -5

    def test_large_shift(self):
        assert _bit_shift_right(1048576, 20) == 1

    def test_negative_shift_error(self):
        with pytest.raises(ValueError):
            _bit_shift_right(5, -1)

    def test_type_error(self):
        with pytest.raises(TypeError):
            _bit_shift_right(5, 2.0)


class TestBitwiseIntegration:
    """Integration tests for bitwise operations."""

    def test_check_even_odd(self):
        # Check if number is even using bit_and
        for i in range(10):
            is_even = _bit_and(i, 1) == 0
            assert is_even == (i % 2 == 0)

    def test_multiply_by_power_of_two(self):
        # Multiplying by 2^n is same as left shift by n
        for i in range(5):
            for n in range(5):
                assert _bit_shift_left(i, n) == i * (2 ** n)

    def test_divide_by_power_of_two(self):
        # Integer division by 2^n is same as right shift by n
        for i in range(20):
            for n in range(3):
                divisor = 2 ** n
                assert _bit_shift_right(i, n) == i // divisor

    def test_swap_with_xor(self):
        # XOR swap algorithm
        a, b = 42, 17
        a = _bit_xor(a, b)
        b = _bit_xor(b, a)
        a = _bit_xor(a, b)
        assert a == 17 and b == 42

    def test_toggle_bits(self):
        # XOR with mask toggles specific bits
        value = 0b1010  # 10
        mask = 0b1100   # 12
        result = _bit_xor(value, mask)
        assert result == 0b0110  # 6

    def test_extract_bits(self):
        # Extract specific bits using AND
        value = 0b11010110  # 214
        mask = 0b00001111   # 15 (extract lower 4 bits)
        result = _bit_and(value, mask)
        assert result == 0b00000110  # 6

    def test_set_bits(self):
        # Set specific bits using OR
        value = 0b10100000  # 160
        mask = 0b00001111   # 15 (set lower 4 bits)
        result = _bit_or(value, mask)
        assert result == 0b10101111  # 175
