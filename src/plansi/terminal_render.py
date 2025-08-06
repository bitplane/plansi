"""ANSI rendering using bittty terminal emulator with dual buffer approach."""

from PIL import Image
from typing import Set, Tuple
from chafa import (
    Canvas,
    CanvasConfig,
    CanvasMode,
    ColorSpace,
    DitherMode,
    PixelMode,
    PixelType,
)
from bittty import Terminal
from .control_codes import (
    DISABLE_LINE_WRAP,
    ENABLE_LNM,
    MOVE_CURSOR,
)
from . import perceptual
from . import style


class TerminalRenderer:
    """Renders frames using bittty dual buffer approach.

    - Main buffer: What we've sent to the real terminal
    - Alt buffer: New frame rendered with chafa
    - Diff the buffers and output only changed cells
    """

    def __init__(
        self,
        width: int,
        height: int,
        color_threshold: float = 5.0,
        debug: bool = False,
        cache_position: bool = False,
        cache_style: bool = True,
    ):
        """Initialize terminal renderer.

        Args:
            width: Width in character cells
            height: Height in character cells
            color_threshold: RGB distance threshold for color changes (0.0-441.67)
            debug: Enable debug output
            cache_position: Enable cursor position caching optimization
            cache_style: Enable style caching optimization
        """
        self.width = width
        self.height = height
        self.color_threshold = color_threshold
        self.debug = debug
        self.cache_position = cache_position
        self.cache_style = cache_style

        # Create bittty terminal instance
        self.terminal = Terminal(width=width, height=height)
        # Configure terminal behavior
        self.terminal.cursor_visible = False
        self.terminal.parser.feed(DISABLE_LINE_WRAP)
        self.terminal.parser.feed(ENABLE_LNM)

        # Configure chafa for full frame rendering
        self.config = CanvasConfig()
        self.config.canvas_mode = CanvasMode.CHAFA_CANVAS_MODE_TRUECOLOR
        self.config.pixel_mode = PixelMode.CHAFA_PIXEL_MODE_SYMBOLS
        self.config.dither_mode = DitherMode.CHAFA_DITHER_MODE_ORDERED
        self.config.color_space = ColorSpace.CHAFA_COLOR_SPACE_RGB
        self.config.work_factor = 1.0
        self.config.width = width
        self.config.height = height

        # Create reusable canvas
        self.canvas = Canvas(self.config)
        self.canvas.width = self.width
        self.canvas.height = self.height

        # State tracking for optimized output generation
        self.current_cursor_x = 0
        self.current_cursor_y = 0
        self.current_style = None  # Track current terminal style state

    def _render_full_frame(self, image: Image.Image) -> str:
        """Render frame to ANSI."""
        # Convert PIL image to RGB if not already
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Get raw pixel data
        width, height = image.size
        pixel_data = image.tobytes()
        rowstride = width * 3  # RGB = 3 bytes per pixel

        # Draw using raw pixel data
        self.canvas.draw_all_pixels(
            PixelType.CHAFA_PIXEL_RGB8,
            pixel_data,
            width,
            height,
            rowstride,
        )

        # Get ANSI output
        ansi_output = self.canvas.print().decode("utf-8")

        return ansi_output

    def _render_to_buffer(self, image: Image.Image) -> str:
        """Render frame for buffer parsing (no line ending fixes needed)."""
        if image.mode != "RGB":
            image = image.convert("RGB")

        width, height = image.size
        pixel_data = image.tobytes()
        rowstride = width * 3

        self.canvas.draw_all_pixels(
            PixelType.CHAFA_PIXEL_RGB8,
            pixel_data,
            width,
            height,
            rowstride,
        )

        return self.canvas.print().decode("utf-8")

    def _cells_different(self, main_cell: tuple, alt_cell: tuple) -> bool:
        """Check if two bittty cells are visually different enough to update.

        Args:
            main_cell: (Style, char) from main buffer
            alt_cell: (Style, char) from alt buffer
        """
        # Optimization: if threshold is 0, skip expensive calculations
        # and just check if cells are identical
        if self.color_threshold == 0.0:
            style1, char1 = main_cell
            style2, char2 = alt_cell
            return not (char1 == char2 and style1 == style2)

        visual_diff = perceptual.visual_difference(main_cell, alt_cell)
        return visual_diff > self.color_threshold

    def _generate_cursor_movement(self, target_col: int, target_row: int) -> str:
        """Generate minimal cursor movement to target position.

        Args:
            target_col: Target column (0-based)
            target_row: Target row (0-based)

        Returns:
            ANSI escape sequence for cursor movement, or empty string if no movement needed
        """
        if not self.cache_position:
            # Cursor caching disabled - always generate explicit positioning
            return MOVE_CURSOR.format(target_row + 1, target_col + 1)

        # Cursor caching enabled - optimize movements
        # Already at target position
        if self.current_cursor_x == target_col and self.current_cursor_y == target_row:
            return ""

        # Natural progression (next column on same row) - no movement needed
        if target_col == self.current_cursor_x + 1 and target_row == self.current_cursor_y:
            return ""

        # Need explicit cursor positioning
        return MOVE_CURSOR.format(target_row + 1, target_col + 1)

    def render_differential(self, image: Image.Image, changed_cells: Set[Tuple[int, int]]) -> Tuple[str, int]:
        """Render only changed cells using dual buffer approach.

        Args:
            image: Current frame as PIL Image
            changed_cells: Set of (cell_x, cell_y) that have changed (IGNORED)

        Returns:
            Tuple of (ANSI string with cursor movements and cell updates, number of changed cells)
        """
        # Initialize primary buffer on first call to match cleared terminal
        if not hasattr(self, "_initialized"):
            self._initialize_primary_buffer()
            self._initialized = True

        # Render new frame with chafa
        full_ansi = self._render_to_buffer(image)

        # Switch to alt buffer and render new frame
        self.terminal.alternate_screen_on()
        self.terminal.clear_screen()  # Clear alt buffer before rendering new frame
        self.terminal.set_cursor(0, 0)  # Reset cursor to home position
        self.terminal.parser.feed(full_ansi)

        # Compare main buffer (current state) vs alt buffer (new frame)
        changed_positions = []
        total_cells = 0
        same_cells = 0

        for row in range(self.height):
            for col in range(self.width):
                total_cells += 1
                # Get cells from both buffers
                main_cell = self.terminal.primary_buffer.get_cell(col, row)
                alt_cell = self.terminal.alt_buffer.get_cell(col, row)

                if self._cells_different(main_cell, alt_cell):
                    changed_positions.append((col, row))
                else:
                    same_cells += 1

        # Build output for changed cells only
        if not changed_positions:
            # Switch back to main buffer
            self.terminal.alternate_screen_off()
            return "", 0

        # Reset state tracking for this frame
        self.current_cursor_x = 0
        self.current_cursor_y = 0
        self.current_style = None

        output_parts = []

        # Sort by row first, then column for optimal cursor movement
        for col, row in sorted(changed_positions, key=lambda pos: (pos[1], pos[0])):
            alt_cell = self.terminal.alt_buffer.get_cell(col, row)
            alt_style, alt_char = alt_cell

            # Generate optimized cursor movement
            cursor_movement = self._generate_cursor_movement(col, row)
            if cursor_movement:
                output_parts.append(cursor_movement)

            # Generate optimized style changes
            style_changes = style.diff(self.current_style, alt_style, self.cache_style)
            if style_changes:
                output_parts.append(style_changes)

            # Update current style for next iteration
            self.current_style = alt_style

            # Add the character
            output_parts.append(alt_char)

            # Update cursor position (character advances cursor by 1)
            self.current_cursor_x = col + 1
            self.current_cursor_y = row

            # Update main buffer to match what we're sending
            self.terminal.primary_buffer.set_cell(col, row, alt_char, alt_style)

        # Switch back to main buffer
        self.terminal.alternate_screen_off()

        return "".join(output_parts), len(changed_positions)

    def clear_cache(self):
        """Clear both buffers to force full refresh."""
        self.terminal.clear_screen()  # Clear main buffer
        self.terminal.alternate_screen_on()
        self.terminal.clear_screen()  # Clear alt buffer
        self.terminal.alternate_screen_off()

    def _initialize_primary_buffer(self):
        """Initialize primary buffer to match cleared terminal state."""
        # Fill primary buffer with empty cells (space char, no colors)
        # Get a sample empty style from an existing cell
        sample_cell = self.terminal.primary_buffer.get_cell(0, 0)
        empty_style = sample_cell[0]  # Use existing style as template

        for row in range(self.height):
            for col in range(self.width):
                self.terminal.primary_buffer.set_cell(col, row, empty_style, " ")
