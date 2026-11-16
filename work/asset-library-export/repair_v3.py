from pathlib import Path
import sys,struct,json,hashlib,io
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'assets/Fallout1-Все-ассеты-20261113'; ALL=OUT/'00_ВСЁ'
sys.path.insert(0,str(ROOT/'tools/asset-pipeline'))
from fallout_assets import decode_frm,palette_rgb
name='art/inven/oknife.frm'; data=(ALL/'Оригиналы'/name).read_bytes()
assert struct.unpack_from('>I',data)[0]==3
assert struct.unpack_from('>I',data,58)[0]==len(data)-62
meta,dirs=decode_frm(struct.pack('>I',4)+data[4:])
assert meta['frame_count']==1 and meta['unique_directions']==1
category_paths=[p for p in OUT.glob('*/**/Оригиналы/art/inven/oknife.frm') if '00_ВСЁ' not in p.parts]
assert len(category_paths)==1,category_paths
relative=category_paths[0].relative_to(OUT); cat='/'.join(relative.parts[:relative.parts.index('Оригиналы')])
f=dirs[0][0]; palette=palette_rgb((ALL/'Оригиналы/color.pal').read_bytes())
im=Image.frombytes('P',(f.width,f.height),f.pixels);im.putpalette(palette);im.info['transparency']=0;im=im.convert('RGBA')
b=io.BytesIO();im.save(b,format='PNG',compress_level=3);png=b.getvalue()
assert Image.open(io.BytesIO(png)).tobytes()==im.tobytes()
meta.update(version=3,source=name,sha256=hashlib.sha256(data).hexdigest(),category=cat,palette='color.pal',frame_count_exported=1,direction_aliases={str(d):0 for d in range(6)},frames=[{'file':'d0-f000.png','direction':0,'frame':0,'width':f.width,'height':f.height,'shift_x':f.shift_x,'shift_y':f.shift_y}],notes='Legacy FRM version 3: same header and raster layout, exact payload size verified. Original bytes unchanged.')
files={Path('Превью/inven/oknife.frm.png'):png,Path('Кадры/inven/oknife.frm/d0-f000.png'):png,Path('Метаданные/inven/oknife.frm.json'):(json.dumps(meta,ensure_ascii=False,indent=2)+'\n').encode()}
for rel,content in files.items():
 for parent in (ALL,OUT/cat):
  target=parent/rel;target.parent.mkdir(parents=True,exist_ok=True)
  assert not target.exists(),target
  target.write_bytes(content);assert target.read_bytes()==content
row={'source':name,'category':cat,'preview':str(Path(cat)/'Превью/inven/oknife.frm.png'),'frames':1,'width':f.width,'height':f.height,'palette':'color.pal'}
(OUT/'legacy-v3-repair.json').write_text(json.dumps({'resource':row,'verified_pairs':3,'original_unchanged':hashlib.sha256((ALL/'Оригиналы'/name).read_bytes()).hexdigest()==meta['sha256']},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(row,ensure_ascii=True))
