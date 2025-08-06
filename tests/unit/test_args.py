"""Tests for argument parsing and implied defaults."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from plansi.args import parse_args, _detect_input_format
from plansi.implied import implied
from unittest.mock import patch


def test_detect_input_format():
    """Test input format detection from various paths."""
    # Local files
    assert _detect_input_format("video.mp4") == "video"
    assert _detect_input_format("recording.cast") == "cast"
    assert _detect_input_format("movie.avi") == "video"
    assert _detect_input_format("data.txt") == "video"  # Default to video

    # URLs
    assert _detect_input_format("http://example.com/video.mp4") == "video"
    assert _detect_input_format("https://example.com/recording.cast") == "cast"
    assert _detect_input_format("http://stream.example.com/live") == "video"

    # stdin
    assert _detect_input_format("-") == "ansi"


def test_default_args():
    """Test default argument parsing without explicit options."""
    args = parse_args(["input.mp4"])

    # Basic arguments
    assert args.input == "input.mp4"
    assert args.output == "-" and implied(args.output)

    # Implied format detection
    assert args.input_format == "video" and implied(args.input_format)

    # Output flags
    assert args.stdout and implied(args.stdout)

    # Threshold and perceptual
    assert args.threshold == 5.0 and implied(args.threshold)
    assert args.perceptual and implied(args.perceptual)  # Perceptual enabled for video input


def test_cast_input_implies():
    """Test that cast input implies different defaults."""
    args = parse_args(["recording.cast"])

    assert args.input == "recording.cast"
    assert args.input_format == "cast" and implied(args.input_format)
    assert not args.perceptual and implied(args.perceptual)  # Cast implies no perceptual


def test_explicit_threshold_enables_perceptual():
    """Test that explicit threshold enables perceptual diff."""
    args = parse_args(["input.mp4", "--threshold", "10.0"])

    assert args.threshold == 10.0 and not implied(args.threshold)
    assert args.perceptual and implied(args.perceptual)  # Perceptual enabled due to explicit threshold


def test_explicit_format_overrides_detection():
    """Test explicit format overrides auto-detection."""
    args = parse_args(["video.mp4", "--input-format", "cast"])

    assert args.input_format == "cast" and not implied(args.input_format)
    assert not args.perceptual and implied(args.perceptual)  # Cast format implies no perceptual


def test_explicit_perceptual_overrides_defaults():
    """Test explicit perceptual flag overrides smart defaults."""
    # Force perceptual off for video input (which would normally enable it)
    args = parse_args(["video.mp4", "--no-perceptual"])

    assert args.input_format == "video" and implied(args.input_format)
    assert not args.perceptual and not implied(args.perceptual)  # User explicitly disabled it


def test_file_output():
    """Test file output disables stdout and realtime."""
    args = parse_args(["input.mp4", "output.cast"])

    assert args.output == "output.cast" and not implied(args.output)
    assert not args.stdout
    assert not args.realtime and implied(args.realtime)  # No realtime for file output


def test_url_input_detection():
    """Test URL input format detection."""
    args = parse_args(["https://example.com/stream.cast"])

    assert args.input == "https://example.com/stream.cast"
    assert args.input_format == "cast" and implied(args.input_format)


def test_stdin_input():
    """Test stdin input handling."""
    args = parse_args(["-"])

    assert args.input == "-"
    assert args.input_format == "ansi" and implied(args.input_format)  # Default to ansi for stdin


@patch("sys.stdout.isatty", return_value=True)
def test_tty_output_enables_realtime(mock_isatty):
    """Test that TTY output enables realtime."""
    args = parse_args(["input.mp4"])

    assert args.stdout and implied(args.stdout)
    assert args.realtime and implied(args.realtime)  # TTY enables realtime


@patch("sys.stdout.isatty", return_value=False)
def test_non_tty_output_disables_realtime(mock_isatty):
    """Test that non-TTY output disables realtime."""
    args = parse_args(["input.mp4"])

    assert args.stdout and implied(args.stdout)
    assert not args.realtime and implied(args.realtime)  # Non-TTY disables realtime


def test_explicit_realtime_overrides_tty_detection():
    """Test explicit realtime flag overrides TTY detection."""
    with patch("sys.stdout.isatty", return_value=True):
        args = parse_args(["input.mp4", "--no-realtime"])

        assert not args.realtime and not implied(args.realtime)  # User explicitly disabled it


def test_explicit_stdout_output():
    """Test explicit stdout output (plansi input -)."""
    args = parse_args(["input.mp4", "-"])

    assert args.input == "input.mp4"
    assert args.output == "-" and not implied(args.output)  # Explicitly set to stdout
    assert args.stdout and not implied(args.stdout)  # Should be True because output is '-'


def test_complex_argument_interaction():
    """Test complex interaction of multiple arguments."""
    args = parse_args(["video.mp4", "output.cast", "--threshold", "2.0", "--input-format", "cast"])

    # Input
    assert args.input == "video.mp4"
    assert args.input_format == "cast" and not implied(args.input_format)  # Explicitly set

    # Output
    assert args.output == "output.cast" and not implied(args.output)
    assert not args.stdout
    assert not args.realtime and implied(args.realtime)  # File output

    # Processing
    assert args.threshold == 2.0 and not implied(args.threshold)  # Explicitly set
    assert not args.perceptual and implied(args.perceptual)  # Cast format implies no perceptual
