"""ANSI rendering using bittty terminal emulator with dual buffer approach."""

from PIL import Image
from typing import Set, Tuple
import tempfile
import os
import sys
import math
from chafa import (
    Canvas,
    CanvasConfig,
    CanvasMode,
    ColorSpace,
    DitherMode,
    PixelMode,
)
from chafa.loader import Loader
from bittty import Terminal


class TerminalRenderer:
    """Renders frames using bittty dual buffer approach.

    - Main buffer: What we've sent to the real terminal
    - Alt buffer: New frame rendered with chafa
    - Diff the buffers and output only changed cells
    """

    def __init__(self, width: int, height: int, color_threshold: float = 30.0, debug: bool = False):
        """Initialize terminal renderer.

        Args:
            width: Width in character cells
            height: Height in character cells
            color_threshold: RGB distance threshold for color changes (0.0-441.67)
            debug: Enable debug output
        """
        self.width = width
        self.height = height
        self.color_threshold = color_threshold
        self.debug = debug

        # Create bittty terminal instance
        self.terminal = Terminal(width=width, height=height)
        # Disable cursor
        self.terminal.cursor_visible = False

        # Configure chafa for full frame rendering
        self.config = CanvasConfig()
        self.config.canvas_mode = CanvasMode.CHAFA_CANVAS_MODE_TRUECOLOR
        self.config.pixel_mode = PixelMode.CHAFA_PIXEL_MODE_SYMBOLS
        self.config.dither_mode = DitherMode.CHAFA_DITHER_MODE_ORDERED
        self.config.color_space = ColorSpace.CHAFA_COLOR_SPACE_RGB
        self.config.work_factor = 1.0
        self.config.width = width
        self.config.height = height

    def _render_full_frame(self, image: Image.Image) -> str:
        """Render entire frame to ANSI using chafa."""
        # Save to temporary file for chafa
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            image.save(tmp.name, "PNG")
            tmp_path = tmp.name

        try:
            # Load image with chafa loader
            loader = Loader(tmp_path)

            # Create chafa canvas for full frame
            canvas = Canvas(self.config)
            canvas.width = self.width
            canvas.height = self.height

            # Draw using loader
            canvas.draw_all_pixels(
                loader.pixel_type, loader.get_pixels(), loader.width, loader.height, loader.rowstride
            )

            # Get ANSI output
            ansi_output = canvas.print().decode("utf-8")

            # Fix line endings - chafa outputs \n but we need \r\n for proper terminal positioning
            ansi_output = ansi_output.replace("\n", "\r\n")

            return ansi_output

        finally:
            os.unlink(tmp_path)

    def _contrast(self, fg_color: tuple, bg_color: tuple) -> float:
        """Calculate contrast between foreground and background colors.

        Args:
            fg_color: RGB tuple (r, g, b) or None
            bg_color: RGB tuple (r, g, b) or None

        Returns:
            Contrast value (0.0 to ~441.67)
        """
        if fg_color is None or bg_color is None:
            return 0.0  # No contrast if either color is missing
        return self._color_distance(fg_color, bg_color)

    def _color_distance(self, color1: tuple, color2: tuple) -> float:
        """Calculate Euclidean distance between two RGB colors.

        Args:
            color1: RGB tuple (r, g, b) or None
            color2: RGB tuple (r, g, b) or None

        Returns:
            Distance between colors (0.0 to ~441.67 for max RGB distance)
        """
        if color1 is None or color2 is None:
            # If either color is None, treat as maximum distance if the other isn't None
            return 441.67 if (color1 is None) != (color2 is None) else 0.0

        r1, g1, b1 = color1
        r2, g2, b2 = color2
        return math.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2)

    def _quantize_rgb(self, color: tuple) -> tuple:
        """Quantize RGB color to reduce noise from dithering artifacts.

        Args:
            color: RGB tuple (r, g, b)

        Returns:
            Quantized RGB tuple
        """
        if color is None:
            return None
        # Reduce from 8-bit to 5-bit per channel (32 levels each)
        r, g, b = color
        return (r // 8 * 8, g // 8 * 8, b // 8 * 8)

    def _extract_rgb_color(self, color_obj) -> tuple:
        """Extract RGB tuple from bittty color object.

        Args:
            color_obj: bittty color object

        Returns:
            RGB tuple (r, g, b) or None if no color
        """
        if not color_obj or not hasattr(color_obj, "value") or not color_obj.value:
            return None

        if hasattr(color_obj.value, "__iter__") and len(color_obj.value) == 3:
            # Extract and quantize the color
            return self._quantize_rgb(tuple(color_obj.value))

        return None

    def _visual_difference(self, cell1: tuple, cell2: tuple) -> float:
        """Calculate visual difference between two cells in perceptual space.

        Args:
            cell1: (Style, char) from first cell
            cell2: (Style, char) from second cell

        Returns:
            Visual difference score (0.0 = identical, higher = more different)
        """
        style1, char1 = cell1
        style2, char2 = cell2

        # Quick check for identical cells
        if char1 == char2 and style1 == style2:
            return 0.0

        # Extract colors
        fg1 = self._extract_rgb_color(style1.fg)
        bg1 = self._extract_rgb_color(style1.bg)
        fg2 = self._extract_rgb_color(style2.fg)
        bg2 = self._extract_rgb_color(style2.bg)

        # Normalize color distances to 0-1 range (max RGB distance is ~441)
        fg_diff = self._color_distance(fg1, fg2) / 441.67
        bg_diff = self._color_distance(bg1, bg2) / 441.67

        # Glyph difference (binary: 0 or 1)
        glyph_weight = 1.0 if char1 != char2 else 0.0

        # Contrast differences (normalized)
        contrast1 = self._contrast(fg1, bg1) / 441.67
        contrast2 = self._contrast(fg2, bg2) / 441.67
        contrast_diff = abs(contrast1 - contrast2)

        # Simple balanced weights as suggested by GPT
        total_diff = (
            0.5 * glyph_weight  # Glyph changes matter most
            + 0.25 * fg_diff  # Foreground color
            + 0.25 * bg_diff  # Background color
            + 0.25 * contrast_diff  # Contrast changes
        )

        # Scale by 100 to make threshold more intuitive (default 30 = 30% difference)
        return total_diff * 100.0

    def _cells_different(self, main_cell: tuple, alt_cell: tuple) -> bool:
        """Check if two bittty cells are visually different enough to update.

        Args:
            main_cell: (Style, char) from main buffer
            alt_cell: (Style, char) from alt buffer
        """
        visual_diff = self._visual_difference(main_cell, alt_cell)

        return visual_diff > self.color_threshold

    def _style_to_ansi(self, style, char: str) -> str:
        """Convert bittty Style object to ANSI escape sequence."""
        parts = []

        # Foreground color
        if style.fg and hasattr(style.fg, "value") and style.fg.value:
            if hasattr(style.fg.value, "__iter__") and len(style.fg.value) == 3:
                r, g, b = style.fg.value
                parts.append(f"\x1b[38;2;{r};{g};{b}m")

        # Background color
        if style.bg and hasattr(style.bg, "value") and style.bg.value:
            if hasattr(style.bg.value, "__iter__") and len(style.bg.value) == 3:
                r, g, b = style.bg.value
                parts.append(f"\x1b[48;2;{r};{g};{b}m")

        # Attributes
        if style.bold:
            parts.append("\x1b[1m")
        if style.reverse:
            parts.append("\x1b[7m")
        if style.dim:
            parts.append("\x1b[2m")
        if style.italic:
            parts.append("\x1b[3m")
        if style.underline:
            parts.append("\x1b[4m")
        if style.blink:
            parts.append("\x1b[5m")
        if style.strike:
            parts.append("\x1b[9m")

        parts.append(char)
        return "".join(parts)

    def render_differential(self, image: Image.Image, changed_cells: Set[Tuple[int, int]]) -> Tuple[str, int]:
        """Render only changed cells using dual buffer approach.

        Args:
            image: Current frame as PIL Image
            changed_cells: Set of (cell_x, cell_y) that have changed (IGNORED)

        Returns:
            Tuple of (ANSI string with cursor movements and cell updates, number of changed cells)
        """
        # Render new frame with chafa
        full_ansi = self._render_full_frame(image)

        # Switch to alt buffer and render new frame
        self.terminal.alternate_screen_on()
        self.terminal.clear_screen()
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

        if self.debug:
            print(
                f"DEBUG: {len(changed_positions)} cells changed, {same_cells} cells same (out of {total_cells} total)",
                file=sys.stderr,
            )
            # Show which rows have content
            rows_with_content = set(row for col, row in changed_positions)
            print(f"DEBUG: rows with content: {sorted(rows_with_content)}", file=sys.stderr)

        # Build output for changed cells only
        if not changed_positions:
            # Switch back to main buffer
            self.terminal.alternate_screen_off()
            return "", 0

        output_parts = []

        # Sort by row first, then column for optimal cursor movement
        for col, row in sorted(changed_positions, key=lambda pos: (pos[1], pos[0])):
            alt_cell = self.terminal.alt_buffer.get_cell(col, row)

            # Position cursor
            output_parts.append(f"\x1b[{row + 1};{col + 1}H")

            # Convert style to ANSI and add character
            cell_ansi = self._style_to_ansi(alt_cell[0], alt_cell[1])
            output_parts.append(cell_ansi)

            # Update main buffer to match what we're sending
            self.terminal.primary_buffer.set_cell(col, row, alt_cell[0], alt_cell[1])

        # Switch back to main buffer
        self.terminal.alternate_screen_off()

        return "".join(output_parts), len(changed_positions)

    def clear_cache(self):
        """Clear both buffers to force full refresh."""
        self.terminal.clear_screen()  # Clear main buffer
        self.terminal.alternate_screen_on()
        self.terminal.clear_screen()  # Clear alt buffer
        self.terminal.alternate_screen_off()
