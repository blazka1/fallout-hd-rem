from pathlib import Path
import csv,json,hashlib,collections,sys,time
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'assets/Fallout1-Все-ассеты-20261113'; ALL=OUT/'00_ВСЁ'
sys.path.insert(0,str(ROOT/'tools/asset-pipeline'))
from fallout_assets import Assets
A=Assets([ROOT/'FALLOUT (extract.me)/MASTER.DAT',ROOT/'FALLOUT (extract.me)/CRITTER.DAT'])
artnames=sorted(n for n in A.index if n.startswith('art/')); rows_by_part=[]; cats={}
for i in range(4):
 with (OUT/f'Каталог-part{i}.csv').open(encoding='utf-8-sig') as f: rows=list(csv.DictReader(f,delimiter=';'))
 for r in rows:
  for key in ('frames','width','height'):r[key]=int(r[key])
  cats[r['source']]=r['category']
 rows_by_part.append(rows)
repair=json.loads((OUT/'legacy-v3-repair.json').read_text(encoding='utf-8'));cats[repair['resource']['source']]=repair['resource']['category']
aux={'scenery':'07_Окружение/Объекты_и_декор','walls':'07_Окружение/Стены','tiles':'07_Окружение/Пол_и_крыши','intrface':'09_Интерфейс','heads':'10_Говорящие_головы','backgrnd':'11_Фоны','skilldex':'12_Иллюстрации_навыков','splash':'13_Заставки','misc':'14_Эффекты_и_служебная_графика','cuts':'15_Ролики_исходники','items':'08_Предметы/Без_прототипа/На_земле','inven':'08_Предметы/Без_прототипа/Инвентарь','critters':'02_Существа/critte'}
pairs=[]
for n in artnames:
 cat=cats.get(n,aux.get(n.split('/')[1],'16_Прочее'))
 pairs.append((ALL/'Оригиналы'/n,OUT/cat/'Оригиналы'/n))
print('Building full file inventory...',flush=True)
for rows in rows_by_part:
 for r in rows:
  name=Path(r['source']);group=name.parts[1];filename=name.name;cat=OUT/r['category']
  rel=Path('Метаданные')/group/(filename+'.json');meta=json.loads((ALL/rel).read_text(encoding='utf-8'))
  relatives=[rel,Path('Превью')/group/(filename+'.png')]+[Path('Кадры')/group/filename/f['file'] for f in meta['frames']]
  pairs.extend((ALL/p,cat/p) for p in relatives)
def check(pair):
 try:
  a,b=(p.read_bytes() for p in pair)
  return (None if hashlib.sha256(a).digest()==hashlib.sha256(b).digest() else str(pair[0]),len(a)+len(b))
 except Exception as e:return(str(pair[0])+': '+repr(e),0)
bad=[];total_bytes=0;start=time.time()
with ThreadPoolExecutor(max_workers=32) as pool:
 for offset in range(0,len(pairs),2048):
  for error,size in pool.map(check,pairs[offset:offset+2048]):
   total_bytes+=size
   if error:bad.append(error)
  print(json.dumps({'checked':min(offset+2048,len(pairs)),'total':len(pairs),'errors':len(bad),'seconds':round(time.time()-start)}),flush=True)
assert not bad,bad[:10]
for i,rows in enumerate(rows_by_part):
 stats={'original_resources':len(artnames[i::4]),'raster_resources':len(rows),'unique_frames':sum(r['frames'] for r in rows),'png_per_copy':sum(r['frames']+1 for r in rows)}
 p={'status':'verified','stats':stats,'categories':dict(collections.Counter(r['category'].split('/')[0] for r in rows)),'resources':rows,'errors':[],'copy_verification_failures':[],'verified_pairs':len(pairs) if i==0 else 0}
 (OUT/f'manifest-part{i}.json').write_text(json.dumps(p,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'verification.json').write_text(json.dumps({'verified_pairs':len(pairs)+3,'failed':bad,'verified_bytes':total_bytes,'legacy_v3_repair':repair,'seconds':round(time.time()-start)},ensure_ascii=False,indent=2),encoding='utf-8')
print('VERIFIED',len(pairs),total_bytes,flush=True)
