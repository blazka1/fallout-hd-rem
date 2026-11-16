from pathlib import Path
import json,csv,collections,sys,re
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'assets/Fallout1-Все-ассеты-20261113'
sys.path.insert(0,str(ROOT/'tools/asset-pipeline'))
from fallout_assets import Assets
parts=[json.loads((OUT/f'manifest-part{i}.json').read_text(encoding='utf-8')) for i in range(4)]
stats=collections.Counter(); cats=collections.Counter(); rows=[]; errors=[]; bad=[]
for p in parts:
    stats.update(p['stats']);cats.update(p['categories']);rows+=p['resources'];errors+=p['errors'];bad+=p['copy_verification_failures']
repair=json.loads((OUT/'legacy-v3-repair.json').read_text(encoding='utf-8'))
rows.append(repair['resource']); stats.update({'raster_resources':1,'unique_frames':1,'png_per_copy':2}); cats[repair['resource']['category'].split('/')[0]]+=1
resolved=[e for e in errors if e['source']==repair['resource']['source']]
errors=[e for e in errors if e['source']!=repair['resource']['source']]
A=Assets([ROOT/'FALLOUT (extract.me)/MASTER.DAT',ROOT/'FALLOUT (extract.me)/CRITTER.DAT'])
names=sorted(n for n in A.index if n.startswith('art/'))
rawmissing=[n for n in names if not (OUT/'00_ВСЁ/Оригиналы'/n).is_file()]
assert not rawmissing,rawmissing
assert stats['original_resources']==len(names)
assert len({r['source'] for r in rows})==len(rows)
expected_rasters={n for n in names if re.search(r'\.(fr[m0-5]|rix|001)$',n)}
assert {r['source'] for r in rows}==expected_rasters
rows.sort(key=lambda r:(r['category'],r['source']))
with (OUT/'Каталог.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['source','category','preview','frames','width','height','palette'],delimiter=';');w.writeheader();w.writerows(rows)
result={'status':'complete' if not errors and not bad else 'completed_with_errors','stats':dict(stats),'categories':dict(cats),'errors':errors,'copy_verification_failures':bad,'original_art_coverage':{'expected':len(names),'present':len(names)-len(rawmissing)},'verified_pairs':sum(p['verified_pairs'] for p in parts),'resources':rows}
result['resolved_legacy_formats']=resolved;result['verified_pairs']+=repair['verified_pairs']
result['raster_coverage']={'expected':len(expected_rasters),'exported':len(rows)}
(OUT/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
size=json.loads((OUT/'verification.json').read_text(encoding='utf-8'))['verified_bytes']
readme='''FALLOUT 1 — БИБЛИОТЕКА ОРИГИНАЛЬНОЙ ГРАФИКИ

КАК ПРОСМАТРИВАТЬ
Откройте категорию, затем подпапку «Превью». Там по одному PNG на ресурс.
В Проводнике выберите «Вид → Огромные значки»; мелкие оригиналы удобнее
открывать в просмотрщике с увеличением. «Кадры» содержит все уникальные
кадры анимаций. «Метаданные» сохраняет размеры, FPS и логические offsets.
Исходные поля холста сохранены, PNG не увеличивались и не перерисовывались.

КАТЕГОРИИ
01_Гуманоиды — люди и человекоподобные мутанты, по семействам внешности.
02_Существа — животные и монстры; сюда входят и мирные животные.
03_Роботы — роботы, включая Mr. Handy, Robobrain и Eyebot.
04_Оружие — изображения в инвентаре и на земле.
05_Броня — изображения брони; надетая броня также среди гуманоидов.
06_Боеприпасы — патроны и другие боеприпасы из прототипов.
07_Окружение — пол/крыши, стены, объекты и декор.
08_Предметы — лекарства, контейнеры, ключи, прочее и общие изображения.
09_Интерфейс — экраны, кнопки, курсоры и прочая UI-графика.
10_Говорящие_головы — портреты и их кадры.
11_Фоны — фоновые изображения.
12_Иллюстрации_навыков — изображения skilldex.
13_Заставки — RIX, преобразованные в PNG, и исходники.
14_Эффекты_и_служебная_графика — ресурсы art/misc.
15_Ролики_исходники — оригинальные MVE и сопровождающие файлы.

ПАПКА «00_ВСЁ»
Полная независимая копия всех изображений, кадров, метаданных и исходных
ресурсов art/ из MASTER.DAT и CRITTER.DAT. Сохранена и основная color.pal.
Копии не являются жёсткими ссылками. В «Превью» ресурсы сгруппированы
только по исходным папкам игры. Все кадры находятся в «Кадры».
Ролики сохранены в MVE; звук, карты и скрипты не относятся к текстурам.
Шесть GIF с расширением .001 тоже преобразованы в PNG.

КЛАССИФИКАЦИЯ И ОГРАНИЧЕНИЯ
Оружие/броня/предметы определены по оригинальным прототипам. Если один
ресурс используется разными типами предметов, он выделен в общую группу.
Гуманоиды/существа/роботы сгруппированы по семействам графики.
Враждебность задаёт игра: один спрайт бывает и врагом, и мирным NPC.
Анимации оружия в руках остаются вместе с соответствующим персонажем.

PNG имеет исходный размер и RGBA. Индекс 0 прозрачен у игровых объектов;
UI/фоны сохраняют непрозрачный холст. Освещение карты и циклы палитры не
запечены. Исходные индексированные пиксели сохранены в FRM, палитры в PAL.
Для отдельной палитры того же имени используется она; иначе color.pal.
У файлов .fr0–.fr5 номер расширения определяет направление. Их заголовок
иногда хранит размер общего набора, поэтому разобран фактический payload;
исходный заголовок и оригинальные байты не менялись. Общие направления
FRM не размножены: соответствия указаны в direction_aliases метаданных.
Старый oknife.frm версии 3 также декодирован; исходный файл сохранён.

Для ComfyUI берите PNG, работайте в отдельной копии. Для интеграции
сохраняйте исходное имя и метаданные. Графика игры от этого экспорта
не меняется. DAT, исходники движка, runtime и AGENTS.md не изменялись.

Каталог.csv — поиск по имени и категории. manifest.json — полный отчёт.
'''
readme+='\nРЕЗУЛЬТАТ\n'+json.dumps({**dict(stats),'verified_pairs':result['verified_pairs'],'errors':errors,'copy_verification_failures':bad,'total_bytes':size},ensure_ascii=False,indent=2)+'\n'
(OUT/'README.txt').write_text(readme,encoding='utf-8-sig')
(ROOT/'work/asset-library-export/task.json').write_text(json.dumps({'scope':'Export original art from both DAT archives into categories and an independent full copy','output':str(OUT),'status':result['status'],'stats':dict(stats),'bytes':size,'runtime_changed':False,'source_archives_changed':False,'limitations':errors},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='resources'},ensure_ascii=False));print('Total GiB:',round(size/2**30,2))
