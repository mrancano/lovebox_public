from PIL import Image, ImageDraw, ImageFont
import textwrap
import os


WIDTH = 480
HEIGHT = 320
BACKGROUND = "white"
FOREGROUND = "black"

# Use a real TTF font on your system
DEFAULT_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def fit_text(draw, text, font_path, max_width, max_height):
    """
    Find the largest font size that fits inside the target area.
    """
    low = 10
    high = 300
    best = None

    while low <= high:
        size = (low + high) // 2
        font = ImageFont.truetype(font_path, size=size)

        # Estimate wrap width dynamically
        avg_char_width = sum(font.getbbox(c)[2] for c in "abcdefghijklmnopqrstuvwxyz") / 26
        wrap_width = max(1, int(max_width / avg_char_width))

        lines = textwrap.wrap(text, width=wrap_width)

        line_heights = []
        line_widths = []

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            line_widths.append(w)
            line_heights.append(h)

        total_height = sum(line_heights) + (len(lines) - 1) * int(size * 0.25)
        max_line_width = max(line_widths)

        if max_line_width <= max_width and total_height <= max_height:
            best = (font, lines, line_heights, total_height)
            low = size + 1
        else:
            high = size - 1

    return best


def text_to_png(text, output_path="output.png"):
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)

    padding = 24
    max_width = WIDTH - padding * 2
    max_height = HEIGHT - padding * 2

    result = fit_text(
        draw,
        text,
        DEFAULT_FONT,
        max_width,
        max_height
    )

    if result is None:
        raise ValueError("Text could not fit.")

    font, lines, line_heights, total_height = result

    spacing = int(font.size * 0.25)

    y = (HEIGHT - total_height) // 2

    for line, line_height in zip(lines, line_heights):
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]

        x = (WIDTH - line_width) // 2

        draw.text((x, y), line, fill=FOREGROUND, font=font)

        y += line_height + spacing

    image.save(output_path)
    return output_path


# Example usage
if __name__ == "__main__":
    text_to_png("Hello", "single_word.png")
    text_to_png(
        "This is a longer sentence that automatically scales and wraps nicely.",
        "sentence.png"
    )