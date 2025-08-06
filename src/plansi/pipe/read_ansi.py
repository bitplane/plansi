"""ANSI reader pipe."""

import sys
import time
from typing import Iterator, Tuple, Any

from .base import Pipe


class AnsiReader(Pipe):
    """Reads ANSI data from files or stdin and outputs ANSI strings.

    Input: (timestamp, filepath) where filepath is path to file or '-' for stdin
    Output: (timestamp, ansi_string) from the input source
    """

    def setup(self):
        """Initialize start time."""
        self.start_time = time.time()

    def process(self, timestamp: float, data: Any) -> Iterator[Tuple[float, str]]:
        """Read ANSI data and yield it."""
        filepath = data

        # Handle stdin vs file input
        if filepath == "-":
            # Read from stdin
            input_stream = sys.stdin
        else:
            # Read from file
            input_stream = open(filepath, "r", encoding="utf-8")

        try:
            # Read all content at once for now
            content = input_stream.read()
            if content:
                # Use elapsed time since setup
                elapsed_time = time.time() - self.start_time
                yield elapsed_time, content
        finally:
            # Close file if we opened it (but not stdin)
            if filepath != "-":
                input_stream.close()

        self.debug("content", f"{len(content) if content else 0} bytes")
