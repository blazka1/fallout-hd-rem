"""Unlit exact-layout QA assemblies from original MAP cells and verified wall placements."""
from pathlib import Path
import json,sys
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,str(Path(__file__).parent))
import pipeline as p
ROOT=p.ROOT;OUT=p.OUT;QA=OUT/'review';QA.mkdir(exist_ok=True)
FONT=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
rows={r['path']:r for r in p.read(p.SOURCE/'manifest.json')['assets']}
registry={}
for line in (p.RUNTIME/'registry.tsv').read_text().splitlines():
    if line and not line.startswith('#'):
        a=line.split();registry.setdefault(int(a[1]),a[4])
cache={}
def current(res):
    if res not in cache:
        r=rows[res];fid=r['fids'][0] if r['fids'] else (4<<24)|r['tile_art_ids'][0]
        cache[res]=p.runtime_image(registry[fid])
    return cache[res]
def floor():
    panel=next(c for c in p.read(OUT/'plan.json')['panels'] if c['id']=='floor')
    if not (OUT/'prepared/floor/result.json').exists():return
    selected={s['source'] for s in panel['slots']};bycell={}
    for res,r in rows.items():
        for c in r['visible_floor_cells']:
            if c['elevation']==0:bycell[c['cell']]=res
    def cells(center):
        row,col=divmod(center,100)
        return [(rr*100+cc,bycell[rr*100+cc]) for rr in range(row-2,row+3) for cc in range(col-2,col+3) if rr*100+cc in bycell]
    center=max((c for c,r in bycell.items() if r in selected),key=lambda c:(len(set(r for _,r in cells(c))&selected),sum(r in selected for _,r in cells(c))))
    entries=cells(center);positions=[]
    for cell,res in entries:
        row,col=divmod(cell,100);positions.append((cell,res,-48*col+32*row,12*col+24*row))
    x0=min(a[2] for a in positions);y0=min(a[3] for a in positions)
    w=max(a[2]+80 for a in positions)-x0;hh=max(a[3]+36 for a in positions)-y0
    canvases=[]
    for variant in ['current','a','b','mix']:
        im=Image.new('RGBA',(w*4,hh*4))
        for cell,res,x,y in positions:
            src=current(res)
            if variant!='current' and res in selected:
                v=('a' if (cell*2654435761)%3 else 'b') if variant=='mix' else variant
                src=Image.open(OUT/'prepared/floor/variants'/f'{Path(res).stem}-{v}.png').convert('RGBA')
            im.paste(src,((x-x0)*4,(y-y0)*4),src)
        canvases.append(im)
    sheet=Image.new('RGB',(w*4*2,(hh*4+60)*2),(23,26,26));d=ImageDraw.Draw(sheet)
    for i,(im,name) in enumerate(zip(canvases,['Текущий пол','Вариант A','Вариант B','Смесь A/B'])):
        x=i%2*w*4;y=i//2*(hh*4+60);d.text((x+12,y+12),name+' · раскладка MAP, без игрового света',font=FONT,fill='#e1ddce');sheet.paste(im,(x,y+60),im)
    sheet.save(QA/'floor-neighbors.png')
    p.save(QA/'floor-neighbors.json',dict(center_cell=center,cells=[dict(cell=c,source=r,x=x,y=y) for c,r,x,y in positions],actual_map_coordinates=True,engine_render=False,lighting='not applied',variant_mix='deterministic illustrative only; not installed'))
def walls():
    for panel in p.read(OUT/'plan.json')['panels']:
        if not panel['id'].startswith('wall'):continue
        name=panel['id'];d=OUT/'prepared'/name
        if not (d/'result.json').exists():continue
        selected={s['source'] for s in panel['slots']};c=panel['context'];box=c['box_native']
        sheet=Image.new('RGB',(2400,3*(800+52)),(23,26,26));draw=ImageDraw.Draw(sheet)
        for i,v in enumerate(['current','a','b']):
            im=Image.new('RGB',(2400,1600))
            for a in c['placements']:
                res=a['source'];src=current(res)
                if v!='current' and res in selected:src=Image.open(d/'variants'/f'{Path(res).stem}-{v}.png').convert('RGBA')
                im.paste(src,((a['x']-box[0])*4,(a['y']-box[1])*4),src)
            # Review downscale only, identical across rows.
            im=im.resize((1200,800),Image.Resampling.LANCZOS)
            draw.text((14,i*852+10),f'{name} / {v} — исходная раскладка, без игрового света',font=FONT,fill='#e1ddce')
            sheet.paste(im,(0,i*852+52))
            attempt=p.read(OUT/'qwen-selection.json').get(name,{}).get(v,v)
            rawpath=OUT/'qwen'/name/attempt/'raw.png'
            if rawpath.exists():
                raw=Image.open(rawpath).convert('RGBA')
                bg=Image.new('RGBA',raw.size,(0,0,0,255));bg.alpha_composite(raw)
                raw=bg.convert('RGB').resize((1200,800),Image.Resampling.LANCZOS);sheet.paste(raw,(1200,i*852+52))
                draw.text((1212,i*852+10),'Сырой Qwen-контекст (не игровая раскладка)',font=FONT,fill='#e1ddce')
        sheet.save(QA/(name+'-neighbors.png'))
if __name__=='__main__':floor();walls()
