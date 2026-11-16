Qwen Image 2.1 Fun ControlNet-Union INT8 — установка 14 ноября 2026

По прямому запросу пользователя установлен один официальный файл:
C:\Users\Administrator\AppData\Local\Comfy-Desktop\ComfyUI-Shared\models\model_patches\qwen_image_2.1_fun_controlnet_union_int8_convrot.safetensors
Размер: 3 779 298 944 байта.
SHA256: 07aa961570ac0e03d4ca936aecd76854d077a33cde69b5092399afba01b3715d
Репозиторий: Comfy-Org/Qwen-Image-2.1
Ревизия: aacf31a6d48e707f352ecba714cee0680da3479b

download-model.py загрузил файл в этот каталог и сверил размер, SHA256,
ключи/смещения safetensors. install-model.ps1 переместил проверенный файл
в models/model_patches и повторно проверил SHA256. Отдельная большая копия
в проекте не оставлена. Существующие модели не заменялись. Исходники,
зависимости и конфиги ComfyUI не менялись; сервер не перезапускался.

Подтверждения: download-plan.json, staged.json, installed.json.
existing-models.json — текущие размеры пяти файлов Qwen/SeedVR2 совпали
с прежними отчётами; перечисленные там старые хеши заново не вычислялись.

Доступны нативные Load Model Patch / Apply Fun ControlNet.
Историческое внутреннее имя второго узла: ZImageFunControlnet;
он поддерживает Qwen 2.1. Обычный SDXL ControlNetLoader здесь не нужен.

smoke/ — изолированный технический тест 512x512 с Canny, strength 1,
2 шага Euler/simple, CFG 1, denoise 1, CPU KV cache. Полный цикл прошёл,
39,593 секунды, PNG RGBA. Источник — простая диагностическая геометрия,
не игровой ассет. Визуально проверены рамка, экран, три ручки и четыре
крепления. Тест не подтверждает точную геометрию, качество полной панели,
скорость 4K, работу inpainting или других видов контроля.

smoke/workflow.json — открыть перетаскиванием в ComfyUI.
smoke/prompt-api.json, run.json, history.json, result.json — воспроизведение
и отчёты. Вход уже загружен под уникальным именем. Два шага служат только
проверке установки; для художественной задачи нужен отдельный каталог/граф.
smoke-test.py submit запрещает повторную отправку существующего задания.
collect получает результат только записанного prompt_id, не отменяет очередь.

Обновлён HD-TEXTURE-GUIDE.md: текущий комплект Qwen 2.1 и SeedVR2,
примеры графов и замеров, отличие Qwen Edit от SDXL img2img, установка
и проверка ControlNet. Исходная версия: HD-TEXTURE-GUIDE.before.md.
AGENTS.md, игровые ассеты, исходники CE, EXE и runtime этой задачей не менялись.
