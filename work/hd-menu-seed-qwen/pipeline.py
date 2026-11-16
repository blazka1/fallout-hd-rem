"""Isolated portrait experiment: original FRM export -> SeedVR2 -> Qwen21."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, urllib.request, urllib.parse, uuid
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'assets/generated/main-menu/seed-qwen-20261114-v1'
SOURCE=ROOT/'assets/reference/main-menu/png/art/intrface/mainmenu.frm.png'
spec=importlib.util.spec_from_file_location('helpers',ROOT/'work/hd-inventory-brass-knuckles/20261113/seed-knuckles.py')
helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)
PROMPT='''Restore and refine this exact Fallout 1 main menu power armor helmet portrait. Preserve the exact composition, crop, helmet silhouette, perspective, all mechanical parts and their positions. This is the original close-up T-51 power armor helmet: preserve the narrow dark horizontal visor, the large round ribbed upper light, the broken-looking cylindrical attachment above-left, the sloping faceplate, circular lower respirator, side hoses and the partial armored shoulder. Keep the small ruined city behind the helmet. Preserve the original muted olive-grey steel, warm oxidized brass accents, left-side illumination, heavy shadow and bleak late-1990s Fallout atmosphere. Improve coherent material detail: finely worn painted steel, selective tiny scratches and paint chips on existing edges, subtle oxidation around existing seams, crisp machined rings and respirator slats. Remove residual pixel dithering and noisy speckling while retaining varied rough metal. Refine existing surfaces without inventing components. Do not change the visor opening, light size, bolt positions or body proportions. No new text, logos, UI, buttons, decoration, lights, glowing eyes, excessive rust, plastic smoothing or exaggerated sharpening. Keep the exact reference image framing, no zoom or recentering. A faithful detailed painted/prerendered game portrait, not a photographic redesign. Opaque image, fully filled canvas.'''
def save(path,value): path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def node(kind,**inputs): return dict(class_type=kind,inputs=inputs)
def upload(path):
    token=uuid.uuid4().hex; boundary='menu-'+token
    body=b''
    for k,v in dict(type='input',subfolder='fallout1_menu_seed_qwen',overwrite='false').items():
        body+=f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    body+=f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{token}.png"\r\nContent-Type: image/png\r\n\r\n'.encode()+path.read_bytes()+f'\r\n--{boundary}--\r\n'.encode()
    request=urllib.request.Request(helpers.BASE+'/upload/image',body,{'Content-Type':'multipart/form-data; boundary='+boundary})
    with urllib.request.urlopen(request,timeout=30) as r: result=json.load(r)
    return result['subfolder']+'/'+result['name']
def submit(stage):
    folder=OUT/stage;folder.mkdir(parents=True,exist_ok=True)
    if (folder/'run.json').exists(): raise RuntimeError('Already submitted; collect the recorded prompt ID.')
    helpers.idle();schemas=helpers.req('/object_info');prefix='fallout1_menu_seed_qwen/'+stage+'-'+uuid.uuid4().hex
    if stage=='seed':
        name=upload(SOURCE)
        g={
          '1':node('LoadImage',image=name),
          '2':node('ImageCrop',image=['1',0],width=380,height=456,x=8,y=12),
          '3':node('ImageScaleBy',image=['2',0],upscale_method='lanczos',scale_by=4.0),
          '4':node('UNETLoader',unet_name='seedvr2_3b_int8_convrot.safetensors',weight_dtype='default'),
          '5':node('VAELoader',vae_name='seedvr2_ema_vae_fp16.safetensors'),
          '6':node('SeedVR2Preprocess',resized_images=['3',0]),
          '7':node('VAEEncodeTiled',pixels=['6',0],vae=['5',0],tile_size=512,overlap=128,temporal_size=4096,temporal_overlap=8),
          '8':node('SeedVR2Conditioning',model=['4',0],vae_conditioning=['7',0]),
          '9':node('KSampler',model=['4',0],positive=['8',0],negative=['8',1],latent_image=['7',0],seed=14112026,steps=1,cfg=1.0,sampler_name='euler',scheduler='simple',denoise=1.0),
          '10':node('VAEDecodeTiled',samples=['9',0],vae=['5',0],tile_size=512,overlap=128,temporal_size=4096,temporal_overlap=8),
          '11':node('SeedVR2PostProcessing',images=['10',0],original_resized_images=['3',0],color_correction_method='none'),
          '12':node('SaveImage',images=['11',0],filename_prefix=prefix+'/portrait-seed-x4'),
          '13':node('SaveImage',images=['2',0],filename_prefix=prefix+'/original-portrait'),
          '14':node('SaveImage',images=['3',0],filename_prefix=prefix+'/lanczos-x4')}
        save(OUT/'source.json',dict(path=str(SOURCE),sha256=sha(SOURCE),crop=[8,12,380,456],runtime_installed=False))
    else:
        source=OUT/'seed/portrait-seed-x4.png';name=upload(source)
        g={
          '1':node('LoadImage',image=name),
          '2':node('ImageScale',image=['1',0],upscale_method='lanczos',width=1600,height=1920,crop='disabled'),
          '3':node('UNETLoader',unet_name='qwen_image_2.1_int8_convrot.safetensors',weight_dtype='default'),
          '4':node('CLIPLoader',clip_name='qwen3vl_8b_int8_convrot.safetensors',type='qwen_image',device='default'),
          '5':node('VAELoader',vae_name='qwen_image_2.1_vae_bf16.safetensors'),
          '6':node('QwenImage21Cache',model=['3',0],device='cpu',dtype='default'),
          '7':node('TextEncodeQwenImage21',clip=['4',0],prompt=PROMPT,negative_prompt='',vae=['5',0],resolution=0,**{'images.image_1':['2',0]}),
          '8':node('KSampler',model=['6',0],positive=['7',0],negative=['7',1],latent_image=['7',2],seed=14112026,steps=25,cfg=1.0,sampler_name='euler',scheduler='simple',denoise=1.0),
          '9':node('VAEDecodeTiled',samples=['8',0],vae=['5',0],tile_size=512,overlap=128,temporal_size=4096,temporal_overlap=8),
          '10':node('SaveImage',images=['9',0],filename_prefix=prefix+'/portrait-seed-qwen'),
          '11':node('ImageScale',image=['9',0],upscale_method='lanczos',width=1800,height=2160,crop='disabled'),
          '12':node('SaveImage',images=['11',0],filename_prefix=prefix+'/portrait-menu-size')}
        save(folder/'source.json',dict(path=str(source),sha256=sha(source),working=[1600,1920],final=[1800,2160],prompt=PROMPT))
    wf=helpers.workflow(g,schemas);wf['extra']['notes']='Menu portrait: sequential SeedVR2 then Qwen21. Experiment only.'
    save(folder/'prompt-api.json',g);save(folder/'workflow.json',wf)
    helpers.idle()
    result=helpers.req('/prompt',dict(prompt=g,client_id='menu-'+uuid.uuid4().hex,extra_data={'extra_pnginfo':{'workflow':wf}}))
    save(folder/'run.json',result);print(json.dumps(result),flush=True)
def collect(stage):
    folder=OUT/stage;pid=json.loads((folder/'run.json').read_text())['prompt_id'];history=helpers.req('/history/'+pid)
    if pid not in history: print('RUNNING '+pid);return
    job=history[pid];save(folder/'history.json',job)
    if job['status']['status_str']!='success': raise RuntimeError(job['status'])
    outputs={'12':'portrait-seed-x4.png','13':'original-portrait.png','14':'lanczos-x4.png'} if stage=='seed' else {'10':'portrait-seed-qwen.png','12':'portrait-menu-size.png'}
    results=[]
    for nid,name in outputs.items():
        record=job['outputs'][nid]['images'][0]
        with urllib.request.urlopen(helpers.BASE+'/view?'+urllib.parse.urlencode(record),timeout=60) as r: (folder/name).write_bytes(r.read())
        im=Image.open(folder/name);results.append(dict(file=name,size=list(im.size),mode=im.mode,sha256=sha(folder/name)))
    save(folder/'result.json',dict(status='completed-for-review',prompt_id=pid,files=results,runtime_installed=False));print(json.dumps(results),flush=True)
def compare():
    paths=[OUT/'seed/original-portrait.png',OUT/'seed/portrait-seed-x4.png',OUT/'qwen/portrait-menu-size.png']
    labels=['Original','SeedVR2 x4','SeedVR2 -> Qwen 2.1']
    canvas=Image.new('RGB',(1500,650),(26,29,27));draw=ImageDraw.Draw(canvas);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',23)
    for i,(p,label) in enumerate(zip(paths,labels)):
        im=Image.open(p).convert('RGB').resize((500,600),Image.Resampling.NEAREST if i==0 else Image.Resampling.LANCZOS)
        canvas.paste(im,(i*500,50));draw.text((i*500+12,12),label,font=font,fill='white')
    canvas.save(OUT/'comparison.png');print(str(OUT/'comparison.png'))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['submit','collect','compare']);p.add_argument('stage',nargs='?',choices=['seed','qwen']);a=p.parse_args()
    compare() if a.action=='compare' else (submit(a.stage) if a.action=='submit' else collect(a.stage))
