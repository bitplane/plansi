"""Argument parsing for plansi."""

import argparse
import os
from . import __version__


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Play videos as ANSI in terminal")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("input", help="Path to video or .cast file")
    parser.add_argument("output", nargs="?", help="Optional output .cast file (if not provided, plays to console)")

    # Auto-detect terminal width
    try:
        default_width = os.get_terminal_size().columns
    except OSError:
        default_width = 80  # Fallback if not in a terminal

    parser.add_argument(
        "--width",
        "-w",
        type=int,
        default=default_width,
        help=f"Terminal width in characters (default: auto-detected {default_width})",
    )
    parser.add_argument("--fps", "-f", type=float, default=None, help="Target FPS (default: original video rate)")
    parser.add_argument(
        "--threshold",
        "-t",
        type=float,
        default=5.0,
        help="Perceptual color difference threshold for cell changes (default: 5.0)",
    )
    parser.add_argument("--no-diff", default=False, action="store_true", help="Disable differential rendering")
    parser.add_argument("--debug", default=False, action="store_true", help="Show debug information")
    parser.add_argument(
        "--cache-position", default=False, action="store_true", help="Enable cursor position caching (experimental)"
    )
    parser.add_argument(
        "--no-cache-style",
        dest="cache_style",
        default=True,
        action="store_false",
        help="Disable style caching optimization",
    )
    parser.add_argument("--log-file", default=None, help="Log debug messages to file")

    return parser.parse_args()
