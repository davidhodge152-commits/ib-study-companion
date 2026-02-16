"""One-time script to generate PWA icons using Pillow (pure Python, no cairo)."""
from PIL import Image, ImageDraw, ImageFont
import math

def create_icon(size):
    """Create an indigo icon with a book/cap glyph."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded rectangle background
    radius = size // 5
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=(79, 70, 229))

    cx, cy = size // 2, size // 2 - size // 20
    s = size / 512  # scale factor

    # Draw graduation cap (diamond shape)
    cap_points = [
        (cx, cy - 110 * s),
        (cx - 80 * s, cy - 70 * s),
        (cx, cy - 30 * s),
        (cx + 80 * s, cy - 70 * s),
    ]
    draw.polygon(cap_points, fill='white')

    # Cap top block
    draw.rectangle([cx - 5 * s, cy - 120 * s, cx + 5 * s, cy - 110 * s], fill='white')

    # Tassel line
    draw.line([(cx + 80 * s, cy - 70 * s), (cx + 80 * s, cy - 35 * s)], fill='white', width=max(1, int(3 * s)))
    draw.ellipse([cx + 75 * s, cy - 37 * s, cx + 85 * s, cy - 27 * s], fill='white')

    # Draw open book
    book_points_left = []
    book_points_right = []
    for i in range(20):
        t = i / 19
        # Left page curve
        x = cx - 120 * s + t * 120 * s
        y_top = cy + 20 * s - 70 * s * (1 - (2 * t - 1) ** 2)
        book_points_left.append((x, y_top))

    for i in range(20):
        t = i / 19
        x = cx + t * 120 * s
        y_top = cy + 20 * s - 70 * s * (1 - (2 * t - 1) ** 2)
        book_points_right.append((x, y_top))

    # Simplified book shape
    book_left = [
        (cx - 120 * s, cy + 80 * s),
        (cx - 120 * s, cy + 20 * s),
        (cx - 80 * s, cy - 10 * s),
        (cx - 40 * s, cy - 30 * s),
        (cx, cy - 50 * s),
        (cx, cy + 80 * s),
    ]
    book_right = [
        (cx, cy + 80 * s),
        (cx, cy - 50 * s),
        (cx + 40 * s, cy - 30 * s),
        (cx + 80 * s, cy - 10 * s),
        (cx + 120 * s, cy + 20 * s),
        (cx + 120 * s, cy + 80 * s),
    ]

    draw.polygon(book_left, fill=(255, 255, 255, 240))
    draw.polygon(book_right, fill=(255, 255, 255, 240))

    # Book spine
    draw.line([(cx, cy - 50 * s), (cx, cy + 80 * s)], fill=(79, 70, 229, 80), width=max(1, int(3 * s)))

    # Page lines
    for offset in [0, 20, 40]:
        y = cy + offset * s
        draw.line([(cx - 90 * s, y), (cx - 20 * s, y - 10 * s)], fill=(79, 70, 229, 50), width=max(1, int(2 * s)))
        draw.line([(cx + 20 * s, y - 10 * s), (cx + 90 * s, y)], fill=(79, 70, 229, 50), width=max(1, int(2 * s)))

    # "IB" text at bottom
    try:
        font_size = int(44 * s)
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
    except (IOError, OSError):
        font = ImageFont.load_default()

    text = "IB STUDY"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text((cx - tw // 2, cy + 100 * s), text, fill=(255, 255, 255, 230), font=font)

    return img.convert('RGB')


if __name__ == '__main__':
    for sz in [512, 192]:
        img = create_icon(sz)
        img.save(f'static/icons/icon-{sz}.png')
        print(f'Created icon-{sz}.png')

    # Maskable: same icon
    img = create_icon(512)
    img.save('static/icons/icon-maskable-512.png')
    print('Created icon-maskable-512.png')
    print('Done!')
