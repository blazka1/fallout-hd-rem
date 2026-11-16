"""Publish the verified executable and registry, preserving all other runtime files."""
import json,shutil,re,hashlib
from PIL import Image,ImageDraw,ImageFont
import prepare as q
R=q.R;RT=q.RT;DATA=q.DATA;BACK=q.BACK;PACK=q.PACK;p=q.p
B=R/'build/hd-vault-rock-a-20261115'
q.idle()
tested=RT/'fallout-vault-rock-test.exe';m=p.read(B/'verified/manifest.json')
assert m['result']['failed']==0 and m['result']['passed']>=554
assert m['executable_sha256'].lower()==p.sha(tested)
package=p.read(PACK/'manifest.json')
assert p.sha(DATA/'vault-rock-a.rgba')==package['runtime_sha256']
im=Image.open(PACK/'atlas.png').convert('RGBA')
assert (DATA/'vault-rock-a.rgba').read_bytes()[20:]==im.tobytes()
before=p.read(BACK/'runtime-before.json')
changed={str((DATA/f).relative_to(R)) for f in ['cave-variety-assets.tsv','cave-variety-placements.tsv']}
cfg=RT/'fallout.cfg';norm=lambda x:re.sub(rb'(?m)^splash=\d+',b'splash=0',x)
assert norm(cfg.read_bytes())==norm((BACK/'fallout.cfg').read_bytes()),'config changed beyond splash'
protected=0
for f,h in before.items():
 if f not in changed and f!=str(cfg.relative_to(R)):
  assert p.sha(R/f)==h,f
  protected+=1
for f,h in p.read(BACK/'protected.json').items():assert p.sha(R/f)==h,f
runtime=p.read(DATA/'manifest.json')
assert not any(a['asset_id']==252 for a in runtime['assets'])
runtime['assets'].append(dict(asset_id=252,category='cave-instance-appearance',native_width=128,native_height=128,
 width=512,height=512,scale=4,filename='vault-rock-a.rgba',source_png=str(PACK/'atlas.png'),source_png_sha256=p.sha(PACK/'atlas.png'),
 runtime_file='data/art/hd/world-pilot/vault-rock-a.rgba',runtime_file_sha256=package['runtime_sha256'],decoded_rgba_sha256=package['rgba_sha256'],
 original_alpha_reused=False,placement_transform='exact object 252; original 31x120 registration, crop 124x480'))
runtime['asset_count']=len(runtime['assets']);assert runtime['asset_count']==247
runtime['cave_appearance_image_count']=17;runtime['cave_appearance_placement_count']=77
runtime['component_patches'].append(dict(component='vault-rock-a-v1',package=str(PACK),object_id=252,asset_id=252,
 new_shape=True,game_map_modified=False,prior_246_asset_images_unchanged=True,
 assets_registry_sha256=p.sha(DATA/'cave-variety-assets.tsv'),placements_sha256=p.sha(DATA/'cave-variety-placements.tsv')))
shutil.copy2(tested,RT/'fallout-ce.exe');shutil.copy2(BACK/'fallout.cfg',cfg);p.save(DATA/'manifest.json',runtime)
package['status']='installed-and-verified';package['world_checks']=m['result'];p.save(PACK/'manifest.json',package)
review=B/'review';review.mkdir(exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',24)
box=(960,0,1380,440)
sheet=Image.new('RGB',(840,480),(24,27,27));draw=ImageDraw.Draw(sheet)
for i,(path,label) in enumerate([(R/'build/hd-cave-seams-20261115/world/entrance-hd.png','До'),(B/'verified/entrance-hd.png','Вариант A в игре')]):
 shot=Image.open(path).convert('RGB').crop(box);sheet.paste(shot,(i*420,40));draw.text((i*420+12,7),label,font=font,fill='white')
sheet.save(review/'comparison.png')
Image.open(B/'verified/entrance-hd-4k.png').crop(tuple(v*2 for v in box)).save(review/'junction-4k.png')
receipt=dict(status='installed-and-verified',executable_sha256=p.sha(RT/'fallout-ce.exe'),world_checks=m['result'],
 source_changes=['src/game/hd_cave_variety.inc','src/game/hd_world_pilot_test.cc'],
 protected_prior_files=protected,prior_246_asset_images_unchanged=True,agents_updated=False,
 review=str(review.relative_to(R)),backup=str(BACK.relative_to(R)),game_map_modified=False)
p.save(B/'integration.json',receipt);p.save(R/'work/hd-vault-rock-a-20261115/task.json',receipt)
assert p.sha(RT/'fallout-ce.exe')==m['executable_sha256'].lower()
assert p.sha(cfg)==p.sha(BACK/'fallout.cfg')
print(json.dumps(dict(status=receipt['status'],passed=m['result']['passed'],failed=0,protected_prior_files=protected,asset_count=247)),flush=True)
