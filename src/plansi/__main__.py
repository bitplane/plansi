"""Command-line interface for plansi."""

import argparse
import json
import os
import sys
import time
from .player import Player


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Play videos as differential ANSI in terminal")
    parser.add_argument("video", help="Path to video file")
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

        if args.output:
            # Write to .cast file
            write_cast_file(player, args.video, args.output, args.width)
        else:
            # Play to console
            play_to_console(player, args.video)

    except KeyboardInterrupt:
        # Clean exit on Ctrl+C
        print("\x1b[0m", flush=True)  # Reset terminal colors
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


def play_to_console(player: Player, video_path: str):
    """Play video to console with timing."""
    last_timestamp = 0.0

    for timestamp, ansi_output in player.play(video_path):
        # Sleep to maintain timing
        if timestamp > last_timestamp:
            sleep_time = timestamp - last_timestamp
            if sleep_time > 0:
                time.sleep(sleep_time)

        # Output ANSI to terminal
        sys.stdout.write(ansi_output)
        sys.stdout.flush()
        last_timestamp = timestamp


def write_cast_file(player: Player, video_path: str, output_path: str, width: int):
    """Write video to .cast file format."""
    with open(output_path, "w") as cast_file:
        first_frame = True

        for timestamp, ansi_output in player.play(video_path):
            if first_frame:
                # Write asciinema header with actual video dimensions
                header = {
                    "version": 2,
                    "width": width,
                    "height": player.height,
                    "timestamp": int(time.time()),
                    "title": f"plansi - {os.path.basename(video_path)}",
                }
                cast_file.write(json.dumps(header) + "\n")
                first_frame = False

            # Write cast entry: [timestamp, "o", data]
            cast_entry = [timestamp, "o", ansi_output]
            cast_file.write(json.dumps(cast_entry) + "\n")

        print(f"Wrote cast file: {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
