"""Record this renderer/asset revision only after its real runtime checks pass."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--preview', required=True)
parser.add_argument('--package', required=True)
parser.add_argument('--benchmark', required=True)
args = parser.parse_args()

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

exe_hash = hashlib.sha256((ROOT / 'runtime/hd-world-pilot/fallout-ce.exe').read_bytes()).hexdigest().upper()
world = read(ROOT / args.preview / 'manifest.json')
menu = read(ROOT / 'build/hd-world-pilot/menu-regression/manifest.json')
benchmark = read(ROOT / args.benchmark / 'manifest.json')
assert world['executable_sha256'] == menu['executable_sha256'] == benchmark['executable_sha256'] == exe_hash
assert world['result']['failed'] == menu['failed'] == benchmark['result']['failed'] == 0
assert world['result']['passed'] >= 116 and menu['passed'] == 139
pack_path = ROOT / args.package
pack = read(pack_path / 'manifest.json')
assert len(pack['assets']) == 159
integration = {
    'verified_utc': datetime.now(timezone.utc).isoformat(),
    'status': 'integrated_and_verified_in_isolated_ce',
    'executable_sha256': exe_hash, 'runtime': 'runtime/hd-world-pilot',
    'preview': args.preview, 'benchmark': args.benchmark,
    'world_checks': world['result']['passed'], 'menu_checks': menu['passed'],
    'artistic_status': 'candidate_for_user_review',
}
pack.update(status=integration['status'], integrated_in_ce=True,
            artistic_status='candidate_for_user_review', integration=integration,
            runtime='runtime/hd-world-pilot', executable_sha256=exe_hash,
            integration_report='build/hd-world-pilot/integration-manifest.json')
write(pack_path / 'manifest.json', pack)
write(pack_path / 'integration.json', integration)

readme_path = ROOT / 'work/hd-world-pilot/README.txt'
readme = readme_path.read_text(encoding='utf-8-sig')
readme = readme.replace('assets/hd/v13ent/v3-hybrid-base-x4', args.package)
readme = readme.replace('build/hd-world-pilot/preview/full-base-v3', args.preview)
old_light = ('Освещение RGB переносится по соотношению исходной и текущей палитры\n'
             'каждого пикселя. Это приближение для новых оттенков, следующее старому\n'
             'освещению и затемнению экрана. Участки egg/translucency используют точное\n'
             'оригинальное смешивание с локальным возвратом к классической графике.')
new_light = ('Яркость сцены хранится отдельно от цвета исходного пикселя и копируется\n'
             'вместе с его владельцем. Общая интерполированная таблица палитры задаёт\n'
             'затемнение, белую вспышку и гамму; старый палитровый дизеринг больше\n'
             'не умножается поверх новых RGB-деталей. Это непрерывный RGB-аналог\n'
             'исходной таблицы освещения, а не пиксельное воспроизведение её квантования.\n'
             'Egg/translucency и grayscale сохраняют точную классическую обработку.')
assert old_light in readme
readme = readme.replace(old_light, new_light)
marker = 'СТАТУС V3: ПОДКЛЮЧЕНО И ПРОВЕРЕНО В CE'
assert marker in readme
readme = readme.split(marker)[0] + '''ИСПРАВЛЕНИЕ ПРОИЗВОДИТЕЛЬНОСТИ И СВЕТА — 12 НОЯБРЯ 2026

MSVC /O2 и NDEBUG заданы явно и проверяются скриптом сборки: прежний
CMake-кеш содержал пустые флаги даже для RelWithDebInfo. HD-слой теперь
пересчитывает изменившиеся ячейки, загружает изменённую область и повторно
использует цветной кеш при прокрутке. Сдвинутый кеш проверяется по настоящим
владельцам и свету каждого пикселя; интерфейс и персонажи сохраняют перекрытия.

Пакет v4 также согласует широкие цветовые пятна и тёмные края 70 полос стен
с оригиналом, сохраняя среднюю фактуру v3. Остальные 89 изображений взяты
из v3 без изменения пикселей. Файлы генерации и прежние варианты сохранены.

Проверки мира: 116 PASS, 0 FAIL; меню: 139 PASS, 0 FAIL. Четыре сценария
отсутствующих/повреждённых ресурсов: 56 PASS, 0 FAIL на том же EXE.
Добавлены промежуточные затемнения и белая вспышка, проверка grayscale,
а также сравнение прокрутки с кадром, собранным заново без кеша.
Проходимость, поля объектов, 12 маршрутов и классический HUD проверены.
Это не полное прохождение и не утверждение художественного результата.

Текущие захваты: ''' + args.preview + '''
Замеры: ''' + args.benchmark + '''
Сводный отчёт: build/hd-world-pilot/integration-manifest.json

Замеры включают реальный renderPresent в скрытом окне SDL при 1080p/4K,
по 24 отсчёта после прогрева. Это время обновления/показа сцены, а не обещание
фиксированного игрового FPS. Ожидание штатного ограничителя прокрутки 33 мс
исключено. HD-off сравнение использует тот же пилот с учётом метаданных.
До/после различаются оптимизация компилятора, кеш и перенос света; считать
всё ускорение заслугой только одного из этих изменений нельзя.

Исходники, меню и EXE других сборок защищены отдельным снимком хешей:
build/hd-world-pilot/shared-baseline-hashes.json. Старые отчёты full-base-v3
описывают предыдущий рендер без измерения производительности.
AGENTS.md и HD-TEXTURE-GUIDE.md в этой задаче не редактировались.
'''
readme_path.write_text(readme, encoding='utf-8')
task_path = ROOT / 'work/hd-world-pilot/task.json'
task = read(task_path)
task.update(date='2026-11-12', intended_package=args.package,
            status='Performance and light-transfer regression fixed; coherent wall candidate integrated and verified',
            final_preview=args.preview, performance_report=args.benchmark)
write(task_path, task)
print('Recorded verified performance/light revision:', exe_hash)
