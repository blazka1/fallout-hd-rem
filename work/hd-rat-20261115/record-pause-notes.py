"""Record completed pause accurately; no generation or installation."""
from pathlib import Path
import json
R=Path(__file__).resolve().parents[2];W=Path(__file__).resolve().parent
O=R/'assets/generated/critter-rat/qwen21-seedvr2-v1-20261115'
j=json.loads((O/'pause-state.json').read_text(encoding='utf-8'))
j['known_remaining_work'][-1]='Run final world regression and loaded/corrupt/missing asset checks after finishing the package.'
for p in [O/'pause-state.json',W/'task.json']:p.write_text(json.dumps(j,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
note=f'''ОБЫЧНАЯ КРЫСА ПЕРВОЙ ПЕЩЕРЫ — QWEN IMAGE 2.1 + SEEDVR2

СТАТУС: ПАУЗА ПО ПРЯМОМУ ЗАПРОСУ ПОЛЬЗОВАТЕЛЯ.
Текущая job na-p00 завершена и сохранена. Новые задания не отправляются.
В момент постановки на паузу очередь ComfyUI пуста; фоновые оркестраторы
этого компонента остановлены. Возобновлять только по просьбе пользователя.

SeedVR2: 37/37 листов.
Qwen: 24/37 листов, 216 уникальных изображений; осталось 13 листов.
prepared-v2: 9/37 листов, 114 уникальных кадров; осталось 28 листов подготовки.
Всего требуется 376 уникальных изображений из 64 оригинальных ресурсов:
540 направленных игровых кадров и 6 одинаковых прицельных схем.
Ресурс masrat*, art index 24, PID 0x01000030; 20 крыс на исходной V13ENT.
Оригинальные смещения, размеры, FPS, action frame сохранены в inventory.json.

Генерация: assets/generated/critter-rat/qwen21-seedvr2-v1-20261115.
pause-state.json — актуальная точка продолжения; прежняя пауза в pause-history/.
prepared/ — ранняя проба с цветным кантом, не финальная.
prepared-v2/ — исходный цвет тонких границ, новая фактура внутри тела,
точная бинарная маска исходных игровых кадров. review/ — частичные сравнения.

na-p00 — зелёная wireframe-схема, Qwen job 7eb3ac9c-bd26-45d8-997d-48b60883413c.
Её финальная подготовка ещё НЕ запускалась. Маски сохранения оригинальных
технических линий: source/aimed-body-mask-*.png, aimed-protected-lines.png.
Qwen-промпт уточнён, загрузчик отдельного EXE принимает её непрозрачный чёрный
фон. Нужно подготовить, просмотреть и проверить защищённые пиксели схемы.

Изолированные исходники: work/hd-rat-20261115/source.
Тестовый runtime: runtime/hd-rat-pilot. Общие исходники и runtime пещеры
этим чатом не изменены. HD-набор крысы ещё НЕ установлен, выбранного полного
пакета assets/hd/critter-rat/qwen21-seedvr2-v1-x4 пока нет.
Текущий EXE: {j['isolated_executable_sha256']}.
На нём: меню 139 PASS, отсутствующий пакет 560 PASS, 0 FAIL.
Регрессия мира 577 PASS относится к предыдущему EXE: повторить в финале.
Реальная HD-ходьба, HD-обводка и полный комплект ещё требуют проверки
после установки. Не выдавать частичные ассеты или сборку без пакета за готовые.

Скрипты: pipeline.py, prepare-ready.py, aimed-mask.py, review.py,
audit-runs.py, package.py, build.ps1, test.ps1, test-fallback.ps1,
test-menu.ps1, test-world.ps1. package.py требует полный проверенный набор.
Существующее окружение Python:
C:/Users/Administrator/AppData/Local/Comfy-Desktop/ComfyUI-Installs/local/standalone-env/python.exe
ComfyUI: http://127.0.0.1:8188. Чужие задания не отменять, /free не вызывать
во время чужой работы. Все job ID, workflow, API prompt, history и хеши сохранены.
AGENTS.md и HD-TEXTURE-GUIDE.md не редактировались.
'''
(W/'README.txt').write_text(note,encoding='utf-8')
(O/'README.txt').write_text(note,encoding='utf-8')
print(json.dumps(dict(status=j['status'],qwen=len(j['completed_panels']['qwen']),qwen_unique=j['unique_qwen_frames'],
    prepared=len(j['completed_panels']['prepared-v2']),prepared_unique=j['unique_prepared_frames'],remaining=len(j['remaining_qwen_panels']))))
