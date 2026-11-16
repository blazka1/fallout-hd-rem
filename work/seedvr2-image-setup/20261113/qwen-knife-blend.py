"""Combine SeedVR2 knife geometry and Qwen material detail using local Qwen 2.1."""
from pathlib import Path
import argparse, importlib.util, json, time, uuid, urllib.request, urllib.parse
from PIL import Image, ImageDraw, ImageFont
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'assets/generated/inventory-knife/qwen21-blend-rust-v1-20261113'
SEED=ROOT/'assets/generated/inventory-knife/seedvr2-x4-20261113'
QWEN=ROOT/'assets/generated/inventory-knife/qwen21-x4-20261113'
spec=importlib.util.spec_from_file_location('knife_helpers',Path(__file__).with_name('knife-upscale.py'))
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
PROMPT='''Edit <image1> into ONE refined Fallout 1 inventory knife, combining the two references with these distinct priorities.
SHAPE: <image1> is the authoritative reference for the handle, guard, pommel, overall proportions, angle, placement and silhouette. Keep its short, irregular dark brown grip, existing small metal fasteners in their original positions, rounded weathered guard, and flared metal pommel. Preserve the authentic old knife character of <image1>. Do not copy the long smooth grip or the tall rectangular guard from <image2>. The broad blade still points to the left and slightly down; keep its length, width, tip and original shallow groove and small imperfections from <image1>.
MATERIAL AND DETAIL: use <image2> only for the quality of the readable fine metal and grip textures, crisp bevel shading, subtle machining and sharpening marks, realistic roughness and clean prerendered rendering. Bring these fine textures onto the shape of <image1>. Aim for a balanced restoration between these two results: clear detailed materials, but still the battered original Fallout knife, not a polished new redesign.
RUST: add visible but restrained irregular dark reddish-brown oxidation, fine pitting and small burnt-orange rust freckles, especially near the base of the blade, in the existing groove, around the guard and at metal fasteners. A few scattered rust patches extend onto the blade face. Keep most of the blade muted grey steel and keep the sharpened cutting edge readable and relatively clean. No thick orange crust, no uniform rust overlay. The grip remains worn dark brown material with subtle grain and wear; metal oxidation stays on the metal parts.
Preserve the first reference's lighting direction, orthographic inventory view, framing and transparent margins. Output a single knife on genuinely transparent background, with transparent empty space around it. No extra weapons, added fittings, new markings, lettering, logos, blood, hands, scenery, ground plane, cast shadow, collage or labels.'''
TEXTURE_REFS=False
TEXTURE_PROMPT='''Restore the knife in <image1>, using <image2> and <image3> only as small surface-texture samples.
The ONLY reference for the entire knife and its geometry is <image1>. Preserve its silhouette, blade profile, tip, short dark brown handle, existing metal grip fasteners, rounded small guard and irregular flared pommel. Preserve the placement, size, viewpoint and orientation of every part. Keep the existing fasteners clearly visible and in their exact locations. Do not replace the grip with a smooth unpinned handle. Do not straighten or enlarge the guard. Do not turn this into a different knife.
<image2> is a close crop of steel surface only. Transfer its restrained fine texture, subtle scratches and readable grey steel shading onto the existing blade of <image1>, retaining the shallow groove, small nicks and worn edges. <image3> is a close crop of brown grip material only. Transfer its material detail onto the small original grip in <image1>, without changing the shape or hiding the metal fasteners. The small texture samples are NOT additional objects and do not determine the object's design.
Add moderate visible reddish-brown rust, uneven dark oxidized spots and tiny burnt-orange freckles on the steel near the guard and blade base, in the existing groove, at the existing metal fasteners, and in a few small scattered patches on the blade. Most of the blade must remain muted grey steel; keep its cutting edge readable. Fine corrosion, not coarse glitter, white speckles, chalky crust or a uniform orange coating. The blade surface is matte weathered steel with selective highlights, not glossy foil. The worn brown grip remains recognizably the same grip.
Match the muted Fallout 1 prerendered 2D inventory style, original light direction and transparent framing of <image1>. Output only the one edited knife. Keep empty space genuinely transparent. No collage, texture panels, labels, text, new ornaments, added parts, hands, ground plane, cast shadow or scenery.'''

def save(name,value):
    (OUT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def submit():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'run.json').exists():raise RuntimeError('Already submitted. Use collect.')
    h.idle()
    # Seed sprite is 4x the native frame; add the same proportional padding
    # as in the preceding Qwen experiment before scaling to the work canvas.
    seed=Image.open(SEED/'knife-seedvr2-x4.png').convert('RGBA');assert seed.size==(352,132)
    canvas=Image.new('RGBA',(384,192),(0,0,0,0));canvas.paste(seed,(16,28));canvas.save(OUT/'reference1-seed-shape.png')
    if TEXTURE_REFS:
        material=Image.open(QWEN/'knife-qwen21-raw.png').convert('RGBA')
        for name,box in [('reference2-qwen-material.png',(400,300,592,348)),('reference3-qwen-grip.png',(864,180,992,212))]:
            patch=material.crop(box);assert np.array(patch)[:,:,3].min()>200
            patch=patch.resize((patch.width*2,patch.height*2),Image.Resampling.LANCZOS);patch.save(OUT/name)
    else:
        (OUT/'reference2-qwen-material.png').write_bytes((QWEN/'knife-qwen21-raw.png').read_bytes())
    (OUT/'source.json').write_bytes((SEED/'source.json').read_bytes())
    refs=[h.upload(OUT/'reference1-seed-shape.png'),h.upload(OUT/'reference2-qwen-material.png')]
    schemas=h.req('/object_info')
    graph=json.loads((QWEN/'prompt-api.json').read_text())
    token=uuid.uuid4().hex;prefix='fallout1_qwen21_knife_blend/'+token;cid='qwen21-knife-blend-'+token
    graph['1']['inputs']['image']=refs[0]
    graph['8']['inputs']['prompt']=PROMPT
    graph['8']['inputs']['images.image_2']=['17',0]
    graph['13']['inputs'].update(x=32,y=78,width=1088,height=408)
    graph['11']['inputs']['filename_prefix']=prefix+'/knife-blend-rust-raw'
    graph['12']['inputs']['filename_prefix']=prefix+'/reference1-working'
    graph['15']['inputs']['filename_prefix']=prefix+'/knife-blend-rust-x4'
    graph['16']={'class_type':'LoadImage','inputs':{'image':refs[1]}}
    graph['17']={'class_type':'JoinImageWithAlpha','inputs':{'image':['16',0],'alpha':['16',1]}}
    if TEXTURE_REFS:
        grip=h.upload(OUT/'reference3-qwen-grip.png')
        graph['18']={'class_type':'LoadImage','inputs':{'image':grip}}
        graph['19']={'class_type':'JoinImageWithAlpha','inputs':{'image':['18',0],'alpha':['18',1]}}
        graph['8']['inputs']['images.image_3']=['19',0]
    for node,field in [('4','unet_name'),('5','clip_name'),('6','vae_name')]:
        assert graph[node]['inputs'][field] in schemas[graph[node]['class_type']]['input']['required'][field][0]
    wf=h.workflow(graph,schemas)
    save('prompt-api.json',graph);save('workflow.json',wf);(OUT/'prompt.txt').write_text(PROMPT+'\n',encoding='utf-8')
    save('plan.json',dict(component='Knife blend with rust',client_id=cid,working_size=[1152,576],target_size=[352,132],final_crop_xywh=[32,78,1088,408],seed=13112026,steps=25,cfg=1,sampler='euler',scheduler='simple',denoise=1,cache_device='cpu',resolution=0,references=[{'role':'shape, handle, guard, placement','path':str(SEED/'knife-seedvr2-x4.png'),'sha256':h.sha(SEED/'knife-seedvr2-x4.png')},{'role':'material and surface detail only','path':str(QWEN/'knife-qwen21-raw.png'),'sha256':h.sha(QWEN/'knife-qwen21-raw.png')}],alpha='Native Qwen-generated RGBA, no forced source mask'))
    if TEXTURE_REFS:
        plan=json.loads((OUT/'plan.json').read_text())
        plan['reference_strategy']='SeedVR2 is the only whole-object reference; Qwen supplies interior texture crops only.'
        plan['references']=plan['references'][:1]+[
            {'role':role,'parent_path':str(QWEN/'knife-qwen21-raw.png'),'parent_sha256':h.sha(QWEN/'knife-qwen21-raw.png'),'crop_box':box,'scale':2,'prepared_file':name,'sha256':h.sha(OUT/name)}
            for role,name,box in [('steel surface only','reference2-qwen-material.png',[400,300,592,348]),('brown grip surface only','reference3-qwen-grip.png',[864,180,992,212])]]
        save('plan.json',plan)
    h.idle()
    try:run=h.req('/prompt',dict(prompt=graph,client_id=cid,extra_data={'extra_pnginfo':{'workflow':wf}}))
    except urllib.error.HTTPError as e:
        details=e.read().decode();(OUT/'validation-error.json').write_text(details,encoding='utf-8');raise RuntimeError(details) from e
    run['client_id']=cid;save('run.json',run)
    if run.get('node_errors'):raise RuntimeError(run)
    print(json.dumps(run),flush=True)

def collect():
    pid=json.loads((OUT/'run.json').read_text())['prompt_id'];start=time.monotonic()
    while True:
        hist=h.req('/history/'+pid)
        if pid in hist:break
        if time.monotonic()-start>3600:raise TimeoutError('Resume collect; do not resubmit.')
        print('Waiting for Qwen blend '+pid,flush=True);time.sleep(15)
    job=hist[pid];save('history.json',job)
    if job['status']['status_str']!='success':raise RuntimeError(job['status'])
    for node,name in [('11','knife-blend-rust-raw.png'),('12','reference1-working.png'),('15','knife-blend-rust-x4.png')]:
        record=job['outputs'][node]['images'][0]
        with urllib.request.urlopen(h.BASE+'/view?'+urllib.parse.urlencode(record),timeout=30) as r:(OUT/name).write_bytes(r.read())
    raw=Image.open(OUT/'knife-blend-rust-raw.png');result=Image.open(OUT/'knife-blend-rust-x4.png')
    assert raw.mode=='RGBA' and raw.size==(1152,576) and result.mode=='RGBA' and result.size==(352,132)
    a=np.array(result)[:,:,3];assert a.min()==0 and a.max()>200
    mask=np.array(raw)[:,:,3]>=128;outside=mask.copy();outside[78:486,32:1120]=False
    events=dict(job['status']['messages']);elapsed=(events['execution_success']['timestamp']-events['execution_start']['timestamp'])/1000
    save('result.json',dict(status='candidate_for_visual_review',prompt_id=pid,output_size=list(result.size),mode=result.mode,elapsed_seconds=elapsed,opaque_pixels_outside_crop=int(outside.sum()),output_sha256=h.sha(OUT/'knife-blend-rust-x4.png'),raw_sha256=h.sha(OUT/'knife-blend-rust-raw.png'),integration='not_installed'))
    preview=Image.new('RGB',(1200,222),(34,38,38));d=ImageDraw.Draw(preview);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
    pictures=[Image.open(SEED/'knife-seedvr2-x4.png').convert('RGBA'),Image.open(QWEN/'knife-qwen21-x4.png').convert('RGBA'),result]
    for i,(im,label) in enumerate(zip(pictures,['SeedVR2 — форма','Qwen — материалы','Qwen — смесь + ржавчина'])):
        d.text((i*400+14,14),label,font=font,fill=(226,224,211));preview.paste(im,(i*400+24,60),im)
    preview.save(OUT/'comparison.png')
    light=Image.new('RGB',(400,180),(235,235,225));light.paste(result,(24,24),result);light.save(OUT/'light-background.png')
    large=Image.new('RGB',raw.size,(34,38,38));large.paste(raw,(0,0),raw);large.save(OUT/'large-preview.png')
    print((OUT/'result.json').read_text(),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['submit','collect']);p.add_argument('--texture-refs',action='store_true');a=p.parse_args()
    if a.texture_refs:
        TEXTURE_REFS=True;PROMPT=TEXTURE_PROMPT;OUT=ROOT/'assets/generated/inventory-knife/qwen21-blend-rust-v2-20261113'
    {'submit':submit,'collect':collect}[a.action]()
