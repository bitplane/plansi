"""Unit tests for Pipe class and event system."""

from typing import Iterator, Tuple, Any
from argparse import Namespace

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from plansi.pipe.base import Pipe, Event


class SourcePipe(Pipe):
    """Test source pipe that yields predefined data."""

    def __init__(self, data_list, args=None):
        super().__init__(None, args)
        self.data_list = data_list

    def __iter__(self):
        with self:
            for item in self.data_list:
                yield item


class EchoPipe(Pipe):
    """Test pipe that echoes input and records what it saw."""

    def setup(self):
        self.seen_data = []
        self.seen_events = []

    def process(self, timestamp: float, data: Any) -> Iterator[Tuple[float, Any]]:
        """Record and pass through data."""
        self.seen_data.append((timestamp, data))
        yield timestamp, data


class TransformPipe(Pipe):
    """Test pipe that transforms data."""

    def process(self, timestamp: float, data: Any) -> Iterator[Tuple[float, Any]]:
        """Transform string data to uppercase."""
        if isinstance(data, str):
            yield timestamp, data.upper()
        else:
            yield timestamp, data


class EventGeneratorPipe(Pipe):
    """Test pipe that generates events."""

    def process(self, timestamp: float, data: Any) -> Iterator[Tuple[float, Any]]:
        """Generate a resize event before first data."""
        if not hasattr(self, "first_seen"):
            self.first_seen = True
            # Emit resize event
            yield 0.0, Event("resize", width=120, height=40)
        yield timestamp, data


class EventConsumerPipe(Pipe):
    """Test pipe that consumes specific events."""

    def setup(self):
        self.test_events = []

    def process(self, timestamp: float, data: Any) -> Iterator[Tuple[float, Any]]:
        """Pass through non-event data."""
        yield timestamp, data

    def on_test(self, timestamp: float, msg: str) -> Iterator[Tuple[float, Any]]:
        """Handle test events and consume them."""
        self.test_events.append(msg)
        # Don't yield anything - consume the event
        return
        yield  # Make it a generator


class EventModifierPipe(Pipe):
    """Test pipe that modifies events."""

    def process(self, timestamp: float, data: Any) -> Iterator[Tuple[float, Any]]:
        """Pass through non-event data."""
        yield timestamp, data

    def on_resize(self, timestamp: float, width: int, height: int) -> Iterator[Tuple[float, Any]]:
        """Modify resize events."""
        # Double the dimensions
        yield timestamp, Event("resize", width=width * 2, height=height * 2)


def test_basic_pipeline():
    """Test basic pipeline operation without events."""
    source_data = [(0.0, "hello"), (1.0, "world")]

    source = SourcePipe(source_data)
    echo = EchoPipe(source)
    transform = TransformPipe(echo)

    result = list(transform)

    assert len(result) == 2
    assert result[0] == (0.0, "HELLO")
    assert result[1] == (1.0, "WORLD")

    # Check echo saw the data
    assert echo.seen_data == source_data


def test_event_propagation():
    """Test that events propagate through pipes."""
    source_data = [(0.0, Event("resize", width=80, height=24)), (1.0, "data")]

    source = SourcePipe(source_data)
    echo1 = EchoPipe(source)
    echo2 = EchoPipe(echo1)

    result = list(echo2)

    assert len(result) == 2
    assert isinstance(result[0][1], Event)
    assert result[0][1].name == "resize"
    assert result[0][1].kwargs == {"width": 80, "height": 24}
    assert result[1] == (1.0, "data")


def test_event_consumption():
    """Test that events can be consumed by handlers."""
    source_data = [(0.0, Event("test", msg="hello")), (1.0, Event("test", msg="world")), (2.0, "data")]

    source = SourcePipe(source_data)
    consumer = EventConsumerPipe(source)

    result = list(consumer)

    # Only data should pass through, test events were consumed
    assert len(result) == 1
    assert result[0] == (2.0, "data")

    # Check consumer saw the test events
    assert consumer.test_events == ["hello", "world"]


def test_event_modification():
    """Test that events can be modified by handlers."""
    source_data = [(0.0, Event("resize", width=80, height=24)), (1.0, "data")]

    source = SourcePipe(source_data)
    modifier = EventModifierPipe(source)

    result = list(modifier)

    assert len(result) == 2
    # Check resize was doubled
    resize_event = result[0][1]
    assert isinstance(resize_event, Event)
    assert resize_event.kwargs["width"] == 160
    assert resize_event.kwargs["height"] == 48


def test_event_generation():
    """Test that pipes can generate events."""
    source_data = [(0.0, "first"), (1.0, "second")]

    source = SourcePipe(source_data)
    generator = EventGeneratorPipe(source)

    result = list(generator)

    # Should have resize event, then data
    assert len(result) == 3
    assert isinstance(result[0][1], Event)
    assert result[0][1].name == "resize"
    assert result[1] == (0.0, "first")
    assert result[2] == (1.0, "second")


def test_default_resize_handler():
    """Test the default on_resize handler in base Pipe class."""
    source_data = [(0.0, Event("resize", width=100, height=50)), (1.0, "data")]

    args = Namespace(width=80)  # Initial width from args
    source = SourcePipe(source_data, args)
    echo = EchoPipe(source, args)

    # Check initial dimensions
    assert echo.width == 80
    assert echo.height == 24  # Default

    result = list(echo)

    # Check dimensions were updated
    assert echo.width == 100
    assert echo.height == 50

    # Check resize propagated
    assert len(result) == 2
    assert isinstance(result[0][1], Event)
    assert result[0][1].name == "resize"


def test_debug_messages():
    """Test debug message handling."""
    source_data = [(0.0, "test")]
    args = Namespace(debug=True)

    source = SourcePipe(source_data, args)
    echo = EchoPipe(source, args)

    # Add debug messages
    echo.debug("test_key", "test_value")
    echo.debug("another", "123")

    # Check debug messages
    assert echo.debug_msg["test_key"] == "test_value"
    assert echo.debug_msg["another"] == "123"

    # Check all_debug_msgs format
    all_msgs = echo.all_debug_msgs()
    assert "EchoPipe.test_key: test_value" in all_msgs
    assert "EchoPipe.another: 123" in all_msgs


def test_complex_pipeline():
    """Test a complex pipeline with multiple event types."""

    class MultiEventPipe(Pipe):
        def setup(self):
            self.events_seen = []

        def process(self, timestamp: float, data: Any) -> Iterator[Tuple[float, Any]]:
            """Pass through non-event data."""
            yield timestamp, data

        def on_resize(self, timestamp: float, width: int, height: int) -> Iterator[Tuple[float, Any]]:
            self.events_seen.append(("resize", width, height))
            # Propagate
            yield timestamp, Event("resize", width=width, height=height)

        def on_custom(self, timestamp: float, value: str) -> Iterator[Tuple[float, Any]]:
            self.events_seen.append(("custom", value))
            # Transform and propagate
            yield timestamp, Event("custom", value=value.upper())

    source_data = [
        (0.0, Event("resize", width=80, height=24)),
        (1.0, Event("custom", value="hello")),
        (2.0, "normal data"),
        (3.0, Event("unknown", foo="bar")),  # Unknown event should propagate
    ]

    source = SourcePipe(source_data)
    multi = MultiEventPipe(source)

    result = list(multi)

    assert len(result) == 4

    # Check resize was handled
    assert result[0][1].name == "resize"
    assert multi.events_seen[0] == ("resize", 80, 24)

    # Check custom was transformed
    assert result[1][1].name == "custom"
    assert result[1][1].kwargs["value"] == "HELLO"
    assert multi.events_seen[1] == ("custom", "hello")

    # Check normal data passed through
    assert result[2] == (2.0, "normal data")

    # Check unknown event propagated unchanged
    assert result[3][1].name == "unknown"
    assert result[3][1].kwargs["foo"] == "bar"


def test_event_handler_can_yield_multiple():
    """Test that event handlers can yield multiple outputs."""

    class MultiYieldPipe(Pipe):
        def process(self, timestamp: float, data: Any) -> Iterator[Tuple[float, Any]]:
            """Pass through non-event data."""
            yield timestamp, data

        def on_burst(self, timestamp: float, count: int) -> Iterator[Tuple[float, Any]]:
            """Generate multiple data items from one event."""
            for i in range(count):
                yield timestamp + i, f"burst_{i}"

    source_data = [(0.0, Event("burst", count=3)), (10.0, "normal")]

    source = SourcePipe(source_data)
    multi = MultiYieldPipe(source)

    result = list(multi)

    assert len(result) == 4
    assert result[0] == (0.0, "burst_0")
    assert result[1] == (1.0, "burst_1")
    assert result[2] == (2.0, "burst_2")
    assert result[3] == (10.0, "normal")
