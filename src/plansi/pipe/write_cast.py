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
        ansi_string = data

        # Skip empty output
        if not ansi_string or not ansi_string.strip():
            return

        # Write header on first actual data (not on events)
        if not self.header_written:
            header = {
                "version": 2,
                "width": self.width,
                "height": self.height,
                "timestamp": int(time.time()),
                "title": getattr(self.args, "title", "plansi recording"),
            }
            yield 0.0, json.dumps(header)
            self.header_written = True
            self.debug("header", f"{self.width}x{self.height}")

        # Convert \n to \r\n for asciinema compatibility (since it doesn't support LNM mode)
        ansi_string = ansi_string.replace("\n", "\r\n")
        # Create cast entry: [timestamp, "o", data]
        cast_entry = [float(f"{timestamp:.4f}"), "o", ansi_string]
        yield timestamp, json.dumps(cast_entry)

    # The base class on_resize handles updating self.width/height
