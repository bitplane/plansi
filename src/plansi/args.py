"""Argument parsing for plansi."""

import argparse
import os
import sys
from . import __version__
from .implied import Implied, implied


def parse_args(argv=sys.argv[1:]):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Play videos as ANSI in terminal with smart format detection",
        epilog="""Examples:
  %(prog)s video.mp4                    # Play video to terminal
  %(prog)s video.mp4 output.cast        # Convert video to .cast file
  %(prog)s recording.cast               # Play .cast file to terminal
  %(prog)s - < data.ansi                # Play ANSI data from stdin
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "input",
        help="Input source: video file (.mp4, .avi, .mov, etc), asciinema .cast recording, or '-' for data from stdin",
    )
    parser.add_argument(
        "output",
        nargs="?",
        default=Implied("-"),
        help="Output destination: .cast file for recording, or '-' for terminal playback (default: terminal)",
    )

    # Auto-detect terminal width
    try:
        default_width = os.get_terminal_size().columns
    except OSError:
        default_width = 80  # Fallback if not in a terminal

    parser.add_argument(
        "--width",
        "-w",
        type=int,
        default=Implied(default_width),
        help=f"Terminal width in characters (default: auto-detected {default_width})",
    )
    parser.add_argument(
        "--fps",
        "-f",
        type=float,
        default=None,
        help="Target playback FPS, slower than source skips frames (default: source video rate)",
    )
    parser.add_argument(
        "--threshold",
        "-t",
        type=float,
        default=Implied(5.0),
        help="Perceptual color difference threshold (0-100). Lower = more sensitive. (default: 5.0)",
    )
    parser.add_argument(
        "--no-diff", action="store_true", help="Disable differential rendering (always output full frames)"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Show debug information with frame stats and processing details"
    )
    parser.add_argument("--debug-args", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--cache-position",
        action="store_true",
        help="Cache cursor positions to reduce movement (experimental, may cause artifacts)",
    )
    parser.add_argument(
        "--no-cache-style",
        dest="cache_style",
        default=True,
        action="store_false",
        help="Disable style caching optimization (slower but more compatible)",
    )
    parser.add_argument("--log-file", metavar="FILE", help="Write debug messages to file instead of stderr")
    parser.add_argument(
        "--no-realtime",
        dest="realtime",
        action="store_false",
        default=None,
        help="Disable realtime playback (show all frames regardless of timing)",
    )
    parser.add_argument(
        "--no-perceptual",
        dest="perceptual",
        action="store_false",
        default=None,
        help="Disable perceptual color difference (use exact pixel matching)",
    )
    parser.add_argument(
        "--input-format",
        choices=["video", "cast", "ansi"],
        default=None,
        help="Force input format: video (mp4/avi/etc), cast (asciinema), ansi (raw text) (default: auto-detect)",
    )

    args = parser.parse_args(argv)

    # Set implied defaults using helper functions
    _set_input_format(args)
    _set_output_flags(args)
    _set_debug(args)
    _set_realtime(args)
    _set_perceptual(args)

    return args


def _detect_input_format(input_path):
    """Detect input format from file path/URL."""
    if input_path == "-":
        # stdin - assume ANSI data
        return "ansi"
    elif input_path.startswith(("http://", "https://")):
        # URL - check extension or assume video
        return "cast" if input_path.endswith(".cast") else "video"
    elif input_path.endswith(".cast"):
        # Local .cast file
        return "cast"
    else:
        # Assume video file
        return "video"


def _set_input_format(args):
    """Set input format based on file path/URL detection."""
    detected_format = _detect_input_format(args.input)
    args.input_format = Implied(detected_format, args.input_format)


def _set_output_flags(args):
    """Set output-related flags."""
    # Set stdout flag based on output destination
    args.stdout = Implied(True) if args.output == "-" and implied(args.output) else False


def _set_debug(args):
    """Set debug flag based on log file and debug args."""
    # --log-file or --debug-args implies --debug
    if args.log_file or args.debug_args:
        args.debug = Implied(True, args.debug)


def _set_realtime(args):
    """Set realtime flag based on output TTY detection."""
    # Auto-detect based on TTY
    output_is_a_tty = args.stdout and sys.stdout.isatty()
    args.realtime = Implied(output_is_a_tty, args.realtime)


def _set_perceptual(args):
    """Set perceptual flag based on input format."""
    # Auto-detect based on input format
    text_format = args.input_format in ("cast", "ansi")
    args.perceptual = Implied(not text_format, args.perceptual)
