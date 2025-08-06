"""Image to ANSI converter pipe."""

from typing import Iterator, Tuple, Any
from chafa import PixelMode, DitherMode, PixelType, Canvas, ColorSpace, CanvasConfig, CanvasMode

from .base import Pipe, Event
from ..control_codes import HIDE_CURSOR, HOME_CURSOR, SHOW_CURSOR


class ImageToAnsi(Pipe):
    """Converts PIL Images to ANSI escape sequences using Chafa.

    Input: (timestamp, PIL.Image)
    Output: (timestamp, ansi_string) full frame ANSI sequences
    """

    def setup(self):
        """Initialize Chafa canvas."""
        # Get dimensions from args - width is already set by base Pipe class
        # which gets it from args or defaults to 80

        # Will calculate height on first frame to maintain aspect ratio
        self.canvas = None
        self.height = None
        self.frame_count = 0

    def teardown(self):
        """Clean up canvas."""
        self.canvas = None

    def process(self, timestamp: float, data: Any) -> Iterator[Tuple[float, str]]:
        """Convert image to ANSI."""
        img = data

        # Initialize canvas on first frame
        if self.canvas is None:
            # Calculate height maintaining aspect ratio
            # Terminal chars are ~2:1 aspect ratio
            img_width, img_height = img.size
            aspect_ratio = img_height / img_width
            self.height = int(self.width * aspect_ratio * 0.5)

            # Configure Chafa
            config = CanvasConfig()
            config.canvas_mode = CanvasMode.CHAFA_CANVAS_MODE_TRUECOLOR
            config.pixel_mode = PixelMode.CHAFA_PIXEL_MODE_SYMBOLS
            config.dither_mode = DitherMode.CHAFA_DITHER_MODE_ORDERED
            config.color_space = ColorSpace.CHAFA_COLOR_SPACE_RGB
            config.work_factor = 1.0
            config.width = self.width
            config.height = self.height

            # Create reusable canvas
            self.canvas = Canvas(config)
            self.canvas.width = self.width
            self.canvas.height = self.height

            self.debug("canvas", f"{self.width}x{self.height}")

            # Emit resize event on first frame
            yield timestamp, Event("resize", width=self.width, height=self.height)

        # Render image to ANSI
        width, height = img.size
        pixel_data = img.tobytes()
        rowstride = width * 3  # RGB = 3 bytes per pixel

        self.canvas.draw_all_pixels(
            PixelType.CHAFA_PIXEL_RGB8,
            pixel_data,
            width,
            height,
            rowstride,
        )

        # Get ANSI output
        ansi_output = self.canvas.print().decode("utf-8")

        # Add cursor control for full frame output
        full_output = HIDE_CURSOR + HOME_CURSOR + ansi_output + SHOW_CURSOR

        self.frame_count += 1

        yield timestamp, full_output
