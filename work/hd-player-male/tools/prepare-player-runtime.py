"""Prepare static idle through ComfyUI and package approved actor pixels.

All image transforms execute in ComfyUI. Python verifies, copies and encodes
lossless F1HD RGBA8 payloads; it never touches a runtime or executable.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import struct
import sys
import time
import urllib.parse
import uuid

from PIL import Image
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/asset-pipeline"))
from comfy_menu import request

spec = importlib.util.spec_from_file_location("player_helpers", Path(__file__).with_name("prepare-hd-v1.py"))
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)

RUN = ROOT / "assets/generated/player-male-vault13/runtime-v1-20261112"
PACKAGE = ROOT / "assets/hd/player-male-vault13/v1-x4"
V1 = ROOT / "assets/generated/player-male-vault13/v1-20261112"
WALK = ROOT / "assets/generated/player-male-vault13/walk-v1-20261112"
REF = ROOT / "assets/reference/player-male-vault13"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    helpers.save_json(path, value)


def write_same(path, data):
    if path.exists() and path.read_bytes() != data:
        raise FileExistsError("Refusing replacement of different artifact: " + str(path))
    path.write_bytes(data)


def prepare_idle(base, timeout):
    output = RUN / "idle"
    output.mkdir(parents=True, exist_ok=True)
    source = V1 / "imagegen-master.png"
    artwork = read(V1 / "comfy-prepared/manifest.json")
    metadata = read(REF / "metadata/art/critters/hmjmpsaa.frm.json")
    entries = []
    for d in range(6):
        art = next(e for e in artwork["entries"] if e.get("direction_index") == d)
        orig = next(e for e in metadata["sheets"] if e["direction"] == d)["cells"][0]
        original_path = REF / f"rgba/art/critters/hmjmpsaa.frm/d{d}-f000.png"
        original = Image.open(original_path).convert("RGBA")
        target_box = original.getchannel("A").getbbox()
        assert original.size == (orig["width"], orig["height"])
        ox, oy, right, bottom = target_box
        entries.append({"direction": d, "animation": 0, "frame": -1,
            "source_crop": art["source_crop"], "native_dimensions": list(original.size),
            "dimensions": [original.width * 4, original.height * 4],
            "target_box_native": list(target_box),
            "target_content_dimensions": [(right-ox) * 4, (bottom-oy) * 4],
            "direction_offset_logical": [metadata["direction_x"][d], metadata["direction_y"][d]],
            "registration_original": str(original_path), "original_sha256": sha(original_path),
            "filename": f"stand-d{d}.png"})
    run_path = output / "run.json"
    if run_path.exists():
        run = read(run_path)
        if run["source_sha256"] != sha(source):
            raise ValueError("Idle master changed since submission")
        pid = run.get("prompt_id") or helpers.recover_prompt(base, run["client_id"])
        if not pid:
            raise RuntimeError("Uncertain prior submission; inspect saved run, no duplicate sent")
    else:
        queue = request(base, "/queue")
        if queue["queue_running"] or queue["queue_pending"]:
            raise RuntimeError("ComfyUI busy; no foreign job cancelled")
        schemas = request(base, "/object_info")
        client_id = "male-player-idle-" + uuid.uuid4().hex
        graph = {}

        def node(kind, **inputs):
            key = str(len(graph)+1)
            if kind not in schemas:
                raise ValueError("Missing Comfy node: " + kind)
            graph[key] = {"class_type": kind, "inputs": inputs}
            return [key, 0]

        def resize(image, width, height):
            return node("ImageScale", image=image, upscale_method="lanczos", width=width, height=height, crop="disabled")

        loaded = node("LoadImage", image=helpers.upload(base, source, client_id))
        alpha_source = node("MaskToImage", mask=node("InvertMask", mask=[loaded[0], 1]))
        for entry in entries:
            x,y,w,h = entry["source_crop"]
            tw,th = entry["target_content_dimensions"]
            ow,oh = entry["dimensions"]
            ox,oy = [x*4 for x in entry["target_box_native"][:2]]
            rgb = resize(node("ImageCrop", image=loaded, x=x, y=y, width=w, height=h), tw, th)
            alpha = resize(node("ImageCrop", image=alpha_source, x=x, y=y, width=w, height=h), tw, th)
            canvas = node("EmptyImage", width=ow, height=oh, batch_size=1, color=0)
            rgb = node("ImageCompositeMasked", destination=canvas, source=rgb, x=ox, y=oy, resize_source=False)
            alpha = node("ImageCompositeMasked", destination=canvas, source=alpha, x=ox, y=oy, resize_source=False)
            mask = node("ImageToMask", image=alpha, channel="red")
            joined = node("JoinImageWithAlpha", image=rgb, alpha=node("InvertMask", mask=mask))
            entry["save_node"] = node("SaveImage", images=joined,
                filename_prefix=f"fallout1_player_male/{client_id}/stand-d{entry['direction']}")[0]
        ui = helpers.workflow(graph, schemas)
        save(output / "prompt-api.json", graph)
        save(output / "workflow.json", ui)
        queue = request(base, "/queue")
        if queue["queue_running"] or queue["queue_pending"]:
            raise RuntimeError("ComfyUI became busy; no prompt submitted")
        run = {"status":"submission_pending", "source":str(source), "source_sha256":sha(source),
               "client_id":client_id, "entries":entries,
               "processing":"Comfy crop, bbox fit at x4, alpha preservation; no diffusion",
               "idle_limit":"One static master per direction, wildcard for idle frames0..11; not a newly animated breathing cycle"}
        save(run_path, run)
        submitted = request(base, "/prompt", {"prompt":graph, "client_id":client_id,
                            "extra_data":{"extra_pnginfo":{"workflow":ui}}})
        pid = submitted["prompt_id"]
        run.update(status="submitted", prompt_id=pid, submission=submitted)
        save(run_path, run)
    print("idle_prompt_id="+pid, flush=True)
    started = time.monotonic()
    while True:
        history = request(base, "/history/"+pid)
        if pid in history:
            record=history[pid]
            break
        if time.monotonic()-started>timeout:
            raise TimeoutError("Saved prompt ID; repeat command to resume")
        time.sleep(1)
    save(output / "history.json", record)
    if record["status"]["status_str"] != "success":
        raise RuntimeError(record["status"])
    for entry in run["entries"]:
        remote = record["outputs"][entry["save_node"]]["images"][0]
        data = request(base, "/view?"+urllib.parse.urlencode(remote))
        path = output / entry["filename"]
        write_same(path, data)
        image = Image.open(path)
        assert image.mode == "RGBA" and list(image.size) == entry["dimensions"]
        alpha = np.asarray(image)[:,:,3]
        assert int(alpha.min()) == 0 and int(alpha.max()) >= 240
        entry.update(sha256=sha(path), alpha_range=[int(alpha.min()),int(alpha.max())])
    run["status"]="completed"
    save(run_path, run)
    save(output / "manifest.json", {"status":"six static idle direction sprites prepared", "prompt_id":pid,
                                   "source_sha256":run["source_sha256"], "entries":run["entries"],
                                   "idle_limit":run["idle_limit"]})
    return output


def package():
    # Prepare and validate every source before the first package write.
    idle = read(RUN / "idle/manifest.json")
    walk = read(WALK / "manifest.json")
    candidates=[]
    for entry in idle["entries"]:
        source = RUN / "idle" / entry["filename"]
        candidates.append({"animation":0,"direction":entry["direction"],"frame":-1,
            "source":str(source), "source_sha256":entry["sha256"],
            "native_dimensions":entry["native_dimensions"],
            "direction_offset_logical":entry["direction_offset_logical"],
            "stem":f"stand-d{entry['direction']}"})
    for entry in walk["entries"]:
        source = WALK / entry["source_file"]
        candidates.append({"animation":1,"direction":entry["direction"],"frame":entry["frame"],
            "source":str(source),"source_sha256":entry["sha256"],
            "native_dimensions":entry["native_dimensions"],
            "frame_shift_logical":entry["frame_shift_logical"],
            "direction_offset_logical":entry["direction_offset_logical"],
            "stem":f"walk-d{entry['direction']}-f{entry['frame']:03}"})
    assert len(candidates)==54
    data=[]
    for entry in candidates:
        source=Path(entry["source"])
        assert sha(source)==entry["source_sha256"]
        image=Image.open(source)
        w,h=entry["native_dimensions"]
        assert image.mode=="RGBA" and image.size==(w*4,h*4)
        rgba=image.tobytes()
        payload=struct.pack("<4s4I", b"F1HD", 1, w*4, h*4, 4)+rgba
        entry.update(png=entry["stem"]+".png",filename=entry["stem"]+".rgba",
            dimensions=list(image.size),rgba_sha256=hashlib.sha256(payload).hexdigest(),
            pixel_sha256=hashlib.sha256(rgba).hexdigest(),bytes=len(payload))
        data.append((source.read_bytes(),payload))
    PACKAGE.mkdir(parents=True,exist_ok=True)
    rows=["# animation direction frame nativeWidth nativeHeight filename.rgba",
          "# animation0 stand frame=-1 wildcard only for frames0..11; animation1 walk frames0..7"]
    for entry,(png,payload) in zip(candidates,data):
        write_same(PACKAGE/entry["png"],png)
        write_same(PACKAGE/entry["filename"],payload)
        w,h=entry["native_dimensions"]
        rows.append(f"{entry['animation']} {entry['direction']} {entry['frame']} {w} {h} {entry['filename']}")
    registry=("\n".join(rows)+"\n").encode("ascii")
    write_same(PACKAGE/"registry.tsv",registry)
    manifest={"status":"prepared actor asset package; installation performed separately",
              "component":"male player Vault13", "critter_index":11,"scale":4,
              "image_count":54,"walk_images":48,"stand_images":6,
              "registry":"registry.tsv","registry_sha256":hashlib.sha256(registry).hexdigest(),
              "format":"F1HD version1 RGBA8 little-endian header; soft alpha preserved",
              "walk_fps":10,"stand_usage":"Static image per direction anchored at original frame0 bottom-center; reused across original idle animation frames0..11",
              "limitations":["Static idle is not a new breathing cycle", "Generated walk pose correspondence remains approximate", "Other animations require classic fallback"],
              "idle_comfy_prompt_id":idle["prompt_id"],"walk_manifest_sha256":sha(WALK/"manifest.json"),
              "source_costume_manifest_sha256":sha(V1/"comfy-prepared/manifest.json"),
              "entries":candidates,"runtime_written":False}
    encoded=(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
    write_same(PACKAGE/"manifest.json",encoded)
    # Verify exact payload/header roundtrip for every packed asset.
    for entry in candidates:
        payload=(PACKAGE/entry["filename"]).read_bytes()
        w,h=entry["native_dimensions"]
        assert struct.unpack("<4s4I",payload[:20])==(b"F1HD",1,w*4,h*4,4)
        assert hashlib.sha256(payload).hexdigest()==entry["rgba_sha256"]
        assert payload[20:]==Image.open(PACKAGE/entry["png"]).tobytes()
    print(json.dumps({"package":str(PACKAGE),"images":54,"lossless_payloads_verified":54,
                      "registry":"registry.tsv","idle_prompt_id":idle["prompt_id"]}),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=["idle","package","all"])
    parser.add_argument("--base",default="http://127.0.0.1:8188")
    parser.add_argument("--timeout",type=float,default=300)
    args=parser.parse_args()
    if args.action in ("idle","all"):
        prepare_idle(args.base,args.timeout)
    if args.action in ("package","all"):
        package()


if __name__=="__main__":
    main()
