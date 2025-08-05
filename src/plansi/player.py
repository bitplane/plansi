"""Main Player class that orchestrates video playback with differential rendering."""

from typing import Iterator, Tuple
import json
import time
import os
import sys
from .core.video import VideoExtractor
from .core.terminal_render import TerminalRenderer


class Player:
    """Video player that generates (timestamp, ansi_str) tuples."""

    def __init__(
        self,
        width: int = 80,
        color_threshold: float = 5.0,
        fps: float = None,
        no_diff: bool = False,
        debug: bool = False,
        realtime: bool = True,
        cache_position: bool = False,
        cache_style: bool = True,
    ):
        """Initialize video player.

        Args:
            width: Terminal width in characters
            color_threshold: RGB distance threshold for color changes (0.0-441.0)
            fps: Target playback FPS, None for original rate
            no_diff: Disable differential rendering
            debug: Enable debug output
            realtime: Skip frames to maintain real-time playback (True for console, False for cast files)
            cache_position: Enable cursor position caching optimization (experimental)
            cache_style: Enable style caching optimization (default: True)
        """
        self.width = width
        self.color_threshold = color_threshold
        self.fps = fps
        self.no_diff = no_diff
        self.debug = debug
        self.realtime = realtime
        self.cache_position = cache_position
        self.cache_style = cache_style

    def play(self, video_path: str) -> Iterator[Tuple[float, str]]:
        """Generate (timestamp, ansi_str) tuples for video playbook.

        Args:
            video_path: Path to video file

        Yields:
            Tuples of (timestamp_seconds, ansi_escape_sequences)
        """
        frame_count = 0
        skipped_frames = 0
        start_time = time.time() if self.realtime else None
        last_timestamp = 0.0

        with VideoExtractor(video_path, self.width, self.fps) as extractor:
            # Store height for external access
            self.height = extractor.height

            renderer = TerminalRenderer(
                self.width,
                extractor.height,
                color_threshold=self.color_threshold,
                debug=self.debug,
                cache_position=self.cache_position,
                cache_style=self.cache_style,
            )

            # Clear screen and hide cursor at start
            setup_terminal = "\x1b[2J\x1b[H\x1b[?25l"  # Clear screen, home cursor, hide cursor
            yield (0.0, setup_terminal)

            for timestamp, frame in extractor.frames():
                # Frame skipping and timing logic for real-time playback
                if self.realtime:
                    current_time = time.time() - start_time
                    if current_time > timestamp:
                        # Skip this frame - we're running behind
                        skipped_frames += 1
                        frame_count += 1
                        continue
                    else:
                        # Wait until it's time to show this frame
                        sleep_time = timestamp - current_time
                        if sleep_time > 0:
                            time.sleep(sleep_time)

                        if skipped_frames > 0 and self.debug:
                            # Report skipped frames when we catch up
                            print(f"Skipped {skipped_frames} frames", file=sys.stderr)
                            skipped_frames = 0

                if self.no_diff:
                    # No differential rendering - output full frame
                    full_ansi = renderer._render_full_frame(frame)
                    if self.debug:
                        status = f"\x1b[0m\x1b[{extractor.height + 1};1HFrame: {frame_count}, Mode: full{' ' * 20}"
                        yield (timestamp, f"\x1b[H{full_ansi}{status}")
                    else:
                        yield (timestamp, f"\x1b[H{full_ansi}")
                else:
                    # Differential rendering
                    ansi_output, num_changed = renderer.render_differential(frame, set())

                    # Add status line only in debug mode
                    if self.debug:
                        status = f"\x1b[0m\x1b[{extractor.height + 1};1HFrame: {frame_count}, Changed: {num_changed}{' ' * 20}"
                        yield (timestamp, f"{ansi_output}{status}")
                    else:
                        yield (timestamp, ansi_output)

                frame_count += 1
                last_timestamp = timestamp

            # After final frame, reset terminal, show cursor, and move below video area for clean shell prompt
            terminal_cleanup = f"\x1b[0m\x1b[?25h\x1b[{extractor.height + 1};1H"  # Reset, show cursor, position below
            yield (last_timestamp, terminal_cleanup)

    def frames(self, video_path: str) -> Iterator[Tuple[float, str]]:
        """Generate raw frame data without timing delays.

        Args:
            video_path: Path to video file

        Yields:
            Tuples of (timestamp_seconds, ansi_escape_sequences)
        """
        for timestamp, ansi_output in self.play(video_path):
            yield timestamp, ansi_output

    def cast_entries(self, video_path: str) -> Iterator[str]:
        """Generate .cast file entries (JSON lines).

        Args:
            video_path: Path to video file

        Yields:
            JSON strings for .cast file format
        """
        first_frame = True

        for timestamp, ansi_output in self.frames(video_path):
            if first_frame:
                # Write asciinema header with actual video dimensions
                header = {
                    "version": 2,
                    "width": self.width,
                    "height": self.height,
                    "timestamp": int(time.time()),
                    "title": f"plansi - {os.path.basename(video_path)}",
                }
                yield json.dumps(header)
                first_frame = False

            # Skip empty output lines
            if ansi_output.strip():
                # Write cast entry: [timestamp, "o", data] with formatted timestamp
                cast_entry = [float(f"{timestamp:.4f}"), "o", ansi_output]
                yield json.dumps(cast_entry)
