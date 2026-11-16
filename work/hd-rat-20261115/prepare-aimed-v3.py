"""Restore the complete Qwen wireframe body and preserve original UI callouts."""
from pathlib import Path
import importlib.util
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
s=importlib.util.spec_from_file_location('rat_pipeline',Path(__file__).with_name('pipeline.py'))
p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
panel=next(v for v in p.read(p.OUT/'panels.json') if v['id']=='na-p00');r=panel['slots'][0]
native=Image.open(p.OUT/'source/frames/u0373.png').convert('RGBA');a=np.array(native)
line=np.all(a[:,:,:3]==a[14,0,:3],axis=2)
protected=Image.fromarray((line*255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))
mask=Image.new('L',native.size);ImageDraw.Draw(mask).rectangle((18,70,159,163),fill=255)
mask=Image.fromarray(np.where(np.array(protected)>0,0,np.array(mask)).astype(np.uint8))
maskpath=p.OUT/'source/aimed-body-mask-v3-native.png';mask.save(maskpath)
p.save(p.OUT/'source/aimed-mask-v3.json',dict(method='Complete wireframe-body region, original callout palette colour plus one native pixel margin protected.',
    body_rectangle=[18,70,159,163],callout_rgb=a[14,0,:3].tolist(),background_rgb=a[0,0,:3].tolist(),
    wireframe_rgb=[60,248,0],wireframe_green_gain=2,editable_native_pixels=int((np.array(mask)>0).sum()),mask_sha256=p.sha(maskpath)))
d=p.OUT/'prepared-aimed-v3/na-p00';g={};outputs={}
def add(kind,**kw):
    key=str(len(g)+1);g[key]=p.node(kind,**kw);return [key,0]
def load(path):return add('LoadImage',image=p.upload(path))
def resize(im,w,h):return add('ImageScale',image=im,upscale_method='nearest-exact',width=w,height=h,crop='disabled')
original=load(p.OUT/'source/frames/u0373.png')
base=resize(original,680,900)
donor=load(p.OUT/'qwen/na-p00/qwen.png')
donor=add('ImageCrop',image=donor,x=r['x'],y=r['y'],width=680,height=900)
green=add('ImageToMask',image=donor,channel='green')
gain=add('MaskComposite',destination=green,source=green,x=0,y=0,operation='add')
background=add('EmptyImage',width=680,height=900,batch_size=1,color=0x040C00)
wire=add('EmptyImage',width=680,height=900,batch_size=1,color=0x3CF800)
wire=add('ImageCompositeMasked',destination=background,source=wire,x=0,y=0,resize_source=False,mask=gain)
edit=add('ImageToMask',image=resize(load(maskpath),680,900),channel='red')
mixed=add('ImageCompositeMasked',destination=base,source=wire,x=0,y=0,resize_source=False,mask=edit)
alpha=add('ImageToMask',image=resize(add('MaskToImage',mask=[original[0],1]),680,900),channel='red')
rgba=add('JoinImageWithAlpha',image=mixed,alpha=alpha)
out=add('SaveImage',images=rgba,filename_prefix='fallout1_rat/aimed-v3/u0373');outputs[out[0]]='u0373.png'
p.execute(d,g,outputs)
p.save(p.OUT/'selection.json',dict(images={'u0373':'prepared-aimed-v3/na-p00/u0373.png'},
    aimed_validation_mask='source/aimed-body-mask-v3-native.png',reason='Whole Qwen wireframe instead of patchwork; original UI rays and outer canvas exact.'))
