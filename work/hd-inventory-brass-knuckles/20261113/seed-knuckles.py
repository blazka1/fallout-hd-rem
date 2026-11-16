"""Export the real Brass Knuckles inventory icon and upscale it with local SeedVR2."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, struct, sys, time, urllib.request, urllib.parse, uuid
from PIL import Image, ImageDraw, ImageFont
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'assets/generated/inventory-brass-knuckles/seedvr2-x4-20261113'
BASE = 'http://127.0.0.1:8188'
sys.path.insert(0, str(ROOT/'tools/asset-pipeline'))
from fallout_assets import Assets, Frame, decode_frm, palette_rgb, png_indexed
from cave_reference import MapInspector, rgba_png

def save(name, value):
    (OUT/name).write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')

def req(path, value=None):
    payload = None if value is None else json.dumps(value).encode()
    request = urllib.request.Request(BASE+path, payload,
        {'Content-Type':'application/json'} if payload is not None else {})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def inventory_frame(raw):
    # CE art_readFrameData/art_readSubFrameData use the same fields for this
    # legacy v3 static icon. Keep the original bytes intact; restrict this
    # compatibility reader to one frame and one shared direction.
    version = struct.unpack_from('>I', raw)[0]
    if version == 4:
        metadata, directions = decode_frm(raw)
        return metadata, directions[0][0]
    version, fps, action, count = struct.unpack_from('>IHHH', raw)
    offsets = struct.unpack_from('>6I', raw, 34)
    data_size = struct.unpack_from('>I', raw, 58)[0]
    assert version == 3 and count == 1 and offsets == (0,)*6
    assert data_size == len(raw)-62
    w, h, n, dx, dy = struct.unpack_from('>HHIhh', raw, 62)
    assert 0 < w*h <= 16000000 and n == w*h and len(raw) == 74+n
    metadata = dict(version=version, stored_fps=fps, action_frame=action,
        frame_count=count, direction_x=struct.unpack_from('>6h',raw,10),
        direction_y=struct.unpack_from('>6h',raw,22), direction_offsets=offsets,
        data_size=data_size, frame_size=[w,h], frame_shift=[dx,dy],
        decoder='Task-local legacy static FRM reader, verified against CE art.cc')
    return metadata, Frame(w,h,dx,dy,raw[74:])

def idle():
    queue = req('/queue')
    if queue['queue_running'] or queue['queue_pending']:
        raise RuntimeError('ComfyUI is busy. No jobs cancelled or submitted.')

def upload(path):
    boundary = 'seedvr2-knuckles-'+uuid.uuid4().hex
    parts = []
    for key, value in {'type':'input','subfolder':'fallout1_seedvr2_knuckles','overwrite':'false'}.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    parts += [f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="knuckles-native-{uuid.uuid4().hex}.png"\r\nContent-Type: image/png\r\n\r\n'.encode(),
              path.read_bytes(), f'\r\n--{boundary}--\r\n'.encode()]
    request = urllib.request.Request(BASE+'/upload/image', b''.join(parts),
        {'Content-Type':'multipart/form-data; boundary='+boundary})
    with urllib.request.urlopen(request, timeout=30) as response:
        record = json.load(response)
    return record['subfolder']+'/'+record['name']

def workflow(graph, schemas):
    links, inputs, outputs = [], {}, {}
    for nid, node in graph.items():
        slot = 0
        for key, value in node['inputs'].items():
            if isinstance(value, list):
                kind = schemas[graph[value[0]]['class_type']]['output'][value[1]]
                link = len(links)+1
                links.append([link,int(value[0]),value[1],int(nid),slot,kind])
                inputs.setdefault(nid,[]).append({'name':key,'type':kind,'link':link})
                outputs.setdefault((value[0],value[1]),[]).append(link)
                slot += 1
    nodes = []
    for nid, node in graph.items():
        values = []
        for key, value in node['inputs'].items():
            if not isinstance(value,list):
                values.append(value)
                if node['class_type']=='KSampler' and key=='seed': values.append('fixed')
        if node['class_type']=='LoadImage': values.append('image')
        schema=schemas[node['class_type']]
        nodes.append(dict(id=int(nid),type=node['class_type'],
            pos=[((int(nid)-1)%4)*410,((int(nid)-1)//4)*330],size=[370,260],
            flags={},order=int(nid)-1,mode=0,inputs=inputs.get(nid,[]),
            outputs=[dict(name=schema.get('output_name',schema['output'])[i],type=t,
                links=outputs.get((nid,i),[]),slot_index=i) for i,t in enumerate(schema['output'])],
            properties={'Node name for S&R':node['class_type']},widgets_values=values))
    return dict(last_node_id=len(nodes),last_link_id=len(links),nodes=nodes,links=links,
        groups=[],config={},extra={'notes':'Local SeedVR2 3B INT8, image x4, one-step, original resized alpha preserved. No prompt required.'},version=0.4)

def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT/'plan.json').exists():
        print('Existing prepared experiment retained.', flush=True)
        return
    assets=Assets([ROOT/'FALLOUT (extract.me)/MASTER.DAT',ROOT/'FALLOUT (extract.me)/CRITTER.DAT'])
    inspector=MapInspector(assets)
    proto=inspector.prototype(21)
    prototype=assets.read(proto['path'])
    pid,message_id=struct.unpack_from('>II',prototype)
    inventory_fid=struct.unpack_from('>I',prototype,52)[0]
    art=inspector.art_path(inventory_fid)
    assert pid==21 and message_id==2100 and art=='art/inven/brsnuck.frm'
    reference=OUT/'reference'
    reference.mkdir(exist_ok=True)
    assets.extract([proto['path'],art,'art/inven/inven.lst','proto/items/items.lst','color.pal','text/english/game/pro_item.msg'],reference)
    raw=assets.read(art)
    palette=palette_rgb(assets.read('color.pal'))
    metadata,frame=inventory_frame(raw)
    (OUT/'knuckles-indexed.png').write_bytes(png_indexed(frame.width,frame.height,frame.pixels,palette))
    png,_=rgba_png(frame,palette)
    source=OUT/'knuckles-native.png'
    source.write_bytes(png)
    save('source.json',dict(pid=pid,name='Brass Knuckles',message_id=message_id,prototype=proto,
        inventory_fid=inventory_fid,source_art=art,frm_sha256=hashlib.sha256(raw).hexdigest(),
        source_png_sha256=sha(source),native_size=[frame.width,frame.height],metadata=metadata,
        preserved='Original DAT, runtime and game resources are unchanged.'))
    idle()
    image_name=upload(source)
    prefix='fallout1_seedvr2_knuckles/'+uuid.uuid4().hex
    def node(kind,**inputs): return {'class_type':kind,'inputs':inputs}
    graph={
        '1':node('LoadImage',image=image_name),
        '2':node('JoinImageWithAlpha',image=['1',0],alpha=['1',1]),
        '3':node('ImageScaleBy',image=['2',0],upscale_method='lanczos',scale_by=4.0),
        '4':node('UNETLoader',unet_name='seedvr2_3b_int8_convrot.safetensors',weight_dtype='default'),
        '5':node('VAELoader',vae_name='seedvr2_ema_vae_fp16.safetensors'),
        '6':node('SeedVR2Preprocess',resized_images=['3',0]),
        '7':node('VAEEncodeTiled',pixels=['6',0],vae=['5',0],tile_size=512,overlap=128,temporal_size=4096,temporal_overlap=8),
        '8':node('SeedVR2Conditioning',model=['4',0],vae_conditioning=['7',0]),
        '9':node('KSampler',model=['4',0],positive=['8',0],negative=['8',1],latent_image=['7',0],
                 seed=13112026,steps=1,cfg=1.0,sampler_name='euler',scheduler='simple',denoise=1.0),
        '10':node('VAEDecodeTiled',samples=['9',0],vae=['5',0],tile_size=512,overlap=128,temporal_size=4096,temporal_overlap=8),
        '11':node('SeedVR2PostProcessing',images=['10',0],original_resized_images=['3',0],color_correction_method='none'),
        '12':node('SaveImage',images=['11',0],filename_prefix=prefix+'/knuckles-seedvr2-x4'),
        '13':node('SaveImage',images=['3',0],filename_prefix=prefix+'/knuckles-lanczos-x4'),
    }
    schemas=req('/object_info')
    save('prompt-api.json',graph)
    save('workflow.json',workflow(graph,schemas))
    save('plan.json',dict(source=image_name,output_size=[frame.width*4,frame.height*4],scale=4,
        seed=13112026,steps=1,cfg=1,sampler='euler',scheduler='simple',denoise=1,
        color_correction='none',alpha='Original alpha resized by Lanczos and restored by native post-processing',
        template='utility_seedvr2_3b_int8_upscale_image.json',status='prepared'))
    print(json.dumps({'source':art,'pid':pid,'size':[frame.width,frame.height],'output_size':[frame.width*4,frame.height*4]}),flush=True)

def submit():
    if (OUT/'run.json').exists():
        raise RuntimeError('Existing run retained; use collect, never resubmit blindly.')
    idle()
    graph=json.loads((OUT/'prompt-api.json').read_text(encoding='utf-8'))
    schemas=req('/object_info')
    assert graph['4']['inputs']['unet_name'] in schemas['UNETLoader']['input']['required']['unet_name'][0]
    assert graph['5']['inputs']['vae_name'] in schemas['VAELoader']['input']['required']['vae_name'][0]
    wf=json.loads((OUT/'workflow.json').read_text(encoding='utf-8'))
    result=req('/prompt',dict(prompt=graph,client_id='seedvr2-knuckles-'+uuid.uuid4().hex,extra_data={'extra_pnginfo':{'workflow':wf}}))
    save('run.json',dict(**result,submitted_utc=datetime.now(timezone.utc).isoformat()))
    if result.get('node_errors'): raise RuntimeError(str(result['node_errors']))
    print(json.dumps(result),flush=True)

def collect():
    run=json.loads((OUT/'run.json').read_text(encoding='utf-8'))
    prompt_id=run['prompt_id']
    started=time.monotonic()
    while True:
        history=req('/history/'+prompt_id)
        if prompt_id in history: break
        print('Waiting for SeedVR2 job '+prompt_id,flush=True)
        if time.monotonic()-started>1800: raise TimeoutError('Job remains in ComfyUI; resume collect.')
        time.sleep(15)
    job=history[prompt_id]
    save('history.json',job)
    if job['status']['status_str']!='success': raise RuntimeError(str(job['status']))
    for key,name in [('12','knuckles-seedvr2-x4.png'),('13','knuckles-lanczos-x4.png')]:
        result=job['outputs'][key]['images'][0]
        with urllib.request.urlopen(BASE+'/view?'+urllib.parse.urlencode(result),timeout=30) as response:
            (OUT/name).write_bytes(response.read())
    original=Image.open(OUT/'knuckles-native.png').convert('RGBA')
    output=Image.open(OUT/'knuckles-seedvr2-x4.png')
    baseline=Image.open(OUT/'knuckles-lanczos-x4.png').convert('RGBA')
    pixels=np.array(output)
    assert output.mode=='RGBA' and output.size==(original.width*4,original.height*4)
    assert np.array_equal(pixels[:,:,3],np.array(baseline)[:,:,3])
    opaque=pixels[pixels[:,:,3]>127,:3]
    assert opaque.size and opaque.max()>20 and float(opaque.std())>1
    events=dict(job['status']['messages'])
    elapsed=(events['execution_success']['timestamp']-events['execution_start']['timestamp'])/1000
    stats=dict(status='completed',prompt_id=prompt_id,output_size=list(output.size),mode=output.mode,
        alpha_matches_lanczos_baseline=True,opaque_rgb_std=float(opaque.std()),elapsed_seconds=elapsed,
        source_sha256=sha(OUT/'knuckles-native.png'),output_sha256=sha(OUT/'knuckles-seedvr2-x4.png'),
        model='seedvr2_3b_int8_convrot.safetensors',runtime_installed=False)
    save('result.json',stats)
    margin=24
    panel_w=max(output.width+margin*2,240)
    panel_h=output.height+margin*2+42
    preview=Image.new('RGB',(panel_w*3,panel_h),(34,38,38))
    draw=ImageDraw.Draw(preview)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
    pictures=[original.resize(output.size,Image.Resampling.NEAREST),baseline,output]
    labels=['Оригинал ×4','Обычное увеличение','SeedVR2 3B INT8 ×4']
    for i,(picture,label) in enumerate(zip(pictures,labels)):
        x=i*panel_w+(panel_w-picture.width)//2
        preview.paste(picture,(x,48+margin//2),picture)
        draw.text((i*panel_w+14,14),label,font=font,fill=(226,224,211))
    preview.save(OUT/'comparison.png')
    print(json.dumps(stats),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['prepare','submit','collect'])
    args=parser.parse_args()
    {'prepare':prepare,'submit':submit,'collect':collect}[args.action]()
