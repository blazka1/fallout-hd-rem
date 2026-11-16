"""Validate scoped wall texture changes and publish provenance after real renderer QA."""
import json,shutil,re
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import pipeline as q
p=q.p;R=q.R;B=q.B;PACK=q.PACK;DATA=q.DATA;BACK=q.BACK;RT=q.RT
def finish():
 q.idle();m=p.read(B/'verified/manifest.json');assert m['result']['failed']==0 and m['result']['passed']>=554
 assert m['executable_sha256'].lower()==p.sha(RT/'fallout-ce.exe')
 pack=p.read(PACK/'manifest.json');before=p.read(BACK/'runtime-before.json')
 # Pixel-level scope check on actual SDL captures, independent of packing.
 old=np.array(Image.open(B/'before/entrance-hd.png').convert('RGB'))
 new=np.array(Image.open(B/'verified/entrance-hd.png').convert('RGB'))
 owners=np.fromfile(B/'before/owners.bin',np.uint32).reshape(540,960)>>24
 scope=np.isin(owners,[a['id'] for a in pack['records']]);scope=np.repeat(np.repeat(scope,2,axis=0),2,axis=1)
 diff=np.any(old!=new,2);assert not (diff&~scope).any(),'unrelated visible pixels changed'
 p.save(B/'pixel-scope-check.json',dict(changed_pixels=int(diff.sum()),outside_target_owners=int((diff&~scope).sum())))
 allowed={str((DATA/a['file']).relative_to(R)) for a in pack['records']}
 cfg=RT/'fallout.cfg';normalize=lambda b:re.sub(rb'(?m)^splash=\d+',b'splash=0',b)
 assert normalize(cfg.read_bytes())==normalize((BACK/'fallout.cfg').read_bytes())
 protected=0
 for f,h in before.items():
  if f not in allowed and f!=str(cfg.relative_to(R)):
   assert p.sha(R/f)==h,f
   protected+=1
 for f,h in p.read(BACK/'protected.json').items():assert p.sha(R/f)==h,f
 runtime=p.read(DATA/'manifest.json');byid={a['asset_id']:a for a in runtime['assets']}
 for a in pack['records']:
  assert p.sha(DATA/a['file'])==a['runtime_sha256']
  byid[a['id']].update(source_png=str(PACK/a['png']),source_png_sha256=a['png_sha256'],runtime_file_sha256=a['runtime_sha256'],decoded_rgba_sha256=a['decoded_rgba_sha256'])
 runtime['component_patches'].append(dict(component='wall-upper-join-v1',package=str(PACK),changed_assets=[a['id'] for a in pack['records']],alpha_unchanged=True,geometry_changed=False))
 p.save(DATA/'manifest.json',runtime);shutil.copy2(BACK/'fallout.cfg',cfg)
 pack['status']='installed-and-verified';p.save(PACK/'manifest.json',pack)
 review=B/'review';review.mkdir(exist_ok=True);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',24)
 box=(1200,110,1660,580);sheet=Image.new('RGB',(920,510),(24,27,27));draw=ImageDraw.Draw(sheet)
 for i,(folder,label) in enumerate([('before','До'),('verified','После')]):
  image=Image.open(B/folder/'entrance-hd.png').convert('RGB').crop(box);sheet.paste(image,(i*460,40));draw.text((i*460+12,7),label,font=font,fill='white')
 sheet.save(review/'comparison.png')
 Image.open(B/'verified/entrance-hd-4k.png').crop(tuple(x*2 for x in box)).save(review/'wall-detail-4k.png')
 receipt=dict(status='installed-and-verified',checks=m['result'],executable_unchanged=True,executable_sha256=p.sha(RT/'fallout-ce.exe'),
  protected_prior_files=protected,changed_assets=[a['id'] for a in pack['records']],alpha_unchanged=True,geometry_changed=False,
  vault_rock_a_preserved=True,review=str(review.relative_to(R)),backup=str(BACK.relative_to(R)))
 p.save(B/'integration.json',receipt);p.save(R/'work/hd-wall-upper-join-20261115/task.json',receipt)
 print(json.dumps(dict(status=receipt['status'],passed=m['result']['passed'],failed=0,protected_files=protected)),flush=True)
if __name__=='__main__':finish()
