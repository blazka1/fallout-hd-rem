from pathlib import Path
import importlib.util,json,uuid,time,urllib.request,urllib.parse,struct,hashlib,shutil
from PIL import Image
import numpy as np
root=Path.cwd();src=root/'assets/generated/inventory-10mm-pistol/qwen21-subtle-rust-v7-20261114';out=root/'assets/hd/inventory/10mm-pistol/v2';out.mkdir(parents=True,exist_ok=True)
spec=importlib.util.spec_from_file_location('helper',root/'work/hd-inventory-pistol/20261113/seed-pistol.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
def save(name,data):(src/name).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
def n(kind,**inputs):return {'class_type':kind,'inputs':inputs}
if not (src/'inventory-postprocess-run.json').exists():
 h.idle();image=h.upload(src/'pistol-subtle-rust.png');prefix='fallout1_pistol_v2_inventory/'+uuid.uuid4().hex
 graph={'1':n('LoadImage',image=image),'2':n('InvertMask',mask=['1',1]),'3':n('ThresholdMask',mask=['2',0],value=15/255),'4':n('MaskComposite',destination=['2',0],source=['3',0],x=0,y=0,operation='multiply'),'5':n('InvertMask',mask=['4',0]),'6':n('JoinImageWithAlpha',image=['1',0],alpha=['5',0]),'7':n('ImageCrop',image=['6',0],width=670,height=603,x=49,y=77),'8':n('ImageScale',image=['7',0],upscale_method='lanczos',width=280,height=252,crop='disabled'),'9':n('SaveImage',images=['8',0],filename_prefix=prefix+'/pistol-hd-x4'),'10':n('SaveImage',images=['6',0],filename_prefix=prefix+'/pistol-master-clean')}
 save('inventory-postprocess-api.json',graph);wf=h.workflow(graph,h.req('/object_info'));wf['extra']['notes']='Prepare user-selected v7 pistol: preserve content and soft alpha, proportional 10:9 crop, Lanczos to existing 280x252 runtime dimensions.';save('inventory-postprocess-workflow.json',wf)
 save('inventory-postprocess-run.json',h.req('/prompt',dict(prompt=graph,client_id='pistol-v2-pack-'+uuid.uuid4().hex,extra_data={'extra_pnginfo':{'workflow':wf}})))
pid=json.loads((src/'inventory-postprocess-run.json').read_text())['prompt_id']
for _ in range(60):
 history=h.req('/history/'+pid)
 if pid in history:break
 time.sleep(1)
job=history[pid];save('inventory-postprocess-history.json',job);assert job['status']['status_str']=='success'
for node,name in [('9','pistol-hd-x4.png'),('10','pistol-master.png')]:
 rec=job['outputs'][node]['images'][0]
 with urllib.request.urlopen(h.BASE+'/view?'+urllib.parse.urlencode(rec)) as response:(out/name).write_bytes(response.read())
raw=Image.open(out/'pistol-master.png').convert('RGBA');a=np.array(raw)[:,:,3];outside=a>0;outside[77:680,49:719]=False;assert not outside.any(),'Cleaned master content clipped'
im=Image.open(out/'pistol-hd-x4.png').convert('RGBA');assert im.size==(280,252)
(out/'pistol.rgba').write_bytes(struct.pack('<4sIIII',b'F1HD',1,280,252,4)+im.tobytes())
assert (out/'pistol.rgba').read_bytes()[20:]==im.tobytes()
for name in ['workflow.json','prompt-api.json','prompt.txt','result.json','plan.json','inventory-postprocess-api.json','inventory-postprocess-workflow.json']:shutil.copy2(src/name,out/name)
shutil.copy2(root/'assets/hd/inventory/10mm-pistol/v1/source.json',out/'source.json')
manifest=dict(status='selected_for_integration',selection='User selected current HD enriched with new-reference details, then requested very slight rust and inventory/HUD/cursor integration',pid=8,inventory_fid=117440516,inventory_art='art/inven/pistol.frm',native_size=[70,63],hd_size=[280,252],master_size=[768,768],source_generation=str(src.relative_to(root)),provenance=['Original pistol FRM -> v1 HD','New left-facing geometry reference -> mirrored candidate','Qwen v6: preserve current v1 HD geometry, borrow candidate details','Qwen v7: extremely subtle rust','Deterministic ComfyUI alpha cleanup and proportional crop'],framing_crop=[49,77,670,603],cleaned_pixels_clipped=0,postprocess='Remove alpha<=15 background noise; retain all higher soft alpha; proportional crop to 10:9; Lanczos to 280x252',format='F1HD RGBA8, byte-identical to decoded selected PNG',classic_fallback='Original DAT FRM retained; no override',files={p.name:h.sha(p) for p in out.iterdir() if p.is_file() and p.name!='manifest.json'})
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print('Prepared v2: 280x252 RGBA; exact F1HD pixels; no cleaned master content clipped.')
