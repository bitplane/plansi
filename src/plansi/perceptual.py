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


def extract_rgb_color(color_obj) -> tuple:
    """Extract RGB tuple from bittty color object.

    Args:
        color_obj: bittty color object

    Returns:
        RGB tuple (r, g, b) - defaults to black if no color
    """
    if not color_obj or not color_obj.value:
        return (0, 0, 0)  # Default to black

    if len(color_obj.value) == 3:
        # Extract and quantize the color
        return quantize_rgb(tuple(color_obj.value))

    return (0, 0, 0)  # Default to black if can't extract


def visual_difference(cell1: tuple, cell2: tuple) -> float:
    """Calculate visual difference between two cells based on human perception.

    Args:
        cell1: (Style, char) tuple from first cell
        cell2: (Style, char) tuple from second cell

    Returns:
        Visual difference percentage (0-100)
    """
    style1, char1 = cell1
    style2, char2 = cell2

    # Early exit for identical characters and styles
    if char1 == char2 and style1.reverse == style2.reverse:
        # Quick style comparison before expensive color extraction
        if style1.fg == style2.fg and style1.bg == style2.bg:
            return 0.0

    # Extract colors once
    fg1 = extract_rgb_color(style1.fg)
    bg1 = extract_rgb_color(style1.bg)
    fg2 = extract_rgb_color(style2.fg)
    bg2 = extract_rgb_color(style2.bg)

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


def contrast(fg_color: tuple, bg_color: tuple) -> float:
    """Calculate contrast between foreground and background colors.

    Args:
        fg_color: RGB tuple (r, g, b)
        bg_color: RGB tuple (r, g, b)

    Returns:
        Contrast value (0.0 to ~441.67)
    """
    return color_distance(fg_color, bg_color)
