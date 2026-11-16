from pathlib import Path
import json,hashlib,shutil
R=Path(__file__).resolve().parents[2];B=R/'build/hd-rat-world-integration-20261115'
RT=R/'runtime/hd-world-pilot';S=R/'work/hd-world-pilot/fallout1-ce-main'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
base=read(B/'baseline.json');merge=read(B/'source-merge.json')
for n,h in merge['source_hashes'].items():assert sha(S/n)==h,n
for n,h in base['runtime'].items():
    if n not in ('fallout-ce.exe','fallout.cfg'):assert (RT/n).is_file() and sha(RT/n)==h,n
exe=R/'build/hd-world-pilot/msvc/RelWithDebInfo/fallout-ce.exe'
build=read(R/'build/hd-world-pilot/logs/build-manifest.json');assert sha(exe)==build['executable_sha256'].lower()
receipt=read(B/'installation.json');receipt.setdefault('superseded_integration_exes',[]).append(receipt['executable_sha256'])
receipt['executable_sha256']=sha(exe);shutil.copy2(exe,RT/'fallout-ce.exe')
(B/'installation.json').write_text(json.dumps(receipt,indent=2)+'\n')
p=RT/'data/art/hd/critter-rat/manifest.json';j=read(p);j['executable_sha256']=sha(exe)
p.write_text(json.dumps(j,indent=2)+'\n')
print('Installed EXE:',sha(exe))
