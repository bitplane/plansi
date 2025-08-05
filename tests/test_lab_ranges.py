"""Test LAB Delta E ranges for known color pairs to understand scaling."""

from plansi.core.terminal_render import TerminalRenderer


def test_lab_delta_e_ranges():
    """Test LAB Delta E values for known color pairs."""
    renderer = TerminalRenderer(width=80, height=24)

    # Test color pairs with expected perceptual differences
    test_pairs = [
        # (color1, color2, description)
        ((0, 0, 0), (255, 255, 255), "Black to White (max contrast)"),
        ((255, 0, 0), (0, 255, 0), "Red to Green (very different hues)"),
        ((0, 0, 255), (139, 69, 19), "Bright Blue to Brown (very different)"),
        ((128, 128, 128), (130, 130, 130), "Similar grays (barely perceptible)"),
        ((100, 100, 100), (150, 150, 150), "Gray to lighter gray (noticeable)"),
        ((255, 0, 0), (255, 100, 100), "Red to pink (same hue, different saturation)"),
        ((0, 0, 255), (0, 100, 255), "Blue to lighter blue (same hue)"),
        ((128, 144, 160), (0, 0, 0), "Light blue-gray to black (video colors)"),
        ((136, 147, 158), (130, 141, 151), "Similar video grays"),
    ]

    print("=== LAB Delta E Test Results ===")
    print("Color1 RGB          Color2 RGB          Delta E   Description")
    print("-" * 80)

    for color1, color2, desc in test_pairs:
        delta_e = renderer._color_distance(color1, color2)
        print(f"{str(color1):20} {str(color2):20} {delta_e:8.2f}  {desc}")

    print()
    print("=== LAB Color Space Conversions ===")
    key_colors = [
        ((0, 0, 0), "Black"),
        ((255, 255, 255), "White"),
        ((255, 0, 0), "Red"),
        ((0, 255, 0), "Green"),
        ((0, 0, 255), "Blue"),
        ((128, 128, 128), "Gray"),
        ((136, 147, 158), "Video blue-gray"),
    ]

    print("RGB Color           LAB Color                   Description")
    print("-" * 70)
    for rgb, desc in key_colors:
        lab = renderer._rgb_to_lab(rgb)
        print(f"{str(rgb):20} {lab[0]:6.1f} {lab[1]:6.1f} {lab[2]:6.1f}        {desc}")


if __name__ == "__main__":
    test_lab_delta_e_ranges()
