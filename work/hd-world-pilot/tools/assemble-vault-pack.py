"""Assemble v5:159 static resources (9 rusty overrides) plus15 outer-door frames."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from vault_pack_common import (
    ROOT, STATIC_INVENTORY, VAULT_RUN, VAULT_SOURCES, STATIC_OVERRIDES, DOOR, DOOR_FID,
    runtime, sha, read_json, json_bytes, relative, reference, resolve_recorded, child,
    original_door, validate_image, door_registration,
)


def prepared_run(directory, expected):
    record = read_json(directory / "run.json")
    if record.get("status") != "success":
        raise ValueError(f"Prepared Comfy run is incomplete: {directory}")
    files = {(entry["source"], entry.get("frame", 0)): entry for entry in record["files"]}
    if len(files) != len(record["files"]) or set(files) != expected:
        raise ValueError(f"Prepared resource/frame coverage differs: {directory}")
    graph = {name: reference(directory / name) for name in ("workflow.json", "prompt-api.json", "history.json")}
    history = read_json(directory / "history.json")
    if history.get("status", {}).get("status_str") not in (None, "success"):
        raise ValueError(f"Prepared Comfy history failed: {directory}")
    for master in record.get("masters", {}).values():
        if "path" not in master or "sha256" not in master:
            raise ValueError(f"Missing ImageGen master input provenance: {directory}")
        if reference(resolve_recorded(master["path"]))["sha256"] != master["sha256"]:
            raise ValueError(f"ImageGen master hash changed: {master['path']}")
    outputs = {}
    for key, entry in files.items():
        for input_kind in ("baseline", "original"):
            input_path = entry.get(input_kind + "_path")
            input_hash = entry.get(input_kind + "_sha256")
            if input_path is not None:
                if input_hash is None or reference(resolve_recorded(input_path))["sha256"] != input_hash:
                    raise ValueError(f"Prepared {input_kind} input changed: {input_path}")
        path = child(directory, entry["path"])
        data = path.read_bytes()
        if sha(data) != entry["sha256"]:
            raise ValueError(f"Prepared output hash changed: {path}")
        if not entry.get("prompt_id") or entry.get("prompt_id") != record.get("prompt_id") or "node" not in entry:
            raise ValueError(f"Prepared output lacks its actual Comfy prompt/node: {path}")
        outputs[key] = (path, data, {
            "kind": "rusty_vault_imagegen_material_with_comfy_registration",
            "run_manifest": reference(directory / "run.json"), "graph": graph,
            "actual_run_record": record, "file_record": entry,
        })
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent-package", type=Path, default=ROOT / "assets/hd/v13ent/v4-wall-coherent-x4")
    parser.add_argument("--frame-run", type=Path, default=VAULT_RUN / "frame-prepared-exact")
    parser.add_argument("--walls-run", type=Path, default=VAULT_RUN / "walls-prepared")
    parser.add_argument("--door-run", type=Path, default=VAULT_RUN / "door-prepared-eroded")
    parser.add_argument("--output", type=Path, default=ROOT / "assets/hd/v13ent/v5-rusty-vault-x4")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if args.output.resolve() == args.parent_package.resolve():
        parser.error("A new output version is required; preserve the parent.")
    parent = read_json(args.parent_package / "manifest.json")
    parent_ref = reference(args.parent_package / "manifest.json")
    inventory = read_json(STATIC_INVENTORY)
    inventory_ref = reference(STATIC_INVENTORY)
    rows = runtime.ordered_assets(inventory)
    if parent.get("asset_count") != 159 or parent["source_inventory"]["sha256"] != inventory_ref["sha256"]:
        raise ValueError("Parent is not the selected159-resource static source package")
    entries = {entry["resource"]: entry for entry in parent["assets"]}
    if len(parent["assets"]) != 159 or set(entries) != {row["path"] for row in rows}:
        raise ValueError("Parent static coverage differs")
    original_asset, original_frames = original_door()
    prepared = {}
    for directory, expected in (
        (args.frame_run, {("art/scenery/v13secr3.frm", 0)}),
        (args.walls_run, {(resource, 0) for resource in STATIC_OVERRIDES if resource.startswith("art/walls/")}),
        (args.door_run, {(DOOR, frame) for frame in range(15)}),
    ):
        prepared.update(prepared_run(directory, expected))
    planned, selected = {}, []
    for asset_id, row in enumerate(rows, start=1):
        resource = row["path"]
        parent_entry = entries[resource]
        png_path = resource + ".png"
        metadata_path = "metadata/" + resource + ".json"
        if parent_entry["asset_id"] != asset_id or parent_entry["png"] != png_path or parent_entry["metadata"] != metadata_path:
            raise ValueError(f"Parent stable identity changed: {resource}")
        data = child(args.parent_package, png_path).read_bytes()
        metadata_data = child(args.parent_package, metadata_path).read_bytes()
        if sha(data) != parent_entry["sha256"] or sha(metadata_data) != parent_entry["metadata_sha256"]:
            raise ValueError(f"Parent source bytes changed: {resource}")
        original_data = child(STATIC_INVENTORY.parent, row["rgba_png"]).read_bytes()
        if sha(original_data) != row["rgba_png_sha256"]:
            raise ValueError(f"Original source hash changed: {resource}")
        validate_image(data, original_data, row["width"], row["height"], resource)
        entry = dict(parent_entry)
        if resource in STATIC_OVERRIDES:
            path, data, provenance = prepared[(resource, 0)]
            if provenance["file_record"].get("source_sha256") not in (row["source_sha256"], row["rgba_png_sha256"]):
                raise ValueError(f"Prepared output uses a different original source: {resource}")
            width, height, _ = validate_image(data, original_data, row["width"], row["height"], path)
            metadata = {
                "resource": resource, "asset_id": asset_id, "source": row, "registration": row["registration"],
                "selected_image": {"path": png_path, "sha256": sha(data), "dimensions": [width, height],
                                   "scale": 4, "input": relative(path), "selection": "rusty_vault_static_override"},
                "alpha_exact_original_nearest_neighbor": True,
                "provenance": provenance, "previous_selected_metadata": read_json(args.parent_package / metadata_path),
                "parent_package": parent_ref, "artistic_status": "candidate_for_review",
                "integration_status": "pending_engine_validation", "integrated_in_ce": False,
            }
            metadata_data = json_bytes(metadata)
            entry.update({"sha256": sha(data), "metadata_sha256": sha(metadata_data), "selection": "rusty_vault_static_override"})
            entry.pop("postprocessing", None)
        planned[png_path], planned[metadata_path] = data, metadata_data
        selected.append(entry)
    for frame in range(15):
        asset_id = 160 + frame
        source_frame, original_data = original_frames[frame]
        path, data, provenance = prepared[(DOOR, frame)]
        if provenance["file_record"].get("source_sha256") not in (original_asset["source"]["sha256"], source_frame["sha256"]):
            raise ValueError(f"Prepared animation source mismatch: frame{frame}")
        width, height, _ = validate_image(data, original_data, 189, 157, path)
        png_path = f"art/scenery/v13secr2.frm/frames/d0-f{frame:03}.png"
        metadata_path = f"metadata/art/scenery/v13secr2.frm/frames/d0-f{frame:03}.json"
        metadata = {
            "resource": DOOR, "asset_id": asset_id, "frame": frame,
            "source": original_asset, "source_frame": source_frame,
            "registration": door_registration(original_asset, frame),
            "selected_image": {"path": png_path, "sha256": sha(data), "dimensions": [width, height],
                               "scale": 4, "input": relative(path), "selection": "rusty_outer_door_animation_frame"},
            "alpha_exact_original_nearest_neighbor": True, "provenance": provenance,
            "artistic_status": "candidate_for_review", "integration_status": "pending_engine_validation", "integrated_in_ce": False,
        }
        metadata_data = json_bytes(metadata)
        planned[png_path], planned[metadata_path] = data, metadata_data
        selected.append({
            "asset_id": asset_id, "resource": DOOR, "category": "scenery", "fids": [DOOR_FID], "frame": frame,
            "png": png_path, "sha256": sha(data), "native_dimensions": [189, 157], "dimensions": [width, height],
            "metadata": metadata_path, "metadata_sha256": sha(metadata_data), "selection": "rusty_outer_door_animation_frame",
        })
    coverage = {
        "scope": "159 existing static base resources plus all15 frames of the existing outer round vault door",
        "selected_image_count": 174, "static_resource_count": 159, "animated_resource_count": 1, "animated_frame_count": 15,
        "static_material_overrides": sorted(STATIC_OVERRIDES), "unchanged_parent_static_count": 150,
        "animated_resource": DOOR, "animation_fps": 10, "new_objects_or_decorations": False,
        "maps_or_prototypes_modified": False, "collision_or_gameplay_modified": False,
        "integration_status": "pending_engine_validation",
        "exclusions": ["Rectangular inner door v13secur.frm stays original", "Critters, items, invisible blockers and markers",
                       "Other maps and script-created dependencies", "HUD and menu artwork"],
    }
    planned["coverage.json"] = json_bytes(coverage)
    planned["README.txt"] = (
        "V13ENT RUSTY VAULT MATERIAL CANDIDATE — X4\n\n"
        "174 images:159 static resources and15 frames of outer round door v13secr2.\n"
        "Nine static images (outer frame and eight metal wall strips) are refreshed;\n"
        "the other150 static PNGs and metadata are byte-identical to parent v4.\n"
        "All animation frames retain original189x157 canvases, alpha, frame shifts,\n"
        "direction offsets, frame order and10fps source metadata. RGB art is x4.\n"
        "Inner rectangular door v13secur remains original. No new objects, map edits,\n"
        "collision changes, gameplay changes, menu changes or HUD changes are made.\n"
        "Per-image metadata retains actual ImageGen/Comfy evidence and source hashes.\n"
        "This package is a candidate until engine and in-game visual tests pass.\n"
        "Keep previous packages immutable; use a new version for different bytes.\n"
    ).encode("utf-8")
    existing = args.output / "manifest.json"
    created = read_json(existing).get("created_utc") if existing.is_file() else datetime.now(timezone.utc).isoformat()
    manifest = {
        "schema_version": 2, "version": args.output.name.removeprefix("v"), "component": "v13ent-cave",
        "created_utc": created, "status": "candidate_integration_pending", "integrated_in_ce": False,
        "scale": 4, "asset_count": 174, "static_resource_count": 159, "animated_resource_count": 1, "animated_frame_count": 15,
        "selection_counts": dict(Counter(entry["selection"] for entry in selected)),
        "parent_package": parent_ref, "source_inventory": inventory_ref,
        "animated_source_inventory": reference(VAULT_SOURCES / "inventory.json"),
        "source_runs": {name: reference(directory / "run.json") for name, directory in (
            ("outer_frame", args.frame_run), ("metal_walls", args.walls_run), ("outer_door_animation", args.door_run))},
        "original_map": parent["original_map"], "coverage_file": "coverage.json", "coverage_sha256": sha(planned["coverage.json"]),
        "all_selected_png_dimensions_and_alpha_validated": True, "all_inputs_validated_before_selected_pack_writes": True,
        "unchanged_parent_static_resources": [entry["resource"] for entry in selected[:159] if entry["resource"] not in STATIC_OVERRIDES],
        "assets": selected,
    }
    planned["manifest.json"] = json_bytes(manifest)
    conflicts = [name for name, data in planned.items() if (args.output / name).exists() and (args.output / name).read_bytes() != data]
    if conflicts:
        raise ValueError(f"Different existing candidate files preserved: {conflicts}")
    if args.validate_only:
        print("Validated174 images, including all15 original animation frames; no files written.")
        return
    for name, data in planned.items():
        path = args.output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if path.read_bytes() != data:
                raise ValueError(f"Candidate file changed after validation: {path}")
        else:
            with path.open("xb") as stream:
                stream.write(data)
    print(f"Assembled174 validated images: {args.output}")


if __name__ == "__main__":
    main()
