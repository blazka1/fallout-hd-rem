"""Task-local Qwen Image 2.1 restoration of the verified Brass Knuckles inventory icon."""
from pathlib import Path
import argparse, importlib.util, json, time, uuid, urllib.request, urllib.parse, hashlib
from PIL import Image, ImageDraw, ImageFont
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'assets/generated/inventory-brass-knuckles/qwen21-x4-20261113'
SOURCE=ROOT/'assets/generated/inventory-brass-knuckles/seedvr2-x4-20261113'
spec=importlib.util.spec_from_file_location('seed_helpers',Path(__file__).with_name('seed-knuckles.py'))
helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)
PROMPT='Restore this exact Fallout 1 brass knuckles inventory icon as a detailed prerendered 2D game asset. Preserve the original silhouette, oblique isometric projection, position, proportions and framing. Exactly four rounded finger holes form the curved lower-right row, with one broad solid palm brace across the upper-left back. Preserve all four empty transparent finger holes, the visible thickness of their rounded steel rims and the long flat back brace. The Fallout item is hardened steel: use dark worn steel with muted warm brown patina, tiny scratches, restrained edge highlights and subtle surface pitting. Keep the original warm upper-left lighting and late-1990s Fallout appearance. Remove pixel dithering and reveal coherent metal detail without changing the geometry. Keep a single connected intact piece with smooth forged contours. No spikes, blades, extra holes, extra parts, logos, inscriptions, hands, background, pedestal, scene or cast shadow. Do not make shiny yellow gold or polished brass. One item only. Preserve transparent background and generous clear margins. All item pixels must stay within the reference item area.'

def save(name,value):
    (OUT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def prepare_submit():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'run.json').exists(): raise RuntimeError('Already submitted; collect the saved run.')
    helpers.idle()
    native=Image.open(SOURCE/'knuckles-native.png').convert('RGBA')
    assert native.size==(81,65)
    # Explicit padding, no aspect-ratio distortion. A 12x working image has
    # 1152x960 dimensions, divisible by Qwen21's 32-pixel grid.
    canvas=Image.new('RGBA',(96,80),(0,0,0,0));canvas.paste(native,(7,7))
    canvas.save(OUT/'source-padded.png')
    (OUT/'source-native.png').write_bytes((SOURCE/'knuckles-native.png').read_bytes())
    (OUT/'source.json').write_bytes((SOURCE/'source.json').read_bytes())
    schemas=helpers.req('/object_info')
    models={'unet':'qwen_image_2.1_int8_convrot.safetensors','clip':'qwen3vl_8b_int8_convrot.safetensors','vae':'qwen_image_2.1_vae_bf16.safetensors'}
    for key,node,field in [('unet','UNETLoader','unet_name'),('clip','CLIPLoader','clip_name'),('vae','VAELoader','vae_name')]:
        assert models[key] in schemas[node]['input']['required'][field][0]
    image_name=helpers.upload(OUT/'source-padded.png')
    token=uuid.uuid4().hex; prefix='fallout1_qwen21_knuckles/'+token
    def n(kind,**inputs):return {'class_type':kind,'inputs':inputs}
    graph={
        '1':n('LoadImage',image=image_name),
        '2':n('JoinImageWithAlpha',image=['1',0],alpha=['1',1]),
        '3':n('ImageScale',image=['2',0],upscale_method='lanczos',width=1152,height=960,crop='disabled'),
        '4':n('UNETLoader',unet_name=models['unet'],weight_dtype='default'),
        '5':n('CLIPLoader',clip_name=models['clip'],type='qwen_image',device='default'),
        '6':n('VAELoader',vae_name=models['vae']),
        '7':n('QwenImage21Cache',model=['4',0],device='cpu',dtype='default'),
        '8':n('TextEncodeQwenImage21',clip=['5',0],prompt=PROMPT,negative_prompt='',vae=['6',0],resolution=0,**{'images.image_1':['3',0]}),
        '9':n('KSampler',model=['7',0],positive=['8',0],negative=['8',1],latent_image=['8',2],seed=13112026,steps=25,cfg=1.0,sampler_name='euler',scheduler='simple',denoise=1.0),
        '10':n('VAEDecode',samples=['9',0],vae=['6',0]),
        '11':n('SaveImage',images=['10',0],filename_prefix=prefix+'/knuckles-qwen21-raw'),
        '12':n('SaveImage',images=['3',0],filename_prefix=prefix+'/reference-working'),
        '13':n('ImageCrop',image=['10',0],width=972,height=780,x=84,y=84),
        '14':n('ImageScale',image=['13',0],upscale_method='lanczos',width=324,height=260,crop='disabled'),
        '15':n('SaveImage',images=['14',0],filename_prefix=prefix+'/knuckles-qwen21-x4'),
    }
    wf=helpers.workflow(graph,schemas)
    save('prompt-api.json',graph);save('workflow.json',wf)
    (OUT/'prompt.txt').write_text(PROMPT+'\n',encoding='utf-8')
    save('plan.json',dict(models=models,native=[81,65],padding_native=[7,7,8,8],working=[1152,960],working_scale=12,target=[324,260],seed=13112026,steps=25,cfg=1,sampler='euler',scheduler='simple',denoise=1,source_sha256=helpers.sha(OUT/'source-native.png'),alpha='Native Qwen-generated alpha retained; no forced source mask',prefix=prefix))
    helpers.idle()
    try:
        result=helpers.req('/prompt',dict(prompt=graph,client_id='qwen21-knuckles-'+token,extra_data={'extra_pnginfo':{'workflow':wf}}))
    except urllib.error.HTTPError as error:
        details=error.read().decode();(OUT/'validation-error.json').write_text(details,encoding='utf-8')
        raise RuntimeError(details) from error
    save('run.json',result)
    if result.get('node_errors'):raise RuntimeError(result)
    print(json.dumps(result),flush=True)

def collect():
    prompt_id=json.loads((OUT/'run.json').read_text())['prompt_id']
    start=time.monotonic()
    while True:
        history=helpers.req('/history/'+prompt_id)
        if prompt_id in history:break
        if time.monotonic()-start>3600:raise TimeoutError('Resume collect; do not resubmit.')
        print('Waiting for Qwen knuckles '+prompt_id,flush=True);time.sleep(20)
    job=history[prompt_id];save('history.json',job)
    if job['status']['status_str']!='success':raise RuntimeError(job['status'])
    for node,name in [('11','knuckles-qwen21-raw.png'),('12','reference-working.png'),('15','knuckles-qwen21-x4.png')]:
        record=job['outputs'][node]['images'][0]
        with urllib.request.urlopen(helpers.BASE+'/view?'+urllib.parse.urlencode(record),timeout=30) as response:
            (OUT/name).write_bytes(response.read())
    result=Image.open(OUT/'knuckles-qwen21-x4.png');raw=Image.open(OUT/'knuckles-qwen21-raw.png')
    assert result.mode=='RGBA' and result.size==(324,260) and raw.size==(1152,960)
    a=np.array(result)[:,:,3];assert a.min()==0 and a.max()>200
    ref=Image.open(SOURCE/'knuckles-lanczos-x4.png').convert('RGBA')
    ma=np.array(ref)[:,:,3]>=128;mb=a>=128
    events=dict(job['status']['messages'])
    elapsed=(events['execution_success']['timestamp']-events['execution_start']['timestamp'])/1000
    save('result.json',dict(status='completed_for_visual_review',output_size=list(result.size),mode=result.mode,elapsed_seconds=elapsed,alpha_min=int(a.min()),alpha_max=int(a.max()),mask_iou_diagnostic=float((ma&mb).sum()/max(1,(ma|mb).sum())),output_sha256=helpers.sha(OUT/'knuckles-qwen21-x4.png'),prompt_id=prompt_id,integration='not_installed'))
    pictures=[Image.open(SOURCE/'knuckles-native.png').convert('RGBA').resize((324,260),Image.Resampling.NEAREST),Image.open(SOURCE/'knuckles-seedvr2-x4.png').convert('RGBA'),result]
    labels=['Оригинал ×4','SeedVR2 3B INT8 ×4','Qwen Image 2.1 → ×4']
    preview=Image.new('RGB',(1200,350),(34,38,38));d=ImageDraw.Draw(preview);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
    for i,(im,label) in enumerate(zip(pictures,labels)):
        d.text((i*400+14,14),label,font=font,fill=(226,224,211));preview.paste(im,(i*400+24,60),im)
    preview.save(OUT/'comparison.png')
    print((OUT/'result.json').read_text(),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['submit','collect']);a=p.parse_args();{'submit':prepare_submit,'collect':collect}[a.action]()
