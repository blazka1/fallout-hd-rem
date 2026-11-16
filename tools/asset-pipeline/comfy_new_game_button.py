"""Build three matching Fallout menu-button skins using local ComfyUI core nodes.

The original plate and up/down FRMs are the only visual inputs. No text is baked
into the skins. Image processing runs in ComfyUI; this script only orchestrates it.
"""
import argparse
import hashlib
import json
import time
import uuid
from pathlib import Path

from comfy_menu import request, upload


class Graph:
    def __init__(self):
        self.prompt = {}
        self.layout = {}

    def add(self, kind, title, pos, **inputs):
        nid = str(len(self.prompt) + 1)
        self.prompt[nid] = {"class_type": kind, "inputs": inputs}
        self.layout[nid] = (title, pos)
        return [nid, 0]

    def workflow(self, schemas):
        links, incoming, outgoing = [], {}, {}
        for nid, item in self.prompt.items():
            target_slot = 0
            for key, value in item["inputs"].items():
                if not isinstance(value, list):
                    continue
                source, slot = value
                kind = schemas[self.prompt[source]["class_type"]]["output"][slot]
                link = len(links) + 1
                links.append([link, int(source), slot, int(nid), target_slot, kind])
                incoming[(nid, key)] = (link, kind)
                outgoing.setdefault((source, slot), []).append(link)
                target_slot += 1
        nodes = []
        for nid, item in self.prompt.items():
            inputs, widgets = [], []
            for key, value in item["inputs"].items():
                if isinstance(value, list):
                    link, kind = incoming[(nid, key)]
                    inputs.append({"name": key, "type": kind, "link": link})
                else:
                    widgets.append(value)
            if item["class_type"] == "LoadImage":
                widgets.append("image")
            outputs = [{"name": kind, "type": kind, "links": outgoing.get((nid, slot), []), "slot_index": slot}
                       for slot, kind in enumerate(schemas[item["class_type"]].get("output", []))]
            title, pos = self.layout[nid]
            nodes.append({"id": int(nid), "type": item["class_type"], "title": title,
                "pos": pos, "size": [300, 260], "flags": {}, "order": int(nid) - 1, "mode": 0,
                "inputs": inputs, "outputs": outputs, "widgets_values": widgets,
                "properties": {"Node name for S&R": item["class_type"]}})
        return {"version": 0.4, "last_node_id": len(nodes), "last_link_id": len(links),
            "nodes": nodes, "links": links, "groups": [], "config": {},
            "extra": {"ds": {"scale": 0.35, "offset": [80, 100]}}}


def build(images, prefix):
    g = Graph()
    add = g.add
    original = add("LoadImage", "Original menu without labels", [0, 0], image=images["mainmenu"])
    up = add("LoadImage", "Original raised red switch", [0, 1000], image=images["menuup"])
    down = add("LoadImage", "Original depressed red switch", [0, 1500], image=images["menudown"])
    model = add("UpscaleModelLoader", "Real-ESRGAN x4 / shared for all states", [0, 500], model_name="RealESRGAN_x4plus.pth")
    plate = add("ImageCrop", "New Game metal plate / original pixels", [350, 0], image=original,
        width=204, height=41, x=400, y=76)
    plate_hd = add("ImageUpscaleWithModel", "Restore metal and corner bolts", [700, 0], upscale_model=model, image=plate)
    sized = add("ImageScale", "Uniform height before extending center", [1050, 0], image=plate_hd,
        upscale_method="lanczos", width=756, height=152, crop="disabled")
    left = add("ImageCrop", "Fixed left end cap", [1400, 0], image=sized, width=80, height=152, x=0, y=0)
    center = add("ImageCrop", "Metal center without corner bolts", [1400, 350], image=sized, width=596, height=152, x=80, y=0)
    right = add("ImageCrop", "Fixed right end cap", [1400, 700], image=sized, width=80, height=152, x=676, y=0)
    center = add("ImageScale", "Extend only the metal center", [1750, 350], image=center,
        upscale_method="lanczos", width=860, height=152, crop="disabled")
    joined = add("ImageStitch", "Left cap + center", [2100, 0], image1=left, direction="right",
        match_image_size=False, spacing_width=0, spacing_color="black", image2=center)
    base = add("ImageStitch", "Shared 1020 x 152 plate", [2450, 0], image1=joined, direction="right",
        match_image_size=False, spacing_width=0, spacing_color="black", image2=right)

    def switch_sprite(src, name, row):
        restored = add("ImageUpscaleWithModel", name + " / restored", [350, row], upscale_model=model, image=src)
        resized = add("ImageScale", name + " / 100 px", [700, row], image=restored,
            upscale_method="lanczos", width=100, height=100, crop="disabled")
        black = add("ImageColorToMask", "Original transparent index rendered as black", [350, row + 300], image=src, color=0)
        alpha = add("InvertMask", "Keep original switch silhouette", [700, row + 300], mask=black)
        alpha_image = add("MaskToImage", "Mask resize input", [1050, row + 300], mask=alpha)
        alpha_image = add("ImageScale", "Smooth mask / same geometry", [1400, row + 300], image=alpha_image,
            upscale_method="bilinear", width=100, height=100, crop="disabled")
        alpha = add("ImageToMask", "Switch opacity", [1750, row + 300], image=alpha_image, channel="red")
        return resized, alpha

    raised, raised_mask = switch_sprite(up, "Raised switch", 1100)
    depressed, depressed_mask = switch_sprite(down, "Depressed switch", 1900)
    states = []
    output_nodes = {}
    for index, (name, tint_color) in enumerate((("normal", 0xABB093), ("hover", 0xD4C6A1), ("pressed", 0x888A76))):
        x, y = 2900 + index * 1250, 0
        tint = add("EmptyImage", name + " / palette", [x, y], width=1020, height=152, batch_size=1, color=tint_color)
        plate_state = add("ImageBlend", name + " / same metal, adjusted lighting", [x, y + 350],
            image1=base, image2=tint, blend_factor=1.0, blend_mode="multiply")
        if name != "normal":
            edge = add("EmptyImage", name + " / top bevel", [x, y + 700], width=1020,
                height=2 if name == "hover" else 4, batch_size=1, color=0xC2A66B if name == "hover" else 0x151A14)
            plate_state = add("ImageCompositeMasked", name + " / bevel response", [x + 350, y + 350],
                destination=plate_state, source=edge, x=0, y=0, resize_source=False)
        sprite, mask = (depressed, depressed_mask) if name == "pressed" else (raised, raised_mask)
        skin = add("ImageCompositeMasked", name + " / mechanical switch", [x + 700, y + 350],
            destination=plate_state, source=sprite, x=44, y=28 if name == "pressed" else 26,
            resize_source=False, mask=mask)
        saved = add("SaveImage", name.upper() + " / text stays in the engine", [x + 700, y + 700],
            images=skin, filename_prefix=f"{prefix}/{name}")
        output_nodes[name] = saved[0]
        states.append(skin)
    strip = add("ImageStitch", "Normal then hover", [3000, 1400], image1=states[0], direction="down",
        match_image_size=False, spacing_width=16, spacing_color="black", image2=states[1])
    strip = add("ImageStitch", "Normal / Hover / Pressed", [3350, 1400], image1=strip, direction="down",
        match_image_size=False, spacing_width=16, spacing_color="black", image2=states[2])
    saved = add("SaveImage", "Three-state comparison", [3700, 1400], images=strip, filename_prefix=f"{prefix}/states")
    output_nodes["states"] = saved[0]
    return g, output_nodes


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reference", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--base", default="http://127.0.0.1:8188")
    p.add_argument("--label", default="new-game-v1")
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if (args.output / "run.json").exists():
        raise SystemExit("Existing run is preserved; use a new output directory.")
    queue = request(args.base, "/queue")
    if queue.get("queue_running") or queue.get("queue_pending"):
        raise SystemExit("ComfyUI queue is busy; do not interrupt existing work.")
    schemas = request(args.base, "/object_info")
    images, sources = {}, {}
    for name in ("mainmenu", "menuup", "menudown"):
        path = args.reference / "png" / "art" / "intrface" / (name + ".frm.png")
        images[name] = upload(args.base, path)
        sources[name] = {"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    g, output_nodes = build(images, "fallout1_menu/" + args.label)
    workflow = g.workflow(schemas)
    (args.output / "workflow.json").write_text(json.dumps(workflow, indent=2), encoding="utf-8")
    (args.output / "prompt-api.json").write_text(json.dumps(g.prompt, indent=2), encoding="utf-8")
    result = request(args.base, "/prompt", {"prompt": g.prompt, "client_id": "fallout-button-" + uuid.uuid4().hex,
        "extra_data": {"extra_pnginfo": {"workflow": workflow}}})
    record = {"sources": sources, "model": "RealESRGAN_x4plus.pth", "size": [1020, 152],
        "plate_crop": [400, 76, 204, 41], "output_nodes": output_nodes,
        "prompt_id": result["prompt_id"], "status": "submitted", "files": []}
    record_path = args.output / "run.json"
    record_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(json.dumps(result), flush=True)
    started = time.monotonic()
    while time.monotonic() - started < 600:
        history = request(args.base, "/history/" + result["prompt_id"])
        if result["prompt_id"] not in history:
            time.sleep(2)
            continue
        entry = history[result["prompt_id"]]
        (args.output / "history.json").write_text(json.dumps(entry, indent=2), encoding="utf-8")
        record["status"] = entry.get("status", {}).get("status_str", "unknown")
        record["seconds"] = round(time.monotonic() - started, 2)
        from urllib.parse import urlencode
        for nid, output in entry.get("outputs", {}).items():
            for item in output.get("images", []):
                data = request(args.base, "/view?" + urlencode(item))
                filename = Path(item["filename"]).name
                path = args.output / filename
                if path.exists():
                    raise RuntimeError("Refusing to overwrite " + str(path))
                path.write_bytes(data)
                record["files"].append({"node": nid, "path": str(path.resolve()), "sha256": hashlib.sha256(data).hexdigest()})
        record_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        print(json.dumps(record, indent=2), flush=True)
        if record["status"] != "success":
            raise SystemExit("ComfyUI failed; see history.json")
        return
    raise SystemExit("Polling timed out; job was not cancelled. Inspect queue/history before retrying.")


if __name__ == "__main__":
    main()
