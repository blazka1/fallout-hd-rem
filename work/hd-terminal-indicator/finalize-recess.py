"""Install the verified recess renderer and record the isolated local repair."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil
from PIL import Image
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'build/hd-terminal-indicator/halo-v4'
BACKUP=ROOT/'build/backups/before-terminal-halo-v4-20261114'
RUNTIME=ROOT/'runtime/hd-world-pilot'
PACKAGE=ROOT/'assets/hd/v13ent/terminal-recess-v4'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
baseline=read(BACKUP/'runtime-baseline.json')
changed=[p for p,h in baseline.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
expected=['runtime/hd-world-pilot/data/art/hd/world-pilot/'+n for n in ['asset-016.rgba','manifest.json']]
assert sorted(changed)==sorted(expected),changed
exe=RUNTIME/'fallout-terminal-test.exe';digest=sha(exe)
assert digest==sha(ROOT/'build/hd-world-pilot/msvc/RelWithDebInfo/fallout-ce.exe')
assert digest==read(ROOT/'build/hd-world-pilot/logs/build-manifest.json')['executable_sha256'].lower()
for item in read(ROOT/'build/hd-world-pilot/logs/source-hashes.json'):
    assert sha(ROOT/'work/hd-world-pilot/fallout1-ce-main'/item['path'])==item['sha256'].lower()
tests=[]
for name in ['loaded','world','benchmark','menu','benchmark-comparison']:
    m=read(OUT/name/'manifest.json')
    assert m['executable_sha256'].lower()==digest and m['exit_code']==0
    assert m['result']['passed']>0 and m['result']['failed']==0
    assert m['base_sha256'].lower()==sha(RUNTIME/'data/art/hd/world-pilot/asset-010.rgba')
    assert m['companion_sha256'].lower()==sha(RUNTIME/'data/art/hd/world-pilot/terminal-indicator-on.rgba')
    tests.append(dict(name=name,passed=m['result']['passed'],failed=0,report=str(OUT/name/'manifest.json')))
checks=(OUT/'loaded/checks.txt').read_text()
assert '(480 clean, 0 wrong)' in checks and '(785 clear, 51 antialiased, 0 wrong)' in checks
previous=ROOT/'build/hd-terminal-indicator/user-contour-v3'
before=np.array(Image.open(previous/'loaded/terminal-on.png'))
after=np.array(Image.open(OUT/'loaded/terminal-on.png'))
y,x=np.where(np.any(before!=after,axis=2))
assert 0<len(x)<10000 and x.min()>=652 and x.max()<732 and y.min()>=288 and y.max()<410
assert np.array_equal(np.array(Image.open(previous/'world/entrance-classic.png')),np.array(Image.open(OUT/'world/entrance-classic.png')))
assert np.array_equal(before,np.array(Image.open(OUT/'original-frame-fallback/terminal-on.png')))
oldPerf=read(OUT/'benchmark-old-exe/benchmark.json')['rows']
newPerf=read(OUT/'benchmark-comparison/benchmark.json')['rows']
key=lambda r:(r['requested_width'],r['requested_height'],r['mode'],r['workload'])
oldRows={key(r):r for r in oldPerf}
perf=[dict(resolution=[r['requested_width'],r['requested_height']],mode=r['mode'],workload=r['workload'],
           before_ms=oldRows[key(r)]['median_ms'],after_ms=r['median_ms'],delta_ms=r['median_ms']-oldRows[key(r)]['median_ms']) for r in newPerf]
save(OUT/'performance-comparison.json',dict(scope='Sequential 24-sample hidden SDL CPU timing of old/new EXE with the same repaired artwork; not gameplay FPS.',rows=perf))
shutil.copy2(exe,RUNTIME/'fallout-ce.exe');assert sha(RUNTIME/'fallout-ce.exe')==digest
pack=read(PACKAGE/'manifest.json')
report=dict(installed_utc=datetime.now(timezone.utc).isoformat(),status='installed_and_verified',
    executable_sha256=digest,previous_executable_sha256=baseline['runtime/hd-world-pilot/fallout-ce.exe'],
    package=str(PACKAGE),terminal_package='assets/hd/v13ent/terminal-user-contour-v3',runtime=str(RUNTIME),backup=str(BACKUP),
    launcher='Start-Fallout-HD-World-Pilot.cmd',tests=tests,
    total_passed=sum(t['passed'] for t in tests if t['name']!='benchmark-comparison'),total_failed=0,
    extra_comparison_benchmark_passed=23,
    root_cause='Old terminal-shaped cutout in v13secr3 exposed lower floor/blocker pixels and original green dither after the terminal matte was trimmed.',
    repair='Qwen locally reconstructed the metal panel/sill; Comfy masks restrict changes. HD-only owner fill covers the old recess at the frame draw order.',
    terminal_rgba_files_unchanged=True,lamp_and_blink_unchanged=True,classic_frame_exact=True,original_frame_fallback_pixel_exact=True,
    changed_render_pixels=int(len(x)),changed_render_bounds=[652,288,732,410],
    protected_runtime_files_unchanged=len(baseline)-3,
    runtime_files_changed=expected+['runtime/hd-world-pilot/fallout-ce.exe'],
    qwen_prompt_id=pack['qwen_prompt_id'],comfy_preparation_prompt_id=pack['comfy_preparation_prompt_id'],
    frame_sha256=sha(RUNTIME/'data/art/hd/world-pilot/asset-016.rgba'),
    scope='Single existing Vault frame in V13ENT, bounded 33x53 native recess. Original DAT/MAP/FRM, terminal sprite, gameplay, collision, menus, other art and settings unchanged.',
    performance_report=str(OUT/'performance-comparison.json'),preview=str(OUT/'terminal-in-game.png'))
save(OUT/'integration.json',report)
current=ROOT/'build/hd-terminal-indicator/integration.json';history=ROOT/'build/hd-terminal-indicator/integration-v3.json'
if not history.exists():shutil.copy2(current,history)
save(current,report)
text='''ТЕРМИНАЛ V4 — ФОН БЕЗ ОРЕОЛА, 14 НОЯБРЯ 2026

Под очищенным терминалом обнаружен старый вырез в v13secr3.frm:
он открывал нижний слой пола/блокеров с зелёной сеткой. V3 правильно
восстанавливал фон, но сам фон не был подходящим после сужения силуэта.
Qwen Image 2.1 INT8 в ComfyUI восстановил металл и порог в этом месте.
Взята только локальная область; остальная рама сохранена попиксельно.
Comfy-маска добавляет 1453 native-ячейки в старом вырезе; все они внутри
x73..105/y157..209. Небольшой HD-hook заполняет его при отрисовке рамы.
Исходный framebuffer/FRM, порядок объектов, коллизии и F11 не меняются.
Старый пакет без заполнения альфы остаётся no-op; его кадр совпал точно.

Актуальная рама: assets/hd/v13ent/terminal-recess-v4/.
Терминал и лампа остаются assets/hd/v13ent/terminal-user-contour-v3/.
Оба terminal RGBA byte-identical V3, ритм 500/1100 мс прежний.
Генерация/подготовка: assets/generated/v13ent-terminal/recess-v4-20261114/.
Инструменты: prepare-recess.py, assemble-recess.py, package-recess.py,
finalize-recess.py. EXE установлен только после проверок.
Квитанция: build/hd-terminal-indicator/halo-v4/integration.json.
Проверки: terminal 27, world 319, menu 139, benchmark 23 = 508 PASS.
Дополнительное сравнение производительности: 23 PASS, отдельный отчёт;
скрытое SDL CPU-время не является измерением FPS игрового сеанса.
Новая проверка: 480 ячеек фона рамы, 0 нижнего слоя/зелёной сетки.
Классический кадр совпадает. Меню/проходимость/другие изображения прежние.
Запуск: Start-Fallout-HD-World-Pilot.cmd. Требуется перезапуск игры.

ИСТОРИЯ V3 И НИЖЕ — ПРЕДЫДУЩИЕ ЭТАПЫ

'''
readme=ROOT/'work/hd-terminal-indicator/README.txt';old=readme.read_text(encoding='utf-8')
assert not old.startswith('ТЕРМИНАЛ V4')
readme.write_text(text+old,encoding='utf-8')
(PACKAGE/'README.txt').write_text(text.split('ИСТОРИЯ V3')[0],encoding='utf-8')
print(json.dumps(dict(installed=True,sha256=digest,passed=report['total_passed'],failed=0,protected_unchanged=report['protected_runtime_files_unchanged'])))
