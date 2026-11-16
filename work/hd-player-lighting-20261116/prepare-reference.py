"""Package unchanged pose references and original shadow metadata; no art edits."""
from pathlib import Path
import hashlib, json, sys
from PIL import Image
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'assets/generated/player-male-vault13/lighting-walk-v2-20261116'
REF = ROOT / 'assets/reference/player-male-vault13'
OLD = ROOT / 'assets/hd/player-male-vault13/v1-x4'
sys.path.insert(0,str(ROOT/'tools/asset-pipeline'))
from fallout_assets import decode_frm

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def bbox(a, t=8):
    y,x=np.where(a>=t)
    return [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]

def main():
    output=RUN/'reference'; output.mkdir(parents=True,exist_ok=True)
    frames={action:decode_frm((REF/f'raw/art/critters/{frm}.frm').read_bytes())[1]
        for action,frm in [('stand','hmjmpsaa'),('walk','hmjmpsab')]}
    records=[]
    for d in range(6):
        hd_sheet=Image.new('RGBA',(1536,1536))
        original_sheet=Image.new('RGBA',(1536,1536))
        for cell in range(9):
            action='stand' if cell==0 else 'walk'; frame=0 if cell==0 else cell-1
            stem=f'stand-d{d}' if cell==0 else f'walk-d{d}-f{frame:03}'
            source=OLD/(stem+'.png')
            hd=Image.open(source).convert('RGBA')
            frm='hmjmpsaa' if cell==0 else 'hmjmpsab'
            orig=Image.open(REF/f'rgba/art/critters/{frm}.frm/d{d}-f{frame:03}.png').convert('RGBA')
            cx=(cell%3)*512;cy=(cell//3)*512
            for sheet,image,scale in [(hd_sheet,hd,1.5),(original_sheet,orig,6)]:
                expanded=image.resize((round(image.width*scale),round(image.height*scale)),Image.Resampling.NEAREST)
                sheet.alpha_composite(expanded,(cx+(512-expanded.width)//2,cy+448-expanded.height))
            f=frames[action][d][frame]
            indices=np.frombuffer(f.pixels,dtype=np.uint8).reshape(f.height,f.width)
            # Idle uses207; walking uses a dark31/47/100 dither for the same
            # ground shape. Decode the whole dither before HD edge smoothing.
            # Restrict to the lower28% to exclude hair and upper-body shadows.
            shadow_indices=[207] if cell==0 else [31,47,100]
            shadow=(np.isin(indices,shadow_indices)&(np.arange(f.height)[:,None]>=int(f.height*.72))).astype(np.uint8)
            (output/(stem+'.shadow-mask')).write_bytes(shadow.tobytes())
            records.append({'direction':d,'animation':0 if action=='stand' else 1,'frame':-1 if cell==0 else frame,
                'cell':cell,'stem':stem,'native_dimensions':[f.width,f.height],
                'hd_source':str(source),'hd_sha256':sha(source),'target_bbox_x4':bbox(np.asarray(hd)[:,:,3]),
                'shadow_pixels':int(shadow.sum()),'shadow_palette_indices':shadow_indices,'shadow_mask':stem+'.shadow-mask',
                'source_shift':[f.shift_x,f.shift_y]})
        hd_sheet.save(output/f'd{d}-current-poses.png')
        original_sheet.save(output/f'd{d}-original-poses.png')
    (output/'manifest.json').write_text(json.dumps({'layout':'3x3: idle, walk0,walk1 / walk2,walk3,walk4 / walk5,walk6,walk7',
        'frame_order':'row-major, 9 figures per direction','entries':records},indent=2),encoding='utf-8')
    print('Prepared 6 paired pose atlases and 54 native shadow masks')
if __name__=='__main__':main()
