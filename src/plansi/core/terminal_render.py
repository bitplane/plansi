"""ANSI rendering using bittty terminal emulator with dual buffer approach."""

from PIL import Image
from typing import Set, Tuple
import math
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
        self.terminal.parser.feed("\x1b[?7l")  # Disable line wrapping
        self.terminal.parser.feed("\x1b[?20h")  # Enable LNM (makes \n behave like \r\n)

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
        """Render entire frame to ANSI using chafa without temporary files."""
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

        # Fix line endings - chafa outputs \n but we need \r\n for proper terminal positioning
        ansi_output = ansi_output.replace("\n", "\r\n")

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

    def _contrast(self, fg_color: tuple, bg_color: tuple) -> float:
        """Calculate contrast between foreground and background colors.

        Args:
            fg_color: RGB tuple (r, g, b)
            bg_color: RGB tuple (r, g, b)

        Returns:
            Contrast value (0.0 to ~441.67)
        """
        return self._color_distance(fg_color, bg_color)

    def _rgb_to_lab(self, rgb: tuple) -> tuple:
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

    def _color_distance(self, color1: tuple, color2: tuple) -> float:
        """Calculate perceptual distance between two RGB colors using LAB color space.

        Args:
            color1: RGB tuple (r, g, b)
            color2: RGB tuple (r, g, b)

        Returns:
            Perceptual distance between colors (Delta E in LAB space)
        """
        lab1 = self._rgb_to_lab(color1)
        lab2 = self._rgb_to_lab(color2)

        L1, a1, b1 = lab1
        L2, a2, b2 = lab2

        # Delta E CIE76 formula
        return math.sqrt((L1 - L2) ** 2 + (a1 - a2) ** 2 + (b1 - b2) ** 2)

    def _quantize_rgb(self, color: tuple) -> tuple:
        """Quantize RGB color to reduce noise from dithering artifacts.

        Args:
            color: RGB tuple (r, g, b)

        Returns:
            Quantized RGB tuple
        """
        # Reduce from 8-bit to 5-bit per channel (32 levels each)
        r, g, b = color
        return (r // 8 * 8, g // 8 * 8, b // 8 * 8)

    def _extract_rgb_color(self, color_obj) -> tuple:
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
            return self._quantize_rgb(tuple(color_obj.value))

        return (0, 0, 0)  # Default to black if can't extract

    def _visual_difference(self, cell1: tuple, cell2: tuple) -> float:
        """Calculate visual difference between two cells based on human perception."""
        style1, char1 = cell1
        style2, char2 = cell2

        # Early exit for identical characters and styles
        if char1 == char2 and style1.reverse == style2.reverse:
            # Quick style comparison before expensive color extraction
            if style1.fg == style2.fg and style1.bg == style2.bg:
                return 0.0

        # Extract colors once
        fg1 = self._extract_rgb_color(style1.fg)
        bg1 = self._extract_rgb_color(style1.bg)
        fg2 = self._extract_rgb_color(style2.fg)
        bg2 = self._extract_rgb_color(style2.bg)

        # Handle inverse video by flipping fg/bg for comparison
        if style1.reverse:
            fg1, bg1 = bg1, fg1
        if style2.reverse:
            fg2, bg2 = bg2, fg2

        # Calculate perceptual color difference between the two cells
        fg_color_diff = min(self._color_distance(fg1, fg2) / 200.0, 1.0)
        bg_color_diff = min(self._color_distance(bg1, bg2) / 200.0, 1.0)
        total_diff = (fg_color_diff + bg_color_diff) / 2.0

        return total_diff * 100.0

    def _cells_different(self, main_cell: tuple, alt_cell: tuple) -> bool:
        """Check if two bittty cells are visually different enough to update.

        Args:
            main_cell: (Style, char) from main buffer
            alt_cell: (Style, char) from alt buffer
        """
        visual_diff = self._visual_difference(main_cell, alt_cell)

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
            return f"\x1b[{target_row + 1};{target_col + 1}H"

        # Cursor caching enabled - optimize movements
        # Already at target position
        if self.current_cursor_x == target_col and self.current_cursor_y == target_row:
            return ""

        # Natural progression (next column on same row) - no movement needed
        if target_col == self.current_cursor_x + 1 and target_row == self.current_cursor_y:
            return ""

        # Need explicit cursor positioning
        return f"\x1b[{target_row + 1};{target_col + 1}H"

    def _generate_style_changes(self, new_style) -> str:
        """Generate minimal ANSI escape sequences for style changes.

        Simple 3-case approach:
        1. If identical -> no output
        2. If attributes differ -> reset + full style
        3. If only colors differ -> color sequences only
        """
        if not self.cache_style:
            # Style caching disabled - always generate full style
            return self._full_style_to_ansi(new_style)

        # Style caching enabled - optimize style changes
        result = ""

        if self.current_style is None:
            # First style - need full setup
            result = self._full_style_to_ansi(new_style)
        else:
            # Check if styles are identical
            if self._styles_identical(self.current_style, new_style):
                # Case 1: Identical - no output needed
                result = ""
            else:
                # Check if any text attributes differ
                attributes_differ = (
                    self.current_style.bold != new_style.bold
                    or self.current_style.dim != new_style.dim
                    or self.current_style.italic != new_style.italic
                    or self.current_style.underline != new_style.underline
                    or self.current_style.blink != new_style.blink
                    or self.current_style.strike != new_style.strike
                    or self.current_style.reverse != new_style.reverse
                )

                if attributes_differ:
                    # Case 2: Attributes differ - reset and full rebuild
                    result = self._full_style_to_ansi(new_style)
                else:
                    # Case 3: Only colors differ - send color sequences only
                    parts = []

                    # Check foreground color
                    if not self._colors_equal(self.current_style.fg, new_style.fg):
                        if new_style.fg and new_style.fg.value and len(new_style.fg.value) == 3:
                            r, g, b = new_style.fg.value
                            parts.append(f"\x1b[38;2;{r};{g};{b}m")
                        else:
                            # No foreground color - reset to default
                            parts.append("\x1b[39m")

                    # Check background color
                    if not self._colors_equal(self.current_style.bg, new_style.bg):
                        if new_style.bg and new_style.bg.value and len(new_style.bg.value) == 3:
                            r, g, b = new_style.bg.value
                            parts.append(f"\x1b[48;2;{r};{g};{b}m")
                        else:
                            # No background color - reset to default
                            parts.append("\x1b[49m")

                    result = "".join(parts)

        # Always update current style to maintain consistency
        self.current_style = new_style
        return result

    def _styles_identical(self, style1, style2) -> bool:
        """Check if two styles are completely identical."""
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
        return self._colors_equal(style1.fg, style2.fg) and self._colors_equal(style1.bg, style2.bg)

    def _colors_equal(self, color1, color2) -> bool:
        """Check if two bittty color objects are equal."""
        if not color1 and not color2:
            return True
        if not color1 or not color2:
            return False
        if not color1.value or not color2.value:
            return not color1.value and not color2.value
        return color1.value == color2.value

    def _full_style_to_ansi(self, style) -> str:
        """Generate full ANSI style sequence (used for first style)."""
        parts = ["\x1b[0m"]  # Reset first

        # Foreground color
        if style.fg and style.fg.value and len(style.fg.value) == 3:
            r, g, b = style.fg.value
            parts.append(f"\x1b[38;2;{r};{g};{b}m")

        # Background color
        if style.bg and style.bg.value and len(style.bg.value) == 3:
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

        return "".join(parts)

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
            style_changes = self._generate_style_changes(alt_style)
            if style_changes:
                output_parts.append(style_changes)

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
