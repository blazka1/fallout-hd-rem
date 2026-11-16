"""Literal game-frame comparisons and measured asset QA; no artistic edits."""
from pipeline import *
from PIL import ImageFont
def run():
 review=BUILD/'review';review.mkdir(exist_ok=True)
 font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
 records=read(PACK/'floor-manifest.json')+read(PACK/'cutaway-manifest.json')
 inventory=read(OUT/'inventory.json');sheet=Image.new('RGB',(1280,len(inventory)*176),(23,26,25));draw=ImageDraw.Draw(sheet)
 checks=[]
 for row,a in enumerate(inventory):
  base=np.array(Image.open(R/a['input']).convert('RGBA'));ww,hh=base.shape[1],base.shape[0]
  for slot in range(4):
   path=R/a['input'] if slot==0 else PACK/f"tile-{a['id']:03}-v{slot}.png"
   im=Image.open(path).convert('RGBA');sheet.paste(im,(slot*320,row*176+28))
   draw.text((slot*320+6,row*176+3),f"ID{a['id']} "+('исходный' if slot==0 else f'вариант {slot}'),font=font,fill='white')
   if not slot:continue
   array=np.array(im);packed=decode(PACK/f"tile-{a['id']:03}-v{slot}.rgba")
   assert im.tobytes()==packed.tobytes()
   edge=np.zeros((hh,ww),bool);edge[:12]=1;edge[-12:]=1;edge[:,:12]=1;edge[:,-12:]=1
   assert np.array_equal(array[edge],base[edge]);assert np.array_equal(array[:,:,3],base[:,:,3])
   delta=np.abs(array[:,:,:3].astype(float)-base[:,:,:3].astype(float))
   checks.append(dict(base_id=a['id'],slot=slot,size=[ww,hh],rgba_lossless=True,alpha_exact=True,exact_perimeter_hd_pixels=12,
    mean_rgb=array[:,:,:3].mean((0,1)).tolist(),base_mean_rgb=base[:,:,:3].mean((0,1)).tolist(),mean_absolute_rgb_difference=float(delta.mean()),
    changed_fraction=float(np.any(delta>0,axis=2).mean()),png_sha256=p.sha(path),rgba_sha256=p.sha(PACK/f"tile-{a['id']:03}-v{slot}.rgba")))
 sheet.save(review/'all-tile-variants.png');write(review/'asset-checks.json',checks)
 before=BUILD/'before-current/tile-variants-before.png';after=BUILD/'world-final/tile-variants-after.png'
 assert before.exists() and after.exists()
 sources={name:dict(path=str(path.relative_to(R)),sha256=p.sha(path)) for name,path in [('before',before),('after',after)]}
 write(review/'capture-provenance.json',sources)
 shutil.copy2(before,review/'before.png');shutil.copy2(after,review/'after.png')
 for name,box in [('floor',(780,360,1410,850)),('cutaway',(1200,10,1850,310))]:
  w,h=box[2]-box[0],box[3]-box[1];pair=Image.new('RGB',(w*2,h+38),(23,26,25));dr=ImageDraw.Draw(pair)
  for col,path in enumerate([before,after]):
   pair.paste(Image.open(path).convert('RGB').crop(box),(col*w,38));dr.text((col*w+10,8),'До' if col==0 else 'После',font=font,fill='white')
  pair.save(review/(name+'-comparison.png'))
 page='''<!doctype html><html lang="ru"><meta charset="utf-8"><title>Варианты пола и верхнего среза пещеры</title><style>body{background:#181b1a;color:#ddd;font:18px system-ui;max-width:1400px;margin:28px auto;padding:20px}img{max-width:100%;height:auto}h2{margin-top:36px}a{color:#aebda4}.slider{position:relative;overflow:hidden;aspect-ratio:16/9}.slider img{position:absolute;inset:0;width:100%;height:100%}.range{width:100%;margin-top:12px}</style><h1>Пол и верхний срез пещеры</h1><p>24 новых варианта пола: восемь исходных фрагментов получили по три дополнительных облика. Верхний срез: два исходных типа, теперь восемь обликов — ×4. Края шириной 12 HD-пикселей и альфа совпадают с исходными побайтно. Геометрия, освещение и данные карты сохранены.</p><p>Настоящие кадры CE при одной камере. Потяните ползунок: слева новая версия, справа прежняя.</p><div class="slider"><img src="before.png"><img id="after" src="after.png" style="clip-path:inset(0 50% 0 0)"></div><input aria-label="Сравнение до и после" class="range" type="range" min="0" max="100" value="50" oninput="document.getElementById('after').style.clipPath='inset(0 '+(100-this.value)+'% 0 0)'"><h2>Пол</h2><img src="floor-comparison.png"><h2>Верхний срез</h2><img src="cutaway-comparison.png"><h2>Все варианты в масштабе HD-ассетов</h2><img src="all-tile-variants.png"><p>Новые материалы: локальный ComfyUI / Qwen Image 2.1 INT8. Цвет, масштаб фактуры, маски и сведение выполнены нативными узлами ComfyUI. Исходные задания пользователя сохранены как референсы; гладкая проба отклонена.</p><p><a href="asset-checks.json">Проверки ассетов</a> · <a href="capture-provenance.json">Происхождение кадров</a> · <a href="../integration.json">Отчёт установки</a></p></html>'''
 (review/'index.html').write_text(page,encoding='utf-8')
 print('Verified 30 lossless pages, exact alpha/perimeter, and generated literal game comparisons')
if __name__=='__main__':run()
