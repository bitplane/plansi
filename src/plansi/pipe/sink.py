"""Output sinks for pipeline termination."""

import sys
import time
from typing import Iterator, Tuple, Any

from .base import Pipe
from ..control_codes import SETUP_TERMINAL, RESTORE_TERMINAL, HOME_CURSOR


class FileSink(Pipe):
    """Writes data to a file.

    Input: (timestamp, string_data)
    Output: passes through input (for potential chaining)

    Args (via self.args):
        filepath: Path to output file
        mode: File mode (default 'w')
    """

    def setup(self):
        """Open output file."""
        filepath = self.args.get("filepath")
        if not filepath:
            raise ValueError("FileSink requires 'filepath' in args")

        mode = self.args.get("mode", "w")
        self.file = open(filepath, mode, encoding="utf-8")

    def teardown(self):
        """Close output file."""
        if hasattr(self, "file"):
            self.file.close()

    def process(self, timestamp: float, data: Any) -> Iterator[Tuple[float, Any]]:
        """Write data to file and pass through.

        Args:
            timestamp: Data timestamp
            data: String data to write

        Yields:
            Original (timestamp, data) unchanged
        """
        # Write data with newline
        self.file.write(str(data) + "\n")
        self.file.flush()

        # Pass through for potential chaining
        yield timestamp, data


class TerminalPlayer(Pipe):
    """Plays ANSI sequences to terminal with proper timing.

    Input: (timestamp, ansi_string)
    Output: passes through input (for potential monitoring)

    Args (via self.args):
        realtime: Skip frames to maintain timing (default True)
        debug: Show debug info (default False)
    """

    def setup(self):
        """Setup terminal and timing."""
        self.realtime = self.args.get("realtime", True)
        self.debug = self.args.get("debug", False)
        self.start_time = None
        self.frame_count = 0
        self.skipped_frames = 0

        # Setup terminal
        sys.stdout.write(SETUP_TERMINAL)
        sys.stdout.flush()

    def teardown(self):
        """Restore terminal."""
        # Get dimensions for cursor positioning
        height = self.args.get("height", 24)

        # Restore terminal and position cursor below content
        sys.stdout.write(f"{RESTORE_TERMINAL}\x1b[{height + 1};1H")
        sys.stdout.flush()

    def process(self, timestamp: float, data: Any) -> Iterator[Tuple[float, Any]]:
        """Output ANSI to terminal with timing control.

        Args:
            timestamp: When to display this frame
            data: ANSI escape sequences

        Yields:
            Original (timestamp, data) for monitoring
        """
        # Initialize timer on first frame
        if self.start_time is None:
            self.start_time = time.time()

        if self.realtime:
            # Calculate when this frame should appear
            current_time = time.time() - self.start_time

            if current_time > timestamp:
                # We're behind - skip this frame
                self.skipped_frames += 1
                self.frame_count += 1
                # Still yield for monitoring but don't display
                yield timestamp, data
                return
            else:
                # Wait until it's time
                sleep_time = timestamp - current_time
                if sleep_time > 0:
                    time.sleep(sleep_time)

                # Report skipped frames when we catch up
                if self.skipped_frames > 0 and self.debug:
                    sys.stderr.write(f"Skipped {self.skipped_frames} frames\n")
                    self.skipped_frames = 0

        # Move cursor to home and output ANSI
        sys.stdout.write(HOME_CURSOR + data)

        # Debug info
        if self.debug:
            height = self.args.get("height", 24)
            status = f"\x1b[0m\x1b[{height + 1};1HFrame: {self.frame_count}"
            if self.realtime:
                status += f", Skipped: {self.skipped_frames}"
            sys.stdout.write(status)

        sys.stdout.flush()
        self.frame_count += 1

        # Pass through for monitoring
        yield timestamp, data
