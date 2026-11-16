"""Install only the new rat directory, current compiled EXE and explicit switch."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,shutil
R=Path(__file__).resolve().parents[2];B=R/'build/hd-rat-world-integration-20261115'
S=R/'work/hd-world-pilot/fallout1-ce-main';RT=R/'runtime/hd-world-pilot'
P=R/'assets/hd/critter-rat/qwen21-seedvr2-v1-x4'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
baseline=read(B/'baseline.json');merge=read(B/'source-merge.json')
for name,digest in merge['source_hashes'].items():assert sha(S/name)==digest,name
for name,digest in baseline['runtime'].items():assert sha(RT/name)==digest,('Runtime changed',name)
build=read(R/'build/hd-world-pilot/logs/build-manifest.json')
exe=R/'build/hd-world-pilot/msvc/RelWithDebInfo/fallout-ce.exe'
assert sha(exe)==build['executable_sha256'].lower()
target=RT/'data/art/hd/critter-rat';assert not target.exists()
manifest=read(P/'manifest.json');assert manifest['unique_images']==376
for im in manifest['images']:
    assert sha(P/'runtime'/im['runtime_file'])==im['runtime_sha256'],im['runtime_file']
shutil.copytree(P/'runtime',target)
manifest.update(runtime='runtime/hd-world-pilot',launcher='Start-Fallout-HD-World-Pilot.cmd',
    status='Installed; world integration checks pending',executable_sha256=sha(exe),
    source_package=P.relative_to(R).as_posix(),world_owner=254)
(target/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
shutil.copy2(exe,RT/'fallout-ce.exe')
cfg=RT/'fallout.cfg';text=cfg.read_text(encoding='utf-8-sig')
assert len(re.findall(r'^\[remaster\]$',text,re.M))==1
if re.search(r'^hd_rat=',text,re.M):text=re.sub(r'^hd_rat=.*$', 'hd_rat=1',text,flags=re.M)
else:text=text.replace('[remaster]\n','[remaster]\nhd_rat=1\n')
with cfg.open('w',encoding='utf-8',newline='\r\n') as f:f.write(text)
changed=[n for n,h in baseline['runtime'].items() if sha(RT/n)!=h]
assert set(changed)=={'fallout-ce.exe','fallout.cfg'},changed
receipt=dict(installed_utc=datetime.now(timezone.utc).isoformat(),executable_sha256=sha(exe),
    previous_executable_sha256=baseline['runtime_exe_sha256'],modified_prior_files=changed,
    unchanged_prior_files=len(baseline['runtime'])-len(changed),new_files=len(list(target.glob('*'))),
    environment_files_unchanged=True,rat_owner=254,wall_geometry_owner=253)
(B/'installation.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
