"""Command-line interface for plansi."""

import argparse
import os
import sys
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
    parser.add_argument(
        "--cache-position", action="store_true", help="Enable cursor position caching optimization (experimental)"
    )
    parser.add_argument(
        "--no-cache-style", action="store_false", dest="cache_style", help="Disable style caching optimization"
    )

    args = parser.parse_args()

    try:
        if args.output:
            # Write to .cast file - use non-realtime to process every frame
            cast_player = Player(
                width=args.width,
                color_threshold=args.threshold,
                fps=args.fps,
                no_diff=args.no_diff,
                debug=args.debug,
                realtime=False,  # Process every frame for complete recording
                cache_position=args.cache_position,
                cache_style=args.cache_style,
            )
            write_cast_file(cast_player, args.video, args.output)
        else:
            # Play to console - use realtime to skip frames as needed
            console_player = Player(
                width=args.width,
                color_threshold=args.threshold,
                fps=args.fps,
                no_diff=args.no_diff,
                debug=args.debug,
                realtime=True,  # Skip frames to maintain timing
                cache_position=args.cache_position,
                cache_style=args.cache_style,
            )
            play_to_console(console_player, args.video)

    except KeyboardInterrupt:
        # Clean exit on Ctrl+C
        print("\x1b[0m", flush=True)  # Reset terminal colors
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


def play_to_console(player: Player, video_path: str):
    """Play video to console (timing handled by Player.play() with realtime flag)."""
    for timestamp, ansi_output in player.frames(video_path):
        # Output ANSI to terminal (no sleep needed - timing handled in Player.play())
        sys.stdout.write(ansi_output)
        sys.stdout.flush()


def write_cast_file(player: Player, video_path: str, output_path: str):
    """Write video to .cast file format."""
    with open(output_path, "w") as cast_file:
        for cast_line in player.cast_entries(video_path):
            cast_file.write(cast_line + "\n")

        print(f"Wrote cast file: {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
