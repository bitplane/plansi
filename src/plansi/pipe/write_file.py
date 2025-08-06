"""File writer pipe."""

from typing import Iterator, Tuple, Any

from .base import Pipe


class FileWriter(Pipe):
    """Writes data to a file.

    Input: (timestamp, string_data)
    Output: passes through input (for potential chaining)
    """

    def setup(self):
        """Open output file."""
        if not self.args.output:
            raise ValueError("FileWriter requires output file path in args.output")

        self.file = open(self.args.output, "w")
        self.line_count = 0

    def teardown(self):
        """Close output file."""
        if hasattr(self, "file"):
            self.file.close()
            self.debug("lines", self.line_count)

    def process(self, timestamp: float, data: Any) -> Iterator[Tuple[float, Any]]:
        """Write data to file and pass through."""
        # Write data with newline
        self.file.write(data + "\n")
        self.file.flush()
        self.line_count += 1

        # Pass through for potential chaining
        yield timestamp, data
