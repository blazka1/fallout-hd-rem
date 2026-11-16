from pathlib import Path
import importlib.util,json,uuid,shutil,time,urllib.request,urllib.parse,argparse
from PIL import Image,ImageDraw,ImageFont
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'assets/generated/inventory-10mm-pistol/qwen21-current-hd-details-v6-20261114'
OUT=ROOT/'assets/generated/inventory-10mm-pistol/qwen21-subtle-rust-v7-20261114'
spec=importlib.util.spec_from_file_location('h',ROOT/'work/hd-inventory-pistol/20261113/seed-pistol.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
PROMPT='Make one extremely subtle local material edit to this exact approved Fallout 1 pistol artwork. Add only a FEW TINY speckles of old muted dark reddish-brown surface rust in two or three existing metal seam recesses and around small fasteners. Rust should cover LESS THAN ONE PERCENT of the steel surface and should be barely noticeable at first glance. Keep the steel predominantly its existing worn dark grey colour. No bright orange rust, broad brown patches, overall orange tint, flakes, holes, new scratches, dirt, new damage, added texture everywhere, or corrosion on the brown grip and ribbed lower component. Preserve the entire pistol drawing as closely as possible: exact silhouette, geometry, all mechanical details, muzzle, perspective, grip, original worn metal texture, edge highlights, lighting, colours, position, scale and framing. Do not redesign, retouch or sharpen anything else. Keep the original transparent background and trigger opening. One identical pistol with only those minimal traces of oxidation.'
def save(name,obj):(OUT/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def submit():
 OUT.mkdir(parents=True,exist_ok=True)
 if (OUT/'run.json').exists():raise RuntimeError('Already submitted; collect.')
 h.idle();source=BASE/'pistol-current-plus-details.png';shutil.copy2(source,OUT/'approved-base.png');assert Image.open(source).size==(768,768)
 graph=json.loads((BASE/'prompt-api.json').read_text());graph['1']['inputs']['image']=h.upload(OUT/'approved-base.png')
 for node in ['12','13','14']:graph.pop(node,None)
 graph['8']['inputs'].pop('images.image_2',None);graph['8']['inputs']['prompt']=PROMPT
 graph['9']['inputs']['seed']=14112028
 graph['11']['inputs']['filename_prefix']='fallout1_pistol_subtle_rust/'+uuid.uuid4().hex+'/pistol-subtle-rust'
 wf=h.workflow(graph,h.req('/object_info'));wf['extra']['notes']='Minimal rust edit of user-liked current HD plus details. Single approved reference; raw preview; no installation.'
 save('prompt-api.json',graph);save('workflow.json',wf);(OUT/'prompt.txt').write_text(PROMPT+'\n',encoding='utf-8')
 save('plan.json',dict(status='preview',source=str(source.relative_to(ROOT)),source_sha256=h.sha(source),requested='Very slight extra rust; preserve approved detail variant',working=[768,768],seed=14112028,steps=25,cfg=1,denoise=1,model=graph['4']['inputs']['unet_name'],runtime_sha256=h.sha(ROOT/'runtime/hd-world-pilot/data/art/hd/inventory/10mm-pistol/pistol.rgba')))
 h.idle();run=h.req('/prompt',dict(prompt=graph,client_id='pistol-rust-'+uuid.uuid4().hex,extra_data={'extra_pnginfo':{'workflow':wf}}));save('run.json',run)
 if run.get('node_errors'):raise RuntimeError(run)
 print(json.dumps(run),flush=True)
def collect():
 pid=json.loads((OUT/'run.json').read_text())['prompt_id'];started=time.monotonic()
 while True:
  hist=h.req('/history/'+pid)
  if pid in hist:break
  if time.monotonic()-started>3600:raise TimeoutError('Resume collect; job not cancelled.')
  print('Waiting for subtle rust edit',flush=True);time.sleep(20)
 job=hist[pid];save('history.json',job)
 if job['status']['status_str']!='success':raise RuntimeError(job['status'])
 rec=job['outputs']['11']['images'][0]
 with urllib.request.urlopen(h.BASE+'/view?'+urllib.parse.urlencode(rec),timeout=30) as response:(OUT/'pistol-subtle-rust.png').write_bytes(response.read())
 before=Image.open(OUT/'approved-base.png').convert('RGBA');after=Image.open(OUT/'pistol-subtle-rust.png').convert('RGBA');assert after.size==(768,768)
 aa=np.array(before)[:,:,3]>=128;ab=np.array(after)[:,:,3]>=128
 canvas=Image.new('RGB',(960,490),(30,35,35));d=ImageDraw.Draw(canvas);f=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
 for i,(im,label) in enumerate(zip([before,after],['Одобренный вариант','Чуть больше ржавчины'])):
  a=np.array(im)[:,:,3];ys,xs=np.where(a>=128);pic=im.crop((int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)));s=min(420/pic.width,390/pic.height);pic=pic.resize((round(pic.width*s),round(pic.height*s)),Image.Resampling.LANCZOS)
  d.text((i*480+20,18),label,font=f,fill=(232,226,204));canvas.paste(pic,(i*480+(480-pic.width)//2,68+(390-pic.height)//2),pic)
 d.line((480,12,480,470),fill=(64,70,66));canvas.save(OUT/'comparison.png')
 events=dict(job['status']['messages']);elapsed=(events['execution_success']['timestamp']-events['execution_start']['timestamp'])/1000
 plan=json.loads((OUT/'plan.json').read_text());assert plan['runtime_sha256']==h.sha(ROOT/'runtime/hd-world-pilot/data/art/hd/inventory/10mm-pistol/pistol.rgba')
 save('result.json',dict(status='generated_for_review',prompt_id=pid,sha256=h.sha(OUT/'pistol-subtle-rust.png'),elapsed_seconds=elapsed,mask_iou_diagnostic=float((aa&ab).sum()/max(1,(aa|ab).sum())),installed=False));print(str(OUT/'pistol-subtle-rust.png'),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['submit','collect']);args=p.parse_args();{'submit':submit,'collect':collect}[args.action]()
