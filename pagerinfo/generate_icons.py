"""
pagerinfo/generate_icons.py
Generates simple placeholder icons for the PWA.
Run once: python generate_icons.py

For a real icon, replace the generated PNGs in static/icons/ with your own.
Requires: pip install pillow
"""

from pathlib import Path

def make_icon(size: int, path: Path):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("❌ Pillow not installed. Run: pip install pillow")
        return

    img  = Image.new("RGBA", (size, size), (10, 10, 10, 255))
    draw = ImageDraw.Draw(img)

    margin = size // 8
    draw.rectangle([margin, margin, size - margin, size - margin],
                   fill=(232, 197, 71, 255))

    font_size = size // 3
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    text = "PI"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size - tw) // 2, (size - th) // 2 - margin // 4),
              text, fill=(10, 10, 10, 255), font=font)

    img.save(path)
    print(f"✅ Icon generated: {path}")


if __name__ == "__main__":
    icons_dir = Path("static/icons")
    icons_dir.mkdir(parents=True, exist_ok=True)
    make_icon(192, icons_dir / "icon-192.png")
    make_icon(512, icons_dir / "icon-512.png")
    make_icon(72,  icons_dir / "badge-72.png")
    print("\nReplace these with your own icons if desired.")
