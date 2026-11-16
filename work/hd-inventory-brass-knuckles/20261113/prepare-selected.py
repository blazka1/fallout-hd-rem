from pathlib import Path
import importlib.util,json,uuid,time,urllib.request,urllib.parse,struct,hashlib,shutil
from PIL import Image
import numpy as np
root=Path('.').resolve();src=root/'assets/generated/inventory-brass-knuckles/qwen21-x4-20261113';out=root/'assets/hd/inventory/brass-knuckles/v1';out.mkdir(parents=True,exist_ok=True)
spec=importlib.util.spec_from_file_location('helper',root/'work/hd-inventory-brass-knuckles/20261113/seed-knuckles.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
def save(name,data):(src/name).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
def n(kind,**inputs):return {'class_type':kind,'inputs':inputs}
if not (src/'postprocess-run.json').exists():
 h.idle();image=h.upload(src/'knuckles-qwen21-raw.png');prefix='fallout1_qwen21_knuckles_framed/'+uuid.uuid4().hex
 graph={'1':n('LoadImage',image=image),'2':n('InvertMask',mask=['1',1]),'3':n('ThresholdMask',mask=['2',0],value=15/255),'4':n('MaskComposite',destination=['2',0],source=['3',0],x=0,y=0,operation='multiply'),'5':n('InvertMask',mask=['4',0]),'6':n('JoinImageWithAlpha',image=['1',0],alpha=['5',0]),'7':n('ImageCrop',image=['6',0],width=972,height=780,x=84,y=84),'8':n('ImageScale',image=['7',0],upscale_method='lanczos',width=324,height=260,crop='disabled'),'9':n('SaveImage',images=['8',0],filename_prefix=prefix+'/knuckles-hd-x4'),'10':n('SaveImage',images=['6',0],filename_prefix=prefix+'/knuckles-master-clean')}
 save('postprocess-api.json',graph);save('postprocess-workflow.json',h.workflow(graph,h.req('/object_info')))
 save('postprocess-run.json',h.req('/prompt',{'prompt':graph,'client_id':'knuckles-post-'+uuid.uuid4().hex}))
run=json.loads((src/'postprocess-run.json').read_text())
for i in range(40):
 history=h.req('/history/'+run['prompt_id'])
 if run['prompt_id'] in history:break
 time.sleep(1)
job=history[run['prompt_id']];save('postprocess-history.json',job);assert job['status']['status_str']=='success'
for node,name in [('9','knuckles-hd-x4.png'),('10','knuckles-master.png')]:
 rec=job['outputs'][node]['images'][0]
 with urllib.request.urlopen(h.BASE+'/view?'+urllib.parse.urlencode(rec)) as r:(out/name).write_bytes(r.read())
raw=Image.open(out/'knuckles-master.png').convert('RGBA');a=np.array(raw)[:,:,3];outside=a>0;outside[84:864,84:1056]=False
assert not outside.any(),'Cleaned master content clipped'
im=Image.open(out/'knuckles-hd-x4.png').convert('RGBA');assert im.size==(324,260)
(out/'knuckles.rgba').write_bytes(struct.pack('<4sIIII',b'F1HD',1,324,260,4)+im.tobytes())
for name in ['source.json','workflow.json','prompt-api.json','prompt.txt','result.json','postprocess-api.json','postprocess-workflow.json']:shutil.copyfile(src/name,out/name)
manifest={'status':'selected_for_integration','selection':'Assistant selected Qwen for detail and silhouette preservation; user requested redrawing the next inventory item in the established HD workflow','pid':21,'inventory_fid':117440652,'inventory_art':'art/inven/brsnuck.frm','native_size':[81,65],'hd_size':[324,260],'master_size':[1152,960],'source_generation':str(src.relative_to(root)),'framing_crop':[84,84,972,780],'opaque_pixels_clipped':0,'postprocess':'ComfyUI: remove alpha<=15 background noise; retain higher alpha; crop to original native canvas at unchanged aspect ratio; Lanczos to 324x260','format':'F1HD RGBA8, exact decoded selected PNG bytes','classic_fallback':'Original brsnuck.frm in DAT, no loose FRM override','files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file() and p.name!='manifest.json'}}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8');print('Prepared full-colour knuckles; no cleaned master pixels clipped.')
