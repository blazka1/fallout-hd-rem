"""Reproducible local ComfyUI img2img for the original Fallout 1 menu art.

Standard library only. Does not install models, alter source art, or patch the game.
The input crop matches hd_mainmenu.cc. Image operations execute in ComfyUI.
"""
import argparse
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

POSITIVE = """Faithful high resolution restoration of the supplied original Fallout 1 (1997) main menu illustration. Preserve the exact original power armor helmet, its silhouette, proportions, orientation, narrow horizontal black visor slit, rounded cheek respirator, large circular grille, tubes and small round lamp on the forehead. Keep every large mechanical part in its original position. Preserve the original three-quarter close-up composition, cropped armored shoulders, ruined city in the background, subdued gray olive and dusty ochre palette, soft overcast side lighting and bleak retrofuturist post-nuclear atmosphere. Detailed aged cast metal, restrained fine scratches, oxidized seams, readable metal panel edges, realistic surface roughness. Restore material detail and clean pixel noise without redesigning the subject. Original late-1990s pre-rendered industrial game artwork, subtle filmic texture, natural contrast. No lettering or interface."""
NEGATIVE = """different helmet, redesigned armor, T-60 armor, T-45 armor, changed silhouette, changed pose, extra helmet, extra eyes, human face, open visor, glowing blue eyes, neon lights, colorful cyberpunk, fantasy armor, cartoon, anime, illustration outlines, plastic, mirror chrome, glossy toy, pristine new metal, excessive random greebles, extra pipes, extra holes, melted geometry, distorted machinery, blurry details, heavy sharpening halos, checkerboard, text, logo, watermark, letters, captions, buttons, user interface, frame, border"""

def request(base, route, data=None, headers=None, timeout=30):
    if isinstance(data, dict):
        data = json.dumps(data).encode("utf-8")
        headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(base + route, data=data, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
            return json.loads(raw) if "json" in response.headers.get("Content-Type", "") else raw
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"{route}: {error.code}: {error.read().decode('utf-8', 'replace')}") from error

def upload(base, path):
    boundary = "fallout-" + uuid.uuid4().hex
    parts = []
    for key, value in {"type": "input", "subfolder": "fallout1_menu", "overwrite": "false"}.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    upload_name = "fallout1-menu-" + path.name
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{upload_name}"\r\nContent-Type: image/png\r\n\r\n'.encode())
    parts.extend([path.read_bytes(), f"\r\n--{boundary}--\r\n".encode()])
    result = request(base, "/upload/image", b"".join(parts), {"Content-Type": f"multipart/form-data; boundary={boundary}"})
    return (result.get("subfolder", "") + "/" + result["name"]).lstrip("/")

def build_prompt(image_name, args):
    def node(kind, **inputs):
        return {"class_type": kind, "inputs": inputs}
    if args.mode == "compose":
        return {
            "1": node("LoadImage", image=image_name),
            "2": node("ImageScale", image=["1", 0], upscale_method="lanczos", width=1800, height=2160, crop="disabled"),
            "3": node("EmptyImage", width=1800, height=2160, batch_size=1, color=0xC1C2AC),
            "4": node("ImageBlend", image1=["2", 0], image2=["3", 0], blend_factor=1.0, blend_mode="multiply"),
            "5": node("EmptyImage", width=3840, height=2160, batch_size=1, color=0x121714),
            "6": node("SolidMask", value=1.0, width=1800, height=2160),
            "7": node("FeatherMask", mask=["6", 0], left=160, top=0, right=630, bottom=0),
            "8": node("ImageCompositeMasked", destination=["5", 0], source=["4", 0],
                x=179, y=0, resize_source=False, mask=["7", 0]),
            "9": node("SaveImage", images=["8", 0], filename_prefix=f"fallout1_menu/{args.label}/background-3840x2160"),
            "10": node("ImageScale", image=["8", 0], upscale_method="lanczos", width=1920, height=1080, crop="disabled"),
            "11": node("SaveImage", images=["10", 0], filename_prefix=f"fallout1_menu/{args.label}/preview-1920x1080"),
        }
    if args.mode in ("upscale", "background"):
        graph = {
            "1": node("LoadImage", image=image_name),
            "2": node("ImageCrop", image=["1", 0], width=380, height=456, x=8, y=12),
            "3": node("ImageUpscaleWithModel", upscale_model=["4", 0], image=["2", 0]),
            "4": node("UpscaleModelLoader", model_name=args.upscale_model),
            "11": node("ImageScale", image=["3", 0], upscale_method="lanczos", width=1800, height=2160, crop="disabled"),
            "12": node("SaveImage", images=["11", 0], filename_prefix=f"fallout1_menu/{args.label}/portrait-2160h"),
            "13": node("SaveImage", images=["3", 0], filename_prefix=f"fallout1_menu/{args.label}/upscale-only-1520x1824"),
        }
        if args.mode == "background":
            graph.update({
                "14": node("EmptyImage", width=1800, height=2160, batch_size=1, color=0xC1C2AC),
                "15": node("ImageBlend", image1=["11", 0], image2=["14", 0], blend_factor=1.0, blend_mode="multiply"),
                "16": node("EmptyImage", width=3840, height=2160, batch_size=1, color=0x121714),
                "17": node("SolidMask", value=1.0, width=1800, height=2160),
                "18": node("FeatherMask", mask=["17", 0], left=160, top=0, right=630, bottom=0),
                "19": node("ImageCompositeMasked", destination=["16", 0], source=["15", 0],
                    x=179, y=0, resize_source=False, mask=["18", 0]),
                "20": node("SaveImage", images=["19", 0], filename_prefix=f"fallout1_menu/{args.label}/background-3840x2160"),
                "21": node("ImageScale", image=["19", 0], upscale_method="lanczos", width=1920, height=1080, crop="disabled"),
                "22": node("SaveImage", images=["21", 0], filename_prefix=f"fallout1_menu/{args.label}/preview-1920x1080"),
            })
        return graph
    tiled = dict(tile_size=512, overlap=64, temporal_size=64, temporal_overlap=8)
    graph = {
        "1": node("LoadImage", image=image_name),
        "2": node("ImageCrop", image=["1", 0], width=380, height=456, x=8, y=12),
        "3": node("ImageScale", image=["2", 0], upscale_method="lanczos", width=960, height=1152, crop="disabled"),
        "4": node("CheckpointLoaderSimple", ckpt_name=args.checkpoint),
        "5": node("CLIPTextEncode", text=POSITIVE, clip=["4", 1]),
        "6": node("CLIPTextEncode", text=NEGATIVE, clip=["4", 1]),
        "7": node("VAEEncodeTiled", pixels=["3", 0], vae=["4", 2], **tiled),
        "8": node("KSampler", model=["4", 0], seed=args.seed, steps=args.steps, cfg=4.5,
            sampler_name="dpmpp_2m", scheduler="karras", positive=["5", 0], negative=["6", 0],
            latent_image=["7", 0], denoise=args.denoise),
        "9": node("VAEDecodeTiled", samples=["8", 0], vae=["4", 2], **tiled),
        "10": node("SaveImage", images=["9", 0], filename_prefix=f"fallout1_menu/{args.label}/restored-960x1152"),
        "11": node("ImageScale", image=["9", 0], upscale_method="lanczos", width=1800, height=2160, crop="disabled"),
        "12": node("SaveImage", images=["11", 0], filename_prefix=f"fallout1_menu/{args.label}/portrait-2160h-lanczos"),
        "13": node("SaveImage", images=["3", 0], filename_prefix=f"fallout1_menu/{args.label}/reference-lanczos-960x1152"),
    }
    return graph

def build_workflow(graph, schemas):
    titles = {"1": "Original extracted mainmenu.frm (unchanged)", "2": "Exact crop used by the game: 8,12,380,456",
        "3": "Img2img input 960 x 1152", "4": "Existing SDXL Base 1.0", "5": "Preserve original helmet and mood",
        "6": "Avoid redesign, text and UI", "7": "Tiled VAE encode for 8 GB GPU", "8": "Gentle restoration / fixed seed",
        "9": "Tiled VAE decode", "10": "Save actual diffusion output", "11": "Presentation resize only (not new AI detail)",
        "12": "Save portrait sized for 4K menu height", "13": "Save comparison reference (no AI)"}
    positions = {"1": [0, 0], "2": [350, 0], "3": [700, 0], "4": [0, 470], "5": [360, 450], "6": [360, 850],
        "7": [1050, 0], "8": [1400, 100], "9": [1780, 100], "10": [2140, 0], "11": [2140, 510],
        "12": [2490, 510], "13": [1050, 610]}
    if graph["4"]["class_type"] == "UpscaleModelLoader":
        titles.update({"3": "Neural x4 restoration without diffusion redesign", "4": "Official Real-ESRGAN x4plus",
            "12": "Save portrait for 4K menu height", "13": "Save direct neural x4 output"})
        positions.update({"11": [1050, 0], "12": [1400, 0]})
        titles.update({"14": "Same muted tint as CE menu", "15": "Apply existing menu tint",
            "16": "4K dark canvas", "17": "Portrait opacity", "18": "Soft edges matching menu",
            "19": "Helmet left / space for interface right", "20": "Save final 4K background",
            "21": "Preview resize only", "22": "Save 1080p preview"})
        positions.update({"14": [1400, 440], "15": [1770, 0], "16": [1770, 760], "17": [1400, 800],
            "18": [1770, 400], "19": [2140, 0], "20": [2510, 0], "21": [2510, 450], "22": [2880, 450]})
    if graph["4"]["class_type"] == "ImageBlend":
        titles = {"1": "Selected restored portrait", "2": "Fit original 5:6 aspect ratio / 2160 px height",
            "3": "Same muted tint as the CE menu", "4": "Apply existing menu tint",
            "5": "4K dark background (no interface)", "6": "Portrait opacity", "7": "Soft edges matching menu",
            "8": "Place helmet / keep right side clear for buttons", "9": "Save final 4K background",
            "10": "Preview resize", "11": "Save 1080p preview"}
        positions = {str(i): [((i - 1) % 4) * 370, ((i - 1) // 4) * 400] for i in range(1, 12)}
    links, nodes, incoming, outgoing = [], [], {}, {}
    link_id = 0
    for nid, item in graph.items():
        slot = 0
        for key, value in item["inputs"].items():
            if not isinstance(value, list):
                continue
            origin, output_slot = value
            link_id += 1
            kind = schemas[graph[origin]["class_type"]]["output"][output_slot]
            links.append([link_id, int(origin), output_slot, int(nid), slot, kind])
            incoming[(nid, key)] = (link_id, kind)
            outgoing.setdefault((origin, output_slot), []).append(link_id)
            slot += 1
    for nid, item in graph.items():
        schema = schemas[item["class_type"]]
        inputs, widgets = [], []
        for key, value in item["inputs"].items():
            if isinstance(value, list):
                link, kind = incoming[(nid, key)]
                inputs.append({"name": key, "type": kind, "link": link})
            else:
                widgets.append(value)
                if item["class_type"] == "KSampler" and key == "seed":
                    widgets.append("fixed")
        if item["class_type"] == "LoadImage":
            widgets.append("image")
        outputs = [{"name": kind, "type": kind, "links": outgoing.get((nid, slot), []), "slot_index": slot}
                   for slot, kind in enumerate(schema.get("output", []))]
        nodes.append({"id": int(nid), "type": item["class_type"], "pos": positions[nid],
            "size": [330, 330 if item["class_type"] in ("CLIPTextEncode", "KSampler") else 260],
            "flags": {}, "order": int(nid)-1, "mode": 0, "inputs": inputs, "outputs": outputs,
            "properties": {"Node name for S&R": item["class_type"]}, "widgets_values": widgets,
            "title": titles[nid]})
    return {"last_node_id": max(map(int, graph)), "last_link_id": link_id, "nodes": nodes, "links": links,
        "groups": [], "config": {}, "extra": {"ds": {"scale": 0.55, "offset": [70, 70]}}, "version": 0.4}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base", default="http://127.0.0.1:8188")
    parser.add_argument("--checkpoint", default="sd_xl_base_1.0.safetensors")
    parser.add_argument("--mode", choices=["restore", "upscale", "compose", "background"], default="restore")
    parser.add_argument("--upscale-model", default="RealESRGAN_x4plus.pth")
    parser.add_argument("--denoise", type=float, default=0.24)
    parser.add_argument("--steps", type=int, default=28)
    parser.add_argument("--seed", type=int, default=11111997)
    parser.add_argument("--label", default="v1-faithful")
    parser.add_argument("--timeout", type=int, default=1200)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if (args.output / "run.json").exists():
        raise SystemExit("Use a fresh output directory; existing runs are preserved.")
    queue = request(args.base, "/queue")
    if queue.get("queue_running") or queue.get("queue_pending"):
        raise SystemExit("ComfyUI already has queued work; do not interrupt it.")
    schemas = request(args.base, "/object_info")
    checkpoints = schemas["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
    if args.mode == "restore" and args.checkpoint not in checkpoints:
        raise SystemExit("Requested checkpoint is not installed.")
    image_name = upload(args.base, args.input)
    graph = build_prompt(image_name, args)
    workflow = build_workflow(graph, schemas)
    for name, data in (("prompt-api.json", graph), ("workflow.json", workflow)):
        (args.output / name).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    submitted = request(args.base, "/prompt", {"prompt": graph, "client_id": "fallout-menu-" + uuid.uuid4().hex,
        "extra_data": {"extra_pnginfo": {"workflow": workflow}}})
    record = {"input": str(args.input.resolve()), "source_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "mode": args.mode, "checkpoint": args.checkpoint if args.mode == "restore" else None,
        "upscale_model": args.upscale_model if args.mode in ("upscale", "background") else None,
        "crop": None if args.mode == "compose" else [8, 12, 380, 456],
        "diffusion_size": [960, 1152] if args.mode == "restore" else None,
        "presentation_size": [3840, 2160] if args.mode in ("compose", "background") else [1800, 2160],
        "presentation_resize": "lanczos, no additional inferred detail",
        "seed": args.seed if args.mode == "restore" else None,
        "steps": args.steps if args.mode == "restore" else None,
        "cfg": 4.5 if args.mode == "restore" else None,
        "denoise": args.denoise if args.mode == "restore" else None,
        "prompt_id": submitted["prompt_id"], "status": "submitted", "files": []}
    record_path = args.output / "run.json"
    record_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(json.dumps(submitted), flush=True)
    started = time.monotonic()
    while time.monotonic() - started < args.timeout:
        history = request(args.base, "/history/" + submitted["prompt_id"])
        if submitted["prompt_id"] not in history:
            time.sleep(3)
            continue
        result = history[submitted["prompt_id"]]
        (args.output / "history.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        record["status"] = result.get("status", {}).get("status_str", "unknown")
        record["seconds"] = round(time.monotonic() - started, 2)
        for nid, output in result.get("outputs", {}).items():
            for item in output.get("images", []):
                content = request(args.base, "/view?" + urllib.parse.urlencode(item))
                destination = args.output / item["filename"]
                if destination.exists():
                    raise RuntimeError(f"Refusing to overwrite {destination}")
                destination.write_bytes(content)
                record["files"].append({"node": nid, "path": str(destination.resolve()),
                    "sha256": hashlib.sha256(content).hexdigest()})
        record_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        print(json.dumps(record, indent=2), flush=True)
        if record["status"] != "success":
            raise SystemExit("ComfyUI did not complete successfully; see history.json")
        return
    raise SystemExit("Polling timed out. Job was not cancelled; inspect ComfyUI history before resubmitting.")

if __name__ == "__main__":
    main()
