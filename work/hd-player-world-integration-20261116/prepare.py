"""Capture the current live installation and prepare a disposable verification runtime."""
from pathlib import Path
import hashlib, json, shutil
ROOT=Path(__file__).resolve().parents[2]
WORK=Path(__file__).resolve().parent
BUILD=ROOT/'build/hd-player-world-integration-20261116'
BACKUP=ROOT/'build/backups/before-world-player-lighting-20261116'
LIVE=ROOT/'runtime/hd-world-pilot'
SOURCE=ROOT/'work/hd-world-pilot/fallout1-ce-main'
SELECTED=ROOT/'work/hd-player-lighting-20261116/source'
PACKAGE=ROOT/'assets/hd/player-male-vault13/lighting-v2-x4'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inventory(base):return {p.relative_to(base).as_posix():sha(p) for p in sorted(base.rglob('*')) if p.is_file()}
assert not (WORK/'baseline.json').exists(), 'Snapshot exists; do not overwrite it'
assert not BACKUP.exists(), 'Backup exists; choose a new integration directory'
BUILD.mkdir(parents=True,exist_ok=True)
BACKUP.mkdir(parents=True)
live=inventory(LIVE); source=inventory(SOURCE); selected=inventory(SELECTED)
source_changes=[name for name,value in selected.items() if source.get(name)!=value]
assert len(source_changes)==8 and set(source).issubset(selected)
manifest=json.loads((PACKAGE/'manifest.json').read_text())
asset_names=['registry.tsv','manifest.json']
for entry in manifest['entries']:
    for key,hashkey in [('png','png_sha256'),('filename','rgba_sha256'),('shadow_mask','shadow_mask_sha256')]:
        assert sha(PACKAGE/entry[key])==entry[hashkey]
        asset_names.append(entry[key])
targets=['work/hd-world-pilot/fallout1-ce-main/'+p for p in source_changes]
targets+=['runtime/hd-world-pilot/fallout-ce.exe']
targets+=['runtime/hd-world-pilot/data/art/hd/player-male-vault13/'+p for p in asset_names]
targets+=['work/hd-world-pilot/task.json','work/hd-world-pilot/README.txt','build/hd-world-pilot/integration-manifest.json']
before={}
for name in targets:
    p=ROOT/name;before[name]=sha(p) if p.is_file() else None
    if p.is_file():
        dest=BACKUP/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
        assert sha(dest)==before[name]
protected={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'AGENTS.md',ROOT/'Start-Fallout-HD-World-Pilot.cmd']}
data={'runtime':live,'source':source,'selected_source':selected,'source_changes':source_changes,
    'asset_names':asset_names,'target_before':before,'protected':protected,
    'runtime_executable_before':live['fallout-ce.exe'],'backup':str(BACKUP)}
(WORK/'baseline.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
(BACKUP/'manifest.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
shutil.copytree(LIVE,WORK/'runtime')
assert inventory(WORK/'runtime')==live
shutil.copy2(ROOT/'work/hd-player-lighting-20261116/source-changes.patch',WORK/'source-changes.patch')
print(json.dumps({'runtime_files':len(live),'source_files':len(source),'source_changes':source_changes,
    'package_files':len(asset_names),'backup_files':sum(v is not None for v in before.values()),'runtime_copy_identical':True}))
