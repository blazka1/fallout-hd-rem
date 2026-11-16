from prepare import *
import numpy as np
source=R/'assets/hd/v13ent/v14-campfire-x4/art/scenery/rock03.frm.png'
rect=[158,210,278,330];im=Image.open(source).convert('RGBA').crop(rect)
patch=Image.open(O/'reference-rock-detail.png').convert('RGBA')
assert np.array_equal(np.asarray(im),np.asarray(patch)) and im.getchannel('A').getextrema()==(255,255)
a=np.asarray(patch)[:,:,:3]
save(O/'material-provenance.json',dict(source_png=str(source.relative_to(R)),source_sha256=sha(source),crop_xyxy=rect,patch_sha256=sha(O/'reference-rock-detail.png'),opaque=True,rgb_median=np.median(a.reshape(-1,3),axis=0).tolist(),usage='Blender world-space box material: 42% color blend plus low-strength bump; no geometry or sprite mask inferred from this texture',box_density=1.45,box_blend=.3))
reg=read(O/'scene-registration.json');reg.update(source='continuous authored Blender rock mesh; procedural material plus verified rock03 detail patch',geometry_type='continuous sculpted rock with sparse partial faults, angular planes and shared crown',individual_plate_objects=0,material_provenance='material-provenance.json');save(O/'scene-registration.json',reg)
print('Reference material verified: exact opaque rock03 patch; median RGB',np.median(a.reshape(-1,3),axis=0))
