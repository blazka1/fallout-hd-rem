"""Package unedited SDL captures and audit the cave sampling regression fix."""
from pathlib import Path
import csv, difflib, hashlib, importlib.util, json, sys
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
BUILD = ROOT / 'build/hd-player-lighting-20261116'
NEW = BUILD / 'cave-sampling-v2'
OLD = BUILD / 'cave-sampling-red'
GALLERY = NEW / 'gallery'
GALLERY.mkdir(exist_ok=True)
PKG = ROOT / 'assets/hd/player-male-vault13/lighting-v2-x4'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return Image.open(p).convert('RGB')
def data(p): return json.loads(p.read_text(encoding='utf-8-sig'))

spec = importlib.util.spec_from_file_location('preview', ROOT / 'work/hd-player-male/tools/create-runtime-preview.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
result, red = data(NEW/'result.json'), data(OLD/'result.json')
assert result['failed'] == 0 and red['failed'] == 1
checks = (NEW/'checks.txt').read_text()
assert '14109376 samples, 0 mismatches' in checks
assert '5927968 mismatches' in (OLD/'checks.txt').read_text()

if '--audit-only' not in sys.argv:
    walk = [[read(NEW/f'cave-walk-d{d}-f{f:03}.png') for f in range(8)] for d in range(6)]
    six = [helper.sheet([walk[d][f] for d in range(6)], [f'{helper.LABELS[d]} / d{d}' for d in range(6)], 3) for f in range(8)]
    six[2].save(GALLERY/'cave-six-directions-still.png')
    helper.animations(six, [100]*8, GALLERY/'cave-six-directions')
    stand = [read(NEW/f'cave-stand-d{d}-f000.png') for d in range(6)]
    helper.sheet(stand, [f'{helper.LABELS[d]} / d{d}' for d in range(6)], 3).save(GALLERY/'cave-stand.png')

    before = read(OLD/'player-behind-geometry-hd.png')
    control = read(OLD/'player-behind-geometry-hidden.png')
    after = read(NEW/'player-behind-geometry-hd.png')
    bounds = ImageChops.difference(before, control).getbbox()
    assert bounds
    x = max(0, min(before.width-320, (bounds[0]+bounds[2])//2-160))
    y = max(0, min(before.height-320, (bounds[1]+bounds[3])//2-160))
    box = (x,y,x+320,y+320)
    helper.sheet([before.crop(box), after.crop(box)], ['До исправления', 'После исправления'], 2).save(GALLERY/'cave-before-after.png')

    timed_dir = NEW/'wall-walk'
    with (timed_dir/'timed-walk.tsv').open() as stream:
        rows = [{k:int(v) for k,v in row.items()} for row in csv.DictReader(stream, delimiter='\t') if row['animation']=='1']
    paths = sorted((p for p in timed_dir.glob('timed-walk-*.bmp') if p.stem.rsplit('-',1)[-1].isdigit()),
        key=lambda p: int(p.stem.rsplit('-',1)[-1]))
    assert len(paths)==24 and len(rows)>24
    frames = [read(p) for p in paths]
    durations = [rows[i+1]['elapsed_ms']-rows[i]['elapsed_ms'] for i in range(len(frames))]
    helper.animations(frames, durations, GALLERY/'walk-through-cave-foreground')
    helper.sheet([frames[i] for i in [0,3,6,9,12,15,18,23]],
        [f"{rows[i]['elapsed_ms']} ms / f{rows[i]['frame']}" for i in [0,3,6,9,12,15,18,23]],4).save(GALLERY/'wall-walk-contact-sheet.png')

baseline = data(WORK/'baseline-sha256.json')
changed = [r['path'] for r in baseline if sha(Path(r['path'])).upper()!=r['sha256']]
# The shared config was saved at 14:40, before this fix's 14:45 source backup.
# Preserve that external change; do not restore an old config over user settings.
shared_config = ROOT/'runtime/hd-world-pilot/fallout.cfg'
assert all(Path(p)==shared_config for p in changed), changed
if changed:
    assert shared_config.stat().st_mtime < (WORK/'backups/before-cave-sampling-fix/sha256.json').stat().st_mtime
verified = 0
runtime = WORK/'runtime/data/art/hd/player-male-vault13'
for entry in data(PKG/'manifest.json')['entries']:
    for key, hash_key in [('png','png_sha256'),('filename','rgba_sha256'),('shadow_mask','shadow_mask_sha256')]:
        assert sha(PKG/entry[key]) == entry[hash_key] == sha(runtime/entry[key])
        verified += 1
assert sha(PKG/'registry.tsv') == sha(runtime/'registry.tsv')
exe = WORK/'runtime/fallout-ce.exe'
assert sha(exe) == sha(BUILD/'msvc/RelWithDebInfo/fallout-ce.exe')
assert sha(exe) == data(NEW/'manifest.json')['executable_sha256'].lower()
# Open-ground rendering must remain byte-identical in every pose.
unchanged = 0
for stem in ['stand-d'+str(d)+'-f000' for d in range(6)] + [f'walk-d{d}-f{f:03}' for d in range(6) for f in range(8)]:
    assert read(BUILD/'v1'/f'{stem}.png').tobytes() == read(NEW/f'{stem}.png').tobytes(), stem
    unchanged += 1

diffs=[]; sources=[]
source=WORK/'source'; reference=ROOT/'work/hd-world-pilot/fallout1-ce-main'
for p in sorted(source.rglob('*')):
    if not p.is_file(): continue
    relative=p.relative_to(source); previous=reference/relative
    if previous.exists() and p.read_bytes()==previous.read_bytes(): continue
    sources.append(relative.as_posix())
    diffs.extend(difflib.unified_diff(previous.read_text(encoding='utf-8').splitlines(keepends=True) if previous.exists() else [],
        p.read_text(encoding='utf-8').splitlines(keepends=True),fromfile='a/'+relative.as_posix(),tofile='b/'+relative.as_posix()))
(WORK/'source-changes.patch').write_text(''.join(diffs),encoding='utf-8')
report = {
    'status':'cave foreground sampling fixed and verified in isolated runtime',
    'cause':'Cave background sampler decoded padded actor owner texel using unpadded body width',
    'fix':'Shared canvas-aware body and floor-shadow sampling for direct and cave background rendering',
    'runtime':str(WORK/'runtime'), 'launcher':'Start-Fallout-HD-Player-Lighting.cmd',
    'executable_sha256':sha(exe), 'tests':{'cave-sampling-v2':result},
    'negative_control':{'test':'cave-sampling-red','result':red,'expected_failure':'cave player sampler mismatch','mismatches':5927968},
    'differential_samples':14109376,'differential_mismatches':0,
    'cave_poses_captured':54,'real_ce_walk_through_translucent_foreground':True,
    'unchanged_open_ground_pose_captures':unchanged,
    'unchanged_asset_files_verified':verified,'protected_shared_files_verified':len(baseline),
    'protected_shared_files_identical':len(baseline)-len(changed),'shared_files_modified_by_fix':[],
    'shared_files_changed':changed,
    'shared_config_note':'Shared fallout.cfg differs from the original generation baseline; its save precedes the fix backup. Preserved without edits. All shared sources, artwork and EXE hashes match.',
    'sources_changed_in_isolated_copy':sources,
    'previews':str(GALLERY), 'gallery_sha256':{p.name:sha(p) for p in GALLERY.iterdir() if p.suffix in ['.png','.gif','.webp']},
    'preview_notes':['Actual SDL pixels, no art edits or resampling; GIF uses a shared 256-color palette, WebP lossless',
        'Six-direction montage is fixed-pose captures at 10fps; separate real CE walk includes first24 samples',
        'Timed captures follow actor tile and include screenshot overhead, not a screen recording'],
    'artwork':'Original lighting-v2-x4 ImageGen body and pose shadow files unchanged; no generation in this fix'
}
for p in [WORK/'integration.json',BUILD/'integration.json',NEW/'fix-integration.json']:
    p.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({k:report[k] for k in ['tests','executable_sha256','unchanged_open_ground_pose_captures','unchanged_asset_files_verified','protected_shared_files_verified','shared_files_changed']},ensure_ascii=False))
