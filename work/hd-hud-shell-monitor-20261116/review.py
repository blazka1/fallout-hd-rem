"""Prepare protected UI masks and visual comparisons for the HUD shell trial."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, urllib.request, urllib.parse, uuid
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('hud_pipeline',HERE/'pipeline.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
ROOT,OUT=p.ROOT,p.OUT
REVIEW=OUT/'review'
# Original HUD-local x,y,w,h; these existing controls are outside this art task.
PROTECTED={
    'inventory':(211,41,32,21),'options':(210,62,34,34),
    'switch_hand':(218,6,22,21),'skilldex_button':(523,7,22,21),
    'map':(526,40,41,19),'character':(526,59,41,19),'pipboy':(526,78,41,19),
    'weapon_surface':(267,26,188,67),'ap_lamps':(315,13,92,7),
    'hp_label_and_counter':(471,27,42,31),'ac_label_and_counter':(471,62,42,31),
    'ammo':(462,26,3,70),'skilldex_plate':(551,3,87,27),'combat_hatch':(580,38,57,58)}

def prepare():
    REVIEW.mkdir(exist_ok=True)
    scale=6
    mask=Image.new('L',(3840,600),255);d=ImageDraw.Draw(mask)
    for x,y,w,h in PROTECTED.values():
        # A one-native-pixel guard preserves the existing edge of each control.
        d.rectangle((max(0,x-1)*scale,max(0,y-1)*scale,min(640,x+w+1)*scale-1,min(100,y+h+1)*scale-1),fill=0)
    # Retain the outermost source pixels exactly; Qwen can refine interior only.
    d.rectangle((0,0,3839,599),outline=0,width=6)
    hard=np.asarray(mask,dtype=np.float32)/255
    soft=np.asarray(mask.filter(ImageFilter.GaussianBlur(3)),dtype=np.float32)/255
    Image.fromarray(np.rint(hard*soft*255).astype('uint8')).save(REVIEW/'shell-mask.png')
    p.save(REVIEW/'protected-regions.json',PROTECTED)
    # An inspection map only; this never enters the image-generation reference.
    overlay=Image.open(OUT/'original.png').convert('RGB').resize((1920,300),Image.Resampling.NEAREST)
    draw=ImageDraw.Draw(overlay)
    for x,y,w,h in PROTECTED.values():draw.rectangle((x*3,y*3,(x+w)*3-1,(y+h)*3-1),outline='#fb9d63',width=2)
    overlay.save(REVIEW/'protected-regions.png')

def submit():
    prepare()
    if (REVIEW/'run.json').exists():raise RuntimeError('Already submitted; collect saved prompt.')
    p.h.idle();schemas=p.h.req('/object_info');prefix='fallout1_hud_shell_monitor/review-'+uuid.uuid4().hex
    src=p.upload(OUT/'original.png');raw=p.upload(OUT/'qwen/qwen-master.png');mask=p.upload(REVIEW/'shell-mask.png')
    seed=p.upload(OUT/'seed/seed-hud.png')
    n=p.n
    g={
      '1':n('LoadImage',image=src),
      '2':n('ImageScale',image=['1',0],upscale_method='lanczos',width=3840,height=600,crop='disabled'),
      '3':n('LoadImage',image=raw),
      '4':n('LoadImageMask',image=mask,channel='red'),
      '5':n('ImageCompositeMasked',destination=['2',0],source=['3',0],x=0,y=0,resize_source=False,mask=['4',0]),
      '6':n('SaveImage',images=['5',0],filename_prefix=prefix+'/shell-monitor-context'),
      '7':n('LoadImage',image=seed),
      '8':n('ImageScale',image=['7',0],upscale_method='lanczos',width=3840,height=600,crop='disabled'),
      '9':n('ImageCompositeMasked',destination=['2',0],source=['8',0],x=0,y=0,resize_source=False,mask=['4',0]),
      '10':n('SaveImage',images=['9',0],filename_prefix=prefix+'/seed-context'),
      '14':n('InvertMask',mask=['4',0]),
      '11':n('JoinImageWithAlpha',image=['3',0],alpha=['14',0]),
      '12':n('SaveImage',images=['11',0],filename_prefix=prefix+'/shell-monitor-layer'),
      '13':n('SaveImage',images=['2',0],filename_prefix=prefix+'/original-lanczos')}
    wf=p.h.workflow(g,schemas);wf['extra']['notes']='Only mask-based compositing; protected original controls remain as preview context. No runtime installation.'
    p.save(REVIEW/'prompt-api.json',g);p.save(REVIEW/'workflow.json',wf)
    p.h.idle();r=p.h.req('/prompt',dict(prompt=g,client_id='hud-review-'+uuid.uuid4().hex,extra_data={'extra_pnginfo':{'workflow':wf}}))
    p.save(REVIEW/'run.json',r);print(json.dumps(r))

def collect():
    pid=json.loads((REVIEW/'run.json').read_text())['prompt_id'];data=p.h.req('/history/'+pid)
    if pid not in data: print('RUNNING '+pid);return
    job=data[pid];p.save(REVIEW/'history.json',job)
    assert job['status']['status_str']=='success',job['status']
    for nid,name in {'6':'shell-monitor-context.png','10':'seed-context.png','12':'shell-monitor-layer.png','13':'original-lanczos.png'}.items():
        rec=job['outputs'][nid]['images'][0]
        with urllib.request.urlopen(p.h.BASE+'/view?'+urllib.parse.urlencode(rec),timeout=30) as r:(REVIEW/name).write_bytes(r.read())
    print('COLLECTED '+pid)

def compare():
    paths=[OUT/'original.png',REVIEW/'seed-context.png',REVIEW/'shell-monitor-context.png']
    labels=['Оригинал Fallout 1','После SeedVR2','SeedVR2 → Qwen 2.1 · корпус и монитор']
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',23)
    small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
    sheet=Image.new('RGB',(1920,1070),'#202326');d=ImageDraw.Draw(sheet)
    for i,(path,label) in enumerate(zip(paths,labels)):
        y=i*345
        d.text((16,y+10),label,font=font,fill='#ecebe3')
        im=Image.open(path).convert('RGB').resize((1920,300),Image.Resampling.NEAREST if i==0 else Image.Resampling.LANCZOS)
        sheet.paste(im,(0,y+42))
    d.text((16,1041),'Превью перед установкой. Кнопки, числа и оружейная площадка сохранены из оригинала для контекста.',font=small,fill='#c5c7c5')
    sheet.save(REVIEW/'comparison-full.png')
    detail=Image.new('RGB',(1800,474),'#202326');d=ImageDraw.Draw(detail)
    for i,(path,label) in enumerate(zip(paths,labels)):
        im=Image.open(path).convert('RGB');sc=im.width/640
        crop=im.crop((0,0,round(209*sc),round(100*sc))).resize((600,287),Image.Resampling.NEAREST if i==0 else Image.Resampling.LANCZOS)
        detail.paste(crop,(i*600,65));d.text((i*600+12,15),label if i<2 else 'SeedVR2 → Qwen 2.1',font=font,fill='#ecebe3')
    d.text((12,375),'Крупный план корпуса монитора; изображение стекла без игровых сообщений.',font=small,fill='#c5c7c5')
    d.text((12,412),'Полный мастер: 3840×600. Художественный кандидат, ещё не подключён к движку.',font=small,fill='#c5c7c5')
    detail.save(REVIEW/'comparison-monitor.png')
    final=np.asarray(Image.open(REVIEW/'shell-monitor-context.png').convert('RGB'))
    baseline=np.asarray(Image.open(REVIEW/'original-lanczos.png').convert('RGB'))
    mask=np.asarray(Image.open(REVIEW/'shell-mask.png'))
    protected=mask==0
    outside_changed=int(np.any(final!=baseline,axis=2)[protected].sum())
    assert outside_changed==0,outside_changed
    layer=Image.open(REVIEW/'shell-monitor-layer.png').convert('RGBA')
    raw_alpha=np.asarray(layer)[:,:,3]
    alpha_error=int(np.abs(raw_alpha.astype('int16')-mask.astype('int16')).max())
    assert alpha_error<=1, 'Unexpected alpha change in Comfy resize_mask.'
    # Comfy's float mask resampling/save can quantize 255 to 254. Packaging
    # restores the prepared mask exactly; generated RGB is retained untouched.
    layer.putalpha(Image.fromarray(mask))
    layer.save(REVIEW/'shell-monitor-layer-exact-alpha.png')
    assert np.array_equal(np.asarray(layer)[:,:,3],mask)
    Image.open(REVIEW/'shell-monitor-context.png').crop((0,0,1254,600)).save(REVIEW/'monitor-candidate.png')
    p.save(REVIEW/'validation.json',dict(status='prepared-for-user-visual-review',master_size=[3840,600],
        original_native=[640,100],protected_pixels=int(protected.sum()),changed_protected_pixels=outside_changed,
        raw_comfy_alpha_quantization_error=alpha_error,packaged_layer_alpha_matches_mask=True,
        note='Mask keeps protected controls and outer boundary exact relative to Lanczos source. Internal material contours still require visual review; Canny is not a pixel-registration guarantee.',
        files=[dict(file=x.name,sha256=p.sha(x)) for x in REVIEW.glob('*.png')],runtime_installed=False))
    print(str(REVIEW/'comparison-full.png'))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','submit','collect','compare']);args=ap.parse_args()
    globals()[args.action]()
