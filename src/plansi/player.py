"""Main Player class that orchestrates video playback with differential rendering."""

from typing import Iterator, Tuple
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
    ):
        """Initialize video player.

        Args:
            width: Terminal width in characters
            color_threshold: RGB distance threshold for color changes (0.0-441.0)
            fps: Target playback FPS, None for original rate
            no_diff: Disable differential rendering
        """
        self.width = width
        self.color_threshold = color_threshold
        self.fps = fps
        self.no_diff = no_diff
        self.debug = debug

    def play(self, video_path: str) -> Iterator[Tuple[float, str]]:
        """Generate (timestamp, ansi_str) tuples for video playbook.

        Args:
            video_path: Path to video file

        Yields:
            Tuples of (timestamp_seconds, ansi_escape_sequences)
        """
        frame_count = 0

        with VideoExtractor(video_path, self.width, self.fps) as extractor:
            # Store height for external access
            self.height = extractor.height

            renderer = TerminalRenderer(
                self.width, extractor.height, color_threshold=self.color_threshold, debug=self.debug
            )

            # Clear screen at start
            clear_screen = "\x1b[2J\x1b[H"
            yield (0.0, clear_screen)

            for timestamp, frame in extractor.frames():
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
