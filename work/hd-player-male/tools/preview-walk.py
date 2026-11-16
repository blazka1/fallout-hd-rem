"""Compose review animations from registered HD walk PNGs; never edit the art.

Original and HD frames use the same CE bottom-center anchor. Cumulative FRM
movement is retained except uniform cycle travel, removed for a stationary
loop. The resulting residual bob is a review convention, not new engine data.
Pillow only lays out QA previews and encodes animations. No runtime writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageSequence

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/asset-pipeline"))
from fallout_assets import decode_frm

SOURCE = ROOT / "assets/reference/player-male-vault13/raw/art/critters/hmjmpsab.frm"
ORIGINALS = ROOT / "assets/reference/player-male-vault13/rgba/art/critters/hmjmpsab.frm"
NAMES = ("NE", "E", "SE", "SW", "W", "NW")
SCALE = 4
PANEL = (272, 352)
ANCHOR = (136, 280)
BACKGROUND = (31, 37, 38)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size):
    path = Path("C:/Windows/Fonts/segoeui.ttf")
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def positions(meta, directions):
    result = {}
    for d, frames in directions.items():
        total = [sum(f.shift_x for f in frames), sum(f.shift_y for f in frames)]
        cumulative = [0, 0]
        direction_positions = []
        for i, frame in enumerate(frames):
            if i:
                cumulative[0] += frame.shift_x
                cumulative[1] += frame.shift_y
            residual = [cumulative[k] - i * total[k] / len(frames) for k in (0, 1)]
            anchor = [ANCHOR[0] + round((meta["direction_x"][d] + residual[0]) * SCALE),
                      ANCHOR[1] + round((meta["direction_y"][d] + residual[1]) * SCALE)]
            xy = [anchor[0] - (frame.width // 2) * SCALE,
                  anchor[1] - (frame.height - 1) * SCALE]
            if min(xy) < 0 or xy[0] + frame.width * SCALE > PANEL[0] or xy[1] + frame.height * SCALE > PANEL[1]:
                raise ValueError(f"Preview canvas would clip direction {d}, frame {i}")
            direction_positions.append({"frame": i, "native_dimensions": [frame.width, frame.height],
                "source_frame_shift": [frame.shift_x, frame.shift_y],
                "direction_offset": [meta["direction_x"][d], meta["direction_y"][d]],
                "cumulative_shift_after_frame0": list(cumulative),
                "cycle_travel": total, "stationary_residual": residual,
                "anchor_px": anchor, "top_left_px": xy})
        result[d] = direction_positions
    return result


def panel(sprite, xy, label):
    canvas = Image.new("RGBA", PANEL, (*BACKGROUND, 255))
    canvas.alpha_composite(sprite, tuple(xy))
    draw = ImageDraw.Draw(canvas)
    draw.text((10, 7), label, font=font(16), fill=(214, 218, 206, 255))
    return canvas.convert("RGB")


def layout(panels, columns):
    rows = (len(panels) + columns - 1) // columns
    result = Image.new("RGB", (columns * PANEL[0], rows * PANEL[1]), BACKGROUND)
    for i, item in enumerate(panels):
        result.paste(item, ((i % columns) * PANEL[0], (i // columns) * PANEL[1]))
    return result


def fixed_palette(frames):
    # Train one palette from the complete cycle, then reuse it for every GIF.
    # This does not resize or alter the PNG/APNG artwork.
    strip = Image.new("RGB", (frames[0].width, sum(im.height for im in frames)))
    y = 0
    for im in frames:
        strip.paste(im, (0, y))
        y += im.height
    return strip.quantize(colors=256, method=Image.Quantize.MEDIANCUT)


def animation_info(path):
    with Image.open(path) as image:
        durations = []
        for frame in ImageSequence.Iterator(image):
            durations.append(frame.info.get("duration"))
        return {"frames": image.n_frames, "durations_ms": durations,
                "dimensions": list(image.size), "loop": image.info.get("loop")}


def gif_table_info(path):
    # Verify that the encoded GIF really uses a single global colour table.
    data = path.read_bytes()
    if data[:6] not in (b"GIF89a", b"GIF87a"):
        raise ValueError("Not a GIF")
    packed = data[10]
    global_table = bool(packed & 128)
    offset = 13 + (3 * 2 ** ((packed & 7) + 1) if global_table else 0)
    local_tables = 0
    image_count = 0

    def skip_blocks(pos):
        while data[pos]:
            pos += 1 + data[pos]
        return pos + 1

    while offset < len(data):
        tag = data[offset]
        offset += 1
        if tag == 0x3B:
            break
        if tag == 0x21:
            offset = skip_blocks(offset + 1)
        elif tag == 0x2C:
            packed = data[offset + 8]
            offset += 9
            image_count += 1
            if packed & 128:
                local_tables += 1
                offset += 3 * 2 ** ((packed & 7) + 1)
            offset = skip_blocks(offset + 1)  # LZW code size, then data blocks.
        else:
            raise ValueError(f"Unexpected GIF block: {tag:#x}")
    return {"global_colour_table": global_table, "local_colour_tables": local_tables,
            "image_descriptors": image_count}


def save_animation(output, name, frames, palette, duration):
    png = output / (name + ".png")
    gif = output / (name + ".gif")
    frames[0].save(png, save_all=True, append_images=frames[1:], duration=duration,
                   loop=0, disposal=0, blend=0, compress_level=9)
    quantized = [im.quantize(palette=palette, dither=Image.Dither.NONE) for im in frames]
    quantized[0].save(gif, save_all=True, append_images=quantized[1:], duration=duration,
                     loop=0, disposal=1, optimize=False, palette=palette.getpalette(),
                     include_color_table=False)
    outputs = []
    for path in (png, gif):
        qa = animation_info(path)
        if qa["frames"] != len(frames) or any(abs(float(ms) - duration) > 0.01 for ms in qa["durations_ms"]):
            raise ValueError(f"Encoded animation lost frame timing/count: {path}: {qa}")
        if path.suffix == ".gif":
            qa.update(gif_table_info(path))
            if not qa["global_colour_table"] or qa["local_colour_tables"]:
                raise ValueError("GIF did not keep a single global colour table")
        outputs.append({"file": path.name, "sha256": sha(path), "qa": qa,
                        "format": "full-colour APNG" if path.suffix == ".png" else "global-palette GIF"})
    return outputs


def transitions(frames):
    arrays = [np.asarray(im, dtype=np.int16) for im in frames]
    # Adjacent metrics include 7 -> 0; these diagnose, not certify, coherence.
    return [{"from": i, "to": (i + 1) % len(frames),
             "mean_absolute_rgb_delta": round(float(np.abs(a - arrays[(i + 1) % len(frames)]).mean()), 4)}
            for i, a in enumerate(arrays)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--directions", default="0,1,2,3,4,5", help="Comma-separated indices, e.g. 1 for first review")
    parser.add_argument("--variant", choices=("registered", "source-mask"), default="registered")
    args = parser.parse_args()
    selected = [int(v) for v in args.directions.split(",")]
    if len(set(selected)) != len(selected) or not selected or any(d not in range(6) for d in selected):
        parser.error("Choose unique direction indices 0..5")
    source_data = SOURCE.read_bytes()
    meta, directions = decode_frm(source_data)
    if meta["frame_count"] != 8 or meta["fps"] != 10:
        raise ValueError("Unexpected source walk timing")
    duration = 1000 // meta["fps"]
    placement = positions(meta, directions)
    source_records, hd_panels, original_panels = [], {}, {}
    for d in selected:
        hd_panels[d], original_panels[d] = [], []
        for f, frame in enumerate(directions[d]):
            path = args.input_root / f"d{d}" / f"{args.variant}-f{f:03}.png"
            original_path = ORIGINALS / f"d{d}-f{f:03}.png"
            with Image.open(path) as im:
                if im.mode != "RGBA" or im.size != (frame.width * SCALE, frame.height * SCALE):
                    raise ValueError(f"Registered frame geometry/alpha is wrong: {path}")
                hd = im.copy()
            with Image.open(original_path) as im:
                if im.size != (frame.width, frame.height):
                    raise ValueError("Original frame dimensions are wrong")
                original = im.convert("RGBA").resize(hd.size, Image.Resampling.NEAREST)
            xy = placement[d][f]["top_left_px"]
            hd_panels[d].append(panel(hd, xy, f"d{d} {NAMES[d]} | HD"))
            original_panels[d].append(panel(original, xy, f"d{d} {NAMES[d]} | Original x4"))
            source_records.append({"direction": d, "frame": f, "file": str(path.resolve()),
                                   "sha256": sha(path), "original_sha256": sha(original_path),
                                   "dimensions": list(hd.size), "placement": placement[d][f]})
    # Validate all input frames before creating any output.
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Choose a fresh preview directory: " + str(output))
    output.mkdir(parents=True, exist_ok=True)
    all_hd = [layout([hd_panels[d][f] for d in selected], min(3, len(selected))) for f in range(8)]
    all_original = [layout([original_panels[d][f] for d in selected], min(3, len(selected))) for f in range(8)]
    palette = fixed_palette(all_hd + all_original)
    outputs = []
    diagnostics = []
    for d in selected:
        outputs.extend(save_animation(output, f"d{d}-{NAMES[d].lower()}-walk", hd_panels[d], palette, duration))
        comparison = layout(original_panels[d] + hd_panels[d], 8)
        path = output / f"d{d}-{NAMES[d].lower()}-all-frames-comparison.png"
        comparison.save(path)
        outputs.append({"file": path.name, "sha256": sha(path), "format": "static PNG",
                        "rows": ["original frames 0..7", "registered HD frames 0..7"]})
        diagnostics.append({"direction": d, "hd_transitions": transitions(hd_panels[d]),
                            "original_transitions": transitions(original_panels[d]),
                            "unique_hd_frames": len({im.tobytes() for im in hd_panels[d]})})
    name = "six-directions-walk" if len(selected) == 6 else "selected-directions-walk"
    outputs.extend(save_animation(output, name, all_hd, palette, duration))
    outputs.extend(save_animation(output, name + "-original", all_original, palette, duration))
    still = output / (name + "-frame0.png")
    all_hd[0].save(still)
    outputs.append({"file": still.name, "sha256": sha(still), "format": "static PNG"})
    manifest = {"status": "animation review preview; not installed in CE", "source": str(SOURCE),
        "source_sha256": hashlib.sha256(source_data).hexdigest(), "directions": selected,
        "variant": args.variant, "frames_per_direction": 8, "fps": 10, "duration_per_frame_ms": duration,
        "full_cycle_ms": 8 * duration, "logical_to_hd_scale": SCALE,
        "registration": "CE bottom-center anchor and direction offset; cumulative shifts after frame0 minus frame_index/8 times summed full-cycle shifts. Uniform travel removed only for stationary QA playback; residual bob retained.",
        "registration_source": ["work/hd-world-pilot/fallout1-ce-main/src/game/object.cc:4688", "work/hd-world-pilot/fallout1-ce-main/src/game/anim.cc:2592"],
        "inputs": source_records, "outputs": outputs, "transition_diagnostics": diagnostics,
        "visual_review": "Required: inspect poses, costume texture consistency and last-to-first transition. Numeric transition deltas are not a quality pass.",
        "runtime_installed": False}
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "directions": selected, "source_frames": len(source_records),
                      "animations": sum(o["format"] != "static PNG" for o in outputs), "fps": 10}, ensure_ascii=False))


if __name__ == "__main__":
    main()
