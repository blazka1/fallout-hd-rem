"""Four original male sprites: local SeedVR2 -> Qwen 2.1, preview only."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,sys,uuid
from PIL import Image,ImageDraw,ImageFont
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2];WORK=Path(__file__).resolve().parent
OUT=ROOT/'assets/generated/player-male-vault13/original-seed-qwen-4poses-20261116'
REF=ROOT/'assets/reference/player-male-vault13'
spec=importlib.util.spec_from_file_location('comfy_helpers',ROOT/'work/cave-variety-seed-qwen-20261115/pipeline.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h);h.OUT=OUT
read=h.read;save=h.save;sha=h.sha;node=h.node
POSES=[('stand',2,0,'Стойка спереди'),('stand',0,0,'Стойка сзади'),('walk',2,2,'Шаг, юго-восток'),('walk',4,6,'Шаг, запад')]

def prepare():
    if (OUT/'plan.json').exists():return
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'inputs').mkdir()
    atlas=Image.new('RGBA',(128,192));records=[]
    for i,(action,direction,frame,label) in enumerate(POSES):
        frm='hmjmpsaa' if action=='stand' else 'hmjmpsab'
        p=REF/f'rgba/art/critters/{frm}.frm/d{direction}-f{frame:03}.png'
        original=Image.open(p).convert('RGBA')
        assert original.width<=56 and original.height<=80
        x=(i%2)*64+(64-original.width)//2;y=(i//2)*96+84-original.height
        atlas.paste(original,(x,y))
        name=f'{action}-d{direction}-f{frame:03}'
        (OUT/'inputs'/f'{name}.png').write_bytes(p.read_bytes())
        records.append(dict(name=name,label=label,action=action,direction=direction,frame=frame,
            source=str(p.relative_to(ROOT)),sha256=sha(p),frm_sha256=sha(REF/f'raw/art/critters/{frm}.frm'),
            width=original.width,height=original.height,x=x,y=y))
    atlas.save(OUT/'inputs/original-atlas.png')
    # Diagnostic nearest-neighbour display only, never used as neural output.
    atlas.resize((512,768),Image.Resampling.NEAREST).save(OUT/'inputs/original-nearest-x4.png')
    protected=[ROOT/'runtime/hd-world-pilot/fallout-ce.exe']+list((ROOT/'runtime/hd-world-pilot/data/art').rglob('*'))
    save(OUT/'runtime-art-baseline.json',{str(p.relative_to(ROOT)):sha(p) for p in protected if p.is_file()})
    save(OUT/'plan.json',dict(status='original-sprite preview, not installed',layout='2x2: front idle, rear idle / SE walking f2, W walking f6',
        native_atlas=[128,192],working_atlas=[512,768],scale=4,poses=records,
        source='Original exported FRM RGBA, not the installed ImageGen character',
        comfy_python='ComfyUI/.venv/Scripts/python.exe',existing_models=True))
    save(OUT/'system-before.json',h.h.req('/system_stats'))
    print('PREPARED four unchanged original sprites',flush=True)

def seed():
    d=OUT/'seedvr2'
    if (d/'result.json').exists():return
    if (d/'run.json').exists():h.execute(d,{},{});return
    g=read(ROOT/'assets/generated/inventory-knife/seedvr2-x4-20261113/prompt-api.json')
    g['1']['inputs']['image']=h.upload(OUT/'inputs/original-atlas.png')
    g['9']['inputs']['seed']=161120264
    prefix='fallout1_player_original/'+uuid.uuid4().hex
    g['12']['inputs']['filename_prefix']=prefix+'/seedvr2-x4'
    g['13']['inputs']['filename_prefix']=prefix+'/lanczos-x4'
    h.execute(d,g,{'12':'seedvr2-x4.png','13':'lanczos-x4.png'})

def qwen():
    d=OUT/'qwen'
    if (d/'result.json').exists():return
    if (d/'run.json').exists():h.execute(d,{},{});return
    prompt=('Restore these FOUR original Fallout 1 male Vault Dweller game sprites as clean detailed pre-rendered 3D-style 2D game art. '
        'This is a fixed 2 by 2 sprite atlas: top left front three-quarter idle, top right rear three-quarter idle, '
        'bottom left a southeast walking step, bottom right a west-facing walking step. '
        'Keep exactly four figures in their exact separate cells, unchanged positions, scale, silhouettes, stout original proportions, '
        'joint positions, foot contacts, arm swing, camera angle and facing direction. Do not turn, straighten, recenter or replace any pose. '
        'Preserve the ORIGINAL simple blue Vault 13 jumpsuit design from the input: muted blue fabric, yellow collar and vertical front stripe, '
        'yellow waist band and yellow 13 on the back where visible, brown boots, bare hands, short brown hair. '
        'Restore the original costume, not a redesign. Do not add armor plates, a tactical vest, shoulder pads, belts, pouches, weapons or props. '
        'Resolve pixel blocks and dithering into smooth continuous shading, readable anatomical volumes, restrained fabric seams and natural folds. '
        'Keep original upper-left lighting, dark shaded torso sides and leg recesses, and the existing small cast shadows on the ground. '
        'Preserve the restrained dark blue and yellow palette, no bright saturated colors, no plastic shine, no grain or painterly brushwork. '
        'Transparent empty background between figures; no ground plane, scene, backdrop, labels, borders or additional characters. '
        'The only lettering is the original small yellow number 13 on the rear-facing suit. Keep the exact atlas layout.')
    g={'1':node('LoadImage',image=h.upload(OUT/'seedvr2/seedvr2-x4.png')),
       '2':node('JoinImageWithAlpha',image=['1',0],alpha=['1',1]),
       '4':node('UNETLoader',unet_name='qwen_image_2.1_int8_convrot.safetensors',weight_dtype='default'),
       '5':node('CLIPLoader',clip_name='qwen3vl_8b_int8_convrot.safetensors',type='qwen_image',device='default'),
       '6':node('VAELoader',vae_name='qwen_image_2.1_vae_bf16.safetensors'),
       '7':node('QwenImage21Cache',model=['4',0],device='cpu',dtype='default'),
       '8':node('TextEncodeQwenImage21',clip=['5',0],prompt=prompt,negative_prompt='',vae=['6',0],resolution=0,**{'images.image_1':['2',0]}),
       '9':node('KSampler',model=['7',0],positive=['8',0],negative=['8',1],latent_image=['8',2],
           seed=161120264,steps=25,cfg=1.0,sampler_name='euler',scheduler='simple',denoise=1.0),
       '10':node('VAEDecode',samples=['9',0],vae=['6',0]),
       '11':node('SaveImage',images=['10',0],filename_prefix='fallout1_player_original/'+uuid.uuid4().hex+'/qwen-raw')}
    d.mkdir(parents=True,exist_ok=True);(d/'prompt.txt').write_text(prompt,encoding='utf-8')
    h.execute(d,g,{'11':'raw.png'})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','seed','qwen']);args=p.parse_args()
    {'prepare':prepare,'seed':seed,'qwen':qwen}[args.stage]()
