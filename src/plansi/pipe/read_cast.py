"""Asciicast reader pipe."""

import json
from typing import Iterator, Tuple, Any

from .base import Pipe


class CastReader(Pipe):
    """Reads .cast files and outputs ANSI sequences.

    Input: (timestamp, filepath) where filepath is path to .cast file
    Output: (timestamp, ansi_string) from the cast file
    """

    def process(self, timestamp: float, data: Any) -> Iterator[Tuple[float, str]]:
        """Read cast file and yield ANSI data."""
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
            if hasattr(self.args, "__dict__"):
                self.args.width = header.get("width", 80)
                self.args.height = header.get("height", 24)

            self.debug(f"Cast file: {header.get('width', 80)}x{header.get('height', 24)}")

            # Process data lines
            entry_count = 0
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
                    entry_count += 1
                    yield float(entry_time), ansi_data

            self.debug(f"Cast read complete: {entry_count} entries")
