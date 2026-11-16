from pathlib import Path
import importlib.util,json,uuid,shutil,time,urllib.request,urllib.parse,argparse
from PIL import Image,ImageDraw,ImageFont
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'assets/generated/inventory-10mm-pistol/qwen21-current-hd-details-v6-20261114'
CURRENT=ROOT/'assets/hd/inventory/10mm-pistol/v1/pistol-hd-x4.png'
DETAILS=ROOT/'build/hd-inventory-comparisons/pistol-geometry-20261114/pistol-mirrored.png'
spec=importlib.util.spec_from_file_location('h',ROOT/'work/hd-inventory-pistol/20261113/seed-pistol.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
PROMPT='Edit IMAGE 1, the current Fallout 1 Colt 6520 10mm pistol HD inventory artwork. IMAGE 1 is the base to preserve. Keep its silhouette, tall proportions, precise three-quarter perspective, strong foreshortening, position, framing, existing uneven worn dark steel and brown materials, lighting and recognizable original Fallout design. Its single main round muzzle faces UPPER RIGHT and its upright grip is at LOWER LEFT. Do not flatten, stretch, rotate or replace this pistol with image 2. Use IMAGE 2 only as a secondary reference for carefully chosen small construction and surface details to add onto matching existing parts of IMAGE 1: coherent recessed grooves in the existing upper slide and side panels, rounded machined bevels and concentric inner rim on the existing muzzle, small restrained flush screw heads and fastening points, cleaner well-defined ribs on the existing brown lower component and grip, and smooth functional edges on the existing trigger guard and cylindrical side mechanism. Preserve all existing major parts and their locations in image 1. Maintain its slightly battered post-apocalyptic metal and selective warm steel edge highlights. Improve clarity and plausible craftsmanship with modest detail rather than making a new design. Do not transfer image 2 flat broad profile, clean black plastic appearance, logo, text or studio lighting. No new barrels, extra muzzle holes, attachments, new protruding mechanisms, scopes, rails, inscriptions, symbols, background or shadows. Do not add random panels, excessive scratches, rust holes or decorative clutter. One complete pistol in the exact original pose and canvas placement of image 1. Transparent background and clear transparent trigger opening. The result must still immediately read as IMAGE 1 with useful details borrowed from IMAGE 2, not as IMAGE 2 redrawn.'
def save(name,obj):(OUT/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def n(kind,**inputs):return dict(class_type=kind,inputs=inputs)
def submit():
 OUT.mkdir(parents=True,exist_ok=True)
 if (OUT/'run.json').exists():raise RuntimeError('Already submitted; collect.')
 h.idle();shutil.copy2(CURRENT,OUT/'current-hd.png');shutil.copy2(DETAILS,OUT/'new-detail-reference.png')
 im=Image.open(CURRENT).convert('RGBA');assert im.size==(280,252)
 canvas=Image.new('RGBA',(320,320),(0,0,0,0));canvas.paste(im,(20,32));canvas.save(OUT/'current-padded.png')
 first=h.upload(OUT/'current-padded.png');second=h.upload(OUT/'new-detail-reference.png');prefix='fallout1_pistol_current_hd_details/'+uuid.uuid4().hex
 graph={'1':n('LoadImage',image=first),'2':n('JoinImageWithAlpha',image=['1',0],alpha=['1',1]),'3':n('ImageScale',image=['2',0],upscale_method='lanczos',width=768,height=768,crop='disabled'),'4':n('UNETLoader',unet_name='qwen_image_2.1_int8_convrot.safetensors',weight_dtype='default'),'5':n('CLIPLoader',clip_name='qwen3vl_8b_int8_convrot.safetensors',type='qwen_image',device='default'),'6':n('VAELoader',vae_name='qwen_image_2.1_vae_bf16.safetensors'),'7':n('QwenImage21Cache',model=['4',0],device='cpu',dtype='default'),'8':n('TextEncodeQwenImage21',clip=['5',0],prompt=PROMPT,negative_prompt='',vae=['6',0],resolution=0,**{'images.image_1':['3',0],'images.image_2':['14',0]}),'9':n('KSampler',model=['7',0],positive=['8',0],negative=['8',1],latent_image=['8',2],seed=14112027,steps=25,cfg=1.0,sampler_name='euler',scheduler='simple',denoise=1.0),'10':n('VAEDecode',samples=['9',0],vae=['6',0]),'11':n('SaveImage',images=['10',0],filename_prefix=prefix+'/pistol-current-plus-details'),'12':n('LoadImage',image=second),'13':n('JoinImageWithAlpha',image=['12',0],alpha=['12',1]),'14':n('ImageScale',image=['13',0],upscale_method='lanczos',width=512,height=512,crop='disabled')}
 wf=h.workflow(graph,h.req('/object_info'));wf['extra']['notes']='Preserve current installed pistol HD geometry; borrow selective surface and construction detail from new mirrored candidate. Raw preview only.'
 save('prompt-api.json',graph);save('workflow.json',wf);(OUT/'prompt.txt').write_text(PROMPT+'\n',encoding='utf-8')
 save('plan.json',dict(status='preview_not_installed',base='current installed HD pistol',geometry='preserve current image 1',detail_reference='new mirrored image 2',working=[768,768],detail_reference_working=[512,512],seed=14112027,steps=25,cfg=1,denoise=1,source_sha256=h.sha(CURRENT),detail_sha256=h.sha(DETAILS),runtime_rgba_sha256=h.sha(ROOT/'runtime/hd-world-pilot/data/art/hd/inventory/10mm-pistol/pistol.rgba')))
 h.idle();result=h.req('/prompt',dict(prompt=graph,client_id='pistol-detail-'+uuid.uuid4().hex,extra_data={'extra_pnginfo':{'workflow':wf}}));save('run.json',result)
 if result.get('node_errors'):raise RuntimeError(result)
 print(json.dumps(result),flush=True)
def collect():
 pid=json.loads((OUT/'run.json').read_text())['prompt_id'];start=time.monotonic()
 while True:
  hist=h.req('/history/'+pid)
  if pid in hist:break
  if time.monotonic()-start>7200:raise TimeoutError('Resume collect; job not cancelled.')
  print('Waiting for current HD plus details',flush=True);time.sleep(20)
 job=hist[pid];save('history.json',job)
 if job['status']['status_str']!='success':raise RuntimeError(job['status'])
 rec=job['outputs']['11']['images'][0]
 with urllib.request.urlopen(h.BASE+'/view?'+urllib.parse.urlencode(rec),timeout=30) as response:(OUT/'pistol-current-plus-details.png').write_bytes(response.read())
 result=Image.open(OUT/'pistol-current-plus-details.png').convert('RGBA');assert result.size==(768,768)
 before=Image.open(OUT/'current-hd.png').convert('RGBA');newref=Image.open(OUT/'new-detail-reference.png').convert('RGBA')
 canvas=Image.new('RGB',(1200,420),(30,35,35));d=ImageDraw.Draw(canvas);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',21);sm=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17)
 for i,(im,label) in enumerate(zip([before,newref,result],['Текущий HD — основа','Новый — образец деталей','HD + детали — результат'])):
  a=np.array(im)[:,:,3];yy,xx=np.where(a>=128);box=(int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1));crop=im.crop(box);scale=min(350/crop.width,320/crop.height);crop=crop.resize((round(crop.width*scale),round(crop.height*scale)),Image.Resampling.LANCZOS)
  d.text((i*400+16,17),label,font=font,fill=(232,226,204));canvas.paste(crop,(i*400+(400-crop.width)//2,63+(320-crop.height)//2),crop)
  if i:d.line((i*400,12,i*400,389),fill=(64,70,66))
 d.text((20,394),'Сравнение при одинаковом размере показа, без искажения пропорций.',font=sm,fill=(180,184,175));canvas.save(OUT/'comparison.png')
 plan=json.loads((OUT/'plan.json').read_text());assert plan['runtime_rgba_sha256']==h.sha(ROOT/'runtime/hd-world-pilot/data/art/hd/inventory/10mm-pistol/pistol.rgba')
 events=dict(job['status']['messages']);elapsed=(events['execution_success']['timestamp']-events['execution_start']['timestamp'])/1000
 save('result.json',dict(status='generated_for_visual_review',prompt_id=pid,sha256=h.sha(OUT/'pistol-current-plus-details.png'),elapsed_seconds=elapsed,installed=False));print(str(OUT/'comparison.png'),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['submit','collect']);a=p.parse_args();{'submit':submit,'collect':collect}[a.action]()
