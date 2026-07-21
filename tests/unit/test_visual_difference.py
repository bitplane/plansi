"""Visual difference algorithm with real bittty styles resolved through a real palette."""

import pytest

from bittty import Board
from bittty.style import Style, Color

from plansi import perceptual


@pytest.fixture
def palette():
    return Board(width=2, height=2).palette


def rgb_style(fg=None, bg=None, reverse=None):
    return Style(
        fg=Color("rgb", fg) if fg else None,
        bg=Color("rgb", bg) if bg else None,
        reverse=reverse,
    )


def test_identical_cells_return_zero(palette):
    style = rgb_style(fg=(255, 255, 255), bg=(0, 0, 0))
    diff = perceptual.visual_difference((style, "A"), (style, "A"), palette)
    assert diff == 0.0


def test_different_characters_same_colors(palette):
    """The algorithm is colour-only: character changes are the caller's problem."""
    style1 = rgb_style(fg=(255, 255, 255), bg=(0, 0, 0))
    style2 = rgb_style(fg=(255, 255, 255), bg=(0, 0, 0))
    diff = perceptual.visual_difference((style1, "A"), (style2, "B"), palette)
    assert diff == 0.0


def test_same_character_different_colors(palette):
    style1 = rgb_style(fg=(255, 255, 255), bg=(0, 0, 0))
    style2 = rgb_style(fg=(255, 0, 0), bg=(0, 0, 0))
    diff = perceptual.visual_difference((style1, "A"), (style2, "A"), palette)
    assert diff > 0.0


def test_high_contrast_beats_low_contrast(palette):
    white = rgb_style(fg=(255, 255, 255), bg=(0, 0, 0))
    black = rgb_style(fg=(0, 0, 0), bg=(0, 0, 0))
    light_gray = rgb_style(fg=(180, 180, 180), bg=(0, 0, 0))
    dark_gray = rgb_style(fg=(120, 120, 120), bg=(0, 0, 0))

    high_diff = perceptual.visual_difference((white, "A"), (black, "A"), palette)
    low_diff = perceptual.visual_difference((light_gray, "A"), (dark_gray, "A"), palette)
    assert high_diff > low_diff


def test_inverse_video_flips_fg_and_bg(palette):
    normal = rgb_style(fg=(255, 255, 255), bg=(0, 0, 0), reverse=False)
    inverse = rgb_style(fg=(0, 0, 0), bg=(255, 255, 255), reverse=True)
    diff = perceptual.visual_difference((normal, "A"), (inverse, "A"), palette)
    assert diff == 0.0


def test_default_colours_resolve_to_palette_fg_and_bg(palette):
    """A default-style cell looks like white-on-black under the default palette."""
    default = Style()
    explicit = rgb_style(fg=(255, 255, 255), bg=(0, 0, 0))
    diff = perceptual.visual_difference((default, " "), (explicit, " "), palette)
    assert diff == 0.0


def test_indexed_colours_resolve_through_the_palette(palette):
    """SGR 31 red compares equal to the RGB the palette maps it to."""
    indexed_red = Style(fg=Color("indexed", 1))
    rgb_red = Style(fg=Color("rgb", palette.colors[1]))
    diff = perceptual.visual_difference((indexed_red, "x"), (rgb_red, "x"), palette)
    assert diff == 0.0


def test_palette_redefinition_changes_the_comparison():
    """OSC 4 recolouring index 1 to blue makes indexed-1 differ from red."""
    board = Board(width=2, height=2)
    indexed = Style(fg=Color("indexed", 1))
    red = Style(fg=Color("rgb", (205, 0, 0)))

    before = perceptual.visual_difference((indexed, "x"), (red, "x"), board.palette)
    board.parser.feed("\x1b]4;1;#0000ff\x07")
    after = perceptual.visual_difference((indexed, "x"), (red, "x"), board.palette)

    assert before == 0.0
    assert after > 30.0


def test_bright_blue_vs_brown(palette):
    blue = rgb_style(fg=(0, 0, 255), bg=(0, 0, 0))
    brown = rgb_style(fg=(139, 69, 19), bg=(0, 0, 0))
    diff = perceptual.visual_difference((blue, "A"), (brown, "A"), palette)
    assert diff > 30.0


def test_similar_video_grays(palette):
    gray1 = rgb_style(fg=(136, 147, 158), bg=(0, 0, 0))
    gray2 = rgb_style(fg=(130, 141, 151), bg=(0, 0, 0))
    diff = perceptual.visual_difference((gray1, " "), (gray2, " "), palette)
    assert diff < 5.0
