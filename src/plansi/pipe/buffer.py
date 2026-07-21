"""Buffer pipe using bittty for ANSI accumulation and differential rendering."""

from typing import Iterator, Tuple, Any
from bittty import Board
from bittty.style import style_to_ansi

from .base import Pipe
from ..control_codes import DISABLE_LINE_WRAP, ENABLE_LNM, MOVE_CURSOR, RESET_STYLE
from .. import perceptual


class AnsiBuffer(Pipe):
    """Accumulates ANSI into a buffer and outputs differential updates.

    Uses a bittty Board to parse ANSI sequences and maintain video memory,
    then compares cells to generate minimal update sequences.

    Input: (timestamp, ansi_string) full frames
    Output: (timestamp, ansi_string) optimized differential updates

    Args (via self.args):
        threshold: Perceptual color difference threshold (default: 5.0)
        width: Terminal width in characters
        height: Terminal height in characters
        debug: Show debug info (default: False)
        cache_position: Enable cursor position caching (default: False)
        cache_style: Enable style caching (default: True)
    """

    def setup(self):
        """Initialize two separate boards."""
        # Previous frame board
        self.prev_board = Board(width=self.width, height=self.height)
        self.prev_board.parser.feed(DISABLE_LINE_WRAP)
        self.prev_board.parser.feed(ENABLE_LNM)

        # Current frame board
        self.curr_board = Board(width=self.width, height=self.height)
        self.curr_board.parser.feed(DISABLE_LINE_WRAP)
        self.curr_board.parser.feed(ENABLE_LNM)

        # State tracking for optimized output
        self.current_cursor_x = 0
        self.current_cursor_y = 0
        self.current_style = None
        self.frame_count = 0
        self.first_frame = True

    def process(self, timestamp: float, data: Any) -> Iterator[Tuple[float, str]]:
        """Process ANSI through bittty and generate differential output.

        Args:
            timestamp: Frame timestamp
            data: Full frame ANSI string

        Yields:
            (timestamp, ansi_string) with differential updates
        """
        ansi_input = data

        # First frame: parse into prev_board and output directly
        if self.first_frame:
            self.first_frame = False
            # Parse into prev_board only - no cursor reset, let ANSI control cursor
            self.prev_board.parser.feed(ansi_input)

            # Output first frame directly
            yield timestamp, ansi_input
            self.frame_count += 1
            return

        # Parse current frame into curr_board - no cursor reset, accumulate naturally
        self.curr_board.parser.feed(ansi_input)

        # Generate differential output by comparing boards

        # Reset state tracking for this frame
        self.current_cursor_x = 0
        self.current_cursor_y = 0
        self.current_style = None

        output = []
        cells_changed = 0
        cells_total = 0

        for row in range(self.height):
            for col in range(self.width):
                cells_total += 1

                # Get cells from both boards
                prev_cell = self.prev_board.blitter.primary_buffer.get_cell(col, row)
                curr_cell = self.curr_board.blitter.primary_buffer.get_cell(col, row)

                # Check if cells are different
                if self._cells_different(prev_cell, curr_cell):
                    cells_changed += 1

                    # Generate cursor movement if needed
                    cursor_move = self._generate_cursor_movement(col, row)
                    if cursor_move:
                        output.append(cursor_move)
                        self.current_cursor_x = col
                        self.current_cursor_y = row

                    # Generate style changes: bittty's cached diff when we know
                    # the current state, reset + full style when we don't
                    curr_style, curr_char = curr_cell
                    if self.args.cache_style and self.current_style is not None:
                        style_changes = self.current_style.diff(curr_style)
                    else:
                        style_changes = RESET_STYLE + style_to_ansi(curr_style)
                    if style_changes:
                        output.append(style_changes)
                    self.current_style = curr_style

                    # Output character
                    output.append(curr_char if curr_char else " ")

                    # Update cursor position after character
                    self.current_cursor_x = col + 1
                    if self.current_cursor_x >= self.width:
                        self.current_cursor_x = 0
                        self.current_cursor_y += 1

        # Swap boards - current becomes previous for next frame
        self.prev_board, self.curr_board = self.curr_board, self.prev_board

        # Debug info
        if self.args.debug:
            self.debug("frame", str(self.frame_count))
            self.debug("changed", f"{cells_changed}/{cells_total}")
            self.debug("threshold", f"{self.args.threshold:.1f}")

        # Output differential ANSI
        ansi_output = "".join(output)
        yield timestamp, ansi_output

        self.frame_count += 1

    def _cells_different(self, main_cell: tuple, alt_cell: tuple) -> bool:
        """Check if two cells are visually different enough to update.

        Args:
            main_cell: (Style, char) from main buffer
            alt_cell: (Style, char) from alt buffer

        Returns:
            True if cells should be updated
        """
        main_style, main_char = main_cell
        alt_style, alt_char = alt_cell

        # Different characters always update
        if main_char != alt_char:
            return True

        # If threshold is 0, any style difference triggers update
        if self.args.threshold == 0:
            return main_style != alt_style

        # Check perceptual difference
        visual_diff = perceptual.visual_difference(main_cell, alt_cell, self.curr_board.palette)
        return visual_diff >= self.args.threshold

    def _generate_cursor_movement(self, target_col: int, target_row: int) -> str:
        """Generate minimal cursor movement to target position.

        Args:
            target_col: Target column (0-based)
            target_row: Target row (0-based)

        Returns:
            ANSI escape sequence for cursor movement, or empty string
        """
        if not self.args.cache_position:
            # Always generate explicit positioning
            return MOVE_CURSOR.format(target_row + 1, target_col + 1)

        # Already at target position
        if self.current_cursor_x == target_col and self.current_cursor_y == target_row:
            return ""

        # Natural progression (next column on same row)
        if target_col == self.current_cursor_x + 1 and target_row == self.current_cursor_y:
            return ""

        # Need explicit cursor positioning
        return MOVE_CURSOR.format(target_row + 1, target_col + 1)

    def on_resize(self, timestamp: float, width: int, height: int) -> Iterator[Tuple[float, Any]]:
        """Handle resize event - resize boards first, then propagate."""
        # Resize our boards first (before updating self.width/height)
        if width != self.width or height != self.height:
            self.prev_board.resize(width, height)
            self.curr_board.resize(width, height)
        # Now call parent to update self.width/height and propagate
        yield from super().on_resize(timestamp, width, height)
