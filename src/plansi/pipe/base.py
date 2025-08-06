"""Base Pipe class for composable pipeline stages."""

import os
from typing import Iterator, Tuple, Any


class Event:
    """Event object for pipeline communication."""

    def __init__(self, name: str, *args, **kwargs):
        self.name = name
        self.args = args
        self.kwargs = kwargs


class Pipe:
    """Base class for pipeline stages that process (timestamp, data) streams.

    Provides context management for resource cleanup and a generator protocol
    for processing input streams. Subclasses implement process() to transform data.
    """

    def __init__(self, input_pipe, args=None):
        """Initialize pipe with input and arguments.

        Args:
            input_pipe: Input iterator of (timestamp, data) tuples
            args: Parsed arguments namespace from argparse
        """
        self.input = input_pipe
        self.args = args or {}
        self.debug_msg = {}
        # Standard dimensions - all pipes have them
        self.width = getattr(args, "width", 80) if args else 80
        self.height = 24  # Default height, updated by resize events

    def __iter__(self):
        """Generate output by processing input through this stage."""
        with self:  # Use self as context manager
            for timestamp, data in self.input:
                # Handle events
                if isinstance(data, Event):
                    # Event handlers are generators that can yield output
                    yield from self.on_event(timestamp, data)
                else:
                    # Normal data processing
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

    def debug(self, key: str, value: str):
        """Store debug message for display later."""
        self.debug_msg[key] = str(value)

        # Log to file if specified
        if hasattr(self.args, "log_file") and self.args.log_file:
            log_msg = f"{type(self).__name__}.{key}: {value}\n"
            os.makedirs(os.path.dirname(self.args.log_file), exist_ok=True)
            with open(self.args.log_file, "a") as f:
                f.write(log_msg)

    def all_debug_msgs(self) -> str:
        msg = ""
        if hasattr(self.input, "all_debug_msgs"):
            msg += self.input.all_debug_msgs() + "\n"
        class_name = type(self).__name__
        for key, value in self.debug_msg.items():
            msg += f"{class_name}.{key}: {value}\n"
        return msg.rstrip("\n")

    def process(self, timestamp: float, data: Any) -> Iterator[Tuple[float, Any]]:
        """Process input and yield output tuples.

        Args:
            timestamp: Input timestamp (None for source pipes)
            data: Input data (None for source pipes)

        Yields:
            Tuples of (timestamp, data) for next stage
        """
        raise NotImplementedError("Subclasses must implement process()")

    def on_event(self, timestamp: float, event: Event) -> Iterator[Tuple[float, Any]]:
        """Handle an event and optionally yield output.

        Default implementation calls on_<event_name> if it exists,
        otherwise propagates the event downstream.
        """
        method_name = f"on_{event.name}"
        handler = getattr(self, method_name, None)
        if handler and callable(handler):
            # Call event handler - it can yield output
            yield from handler(timestamp, *event.args, **event.kwargs)
        else:
            # No handler - propagate event downstream
            yield timestamp, event

    def on_resize(self, timestamp: float, width: int, height: int) -> Iterator[Tuple[float, Any]]:
        """Default resize handler - update dimensions and propagate."""
        if width != self.width or height != self.height:
            self.width = width
            self.height = height
            self.debug("resized", f"{width}x{height}")
        # Propagate event downstream
        yield timestamp, Event("resize", width=width, height=height)
