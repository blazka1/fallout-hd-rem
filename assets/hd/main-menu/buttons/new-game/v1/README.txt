Fallout 1 CE — New Game, HD-кнопка v1
Подготовлено 11 ноября 2026.

Мастер-файлы
  normal.png  — обычное состояние.
  hover.png   — наведение мыши или фокус клавиатуры.
  pressed.png — удержание кнопки мыши или подтверждение клавиатурой.
  Каждый файл имеет размер 1020×152: 1:1 при выводе меню в 3840×2160.
  В 1920×1080 кнопка отображается как 510×76.
  states.png — сравнение трёх текстур без надписей.

Происхождение
  Экспорт из принадлежащего пользователю MASTER.DAT, без изменения архива:
  assets/reference/main-menu-buttons/png/art/intrface/mainmenu.frm.png
  assets/reference/main-menu-buttons/png/art/intrface/menuup.frm.png
  assets/reference/main-menu-buttons/png/art/intrface/menudown.frm.png

  Плашка New Game вырезана из mainmenu.frm: x=400, y=76, w=204, h=41.
  Original menuup/menudown 26×26 — настоящий красный переключатель Fallout.
  Обработка выполнена локально в ComfyUI 0.45.2, RealESRGAN_x4plus.pth.
  Это нейросетевое восстановление исходной графики; SDXL и диффузионная
  перерисовка здесь не использовались. Новые модели не скачивались.

  Все художественные операции выполнены узлами ComfyUI:
  ImageCrop → ImageUpscaleWithModel → ImageScale; удлинение середины
  плашки без растяжения торцевых заклёпок; три варианта освещения;
  маска исходного переключателя и ImageCompositeMasked.
  Геометрия и фактура общие для трёх состояний.

Воспроизведение
  comfy-workflow.json — граф для открытия в ComfyUI.
  comfy-api.json — тот же граф для API.
  Исходные изображения загружены в локальный ComfyUI, папка fallout1_menu.
  При переносе на другую машину нужно заново указать три исходных PNG
  в узлах LoadImage и установить RealESRGAN_x4plus.pth в upscale_models.

  Из PowerShell в корне проекта, при запущенном ComfyUI:
  python .\tools\asset-pipeline\comfy_new_game_button.py --reference .\assets\reference\main-menu-buttons --output .\assets\generated\main-menu\new-game-v2 --label new-game-v2
  Существующий запуск не перезаписывается; для нового варианта меняйте v2.
  Python использует только стандартную библиотеку. Нужны штатные узлы ComfyUI.
  Полный журнал текущей генерации: assets/generated/main-menu/new-game-v1.

Интеграция
  Надписи NEW GAME и N не включены в текстуры. CE рисует их отдельно
  в физических пикселях окна, с тенью и сдвигом текста на 1 UI-пиксель
  при нажатии. Это сохраняет читаемость и возможность будущей локализации.
  Область клика — вся плашка, а не только круглый переключатель.
  Увод мыши отменяет нажатие; возврат при удержании восстанавливает его.
  Подтверждение запускает штатную команду New Game / выбор персонажа CE.

  scripts/prepare-hd-menu.ps1 преобразует PNG в BMP без изменения пикселей:
  runtime/hd-menu/data/art/hd/main-menu/new-game/{normal,hover,pressed}.bmp.
  CE загружает все три файла как единый комплект, проверяя размер.
  При отсутствии/повреждении любого состояния остаётся прежняя рабочая кнопка.
  В runtime/hd-menu/fallout.cfg: [remaster] hd_new_game_button=0 отключает
  эту плашку; при отсутствии ключа она включена.

Проверка
  scripts/test-hd-menu.ps1: ввод, переходы, шесть разрешений до 4К,
  отмена клика, клавиатурный фокус, загрузка и пересоздание текстур.
  build/hd-menu-preview/new-game-states.png — настоящие кадры CE с текстом:
  сверху обычное состояние, затем наведение, затем нажатие.
  build/hd-menu-preview/1920x1080.png — кнопка в полном меню.
  Отчёты: checks.txt, integration.txt, manifest.json в той же папке.

  Обновлена только кнопка New Game. Остальные пункты меню используют
  предыдущую графику; выбор персонажа пока классический.
  Резервная копия: build/backups/before-hd-new-game-button.
