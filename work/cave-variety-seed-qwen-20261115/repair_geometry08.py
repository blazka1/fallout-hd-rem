"""Replace the overly architectural stair-like concept with a natural fractured outcrop."""
import copy,uuid
import pipeline as p
from new_geometry import GEO

d=GEO/'qwen/geo-rock-08-revision'
if not (d/'result.json').exists():
    if (d/'run.json').exists():p.execute(d,{}, {})
    else:
        g=p.read(GEO/'qwen/rocks-01/prompt-api.json')
        g={k:v for k,v in g.items() if int(k)<=15}
        g['1']['inputs'].update(width=512,height=512);g['2']['inputs'].update(width=512,height=512)
        g['11']['inputs']['prompt']='''Create ONE entirely new natural cave outcrop sprite on the empty transparent first image. Second image is only rock material and isometric camera reference. Low, wide, irregular collapsed sedimentary outcrop: four thick fractured slabs tilted in DIFFERENT directions, some sticking out to the left and others projecting toward the viewer, broken jagged ends, unequal heights and lengths, deep diagonal fissures. Chaotic asymmetric geological shape. The uppermost slab is split and partially fallen sideways, two small angular fragments beside the base. No staircase, no evenly descending tiers, no repeated horizontal treads, no masonry, no perfectly rectangular blocks, no architecture. Neutral muted grey-brown cave rock, soft upper-left lighting, clean prerendered 3D material as a 2D orthographic isometric game sprite. Strong broad faces with cracks and chips, not grainy or stippled. Object entirely inside canvas, at least 36 pixels of empty margin around it. RGBA transparency, no ground plane, cast shadow extension, text or border. A visibly irregular natural formation.'''
        g['12']['inputs']['seed']=15116908
        prefix='fallout1_cave_variety/new_geometry_repair/'+uuid.uuid4().hex
        g['14']['inputs']['filename_prefix']=prefix+'/geo-rock-08-natural'
        g['15']['inputs']['filename_prefix']=prefix+'/material-reference'
        d.mkdir(parents=True,exist_ok=True);(d/'prompt.txt').write_text(g['11']['inputs']['prompt'],encoding='utf-8')
        p.execute(d,g,{'14':'raw.png','15':'reference.png'})
    
dst=GEO/'selected/rocks-02'
if not (dst/'result.json').exists():
    n=p.node;prefix='fallout1_cave_variety/new_geometry_selected/'+uuid.uuid4().hex
    g={'1':n('LoadImage',image=p.upload(GEO/'qwen/rocks-02/raw.png')),
       '2':n('JoinImageWithAlpha',image=['1',0],alpha=['1',1]),
       '3':n('LoadImage',image=p.upload(d/'raw.png')),
       '4':n('JoinImageWithAlpha',image=['3',0],alpha=['3',1]),
       '5':n('ImageCompositeMasked',destination=['2',0],source=['4',0],x=512,y=512,resize_source=False),
       '6':n('SaveImage',images=['5',0],filename_prefix=prefix+'/atlas')}
    p.execute(dst,g,{'6':'raw.png'})
    p.save(dst/'selection.json',dict(base='qwen/rocks-02/raw.png',replacement='qwen/geo-rock-08-revision/raw.png',cell=[512,512,512,512],reason='Initial geo-rock-08 looked like constructed stairs; retained as rejected trial.',unchanged_cells=['geo-rock-05','geo-rock-06','geo-rock-07']))
