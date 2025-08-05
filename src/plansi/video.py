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

        # Calculate character height maintaining aspect ratio
        # Let chafa handle pixel scaling - we just need character dimensions
        original_width = self._stream.width
        original_height = self._stream.height
        aspect_ratio = original_height / original_width
        self.height = int(self.width * aspect_ratio * 0.5)  # Terminal chars are ~2:1 aspect ratio

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

            # Get original image - chafa will handle all scaling
            img = frame.to_image()

            yield timestamp, img
            last_time = timestamp
