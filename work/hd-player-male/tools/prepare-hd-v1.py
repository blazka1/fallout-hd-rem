"""Prepare one six-view ImageGen master through deterministic ComfyUI nodes.

Python performs orchestration, alpha analysis and QA only. ComfyUI does all
pixel crops, resampling, alpha preparation and contact-sheet compositing.
No generation, diffusion, engine changes or original-mask enforcement.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.parse
import uuid

from PIL import Image
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/asset-pipeline"))
from comfy_menu import request

DIRECTIONS = [("d0-ne", "NE"), ("d1-e", "E"), ("d2-se", "SE"),
              ("d3-sw", "SW"), ("d4-w", "W"), ("d5-nw", "NW")]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def workflow(graph, schemas):
    links, incoming, outgoing = [], {}, {}
    for nid, item in graph.items():
        slot = 0
        for key, value in item["inputs"].items():
            if not isinstance(value, list):
                continue
            origin, output = value
            kind = schemas[graph[origin]["class_type"]]["output"][output]
            link = len(links) + 1
            links.append([link, int(origin), output, int(nid), slot, kind])
            incoming[nid, key] = (link, kind)
            outgoing.setdefault((origin, output), []).append(link)
            slot += 1
    nodes = []
    for nid, item in graph.items():
        inputs, widgets = [], []
        for key, value in item["inputs"].items():
            if isinstance(value, list):
                link, kind = incoming[nid, key]
                inputs.append({"name": key, "type": kind, "link": link})
            else:
                widgets.append(value)
        if item["class_type"] == "LoadImage":
            widgets.append("image")
        outputs = [{"name": kind, "type": kind, "links": outgoing.get((nid, slot), []), "slot_index": slot}
                   for slot, kind in enumerate(schemas[item["class_type"]]["output"])]
        nodes.append({"id": int(nid), "type": item["class_type"],
                      "pos": [((int(nid) - 1) % 8) * 360, ((int(nid) - 1) // 8) * 300],
                      "size": [330, 260], "flags": {}, "order": int(nid) - 1, "mode": 0,
                      "inputs": inputs, "outputs": outputs,
                      "properties": {"Node name for S&R": item["class_type"]}, "widgets_values": widgets})
    return {"last_node_id": len(nodes), "last_link_id": len(links), "nodes": nodes,
            "links": links, "groups": [], "config": {}, "extra": {}, "version": 0.4}


def upload(base, source, client_id):
    boundary = "player-" + uuid.uuid4().hex
    filename = client_id + "-master.png"
    body = []
    for key, value in {"type": "input", "subfolder": "fallout1_player_male", "overwrite": "false"}.items():
        body.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    body.extend([f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{filename}"\r\nContent-Type: image/png\r\n\r\n'.encode(),
                 source.read_bytes(), f"\r\n--{boundary}--\r\n".encode()])
    result = request(base, "/upload/image", b"".join(body), {"Content-Type": f"multipart/form-data; boundary={boundary}"})
    return (result.get("subfolder", "") + "/" + result["name"]).lstrip("/")


def analyze(source, height, padding, cells_file):
    image = Image.open(source)
    if "A" not in image.getbands():
        raise ValueError("Master has no alpha channel; request real transparency from ImageGen.")
    rgba = np.asarray(image.convert("RGBA"))
    h, w = rgba.shape[:2]
    if np.count_nonzero(rgba[:, :, 3] < 16) / (w * h) < 0.05:
        raise ValueError("Master does not contain a sufficiently transparent background.")
    cells = json.loads(cells_file.read_text(encoding="utf-8")) if cells_file else [
        [round(col * w / 3), round(row * h / 2),
         round((col + 1) * w / 3) - round(col * w / 3),
         round((row + 1) * h / 2) - round(row * h / 2)]
        for row in range(2) for col in range(3)]
    if len(cells) != 6:
        raise ValueError("Exactly six cells are required.")
    entries = []
    for index, (cell, (key, direction)) in enumerate(zip(cells, DIRECTIONS)):
        x, y, cw, ch = map(int, cell)
        if min(x, y) < 0 or min(cw, ch) < 1 or x + cw > w or y + ch > h:
            raise ValueError(f"Invalid source cell {index}: {cell}")
        alpha = rgba[y:y + ch, x:x + cw, 3]
        yy, xx = np.nonzero(alpha >= 8)
        if len(xx) < 100:
            raise ValueError(f"Cell {index} is empty or too small.")
        bx, by, br, bb = int(xx.min()), int(yy.min()), int(xx.max()) + 1, int(yy.max()) + 1
        if min(bx, by, cw - br, ch - bb) < 2:
            raise ValueError(f"Figure touches cell {index} boundary; use --cells-json or fix the master.")
        crop = [x + bx, y + by, br - bx, bb - by]
        target_width = max(1, round(crop[2] * height / crop[3]))
        entries.append({"key": key, "direction_index": index, "direction": direction,
                        "source_cell": cell, "source_crop": crop,
                        "source_bbox_alpha_threshold": 8,
                        "source_alpha_max": int(alpha.max()),
                        "source_solid_bbox_at128": Image.fromarray((alpha >= 128).astype("uint8") * 255).getbbox(),
                        "alpha_note": "Soft alpha retained within crop; faint background noise outside alpha>=8 bounding box is omitted",
                        "content_dimensions": [target_width, height],
                        "dimensions": [target_width + 2 * padding, height + 2 * padding],
                        "padding": padding, "scale": height / crop[3]})
    return entries, [w, h]


def recover_prompt(base, client_id):
    queue = request(base, "/queue")
    for item in queue["queue_running"] + queue["queue_pending"]:
        if len(item) > 3 and item[3].get("client_id") == client_id:
            return item[1]
    for pid, record in request(base, "/history").items():
        prompt = record.get("prompt", [])
        if len(prompt) > 3 and prompt[3].get("client_id") == client_id:
            return pid
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--base", default="http://127.0.0.1:8188")
    parser.add_argument("--height", "--figure-height", dest="height", type=int, default=256)
    parser.add_argument("--padding", type=int, default=8)
    parser.add_argument("--cells-json", type=Path, help="Optional six [x,y,width,height] cells in direction order")
    parser.add_argument("--analyze-only", action="store_true", help="Analyze alpha/cells without uploading or submitting")
    parser.add_argument("--timeout", type=float, default=300, help="Maximum history wait, seconds; rerun to resume")
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    if not 32 <= args.height <= 2048 or not 2 <= args.padding <= 128:
        parser.error("Height must be 32..2048 and padding 2..128.")
    source_hash = digest(source.read_bytes())
    entries, source_dimensions = analyze(source, args.height, args.padding, args.cells_json)
    if args.analyze_only:
        print(json.dumps({"source_dimensions": source_dimensions, "entries": entries}, indent=2))
        return
    output.mkdir(parents=True, exist_ok=True)
    run_path = output / "run.json"
    if run_path.exists():
        run = json.loads(run_path.read_text(encoding="utf-8"))
        if run["source_sha256"] != source_hash or run["height"] != args.height or run["padding"] != args.padding:
            raise ValueError("Existing run uses different source/options; choose a new output directory.")
        if [e["source_crop"] for e in run["entries"]] != [e["source_crop"] for e in entries]:
            raise ValueError("Existing run uses different cell crops; choose a new output directory.")
        pid = run.get("prompt_id") or recover_prompt(args.base, run["client_id"])
        if not pid:
            raise RuntimeError("Prior submission has uncertain status. No duplicate was submitted; inspect queue/history.")
        run["prompt_id"] = pid
        save_json(run_path, run)
    else:
        queue = request(args.base, "/queue")
        if queue["queue_running"] or queue["queue_pending"]:
            raise RuntimeError("ComfyUI is busy; wait without cancelling another task.")
        client_id = "player-male-v1-" + uuid.uuid4().hex
        schemas = request(args.base, "/object_info")
        graph = {}

        def node(kind, **inputs):
            if kind not in schemas:
                raise ValueError("Required ComfyUI node missing: " + kind)
            key = str(len(graph) + 1)
            graph[key] = {"class_type": kind, "inputs": inputs}
            return [key, 0]

        def resize(image, width, height):
            return node("ImageScale", image=image, upscale_method="lanczos", width=width, height=height, crop="disabled")

        def paste(destination, image, x, y, mask=None):
            inputs = dict(destination=destination, source=image, x=x, y=y, resize_source=False)
            if mask is not None:
                inputs["mask"] = mask
            return node("ImageCompositeMasked", **inputs)

        loaded = node("LoadImage", image=upload(args.base, source, client_id))
        opacity = node("InvertMask", mask=[loaded[0], 1])
        opacity_image = node("MaskToImage", mask=opacity)
        cell_width = max(e["dimensions"][0] for e in entries) + 32
        cell_height = args.height + args.padding * 2 + 32
        sheet = node("EmptyImage", width=cell_width * 3, height=cell_height * 2, batch_size=1, color=0x202527)
        for entry in entries:
            x, y, w, h = entry["source_crop"]
            tw, th = entry["content_dimensions"]
            pw, ph = entry["dimensions"]
            rgb = resize(node("ImageCrop", image=loaded, width=w, height=h, x=x, y=y), tw, th)
            alpha_image = resize(node("ImageCrop", image=opacity_image, width=w, height=h, x=x, y=y), tw, th)
            # Paste RGB without opacity first, then attach alpha once; avoids
            # multiplying edge colours twice on an RGBA output.
            canvas = node("EmptyImage", width=pw, height=ph, batch_size=1, color=0)
            padded_rgb = paste(canvas, rgb, args.padding, args.padding)
            padded_alpha = paste(canvas, alpha_image, args.padding, args.padding)
            padded_mask = node("ImageToMask", image=padded_alpha, channel="red")
            rgba = node("JoinImageWithAlpha", image=padded_rgb, alpha=node("InvertMask", mask=padded_mask))
            saved = node("SaveImage", images=rgba, filename_prefix=f"fallout1_player_male/{client_id}/{entry['key']}")
            entry["save_node"] = saved[0]
            col, row = entry["direction_index"] % 3, entry["direction_index"] // 3
            sx, sy = col * cell_width + (cell_width - pw) // 2, row * cell_height + 16
            sheet = paste(sheet, padded_rgb, sx, sy, padded_mask)
            entry["contact_sheet_xy"] = [sx, sy]
        sheet_saved = node("SaveImage", images=sheet, filename_prefix=f"fallout1_player_male/{client_id}/six-directions")
        save_json(output / "prompt-api.json", graph)
        save_json(output / "workflow.json", workflow(graph, schemas))
        queue = request(args.base, "/queue")
        if queue["queue_running"] or queue["queue_pending"]:
            raise RuntimeError("ComfyUI became busy; no prompt submitted. Rerun after the queue is free.")
        run = {"status": "submission_pending", "client_id": client_id,
               "source": str(source), "source_sha256": source_hash, "source_dimensions": source_dimensions,
               "height": args.height, "padding": args.padding, "entries": entries,
               "contact_sheet": {"save_node": sheet_saved[0], "dimensions": [cell_width * 3, cell_height * 2]},
               "processing": "ComfyUI crop, isotropic Lanczos RGB/alpha resize, padding, alpha join, contact sheet; no diffusion",
               "stage": "art experiment; not registered or installed in CE"}
        save_json(run_path, run)
        submitted = request(args.base, "/prompt", {"prompt": graph, "client_id": client_id,
                                                   "extra_data": {"extra_pnginfo": {"workflow": workflow(graph, schemas)}}})
        pid = submitted["prompt_id"]
        run.update(prompt_id=pid, status="submitted", submission=submitted)
        save_json(run_path, run)
    print("prompt_id=" + pid, flush=True)
    start = time.monotonic()
    while True:
        history = request(args.base, "/history/" + pid)
        if pid in history:
            record = history[pid]
            break
        if time.monotonic() - start >= args.timeout:
            raise TimeoutError("Still pending; prompt_id saved. Rerun the same command to resume, not resubmit.")
        time.sleep(1)
    save_json(output / "history.json", record)
    if record["status"]["status_str"] != "success":
        raise RuntimeError(record["status"])
    manifest_entries = []
    for entry in run["entries"] + [dict(run["contact_sheet"], key="six-directions")]:
        remote = record["outputs"][entry["save_node"]]["images"][0]
        data = request(args.base, "/view?" + urllib.parse.urlencode(remote))
        target = output / (entry["key"] + ".png")
        if target.exists() and target.read_bytes() != data:
            raise FileExistsError("Refusing to overwrite different image: " + str(target))
        target.write_bytes(data)
        img = Image.open(target)
        if list(img.size) != entry["dimensions"]:
            raise ValueError(f"Unexpected dimensions for {target}: {img.size}")
        qa = {"dimensions_match": True, "mode": img.mode}
        if entry["key"] != "six-directions":
            if img.mode != "RGBA":
                raise ValueError("ComfyUI output lost alpha: " + str(target))
            alpha = np.asarray(img)[:, :, 3]
            if int(alpha.min()) != 0 or int(alpha.max()) < 240:
                raise ValueError("Invalid transparency range: " + str(target))
            if np.any(alpha[0]) or np.any(alpha[-1]) or np.any(alpha[:, 0]) or np.any(alpha[:, -1]):
                raise ValueError("Nontransparent output boundary: " + str(target))
            qa.update(alpha_range=[int(alpha.min()), int(alpha.max())],
                      soft_alpha_pixels=int(((alpha > 0) & (alpha < 255)).sum()),
                      boundary_transparent=True,
                      alpha_bbox=Image.fromarray(alpha).getbbox())
        manifest_entries.append(dict(entry, file=target.name, sha256=digest(data), qa=qa))
    save_json(output / "manifest.json", {"status": "prepared_art_experiment", "prompt_id": pid,
              "source_sha256": source_hash, "workflow": "workflow.json", "api_prompt": "prompt-api.json",
              "entries": manifest_entries, "runtime_installed": False})
    run["status"] = "completed"
    save_json(run_path, run)
    print("Prepared and verified six RGBA views and one contact sheet through ComfyUI.", flush=True)


if __name__ == "__main__":
    main()
