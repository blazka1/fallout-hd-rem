"""Local Qwen follow-up: clean the latest knife's silhouette and repair its tip."""
from pathlib import Path
import argparse, importlib.util, json, time, uuid, urllib.request, urllib.parse
from PIL import Image, ImageDraw, ImageFont
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
PREVIOUS=ROOT/'assets/generated/inventory-knife/qwen21-blend-rust-v2-20261113'
OUT=ROOT/'assets/generated/inventory-knife/qwen21-clean-edges-v3-20261113'
spec=importlib.util.spec_from_file_location('knife_helpers',Path(__file__).with_name('knife-upscale.py'))
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
PROMPT='''Edit this exact knife in <image1>. Make only the following focused repairs while retaining the established design, materials and rust.
1. Repair the blade tip at the far LEFT. Remove the dark transverse fracture or joint line that separates the small pointed end from the rest of the blade. Remove the kink or break in the upper blade contour beside that line. Reconstruct this area as ONE solid, continuous piece of grey steel, with a smooth continuous transition from the pointed end into the blade. The pointed end must not look snapped, bent, welded, segmented or attached separately. Continue the existing fine steel grain and shading naturally through the repaired area, with no visible seam. Keep the blade's broad curved profile and its current length; do not cut off or blunt the tip.
2. Clean the external edges around the entire knife: make the blade spine and cutting edge, guard, grip and pommel outlines smooth, coherent and sharply defined with clean anti-aliased transparency. Remove accidental jagged steps, pixel staircases, ragged torn-looking notches and tiny random bites along the silhouette. Preserve intentional large grip contours and the recognizable overall shape. This is contour cleanup, not a redesign or a blur filter. Keep the small material details inside the silhouette sharp.
Preserve the short irregular dark brown grip with its TWO existing metal fasteners, the rounded rusty guard and the flared metal pommel. Preserve the shallow longitudinal groove in the central blade; only the unwanted short fracture near the far-left pointed end is removed. Keep the existing restrained reddish-brown rust patches and fine scratches on the mostly muted grey steel. Maintain the current dull metal roughness, brown grip, lighting direction, orthographic inventory perspective, proportions, placement and transparent margins. Do not increase corrosion or add new chips, cracks, nicks, seams, serrations, decorations or lettering.
Output only this repaired single Fallout 1 inventory knife on a genuinely transparent background. No hands, extra objects, labels, collage, ground plane, cast shadow, glow or white outline.'''
SEED_VALUE=13112026
REFINED_PROMPT='''Make a precise, restrained contour repair to this same knife. Keep the soft matte grey steel, subdued brown grip, fine texture and existing small rust patches exactly as they appear in the reference; do not enhance contrast, sharpening, gloss, saturation, grain or corrosion.
Repair the leftmost pointed end of the blade. The dark near-vertical diagonal line crossing the blade close to its far-left tip is an unwanted fracture: completely remove that line, its shadow, and the small dip/kink where it meets the upper edge. Reconstruct uninterrupted metal and a single smooth flowing upper contour into the tip, with no dent, seam, joint or separate tip segment. The blade remains one solid piece with a smooth curved cutting edge.
Clean up only accidental tiny ragged notches and stair-step bumps on the outside silhouette of the blade, guard, brown grip and pommel. Fill those tiny torn-looking bites and use smooth, naturally anti-aliased curves. Keep the grip's large intentional contour and two fasteners, the rounded guard, flared pommel, blade length and width, central longitudinal groove, original angle and framing. Do not copy the unwanted fracture or jagged pixel contour from the reference.
Retain natural muted shading and soft, narrow edge highlights. No bright white rim, metallic glitter, oversharpened outlines, coarse speckles, extra rust, new chips or scratches. No changes to the knife design. Output this single repaired matte Fallout inventory knife with truly transparent surroundings, in the same position and size. No additional objects, labels, background or cast shadow.'''

def save(name,value):
    (OUT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def submit():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'run.json').exists():raise RuntimeError('Already submitted; use collect.')
    h.idle()
    source=PREVIOUS/'knife-blend-rust-raw.png'
    assert Image.open(source).size==(1152,576) and Image.open(source).mode=='RGBA'
    (OUT/'reference-latest-knife.png').write_bytes(source.read_bytes())
    (OUT/'source.json').write_bytes((PREVIOUS/'source.json').read_bytes())
    uploaded=h.upload(OUT/'reference-latest-knife.png')
    graph=json.loads((PREVIOUS/'prompt-api.json').read_text())
    for node in ['16','17','18','19']:graph.pop(node,None)
    graph['8']['inputs'].pop('images.image_2',None);graph['8']['inputs'].pop('images.image_3',None)
    graph['1']['inputs']['image']=uploaded;graph['8']['inputs']['prompt']=PROMPT
    graph['9']['inputs']['seed']=SEED_VALUE
    token=uuid.uuid4().hex;cid='qwen21-knife-clean-'+token;prefix='fallout1_qwen21_knife_clean/'+token
    for node,name in [('11','knife-clean-raw'),('12','reference-working'),('15','knife-clean-x4')]:graph[node]['inputs']['filename_prefix']=prefix+'/'+name
    schemas=h.req('/object_info')
    for node,field in [('4','unet_name'),('5','clip_name'),('6','vae_name')]:
        assert graph[node]['inputs'][field] in schemas[graph[node]['class_type']]['input']['required'][field][0]
    wf=h.workflow(graph,schemas);save('workflow.json',wf);save('prompt-api.json',graph)
    (OUT/'prompt.txt').write_text(PROMPT+'\n',encoding='utf-8')
    save('plan.json',dict(component='Knife contour cleanup and tip repair',client_id=cid,reference=str(source),reference_sha256=h.sha(source),working_size=[1152,576],target_size=[352,132],crop_xywh=[32,78,1088,408],seed=SEED_VALUE,steps=25,cfg=1,sampler='euler',scheduler='simple',denoise=1,cache='cpu/default',alpha='Native Qwen RGBA; no old silhouette mask imposed'))
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
        history=h.req('/history/'+pid)
        if pid in history:break
        if time.monotonic()-start>3600:raise TimeoutError('Resume collect; do not resubmit.')
        print('Waiting for contour repair '+pid,flush=True);time.sleep(15)
    job=history[pid];save('history.json',job)
    if job['status']['status_str']!='success':raise RuntimeError(job['status'])
    for node,name in [('11','knife-clean-raw.png'),('12','reference-working.png'),('15','knife-clean-x4.png')]:
        record=job['outputs'][node]['images'][0]
        with urllib.request.urlopen(h.BASE+'/view?'+urllib.parse.urlencode(record),timeout=30) as response:(OUT/name).write_bytes(response.read())
    raw=Image.open(OUT/'knife-clean-raw.png');result=Image.open(OUT/'knife-clean-x4.png')
    assert raw.mode=='RGBA' and raw.size==(1152,576) and result.mode=='RGBA' and result.size==(352,132)
    a=np.array(result)[:,:,3];assert a.min()==0 and a.max()>200
    mask=np.array(raw)[:,:,3]>=128;outside=mask.copy();outside[78:486,32:1120]=False
    assert not outside.any(),'Opaque pixels outside fixed crop; reframe before delivery.'
    events=dict(job['status']['messages']);elapsed=(events['execution_success']['timestamp']-events['execution_start']['timestamp'])/1000
    save('result.json',dict(status='candidate_for_visual_review',prompt_id=pid,output_size=list(result.size),mode=result.mode,elapsed_seconds=elapsed,opaque_pixels_outside_crop=int(outside.sum()),output_sha256=h.sha(OUT/'knife-clean-x4.png'),raw_sha256=h.sha(OUT/'knife-clean-raw.png'),integration='not_installed'))
    old=Image.open(PREVIOUS/'knife-blend-rust-x4.png').convert('RGBA')
    preview=Image.new('RGB',(800,222),(34,38,38));d=ImageDraw.Draw(preview);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
    for i,(im,label) in enumerate(zip([old,result],['До — надлом и неровные края','После — обработка Qwen'])):
        d.text((i*400+14,14),label,font=font,fill=(226,224,211));preview.paste(im,(i*400+24,60),im)
    preview.save(OUT/'comparison.png')
    light=Image.new('RGB',(400,180),(235,235,225));light.paste(result,(24,24),result);light.save(OUT/'light-background.png')
    large=Image.new('RGB',raw.size,(34,38,38));large.paste(raw,(0,0),raw);large.save(OUT/'large-preview.png')
    # Same camera-space crop in both full-resolution frames, without zoom.
    detail=Image.new('RGB',(720,320),(34,38,38));d=ImageDraw.Draw(detail)
    for i,im in enumerate([Image.open(PREVIOUS/'knife-blend-rust-raw.png').convert('RGBA'),raw]):
        crop=im.crop((32,240,368,504));detail.paste(crop,(i*360+12,44),crop);d.text((i*360+12,12),['Кончик до','Кончик после'][i],font=font,fill=(226,224,211))
    detail.save(OUT/'tip-detail.png')
    print((OUT/'result.json').read_text(),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['submit','collect']);p.add_argument('--refined-matte',action='store_true');a=p.parse_args()
    if a.refined_matte:
        OUT=ROOT/'assets/generated/inventory-knife/qwen21-clean-edges-v4-20261113';PROMPT=REFINED_PROMPT;SEED_VALUE=13112027
    {'submit':submit,'collect':collect}[a.action]()
