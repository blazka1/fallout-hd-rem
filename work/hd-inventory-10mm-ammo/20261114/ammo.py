"""Task-local original export and independent local ComfyUI ammo candidates."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, importlib.util, json, struct, sys, uuid, urllib.request, urllib.parse
from PIL import Image, ImageDraw, ImageFont
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT/'assets/generated/inventory-10mm-ammo/20261114'
spec=importlib.util.spec_from_file_location('helpers',ROOT/'work/hd-inventory-brass-knuckles/20261113/seed-knuckles.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
ITEMS={'jhp':dict(pid=29,name='10mm JHP',fid=0x0700001f,size=(83,58)),
       'ap':dict(pid=30,name='10mm AP',fid=0x0700001e,size=(83,61))}

def save(path,value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def export():
    assets=h.Assets([ROOT/'FALLOUT (extract.me)/MASTER.DAT',ROOT/'FALLOUT (extract.me)/CRITTER.DAT'])
    inspector=h.MapInspector(assets)
    preview=Image.new('RGB',(800,340),(34,38,38));d=ImageDraw.Draw(preview)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
    for i,(key,item) in enumerate(ITEMS.items()):
        out=BASE/key/'source';out.mkdir(parents=True,exist_ok=True)
        if not (out/'source.json').exists():
            proto=inspector.prototype(item['pid']);rawproto=assets.read(proto['path'])
            pid,message=struct.unpack_from('>II',rawproto);fid=struct.unpack_from('>I',rawproto,52)[0]
            assert pid==item['pid'] and fid==item['fid']
            art=inspector.art_path(fid);raw=assets.read(art);meta,frame=h.inventory_frame(raw)
            assert (frame.width,frame.height)==item['size']
            paths=[proto['path'],art,'color.pal','art/inven/inven.lst','proto/items/items.lst','text/english/game/pro_item.msg']
            assets.extract(paths,out/'reference');palette=h.palette_rgb(assets.read('color.pal'))
            (out/'native.png').write_bytes(h.rgba_png(frame,palette)[0])
            (out/'indexed.png').write_bytes(h.png_indexed(frame.width,frame.height,frame.pixels,palette))
            save(out/'source.json',dict(pid=pid,name=item['name'],message_id=message,prototype=proto,inventory_fid=fid,
                source_art=art,native_size=item['size'],metadata=meta,frm_sha256=hashlib.sha256(raw).hexdigest(),source_sha256=h.sha(out/'native.png')))
        im=Image.open(out/'native.png').convert('RGBA').resize(tuple(v*4 for v in item['size']),Image.Resampling.NEAREST)
        preview.paste(im,(i*400+34,60),im);d.text((i*400+34,20),item['name']+' — original ×4',font=font,fill='white')
    preview.save(BASE/'originals.png')
    print(BASE/'originals.png')

def upload(path):
    boundary='ammo-'+uuid.uuid4().hex
    parts=[]
    for key,value in {'type':'input','subfolder':'fallout1_10mm_ammo','overwrite':'false'}.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    parts += [f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="ammo-{uuid.uuid4().hex}.png"\r\nContent-Type: image/png\r\n\r\n'.encode(),path.read_bytes(),f'\r\n--{boundary}--\r\n'.encode()]
    req=urllib.request.Request(h.BASE+'/upload/image',b''.join(parts),{'Content-Type':'multipart/form-data; boundary='+boundary})
    with urllib.request.urlopen(req,timeout=30) as response:record=json.load(response)
    return record['subfolder']+'/'+record['name']

def submit(key,model):
    item=ITEMS[key];out=BASE/key/model;out.mkdir(parents=True,exist_ok=True)
    if (out/'run.json').exists():raise RuntimeError('Existing run: collect instead of submit.')
    h.idle();schemas=h.req('/object_info')
    native=Image.open(BASE/key/'source/native.png').convert('RGBA')
    source=BASE/key/'source/native.png'
    if model=='qwen':
        canvas=Image.new('RGBA',(96,80),(0,0,0,0));canvas.paste(native,(6,9))
        canvas.save(out/'source-padded.png');source=out/'source-padded.png'
    image=upload(source);token=uuid.uuid4().hex;prefix='fallout1_10mm_ammo/'+key+'/'+model+'/'+token
    def n(kind,**inputs):return dict(class_type=kind,inputs=inputs)
    graph={'1':n('LoadImage',image=image),'2':n('JoinImageWithAlpha',image=['1',0],alpha=['1',1])}
    if model=='seed':
        template=json.loads((ROOT/'assets/generated/inventory-brass-knuckles/seedvr2-x4-20261113/prompt-api.json').read_text())
        graph.update({k:v for k,v in template.items() if int(k)>2})
        for node in ['12','13']:graph[node]['inputs']['filename_prefix']=prefix+('/candidate' if node=='12' else '/lanczos')
        outputs={'12':'candidate.png','13':'lanczos.png'}
    else:
        prompt=(BASE/key/'prompt.txt').read_text(encoding='utf-8')
        graph.update({
          '3':n('ImageScale',image=['2',0],upscale_method='lanczos',width=1152,height=960,crop='disabled'),
          '4':n('UNETLoader',unet_name='qwen_image_2.1_int8_convrot.safetensors',weight_dtype='default'),
          '5':n('CLIPLoader',clip_name='qwen3vl_8b_int8_convrot.safetensors',type='qwen_image',device='default'),
          '6':n('VAELoader',vae_name='qwen_image_2.1_vae_bf16.safetensors'),
          '7':n('QwenImage21Cache',model=['4',0],device='cpu',dtype='default'),
          '8':n('TextEncodeQwenImage21',clip=['5',0],prompt=prompt,negative_prompt='',vae=['6',0],resolution=0,**{'images.image_1':['3',0]}),
          '9':n('KSampler',model=['7',0],positive=['8',0],negative=['8',1],latent_image=['8',2],seed=13112026,steps=25,cfg=1.0,sampler_name='euler',scheduler='simple',denoise=1.0),
          '10':n('VAEDecode',samples=['9',0],vae=['6',0]),
          '11':n('SaveImage',images=['10',0],filename_prefix=prefix+'/raw'),
          '12':n('SaveImage',images=['3',0],filename_prefix=prefix+'/reference'),
          '13':n('ImageCrop',image=['10',0],width=native.width*12,height=native.height*12,x=72,y=108),
          '14':n('ImageScale',image=['13',0],upscale_method='lanczos',width=native.width*4,height=native.height*4,crop='disabled'),
          '15':n('SaveImage',images=['14',0],filename_prefix=prefix+'/candidate')})
        outputs={'11':'raw.png','12':'reference-working.png','15':'candidate.png'}
        (out/'prompt.txt').write_text(prompt,encoding='utf-8')
    for node in graph.values():
        assert node['class_type'] in schemas
        if node['class_type'] in ['UNETLoader','VAELoader','CLIPLoader']:
            field={'UNETLoader':'unet_name','VAELoader':'vae_name','CLIPLoader':'clip_name'}[node['class_type']]
            assert node['inputs'][field] in schemas[node['class_type']]['input']['required'][field][0]
    wf=h.workflow(graph,schemas);wf['extra']={'notes':'10mm ammo; independent original-reference '+model+' branch'}
    save(out/'prompt-api.json',graph);save(out/'workflow.json',wf)
    save(out/'plan.json',dict(item=item,model=model,outputs=outputs,target=[native.width*4,native.height*4],
         working=[1152,960] if model=='qwen' else None,padding_native=[6,9,7,80-native.height-9] if model=='qwen' else None,
         source_sha256=h.sha(BASE/key/'source/native.png'),seed=13112026,steps=25 if model=='qwen' else 1,cfg=1,denoise=1))
    h.idle();result=h.req('/prompt',dict(prompt=graph,client_id='ammo-'+token,extra_data={'extra_pnginfo':{'workflow':wf}}))
    save(out/'run.json',dict(**result,submitted_utc=datetime.now(timezone.utc).isoformat()))
    assert not result.get('node_errors'),result
    print(json.dumps(result))

def collect(key,model):
    out=BASE/key/model;run=json.loads((out/'run.json').read_text());pid=run['prompt_id'];history=h.req('/history/'+pid)
    if pid not in history:print('RUNNING '+pid);return
    job=history[pid];save(out/'history.json',job)
    assert job['status']['status_str']=='success',job['status']
    plan=json.loads((out/'plan.json').read_text())
    for node,name in plan['outputs'].items():
        record=job['outputs'][node]['images'][0]
        with urllib.request.urlopen(h.BASE+'/view?'+urllib.parse.urlencode(record),timeout=30) as response:(out/name).write_bytes(response.read())
    im=Image.open(out/'candidate.png');a=np.array(im)[:,:,3]
    assert im.mode=='RGBA' and list(im.size)==plan['target'] and a.min()==0 and a.max()>200
    events=dict(job['status']['messages'])
    save(out/'result.json',dict(status='candidate_for_visual_review',sha256=h.sha(out/'candidate.png'),mode=im.mode,size=im.size,
      alpha_bbox=im.getchannel('A').getbbox(),elapsed_seconds=(events['execution_success']['timestamp']-events['execution_start']['timestamp'])/1000))
    print((out/'result.json').read_text())

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['export','submit','collect']);p.add_argument('--item',choices=ITEMS);p.add_argument('--model',choices=['seed','qwen']);a=p.parse_args()
    if a.action=='export':export()
    else:globals()[a.action](a.item,a.model)
