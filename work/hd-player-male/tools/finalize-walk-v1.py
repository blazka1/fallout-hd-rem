"""Verify and package the reviewed walk artwork; no runtime installation."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "assets/generated/player-male-vault13/walk-v1-20261112"
META = ROOT / "assets/reference/player-male-vault13/metadata/art/critters/hmjmpsab.frm.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    original = read(META)
    receipt = read(RUN / "imagegen-receipts.json")
    preview = read(RUN / "preview/manifest.json")
    visual_review = read(RUN / "preview/visual-review.json")
    assert preview["directions"] == list(range(6))
    assert preview["frames_per_direction"] == 8 and preview["fps"] == 10
    for output in preview["outputs"]:
        assert sha(RUN / "preview" / output["file"]) == output["sha256"]
        if "qa" in output:
            assert output["qa"]["frames"] == 8
            assert all(duration == 100 for duration in output["qa"]["durations_ms"])
    entries, directions = [], []
    for d in range(6):
        directory = RUN / f"prepared/d{d}"
        manifest = read(directory / "manifest.json")
        assert manifest["direction_index"] == d
        assert manifest["frame_count"] == 8 and manifest["fps"] == 10
        assert read(directory / "run.json")["status"] == "completed"
        source_cells = next(s["cells"] for s in original["sheets"] if s["direction"] == d)
        for index, frame in enumerate(manifest["entries"]):
            source = source_cells[index]
            path = directory / frame["registered_file"]
            assert path.exists()
            assert sha(path) == frame["registered_sha256"]
            assert frame["native_dimensions"] == [source["width"], source["height"]]
            assert frame["dimensions"] == [4 * source["width"], 4 * source["height"]]
            assert frame["frame_shift_logical"] == [source["shift_x"], source["shift_y"]]
            assert frame["direction_offset_logical"] == [original["direction_x"][d], original["direction_y"][d]]
            assert sha(Path(frame["original"])) == frame["original_sha256"]
            entries.append({"direction": d, "frame": index,
                "file": f"frames/d{d}/f{index:03}.png", "source_file": str(path.relative_to(RUN)).replace("\\", "/"),
                "sha256": sha(path), "native_dimensions": frame["native_dimensions"],
                "dimensions": frame["dimensions"], "frame_shift_logical": frame["frame_shift_logical"],
                "direction_offset_logical": frame["direction_offset_logical"],
                "transform": frame["transform"], "pose_comparison": frame["qa"]})
        directions.append({"direction": d, "name": manifest["direction"],
                           "manifest": f"prepared/d{d}/manifest.json",
                           "comfy_prompt_id": manifest["prompt_id"]})
    assert len(entries) == 48
    for generation in receipt["entries"]:
        for field in ("request", "pose_reference", "costume_reference", "project_output"):
            assert sha(RUN / generation[field]) == generation[field + "_sha256"]
    final = {
        "component": "player-male-vault13", "animation": "hmjmpsab walk", "version": "walk-v1",
        "status": "48 registered HD walking frames with reviewed animation previews; not installed in CE",
        "source_art": "art/critters/hmjmpsab.frm", "critter_list_index": 11,
        "source_metadata_sha256": sha(META), "directions": directions,
        "frames_per_direction": 8, "frame_total": 48, "fps": 10, "frame_duration_ms": 100,
        "scale": 4, "action_frame": original["action_frame"],
        "offset_units": "original logical pixels; frame shifts are incremental movement deltas, not absolute positions",
        "selected_variant": "registered soft-alpha artwork; source-mask images remain diagnostics and are excluded from delivery ZIP",
        "geometry": "ImageGen follows each original pose; ComfyUI fits each generated bounding box to the original frame at x4. This is not proof of exact skeletal correspondence.",
        "preview": "preview/six-directions-walk.gif",
        "preview_registration": "CE bottom-center anchor, direction offsets and source residual bob; uniform cycle travel removed for in-place preview",
        "imagegen_receipts": "imagegen-receipts.json", "visual_review": "preview/visual-review.json",
        "runtime_installed": False,
        "limitations": ["Pose and torso-twist correspondence is approximate; source silhouette is not imposed on selected frames",
                        "Fine texture/outline variation remains possible across generated frames",
                        "No standing, running, combat or weapon animation added in this walk task",
                        "No CE actor renderer or in-game light/occlusion validation performed"],
        "checks": {"all_48_frame_dimensions_and_logical_offsets": "pass", "original_and_generation_hashes": "pass",
                   "comfy_runs": "all six completed", "preview_encoding_and_visual_review": "see preview manifest and review"},
        "entries": entries,
    }
    save(RUN / "manifest.json", final)
    notes = """Убежище 13 — мужской персонаж, ходьба HD V1

Подготовлено 48 отдельных PNG: 8 кадров на каждое из шести направлений,
10 кадров/с, плотность x4. Внешний вид костюма взят из утверждённого V1.
Все направления генерировались отдельно, номер 13 не зеркалился.

ImageGen перерисовал исходные позы из hmjmpsab.frm с сохранением костюма.
ComfyUI выполнил кроп, приведение к исходным размерам x4, альфу и упаковку.
Основной вариант: registered-f*.png с собственной мягкой альфой.
source-mask-f*.png — только диагностика, в ZIP они не включены.

Результаты:
  preview/six-directions-walk.gif — все шесть циклов, 10 кадров/с.
  preview/six-directions-walk.png — полноцветный анимированный PNG.
  preview/d*-all-frames-comparison.png — оригинал и HD покадрово.
  prepared/d0..d5/registered-f000.png..007 — отдельные игровые кадры.
  walk-v1-x4.zip — 48 PNG, метаданные и эта инструкция.
  Внутри ZIP кадры находятся в frames/d0..d5/f000.png..007.png.

Исходные размеры, offsets, FPS и хеши сохранены. frame_shift_logical —
приращение движения исходного CE, не абсолютная координата. При просмотре
на месте вычитается только равномерный перенос за цикл; остаточная качка
сохранена. Логические offsets нельзя повторно умножать на плотность x4.

Это первая анимационная версия для просмотра, не установленная в игру.
Позы следуют исходным фазам, но повороты торса/контуры не совпадают с
оригиналом попиксельно; ограничение записано в визуальной проверке.
Текущий HD-рендер пещеры ещё не поддерживает этот набор персонажа.
Стойка, бег и боевые действия не изменялись. DAT, общий runtime и AGENTS.md
не менялись. Все промпты, графы, prompt_id/history сохранены в этой папке.
"""
    (RUN / "README.txt").write_text(notes, encoding="utf-8")
    archive = RUN / "walk-v1-x4.zip"
    if archive.exists():
        raise FileExistsError("Refusing to replace delivery archive")
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zip:
        zip.write(RUN / "README.txt", "README.txt")
        zip.writestr("manifest.json", json.dumps(final, ensure_ascii=False, indent=2) + "\n")
        for entry in entries:
            zip.write(RUN / entry["source_file"], entry["file"])
    with zipfile.ZipFile(archive) as zip:
        assert zip.testzip() is None
        assert len(zip.namelist()) == 50
    backup = RUN / "component-state-before-walk"
    backup.mkdir(exist_ok=True)
    for name in ("task.json", "README.txt"):
        target = backup / name
        if target.exists():
            raise FileExistsError(target)
        shutil.copyfile(ROOT / "work/hd-player-male" / name, target)
    task_path = ROOT / "work/hd-player-male/task.json"
    task = read(task_path)
    task["status"] = final["status"]
    task["latest_walk"] = {"directory": str(RUN.relative_to(ROOT)).replace("\\", "/"),
                           "manifest": "manifest.json", "frames": 48, "fps": 10, "scale": 4,
                           "preview": final["preview"], "archive": archive.name, "runtime_installed": False}
    task["next_stage"] = "Review the first walk animation; exact pose refinement and game integration remain separate work"
    task["remaining"] = ["Refine pose/temporal details as needed after animation review",
                         "Player-only direction-aware HD rendering and runtime validation",
                         "Standing, running, weapon, interaction, hit and death animation sets",
                         "Split FR0-FR5 exporter support for relevant actions"]
    save(task_path, task)
    readme_path = ROOT / "work/hd-player-male/README.txt"
    readme = readme_path.read_text(encoding="utf-8")
    readme = readme.replace(
        "Status: first HD art study V1 generated with built-in ImageGen and prepared\nthrough ComfyUI: six separate transparent views and one comparison sheet.",
        "Status: first HD walk animation prepared: 48 frames, six directions,\n8 frames per direction at 10 fps. The earlier V1 costume study is retained.")
    readme += "\nWalk V1 completed: assets/generated/player-male-vault13/walk-v1-20261112\n48 registered soft-alpha PNGs, six 8-frame loops at 10 fps, original logical\noffsets retained. See its README/manifest and preview visual review for\napproximate pose matching and temporal limits. No runtime installation.\n"
    readme_path.write_text(readme, encoding="utf-8")
    print(json.dumps({"verified_frames": 48, "fps": 10, "archive": str(archive), "sha256": sha(archive), "runtime_installed": False}))


if __name__ == "__main__":
    main()
