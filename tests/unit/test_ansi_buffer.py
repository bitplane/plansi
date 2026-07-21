"""AnsiBuffer: differential rendering through real bittty boards."""

from argparse import Namespace

from plansi.pipe.buffer import AnsiBuffer


def make_args(**overrides):
    defaults = dict(width=10, threshold=5.0, debug=False, cache_position=False, cache_style=True)
    defaults.update(overrides)
    return Namespace(**defaults)


def run_pipe(frames, args=None):
    pipe = AnsiBuffer(iter(frames), args or make_args())
    pipe.height = 3
    return list(pipe), pipe


def test_first_frame_passes_through():
    frames = [(0.0, "\x1b[1;1HHello")]
    output, _ = run_pipe(frames)
    assert output == [(0.0, "\x1b[1;1HHello")]


def test_single_changed_cell_yields_minimal_update():
    frames = [
        (0.0, "\x1b[1;1HHello     "),
        (1.0, "\x1b[1;1HHellp     "),
    ]
    output, _ = run_pipe(frames)
    _, diff = output[1]
    assert diff.endswith("p")
    assert "Hell" not in diff  # unchanged cells stay silent
    assert diff.startswith("\x1b[1;5H")  # cursor jumps straight to the change


def test_identical_frames_yield_nothing():
    frames = [
        (0.0, "\x1b[1;1HHello     "),
        (1.0, "\x1b[1;1HHello     "),
    ]
    output, _ = run_pipe(frames)
    assert output[1] == (1.0, "")


def test_colour_change_below_threshold_is_suppressed():
    frames = [
        (0.0, "\x1b[1;1H\x1b[38;2;136;147;158mx"),
        (1.0, "\x1b[1;1H\x1b[38;2;130;141;151mx"),  # near-identical grey
    ]
    output, _ = run_pipe(frames)
    assert output[1] == (1.0, "")


def test_colour_change_above_threshold_is_emitted():
    frames = [
        (0.0, "\x1b[1;1H\x1b[38;2;255;255;255mx"),
        (1.0, "\x1b[1;1H\x1b[38;2;255;0;0mx"),
    ]
    output, _ = run_pipe(frames)
    _, diff = output[1]
    assert "\x1b[38;2;255;0;0m" in diff


def test_boards_track_resize_events():
    _, pipe = run_pipe([(0.0, "hi")])
    events = list(pipe.on_resize(1.0, 20, 5))
    assert events
    assert (pipe.prev_board.width, pipe.prev_board.height) == (20, 5)
    assert (pipe.curr_board.width, pipe.curr_board.height) == (20, 5)
