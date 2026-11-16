"""One small, isolated native ControlNet inference to verify installation, not art quality."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import importlib.util
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from PIL import Image, ImageDraw
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / 'smoke'
BASE = 'http://127.0.0.1:8188'
PATCH = 'qwen_image_2.1_fun_controlnet_union_int8_convrot.safetensors'

def save(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

def req(path, data=None):
    payload = None if data is None else json.dumps(data).encode()
    request = urllib.request.Request(BASE + path, payload,
        {'Content-Type': 'application/json'} if payload else {})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)

def idle():
    queue = req('/queue')
    if queue['queue_running'] or queue['queue_pending']:
        raise RuntimeError('Queue busy; no test submitted, no jobs interrupted.')

def upload(path, token):
    boundary = 'qwen21control-' + token
    fields = {'type': 'input', 'subfolder': 'fallout1_qwen21_controlnet_test', 'overwrite': 'false'}
    data = b''.join(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
                    for k, v in fields.items())
    data += (f'--{boundary}\r\nContent-Disposition: form-data; name="image"; '
             f'filename="diagnostic-{token}.png"\r\nContent-Type: image/png\r\n\r\n').encode()
    data += path.read_bytes() + f'\r\n--{boundary}--\r\n'.encode()
    request = urllib.request.Request(BASE + '/upload/image', data,
        {'Content-Type': 'multipart/form-data; boundary=' + boundary})
    with urllib.request.urlopen(request, timeout=30) as response:
        record = json.load(response)
    return record['subfolder'] + '/' + record['name']

def submit():
    OUT.mkdir(exist_ok=True)
    if (OUT / 'run.json').exists():
        raise RuntimeError('Existing run retained. Use collect instead of resubmitting.')
    idle()
    schemas = req('/object_info')
    assert PATCH in schemas['ModelPatchLoader']['input']['required']['name'][0]
    token = uuid.uuid4().hex
    # Procedural diagnostic geometry only; no Fallout resources or runtime writes.
    source = Image.new('RGB', (512, 512), (35, 35, 35))
    draw = ImageDraw.Draw(source)
    draw.rounded_rectangle((40, 72, 472, 440), radius=16, fill=(115, 115, 115), outline='white', width=4)
    draw.rectangle((96, 128, 416, 304), fill=(20, 20, 20), outline=(205, 205, 205), width=6)
    for x in (64, 448):
        for y in (96, 416):
            draw.ellipse((x-7, y-7, x+7, y+7), fill=(210, 210, 210))
    for x in (136, 256, 376):
        draw.ellipse((x-28, 348, x+28, 404), fill=(55, 55, 55), outline='white', width=3)
    source.save(OUT / 'diagnostic-source.png')
    image_name = upload(OUT / 'diagnostic-source.png', token)
    def n(kind, **inputs):
        return {'class_type': kind, 'inputs': inputs}
    prefix = 'fallout1_qwen21_controlnet_test/' + token
    graph = {
        '1': n('LoadImage', image=image_name),
        '2': n('Canny', image=['1', 0], low_threshold=0.2, high_threshold=0.6),
        '3': n('UNETLoader', unet_name='qwen_image_2.1_int8_convrot.safetensors', weight_dtype='default'),
        '4': n('CLIPLoader', clip_name='qwen3vl_8b_int8_convrot.safetensors', type='qwen_image', device='default'),
        '5': n('VAELoader', vae_name='qwen_image_2.1_vae_bf16.safetensors'),
        '6': n('ModelPatchLoader', name=PATCH),
        '7': n('QwenImage21Cache', model=['3', 0], device='cpu', dtype='default'),
        '8': n('ZImageFunControlnet', model=['7', 0], model_patch=['6', 0], vae=['5', 0],
               strength=1.0, image=['2', 0], start_percent=0.0, end_percent=1.0),
        '9': n('TextEncodeQwenImage21', clip=['4', 0],
               prompt='A front view of a rectangular matte steel instrument panel, one dark rectangular display and three round knobs below it, four corner screws, neutral gray industrial metal, no text.',
               negative_prompt='', vae=['5', 0], resolution=512),
        '10': n('KSampler', model=['8', 0], positive=['9', 0], negative=['9', 1], latent_image=['9', 2],
                seed=14112026, steps=2, cfg=1.0, sampler_name='euler', scheduler='simple', denoise=1.0),
        '11': n('VAEDecode', samples=['10', 0], vae=['5', 0]),
        '12': n('SaveImage', images=['11', 0], filename_prefix=prefix + '/diagnostic-output'),
        '13': n('SaveImage', images=['2', 0], filename_prefix=prefix + '/canny-control'),
    }
    spec = importlib.util.spec_from_file_location('workflow_helpers', ROOT / 'work/seedvr2-image-setup/20261113/knife-upscale.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    workflow = helper.workflow(graph, schemas)
    workflow['extra'] = {'notes': 'Installation smoke test only: Qwen 2.1 + Fun ControlNet Union INT8. 512x512, 2 steps; not an artwork quality preset.'}
    save('workflow.json', workflow)
    save('prompt-api.json', graph)
    save('system-before.json', req('/system_stats'))
    save('node-info.json', {k: schemas[k] for k in {n['class_type'] for n in graph.values()}})
    idle()
    try:
        result = req('/prompt', dict(prompt=graph, client_id='qwen21control-test-' + token,
                     extra_data={'extra_pnginfo': {'workflow': workflow}}))
    except urllib.error.HTTPError as e:
        (OUT / 'validation-error.json').write_bytes(e.read())
        raise
    save('run.json', result)
    assert not result.get('node_errors'), result
    print(json.dumps(result), flush=True)

def collect():
    prompt_id = json.loads((OUT / 'run.json').read_text())['prompt_id']
    start = time.monotonic()
    while True:
        data = req('/history/' + prompt_id)
        if prompt_id in data:
            break
        if time.monotonic() - start > 1200:
            raise TimeoutError('Resume collect; job was not cancelled or resubmitted.')
        print('Waiting for installation smoke test ' + prompt_id, flush=True)
        time.sleep(15)
    job = data[prompt_id]
    save('history.json', job)
    assert job['status']['status_str'] == 'success', job['status']
    for node, name in [('12', 'diagnostic-output.png'), ('13', 'canny-control.png')]:
        record = job['outputs'][node]['images'][0]
        with urllib.request.urlopen(BASE + '/view?' + urllib.parse.urlencode(record), timeout=30) as response:
            (OUT / name).write_bytes(response.read())
    result = Image.open(OUT / 'diagnostic-output.png')
    pixels = np.asarray(result)
    assert result.size == (512, 512) and result.mode in ('RGB', 'RGBA')
    assert np.isfinite(pixels).all() and float(pixels[:, :, :3].std()) > 1.0
    events = dict(job['status']['messages'])
    elapsed = (events['execution_success']['timestamp'] - events['execution_start']['timestamp']) / 1000
    save('result.json', dict(status='native_controlnet_inference_passed', prompt_id=prompt_id,
        model_patch=PATCH, output_size=list(result.size), mode=result.mode, steps=2,
        strength=1.0, elapsed_seconds=elapsed, rgb_std=float(pixels[:, :, :3].std()),
        sha256=hashlib.sha256((OUT / 'diagnostic-output.png').read_bytes()).hexdigest(),
        verified_utc=datetime.now(timezone.utc).isoformat(),
        scope='Loads INT8 patch, applies Canny control, samples and decodes. Does not establish artistic quality, exact geometry or high-resolution performance.'))
    print((OUT / 'result.json').read_text(), flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['submit', 'collect'])
    args = parser.parse_args()
    {'submit': submit, 'collect': collect}[args.action]()
