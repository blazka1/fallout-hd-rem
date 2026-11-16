"""Compare native SDL captures and package previews without retouching them."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[2]
COMPONENT = Path(__file__).resolve().parent
BUILD = ROOT / "build/hd-player-shadow-20261116"
RUN = BUILD / (sys.argv[1] if len(sys.argv) > 1 else "v2")
OUT = RUN / "gallery"
OUT.mkdir(exist_ok=True)
spec = importlib.util.spec_from_file_location("preview", ROOT / "work/hd-player-male/tools/create-runtime-preview.py")
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)


def read(directory, filename):
    return Image.open(directory / filename).convert("RGB")


comparisons = []
for direction in range(6):
    for action, count in (("stand", 1), ("walk", 8)):
        for frame in range(count):
            filename = f"{action}-d{direction}-f{frame:03}.png"
            old = read(BUILD / "baseline", filename)
            off = read(RUN, "no-shadow-" + filename)
            on = read(RUN, filename)
            comparisons.append({"file": filename,
                "disabled_matches_installed_exe": old.tobytes() == off.tobytes(),
                "shadow_diff_bounds_in_crop": ImageChops.difference(on, off).getbbox()})

stand = [read(RUN, f"stand-d{d}-f000.png") for d in range(6)]
preview.sheet(stand, [f"Shadow / {name}" for name in preview.LABELS], 3).save(OUT / "six-directions-stand.png")
preview.sheet([read(RUN, "no-shadow-stand-d2-f000.png"), stand[2]],
    ["Без тени", "Мягкая контактная тень"], 2).save(OUT / "shadow-comparison.png")
frames = [preview.sheet([read(RUN, f"walk-d{d}-f{f:03}.png") for d in range(6)],
    [f"Shadow / {name}" for name in preview.LABELS], 3) for f in range(8)]
animation = preview.animations(frames, [100] * 8, OUT / "six-directions-shadow-walk")
pair = [preview.sheet([read(RUN, f"no-shadow-walk-d2-f{f:03}.png"), read(RUN, f"walk-d2-f{f:03}.png")],
    ["Без тени", "Мягкая контактная тень"], 2) for f in range(8)]
preview.animations(pair, [100] * 8, OUT / "shadow-walk-comparison")
protected = json.loads((COMPONENT / "baseline-sha256.json").read_text(encoding="utf-8-sig"))
changed = [row["path"] for row in protected
    if hashlib.sha256(Path(row["path"]).read_bytes()).hexdigest().upper() != row["sha256"]]
manifest = {"source": "Actual SDL render crops; no retouching or resampling",
    "scope": "6 posed stand views, 48 posed walk frames assembled at original 10 fps; not six simultaneous live paths",
    "comparisons": comparisons, "animation": animation,
    "shared_files_checked": len(protected), "shared_files_changed": changed,
    "pixel_identical_when_shadow_disabled": sum(row["disabled_matches_installed_exe"] for row in comparisons),
    "output_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file()}}
(BUILD / "review.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps({k: manifest[k] for k in ("pixel_identical_when_shadow_disabled", "shared_files_checked", "shared_files_changed")}, ensure_ascii=False))
assert len(comparisons) == 54 and all(row["disabled_matches_installed_exe"] for row in comparisons)
assert not changed
