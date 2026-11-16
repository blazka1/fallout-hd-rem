"""Inventory male jumpsuit art and prepare unchanged source pixels for review.

No artistic processing, GPU calls, engine edits, or runtime writes.
"""
from pathlib import Path
import hashlib
import json
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/asset-pipeline"))
from fallout_assets import Assets, decode_frm, export_frm, palette_rgb, png_chunk, png_indexed, write_bytes, write_json
import zlib

REF = ROOT / "assets/reference/player-male-vault13"
WORK = ROOT / "work/hd-player-male"
assets = Assets([ROOT / "FALLOUT (extract.me)/MASTER.DAT", ROOT / "FALLOUT (extract.me)/CRITTER.DAT"])
palette = palette_rgb(assets.read("color.pal"))
clips = {"hmjmpsaa.frm": "stand", "hmjmpsab.frm": "walk", "hmjmpsat.frm": "run"}
sources = ["color.pal", "art/critters/critters.lst"] + ["art/critters/" + n for n in clips]
records = assets.extract(sources, REF)
write_json(REF, "extraction.json", records)

inventory = []
for name in sorted(n for n in assets.index if n.startswith("art/critters/hmjmps")):
    data = assets.read(name)
    version, fps, action, count = struct.unpack(">I3H", data[:10])
    offsets = struct.unpack(">6I", data[34:58])
    split = Path(name).suffix != ".frm"
    inventory.append({
        "source": name, "archive": str(assets.index[name].path),
        "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
        "version": version, "stored_fps": fps, "effective_fps": fps or 10,
        "action_frame": action, "frames_per_direction": count,
        "stored_direction_count": 1 if split else len(set(offsets)),
        "split_direction": int(name[-1]) if split else None,
        "declared_data_size": struct.unpack(">I", data[58:62])[0],
        "actual_data_size": len(data) - 62,
        "validation": "header inventory only; not a full animation decode",
    })
write_json(WORK, "inventory.json", {
    "prefix": "hmjmps", "critter_list_index": 11,
    "resource_files": len(inventory),
    "frm_files": sum(r["split_direction"] is None for r in inventory),
    "split_files": sum(r["split_direction"] is not None for r in inventory),
    "resources": inventory,
})

frame_total = 0
clip_report = []
for filename, label in clips.items():
    name = "art/critters/" + filename
    data = assets.read(name)
    meta, directions = decode_frm(data)
    export_frm(data, name, palette, REF, all_frames=True)
    for direction, frames in directions.items():
        for index, frame in enumerate(frames):
            # Lossless indexed-to-RGBA conversion; index zero stays transparent.
            rows = []
            for y in range(frame.height):
                row = bytearray(b"\0")
                for p in frame.pixels[y * frame.width:(y + 1) * frame.width]:
                    row.extend(palette[p * 3:p * 3 + 3])
                    row.append(255 if p else 0)
                rows.append(bytes(row))
            rgba = (b"\x89PNG\r\n\x1a\n"
                    + png_chunk(b"IHDR", struct.pack(">IIBBBBB", frame.width, frame.height, 8, 6, 0, 0, 0))
                    + png_chunk(b"IDAT", zlib.compress(b"".join(rows), 9))
                    + png_chunk(b"IEND", b""))
            write_bytes(REF, f"rgba/{name}/d{direction}-f{index:03}.png", rgba)
            frame_total += 1
    clip_report.append({"source": name, "clip": label, "directions": len(directions),
                        "frames_per_direction": meta["frame_count"], "fps": meta["fps"]})
    if label == "stand":
        # Review sheet only: six original first frames enlarged exactly 4x.
        # Visual bottom alignment is for comparison, NOT engine registration.
        scale, cell_w, cell_h = 4, 48, 80
        width, height = cell_w * 6 * scale, cell_h * scale
        pixels = bytearray(width * height)
        for direction in range(6):
            frame = directions[direction][0]
            x = (direction * cell_w + (cell_w - frame.width) // 2) * scale
            y = (cell_h - frame.height - 6) * scale
            for sy in range(frame.height):
                row = bytes(p for p in frame.pixels[sy * frame.width:(sy + 1) * frame.width] for _ in range(scale))
                for repeat in range(scale):
                    start = (y + sy * scale + repeat) * width + x
                    pixels[start:start + len(row)] = row
        write_bytes(WORK, "preview/original-stand-six-directions-x4.png", png_indexed(width, height, bytes(pixels), palette))

write_json(WORK, "task.json", {
    "component": "player-male-vault13", "date": "2026-11-12",
    "scope": "HD redesign of male playable character wearing the Vault 13 jumpsuit",
    "status": "Original references prepared; no HD art generated or installed",
    "source_prefix": "hmjmps", "critter_list_index": 11,
    "reference_directory": str(REF.relative_to(ROOT)).replace("\\", "/"),
    "exported_frames": frame_total, "clips": clip_report,
    "source_integrity": "DAT files read only; extracted originals are immutable",
    "registration": "Retained source frame shifts, direction offsets, fps, action frame in reference metadata",
    "preview_note": "Nearest-neighbour 4x source pixels; visual bottom alignment only, not an HD asset or runtime screenshot",
    "current_world_baseline_observed": "work/hd-world-pilot/task.json reports V14 campfire; AGENTS.md is a V13 snapshot",
    "integration_status": "Not connected; current HD world resolver lacks player identity and direction keys",
    "next_stage": "Develop coherent costume appearance, then validate complete stand/walk cycles in all six directions",
    "remaining": [
        "Art redesign and animated consistency review",
        "Isolated exporter support for split .fr0-.fr5 before processing those actions",
        "Player-only direction-aware HD rendering and runtime validation",
        "Remaining weapon, interaction, hit and death animations",
    ],
    "shared_files_modified": [],
})
print(json.dumps({"resources_in_inventory": len(inventory), "exported_frames": frame_total, "reference": str(REF)}, ensure_ascii=False))
