"""Local FLUX.2 klein refinement; task-local artwork, never a runtime install."""
from pathlib import Path
import argparse, importlib.util, json, shutil, sys, uuid
from PIL import Image
import numpy as np
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
PREV = ROOT/'assets/generated/player-male-vault13/flux2-klein-4b-v11-20261116'
OUT = ROOT/'assets/generated/player-male-vault13/flux2-refined-v12-20261117'
spec = importlib.util.spec_from_file_location('core', ROOT/'work/hd-player-three-pipelines-20261116/pipeline.py')
core = importlib.util.module_from_spec(spec); spec.loader.exec_module(core); core.OUT = OUT
read, save, sha, node = core.read, core.save, core.sha, core.node
PROMPT = '''Image 1 is the exact geometric template: four original Fallout 1 male game sprites. Image 2 is ONLY the material and facial reference from our previous FLUX version. Restore the four original sprites in image 1 using the worn dark-blue cloth, brown boots, short brown hair and ordinary rugged face of image 2.
Match IMAGE 1 precisely: the same overhead isometric camera, smaller heads, narrow shoulders, torso leaning, elbows, wrists, knees, feet, silhouettes and positions. Match each of the four DIFFERENT original poses, including the crossing legs and swinging arms of the bottom-left walking frame. Do NOT copy the broader shoulders, different stride, raised collar or larger cast shadows from image 2. Four figures only, fixed 2 by 2 layout with the exact original spacing.
Correct the outfit: a simple close-fitting ONE-PIECE jumpsuit with a flat round neckline, NO folded collar, NO shirt lapels, NO raised collar and NO V-neck opening. The thin worn ochre-yellow trim sits flat on the neckline and continues as a single center-front vertical stripe, with the original yellow waistband. The blue chest fabric to either side of this single stripe is COMPLETELY PLAIN: remove all chest badges, letters, symbols, numbers and logos. Only the upper-right REAR view has the small neat legible ochre number "13", two separate digits ONE and THREE, centered high on the back, following the fabric. No other lettering anywhere. Do not enlarge the back number.
Preserve modest fabric folds and dust, add just a little fine irregular grain and softly broken shading. Slightly soften the too-clean sharp finish: subdued moderately-HD late-1990s prerendered Fallout sprite, no portrait glamour, no giant pixels, no ink outlines. Maintain the original top-left lighting, dark sides of the torso and arms, exact foot contact and the small original ground shadows from IMAGE 1. Neutral flat gray background, no scenery, no floor plane, no labels, no extra objects. Output the exact layout and anatomy of image 1 with the corrected material of image 2.'''

def prepare():
    if (OUT/'plan.json').exists(): return
    inp=OUT/'inputs'; inp.mkdir(parents=True,exist_ok=True)
    shutil.copytree(PREV/'inputs',inp,dirs_exist_ok=True)
    shutil.copy2(PREV/'edit-v1/raw.png',inp/'previous-flux.png')
    shutil.copy2(PREV/'models.json',OUT/'model-files-inherited.json')
    source=Image.open(inp/'original-atlas.png').convert('RGBA')
    source=source.resize((768,1152),Image.Resampling.LANCZOS)
    bg=Image.new('RGBA',source.size,(162,164,167,255)); bg.alpha_composite(source)
    bg.convert('RGB').save(inp/'original-geometry-x6.png')
    Image.open(inp/'previous-flux.png').resize((768,1152),Image.Resampling.LANCZOS).save(inp/'previous-material-x6.png')
    poses=read(PREV/'plan.json')['poses']
    for p in poses: assert sha(ROOT/p['source'])==p['sha256']
    tracked=[ROOT/'AGENTS.md',ROOT/'HD-TEXTURE-GUIDE.md',ROOT/'runtime/hd-world-pilot/fallout-ce.exe',ROOT/'assets/generated/player-male-vault13/pixel-art-xl-v10-20261116/paused.json']+list((ROOT/'runtime/hd-world-pilot/data/art').rglob('*'))
    save(OUT/'protected-before.json',{str(p.relative_to(ROOT)):sha(p) for p in tracked if p.is_file()})
    save(OUT/'plan.json',dict(status='four-frame refinement, not installed',poses=poses,working_size=[768,1152],delivery_scale=4,
        previous_raw_sha256=sha(inp/'previous-flux.png'),guide_sha256=sha(ROOT/'HD-TEXTURE-GUIDE.md'),
        method='FLUX two references: original anatomy first, previous FLUX material second; deterministic registration and native shadow restoration after inspection',
        parameters=dict(steps=4,cfg=1,seed=1711202612,sampler='euler',schedule='Flux2Scheduler'),runtime_modified=False))
    (OUT/'prompt.txt').write_text(PROMPT,encoding='utf8')
    print('Prepared two references and fresh protected baseline',flush=True)

def run():
    name='edit-two-references'
    if (OUT/name/'run.json').exists(): core.execute(name,{},{});return
    g={'1':node('LoadImage',image=core.upload(OUT/'inputs/original-geometry-x6.png')),
       '2':node('UNETLoader',unet_name='flux-2-klein-4b-fp8.safetensors',weight_dtype='default'),
       '3':node('CLIPLoader',clip_name='qwen_3_4b_fp4_flux2.safetensors',type='flux2',device='default'),
       '4':node('VAELoader',vae_name='flux2-vae.safetensors'),
       '5':node('CLIPTextEncode',clip=['3',0],text=PROMPT),
       '6':node('CLIPTextEncode',clip=['3',0],text=''),
       '7':node('VAEEncodeTiled',pixels=['1',0],vae=['4',0],tile_size=256,overlap=64,temporal_size=64,temporal_overlap=8),
       '8':node('ReferenceLatent',conditioning=['5',0],latent=['7',0]),
       '9':node('ReferenceLatent',conditioning=['6',0],latent=['7',0]),
       '10':node('CFGGuider',model=['2',0],positive=['20',0],negative=['21',0],cfg=1.),
       '11':node('KSamplerSelect',sampler_name='euler'),
       '12':node('Flux2Scheduler',steps=4,width=768,height=1152),
       '13':node('RandomNoise',noise_seed=1711202612),
       '14':node('EmptyFlux2LatentImage',width=768,height=1152,batch_size=1),
       '15':node('SamplerCustomAdvanced',noise=['13',0],guider=['10',0],sampler=['11',0],sigmas=['12',0],latent_image=['14',0]),
       '16':node('VAEDecodeTiled',samples=['15',0],vae=['4',0],tile_size=256,overlap=64,temporal_size=64,temporal_overlap=8),
       '17':node('SaveImage',images=['16',0],filename_prefix='fallout1_flux_refine/'+uuid.uuid4().hex+'/four-poses'),
       '18':node('LoadImage',image=core.upload(OUT/'inputs/previous-material-x6.png')),
       '19':node('VAEEncodeTiled',pixels=['18',0],vae=['4',0],tile_size=256,overlap=64,temporal_size=64,temporal_overlap=8),
       '20':node('ReferenceLatent',conditioning=['8',0],latent=['19',0]),
       '21':node('ReferenceLatent',conditioning=['9',0],latent=['19',0])}
    core.execute(name,g,{'17':'raw.png'})

def neckline():
    name='neckline-edit'
    if (OUT/name/'run.json').exists():core.execute(name,{},{});return
    raw=Image.open(OUT/'edit-two-references/raw.png').convert('RGB')
    boxes=[(132,118,260,246),(518,124,646,252),(132,694,260,822),(500,725,628,853)]
    sheet=Image.new('RGB',(512,512))
    for i,b in enumerate(boxes):sheet.paste(raw.crop(b).resize((256,256),Image.Resampling.LANCZOS),((i%2)*256,(i//2)*256))
    sheet.save(OUT/'inputs/neckline-crops.png');save(OUT/'inputs/neckline-crop-boxes.json',boxes)
    prompt=('Edit these four cropped views of the SAME blue Vault 13 jumpsuit. Remove the folded yellow shirt collar and both triangular lapels completely in EVERY view. '
            'Replace them with plain blue jumpsuit fabric around a SIMPLE FLAT ROUND CREW NECK OPENING. No collar of any kind. '
            'The vertical yellow front stripe ends directly at the base of the bare neck. No horizontal yellow band around the neck. '
            'Preserve the same face, neck, shoulders, fabric folds, worn blue material, back number 13, pose, lighting and four-panel layout. '
            'Edit only the neck opening and former collar area. Absolutely no folded tabs or raised rim. Leave the chest completely plain blue to either side of its central yellow stripe.')
    g=read(OUT/'edit-two-references/prompt-api.json')
    for k in ['18','19','20','21']:del g[k]
    g['1']['inputs']['image']=core.upload(OUT/'inputs/neckline-crops.png')
    g['5']['inputs']['text']=prompt
    g['10']['inputs'].update(positive=['8',0],negative=['9',0])
    g['12']['inputs'].update(width=512,height=512)
    g['14']['inputs'].update(width=512,height=512)
    g['13']['inputs']['noise_seed']=1711202613
    g['17']['inputs']['filename_prefix']='fallout1_flux_refine/'+uuid.uuid4().hex+'/neckline'
    core.execute(name,g,{'17':'raw.png'})

def cleanup():
    name='registered-cleanup'
    if (OUT/name/'run.json').exists():core.execute(name,{},{});return
    im=Image.open(OUT/'registered/atlas-x4.png').resize((768,1152),Image.Resampling.LANCZOS)
    sheet=Image.new('RGBA',im.size,(151,153,153,255));sheet.alpha_composite(im)
    sheet.convert('RGB').save(OUT/'inputs/registered-cleanup-input.png')
    prompt=('Clean up only the stretched fabric and edge smears in this exact four-sprite atlas. '
            'Keep these same narrow original Fallout 1 bodies, small heads, fixed two by two positions, overhead isometric angle, '
            'exact pose, arm swing, crossed walking legs, bent knees, boot placement and small original ground shadows. '
            'Do not straighten their bodies, spread the legs, enlarge the heads or broaden the shoulders. '
            'Correct the deformed arm and trouser fabric into coherent worn dark blue cloth, with soft grain and restrained tiny texture. '
            'Preserve the ordinary adult face and short brown hair, bare hands, dusty brown boots, yellow center stripe and waistband. '
            'Keep the simple flat round BLUE neckline: NO collar, no lapels, no yellow neck band. '
            'Plain blue chest with NO letters or emblems. Only the rear upper-right figure has the clear small number 13 on its back. '
            'Do not add any other text. Preserve the flat grey background and exact sprite sizes and placement. '
            'Moderately HD pre-rendered game sprite, gently grainy cloth, no glamour, no razor-sharp digital outlines. '
            'This is a local repair, not a redesign. Preserve all four poses and existing cast-shadow footprints.')
    g=read(OUT/'edit-two-references/prompt-api.json')
    for k in ['18','19','20','21']:del g[k]
    g['1']['inputs']['image']=core.upload(OUT/'inputs/registered-cleanup-input.png')
    g['5']['inputs']['text']=prompt
    g['10']['inputs'].update(positive=['8',0],negative=['9',0])
    g['13']['inputs']['noise_seed']=1711202614
    g['17']['inputs']['filename_prefix']='fallout1_flux_refine/'+uuid.uuid4().hex+'/registered-cleanup'
    core.execute(name,g,{'17':'raw.png'})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','run','neckline','cleanup']);a=p.parse_args();globals()[a.stage]()
