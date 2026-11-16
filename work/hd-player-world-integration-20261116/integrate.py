"""Stage or install the approved player package without replacing cave resources."""
from pathlib import Path
import argparse, hashlib, json, shutil
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];WORK=Path(__file__).resolve().parent
BUILD=ROOT/'build/hd-player-world-integration-20261116'
LIVE=ROOT/'runtime/hd-world-pilot';STAGE=WORK/'runtime'
SOURCE=ROOT/'work/hd-world-pilot/fallout1-ce-main'
PACKAGE=ROOT/'assets/hd/player-male-vault13/lighting-v2-x4'
EXE=ROOT/'build/hd-world-pilot/msvc/RelWithDebInfo/fallout-ce.exe'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,value):p.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8')
def inventory(base):return {p.relative_to(base).as_posix():sha(p) for p in sorted(base.rglob('*')) if p.is_file()}
args=argparse.ArgumentParser();args.add_argument('mode',choices=['stage','install']);mode=args.parse_args().mode
baseline=read(WORK/'baseline.json');merge=read(WORK/'source-merge.json')
assert inventory(SOURCE)==merge['source_hashes'],'Shared source changed after merge'
assert sha(EXE)==read(ROOT/'build/hd-world-pilot/logs/build-manifest.json')['executable_sha256'].lower()
for r in read(ROOT/'build/hd-world-pilot/logs/source-hashes.json'):
    assert sha(SOURCE/r['path'])==r['sha256'].lower()
files={'fallout-ce.exe':EXE}
files.update({'data/art/hd/player-male-vault13/'+name:PACKAGE/name for name in baseline['asset_names']})
expected={name:sha(p) for name,p in files.items()}
if mode=='stage':
    assert read(BUILD/'baseline-player/result.json')['failed']==0
    for name,p in files.items():
        target=STAGE/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
        assert sha(target)==expected[name]
    write(WORK/'candidate.json',{'files':expected,'executable_sha256':sha(EXE)})
    print(json.dumps({'staged_files':len(files),'executable_sha256':sha(EXE)}))
else:
    assert not (BUILD/'integration.json').exists(),'This integration was already installed'
    candidate=read(WORK/'candidate.json');assert candidate['files']==expected
    player=read(BUILD/'verified-player/manifest.json');menu=read(BUILD/'verified-menu/manifest.json')
    assert player['result']['failed']==0 and player['result']['passed']==403
    assert menu['failed']==0 and menu['passed']==139
    assert player['executable_sha256'].lower()==menu['executable_sha256'].lower()==sha(EXE)
    for name,digest in expected.items():assert sha(STAGE/name)==digest
    # A full HD environment capture with the original actor must remain exact.
    preserved_captures=[]
    for name in ['player-classic-cave-hd.png','fallback-female.png','fallback-running.png']:
        before=Image.open(BUILD/'baseline-player'/name).convert('RGB')
        after=Image.open(BUILD/'verified-player'/name).convert('RGB')
        assert before.size==after.size and before.tobytes()==after.tobytes(),name
        preserved_captures.append(name)
    current=inventory(LIVE)
    assert current==baseline['runtime'],'Live files changed since snapshot; review before installation'
    for name,digest in baseline['protected'].items():assert sha(ROOT/name)==digest
    for name,p in files.items():
        target=LIVE/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
        assert sha(target)==expected[name]
    after=inventory(LIVE)
    preserved={name:digest for name,digest in current.items() if name not in files}
    assert all(after.get(name)==digest for name,digest in preserved.items())
    assert set(after)==set(current)|set(files)
    for name,digest in baseline['protected'].items():assert sha(ROOT/name)==digest
    preservation={'unchanged_runtime_files':len(preserved),'unchanged_runtime_sha256':preserved,
        'changed_runtime_files':[name for name,value in current.items() if after.get(name)!=value],
        'added_runtime_files':sorted(set(after)-set(current)),
        'pixel_identical_environment_captures':preserved_captures,
        'config_and_saves_preserved':True,'launcher_preserved':True,'AGENTS_md_preserved':True}
    write(BUILD/'preservation.json',preservation)
    report={'status':'installed and verified in main cave runtime','date':'2026-11-16',
        'runtime':str(LIVE),'launcher':'Start-Fallout-HD-World-Pilot.cmd',
        'executable_sha256':sha(EXE),'previous_executable_sha256':baseline['runtime_executable_before'],
        'package':str(PACKAGE),'idle_directions':6,'walk_frames':48,'walk_fps':10,
        'body_frames':54,'pose_shadow_masks':54,'package_files_verified':len(files)-1,
        'source_changes':merge['changed_files'],'backup':baseline['backup'],
        'tests':{'player':player['result'],'menu':{'passed':menu['passed'],'failed':menu['failed']}},
        'test_runtime':str(STAGE),'tested_executable_and_player_files_identical_to_installed':True,
        'baseline_player':read(BUILD/'baseline-player/result.json'),
        'unchanged_runtime_files':len(preserved),'pixel_identical_environment_captures':preserved_captures,
        'preservation_report':str(BUILD/'preservation.json'),
        'limitations':['Male unarmed stand/walk only; other actions use classic fallback',
            'Tests ran on a fresh copy of the current main runtime; installed executable and package hashes match',
            'Existing cave artwork and registries were preserved; this is not a new full gameplay walkthrough'],
        'historical_components':{'rats':'build/hd-rat-world-integration-20261115/integration.json',
            'walls':'build/hd-wall-grey-match-20261116/integration.json',
            'approved_player':'work/hd-player-lighting-20261116/integration.json'}}
    write(BUILD/'integration.json',report)
    write(ROOT/'build/hd-world-pilot/integration-manifest.json',report)
    write(ROOT/'work/hd-world-pilot/task.json',{
        'task':'Approved male Vault13 lighting and walk integrated into current cave',
        'date':'2026-11-16','status':report['status'],'runtime':'runtime/hd-world-pilot',
        'launcher':report['launcher'],'executable_sha256':report['executable_sha256'],
        'package':'assets/hd/player-male-vault13/lighting-v2-x4',
        'final_report':'build/hd-player-world-integration-20261116/integration.json',
        'preservation_report':'build/hd-player-world-integration-20261116/preservation.json',
        'backup':report['backup'],'historical_components':report['historical_components']})
    summary=f'''FALLOUT 1 CE — ОСНОВНАЯ HD-ПЕЩЕРА, 16 НОЯБРЯ 2026

Запуск: Start-Fallout-HD-World-Pilot.cmd — обычное меню основной пещеры.
F11 — HD/оригинал. После установки новых файлов перезапустить игру.
Подключён одобренный мужской персонаж Убежища 13: 6 направлений стойки,
48 кадров ходьбы (10 кадр/с), светотень на теле и 54 напольные маски по позам.
Исправлено чтение персонажа сквозь переднюю стену: полосы устранены.
Для неподдерживаемых действий/оружия/других персонажей остаётся оригинал.
hd_player_male=1 сохранён; hd_player_shadow по умолчанию включён в коде.
Настройки и сохранения не перезаписывались.

Сохранены все {len(preserved)} остальных runtime-файлов: текущее окружение,
стены и срез, крысы, скелет, предметы, HUD, меню и реестры окружения.
Три фиксированных игровых кадра с классическим персонажем/HD-окружением
до и после совпали пиксельно. Ассеты окружающего мира не переустанавливались.
Исходники основной пещеры получили только 8 файлов изменений персонажа.

Новые проверки на копии актуального runtime: игрок 403 PASS/0 FAIL,
меню 139 PASS/0 FAIL. EXE и пакет после установки совпадают с проверенными.
Контроль старой сборки: игрок 228 PASS/0 FAIL (исторический, отдельно).
Не заявляется полное ручное прохождение или новые проверки всех существ.
EXE SHA256: {report['executable_sha256']}
Отчёт: build/hd-player-world-integration-20261116/integration.json
Сохранность: build/hd-player-world-integration-20261116/preservation.json
Резервная копия: build/backups/before-world-player-lighting-20261116
Инструменты: work/hd-player-world-integration-20261116

Исходники: work/hd-world-pilot/fallout1-ce-main
Обычная сборка: work/hd-world-pilot/tools/build.ps1 -Jobs 6
Не запускать прежние общие установщики ассетов поверх актуальной пещеры.
История крысы: build/hd-rat-world-integration-20261115/integration.json
История стен: build/hd-wall-grey-match-20261116/integration.json
Старая общая сводка сохранена в резервной копии. AGENTS.md не изменялся.
'''
    (ROOT/'work/hd-world-pilot/README.txt').write_text(summary,encoding='utf-8')
    target_after={name:sha(ROOT/name) for name in baseline['target_before']}
    write(WORK/'installed-files.json',{'before':baseline['target_before'],'after':target_after,'backup':baseline['backup']})
    print(json.dumps({'installed':True,'exe':sha(EXE),'preserved_runtime_files':len(preserved),
        'package_files':len(files)-1,'pixel_identical_environment_captures':preserved_captures,'tests':report['tests']}))
