"""Perceptual analysis functions for color and visual differences.

This module provides functions for calculating perceptual differences between colors
and terminal cells, using LAB color space for human-perception-based comparisons.
"""

import math


def rgb_to_lab(rgb: tuple) -> tuple:
    """Convert RGB to LAB color space for perceptual color comparison.

    Args:
        rgb: RGB tuple (r, g, b) with values 0-255

    Returns:
        LAB tuple (L, a, b) where L is 0-100, a and b are roughly -128 to +128
    """
    r, g, b = rgb

    # Normalize RGB to 0-1
    r, g, b = r / 255.0, g / 255.0, b / 255.0

    # Convert to linear RGB (gamma correction)
    def gamma_correct(c):
        return c / 12.92 if c <= 0.04045 else pow((c + 0.055) / 1.055, 2.4)

    r, g, b = gamma_correct(r), gamma_correct(g), gamma_correct(b)

    # Convert to XYZ using sRGB matrix
    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041

    # Normalize by D65 white point
    x, y, z = x / 0.95047, y / 1.00000, z / 1.08883

    # Convert to LAB
    def xyz_to_lab_component(t):
        return pow(t, 1 / 3) if t > 0.008856 else (7.787 * t + 16 / 116)

    fx, fy, fz = xyz_to_lab_component(x), xyz_to_lab_component(y), xyz_to_lab_component(z)

    L = 116 * fy - 16
    a = 500 * (fx - fy)
    b = 200 * (fy - fz)

    return (L, a, b)


def color_distance(color1: tuple, color2: tuple) -> float:
    """Calculate perceptual distance between two RGB colors using LAB color space.

    Args:
        color1: RGB tuple (r, g, b)
        color2: RGB tuple (r, g, b)

    Returns:
        Perceptual distance between colors (Delta E in LAB space)
    """
    lab1 = rgb_to_lab(color1)
    lab2 = rgb_to_lab(color2)

    L1, a1, b1 = lab1
    L2, a2, b2 = lab2

    # Delta E CIE76 formula
    return math.sqrt((L1 - L2) ** 2 + (a1 - a2) ** 2 + (b1 - b2) ** 2)


def quantize_rgb(color: tuple) -> tuple:
    """Quantize RGB color to reduce noise from dithering artifacts.

    Args:
        color: RGB tuple (r, g, b)

    Returns:
        Quantized RGB tuple
    """
    # Reduce from 8-bit to 5-bit per channel (32 levels each)
    r, g, b = color
    return (r // 8 * 8, g // 8 * 8, b // 8 * 8)


def resolve_rgb(color, palette, fallback: tuple) -> tuple:
    """Resolve a bittty colour to quantized RGB through the live palette.

    Indexed colours look up the palette's 256-colour table; default colours
    fall back to the palette's real foreground/background instead of black.

    Args:
        color: bittty Color object (or None)
        palette: bittty PaletteDevice
        fallback: RGB tuple used when the colour is default/unset

    Returns:
        Quantized RGB tuple (r, g, b)
    """
    rgb = palette.resolve(color)
    if rgb is None:
        rgb = fallback
    return quantize_rgb(tuple(rgb))


def visual_difference(cell1: tuple, cell2: tuple, palette) -> float:
    """Calculate visual difference between two cells based on human perception.

    Colour-only: character differences are the caller's problem.

    Args:
        cell1: (Style, char) tuple from first cell
        cell2: (Style, char) tuple from second cell
        palette: bittty PaletteDevice for resolving indexed/default colours

    Returns:
        Visual difference percentage (0-100)
    """
    style1, _ = cell1
    style2, _ = cell2

    # Early exit before expensive color extraction
    if style1.reverse == style2.reverse and style1.fg == style2.fg and style1.bg == style2.bg:
        return 0.0

    # Extract colors once
    fg1 = resolve_rgb(style1.fg, palette, palette.foreground)
    bg1 = resolve_rgb(style1.bg, palette, palette.background)
    fg2 = resolve_rgb(style2.fg, palette, palette.foreground)
    bg2 = resolve_rgb(style2.bg, palette, palette.background)

    # Handle inverse video by flipping fg/bg for comparison
    if style1.reverse:
        fg1, bg1 = bg1, fg1
    if style2.reverse:
        fg2, bg2 = bg2, fg2

    # Calculate perceptual color difference between the two cells
    fg_color_diff = min(color_distance(fg1, fg2) / 200.0, 1.0)
    bg_color_diff = min(color_distance(bg1, bg2) / 200.0, 1.0)
    total_diff = (fg_color_diff + bg_color_diff) / 2.0

    return total_diff * 100.0
