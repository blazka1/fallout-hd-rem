"""Apply only the reviewed player changes to the unchanged shared CE source."""
from pathlib import Path
import hashlib,json,subprocess,shutil
ROOT=Path(__file__).resolve().parents[2];WORK=Path(__file__).resolve().parent
SOURCE=ROOT/'work/hd-world-pilot/fallout1-ce-main'
SELECTED=ROOT/'work/hd-player-lighting-20261116/source'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
baseline=json.loads((WORK/'baseline.json').read_text())
for name,digest in baseline['source'].items():assert sha(SOURCE/name)==digest,name
assert all((SOURCE/name).exists()==(name in baseline['source']) for name in baseline['source_changes'])
patch=WORK/'source-changes.patch'
subprocess.run(['git','apply','--ignore-space-change','--check',str(patch)],cwd=SOURCE,check=True)
subprocess.run(['git','apply','--ignore-space-change',str(patch)],cwd=SOURCE,check=True)
after={p.relative_to(SOURCE).as_posix():sha(p) for p in SOURCE.rglob('*') if p.is_file()}
assert set(after)==set(baseline['selected_source'])
for name in after:
    # git apply can preserve CRLF context while new hunks use LF.
    assert (SOURCE/name).read_bytes()==(SELECTED/name).read_bytes() or (SOURCE/name).read_text(encoding='utf-8')==(SELECTED/name).read_text(encoding='utf-8'),name
changes=[name for name,value in after.items() if baseline['source'].get(name)!=value]
assert sorted(changes)==sorted(baseline['source_changes'])
report={'changed_files':changes,'source_matches_approved_test_ignoring_line_endings':True,'source_hashes':after}
(WORK/'source-merge.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
backup=Path(baseline['backup'])/'previous-build-logs'
logs=ROOT/'build/hd-world-pilot/logs'
if logs.exists():shutil.copytree(logs,backup)
print(json.dumps({'changed_files':changes,'source_matches_approved_test_ignoring_line_endings':True}))
