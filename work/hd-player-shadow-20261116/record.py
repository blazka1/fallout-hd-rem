import difflib
import hashlib
import json
from pathlib import Path

component = Path(__file__).resolve().parent
root = component.parents[1]
build = root / "build/hd-player-shadow-20261116"
reference = root / "work/hd-world-pilot/fallout1-ce-main"
source = component / "source"
diffs, changes = [], []
for path in sorted(source.rglob("*")):
    if not path.is_file():
        continue
    relative = path.relative_to(source)
    old = reference / relative
    if old.exists() and old.read_bytes() == path.read_bytes():
        continue
    changes.append(relative.as_posix())
    diffs.extend(difflib.unified_diff(
        old.read_text(encoding="utf-8").splitlines(keepends=True) if old.exists() else [],
        path.read_text(encoding="utf-8").splitlines(keepends=True),
        fromfile="a/" + relative.as_posix(), tofile="b/" + relative.as_posix()))
(component / "source-changes.patch").write_text("".join(diffs), encoding="utf-8")
review = json.loads((build / "review.json").read_text(encoding="utf-8"))
checks = json.loads((build / "v2/result.json").read_text(encoding="utf-8"))
assert checks["failed"] == 0 and review["pixel_identical_when_shadow_disabled"] == 54 and not review["shared_files_changed"]
exe = component / "runtime/fallout-ce.exe"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(exe) == sha(build / "msvc/RelWithDebInfo/fallout-ce.exe")
report = {"component": "player-contact-shadow", "date": "2026-11-16",
    "status": "verified in isolated CE runtime; shared runtime not modified",
    "runtime": str(exe.parent), "launcher": "Start-Fallout-HD-Player-Shadow.cmd",
    "executable_sha256": sha(exe), "source_changes": changes,
    "test_result": checks, "disabled_identical_frames": 54,
    "shared_files_checked": review["shared_files_checked"], "shared_files_changed": [],
    "artwork_changed": False, "shadow": "Separate procedural floor-only contact shadow, 34x14 native px, max alpha 90/255",
    "limits": "Not a directional physically traced shadow; existing male unarmed V13ENT stand/walk support only",
    "previews": str(build / "v2/gallery"), "details": "README.txt"}
(component / "integration.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps({"source_changes": changes, "result": checks, "executable_sha256": sha(exe)}, ensure_ascii=False))
