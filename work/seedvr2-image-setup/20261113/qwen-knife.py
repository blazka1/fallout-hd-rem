"""Task-local Qwen Image 2.1 restoration of the verified Knife inventory icon."""
from pathlib import Path
import argparse, importlib.util, json, time, uuid, urllib.request, urllib.parse, hashlib
from PIL import Image, ImageDraw, ImageFont
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'assets/generated/inventory-knife/qwen21-x4-20261113'
SOURCE=ROOT/'assets/generated/inventory-knife/seedvr2-x4-20261113'
spec=importlib.util.spec_from_file_location('seed_helpers',Path(__file__).with_name('knife-upscale.py'))
helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)
PROMPT=(
    'Restore this exact Fallout 1 inventory icon as a detailed prerendered 2D game asset. '
    'It is one broad steel knife, with its blade tip pointing left and slightly down, '
    'and a dark brown handle extending to the upper right. Preserve the exact blade profile, '
    'tip shape, blade length, guard, handle outline, orientation, proportions, position and framing. '
    'Replace pixel dithering with readable restrained worn steel, subtle sharpening marks and a '
    'weathered brown grip. Keep the original muted grey and brown palette and lighting direction. '
    'Retain the recognizable late-1990s Fallout prerendered inventory style. '
    'Do not redesign the knife, change its angle, add serrations, engravings, lettering or ornaments. '
    'Keep the surrounding empty area transparent, including the existing transparent margins. '
    'No extra objects, background, scene, hands, pedestal or cast shadow.'
)

def save(name,value):
    (OUT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def prepare_submit():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'run.json').exists(): raise RuntimeError('Already submitted; collect the saved run.')
    helpers.idle()
    native=Image.open(SOURCE/'knife-native.png').convert('RGBA')
    assert native.size==(88,33)
    # Explicit padding, no aspect-ratio distortion. A 12x working image has
    # 1152x576 dimensions, divisible by Qwen21's 32-pixel grid.
    canvas=Image.new('RGBA',(96,48),(0,0,0,0));canvas.paste(native,(4,7))
    canvas.save(OUT/'source-padded.png')
    (OUT/'source-native.png').write_bytes((SOURCE/'knife-native.png').read_bytes())
    (OUT/'source.json').write_bytes((SOURCE/'source.json').read_bytes())
    schemas=helpers.req('/object_info')
    models={'unet':'qwen_image_2.1_int8_convrot.safetensors','clip':'qwen3vl_8b_int8_convrot.safetensors','vae':'qwen_image_2.1_vae_bf16.safetensors'}
    for key,node,field in [('unet','UNETLoader','unet_name'),('clip','CLIPLoader','clip_name'),('vae','VAELoader','vae_name')]:
        assert models[key] in schemas[node]['input']['required'][field][0]
    image_name=helpers.upload(OUT/'source-padded.png')
    token=uuid.uuid4().hex; prefix='fallout1_qwen21_knife/'+token
    def n(kind,**inputs):return {'class_type':kind,'inputs':inputs}
    graph={
        '1':n('LoadImage',image=image_name),
        '2':n('JoinImageWithAlpha',image=['1',0],alpha=['1',1]),
        '3':n('ImageScale',image=['2',0],upscale_method='lanczos',width=1152,height=576,crop='disabled'),
        '4':n('UNETLoader',unet_name=models['unet'],weight_dtype='default'),
        '5':n('CLIPLoader',clip_name=models['clip'],type='qwen_image',device='default'),
        '6':n('VAELoader',vae_name=models['vae']),
        '7':n('QwenImage21Cache',model=['4',0],device='cpu',dtype='default'),
        '8':n('TextEncodeQwenImage21',clip=['5',0],prompt=PROMPT,negative_prompt='',vae=['6',0],resolution=0,**{'images.image_1':['3',0]}),
        '9':n('KSampler',model=['7',0],positive=['8',0],negative=['8',1],latent_image=['8',2],seed=13112026,steps=25,cfg=1.0,sampler_name='euler',scheduler='simple',denoise=1.0),
        '10':n('VAEDecode',samples=['9',0],vae=['6',0]),
        '11':n('SaveImage',images=['10',0],filename_prefix=prefix+'/knife-qwen21-raw'),
        '12':n('SaveImage',images=['3',0],filename_prefix=prefix+'/reference-working'),
        '13':n('ImageCrop',image=['10',0],width=1056,height=396,x=48,y=84),
        '14':n('ImageScale',image=['13',0],upscale_method='lanczos',width=352,height=132,crop='disabled'),
        '15':n('SaveImage',images=['14',0],filename_prefix=prefix+'/knife-qwen21-x4'),
    }
    wf=helpers.workflow(graph,schemas)
    save('prompt-api.json',graph);save('workflow.json',wf)
    (OUT/'prompt.txt').write_text(PROMPT+'\n',encoding='utf-8')
    save('plan.json',dict(models=models,native=[88,33],padding_native=[4,7,4,8],working=[1152,576],working_scale=12,target=[352,132],seed=13112026,steps=25,cfg=1,sampler='euler',scheduler='simple',denoise=1,source_sha256=helpers.sha(OUT/'source-native.png'),alpha='Native Qwen-generated alpha retained; no forced source mask',prefix=prefix))
    helpers.idle()
    try:
        result=helpers.req('/prompt',dict(prompt=graph,client_id='qwen21-knife-'+token,extra_data={'extra_pnginfo':{'workflow':wf}}))
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
        print('Waiting for Qwen knife '+prompt_id,flush=True);time.sleep(20)
    job=history[prompt_id];save('history.json',job)
    if job['status']['status_str']!='success':raise RuntimeError(job['status'])
    for node,name in [('11','knife-qwen21-raw.png'),('12','reference-working.png'),('15','knife-qwen21-x4.png')]:
        record=job['outputs'][node]['images'][0]
        with urllib.request.urlopen(helpers.BASE+'/view?'+urllib.parse.urlencode(record),timeout=30) as response:
            (OUT/name).write_bytes(response.read())
    result=Image.open(OUT/'knife-qwen21-x4.png');raw=Image.open(OUT/'knife-qwen21-raw.png')
    assert result.mode=='RGBA' and result.size==(352,132) and raw.size==(1152,576)
    a=np.array(result)[:,:,3];assert a.min()==0 and a.max()>200
    ref=Image.open(SOURCE/'knife-lanczos-x4.png').convert('RGBA')
    ma=np.array(ref)[:,:,3]>=128;mb=a>=128
    events=dict(job['status']['messages'])
    elapsed=(events['execution_success']['timestamp']-events['execution_start']['timestamp'])/1000
    save('result.json',dict(status='completed_for_visual_review',output_size=list(result.size),mode=result.mode,elapsed_seconds=elapsed,alpha_min=int(a.min()),alpha_max=int(a.max()),mask_iou_diagnostic=float((ma&mb).sum()/max(1,(ma|mb).sum())),output_sha256=helpers.sha(OUT/'knife-qwen21-x4.png'),prompt_id=prompt_id,integration='not_installed'))
    pictures=[Image.open(SOURCE/'knife-native.png').convert('RGBA').resize((352,132),Image.Resampling.NEAREST),Image.open(SOURCE/'knife-seedvr2-x4.png').convert('RGBA'),result]
    labels=['Оригинал ×4','SeedVR2 3B INT8 ×4','Qwen Image 2.1 → ×4']
    preview=Image.new('RGB',(1200,222),(34,38,38));d=ImageDraw.Draw(preview);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
    for i,(im,label) in enumerate(zip(pictures,labels)):
        d.text((i*400+14,14),label,font=font,fill=(226,224,211));preview.paste(im,(i*400+24,60),im)
    preview.save(OUT/'comparison.png')
    print((OUT/'result.json').read_text(),flush=True)

def finish():
    # Qwen expanded the source outline slightly. Retain the raw result and
    # the exact-registration crop, then widen the viewing crop by 16/6 pixels
    # per side without changing its aspect ratio or cutting opaque pixels.
    original=OUT/'knife-qwen21-x4-exact-crop.png'
    if not original.exists():original.write_bytes((OUT/'knife-qwen21-x4.png').read_bytes())
    raw=Image.open(OUT/'knife-qwen21-raw.png');a=np.array(raw)[:,:,3]
    mask=a>=128;outside=mask.copy();outside[78:486,32:1120]=False
    assert not outside.any()
    if (OUT/'postprocess-run.json').exists():
        run=json.loads((OUT/'postprocess-run.json').read_text())
    else:
        helpers.idle();name=helpers.upload(OUT/'knife-qwen21-raw.png')
        def n(kind,**inputs):return {'class_type':kind,'inputs':inputs}
        graph={'1':n('LoadImage',image=name),'2':n('JoinImageWithAlpha',image=['1',0],alpha=['1',1]),
            '3':n('ImageCrop',image=['2',0],width=1088,height=408,x=32,y=78),
            '4':n('ImageScale',image=['3',0],upscale_method='lanczos',width=352,height=132,crop='disabled'),
            '5':n('SaveImage',images=['4',0],filename_prefix='fallout1_qwen21_knife/'+uuid.uuid4().hex+'/knife-qwen21-x4-framed')}
        save('postprocess-api.json',graph)
        run=helpers.req('/prompt',dict(prompt=graph,client_id='qwen21-knife-framing-'+uuid.uuid4().hex));save('postprocess-run.json',run)
    while True:
        history=helpers.req('/history/'+run['prompt_id'])
        if run['prompt_id'] in history:break
        time.sleep(1)
    job=history[run['prompt_id']];save('postprocess-history.json',job)
    assert job['status']['status_str']=='success'
    record=job['outputs']['5']['images'][0]
    with urllib.request.urlopen(helpers.BASE+'/view?'+urllib.parse.urlencode(record),timeout=30) as response:(OUT/'knife-qwen21-x4.png').write_bytes(response.read())
    result=Image.open(OUT/'knife-qwen21-x4.png');assert result.mode=='RGBA' and result.size==(352,132)
    # A reproducible complete graph is included separately from the executed
    # generation graph, whose recorded API prompt remains untouched.
    graph=json.loads((OUT/'prompt-api.json').read_text());graph['13']['inputs'].update(width=1088,height=408,x=32,y=78)
    save('prompt-api-framed.json',graph)
    if not (OUT/'workflow-generation.json').exists():(OUT/'workflow-generation.json').write_bytes((OUT/'workflow.json').read_bytes())
    save('workflow.json',helpers.workflow(graph,helpers.req('/object_info')))
    info=json.loads((OUT/'result.json').read_text());info.update(status='reviewed_comparison_candidate',output_sha256=helpers.sha(OUT/'knife-qwen21-x4.png'),raw_opaque_pixels_cut_by_final_crop=0,final_crop_xywh=[32,78,1088,408],exact_registration_crop='knife-qwen21-x4-exact-crop.png',visual_note='Qwen changes blade and guard design; slight reframing avoids clipping expanded generated edges.')
    ref=np.array(Image.open(SOURCE/'knife-lanczos-x4.png'))[:,:,3]>=128;b=np.array(result)[:,:,3]>=128
    info['final_mask_iou_diagnostic']=float((ref&b).sum()/max(1,(ref|b).sum()));save('result.json',info)
    pictures=[Image.open(SOURCE/'knife-native.png').convert('RGBA').resize((352,132),Image.Resampling.NEAREST),Image.open(SOURCE/'knife-seedvr2-x4.png').convert('RGBA'),result]
    preview=Image.new('RGB',(1200,222),(34,38,38));d=ImageDraw.Draw(preview);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
    for i,(im,label) in enumerate(zip(pictures,['Оригинал ×4','SeedVR2 3B INT8 ×4','Qwen Image 2.1 → ×4'])):
        d.text((i*400+14,14),label,font=font,fill=(226,224,211));preview.paste(im,(i*400+24,60),im)
    preview.save(OUT/'comparison.png')
    light=Image.new('RGB',(400,180),(235,235,225));light.paste(result,(24,24),result);light.save(OUT/'light-background.png')
    print('Framed Qwen output: 352x132, no opaque source pixels cropped.',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['submit','collect','finish']);a=p.parse_args()
    {'submit':prepare_submit,'collect':collect,'finish':finish}[a.action]()
