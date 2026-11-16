"""Record only completed, passing integration checks for the isolated pilot."""
from pathlib import Path
import datetime
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8-sig"))


def write(path, value):
    (ROOT / path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest().upper()


preview = "build/hd-player-male/preview/integration-v1"
receipt = "build/hd-player-male/integration-v1.json"
player = read(preview + "/manifest.json")
world = read("build/hd-world-pilot/preview/player-walk-v1-world-regression/manifest.json")
menu = read("build/hd-world-pilot/menu-regression/manifest.json")
fallback = read("build/hd-player-male/fallback-v1/manifest.json")
integrity = read("build/hd-player-male/integrity-audit.json")
comparison = read("build/hd-player-male/world-frame-comparison.json")
gallery = read(preview + "/gallery/preview-manifest.json")
exe_hash = sha("runtime/hd-world-pilot/fallout-ce.exe")
for report in (player, world, menu, fallback):
    assert report["executable_sha256"].upper() == exe_hash
for report in (player["result"], world["result"], menu):
    assert report["passed"] > 0 and report["failed"] == 0
assert len(fallback["cases"]) == 3 and fallback["all_files_restored"]
assert all(case["result"]["failed"] == 0 for case in fallback["cases"])
assert integrity["status"] == "PASS" and comparison["identical"] == comparison["total"] == 112
package = "assets/hd/player-male-vault13/v1-x4"
manifest = read(package + "/manifest.json")
for entry in manifest["entries"]:
    assert sha("runtime/hd-world-pilot/data/art/hd/player-male-vault13/" + entry["filename"]) == entry["rgba_sha256"].upper()

limits = [
    "Only male obj_dude, original unarmed hmjmps body, V13ENT.MAP/V13ENT.SAV; other maps remain outside this pilot.",
    "Six static directional idle sprites; original idle frame numbers retain one fixed HD pose per direction.",
    "48 walking frames use original CE direction, frame, movement offsets and 100 ms timing. Approximate art poses retain V1 temporal variation, particularly torso turns in side views.",
    "Running, weapons, combat, interactions, hits/death, armour, female actors, NPCs, active outlines and translucency use the original renderer.",
    "Timed CE animation was exercised on one eight-hex route. Six-direction gallery is assembled from real posed SDL captures, not six simultaneous gameplay paths.",
    "Performance samples are hidden-window CPU elapsed times for full refresh plus presentation, not guaranteed gameplay FPS.",
]
report = {
    "recorded_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "status": "integrated_and_verified_in_isolated_ce_pilot",
    "revision": "V17 male Vault 13 standing and walking player",
    "runtime": "runtime/hd-world-pilot",
    "launcher": "Start-Fallout-HD-Player-Pilot.cmd",
    "normal_menu_launcher": "Start-Fallout-HD-World-Pilot.cmd",
    "executable_sha256": exe_hash,
    "parent_report": "build/hd-world-pilot/campfire-front-shadow-v16-integration.json",
    "selected_package": "assets/hd/v13ent/v14-campfire-x4",
    "selected_image_count": 206,
    "world_art_unchanged": True,
    "actor_package": package,
    "actor_package_manifest_sha256": sha(package + "/manifest.json"),
    "actor_image_count": 54,
    "actor_idle_directions": 6,
    "actor_walk_frames": 48,
    "actor_scale": 4,
    "actor_config": "[remaster] hd_player_male=1",
    "player_checks": player["result"],
    "world_checks": world["result"],
    "menu_checks": {"passed": menu["passed"], "failed": menu["failed"]},
    "fallback_checks": fallback,
    "integrity_summary": integrity["summary"],
    "integrity_report": "build/hd-player-male/integrity-audit.json",
    "world_comparison": {"unchanged": comparison["identical"], "total": comparison["total"], "report": "build/hd-player-male/world-frame-comparison.json"},
    "timings": read(preview + "/timings.json"),
    "preview": preview,
    "visual_review": preview + "/gallery/qa-review.txt",
    "gallery": preview + "/gallery/preview-manifest.json",
    "reviewed_render_properties": ["bottom-center registration", "soft alpha restores cave underneath original silhouette", "foreground occlusion", "no trails on timed walk or scroll", "classic F11 and unsupported-pose fallback", "renderer recreation and palette lighting"],
    "backup": "build/backups/before-hd-player-v1-20261112",
    "limits": limits,
}
write(receipt, report)
write("build/hd-world-pilot/integration-manifest.json", report)

task = read("work/hd-player-male/task.json")
task.update({
    "status": "Integrated in isolated CE pilot V17: 6 static idle directions and 48 walking frames",
    "integration_status": "Installed and verified: 228 player checks, 306 world checks, 139 menu checks; zero failures",
    "current_world_baseline_observed": "V16 cave art/contact shadow retained; V17 adds player rendering",
    "runtime": "runtime/hd-world-pilot", "launcher": "Start-Fallout-HD-Player-Pilot.cmd",
    "integration_receipt": receipt, "executable_sha256": exe_hash,
    "next_stage": "Review the V1 actor in the cave; further animation artwork is separate work",
    "remaining": ["Temporal/pose refinement if requested", "Animated idle, running, weapon, interaction, hit and death HD sets", "Other armour, female characters and NPCs", "Other maps outside V13ENT"],
    "shared_files_modified": ["work/hd-world-pilot/fallout1-ce-main/CMakeLists.txt", "work/hd-world-pilot/fallout1-ce-main/src/game/main.cc", "work/hd-world-pilot/fallout1-ce-main/src/game/object.cc", "work/hd-world-pilot/fallout1-ce-main/src/game/hd_world_pilot.cc", "work/hd-world-pilot/fallout1-ce-main/src/game/hd_world_pilot.h"],
    "limits": limits,
})
task["latest_walk"]["runtime_installed"] = True
task["latest_art"]["limitations"] = "Original art study retains straighter arms and elongated silhouette. Six cropped/registered static idle views derived via ComfyUI are now integrated; this study itself is not used as a complete animation."
task["preview_note"] = "Reference previews remain nearest-neighbour originals. Actual current CE previews are in " + preview
write("work/hd-player-male/task.json", task)

world_task = read("work/hd-world-pilot/task.json")
world_task.update({
    "task": "Integrate male Vault 13 HD player and walking into test cave",
    "user_scope": "Show existing HD male suit and six-direction walk in the isolated real CE cave",
    "status": "V17 integrated: male standing/walking HD player; V16 environment retained; all current integration checks pass",
    "integration_receipt": receipt,
    "final_preview": preview,
    "executable_sha256": exe_hash,
    "player_launcher": "Start-Fallout-HD-Player-Pilot.cmd",
    "player_package": package,
    "known_scope_exclusions": "Only male unarmed player stand/walk in V13ENT are now HD. Other character actions/actors, items, HUD and inner rectangular door remain classic.",
    "performance_report": preview + "/timings.json",
    "performance_note": "12 samples per output/actor-on-off case. Hidden-window refresh+presentation CPU time; not gameplay FPS.",
    "latest_asset_delta": {"unchanged_environment_images": 206, "new_actor_images": 54, "changed_placements": 0, "game_objects_created": 0},
})
write("work/hd-world-pilot/task.json", world_task)

(ROOT / "work/hd-player-male/README.txt").write_text("""Мужской персонаж — костюм Убежища 13, первый игровой HD-вариант
12 ноября 2026. Подключён в изолированный Fallout 1 CE, V17.

Запуск сразу в пещере: Start-Fallout-HD-Player-Pilot.cmd.
Обычное главное меню: Start-Fallout-HD-World-Pilot.cmd.
Одновременно запускать только один Fallout. После установки перезапустить игру.
Для ходьбы используйте одиночный щелчок по земле; двойной щелчок включает бег,
который пока отображается оригинальными кадрами. F11 переключает HD/оригинал.

Работает только мужчина-игрок в исходном костюме hmjmps без оружия на V13ENT.
54 изображения x4: шесть статичных стоек и 48 кадров ходьбы (6×8, 10 fps).
Направление, кадр, смещения, маршрут и скорость выбирает оригинальный CE.
Мягкая альфа смешивается с фоном; свет и перекрытие стенами сохранены.
Стойка пока статична. В V1 остаётся заметный поворот корпуса между отдельными
кадрами ходьбы, особенно сбоку. Это первый вариант для визуальной оценки.
Бег, оружие, бой, взаимодействия, повреждения/смерть, другая броня, женщины,
NPC, обводки и полупрозрачность отображаются оригинальной графикой.
Отсутствующий/повреждённый HD-кадр автоматически заменяется оригинальным.

Пакет: assets/hd/player-male-vault13/v1-x4.
Исходные FRM/метаданные: assets/reference/player-male-vault13.
ImageGen-костюм: assets/generated/player-male-vault13/v1-20261112.
Ходьба: assets/generated/player-male-vault13/walk-v1-20261112.
ComfyUI-стойки: assets/generated/player-male-vault13/runtime-v1-20261112.

Сборка: work/hd-world-pilot/tools/build.ps1 -Jobs 6
Установка: work/hd-player-male/tools/install-player-pilot.ps1
Проверка: work/hd-player-male/tools/test-player.ps1
Проверка fallback: work/hd-player-male/tools/test-player-fallback.ps1
HD-персонаж отключается через [remaster] hd_player_male=0 и перезапуск.

Проверено: 228 проверок персонажа, 306 мира, 139 меню; ошибок нет.
Отдельно проверены отсутствующий кадр, повреждённый кадр и отсутствующий реестр.
112 контрольных PNG пещеры без HD-персонажа совпали с V16 побайтно.
Реальный маршрут CE пройден на восемь гексов без следов от старых кадров.
Галерея направлений составлена из отдельных реальных SDL-кадров; это не запись
шести одновременно движущихся персонажей. Подробности — gallery/qa-review.txt.

Отчёт: build/hd-player-male/integration-v1.json.
Кадры: build/hd-player-male/preview/integration-v1.
Резервная копия: build/backups/before-hd-player-v1-20261112.
Окружение V16, готовое меню и оригинальные игровые данные не изменялись.
AGENTS.md не обновлялся.
""", encoding="utf-8")

(ROOT / "work/hd-world-pilot/README.txt").write_text("""FALLOUT 1 CE — ПИЛОТ V17, HD-ПЕРСОНАЖ В ПЕЩЕРЕ

Start-Fallout-HD-Player-Pilot.cmd — сразу начать новую игру в пещере мужчиной.
Start-Fallout-HD-World-Pilot.cmd — обычное главное меню тестовой сборки.
F11 — HD/оригинал. После установки игру перезапускать. Один экземпляр за раз.

Добавлен мужской игрок в костюме Убежища 13: 6 статичных стоек и 48 кадров
ходьбы во всех шести направлениях. Бег, оружие и другие действия пока classic.
Одиночный щелчок — ходьба; двойной — бег. Смещения, скорость, проходимость,
сохранения и правила игры остаются оригинальными.
Настройка персонажа: [remaster] hd_player_male=1 (0 отключает, нужен перезапуск).
Подробнее: work/hd-player-male/README.txt.

Окружение V16 сохранено: 206 изображений assets/hd/v13ent/v14-campfire-x4,
19 размещений декора, усиленная тень ниже переднего края костра.
Костёр: гекс23677, этаж0, смещения(-6,22), flat=true, 64×24.
Тень: [remaster] hd_world_campfire_shadow=1, максимальное затемнение50%.
История окружения: build/hd-world-pilot/campfire-front-shadow-v16-integration.json.

Текущие проверки: 228 персонажа, 306 мира, 139 меню, все PASS.
Есть отдельная проверка трёх отказов пакета персонажа.
112 контрольных кадров мира без нового персонажа побайтно совпадают с V16.
Отчёт: build/hd-player-male/integration-v1.json.
Текущая сводка: build/hd-world-pilot/integration-manifest.json.
Превью: build/hd-player-male/preview/integration-v1.

Сборка: work/hd-world-pilot/tools/build.ps1 -Jobs 6.
Повторная установка персонажа и EXE: work/hd-player-male/tools/install-player-pilot.ps1.
Резервная копия до V17: build/backups/before-hd-player-v1-20261112.
Общий runtime меню и classic не изменены. AGENTS.md остаётся снимком V13.
""", encoding="utf-8")
print("Recorded verified V17 integration; AGENTS.md unchanged.")
