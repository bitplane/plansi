"""Command-line interface for plansi."""

import argparse
import sys
import time
from .player import Player


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Play videos as differential ANSI in terminal")
    parser.add_argument("video", help="Path to video file")
    parser.add_argument("--width", "-w", type=int, default=80, help="Terminal width in characters (default: 80)")
    parser.add_argument("--fps", "-f", type=float, default=None, help="Target FPS (default: original video rate)")
    parser.add_argument(
        "--pixel-threshold", "-p", type=int, default=30, help="RGB distance threshold for pixel changes (default: 30)"
    )
    parser.add_argument(
        "--cell-threshold",
        "-c",
        type=float,
        default=0.25,
        help="Fraction of pixels that must change in cell (default: 0.25)",
    )
    parser.add_argument(
        "--keyframe-interval",
        "-k",
        type=int,
        default=30,
        help="Full refresh every N frames to prevent drift (default: 30)",
    )

    args = parser.parse_args()

    try:
        player = Player(
            width=args.width,
            pixel_threshold=args.pixel_threshold,
            cell_threshold=args.cell_threshold,
            fps=args.fps,
            keyframe_interval=args.keyframe_interval,
        )

        last_timestamp = 0.0

        for timestamp, ansi_output in player.play(args.video):
            # Sleep to maintain timing
            if timestamp > last_timestamp:
                sleep_time = timestamp - last_timestamp
                if sleep_time > 0:
                    time.sleep(sleep_time)

            # Output ANSI to terminal
            print(ansi_output, end="", flush=True)
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
