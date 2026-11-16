"""Compare and package real SDL screenshots; audit isolated installation."""
from pathlib import Path
import json,hashlib,importlib.util,difflib
from PIL import Image,ImageChops
ROOT=Path(__file__).resolve().parents[2]
WORK=Path(__file__).resolve().parent
BUILD=ROOT/'build/hd-player-lighting-20261116'
RUN=ROOT/'assets/generated/player-male-vault13/lighting-walk-v2-20261116'
PKG=ROOT/'assets/hd/player-male-vault13/lighting-v2-x4'
GALLERY=BUILD/'v1/gallery';GALLERY.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if sha(WORK/'runtime/fallout-ce.exe') != '9ca43e9905584075dc40a9085bebee825f612419c492e41e692ff7afbf3c0561':
    raise SystemExit('This is the historical v1 audit. For cave-sampling-v2 use review-cave-fix.py.')
spec=importlib.util.spec_from_file_location('preview',ROOT/'work/hd-player-male/tools/create-runtime-preview.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
def read(path):return Image.open(path).convert('RGB')
old=ROOT/'build/hd-player-shadow-20261116/baseline'
new=BUILD/'v1'
before=read(old/'stand-d2-f000.png');after=read(new/'stand-d2-f000.png')
helper.sheet([before,after],['Прежний HD','Новая светотень'],2).save(GALLERY/'lighting-before-after.png')
pairs=[helper.sheet([read(old/f'walk-d2-f{f:03}.png'),read(new/f'walk-d2-f{f:03}.png')],
    ['Прежний HD','Новая светотень'],2) for f in range(8)]
helper.animations(pairs,[100]*8,GALLERY/'lighting-walk-comparison')
baseline=json.loads((WORK/'baseline-sha256.json').read_text(encoding='utf-8-sig'))
changed=[r['path'] for r in baseline if sha(Path(r['path'])).upper()!=r['sha256']]
assert not changed,changed
manifest=json.loads((PKG/'manifest.json').read_text())
runtime=WORK/'runtime/data/art/hd/player-male-vault13'
installed=[]
for entry in manifest['entries']:
    for name in [entry['filename'],entry['png'],entry['shadow_mask']]:
        assert sha(PKG/name)==sha(runtime/name),name
        installed.append(name)
assert sha(PKG/'registry.tsv')==sha(runtime/'registry.tsv')
assert sha(WORK/'runtime/fallout-ce.exe')==sha(BUILD/'msvc/RelWithDebInfo/fallout-ce.exe')
receipts=json.loads((RUN/'imagegen-receipts.json').read_text())
for r in receipts:
    assert sha(Path(r['original_output']))==sha(RUN/r['project_output'])
results={name:json.loads((BUILD/name/'result.json').read_text()) for name in ['v1','corrupt-shadow']}
assert all(r['failed']==0 for r in results.values())
source=WORK/'source';reference=ROOT/'work/hd-world-pilot/fallout1-ce-main';diffs=[];sources=[]
for p in sorted(source.rglob('*')):
    if not p.is_file():continue
    relative=p.relative_to(source);oldpath=reference/relative
    if oldpath.exists() and p.read_bytes()==oldpath.read_bytes():continue
    sources.append(relative.as_posix())
    diffs.extend(difflib.unified_diff(oldpath.read_text(encoding='utf-8').splitlines(keepends=True) if oldpath.exists() else [],
        p.read_text(encoding='utf-8').splitlines(keepends=True),fromfile='a/'+relative.as_posix(),tofile='b/'+relative.as_posix()))
(WORK/'source-changes.patch').write_text(''.join(diffs),encoding='utf-8')
report={'status':'installed and verified in isolated CE cave runtime','component':'male Vault13 body relighting and pose-dependent ground shadow',
    'runtime':str(WORK/'runtime'),'launcher':'Start-Fallout-HD-Player-Lighting.cmd','package':str(PKG),
    'frame_count':54,'idle_directions':6,'walk_frames':48,'walk_fps':10,
    'executable_sha256':sha(WORK/'runtime/fallout-ce.exe'),'tests':results,
    'imagegen_receipts':str(RUN/'imagegen-receipts.json'),'all_six_imagegen_outputs_losslessly_copied':True,
    'installed_asset_files_verified':len(installed),'protected_shared_files_verified':len(baseline),'shared_files_changed':changed,
    'sources_changed_in_isolated_copy':sources,'old_new_stand_diff_bbox':ImageChops.difference(before,after).getbbox(),
    'previews':str(GALLERY),'source_mask_note':'Original idle207 and walk31/47/100 dark dither restricted to lower28%; runtime blur sigma0.85 native px, strength145/255, HD floor only',
    'limitations':['6 fixed-pose rendered cycles in montage, one actual multi-hex timed walk test',
        'AI preserves costume design but not every pixel/contour; registration matches previous native frame extents',
        'Existing side-view torso yaw variation retained; fine-detail/shape variation remains',
        'Unarmed male V13ENT stand/walk only; other actions/states retain classic fallback',
        'Baked body shading and approximate floor shadow, not a dynamic3D light simulation'],
    'gallery_sha256':{p.name:sha(p) for p in GALLERY.iterdir() if p.suffix in ['.gif','.webp','.png']}}
(WORK/'integration.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
(BUILD/'integration.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({'tests':results,'assets_verified':len(installed),'protected_files_verified':len(baseline),'shared_files_changed':changed,'exe':report['executable_sha256']},ensure_ascii=False))
