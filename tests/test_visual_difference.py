"""Tests for visual difference algorithm with known color values and styles."""

from unittest.mock import Mock
from plansi.core.terminal_render import TerminalRenderer


class TestVisualDifference:
    """Test visual difference calculations with known values."""

    def setup_method(self):
        """Set up test renderer."""
        self.renderer = TerminalRenderer(width=80, height=24, color_threshold=30.0)

    def create_mock_style(self, fg_rgb=None, bg_rgb=None, reverse=False):
        """Create a mock bittty Style object."""
        style = Mock()
        style.reverse = reverse

        # Mock fg color
        if fg_rgb:
            style.fg = Mock()
            style.fg.value = fg_rgb
        else:
            style.fg = None

        # Mock bg color
        if bg_rgb:
            style.bg = Mock()
            style.bg.value = bg_rgb
        else:
            style.bg = None

        return style

    def test_identical_cells_return_zero(self):
        """Identical cells should return 0.0 difference."""
        # Same character, same colors
        style1 = self.create_mock_style(fg_rgb=(255, 255, 255), bg_rgb=(0, 0, 0))
        style2 = self.create_mock_style(fg_rgb=(255, 255, 255), bg_rgb=(0, 0, 0))

        cell1 = (style1, "A")
        cell2 = (style2, "A")

        diff = self.renderer._visual_difference(cell1, cell2)
        assert diff == 0.0, f"Identical cells should return 0.0, got {diff}"

    def test_different_characters_same_colors(self):
        """Different characters with same colors should give NO difference (color-only algorithm)."""
        style1 = self.create_mock_style(fg_rgb=(255, 255, 255), bg_rgb=(0, 0, 0))
        style2 = self.create_mock_style(fg_rgb=(255, 255, 255), bg_rgb=(0, 0, 0))

        cell1 = (style1, "A")
        cell2 = (style2, "B")

        diff = self.renderer._visual_difference(cell1, cell2)
        assert diff == 0.0, f"Same colors should give 0 difference regardless of character, got {diff}"
        print(f"Different chars, same colors: {diff}")

    def test_same_character_different_colors(self):
        """Same character with different colors should give some difference."""
        style1 = self.create_mock_style(fg_rgb=(255, 255, 255), bg_rgb=(0, 0, 0))
        style2 = self.create_mock_style(fg_rgb=(255, 0, 0), bg_rgb=(0, 0, 0))  # Red fg

        cell1 = (style1, "A")
        cell2 = (style2, "A")

        diff = self.renderer._visual_difference(cell1, cell2)
        assert diff > 0.0, f"Different colors should give difference > 0, got {diff}"
        print(f"Same char, different colors: {diff}")

    def test_high_contrast_vs_low_contrast_colors(self):
        """Different high contrast colors vs different low contrast colors."""
        # High contrast colors: white vs black
        white_style = self.create_mock_style(fg_rgb=(255, 255, 255), bg_rgb=(0, 0, 0))
        black_style = self.create_mock_style(fg_rgb=(0, 0, 0), bg_rgb=(0, 0, 0))

        # Low contrast colors: light gray vs dark gray
        light_gray_style = self.create_mock_style(fg_rgb=(180, 180, 180), bg_rgb=(0, 0, 0))
        dark_gray_style = self.create_mock_style(fg_rgb=(120, 120, 120), bg_rgb=(0, 0, 0))

        high_cell1 = (white_style, "A")
        high_cell2 = (black_style, "A")

        low_cell1 = (light_gray_style, "A")
        low_cell2 = (dark_gray_style, "A")

        high_diff = self.renderer._visual_difference(high_cell1, high_cell2)
        low_diff = self.renderer._visual_difference(low_cell1, low_cell2)

        print(f"High contrast color diff: {high_diff}")
        print(f"Low contrast color diff: {low_diff}")

        assert high_diff > low_diff, f"High contrast colors should be more different: {high_diff} vs {low_diff}"

    def test_inverse_video_handling(self):
        """Inverse video should be handled by flipping fg/bg."""
        # Normal: white fg, black bg
        normal_style = self.create_mock_style(fg_rgb=(255, 255, 255), bg_rgb=(0, 0, 0), reverse=False)

        # Inverse: black fg, white bg, but with reverse=True (so effectively white fg, black bg)
        inverse_style = self.create_mock_style(fg_rgb=(0, 0, 0), bg_rgb=(255, 255, 255), reverse=True)

        cell1 = (normal_style, "A")
        cell2 = (inverse_style, "A")

        diff = self.renderer._visual_difference(cell1, cell2)
        print(f"Normal vs inverse (should be same): {diff}")

        # Should be identical after inverse handling
        assert diff == 0.0, f"Inverse video should be handled properly, got {diff}"

    def test_empty_vs_content_cells(self):
        """Empty cells vs content cells should show difference."""
        # Empty cell (space character, no colors)
        empty_style = self.create_mock_style()
        empty_cell = (empty_style, " ")

        # Content cell
        content_style = self.create_mock_style(fg_rgb=(255, 255, 255), bg_rgb=(0, 0, 0))
        content_cell = (content_style, "A")

        diff = self.renderer._visual_difference(empty_cell, content_cell)
        print(f"Empty vs content: {diff}")

        assert diff > 0.0, f"Empty vs content should show difference, got {diff}"

    def test_bright_blue_vs_brown(self):
        """Bright blue vs brown should show large perceptual difference."""
        blue_style = self.create_mock_style(fg_rgb=(0, 0, 255), bg_rgb=(0, 0, 0))
        brown_style = self.create_mock_style(fg_rgb=(139, 69, 19), bg_rgb=(0, 0, 0))

        blue_cell = (blue_style, "A")
        brown_cell = (brown_style, "A")

        diff = self.renderer._visual_difference(blue_cell, brown_cell)
        print(f"Bright blue vs brown: {diff}")

        # Should be significant difference (LAB Delta E ~158, but averaged with bg)
        assert diff > 30.0, f"Bright blue vs brown should be very different, got {diff}"

    def test_similar_video_grays(self):
        """Similar video grays should show small difference."""
        gray1_style = self.create_mock_style(fg_rgb=(136, 147, 158), bg_rgb=(0, 0, 0))
        gray2_style = self.create_mock_style(fg_rgb=(130, 141, 151), bg_rgb=(0, 0, 0))

        cell1 = (gray1_style, " ")
        cell2 = (gray2_style, " ")

        diff = self.renderer._visual_difference(cell1, cell2)
        print(f"Similar video grays: {diff}")

        # Should be small difference (LAB Delta E ~2.4)
        assert diff < 5.0, f"Similar grays should be small difference, got {diff}"


if __name__ == "__main__":
    test = TestVisualDifference()
    test.setup_method()

    print("=== Testing Visual Difference Algorithm ===")
    test.test_identical_cells_return_zero()
    test.test_different_characters_same_colors()
    test.test_same_character_different_colors()
    test.test_high_contrast_vs_low_contrast_colors()
    test.test_inverse_video_handling()
    test.test_empty_vs_content_cells()
    test.test_bright_blue_vs_brown()
    test.test_similar_video_grays()
    print("All tests passed!")
