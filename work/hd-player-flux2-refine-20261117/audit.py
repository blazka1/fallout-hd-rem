"""Final provenance, dimensions and immutable-source audit for four review frames."""
from pipeline import ROOT,OUT,read,save,sha
from PIL import Image
import numpy as np

plan=read(OUT/'plan.json');geom=read(OUT/'registration-qa.json');finish=read(OUT/'finish-settings.json')
checks=[]
def check(name,ok,**details):checks.append(dict(check=name,pass_=bool(ok),**details))
for p,g in zip(plan['poses'],geom['frames']):
    check(p['name']+' original hash',sha(ROOT/p['source'])==p['sha256'])
    for scale in [2,4]:
        im=Image.open(OUT/'final'/(p['name']+f'-x{scale}.png'))
        check(p['name']+f' x{scale} RGBA/dimensions',im.mode=='RGBA' and im.size==(p['width']*scale,p['height']*scale))
    check(p['name']+' original body coverage agreement',g['native_body_silhouette_iou']>.97,body_iou=g['native_body_silhouette_iou'])
    check(p['name']+' initial inverse deformation has no folds',g['inverse_warp_fold_fraction']==0)
    body=Image.open(OUT/'final'/(p['name']+'-body-x4.png'));floor=Image.open(OUT/'final'/(p['name']+'-shadow-x4.png'))
    comp=floor.copy();comp.alpha_composite(body)
    check(p['name']+' separate shadow/body recomposition',np.array_equal(np.asarray(comp),np.asarray(Image.open(OUT/'final'/(p['name']+'-x4.png')))))
    check(p['name']+' floor copy intact',sha(OUT/'final'/(p['name']+'-shadow-x4.png'))==sha(OUT/'registered'/(p['name']+'-shadow-x4.png')))
    check(p['name']+' final hash',sha(OUT/'final'/(p['name']+'-x4.png'))==next(f['sha256'] for f in finish['frames'] if f['name']==p['name']))
for name in ['edit-two-references','neckline-edit','registered-cleanup']:
    hist=read(OUT/name/'history.json');result=read(OUT/name/'result.json')
    check(name+' successful FLUX job',hist['status']['status_str']=='success')
    check(name+' raw preserved',sha(OUT/name/'raw.png')==result['files'][0]['sha256'])
before=read(OUT/'protected-before.json');changed=[p for p,h in before.items() if not (ROOT/p).exists() or sha(ROOT/p)!=h]
runtime_changed=[p for p in changed if p.startswith('runtime')]
other_changed=[p for p in changed if p!='AGENTS.md' and not p.startswith('runtime')]
check('runtime files unchanged',not runtime_changed,count=sum(p.startswith('runtime') for p in before),changed=runtime_changed)
check('guide and paused task unchanged',not other_changed,changed=other_changed)
shared_observations=[dict(file=p,before=before[p],after=sha(ROOT/p),note='Changed during the task; our scripts and patches do not write this shared document. Current contents retained.') for p in changed if p=='AGENTS.md']
check('Pixel Art XL remains paused',read(ROOT/'assets/generated/player-male-vault13/pixel-art-xl-v10-20261116/paused.json')['do_not_auto_resume'])
save(OUT/'final-qa.json',dict(status='four review frames completed; no runtime installation',checks=checks,
    pass_count=sum(c['pass_'] for c in checks),fail_count=sum(not c['pass_'] for c in checks),
    visual_review=dict(chest='No extra glyphs; central stripe and waistband retained',neck='Folded yellow collar removed; flat blue neckline',
        back='Larger clear 13 reused from local FLUX correction',pose='Native contours, limb/foot landmarks, source floor footprints; soft antialiasing changes exact RGBA alpha',
        style='Muted blue, restrained grain and softness; faint contour stretching remains visible at enlarged size',
        context='Light/dark backgrounds and static cave montage inspected'),
    limitations=['Only four frames, not a complete animation','Static cave montage has no CE lighting/occlusion','Native contour IoU does not validate anatomy or animation','Small edge stretches are retained for review; not a released runtime asset'],
    protected_files_checked=len(before),protected_files_changed=changed,
    shared_document_observations=shared_observations,
    final_manifest=[dict(file=str(p.relative_to(OUT)),bytes=p.stat().st_size,sha256=sha(p)) for p in (OUT/'final').glob('*.png')]))
print({k:read(OUT/'final-qa.json')[k] for k in ['status','pass_count','fail_count','protected_files_checked','protected_files_changed']},flush=True)
assert all(c['pass_'] for c in checks)
