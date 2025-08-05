"""ANSI escape code constants for terminal control.

This module centralizes all ANSI escape sequences used throughout plansi,
providing well-named constants that are self-documenting and easy to maintain.
"""

# Terminal setup and cleanup
CLEAR_SCREEN = "\x1b[2J"
HOME_CURSOR = "\x1b[H"
HIDE_CURSOR = "\x1b[?25l"
SHOW_CURSOR = "\x1b[?25h"
DISABLE_LINE_WRAP = "\x1b[?7l"
ENABLE_LNM = "\x1b[?20h"  # Line Feed/New Line Mode - makes \n behave like \r\n

# Combined sequences for common operations
SETUP_TERMINAL = CLEAR_SCREEN + HOME_CURSOR + HIDE_CURSOR
RESTORE_TERMINAL = "\x1b[0m" + SHOW_CURSOR  # Reset + show cursor

# Cursor movement (use .format(row+1, col+1) for 1-based positioning)
MOVE_CURSOR = "\x1b[{};{}H"

# Color control
SET_FOREGROUND_RGB = "\x1b[38;2;{};{};{}m"  # Use .format(r, g, b)
SET_BACKGROUND_RGB = "\x1b[48;2;{};{};{}m"  # Use .format(r, g, b)
RESET_FOREGROUND = "\x1b[39m"
RESET_BACKGROUND = "\x1b[49m"

# Text styling
RESET_STYLE = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
ITALIC = "\x1b[3m"
UNDERLINE = "\x1b[4m"
BLINK = "\x1b[5m"
REVERSE = "\x1b[7m"
STRIKETHROUGH = "\x1b[9m"
