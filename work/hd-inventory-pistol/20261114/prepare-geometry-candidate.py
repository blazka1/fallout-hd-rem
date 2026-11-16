from pathlib import Path
import importlib.util,json,uuid,time,urllib.request,urllib.parse,math
from PIL import Image,ImageDraw,ImageFont
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('job',Path(__file__).with_name('qwen-pistol-geometry.py'));job=importlib.util.module_from_spec(spec);spec.loader.exec_module(job)
h=job.h;OUT=job.OUT
raw=Image.open(OUT/'pistol-geometry-v2-raw.png');assert raw.mode=='RGBA'
a=np.array(raw)[:,:,3];ys,xs=np.where(a>15);assert len(xs)>0
bbox=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
assert bbox[0]>0 and bbox[1]>0 and bbox[2]<raw.width and bbox[3]<raw.height,'Generated content touches canvas: review before cropping.'
k=max(math.ceil((bbox[2]-bbox[0]+24)/10),math.ceil((bbox[3]-bbox[1]+24)/9));w,hgt=10*k,9*k
assert w<=raw.width and hgt<=raw.height,'Cannot fit 10:9 framing without clipping.'
x=max(0,min(raw.width-w,round((bbox[0]+bbox[2]-w)/2)));y=max(0,min(raw.height-hgt,round((bbox[1]+bbox[3]-hgt)/2)))
def n(kind,**inputs):return dict(class_type=kind,inputs=inputs)
if not (OUT/'postprocess-run.json').exists():
 h.idle();source=h.upload(OUT/'pistol-geometry-v2-raw.png');prefix='fallout1_qwen21_pistol_geometry_v2_clean/'+uuid.uuid4().hex
 graph={'1':n('LoadImage',image=source),'2':n('InvertMask',mask=['1',1]),'3':n('ThresholdMask',mask=['2',0],value=15/255),'4':n('MaskComposite',destination=['2',0],source=['3',0],x=0,y=0,operation='multiply'),'5':n('InvertMask',mask=['4',0]),'6':n('JoinImageWithAlpha',image=['1',0],alpha=['5',0]),'7':n('ImageCrop',image=['6',0],width=w,height=hgt,x=x,y=y),'8':n('ImageScale',image=['7',0],upscale_method='lanczos',width=280,height=252,crop='disabled'),'9':n('SaveImage',images=['8',0],filename_prefix=prefix+'/pistol-candidate-x4'),'10':n('SaveImage',images=['7',0],filename_prefix=prefix+'/pistol-candidate-master')}
 job.save('postprocess-api.json',graph);wf=h.workflow(graph,h.req('/object_info'));wf['extra']['notes']='Candidate only. Remove alpha<=15 background noise, retain soft alpha, proportional 10:9 crop retaining content, Lanczos to inventory x4. No installed asset changed.';job.save('postprocess-workflow.json',wf)
 job.save('postprocess-run.json',h.req('/prompt',dict(prompt=graph,client_id='pistol-geometry-post-'+uuid.uuid4().hex,extra_data={'extra_pnginfo':{'workflow':wf}})))
pid=json.loads((OUT/'postprocess-run.json').read_text())['prompt_id']
for _ in range(60):
 history=h.req('/history/'+pid)
 if pid in history:break
 time.sleep(1)
result=history[pid];job.save('postprocess-history.json',result);assert result['status']['status_str']=='success'
for node,name in [('9','pistol-candidate-x4.png'),('10','pistol-candidate-master.png')]:
 rec=result['outputs'][node]['images'][0]
 with urllib.request.urlopen(h.BASE+'/view?'+urllib.parse.urlencode(rec),timeout=30) as response:(OUT/name).write_bytes(response.read())
outside=a>15;outside[y:y+hgt,x:x+w]=False;assert not outside.any()
plan=json.loads((OUT/'plan.json').read_text());assert h.sha(ROOT/'runtime/hd-world-pilot/data/art/hd/inventory/10mm-pistol/pistol.rgba')==plan['runtime_asset_sha256']
job.save('candidate.json',dict(status='candidate_not_installed',direction='left-facing to match user geometry reference',master_bbox_alpha_gt15=bbox,framing_crop=[x,y,w,hgt],cleaned_pixels_clipped=0,postprocess='ComfyUI alpha<=15 noise cleanup, preserve higher alpha, crop 10:9, Lanczos to 280x252',output_size=[280,252],master_size=[w,hgt],candidate_sha256=h.sha(OUT/'pistol-candidate-x4.png'),runtime_unchanged=True))
pictures=[Image.open(job.SOURCE/'pistol-native.png').convert('RGBA').resize((280,252),Image.Resampling.NEAREST),Image.open(ROOT/'assets/hd/inventory/10mm-pistol/v1/pistol-hd-x4.png').convert('RGBA'),Image.open(OUT/'pistol-candidate-x4.png').convert('RGBA')]
canvas=Image.new('RGB',(1020,330),(30,35,35));d=ImageDraw.Draw(canvas);f=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',21)
for i,(pic,label) in enumerate(zip(pictures,['Оригинал Fallout','Сейчас в игре','Новый ракурс'])):
 d.text((i*340+20,16),label,font=f,fill=(231,226,207));canvas.paste(pic,(i*340+30,61),pic)
canvas.save(OUT/'comparison.png')
print('Candidate prepared; installed pistol unchanged. Crop:',x,y,w,hgt,flush=True)
