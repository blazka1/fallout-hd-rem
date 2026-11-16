"""Freeze V13 verification and update component-local records only."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,collections,csv
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'build/hd-world-pilot'
PREVIEW=OUT/'preview/varied-decor-v13'
PACKAGE=ROOT/'assets/hd/v13ent/v13-varied-decor-x4'
RUNTIME=ROOT/'runtime/hd-world-pilot'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,obj):p.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
package=read(PACKAGE/'manifest.json');runtime=read(RUNTIME/'data/art/hd/world-pilot/manifest.json')
world=read(PREVIEW/'manifest.json');menu=read(OUT/'menu-regression/manifest.json')
fallback=read(OUT/'decor-fallback/v13/manifest.json')
benchmark=read(OUT/'benchmark/varied-decor-v13-after/manifest.json')
exe=sha(RUNTIME/'fallout-ce.exe')
assert exe==world['executable_sha256']==menu['executable_sha256']==fallback['executable_sha256']==benchmark['executable_sha256']
assert world['result']['failed']==menu['failed']==fallback['failed']==benchmark['result']['failed']==0
assert fallback['restored_and_hash_verified']
assert runtime['asset_count']==205 and runtime['decoration_image_count']==7
assert runtime['selected_manifest_sha256'].upper()==sha(PACKAGE/'manifest.json')
counts=collections.Counter(p['asset_id'] for p in runtime['decoration_placements'])
assert counts=={240:1,241:1,242:5,244:1,245:1,246:5,247:4}
assert {e['asset_id'] for e in runtime['assets'] if e.get('category')=='decoration'}==set(counts)
for entry in runtime['assets']:
    assert sha(RUNTIME/entry['runtime_file'])==entry['runtime_file_sha256'].upper()
    assert sha(RUNTIME/entry['metadata_file'])==entry['metadata_sha256'].upper()
for name,field in [('registry.tsv','registry_sha256'),('variants.tsv','variants_sha256'),('decor.tsv','decor_registry_sha256'),('decor-placements.tsv','decor_placements_sha256')]:
    assert sha(RUNTIME/'data/art/hd/world-pilot'/name)==runtime[field].upper()
protected=[r for r in read(OUT/'shared-baseline-hashes.json')['files'] if r['path'].startswith('fallout1-ce-main/')
    or r['path'].lower().endswith('.exe') or '/data/art/hd/main-menu/' in r['path']]
assert all(sha(ROOT/r['path'])==r['sha256'].upper() for r in protected)
before=read(ROOT/'build/backups/before-scattered-decor-v12/build/hd-world-pilot/logs/source-hashes.json')
after=read(OUT/'logs/source-hashes.json')
old_hashes={r['path']:r['sha256'] for r in before}
changed=[r['path'] for r in after if old_hashes.get(r['path'])!=r['sha256']]
assert set(changed)=={'src/game/hd_world_pilot.cc','src/game/hd_world_pilot.h','src/game/hd_world_pilot_test.cc'},changed
placements=list(csv.DictReader((PREVIEW/'decor-placement-checks.tsv').open(),delimiter='\t'))
assert len(placements)==18 and all(int(r['visible_pixels'])>40 and int(r['path_length'])>0 for r in placements)
previous=read(OUT/'floor-decor-v11-integration.json')
report={
    'recorded_utc':datetime.now(timezone.utc).isoformat(),'status':'integrated_and_verified_in_isolated_ce_pilot',
    'map':'V13ENT.MAP / V13ENT.SAV, ground elevation0','runtime':'runtime/hd-world-pilot',
    'launcher':'Start-Fallout-HD-World-Pilot.cmd','selected_package':str(PACKAGE.relative_to(ROOT)),
    'selected_package_manifest_sha256':sha(PACKAGE/'manifest.json'),'executable_sha256':exe,
    'selected_image_count':205,'unchanged_reused_images':201,'new_images':4,'decoration_image_count':7,
    'density':package['decoration_density'],'variant_counts':dict(counts),'placements':runtime['decoration_placements'],
    'placement_seed':12112026,'randomization':'Saved layout; never rerolled at launch/load. Candidates checked with actual original pathfinder and SDL visibility.',
    'removed_new_spires':True,'original_objects_maps_prototypes_modified':False,'new_game_objects_created':0,
    'world_checks':world['result'],'menu_checks':{'passed':menu['passed'],'failed':0},
    'decoration_fallback_checks':{'passed':fallback['passed'],'failed':0,'asset_id':247,'report':'build/hd-world-pilot/decor-fallback/v13/manifest.json'},
    'historical_checks_not_rerun':{'previous_executable_sha256':previous['executable_sha256'],
        'base_fallback':previous['fallback_checks'],'frame_fallback':previous['frame_fallback_checks'],
        'wall_variant_fallback':previous['wall_variant_fallback_checks']},
    'protected_original_files_verified_unchanged':len(protected),'source_changes_since_v11':changed,
    'source_change_scope':'Extend decorative image IDs240..247 and expose loaded dimensions for generalized placement/occlusion checks; original gameplay and object sorting unchanged.',
    'visual_review':read(PREVIEW/'qa/review.json'),'preview':'build/hd-world-pilot/preview/varied-decor-v13',
    'art':{'generator':'built-in image_gen','masters':'assets/generated/v13ent-floor-decor/variety-v1-20261112',
        'prompts':'assets/generated/v13ent-floor-decor/variety-v1-20261112/prompts.json',
        'preparation':'assets/generated/v13ent-floor-decor/variety-prepared-v1-20261112',
        'comfy_prompt_id':'edde1f27-39ef-4bb2-811a-d701005e99dd',
        'processing':'ComfyUI crop, scale, gain/desaturation, native binary alpha; original generated images preserved'},
    'performance':{'report':'build/hd-world-pilot/benchmark/varied-decor-v13-after/manifest.json',
        'result':benchmark['result'],'historical_comparison':'build/hd-world-pilot/benchmark/floor-decor-v11-after',
        'limit':'24 hidden-window CPU samples per scenario through renderPresent; not a gameplay FPS guarantee.'},
    'limits':['Counts refer to added decorative groups; original map bones/stalagmites preserved.',
        'RGB light and fades follow the existing HD renderer. Static captures and scripted walking/occlusion checks, not a full manual playthrough.',
        'Earlier dense V12 scatter was superseded; its failed occluded locations were excluded from the final layout.']}
write(OUT/'varied-decor-v13-integration.json',report);write(OUT/'integration-manifest.json',report)
p=ROOT/'work/hd-world-pilot/task.json';task=read(p)
task.update(task='Sparse bones and varied mushroom decorations throughout V13ENT',
    user_scope='Add coyote/brahmin bones and two mushroom images; exactly3 added bone piles to14 mushroom groups; remove added spires; preserve walkability/menu',
    intended_package=str(PACKAGE.relative_to(ROOT)),status='V13 integrated:3 bone piles,14 mushroom groups,1 litter;286 world checks,139 menu checks,117 decoration fallback checks,23 benchmark checks;zero failures',
    final_preview='build/hd-world-pilot/preview/varied-decor-v13',integration_receipt='build/hd-world-pilot/varied-decor-v13-integration.json',
    executable_sha256=exe,performance_report='build/hd-world-pilot/benchmark/varied-decor-v13-after',
    performance_baseline='build/hd-world-pilot/benchmark/floor-decor-v11-after',
    performance_limit='24 hidden-window renderPresent CPU samples, not gameplay FPS; 4K scroll median29.23ms.',
    performance_note='Fresh V13 timings; V11 before-run is a historical comparison, not simultaneous measurement.',
    decoration_fallback_report='build/hd-world-pilot/decor-fallback/v13',
    art_workflow='Four new built-in ImageGen sprites, ComfyUI deterministic integration; fixed seeded layout filtered by in-engine visibility.',
    latest_asset_delta={'unchanged_reused_images':201,'new_images':4,'removed_decorative_image_ids':[243],
        'decorative_images':7,'bone_piles':3,'mushroom_groups':14,'litter_piles':1,'game_objects_created':0})
task['base_inventory'].update(selected_images=205,decoration_images=7)
for run in ['assets/generated/v13ent-floor-decor/variety-v1-20261112','assets/generated/v13ent-floor-decor/variety-prepared-v1-20261112']:
    if run not in task['art_runs']:task['art_runs'].append(run)
write(p,task)
(ROOT/'work/hd-world-pilot/README.txt').write_text('''FALLOUT 1 CE — РАЗНООБРАЗНЫЕ ДЕКОРАЦИИ ПЕЩЕРЫ V13

Запуск: Start-Fallout-HD-World-Pilot.cmd. F11 — HD/оригинал в V13ENT.
ComfyUI и чат для игры не нужны. Сохранения: runtime/hd-world-pilot.
Start-Fallout-HD.cmd остаётся отдельной старой сборкой меню.

Новая расстановка по пещере: 3 скопления костей (по одному: прежние,
койот, брамин), 14 групп грибов (5 прежних, 5 дождевиков, 4 колокольчатых),
1 прежняя кучка мусора у убежища. Добавленные шипы полностью отключены.
Исходные предметы карты, включая оригинальные кости и сталагмиты, сохранены.
Всего 18 добавленных мест; сохранённая случайная расстановка не меняется
при перезапуске/загрузке. Новой игры не требует: слой поддерживает MAP/SAV.

Декорации не создают Object/PID/FID, коллизии, события или предметы.
Проходимость, сохранения, прототипы и готовое меню сохранены. Плоские кости
и мусор под ногами; грибы сортируются с персонажем. Цвет/размер подготовлены
в ComfyUI; реальное освещение и вспышки обрабатывает движок.

Пакет: assets/hd/v13ent/v13-varied-decor-x4. 205 изображений:
174 базовых кадра, 24 варианта стен, 7 декоративных изображений.
201 старое изображение и его метаданные сохранены побайтно, 4 — новые.
ImageGen-мастера и промпты: assets/generated/v13ent-floor-decor/variety-v1-20261112.
ComfyUI, маски, параметры и placements.json:
assets/generated/v13ent-floor-decor/variety-prepared-v1-20261112.

Свежие проверки: мир 286, меню 139, fallback нового ID247 117, benchmark23;
ошибок0. Все18 мест видимы и доступны;120000 блокеров,30000 слов пола/крыши,
12 прежних маршрутов и18 путей к декорациям неизменны.
Прежние проверки base/frame/wall fallback относятся к V11, не повторялись.
Без декораций HD-кадр и классический кадр совпадают с V11 пиксель в пиксель.
308 защищённых исходных файлов сохранены.

Кадры: build/hd-world-pilot/preview/varied-decor-v13 (крупные планы в qa).
Отчёт: build/hd-world-pilot/varied-decor-v13-integration.json.
Benchmark: build/hd-world-pilot/benchmark/varied-decor-v13-after.
1080p полный кадр14.15мс, прокрутка11.91мс;4K15.48мс/29.23мс.
Это время скрытого окна (24 замера), не гарантия игрового FPS.

После закрытия игры: tools/build.ps1, затем tools/prepare-runtime.ps1
и tools/test.ps1 -OutputDirectory <новая папка> из этого компонента.
Отключить новые декорации: [remaster] hd_world_decorations=0 в конфиге runtime,
затем перезапустить игру. По умолчанию1. F11 переключает весь HD-мир.
Вернуть V11: prepare-runtime.ps1 -AssetsOnly -AssetPackage assets/hd/v13ent/v11-floor-decor-x4.
Вернуть V10 без декораций: prepare-runtime.ps1 -AssetsOnly -AssetPackage assets/hd/v13ent/v10-neutral-cave-x4.
Резервная копия до задачи: build/backups/before-scattered-decor-v12.
Плотная промежуточная V12 не выбрана; её закрытые стенами места исключены.
''',encoding='utf-8')
(ROOT/'assets/generated/v13ent-floor-decor/variety-v1-20261112/README.txt').write_text('''Four new transparent ImageGen masters, saved byte-for-byte in this directory.
Prompts: prompts.json. Source paths: generation-outputs.json. SHA256/alpha stats: manifest.json.
Built-in image_gen used, not CLI. Model/seed not exposed by the tool; not invented.
Subjects: desert coyote remains, two brahmin skulls with ribs, puffball fungi, inkcap fungi.
Prepared via ComfyUI in ../variety-prepared-v1-20261112; original masters remain unchanged.
Final selected package: assets/hd/v13ent/v13-varied-decor-x4.
Integrated into runtime/hd-world-pilot; receipt build/hd-world-pilot/varied-decor-v13-integration.json.
''',encoding='utf-8')
(ROOT/'assets/generated/v13ent-floor-decor/variety-prepared-v1-20261112/README.txt').write_text('''ComfyUI deterministic preparation of four new ImageGen assets.
Prompt edde1f27-39ef-4bb2-811a-d701005e99dd; workflow/API/history/parameters/hashes retained.
Native dimensions:244 coyote48x23;245 brahmin64x43;246 puffball26x23;247 inkcap24x31.
RGBA masters x4; binary alpha constant within each native4x4 cell. No opaque backdrop.
Final placements.json:3 added bone piles total,14 fungus groups across3 images,1 litter.
Added spires ID243 omitted. Original map objects unchanged. Seed12112026; no runtime RNG.
Locations come from engine-verified reachable floor and actual per-placement visibility tests.
Earlier V12 candidates hidden behind original foreground walls were discarded.
Final runtime uses existing ambient/tile lighting, actor occlusion and HD palette fade logic.
Record: build/hd-world-pilot/varied-decor-v13-integration.json.
''',encoding='utf-8')
print(f'Finalized V13:205 verified assets,18 placements,3 bones/14 fungi/1 litter;{len(protected)} protected originals unchanged.')
