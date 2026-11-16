"""Compare real SDL frames, including decorations under translucent walls."""
from pipeline import *
before=B/'before';after=B/'after-v2'
a=read(before/'manifest.json');b=read(after/'manifest.json')
assert a['result']['failed']==0 and b['result']['failed']==0
for key in ['collision_hash','collision_hexes_checked','blocked_hexes','path_routes_checked','decoration_placements','decoration_images','loaded_resources']:
 assert a['result'][key]==b['result'][key],key
classics=[p for p in before.glob('*.png') if 'classic' in p.stem]
for p in classics:assert np.array_equal(np.array(Image.open(p)),np.array(Image.open(after/p.name))),p.name
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
def pair(name,filename,box):
 w,ht=box[2]-box[0],box[3]-box[1];canvas=Image.new('RGB',(w*2+24,ht+48),(25,25,25));d=ImageDraw.Draw(canvas)
 for x,label,folder in [(8,'ДО',before),(w+16,'ПОСЛЕ',after)]:
  im=Image.open(folder/filename).convert('RGB');d.text((x,10),label,font=font,fill='white');canvas.paste(im.crop(box),(x,40))
 canvas.save(B/name)
pair('scene-before-after.png','decor-240-tile-19491.png',(640,80,1060,500))
canvas=Image.new('RGB',(904,952),(25,25,25));d=ImageDraw.Draw(canvas)
for row,(i,tile,label) in enumerate([(240,19491,'Кости и череп'),(244,24070,'Койот'),(245,25729,'Брамин'),(241,18092,'Мусор')]):
 filename=f'decor-{i}-tile-{tile}.png';y=row*238
 for x,title,folder in [(8,label+' — до',before),(456,label+' — после',after)]:
  d.text((x,y+4),title,font=font,fill='white')
  # Matching220x100 crops at uniform2x, without color or brightness edits.
  im=Image.open(folder/filename).convert('RGB').crop((850,390,1070,490)).resize((440,200),Image.Resampling.NEAREST)
  canvas.paste(im,(x,y+32))
canvas.save(B/'details-before-after.png')
save(B/'visual-qa.json',dict(classic_frames_exact=len(classics),same_collision_and_paths=True,comparisons=['scene-before-after.png','details-before-after.png'],first_attempt='1118 PASS/1 FAIL: direct-owner-only visibility assertion missed bones visible through translucent wall; corrected diagnostics in isolated test-source only',frames_source_before=str(before),frames_source_after=str(after)))
print('Classic frames identical:',len(classics),'real scene comparisons ready')
