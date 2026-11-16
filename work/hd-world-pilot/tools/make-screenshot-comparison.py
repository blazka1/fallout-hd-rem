"""QA contact sheet from unchanged SDL captures; never modifies game assets."""
from pathlib import Path
import argparse
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--directory', default='build/hd-world-pilot/preview/perf-light-v4-final')
parser.add_argument('--label', default='HD: исправленный свет и стены')
args = parser.parse_args()
directory = root / args.directory
box = (1050, 250, 1600, 650)
canvas = Image.new("RGB", (1124, 464), (24, 29, 28))
draw = ImageDraw.Draw(canvas)
font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 25)
for x, name, label in ((8, "entrance-classic.png", "Оригинал"),
                       (566, "entrance-hd.png", args.label)):
    with Image.open(directory / name) as screenshot:
        canvas.paste(screenshot.convert("RGB").crop(box), (x, 48))
    draw.text((x, 10), label, font=font, fill=(222, 226, 215))
canvas.save(directory / "detail-comparison.png")
print(directory / "detail-comparison.png")
