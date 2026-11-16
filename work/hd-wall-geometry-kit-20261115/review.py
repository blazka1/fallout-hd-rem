"""Read-only art QA, contact sheets and metadata. Never installs assets."""
from pathlib import Path
import sys,json,itertools,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,str(Path(__file__).parent))
import kit
O=kit.OUT; B=kit.B; R=kit.R; P=kit.PLAN
def sha(f):return hashlib.sha256(Path(f).read_bytes()).hexdigest()
def save(f,v):f.parent.mkdir(parents=True,exist_ok=True);f.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def font(n):return ImageFont.truetype('C:/Windows/Fonts/arial.ttf',n)
def label(im,xy,s,size=20,color='#e2e6eb'):ImageDraw.Draw(im).text(xy,s,font=font(size),fill=color)
def sheet(paths,labels,dest,cols=2,cell=(720,480)):
 cw,ch=cell; rows=(len(paths)+cols-1)//cols
 out=Image.new('RGB',(cw*cols,(ch+38)*rows),(24,27,32))
 for i,(path,title) in enumerate(zip(paths,labels)):
  x=i%cols*cw;y=i//cols*(ch+38);label(out,(x+12,y+7),title)
  im=Image.open(path).convert('RGB');im.thumbnail((cw-4,ch),Image.Resampling.LANCZOS)
  out.paste(im,(x+(cw-im.width)//2,y+38+(ch-im.height)//2))
 dest.parent.mkdir(parents=True,exist_ok=True);out.save(dest)
def main():
 inv=kit.p.read(O/'inventory.json'); contexts=P['contexts'];assets=[];coverage={};checks=[]
 labels=['Оригинал: форма и расположение','A — массивные уступы','B — косые плиты','C — неглубокие ниши']
 for c in contexts:
  name=c['id'];paths=[O/'inputs'/f'{name}.png']+[O/'imagegen'/name/f'{v}.png' for v in 'abc']
  sheet(paths,labels,B/'review'/f'{name}.png')
  original=np.asarray(Image.open(paths[0]).convert('RGB')).max(axis=2)>0
  for v,path in zip('abc',paths[1:]):
   im=Image.open(path);assert im.size==(1536,1024)
   small=np.asarray(im.convert('RGB').resize((600,400),Image.Resampling.NEAREST)).max(axis=2)>10
   union=(small|original).sum();iou=float((small&original).sum()/union)
   assets.append(dict(context=name,variant=v,png=str(path.relative_to(R)),sha256=sha(path),size=list(im.size),generation=kit.p.read(path.with_suffix('.json')),silhouette_iou_to_original=round(iou,4),silhouette_note='diagnostic only; silhouettes intentionally redesigned; IoU is not a compatibility score',ready_for_runtime=False))
  for s in c['selected']:
   assert s['source'] not in coverage
   x=s['x']-c['box_native'][0];y=s['y']-c['box_native'][1]
   coverage[s['source']]=dict(context=name,reference_box_native=[x,y,s['width'],s['height']],representative_object=s['id'],variants=['a','b','c'],status='whole-context concept; not an independently registered replacement')
 assert set(coverage)==set(P['walls']) and len(assets)==15
 checks.append(dict(test='Original type reference coverage',result='PASS',count=len(coverage)))
 checks.append(dict(test='Unique complete generated contexts',result='PASS',count=len(assets)))
 # Four position-specific blocks, three variants. These checks cover raster seams only.
 D=O/'connector-proof';base=np.asarray(Image.open(D/'a.png').convert('RGBA'))
 variants={v:np.asarray(Image.open(D/f'{v}.png').convert('RGBA')) for v in 'abc'}
 for v,im in variants.items():
  assert im.shape==base.shape and np.array_equal(im[:,:,3],base[:,:,3])
  for x in [384,768,1152]:assert np.array_equal(im[:,x-48:x+48],base[:,x-48:x+48])
 for seq in itertools.product('abc',repeat=4):
  mixed=np.concatenate([np.asarray(Image.open(D/'blocks'/f'{i}-{v}.png').convert('RGBA')) for i,v in enumerate(seq)],axis=1)
  assert np.array_equal(mixed[:,:,3],base[:,:,3])
  for x in [384,768,1152]:assert np.array_equal(mixed[:,x-48:x+48],base[:,x-48:x+48])
 checks.append(dict(test='A/B/C same-position combinations preserve canonical outline and connector strips',result='PASS',combinations=81,note='Not CE registration or arbitrary block reordering'))
 seq='abca';mixed=Image.new('RGBA',(1536,512))
 for i,v in enumerate(seq):mixed.paste(Image.open(D/'blocks'/f'{i}-{v}.png'),(i*384,0))
 mixed.save(B/'review/mixed-abca.png')
 sheet([D/'a.png',B/'review/mixed-abca.png'],['Общий профиль A','Смешанный ряд A / B / C / A — границы блоков одинаковы'],B/'review/connector-comparison.png',cols=1,cell=(1536,512))
 allpaths=[];alllabels=[]
 for c in contexts:
  allpaths.append(O/'inputs'/f"{c['id']}.png");alllabels.append(c['id']+' / оригинал')
  for v in 'abc':allpaths.append(O/'imagegen'/c['id']/f'{v}.png');alllabels.append(c['id']+' / '+v.upper())
 sheet(allpaths,alllabels,B/'review/overview.png',cols=4,cell=(450,300))
 baseline=kit.p.read(O/'baseline.json');hashcheck={p:dict(before=h,after=sha(R/p)) for p,h in baseline.items()}
 for p,h in hashcheck.items():h['unchanged']=h['before']==h['after']
 save(B/'baseline-check.json',hashcheck)
 checks.append(dict(test='Tracked project/runtime baseline unchanged',result='PASS' if all(h['unchanged'] for h in hashcheck.values()) else 'CHANGED_EXTERNALLY_OR_UNEXPECTED',files=len(hashcheck)))
 save(O/'source-context-map.json',coverage)
 save(O/'manifest.json',dict(status='geometry concepts and connector proof; not game-ready',tool='built-in image_gen; connector preparation through native ComfyUI',source_count=62,source_placements=418,observed_contacts=522,concept_images=15,independent_ready_sprites=0,planned_original_variant_count=186,planning_correction='62 x 3 is a planning target, not a completed sprite count. Generator changed layout; per-FRM export would reproduce seams. Use connected wall blocks with fixed connector geometry.',assets=assets,main_runtime_modified=False,scope='First cave ca wall resource families only; cutaway floor tiles, vault architecture and approved door owner252 remain outside this export.'))
 save(B/'checks.json',dict(checks=checks,engine_tests_run=False,visual_limit='Connected context concepts are continuous within each image. Global assembly and CE registration are unverified. Fixed connector proof can retain visible interior blend transitions.'))
 print(json.dumps(dict(images=len(assets),coverage=len(coverage),connector_combinations=81,checks=checks),ensure_ascii=False))
if __name__=='__main__':main()
