"""Record unmodified native ImageGen outputs; no image processing."""
from pathlib import Path
from PIL import Image
import hashlib,json
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'assets/generated/player-male-vault13/imagegen-ordinary-simplified-v7-20261116'
GEN=Path('C:/Users/Administrator/.codex/generated_images/01a1d091-beef-73c2-a04f-a3abcdbaa573')
pairs={'character-master.png':'exec-f6dd9a1a-bcbe-4617-92ad-b12af2c41939.png','fabric-master.png':'exec-da4ed6f8-858f-495a-8e29-39f1386d725e.png'}
files=[]
for name,original in pairs.items():
    path=OUT/name;digest=hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest==hashlib.sha256((GEN/original).read_bytes()).hexdigest()
    im=Image.open(path);im.load()
    entry=dict(file=name,source=str(GEN/original),sha256=digest,size=list(im.size),mode=im.mode,unchanged_from_native_imagegen=True)
    if 'A' in im.getbands():
        hist=im.getchannel('A').histogram();entry.update(alpha_extrema=im.getchannel('A').getextrema(),fully_transparent_pixels=hist[0],near_opaque_pixels=sum(hist[240:]))
        assert hist[0]>0 and sum(hist[240:])>0
    files.append(entry)
result=dict(status='revised art-direction candidate for review, not installed',tool='built-in image_gen',model_and_seed='not exposed',files=files,
    prompt_set='prompts.json',runtime_modified=False,postprocessing='none',supersedes_for_review='../imagegen-pixel-dirty-v6-20261116')
(OUT/'result.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(files,ensure_ascii=False))
