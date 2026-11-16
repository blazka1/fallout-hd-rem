"""Isolated, resumable SeedVR2 -> Qwen 2.1 candidate production. No runtime writes."""
from pathlib import Path
import argparse, copy, hashlib, importlib.util, json, math, struct, sys, time, urllib.request, urllib.parse, uuid
sys.dont_write_bytecode = True
from PIL import Image, ImageDraw, ImageFont
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'assets/generated/v13ent-cave-variety/seedvr2-qwen21-20261115'
SOURCE=ROOT/'assets/generated/v13ent-cave/v1-20261111/sources'
RUNTIME=ROOT/'runtime/hd-world-pilot/data/art/hd/world-pilot'
spec=importlib.util.spec_from_file_location('helpers',ROOT/'work/seedvr2-image-setup/20261113/knife-upscale.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def node(kind,**kw):return dict(class_type=kind,inputs=kw)
def runtime_image(filename):
    b=(RUNTIME/filename).read_bytes();magic,v,w,hh,s=struct.unpack('<4sIIII',b[:20]);assert magic==b'F1HD' and v==1 and s==4
    return Image.frombytes('RGBA',(w,hh),b[20:])
def upload(path):
    boundary='cave-variety-'+uuid.uuid4().hex
    body=b''
    for key,val in {'type':'input','subfolder':'fallout1_cave_variety_20261115','overwrite':'false'}.items():
        body+=f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{val}\r\n'.encode()
    body+=f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{path.stem}-{uuid.uuid4().hex}.png"\r\nContent-Type: image/png\r\n\r\n'.encode()+path.read_bytes()+f'\r\n--{boundary}--\r\n'.encode()
    req=urllib.request.Request(h.BASE+'/upload/image',body,{'Content-Type':'multipart/form-data; boundary='+boundary})
    with urllib.request.urlopen(req,timeout=45) as r:result=json.load(r)
    return result['subfolder']+'/'+result['name']

def prepare():
    if (OUT/'plan.json').exists():print('Existing plan retained.');return
    OUT.mkdir(parents=True,exist_ok=True)
    rows={r['path']:r for r in read(SOURCE/'manifest.json')['assets']}
    reg={}
    for line in (RUNTIME/'registry.tsv').read_text().splitlines():
        if not line or line.startswith('#'):continue
        vals=line.split();reg.setdefault(int(vals[1]),vals[4])
    selected_walls=[f'art/walls/ca{n:03}.frm' for n in [3,4,5,6,7,8,9,19,20,21,22,23]]
    floor_names=[f'art/tiles/cav{n}.frm' for n in [1000,1001,1002,1003,3000,3004,4000,4003]]
    groups=[('rocks-a',[f'art/scenery/rock{n:02}.frm' for n in [1,2,3]],(384,128),3),
            ('rocks-b',[f'art/scenery/rock{n:02}.frm' for n in [4,5,6]],(384,128),3),
            ('formations',[f'art/scenery/{n}.frm' for n in ['cstalag1','cstalag2','cvcolum1','cvcolum2']],(256,128),2),
            ('floor',floor_names,(192,256),2)]
    panels=[];selected=set(selected_walls)
    # Exact source placement and decoding only; all artistic operations are ComfyUI graphs.
    for name,names,size,variants in groups:
        native=Image.new('RGBA',size);current=Image.new('RGBA',(size[0]*4,size[1]*4));slots=[]
        for i,res in enumerate(names):
            r=rows[res];selected.add(res)
            src=Image.open(SOURCE/r['rgba_png']).convert('RGBA');assert sha(SOURCE/r['rgba_png'])==r['rgba_png_sha256']
            if name=='floor':x=(i%2)*96+8;y=(i//2)*64+14
            else:
                cell=size[0]//len(names);x=i*cell+(cell-r['width'])//2;y=(size[1]-r['height'])//2
            fid=r['fids'][0] if r['fids'] else (4<<24)|r['tile_art_ids'][0]
            filename=reg[fid];cur=runtime_image(filename)
            native.paste(src,(x,y));current.paste(cur,(x*4,y*4))
            slots.append(dict(source=res,x=x,y=y,width=r['width'],height=r['height']))
        d=OUT/'inputs'/name;d.mkdir(parents=True,exist_ok=True)
        native.save(d/'original.png');current.save(d/'current-hd.png')
        panels.append(dict(id=name,native_size=size,working_size=[size[0]*4,size[1]*4],variants=variants,slots=slots))
    contexts=read(ROOT/'assets/generated/v13ent-rock-detail/v1-crisp-20261112/analysis/context-plan.json')['contexts']
    for c in contexts:
        slots=[s for s in c['selected'] if s['source'] in selected_walls]
        if not slots:continue
        name=c['id'];box=c['box_native'];size=(600,400)
        native_path=ROOT/f'assets/generated/v13ent-wall-joins/v1-20261112/prepared/{name}/original-context.png'
        native=Image.open(native_path).convert('RGB');assert native.size==size
        current=Image.new('RGB',(2400,1600))
        for p in c['placements']:
            r=rows[p['source']];cur=runtime_image(reg[r['fids'][0]])
            current.paste(cur,((p['x']-box[0])*4,(p['y']-box[1])*4),cur)
        d=OUT/'inputs'/name;d.mkdir(parents=True,exist_ok=True)
        native.save(d/'original.png');current.save(d/'current-hd.png')
        panels.append(dict(id=name,native_size=size,working_size=[1200,800],variants=2,
            slots=[dict(source=s['source'],x=s['x']-box[0],y=s['y']-box[1],width=s['width'],height=s['height']) for s in slots],context=c))
    records=[]
    for res in sorted(selected):
        r=rows[res];fid=r['fids'][0] if r['fids'] else (4<<24)|r['tile_art_ids'][0]
        filename=reg[fid];d=OUT/'sources'/res;d.parent.mkdir(parents=True,exist_ok=True)
        (Path(str(d)+'.png')).write_bytes((SOURCE/r['rgba_png']).read_bytes())
        runtime_image(filename).save(Path(str(d)+'.current.png'))
        records.append(dict(source=res,category=r['category'],native=[r['width'],r['height']],instances=len(r['map_instances']),floor_cells=len(r['visible_floor_cells']),
            source_sha256=r['source_sha256'],png_sha256=r['rgba_png_sha256'],runtime_file=filename,runtime_sha256=sha(RUNTIME/filename),registration=r['registration'],fids=r['fids']))
    save(OUT/'source-inventory.json',records)
    all_counts=[dict(source=r['path'],category=r['category'],instances=len(r['map_instances']),floor_cells=len(r['visible_floor_cells']),native=[r['width'],r['height']]) for r in rows.values()]
    save(OUT/'full-cave-inventory.json',all_counts)
    tracked=[ROOT/'AGENTS.md',ROOT/'HD-TEXTURE-GUIDE.md',ROOT/'runtime/hd-world-pilot/fallout-ce.exe',RUNTIME/'registry.tsv',RUNTIME/'variants.tsv',RUNTIME/'manifest.json']
    save(OUT/'baseline-hashes.json',{str(p.relative_to(ROOT)):sha(p) for p in tracked})
    save(OUT/'plan.json',dict(status='candidate-only; user requested comparisons before integration',pipeline='original -> SeedVR2 x4 -> Qwen Image 2.1 with current HD as material context',panels=panels,source_count=len(records),new_variant_count=sum(len(p['slots'])*p['variants'] for p in panels),runtime_writes=False))
    print(json.dumps(read(OUT/'plan.json'),ensure_ascii=False)[:1800],flush=True)

def execute(d,graph,outputs):
    d.mkdir(parents=True,exist_ok=True)
    if (d/'result.json').exists():return read(d/'result.json')
    if not (d/'run.json').exists():
        schemas=h.req('/object_info');wf=h.workflow(graph,schemas)
        wf['last_node_id']=max(int(k) for k in graph)
        wf['extra']['notes']='Isolated cave candidates; SeedVR2 -> Qwen 2.1. No runtime changes.'
        save(d/'prompt-api.json',graph);save(d/'workflow.json',wf);save(d/'outputs.json',outputs)
        # Wait without changing anyone else's shared queue.
        while True:
            q=h.req('/queue')
            if not q['queue_running'] and not q['queue_pending']:break
            print('Shared queue busy; waiting without cancelling.',flush=True);time.sleep(10)
        token='cave-variety-'+uuid.uuid4().hex
        try:r=h.req('/prompt',dict(prompt=graph,client_id=token,extra_data={'extra_pnginfo':{'workflow':wf}}))
        except urllib.error.HTTPError as e:
            (d/'error.json').write_bytes(e.read());raise
        save(d/'run.json',r)
        if r.get('node_errors'):raise RuntimeError(r)
        print(f'SUBMITTED {d.relative_to(OUT)} {r["prompt_id"]}',flush=True)
    pid=read(d/'run.json')['prompt_id']
    outputs=read(d/'outputs.json')
    start=time.monotonic()
    while True:
        job=h.req('/history/'+pid).get(pid)
        if job:break
        if time.monotonic()-start>3600:raise TimeoutError('Resume same job; never blindly resubmit.')
        time.sleep(5)
    save(d/'history.json',job)
    if job['status']['status_str']!='success':raise RuntimeError(job['status'])
    files=[]
    for nid,name in outputs.items():
        record=job['outputs'][nid]['images'][0];p=d/name;p.parent.mkdir(parents=True,exist_ok=True)
        with urllib.request.urlopen(h.BASE+'/view?'+urllib.parse.urlencode(record),timeout=60) as response:data=response.read()
        if p.exists() and p.read_bytes()!=data:raise RuntimeError('Refusing to replace different result')
        p.write_bytes(data);im=Image.open(p)
        files.append(dict(file=name,sha256=sha(p),size=im.size,mode=im.mode))
    ev=dict(job['status']['messages']);elapsed=(ev['execution_success']['timestamp']-ev['execution_start']['timestamp'])/1000
    result=dict(status='generated candidate, not installed',prompt_id=pid,elapsed_seconds=elapsed,files=files)
    save(d/'result.json',result);print(f'DONE {d.relative_to(OUT)} {elapsed:.1f}s',flush=True)
    return result

def seed(panel,current=False):
    d=OUT/('seedvr2-current' if current else 'seedvr2')/panel['id']
    if (d/'result.json').exists():return
    if (d/'run.json').exists():execute(d,{},{});return
    g=read(ROOT/'assets/generated/inventory-knife/seedvr2-x4-20261113/prompt-api.json')
    g['1']['inputs']['image']=upload(OUT/'inputs'/panel['id']/('current-hd.png' if current else 'original.png'))
    if current:g['3']['inputs']['scale_by']=1.0
    prefix='fallout1_cave_variety/'+uuid.uuid4().hex
    g['12']['inputs']['filename_prefix']=prefix+'/seedvr2-x4';g['13']['inputs']['filename_prefix']=prefix+'/lanczos-x4'
    g['9']['inputs']['seed']=15112026
    execute(d,g,{'12':'seedvr2-x4.png','13':'lanczos-x4.png'})
    if current:save(d/'source-note.json',dict(source='Current installed HD decoded losslessly',operation='SeedVR2 detail restoration at existing 4x game density; no extra scale multiplication',scale_by=1.0))

STYLES={
 'a':'MATERIAL A: dark grey fractured limestone, broad angular broken faces with clearly visible sharp chips and deep irregular cracks. Rough cut stone, coherent detail at several scales, warm grey dust in recesses. No repeated parallel ridges, no smooth river pebbles.',
 'b':'MATERIAL B: dark grey SEDIMENTARY ROCK with thick fractured strata and broad jagged ledges. Clearly redraw each boulder as a different formation of layered slabs; visible irregular dark seams separating strata and diagonal fractures cutting across them. Occasional narrow muted ochre mineral deposits. Substantial differences in the pattern and surface relief from the input. No smooth rounded pebbles, pale chalk, silver material or polished surfaces.',
 'c':'MATERIAL C: weathered charcoal grey cave limestone with heavily eroded irregular cavities, broken angular corners and a few broad smooth worn planes. Several deep cracks and medium-sized pits, subtle dark earthy deposits in recesses, dusty sharp exposed edges. Vary the size and arrangement of pits and cracks between rocks. No smooth river pebbles, moss, plants, glow or crystals.'}

def qwen(panel,variant,attempt=None,current=False,full=False):
    name=panel['id'];d=OUT/'qwen'/name/(variant if not attempt else variant+'-'+attempt)
    if (d/'result.json').exists():return
    if (d/'run.json').exists():execute(d,{},{});return
    if name.startswith('rocks'):w,hh=960,320;refw,refh=384,128
    elif name=='formations':w,hh=768,384;refw,refh=384,192
    elif name=='floor':w,hh=576,768;refw,refh=288,384
    else:w,hh=960,640;refw,refh=480,320
    if full:
        w,hh=panel['working_size'];w=w//32*32;hh=hh//32*32
    kind='wall' if name.startswith('wall') else ('floor' if name=='floor' else 'objects')
    common='Repaint these cave sprites as clean high-resolution PRE-RENDERED 3D game art, delivered as flat 2D assets. Realistic natural rock material and soft continuous lighting, not pixel art, drawing or stippled illustration. Substantially redesign the internal surface relief: bold broad facets and cracks, dark recesses and selective edge highlights. Neutral medium-dark grey under soft upper-left light, muted post-apocalyptic atmosphere. Keep the exact outer silhouettes, object positions, framing, footprints and isometric camera. No dither, grain, black drawn outlines, stippling, plastic shine, text, characters, extra objects or blue tint. '
    if kind=='wall':common+='This is a connected wall neighborhood, not separate upright plates. Keep every major wall boundary, top cut surface, base line and black void unchanged. Draw coherent continuous rock strata across the full wall face. Do not introduce seams at narrow sprite boundaries. Keep black unpainted regions black. '
    elif kind=='floor':common+='This is a fixed-position atlas of eight separate isometric floor tiles. Keep all eight tiles at their exact original positions with transparent margins, keep each diamond outline and topology. Flattened dust, bedrock and small embedded stones, no raised piles. Texture should have irregular broad patches and quiet areas, modest contrast, no single conspicuous repeating motif. '
    else:common+='This is a fixed-position atlas of separate cave rock or stone formation sprites. Keep the exact number, positions and external contours, transparent empty space, same footprint, and orthographic isometric viewing angles. Redraw their interior faces distinctly; do not connect, merge or duplicate sprites. No ground plane or cast-shadow extensions. '
    style=STYLES[variant]
    if kind=='floor' and variant=='b':
        style='MATERIAL B: compacted dusty cave earth, irregular broad worn patches and sparse fine gravel, subtle shallow erosion channels. Grey-brown dust dominates the four plain tiles in the top two rows; keep them mostly quiet and flat. The four lower tiles retain their original embedded stones, with dust settled between them. No paving, cobblestone pattern, large polygonal slabs, new boulder piles or evenly spaced cracks.'
    prompt=common+style+' Prioritize large irregular geological forms and clean continuous shading. Keep broad quiet surfaces between a few decisive cracks. No fine grain, stippling, sandpaper texture, tessellated pebbles or uniformly noisy micro-detail.'
    seed_path=OUT/('seedvr2-current' if current else 'seedvr2')/name/'seedvr2-x4.png'
    prefix='fallout1_cave_variety/'+uuid.uuid4().hex
    g={
      '1':node('LoadImage',image=upload(seed_path)),
      '2':node('JoinImageWithAlpha',image=['1',0],alpha=['1',1]),
      '3':node('ImageScale',image=['2',0],upscale_method='lanczos',width=w,height=hh,crop='disabled'),
      '4':node('UNETLoader',unet_name='qwen_image_2.1_int8_convrot.safetensors',weight_dtype='default'),
      '5':node('CLIPLoader',clip_name='qwen3vl_8b_int8_convrot.safetensors',type='qwen_image',device='default'),
      '6':node('VAELoader',vae_name='qwen_image_2.1_vae_bf16.safetensors'),
      '7':node('QwenImage21Cache',model=['4',0],device='cpu',dtype='default'),
      '8':node('TextEncodeQwenImage21',clip=['5',0],prompt=prompt,negative_prompt='',vae=['6',0],resolution=0,**{'images.image_1':['3',0]}),
      '9':node('KSampler',model=['7',0],positive=['8',0],negative=['8',1],latent_image=['8',2],seed=15112026+ord(variant),steps=25,cfg=1.0,sampler_name='euler',scheduler='simple',denoise=1.0),
      '10':node('VAEDecode',samples=['9',0],vae=['6',0]),
      '11':node('SaveImage',images=['10',0],filename_prefix=prefix+'/qwen-raw'),
      '12':node('SaveImage',images=['3',0],filename_prefix=prefix+'/seed-reference'),
    }
    d.mkdir(parents=True,exist_ok=True);(d/'prompt.txt').write_text(prompt,encoding='utf-8')
    save(d/'plan.json',dict(panel=name,variant=variant,attempt=attempt,prompt_revision=3,working=[w,hh],full_working_resolution=full,seed=15112026+ord(variant),steps=25,source_path=str(seed_path.relative_to(OUT)),source=sha(seed_path),current_reference_used=False))
    execute(d,g,{'11':'raw.png','12':'seed-reference.png'})

def run(stage,only=None):
    panels=read(OUT/'plan.json')['panels']
    if only:panels=[p for p in panels if p['id']==only]
    for p in panels:
        if stage=='seed':seed(p)
        if stage=='seed-current':seed(p,True)
        if stage=='qwen':
            for v in 'abc'[:p['variants']]:qwen(p,v)
        if stage=='prepare-assets':prepare_assets(p)

def prepare_assets(panel):
    name=panel['id'];d=OUT/'prepared'/name
    if (d/'result.json').exists():return
    if (d/'run.json').exists():execute(d,{},{});return
    g={};outputs={};prefix='fallout1_cave_variety/prepared/'+uuid.uuid4().hex
    def add(c,**kw):
        key=str(len(g)+1);g[key]=node(c,**kw);return [key,0]
    def load(p):return add('LoadImage',image=upload(p))
    def emit(im,path):
        n=add('SaveImage',images=im,filename_prefix=prefix+'/'+path.removesuffix('.png'));outputs[n[0]]=path
    raw={};nativew,nativeh=panel['native_size'];color_records={}
    choices=read(OUT/'qwen-selection.json').get(name,{}) if (OUT/'qwen-selection.json').exists() else {}
    for v in 'abc'[:panel['variants']]:
        path=OUT/'qwen'/name/choices.get(v,v)/'raw.png'
        src=load(path)
        rgba=add('JoinImageWithAlpha',image=src,alpha=[src[0],1])
        scaled=add('ImageScale',image=rgba,upscale_method='lanczos',width=nativew*4,height=nativeh*4,crop='disabled')
        # Analysis estimates ONE shared gain per panel/variant; ComfyUI applies it.
        # Individual strip gains would undermine the connected wall material.
        donor=Image.open(path).convert('RGBA').resize((nativew*4,nativeh*4),Image.Resampling.LANCZOS)
        old_sum=np.zeros(3);new_sum=np.zeros(3);count=0
        for s in panel['slots']:
            cur=np.array(Image.open(OUT/'sources'/(s['source']+'.current.png')).convert('RGBA'))
            dr=np.array(donor.crop((s['x']*4,s['y']*4,(s['x']+s['width'])*4,(s['y']+s['height'])*4)))
            mask=(cur[:,:,3]>0)&(dr[:,:,3]>200)
            old_sum+=cur[:,:,:3][mask].sum(axis=0);new_sum+=dr[:,:,:3][mask].sum(axis=0);count+=int(mask.sum())
        gains=np.clip(old_sum/np.maximum(1,new_sum),0.4,1.0)
        rgb8=np.rint(gains*255).astype(int);color=int(rgb8[0]*65536+rgb8[1]*256+rgb8[2])
        split=add('SplitImageWithAlpha',image=scaled)
        flat=add('EmptyImage',width=nativew*4,height=nativeh*4,batch_size=1,color=color)
        matched=add('ImageBlend',image1=split,image2=flat,blend_factor=1.0,blend_mode='multiply')
        raw[v]=add('JoinImageWithAlpha',image=matched,alpha=[split[0],1])
        color_records[v]=dict(method='one shared linear RGB multiplier for whole source context',rgb_multiplier=(rgb8/255).tolist(),old_mean=(old_sum/max(1,count)).tolist(),generated_mean=(new_sum/max(1,count)).tolist(),sample_pixels=count,source=str(path.relative_to(OUT)))
    seedim=load(OUT/'seedvr2'/name/'seedvr2-x4.png')
    seedrgba=add('JoinImageWithAlpha',image=seedim,alpha=[seedim[0],1])
    hdseed=load(OUT/'seedvr2-current'/name/'seedvr2-x4.png')
    hdseed=add('JoinImageWithAlpha',image=hdseed,alpha=[hdseed[0],1])
    records=[]
    for slot in panel['slots']:
        res=slot['source'];stem=Path(res).stem;w=slot['width']*4;hh=slot['height']*4;x=slot['x']*4;y=slot['y']*4
        old=load(OUT/'sources'/(res+'.current.png'))
        alpha=[old[0],1];opaque=add('InvertMask',mask=alpha)
        # A protected band retains installed joins. It does not prove internal geometry correctness.
        border=8 if res.startswith('art/walls/') else (12 if res.startswith('art/tiles/') else 2)
        inner=add('GrowMask',mask=opaque,expand=-border,tapered_corners=False)
        empty=add('SolidMask',value=0.0,width=w,height=hh)
        rect=add('SolidMask',value=1.0,width=w-2*border,height=hh-2*border)
        rect=add('MaskComposite',destination=empty,source=rect,x=border,y=border,operation='add')
        inner=add('MaskComposite',destination=inner,source=rect,x=0,y=0,operation='multiply')
        blur=add('MaskToImage',mask=inner);blur=add('ImageBlur',image=blur,blur_radius=4,sigma=1.0)
        soft=add('ImageToMask',image=blur,channel='red')
        soft=add('MaskComposite',destination=inner,source=soft,x=0,y=0,operation='multiply')
        emit(add('MaskToImage',mask=soft),f'masks/{stem}.png')
        scrop=add('ImageCrop',image=seedrgba,x=x,y=y,width=w,height=hh)
        emit(scrop,f'seed/{stem}-raw.png')
        # Original, exact registration for the restoration baseline; no color enhancement here.
        emit(add('JoinImageWithAlpha',image=scrop,alpha=alpha),f'seed/{stem}.png')
        hdscrop=add('ImageCrop',image=hdseed,x=x,y=y,width=w,height=hh)
        emit(add('JoinImageWithAlpha',image=hdscrop,alpha=alpha),f'seed-current/{stem}.png')
        for v,atlas in raw.items():
            crop=add('ImageCrop',image=atlas,x=x,y=y,width=w,height=hh)
            emit(crop,f'raw/{stem}-{v}.png')
            rgb,trans=add('SplitImageWithAlpha',image=crop),None
            trans=[rgb[0],1];generated_opaque=add('InvertMask',mask=trans)
            available=add('MaskComposite',destination=soft,source=generated_opaque,x=0,y=0,operation='multiply')
            result=add('ImageCompositeMasked',destination=old,source=rgb,x=0,y=0,resize_source=False,mask=available)
            result=add('JoinImageWithAlpha',image=result,alpha=alpha)
            emit(result,f'variants/{stem}-{v}.png')
        records.append(dict(source=res,crop=[x,y,w,hh],protected_border_hd=border,alpha='exact installed alpha; unchanged native registration',candidate_status='visual review required'))
    d.mkdir(parents=True,exist_ok=True);save(d/'asset-plan.json',records);save(d/'color-match.json',color_records)
    execute(d,g,outputs)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','seed','seed-current','qwen','prepare-assets']);p.add_argument('--only');p.add_argument('--variant');p.add_argument('--attempt');p.add_argument('--current',action='store_true');p.add_argument('--full',action='store_true');a=p.parse_args()
    if a.stage=='prepare':prepare()
    elif a.stage=='qwen' and a.variant:
        panel=next(x for x in read(OUT/'plan.json')['panels'] if x['id']==a.only)
        qwen(panel,a.variant,a.attempt,a.current,a.full)
    else:run(a.stage,a.only)
