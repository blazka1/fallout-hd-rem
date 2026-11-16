"""Second ComfyUI pass: correct crop, contextual restoration and sharp bevels.

All visual work runs in ComfyUI core nodes. The Python runner only builds the
graph, submits it and archives results. The v1 recipe and selected assets stay intact.
"""
import argparse
import hashlib
import json
import time
import uuid
from pathlib import Path
from urllib.parse import urlencode
from comfy_menu import request, upload
from comfy_new_game_button import build as build_v1


def build(images, prefix):
    g, outputs = build_v1(images, prefix)
    nodes = g.prompt
    # Restore with pixels above, below and on both sides of the small button.
    nodes['5']['inputs'].update(x=395, y=60, width=215, height=70)
    g.layout['5'] = ('Context around New Game plate', [350, 0])
    restored = g.add('ImageCrop', 'Tight plate / remove external menu frame', [800, -900],
        image=['6', 0], x=72, y=72, width=764, height=156)
    raw = g.add('ImageCrop', 'Exact original metal plate', [350, -900],
        image=['1', 0], x=413, y=78, width=191, height=39)
    raw = g.add('ImageScale', 'Original fine texture reference', [700, -1250],
        image=raw, upscale_method='lanczos', width=764, height=156, crop='disabled')
    metal = g.add('ImageBlend', 'Retain a little original metal grain', [1150, -900],
        image1=restored, image2=raw, blend_factor=0.16, blend_mode='normal')
    nodes['7']['inputs'].update(image=metal, width=744)
    nodes['9']['inputs']['width'] = 584
    nodes['10']['inputs']['x'] = 664
    # Resize each end cap once and only extend the center horizontally.
    # The final physical size and all click coordinates remain unchanged.

    # Replace the broad bilinear mask transition with a subpixel contour.
    for nid in list(nodes):
        inputs = nodes[nid]['inputs']
        if nodes[nid]['class_type'] == 'ImageScale' and inputs.get('upscale_method') == 'bilinear':
            inputs.update(upscale_method='lanczos', width=104, height=104)
            mask = g.add('ImageToMask', 'Switch contour at native ESRGAN scale', [1800, 2850 + int(nid) * 15],
                image=[nid, 0], channel='red')
            mask = g.add('ThresholdMask', 'Remove four-pixel soft fringe', [2150, 2850 + int(nid) * 15],
                mask=mask, value=0.5)
            mask_img = g.add('MaskToImage', 'Hard contour before final antialias', [2500, 2850 + int(nid) * 15], mask=mask)
            mask_img = g.add('ImageScale', 'One narrow antialiased edge', [2850, 2850 + int(nid) * 15],
                image=mask_img, upscale_method='lanczos', width=100, height=100, crop='disabled')
            for next_id in list(nodes):
                if nodes[next_id]['class_type'] == 'ImageToMask' and nodes[next_id]['inputs'].get('image') == [nid, 0] and next_id != mask[0]:
                    # Only the original ImageToMask consumer; new node is earlier in this chain.
                    if int(next_id) <= 46:
                        nodes[next_id]['inputs']['image'] = mask_img

    def rect(image, x, y, width, height, color, title, pos):
        ink = g.add('EmptyImage', title + ' / color', pos,
            width=width, height=height, batch_size=1, color=color)
        return g.add('ImageCompositeMasked', title, [pos[0] + 350, pos[1]],
            destination=image, source=ink, x=x, y=y, resize_source=False)

    for index, state in enumerate(('normal', 'hover', 'pressed')):
        save = outputs[state]
        old_skin = nodes[save]['inputs']['images']
        skin = old_skin
        # A closed, controlled two-stage metal bevel. No blurred outside frame.
        high = {'normal': 0x7E8062, 'hover': 0xB19B63, 'pressed': 0x22291E}[state]
        low = {'normal': 0x22291E, 'hover': 0x383D29, 'pressed': 0x72775A}[state]
        for side, (x, y, w, h, color) in enumerate((
            (0, 0, 1020, 2, 0x151B15), (0, 150, 1020, 2, 0x0B100D),
            (0, 2, 2, 148, 0x151B15), (1018, 2, 2, 148, 0x0B100D),
            (2, 2, 1016, 3, high), (2, 5, 3, 143, high),
            (5, 147, 1013, 3, low), (1015, 5, 3, 142, low),
        )):
            skin = rect(skin, x, y, w, h, color, state + ' / crisp bevel ' + str(side),
                [4500 + index * 900, 1400 + side * 300])
        # Rewire both SaveImage and the state contact sheet to the new perimeter.
        for nid in list(nodes):
            if int(nid) > 46:
                continue
            for key, value in list(nodes[nid]['inputs'].items()):
                if value == old_skin:
                    nodes[nid]['inputs'][key] = skin
    return g, outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--base', default='http://127.0.0.1:8188')
    parser.add_argument('--label', default='new-game-v2')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if (args.output / 'run.json').exists():
        raise SystemExit('Existing run is preserved; choose a new output directory.')
    queue = request(args.base, '/queue')
    if queue.get('queue_running') or queue.get('queue_pending'):
        raise SystemExit('ComfyUI queue is busy; no work was interrupted.')
    schemas = request(args.base, '/object_info')
    images, sources = {}, {}
    for name in ('mainmenu', 'menuup', 'menudown'):
        path = args.reference / 'png' / 'art' / 'intrface' / (name + '.frm.png')
        images[name] = upload(args.base, path)
        sources[name] = {'path': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    graph, outputs = build(images, 'fallout1_menu/' + args.label)
    workflow = graph.workflow(schemas)
    (args.output / 'workflow.json').write_text(json.dumps(workflow, indent=2), encoding='utf-8')
    (args.output / 'prompt-api.json').write_text(json.dumps(graph.prompt, indent=2), encoding='utf-8')
    job = request(args.base, '/prompt', {'prompt': graph.prompt, 'client_id': 'fallout-button-' + uuid.uuid4().hex,
        'extra_data': {'extra_pnginfo': {'workflow': workflow}}})
    record = {'sources': sources, 'model': 'RealESRGAN_x4plus.pth', 'size': [1020, 152],
        'context_crop': [395, 60, 215, 70], 'plate_crop': [413, 78, 191, 39],
        'original_texture_blend': 0.16, 'mask': 'lanczos104/threshold0.5/lanczos100',
        'bevel': 'closed two-stage 2px outer / 3px inner',
        'output_nodes': outputs, 'prompt_id': job['prompt_id'], 'status': 'submitted', 'files': []}
    record_path = args.output / 'run.json'
    record_path.write_text(json.dumps(record, indent=2), encoding='utf-8')
    print(json.dumps(job), flush=True)
    start = time.monotonic()
    while time.monotonic() - start < 600:
        entry = request(args.base, '/history/' + job['prompt_id']).get(job['prompt_id'])
        if entry is None:
            time.sleep(2)
            continue
        (args.output / 'history.json').write_text(json.dumps(entry, indent=2), encoding='utf-8')
        record['status'] = entry.get('status', {}).get('status_str', 'unknown')
        record['seconds'] = round(time.monotonic() - start, 2)
        for nid, output in entry.get('outputs', {}).items():
            for item in output.get('images', []):
                data = request(args.base, '/view?' + urlencode(item))
                path = args.output / Path(item['filename']).name
                if path.exists():
                    raise RuntimeError('Refusing to overwrite ' + str(path))
                path.write_bytes(data)
                record['files'].append({'node': nid, 'path': str(path.resolve()), 'sha256': hashlib.sha256(data).hexdigest()})
        record_path.write_text(json.dumps(record, indent=2), encoding='utf-8')
        print(json.dumps(record, indent=2), flush=True)
        if record['status'] != 'success':
            raise SystemExit('ComfyUI failed; see history.json')
        return
    raise SystemExit('Timed out polling; job was not cancelled.')


if __name__ == '__main__':
    main()
