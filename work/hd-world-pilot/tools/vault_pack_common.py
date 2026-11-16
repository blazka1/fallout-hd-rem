"""Shared strict validation for the V13ENT outer-door material revision."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
STATIC_INVENTORY = ROOT / "assets/generated/v13ent-cave/v1-20261111/sources/manifest.json"
VAULT_SOURCES = ROOT / "assets/generated/v13ent-vault/v1-rust-20261112/sources"
VAULT_RUN = VAULT_SOURCES.parent
DOOR = "art/scenery/v13secr2.frm"
DOOR_FID = 33554713
STATIC_OVERRIDES = {
    "art/scenery/v13secr3.frm",
    *(f"art/walls/{name}.frm" for name in (
        "va5001", "vb3000", "vb3001", "vb4000", "vb4003", "vcn3000", "vcn4000", "vcn6000")),
}


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runtime = load_module("vault_runtime_base", "export-runtime-assets.py")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def relative(path):
    path = Path(path).resolve()
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def reference(path):
    path = Path(path)
    return {"path": relative(path), "sha256": sha(path.read_bytes())}


def resolve_recorded(path):
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def child(root, relative_path):
    root = Path(root).resolve()
    result = (root / relative_path).resolve()
    if not result.is_relative_to(root):
        raise ValueError(f"Recorded path escapes package: {relative_path}")
    return result


def original_door():
    """Recheck the exported animation against DAT-derived raw FRM and palette bytes."""
    inventory = read_json(VAULT_SOURCES / "inventory.json")
    matches = [a for a in inventory["assets"] if a["resource"] == DOOR]
    if len(matches) != 1:
        raise ValueError("Missing unique outer-door source resource")
    asset = matches[0]
    if (asset["frame_count"], asset["fps"], asset["unique_directions"], asset["fids"]) != (15, 10, 1, [DOOR_FID]):
        raise ValueError("Outer-door identity, animation rate or frame count changed")
    sys.path.insert(0, str(ROOT / "tools/asset-pipeline"))
    from fallout_assets import decode_frm, palette_rgb
    from cave_reference import rgba_png
    raw = child(VAULT_SOURCES, asset["source"]["output"]).read_bytes()
    if sha(raw) != asset["source"]["sha256"]:
        raise ValueError("Original outer-door FRM hash changed")
    meta, directions = decode_frm(raw)
    for key in ("frame_count", "fps", "unique_directions", "direction_x", "direction_y", "direction_offsets"):
        actual = list(meta[key]) if isinstance(meta[key], tuple) else meta[key]
        if actual != asset[key]:
            raise ValueError(f"Original outer-door registration changed: {key}")
    palette_raw = (VAULT_SOURCES / "raw/color.pal").read_bytes()
    static_inventory = read_json(STATIC_INVENTORY)
    if sha(palette_raw) != static_inventory["palette"]["source_sha256"]:
        raise ValueError("Original palette hash changed")
    palette = palette_rgb(palette_raw)
    frames = {}
    if len(asset["frames"]) != 15:
        raise ValueError("Expected15 original source frames")
    for entry in asset["frames"]:
        frame_id = entry["frame"]
        if frame_id not in range(15) or frame_id in frames:
            raise ValueError("Original frame IDs must be unique0..14")
        frame = directions[0][frame_id]
        if (frame.width, frame.height, frame.shift_x, frame.shift_y) != (189, 157, 0, 0):
            raise ValueError(f"Outer-door frame dimensions/offset changed: {frame_id}")
        data = child(VAULT_SOURCES, entry["png"]).read_bytes()
        expected, _ = rgba_png(frame, palette)
        if data != expected or sha(data) != entry["sha256"]:
            raise ValueError(f"Original RGBA frame is not the exact FRM decode: {frame_id}")
        frames[frame_id] = (entry, data)
    return asset, frames


def validate_image(data, original_data, width, height, label):
    ow, oh, original = runtime.decode_rgba8(original_data)
    w, h, pixels = runtime.decode_rgba8(data)
    if (ow, oh, w, h) != (width, height, width * 4, height * 4):
        raise ValueError(f"Original or x4 canvas dimensions changed: {label}")
    if not runtime.exact_scaled_alpha(pixels, original, width, height):
        raise ValueError(f"Original nearest-neighbor alpha changed: {label}")
    return w, h, pixels


def door_registration(asset, frame):
    return {
        "frame": frame, "direction": 0, "frame_shift_x": 0, "frame_shift_y": 0,
        "direction_x": asset["direction_x"], "direction_y": asset["direction_y"],
        "direction_offsets": asset["direction_offsets"], "fps": asset["fps"],
        "native_dimensions": [189, 157], "engine_offsets_unchanged": True,
    }
