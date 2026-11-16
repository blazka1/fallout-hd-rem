from pathlib import Path
import importlib.util, json, uuid, argparse, urllib.request, urllib.parse, time, shutil
from PIL import Image
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'assets/generated/inventory-10mm-pistol/qwen21-geometry-reference-v2-20261114'
SOURCE=ROOT/'assets/generated/inventory-10mm-pistol/seedvr2-x4-20261113'
REF=Path('C:/Users/ADMINI~1/AppData/Local/Temp/codex-clipboard-ef67cc54-b8a6-463c-8e31-81fa2626b33a.png')
spec=importlib.util.spec_from_file_location('helpers',ROOT/'work/hd-inventory-pistol/20261113/seed-pistol.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
PROMPT='Create one faithful HD 2D inventory sprite of the original Fallout 1 Colt 6520 10mm pistol using these two references. Image 1 is the ORIGINAL GAME ART and is the primary authority for the recognizable design, broad painted shapes, worn dark grey steel, muted brown ribbed lower component, restrained original lighting, material character and amount of detail. Image 2 is ONLY a guide to coherent geometry, camera angle and arrangement of the existing parts. Borrow its left-facing three-quarter view: the muzzle face is at the upper LEFT and the vertical grip at the lower RIGHT. Borrow its straight long upper body, aligned single main circular muzzle, smaller front fittings, correctly connected trigger guard, lower ribbed component and grip placement. Translate the original game design into that pose. Keep the original Fallout drawing as much as possible: retain its proportions and characteristic blocky retrofuturistic Colt 6520 design, muted worn colours and simple strong shapes. Reveal existing original details, do not redesign or modernize the weapon and do not overdecorate it. Do not copy the studio render finish or fine etched patterns from Image 2. No new barrels, scopes, rails, extra apertures, fantasy panels, new mechanical parts, logos or inscriptions. Smooth intact metal contours, subtle wear, coherent modest highlights, no jagged edges. One complete pistol centered on the square canvas, fitting inside the central 86 percent of the width and 80 percent of the height, with clear transparent margins on every side. Native transparent background and transparent trigger opening. No hand, scene, pedestal, ground shadow, black background, text or watermark. Output only the single left-facing pistol, not a comparison sheet.'
def save(name,value):(OUT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def n(kind,**inputs):return dict(class_type=kind,inputs=inputs)
def submit():
 OUT.mkdir(parents=True,exist_ok=True)
 if (OUT/'run.json').exists():raise RuntimeError('Existing run; use collect.')
 h.idle();shutil.copy2(REF,OUT/'user-geometry-reference.png')
 native=Image.open(SOURCE/'pistol-native.png').convert('RGBA');assert native.size==(70,63)
 canvas=Image.new('RGBA',(80,80),(0,0,0,0));canvas.paste(native,(5,8));canvas.save(OUT/'source-padded.png')
 ref=Image.open(OUT/'user-geometry-reference.png').convert('RGB');pad=Image.new('RGB',(1088,608),(12,12,12));pad.paste(ref,((1088-ref.width)//2,(608-ref.height)//2));pad.save(OUT/'geometry-padded.png')
 shutil.copy2(SOURCE/'source.json',OUT/'source.json');shutil.copy2(SOURCE/'pistol-native.png',OUT/'source-native.png')
 schemas=h.req('/object_info');first=h.upload(OUT/'source-padded.png');second=h.upload(OUT/'geometry-padded.png');prefix='fallout1_qwen21_pistol_geometry_v2/'+uuid.uuid4().hex
 graph={'1':n('LoadImage',image=first),'2':n('JoinImageWithAlpha',image=['1',0],alpha=['1',1]),'3':n('ImageScale',image=['2',0],upscale_method='lanczos',width=960,height=960,crop='disabled'),'4':n('UNETLoader',unet_name='qwen_image_2.1_int8_convrot.safetensors',weight_dtype='default'),'5':n('CLIPLoader',clip_name='qwen3vl_8b_int8_convrot.safetensors',type='qwen_image',device='default'),'6':n('VAELoader',vae_name='qwen_image_2.1_vae_bf16.safetensors'),'7':n('QwenImage21Cache',model=['4',0],device='cpu',dtype='default'),'8':n('TextEncodeQwenImage21',clip=['5',0],prompt=PROMPT,negative_prompt='',vae=['6',0],resolution=0,**{'images.image_1':['3',0],'images.image_2':['12',0]}),'9':n('KSampler',model=['7',0],positive=['8',0],negative=['8',1],latent_image=['8',2],seed=14112026,steps=25,cfg=1.0,sampler_name='euler',scheduler='simple',denoise=1.0),'10':n('VAEDecode',samples=['9',0],vae=['6',0]),'11':n('SaveImage',images=['10',0],filename_prefix=prefix+'/pistol-geometry-v2-raw'),'12':n('LoadImage',image=second),'13':n('SaveImage',images=['3',0],filename_prefix=prefix+'/original-working')}
 wf=h.workflow(graph,schemas);wf['extra']['notes']='Qwen Image 2.1 two references: original Fallout inventory art for design; user reference for left-facing geometry and pose. Separate candidate, not installed.'
 save('prompt-api.json',graph);save('workflow.json',wf);(OUT/'prompt.txt').write_text(PROMPT+'\n',encoding='utf-8')
 save('plan.json',dict(status='candidate_not_installed',model=graph['4']['inputs']['unet_name'],clip=graph['5']['inputs']['clip_name'],vae=graph['6']['inputs']['vae_name'],seed=14112026,steps=25,cfg=1,denoise=1,sampler='euler',scheduler='simple',working=[960,960],references=[dict(role='primary original design',file='source-native.png',sha256=h.sha(OUT/'source-native.png')),dict(role='geometry and left-facing pose',file='user-geometry-reference.png',sha256=h.sha(OUT/'user-geometry-reference.png'))],runtime_asset_sha256=h.sha(ROOT/'runtime/hd-world-pilot/data/art/hd/inventory/10mm-pistol/pistol.rgba')))
 h.idle();run=h.req('/prompt',dict(prompt=graph,client_id='pistol-geometry-v2-'+uuid.uuid4().hex,extra_data={'extra_pnginfo':{'workflow':wf}}));save('run.json',run)
 if run.get('node_errors'):raise RuntimeError(run)
 print(json.dumps(run),flush=True)
def collect():
 pid=json.loads((OUT/'run.json').read_text())['prompt_id'];start=time.monotonic()
 while True:
  history=h.req('/history/'+pid)
  if pid in history:break
  if time.monotonic()-start>3600:raise TimeoutError('Resume collect later; do not resubmit.')
  print('Waiting for local Qwen geometry candidate',flush=True);time.sleep(20)
 job=history[pid];save('history.json',job)
 if job['status']['status_str']!='success':raise RuntimeError(job['status'])
 for node,name in [('11','pistol-geometry-v2-raw.png'),('13','original-working.png')]:
  rec=job['outputs'][node]['images'][0]
  with urllib.request.urlopen(h.BASE+'/view?'+urllib.parse.urlencode(rec),timeout=30) as response:(OUT/name).write_bytes(response.read())
 im=Image.open(OUT/'pistol-geometry-v2-raw.png');assert im.size==(960,960)
 events=dict(job['status']['messages']);elapsed=(events['execution_success']['timestamp']-events['execution_start']['timestamp'])/1000
 save('result.json',dict(status='generated_for_review',mode=im.mode,size=list(im.size),elapsed_seconds=elapsed,prompt_id=pid,sha256=h.sha(OUT/'pistol-geometry-v2-raw.png'),installed=False));print('Collected local Qwen candidate in '+str(elapsed)+' sec',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['submit','collect']);a=p.parse_args();{'submit':submit,'collect':collect}[a.action]()
