"""Terminal player for ANSI sequences."""

import sys
import time
from typing import Iterator, Tuple, Any

from .base import Pipe
from ..control_codes import SETUP_TERMINAL, RESTORE_TERMINAL, CLEAR_TO_EOL


class TerminalPlayer(Pipe):
    """Plays ANSI sequences to terminal with proper timing.

    Input: (timestamp, ansi_string)
    Output: passes through input (for potential monitoring)
    """

    def setup(self):
        """Setup terminal and timing."""
        self.start_time = None
        self.frame_count = 0
        self.late_frames = 0

        # Setup terminal
        sys.stdout.write(SETUP_TERMINAL)
        sys.stdout.flush()

    def teardown(self):
        """Restore terminal."""

        # Restore terminal and position cursor below content
        sys.stdout.write(f"{RESTORE_TERMINAL}\x1b[{self.height + 1};1H")
        sys.stdout.flush()

    def process(self, timestamp: float, data: Any) -> Iterator[Tuple[float, Any]]:
        """Output ANSI to terminal with timing control."""
        # Initialize timer on first frame
        if self.start_time is None:
            self.start_time = time.time()
            # Always display first frame immediately, regardless of timing

        elif self.args.realtime:
            # A differential stream can't drop frames - every diff assumes the
            # previous one landed. When we're behind, we drop the sleep instead
            # and the video runs at whatever speed the pipeline manages.
            sleep_time = timestamp - (time.time() - self.start_time)
            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                self.late_frames += 1
                if self.args.debug:
                    self.debug("late", self.late_frames)

        # Output ANSI data directly - let ANSI sequences control cursor positioning
        sys.stdout.write(data)

        # Debug info - display all pipeline debug messages
        if self.args.debug:
            self.debug("frame", self.frame_count)
            all_msgs = self.all_debug_msgs()
            if all_msgs:
                # Position cursor below video and display debug info with clear-to-EOL
                lines = all_msgs.split("\n")
                debug_output = "\x1b[0m"
                for i, line in enumerate(lines):
                    debug_output += f"\x1b[{self.height + 1 + i};1H{line}{CLEAR_TO_EOL}\n"
                sys.stdout.write(debug_output)

        sys.stdout.flush()
        self.frame_count += 1

        # Pass through for monitoring
        yield timestamp, data
