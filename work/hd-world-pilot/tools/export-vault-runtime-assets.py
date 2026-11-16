"""Validate and losslessly package174 V13ENT images, including15 outer-door frames."""
import argparse
from pathlib import Path
import struct

from vault_pack_common import (
    STATIC_INVENTORY, VAULT_SOURCES, DOOR, DOOR_FID, runtime, sha,
    read_json, json_bytes, child, original_door, validate_image, door_registration,
)


def validate_package(source):
    selected = read_json(source / "manifest.json")
    if (selected.get("asset_count"), selected.get("static_resource_count"),
            selected.get("animated_resource_count"), selected.get("animated_frame_count")) != (174, 159, 1, 15):
        raise ValueError("Expected the complete174-image vault package")
    by_id = {entry["asset_id"]: entry for entry in selected["assets"]}
    if len(selected["assets"]) != 174 or set(by_id) != set(range(1, 175)):
        raise ValueError("Selected IDs must be exactly1..174")
    inventory, inventory_sha, prepared = runtime.validate_package(source, STATIC_INVENTORY)
    if selected["source_inventory"]["sha256"] != inventory_sha:
        raise ValueError("Selected static source inventory changed")
    for entry, _, metadata in prepared:
        selection = by_id[entry["asset_id"]]
        if (selection["resource"] != entry["original_resource"] or selection.get("frame", 0) != 0
                or selection["fids"] != entry["fids"] or selection["sha256"] != entry["source_png_sha256"]
                or selection["metadata_sha256"] != sha(metadata)):
            raise ValueError(f"Selected static entry differs from validated bytes: {entry['asset_id']}")
        entry["frame"] = 0
    source_inventory_path = VAULT_SOURCES / "inventory.json"
    if selected["animated_source_inventory"]["sha256"] != sha(source_inventory_path.read_bytes()):
        raise ValueError("Selected animated source inventory changed")
    original_asset, original_frames = original_door()
    for frame in range(15):
        asset_id = 160 + frame
        selection = by_id[asset_id]
        if (selection["resource"], selection.get("frame"), selection["fids"],
                selection["native_dimensions"]) != (DOOR, frame, [DOOR_FID], [189, 157]):
            raise ValueError(f"Animated FID/frame/geometry changed: ID{asset_id}")
        source_png = child(source, selection["png"])
        data = source_png.read_bytes()
        source_frame, original_data = original_frames[frame]
        if sha(data) != selection["sha256"]:
            raise ValueError(f"Selected animated PNG changed: ID{asset_id}")
        width, height, pixels = validate_image(data, original_data, 189, 157, source_png)
        metadata = child(source, selection["metadata"]).read_bytes()
        if sha(metadata) != selection["metadata_sha256"]:
            raise ValueError(f"Selected animated metadata changed: ID{asset_id}")
        metadata_record = read_json(source / selection["metadata"])
        registration = door_registration(original_asset, frame)
        if metadata_record.get("registration") != registration:
            raise ValueError(f"Animated frame registration differs from original: ID{asset_id}")
        filename = f"asset-{asset_id:03}.rgba"
        payload = struct.pack("<4sIIII", b"F1HD", 1, width, height, 4) + pixels
        entry = {
            "asset_id": asset_id, "original_resource": DOOR, "category": "scenery", "frame": frame,
            "fid": DOOR_FID, "fids": [DOOR_FID], "tile_art_ids": [],
            "native_width": 189, "native_height": 157, "width": width, "height": height, "scale": 4,
            "filename": filename, "source_png": str(source_png.resolve()), "source_png_sha256": sha(data),
            "original_png_sha256": source_frame["sha256"], "original_frm_sha256": original_asset["source"]["sha256"],
            "runtime_file": "data/art/hd/world-pilot/" + filename, "runtime_file_sha256": sha(payload),
            "decoded_rgba_sha256": sha(pixels),
            "metadata_file": "data/art/hd/world-pilot/" + filename.replace(".rgba", ".metadata.json"),
            "metadata_sha256": sha(metadata), "metadata_origin": "selected_package",
            "alpha_values": sorted(set(pixels[3::4])), "alpha_exact_original_nearest_neighbor": True,
            "registration": registration,
        }
        prepared.append((entry, payload, metadata))
    keys = [(fid, entry["frame"]) for entry, _, _ in prepared for fid in entry["fids"]]
    if len(keys) != len(set(keys)) or len(prepared) != 174:
        raise ValueError("Duplicate/missing FID+frame registration")
    coverage_data = child(source, selected["coverage_file"]).read_bytes()
    if sha(coverage_data) != selected["coverage_sha256"]:
        raise ValueError("Selected coverage hash changed")
    base_images = {entry['asset_id']: (entry, payload, metadata) for entry, payload, metadata in prepared}
    slots, ids = set(), set(base_images)
    variants = selected.get('variants', [])
    decorations = selected.get('decorations', [])
    if (selected.get('variant_image_count', 0) != len(variants)
            or selected.get('decoration_image_count', 0) != len(decorations)
            or selected.get('total_image_count', 174) != 174 + len(variants) + len(decorations)):
        raise ValueError('Incorrect variant inventory counts')
    for item in variants:
        asset_id, base_id, slot = item['asset_id'], item['base_asset_id'], item['variant_slot']
        if asset_id not in range(200, 256) or asset_id in ids or base_id not in base_images or slot not in (1, 2) or (base_id, slot) in slots:
            raise ValueError('Invalid or duplicate variant ID/slot')
        base, base_payload, base_metadata = base_images[base_id]
        if not base['original_resource'].startswith('art/walls/ca') or base['frame'] != 0:
            raise ValueError('Only static cave wall variants are supported')
        data = child(source, item['png']).read_bytes()
        metadata = child(source, item['metadata']).read_bytes()
        width, height, pixels = runtime.decode_rgba8(data)
        original = base_payload[20:]
        if (sha(data) != item['sha256'] or sha(metadata) != item['metadata_sha256']
                or metadata != base_metadata or item['resource'] != base['original_resource']
                or item['fids'] != base['fids'] or item.get('frame', 0) != 0
                or item['native_dimensions'] != [base['native_width'], base['native_height']]
                or (width, height) != (base['width'], base['height']) or pixels[3::4] != original[3::4]):
            raise ValueError(f'Variant changes geometry, alpha, metadata or hashes: {asset_id}')
        for y in range(height):
            for x in range(width):
                pos = (y * width + x) * 4
                if (x < 8 or y < 8 or x >= width - 8 or y >= height - 8) and pixels[pos:pos+4] != original[pos:pos+4]:
                    raise ValueError(f'Variant changes protected join edge: {asset_id}')
        if pixels == original:
            raise ValueError('Variant identical to base')
        entry = dict(base, asset_id=asset_id, base_asset_id=base_id, variant_slot=slot,
            filename=f'asset-{asset_id:03}.rgba', source_png=str(child(source, item['png'])), source_png_sha256=sha(data))
        payload = base_payload[:20] + pixels
        entry.update(runtime_file='data/art/hd/world-pilot/' + entry['filename'], runtime_file_sha256=sha(payload),
            decoded_rgba_sha256=sha(pixels), metadata_file='data/art/hd/world-pilot/' + entry['filename'].replace('.rgba', '.metadata.json'))
        prepared.append((entry, payload, metadata)); ids.add(asset_id); slots.add((base_id, slot))
    for item in decorations:
        asset_id = item['asset_id']
        if asset_id not in range(240, 249) or asset_id in ids:
            raise ValueError('Invalid or duplicate decoration ID')
        width, height = item['native_dimensions']
        if not (1 <= width <= 128 and 1 <= height <= 128):
            raise ValueError('Decoration too large')
        png = child(source, item['png']); data = png.read_bytes()
        metadata = child(source, item['metadata']).read_bytes()
        w, h, pixels = runtime.decode_rgba8(data)
        if ((w, h) != (width*4, height*4) or sha(data) != item['sha256']
                or sha(metadata) != item['metadata_sha256']):
            raise ValueError('Decoration dimensions/hash mismatch')
        if set(pixels[3::4]) != {0,255}:
            raise ValueError('Decoration needs transparent binary alpha')
        for y in range(h):
            for x in range(w):
                if pixels[(y*w+x)*4+3] != pixels[((y//4*4)*w+x//4*4)*4+3]:
                    raise ValueError('Decoration alpha not constant in native cells')
        filename = f'asset-{asset_id:03}.rgba'
        payload = struct.pack('<4sIIII', b'F1HD', 1, w, h, 4) + pixels
        entry = dict(asset_id=asset_id, category='decoration', key=item['key'],
            native_width=width, native_height=height, width=w, height=h, scale=4, filename=filename,
            source_png=str(png.resolve()), source_png_sha256=sha(data), decoded_rgba_sha256=sha(pixels),
            runtime_file='data/art/hd/world-pilot/'+filename, runtime_file_sha256=sha(payload),
            metadata_file='data/art/hd/world-pilot/'+filename.replace('.rgba','.metadata.json'), metadata_sha256=sha(metadata),
            render_only=True, original_frm=None, original_fid=None, creates_game_object=False)
        prepared.append((entry,payload,metadata)); ids.add(asset_id)
    decoration_ids = {item['asset_id'] for item in decorations}
    placements = selected.get('decoration_placements', [])
    if len(placements) > 64: raise ValueError('Too many decoration placements')
    used = set()
    for item in placements:
        key = item['asset_id'], item['tile']
        if (key in used or item['asset_id'] not in decoration_ids or not 0 <= item['tile'] < 40000
                or item['elevation'] != 0 or not -64 <= item['offset_x'] <= 64
                or not -64 <= item['offset_y'] <= 64 or type(item['flat']) is not bool):
            raise ValueError('Invalid decoration placement')
        used.add(key)
    return selected, prepared


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    # Complete validation of every static and animated image precedes all writes.
    selected, prepared = validate_package(args.source)
    if args.validate_only:
        print(f"Validated {len(prepared)} images, geometry/alpha/offsets/variant edges and selected hashes. No runtime files written.")
        return
    lines = ["# F1HD world registry v2; optional sixth column is frame",
             "# id\tfid\tnative_width\tnative_height\tfilename\tframe(optional; default0)"]
    variant_lines = ['# base_id\tslot\tvariant_id\tfilename']
    decor_lines = ['# id\tnative_width\tnative_height\tfilename']
    for entry, _, _ in prepared:
        if entry.get('category') == 'decoration':
            decor_lines.append(f"{entry['asset_id']}\t{entry['native_width']}\t{entry['native_height']}\t{entry['filename']}")
            continue
        if 'variant_slot' in entry:
            variant_lines.append(f"{entry['base_asset_id']}\t{entry['variant_slot']}\t{entry['asset_id']}\t{entry['filename']}")
            continue
        for fid in entry["fids"]:
            line = f"{entry['asset_id']}\t{fid}\t{entry['native_width']}\t{entry['native_height']}\t{entry['filename']}"
            if entry["asset_id"] >= 160:
                line += f"\t{entry['frame']}"
            lines.append(line)
    registry = ("\n".join(lines) + "\n").encode("ascii")
    manifest = {
        "schema_version": 3, "format": "F1HDv1 straight RGBA8; optional registry frame column",
        "operation": "lossless PNG decode and packaging only",
        "selected_package": str(args.source.resolve()), "selected_manifest_sha256": sha((args.source / "manifest.json").read_bytes()),
        "asset_count": len(prepared), "base_asset_count": 174, "variant_image_count": len(selected.get('variants', [])),
        "decoration_image_count": len(selected.get('decorations', [])),
        "decoration_placements": selected.get('decoration_placements', []),
        "static_resource_count": 159, "animated_resource_count": 1, "animated_frame_count": 15,
        "source_inventory": str(STATIC_INVENTORY), "source_inventory_sha256": sha(STATIC_INVENTORY.read_bytes()),
        "animated_source_inventory": str(VAULT_SOURCES / "inventory.json"),
        "animated_source_inventory_sha256": sha((VAULT_SOURCES / "inventory.json").read_bytes()),
        "registry_file": "data/art/hd/world-pilot/registry.tsv", "registry_sha256": sha(registry),
        "all_inputs_validated_before_runtime_writes": True, "assets": [entry for entry, _, _ in prepared],
    }
    target = args.runtime / "data/art/hd/world-pilot"
    target.mkdir(parents=True, exist_ok=True)
    for entry, payload, metadata in prepared:
        runtime.write_atomic(target / entry["filename"], payload)
        runtime.write_atomic(target / entry["filename"].replace(".rgba", ".metadata.json"), metadata)
    variants_data = ('\n'.join(variant_lines) + '\n').encode('ascii')
    manifest['variants_sha256'] = sha(variants_data)
    runtime.write_atomic(target / "variants.tsv", variants_data)
    decor_data = ('\n'.join(decor_lines)+'\n').encode('ascii')
    placement_lines = ['# asset_id\ttile\televation\toffset_x\toffset_y\tflat']
    for item in selected.get('decoration_placements', []):
        placement_lines.append('\t'.join(str(int(item[k])) for k in ('asset_id','tile','elevation','offset_x','offset_y','flat')))
    placement_data = ('\n'.join(placement_lines)+'\n').encode('ascii')
    runtime.write_atomic(target / 'decor.tsv', decor_data)
    runtime.write_atomic(target / 'decor-placements.tsv', placement_data)
    manifest.update(decor_registry_sha256=sha(decor_data), decor_placements_sha256=sha(placement_data))
    runtime.write_atomic(target / "manifest.json", json_bytes(manifest))
    runtime.write_atomic(target / "registry.tsv", registry)
    print(f"Packaged {len(prepared)} verified images: {target}")


if __name__ == "__main__":
    main()
