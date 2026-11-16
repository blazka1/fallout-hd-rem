"""Register an eight-frame directional art sheet through ComfyUI.

Python orchestrates, reads source masks/metadata and evaluates outputs only.
ComfyUI performs all actual crops, resampling, alpha joins and file renders.
Registered soft-alpha frames are primary. Source-mask variants are diagnostic
candidates only: an exact alpha mask does not prove correctly drawn anatomy.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
import urllib.parse
import uuid

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/asset-pipeline"))
from comfy_menu import request

spec = importlib.util.spec_from_file_location("hd_v1_helpers", Path(__file__).with_name("prepare-hd-v1.py"))
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)

REF = ROOT / "assets/reference/player-male-vault13"
META = REF / "metadata/art/critters/hmjmpsab.frm.json"
DIRECTIONS = ["NE", "E", "SE", "SW", "W", "NW"]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    helpers.save_json(path, value)


def original_frame(direction, frame):
    return REF / f"rgba/art/critters/hmjmpsab.frm/d{direction}-f{frame:03}.png"


def bbox(alpha, threshold):
    yy, xx = np.nonzero(alpha >= threshold)
    if len(xx) < 1:
        return None
    return [int(xx.min()), int(yy.min()), int(xx.max()) + 1, int(yy.max()) + 1]


def mask_metrics(generated, target):
    intersection = int((generated & target).sum())
    union = int((generated | target).sum())
    gcount, tcount = int(generated.sum()), int(target.sum())
    return {"iou": intersection / max(1, union),
            "target_coverage": intersection / max(1, tcount),
            "generated_spill_fraction": int((generated & ~target).sum()) / max(1, gcount),
            "missing_target_pixels": int((target & ~generated).sum()),
            "spill_pixels": int((generated & ~target).sum()),
            "intersection_pixels": intersection, "union_pixels": union}


def analyze(args):
    master = Image.open(args.source)
    if "A" not in master.getbands():
        raise ValueError("Generated master must have genuine alpha.")
    pixels = np.asarray(master.convert("RGBA"))
    h, w = pixels.shape[:2]
    alpha = pixels[:, :, 3]
    if np.count_nonzero(alpha < 16) < w * h * 0.05:
        raise ValueError("Master background is not sufficiently transparent.")
    metadata = json.loads(META.read_text(encoding="utf-8"))
    cells = json.loads(args.cells_json.read_text(encoding="utf-8")) if args.cells_json else [
        [round(col * w / 4), round(row * h / 2),
         round((col + 1) * w / 4) - round(col * w / 4),
         round((row + 1) * h / 2) - round(row * h / 2)]
        for row in range(2) for col in range(4)]
    if len(cells) != metadata["frame_count"]:
        raise ValueError("Exactly eight cells in playback order are required.")
    original_cells = next(s["cells"] for s in metadata["sheets"] if s["direction"] == args.direction)
    entries = []
    for frame_index, cell in enumerate(cells):
        x, y, cw, ch = [int(v) for v in cell]
        if min(x, y) < 0 or min(cw, ch) < 1 or x + cw > w or y + ch > h:
            raise ValueError(f"Invalid cell {frame_index}: {cell}")
        cell_alpha = alpha[y:y + ch, x:x + cw]
        box = bbox(cell_alpha, args.alpha_threshold)
        if box is None or np.count_nonzero(cell_alpha >= args.alpha_threshold) < 100:
            raise ValueError(f"Cell {frame_index} empty or too small.")
        bx, by, br, bb = box
        if min(bx, by, cw - br, ch - bb) < 2:
            raise ValueError(f"Figure touches cell {frame_index} boundary; supply --cells-json or repair master.")
        original_path = original_frame(args.direction, frame_index)
        original = Image.open(original_path).convert("RGBA")
        original_pixels = np.asarray(original)
        original_box = bbox(original_pixels[:, :, 3], 1)
        ox, oy, ore, obe = original_box
        source_crop = [x + bx, y + by, br - bx, bb - by]
        target_size = [(ore - ox) * args.scale, (obe - oy) * args.scale]
        sx, sy = target_size[0] / source_crop[2], target_size[1] / source_crop[3]
        # Analysis-only estimate. No output artwork is written with Pillow.
        estimate = np.asarray(Image.fromarray(cell_alpha[by:bb, bx:br]).resize(tuple(target_size), Image.Resampling.LANCZOS)) >= 128
        target = np.repeat(np.repeat(original_pixels[:, :, 3] > 0, args.scale, 0), args.scale, 1)
        estimated_canvas = np.zeros_like(target)
        estimated_canvas[oy * args.scale:obe * args.scale, ox * args.scale:ore * args.scale] = estimate
        original_cell = original_cells[frame_index]
        entries.append({
            "frame_index": frame_index, "source_cell": cell,
            "generated_crop": source_crop, "generated_alpha_threshold": args.alpha_threshold,
            "generated_alpha_max": int(cell_alpha.max()),
            "original": str(original_path), "original_sha256": sha(original_path.read_bytes()),
            "native_dimensions": list(original.size),
            "dimensions": [original.width * args.scale, original.height * args.scale],
            "target_bbox_native": original_box, "target_content_dimensions": target_size,
            "transform": {"scale_x": sx, "scale_y": sy, "x_to_y_ratio": sx / sy,
                          "anisotropy_factor": max(sx, sy) / min(sx, sy),
                          "method": "bbox affine fit; differing axis scales explicitly retained"},
            "frame_shift_logical": [original_cell["shift_x"], original_cell["shift_y"]],
            "direction_offset_logical": [metadata["direction_x"][args.direction], metadata["direction_y"][args.direction]],
            "estimated_pre_mask": mask_metrics(estimated_canvas, target),
            "estimated_pre_mask_upper_half": mask_metrics(estimated_canvas[:target.shape[0] // 2], target[:target.shape[0] // 2]),
            "estimated_pre_mask_lower_half": mask_metrics(estimated_canvas[target.shape[0] // 2:], target[target.shape[0] // 2:]),
            "registered_file": f"registered-f{frame_index:03}.png",
            "source_mask_file": f"source-mask-f{frame_index:03}.png",
        })
    return metadata, [w, h], entries


def build_prompt(args, entries, client_id, schemas):
    graph = {}

    def node(kind, **inputs):
        if kind not in schemas:
            raise ValueError("Missing ComfyUI node: " + kind)
        key = str(len(graph) + 1)
        graph[key] = {"class_type": kind, "inputs": inputs}
        return [key, 0]

    def resize(image, width, height, method="lanczos"):
        return node("ImageScale", image=image, upscale_method=method, width=width, height=height, crop="disabled")

    def paste(destination, source, x, y):
        return node("ImageCompositeMasked", destination=destination, source=source, x=x, y=y, resize_source=False)

    loaded = node("LoadImage", image=helpers.upload(args.base, args.source, client_id))
    generated_opacity = node("MaskToImage", mask=node("InvertMask", mask=[loaded[0], 1]))
    for entry in entries:
        frame = entry["frame_index"]
        x, y, w, h = entry["generated_crop"]
        tw, th = entry["target_content_dimensions"]
        ow, oh = entry["dimensions"]
        ox, oy = [v * args.scale for v in entry["target_bbox_native"][:2]]
        rgb = resize(node("ImageCrop", image=loaded, x=x, y=y, width=w, height=h), tw, th)
        alpha = resize(node("ImageCrop", image=generated_opacity, x=x, y=y, width=w, height=h), tw, th)
        black = node("EmptyImage", width=ow, height=oh, batch_size=1, color=0)
        full_rgb = paste(black, rgb, ox, oy)
        full_alpha = node("ImageToMask", image=paste(black, alpha, ox, oy), channel="red")
        registered = node("JoinImageWithAlpha", image=full_rgb, alpha=node("InvertMask", mask=full_alpha))
        entry["registered_save_node"] = node("SaveImage", images=registered,
            filename_prefix=f"fallout1_player_male/{client_id}/registered-f{frame:03}")[0]
        original = node("LoadImage", image=helpers.upload(args.base, Path(entry["original"]), client_id + f"-source-f{frame:03}"))
        original_opacity = node("MaskToImage", mask=node("InvertMask", mask=[original[0], 1]))
        original_alpha = node("ImageToMask", image=resize(original_opacity, ow, oh, "nearest-exact"), channel="red")
        candidate = node("JoinImageWithAlpha", image=full_rgb, alpha=node("InvertMask", mask=original_alpha))
        entry["source_mask_save_node"] = node("SaveImage", images=candidate,
            filename_prefix=f"fallout1_player_male/{client_id}/source-mask-f{frame:03}")[0]
    return graph


def fetch_outputs(args, run, record):
    manifest_entries = []
    for entry in run["entries"]:
        result = dict(entry)
        outputs = {}
        for kind in ["registered", "source_mask"]:
            remote = record["outputs"][entry[kind + "_save_node"]]["images"][0]
            data = request(args.base, "/view?" + urllib.parse.urlencode(remote))
            target = args.output / entry[kind + "_file"]
            if target.exists() and target.read_bytes() != data:
                raise FileExistsError("Refusing to replace different result: " + str(target))
            target.write_bytes(data)
            image = Image.open(target)
            if image.mode != "RGBA" or list(image.size) != entry["dimensions"]:
                raise ValueError(f"Unexpected output mode/dimensions: {target}")
            rgba = np.asarray(image)
            outputs[kind] = rgba
            result[kind + "_sha256"] = sha(data)
        original_alpha = np.asarray(Image.open(entry["original"]).convert("RGBA"))[:, :, 3]
        exact_alpha = np.repeat(np.repeat(original_alpha, args.scale, 0), args.scale, 1)
        if not np.array_equal(outputs["source_mask"][:, :, 3], exact_alpha):
            raise ValueError("Source-mask diagnostic is not an exact original mask: " + str(entry["frame_index"]))
        generated = outputs["registered"][:, :, 3] >= 128
        target = exact_alpha > 0
        lower = target.shape[0] // 2
        result["qa"] = {
            "dimensions_match": True,
            "registered_alpha_range": [int(outputs["registered"][:, :, 3].min()), int(outputs["registered"][:, :, 3].max())],
            "pre_mask": mask_metrics(generated, target),
            "pre_mask_lower_half": mask_metrics(generated[lower:], target[lower:]),
            "pre_mask_upper_half": mask_metrics(generated[:lower], target[:lower]),
            "source_mask_exact": True,
            "source_mask_warning": "Exact alpha is imposed, not evidence of correct anatomy or costume registration.",
            "region_note": "Upper/lower half refer to raster rows, not a semantic body/shadow segmentation. Original ground shadow is included in whole-mask metrics.",
        }
        result["status"] = "registered_art_pending_visual_pose_and_temporal_review"
        manifest_entries.append(result)
    manifest = {
        "status": "registered_walk_art_candidates", "direction_index": args.direction,
        "direction": DIRECTIONS[args.direction], "source": str(args.source),
        "source_sha256": run["source_sha256"], "source_dimensions": run["source_dimensions"],
        "scale": args.scale, "fps": run["fps"], "frame_count": len(manifest_entries),
        "action_frame": run["action_frame"], "prompt_id": run["prompt_id"],
        "workflow": "workflow.json", "api_prompt": "prompt-api.json", "entries": manifest_entries,
        "registration_note": "Native canvas dimensions, frame shifts and direction offsets retained. Pixel fit does not prove exact pose or temporal consistency.",
        "source_mask_status": "diagnostic candidates only; not automatically accepted",
        "runtime_installed": False,
    }
    save(args.output / "manifest.json", manifest)
    save(args.output / "qa.json", {
        "direction_index": args.direction,
        "mean_pre_mask_iou": float(np.mean([e["qa"]["pre_mask"]["iou"] for e in manifest_entries])),
        "min_pre_mask_iou": min(e["qa"]["pre_mask"]["iou"] for e in manifest_entries),
        "max_anisotropy": max(e["transform"]["anisotropy_factor"] for e in manifest_entries),
        "frames": [{"frame": e["frame_index"], "transform": e["transform"], **e["qa"]} for e in manifest_entries],
    })
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--direction", type=int, choices=range(6), required=True)
    parser.add_argument("--scale", type=int, choices=[2, 4, 6, 8], default=4)
    parser.add_argument("--base", default="http://127.0.0.1:8188")
    parser.add_argument("--alpha-threshold", type=int, default=8)
    parser.add_argument("--cells-json", type=Path)
    parser.add_argument("--analyze-only", action="store_true")
    parser.add_argument("--timeout", type=float, default=300)
    args = parser.parse_args()
    args.source, args.output = args.source.resolve(), args.output.resolve()
    if not 1 <= args.alpha_threshold <= 128:
        parser.error("Alpha threshold must be 1..128.")
    metadata, dimensions, entries = analyze(args)
    if args.analyze_only:
        print(json.dumps({"source_dimensions": dimensions, "direction": args.direction,
                          "entries": entries}, indent=2))
        return
    args.output.mkdir(parents=True, exist_ok=True)
    run_path = args.output / "run.json"
    source_hash = sha(args.source.read_bytes())
    if run_path.exists():
        run = json.loads(run_path.read_text(encoding="utf-8"))
        if (run["source_sha256"], run["direction_index"], run["scale"]) != (source_hash, args.direction, args.scale):
            raise ValueError("Existing run differs; choose a new output directory.")
        if [e["generated_crop"] for e in entries] != [e["generated_crop"] for e in run["entries"]]:
            raise ValueError("Existing crop settings differ; choose a new output directory.")
        if [e["original_sha256"] for e in entries] != [e["original_sha256"] for e in run["entries"]] or run["source_metadata_sha256"] != sha(META.read_bytes()):
            raise ValueError("Original reference data changed; inspect before resuming.")
        pid = run.get("prompt_id") or helpers.recover_prompt(args.base, run["client_id"])
        if not pid:
            raise RuntimeError("Prior submission uncertain; inspect queue/history. No duplicate sent.")
        run["prompt_id"] = pid
        save(run_path, run)
    else:
        queue = request(args.base, "/queue")
        if queue["queue_running"] or queue["queue_pending"]:
            raise RuntimeError("ComfyUI busy; wait without cancelling another task.")
        schemas = request(args.base, "/object_info")
        client_id = f"male-walk-d{args.direction}-" + uuid.uuid4().hex
        graph = build_prompt(args, entries, client_id, schemas)
        ui_workflow = helpers.workflow(graph, schemas)
        save(args.output / "prompt-api.json", graph)
        save(args.output / "workflow.json", ui_workflow)
        queue = request(args.base, "/queue")
        if queue["queue_running"] or queue["queue_pending"]:
            raise RuntimeError("ComfyUI became busy; no job submitted.")
        run = {"status": "submission_pending", "client_id": client_id,
               "source": str(args.source), "source_sha256": source_hash, "source_dimensions": dimensions,
               "direction_index": args.direction, "scale": args.scale,
               "fps": metadata["fps"], "action_frame": metadata["action_frame"],
               "source_metadata": str(META), "source_metadata_sha256": sha(META.read_bytes()),
               "entries": entries, "stage": "registration experiment, not runtime installation"}
        save(run_path, run)
        submitted = request(args.base, "/prompt", {"prompt": graph, "client_id": client_id,
            "extra_data": {"extra_pnginfo": {"workflow": ui_workflow}}})
        pid = submitted["prompt_id"]
        run.update(prompt_id=pid, submission=submitted, status="submitted")
        save(run_path, run)
    print("prompt_id=" + pid, flush=True)
    started = time.monotonic()
    while True:
        history = request(args.base, "/history/" + pid)
        if pid in history:
            record = history[pid]
            break
        if time.monotonic() - started > args.timeout:
            raise TimeoutError("Prompt ID saved; rerun same command to resume, not resubmit.")
        time.sleep(1)
    save(args.output / "history.json", record)
    if record["status"]["status_str"] != "success":
        raise RuntimeError(record["status"])
    manifest = fetch_outputs(args, run, record)
    run["status"] = "completed"
    save(run_path, run)
    print(json.dumps({"prepared_direction": args.direction, "frames": len(manifest["entries"]),
                      "mean_pre_mask_iou": float(np.mean([e["qa"]["pre_mask"]["iou"] for e in manifest["entries"]]))}), flush=True)


if __name__ == "__main__":
    main()
