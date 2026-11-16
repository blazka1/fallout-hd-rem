"""Verify preservation, then publish the actual installed state and requested AGENTS update."""
from pathlib import Path
from datetime import datetime,timezone
import configparser,hashlib,json,shutil,struct
from PIL import Image,ImageChops
R=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent
B=R/'build/hd-rat-world-integration-20261115';RT=R/'runtime/hd-world-pilot'
S=R/'work/hd-world-pilot/fallout1-ce-main';P=R/'assets/hd/critter-rat/qwen21-seedvr2-v1-x4'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
save=lambda p,x:p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
base=read(B/'baseline.json');install=read(B/'installation.json');merge=read(B/'source-merge.json')
exe=sha(RT/'fallout-ce.exe');assert exe==install['executable_sha256']
assert exe==sha(R/'build/hd-world-pilot/msvc/RelWithDebInfo/fallout-ce.exe')
changed=[n for n,h in base['runtime'].items() if not (RT/n).is_file() or sha(RT/n)!=h]
assert set(changed)=={'fallout-ce.exe','fallout.cfg'},changed
prior=set(base['runtime']);added={p.relative_to(RT).as_posix() for p in RT.rglob('*') if p.is_file()}-prior
assert len(added)==378 and all(n.startswith('data/art/hd/critter-rat/') for n in added),added
for name,digest in merge['source_hashes'].items():assert sha(S/name)==digest,name
assert sha(R/'HD-TEXTURE-GUIDE.md')==base['documents']['HD-TEXTURE-GUIDE.md']
assert sha(R/'AGENTS.md')==base['documents']['AGENTS.md']
assert (R/'Start-Fallout-HD-World-Pilot.cmd').read_bytes()==(R/base['backup']/'Start-Fallout-HD-World-Pilot.cmd').read_bytes()
before_cfg=configparser.ConfigParser();after_cfg=configparser.ConfigParser()
before_cfg.read(R/base['backup']/'runtime/hd-world-pilot/fallout.cfg',encoding='utf-8-sig')
after_cfg.read(RT/'fallout.cfg',encoding='utf-8-sig')
before_cfg.set('remaster','hd_rat','1')
assert {s:dict(before_cfg[s]) for s in before_cfg.sections()}=={s:dict(after_cfg[s]) for s in after_cfg.sections()}
reports={}
for mode in ['rat','world','menu','player','hud','missing-frame','corrupt-frame','missing-aimed','corrupt-aimed']:
    path=B/'verified'/mode/'manifest.json';j=read(path);res=j['result']
    assert j['executable_sha256'].lower()==exe and j['exit_code']==0 and res['failed']==0,(mode,j)
    reports[mode]=dict(file=path.relative_to(R).as_posix(),passed=res['passed'],failed=res['failed'],sha256=sha(path))
rat=read(B/'verified/rat/result.json');assert rat['world_frames']==rat['rendered_frames']==rat['rat_keys']==540 and rat['missing_frames']==0
before=read(B/'before/manifest.json');assert before['executable_sha256'].lower()==base['runtime_exe_sha256']
assert before['result']['failed']==0
pairs=[]
for old in sorted((B/'before').glob('*.png')):
    # These suites choose an example object from pointer-ordered collections;
    # their camera/subject may differ across processes. Fixed views are comparable.
    if old.name.startswith(('new-form-','wall-geometry-')):continue
    new=B/'verified/world'/old.name;assert new.is_file(),new
    a=Image.open(old).convert('RGB');b=Image.open(new).convert('RGB')
    assert a.size==b.size and ImageChops.difference(a,b).getbbox() is None,('Environment capture differs',old.name)
    pairs.append(dict(file=old.name,pixels_equal=True,before_sha256=sha(old),after_sha256=sha(new)))
assert len(pairs)>=30
manifest=read(P/'manifest.json')
for im in manifest['images']:
    png=P/'frames'/im['png'];rgba=RT/'data/art/hd/critter-rat'/im['runtime_file']
    assert sha(png)==im['png_sha256'] and sha(rgba)==im['runtime_sha256']
    decoded=Image.open(png).convert('RGBA');data=rgba.read_bytes()
    assert struct.unpack('<4sIIII',data[:20])==(b'F1HD',1,decoded.width,decoded.height,4)
    assert decoded.tobytes()==data[20:]
geometry=RT/'data/art/hd/world-pilot/wall-geometry.tsv'
placements=[s for s in geometry.read_text().splitlines() if s.strip() and not s.startswith('#')]
assert len(placements)==417
save(B/'preservation.json',dict(unchanged_prior_runtime_files=1008,modified_prior_files=changed,new_rat_files=len(added),
    previous_config_values_preserved=True,added_config='[remaster] hd_rat=1',
    unchanged_environment_images_and_registries=True,wall_geometry_placements=len(placements),
    compared_world_captures=len(pairs),all_capture_pixels_equal=True,captures=pairs,
    original_runtime_hashes=base['runtime']))
receipt=dict(status='installed and verified in current world pilot',created_utc=datetime.now(timezone.utc).isoformat(),
    runtime='runtime/hd-world-pilot',launcher='Start-Fallout-HD-World-Pilot.cmd',executable_sha256=exe,
    previous_executable_sha256=base['runtime_exe_sha256'],backup=base['backup'],
    rat_package=P.relative_to(R).as_posix(),qwen_panels=37,seedvr2_panels=37,unique_rat_images=376,
    world_animation_keys=540,aimed_diagram_images=1,original_map_rats=20,world_owner=254,wall_geometry_owner=253,
    unchanged_prior_runtime_files=1008,modified_prior_files=changed,added_rat_files=378,
    baseline_checks=before['result'],reports=reports,checks_total=sum(x['passed'] for x in reports.values()),failed=0,
    environment_captures_equal=len(pairs),preservation_report='build/hd-rat-world-integration-20261115/preservation.json',
    source_merge_report='build/hd-rat-world-integration-20261115/source-merge.json',
    legacy_player_test_diagnostic=dict(before='player-before/manifest.json',initial='player/manifest.json',
        baseline_result='227 PASS, 1 FAIL on both pre-rat and initial rat EXE',
        cause='Legacy assertion treated translucent wall cells as opaque; final diagnostic checks actual full opacity.'),
    limits=['Rat silhouette, timing, offsets, gameplay and original archives remain unchanged.',
        'Full rat pose rendering and timed walking were tested; no full combat playthrough claimed.',
        'Partial/full floor-boundary differences match the classic-rat control.'])
installed=read(RT/'data/art/hd/critter-rat/manifest.json')
installed.update(status=receipt['status'],validation=reports,world_integration_report='build/hd-rat-world-integration-20261115/integration.json')
save(RT/'data/art/hd/critter-rat/manifest.json',installed)
save(B/'integration.json',receipt)
save(R/'build/hd-world-pilot/integration-manifest.json',receipt)
state=dict(task='HD ordinary rats integrated into the latest cave environment',date='2026-11-15',status=receipt['status'],
    runtime=receipt['runtime'],launcher=receipt['launcher'],executable_sha256=exe,package=receipt['rat_package'],
    final_report='build/hd-rat-world-integration-20261115/integration.json',preservation_report=receipt['preservation_report'],
    backup=base['backup'],historical_task_snapshot=base['backup']+'/work/hd-world-pilot/task.json',
    known_scope_exclusions='Other creatures and maps unchanged; male player HD coverage remains the pre-existing stand/walk set.')
save(W/'task.json',state);save(R/'work/hd-world-pilot/task.json',state)
readme=f'''FALLOUT 1 CE — ТЕКУЩАЯ ПЕЩЕРА С HD-КРЫСАМИ, 15 НОЯБРЯ 2026

Запуск: Start-Fallout-HD-World-Pilot.cmd — обычное главное меню.
Start-Fallout-HD-Player-Pilot.cmd — новая игра в первой пещере.
F11 — HD/оригинал мира. После установки перезапустить игру.
[remaster] hd_rat=1 включён в fallout.cfg; 0 отключает крысу после перезапуска.
376 изображений Qwen Image 2.1 + SeedVR2 x4: 375 кадров и прицельная схема.
Все 540 сочетаний animation/direction/frame и 20 исходных крыс сохранены.
Новые текстуры установлены также в обычный runtime/hd-world-pilot.
Отдельный hd-rat-pilot остаётся исторической тестовой сборкой на более старом окружении.

Все 1008 прежних runtime-файлов, кроме EXE и fallout.cfg, совпадают с базой.
Последние стены V4, 417 размещений геометрии, материалы среза, варианты пола,
рама убежища V4, терминал V5, декорации, скелет, игрок и 8 предметов сохранены.
{len(pairs)} игровых кадров окружения с фиксированными ракурсами до/после совпали попиксельно.
Крыса использует owner254, геометрия стен сохраняет owner253.
Прицел подключён в настоящее окно CE; UI остался прежним.

Текущие проверки: {json.dumps({k:v['passed'] for k,v in reports.items()},ensure_ascii=False)}.
Все 0 FAIL; всего {receipt['checks_total']} PASS на текущем EXE.
Контроль до установки: {before['result']['passed']} PASS, 0 FAIL на прежнем EXE.
Это программные проверки и просмотр кадров, не полное прохождение боя.
EXE SHA256: {exe}
Отчёт: build/hd-rat-world-integration-20261115/integration.json.
Сверка окружения: build/hd-rat-world-integration-20261115/preservation.json.
Резервная копия: {base['backup']}.

Исходники: work/hd-world-pilot/fallout1-ce-main.
Сборка: work/hd-world-pilot/tools/build.ps1 -Jobs 3.
Проверки этой интеграции: work/hd-rat-world-integration-20261115/test.ps1.
Не запускать старые общие установщики: они могут вернуть прежние EXE/ассеты.
install.py этого компонента одноразовый и проверяет точную исходную базу.
Предыдущие task/README/общая сводка сохранены в резервной копии.
AGENTS.md обновлён по прямому запросу пользователя, актуальный раздел13.
'''
for p in [W/'README.txt',R/'work/hd-world-pilot/README.txt']:p.write_text(readme,encoding='utf-8')

agents=R/'AGENTS.md';text=agents.read_text(encoding='utf-8')
intro='**Добавлено по прямому запросу пользователя 15 ноября 2026 года:** полный HD-набор обычной крысы подключён к **обычной сборке пещеры `Start-Fallout-HD-World-Pilot.cmd`** с сохранением всех последних файлов окружения. Актуальный EXE, проверки и точка продолжения — **раздел 13**. Раздел 12 сохраняет состояние своего этапа; его старый EXE не устанавливать поверх нового.\n\n'
marker='**Обновлять этот файл только по прямому запросу пользователя.**'
assert text.count(marker)==1;text=text.replace(marker,intro+marker)
old=next(line for line in text.splitlines() if line.startswith('- **Актуальная точка продолжения'))
text=text.replace(old,'- **Актуальная точка продолжения — раздел 13.** В `runtime/hd-world-pilot` объединены HD-крысы и последнее окружение на 15 ноября: стены/срез V4, 417 размещений геометрии и текущие варианты пола. Рама `vault-surface-fixes-v4`, терминал `terminal-detail-v5`, дверь и внутренний металл сохранены. Все прежние ассеты и реестры сверены побайтно, игровые кадры окружения — попиксельно. Старые общие установщики не запускать поверх текущей сборки.')
old=next(line for line in text.splitlines() if line.startswith('- Выбор персонажа, загрузка и настройки'))
text=text.replace(old,'- Выбор персонажа, загрузка, настройки и фон HUD остаются классическими. В текущем runtime сохранены HD-иконки 8 предметов (Knife, 10mm pistol, brass knuckles, 10mm JHP/AP, stimpak, flare unlit/lit), HD-игрок в стойке/ходьбе и скелет. **Обычная крыса теперь HD во всех 540 исходных позах и в схеме прицеливания**; другие существа этим этапом не обновлялись. Универсальная замена всей графики игры не выполнена.')
old='| `assets/hd/v13ent/v13-varied-decor-x4/` | Выбранные PNG, метаданные и манифест текущих 205 изображений |'
text=text.replace(old,'| `assets/hd/v13ent/v13-varied-decor-x4/` | Исторический пакет V13, 205 изображений; не переустанавливать поверх новых компонентов |')
text=text.replace('текущий пакет и изолированные исходники указаны в разделе 10.',
    'исторический пакет V13 описан в разделе 10, актуальная сборка и исходники — в разделе 13.')
text=text.replace('Последние изменения материалов и терминала V5 **не пересобирали EXE**. Актуальный установленный `runtime/hd-world-pilot/fallout-ce.exe`:',
    'Последние изменения материалов и терминала V5 **не пересобирали EXE**. Ниже сохранён **исторический EXE этапа раздела 12**; текущий установленный EXE после интеграции крысы указан в разделе 13:')
text=text.replace('Последними игровыми проверками остаются **346 PASS, 0 FAIL от 14 ноября**;',
    'Для зафиксированного здесь этапа последними игровыми проверками были **346 PASS, 0 FAIL от 14 ноября** (текущий прогон — раздел 13);')
rows='\n'.join(f'| {k} | {v["passed"]} | 0 | `{v["file"]}` |' for k,v in reports.items())
section=f'''## 13. HD-крысы в обычной сборке пещеры — 15 ноября 2026

По прямому запросу пользователя HD-крысы перенесены из отдельного `hd-rat-pilot`
в **текущий `runtime/hd-world-pilot`**, который запускается через
**`Start-Fallout-HD-World-Pilot.cmd`**. Этот ярлык и обычное меню сохранены.
Отдельный `Start-Fallout-HD-Rat-Pilot.cmd` остаётся тестовой копией с более старым
окружением; для общей пещеры использовать World-Pilot. Игра допускает один экземпляр.

### Что подключено

- Обычная крыса `masrat`, art index24, PID `0x01000030`: **375 уникальных кадров мира + 1 схема прицеливания**, всего **376 PNG x4**, все **540 сочетаний animation/direction/frame**. С шестью ссылками на схему — 546 направленных кадров исходной инвентаризации. Все 20 исходных крыс карты сохранены.
- Qwen Image2.1 INT8 + SeedVR2 3B INT8: **37/37 листов каждого этапа завершены**. Новая генерация при переносе не выполнялась. Пакет: `assets/hd/critter-rat/qwen21-seedvr2-v1-x4`; происхождение, workflow, API-prompt, job ID и хеши — `assets/generated/critter-rat/qwen21-seedvr2-v1-20261115`.
- Runtime: `data/art/hd/critter-rat/` — 376 F1HD RGBA8, `registry.tsv` (540 ключей), `manifest.json`. Все RGBA сверены с декодированными PNG побайтно. Выбранная схема — `prepared-aimed-v4`; её прямые линии наведения и внешний холст сохранены точно.
- Исходная бинарная маска игровых кадров, размеры, offsets, FPS/action frame и логика CE не менялись. Оригинальные DAT/MAP/FRM не заменялись. F11 переключает HD/оригинал мира. Настройка `[remaster] hd_rat=1` включена явно; `0` отключает HD-крысу после перезапуска.

### Как сохранено последнее окружение

Интеграция сделана небольшими правками **свежих** исходников
`work/hd-world-pilot/fallout1-ce-main`; старое дерево тестовой крысы целиком не копировалось.
Сохранены новая геометрия стен, кэш прозрачности и современные проверки перекрытий.
До установки EXE имел SHA256 `{base['runtime_exe_sha256']}`.

**1008 прежних файлов runtime совпали побайтно.** Из прежних файлов изменились только
`fallout-ce.exe` и `fallout.cfg` (добавлено `hd_rat=1`); добавлены 378 файлов крысы.
Все существовавшие изображения, реестры, настройки разрешения и сохранения сохранены.
Это включает раму/терминал раздела12, стены и каменный срез V4
(`assets/hd/v13ent/wall-crown-v4`),
417 размещений геометрии, текущие варианты пола, декор, скелет, игрок и 8 предметов.
**{len(pairs)} игровых кадров окружения с фиксированными ракурсами до/после совпали попиксельно** при выключенной
крысе в контрольном world-harness; это отдельная сверка помимо хешей ассетов.

Код: `hd_rat.cc/.h`, `hd_world_pilot.cc/.h`, один вызов в `object.cc`;
схема прицела — `hd_hud.cc` и реальное окно в `combat.cc`.
Для крысы зарезервирован **owner254**; **owner253 оставлен геометрии стен**,
owner252 — отдельному камню у входа. `hd_cave_variety.inc` учитывает HD-крысу под
полупрозрачной стеной; прежняя логика стен сохранена.
Новые ресурсы не назначать на эти ID. Тесты крысы — `hd_rat_test.inc`.

### Установленный EXE и проверки

`runtime/hd-world-pilot/fallout-ce.exe` и
`build/hd-world-pilot/msvc/RelWithDebInfo/fallout-ce.exe` совпадают:

`{exe.upper()}`

Текущие проверки на этом EXE:

| Проверка | PASS | FAIL | Отчёт |
| --- | ---: | ---: | --- |
{rows}

Всего **{receipt['checks_total']} PASS, 0 FAIL**. Контроль до установки:
**{before['result']['passed']} PASS, 0 FAIL** на прежнем EXE; он не прибавляется к текущему итогу.
Проверены все 540 поз через настоящий SDL-рендер, 4K, реальная ходьба через
планировщик CE, обводка, настоящее окно прицела, F11, исходные HP/позиции/блокеры,
повреждённые/отсутствующие кадры, меню, игрок/скелет и инвентарь Knife.
Остальные 7 ранее подключённых предметов сохранены по хешам; отдельные новые
игровые прогоны для каждого из них этим этапом не заявляются.

Небольшие различия границ пола при частичной/полной перерисовке совпали с
контрольной классической крысой; новых следов HD-крыса не добавляет.
Это автоматические проверки и просмотр изображений, **не полное прохождение боя**.
Генерационный QA пакета: 1129 PASS, 0 FAIL, выполнен до этого переноса и подтверждён
совпадением выбранных файлов; он не прибавлен к текущим игровым проверкам.
Старый тест игрока дал одинаковые 227 PASS/1 FAIL на прежнем и первом новом EXE:
он ошибочно считал полупрозрачные ячейки стен полностью непрозрачными.
В финальном harness проверяется фактическая непрозрачность всех 16 субпикселей
и совпадение кэша полупрозрачной стены с полной перерисовкой;
это изменение диагностики, отрисовка и материалы окружения сохранены.
Кадры `new-form-*`/`wall-geometry-*` не включены в сравнение фиксированных ракурсов:
их пример выбирается из коллекции объектов, упорядоченной по адресу в памяти.

### Продолжение, отчёты и откат

- Общая актуальная сводка: `build/hd-world-pilot/integration-manifest.json`.
- Полный отчёт: `build/hd-rat-world-integration-20261115/integration.json`; сохранность всех прежних файлов/кадров: `preservation.json` рядом. Разница исходников: `source-merge.diff`; точные хеши — `source-merge.json`.
- Игровая крыса крупно: `build/hd-rat-world-integration-20261115/verified/rat/rat-detail-4k.png`; прицел: `verified/rat/aimed-hd.png`; текущее окружение: `verified/world/entrance-hd.png`.
- Состояние компонента: `work/hd-world-pilot/task.json`, `README.txt`; инструменты переноса/проверок: `work/hd-rat-world-integration-20261115/`. `install.py` одноразовый, проверяет точную базу. Повторная обычная сборка — `work/hd-world-pilot/tools/build.ps1 -Jobs 3`.
- Резервная копия до переноса и до обновления AGENTS.md: `{base['backup']}`. Содержит исходники, прежний EXE/конфиги, AUTOMAP.DB, AGENTS.md и прежние task/README/общую сводку. Не восстанавливать весь старый пакет окружения ради отката крысы.
- Последние стены V4 и их художественные ограничения сохранены как были; этот перенос не объявляет их окончательно одобренными. История компонента: `build/hd-wall-crown-v4-20261115/integration.json`, `work/hd-wall-crown-v4-20261115/README.txt`.

'''
ending='Этот файл фиксирует концепцию и состояние. **Следующее его обновление — по запросу пользователя.**'
assert text.count(ending)==1;text=text.replace(ending,section+ending)
agents.write_text(text,encoding='utf-8')
save(B/'documentation.json',dict(agents_sha256=sha(agents),backup=base['backup']+'/AGENTS.md',
    hd_texture_guide_unchanged=True,section=13))
print(json.dumps(dict(status=receipt['status'],checks=receipt['checks_total'],failed=0,environment_captures_equal=len(pairs),unchanged_prior_files=1008,exe=exe)))
