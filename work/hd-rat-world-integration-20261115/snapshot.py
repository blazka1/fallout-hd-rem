"""Capture the actual current world build before the rat-only merge."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, shutil

R=Path(__file__).resolve().parents[2]
W=Path(__file__).resolve().parent
B=R/'build/hd-rat-world-integration-20261115'
BACK=R/'build/backups/before-world-hd-rat-20261115'
S=R/'work/hd-world-pilot/fallout1-ce-main'
RT=R/'runtime/hd-world-pilot'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not BACK.exists(), 'Preserve the existing backup.'
assert not (RT/'data/art/hd/critter-rat').exists()
BACK.mkdir(parents=True);B.mkdir(parents=True,exist_ok=True)
shutil.copytree(S,BACK/'source')
for rel in ['AGENTS.md','Start-Fallout-HD-World-Pilot.cmd','work/hd-world-pilot/task.json',
            'work/hd-world-pilot/README.txt','build/hd-world-pilot/integration-manifest.json',
            'runtime/hd-world-pilot/fallout-ce.exe','runtime/hd-world-pilot/fallout.cfg',
            'runtime/hd-world-pilot/f1_res.ini']:
    src=R/rel;dst=BACK/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
state=dict(created_utc=datetime.now(timezone.utc).isoformat(),runtime_exe_sha256=sha(RT/'fallout-ce.exe'),
    source={p.relative_to(S).as_posix():sha(p) for p in S.rglob('*') if p.is_file()},
    runtime={p.relative_to(RT).as_posix():sha(p) for p in RT.rglob('*') if p.is_file()},
    documents={str(p.relative_to(R)):sha(p) for p in [R/'AGENTS.md',R/'HD-TEXTURE-GUIDE.md']},
    backup=BACK.relative_to(R).as_posix())
(B/'baseline.json').write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
(W/'task.json').write_text(json.dumps(dict(status='integrating',scope='Rat-only merge into current world runtime; preserve all prior environment files',backup=state['backup']),indent=2)+'\n')
print(json.dumps(dict(runtime_files=len(state['runtime']),source_files=len(state['source']),exe=state['runtime_exe_sha256'],backup=state['backup'])))
