"""Asciicast writer pipe."""

import json
import time
from typing import Iterator, Tuple, Any

from .base import Pipe


class CastWriter(Pipe):
    """Converts ANSI sequences to .cast file format (JSON lines).

    Input: (timestamp, ansi_string)
    Output: (timestamp, json_string) for each line of the cast file
    """

    def setup(self):
        """Track if header has been written."""
        self.header_written = False

    def process(self, timestamp: float, data: Any) -> Iterator[Tuple[float, str]]:
        """Convert ANSI to cast format JSON."""
        # Write header on first frame
        if not self.header_written:
            header = {
                "version": 2,
                "width": getattr(self.args, "width", 80),
                "height": getattr(self.args, "height", 24),
                "timestamp": int(time.time()),
                "title": getattr(self.args, "title", "plansi recording"),
            }
            yield 0.0, json.dumps(header)
            self.header_written = True
            self.debug("header", f"{header['width']}x{header['height']}")

        # Skip empty output
        ansi_string = data
        if ansi_string and ansi_string.strip():
            # Create cast entry: [timestamp, "o", data]
            cast_entry = [float(f"{timestamp:.4f}"), "o", ansi_string]
            yield timestamp, json.dumps(cast_entry)
