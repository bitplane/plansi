"""AnsiBuffer: differential rendering through real bittty boards."""

from argparse import Namespace

from bittty import Board

from plansi.pipe.buffer import AnsiBuffer


def make_args(**overrides):
    defaults = dict(width=10, threshold=5.0, debug=False, cache_position=False, cache_style=True)
    defaults.update(overrides)
    return Namespace(**defaults)


def run_pipe(frames, args=None):
    pipe = AnsiBuffer(iter(frames), args or make_args())
    pipe.height = 3
    return list(pipe), pipe


def replay(output, width=10, height=3):
    """Feed the emitted stream into a fresh board: what a viewer would see."""
    board = Board(width=width, height=height)
    for _, chunk in output:
        board.parser.feed(chunk)
    return [board.blitter.primary_buffer.get_line_text(y).rstrip() for y in range(height)]


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


def test_identical_frames_vanish_from_the_stream():
    frames = [
        (0.0, "\x1b[1;1HHello     "),
        (1.0, "\x1b[1;1HHello     "),
    ]
    output, _ = run_pipe(frames)
    assert output == [(0.0, "\x1b[1;1HHello     ")]


def test_incremental_chunks_accumulate():
    """Cast chunks build on each other; earlier chunks must survive later diffs."""
    frames = [
        (0.0, "\x1b[1;1Hhello"),
        (1.0, "\x1b[2;1Hworld"),
        (2.0, "\x1b[3;1H!"),
    ]
    output, pipe = run_pipe(frames)
    truth = pipe.truth_board.blitter.current_buffer
    assert replay(output) == [truth.get_line_text(y).rstrip() for y in range(3)]


def test_colour_change_below_threshold_is_suppressed():
    frames = [
        (0.0, "\x1b[1;1H\x1b[38;2;136;147;158mx"),
        (1.0, "\x1b[1;1H\x1b[38;2;130;141;151mx"),  # near-identical grey
    ]
    output, _ = run_pipe(frames)
    assert len(output) == 1


def test_suppressed_drift_eventually_crosses_the_threshold():
    """Slow colour drift accumulates against the viewer until it must be emitted."""
    grey = "\x1b[1;1H\x1b[38;2;{0};{0};{0}mx"
    frames = [(float(i), grey.format(200 - i * 4)) for i in range(8)]
    output, _ = run_pipe(frames, make_args(threshold=2.0))
    assert len(output) == 2  # per-frame steps stay below threshold, the total does not
    assert "\x1b[38;2;180;180;180m" in output[1][1]  # emitted once the drift crosses


def test_colour_change_above_threshold_is_emitted():
    frames = [
        (0.0, "\x1b[1;1H\x1b[38;2;255;255;255mx"),
        (1.0, "\x1b[1;1H\x1b[38;2;255;0;0mx"),
    ]
    output, _ = run_pipe(frames)
    _, diff = output[1]
    assert "\x1b[38;2;255;0;0m" in diff


def test_indexed_colour_frames_diff_through_the_palette():
    """SGR 31/34 frames used to crash colour extraction; now they resolve via the palette."""
    frames = [
        (0.0, "\x1b[1;1H\x1b[31mxx        "),
        (1.0, "\x1b[1;1H\x1b[34mxx        "),
    ]
    output, _ = run_pipe(frames)
    _, diff = output[1]
    assert "x" in diff  # red -> blue is far beyond any threshold


def test_boards_track_resize_events():
    _, pipe = run_pipe([(0.0, "hi")])
    events = list(pipe.on_resize(1.0, 20, 5))
    assert events
    assert (pipe.truth_board.width, pipe.truth_board.height) == (20, 5)
    assert (pipe.viewer_board.width, pipe.viewer_board.height) == (20, 5)
