"""Verify independent engine fallback captures and stable location assignments."""
import csv,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
out=Path(sys.argv[1]).resolve();runtime=ROOT/'runtime/hd-world-pilot'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
exe=sha(runtime/'fallout-ce.exe');cases=[];comparisons=[]
expected_count=read(runtime/'data/art/hd/world-pilot/manifest.json')['asset_count']-1
names=['omitted-slot-control','missing-file','invalid-alpha','invalid-header','changed-silhouette']
def assignments(folder):
    rows=csv.DictReader((folder/'wall-variant-assignments.tsv').read_text().splitlines(),delimiter='\t')
    # Object enumeration follows addresses, whose order can differ between processes.
    return sorted(tuple(int(r[k]) for k in ['object','fid','tile','elevation','base','appearance']) for r in rows)
control=out/names[0]
for name in names:
    folder=out/name;m=read(folder/'manifest.json');r=m['result']
    assert m['executable_sha256']==exe and r['failed']==0 and r['wall_variants']==23 and r['loaded_resources']==expected_count
    cases.append({'name':name,'result':r,'output':str(folder)})
    if name==names[0]:continue
    for file in ['entrance-hd.bmp','wall-variants-enabled.bmp']:
        assert sha(folder/file)==sha(control/file),(name,file)
        comparisons.append(name+'/'+file+' identical to omitted-slot control')
    assert assignments(folder)==assignments(control),name+' stable assignments differ'
    comparisons.append(name+' original object/location/appearance assignments identical after sorting by identity')
for p in (out/'backup').iterdir():
    assert sha(p)==sha(runtime/'data/art/hd/world-pilot'/p.name),'Runtime restoration mismatch'
report={'executable_sha256':exe,'cases':cases,'comparisons':comparisons,'restored_and_hash_verified':True,
    'passed':sum(c['result']['passed'] for c in cases)+len(comparisons),'failed':0,
    'comparison_note':'TSV enumeration order is address-dependent; exact object/FID/tile/elevation/appearance records compared independent of row order.'}
(out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'passed':report['passed'],'failed':0,'report':str(out/'manifest.json')}))
