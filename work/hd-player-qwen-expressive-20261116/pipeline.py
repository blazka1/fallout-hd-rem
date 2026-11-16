"""A more expressive Qwen study with fixed FRM anchors and contour control."""
from pathlib import Path
import argparse,importlib.util,json,sys,uuid
from PIL import Image
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2];WORK=Path(__file__).resolve().parent
PREV=ROOT/'assets/generated/player-male-vault13/original-seed-qwen-4poses-20261116'
OUT=ROOT/'assets/generated/player-male-vault13/qwen-expressive-4poses-v2-20261116'
REF=ROOT/'assets/reference/player-male-vault13'
spec=importlib.util.spec_from_file_location('helpers',ROOT/'work/cave-variety-seed-qwen-20261115/pipeline.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h);h.OUT=OUT
read=h.read;save=h.save;sha=h.sha;node=h.node
sys.path.insert(0,str(ROOT/'tools/asset-pipeline'))
from fallout_assets import decode_frm

def prepare():
    if (OUT/'plan.json').exists():return
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'inputs').mkdir()
    old=read(PREV/'plan.json');seed=Image.open(PREV/'seedvr2/seedvr2-x4.png').convert('RGBA')
    first=Image.open(PREV/'qwen/raw.png').convert('RGBA')
    native=Image.new('RGBA',(128,192));registered=Image.new('RGBA',(512,768));previous=Image.new('RGBA',(512,768))
    records=[]
    for i,p in enumerate(old['poses']):
        frm='hmjmpsaa' if p['action']=='stand' else 'hmjmpsab'
        raw=REF/f'raw/art/critters/{frm}.frm';meta,frames=decode_frm(raw.read_bytes())
        d=p['direction'];f=p['frame'];frame=frames[d][f]
        cx=(i%2)*64;cy=(i//2)*96;anchor=[cx+32,cy+80]
        left=anchor[0]+meta['direction_x'][d]-frame.width//2
        top=anchor[1]+meta['direction_y'][d]-frame.height+1
        dx=(left-p['x'])*4;dy=(top-p['y'])*4
        original=Image.open(ROOT/p['source']).convert('RGBA');native.paste(original,(left,top))
        box=(cx*4,cy*4,(cx+64)*4,(cy+96)*4)
        for src,dest in [(seed,registered),(first,previous)]:
            cell=src.crop(box);shifted=Image.new('RGBA',(256,384));shifted.paste(cell,(dx,dy));dest.paste(shifted,(cx*4,cy*4))
            if src is seed:
                assert cell.getchannel('A').histogram()==shifted.getchannel('A').histogram(),'Reference clipped by registration'
        records.append(dict(**p,frm=str(raw.relative_to(ROOT)),fps=meta['fps'],action_frame=meta['action_frame'],
            frame_count=meta['frame_count'],direction_offset=[meta['direction_x'][d],meta['direction_y'][d]],
            frame_shift=[frame.shift_x,frame.shift_y],anchor_native=anchor,left_native=left,top_native=top,
            old_atlas_to_registered_x4=[dx,dy],object_xy_for_in_place_preview=[0,0],
            motion_note='Frame deltas retained as metadata; no cumulative locomotion applied to these isolated in-place poses'))
    native.save(OUT/'inputs/original-registered-native.png');registered.save(OUT/'inputs/seed-registered-x4.png')
    previous.save(OUT/'inputs/first-qwen-registered-x4.png')
    save(OUT/'plan.json',dict(status='preview only, not installed',poses=records,logical_atlas=[128,192],
        seed_atlas=[512,768],working_atlas=[768,1152],preview_export=[512,768],
        guide='old-new-persons-model-converter.md',guide_sha256=sha(ROOT/'old-new-persons-model-converter.md'),
        seed_reused_sha256=sha(PREV/'seedvr2/seedvr2-x4.png'),
        applied=['CE anchor convention including direction offsets and top=anchor-height+1',
            'Same four poses in one atlas with one palette, camera and light specification',
            'Shared neutral matte for contour extraction, independent generated RGBA',
            'Contour control and separate alpha QA; no forced original silhouette to conceal drift',
            'IoU and HD95 plus mask extent/centroid measurements'],
        not_implemented=['Full temporal cycle validation','Complete edge-color extension and constrained matting converter'],
        qwen={'steps':25,'cfg':1,'denoise':1,'seed':161120265,'cpu_kv_cache':True,'control_strength':0.8,'control_end':0.85}))
    protected=[ROOT/'runtime/hd-world-pilot/fallout-ce.exe']+list((ROOT/'runtime/hd-world-pilot/data/art').rglob('*'))
    save(OUT/'runtime-art-baseline.json',{str(p.relative_to(ROOT)):sha(p) for p in protected if p.is_file()})
    print('Prepared four poses with CE anchors and source frame passports',flush=True)

def control():
    d=OUT/'control-v2'
    if (d/'result.json').exists():return
    if (d/'run.json').exists():h.execute(d,{},{});return
    g={'1':node('LoadImage',image=h.upload(OUT/'inputs/seed-registered-x4.png')),
       '2':node('JoinImageWithAlpha',image=['1',0],alpha=['1',1]),
       '3':node('ImageScale',image=['2',0],upscale_method='lanczos',width=768,height=1152,crop='disabled'),
       '4':node('EmptyImage',width=512,height=768,batch_size=1,color=8421504),
       '5':node('InvertMask',mask=['1',1]),
       '6':node('ImageCompositeMasked',destination=['4',0],source=['1',0],x=0,y=0,resize_source=False,mask=['5',0]),
       '7':node('ImageScale',image=['6',0],upscale_method='lanczos',width=768,height=1152,crop='disabled'),
       '8':node('Canny',image=['7',0],low_threshold=0.05,high_threshold=0.12),
       '9':node('SaveImage',images=['3',0],filename_prefix='fallout1_player_expressive/'+uuid.uuid4().hex+'/seed-reference'),
       '10':node('SaveImage',images=['7',0],filename_prefix='fallout1_player_expressive/'+uuid.uuid4().hex+'/neutral-reference'),
       '11':node('SaveImage',images=['8',0],filename_prefix='fallout1_player_expressive/'+uuid.uuid4().hex+'/canny')}
    h.execute(d,g,{'9':'seed-reference.png','10':'neutral-reference.png','11':'canny.png'})

def qwen(soft=False):
    d=OUT/('qwen-soft' if soft else 'qwen')
    if (d/'result.json').exists():return
    if (d/'run.json').exists():h.execute(d,{},{});return
    prompt=('Re-render these FOUR original Fallout Vault 13 male sprites with moderately MORE EXPRESSIVE, REALISTIC MATERIALS AND MODELING. '
        'Create high-quality pre-rendered isometric RPG character art, like a carefully lit realistic miniature. '
        'Keep the same adult man, short brown hair, original stocky proportions, blue and yellow Vault jumpsuit and brown boots in all four cells. '
        'The blue jumpsuit is REAL MATTE WOVEN WORKWEAR, not smooth rubber, spandex, a superhero bodysuit or painted skin. '
        'Show meaningful cloth tension and compression: small collar folds, bent-elbow creases, gathered fabric at the waist, '
        'diagonal folds across the hips, compression behind knees and a few folds above the boots. '
        'Add restrained fine weave, visible existing seams and stitching, subtle wear at elbows and knees, and supple worn brown leather boots with defined soles. '
        'Keep large readable planes between the folds; do not cover the suit with noisy microtexture or random wrinkles. '
        'Make the face slightly more characterful with a defined brow, cheekbones and natural skin shading, without changing the identity or enlarging the head. '
        'Use stronger but believable upper-left key lighting, soft fill, occlusion under the chin, inside elbows, at the waist and between legs. '
        'Retain the original small dark contact and cast shadows by the feet. Muted indigo-blue fabric and warm mustard-yellow trim, no saturated neon yellow. '
        'Preserve the original SIMPLE costume design: yellow collar, front stripe and waist band, yellow 13 on the back, bare hands. '
        'Do not add armor, shoulder pads, weapons, pouches, decorative panels, new belts, logos or accessories. '
        'Avoid cartoon, toy, clay, wax, glossy plastic, smooth muscle-shaped rubber and painted illustration. '
        'Exact 2x2 atlas layout: front three-quarter idle top left, rear three-quarter idle top right, southeast walking step bottom left, west walking step bottom right. '
        'Follow the control contours. Preserve exact positions, foot anchors, limb angles, strides, facing directions and figure scale; do not recenter any figure. '
        'Redraw material and light inside the established shapes, not the anatomy or poses. Transparent background, no scene, floor plane, labels, borders or extra people.')
    if soft:
        prompt=('Edit this transparent RGBA atlas of four Fallout Vault 13 male sprites. Keep the background transparent with alpha zero. '
            'Keep exactly these four characters at the same positions, scale, foot contacts, poses, camera angles and facing directions. '
            'Make the existing costume moderately more expressive and believable through fabric, light and facial detail. '
            'Preserve the original blue jumpsuit, mustard-yellow collar, front stripe, waist band, yellow 13 on the back, brown boots, bare hands and short brown hair. '
            'Render a realistic adult human wearing a tailored matte cotton-twill work jumpsuit. The fabric rests over the body rather than tracing every muscle. '
            'Use soft natural cloth folds at elbows, waist, crotch and knees, fine existing seams and stitching, subtle fabric weave and light wear. '
            'Brown leather boots have natural creases and defined soles. Add a little more definition to the brow, nose, cheekbones and hands without changing identity or proportions. '
            'Keep readable broad fabric planes and quiet textures. Use clear upper-left lighting with soft fill and deep contact shading under the chin, arms and between the legs. '
            'Retain the existing small ground shadows beside the feet as part of the transparent sprites. '
            'Smooth the old pixel stair-steps into natural contours. Preserve the overall silhouettes and exact strides, but do not reproduce jagged pixel blocks or hard polygon-like folds. '
            'The result is detailed realistic pre-rendered isometric RPG art, not a cartoon, toy, plastic figure, painting or rubber superhero suit. '
            'No new armor, pouches, equipment, shoulder pads, belts or props. '
            'Keep the exact 2x2 atlas arrangement: front idle, rear idle, southeast walking step, west walking step. '
            'Keep transparent empty space around and between the four figures. Do not paint a white or colored background or a floor surface. Output transparent RGBA.')
    g={'1':node('LoadImage',image=h.upload(OUT/'control-v2/seed-reference.png')),
       '2':node('JoinImageWithAlpha',image=['1',0],alpha=['1',1]),
       '3':node('LoadImage',image=h.upload(OUT/'control-v2/canny.png')),
       '4':node('UNETLoader',unet_name='qwen_image_2.1_int8_convrot.safetensors',weight_dtype='default'),
       '5':node('CLIPLoader',clip_name='qwen3vl_8b_int8_convrot.safetensors',type='qwen_image',device='default'),
       '6':node('VAELoader',vae_name='qwen_image_2.1_vae_bf16.safetensors'),
       '7':node('QwenImage21Cache',model=['4',0],device='cpu',dtype='default'),
       '8':node('TextEncodeQwenImage21',clip=['5',0],prompt=prompt,negative_prompt='',vae=['6',0],resolution=0,**{'images.image_1':['2',0]}),
       '9':node('ModelPatchLoader',name='qwen_image_2.1_fun_controlnet_union_int8_convrot.safetensors'),
       '10':node('ZImageFunControlnet',model=['7',0],model_patch=['9',0],vae=['6',0],strength=(.35 if soft else .8),image=['3',0],start_percent=0.,end_percent=(.65 if soft else .85)),
       '11':node('KSampler',model=['10',0],positive=['8',0],negative=['8',1],latent_image=['8',2],
           seed=161120265,steps=25,cfg=1.,sampler_name='euler',scheduler='simple',denoise=1.),
       '12':node('VAEDecode',samples=['11',0],vae=['6',0]),
       '13':node('SaveImage',images=['12',0],filename_prefix='fallout1_player_expressive/'+uuid.uuid4().hex+'/raw'),
       '14':node('ImageScale',image=['12',0],upscale_method='lanczos',width=512,height=768,crop='disabled'),
       '15':node('SaveImage',images=['14',0],filename_prefix='fallout1_player_expressive/'+uuid.uuid4().hex+'/x4')}
    d.mkdir(parents=True,exist_ok=True);(d/'prompt.txt').write_text(prompt,encoding='utf-8')
    h.execute(d,g,{'13':'raw-x6.png','15':'candidate-x4.png'})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','control','qwen','qwen-soft']);args=p.parse_args()
    {'prepare':prepare,'control':control,'qwen':qwen,'qwen-soft':lambda:qwen(True)}[args.stage]()
