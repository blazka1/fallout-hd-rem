V22: HD-скелет с промежуточной тенью между V20 и V21. 13 ноября 2026.

Выбранный пользователем Qwen contact-shadow-v6 установлен в runtime/hd-world-pilot.
Исходник: assets/generated/v13ent-door-skeleton-qwen/trial-v1-20261113/contact-shadow-v6.
Пакет: assets/hd/v13ent-door-skeleton/v5-balanced-shadow-x4 — PNG268x164 и F1HD RGBA.
V22: ComfyUI добавляет умеренную чёрную подложку под существующий спрайт:
расширение3 HD px, смещение вниз5 HD px, sigma1.95, alpha до60%.
Плотность и мягкость края между V20 и V21; тело и привязка не меняются.
Непрозрачные пиксели тела сохранены побайтно. Новая диффузия не запускалась.
Граф и параметры: assets/generated/v13ent-door-skeleton-qwen/shadow-balanced-v5-20261113.
Подготовка: tools/strengthen-shadow.py --balanced.
Предыдущая контрастная тень сохранена в v4-classic-shadow-x4.
Предыдущая усиленная мягкая тень сохранена в v3-shadow-x4.
Предыдущая мягкая тень сохранена в v2-shadow-x4.
Предыдущий вариант без тени сохранён в v1-x4. EXE V18 не менялся.
Исходный размер67x41, offsets(+20,+30), frame shifts(0,0), tile17488 сохранены.
Объект FID113/PID211 остаётся исходным контейнером с двумя записями инвентаря.

Запуск: Start-Fallout-HD-Player-Pilot.cmd сразу открывает первую пещеру.
Start-Fallout-HD-World-Pilot.cmd открывает обычное меню тестовой игры.
F11 — HD/оригинал. [remaster] hd_v13_skeleton=0 отключает скелет после перезапуска.
После установки нового ассета или EXE игру нужно перезапустить.

Рендер: отдельная soft-alpha текстура и owner250 в существующем HD-слое.
Сохраняется фон под скелетом отдельно от фона под персонажем. Поэтому игрок
может перекрывать скелет, а прозрачные края показывают пол. Классический
индексированный framebuffer, карта, прототип, инвентарь и коллизии не меняются.
Геометрия использует исходную FRM-рамку, без новых смещений. Исходная маска
не обрезает новый арт. Неисправный/отсутствующий файл оставляет оригинал.

Сборка: work/hd-world-pilot/tools/build.ps1 -Jobs 6.
Установка только ассета: work/hd-door-skeleton/tools/install.ps1 -AssetsOnly.
Откат: добавить -PackageDirectory assets/hd/v13ent-door-skeleton/v1-x4.
Подготовка ассета: tools/prepare.py через существующий ComfyUI; без генерации.
Проверки скелета включаются переменной FALLOUT_HD_SKELETON_EXPECT=1 вместе
с work/hd-player-male/tools/test-player.ps1. В обычной игре переменная не нужна.
Fallback-тест: tools/test-fallback.ps1, временно удерживает только свой ассет.
Меню: tools/test-menu.ps1 с отдельным каталогом отчётов.
Свежие проверки: 244 PASS, 0 FAIL; скелет, перекрытия, персонаж и исходный контейнер.
Итог и реальные SDL-кадры: build/hd-door-skeleton/integration-v22-shadow.json,
build/hd-door-skeleton/preview/v22-shadow.
Проверки мира/меню/отказов V18 остаются в истории и заново не запускались.

Предыдущий ассет и метаданные сохранены в build/backups/before-v22-skeleton-shadow-20261113.
Общие runtime меню/classic, оригинальные DAT и AGENTS.md не изменялись.
