"""Build a lossless review sheet from actual, unretouched SDL captures."""
from pathlib import Path
import hashlib
import json
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
before = ROOT / "build/hd-world-pilot/preview/perf-light-v4-final/entrance-hd.png"
after = ROOT / "build/hd-world-pilot/preview/vault-rust-v5/entrance-hd.png"
out = after.parent / "qa"
out.mkdir(exist_ok=True)
crop = (310, 0, 1230, 460)
canvas = Image.new("RGB", (1852, 504), "#111417")
draw = ImageDraw.Draw(canvas)
font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 23)
for x, path, label in ((4, before, "Before | previous pilot v4"),
                       (928, after, "After | rusty vault v5")):
    with Image.open(path) as frame:
        assert frame.size == (1920, 1080)
        canvas.paste(frame.crop(crop).convert("RGB"), (x, 40))
    draw.text((x + 8, 6), label, font=font, fill="#f4f4f4")
target = out / "vault-before-after.png"
canvas.save(target)
record = {
    "method": "Unmodified, same-scale crops of actual SDL captures; labels added outside pixels.",
    "crop_xyxy": crop,
    "inputs": [{"path": p.relative_to(ROOT).as_posix(),
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in (before, after)],
    "output": target.relative_to(ROOT).as_posix(),
    "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
}
(out / "vault-comparison.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
print(target)
