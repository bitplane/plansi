"""Live resize: SIGWINCH injection and canvas rebuilds, with real signals and real chafa."""

import os
import signal
from argparse import Namespace

from PIL import Image

from plansi.pipe.base import Event
from plansi.pipe.image_to_ansi import ImageToAnsi
from plansi.pipe.winch import ResizeWatcher


def test_sigwinch_injects_a_resize_event(monkeypatch):
    monkeypatch.setenv("COLUMNS", "100")
    monkeypatch.setenv("LINES", "40")

    def frames():
        yield 0.0, "first"
        os.kill(os.getpid(), signal.SIGWINCH)
        yield 1.0, "second"

    watcher = ResizeWatcher(frames(), Namespace(width=80))
    output = list(watcher)

    assert output[0] == (0.0, "first")
    timestamp, event = output[1]
    assert isinstance(event, Event)
    assert event.name == "resize"
    assert event.kwargs == {"width": 100, "height": 40}
    assert output[2] == (1.0, "second")


def test_previous_signal_handler_is_restored():
    before = signal.getsignal(signal.SIGWINCH)
    watcher = ResizeWatcher(iter([(0.0, "x")]), Namespace(width=80))
    list(watcher)
    assert signal.getsignal(signal.SIGWINCH) is before


def test_unchanged_size_injects_nothing(monkeypatch):
    monkeypatch.setenv("COLUMNS", "80")
    monkeypatch.setenv("LINES", "24")

    def frames():
        os.kill(os.getpid(), signal.SIGWINCH)
        yield 0.0, "only"

    watcher = ResizeWatcher(frames(), Namespace(width=80))
    watcher.height = 24
    assert list(watcher) == [(0.0, "only")]


def test_image_to_ansi_rebuilds_canvas_on_resize():
    img = Image.new("RGB", (64, 32), (200, 40, 40))
    source = iter(
        [
            (0.0, img),
            (1.0, Event("resize", width=40, height=0)),
            (2.0, img),
        ]
    )
    pipe = ImageToAnsi(source, Namespace(width=80, debug=False))
    output = list(pipe)

    resizes = [data for _, data in output if isinstance(data, Event)]
    assert [event.kwargs["width"] for event in resizes] == [80, 40]
    assert resizes[1].kwargs["height"] == 10  # 40 * (32/64) * 0.5, aspect re-derived
    assert pipe.width == 40
