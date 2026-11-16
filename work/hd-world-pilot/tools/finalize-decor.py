"""Freeze verified V11 receipt and update only this component's documentation."""
from pathlib import Path
import json, hashlib, shutil
ROOT=Path(__file__).resolve().parents[3]
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,data): p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest().upper()
report=read(ROOT/'build/hd-world-pilot/integration-manifest.json')
runtime=ROOT/'runtime/hd-world-pilot'
assets=read(runtime/'data/art/hd/world-pilot/manifest.json')
assert sha(runtime/'fallout-ce.exe')==report['executable_sha256']
assert assets['asset_count']==202 and len(assets['decoration_placements'])==4
assert all(sha(runtime/e['runtime_file'])==e['runtime_file_sha256'].upper() for e in assets['assets'])
for name,field in [('decor.tsv','decor_registry_sha256'),('decor-placements.tsv','decor_placements_sha256')]:
    assert sha(runtime/'data/art/hd/world-pilot'/name)==assets[field].upper()
assert report['world_checks']['passed']==211 and report['world_checks']['failed']==0
receipt='build/hd-world-pilot/floor-decor-v11-integration.json'
shutil.copyfile(ROOT/'build/hd-world-pilot/integration-manifest.json',ROOT/receipt)
p=ROOT/'work/hd-world-pilot/task.json';m=read(p)
m.update(task='Four render-only floor decorations integrated into first cave',
    user_scope='Install bones, household litter, mushrooms and low stalagmites in isolated pilot; fit scale and light; preserve passability and menu',
    art_workflow='Existing ImageGen candidates; ComfyUI deterministic crop, scale, neutralization/gain and native binary alpha',
    intended_package='assets/hd/v13ent/v11-floor-decor-x4',
    status='V11 integrated and verified: four decorative images and four passable placements; 211 world checks; zero failures',
    final_preview='build/hd-world-pilot/preview/floor-decor-v11',
    performance_report='build/hd-world-pilot/benchmark/floor-decor-v11-after',
    performance_baseline='build/hd-world-pilot/benchmark/floor-decor-v11-before',
    performance_limit='24 hidden-window renderPresent CPU samples per case; not gameplay FPS. 4K scrolling median27.27ms.',
    performance_note='Fresh before/after V11 measurement; no general slowdown observed in this run.',
    frame_fallback_report='build/hd-world-pilot/frame-fallback/20261112-165902-777-15654b6a',
    wall_variant_fallback_report='build/hd-world-pilot/wall-variant-fallback/v11',
    decoration_fallback_report='build/hd-world-pilot/decor-fallback/v11',
    integration_receipt=receipt,executable_sha256=report['executable_sha256'],
    latest_asset_delta={'unchanged_images':198,'new_decoration_images':4,'placements':4,'game_objects_created':0})
m['base_inventory'].update(selected_images=202,decoration_images=4)
for run in ['assets/generated/v13ent-floor-decor/v1-20261112','assets/generated/v13ent-floor-decor/integration-v1-20261112']:
    if run not in m['art_runs']:m['art_runs'].append(run)
write(p,m)
(ROOT/'work/hd-world-pilot/README.txt').write_text('''FALLOUT 1 CE — ДЕКОРАЦИИ ПЕРВОЙ ПЕЩЕРЫ V11

Запуск: Start-Fallout-HD-World-Pilot.cmd. F11 — HD/оригинал в V13ENT.
Для игры ComfyUI и чат не нужны. Сохранения: runtime/hd-world-pilot.
Start-Fallout-HD.cmd относится к отдельной старой сборке меню.

Добавлены четыре предмета: кости, бытовой мусор, пещерные грибы и низкие
сталагмиты. Мусор расположен на подходе к убежищу, кости — у внутреннего
изгиба прохода, грибы и шипы — у правой стены/каменной колонны.
Все четыре видны в стартовом ракурсе. Размеры 54x26, 38x22, 28x20, 30x31
логических пикселей; HD-мастера вчетверо плотнее. Цвет и яркость
подготовлены в ComfyUI; в игре применяются реальный свет карты и вспышки.

Это исключительно отрисовка: новые Object/PID/FID не создаются, коллизий,
событий и взаимодействий нет. Можно пройти через каждый предмет. Кости
и мусор лежат под персонажем; грибы и шипы участвуют в порядке перекрытия.
MAP/SAV, прототипы, исходные DAT/FRM, меню и формат сохранений не изменены.
Работает и при загрузке сохранённой первой пещеры; новой игры не требует.

Пакет: assets/hd/v13ent/v11-floor-decor-x4. Всего 202 изображения:
174 основных кадра, 24 варианта стен, 4 новых декорации в 4 местах.
Все 198 изображений V10 и их метаданные сохранены побайтно, включая
нейтрально-серые стены/камни, ржавое убежище и улучшенный терминал.

Свежие проверки: мир 211, меню 139, fallback 56, кадры 45, варианты 147,
декорации/fallback 117, benchmark 23; ошибок 0. Проверены 120000 гексов,
30000 слов пола/крыши, 12 прежних маршрутов и 4 пути к декорациям,
перекрытия с персонажем, освещение, вспышки, прокрутка и 4K.
При отключении только декораций кадр совпадает с V10 пиксель в пиксель.
308 защищённых исходных файлов не изменились.

Замеры: build/hd-world-pilot/benchmark/floor-decor-v11-{before,after}.
Это время отрисовки скрытого окна, 24 замера на сценарий; не гарантия FPS.
После: полный кадр 1080p 13.28 мс, прокрутка 11.31 мс;
полный кадр 4K 13.18 мс, прокрутка 27.27 мс. Общего замедления в прогоне нет.

Реальные кадры: build/hd-world-pilot/preview/floor-decor-v11.
Крупные планы и разметка: подпапка qa.
Отчёт: build/hd-world-pilot/floor-decor-v11-integration.json.
Параметры/ComfyUI: assets/generated/v13ent-floor-decor/integration-v1-20261112.
Исходные генерации: assets/generated/v13ent-floor-decor/v1-20261112.

После закрытия игры выполнить work/hd-world-pilot/tools/build.ps1,
затем prepare-runtime.ps1 и test.ps1 -OutputDirectory <новая папка>.
Отключить только декорации: [remaster] hd_world_decorations=0
в runtime/hd-world-pilot/fallout.cfg, затем перезапустить. По умолчанию 1.
Варианты стен отдельно: hd_world_wall_variants=0. F11 — весь HD-мир.
Вернуть V10: prepare-runtime.ps1 -AssetsOnly -AssetPackage assets/hd/v13ent/v10-neutral-cave-x4.
Резервная копия EXE/исходников/инструментов/конфига: build/backups/before-floor-decor-v11.
''',encoding='utf-8')
(ROOT/'assets/generated/v13ent-floor-decor/integration-v1-20261112/README.txt').write_text('''V13ENT floor decorations integrated into isolated CE pilot V11.
Source: ../v1-20261112, four original ImageGen candidates preserved.
Preparation: ../prepare-integration.py, existing ComfyUI, deterministic crop,
RGB scale/gain/desaturation and native binary opacity (no diffusion/model).
Prompt cf791e78-80b5-4d05-9280-76d822dd293b. Workflow/API/history/hashes saved here.
Registration/placements: manifest.json and placements.json.
240 bones 54x26 flat tile19491 offsetY13;241 litter 38x22 flat tile18092 offsetY11;
242 mushrooms 28x20 standing tile20087;243 stalagmites 30x31 standing tile19488.
All ground elevation0; HD masters x4; no Object/PID/FID/collision/save data.
Actual ambient/tile lighting and palette fades; existing object tile order.
Selected package assets/hd/v13ent/v11-floor-decor-x4; runtime/hd-world-pilot.
Launcher Start-Fallout-HD-World-Pilot.cmd. F11 HD/original. No ComfyUI needed to play.
Receipt build/hd-world-pilot/floor-decor-v11-integration.json.
Actual SDL captures build/hd-world-pilot/preview/floor-decor-v11.
198 old PNGs and metadata unchanged. Classic and disabled-decor HD match V10 exactly.
Fresh world211/menu139/base56/frame45/wall147/decor117/benchmark23 checks, zero failures.
See work/hd-world-pilot/README.txt for config, rollback and performance limitations.
''',encoding='utf-8')
print('Final runtime:202 verified assets,4 render-only placements; tested EXE hash '+report['executable_sha256'])
