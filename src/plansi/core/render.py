"""ANSI rendering with chafa integration and differential output."""

from PIL import Image
from typing import Set, Tuple, Dict
import tempfile
import os
from chafa import (
    ChafaCanvas,
    ChafaCanvasMode,
    ChafaColorSpace,
    ChafaConfig,
    ChafaDitherMode,
    ChafaPixelMode,
    ChafaPixelType,
)


class ANSIRenderer:
    """Renders frames to ANSI with differential updates."""

    def __init__(self, width: int, height: int):
        """Initialize ANSI renderer.

        Args:
            width: Width in character cells
            height: Height in character cells
        """
        self.width = width
        self.height = height
        self._cell_cache: Dict[Tuple[int, int], str] = {}

        # Configure chafa for 8x4 character blocks
        self.config = ChafaConfig()
        self.config.set_canvas_mode(ChafaCanvasMode.CHAFA_CANVAS_MODE_INDEXED_240)
        self.config.set_pixel_mode(ChafaPixelMode.CHAFA_PIXEL_MODE_SYMBOLS)
        self.config.set_dither_mode(ChafaDitherMode.CHAFA_DITHER_MODE_NONE)
        self.config.set_color_space(ChafaColorSpace.CHAFA_COLOR_SPACE_RGB)
        self.config.set_work_factor(1.0)

    def _render_cell(self, image: Image.Image, cell_x: int, cell_y: int) -> str:
        """Render a single 8x4 cell to ANSI using chafa."""
        # Extract the cell region (8x4 pixels)
        left = cell_x * 8
        top = cell_y * 4
        right = min(left + 8, image.width)
        bottom = min(top + 4, image.height)

        if left >= image.width or top >= image.height:
            return " "  # Empty cell

        cell_img = image.crop((left, top, right, bottom))

        # Save to temporary file for chafa
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            cell_img.save(tmp.name, "PNG")
            tmp_path = tmp.name

        try:
            # Create chafa canvas for this single cell
            canvas = ChafaCanvas(self.config)
            canvas.set_size(1, 1)  # 1x1 character

            # Load and draw the cell image
            with open(tmp_path, "rb") as f:
                canvas.draw_all_pixels(
                    ChafaPixelType.CHAFA_PIXEL_RGB8, f.read(), cell_img.width, cell_img.height, cell_img.width * 3
                )

            # Get ANSI output
            ansi_output = canvas.print().decode("utf-8").strip()
            return ansi_output if ansi_output else " "

        finally:
            os.unlink(tmp_path)

    def render_differential(self, image: Image.Image, changed_cells: Set[Tuple[int, int]]) -> str:
        """Render only changed cells with cursor positioning.

        Args:
            image: Current frame as PIL Image
            changed_cells: Set of (cell_x, cell_y) that have changed

        Returns:
            ANSI string with cursor movements and cell updates
        """
        if not changed_cells:
            return ""

        output_parts = []

        for cell_x, cell_y in sorted(changed_cells):
            # Render the cell
            cell_ansi = self._render_cell(image, cell_x, cell_y)

            # Cache the result
            self._cell_cache[(cell_x, cell_y)] = cell_ansi

            # Position cursor and write cell
            # Terminal rows/cols are 1-indexed
            cursor_pos = f"\x1b[{cell_y + 1};{cell_x + 1}H"
            output_parts.append(f"{cursor_pos}{cell_ansi}")

        return "".join(output_parts)

    def clear_cache(self):
        """Clear the cell cache to force full refresh."""
        self._cell_cache.clear()
