"""Original V13 entrance skeleton through the tested local SeedVR2 image graph."""
from pathlib import Path
import argparse, importlib.util, json, time, uuid, urllib.request, urllib.parse
from PIL import Image,ImageDraw,ImageFont
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'assets/generated/v13ent-door-skeleton-seedvr2/x4-20261113'
REFERENCE=ROOT/'assets/generated/v13ent-door-skeleton-qwen/reference-v1-20261113'
spec=importlib.util.spec_from_file_location('seed_helpers',Path(__file__).with_name('knife-upscale.py'))
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)

def save(name,value):
    (OUT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'plan.json').exists(): print('Prepared plan retained.');return
    provenance=json.loads((REFERENCE/'provenance.json').read_text())
    assets=h.Assets([ROOT/'FALLOUT (extract.me)/MASTER.DAT'])
    raw=assets.read('art/items/v13bones.frm')
    import hashlib
    assert hashlib.sha256(raw).hexdigest()==provenance['source_sha256']
    metadata,directions=h.decode_frm(raw);frame=directions[0][0]
    palette=h.palette_rgb(assets.read('color.pal'))
    png,_=h.rgba_png(frame,palette)
    (OUT/'skeleton-native.png').write_bytes(png)
    native=Image.open(OUT/'skeleton-native.png')
    assert native.size==(67,41) and native.tobytes()==Image.open(REFERENCE/'v13bones-native.png').tobytes()
    (OUT/'skeleton-indexed.png').write_bytes(h.png_indexed(frame.width,frame.height,frame.pixels,palette))
    (OUT/'v13bones.frm').write_bytes(raw)
    save('source.json',provenance)
    graph=json.loads((ROOT/'assets/generated/inventory-knife/seedvr2-x4-20261113/prompt-api.json').read_text())
    graph['1']['inputs']['image']=h.upload(OUT/'skeleton-native.png')
    prefix='fallout1_seedvr2_v13bones/'+uuid.uuid4().hex
    graph['12']['inputs']['filename_prefix']=prefix+'/skeleton-seedvr2-x4'
    graph['13']['inputs']['filename_prefix']=prefix+'/skeleton-lanczos-x4'
    schemas=h.req('/object_info')
    save('prompt-api.json',graph);save('workflow.json',h.workflow(graph,schemas))
    save('plan.json',dict(source_art='art/items/v13bones.frm',map='maps/v13ent.map',object=271,pid=211,fid=113,frame=0,direction=0,native=[67,41],target=[268,164],seed=13112026,steps=1,cfg=1,alpha='Resized source alpha retained by SeedVR2PostProcessing',model='seedvr2_3b_int8_convrot.safetensors',source_sha256=h.sha(OUT/'skeleton-native.png')))
    print('Prepared original V13 skeleton: 67x41 -> 268x164.',flush=True)

def submit():
    if (OUT/'run.json').exists():raise RuntimeError('Already submitted; collect saved run.')
    h.idle()
    graph=json.loads((OUT/'prompt-api.json').read_text());wf=json.loads((OUT/'workflow.json').read_text())
    result=h.req('/prompt',dict(prompt=graph,client_id='seedvr2-v13bones-'+uuid.uuid4().hex,extra_data={'extra_pnginfo':{'workflow':wf}}))
    save('run.json',result)
    if result.get('node_errors'):raise RuntimeError(result)
    print(json.dumps(result),flush=True)

def collect():
    pid=json.loads((OUT/'run.json').read_text())['prompt_id'];start=time.monotonic()
    while True:
        history=h.req('/history/'+pid)
        if pid in history:break
        print('Waiting for skeleton '+pid,flush=True)
        if time.monotonic()-start>1800:raise TimeoutError('Resume collect; do not resubmit.')
        time.sleep(15)
    job=history[pid];save('history.json',job)
    if job['status']['status_str']!='success':raise RuntimeError(job['status'])
    for node,name in [('12','skeleton-seedvr2-x4.png'),('13','skeleton-lanczos-x4.png')]:
        record=job['outputs'][node]['images'][0]
        with urllib.request.urlopen(h.BASE+'/view?'+urllib.parse.urlencode(record),timeout=30) as response:(OUT/name).write_bytes(response.read())
    output=Image.open(OUT/'skeleton-seedvr2-x4.png');baseline=Image.open(OUT/'skeleton-lanczos-x4.png').convert('RGBA')
    a=np.array(output);assert output.mode=='RGBA' and output.size==(268,164)
    assert np.array_equal(a[:,:,3],np.array(baseline)[:,:,3])
    rgb=a[a[:,:,3]>127,:3];assert rgb.std()>1 and rgb.max()>20
    events=dict(job['status']['messages']);elapsed=(events['execution_success']['timestamp']-events['execution_start']['timestamp'])/1000
    save('result.json',dict(status='completed_for_visual_review',prompt_id=pid,output_size=list(output.size),mode=output.mode,alpha_matches_baseline=True,elapsed_seconds=elapsed,output_sha256=h.sha(OUT/'skeleton-seedvr2-x4.png'),integration='not_installed'))
    native=Image.open(OUT/'skeleton-native.png').convert('RGBA').resize(output.size,Image.Resampling.NEAREST)
    preview=Image.new('RGB',(948,254),(34,38,38));d=ImageDraw.Draw(preview);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
    for i,(im,label) in enumerate(zip([native,baseline,output],['Оригинал ×4','Обычное увеличение','SeedVR2 3B INT8 ×4'])):
        d.text((i*316+14,14),label,font=font,fill=(226,224,211));preview.paste(im,(i*316+24,60),im)
    preview.save(OUT/'comparison.png')
    light=Image.new('RGB',(316,254),(235,235,225));d=ImageDraw.Draw(light);d.text((14,14),'SeedVR2 — светлый фон',font=font,fill=(40,40,40));light.paste(output,(24,60),output);light.save(OUT/'light-background.png')
    print((OUT/'result.json').read_text(),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','submit','collect']);a=p.parse_args();{'prepare':prepare,'submit':submit,'collect':collect}[a.action]()
