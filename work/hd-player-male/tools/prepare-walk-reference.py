"""Assemble unchanged original walk poses for ImageGen reference and motion QA.

Pillow is used only for reference enlargement, composition, GIF packaging.
No artwork is generated or painted and no game file is changed.
"""
from pathlib import Path
import hashlib
import json
import sys

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/asset-pipeline"))
from fallout_assets import decode_frm, palette_rgb

OUTPUT = ROOT / "assets/generated/player-male-vault13/walk-v1-20261112/reference"
SOURCE = ROOT / "assets/reference/player-male-vault13/raw/art/critters/hmjmpsab.frm"
PALETTE = ROOT / "assets/reference/player-male-vault13/raw/color.pal"
DIRECTIONS = ["NE", "E", "SE", "SW", "W", "NW"]
OUTPUT.mkdir(parents=True, exist_ok=True)


def save_image(path, image, **options):
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite: {path}")
    image.save(path, **options)


def rgba(frame, palette):
    pixels = bytearray()
    for index in frame.pixels:
        pixels.extend(palette[index * 3:index * 3 + 3])
        pixels.append(255 if index else 0)
    return Image.frombytes("RGBA", (frame.width, frame.height), bytes(pixels))


def main():
    data = SOURCE.read_bytes()
    meta, directions = decode_frm(data)
    assert meta["frame_count"] == 8 and len(directions) == 6 and meta["fps"] == 10
    palette = palette_rgb(PALETTE.read_bytes())
    images = {d: [rgba(frame, palette) for frame in frames] for d, frames in directions.items()}
    sheets = []
    for d, frames in directions.items():
        sheet = Image.new("RGBA", (1536, 1024))
        records = []
        for f, frame in enumerate(frames):
            cx, cy = (f % 4) * 384, (f // 4) * 512
            width, height = frame.width * 6, frame.height * 6
            # Every pixel is magnified exactly six times. No per-frame fit.
            x, y = cx + (384 - width) // 2, cy + 440 - height
            sprite = images[d][f].resize((width, height), Image.Resampling.NEAREST)
            sheet.alpha_composite(sprite, (x, y))
            records.append({"frame": f, "cell": [cx, cy, 384, 512],
                            "reference_rgba_rect": [x, y, width, height],
                            "source_dimensions": [frame.width, frame.height],
                            "source_frame_shift": [frame.shift_x, frame.shift_y],
                            "native_bottom_center_anchor": [frame.width // 2, frame.height - 1]})
        path = OUTPUT / f"d{d}-poses.png"
        save_image(path, sheet)
        sheets.append({"direction": d, "direction_name": DIRECTIONS[d], "file": path.name,
                       "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                       "direction_offset": [meta["direction_x"][d], meta["direction_y"][d]],
                       "scale": 6, "cells": records})

    # Native x4 viewing. Motion is the original cycle with mean travel removed,
    # suitable for a stationary comparison viewer, not a game movement rewrite.
    preview_frames = []
    summed = {d: [sum(f.shift_x for f in frames), sum(f.shift_y for f in frames)]
              for d, frames in directions.items()}
    cumulative = {d: [0, 0] for d in directions}
    preview_positions = []
    for f in range(8):
        preview = Image.new("RGB", (720, 640), (31, 37, 39))
        draw = ImageDraw.Draw(preview)
        positions = []
        for d, frames in directions.items():
            frame = frames[f]
            if f:
                cumulative[d][0] += frame.shift_x
                cumulative[d][1] += frame.shift_y
            residual = [cumulative[d][axis] - f * summed[d][axis] / 8 for axis in range(2)]
            col, row = d % 3, d // 3
            anchor_x = col * 240 + 120 + round((meta["direction_x"][d] + residual[0]) * 4)
            anchor_y = row * 320 + 292 + round((meta["direction_y"][d] + residual[1]) * 4)
            x, y = anchor_x - frame.width // 2 * 4, anchor_y - (frame.height - 1) * 4
            sprite = images[d][f].resize((frame.width * 4, frame.height * 4), Image.Resampling.NEAREST)
            preview.paste(sprite, (x, y), sprite)
            draw.text((col * 240 + 10, row * 320 + 8), f"d{d} {DIRECTIONS[d]}  frame {f}", fill=(211, 213, 200))
            positions.append({"direction": d, "frame": f, "residual_translation": residual,
                              "preview_xy": [x, y]})
        preview_frames.append(preview)
        preview_positions.append(positions)
    save_image(OUTPUT / "original-walk-six-directions.gif", preview_frames[0], save_all=True,
               append_images=preview_frames[1:], duration=100, loop=0, disposal=2)
    save_image(OUTPUT / "original-walk-six-directions-frame0.png", preview_frames[0])
    manifest = {"status": "unaltered original pose references", "source": str(SOURCE.relative_to(ROOT)).replace("\\", "/"),
                "source_sha256": hashlib.sha256(data).hexdigest(), "fps": 10, "frames_per_direction": 8,
                "directions": 6, "sheet_dimensions": [1536, 1024], "grid": [4, 2],
                "cell_dimensions": [384, 512], "source_scale": 6,
                "frame_order": "row-major 0,1,2,3 on top; 4,5,6,7 on bottom",
                "sheet_registration": "Visual bottom-center alignment only; originals unchanged; use source offsets for engine integration",
                "sheets": sheets, "cycle_travel_per_direction": summed,
                "preview": {"file": "original-walk-six-directions.gif", "scale": 4,
                            "registration": "CE-style bottom-center anchor and direction offsets; cumulative deltas minus uniform cycle travel for stationary viewer",
                            "frame_positions": preview_positions},
                "source_header": meta}
    manifest_path = OUTPUT / "manifest.json"
    if manifest_path.exists():
        raise FileExistsError(manifest_path)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"sheets": [str(OUTPUT / item["file"]) for item in sheets], "frames": 48,
                      "gif": str(OUTPUT / "original-walk-six-directions.gif")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
