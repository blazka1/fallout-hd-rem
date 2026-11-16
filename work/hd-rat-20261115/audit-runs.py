"""Audit saved provenance and source bytes without submitting generation jobs."""
from pathlib import Path
import hashlib,json,sys
from PIL import Image
R=Path(__file__).resolve().parents[2];O=R/'assets/generated/critter-rat/qwen21-seedvr2-v1-20261115'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checks=[]
for source in read(O/'inventory.json')['source_files']:
    p=O/'source/raw'/source['resource'];checks.append(dict(file=str(p.relative_to(O)),ok=sha(p)==source['sha256']))
for stage in ['seed','qwen','prepared-v2','prepared-aimed-v3','prepared-aimed-v4']:
    for p in sorted((O/stage).glob('*/result.json')):
        result=read(p);run=read(p.with_name('run.json'));history=read(p.with_name('history.json'))
        checks.append(dict(file=str(p.relative_to(O)),ok=result['prompt_id']==run['prompt_id'] and history['status']['status_str']=='success'))
        for record in result['files']:
            image=p.parent/record['file'];im=Image.open(image)
            checks.append(dict(file=str(image.relative_to(O)),ok=sha(image)==record['sha256'] and list(im.size)==record['size'] and im.mode==record['mode']))
report=dict(status='saved sources and completed runs audit',passed=sum(c['ok'] for c in checks),failed=sum(not c['ok'] for c in checks),checks=checks)
destination=O/('run-audit-'+(sys.argv[1] if len(sys.argv)>1 else 'current')+'.json')
destination.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(passed=report['passed'],failed=report['failed'],report=str(destination))))
if report['failed']:raise SystemExit(1)
