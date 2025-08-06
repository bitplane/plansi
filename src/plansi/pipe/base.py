"""Base Pipe class for composable pipeline stages."""

from typing import Iterator, Tuple, Any, Optional


class Pipe:
    """Base class for pipeline stages that process (timestamp, data) streams.

    Provides context management for resource cleanup and a generator protocol
    for processing input streams. Subclasses implement process() to transform data.
    """

    def __init__(self, input_pipe: Optional[Iterator[Tuple[float, Any]]] = None, **kwargs):
        """Initialize pipe with optional input and arguments.

        Args:
            input_pipe: Optional input iterator of (timestamp, data) tuples
            **kwargs: Additional arguments available as self.args
        """
        self.input = input_pipe
        self.args = kwargs

    def __iter__(self):
        """Generate output by processing input through this stage."""
        with self:  # Use self as context manager
            if self.input is None:
                # Source pipe - generate initial data
                yield from self.process(None, None)
            else:
                for timestamp, data in self.input:
                    yield from self.process(timestamp, data)

    def __enter__(self):
        """Enter context and call setup."""
        self.setup()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and call teardown."""
        self.teardown()

    def setup(self):
        """Override to initialize resources."""
        pass

    def teardown(self):
        """Override to clean up resources."""
        pass

    def process(self, timestamp: float, data: Any) -> Iterator[Tuple[float, Any]]:
        """Process input and yield output tuples.

        Args:
            timestamp: Input timestamp (None for source pipes)
            data: Input data (None for source pipes)

        Yields:
            Tuples of (timestamp, data) for next stage
        """
        raise NotImplementedError("Subclasses must implement process()")
