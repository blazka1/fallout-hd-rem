"""Local patches on the FIRST FLUX only. No pose warp, FRM mask or registration."""
from pathlib import Path
import argparse,importlib.util,sys,uuid,shutil
from PIL import Image,ImageDraw,ImageFilter,ImageFont
import numpy as np
from scipy import ndimage as ndi
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'assets/generated/player-male-vault13/flux2-klein-4b-v11-20261116'
OUT=ROOT/'assets/generated/player-male-vault13/flux2-local-only-v13-20261117'
spec=importlib.util.spec_from_file_location('helpers',ROOT/'work/hd-player-three-pipelines-20261116/pipeline.py')
core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core);core.OUT=OUT
read,save,sha,node=core.read,core.save,core.sha,core.node
BOXES=[(64,64,192,192),(320,64,448,192),(64,448,192,576),(304,468,432,596)]
PROMPT=('Edit ONLY the specified clothing details in these four crops of the SAME male Vault 13 jumpsuit. '
        'Keep the exact same camera, pose, proportions, face, neck, shoulders, silhouette and lighting in all four crops. '
        'Remove every tiny yellow chest badge, chest numeral and chest emblem: replace them with matching plain worn dark blue fabric. '
        'Keep the single yellow vertical center stripe on the front and the yellow waistband. '
        'Remove the folded yellow shirt collar and triangular lapels in ALL views. Replace them with a simple FLAT BLUE ROUND NECKLINE, '
        'blue cloth lying flat against the base of the neck, without raised collar, without lapels and without yellow neck band. '
        'The yellow front stripe stops at the base of the neck. Do not change the face or hair. '
        'In the UPPER RIGHT rear view only, clarify the existing yellow number "13": two clear separate digits ONE and THREE, '
        'same size, same position and same perspective as the existing marking. Keep its subdued worn ochre colour and fabric texture. '
        'Do not add text anywhere else. Preserve the original dark desaturated blue fabric colour, texture, folds and wear. '
        'No added grain in this edit; the small amount of grain will be applied separately. Do not redesign or repaint the person. '
        'Keep the same four-crop 2x2 layout, exact crop framing, flat gray background, and every other detail unchanged.')

def prepare():
    if (OUT/'plan.json').exists():return
    inp=OUT/'inputs';inp.mkdir(parents=True,exist_ok=True)
    shutil.copy2(BASE/'edit-v1/raw.png',inp/'first-flux.png')
    shutil.copy2(BASE/'models.json',OUT/'model-files-inherited.json')
    src=Image.open(inp/'first-flux.png').convert('RGB');assert src.size==(512,768)
    sheet=Image.new('RGB',(512,512))
    for i,b in enumerate(BOXES):sheet.paste(src.crop(b).resize((256,256),Image.Resampling.LANCZOS),((i%2)*256,(i//2)*256))
    sheet.save(inp/'torso-crops.png')
    save(OUT/'plan.json',dict(status='four-frame local-only edit',source=str((BASE/'edit-v1/raw.png').relative_to(ROOT)),
        source_sha256=sha(inp/'first-flux.png'),size=[512,768],crop_boxes=BOXES,crop_uniform_scale=2,
        forbidden=['pose or contour warp','original FRM alpha','stretching','previous deformed v12 artwork','whole-image model replacement'],
        allowed=['local collar and chest-glyph edits','clearer existing back 13','very slight monochrome cloth grain'],
        final_canvas='first FLUX RGB copied unchanged outside explicit colour edit/grain masks',runtime_modified=False))
    tracked=[ROOT/'runtime/hd-world-pilot/fallout-ce.exe']+list((ROOT/'runtime/hd-world-pilot/data/art').rglob('*'))
    save(OUT/'runtime-before.json',{str(p.relative_to(ROOT)):sha(p) for p in tracked if p.is_file()})
    (OUT/'prompt.txt').write_text(PROMPT,encoding='utf8')
    print('Prepared FIRST FLUX only; four identical-scale torso crops',flush=True)

def edit():
    name='local-edit'
    if (OUT/name/'run.json').exists():core.execute(name,{},{});return
    g=read(BASE/'edit-v1/prompt-api.json')
    g['1']['inputs']['image']=core.upload(OUT/'inputs/torso-crops.png')
    g['5']['inputs']['text']=PROMPT
    g['12']['inputs'].update(width=512,height=512)
    g['14']['inputs'].update(width=512,height=512)
    g['13']['inputs']['noise_seed']=1711202713
    g['17']['inputs']['filename_prefix']='fallout1_flux_local/'+uuid.uuid4().hex+'/torso-edit'
    core.execute(name,g,{'17':'raw.png'})

def chest():
    name='side-chest-only'
    if (OUT/name/'run.json').exists():core.execute(name,{},{});return
    # Independent crop of the FIRST FLUX, never of another model's edited output.
    box=(344,512,408,576)
    im=Image.open(OUT/'inputs/first-flux.png').crop(box).resize((512,512),Image.Resampling.LANCZOS)
    im.save(OUT/'inputs/side-chest-crop.png')
    prompt=('Remove the small yellow emblem on the blue chest. Replace ONLY that emblem with plain blue fabric '
            'matching the surrounding worn cloth, folds, shading and texture. This area has absolutely NO text, '
            'NO numbers, NO 13, NO logo and NO symbols. Keep the vertical yellow stripe near the left edge exactly unchanged. '
            'Do not modify the collar, arm, body shape, crop, fabric colour or lighting. The result is the same '
            'close-up with the tiny chest emblem erased into continuous blue cloth.')
    g=read(OUT/'local-edit/prompt-api.json');g['1']['inputs']['image']=core.upload(OUT/'inputs/side-chest-crop.png')
    g['5']['inputs']['text']=prompt;g['13']['inputs']['noise_seed']=1711202714
    g['17']['inputs']['filename_prefix']='fallout1_flux_local/'+uuid.uuid4().hex+'/side-chest'
    core.execute(name,g,{'17':'raw.png'})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','edit','chest']);a=p.parse_args();globals()[a.stage]()
