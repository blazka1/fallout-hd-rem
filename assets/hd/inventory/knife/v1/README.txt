Выбранный пользователем обычный нож для инвентаря Fallout 1.

Утверждён результат qwen21-handle-fill-v6-20261113: цельная нижняя часть рукояти,
крепления, матовая сталь, умеренная ржавчина, исправленный надлом у кончика.
knife-master.png — исходный результат 1152×576 с прозрачностью.
knife-hd-x4.png — выбранный HD-ассет 352×132 с прозрачностью.

В HUD и в окне инвентаря используется HD-слой из knife.rgba.
В ячейках рук он сохраняет размер 88×33 логических пикселя и до 352×132
пикселей при выводе 4x. В списке подгоняется под слот 56×40 (сам нож
56×21 логический пиксель), с выборкой прямо из HD-источника 352×132.
Промежуточная маленькая палитровая картинка не используется.
knife.rgba содержит точные пиксели knife-hd-x4.png, без потери цвета.
Остальные предметы, фон и текст интерфейса остаются классическими.
Нож на курсоре во время перетаскивания также выводится из HD RGBA.

oknife.frm 88×33 в игровой палитре остаётся резервным вариантом при
отсутствии/повреждении HD-файла или отключении hd_hud_icons.
knife-runtime-native.png показывает точные пиксели этой резервной версии.

Установка: runtime/hd-world-pilot/data/art/inven/oknife.frm.
Запуск: Start-Fallout-HD-World-Pilot.cmd. После установки перезапустить игру:
загруженные FRM могут оставаться в кэше до завершения процесса.
Отдельные сборки classic и hd-menu не обновляются этим пакетом.
Иконка заменяется по ресурсу art/inven/oknife.frm для обычного Knife, PID 4.
Мировой спрайт ножа и предметы в руках персонажа этой иконкой не заменяются.

Оригинальные DAT/прототипы, размеры, FPS и смещения FRM не изменены.
Для классического override EXE пересобирать не требуется: CE читает loose FRM
из master_patches=data. Для HD-кнопки требуется новая сборка пилота с hd_hud.cc
и файл data/art/hd/inventory/knife/knife.rgba рядом с её игровыми данными.
Проверены структура FRM, декодирование пикселей, палитра, размеры и хеши копий.
Фактическая установка и откат описаны в build/hd-inventory-knife/selected-v1/installation.json.
Для первого отката убрать только указанный override oknife.frm из runtime:
движок снова прочитает оригинал из MASTER.DAT. Архивы изменять не нужно.

Воспроизводимая подготовка/установка:
work/seedvr2-image-setup/20261113/install-selected-knife.py prepare
work/seedvr2-image-setup/20261113/install-selected-knife.py install
Скрипту нужны PIL и NumPy из уже установленного Python ComfyUI.

Подготовка HD-HUD и проверки: work/hd-inventory-knife/README.txt.
Установка проверенной HD-сборки: work/hd-inventory-knife/install-hud.ps1.
Проверки и отчёты: build/hd-inventory-knife/preview и installations.
При отсутствии/повреждении knife.rgba возвращается классический FRM.
hd_hud_icons=0 в [remaster] отключает HD-иконку; требуется перезапуск.
Резервные копии EXE и RGBA указаны в отчёте конкретной установки.

Окно инвентаря: work/hd-inventory-knife/INVENTORY.txt.
Актуальный отчёт: build/hd-inventory-knife/inventory-integration.json.

HD-курсор: work/hd-inventory-knife/CURSOR.txt.
Актуальная сборка: build/hd-inventory-knife/cursor-integration.json.
