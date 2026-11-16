"""ComfyUI-only final alpha/crop/scale, lossless packing, and QA sheets."""
from pathlib import Path
import argparse, importlib.util, json, struct, shutil, uuid, urllib.request, urllib.parse
from PIL import Image, ImageDraw, ImageFont
import numpy as np
spec=importlib.util.spec_from_file_location('ammo',Path(__file__).with_name('ammo.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def prepare(key,threshold,crop):
    src=m.BASE/key/'qwen';out=m.ROOT/('assets/hd/inventory/'+key+'/v1')
    if (src/'postprocess-run.json').exists():raise RuntimeError('Already submitted; collect.')
    raw=Image.open(src/'raw.png').convert('RGBA');a=np.array(raw)[:,:,3]
    x,y,w,h=crop;outside=a>threshold;outside[y:y+h,x:x+w]=False
    assert not outside.any(),f'Crop excludes {outside.sum()} visible pixels; inspect framing.'
    assert x>=0 and y>=0 and x+w<=raw.width and y+h<=raw.height
    native=m.ITEMS[key]['size'];assert abs(w/h-native[0]/native[1])/(native[0]/native[1])<0.001,'Preserve source aspect ratio within pixel rounding (0.1%)'
    m.h.idle();name=m.upload(src/'raw.png');token=uuid.uuid4().hex;prefix='fallout1_stimpak/'+key+'/final/'+token
    def n(kind,**inputs):return dict(class_type=kind,inputs=inputs)
    graph={'1':n('LoadImage',image=name),'2':n('InvertMask',mask=['1',1]),
      '3':n('ThresholdMask',mask=['2',0],value=threshold/255),
      '4':n('MaskComposite',destination=['2',0],source=['3',0],x=0,y=0,operation='multiply'),
      '5':n('InvertMask',mask=['4',0]),'6':n('JoinImageWithAlpha',image=['1',0],alpha=['5',0]),
      '7':n('ImageCrop',image=['6',0],width=w,height=h,x=x,y=y),
      '8':n('ImageScale',image=['7',0],upscale_method='lanczos',width=native[0]*4,height=native[1]*4,crop='disabled'),
      '9':n('SaveImage',images=['8',0],filename_prefix=prefix+'/stimpak-hd-x4'),
      '10':n('SaveImage',images=['6',0],filename_prefix=prefix+'/master')}
    wf=m.h.workflow(graph,m.h.req('/object_info'));wf['extra']={'notes':'Selected Stimpak alpha, crop and scale'}
    m.save(src/'postprocess-api.json',graph);m.save(src/'postprocess-workflow.json',wf)
    m.save(src/'postprocess-plan.json',dict(threshold=threshold,crop=crop,opaque_pixels_clipped=0,target=[v*4 for v in native]))
    m.save(src/'postprocess-run.json',m.h.req('/prompt',dict(prompt=graph,client_id='ammo-post-'+token,extra_data={'extra_pnginfo':{'workflow':wf}})))
    print('Submitted final processing: '+key)

def collect(key):
    src=m.BASE/key/'qwen';out=m.ROOT/('assets/hd/inventory/'+key+'/v1')
    pid=json.loads((src/'postprocess-run.json').read_text())['prompt_id'];history=m.h.req('/history/'+pid)
    if pid not in history:print('RUNNING');return
    job=history[pid];assert job['status']['status_str']=='success';m.save(src/'postprocess-history.json',job)
    out.mkdir(parents=True,exist_ok=True)
    for node,name in [('9','stimpak-hd-x4.png'),('10','master.png')]:
        rec=job['outputs'][node]['images'][0]
        with urllib.request.urlopen(m.h.BASE+'/view?'+urllib.parse.urlencode(rec),timeout=30) as response:(out/name).write_bytes(response.read())
    plan=json.loads((src/'postprocess-plan.json').read_text());im=Image.open(out/'stimpak-hd-x4.png');raw=Image.open(out/'master.png')
    assert im.mode=='RGBA' and list(im.size)==plan['target']
    a=np.array(raw)[:,:,3];x,y,w,h=plan['crop'];outside=a>0;outside[y:y+h,x:x+w]=False;assert not outside.any()
    header=struct.pack('<4sIIII',b'F1HD',1,im.width,im.height,4);(out/'stimpak.rgba').write_bytes(header+im.tobytes())
    assert (out/'stimpak.rgba').read_bytes()[20:]==im.tobytes()
    shutil.copyfile(m.BASE/key/'source/source.json',out/'source.json')
    for name in ['workflow.json','prompt-api.json','prompt.txt','plan.json','run.json','result.json','postprocess-api.json','postprocess-workflow.json','postprocess-plan.json','postprocess-run.json']:
        shutil.copyfile(src/name,out/name)
    m.save(out/'manifest.json',dict(status='selected_for_integration',item=m.ITEMS[key],source_generation=str(src.relative_to(m.ROOT)),
       final_processing=plan,format='F1HD RGBA8; exact selected PNG bytes',original_fallback='Original DAT FRM; no loose overrides',
       files={p.name:m.h.sha(p) for p in out.iterdir() if p.is_file() and p.name!='manifest.json'}))
    print('Packed '+str(out))

def compare():
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',19)
    sheet=Image.new('RGB',(1140,330),(34,38,38));d=ImageDraw.Draw(sheet)
    edge=Image.new('RGB',(760,310));ed=ImageDraw.Draw(edge)
    for row,(key,item) in enumerate(m.ITEMS.items()):
        size=tuple(v*4 for v in item['size']);src=m.BASE/key
        chosen=m.ROOT/('assets/hd/inventory/'+key+'/v1/stimpak-hd-x4.png')
        pictures=[Image.open(src/'source/native.png').convert('RGBA').resize(size,Image.Resampling.NEAREST),Image.open(src/'seed/candidate.png'),Image.open(chosen if chosen.exists() else src/'qwen/candidate.png')]
        for col,(im,label) in enumerate(zip(pictures,['Original x4','SeedVR2 x4','Qwen x4'])):
            d.text((col*380+24,row*330+12),item['name']+' / '+label,font=font,fill='white');sheet.paste(im,(col*380+24,row*330+60),im)
        for col,bg in enumerate([(20,22,22),(223,220,211)]):
            ed.rectangle((col*380,row*310,(col+1)*380,(row+1)*310),fill=bg)
            edge.paste(pictures[-1],(col*380+24,row*310+40),pictures[-1])
    sheet.save(m.BASE/'comparison.png');edge.save(m.BASE/'alpha-review.png')
    print(m.BASE/'comparison.png')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','collect','compare']);p.add_argument('--item',choices=m.ITEMS);p.add_argument('--threshold',type=int,default=15);p.add_argument('--crop',type=int,nargs=4);a=p.parse_args()
    if a.action=='prepare':prepare(a.item,a.threshold,a.crop)
    elif a.action=='collect':collect(a.item)
    else:compare()
