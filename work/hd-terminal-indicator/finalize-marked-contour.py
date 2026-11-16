"""Record the asset-only install after current runtime and image checks."""
from pathlib import Path
from datetime import datetime, timezone
import json, hashlib, shutil
from PIL import Image
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'build/hd-terminal-indicator/user-contour-v3'
BACKUP=ROOT/'build/backups/before-terminal-user-contour-v3-20261114'
PACKAGE=ROOT/'assets/hd/v13ent/terminal-user-contour-v3'
RUNTIME=ROOT/'runtime/hd-world-pilot'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

baseline=read(BACKUP/'baseline.json')
allowed=['runtime/hd-world-pilot/data/art/hd/world-pilot/'+n for n in ['asset-010.rgba','terminal-indicator-on.rgba','manifest.json']]
changed=[p for p,h in baseline.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
assert sorted(changed)==sorted(allowed),changed
exe=sha(RUNTIME/'fallout-ce.exe')
assert exe==baseline['runtime/hd-world-pilot/fallout-ce.exe']
tests=[]
for name in ['loaded','world']:
    path=OUT/name/'manifest.json';m=read(path)
    assert m['executable_sha256'].lower()==exe and m['exit_code']==0
    assert m['result']['failed']==0 and m['result']['passed']>0
    assert m['base_sha256'].lower()==sha(RUNTIME/'data/art/hd/world-pilot/asset-010.rgba')
    assert m['companion_sha256'].lower()==sha(RUNTIME/'data/art/hd/world-pilot/terminal-indicator-on.rgba')
    tests.append(dict(name=name,passed=m['result']['passed'],failed=0,report=str(path)))
assert sum(t['passed'] for t in tests)==345
checks=(OUT/'loaded/checks.txt').read_text()
assert 'PASS removed outline reveals exact real background' in checks and '0 wrong)' in checks
previous=ROOT/'build/hd-terminal-indicator/natural-edge-v2/release'
before=np.array(Image.open(previous/'loaded/terminal-on.png'))
after=np.array(Image.open(OUT/'loaded/terminal-on.png'))
y,x=np.where(np.any(before!=after,axis=2))
assert 0<len(x)<2000 and x.min()>=660 and x.max()<724 and y.min()>=294 and y.max()<407
assert np.array_equal(np.array(Image.open(previous/'world/entrance-classic.png')),np.array(Image.open(OUT/'world/entrance-classic.png')))
pack=read(PACKAGE/'manifest.json')
report=dict(installed_utc=datetime.now(timezone.utc).isoformat(),status='installed_and_verified',
    executable_sha256=exe,executable_unchanged=True,backup=str(BACKUP),package=str(PACKAGE),
    runtime=str(RUNTIME),launcher='Start-Fallout-HD-World-Pilot.cmd',tests=tests,total_passed=345,total_failed=0,
    rgb_exact_previous=pack['rgb_exact_previous'],lamp_and_blink_unchanged=True,
    real_background_exact=True,classic_frame_exact=True,changed_protected_files=changed,
    protected_files_unchanged=len(baseline)-len(changed),
    changed_render_pixels=int(len(x)),changed_render_bounds=[int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)],
    comfy_prompt_id=pack['comfy_prompt_id'],diffusion=False,
    scope='Only terminal matte follows the user red outline. Original RGB, lamp, EXE, gameplay, maps, settings and other runtime art unchanged.',
    preview=str(OUT/'terminal-in-game.png'),comparison=str(OUT/'in-game-comparison.png'))
save(OUT/'integration.json',report)
current=ROOT/'build/hd-terminal-indicator/integration.json'
history=ROOT/'build/hd-terminal-indicator/integration-v2.json'
if not history.exists():shutil.copy2(current,history)
save(current,report)
readme=ROOT/'work/hd-terminal-indicator/README.txt'
old=readme.read_text(encoding='utf-8')
header='''ТЕРМИНАЛ V3 — КОНТУР ПО РАЗМЕТКЕ ПОЛЬЗОВАТЕЛЯ, 14 НОЯБРЯ 2026

Актуальный пакет: assets/hd/v13ent/terminal-user-contour-v3/.
Установлены только asset-010.rgba и terminal-indicator-on.rgba;
обновлены их данные в runtime manifest. EXE и исходники не менялись.
Красная разметка пользователя перенесена в маску через ComfyUI;
удалены выступы фона сверху, справа и у основания. Исходная поддержка
FRM ограничивает маску, canvas/offsets 128x212 остаются прежними.
RGB всех пикселей обоих состояний точно совпадает с V2, лампа сохранена.
Альфа: 0/63/127/191/255. Используется уже установленный renderer V2.
Новой генерации Qwen нет: выполнена точная техническая подготовка маски.

Подготовка: assets/generated/v13ent-terminal/user-contour-v4-20261114/.
Скрипты: prepare-marked-contour.py, package-marked-contour.py,
finalize-marked-contour.py. Workflow, prompt, run и history сохранены.
Проверки установленного EXE: terminal 26 + world 319 = 345 PASS, 0 FAIL.
Фон: 785 прозрачных, 51 сглаженный пиксель, 0 неверных.
Классический кадр и все остальные защищённые файлы совпадают.
Квитанция: build/hd-terminal-indicator/user-contour-v3/integration.json.
Кадр: build/hd-terminal-indicator/user-contour-v3/terminal-in-game.png.
Запуск: Start-Fallout-HD-World-Pilot.cmd; после замены ассетов перезапуск.

ИСТОРИЯ V2 — ОПИСАНИЕ НИЖЕ НЕ ЯВЛЯЕТСЯ ТЕКУЩЕЙ МАСКОЙ

'''
assert not old.startswith('ТЕРМИНАЛ V3')
readme.write_text(header+old,encoding='utf-8')
print(json.dumps(dict(installed=True,passed=345,failed=0,protected_files_unchanged=report['protected_files_unchanged'],changed_render_pixels=len(x))))
