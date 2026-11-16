"""Inspectable source masks and working comparisons for sprite retargeting."""
from pipeline import ROOT,OUT,PREV,read,save
from PIL import Image,ImageDraw,ImageFont
import numpy as np
from scipy import ndimage as ndi

def masks(p):
    ind=np.asarray(Image.open(OUT/'inputs'/(p['name']+'-indexed.png')))
    rgba=np.asarray(Image.open(ROOT/p['source']).convert('RGBA'))
    shadow=np.isin(ind,[207] if p['action']=='stand' else [31,47,100])&(np.arange(p['height'])[:,None]>=int(p['height']*.72))
    return (rgba[:,:,3]>0)&~shadow,shadow

def body_alpha(p):
    body,shadow=masks(p)
    return Image.fromarray((body*255).astype('uint8')).resize((p['width']*4,p['height']*4),Image.Resampling.LANCZOS)

def grid(im,step=20):
    im=im.convert('RGBA');bg=Image.new('RGBA',im.size,(145,148,148,255));bg.alpha_composite(im)
    out=bg.resize((im.width*2,im.height*2),Image.Resampling.NEAREST).convert('RGB');d=ImageDraw.Draw(out)
    for x in range(0,im.width,step):d.line((x*2,0,x*2,out.height),fill=(95,135,115));d.text((x*2+2,1),str(x),fill=(255,250,200))
    for y in range(0,im.height,step):d.line((0,y*2,out.width,y*2),fill=(95,135,115));d.text((0,y*2+2),str(y),fill=(255,250,200))
    return out

def inspect():
    dest=OUT/'geometry';dest.mkdir(exist_ok=True)
    plan=read(OUT/'plan.json');raw=Image.open(OUT/'edit-two-references/raw.png').resize((512,768),Image.Resampling.LANCZOS)
    for i,p in enumerate(plan['poses']):
        orig=Image.open(ROOT/p['source']).resize((p['width']*4,p['height']*4),Image.Resampling.NEAREST).convert('RGBA')
        target=Image.new('RGBA',(256,384));target.alpha_composite(orig,(p['x']*4-(i%2)*256,p['y']*4-(i//2)*384))
        src=raw.crop(((i%2)*256,(i//2)*384,(i%2+1)*256,(i//2+1)*384))
        board=Image.new('RGB',(1024,768));board.paste(grid(target),(0,0));board.paste(grid(src),(512,0));board.save(dest/(p['name']+'-grid.png'))
        body,shadow=masks(p)
        Image.fromarray((body*255).astype('uint8')).save(dest/(p['name']+'-body-native.png'))
        Image.fromarray((shadow*255).astype('uint8')).save(dest/(p['name']+'-shadow-native.png'))
    print('Geometry sheets and source masks saved')
if __name__=='__main__':inspect()
