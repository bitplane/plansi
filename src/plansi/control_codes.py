"""ANSI escape code constants for terminal control.

This module centralizes all ANSI escape sequences used throughout plansi,
providing well-named constants that are self-documenting and easy to maintain.
"""

# Terminal setup and cleanup
CLEAR_SCREEN = "\x1b[2J"
CLEAR_TO_EOL = "\x1b[K"
HOME_CURSOR = "\x1b[H"
HIDE_CURSOR = "\x1b[?25l"
SHOW_CURSOR = "\x1b[?25h"
DISABLE_LINE_WRAP = "\x1b[?7l"
ENABLE_LNM = "\x1b[?20h"  # Line Feed/New Line Mode - makes \n behave like \r\n

# Text styling
RESET_STYLE = "\x1b[0m"

# Combined sequences for common operations
SETUP_TERMINAL = CLEAR_SCREEN + HOME_CURSOR + HIDE_CURSOR
RESTORE_TERMINAL = RESET_STYLE + SHOW_CURSOR  # Reset + show cursor

# Cursor movement (use .format(row+1, col+1) for 1-based positioning)
MOVE_CURSOR = "\x1b[{};{}H"
