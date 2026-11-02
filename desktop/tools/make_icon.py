"""Draws Open RAG's app icon in the AI Engineering Arena style: a tilted tomato sticker with an ink outline and a
hard shadow, holding a document and a sun-yellow magnifying glass.

Every size is drawn at 8x and scaled down, so small sizes in the taskbar stay sharp.
Run from the repo root:  python desktop/tools/make_icon.py
"""

from pathlib import Path

from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parent.parent / "src" / "OpenRag.App" / "Assets"
SIZES = [16, 20, 24, 32, 40, 48, 64, 96, 128, 256]
SUPERSAMPLE = 8
INK = (0x17, 0x18, 0x3A, 255)
TOMATO = (0xFF, 0x6B, 0x4A, 255)
SUN = (0xFF, 0xC8, 0x3D, 255)
COBALT = (0x3F, 0x5B, 0xFF, 255)
WHITE = (255, 255, 255, 255)
TILT = -6


def sticker(n: int, small: bool) -> Image.Image:
    """The tomato plate with its ink outline and offset shadow, drawn upright (it is rotated afterwards)."""
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    edge = n * (0.05 if small else 0.035)
    shadow = n * 0.05
    box = (n * 0.12, n * 0.12, n * 0.84, n * 0.84)
    radius = n * 0.17
    d.rounded_rectangle((box[0] + shadow, box[1] + shadow, box[2] + shadow, box[3] + shadow), radius=radius, fill=INK)
    d.rounded_rectangle(box, radius=radius, fill=TOMATO, outline=INK, width=int(edge))

    # A white page with an ink outline.
    page = (n * 0.27, n * 0.24, n * 0.6, n * 0.7)
    d.rounded_rectangle(page, radius=n * 0.05, fill=WHITE, outline=INK, width=int(edge * 0.8))
    if not small:
        for i, width in enumerate((0.2, 0.16, 0.19)):
            y = page[1] + n * (0.08 + i * 0.085)
            d.rounded_rectangle((page[0] + n * 0.05, y, page[0] + n * (0.05 + width), y + n * 0.035), radius=n * 0.017,
                                fill=COBALT)

    # The magnifying glass: a sun lens with an ink ring and handle.
    cx, cy, r = n * 0.6, n * 0.6, n * (0.13 if not small else 0.15)
    ring = n * (0.05 if not small else 0.065)
    handle_end = (cx + r + n * 0.13, cy + r + n * 0.13)
    d.line((cx + r * 0.6, cy + r * 0.6, *handle_end), fill=INK, width=int(ring * 1.8))
    d.ellipse((cx - r - ring, cy - r - ring, cx + r + ring, cy + r + ring), fill=INK)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=SUN)
    return img


def draw(size: int) -> Image.Image:
    n = size * SUPERSAMPLE
    small = size <= 24
    img = sticker(n, small).rotate(TILT, resample=Image.BICUBIC, center=(n / 2, n / 2))
    return img.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    ASSETS.mkdir(parents=True, exist_ok=True)
    images = [draw(s) for s in SIZES]
    images[-1].save(ASSETS / "OpenRag.ico", sizes=[(s, s) for s in SIZES], append_images=images[:-1])
    images[-1].save(ASSETS / "OpenRag.png")
    print(f"wrote {ASSETS / 'OpenRag.ico'}")
