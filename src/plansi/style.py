"""Style manipulation and comparison functions for terminal cells.

This module provides functions for comparing bittty style objects,
generating ANSI escape sequences, and optimizing style changes.
"""

from .control_codes import (
    SET_FOREGROUND_RGB,
    SET_BACKGROUND_RGB,
    RESET_FOREGROUND,
    RESET_BACKGROUND,
    RESET_STYLE,
    BOLD,
    DIM,
    ITALIC,
    UNDERLINE,
    BLINK,
    REVERSE,
    STRIKETHROUGH,
)


def equal(style1, style2) -> bool:
    """Check if two styles are completely identical.

    Args:
        style1: First bittty Style object
        style2: Second bittty Style object

    Returns:
        True if styles are identical, False otherwise
    """
    # Check all attributes
    if (
        style1.bold != style2.bold
        or style1.dim != style2.dim
        or style1.italic != style2.italic
        or style1.underline != style2.underline
        or style1.blink != style2.blink
        or style1.strike != style2.strike
        or style1.reverse != style2.reverse
    ):
        return False

    # Check colors
    return equal_color(style1.fg, style2.fg) and equal_color(style1.bg, style2.bg)


def equal_color(color1, color2) -> bool:
    """Check if two bittty color objects are equal.

    Args:
        color1: First bittty color object
        color2: Second bittty color object

    Returns:
        True if colors are equal, False otherwise
    """
    if not color1 and not color2:
        return True
    if not color1 or not color2:
        return False
    if not color1.value or not color2.value:
        return not color1.value and not color2.value
    return color1.value == color2.value


def to_ansi(style) -> str:
    """Generate full ANSI style sequence for a style.

    Args:
        style: bittty Style object

    Returns:
        ANSI escape sequence string
    """
    parts = [RESET_STYLE]

    # Foreground color
    if style.fg and style.fg.value and len(style.fg.value) == 3:
        r, g, b = style.fg.value
        parts.append(SET_FOREGROUND_RGB.format(r, g, b))

    # Background color
    if style.bg and style.bg.value and len(style.bg.value) == 3:
        r, g, b = style.bg.value
        parts.append(SET_BACKGROUND_RGB.format(r, g, b))

    # Attributes
    if style.bold:
        parts.append(BOLD)
    if style.reverse:
        parts.append(REVERSE)
    if style.dim:
        parts.append(DIM)
    if style.italic:
        parts.append(ITALIC)
    if style.underline:
        parts.append(UNDERLINE)
    if style.blink:
        parts.append(BLINK)
    if style.strike:
        parts.append(STRIKETHROUGH)

    return "".join(parts)


def diff(current_style, new_style, cache_style: bool = True) -> str:
    """Generate minimal ANSI escape sequences for style changes.

    Optimized 3-case approach:
    1. If identical -> no output
    2. If attributes differ -> reset + full style
    3. If only colors differ -> color sequences only

    Args:
        current_style: Current bittty Style object (or None)
        new_style: New bittty Style object
        cache_style: Whether to use style caching optimizations

    Returns:
        ANSI escape sequence string for the style change
    """
    if not cache_style:
        # Style caching disabled - always generate full style
        return to_ansi(new_style)

    # Style caching enabled - optimize style changes
    if current_style is None:
        # First style - need full setup
        return to_ansi(new_style)

    # Check if styles are identical
    if equal(current_style, new_style):
        # Case 1: Identical - no output needed
        return ""

    # Check if any text attributes differ
    attributes_differ = (
        current_style.bold != new_style.bold
        or current_style.dim != new_style.dim
        or current_style.italic != new_style.italic
        or current_style.underline != new_style.underline
        or current_style.blink != new_style.blink
        or current_style.strike != new_style.strike
        or current_style.reverse != new_style.reverse
    )

    if attributes_differ:
        # Case 2: Attributes differ - reset and full rebuild
        return to_ansi(new_style)

    # Case 3: Only colors differ - send color sequences only
    parts = []

    # Check foreground color
    if not equal_color(current_style.fg, new_style.fg):
        if new_style.fg and new_style.fg.value and len(new_style.fg.value) == 3:
            r, g, b = new_style.fg.value
            parts.append(SET_FOREGROUND_RGB.format(r, g, b))
        else:
            # No foreground color - reset to default
            parts.append(RESET_FOREGROUND)

    # Check background color
    if not equal_color(current_style.bg, new_style.bg):
        if new_style.bg and new_style.bg.value and len(new_style.bg.value) == 3:
            r, g, b = new_style.bg.value
            parts.append(SET_BACKGROUND_RGB.format(r, g, b))
        else:
            # No background color - reset to default
            parts.append(RESET_BACKGROUND)

    return "".join(parts)
