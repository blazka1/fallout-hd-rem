"""Losslessly package all 159 static V13ENT PNGs for the isolated CE runtime.

F1HD v1: 4-byte ASCII magic + four little-endian uint32 values
(version, width, height, scale), followed by straight RGBA8, top row first.
No resize, quantization, premultiplication, or image generation is performed.
The small decoder deliberately accepts only non-interlaced RGBA8 PNGs. All
resources are validated against original geometry and alpha before any runtime
file is written. Missing/corrupt files at game startup are the engine's fallback
case; an incomplete selected package is not silently published by this tool.
"""

import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INVENTORY = PROJECT_ROOT / "assets/generated/v13ent-cave/v1-20261111/sources/manifest.json"
EXPECTED_ASSETS = 159
SCALE = 4
FIRST_RESOURCES = ("art/tiles/cav1000.frm", "art/scenery/rock03.frm")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def decode_rgba8(data):
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Invalid PNG signature")
    offset, compressed, dimensions = 8, bytearray(), None
    ended = False
    while offset + 12 <= len(data):
        size = struct.unpack_from(">I", data, offset)[0]
        kind = data[offset + 4:offset + 8]
        chunk = data[offset + 8:offset + 8 + size]
        if offset + 12 + size > len(data):
            raise ValueError("Truncated PNG chunk")
        crc = struct.unpack_from(">I", data, offset + 8 + size)[0]
        if zlib.crc32(kind + chunk) & 0xFFFFFFFF != crc:
            raise ValueError("PNG CRC mismatch")
        if kind == b"IHDR":
            width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", chunk)
            if (depth, color, compression, filtering, interlace) != (8, 6, 0, 0, 0):
                raise ValueError("Expected non-interlaced RGBA8 PNG")
            if not (0 < width <= 4096 and 0 < height <= 4096):
                raise ValueError("Unexpected PNG dimensions")
            dimensions = width, height
        elif kind == b"IDAT":
            compressed.extend(chunk)
        elif kind == b"IEND":
            ended = True
            break
        offset += size + 12
    if not ended or dimensions is None:
        raise ValueError("Incomplete PNG")
    width, height = dimensions
    stride = width * 4
    raw = zlib.decompress(compressed)
    if len(raw) != height * (stride + 1):
        raise ValueError("Unexpected PNG pixel stream size")
    pixels, previous = bytearray(), bytearray(stride)
    for row in range(height):
        row_start = row * (stride + 1)
        filter_type = raw[row_start]
        current = bytearray(raw[row_start + 1:row_start + 1 + stride])
        if filter_type > 4:
            raise ValueError("Invalid PNG row filter")
        for x in range(stride):
            left = current[x - 4] if x >= 4 else 0
            up = previous[x]
            upper_left = previous[x - 4] if x >= 4 else 0
            if filter_type == 0:
                prediction = 0
            elif filter_type == 1:
                prediction = left
            elif filter_type == 2:
                prediction = up
            elif filter_type == 3:
                prediction = (left + up) // 2
            else:
                p = left + up - upper_left
                a, b, c = abs(p - left), abs(p - up), abs(p - upper_left)
                prediction = left if a <= b and a <= c else (up if b <= c else upper_left)
            current[x] = (current[x] + prediction) & 255
        pixels.extend(current)
        previous = current
    return width, height, bytes(pixels)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def ordered_assets(inventory):
    rows = inventory["assets"]
    by_path = {row["path"]: row for row in rows}
    if len(rows) != EXPECTED_ASSETS or len(by_path) != EXPECTED_ASSETS:
        raise ValueError("Expected exactly 159 unique static source resources")
    if not all(resource in by_path for resource in FIRST_RESOURCES):
        raise ValueError("Source inventory is missing the two stable pilot resources")
    paths = list(FIRST_RESOURCES) + sorted(set(by_path) - set(FIRST_RESOURCES))
    return [by_path[path] for path in paths]


def exact_scaled_alpha(pixels, original, width, height):
    """Compare RGBA alpha to an integer nearest-neighbor expansion, without PIL."""
    alpha = pixels[3::4]
    original_alpha = original[3::4]
    hd_width = width * SCALE
    for y in range(height):
        expected_row = b"".join(bytes([value]) * SCALE
                                for value in original_alpha[y * width:(y + 1) * width])
        for subrow in range(SCALE):
            offset = (y * SCALE + subrow) * hd_width
            if alpha[offset:offset + hd_width] != expected_row:
                return False
    return True


def validate_package(source_root, inventory_path):
    inventory_data = inventory_path.read_bytes()
    inventory = json.loads(inventory_data.decode("utf-8-sig"))
    source_folder = inventory_path.parent
    ordered = ordered_assets(inventory)
    missing = [row["path"] + ".png" for row in ordered
               if not (source_root / (row["path"] + ".png")).is_file()]
    if missing:
        raise ValueError(f"Selected package is incomplete ({len(missing)} missing PNGs): {missing}")
    prepared = []
    used_fids = set()
    for asset_id, row in enumerate(ordered, start=1):
        resource = row["path"]
        if Path(resource).is_absolute() or ".." in Path(resource).parts:
            raise ValueError(f"Unexpected resource path: {resource}")
        if (row["frm"]["frame_count"], row["frm"]["unique_directions"], row["frame"]) != (1, 1, 0):
            raise ValueError(f"Only static single-image assets are supported: {resource}")
        native_width, native_height = row["width"], row["height"]
        source = source_root / (resource + ".png")
        png_data = source.read_bytes()
        width, height, pixels = decode_rgba8(png_data)
        expected = (native_width * SCALE, native_height * SCALE)
        if (width, height) != expected:
            raise ValueError(f"Unexpected selected asset size: {source}: {(width, height)}; expected {expected}")
        original_path = source_folder / row["rgba_png"]
        original_png = original_path.read_bytes()
        if sha256(original_png) != row["rgba_png_sha256"].lower():
            raise ValueError(f"Original source PNG hash mismatch: {original_path}")
        original_width, original_height, original_pixels = decode_rgba8(original_png)
        if (original_width, original_height) != (native_width, native_height):
            raise ValueError(f"Original dimensions do not match inventory: {resource}")
        if not set(original_pixels[3::4]).issubset({0, 255}):
            raise ValueError(f"Original source does not use binary alpha: {resource}")
        if not exact_scaled_alpha(pixels, original_pixels, native_width, native_height):
            raise ValueError(f"Selected alpha does not exactly match original nearest-neighbor mask: {resource}")
        if row["category"] == "tiles":
            fids = [(4 << 24) | tile_id for tile_id in row["tile_art_ids"]]
        else:
            fids = list(row["fids"])
        if not fids or len(set(fids)) != len(fids) or used_fids.intersection(fids):
            raise ValueError(f"Missing or duplicate engine FID mapping: {resource}")
        used_fids.update(fids)
        filename = "cav1000.rgba" if asset_id == 1 else "rock03.rgba" if asset_id == 2 else f"asset-{asset_id:03d}.rgba"
        metadata_source = source_root / "metadata" / (resource + ".json")
        if metadata_source.is_file():
            metadata = metadata_source.read_bytes()
            json.loads(metadata.decode("utf-8-sig"))
            metadata_origin = "selected_package"
        else:
            metadata = (json.dumps(row, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
            metadata_origin = "source_inventory"
        payload = struct.pack("<4sIIII", b"F1HD", 1, width, height, SCALE) + pixels
        entry = {
            "asset_id": asset_id,
            "original_resource": resource,
            "category": row["category"],
            "fids": fids,
            "fid": fids[0] if len(fids) == 1 else None,
            "tile_art_ids": row["tile_art_ids"],
            "native_width": native_width,
            "native_height": native_height,
            "width": width,
            "height": height,
            "scale": SCALE,
            "filename": filename,
            "source_png": str(source.resolve()),
            "source_png_sha256": sha256(png_data),
            "original_png_sha256": sha256(original_png),
            "original_frm_sha256": row["source_sha256"],
            "runtime_file": "data/art/hd/world-pilot/" + filename,
            "runtime_file_sha256": sha256(payload),
            "decoded_rgba_sha256": sha256(pixels),
            "metadata_file": "data/art/hd/world-pilot/" + filename.replace(".rgba", ".metadata.json"),
            "metadata_sha256": sha256(metadata),
            "metadata_origin": metadata_origin,
            "alpha_values": sorted(set(pixels[3::4])),
            "alpha_exact_original_nearest_neighbor": True,
        }
        if len(row["tile_art_ids"]) == 1:
            entry["tile_id"] = row["tile_art_ids"][0]
        prepared.append((entry, payload, metadata))
    return inventory, sha256(inventory_data), prepared


def write_atomic(path, data):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(data)
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY,
                        help="Verified original 159-resource inventory and adjacent RGBA sources")
    parser.add_argument("--validate-only", action="store_true",
                        help="Validate all assets and masks without creating any runtime files")
    args = parser.parse_args()
    # Complete validation precedes mkdir, metadata, assets, registry and manifest writes.
    inventory, inventory_sha, prepared = validate_package(args.source, args.inventory)
    if args.validate_only:
        print(f"Validated all {len(prepared)} selected assets; original dimensions and alpha match. No runtime files written.")
        return
    registry = ["# F1HD world registry v1", "# id\tfid\tnative_width\tnative_height\tfilename"]
    for entry, _, _ in prepared:
        for fid in entry["fids"]:
            registry.append(f"{entry['asset_id']}\t{fid}\t{entry['native_width']}\t{entry['native_height']}\t{entry['filename']}")
    registry_data = ("\n".join(registry) + "\n").encode("ascii")
    entries = [entry for entry, _, _ in prepared]
    manifest = {
        "schema_version": 2,
        "format": "F1HD v1: <4sIIII magic/version/width/height/scale, then straight top-down RGBA8",
        "operation": "lossless PNG decode and packaging only",
        "selected_package": str(args.source.resolve()),
        "asset_count": len(entries),
        "source_inventory": str(args.inventory.resolve()),
        "source_inventory_sha256": inventory_sha,
        "source_coverage": inventory["coverage"],
        "registry_file": "data/art/hd/world-pilot/registry.tsv",
        "registry_sha256": sha256(registry_data),
        "all_inputs_validated_before_runtime_writes": True,
        "assets": entries,
    }
    target = args.runtime / "data/art/hd/world-pilot"
    target.mkdir(parents=True, exist_ok=True)
    for entry, payload, metadata in prepared:
        write_atomic(target / entry["filename"], payload)
        write_atomic(target / entry["filename"].replace(".rgba", ".metadata.json"), metadata)
    write_atomic(target / "manifest.json", (json.dumps(manifest, indent=2) + "\n").encode("utf-8"))
    # Publish the loader registry only after every file it references is complete.
    write_atomic(target / "registry.tsv", registry_data)
    print(f"Packaged {len(entries)} selected assets into {target}")


if __name__ == "__main__":
    main()
