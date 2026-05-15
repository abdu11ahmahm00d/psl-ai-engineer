"""
Creates a realistic handwritten-style legal document image for testing OCR.
Uses PIL to simulate handwriting with various fonts and noise.
"""
from PIL import Image, ImageDraw, ImageFont
import random
import os

HANDWRITING_TEXTS = [
    "SETTLEMENT AGREEMENT",
    "",
    "This agreement is made on the 15th day of March, 2024",
    "between the following parties:",
    "",
    "Party A: John Michael Davidson",
    "Party B: Williams & Associates LLC",
    "",
    "WHEREAS, the parties wish to resolve all outstanding",
    "disputes arising from the contract dated January 10, 2023;",
    "",
    "NOW THEREFORE, in consideration of the mutual covenants",
    "contained herein, the parties agree as follows:",
    "",
    "1. Party A shall pay Party B the sum of $125,000",
    "   (One Hundred Twenty-Five Thousand Dollars)",
    "",
    "2. Payment shall be made in two equal installments:",
    "   - First installment: $62,500 by April 1, 2024",
    "   - Second installment: $62,500 by July 1, 2024",
    "",
    "3. Upon full payment, Party B shall release all claims",
    "   against Party A related to the aforementioned contract.",
    "",
    "4. This agreement shall be governed by the laws of",
    "   the State of California.",
    "",
    "5. Any disputes shall be resolved through mediation",
    "   before either party may pursue litigation.",
    "",
    "IN WITNESS WHEREOF, the parties have executed this",
    "agreement as of the date first written above.",
    "",
    "_______________________     _______________________",
    "John M. Davidson              Sarah Williams",
    "Authorized Signature          Authorized Signature",
    "",
    "Date: March 15, 2024          Date: March 15, 2024",
]


def create_handwritten_document(output_path: str, width: int = 1700, height: int = 2200):
    bg_color = (245, 240, 230)
    ink_color = (30, 30, 60)
    
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    
    # Add subtle paper texture noise
    for y in range(0, height, 2):
        for x in range(0, width, 2):
            if random.random() < 0.03:
                noise_val = random.randint(-8, 8)
                r = max(0, min(255, bg_color[0] + noise_val))
                g = max(0, min(255, bg_color[1] + noise_val))
                b = max(0, min(255, bg_color[2] + noise_val))
                draw.point((x, y), fill=(int(r), int(g), int(b)))
    
    # Add faint horizontal lines (like lined paper)
    line_color = (210, 205, 195)
    for y in range(80, height - 40, 35):
        draw.line([(40, y), (width - 40, y)], fill=line_color, width=1)
    
    # Try to use a handwriting-style font, fall back to default
    font_sizes = {"title": 28, "body": 22, "small": 18}
    fonts = {}
    
    font_candidates = [
        "C:/Windows/Fonts/COMIC.TTF",
        "C:/Windows/Fonts/BRUSHSCI.TTF",
        "C:/Windows/Fonts/arial.ttf",
    ]
    
    loaded_font = None
    for fc in font_candidates:
        if os.path.exists(fc):
            try:
                loaded_font = ImageFont.truetype(fc, font_sizes["body"])
                title_font = ImageFont.truetype(fc, font_sizes["title"])
                small_font = ImageFont.truetype(fc, font_sizes["small"])
                fonts = {"title": title_font, "body": loaded_font, "small": small_font}
                break
            except Exception:
                continue
    
    if not fonts:
        fonts = {
            "title": ImageFont.load_default(),
            "body": ImageFont.load_default(),
            "small": ImageFont.load_default(),
        }
    
    # Draw text with slight position variation (simulating handwriting)
    y_pos = 60
    x_base = 60
    
    for line in HANDWRITING_TEXTS:
        if not line:
            y_pos += 20
            continue
        
        is_title = line == "SETTLEMENT AGREEMENT"
        font_key = "title" if is_title else ("small" if line.startswith("   ") else "body")
        font = fonts.get(font_key, fonts["body"])
        
        # Slight random offset for each line (handwriting variation)
        x_offset = x_base + random.randint(-3, 3)
        y_offset = y_pos + random.randint(-2, 2)
        
        # Slight color variation in ink
        ink_r = ink_color[0] + random.randint(-5, 5)
        ink_g = ink_color[1] + random.randint(-5, 5)
        ink_b = ink_color[2] + random.randint(-5, 5)
        line_color_ink = (max(0, ink_r), max(0, ink_g), max(0, ink_b))
        
        draw.text((x_offset, y_offset), line, fill=line_color_ink, font=font)
        
        y_pos += 35
    
    # Add slight rotation/warp effect by adding noise near text
    for _ in range(200):
        x = random.randint(50, width - 50)
        y = random.randint(50, height - 50)
        if random.random() < 0.15:
            draw.point((x, y), fill=(random.randint(20, 50), random.randint(20, 50), random.randint(40, 70)))
    
    # Add a stamp-like circle in the corner
    stamp_x, stamp_y = width - 200, height - 200
    draw.ellipse(
        [(stamp_x, stamp_y), (stamp_x + 150, stamp_y + 150)],
        outline=(180, 40, 40),
        width=3,
    )
    draw.ellipse(
        [(stamp_x + 8, stamp_y + 8), (stamp_x + 142, stamp_y + 142)],
        outline=(180, 40, 40),
        width=2,
    )
    stamp_font = fonts.get("small", fonts["body"])
    draw.text((stamp_x + 25, stamp_y + 55), "RECEIVED", fill=(180, 40, 40), font=stamp_font)
    draw.text((stamp_x + 30, stamp_y + 80), "MAR 18 2024", fill=(180, 40, 40), font=stamp_font)
    
    # Add signature scribble lines
    sig_y = height - 340
    for sig_x_start in [x_base, x_base + 500]:
        for _ in range(8):
            sx = sig_x_start + random.randint(0, 180)
            sy = sig_y + random.randint(-5, 5)
            ex = sig_x_start + random.randint(20, 200)
            ey = sig_y + random.randint(-3, 3)
            draw.line([(sx, sy), (ex, ey)], fill=(20, 20, 50), width=1)
    
    img.save(output_path, "PNG", quality=95)
    print(f"Handwritten document saved to: {output_path}")


if __name__ == "__main__":
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")
    os.makedirs(output_dir, exist_ok=True)
    create_handwritten_document(os.path.join(output_dir, "handwritten_settlement_scan.png"))
