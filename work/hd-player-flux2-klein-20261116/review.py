"""Raw-vs-original-mask Flux2 review; no hidden registration claims."""
from pipeline import ROOT,OLD,OUT,read,save,sha
from PIL import Image,ImageDraw,ImageFont
import numpy as np
import json
plan=read(OUT/'plan.json');poses=plan['poses'];raw=Image.open(OUT/'edit-v1/raw.png').convert('RGB')
assert raw.size==(512,768)
base=Image.open(OUT/'inputs/original-lanczos-x4.png').convert('RGBA')
nearest=Image.open(OUT/'inputs/original-nearest-x4.png').convert('RGBA')
mask=base.getchannel('A');registered=raw.convert('RGBA');registered.putalpha(mask)
dest=OUT/'prepared';dest.mkdir(exist_ok=True);preview=OUT/'preview';preview.mkdir(exist_ok=True)
registered.save(dest/'atlas-x4.png');registered.resize((256,384),Image.Resampling.LANCZOS).save(dest/'atlas-x2.png')
def font(n):return ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',n)
def crop(im,p,pad=0):return im.crop((p['x']*4-pad,p['y']*4-pad,(p['x']+p['width'])*4+pad,(p['y']+p['height'])*4+pad))
def comp(im,bg=(62,62,58)):
    b=Image.new('RGBA',im.size,(*bg,255));b.alpha_composite(im.convert('RGBA'));return b.convert('RGB')
ra=np.array(raw).astype(float);a=np.array(base);bg=np.median(np.concatenate([ra[:16].reshape(-1,3),ra[-16:].reshape(-1,3),ra[:,:16].reshape(-1,3),ra[:,-16:].reshape(-1,3)]),axis=0)
rough=np.max(np.abs(ra-bg),axis=2)>18
estimated_mask=Image.fromarray((rough*255).astype('uint8'));estimated_mask.save(preview/'raw-estimated-foreground.png')
metrics=[]
for p in poses:
    out=crop(registered,p);out.save(dest/(p['name']+'-x4.png'))
    out.resize((p['width']*2,p['height']*2),Image.Resampling.LANCZOS).save(dest/(p['name']+'-x2.png'))
    crop(raw,p,8).save(dest/(p['name']+'-raw-preview.png'))
    assert out.size==(p['width']*4,p['height']*4)
    om=np.array(crop(base,p))[:,:,3]>127;rm=np.array(crop(estimated_mask,p))>127
    assert np.array_equal(np.array(out)[:,:,3],np.array(crop(base,p))[:,:,3])
    metrics.append(dict(name=p['name'],size=out.size,original_alpha_exact=True,
        raw_foreground_estimate_iou=float((om&rm).sum()/max(1,(om|rm).sum())),
        source_foreground_coverage_estimate=float((om&rm).sum()/max(1,om.sum())),sha256=sha(dest/(p['name']+'-x4.png'))))
comp(registered,(230,226,213)).save(preview/'light.png');comp(registered,(16,18,21)).save(preview/'dark.png')

def board(rows,path,scale=4,bg=(62,62,58)):
    labelw=230;cw=210 if scale==4 else 150;ch=300 if scale==4 else 170;top=115
    out=Image.new('RGB',(labelw+cw*4,top+ch*len(rows)+42),(25,28,29));d=ImageDraw.Draw(out)
    d.text((18,14),'Vault 13 · FLUX.2 klein 4B · четыре исходные позы',font=font(25),fill=(226,218,188))
    d.text((18,51),f'FLUX Edit · 4 шага · CFG 1 · масштаб ×{scale} · эксперимент',font=font(18),fill=(170,180,173))
    for i,t in enumerate(['Стойка спереди','Стойка сзади','Шаг · ЮВ · кадр 2','Шаг · З · кадр 6']):d.text((labelw+i*cw+6,86),t,font=font(16),fill=(207,210,195))
    for r,(title,note,im) in enumerate(rows):
        y=top+r*ch;d.multiline_text((18,y+27),title,font=font(21),fill=(225,213,161),spacing=7)
        d.multiline_text((18,y+116),note,font=font(15),fill=(169,181,174),spacing=6)
        for i,p in enumerate(poses):
            sprite=crop(im,p,8).convert('RGBA')
            if scale!=4:sprite=sprite.resize((sprite.width*scale//4,sprite.height*scale//4),Image.Resampling.LANCZOS)
            tile=Image.new('RGBA',(cw-8,ch-8),(*bg,255));tile.alpha_composite(sprite,((tile.width-sprite.width)//2,tile.height-15-sprite.height))
            out.paste(tile.convert('RGB'),(labelw+i*cw,y))
    d.text((18,out.height-29),'Исходная маска не исправляет перерисованную геометрию. Полный цикл и игровой рендер не проверялись.',font=font(14),fill=(163,175,171))
    out.save(path)

rows=[('Оригинал','Nearest ×4',nearest),('FLUX.2 klein 4B','Сырой RGB-результат\nбез обрезки по маске',raw),('FLUX + исходная\nмаска','Диагностика геометрии\nи прозрачности',registered)]
board(rows,preview/'comparison-x4.png');board(rows,preview/'comparison-x2.png',2)
board([rows[1]],preview/'four-poses-raw.png')
board([rows[2]],preview/'four-poses.png');board([rows[2]],preview/'four-poses-light.png',bg=(230,226,213));board([rows[2]],preview/'four-poses-dark.png',bg=(16,18,21))
board([('Qwen 2.1','Прежний прямой Edit',Image.open(OLD/'qwen-direct/raw.png').convert('RGBA')),('FLUX.2 klein 4B','Новый сырой RGB',raw)],preview/'qwen-vs-flux-raw.png')

scene_path=ROOT/'assets/generated/player-male-vault13/qwen-cave-pixel-v5-20261116/prepare-v2/cave-style-reference.png'
scene=Image.open(scene_path).convert('RGBA');montage=Image.new('RGB',(1280,538))
for i,(title,im) in enumerate([('Оригинал',nearest),('FLUX + исходная маска',registered)]):
    pane=scene.copy()
    for p,(x,y) in zip(poses,[(20,402),(97,425),(177,410),(263,434)]):
        sp=crop(im,p).resize((p['width']*2,p['height']*2),Image.Resampling.LANCZOS);pane.alpha_composite(sp,(x,y-sp.height))
    tile=Image.new('RGB',(640,538),(25,28,29));tile.paste(pane.convert('RGB'),(0,58));d=ImageDraw.Draw(tile)
    d.text((12,9),title,font=font(21),fill=(225,214,176));d.text((12,34),'Монтаж ×2 · не кадр CE, без игрового освещения и перекрытий',font=font(13),fill=(165,176,171));montage.paste(tile,(640*i,0))
montage.save(preview/'cave-montage.png')
before=read(OUT/'protected-before.json');changed=[p for p,h in before.items() if not (ROOT/p).exists() or sha(ROOT/p)!=h]
for p in poses:assert sha(ROOT/p['source'])==p['sha256']
result=read(OUT/'edit-v1/result.json');assert read(OUT/'edit-v1/history.json')['status']['status_str']=='success'
assert sha(OUT/'edit-v1/raw.png')==result['files'][0]['sha256']
save(OUT/'qa.json',dict(status='four-pose experiment complete; original-mask composite rejected, not installed',frames=metrics,raw_size=list(raw.size),raw_mode=raw.mode,
    estimated_background_rgb=bg.tolist(),mask_estimation='Only a diagnostic: max RGB difference >18 from median border. Not ground-truth segmentation.',
    protected_files_checked=len(before),protected_files_changed=changed,
    pixel_art_task_still_paused=read(ROOT/'assets/generated/player-male-vault13/pixel-art-xl-v10-20261116/paused.json')['do_not_auto_resume'],
    elapsed_seconds=result['elapsed_seconds'],visual_review=dict(raw='Four figures, added fabric wear and facial definition; costume desaturated, shadows reinterpreted, extra yellow chest marks',
        registration='Original mask exposes grey background halos and clips changed limb contours; reject as game-ready replacement',
        primary_preview='preview/four-poses-raw.png',mask_diagnostics='prepared/ and preview/comparison-x4.png'),
    limitations=['Original alpha equality does not prove content registration','Four selected frames are not a complete animation cycle','Cave image is a static montage of a rejected mask diagnostic']))
assert not changed,'Review concurrent protected-file modifications before claiming unchanged.'
print(json.dumps(dict(frames=metrics,protected_files=len(before),changed=changed),ensure_ascii=False),flush=True)
