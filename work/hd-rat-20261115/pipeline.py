"""Qwen 2.1 / SeedVR2 rat production. Original archives are read-only."""
from pathlib import Path
import argparse, collections, hashlib, importlib.util, json, math, struct, sys, time, urllib.request, urllib.parse, uuid
from PIL import Image, ImageDraw
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'assets/generated/critter-rat/qwen21-seedvr2-v1-20261115'
sys.path.insert(0, str(ROOT/'tools/asset-pipeline'))
from fallout_assets import Assets, decode_frm, Frame, palette_rgb
from cave_reference import MapInspector
spec=importlib.util.spec_from_file_location('comfy_helpers',ROOT/'work/seedvr2-image-setup/20261113/knife-upscale.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
BASE='http://127.0.0.1:8188'
PREPARED_NAME='prepared-v2'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def node(kind,**kw):return dict(class_type=kind,inputs=kw)
def decode(raw,split):
    if not split:return decode_frm(raw)
    version,fps,action,count=struct.unpack_from('>IHHH',raw)
    assert version==4 and 0<count<128
    offsets=struct.unpack_from('>6I',raw,34);assert len(set(offsets))==1
    pos=62;frames=[]
    for f in range(count):
        w,hh,n,x,y=struct.unpack_from('>HHIhh',raw,pos);pos+=12
        assert 0<w<512 and 0<hh<512 and n==w*hh and pos+n<=len(raw)
        frames.append(Frame(w,hh,x,y,raw[pos:pos+n]));pos+=n
    assert pos==len(raw)
    return dict(version=version,fps=fps or 10,stored_fps=fps,action_frame=action,frame_count=count,
        direction_x=struct.unpack_from('>6h',raw,10),direction_y=struct.unpack_from('>6h',raw,22),
        direction_offsets=offsets,declared_data_size=struct.unpack_from('>I',raw,58)[0],actual_data_size=len(raw)-62,
        decoder='Single-direction FR0..FR5; sequential CE frame reader; original header retained'),{0:frames}

def rgba(f,pal):
    ix=np.frombuffer(f.pixels,dtype=np.uint8).reshape(f.height,f.width)
    rgb=np.frombuffer(pal,dtype=np.uint8).reshape(256,3)[ix]
    return Image.fromarray(np.dstack((rgb,np.where(ix>0,255,0).astype(np.uint8))))

def animation(code):
    if code=='na':return 64
    if code=='ch':return 36
    if code=='cj':return 37
    if code[0]=='a':return ord(code[1])-97
    if code[0]=='b':return 20+ord(code[1])-97
    if code[0]=='r':return 48+ord(code[1])-97
    raise ValueError(code)

def inventory():
    if (OUT/'inventory.json').exists():return
    a=Assets([ROOT/'FALLOUT (extract.me)/MASTER.DAT',ROOT/'FALLOUT (extract.me)/CRITTER.DAT'])
    pal=palette_rgb(a.read('color.pal'));inspector=MapInspector(a);m=inspector.parse('maps/v13ent.map')
    rats=[o for o in m['objects'] if o['pid']==0x01000030]
    assert len(rats)==20 and all(o['fid']==0x01000018 for o in rats)
    names=sorted(n for n in a.index if n.startswith('art/critters/masrat'))
    records=[];sources=[];unique={}
    for name in names:
        raw=a.read(name);split=name[-1].isdigit();meta,dirs=decode(raw,split)
        p=OUT/'source/raw'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        code=Path(name).stem[-2:];anim=animation(code)
        sources.append(dict(resource=name,sha256=sha(p),code=code,animation=anim,metadata=meta))
        for direction,fs in dirs.items():
            direction=int(name[-1]) if split else direction
            for fi,f in enumerate(fs):
                digest=hashlib.sha256(struct.pack('<II',f.width,f.height)+f.pixels).hexdigest()
                key=unique.setdefault(digest,f'u{len(unique):04}')
                png=OUT/'source/frames'/f'{key}.png'
                if not png.exists():png.parent.mkdir(parents=True,exist_ok=True);rgba(f,pal).save(png)
                records.append(dict(resource=name,source_sha256=hashlib.sha256(raw).hexdigest(),code=code,animation=anim,
                    direction=direction,frame=fi,unique=key,width=f.width,height=f.height,
                    frame_shift=[f.shift_x,f.shift_y],direction_offset=[meta['direction_x'][direction],meta['direction_y'][direction]],
                    fps=meta['fps'],action_frame=meta['action_frame'],palette_cycle_pixels=sum(1 for x in f.pixels if x>=229)))
    save(OUT/'inventory.json',dict(component='Ordinary cave rat masrat, art index 24, PID 0x01000030',
        map_rats=rats,source_files=sources,frames=records,total_directional_frames=len(records),unique_frames=len(unique),
        original_archives_modified=False))
    save(OUT/'baseline.json',{str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'AGENTS.md',ROOT/'HD-TEXTURE-GUIDE.md',ROOT/'runtime/hd-world-pilot/fallout-ce.exe']})
    overview=Image.new('RGB',(1200,len(sources)*100//6+200),(27,30,28));dr=ImageDraw.Draw(overview)
    groups=collections.defaultdict(list)
    for r in records:
        if r['frame']==0:groups[r['code']].append(r)
    overview=Image.new('RGB',(1400,len(groups)*105),(27,30,28));dr=ImageDraw.Draw(overview)
    for row,(code,rs) in enumerate(groups.items()):
        dr.text((8,row*105+8),f'{code} / animation {rs[0]["animation"]}',fill='white')
        for col,r in enumerate(rs[:6]):
            im=Image.open(OUT/'source/frames'/f'{r["unique"]}.png').convert('RGBA')
            im.thumbnail((180,84));im=im.resize((im.width*min(4,180//im.width),im.height*min(4,180//im.width)),Image.Resampling.NEAREST)
            overview.paste(im,(170+col*200,row*105+16),im)
    overview.save(OUT/'source-overview.png')
    print(json.dumps(dict(source_files=len(sources),directional_frames=len(records),unique_frames=len(unique),codes=list(groups)),ensure_ascii=False),flush=True)

def upload(path):
    boundary='fallout-rat-'+uuid.uuid4().hex
    body=b''
    for k,v in {'type':'input','subfolder':'fallout1_rat_20261115','overwrite':'false'}.items():
        body+=f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    body+=f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{path.stem}-{uuid.uuid4().hex}.png"\r\nContent-Type: image/png\r\n\r\n'.encode()+path.read_bytes()+f'\r\n--{boundary}--\r\n'.encode()
    req=urllib.request.Request(BASE+'/upload/image',body,{'Content-Type':'multipart/form-data; boundary='+boundary})
    with urllib.request.urlopen(req,timeout=40) as response:r=json.load(response)
    return r['subfolder']+'/'+r['name']

def execute(d,g,outputs):
    d.mkdir(parents=True,exist_ok=True)
    if (d/'result.json').exists():return read(d/'result.json')
    if not (d/'run.json').exists():
        wf=h.workflow(g,h.req('/object_info'));wf['extra']['notes']='Isolated ordinary-rat remaster; source FRM geometry retained.'
        save(d/'prompt-api.json',g);save(d/'workflow.json',wf);save(d/'outputs.json',outputs)
        wait_started=time.monotonic();last_notice=-60
        while True:
            q=h.req('/queue')
            if not q['queue_running'] and not q['queue_pending']:break
            if time.monotonic()-wait_started-last_notice>=60:
                print('Shared GPU busy; waiting.',flush=True);last_notice=time.monotonic()-wait_started
            time.sleep(2)
        client='fallout-rat-'+uuid.uuid4().hex
        save(d/'submission.json',dict(client_id=client,started_utc=time.time()))
        try:r=h.req('/prompt',dict(prompt=g,client_id=client,extra_data={'extra_pnginfo':{'workflow':wf}}))
        except urllib.error.HTTPError as e:(d/'error.json').write_bytes(e.read());raise
        save(d/'run.json',r)
        if r.get('node_errors'):raise RuntimeError(r)
        print('SUBMITTED',d.name,r['prompt_id'],flush=True)
    pid=read(d/'run.json')['prompt_id'];outputs=read(d/'outputs.json');start=time.monotonic()
    while True:
        job=h.req('/history/'+pid).get(pid)
        if job:break
        if time.monotonic()-start>5400:raise TimeoutError('Resume this prompt ID; do not resubmit.')
        time.sleep(5)
    save(d/'history.json',job)
    if job['status']['status_str']!='success':raise RuntimeError(job['status'])
    files=[]
    for nid,name in outputs.items():
        item=job['outputs'][nid]['images'][0]
        with urllib.request.urlopen(BASE+'/view?'+urllib.parse.urlencode(item),timeout=90) as response:data=response.read()
        p=d/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        im=Image.open(p);files.append(dict(file=name,sha256=sha(p),size=im.size,mode=im.mode))
    ev=dict(job['status']['messages']);secs=(ev['execution_success']['timestamp']-ev['execution_start']['timestamp'])/1000
    result=dict(status='generated, not installed',prompt_id=pid,elapsed_seconds=secs,files=files);save(d/'result.json',result)
    print('DONE',d.name,round(secs,1),'seconds',flush=True);return result

def panels():
    inv=read(OUT/'inventory.json');representatives={}
    for r in inv['frames']:representatives.setdefault(r['unique'],r)
    # Keep complete consecutive cycles together, with identical spacing in every sheet.
    groups=collections.defaultdict(list)
    for r in representatives.values():groups[r['code']].append(r)
    plans=[]
    for code,all_rs in groups.items():
        scale=4 if code=='na' or max(r['width'] for r in all_rs)>80 else 6
        cw=math.ceil((max(r['width'] for r in all_rs)*scale+32)/32)*32
        ch=math.ceil((max(r['height'] for r in all_rs)*scale+32)/32)*32
        cols=min(len(all_rs),max(1,1024//cw));capacity=cols*max(1,896//ch)
        for page,start in enumerate(range(0,len(all_rs),capacity)):
            rs=all_rs[start:start+capacity];rows=math.ceil(len(rs)/cols);w,hh=cols*cw,rows*ch
            slots=[];canvas=Image.new('RGBA',(w,hh))
            for i,r in enumerate(rs):
                x=(i%cols)*cw+(cw-r['width']*scale)//2;y=(i//cols)*ch+(ch-r['height']*scale)//2
                src=Image.open(OUT/'source/frames'/f'{r["unique"]}.png').convert('RGBA').resize((r['width']*scale,r['height']*scale),Image.Resampling.NEAREST)
                canvas.paste(src,(x,y));slots.append(dict(**r,x=x,y=y,scale=scale))
            name=f'{code}-p{page:02}';dest=OUT/'panels'/name;dest.mkdir(parents=True,exist_ok=True);canvas.save(dest/'original-x6.png')
            plans.append(dict(id=name,code=code,size=[w,hh],slots=slots))
    save(OUT/'panels.json',plans);print('Panels',len(plans),flush=True)

def seed(p):
    d=OUT/'seed'/p['id']
    if (d/'run.json').exists():return execute(d,{}, {})
    g=read(ROOT/'assets/generated/inventory-knife/seedvr2-x4-20261113/prompt-api.json')
    g['1']['inputs']['image']=upload(OUT/'panels'/p['id']/'original-x6.png');g['3']['inputs']['scale_by']=1.0
    prefix='fallout1_rat/'+uuid.uuid4().hex
    g['9']['inputs']['seed']=15112026
    g['12']['inputs']['filename_prefix']=prefix+'/seedvr2';g['13']['inputs']['filename_prefix']=prefix+'/reference'
    return execute(d,g,{'12':'seed.png','13':'reference.png'})

def qwen(p):
    d=OUT/'qwen'/p['id']
    if (d/'run.json').exists():return execute(d,{}, {})
    prompt=(f'Restore this exact sprite animation sheet of ONE ordinary Fallout cave rat, {len(p["slots"])} separate consecutive poses. '
      'Keep every pose in its exact position, with the exact same silhouette, dimensions, tail curve, paws, head angle and orthographic isometric camera. '
      'It is the SAME animal in EVERY cell. Redraw the pixelated interior as detailed high resolution prerendered 3D game art: '
      'matted coarse dusty brown-grey fur, sparse fine hairs, small pink-brown ears, dark eyes, thin scaly muted pink-brown tail, little claws. '
      'Maintain original subdued brown colour, soft upper-left lighting and dark underside. Keep the original anatomy, hunched back and low stance. '
      'Remove pixel blocks and dithering, add clean fur shading and restrained natural detail. No glossy plastic, outlines, extra legs, enlarged ears, extra rats, scenery, text, tile borders or ground plane. '
      'Keep transparent empty space, do not merge, move, duplicate or omit any pose. Preserve identical coat colour and lighting across the entire animation. ')
    if p['code'][0] in 'br':prompt+='This is an original injury/death pose sequence. Preserve the exact original wounds, blood, remains, flames or burned areas where present; do not restore dead poses to a living standing rat. '
    effects={
      'bd':'GIBS AND BLOOD ONLY: the rat has violently disintegrated into scattered small flesh fragments, muted red blood splashes and grey-brown fur scraps. Restore the exact fragments and their exact positions in EVERY cell. No intact rat bodies, no standing animals, no added flesh or new objects. Preserve small isolated droplets and the progressive falling motion of all original particles.',
      'be':'An original burning and charring death animation of one rat. Preserve the exact changing pose, exposed ribs, upright burned torso, flames and final charcoal remains of each frame. Charred black-brown skin and pale bones where the original shows them, restrained orange flame highlights only where originally present. Do not restore a healthy animal or add fur over original skeleton areas.',
      'bh':'An original electrical death animation: a prone dark rat turns into charred remains. Preserve each exact silhouette and original bright electrical flash and pale exposed details. Dark burned fur and charcoal body, no healthy standing rats, no added lightning outside the original silhouette.',
      'bk':'An original electrical disintegration death animation, progressively reducing a dark burned rat to small charcoal fragments. Restore the exact remnants and their positions in each cell; preserve every disappearing body part and original pale flash. No intact healthy rats, no additional particles or flames.',
      'rd':'Only the final scattered remains and muted red blood splashes of the original disintegrated rat. Keep all small flesh and fur fragments at exactly their current positions. No intact rat, no restored living animal.'}
    if p['code'] in effects:prompt=(f'Restore this exact original Fallout animation sprite sheet, {len(p["slots"])} separate fixed-position frames. '+effects[p['code']]+' Detailed clean high-resolution prerendered 3D game art, subdued original colour and upper-left light. Preserve exact silhouettes, frame layout, original motion, all transparent space and all original content. Remove blocky pixels and dithering without changing anatomy or particle geometry. No text, outlines, ground plane or scenery.')
    if p['code']=='na':prompt=('Restore this exact original Fallout aimed-attack targeting diagram. It is a technical monochrome GREEN WIREFRAME MESH of a cave rat on a pure black computer display. '
        'Preserve the exact pose, projection, head, feet, tail, body silhouette and position. Redraw its curved three-dimensional wire mesh with crisp thin green topology lines and smooth continuous contours. '
        'The surface must remain an open green wireframe grid with black gaps between wires, not filled skin, fur, shaded solid tissue or a green photograph. '
        'Keep every straight horizontal and vertical green targeting callout line exactly where it is, with the same endpoints and right-angle bends. '
        'No extra lines, text, labels, glow, brown colour, scenery, anatomical changes or new objects. Retain the original sparse 1997 Fallout targeting-screen appearance, with clean high-resolution line work.')
    prefix='fallout1_rat/'+uuid.uuid4().hex
    g={'1':node('LoadImage',image=upload(OUT/'seed'/p['id']/'seed.png')),
       '2':node('JoinImageWithAlpha',image=['1',0],alpha=['1',1]),
       '4':node('UNETLoader',unet_name='qwen_image_2.1_int8_convrot.safetensors',weight_dtype='default'),
       '5':node('CLIPLoader',clip_name='qwen3vl_8b_int8_convrot.safetensors',type='qwen_image',device='default'),
       '6':node('VAELoader',vae_name='qwen_image_2.1_vae_bf16.safetensors'),
       '7':node('QwenImage21Cache',model=['4',0],device='cpu',dtype='default'),
       '8':node('TextEncodeQwenImage21',clip=['5',0],prompt=prompt,negative_prompt='',vae=['6',0],resolution=0,**{'images.image_1':['2',0]}),
       '9':node('KSampler',model=['7',0],positive=['8',0],negative=['8',1],latent_image=['8',2],seed=15112026,steps=25,cfg=1.0,sampler_name='euler',scheduler='simple',denoise=1.0),
       '10':node('VAEDecode',samples=['9',0],vae=['6',0]),
       '11':node('SaveImage',images=['10',0],filename_prefix=prefix+'/qwen')}
    d.mkdir(parents=True,exist_ok=True);(d/'prompt.txt').write_text(prompt,encoding='utf-8')
    return execute(d,g,{'11':'qwen.png'})

def prepare(p):
    d=OUT/PREPARED_NAME/p['id']
    if (d/'run.json').exists():return execute(d,{}, {})
    g={};outputs={};prefix='fallout1_rat/prepared/'+uuid.uuid4().hex
    def add(kind,**kw):
        key=str(len(g)+1);g[key]=node(kind,**kw);return [key,0]
    def load(path):return add('LoadImage',image=upload(path))
    def resize(im,w,hh,method='lanczos'):return add('ImageScale',image=im,upscale_method=method,width=w,height=hh,crop='disabled')
    seedim=load(OUT/'seed'/p['id']/'seed.png');generated=load(OUT/'qwen'/p['id']/'qwen.png')
    original=load(OUT/'panels'/p['id']/'original-x6.png')
    original_empty=add('MaskToImage',mask=[original[0],1])
    interior=add('GrowMask',mask=add('InvertMask',mask=[original[0],1]),expand=-p['slots'][0]['scale'],tapered_corners=True)
    if p['code']=='na':
        protection=load(OUT/'source/aimed-body-mask-panel.png')
        interior=add('ImageToMask',image=protection,channel='red')
    confidence=add('MaskComposite',destination=interior,source=add('InvertMask',mask=[generated[0],1]),x=0,y=0,operation='multiply')
    fringe=add('ImageBlend',image1=original,image2=seedim,blend_factor=0.3,blend_mode='normal')
    if p['code']=='na':fringe=original
    mixed=add('ImageCompositeMasked',destination=fringe,source=generated,x=0,y=0,resize_source=False,mask=confidence)
    for r in p['slots']:
        w,hh=r['width']*4,r['height']*4
        crop=dict(x=r['x'],y=r['y'],width=r['width']*r['scale'],height=r['height']*r['scale'])
        rgb=resize(add('ImageCrop',image=mixed,**crop),w,hh)
        exact_alpha=resize(add('ImageCrop',image=original_empty,**crop),w,hh,'nearest-exact')
        exact_alpha=add('ImageToMask',image=exact_alpha,channel='red')
        joined=add('JoinImageWithAlpha',image=rgb,alpha=exact_alpha)
        out=add('SaveImage',images=joined,filename_prefix=prefix+'/'+r['unique']);outputs[out[0]]=r['unique']+'.png'
    return execute(d,g,outputs)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['inventory','panels','seed','qwen','prepare']);ap.add_argument('--only');args=ap.parse_args()
    if args.stage=='inventory':inventory()
    elif args.stage=='panels':panels()
    else:
        ps=read(OUT/'panels.json')
        if args.only:ps=[p for p in ps if p['id'] in args.only.split(',')]
        for p in ps:
            existed=(OUT/('qwen' if args.stage=='qwen' else 'seed' if args.stage=='seed' else PREPARED_NAME)/p['id']/'result.json').exists()
            dict(seed=seed,qwen=qwen,prepare=prepare)[args.stage](p)
            if args.stage=='qwen' and not existed:time.sleep(3)
