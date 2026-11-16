"""Record the chosen study and confirm no installed art was altered."""
from pathlib import Path
import importlib.util, json, shutil

WORK = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('review', WORK / 'review.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
out = r.OUT
hard = out / 'qwen-hard-result.json'
if not hard.exists():
    original = r.read(out / 'result.json')
    assert original['attempt'] == 'qwen'
    shutil.copy2(out / 'result.json', hard)
selected = r.read(out / 'qwen-soft-result.json')
baseline = r.read(out / 'runtime-art-baseline.json')
changed = [p for p, digest in baseline.items() if not (r.ROOT / p).is_file() or r.sha(r.ROOT / p) != digest]
assert not changed, changed
selected['selected_for_visual_review'] = True
selected['visual_review'] = {
    'improvements': ['More readable sleeve and trouser folds', 'Stronger modeling of face, collar and boots',
                     'Original poses and floor-shadow extents retained much better than first uncontrolled Qwen'],
    'remaining_issues': ['Slightly smooth/stylized fabric rather than strong woven microdetail',
                         'Blue tint in floor shadows', 'Light fringe along portions of the contour'],
    'ready_for_runtime_installation': False,
    'reviewed_backgrounds': ['neutral gray', 'light', 'dark'],
}
selected['selected_rgba'] = 'qwen-soft/candidate-x4.png'
selected['selected_preview'] = 'qwen-soft-preview/before-after.png'
selected['unchanged_runtime_art_and_executable_files'] = len(baseline)
selected['rejected_attempt_report'] = 'qwen-hard-result.json'
r.write(out / 'result.json', selected)
print(json.dumps({'selected': selected['selected_rgba'], 'runtime_unchanged': len(baseline),
                  'runtime_installed': False, 'preview': selected['selected_preview']}))
