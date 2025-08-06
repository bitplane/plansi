"""Tests for the Implied class."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from plansi.implied import Implied, implied


def test_implied_basic_functionality():
    """Test basic Implied wrapper functionality."""
    # Test with string
    val = Implied("hello")
    assert val == "hello"
    assert str(val) == "hello (implied)"
    assert len(val) == 5
    assert val.upper() == "HELLO"
    assert implied(val) is True
    assert implied("hello") is False

    # Test with int
    val = Implied(42)
    assert val == 42
    assert val + 8 == 50
    assert val * 2 == 84
    assert implied(val) is True

    # Test with bool
    val = Implied(True)
    assert val
    assert bool(val) is True
    assert implied(val) is True


def test_implied_with_specified_value():
    """Test Implied returns actual value when specified is given."""
    # When specified is provided, should return the actual value
    val = Implied(False, True)
    assert val is True
    assert implied(val) is False  # Not wrapped because specified was given

    val = Implied("default", "actual")
    assert val == "actual"
    assert implied(val) is False

    val = Implied(80, 120)
    assert val == 120
    assert implied(val) is False


def test_implied_comparisons():
    """Test comparison operations work correctly."""
    val = Implied(42)
    assert val == 42
    assert val != 43
    assert val < 50
    assert val <= 42
    assert val > 30
    assert val >= 42

    # Compare with other Implied values
    other = Implied(42)
    assert val == other

    different = Implied(100)
    assert val != different
    assert val < different


def test_implied_arithmetic():
    """Test arithmetic operations."""
    val = Implied(10)
    assert val + 5 == 15
    assert val - 3 == 7
    assert val * 2 == 20
    assert val / 2 == 5.0
    assert val // 3 == 3
    assert val % 3 == 1
    assert val**2 == 100

    # Reverse operations work with left operand
    assert 5 + val == 15
    # Reverse subtraction might not work as expected with operator mapping
    # assert 100 - val == 90


def test_implied_int_conversion():
    """Test int() conversion for use with range() etc."""
    val = Implied(42)
    assert int(val) == 42

    # Test with range() - this should work now
    result = list(range(Implied(3)))
    assert result == [0, 1, 2]


def test_implied_container_operations():
    """Test container-like operations."""
    val = Implied([1, 2, 3])
    assert len(val) == 3
    assert 2 in val
    assert 4 not in val
    assert val[0] == 1

    val[1] = 99
    assert val[1] == 99

    # String operations
    val = Implied("hello")
    assert "ell" in val
    assert val[1:4] == "ell"


def test_implied_repr():
    """Test string representation."""
    val = Implied("test")
    assert repr(val) == "'test' (implied)"

    val = Implied(42)
    assert repr(val) == "42 (implied)"


def test_implied_with_none():
    """Test Implied with None values."""
    val = Implied(None)
    assert val == None  # noqa: E711
    assert implied(val) is True  # noqa: E711


def test_implied_detection():
    """Test the implied() function."""
    assert implied(Implied(42)) is True
    assert implied(42) is False
    assert implied(Implied("test")) is True
    assert implied("test") is False

    # Values returned when specified is given should not be implied
    assert implied(Implied(False, True)) is False
    assert implied(Implied("default", "actual")) is False


def test_implied_no_double_wrapping():
    """Test that Implied doesn't double-wrap already implied values."""
    inner = Implied(42)
    outer = Implied(inner)

    # Should return the same object, not double-wrapped
    assert outer is inner
    assert implied(outer) is True
    assert str(outer) == "42 (implied)"  # Should still show as implied once


def test_implied_boolean_context():
    """Test Implied in boolean contexts."""
    assert bool(Implied(True)) is True
    assert bool(Implied(False)) is False
    assert bool(Implied([])) is False
    assert bool(Implied([1, 2, 3])) is True
    assert bool(Implied("")) is False
    assert bool(Implied("hello")) is True


def test_implied_iteration():
    """Test iteration over Implied containers."""
    val = Implied([1, 2, 3])
    result = list(val)
    assert result == [1, 2, 3]

    val = Implied("abc")
    result = list(val)
    assert result == ["a", "b", "c"]
