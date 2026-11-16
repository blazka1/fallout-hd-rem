"""Lossless candidate QA and comparison layouts, never artistic synthesis."""
from pathlib import Path
import json,html,hashlib,math,sys
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
sys.path.insert(0,str(Path(__file__).parent))
import pipeline as p
OUT=p.OUT;ROOT=p.ROOT
QA=OUT/'review';QA.mkdir(exist_ok=True)
FONT=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
SMALL=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
TITLE=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',25)
BG=(25,28,28);TEXT=(225,221,206)
def canvas(size):return Image.new('RGB',size,BG)
def paste_center(dst,im,box):
    x,y,w,h=box;im=im.copy().convert('RGBA');im.thumbnail((w,h),Image.Resampling.LANCZOS)
    dst.paste(im,(x+(w-im.width)//2,y+(h-im.height)//2),im)
def label(draw,xy,s,font=FONT):draw.text(xy,s,fill=TEXT,font=font)
def raw_previews():
    made=[]
    for path in OUT.glob('qwen/*/*/raw.png'):
        target=path.with_name('raw-on-dark.png')
        if target.exists():continue
        im=Image.open(path).convert('RGBA');bg=Image.new('RGBA',im.size,(32,36,36,255));bg.alpha_composite(im)
        bg.convert('RGB').save(target);made.append(str(target.relative_to(OUT)))
    print(json.dumps({'new_raw_previews':made}))
def main():
    plan=p.read(OUT/'plan.json');sources={r['source']:r for r in p.read(OUT/'source-inventory.json')}
    metrics=[];gallery=[]
    for panel in plan['panels']:
        prepared=OUT/'prepared'/panel['id']
        if not (prepared/'result.json').exists():continue
        cols=4+panel['variants']
        cw=220 if panel['id'].startswith('wall') else (340 if panel['id']=='floor' else 520)
        rh=240 if panel['id']=='floor' else 500
        sheet=canvas((cw*cols,90+rh*len(panel['slots'])));d=ImageDraw.Draw(sheet)
        headers=['Оригинал ×4','Текущая HD','SeedVR2 оригинала','SeedVR2 текущей HD','A · сколы','B · слои','C · эрозия'][:cols]
        if panel['id']=='floor':headers[-1]='B · пыль / гравий'
        for j,s in enumerate(headers):label(d,(j*cw+14,16),s,FONT if cw<400 else TITLE)
        for i,slot in enumerate(panel['slots']):
            res=slot['source'];stem=Path(res).stem;src=sources[res];w,hh=src['native'];y=90+i*rh
            original=Image.open(OUT/'sources'/(res+'.png')).convert('RGBA').resize((w*4,hh*4),Image.Resampling.NEAREST)
            current=Image.open(OUT/'sources'/(res+'.current.png')).convert('RGBA');cur=np.array(current)
            seed=Image.open(prepared/'seed'/f'{stem}.png').convert('RGBA')
            hdseed=Image.open(prepared/'seed-current'/f'{stem}.png').convert('RGBA')
            pictures=[original,current,seed,hdseed];files=[]
            exact=np.array(original)[:,:,3]
            for v in 'abc'[:panel['variants']]:
                path=prepared/'variants'/f'{stem}-{v}.png';im=Image.open(path).convert('RGBA');a=np.array(im)
                raw=Image.open(prepared/'raw'/f'{stem}-{v}.png').convert('RGBA');r=np.array(raw)
                mask=np.array(Image.open(prepared/'masks'/f'{stem}.png').convert('L'))
                support=(exact>0);rs=r[:,:,3]>=128;ref=support
                protected=(mask==0)&support
                ma=np.abs(a[:,:,:3].astype(float)-cur[:,:,:3].astype(float)).mean(2)
                stat=dict(source=res,panel=panel['id'],variant=v,file=str(path.relative_to(OUT)),
                    size=list(im.size),expected_size=[w*4,hh*4],exact_source_alpha=bool(np.array_equal(a[:,:,3],exact)),
                    matches_current_alpha=bool(np.array_equal(a[:,:,3],cur[:,:,3])),
                    protected_rgb_unchanged=bool(np.array_equal(a[:,:,:3][protected],cur[:,:,:3][protected])),
                    changed_opaque_fraction=float((ma[support]>2).mean()),mean_absolute_rgb_change=float(ma[support].mean()),
                    raw_mask_iou=float((ref&rs).sum()/max(1,(ref|rs).sum())),raw_source_coverage=float((ref&rs).sum()/max(1,ref.sum())),
                    raw_coverage_is_not_shape_guarantee=True,sha256=p.sha(path),status='candidate; not installed')
                assert im.size==(w*4,hh*4) and stat['exact_source_alpha'] and stat['protected_rgb_unchanged'],stat
                metrics.append(stat);pictures.append(im);files.append(path)
            for j,im in enumerate(pictures):
                label(d,(j*cw+14,y+2),f'{stem} · {src["instances"] or src["floor_cells"]} размещений',SMALL)
                # All columns use the same scale, with no exposure/color correction.
                paste_center(sheet,im,(j*cw+10,y+30,cw-20,rh-65))
            gallery.append(dict(source=res,group=panel['id'],variants=[str(f.relative_to(QA)).replace('\\','/') if f.is_relative_to(QA) else '../'+str(f.relative_to(OUT)).replace('\\','/') for f in files]))
        sheet.save(QA/(panel['id']+'-comparison.png'))
        small=sheet.copy();small.thumbnail((1920,2400),Image.Resampling.LANCZOS);small.save(QA/(panel['id']+'-overview.jpg'),quality=93)
        # Alpha review for all candidates, each shown on both backgrounds.
        checks=canvas((1600,max(1,len(panel['slots']))*250))
        cd=ImageDraw.Draw(checks)
        for i,slot in enumerate(panel['slots']):
            stem=Path(slot['source']).stem
            for j,v in enumerate('abc'[:panel['variants']]):
                im=Image.open(prepared/'variants'/f'{stem}-{v}.png')
                for k,color in enumerate([(20,20,20),(225,225,220)]):
                    x=j*530+k*260;y=i*250;cd.rectangle((x,y,x+258,y+248),fill=color)
                    paste_center(checks,im,(x,y+24,258,220));cd.text((x+5,y+4),f'{stem} {v}',font=SMALL,fill=(150,110,70))
        checks.save(QA/(panel['id']+'-alpha.png'))
    p.save(QA/'asset-qa.json',dict(candidate_count=len(metrics),metrics=metrics,installed=False,scope='Dimensions, exact source alpha, protected edges; raw generated alpha diagnostics. Does not prove art quality or internal geometry.'))
    # Exact selected-source and runtime hashes, without writing to them.
    baseline=p.read(OUT/'baseline-hashes.json')
    checks={name:dict(before=digest,after=p.sha(ROOT/name),unchanged=p.sha(ROOT/name)==digest) for name,digest in baseline.items()}
    p.save(QA/'baseline-check.json',checks)
    titles={'rocks-a':'Камни 01–03','rocks-b':'Камни 04–06','formations':'Сталагмиты и колонны','floor':'Пол','wall-01':'Связанный участок стен 1','wall-03':'Связанный участок стен 3'}
    cards=''.join(f'<section><h2>{titles[x["id"]]}</h2><a href="{x["id"]}-comparison.png"><img src="{x["id"]}-overview.jpg"></a><p><a href="{x["id"]}-comparison.png">Полное сравнение</a> · <a href="{x["id"]}-alpha.png">Контуры на двух фонах</a></p></section>' for x in plan['panels'] if (QA/(x['id']+'-comparison.png')).exists())
    page='''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Пещера V13 — кандидаты SeedVR2 → Qwen</title><style>body{margin:0;background:#171b1b;color:#e1ddce;font:17px/1.6 system-ui}main{max-width:1500px;margin:auto;padding:40px 28px}h1{font-size:36px;line-height:1.2}h2{font-size:23px;margin-top:40px}p{max-width:1000px;color:#bfc4bc}a{color:#d5b474}img{width:100%;background:#202525;border:1px solid #414845}small{color:#b0b9ae}.note{padding:20px;background:#25312c;border-left:4px solid #b49c6a}button{padding:10px 18px;background:#404a41;color:#eee;border:1px solid #68725e;cursor:pointer}.zoom img{width:auto;max-width:none}section{overflow:auto}</style><main><small>FALLOUT 1 CE · V13ENT · 15 ноября 2026</small><h1>Варианты каменной пещеры</h1><p class="note">Отдельный набор для художественного отбора. В игру ничего не установлено. Слева направо: оригинал, установленная HD-версия, SeedVR2 оригинала, SeedVR2 текущей HD, новые варианты Qwen. Одинаковый масштаб внутри каждого сравнения, без осветления.</p><p>Три направления: A — крупные сколы и трещины; B — слоистая порода; C — эрозия и изношенные плоскости. C подготовлен только для камней. Семейства материалов нужно выбирать и смешивать осмысленно, а не распределять контрастные рисунки случайно.</p><button onclick="document.body.classList.toggle('zoom')">Масштаб: вписать / 1:1</button>'''+cards+'''<p>Точная альфа и защищённые края восстановлены отдельно от нейросетевого рисунка. Эти проверки не доказывают правильность внутренней формы. Сырые генерации, графы, промпты и параметры находятся рядом с этим обзором.</p><p><a href="asset-qa.json">Техническая проверка PNG</a> · <a href="baseline-check.json">Сверка неизменности базы</a></p></main></html>'''
    page=page.replace('Одинаковый масштаб внутри каждого сравнения, без осветления.', 'Одинаковый масштаб внутри каждого сравнения. Кандидаты согласованы по тону с текущей HD-базой; дополнительного осветления при показе нет.')
    page=page.replace('B — слоистая порода;', 'B — слоистая порода, а для пола — пыль и гравий;')
    context_links='<section><h2>Соседство и исходная пещера</h2><p>'
    for file,title in [('floor-neighbors.png','Пол в настоящей раскладке MAP'),('wall-01-neighbors.png','Стыки стены 1'),('wall-03-neighbors.png','Стыки стены 3'),('original-cave-six-views.jpg','Шесть исходных ракурсов пещеры')]:
        if (QA/file).exists():context_links+=f'<a href="{file}">{title}</a> · '
    context_links+='</p><p>Раскладки новых вариантов собраны для QA без игрового света. Шесть исходных ракурсов — исторические SDL-кадры V13; проверено совпадение 30 выбранных текстур с текущим runtime.</p></section>'
    page=page.replace('</main>',context_links+'</main>')
    (QA/'index.html').write_text(page,encoding='utf-8')
    print(json.dumps(dict(candidates=len(metrics),all_alpha=all(m['exact_source_alpha'] for m in metrics),all_edges=all(m['protected_rgb_unchanged'] for m in metrics)),ensure_ascii=False))
if __name__=='__main__':
    if '--raw-only' in sys.argv:raw_previews()
    else:main()
