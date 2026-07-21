"""TerminalPlayer: late frames slow down, they never vanish."""

from argparse import Namespace

from plansi.pipe.player import TerminalPlayer


def test_late_frames_are_still_written(capsys):
    """A differential stream corrupts if a frame is dropped, so being behind
    schedule must never skip the write."""
    # Timestamps in the past the moment they arrive: every frame is late
    frames = [(0.0, "one"), (0.0, "two"), (0.0, "three")]
    player = TerminalPlayer(iter(frames), Namespace(realtime=True, debug=False))
    output = list(player)

    written = capsys.readouterr().out
    assert "one" in written
    assert "two" in written
    assert "three" in written
    assert player.late_frames == 2  # all but the first, which starts the clock
    assert [data for _, data in output] == ["one", "two", "three"]


def test_paced_frames_sleep_to_their_timestamp(capsys):
    frames = [(0.0, "a"), (0.05, "b")]
    player = TerminalPlayer(iter(frames), Namespace(realtime=True, debug=False))
    list(player)
    assert player.late_frames == 0
    assert "b" in capsys.readouterr().out
