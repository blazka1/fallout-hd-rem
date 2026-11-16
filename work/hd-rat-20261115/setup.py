"""Snapshot current sources and art into an isolated rat preview, no shared edits."""
from pathlib import Path
import hashlib,json,shutil
R=Path(__file__).resolve().parents[2]
W=Path(__file__).resolve().parent
source=R/'work/hd-world-pilot/fallout1-ce-main'
dest=W/'source'
runtime=R/'runtime/hd-rat-pilot'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def snapshot(base):return {str(p.relative_to(base)).replace('\\','/'):sha(p) for p in base.rglob('*') if p.is_file()}
if dest.exists() or runtime.exists():raise FileExistsError('Isolated rat snapshot already exists; retain existing work.')
before=snapshot(source)
shutil.copytree(source,dest,ignore=shutil.ignore_patterns('__pycache__'))
assert before==snapshot(source),'Source changed during snapshot'
assert all(sha(dest/p)==digest for p,digest in before.items())
runtime.mkdir(parents=True)
old=R/'runtime/hd-world-pilot'
art_before=snapshot(old/'data/art')
shutil.copytree(old/'data/art',runtime/'data/art')
assert art_before==snapshot(old/'data/art'),'Shared art changed during snapshot'
for name in ['fallout.cfg','f1_res.ini','fallout-ce.exe']:
    shutil.copy2(old/name,runtime/name)
    assert sha(old/name)==sha(runtime/name)
record=dict(status='isolated snapshot; rat code not yet added',shared_source_hashes=before,
    shared_art_hashes=art_before,base_exe_sha256=sha(runtime/'fallout-ce.exe'),
    source=str(dest.relative_to(R)),runtime=str(runtime.relative_to(R)),shared_files_modified=False)
(W/'snapshot.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(source_files=len(before),art_files=len(art_before),runtime=str(runtime))))
