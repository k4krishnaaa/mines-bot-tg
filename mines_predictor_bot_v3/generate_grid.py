
from PIL import Image, ImageDraw, ImageFilter
from pathlib import Path
import random

BG_COLOR = (12, 29, 35)       # dark bluish overall background
TILE_COLOR = (47, 64, 72)     # tile color
BORDER_COLOR = (60, 80, 90)   # border
SHADOW = (6, 18, 24)          # shadow color

def rounded_rectangle(draw, xy, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)

def make_prediction_image(safe_indices, out_path, rows=5, cols=5, size=(700,700), padding=28):
    W, H = size
    img = Image.new("RGBA", (W, H), BG_COLOR + (255,))
    draw = ImageDraw.Draw(img)

    gap = int(W * 0.02)
    tile_size = int((W - 2*padding - (cols-1)*gap) / cols)
    radius = int(tile_size * 0.16)

    total_w = cols*tile_size + (cols-1)*gap
    total_h = rows*tile_size + (rows-1)*gap
    start_x = (W - total_w) // 2
    start_y = (H - total_h) // 2

    # Load diamond icon and scale
    diamond_path = Path(__file__).parent / "assets" / "diamond.png"
    diamond = Image.open(diamond_path).convert("RGBA")
    icon_size = int(tile_size * 0.78)
    diamond = diamond.resize((icon_size, icon_size), Image.LANCZOS)

    # draw tiles with subtle drop shadows (to match provided grid)
    for r in range(rows):
        for c in range(cols):
            x = start_x + c*(tile_size + gap)
            y = start_y + r*(tile_size + gap)
            # shadow
            shadow_box = (x+6, y+8, x+tile_size+6, y+tile_size+8)
            rounded_rectangle(draw, shadow_box, radius, SHADOW)
            # tile
            rect = (x, y, x+tile_size, y+tile_size)
            rounded_rectangle(draw, rect, radius, TILE_COLOR, outline=BORDER_COLOR, width=2)

    # paste diamonds (safe spots)
    for idx in safe_indices:
        r = idx // cols
        c = idx % cols
        x = start_x + c*(tile_size + gap)
        y = start_y + r*(tile_size + gap)
        px = x + (tile_size - icon_size)//2
        py = y + (tile_size - icon_size)//2
        img.alpha_composite(diamond, (px, py))

    # finalize
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out_path, format="PNG")
    return str(out_path)

if __name__ == "__main__":
    # quick test create
    indices = sorted(random.sample(range(25), 8))
    make_prediction_image(indices, "out_test.png")
