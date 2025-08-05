"""Pixel difference detection for 8x4 character cells."""

from PIL import Image
from typing import Set, Tuple, Optional
import math


class DiffEngine:
    """Detects changes between frames at the 8x4 character cell level."""

    def __init__(self, pixel_threshold: int = 30, cell_threshold: float = 0.25):
        """Initialize difference engine.

        Args:
            pixel_threshold: RGB distance threshold for pixel changes (0-255)
            cell_threshold: Fraction of pixels that must change in a cell (0.0-1.0)
        """
        self.pixel_threshold = pixel_threshold
        self.cell_threshold = cell_threshold
        self.reference_frame: Optional[Image.Image] = None

    def _pixel_distance(self, p1: tuple, p2: tuple) -> float:
        """Calculate RGB distance between two pixels."""
        if len(p1) == 4:  # RGBA
            p1 = p1[:3]
        if len(p2) == 4:  # RGBA
            p2 = p2[:3]
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2)))

    def _cell_changed(self, current: Image.Image, reference: Image.Image, cell_x: int, cell_y: int) -> bool:
        """Check if an 8x4 cell has enough changed pixels."""
        changed_pixels = 0
        total_pixels = 32  # 8x4

        # Sample pixels in the cell
        for y in range(cell_y * 4, (cell_y + 1) * 4):
            for x in range(cell_x * 8, (cell_x + 1) * 8):
                if x < current.width and y < current.height and x < reference.width and y < reference.height:
                    curr_pixel = current.getpixel((x, y))
                    ref_pixel = reference.getpixel((x, y))

                    if self._pixel_distance(curr_pixel, ref_pixel) > self.pixel_threshold:
                        changed_pixels += 1

        return (changed_pixels / total_pixels) >= self.cell_threshold

    def get_changed_cells(self, current_frame: Image.Image) -> Set[Tuple[int, int]]:
        """Get set of (cell_x, cell_y) coordinates that have changed.

        Args:
            current_frame: Current frame as PIL Image

        Returns:
            Set of (x, y) cell coordinates that have changed
        """
        if self.reference_frame is None:
            # First frame - everything has "changed"
            self.reference_frame = current_frame.copy()
            cols = (current_frame.width + 7) // 8
            rows = (current_frame.height + 3) // 4
            return {(x, y) for x in range(cols) for y in range(rows)}

        changed_cells = set()
        cols = (current_frame.width + 7) // 8
        rows = (current_frame.height + 3) // 4

        for cell_y in range(rows):
            for cell_x in range(cols):
                if self._cell_changed(current_frame, self.reference_frame, cell_x, cell_y):
                    changed_cells.add((cell_x, cell_y))

        return changed_cells

    def update_reference(self, new_frame: Image.Image):
        """Update the reference frame to prevent drift."""
        self.reference_frame = new_frame.copy()
