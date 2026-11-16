"""Final artifact/source audit; not a gameplay or animation test."""
from pipeline import ROOT,OUT,read,save,sha
from PIL import Image
import numpy as np

selection=dict(qwen='qwen-direct',dream='dream-direct/d22',seed_dream='seed-dream/d22',
    status='Representative sketches for comparison, not an approved game asset',
    reason='Uncontrolled Qwen matches the requested direct route; .22 is the common middle DreamShaper trial, not a winning preset')
save(OUT/'selection.json',selection)
before=read(OUT/'protected-before.json')
changed=[k for k,v in before.items() if not (ROOT/k).exists() or sha(ROOT/k)!=v]
sources=[]
for p in read(OUT/'plan.json')['poses']:
    ok=sha(ROOT/p['source'])==p['sha256']
    copy=OUT/'inputs'/(p['name']+'.png');assert ok and sha(copy)==p['sha256']
    indexed=Image.open(OUT/'inputs'/(p['name']+'-indexed.png'))
    assert indexed.mode=='P'
    sources.append(dict(name=p['name'],source_unchanged=ok,indexed_original_preserved=True))
jobs=[]
for path in sorted(OUT.glob('**/run.json')):
    d=path.parent;r=read(d/'result.json');history=read(d/'history.json')
    assert history['status']['status_str']=='success'
    assert r['prompt_id']==read(path)['prompt_id']
    assert (d/'workflow.json').exists() and (d/'prompt-api.json').exists()
    for f in r['files']:
        assert sha(d/f['file'])==f['sha256']
        im=Image.open(d/f['file']);im.verify()
    jobs.append(dict(path=str(d.relative_to(OUT)),prompt_id=r['prompt_id'],elapsed_seconds=r['elapsed_seconds']))
previews=[]
for p in sorted((OUT/'selected-preview').glob('*/*-preview-x4.png')):
    im=Image.open(p);im.load();a=np.array(im)[:,:,3]
    assert im.mode=='RGBA' and a.min()==0 and a.max()>=240
    previews.append(dict(file=str(p.relative_to(OUT)),size=list(im.size),sha256=sha(p)))
assert len(previews)==12
q=read(OUT/'image-qa.json');assert len(q)==9
assert all(p['alpha_matches_original_control'] for branch in q.values() for p in branch)
report=dict(status='art comparison complete; no approved replacement',
    source_checks=sources,successful_comfy_jobs=jobs,model_files_with_hashes=len(read(OUT/'model-files.json')),
    selected_sketches_x4=previews,selected_sketches_x2=len(list((OUT/'selected-preview').glob('*/*-preview-x2.png'))),
    registered_size_and_mask_checks=36,protected_files_checked=len(before),protected_files_changed=changed,
    quality_limits=['Qwen direct changes silhouette and loses ground shadows',
        'Qwen original-mask composite rejected for clipped/doubled details',
        'ControlNet .8 rejected for white background and flat coarse art; .3 still changes geometry and loses shadows',
        'DreamShaper direct has limited detail; SeedVR2 + DreamShaper looks flatter/brighter',
        'Four isolated poses only; temporal stability and CE integration not tested'],
    cave_preview='Static montage; no renderer lighting/occlusion',runtime_writes=False)
save(OUT/'final-audit.json',report)
print(dict(successful_jobs=len(jobs),selected_sketches=len(previews),protected_files=len(before),changed_files=changed,
           status=report['status']))
assert not changed,'Concurrent protected-file changes need investigation; do not claim unchanged.'
