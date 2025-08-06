#!/usr/bin/env python3
"""Command-line interface for plansi."""

import argparse
import atexit
import os
import sys
from . import __version__
from .control_codes import SHOW_CURSOR, RESTORE_TERMINAL
from .pipe import VideoReader, ImageToAnsi, CastWriter, CastReader, AnsiBuffer, FileWriter, TerminalPlayer


def restore_cursor():
    """Restore cursor visibility on exit."""
    print(SHOW_CURSOR, end="", flush=True)


def main():
    """Main CLI entry point."""
    # Register cursor restoration for any exit scenario
    atexit.register(restore_cursor)

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

    args = parser.parse_args()

    try:
        # Determine input type
        is_cast_input = args.input.endswith(".cast")

        # Create input list for source pipe
        input_list = [(0.0, args.input)]

        if is_cast_input:
            # Cast file input - play or convert
            pipeline = CastReader(input_list, args)
        else:
            # Video file input - convert to ANSI
            video = VideoReader(input_list, args)
            pipeline = ImageToAnsi(video, args)

        # Apply differential rendering unless disabled
        if not args.no_diff:
            pipeline = AnsiBuffer(pipeline, args)

        if args.output:
            # Output to .cast file
            if not is_cast_input:
                # Need to convert ANSI to cast format
                args.title = f"plansi - {os.path.basename(args.input)}"
                cast = CastWriter(pipeline, args)
                sink = FileWriter(cast, args)
            else:
                # Direct copy of cast file
                sink = FileWriter(pipeline, args)

            # Process pipeline
            for _ in sink:
                pass  # FileSink handles writing

            print(f"Wrote cast file: {args.output}", file=sys.stderr)
        else:
            # Play to terminal
            args.realtime = True
            player = TerminalPlayer(pipeline, args)

            # Play pipeline
            for _ in player:
                pass  # TerminalPlayer handles output

    except KeyboardInterrupt:
        # Clean exit on Ctrl+C
        print(RESTORE_TERMINAL, flush=True)
        sys.exit(0)
    except Exception:
        # Restore cursor on any error
        print(RESTORE_TERMINAL, flush=True)
        # Let the exception propagate with full stack trace
        raise
