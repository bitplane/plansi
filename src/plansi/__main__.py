"""Command-line interface for plansi."""

import argparse
import os
import sys
import time
from .player import Player


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Play videos as differential ANSI in terminal")
    parser.add_argument("video", help="Path to video file")
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
    parser.add_argument("--no-diff", action="store_true", help="Disable differential rendering, output full frames")
    parser.add_argument("--debug", action="store_true", help="Show debug information about cell comparisons")

    args = parser.parse_args()

    try:
        player = Player(
            width=args.width,
            color_threshold=args.threshold,
            fps=args.fps,
            no_diff=args.no_diff,
            debug=args.debug,
        )

        last_timestamp = 0.0

        for timestamp, ansi_output in player.play(args.video):
            # Sleep to maintain timing
            if timestamp > last_timestamp:
                sleep_time = timestamp - last_timestamp
                if sleep_time > 0:
                    time.sleep(sleep_time)

            # Output ANSI to terminal
            sys.stdout.write(ansi_output)
            sys.stdout.flush()
            last_timestamp = timestamp

    except KeyboardInterrupt:
        # Clean exit on Ctrl+C
        print("\x1b[0m", flush=True)  # Reset terminal colors
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
