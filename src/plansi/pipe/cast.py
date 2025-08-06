"""Asciicast format pipes for reading and writing .cast files."""

import json
import time
from typing import Iterator, Tuple, Any

from .base import Pipe


class CastToAnsi(Pipe):
    """Reads .cast files and outputs ANSI sequences.

    Input: (timestamp, filepath) where filepath is path to .cast file
    Output: (timestamp, ansi_string) from the cast file
    """

    def process(self, timestamp: float, data: Any) -> Iterator[Tuple[float, str]]:
        """Read cast file and yield ANSI data.

        Args:
            timestamp: Ignored (cast files have their own timeline)
            data: Path to .cast file

        Yields:
            (timestamp, ansi_string) from cast entries
        """
        filepath = data

        with open(filepath, "r", encoding="utf-8") as f:
            # Read header (first line)
            header_line = f.readline().strip()
            if not header_line:
                raise ValueError(f"Empty cast file: {filepath}")

            try:
                header = json.loads(header_line)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in cast header: {e}")

            # Validate header
            if header.get("version") != 2:
                raise ValueError(f"Unsupported cast version: {header.get('version')}")

            # Store dimensions in args for downstream pipes
            self.args["width"] = header.get("width", 80)
            self.args["height"] = header.get("height", 24)

            # Process data lines
            for line_num, line in enumerate(f, 2):
                line = line.strip()
                if not line:
                    continue

                try:
                    entry = json.loads(line)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON at line {line_num}: {e}")

                # Validate entry format: [timestamp, event_type, data]
                if not isinstance(entry, list) or len(entry) != 3:
                    raise ValueError(f"Invalid entry format at line {line_num}: {entry}")

                entry_time, event_type, ansi_data = entry

                # Only process output events
                if event_type == "o":
                    yield float(entry_time), ansi_data


class AnsiToCast(Pipe):
    """Converts ANSI sequences to .cast file format (JSON lines).

    Input: (timestamp, ansi_string)
    Output: (timestamp, json_string) for each line of the cast file
    """

    def setup(self):
        """Track if header has been written."""
        self.header_written = False

    def process(self, timestamp: float, data: Any) -> Iterator[Tuple[float, str]]:
        """Convert ANSI to cast format JSON.

        Args:
            timestamp: Frame timestamp
            data: ANSI escape sequences

        Yields:
            (timestamp, json_string) for cast file lines
        """
        # Write header on first frame
        if not self.header_written:
            header = {
                "version": 2,
                "width": self.args.get("width", 80),
                "height": self.args.get("height", 24),
                "timestamp": int(time.time()),
                "title": self.args.get("title", "plansi recording"),
            }
            yield 0.0, json.dumps(header)
            self.header_written = True

        # Skip empty output
        ansi_string = data
        if ansi_string and ansi_string.strip():
            # Create cast entry: [timestamp, "o", data]
            cast_entry = [float(f"{timestamp:.4f}"), "o", ansi_string]
            yield timestamp, json.dumps(cast_entry)
