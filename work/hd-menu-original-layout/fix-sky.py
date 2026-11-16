"""Repair a compositing seam using the existing clean Qwen source, no new generation."""
from pathlib import Path
import importlib.util,json,time,urllib.request,urllib.parse
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('menu',ROOT/'work/hd-menu-seed-qwen/pipeline.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
OUT=ROOT/'assets/generated/main-menu/sky-seam-fix-20261114';OUT.mkdir(parents=True,exist_ok=True)
if (OUT/'run.json').exists():raise RuntimeError('Existing run retained; inspect history before resubmitting.')
m.helpers.idle()
base=ROOT/'assets/hd/main-menu/background-seed-qwen-v2/background-4k.png'
clean=ROOT/'assets/generated/main-menu/original-layout-20261114/expanded-working.png'
g={
 '1':m.node('LoadImage',image=m.upload(base)),
 '2':m.node('LoadImage',image=m.upload(clean)),
 '3':m.node('ImageScale',image=['2',0],upscale_method='lanczos',width=3840,height=2160,crop='disabled'),
 '4':m.node('ImageCrop',image=['3',0],x=1696,y=400,width=144,height=880),
 '5':m.node('SolidMask',value=1.0,width=144,height=880),
 '6':m.node('FeatherMask',mask=['5',0],left=24,top=80,right=24,bottom=80),
 '7':m.node('ImageCompositeMasked',destination=['1',0],source=['4',0],x=1696,y=400,resize_source=False,mask=['6',0]),
 '8':m.node('SaveImage',images=['7',0],filename_prefix='fallout1_menu_sky_fix/background-4k')}
m.save(OUT/'prompt-api.json',g);m.save(OUT/'workflow.json',m.helpers.workflow(g,m.helpers.req('/object_info')))
m.save(OUT/'source.json',dict(base=str(base),base_sha256=m.sha(base),clean=str(clean),clean_sha256=m.sha(clean),patch=[1696,400,144,880],method='Existing clean Qwen sky composited through a local feathered mask; no new generated pixels'))
m.helpers.idle();r=m.helpers.req('/prompt',dict(prompt=g,client_id='sky-seam-fix-20261114'));m.save(OUT/'run.json',r)
for i in range(30):
 h=m.helpers.req('/history/'+r['prompt_id'])
 if r['prompt_id'] in h:break
 time.sleep(1)
job=h[r['prompt_id']];m.save(OUT/'history.json',job);assert job['status']['status_str']=='success'
record=job['outputs']['8']['images'][0]
with urllib.request.urlopen(m.helpers.BASE+'/view?'+urllib.parse.urlencode(record)) as response:(OUT/'background-4k.png').write_bytes(response.read())
print(str(OUT/'background-4k.png'))
