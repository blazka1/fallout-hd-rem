"""Registered exports, transparent-edge QA and honest comparison boards."""
from pipeline import ROOT,OUT,REF,MODELS,read,save,sha
from PIL import Image,ImageDraw,ImageFont
import numpy as np

PREVIEW=OUT/'preview';PREVIEW.mkdir(exist_ok=True)
PLAN=read(OUT/'plan.json');POSES=PLAN['poses']
BASE=Image.open(OUT/'inputs/original-lanczos-x4.png').convert('RGBA')
A=np.array(BASE);MASK=BASE.getchannel('A')
def font(n):return ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',n)
def composite(im,color=(65,65,61)):
    bg=Image.new('RGBA',im.size,(*color,255));bg.alpha_composite(im.convert('RGBA'));return bg.convert('RGB')
def crop(im,p,scale=4):return im.crop(tuple(v*scale for v in [p['x'],p['y'],p['x']+p['width'],p['y']+p['height']]))

def export(name):
    raw=Image.open(OUT/name/'raw.png').convert('RGBA');assert raw.size==BASE.size
    ra=np.array(raw);data=ra.copy();metrics=[]
    if name.startswith('qwen'):
        # Qwen stores magenta RGB in near-transparent background. Do not expose it
        # by blindly assigning original alpha. Composite over original RGB first.
        weight=ra[:,:,3:4].astype(float)/255
        data[:,:,:3]=np.rint(ra[:,:,:3]*weight+A[:,:,:3]*(1-weight)).astype('uint8')
    data[:,:,3]=A[:,:,3]
    final=Image.fromarray(data)
    dest=OUT/name/'registered';dest.mkdir(exist_ok=True)
    final.save(dest/'atlas-x4.png')
    final.resize((256,384),Image.Resampling.LANCZOS).save(dest/'atlas-x2.png')
    for p in POSES:
        out=crop(final,p);out.save(dest/(p['name']+'-x4.png'))
        out.resize((p['width']*2,p['height']*2),Image.Resampling.LANCZOS).save(dest/(p['name']+'-x2.png'))
        assert out.size==(p['width']*4,p['height']*4)
        assert np.array_equal(np.array(out)[:,:,3],np.array(crop(BASE,p))[:,:,3])
        b=np.array(crop(BASE,p));r=np.array(crop(raw,p));m=b[:,:,3]>127;rm=r[:,:,3]>127
        rec=dict(name=p['name'],size=list(out.size),alpha_matches_original_control=True,
            final_mean_rgb=np.mean(np.array(out)[:,:,:3][m],axis=0).round(2).tolist())
        if name.startswith('qwen'):
            rec.update(raw_mask_iou=float((m&rm).sum()/max(1,(m|rm).sum())),raw_original_mask_coverage=float((m&rm).sum()/max(1,m.sum())))
        metrics.append(rec)
    composite(raw).save(OUT/name/'raw-neutral.png')
    composite(final,(235,231,219)).save(dest/'light.png')
    composite(final,(18,20,22)).save(dest/'dark.png')
    return final,metrics

def board(rows,path,scale=4,background=(65,65,61)):
    cellw=210 if scale==4 else 150;cellh=300 if scale==4 else 165;labelw=220;top=120
    b=Image.new('RGB',(labelw+cellw*4,top+len(rows)*cellh+42),(25,28,29));d=ImageDraw.Draw(b)
    d.text((22,16),'Fallout 1 · Vault 13 · четыре исходные позы',font=font(26),fill=(225,219,198))
    d.text((22,53),f'Одинаковый масштаб ×{scale} · эксперимент, в игру не установлен',font=font(18),fill=(167,173,172))
    for i,p in enumerate(POSES):
        text=['Стойка спереди','Стойка сзади','Шаг · ЮВ · кадр 2','Шаг · З · кадр 6'][i]
        d.text((labelw+i*cellw+10,91),text,font=font(17),fill=(208,208,194))
    for r,(label,detail,im) in enumerate(rows):
        y=top+r*cellh
        d.multiline_text((20,y+26),label,font=font(21),fill=(225,214,166),spacing=6)
        d.multiline_text((20,y+110),detail,font=font(15),fill=(159,170,170),spacing=5)
        for c,p in enumerate(POSES):
            tile=Image.new('RGBA',(cellw-8,cellh-8),(*background,255))
            # Eight working pixels of padding reveal drift outside the old mask.
            sprite=im.crop((p['x']*4-8,p['y']*4-8,(p['x']+p['width'])*4+8,(p['y']+p['height'])*4+8))
            if scale!=4:sprite=sprite.resize((sprite.width*scale//4,sprite.height*scale//4),Image.Resampling.LANCZOS)
            tile.alpha_composite(sprite,((tile.width-sprite.width)//2,tile.height-16-sprite.height))
            b.paste(tile.convert('RGB'),(labelw+c*cellw,y))
    d.text((22,b.height-30),'Сравнение отдельных кадров. Геометрия и тени Qwen изменились; полный цикл не проверялся.',font=font(15),fill=(155,165,165))
    b.save(path)

allnames=['qwen-direct','qwen-direct-controlled','qwen-direct-soft']+[f'{branch}/d{n}' for branch in ['dream-direct','seed-dream'] for n in [15,22,30]]
images={};metrics={}
for name in allnames:
    if (OUT/name/'raw.png').exists():images[name],metrics[name]=export(name)
save(OUT/'image-qa.json',metrics)

for branch in ['dream-direct','seed-dream']:
    if not all(f'{branch}/d{n}' in images for n in [15,22,30]):continue
    board([(f'{"Оригинал" if branch=="dream-direct" else "SeedVR2"}\n→ DreamShaper',f'denoise 0.{n}\n8 шагов · CFG 2',images[f'{branch}/d{n}']) for n in [15,22,30]],PREVIEW/f'{branch}-denoise.png')

selection=read(OUT/'selection.json') if (OUT/'selection.json').exists() else dict(qwen='qwen-direct',dream='dream-direct/d22',seed_dream='seed-dream/d22')
qraw=Image.open(OUT/selection['qwen']/'raw.png').convert('RGBA')
rows=[('Оригинал','Nearest ×4\nбез нейросети',Image.open(OUT/'inputs/original-nearest-x4.png').convert('RGBA')),
      ('1. Оригинал\n→ Qwen','25 шагов · CFG 1\nальфа самой модели\nтени потеряны',qraw),
      ('2. Оригинал\n→ DreamShaper','XL v2 Turbo · d 0.'+selection['dream'][-2:]+'\n8 шагов · CFG 2',images[selection['dream']]),
      ('3. Оригинал\n→ SeedVR2\n→ DreamShaper','XL v2 Turbo · d 0.'+selection['seed_dream'][-2:]+'\n8 шагов · CFG 2',images[selection['seed_dream']])]
board(rows,PREVIEW/'comparison-x4.png')
board(rows,PREVIEW/'comparison-x2.png',2)
board(rows,PREVIEW/'comparison-light-x4.png',background=(229,225,211))
board(rows,PREVIEW/'comparison-dark-x4.png',background=(15,17,20))
board([('Qwen: сырой','Собственная альфа\nсилуэт изменён',qraw),('Qwen + маска','Диагностика: обрезает\nизменённые руки/ноги\nне годится для игры',images[selection['qwen']])],PREVIEW/'qwen-registration-diagnostic.png')
board([('Без ControlNet','Исходный Edit-граф',qraw),('ControlNet 0.3','Мягкий контроль',Image.open(OUT/'qwen-direct-soft/raw.png').convert('RGBA')),('ControlNet 0.8','Отбракован: белый фон\nи плоская графика',Image.open(OUT/'qwen-direct-controlled/raw.png').convert('RGBA'))],PREVIEW/'qwen-controls.png')
board([('Оригинал','Lanczos ×4',BASE),('Оригинал\n→ SeedVR2','Один шаг\nбез DreamShaper',Image.open(OUT/'seedvr2-control/raw.png').convert('RGBA'))],PREVIEW/'controls.png')

selected=OUT/'selected-preview';selected.mkdir(exist_ok=True)
for key,im in [('1-original-qwen',qraw),('2-original-dreamshaper',images[selection['dream']]),('3-original-seedvr2-dreamshaper',images[selection['seed_dream']])]:
    dest=selected/key;dest.mkdir(exist_ok=True);im.save(dest/'atlas-x4.png')
    for p in POSES:
        # This crop is only for preview; original registration is kept in plan.json.
        box=(p['x']*4-8,p['y']*4-8,(p['x']+p['width'])*4+8,(p['y']+p['height'])*4+8)
        pose=im.crop(box);pose.save(dest/(p['name']+'-preview-x4.png'))
        pose.resize((pose.width//2,pose.height//2),Image.Resampling.LANCZOS).save(dest/(p['name']+'-preview-x2.png'))
save(selected/'manifest.json',dict(status='12 sketches for comparison, not registered game replacements',
    selection=selection,preview_padding_working_pixels=8,
    qwen_alpha='Generated alpha retained in main comparison. Original-mask alternative rejected due clipping and doubled details.',
    dream_alpha='Original Lanczos x4 alpha applied to RGB SDXL outputs',runtime_installed=False))

# Cave context is explicitly a static montage, not a CE capture or an integration.
scene_path=ROOT/'assets/generated/player-male-vault13/qwen-cave-pixel-v5-20261116/prepare-v2/cave-style-reference.png'
scene=Image.open(scene_path).convert('RGBA')
panels=[]
for label,detail,im in rows:
    panel=scene.copy()
    for p,(x,baseline) in zip(POSES,[(20,402),(97,425),(177,410),(263,434)]):
        spr=crop(im,p).resize((p['width']*2,p['height']*2),Image.Resampling.LANCZOS)
        panel.alpha_composite(spr,(x,baseline-spr.height))
    tile=Image.new('RGB',(640,538),(25,28,29));tile.paste(panel.convert('RGB'),(0,58))
    dr=ImageDraw.Draw(tile);dr.text((12,10),label.replace('\n',' '),font=font(20),fill=(225,214,166))
    dr.text((12,34),'Статический монтаж ×2 · не игровой кадр',font=font(14),fill=(174,180,178));panels.append(tile)
montage=Image.new('RGB',(1280,1076))
for i,p in enumerate(panels):montage.paste(p,((i%2)*640,(i//2)*538))
montage.save(PREVIEW/'cave-context-montage.png')
save(OUT/'preview-provenance.json',dict(scene=str(scene_path.relative_to(ROOT)),scene_sha256=sha(scene_path),
    type='Static manual comparison montage; no in-engine screenshot and no runtime installation',scale=2,selection=selection))
print('Exported registered poses, masks QA, denoise boards, x2/x4 and cave montage.',flush=True)
