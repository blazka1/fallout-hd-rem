"""Record the selected static/frame cave package against its protected baseline."""
from pathlib import Path
from datetime import datetime, timezone
import difflib
import argparse
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "build/hd-world-pilot"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--preview', default='build/hd-world-pilot/preview/perf-light-v4')
parser.add_argument('--package', default='assets/hd/v13ent/v3-hybrid-base-x4')
parser.add_argument('--benchmark-before')
parser.add_argument('--benchmark-after')
parser.add_argument('--frame-fallback', help='Completed exact-frame fallback run directory')
parser.add_argument('--wall-variant-fallback', help='Completed wall appearance fallback run directory')
parser.add_argument('--decor-fallback', help='Completed render-only decoration fallback run directory')
args = parser.parse_args()
if bool(args.benchmark_before) != bool(args.benchmark_after):
    parser.error('--benchmark-before and --benchmark-after must be provided together')


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


baseline = read(OUT / "shared-baseline-hashes.json")
protected = [item for item in baseline["files"] if item["path"].startswith("fallout1-ce-main/")
             or item["path"].lower().endswith(".exe") or "/data/art/hd/main-menu/" in item["path"]]
changed_originals = [item["path"] for item in protected
                     if sha(ROOT / item["path"]) != item["sha256"].upper()]
if changed_originals:
    raise SystemExit(f"Protected original files changed: {changed_originals}")

original = ROOT / "fallout1-ce-main"
pilot = ROOT / "work/hd-world-pilot/fallout1-ce-main"
changes, patch = [], []
for path in sorted(pilot.rglob("*")):
    if not path.is_file():
        continue
    relative = path.relative_to(pilot)
    source = original / relative
    data = path.read_bytes()
    if source.exists() and source.read_bytes() == data:
        continue
    changes.append({"path": relative.as_posix(), "sha256": sha(path),
                    "kind": "modified" if source.exists() else "added"})
    old = source.read_text(encoding="utf-8-sig").splitlines(True) if source.exists() else []
    new = data.decode("utf-8-sig").splitlines(True)
    patch.extend(difflib.unified_diff(old, new,
        fromfile="a/" + relative.as_posix() if source.exists() else "/dev/null",
        tofile="b/" + relative.as_posix()))
(OUT / "pilot-changes.patch").write_text("".join(patch), encoding="utf-8")

exe_hash = sha(ROOT / "runtime/hd-world-pilot/fallout-ce.exe")
world = read(ROOT / args.preview / "manifest.json")
menu = read(OUT / "menu-regression/manifest.json")
assert exe_hash == world["executable_sha256"] == menu["executable_sha256"]
assert world["result"]["failed"] == menu["failed"] == 0
fallback_path = sorted((OUT / "fallback").glob("*/manifest.json"))[-1]
fallback = read(fallback_path)
assert fallback["completed_cases"] >= 3 and fallback["assets_restored_and_hash_verified"]
for case in fallback["cases"]:
    assert case["result"]["failed"] == 0
    assert read(Path(case["output"]) / "manifest.json")["executable_sha256"] == exe_hash
package = read(ROOT / args.package / "manifest.json")
inventory = read(ROOT / "assets/generated/v13ent-cave/v1-20261111/sources/manifest.json")
selected_assets = package["assets"]
variants = package.get('variants', [])
decorations = package.get('decorations', [])
image_count = package.get('total_image_count', package['asset_count'])
assert len(selected_assets) + len(variants) + len(decorations) == image_count
assert len({entry["asset_id"] for entry in selected_assets + variants + decorations}) == image_count
assert world["result"]["loaded_resources"] == image_count
resources = list(dict.fromkeys(entry["resource"] for entry in selected_assets))
resource_frames = {resource: [entry.get("frame", 0) for entry in selected_assets
                              if entry["resource"] == resource] for resource in resources}
animated_resources = [resource for resource, frames in resource_frames.items()
                      if len(frames) > 1 or any(frame != 0 for frame in frames)]
static_count = len(resources) - len(animated_resources)
animated_frame_count = sum(len(resource_frames[resource]) for resource in animated_resources)
assert image_count == static_count + animated_frame_count + len(variants) + len(decorations)
for field, actual in (("static_resource_count", static_count),
                      ("animated_resource_count", len(animated_resources)),
                      ("animated_frame_count", animated_frame_count)):
    if field in package:
        assert package[field] == actual, (field, package[field], actual)
for resource, frames in resource_frames.items():
    assert len(set(frames)) == len(frames), f"Duplicate selected frame: {resource}"
coverage = read(ROOT / args.package / package.get("coverage_file", "coverage.json"))
if "coverage_sha256" in package:
    assert sha(ROOT / args.package / package.get("coverage_file", "coverage.json")) == package["coverage_sha256"].upper()
classic_doors = [resource for resource in ("art/scenery/v13secr2.frm", "art/scenery/v13secur.frm")
                 if resource not in resources]
scope_limit = f"{static_count} static resources"
if animated_resources:
    scope_limit += f" plus {animated_frame_count} frames of {len(animated_resources)} animated resource(s)"
scope_limit += f"; {len(resources)} distinct original FRM resources, {image_count} selected images."
if variants:
    scope_limit += f" Includes {len(variants)} optional appearances for {len({v['base_asset_id'] for v in variants})} existing cave wall resources."
if decorations:
    scope_limit += f" Includes {len(decorations)} new render-only floor decorations with no Object/PID/FID or collision data."
if classic_doors:
    scope_limit += " Door resources remaining classic: " + ", ".join(classic_doors) + "."
scope_limit += " Critters, items and HUD remain classic."
report = {
    "recorded_utc": datetime.now(timezone.utc).isoformat(),
    "status": "integrated_and_verified_in_isolated_ce_pilot",
    "map": "V13ENT.MAP", "saved_map_name_supported": "V13ENT.SAV",
    "selected_resources": resources,
    "resource_count": len(resources), "selected_image_count": image_count,
    "wall_variant_image_count": len(variants), "wall_variant_resources": len({v['base_asset_id'] for v in variants}),
    "decoration_image_count": len(decorations), "decoration_placements": package.get('decoration_placements', []),
    "static_resource_count": static_count, "animated_resource_count": len(animated_resources),
    "animated_frame_count": animated_frame_count,
    "selected_animation_frames": [{"resource": resource, "frames": sorted(resource_frames[resource]),
                                    "asset_ids": [entry["asset_id"] for entry in selected_assets
                                                  if entry["resource"] == resource]}
                                   for resource in animated_resources],
    "coverage": coverage, "static_source_coverage": inventory["coverage"],
    "selected_package": args.package,
    "selected_package_manifest_sha256": sha(ROOT / args.package / "manifest.json"),
    "density": "adaptive 1x-4x, master images x4", "replaces_existing_instances_only": not bool(decorations),
    "new_game_objects_created": False, "original_map_and_prototypes_modified": False,
    "source": "work/hd-world-pilot/fallout1-ce-main",
    "runtime": "runtime/hd-world-pilot", "launcher": "Start-Fallout-HD-World-Pilot.cmd",
    "executable_sha256": exe_hash,
    "protected_original_files_verified_unchanged": len(protected),
    "protection_scope": "Original sources, menu art and EXEs. Mutable config/automap state is excluded after user played the original runtime.",
    "source_changes": changes, "review_patch": "build/hd-world-pilot/pilot-changes.patch",
    "world_checks": world["result"], "menu_checks": {"passed": menu["passed"], "failed": menu["failed"]},
    "fallback_checks": {"passed": sum(case["result"]["passed"] for case in fallback["cases"]),
                        "failed": 0, "report": fallback_path.relative_to(ROOT).as_posix()},
    "preview": args.preview + "/entrance-hd.png",
    "comparison_key": "F11 in V13ENT; no map/object/pathfinding state changes",
    "limits": [
        scope_limit,
        "Existing FRM resources retain original binary silhouette and registration. New decoration silhouettes are binary at native logical coordinates, with no original FRM registration.",
        "Map light is stored independently of source color; a common interpolated palette transfer handles fades/gamma. RGB lighting approximates the original indexed table without reintroducing its quantization.",
        "Egg/translucent compositing uses exact classic pixels in the affected area.",
        "Art remains a trial candidate; this report verifies integration, not final artistic approval.",
        "Static wall-strip joins remain visible at 1080p in dark diagonal hatching; broad material bands are reduced, not eliminated.",
        "Performance timings are hidden-window CPU wall time through renderPresent, not a guarantee of fixed gameplay FPS; 4K scrolling remains more expensive than 1080p.",
    ],
}
if animated_resources:
    report["limits"].append("Animation verification renders each original frame and restores game state; it is not a timed interactive door-script playthrough.")
if args.frame_fallback:
    frame_fallback_path = ROOT / args.frame_fallback / "manifest.json"
    frame_fallback = read(frame_fallback_path)
    assert frame_fallback["executable_sha256"] == exe_hash
    assert frame_fallback["completed_cases"] == 3
    assert frame_fallback["registry_restored_and_hash_verified"]
    assert frame_fallback["failed"] == 0 and frame_fallback["comparison_checks"]["passed"] == 3
    for case in frame_fallback["cases"]:
        assert case["result"]["failed"] == 0
        assert read(Path(case["output"]) / "manifest.json")["executable_sha256"] == exe_hash
    report["frame_fallback_checks"] = {
        "passed": frame_fallback["passed"], "failed": frame_fallback["failed"],
        "report": frame_fallback_path.relative_to(ROOT).as_posix(),
        "scope": "Real rock03 frame-zero drawing with only frame7 registered matches a floor-only classic-rock control; explicit frame0 is the positive control.",
    }
if args.wall_variant_fallback:
    variant_path = ROOT / args.wall_variant_fallback / 'manifest.json'
    variant_result = read(variant_path)
    assert variant_result['executable_sha256'] == exe_hash
    assert variant_result['failed'] == 0 and variant_result['restored_and_hash_verified']
    assert len(variant_result['cases']) == 5 and len(variant_result['comparisons']) == 12
    report['wall_variant_fallback_checks'] = {'passed': variant_result['passed'], 'failed': 0,
        'report': variant_path.relative_to(ROOT).as_posix(),
        'scope': 'Missing file, invalid header, fractional alpha and changed binary silhouette reproduce the omitted-slot base-texture control exactly; remaining slots stay in place.'}
if args.decor_fallback:
    decor_path = ROOT / args.decor_fallback / 'manifest.json'
    result = read(decor_path)
    assert result['executable_sha256'] == exe_hash and result['failed'] == 0
    assert result['restored_and_hash_verified'] and len(result['cases']) == 4
    assert len(result['comparisons']) == 9
    report['decoration_fallback_checks'] = {'passed': result['passed'], 'failed': 0,
        'report': decor_path.relative_to(ROOT).as_posix(),
        'scope': 'Missing file, invalid alpha and invalid header omit only that decoration and reproduce the omitted-asset control pixel exactly.'}
    review_path = ROOT / args.preview / 'qa/review.json'
    report['decoration_visual_checks'] = read(review_path)
    assert world['result']['decoration_images'] == len(decorations) == 4
    assert world['result']['decoration_placements'] == len(package['decoration_placements']) == 4
if args.benchmark_before and args.benchmark_after:
    before = read(ROOT / args.benchmark_before / 'manifest.json')
    after = read(ROOT / args.benchmark_after / 'manifest.json')
    assert after['executable_sha256'] == exe_hash
    assert before['result']['failed'] == after['result']['failed'] == 0
    for field in ('map', 'camera_tile', 'logical_width', 'logical_height', 'warmup_frames', 'sample_count'):
        assert before['result'][field] == after['result'][field], f"Benchmark conditions differ: {field}"
    timings = []
    for old in before['result']['rows']:
        if old['mode'] != 'hd_enabled':
            continue
        new = next(row for row in after['result']['rows']
                   if row['actual_width'] == old['actual_width']
                   and row['actual_height'] == old['actual_height']
                   and row['mode'] == old['mode'] and row['workload'] == old['workload'])
        assert new['renderer'] == old['renderer']
        timings.append({'resolution': [old['actual_width'], old['actual_height']],
                        'workload': old['workload'], 'before_median_ms': old['median_ms'],
                        'after_median_ms': new['median_ms'], 'before_p95_ms': old['p95_ms'],
                        'after_p95_ms': new['p95_ms']})
    report['performance'] = {'before': args.benchmark_before, 'after': args.benchmark_after,
                             'before_label': before.get('label'), 'after_label': after.get('label'),
                             'before_executable_sha256': before['executable_sha256'],
                             'after_executable_sha256': after['executable_sha256'],
                             'before_registry_sha256': before.get('registry_sha256'),
                             'after_registry_sha256': after.get('registry_sha256'),
                             'scope': after['result']['scope'], 'timings': timings,
                             'comparison_note': 'Measured before/after runs may differ in artwork and renderer code. The comparison does not isolate one cause or measure timed door animation.',
                             'renderer_features': 'MSVC /O2 and NDEBUG; cached ownership/light, partial updates, translated scroll cache, continuous light transfer; exact optional registry frame lookup'}
(OUT / "integration-manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Verified {len(protected)} protected originals; {len(changes)} isolated source changes.")
print(OUT / "integration-manifest.json")
