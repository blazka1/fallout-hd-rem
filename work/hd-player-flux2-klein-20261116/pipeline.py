"""Four original male sprites through installed FLUX.2 klein 4B Edit."""
from pathlib import Path
import argparse,importlib.util,json,shutil,struct,sys,uuid
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/'assets/generated/player-male-vault13/three-pipelines-guide-v9-20261116'
OUT=ROOT/'assets/generated/player-male-vault13/flux2-klein-4b-v11-20261116'
COMFY=Path('C:/Users/Administrator/AppData/Local/Comfy-Desktop/ComfyUI-Installs/local/ComfyUI')
spec=importlib.util.spec_from_file_location('shared_helpers',ROOT/'work/hd-player-three-pipelines-20261116/pipeline.py')
core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core);core.OUT=OUT
read,save,sha,node=core.read,core.save,core.sha,core.node
PROMPT=('Restore this exact atlas of FOUR original Fallout 1 male Vault 13 game sprites. '
    'Keep the fixed two-by-two layout: front three-quarter idle at upper left, rear three-quarter idle at upper right, '
    'southeast walking step at lower left, west-facing walking step at lower right. '
    'Keep exactly the existing poses, camera angle, body proportions, silhouette positions, arm swing, stride, foot contacts and spacing. '
    'Restore the original muted dark blue cloth jumpsuit with ochre yellow collar, front stripe, waistband and the small yellow 13 on the back; '
    'brown worn boots, bare hands, short brown hair and an ordinary adult face. '
    'Improve readability with restrained cloth folds, slight dust and wear, and simple believable facial planes. '
    'Preserve the volumetric late-1990s pre-rendered isometric RPG look, upper-left lighting, dark body shading, and ALL existing ground shadows with their original shape and extent. '
    'Moderately HD with subtle fine raster character, not a glossy beauty portrait, flat cartoon or coarse pixel-art redesign. '
    'Keep the existing neutral grey empty background and exact framing. No scenery, floor plane, new props, armor, weapons, pouches, extra figures, captions or borders. '
    'Only restore these four original sprites; retain the subdued palette and small scale of details.')

def prepare():
    if (OUT/'plan.json').exists():return
    OUT.mkdir(parents=True,exist_ok=True)
    shutil.copytree(OLD/'inputs',OUT/'inputs',dirs_exist_ok=True)
    shutil.copy2(OLD/'dream-direct/d22/input-rgb.png',OUT/'inputs/original-rgb-x4.png')
    plan=read(OLD/'plan.json')
    for p in plan['poses']:assert sha(ROOT/p['source'])==p['sha256']
    names=['diffusion_models/flux-2-klein-4b-fp8.safetensors','text_encoders/qwen_3_4b_fp4_flux2.safetensors','vae/flux2-vae.safetensors']
    models=[]
    for n in names:
        p=core.MODELS/n
        with p.open('rb') as f:
            count=struct.unpack('<Q',f.read(8))[0];header=json.loads(f.read(count))
        models.append(dict(file=str(p),bytes=p.stat().st_size,sha256=sha(p),metadata=header.get('__metadata__',{})))
        print('VERIFIED',n,flush=True)
    save(OUT/'models.json',models)
    shutil.copy2(COMFY/'blueprints/Image Edit (Flux.2 Klein 4B).json',OUT/'installed-base-blueprint-reference.json')
    save(OUT/'workflow-provenance.json',dict(
        local_blueprint='installed-base-blueprint-reference.json',
        distilled_reference='https://raw.githubusercontent.com/Comfy-Org/workflow_templates/main/templates/image_flux2_klein_image_edit_4b_distilled.json',
        docs='https://docs.comfy.org/tutorials/flux/flux-2-klein',
        recipe='Native Flux2Scheduler + Euler + CFG1 + ReferenceLatent + EmptyFlux2LatentImage; 4 distilled steps',
        adaptations=['512x768 registered source atlas, not default 1MP scaling','Installed FP4 Qwen3 4B Flux2 text encoder','Tiled VAE encode/decode 256px overlap64 to reduce peak VRAM'],
        official_json_download='Direct shell download blocked by network sandbox; official distilled graph inspected through web tool. No model download required.'))
    tracked=[ROOT/'AGENTS.md',ROOT/'HD-TEXTURE-GUIDE.md',ROOT/'runtime/hd-world-pilot/fallout-ce.exe',ROOT/'assets/generated/player-male-vault13/pixel-art-xl-v10-20261116/paused.json']+list((ROOT/'runtime/hd-world-pilot/data/art').rglob('*'))
    save(OUT/'protected-before.json',{str(p.relative_to(ROOT)):sha(p) for p in tracked if p.is_file()})
    save(OUT/'plan.json',dict(status='four-pose experiment, not installed',poses=plan['poses'],
        original_atlas=[128,192],working_atlas=[512,768],output_scales=[2,4],
        route='Original FRM -> ordinary Lanczos x4 -> FLUX.2 klein 4B reference edit (no SeedVR2, Qwen artwork, LoRA or ImageGen)',
        seed=1611202711,steps=4,cfg=1,sampler='euler',schedule='Flux2Scheduler',
        denoise='No SDXL img2img denoise: empty output latent and separate source reference latent',
        alpha='Original mask retained separately; compare raw RGB and original-mask composite, reject clipping/ghost artifacts',
        source_rgb_sha256=sha(OUT/'inputs/original-rgb-x4.png'),pixel_art_experiment='remains paused',runtime_modified=False))
    (OUT/'prompt.txt').write_text(PROMPT,encoding='utf8')
    save(OUT/'system-before.json',core.h.req('/system_stats'))
    print('PREPARED four original poses and Flux2 Edit graph settings',flush=True)

def run():
    name='edit-v1'
    if (OUT/name/'run.json').exists():core.execute(name,{},{});return
    g={'1':node('LoadImage',image=core.upload(OUT/'inputs/original-rgb-x4.png')),
       '2':node('UNETLoader',unet_name='flux-2-klein-4b-fp8.safetensors',weight_dtype='default'),
       '3':node('CLIPLoader',clip_name='qwen_3_4b_fp4_flux2.safetensors',type='flux2',device='default'),
       '4':node('VAELoader',vae_name='flux2-vae.safetensors'),
       '5':node('CLIPTextEncode',clip=['3',0],text=PROMPT),
       '6':node('CLIPTextEncode',clip=['3',0],text=''),
       '7':node('VAEEncodeTiled',pixels=['1',0],vae=['4',0],tile_size=256,overlap=64,temporal_size=64,temporal_overlap=8),
       '8':node('ReferenceLatent',conditioning=['5',0],latent=['7',0]),
       '9':node('ReferenceLatent',conditioning=['6',0],latent=['7',0]),
       '10':node('CFGGuider',model=['2',0],positive=['8',0],negative=['9',0],cfg=1.),
       '11':node('KSamplerSelect',sampler_name='euler'),
       '12':node('Flux2Scheduler',steps=4,width=512,height=768),
       '13':node('RandomNoise',noise_seed=1611202711),
       '14':node('EmptyFlux2LatentImage',width=512,height=768,batch_size=1),
       '15':node('SamplerCustomAdvanced',noise=['13',0],guider=['10',0],sampler=['11',0],sigmas=['12',0],latent_image=['14',0]),
       '16':node('VAEDecodeTiled',samples=['15',0],vae=['4',0],tile_size=256,overlap=64,temporal_size=64,temporal_overlap=8),
       '17':node('SaveImage',images=['16',0],filename_prefix='fallout1_player_flux2/'+uuid.uuid4().hex+'/four-poses')}
    core.execute(name,g,{'17':'raw.png'})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','run']);args=p.parse_args();globals()[args.stage]()
