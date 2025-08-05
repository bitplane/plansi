"""Video frame extraction using PyAV with scaling."""

import av
from PIL import Image
from typing import Iterator, Tuple


class VideoExtractor:
    """Extracts and scales video frames using PyAV."""

    def __init__(self, video_path: str, width: int, fps: float = None):
        """Initialize video extractor.

        Args:
            video_path: Path to video file
            width: Target width in characters (height auto-calculated)
            fps: Target FPS, None for original rate
        """
        self.video_path = video_path
        self.width = width
        self.fps = fps
        self._container = None
        self._stream = None

    def __enter__(self):
        self._container = av.open(self.video_path)
        self._stream = self._container.streams.video[0]

        # Calculate height maintaining aspect ratio
        # Each character cell is 8x4 pixels in chafa
        original_width = self._stream.width
        original_height = self._stream.height
        pixel_width = self.width * 8
        pixel_height = int((pixel_width * original_height) / original_width)
        # Round to nearest multiple of 4 for character alignment
        self.height = (pixel_height + 2) // 4
        self.pixel_height = self.height * 4

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._container:
            self._container.close()

    def frames(self) -> Iterator[Tuple[float, Image.Image]]:
        """Generate (timestamp, PIL.Image) tuples."""
        if not self._container:
            raise RuntimeError("VideoExtractor not initialized - use with statement")

        frame_interval = 1.0 / self.fps if self.fps else None
        last_time = 0.0

        for frame in self._container.decode(self._stream):
            timestamp = float(frame.time)

            # Skip frames if target FPS is lower than source
            if frame_interval and (timestamp - last_time) < frame_interval:
                continue

            # Scale frame to target size
            img = frame.to_image()
            img = img.resize((self.width * 8, self.pixel_height), Image.LANCZOS)

            yield timestamp, img
            last_time = timestamp
