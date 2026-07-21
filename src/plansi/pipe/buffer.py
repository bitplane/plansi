"""Buffer pipe using bittty for ANSI accumulation and differential rendering."""

from typing import Iterator, Tuple, Any
from bittty import Board
from bittty.style import style_to_ansi

from .base import Pipe
from ..control_codes import DISABLE_LINE_WRAP, ENABLE_LNM, MOVE_CURSOR, RESET_STYLE
from .. import perceptual


class AnsiBuffer(Pipe):
    """Accumulates ANSI into a buffer and outputs differential updates.

    Two bittty Boards: the truth board parses every input chunk and holds what
    the input has actually drawn; the viewer board holds what the receiving
    terminal shows, updated only with the cells we emit. Diffing truth against
    viewer means incremental input (cast chunks) accumulates instead of being
    erased, and changes suppressed by the threshold stay in play — their drift
    keeps growing against future frames until it crosses the line.

    Input: (timestamp, ansi_string) full frames or incremental chunks
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
        """Initialize the truth and viewer boards."""
        self.truth_board = Board(width=self.width, height=self.height)
        self.truth_board.parser.feed(DISABLE_LINE_WRAP)
        self.truth_board.parser.feed(ENABLE_LNM)

        self.viewer_board = Board(width=self.width, height=self.height)
        self.viewer_board.parser.feed(DISABLE_LINE_WRAP)
        self.viewer_board.parser.feed(ENABLE_LNM)

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
            data: Full frame or incremental chunk of ANSI

        Yields:
            (timestamp, ansi_string) with differential updates
        """
        self.truth_board.parser.feed(data)

        # First frame: pass through verbatim - the viewer sees exactly what we sent
        if self.first_frame:
            self.first_frame = False
            self.viewer_board.parser.feed(data)
            yield timestamp, data
            self.frame_count += 1
            return

        # Reset state tracking for this frame
        self.current_cursor_x = 0
        self.current_cursor_y = 0
        self.current_style = None

        output = []
        cells_changed = 0
        cells_total = 0
        truth_page = self.truth_board.blitter.current_buffer
        viewer_page = self.viewer_board.blitter.primary_buffer

        for row in range(self.height):
            for col in range(self.width):
                cells_total += 1

                viewer_cell = viewer_page.get_cell(col, row)
                truth_cell = truth_page.get_cell(col, row)

                if self._cells_different(viewer_cell, truth_cell):
                    cells_changed += 1

                    # Generate cursor movement if needed
                    cursor_move = self._generate_cursor_movement(col, row)
                    if cursor_move:
                        output.append(cursor_move)
                        self.current_cursor_x = col
                        self.current_cursor_y = row

                    # Generate style changes: bittty's cached diff when we know
                    # the current state, reset + full style when we don't
                    truth_style, truth_char = truth_cell
                    if self.args.cache_style and self.current_style is not None:
                        style_changes = self.current_style.diff(truth_style)
                    else:
                        style_changes = RESET_STYLE + style_to_ansi(truth_style)
                    if style_changes:
                        output.append(style_changes)
                    self.current_style = truth_style

                    # Output character, and land it on the viewer board
                    char = truth_char if truth_char else " "
                    output.append(char)
                    viewer_page.set_cell(col, row, char, truth_style)

                    # Update cursor position after character
                    self.current_cursor_x = col + 1
                    if self.current_cursor_x >= self.width:
                        self.current_cursor_x = 0
                        self.current_cursor_y += 1

        # Debug info
        if self.args.debug:
            self.debug("frame", str(self.frame_count))
            self.debug("changed", f"{cells_changed}/{cells_total}")
            self.debug("threshold", f"{self.args.threshold:.1f}")

        self.frame_count += 1

        # Output differential ANSI; silent frames vanish from the stream
        ansi_output = "".join(output)
        if ansi_output:
            yield timestamp, ansi_output

    def _cells_different(self, viewer_cell: tuple, truth_cell: tuple) -> bool:
        """Check if two cells are visually different enough to update.

        Args:
            viewer_cell: (Style, char) the receiving terminal currently shows
            truth_cell: (Style, char) the input has drawn

        Returns:
            True if cells should be updated
        """
        viewer_style, viewer_char = viewer_cell
        truth_style, truth_char = truth_cell

        # Different characters always update
        if viewer_char != truth_char:
            return True

        # If threshold is 0, any style difference triggers update
        if self.args.threshold == 0:
            return viewer_style != truth_style

        # Check perceptual difference
        visual_diff = perceptual.visual_difference(viewer_cell, truth_cell, self.truth_board.palette)
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
            self.truth_board.resize(width, height)
            self.viewer_board.resize(width, height)
        # Now call parent to update self.width/height and propagate
        yield from super().on_resize(timestamp, width, height)
