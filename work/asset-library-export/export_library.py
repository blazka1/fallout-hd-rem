"""Read-only original DAT export into a separate browsable asset library."""
from pathlib import Path
import argparse
import sys, json, struct, hashlib, csv, re, shutil, collections, time
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/asset-pipeline'))
from fallout_assets import Assets, decode_frm, palette_rgb, lst_names

OUT = ROOT / 'assets' / 'Fallout1-Все-ассеты-20261113'
parser=argparse.ArgumentParser(); parser.add_argument('--part',type=int,default=0); parser.add_argument('--parts',type=int,default=1); args=parser.parse_args()
suffix=f'-part{args.part}' if args.parts>1 else ''
ALL = OUT / '00_ВСЁ'
OUT.mkdir(parents=True, exist_ok=True)
if (OUT / 'manifest.json').exists():
    raise SystemExit('Completed export already exists; refusing overwrite.')
A = Assets([ROOT/'FALLOUT (extract.me)/MASTER.DAT', ROOT/'FALLOUT (extract.me)/CRITTER.DAT'])
pal = palette_rgb(A.read('color.pal'))
types = {0:'05_Броня',1:'08_Предметы/Лекарства',2:'08_Предметы/Контейнеры',3:'04_Оружие',4:'06_Боеприпасы',5:'08_Предметы/Разное',6:'08_Предметы/Ключи'}
item_cats = collections.defaultdict(set)
evidence = collections.defaultdict(list)
lists = {}
for group in ('items','inven','intrface'):
    lists[group] = lst_names(A.read(f'art/{group}/{group}.lst'))
for name in sorted(A.index):
    if name.startswith('proto/items/') and name.endswith('.pro'):
        data = A.read(name)
        if len(data) < 56: continue
        pid, message, fid = struct.unpack_from('>3I',data)
        subtype = struct.unpack_from('>i',data,32)[0]
        invfid = struct.unpack_from('>i',data,52)[0]
        for group, artfid in [('items',fid),('inven',invfid)]:
            idx = artfid & 4095
            if artfid >= 0 and idx < len(lists[group]):
                resource = f'art/{group}/{lists[group][idx]}'
                item_cats[resource].add(types.get(subtype,'08_Предметы/Неопределённые'))
                evidence[resource].append({'prototype':name,'pid':pid,'item_type':subtype})

def category(name):
    group = name.split('/')[1]
    stem = Path(name).stem
    if group == 'critters':
        code = stem[:6]
        if code in ('marobo','mafeye','mahand'):
            return '03_Роботы/'+code, 'critter family prefix'
        if code.startswith(('h','n')) or code in ('mamtn2','mamtnt','malieu'):
            sub = 'Мутанты' if code in ('mamtn2','mamtnt','malieu','naghul','naglow') else 'Люди'
            return '01_Гуманоиды/'+sub+'/'+code, 'critter family prefix; allegiance not inferred'
        return '02_Существа/'+code, 'critter family prefix; includes peaceful animals'
    if group in ('items','inven'):
        found = item_cats.get(name,set())
        cat = next(iter(found)) if len(found)==1 else ('08_Предметы/Общие_для_разных_типов' if found else '08_Предметы/Без_прототипа')
        return cat+('/На_земле' if group=='items' else '/Инвентарь'), 'item prototypes' if found else 'no item prototype mapping'
    return {'scenery':'07_Окружение/Объекты_и_декор','walls':'07_Окружение/Стены',
            'tiles':'07_Окружение/Пол_и_крыши','intrface':'09_Интерфейс',
            'heads':'10_Говорящие_головы','backgrnd':'11_Фоны',
            'skilldex':'12_Иллюстрации_навыков','splash':'13_Заставки',
            'misc':'14_Эффекты_и_служебная_графика','cuts':'15_Ролики_исходники'}.get(group,'16_Прочее'), 'original art directory'

stats = collections.Counter(); cats = collections.Counter(); rows=[]; errors=[]; verification=[]
def write(path,data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes()!=data: raise FileExistsError(path)
        return
    path.write_bytes(data)
def paired(relative, catrelative, data):
    p = ALL/relative; q = OUT/catrelative
    write(p,data); write(q,data)
    verification.append((str(p.relative_to(OUT)),str(q.relative_to(OUT)),hashlib.sha256(data).hexdigest()))

def save_png(im,relative,catrelative):
    import io
    buf=io.BytesIO(); im.save(buf,format='PNG',compress_level=3)
    paired(relative,catrelative,buf.getvalue())
    stats['png_per_copy'] += 1

def frame_image(f,palette,transparent):
    im=Image.frombytes('P',(f.width,f.height),f.pixels); im.putpalette(palette)
    if transparent: im.info['transparency']=0
    return im.convert('RGBA')

artnames = sorted(n for n in A.index if n.startswith('art/'))
start=time.time()
for k,name in enumerate(artnames):
    if k%args.parts!=args.part: continue
    data=A.read(name); cat,reason=category(name)
    relative=Path(name); group=relative.parts[1]; filename=relative.name
    # Preserve every original art resource, including palettes, lists and movies.
    paired(Path('Оригиналы')/relative,Path(cat)/'Оригиналы'/relative,data)
    stats['original_resources']+=1
    raster=bool(re.search(r'\.fr[m0-5]$',name)) or name.endswith('.rix') or data[:6] in (b'GIF87a',b'GIF89a') or (name.endswith('.001') and data[:4]==b'\0\0\0\4')
    if not raster: continue
    existing=ALL/'Метаданные'/group/(filename+'.json')
    if existing.exists():
        md=json.loads(existing.read_text(encoding='utf-8')); preview=Path('Превью')/group/(filename+'.png')
        rows.append({'source':name,'category':cat,'preview':str(Path(cat)/preview),'frames':md['frame_count_exported'],'width':Image.open(ALL/preview).width,'height':Image.open(ALL/preview).height,'palette':md['palette']})
        stats['raster_resources']+=1; stats['unique_frames']+=md['frame_count_exported']; stats['png_per_copy']+=md['frame_count_exported']+1; cats[cat.split('/')[0]]+=1
        relatives=[preview,Path('Метаданные')/group/(filename+'.json')]+[Path('Кадры')/group/filename/f['file'] for f in md['frames']]
        for rel in relatives:
            verification.append((str(Path('00_ВСЁ')/rel),str(Path(cat)/rel),hashlib.sha256((ALL/rel).read_bytes()).hexdigest()))
        continue
    try:
        palette=pal; palette_name='color.pal'; transparent=group not in ('intrface','backgrnd','splash')
        matching=f'art/{group}/{relative.stem}.pal'
        if matching in A.index:
            palette=palette_rgb(A.read(matching)); palette_name=matching
        if group=='intrface':
            for idx,pn in ((309,'death'),(297,'helpscrn')):
                if idx < len(lists['intrface']) and filename==lists['intrface'][idx] and f'art/intrface/{pn}.pal' in A.index:
                    palette_name=f'art/intrface/{pn}.pal'; palette=palette_rgb(A.read(palette_name))
        if data[:6] in (b'GIF87a',b'GIF89a'):
            import io
            gif=Image.open(io.BytesIO(data)); frame_total=gif.n_frames
            metadata={'format':'GIF','palette':'embedded','frames':[]}
            for fi in range(frame_total):
                gif.seek(fi); frame=gif.convert('RGBA'); outname=f'd0-f{fi:03}.png'
                if fi==0: im=frame.copy()
                save_png(frame,Path('Кадры')/group/filename/outname,Path(cat)/'Кадры'/group/filename/outname)
                metadata['frames'].append({'file':outname,'frame':fi,'direction':0,'width':frame.width,'height':frame.height})
        elif name.endswith('.rix'):
            assert data[:4]==b'RIX3'
            w,h=struct.unpack_from('<HH',data,4)
            assert len(data)==10+768+w*h,(name,len(data),w,h)
            im=Image.frombytes('P',(w,h),data[778:]); im.putpalette(palette_rgb(data[10:778])); im=im.convert('RGBA')
            metadata={'format':'RIX3','width':w,'height':h,'palette':'embedded','frames':[{'file':'d0-f000.png','frame':0,'direction':0,'width':w,'height':h}]}
            frame_total=1
            save_png(im,Path('Кадры')/group/filename/'d0-f000.png',Path(cat)/'Кадры'/group/filename/'d0-f000.png')
        else:
            declared=struct.unpack_from('>I',data,58)[0]
            decode_data=data
            if re.search(r'\.fr[0-5]$',name) and declared!=len(data)-62:
                decode_data=data[:58]+struct.pack('>I',len(data)-62)+data[62:]
            meta,dirs=decode_frm(decode_data); metadata=dict(meta); metadata['frames']=[]
            metadata['original_declared_data_size']=declared
            metadata['physical_data_size']=len(data)-62
            im=frame_image(dirs[0][0],palette,transparent)
            seen={}; frame_total=0
            for direction,frames in dirs.items():
                offset=meta['direction_offsets'][direction]
                if offset in seen: continue
                seen[offset]=direction
                actual=int(name[-1]) if re.search(r'\.fr[0-5]$',name) else direction
                for fi,f in enumerate(frames):
                    outname=f'd{actual}-f{fi:03}.png'
                    image=frame_image(f,palette,transparent)
                    save_png(image,Path('Кадры')/group/filename/outname,Path(cat)/'Кадры'/group/filename/outname)
                    # Validate exact indexed -> RGBA mapping including alpha for every frame.
                    back=image.convert('RGB').tobytes()
                    expected=bytes(f.pixels).translate(palette[0::3])+bytes(f.pixels).translate(palette[1::3])+bytes(f.pixels).translate(palette[2::3])
                    actual_channels=b''.join(c.tobytes() for c in image.convert('RGB').split())
                    if actual_channels!=expected: raise ValueError('RGB conversion mismatch')
                    if transparent and image.getchannel('A').tobytes()!=bytes(0 if v==0 else 255 for v in f.pixels): raise ValueError('Alpha mismatch')
                    metadata['frames'].append({'file':outname,'direction':actual,'stored_direction':direction,'frame':fi,'width':f.width,'height':f.height,'shift_x':f.shift_x,'shift_y':f.shift_y})
                    frame_total+=1
            metadata['direction_aliases']={str(d):seen[off] for d,off in enumerate(meta['direction_offsets'])}
            metadata['palette']=palette_name
        preview=Path('Превью')/group/(filename+'.png')
        save_png(im,preview,Path(cat)/preview)
        metadata.update(source=name,archive=str(A.index[name].path),sha256=hashlib.sha256(data).hexdigest(),category=cat,classification_reason=reason,prototype_evidence=evidence.get(name,[]),frame_count_exported=frame_total,notes='Original size and canvas. No upscale, no scene lighting, no palette-cycle animation. Offsets in original logical pixels.')
        encoded=(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n').encode()
        paired(Path('Метаданные')/group/(filename+'.json'),Path(cat)/'Метаданные'/group/(filename+'.json'),encoded)
        rows.append({'source':name,'category':cat,'preview':str(Path(cat)/preview),'frames':frame_total,'width':im.width,'height':im.height,'palette':metadata['palette']})
        stats['raster_resources']+=1; stats['unique_frames']+=frame_total; cats[cat.split('/')[0]]+=1
    except Exception as exc:
        errors.append({'source':name,'error':repr(exc)})
    if k%250==0: print(json.dumps({'done':k,'total':len(artnames),'stats':dict(stats),'errors':len(errors),'seconds':round(time.time()-start)},ensure_ascii=False),flush=True)

if args.part==0: write(ALL/'Оригиналы/color.pal',A.read('color.pal'))
with (OUT/f'Каталог{suffix}.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=['source','category','preview','frames','width','height','palette'],delimiter=';'); writer.writeheader(); writer.writerows(rows)
print('Verifying both copies...',flush=True)
bad=[]
for p,q,digest in verification:
    if hashlib.sha256((OUT/p).read_bytes()).hexdigest()!=digest or hashlib.sha256((OUT/q).read_bytes()).hexdigest()!=digest: bad.append(p)
result={'status':'complete' if not errors and not bad else 'completed_with_errors','archives':[str(a.path) for a in A.archives],'stats':dict(stats),'categories':dict(cats),'errors':errors,'copy_verification_failures':bad,'verified_pairs':len(verification),'seconds':round(time.time()-start),'resources':rows}
write(OUT/f'manifest{suffix}.json',(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps({k:v for k,v in result.items() if k!='resources'},ensure_ascii=False),flush=True)
