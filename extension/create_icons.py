#!/usr/bin/env python3
"""
Simple script to create extension icons
Run this to generate the required icon files
"""

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Please install Pillow: pip install Pillow")
    exit(1)

import os
import sys
from pathlib import Path

# Create images directory
images_dir = Path(__file__).parent / "images"
images_dir.mkdir(exist_ok=True)

# Define icon sizes
sizes = [16, 48, 128]

# Color: Light blue
color = (74, 144, 226)  # RGB for #4a90e2

for size in sizes:
    # Create new image with solid color background
    img = Image.new('RGBA', (size, size), color)

    # Add a simple book icon (white)
    draw = ImageDraw.Draw(img)

    # Draw a simple book shape
    margin = size // 8
    book_color = (255, 255, 255)  # White

    # Book spine
    draw.rectangle(
        [margin, margin, size - margin, size - margin],
        outline=book_color,
        width=max(1, size // 16)
    )

    # Book pages (vertical lines)
    mid = size // 2
    draw.line([(mid, margin), (mid, size - margin)], fill=book_color, width=max(1, size // 16))

    # Save icon
    filename = images_dir / f"icon{size}.png"
    img.save(filename)
    sys.stdout.write(f"Created {filename}\n")
    sys.stdout.flush()

sys.stdout.write(f"\nAll icons created successfully!\n")
sys.stdout.write(f"Icons saved to: {images_dir}\n")
sys.stdout.flush()
