"""Video reader pipe."""

import av
from typing import Iterator, Tuple, Any
from PIL import Image

from .base import Pipe


class VideoReader(Pipe):
    """Reads video files and outputs PIL Images at timestamps.

    Input: (timestamp, filepath) where filepath is path to video
    Output: (timestamp, PIL.Image) for each frame
    """

    def setup(self):
        """Initialize video container cache."""
        self.containers = {}

    def teardown(self):
        """Close all open video containers."""
        for container in self.containers.values():
            container.close()
        self.containers.clear()

    def process(self, timestamp: float, data: Any) -> Iterator[Tuple[float, Image.Image]]:
        """Extract frames from video file."""
        filepath = data

        # Open container if not cached
        if filepath not in self.containers:
            self.containers[filepath] = av.open(filepath)

        container = self.containers[filepath]
        stream = container.streams.video[0]

        # Get target FPS if specified

        frame_interval = None
        if self.args.fps:
            frame_interval = 1.0 / self.args.fps
        last_time = 0.0
        frame_count = 0
        skipped_count = 0

        self.debug("fps", self.args.fps or "original")

        # Decode frames
        for frame in container.decode(stream):
            frame_time = float(frame.time)
            frame_count += 1

            # Skip frames if target FPS is lower than source
            if frame_interval and (frame_time - last_time) < (frame_interval * 0.9):
                skipped_count += 1
                continue

            self.debug("processed", f"{frame_count}/{skipped_count}")

            # Convert to PIL Image
            img = frame.to_image()

            # Ensure RGB format
            if img.mode != "RGB":
                img = img.convert("RGB")

            yield frame_time, img
            last_time = frame_time

        self.debug("total", f"{frame_count}/{skipped_count}")
