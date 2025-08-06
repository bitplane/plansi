#!/usr/bin/env python3
"""Command-line interface for plansi."""

import argparse
import atexit
import os
import sys
from . import __version__
from .control_codes import SHOW_CURSOR, RESTORE_TERMINAL
from .pipe import VideoSplitter, ImageToAnsi, AnsiToCast, CastToAnsi, FileSink, TerminalPlayer


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
    parser.add_argument("--debug", action="store_true", help="Show debug information")

    args = parser.parse_args()

    try:
        # Determine input type
        is_cast_input = args.input.endswith(".cast")

        if is_cast_input:
            # Cast file input - play or convert
            # Start with a single input tuple
            source = iter([(0.0, args.input)])
            pipeline = CastToAnsi(source)

            # Store dimensions for output
            width = None
            height = None
        else:
            # Video file input - convert to ANSI
            # Start with a single input tuple
            source = iter([(0.0, args.input)])

            # Build video processing pipeline
            video = VideoSplitter(source, fps=args.fps)
            pipeline = ImageToAnsi(video, width=args.width)

            # Calculate height for terminal output
            # Will be set by ImageToAnsi on first frame
            width = args.width
            height = None

        if args.output:
            # Output to .cast file
            if not is_cast_input:
                # Need to convert ANSI to cast format
                cast = AnsiToCast(pipeline, width=width, title=f"plansi - {os.path.basename(args.input)}")
                sink = FileSink(cast, filepath=args.output)
            else:
                # Direct copy of cast file
                sink = FileSink(pipeline, filepath=args.output)

            # Process pipeline
            for _ in sink:
                pass  # FileSink handles writing

            print(f"Wrote cast file: {args.output}", file=sys.stderr)
        else:
            # Play to terminal
            # Get dimensions from first frame if needed
            if is_cast_input:
                # Peek at first frame to get dimensions from cast file
                # This is a bit hacky but works for now
                peek_source = iter([(0.0, args.input)])
                peek_pipe = CastToAnsi(peek_source)
                with peek_pipe:
                    # CastToAnsi stores dimensions in args after reading header
                    for _ in peek_pipe:
                        break  # Just need to trigger header read
                    width = peek_pipe.args.get("width", 80)
                    height = peek_pipe.args.get("height", 24)

                # Create fresh pipeline for actual playback
                source = iter([(0.0, args.input)])
                pipeline = CastToAnsi(source)
            else:
                # For video, height will be calculated by ImageToAnsi
                # Use a reasonable default for now
                height = int(args.width * 9 / 16 * 0.5)  # Assume 16:9 aspect ratio

            # Create terminal player
            player = TerminalPlayer(pipeline, realtime=True, debug=args.debug, width=width, height=height)

            # Play pipeline
            for _ in player:
                pass  # TerminalPlayer handles output

    except KeyboardInterrupt:
        # Clean exit on Ctrl+C
        print(RESTORE_TERMINAL, flush=True)
        sys.exit(0)
    except Exception as e:
        # Restore cursor on any error
        print(RESTORE_TERMINAL, flush=True)
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)
