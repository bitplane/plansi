"""Cast quantization end to end: real cast in, valid quantized cast out."""

import json

from bittty import Board

from plansi.args import parse_args
from plansi.pipeline import build_pipeline


def write_cast(path, width, height, frames):
    with open(path, "w") as f:
        f.write(json.dumps({"version": 2, "width": width, "height": height, "timestamp": 1234567890}) + "\n")
        for frame in frames:
            f.write(json.dumps(list(frame)) + "\n")
    return path


def read_cast(path):
    with open(path) as f:
        header = json.loads(f.readline())
        entries = [json.loads(line) for line in f if line.strip()]
    return header, entries


def replay(path):
    """What a terminal shows after playing the cast."""
    header, entries = read_cast(path)
    board = Board(width=header["width"], height=header["height"])
    for _, stream_type, data in entries:
        if stream_type == "o":
            board.parser.feed(data)
    page = board.blitter.current_buffer
    return [page.get_line_text(y).rstrip() for y in range(header["height"])]


def quantize(src, out, extra_args=()):
    args = parse_args([str(src), str(out), *extra_args])
    pipeline, is_file_output = build_pipeline(args)
    for _ in pipeline:
        pass
    assert is_file_output
    return out


def test_cast_to_cast_writes_a_real_cast(tmp_path):
    src = write_cast(
        tmp_path / "in.cast",
        20,
        4,
        [
            (0.0, "o", "\x1b[1;1Hhello"),
            (1.0, "o", "\x1b[2;1H\x1b[38;2;255;0;0mworld"),
            (2.0, "o", "\x1b[1;7Hagain"),
        ],
    )
    out = quantize(src, tmp_path / "out.cast")

    header, entries = read_cast(out)
    assert header["version"] == 2
    assert (header["width"], header["height"]) == (20, 4)
    assert all(entry[1] == "o" for entry in entries)
    assert replay(out) == replay(src)


def test_quantization_drops_redundant_frames(tmp_path):
    src = write_cast(
        tmp_path / "in.cast",
        10,
        2,
        [
            (0.0, "o", "\x1b[1;1Hsame"),
            (1.0, "o", "\x1b[1;1Hsame"),
            (2.0, "o", "\x1b[1;1Hsame"),
            (3.0, "o", "\x1b[1;1Hdiff"),
        ],
    )
    out = quantize(src, tmp_path / "out.cast")

    _, entries = read_cast(out)
    assert len(entries) == 2  # the two repeats vanish
    assert entries[1][0] == 3.0  # the change keeps its original timestamp
    assert replay(out) == replay(src)
