"""Analyze colors from the top row of the video output."""

import re
from plansi.core.terminal_render import TerminalRenderer


def extract_rgb_from_ansi(ansi_text):
    """Extract RGB values from ANSI escape sequences."""
    # Pattern to match 38;2;r;g;b (foreground) and 48;2;r;g;b (background)
    fg_pattern = r"\x1b\[38;2;(\d+);(\d+);(\d+)m"
    bg_pattern = r"\x1b\[48;2;(\d+);(\d+);(\d+)m"

    fg_colors = []
    bg_colors = []

    for match in re.finditer(fg_pattern, ansi_text):
        r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
        fg_colors.append((r, g, b))

    for match in re.finditer(bg_pattern, ansi_text):
        r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
        bg_colors.append((r, g, b))

    return fg_colors, bg_colors


def analyze_video_colors():
    """Analyze colors from video output and their perceptual differences."""
    import subprocess

    # Capture the first line from tmux
    result = subprocess.run(["tmux", "capture-pane", "-t", "main:0.1", "-p", "-e"], capture_output=True, text=True)
    first_line = result.stdout.split("\n")[0] if result.stdout else ""

    # Extract colors
    fg_colors, bg_colors = extract_rgb_from_ansi(first_line)

    print("=== Video Colors Analysis ===")
    print(f"Found {len(fg_colors)} foreground colors and {len(bg_colors)} background colors")
    print()

    renderer = TerminalRenderer(width=80, height=24)

    print("Foreground Colors:")
    for i, color in enumerate(fg_colors[:10]):  # First 10 colors
        print(f"  FG{i:2d}: {color}")

    print("\nBackground Colors:")
    for i, color in enumerate(bg_colors[:10]):  # First 10 colors
        print(f"  BG{i:2d}: {color}")

    print("\n=== Perceptual Differences Between Adjacent Colors ===")

    # Compare adjacent foreground colors
    print("Adjacent FG color differences:")
    for i in range(min(len(fg_colors) - 1, 9)):
        color1, color2 = fg_colors[i], fg_colors[i + 1]
        diff = renderer._color_distance(color1, color2)
        perceptual_diff = min(diff / 200.0, 1.0) * 100.0
        print(f"  FG{i:2d} {color1} -> FG{i+1:2d} {color2}: LAB ΔE={diff:6.2f}, Perceptual={perceptual_diff:5.2f}%")

    print("\nAdjacent BG color differences:")
    for i in range(min(len(bg_colors) - 1, 9)):
        color1, color2 = bg_colors[i], bg_colors[i + 1]
        diff = renderer._color_distance(color1, color2)
        perceptual_diff = min(diff / 200.0, 1.0) * 100.0
        print(f"  BG{i:2d} {color1} -> BG{i+1:2d} {color2}: LAB ΔE={diff:6.2f}, Perceptual={perceptual_diff:5.2f}%")

    print("\n=== Threshold Analysis ===")
    print("Current threshold: 5.0%")
    print("Colors that would trigger differential update (>5.0%):")

    trigger_count = 0
    for i in range(min(len(fg_colors) - 1, 9)):
        color1, color2 = fg_colors[i], fg_colors[i + 1]
        diff = renderer._color_distance(color1, color2)
        perceptual_diff = min(diff / 200.0, 1.0) * 100.0
        if perceptual_diff > 5.0:
            print(f"  ✓ FG{i} -> FG{i+1}: {perceptual_diff:.2f}%")
            trigger_count += 1

    for i in range(min(len(bg_colors) - 1, 9)):
        color1, color2 = bg_colors[i], bg_colors[i + 1]
        diff = renderer._color_distance(color1, color2)
        perceptual_diff = min(diff / 200.0, 1.0) * 100.0
        if perceptual_diff > 5.0:
            print(f"  ✓ BG{i} -> BG{i+1}: {perceptual_diff:.2f}%")
            trigger_count += 1

    print(f"\nTotal colors that would trigger update: {trigger_count}")


if __name__ == "__main__":
    analyze_video_colors()
