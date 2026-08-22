#!/usr/bin/env python3
"""Generate the GrowHall favicon set: an open book with a growing sprout
in the brand purple. Renders a high-res master with PIL and downsamples for
crisp anti-aliasing, then writes favicon.ico (multi-size) + PNGs."""

from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).parent / "static" / "images"
OUT.mkdir(parents=True, exist_ok=True)

SS = 2048  # supersample master size

# Brand palette
TOP = (157, 132, 255)   # --primary-light  #9d84ff
BOT = (107, 82, 204)    # --primary-dark   #6b52cc
WHITE = (255, 255, 255)
PAGE_SHADE = (226, 220, 250)
LEAF = (74, 201, 126)   # fresh green
LEAF_DK = (46, 170, 100)
STEM = (56, 180, 108)


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def make_master():
    img = Image.new("RGBA", (SS, SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Vertical gradient background painted into a rounded-rect mask
    grad = Image.new("RGB", (1, SS))
    for y in range(SS):
        grad.putpixel((0, y), lerp(TOP, BOT, y / (SS - 1)))
    grad = grad.resize((SS, SS))

    mask = Image.new("L", (SS, SS), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, SS - 1, SS - 1], radius=int(SS * 0.22), fill=255
    )
    img.paste(grad, (0, 0), mask)
    d = ImageDraw.Draw(img)

    def P(x, y):
        return (x * SS, y * SS)

    # ---- Open book (two pages meeting at a center spine) ----
    # left page (outer edge droops lower than the raised center crease)
    left = [P(0.135, 0.470), P(0.500, 0.430), P(0.500, 0.745), P(0.135, 0.690)]
    right = [P(0.865, 0.470), P(0.500, 0.430), P(0.500, 0.745), P(0.865, 0.690)]
    d.polygon(left, fill=WHITE)
    d.polygon(right, fill=WHITE)

    # subtle page shading near the spine for depth
    d.polygon([P(0.500, 0.430), P(0.560, 0.437), P(0.560, 0.740), P(0.500, 0.745)],
              fill=PAGE_SHADE)
    d.polygon([P(0.500, 0.430), P(0.440, 0.437), P(0.440, 0.740), P(0.500, 0.745)],
              fill=PAGE_SHADE)

    lw = int(SS * 0.012)
    # spine
    d.line([P(0.500, 0.418), P(0.500, 0.752)], fill=BOT, width=lw)

    # page text lines
    tl = int(SS * 0.009)
    for i, ty in enumerate((0.515, 0.560, 0.605, 0.650)):
        inset = 0.02 * i
        d.line([P(0.190 + inset, ty + 0.010), P(0.470, ty)], fill=(196, 188, 232), width=tl)
        d.line([P(0.530, ty), P(0.810 - inset, ty + 0.010)], fill=(196, 188, 232), width=tl)

    # ---- Sprout growing out of the book ----
    # stem
    d.line([P(0.500, 0.470), P(0.500, 0.245)], fill=STEM, width=int(SS * 0.022))

    def leaf(cx, cy, w, h, ang, color):
        """Draw a leaf as an ellipse rotated by ang (degrees) around (cx,cy)."""
        import math
        layer = Image.new("RGBA", (SS, SS), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        ld.ellipse([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], fill=color)
        layer = layer.rotate(ang, center=(cx, cy), resample=Image.BICUBIC)
        img.alpha_composite(layer)

    # right leaf, then left leaf, then a top bud
    leaf(0.605 * SS, 0.300 * SS, 0.190 * SS, 0.115 * SS, -32, LEAF)
    leaf(0.395 * SS, 0.320 * SS, 0.190 * SS, 0.115 * SS, 32, LEAF_DK)
    leaf(0.500 * SS, 0.232 * SS, 0.100 * SS, 0.150 * SS, 0, LEAF)

    return img


def main():
    master = make_master()
    master.save(OUT / "favicon-512.png")

    # apple touch icon on an opaque bg (iOS ignores transparency/rounding)
    apple = Image.new("RGBA", (SS, SS), (0, 0, 0, 0))
    apple.alpha_composite(master)
    apple.convert("RGB").resize((180, 180), Image.LANCZOS).save(OUT / "apple-touch-icon.png")

    for s in (16, 32, 48, 180, 192):
        master.resize((s, s), Image.LANCZOS).save(OUT / f"favicon-{s}.png")

    ico_sizes = [16, 24, 32, 48, 64, 256]
    master.resize((256, 256), Image.LANCZOS).save(
        OUT / "favicon.ico", sizes=[(s, s) for s in ico_sizes]
    )

    print("Wrote:", *(p.name for p in sorted(OUT.glob("favicon*")) ), "apple-touch-icon.png")


if __name__ == "__main__":
    main()
