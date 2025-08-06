"""Terminal player for ANSI sequences."""

import sys
import time
from typing import Iterator, Tuple, Any

from .base import Pipe
from ..control_codes import SETUP_TERMINAL, RESTORE_TERMINAL, HOME_CURSOR, CLEAR_TO_EOL


class TerminalPlayer(Pipe):
    """Plays ANSI sequences to terminal with proper timing.

    Input: (timestamp, ansi_string)
    Output: passes through input (for potential monitoring)
    """

    def setup(self):
        """Setup terminal and timing."""
        self.start_time = None
        self.frame_count = 0
        self.skipped_frames = 0

        # Setup terminal
        sys.stdout.write(SETUP_TERMINAL)
        sys.stdout.flush()

    def teardown(self):
        """Restore terminal."""

        # Restore terminal and position cursor below content
        sys.stdout.write(f"{RESTORE_TERMINAL}\x1b[{self.args.height + 1};1H")
        sys.stdout.flush()

    def process(self, timestamp: float, data: Any) -> Iterator[Tuple[float, Any]]:
        """Output ANSI to terminal with timing control."""
        # Initialize timer on first frame
        if self.start_time is None:
            self.start_time = time.time()
            # Always display first frame immediately, regardless of timing
            # Don't apply realtime logic to first frame

        elif self.args.realtime:
            # Calculate when this frame should appear
            current_time = time.time() - self.start_time

            if current_time > timestamp:
                # We're behind - skip this frame
                self.skipped_frames += 1
                self.frame_count += 1
                yield timestamp, data
                return
            else:
                # Wait until it's time
                sleep_time = timestamp - current_time
                if sleep_time > 0:
                    time.sleep(sleep_time)

                # Report skipped frames when we catch up
                if self.skipped_frames > 0 and self.args.debug:
                    self.debug("skipped", self.skipped_frames)
                    self.skipped_frames = 0

        # Move cursor to home and output ANSI
        sys.stdout.write(HOME_CURSOR + data)

        # Debug info - display all pipeline debug messages
        if self.args.debug:
            self.debug("frame", self.frame_count)
            all_msgs = self.all_debug_msgs()
            if all_msgs:
                # Position cursor below video and display debug info with clear-to-EOL
                lines = all_msgs.split("\n")
                debug_output = "\x1b[0m"
                for i, line in enumerate(lines):
                    debug_output += f"\x1b[{self.args.height + 1 + i};1H{line}{CLEAR_TO_EOL}\n"
                sys.stdout.write(debug_output)

        sys.stdout.flush()
        self.frame_count += 1

        # Pass through for monitoring
        yield timestamp, data
