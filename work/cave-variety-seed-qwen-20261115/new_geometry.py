"""New silhouettes explicitly requested by user; no reuse of original alpha or runtime IDs."""
import sys,uuid
from pathlib import Path
import pipeline as p

GEO=p.OUT/'new-geometry'
GROUPS=[
 ('rocks-01','rocks-a',[
  ('geo-rock-01','A very LOW and WIDE collapsed pile of three large offset flat slabs; stepped silhouette, no central peak.'),
  ('geo-rock-02','One TALL leaning asymmetrical wedge boulder, narrow top leaning left and broad triangular base, a single dominant pointed crest.'),
  ('geo-rock-03','TWO unequal chunky boulders with a deep open V-shaped cleft between them, one short rounded block and one tall angular block.'),
  ('geo-rock-04','One huge squat rounded rectangular limestone mass, strongly undercut on its right side, supported by two small broken feet. Broad solid top, hollow notch underneath.')]),
 ('rocks-02','rocks-b',[
  ('geo-rock-05','A LOW natural limestone bridge: wide irregular horizontal rock spanning two squat feet, a clearly open dark arch HOLE through its middle; not a built doorway.'),
  ('geo-rock-06','A FAN of THREE thin tall stone fins rising from one small base, all leaning right, large V-shaped negative spaces between the blades.'),
  ('geo-rock-07','A very wide half-buried rounded dome boulder split diagonally into two displaced halves. Rounded smooth large silhouette, one major fracture, low center of gravity.'),
  ('geo-rock-08','A long LOW stair-step formation with four thick broken sedimentary ledges descending from left to right, almost horizontal footprint, no vertical spire.')]),
 ('rocks-03','rocks-a',[
  ('geo-rock-09','A HORSESHOE-shaped curved cluster of five irregular rubble blocks with a large open empty center and open front, a recognizable C-shaped footprint.'),
  ('geo-rock-10','One NARROW jagged pinnacle with three unequal sharp crown points rising from a single compact diagonal stone mass, much taller than wide.'),
  ('geo-rock-11','A TOPPLED thick natural rock column lying diagonally on the ground, nearly horizontal body, visible broken polygonal end and a small detached end fragment.'),
  ('geo-rock-12','A huge tilted thin stone sheet leaning over a few small supporting blocks, triangular open negative space under it, asymmetric sail-like silhouette.')]),
 ('formations-01','formations',[
  ('geo-formation-01','A squat dense cluster of FIVE thick unequal eroded stalagmites, tallest at far left, broad shallow base and clearly separate tapered tips; no tall thin central needle.'),
  ('geo-formation-02','A solitary crooked tall stalagmite with a thick bent trunk and a BIFURCATED Y-shaped upper tip, large empty notch between two prongs, small irregular foot.'),
  ('geo-formation-03','A massive cave COLUMN with its upper trunk displaced to the left relative to its broad foot; deeply asymmetric curved waist, narrow roof-contact cap, erosion hollows on one side.'),
  ('geo-formation-04','TWO unequal cave column trunks joined by a rough shared roof-contact rock cap, forming a large irregular open WINDOW between them. Wide forked silhouette with two distinct feet, natural not constructed.')])]

def generate(group):
    name,reference,objects=group;d=GEO/'qwen'/name
    if (d/'result.json').exists():return
    if (d/'run.json').exists():p.execute(d,{},{});return
    prompt='''Create FOUR ENTIRELY NEW cave rock game sprites in a 2 by 2 sprite sheet on the empty first image. The second image is ONLY a reference for the Fallout cave rock MATERIAL, muted grey-brown palette, upper-left lighting and orthographic isometric camera. DO NOT copy any reference silhouette or object geometry. Invent all four shapes from the following descriptions. This is new object design, NOT surface repainting. Each of the four sprites must have a radically distinct recognizable outer silhouette and negative spaces. Keep each object fully inside its own 512 by 512 quadrant with at least 40 pixels of empty margin on all sides; bottom of each object near the lower edge of its cell. No overlap or contact between quadrants. Render actual RGBA TRANSPARENCY around and through the objects. No ground plane, background, base tile, border, labels, letters, numbers, people, vegetation, glow or cast shadow outside the footprint. Clean high-resolution prerendered 3D-looking natural rock as a flat 2D game sprite, continuous shading, broad quiet stone faces, a few strong cracks and chips, readable at game scale. No pixel art, dithering, grain, stippling or painted black outlines. Dark neutral grey limestone, muted warm dust, no blue stone. Material should be secondary to big new forms.\n'''
    for pos,(_,description) in zip(['TOP LEFT','TOP RIGHT','BOTTOM LEFT','BOTTOM RIGHT'],objects):prompt+=pos+': '+description+'\n'
    prompt+='All four designs must be visible in full and physically plausible. Preserve the reference viewing direction and lighting only. The outer shapes and alpha silhouettes must be NEW.'
    prefix='fallout1_cave_variety/new_geometry/'+uuid.uuid4().hex
    node=p.node
    seedpath=p.OUT/'seedvr2-current'/reference/'seedvr2-x4.png'
    g={
     '1':node('EmptyImage',width=1024,height=1024,batch_size=1,color=0),
     '2':node('SolidMask',value=1.0,width=1024,height=1024),
     '3':node('JoinImageWithAlpha',image=['1',0],alpha=['2',0]),
     '4':node('LoadImage',image=p.upload(seedpath)),
     '5':node('JoinImageWithAlpha',image=['4',0],alpha=['4',1]),
     '6':node('ImageScale',image=['5',0],upscale_method='lanczos',width=768 if reference.startswith('rocks') else 512,height=256,crop='disabled'),
     '7':node('UNETLoader',unet_name='qwen_image_2.1_int8_convrot.safetensors',weight_dtype='default'),
     '8':node('CLIPLoader',clip_name='qwen3vl_8b_int8_convrot.safetensors',type='qwen_image',device='default'),
     '9':node('VAELoader',vae_name='qwen_image_2.1_vae_bf16.safetensors'),
     '10':node('QwenImage21Cache',model=['7',0],device='cpu',dtype='default'),
     '11':node('TextEncodeQwenImage21',clip=['8',0],prompt=prompt,negative_prompt='',vae=['9',0],resolution=0,**{'images.image_1':['3',0],'images.image_2':['6',0]}),
     '12':node('KSampler',model=['10',0],positive=['11',0],negative=['11',1],latent_image=['11',2],seed=15116000+[x[0] for x in GROUPS].index(name),steps=25,cfg=1.0,sampler_name='euler',scheduler='simple',denoise=1.0),
     '13':node('VAEDecode',samples=['12',0],vae=['9',0]),
     '14':node('SaveImage',images=['13',0],filename_prefix=prefix+'/new-geometry'),
     '15':node('SaveImage',images=['6',0],filename_prefix=prefix+'/seed-material-reference')}
    outputs={'14':'raw.png','15':'seed-material-reference.png'}
    for i,(identifier,desc) in enumerate(objects):
        n=str(16+i*2);sn=str(17+i*2)
        g[n]=node('ImageCrop',image=['13',0],x=i%2*512,y=i//2*512,width=512,height=512)
        g[sn]=node('SaveImage',images=[n,0],filename_prefix=prefix+'/'+identifier)
        outputs[sn]='sprites/'+identifier+'.png'
    d.mkdir(parents=True,exist_ok=True);(d/'prompt.txt').write_text(prompt,encoding='utf-8')
    p.save(d/'plan.json',dict(status='new geometry candidates, not installed',source_material=str(seedpath.relative_to(p.OUT)),source_sha256=p.sha(seedpath),working_size=[1024,1024],cell_size=[512,512],original_alpha_reused=False,objects=[dict(id=i,description=s) for i,s in objects]))
    p.execute(d,g,outputs)

if __name__=='__main__':
    p.save(GEO/'brief.json',dict(user_request='Кардинально новые спрайты, заметно отличающиеся по геометрии от оригинала',candidate_count=16,rocks=12,formations=4,original_alpha_reused=False,installation=False,geometry_integration='New silhouettes require footprint/pivot/occlusion review; no automatic replacement of source sprites.',groups=[dict(id=n,material_reference=r,objects=[dict(id=i,description=s) for i,s in o]) for n,r,o in GROUPS]))
    for group in GROUPS:
        if len(sys.argv)<2 or group[0]==sys.argv[1]:generate(group)
