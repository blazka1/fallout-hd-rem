"""Local Qwen 2.1 terminal edit; isolated, resumable, no installation."""
from pathlib import Path
import importlib.util, json, uuid, argparse, urllib.request, urllib.parse, time, shutil

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'assets/generated/v13ent-terminal/qwen21-indicator-v2-20261114'
SOURCE = ROOT / 'assets/hd/v13ent/v14-campfire-x4/art/scenery/doorcomp.frm.png'
spec = importlib.util.spec_from_file_location('qwen_helpers', ROOT / 'assets/generated/v13ent-door-skeleton-qwen/trial-v1-20261113/run-qwen21-edit.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
BASE = 'http://127.0.0.1:8188'
PROMPT = '''Precisely edit this same small Fallout 1 vault access terminal sprite, keeping its exact framing, silhouette, pose, proportions, perspective and every component in the same position. Keep the existing narrow metal pedestal, vertical ribs, curved cable, dark worn gunmetal case, amber screen and small row of control buttons. Replace ONLY the rightmost button in the row immediately under the screen with one tiny round green indicator lamp, about the size of that one button, recessed in its metal socket. The green lamp is on; its light is confined to its small glass lens, no light spill, bloom, glow or aura. Keep all other buttons and the amber screen as they are. Remove the pale yellow-grey halo and bright matte fringe along the outside of the case and pedestal. The perimeter must be dark neutral metal matching the adjacent metal surface, clean and opaque inside, clean transparency outside, with no bright outline or scattered pale pixels. No cast light or cast shadow outside the silhouette, no ground, no scenery or door frame, no new parts, no text or watermark. Preserve the original subdued late-1990s prerendered isometric Fallout appearance and aged metal texture. This is a local correction, not a redesign. Output the single identical-shaped terminal on a true transparent background, exactly the same size and placement in the frame.'''

def save(name, value):
    (OUT/name).write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')

def n(kind, **inputs): return {'class_type':kind,'inputs':inputs}

def submit():
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT/'run.json').exists(): raise RuntimeError('Existing run: collect instead of resubmitting')
    h.require_idle(BASE)
    models = {'unet':'qwen_image_2.1_int8_convrot.safetensors','clip':'qwen3vl_8b_int8_convrot.safetensors','vae':'qwen_image_2.1_vae_bf16.safetensors'}
    schemas, checks = h.preflight(BASE, models)
    if not checks['ready_to_submit']: raise RuntimeError(checks)
    shutil.copy2(SOURCE, OUT/'source.png')
    prefix = 'fallout1_terminal_indicator/'+uuid.uuid4().hex
    uploaded = h.upload(BASE, OUT/'source.png', 'terminal-'+uuid.uuid4().hex+'.png')
    graph = {
        '1':n('LoadImage', image=uploaded),
        '2':n('JoinImageWithAlpha', image=['1',0], alpha=['1',1]),
        '3':n('ImageScale', image=['2',0], upscale_method='lanczos', width=384, height=640, crop='disabled'),
        '4':n('UNETLoader', unet_name=models['unet'], weight_dtype='default'),
        '5':n('CLIPLoader', clip_name=models['clip'], type='qwen_image', device='default'),
        '6':n('VAELoader', vae_name=models['vae']),
        '7':n('QwenImage21Cache', model=['4',0], device='cpu', dtype='default'),
        '8':n('TextEncodeQwenImage21', clip=['5',0], prompt=PROMPT, negative_prompt='', vae=['6',0], resolution=0, **{'images.image_1':['3',0]}),
        '9':n('KSampler', model=['7',0], positive=['8',0], negative=['8',1], latent_image=['8',2], seed=1411202601, steps=25, cfg=1.0, sampler_name='euler', scheduler='simple', denoise=1.0),
        '10':n('VAEDecode', samples=['9',0], vae=['6',0]),
        '11':n('SaveImage', images=['10',0], filename_prefix=prefix+'/terminal-raw'),
        '12':n('SaveImage', images=['3',0], filename_prefix=prefix+'/reference-working')}
    workflow = h.make_workflow(graph, schemas)
    save('workflow.json',workflow); save('prompt-api.json',graph); save('preflight.json',checks)
    (OUT/'prompt.txt').write_text(PROMPT+'\n',encoding='utf-8')
    save('plan.json',dict(source=str(SOURCE),source_sha256=h.sha_file(SOURCE),models=models,seed=1411202601,steps=25,working=[384,640],target=[128,212],status='candidate_not_installed'))
    h.require_idle(BASE)
    run=h.request(BASE,'/prompt',{'prompt':graph,'client_id':prefix,'extra_data':{'extra_pnginfo':{'workflow':workflow}}})
    save('run.json',run)
    print(json.dumps(run),flush=True)

def collect():
    pid=json.loads((OUT/'run.json').read_text())['prompt_id']
    history=h.request(BASE,'/history/'+pid)
    if pid not in history: print('Still running: '+pid); return
    job=history[pid];save('history.json',job)
    if job['status']['status_str']!='success':raise RuntimeError(job['status'])
    for node,name in [('11','terminal-raw.png'),('12','reference-working.png')]:
        record=job['outputs'][node]['images'][0]
        data=h.request(BASE,'/view?'+urllib.parse.urlencode(record))
        (OUT/name).write_bytes(data)
    messages=dict(job['status']['messages'])
    save('result.json',dict(status='generated_for_review',prompt_id=pid,elapsed_seconds=(messages['execution_success']['timestamp']-messages['execution_start']['timestamp'])/1000,sha256=h.sha_file(OUT/'terminal-raw.png'),installed=False))
    print('Collected '+str(OUT/'terminal-raw.png'))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['submit','collect']);args=parser.parse_args()
    {'submit':submit,'collect':collect}[args.action]()
