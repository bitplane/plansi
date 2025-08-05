"""Main Player class that orchestrates video playback with differential rendering."""

from typing import Iterator, Tuple
from .core.video import VideoExtractor
from .core.diff import DiffEngine
from .core.render import ANSIRenderer


class Player:
    """Video player that generates (timestamp, ansi_str) tuples."""

    def __init__(
        self,
        width: int = 80,
        pixel_threshold: int = 30,
        cell_threshold: float = 0.25,
        fps: float = None,
        keyframe_interval: int = 30,
    ):
        """Initialize video player.

        Args:
            width: Terminal width in characters
            pixel_threshold: RGB distance threshold for pixel changes (0-255)
            cell_threshold: Fraction of pixels that must change in a cell (0.0-1.0)
            fps: Target playback FPS, None for original rate
            keyframe_interval: Send full refresh every N frames to prevent drift
        """
        self.width = width
        self.pixel_threshold = pixel_threshold
        self.cell_threshold = cell_threshold
        self.fps = fps
        self.keyframe_interval = keyframe_interval

    def play(self, video_path: str) -> Iterator[Tuple[float, str]]:
        """Generate (timestamp, ansi_str) tuples for video playback.

        Args:
            video_path: Path to video file

        Yields:
            Tuples of (timestamp_seconds, ansi_escape_sequences)
        """
        frame_count = 0

        with VideoExtractor(video_path, self.width, self.fps) as extractor:
            diff_engine = DiffEngine(self.pixel_threshold, self.cell_threshold)
            renderer = ANSIRenderer(self.width, extractor.height)

            # Clear screen at start
            clear_screen = "\x1b[2J\x1b[H"
            yield (0.0, clear_screen)

            for timestamp, frame in extractor.frames():
                # Check if this should be a keyframe (full refresh)
                is_keyframe = (frame_count % self.keyframe_interval) == 0

                if is_keyframe:
                    # Force full refresh by clearing diff engine reference
                    diff_engine.reference_frame = None
                    renderer.clear_cache()

                # Get changed cells
                changed_cells = diff_engine.get_changed_cells(frame)

                # Render differential output
                if changed_cells:
                    ansi_output = renderer.render_differential(frame, changed_cells)
                    if ansi_output:
                        yield (timestamp, ansi_output)

                # Update reference frame periodically to prevent drift
                if is_keyframe:
                    diff_engine.update_reference(frame)

                frame_count += 1
