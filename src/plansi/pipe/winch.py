"""Terminal resize watcher: turns SIGWINCH into pipeline resize events."""

import shutil
import signal
from typing import Iterator, Tuple, Any

from .base import Pipe, Event


class ResizeWatcher(Pipe):
    """Injects a resize event when the controlling terminal changes size.

    Sits between the frame source and the ANSI conversion so a SIGWINCH
    reshapes everything downstream. The signal handler only sets a flag;
    the size is read and the event emitted on the next frame through.

    Input: (timestamp, data) passthrough
    Output: same stream, with Event("resize") injected after a SIGWINCH
    """

    def setup(self):
        self._winched = False
        self._previous_handler = signal.signal(signal.SIGWINCH, self._on_winch)

    def teardown(self):
        signal.signal(signal.SIGWINCH, self._previous_handler)

    def _on_winch(self, signum, frame):
        self._winched = True

    def process(self, timestamp: float, data: Any) -> Iterator[Tuple[float, Any]]:
        if self._winched:
            self._winched = False
            size = shutil.get_terminal_size()
            if (size.columns, size.lines) != (self.width, self.height):
                self.width, self.height = size.columns, size.lines
                yield timestamp, Event("resize", width=size.columns, height=size.lines)
        yield timestamp, data
