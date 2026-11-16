from pathlib import Path
import argparse,importlib.util,json,time,uuid,urllib.request,urllib.parse
from PIL import Image,ImageDraw,ImageFont
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'assets/generated/inventory-knife/qwen21-clean-edges-v4-20261113'
OUT=ROOT/'assets/generated/inventory-knife/qwen21-handle-fill-v5-20261113'
REFERENCE_OVERRIDE=None
s=importlib.util.spec_from_file_location('helper',Path(__file__).with_name('knife-upscale.py'));h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
PROMPT='''Make one small local repair to this exact knife: fill the missing pieces along the BOTTOM edge of the BROWN HANDLE, between the rusty guard and the silver pommel.
There are several black/transparent bite-shaped holes and deep angular notches cutting into the underside of the brown grip. These are missing material, NOT finger grooves. Paint continuous dark brown grip material into those missing areas, matching the adjacent worn brown surface, grain, shading and thickness. Bridge the gaps so the underside becomes a solid, smooth gently curved uninterrupted edge from just behind the guard to the metal pommel. Fill the deeper rectangular notch below the right-hand fastener and the smaller bite close to the guard. The grip must no longer look torn or eaten away. Keep the existing TWO golden metal fasteners in place. Do not make a new handle: retain its length, upper contour, thickness and overall angle, only reconstruct the missing lower edge.
Keep the rest of the image unchanged: the repaired continuous blade tip without a fracture, blade groove, muted matte steel, small rust patches, rounded rusty guard, silver pommel, lighting, framing and position. Do not increase detail, gloss, contrast, sharpness or rust. No added parts or markings. The added grip material is opaque; the space outside the completed knife stays genuinely transparent. Output the same single knife with only this local underside repair.'''
def save(name,v):(OUT/name).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def submit():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'run.json').exists():raise RuntimeError('Already submitted; collect.')
    h.idle();src=REFERENCE_OVERRIDE or BASE/'knife-clean-raw.png';(OUT/'reference.png').write_bytes(src.read_bytes());(OUT/'source.json').write_bytes((BASE/'source.json').read_bytes())
    graph=json.loads((BASE/'prompt-api.json').read_text());graph['1']['inputs']['image']=h.upload(OUT/'reference.png');graph['8']['inputs']['prompt']=PROMPT
    token=uuid.uuid4().hex;cid='qwen-knife-handle-'+token
    for node,name in [('11','knife-handle-raw'),('12','reference-working'),('15','knife-handle-x4')]:graph[node]['inputs']['filename_prefix']='fallout1_qwen21_handle/'+token+'/'+name
    wf=h.workflow(graph,h.req('/object_info'));save('workflow.json',wf);save('prompt-api.json',graph);(OUT/'prompt.txt').write_text(PROMPT,encoding='utf-8')
    save('plan.json',dict(client_id=cid,reference=str(src),reference_sha256=h.sha(src),target='Fill missing brown grip material on underside, keeping both metal fasteners',seed=graph['9']['inputs']['seed'],steps=25,working_size=[1152,576],target_size=[352,132],crop=[32,78,1088,408]))
    h.idle();run=h.req('/prompt',dict(prompt=graph,client_id=cid,extra_data={'extra_pnginfo':{'workflow':wf}}));run['client_id']=cid;save('run.json',run);print(json.dumps(run),flush=True)
def collect():
    pid=json.loads((OUT/'run.json').read_text())['prompt_id'];start=time.monotonic()
    while True:
        hist=h.req('/history/'+pid)
        if pid in hist:break
        if time.monotonic()-start>1800:raise TimeoutError('Resume collect, never resubmit.')
        print('Waiting for handle repair '+pid,flush=True);time.sleep(15)
    job=hist[pid];save('history.json',job);assert job['status']['status_str']=='success',job['status']
    for node,name in [('11','knife-handle-raw.png'),('15','knife-handle-x4.png')]:
        rec=job['outputs'][node]['images'][0]
        with urllib.request.urlopen(h.BASE+'/view?'+urllib.parse.urlencode(rec)) as r:(OUT/name).write_bytes(r.read())
    raw=Image.open(OUT/'knife-handle-raw.png');im=Image.open(OUT/'knife-handle-x4.png');assert raw.mode==im.mode=='RGBA' and raw.size==(1152,576) and im.size==(352,132)
    a=np.array(raw)[:,:,3];m=a>=128;m[78:486,32:1120]=False;assert not m.any()
    events=dict(job['status']['messages']);save('result.json',dict(status='pending_visual_review',elapsed_seconds=(events['execution_success']['timestamp']-events['execution_start']['timestamp'])/1000,output_sha256=h.sha(OUT/'knife-handle-x4.png'),raw_sha256=h.sha(OUT/'knife-handle-raw.png'),output_size=[352,132],mode='RGBA',opaque_pixels_clipped=0,integration='not_installed'))
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
    comp=Image.new('RGB',(800,220),(34,38,38));d=ImageDraw.Draw(comp)
    for i,pic in enumerate([Image.open(BASE/'knife-clean-x4.png'),im]):d.text((i*400+14,14),['До','После'][i],font=font,fill='white');comp.paste(pic,(i*400+24,60),pic)
    comp.save(OUT/'comparison.png')
    detail=Image.new('RGB',(800,380),(34,38,38));d=ImageDraw.Draw(detail)
    for i,pic in enumerate([Image.open(BASE/'knife-clean-raw.png'),raw]):
        crop=pic.crop((736,64,1136,400));detail.paste(crop,(i*400,44),crop);d.text((i*400+14,12),['Рукоять до','Рукоять после'][i],font=font,fill='white')
    detail.save(OUT/'handle-detail.png')
    light=Image.new('RGB',(400,180),(235,235,225));light.paste(im,(24,24),im);light.save(OUT/'light-background.png')
    print((OUT/'result.json').read_text(),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['submit','collect']);a=p.parse_args();{'submit':submit,'collect':collect}[a.action]()
