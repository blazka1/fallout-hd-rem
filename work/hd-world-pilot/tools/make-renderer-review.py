"""Factual comparisons: byte-exact crops from SDL screenshots, labels outside.

No resampling, brightness changes, asset changes or runtime changes.
"""
from pathlib import Path
import argparse
import hashlib
import json
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--new-run", type=Path, default=ROOT / "build/hd-world-pilot/preview/perf-light-v4")
args = parser.parse_args()
old = ROOT / "build/hd-world-pilot/preview/full-base-v3"
new = args.new_run.resolve()
output = new / "qa"
output.mkdir(exist_ok=True)
box = (1050, 250, 1600, 650)
font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 25)
small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 18)
reports = []
for stem in ("entrance", "cave-24097"):
    canvas = Image.new("RGB", (1706, 490), (24, 29, 28))
    draw = ImageDraw.Draw(canvas)
    entries = ((new / (stem + "-classic.png"), "Оригинал"),
               (old / (stem + "-hd.png"), "HD v3: прежний свет"),
               (new / (stem + "-hd.png"), "HD v4: новый свет"))
    inputs = []
    for index, (path, label) in enumerate(entries):
        x = 8 + index * 566
        with Image.open(path) as screenshot:
            crop = screenshot.convert("RGB").crop(box)
            canvas.paste(crop, (x, 48))
        draw.text((x, 10), label, font=font, fill=(222, 226, 215))
        assert canvas.crop((x, 48, x + 550, 448)).tobytes() == crop.tobytes()
        inputs.append({"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    draw.text((8, 458), "Кадры SDL, одинаковый фрагмент 1050,250–1600,650; пиксели кропов сохранены 1:1.", font=small, fill=(180, 190, 180))
    target = output / (stem + "-original-v3-v4.png")
    canvas.save(target)
    reports.append({"output": str(target), "source_rect": list(box), "crop_pixels_exact": True, "inputs": inputs})
    print(target)
canvas = Image.new("RGB", (2272, 490), (24, 29, 28))
draw = ImageDraw.Draw(canvas)
for index, (name, label) in enumerate((("normal", "Обычный свет"), ("dark25", "Затемнение: 25%"), ("white50", "Вспышка: 50%"), ("white", "Белый: 252/255"))):
    x = 8 + index * 566
    path = new / ("fade-" + name + "-hd.png")
    with Image.open(path) as screenshot:
        crop = screenshot.convert("RGB").crop(box)
        canvas.paste(crop, (x, 48))
    draw.text((x, 10), label, font=font, fill=(222, 226, 215))
    assert canvas.crop((x, 48, x + 550, 448)).tobytes() == crop.tobytes()
draw.text((8, 458), "Реальные промежуточные кадры SDL; тот же фрагмент и неизменённые пиксели.", font=small, fill=(180, 190, 180))
target = output / "fade-actual-frames.png"
canvas.save(target)
print(target)
(output / "comparison-provenance.json").write_text(json.dumps({"comparisons": reports, "fade_contact": str(target)}, indent=2), encoding="utf-8")
