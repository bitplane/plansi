"""Buffer pipe using bittty for ANSI accumulation and differential rendering."""

from typing import Iterator, Tuple, Any
from bittty import Terminal

from .base import Pipe
from ..control_codes import DISABLE_LINE_WRAP, ENABLE_LNM, MOVE_CURSOR
from .. import style
from .. import perceptual


class AnsiBuffer(Pipe):
    """Accumulates ANSI into a buffer and outputs differential updates.

    Uses bittty Terminal to parse ANSI sequences and maintain buffers,
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
        """Initialize two separate terminals."""
        # Previous frame terminal
        self.prev_terminal = Terminal(width=self.args.width, height=self.args.height)
        self.prev_terminal.cursor_visible = False
        self.prev_terminal.parser.feed(DISABLE_LINE_WRAP)
        self.prev_terminal.parser.feed(ENABLE_LNM)

        # Current frame terminal
        self.curr_terminal = Terminal(width=self.args.width, height=self.args.height)
        self.curr_terminal.cursor_visible = False
        self.curr_terminal.parser.feed(DISABLE_LINE_WRAP)
        self.curr_terminal.parser.feed(ENABLE_LNM)

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

        # First frame: parse into prev_terminal and output directly
        if self.first_frame:
            self.first_frame = False
            # Parse into prev_terminal only
            self.prev_terminal.set_cursor(0, 0)
            self.prev_terminal.parser.feed(ansi_input)

            # Output first frame directly
            yield timestamp, ansi_input
            self.frame_count += 1
            return

        # Parse current frame into curr_terminal
        self.curr_terminal.set_cursor(0, 0)
        self.curr_terminal.parser.feed(ansi_input)

        # Generate differential output by comparing terminals

        # Reset state tracking for this frame
        self.current_cursor_x = 0
        self.current_cursor_y = 0
        self.current_style = None

        output = []
        cells_changed = 0
        cells_total = 0

        for row in range(self.args.height):
            for col in range(self.args.width):
                cells_total += 1

                # Get cells from both terminals
                prev_cell = self.prev_terminal.primary_buffer.get_cell(col, row)
                curr_cell = self.curr_terminal.primary_buffer.get_cell(col, row)

                # Check if cells are different
                if self._cells_different(prev_cell, curr_cell):
                    cells_changed += 1

                    # Generate cursor movement if needed
                    cursor_move = self._generate_cursor_movement(col, row)
                    if cursor_move:
                        output.append(cursor_move)
                        self.current_cursor_x = col
                        self.current_cursor_y = row

                    # Generate style changes
                    curr_style, curr_char = curr_cell
                    style_changes = style.diff(self.current_style, curr_style, self.args.cache_style)
                    if style_changes:
                        output.append(style_changes)
                        self.current_style = curr_style

                    # Output character
                    output.append(curr_char if curr_char else " ")

                    # Update cursor position after character
                    self.current_cursor_x = col + 1
                    if self.current_cursor_x >= self.args.width:
                        self.current_cursor_x = 0
                        self.current_cursor_y += 1

        # Swap terminals - current becomes previous for next frame
        self.prev_terminal, self.curr_terminal = self.curr_terminal, self.prev_terminal

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
            return not style.equal(main_style, alt_style)

        # Check perceptual difference
        visual_diff = perceptual.visual_difference(main_cell, alt_cell)
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

    def _initialize_primary_buffer(self):
        """Initialize primary buffer to match cleared terminal state."""
        # Clear the primary buffer completely
        self.terminal.clear_screen()

        # Now the primary buffer should have empty cells with default style
