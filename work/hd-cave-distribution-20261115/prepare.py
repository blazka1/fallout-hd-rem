"""Balanced appearance assignment on existing objects; never modifies MAP/FRM."""
from pathlib import Path
import json,hashlib,math,struct
from collections import Counter
from PIL import Image
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'assets/hd/v13ent/cave-distribution-v1'
BUILD=ROOT/'build/hd-cave-distribution-20261115'
SOURCE=ROOT/'assets/generated/v13ent-cave/v1-20261111/sources'
GEN=ROOT/'assets/generated/v13ent-cave-variety/seedvr2-qwen21-20261115/candidate-pack/new-geometry'
SEED=15112026
def save(path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
def rank(*items):return int(hashlib.sha256(('|'.join(map(str,(SEED,)+items))).encode()).hexdigest()[:16],16)
def xy(o):
    row,col=divmod(o['tile'],200)
    return (col+0.5*(row%2),row*math.sqrt(3)/2)
def distance(a,b):
    x,y=xy(a);u,v=xy(b);return (x-u)**2+(y-v)**2
def dispersed(items,count):
    pool=list(items);chosen=[]
    while len(chosen)<count:
        p=max(pool,key=lambda x:(min((distance(x,c) for c in chosen),default=0),rank(x['id'])))
        chosen.append(p);pool.remove(p)
    return chosen

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    resources=json.loads((SOURCE/'manifest.json').read_text())['assets']
    records=json.loads((GEN/'manifest.json').read_text())['records'];art={};types={}
    for i,r in enumerate(records):
        name=r['id'];im=Image.open(GEN/r['file']).convert('RGBA');a=np.array(im)[:,:,3]
        box=Image.fromarray(((a>8)*255).astype('uint8')).getbbox();x,y,u,v=box
        box=[max(0,x-4),max(0,y-4),min(512,u+4),min(512,v+4)]
        asset=224+i;filename=name+'.rgba'
        (OUT/filename).write_bytes(struct.pack('<4sIIII',b'F1HD',1,512,512,4)+im.tobytes())
        art[name]=dict(id=asset,file=filename,box=box,source=str((GEN/r['file']).relative_to(ROOT)),sha256=hashlib.sha256((GEN/r['file']).read_bytes()).hexdigest())
    for r in resources:
        stem=Path(r['path']).stem
        if stem in ['rock%02d'%i for i in range(1,7)]+['cstalag1','cstalag2','cvcolum1','cvcolum2']:
            types[stem]=r
    groups=[('rocks',['rock%02d'%i for i in range(1,7)],['geo-rock-%02d'%i for i in range(1,13)],{**{'rock%02d'%i:6 for i in range(1,7)},**{'geo-rock-%02d'%i:5 if i==9 else 6 for i in range(1,13)}}),
      ('stalagmites',['cstalag1','cstalag2'],['geo-formation-01','geo-formation-02'],{'cstalag1':1,'cstalag2':2,'geo-formation-01':2,'geo-formation-02':2}),
      ('columns',['cvcolum1','cvcolum2'],['geo-formation-03','geo-formation-04'],{'cvcolum1':0,'cvcolum2':1,'geo-formation-03':1,'geo-formation-04':0})]
    assignments=[];summaries=[]
    for group,old,new,quota in groups:
        objects=[dict(o,source=stem,width=types[stem]['width'],height=types[stem]['height']) for stem in old for o in types[stem]['map_instances']]
        assert sum(quota.values())==len(objects)
        kept=[]
        for stem in old:kept+=dispersed([o for o in objects if o['source']==stem],quota[stem])
        keepids={o['id'] for o in kept};remaining=[o for o in objects if o['id'] not in keepids]
        order=dispersed(remaining,len(remaining));placed={n:[] for n in new};available={n:quota[n] for n in new}
        for o in kept:assignments.append(dict(object=o,appearance=o['source'],group=group,new=False))
        for o in order:
            options=[n for n in new if available[n]]
            chosen=max(options,key=lambda n:(min((distance(o,c) for c in placed[n]),default=100000),available[n]/max(1,quota[n]),rank(o['id'],n)))
            placed[chosen].append(o);available[chosen]-=1
            assignments.append(dict(object=o,appearance=chosen,group=group,new=True))
        summaries.append(dict(group=group,places=len(objects),quotas=quota,old=sum(quota[n] for n in old),new=sum(quota[n] for n in new),formula='largest-remainder equal type weights; retain old types only on matching existing objects; columns have only two compatible slots'))
    rows=[]
    for index,item in enumerate(sorted((r for r in assignments if r['new']),key=lambda r:r['object']['id'])):
        o=item['object'];a=art[item['appearance']];x,y,u,v=a['box'];sw,sh=u-x,v-y
        # Preserve aspect ratio. Rocks stay inside the old drawing rectangle.
        # Roof-contact columns retain height; their modest wider bound is tracked by CE.
        factor=(o['height']-2)/sh if item['group']=='columns' else min((o['width']-4)/sw,(o['height']-2)/sh)
        dw=max(1,round(sw*factor));dh=max(1,round(sh*factor));dx=(o['width']-dw)//2;dy=o['height']-dh
        vals=[index,o['id'],o['fid'],o['pid'],o['tile'],o['elevation'],o['x'],o['y'],o['rotation'],a['id'],o['width'],o['height'],x,y,sw,sh,dx,dy,dw,dh]
        rows.append(' '.join(map(str,vals)))
        item.update(index=index,asset_id=a['id'],source_box=[x,y,sw,sh],draw_in_classic_rect=[dx,dy,dw,dh],aspect_ratio_error=abs(dw/dh-sw/sh),bounds_expand=dx<0 or dy<0 or dx+dw>o['width'] or dy+dh>o['height'])
    (OUT/'cave-variety-assets.tsv').write_text('# id width height file\n'+''.join(f"{a['id']} 128 128 {a['file']}\n" for a in art.values()),encoding='utf-8')
    (OUT/'cave-variety-placements.tsv').write_text('# index object_id fid pid tile elevation x y rotation asset_id old_w old_h crop_x crop_y crop_w crop_h draw_x draw_y draw_w draw_h\n'+'\n'.join(rows)+'\n',encoding='utf-8')
    save(OUT/'distribution.json',dict(seed=SEED,placements=len(assignments),changed=len(rows),unchanged=len(assignments)-len(rows),groups=summaries,assets=art,assignments=assignments,
      constraints=['No new game objects or collision','Existing coordinates and original FRM remain unchanged','Old forms kept on original matching FIDs','Distinct stalagmite and roof-column roles','Deterministic farthest-point spacing and equal quotas'],
      unused_geometry='geo-formation-04: only two compatible column positions; keep one original and one new column in this seed'))
    print(json.dumps(dict(placements=len(assignments),changed=len(rows),unchanged=len(assignments)-len(rows),groups=summaries)))
if __name__=='__main__':main()
