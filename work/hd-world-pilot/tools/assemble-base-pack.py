"""Assemble the immutable 159-resource V13ENT hybrid candidate without editing art.

All completed Comfy outputs, provenance hashes, dimensions and original NN alpha
are checked before any selected-pack file is written. Existing different files
are never overwritten. This tool does not generate images or update the runtime.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
GENERATION = ROOT / "assets/generated/v13ent-cave/v2-visible-20261111"
INVENTORY = ROOT / "assets/generated/v13ent-cave/v1-20261111/sources/manifest.json"
OUTPUT = ROOT / "assets/hd/v13ent/v2-hybrid-base-x4"
ROCK = ROOT / "assets/generated/v13ent-rock03/v2-visible-20261111/rock03.frm.png"
FLOOR = ROOT / "assets/generated/v13ent-cav1000/v3-hybrid-20261111/cav1000.frm.png"
FAITHFUL_PACKAGE = ROOT / "assets/hd/v13ent/v1.1-detail-x4"
FAITHFUL_MECHANICAL = {
    "art/tiles/grt2000.frm": "The direct candidate changed the original cross-grid grating into parallel bars; retain the previous HD grid geometry.",
    "art/scenery/doorcomp.frm": "The direct candidate reinterpreted the display and buttons; retain the previous HD control layout.",
    "art/scenery/v13secr3.frm": "The direct candidate rounded the sill and smoothed the original right-pillar panel wear and shading; retain the previous HD mechanical structure.",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def display_path(path):
    path = path.resolve()
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_decoder():
    path = Path(__file__).with_name("export-runtime-assets.py")
    spec = importlib.util.spec_from_file_location("v13ent_runtime_packaging", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Evidence:
    def __init__(self):
        self.references = {}

    def reference(self, path):
        path = path.resolve()
        key = str(path)
        if key not in self.references:
            data = path.read_bytes()
            self.references[key] = {"path": display_path(path), "sha256": digest(data)}
        return self.references[key]

    def run(self, directory, expected_count=None, source_sha=None):
        manifest = directory / "run.json"
        record = load_json(manifest)
        if record.get("status") != "success":
            raise ValueError(f"Generation is not complete: {manifest}: {record.get('status')}")
        if expected_count is not None:
            if record.get("asset_count") != expected_count or len(record.get("files", [])) != expected_count:
                raise ValueError(f"Incomplete generation inventory: {manifest}")
        if source_sha is not None and record.get("source_manifest_sha256") != source_sha:
            raise ValueError(f"Generation uses a different original inventory: {manifest}")
        return record, self.reference(manifest)

    def graph(self, directory, prompt_id, node=None):
        result = {"prompt_id": prompt_id}
        if not prompt_id:
            raise ValueError(f"Missing recorded Comfy prompt_id: {directory}")
        if node is not None:
            result["output_node"] = node
        for name in ("workflow.json", "prompt-api.json", "history.json"):
            result[name] = self.reference(directory / name)
        return result

    def atlas_provenance(self, directory, record, run_ref, entry):
        jobs = [job for job in record["jobs"] if job.get("prompt_id") == entry["prompt_id"]]
        if len(jobs) != 1 or jobs[0].get("status") != "success":
            raise ValueError(f"Missing successful job for {entry['source']}")
        job = jobs[0]
        return {
            "run_manifest": run_ref,
            "processing": record.get("processing"),
            "models": record.get("models", {}),
            "parameters": record.get("parameters", {}),
            "job": job,
            "file_record": {key: value for key, value in entry.items() if key != "source_metadata"},
            "graph": self.graph(directory / "jobs" / f"{job['batch']:03d}", entry["prompt_id"], entry.get("node")),
        }


def completed_files(directory, record, expected_resources):
    entries = {entry["source"]: entry for entry in record["files"]}
    if len(entries) != len(record["files"]) or set(entries) != set(expected_resources):
        raise ValueError(f"Generation resource coverage differs from source inventory: {directory}")
    data_by_resource = {}
    for resource, entry in entries.items():
        path = (directory / entry["path"]).resolve()
        if not path.is_relative_to(directory.resolve()):
            raise ValueError(f"Output path escapes its recorded run: {path}")
        data = path.read_bytes()
        if digest(data) != entry["sha256"]:
            raise ValueError(f"Recorded output hash mismatch: {path}")
        data_by_resource[resource] = (path, data)
    return entries, data_by_resource


def write_immutable_pack(output, planned, validate_only):
    conflicts = [relative for relative, data in planned.items()
                 if (output / relative).exists() and (output / relative).read_bytes() != data]
    if conflicts:
        raise ValueError(f"Existing different selected-pack files preserved; choose a new version: {conflicts}")
    if validate_only:
        print(f"Validated all 159 selected resources and provenance; no files written. Destination: {output}")
        return
    created_files = 0
    for relative, data in planned.items():
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if destination.read_bytes() != data:
                raise ValueError(f"Selected-pack file changed after validation; preserved: {destination}")
            continue
        with destination.open("xb") as stream:
            stream.write(data)
        created_files += 1
    print(f"Assembled 159 validated static resources; {created_files} new files: {output}")


def assemble_wall_revision(args):
    """Derive a new package from a frozen selected pack; only 70 wall PNGs change."""
    decoder = load_decoder()
    evidence = Evidence()
    inventory = load_json(args.inventory)
    inventory_ref = evidence.reference(args.inventory)
    rows = decoder.ordered_assets(inventory)
    resources = {row["path"] for row in rows}
    walls = {row["path"] for row in rows if row["category"] == "walls"}
    if len(rows) != 159 or len(walls) != 70:
        raise ValueError("Expected the 159-resource static inventory with 70 walls")
    parent_ref = evidence.reference(args.parent_package / "manifest.json")
    parent = load_json(args.parent_package / "manifest.json")
    if parent.get("asset_count") != 159 or parent.get("source_inventory", {}).get("sha256") != inventory_ref["sha256"]:
        raise ValueError("Parent package does not match the original 159-resource inventory")
    parent_entries = {entry["resource"]: entry for entry in parent["assets"]}
    if len(parent_entries) != 159 or set(parent_entries) != resources:
        raise ValueError("Parent package coverage differs from source inventory")
    run, run_ref = evidence.run(args.wall_run, 70, inventory_ref["sha256"])
    wall_entries, wall_data = completed_files(args.wall_run, run, walls)
    baseline_manifest_ref = evidence.reference(args.faithful_package / "manifest.json")
    baseline_manifest = load_json(args.faithful_package / "manifest.json")
    baseline_entries = {entry["resource"]: entry for entry in baseline_manifest["assets"]}
    planned = {}
    selected = []
    changed_walls = []
    baseline_kinds = Counter()
    for asset_id, row in enumerate(rows, start=1):
        resource = row["path"]
        if Path(resource).is_absolute() or ".." in Path(resource).parts:
            raise ValueError(f"Invalid source resource path: {resource}")
        parent_entry = parent_entries[resource]
        png_relative = resource + ".png"
        metadata_relative = "metadata/" + resource + ".json"
        fids = [(4 << 24) | tile_id for tile_id in row["tile_art_ids"]] if row["category"] == "tiles" else row["fids"]
        if (parent_entry.get("asset_id") != asset_id or parent_entry.get("png") != png_relative
                or parent_entry.get("metadata") != metadata_relative or parent_entry.get("fids") != fids
                or parent_entry.get("category") != row["category"]):
            raise ValueError(f"Parent package identity or registration changed: {resource}")
        parent_png = args.parent_package / png_relative
        parent_data = parent_png.read_bytes()
        parent_metadata_path = args.parent_package / metadata_relative
        parent_metadata_data = parent_metadata_path.read_bytes()
        if digest(parent_data) != parent_entry["sha256"] or digest(parent_metadata_data) != parent_entry["metadata_sha256"]:
            raise ValueError(f"Parent package PNG or metadata hash mismatch: {resource}")
        source_data = (args.inventory.parent / row["rgba_png"]).read_bytes()
        if digest(source_data) != row["rgba_png_sha256"]:
            raise ValueError(f"Original source RGBA changed: {resource}")
        source_width, source_height, source = decoder.decode_rgba8(source_data)
        if (source_width, source_height) != (row["width"], row["height"]):
            raise ValueError(f"Original dimensions differ from inventory: {resource}")

        def validate_rgba(data, label):
            width, height, pixels = decoder.decode_rgba8(data)
            if (width, height) != (row["width"] * 4, row["height"] * 4):
                raise ValueError(f"Incorrect x4 dimensions: {label}")
            if not decoder.exact_scaled_alpha(pixels, source, row["width"], row["height"]):
                raise ValueError(f"Original nearest-neighbor alpha differs: {label}")

        validate_rgba(parent_data, parent_png)
        data = parent_data
        metadata_data = parent_metadata_data
        selected_entry = dict(parent_entry)
        if resource in walls:
            entry = wall_entries[resource]
            donor_path = Path(entry["donor_path"])
            if not donor_path.is_absolute():
                donor_path = ROOT / donor_path
            donor_ref = evidence.reference(donor_path)
            if (donor_path.resolve() != parent_png.resolve() or entry.get("donor_sha256") != digest(parent_data)
                    or donor_ref["sha256"] != digest(parent_data)):
                raise ValueError(f"Wall donor is not this exact parent selected PNG: {resource}")
            baseline_path = Path(entry["baseline_path"])
            if not baseline_path.is_absolute():
                baseline_path = ROOT / baseline_path
            baseline_ref = evidence.reference(baseline_path)
            if baseline_ref["sha256"] != entry.get("baseline_sha256"):
                raise ValueError(f"Wall baseline hash changed: {resource}")
            source_path = args.inventory.parent / row["rgba_png"]
            expected_previous = args.faithful_package / baseline_entries[resource]["png"]
            if baseline_path.resolve() == source_path.resolve():
                if baseline_ref["sha256"] != row["rgba_png_sha256"]:
                    raise ValueError(f"Wall original macro baseline differs from inventory: {resource}")
                baseline_kind = "original_native_rgba_upscaled_in_comfy"
            elif baseline_path.resolve() == expected_previous.resolve():
                if baseline_ref["sha256"] != baseline_entries[resource]["sha256"]:
                    raise ValueError(f"Wall previous HD baseline differs from its manifest: {resource}")
                validate_rgba(baseline_path.read_bytes(), baseline_path)
                baseline_kind = "faithful_previous_hd_package"
            else:
                raise ValueError(f"Wall baseline is neither its original source nor faithful previous PNG: {resource}")
            baseline_kinds[baseline_kind] += 1
            path, data = wall_data[resource]
            validate_rgba(data, path)
            if digest(data) != digest(parent_data):
                changed_walls.append(resource)
            metadata = json.loads(parent_metadata_data.decode("utf-8-sig"))
            postprocessing = evidence.atlas_provenance(args.wall_run, run, run_ref, entry)
            postprocessing.update({
                "kind": "coherent_wall_palette_and_medium_detail",
                "selected_artistic_donor": donor_ref,
                "baseline": baseline_ref,
                "baseline_kind": baseline_kind,
                "baseline_source_inventory": inventory_ref,
                "parent_package_manifest": parent_ref,
                "parent_metadata": evidence.reference(parent_metadata_path),
                "actual_run_record": {key: run[key] for key in
                    ("status", "run_id", "scale", "processing", "edge_policy", "parameters", "models") if key in run},
            })
            if baseline_kind == "faithful_previous_hd_package":
                postprocessing["baseline_package_manifest"] = baseline_manifest_ref
            if "postprocessing" in metadata:
                metadata.setdefault("prior_postprocessing", []).append(metadata["postprocessing"])
            metadata["postprocessing"] = postprocessing
            metadata["selected_image"].update({
                "sha256": digest(data), "input": display_path(path),
                "processing_kind": postprocessing["kind"],
            })
            metadata["artistic_status"] = "candidate_for_review"
            metadata["integration_status"] = "pending_engine_validation"
            metadata["integrated_in_ce"] = False
            metadata_data = json_bytes(metadata)
            selected_entry.update({
                "sha256": digest(data), "metadata_sha256": digest(metadata_data),
                "postprocessing": postprocessing["kind"],
            })
        planned[png_relative] = data
        planned[metadata_relative] = metadata_data
        selected.append(selected_entry)
    unchanged = [entry["resource"] for entry in selected if entry["category"] != "walls"]
    if len(unchanged) != 89:
        raise ValueError("The wall-only revision must preserve exactly 89 other resources")
    coverage_path = args.parent_package / parent.get("coverage_file", "coverage.json")
    coverage_data = coverage_path.read_bytes()
    if digest(coverage_data) != parent.get("coverage_sha256"):
        raise ValueError("Parent package coverage hash changed")
    coverage = json.loads(coverage_data.decode("utf-8-sig"))
    coverage.update({
        "integration_status": "pending_engine_validation",
        "coherent_wall_postprocessing_count": 70,
        "wall_only_revision": True,
        "unchanged_parent_png_count": 89,
        "changed_wall_png_count": len(changed_walls),
    })
    planned["coverage.json"] = json_bytes(coverage)
    planned["README.txt"] = (
        "FALLOUT 1 CE — V13ENT STATIC BASE HYBRID TEXTURES, X4\n\n"
        "Status: candidate; engine integration and in-game visual validation pending.\n"
        "Derived from the selected v3 package. All 159 resources remain existing\n"
        "static base art: 57 floor tiles, 70 walls and 32 scenery images.\n\n"
        "This revision prepares all 70 walls through the recorded deterministic\n"
        "ComfyUI coherence workflow: the recorded original/faithful macro baseline\n"
        "with medium detail from the selected v3 donor. Per-wall metadata identifies\n"
        "the actual baseline and its source hash. No new scene geometry is created.\n"
        "The other 89 PNGs and their metadata are copied byte-for-byte from the\n"
        "parent. Existing floor coherence, two hybrid overrides and three faithful\n"
        "mechanical selections remain as recorded in that parent package.\n\n"
        "Every selected image was validated for exact x4 dimensions and original\n"
        "nearest-neighbor alpha. Baselines were checked at their recorded original\n"
        "native or previous HD dimensions. Wall metadata preserves original\n"
        "art provenance and appends actual prompt/workflow/history and input hashes.\n"
        "Assembly copies PNG bytes and performs no artistic image editing.\n\n"
        "Animated doors, critters, items, invisible blockers, exit markers and\n"
        "script-created dependencies remain excluded. No map, prototype, collision,\n"
        "pathfinding, HUD or menu content is changed. This is not the full remaster.\n"
        "A parent resource's previous integration status does not validate this new\n"
        "wall candidate; review seams, lighting and appearance in the actual game.\n"
        "Do not overwrite this version with different bytes; use a new directory.\n"
    ).encode("utf-8")
    existing_manifest = args.output / "manifest.json"
    created = load_json(existing_manifest).get("created_utc") if existing_manifest.is_file() else None
    manifest = dict(parent)
    for key in ("integration", "integration_manifest", "integration_report", "validation",
                "verified_utc", "runtime", "executable_sha256"):
        manifest.pop(key, None)
    manifest.update({
        "version": args.output.name.removeprefix("v"),
        "created_utc": created or datetime.now(timezone.utc).isoformat(),
        "status": "candidate_integration_pending", "artistic_status": "candidate_for_review", "integrated_in_ce": False,
        "parent_package": parent_ref,
        "source_runs": dict(parent["source_runs"], wall_coherent=run_ref),
        "assets": selected,
        "coverage_sha256": digest(planned["coverage.json"]),
        "coherent_wall_postprocessing": {
            "run_manifest": run_ref, "resource_count": 70, "changed_png_count": len(changed_walls),
            "selected_artistic_donor_hashes_verified": True, "processing": run.get("processing"),
            "parameters": run.get("parameters", {}), "baseline_kinds": dict(baseline_kinds),
        },
        "unchanged_parent_resources": {"count": 89, "png_and_metadata_byte_identical": True, "resources": unchanged},
        "all_selected_png_dimensions_and_alpha_validated": True,
        "all_inputs_validated_before_selected_pack_writes": True,
    })
    planned["manifest.json"] = json_bytes(manifest)
    write_immutable_pack(args.output, planned, args.validate_only)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=INVENTORY)
    parser.add_argument("--direct-run", type=Path, default=GENERATION / "direct-atlas")
    parser.add_argument("--floor-run", type=Path, default=GENERATION / "floor-soft")
    parser.add_argument("--rock", type=Path, default=ROCK)
    parser.add_argument("--floor", type=Path, default=FLOOR)
    parser.add_argument("--faithful-package", type=Path, default=FAITHFUL_PACKAGE)
    parser.add_argument("--coherent-run", type=Path,
                        help="Optional completed 57-floor palette/detail preparation; requires a new output version")
    parser.add_argument("--wall-run", type=Path,
                        help="Completed 70-wall coherence run; derive a new package from --parent-package")
    parser.add_argument("--parent-package", type=Path,
                        default=ROOT / "assets/hd/v13ent/v3-hybrid-base-x4")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if args.wall_run:
        if args.coherent_run:
            parser.error("--wall-run inherits parent floors; do not also pass --coherent-run")
        if args.output.resolve() in (OUTPUT.resolve(), args.parent_package.resolve()):
            parser.error("--wall-run requires a new --output version, preserving v2 and the parent")
        assemble_wall_revision(args)
        return
    if args.coherent_run and args.output.resolve() == OUTPUT.resolve():
        parser.error("--coherent-run requires a new --output directory; the v2 package is immutable")
    decoder = load_decoder()
    inventory_data = args.inventory.read_bytes()
    inventory_sha = digest(inventory_data)
    inventory = json.loads(inventory_data.decode("utf-8-sig"))
    rows = decoder.ordered_assets(inventory)
    resources = {row["path"] for row in rows}
    floors = {row["path"] for row in rows if row["category"] == "tiles"}
    evidence = Evidence()
    direct, direct_ref = evidence.run(args.direct_run, 159, inventory_sha)
    floor_run, floor_ref = evidence.run(args.floor_run, 57, inventory_sha)
    if floor_run.get("parent_run_sha256") != direct_ref["sha256"]:
        raise ValueError("Floor edge run does not reference this completed direct-atlas run")
    direct_entries, direct_data = completed_files(args.direct_run, direct, resources)
    floor_entries, floor_data = completed_files(args.floor_run, floor_run, floors)
    for resource in floors:
        if floor_entries[resource].get("parent_output_sha256") != direct_entries[resource]["sha256"]:
            raise ValueError(f"Floor edge parent output mismatch: {resource}")

    coherent = coherent_ref = None
    coherent_entries, coherent_data = {}, {}
    if args.coherent_run:
        coherent, coherent_ref = evidence.run(args.coherent_run, 57, inventory_sha)
        coherent_entries, coherent_data = completed_files(args.coherent_run, coherent, floors)

    overrides = {}
    for resource, path in (("art/scenery/rock03.frm", args.rock), ("art/tiles/cav1000.frm", args.floor)):
        record, run_ref = evidence.run(path.parent)
        data = path.read_bytes()
        if record.get("output_sha256") != digest(data) or record.get("output") != path.name:
            raise ValueError(f"Override output does not match its completed run: {path}")
        for input_record in record.get("inputs", {}).values():
            if isinstance(input_record, dict) and "path" in input_record and "sha256" in input_record:
                actual = evidence.reference(ROOT / input_record["path"])
                if actual["sha256"] != input_record["sha256"]:
                    raise ValueError(f"Override input hash mismatch: {actual['path']}")
        overrides[resource] = (path, data, {
            "kind": "image_gen_material_with_comfy_preparation",
            "run_manifest": run_ref,
            "actual_run_record": record,
            "graph": evidence.graph(path.parent, record.get("prompt_id")),
        })

    previous_manifest_path = args.faithful_package / "manifest.json"
    previous_manifest = load_json(previous_manifest_path)
    previous_manifest_ref = evidence.reference(previous_manifest_path)
    previous_entries = {entry["resource"]: entry for entry in previous_manifest["assets"]}
    faithful_overrides = {}
    for resource, reason in FAITHFUL_MECHANICAL.items():
        if resource not in resources or resource not in previous_entries:
            raise ValueError(f"Faithful mechanical selection is not in both source inventories: {resource}")
        previous_entry = previous_entries[resource]
        path = args.faithful_package / previous_entry["png"]
        data = path.read_bytes()
        if digest(data) != previous_entry["sha256"]:
            raise ValueError(f"Previous HD mechanical output hash changed: {path}")
        previous_metadata_path = args.faithful_package / previous_entry["metadata"]
        metadata_ref = evidence.reference(previous_metadata_path)
        if metadata_ref["sha256"] != previous_entry["metadata_sha256"]:
            raise ValueError(f"Previous mechanical metadata hash changed: {previous_metadata_path}")
        rejected = {"direct_atlas": evidence.reference(direct_data[resource][0])}
        if resource in floors:
            rejected["floor_edge_prepared"] = evidence.reference(floor_data[resource][0])
        faithful_overrides[resource] = (path, data, {
            "kind": "faithful_previous_hd_mechanical",
            "selection_reason": reason,
            "previous_package_manifest": previous_manifest_ref,
            "previous_package_entry": previous_entry,
            "previous_metadata": metadata_ref,
            "actual_previous_metadata_record": load_json(previous_metadata_path),
            "rejected_new_candidates": rejected,
        })

    planned = {}
    selected = []
    for asset_id, row in enumerate(rows, start=1):
        resource = row["path"]
        if Path(resource).is_absolute() or ".." in Path(resource).parts:
            raise ValueError(f"Invalid source resource path: {resource}")
        if resource in overrides:
            path, data, provenance = overrides[resource]
            selection_kind = "individual_hybrid_override"
        elif resource in faithful_overrides:
            path, data, provenance = faithful_overrides[resource]
            selection_kind = "faithful_previous_hd_mechanical"
        elif resource in floors:
            path, data = floor_data[resource]
            provenance = {
                "kind": "direct_sdxl_then_comfy_floor_edges",
                "direct_generation": evidence.atlas_provenance(args.direct_run, direct, direct_ref, direct_entries[resource]),
                "edge_preparation": evidence.atlas_provenance(args.floor_run, floor_run, floor_ref, floor_entries[resource]),
            }
            selection_kind = "floor_edge_prepared"
        else:
            path, data = direct_data[resource]
            provenance = evidence.atlas_provenance(args.direct_run, direct, direct_ref, direct_entries[resource])
            provenance["kind"] = "direct_sdxl_material_refresh"
            selection_kind = "direct_material_refresh"
        postprocessing = None
        if args.coherent_run and resource in floors and resource not in faithful_overrides:
            # The coherent donor must be exactly the art selected above, including
            # cav1000's individual hybrid. Never replace grt2000's faithful grid.
            coherent_entry = coherent_entries[resource]
            donor_hash = digest(data)
            if coherent_entry.get("donor_sha256") != donor_hash:
                raise ValueError(f"Coherent floor donor differs from selected artistic input: {resource}")
            donor_path = Path(coherent_entry["donor_path"])
            if not donor_path.is_absolute():
                donor_path = ROOT / donor_path
            if evidence.reference(donor_path)["sha256"] != donor_hash:
                raise ValueError(f"Recorded coherent floor donor file changed: {resource}")
            baseline_path = Path(coherent_entry["baseline_path"])
            if not baseline_path.is_absolute():
                baseline_path = ROOT / baseline_path
            baseline_ref = evidence.reference(baseline_path)
            if baseline_ref["sha256"] != coherent_entry.get("baseline_sha256"):
                raise ValueError(f"Recorded coherent floor baseline file changed: {resource}")
            postprocessing = evidence.atlas_provenance(args.coherent_run, coherent, coherent_ref, coherent_entry)
            postprocessing.update({
                "kind": "coherent_floor_palette_and_medium_detail",
                "selected_artistic_donor": {"path": display_path(path), "sha256": donor_hash,
                                            "selection": selection_kind},
                "baseline": baseline_ref,
                "actual_run_record": {key: coherent[key] for key in (
                    "status", "run_id", "scale", "seed", "steps", "denoise", "processing", "edge_policy", "parameters", "models")
                    if key in coherent},
            })
            path, data = coherent_data[resource]
        width, height, pixels = decoder.decode_rgba8(data)
        if (width, height) != (row["width"] * 4, row["height"] * 4):
            raise ValueError(f"Selected image has incorrect dimensions: {path}")
        original_data = (args.inventory.parent / row["rgba_png"]).read_bytes()
        if digest(original_data) != row["rgba_png_sha256"]:
            raise ValueError(f"Original RGBA source hash changed: {resource}")
        original_width, original_height, original = decoder.decode_rgba8(original_data)
        if (original_width, original_height) != (row["width"], row["height"]):
            raise ValueError(f"Original geometry differs from inventory: {resource}")
        if not decoder.exact_scaled_alpha(pixels, original, row["width"], row["height"]):
            raise ValueError(f"Selected image does not preserve exact original NN alpha: {path}")
        png_relative = resource + ".png"
        metadata_relative = "metadata/" + resource + ".json"
        fids = [(4 << 24) | tile_id for tile_id in row["tile_art_ids"]] if row["category"] == "tiles" else row["fids"]
        metadata = {
            "resource": resource, "asset_id": asset_id,
            "source": row,
            "selected_image": {"path": png_relative, "sha256": digest(data), "dimensions": [width, height],
                               "input": display_path(path), "scale": 4, "selection": selection_kind},
            "registration": row["registration"],
            "alpha_exact_original_nearest_neighbor": True,
            "provenance": provenance,
            "artistic_status": "candidate_for_review",
            "integration_status": "pending_engine_validation",
            "integrated_in_ce": False,
        }
        if postprocessing is not None:
            # Keep the original artistic provenance intact and append the actual
            # deterministic preparation with its donor, baseline and graph hashes.
            metadata["postprocessing"] = postprocessing
            metadata["selected_image"]["processing_kind"] = postprocessing["kind"]
        metadata_data = json_bytes(metadata)
        planned[png_relative] = data
        planned[metadata_relative] = metadata_data
        selected.append({"asset_id": asset_id, "resource": resource, "category": row["category"], "fids": fids,
                         "png": png_relative, "sha256": digest(data), "native_dimensions": [row["width"], row["height"]],
                         "dimensions": [width, height], "metadata": metadata_relative,
                         "metadata_sha256": digest(metadata_data), "selection": selection_kind})
        if postprocessing is not None:
            selected[-1]["postprocessing"] = postprocessing["kind"]

    coverage = dict(inventory["coverage"])
    coverage.update({
        "scope": "Existing static V13ENT base art only: 57 floor, 70 wall and 32 scenery resources",
        "selected_asset_count": len(selected),
        "selected_existing_object_instances": 603,
        "selected_existing_floor_cells": 7549,
        "new_objects_or_decorations": False,
        "maps_or_prototypes_modified": False,
        "integration_status": "pending_engine_validation",
        "exclusions": ["Two animated vault-door resources v13secur.frm and v13secr2.frm",
                       "Critters and their animations", "Items including v13bones, knife and ammo",
                       "1x1 engine blockers and misc/exit-grid markers", "Script-created dependencies",
                       "Other maps, HUD and menu artwork"],
        "limitations": ["Map references do not guarantee screen visibility; runtime flags, occlusion and lighting still apply.",
                        "Animated and script-created dependencies are excluded from this static base subset.",
                        "This selected artistic candidate does not itself prove successful CE integration."],
    })
    if args.coherent_run:
        coverage["coherent_floor_postprocessing_count"] = sum("postprocessing" in entry for entry in selected)
        coverage["coherent_floor_excluded_faithful_resources"] = sorted(floors.intersection(faithful_overrides))
    planned["coverage.json"] = json_bytes(coverage)
    planned["README.txt"] = (
        "FALLOUT 1 CE — V13ENT STATIC BASE HYBRID TEXTURES, X4\n\n"
        "Status: artistic candidate; engine integration and in-game validation pending.\n"
        "159 existing resources: 57 floor tiles, 70 walls, 32 scenery images.\n"
        "99 new direct ComfyUI/SDXL outputs, 55 new floor-edge-prepared outputs,\n"
        "two individual ImageGen + ComfyUI overrides (rock03 and cav1000), and\n"
        "three faithful previous HD mechanical resources. This is 154 new Comfy\n"
        "resources + two individual hybrids + three preserved prior HD outputs.\n"
        "grt2000 retains its cross-grid grating; doorcomp retains its display and\n"
        "buttons; v13secr3 retains its sill and pillar panel structure/shading.\n"
        "The stronger new mechanical candidates were rejected for those changes.\n"
        "Original canvas, frame offsets and exact nearest-neighbor alpha are retained.\n"
        "The assembly only copies validated PNG bytes; it performs no artistic edits.\n\n"
        "This package does not replace animated doors, critters, items, invisible\n"
        "blockers, exit markers or script-created dependencies. It does not add\n"
        "decorations, alter maps/prototypes or change collision and pathfinding.\n"
        "This is the static base subset of the first cave, not the complete remaster.\n\n"
        "Per-resource metadata contains original inventory records, selected hashes,\n"
        "actual generation run references, Comfy prompt IDs and workflow/API/history hashes.\n"
        "Review visual quality in the actual map, especially wall/floor seams and lighting.\n"
        "Do not overwrite this version with different bytes; use a new version directory.\n"
    ).encode("utf-8")
    if args.coherent_run:
        planned["README.txt"] += (
            "\nFINAL FLOOR PREPARATION\n"
            "56 floor assets, including the cav1000 hybrid, use the completed\n"
            "floor-coherent Comfy preparation for baseline palette, medium detail\n"
            "and gradual edge blending. grt2000 keeps its faithful previous HD grid.\n"
            "The source selection counts above describe artistic donors; per-asset\n"
            "postprocessing records the final PNG, actual graph and verified input hashes.\n"
        ).encode("utf-8")
    existing_manifest = args.output / "manifest.json"
    created = load_json(existing_manifest).get("created_utc") if existing_manifest.is_file() else None
    manifest = {
        "schema_version": 1,
        "version": args.output.name.removeprefix("v") if args.coherent_run else "2-hybrid-base-x4",
        "component": "v13ent-cave",
        "created_utc": created or datetime.now(timezone.utc).isoformat(),
        "status": "candidate_integration_pending", "artistic_status": "candidate_for_review", "integrated_in_ce": False,
        "scale": 4, "asset_count": len(selected), "category_counts": dict(Counter(row["category"] for row in rows)),
        "selection_counts": dict(Counter(entry["selection"] for entry in selected)),
        "source_inventory": evidence.reference(args.inventory),
        "original_map": inventory["map"],
        "source_runs": {"direct_atlas": direct_ref, "floor_edges": floor_ref,
                        "rock03_override": overrides["art/scenery/rock03.frm"][2]["run_manifest"],
                        "cav1000_override": overrides["art/tiles/cav1000.frm"][2]["run_manifest"]},
        "faithful_mechanical_source_package": previous_manifest_ref,
        "faithful_mechanical_selection_reasons": FAITHFUL_MECHANICAL,
        "coverage_file": "coverage.json", "coverage_sha256": digest(planned["coverage.json"]),
        "all_selected_png_dimensions_and_alpha_validated": True,
        "all_inputs_validated_before_selected_pack_writes": True,
        "assets": selected,
    }
    if args.coherent_run:
        manifest["source_runs"]["floor_coherent"] = coherent_ref
        manifest["coherent_floor_postprocessing"] = {
            "run_manifest": coherent_ref,
            "resource_count": sum("postprocessing" in entry for entry in selected),
            "faithful_exclusions": sorted(floors.intersection(faithful_overrides)),
            "selected_artistic_donor_hashes_verified": True,
            "processing": coherent.get("processing"),
            "parameters": coherent.get("parameters", {}),
        }
    planned["manifest.json"] = json_bytes(manifest)

    # Inspect every prospective conflict before the first directory/file write.
    conflicts = [relative for relative, data in planned.items()
                 if (args.output / relative).exists() and (args.output / relative).read_bytes() != data]
    if conflicts:
        raise ValueError(f"Existing different selected-pack files preserved; choose a new version: {conflicts}")
    if args.validate_only:
        print(f"Validated all 159 selected resources and provenance; no files written. Destination: {args.output}")
        return
    created_files = 0
    for relative, data in planned.items():
        destination = args.output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if destination.read_bytes() != data:
                raise ValueError(f"Selected-pack file changed after validation; preserved: {destination}")
            continue
        with destination.open("xb") as stream:
            stream.write(data)
        created_files += 1
    print(f"Assembled 159 validated static resources; {created_files} new files: {args.output}")


if __name__ == "__main__":
    main()
