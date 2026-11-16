"""Prepare new-geometry candidates in ComfyUI and make literal QA comparison sheets."""
import json,sys,uuid,shutil
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import numpy as np
import pipeline as p
from new_geometry import GEO,GROUPS

FONT=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',21)
SMALL=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)

def prepare(group):
    name,reference,objects=group;src=GEO/'qwen'/name;dst=GEO/'prepared'/name
    if not (src/'result.json').exists():return
    if (dst/'result.json').exists():return
    if (dst/'run.json').exists():p.execute(dst,{},{});return
    selected=GEO/'selected'/name/'raw.png'
    if not selected.exists():selected=src/'raw.png'
    old=np.array(Image.open(p.OUT/'inputs'/reference/'current-hd.png').convert('RGBA'))
    raw=np.array(Image.open(selected).convert('RGBA'))
    oldmean=old[:,:,:3][old[:,:,3]>200].mean(0);newmean=raw[:,:,:3][raw[:,:,3]>200].mean(0)
    rgb=np.rint(np.clip(oldmean/np.maximum(1,newmean),.4,1)*255).astype(int)
    gain=int(rgb[0]*65536+rgb[1]*256+rgb[2]);prefix='fallout1_cave_variety/new_geometry_prepared/'+uuid.uuid4().hex
    n=p.node
    g={'1':n('LoadImage',image=p.upload(selected)),
       '2':n('EmptyImage',width=1024,height=1024,batch_size=1,color=gain),
       '3':n('ImageBlend',image1=['1',0],image2=['2',0],blend_factor=1.,blend_mode='multiply'),
       '4':n('JoinImageWithAlpha',image=['3',0],alpha=['1',1]),
       '5':n('SaveImage',images=['4',0],filename_prefix=prefix+'/atlas')}
    outputs={'5':'atlas.png'}
    for i,(identifier,desc) in enumerate(objects):
        a=str(6+i*2);b=str(7+i*2)
        g[a]=n('ImageCrop',image=['4',0],x=i%2*512,y=i//2*512,width=512,height=512)
        g[b]=n('SaveImage',images=[a,0],filename_prefix=prefix+'/'+identifier)
        outputs[b]='sprites/'+identifier+'.png'
    p.save(dst/'color-match.json',dict(method='one shared RGB gain per new geometry atlas; compares global opaque material mean, not pixel correspondence',source=str(selected.relative_to(p.OUT)),gain=(rgb/255).tolist(),source_mean=newmean.tolist(),target_mean=oldmean.tolist(),raw_preserved=True,original_alpha_reused=False))
    p.execute(dst,g,outputs)

def composite(im,color):
    bg=Image.new('RGBA',im.size,(*color,255));bg.alpha_composite(im.convert('RGBA'));return bg.convert('RGB')

def silhouette(im):
    a=np.array(im.convert('RGBA'))[:,:,3];mask=Image.fromarray(((a>127)*255).astype('uint8'))
    box=mask.getbbox()
    if box:mask=mask.crop(box)
    mask.thumbnail((112,112),Image.Resampling.NEAREST)
    out=Image.new('L',(128,128));out.paste(mask,((128-mask.width)//2,120-mask.height));return np.array(out)>127

def review():
    qa=GEO/'review';qa.mkdir(parents=True,exist_ok=True)
    refs=[]
    for s in p.read(p.OUT/'source-inventory.json'):
        if s['category']=='scenery':
            im=Image.open(p.OUT/'sources'/(s['source']+'.current.png')).convert('RGBA');refs.append((Path(s['source']).stem,im,silhouette(im)))
    records=[];pictures=[]
    for name,reference,objects in GROUPS:
        rawdir=GEO/'qwen'/name;prep=GEO/'prepared'/name
        if (rawdir/'raw.png').exists():composite(Image.open(rawdir/'raw.png'),(30,34,34)).save(rawdir/'raw-on-dark.png')
        if not (prep/'result.json').exists():continue
        selected=GEO/'selected'/name/'raw.png'
        for index,(identifier,desc) in enumerate(objects):
            if identifier=='geo-rock-08' and selected.exists():desc='Low irregular outcrop of fractured slabs tilted in different directions; replaces the rejected staircase-like initial design.'
            path=prep/'sprites'/(identifier+'.png');im=Image.open(path).convert('RGBA')
            raw=Image.open(selected).convert('RGBA').crop((index%2*512,index//2*512,index%2*512+512,index//2*512+512)) if selected.exists() else Image.open(rawdir/'sprites'/(identifier+'.png')).convert('RGBA')
            alpha=np.array(im)[:,:,3];strong=alpha>127
            box=Image.fromarray((strong*255).astype('uint8')).getbbox();assert box
            mask=silhouette(im);matches=[]
            for stem,_,r in refs:matches.append((float((mask&r).sum()/max(1,(mask|r).sum())),stem))
            score,closest=max(matches)
            samealpha=bool(np.array_equal(alpha,np.array(raw)[:,:,3]))
            alpha_delta=int(np.abs(alpha.astype(int)-np.array(raw)[:,:,3].astype(int)).max())
            assert alpha_delta<=1,(identifier,alpha_delta)
            edge=int(strong[0].sum()+strong[-1].sum()+strong[:,0].sum()+strong[:,-1].sum())
            record=dict(id=identifier,file=str(path.relative_to(p.OUT)),sha256=p.sha(path),description=desc,size=list(im.size),native_canvas_proposal=[128,128],new_generated_alpha=True,original_alpha_reused=False,alpha_unchanged_from_qwen=samealpha,alpha_max_abs_change=alpha_delta,alpha_note='Native Comfy LoadImage/JoinImageWithAlpha float conversion quantizes soft alpha by at most 1/255; original game alpha is never substituted.',opaque_border_pixels=edge,opaque_bbox=list(box),alpha_coverage=float(strong.mean()),
                proposed_anchor_hd=[(box[0]+box[2])//2,box[3]-1],anchor_status='Geometric bottom-center proposal only; verify actual base/contact/footprint in engine before integration',
                closest_normalized_original_silhouette=closest,normalized_silhouette_iou=score,iou_note='Bounding boxes normalized preserving aspect ratio; diagnostic only, does not prove geometry quality',status='new geometry candidate; not installed')
            records.append(record);pictures.append((identifier,im))
    p.save(qa/'geometry-qa.json',dict(count=len(records),records=records,installed=False))
    if not pictures:return
    board=Image.new('RGB',(1536,90+len(pictures)//4*430),(24,28,28));d=ImageDraw.Draw(board)
    d.text((18,15),'НОВЫЕ ФОРМЫ · собственные силуэты и альфа',font=FONT,fill='#e1ddce')
    for i,(identifier,im) in enumerate(pictures):
        x=i%4*384;y=90+i//4*430;d.text((x+12,y+6),identifier,font=FONT,fill='#e1ddce')
        view=im.resize((384,384),Image.Resampling.LANCZOS);board.paste(composite(view,(24,28,28)),(x,y+36))
    board.save(qa/'new-geometry-overview.png')
    # Same uniform alpha visualization for originals and generated forms.
    all_shapes=[(stem,im) for stem,im,_ in refs]+pictures
    cols=6;rows=(len(all_shapes)+cols-1)//cols
    sh=Image.new('RGB',(1536,rows*280+70),(235,233,224));sd=ImageDraw.Draw(sh)
    sd.text((18,16),'СИЛУЭТЫ: сначала 10 исходных, затем новые формы (нормированы по рамке)',font=FONT,fill='#252a28')
    for i,(name,im) in enumerate(all_shapes):
        a=silhouette(im);mask=Image.fromarray((a*255).astype('uint8')).resize((224,224),Image.Resampling.NEAREST)
        x=i%cols*256;y=70+i//cols*280;sd.text((x+8,y+6),name,font=SMALL,fill='#252a28');sh.paste((35,40,38),(x+16,y+35,x+240,y+259),mask)
    sh.save(qa/'silhouette-comparison.png')
    alpha_board=Image.new('RGB',(2048,len(pictures)//4*320),(30,30,30));ad=ImageDraw.Draw(alpha_board)
    for i,(name,im) in enumerate(pictures):
        x=i%4*512;y=i//4*320;ad.text((x+8,y+8),name,font=SMALL,fill='#d8cba8')
        small=im.resize((256,256),Image.Resampling.LANCZOS)
        alpha_board.paste(composite(small,(20,20,20)),(x,y+40));alpha_board.paste(composite(small,(230,230,225)),(x+256,y+40))
    alpha_board.save(qa/'alpha-review.png')
    print(json.dumps({'geometry_candidates':len(records),'border_pixels':sum(r['opaque_border_pixels'] for r in records),'max_alpha_quantization':max(r['alpha_max_abs_change'] for r in records)}))

if __name__=='__main__':
    if '--review-only' not in sys.argv:
        for group in GROUPS:prepare(group)
    review()
