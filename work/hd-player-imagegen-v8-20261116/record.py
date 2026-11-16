"""Read-only image QA and provenance for the user's exact-reference edit."""
from pathlib import Path
from PIL import Image
import hashlib,json
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'assets/generated/player-male-vault13/imagegen-subtle-tactics-v8-20261116'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
original=Path('C:/Users/Administrator/.codex/generated_images/01a1d091-beef-73c2-a04f-a3abcdbaa573/exec-d9cd0eb5-e48c-44f3-855d-8c8a8cd3b4d7.png')
assert sha(original)==sha(OUT/'character-master.png')
files=[]
for name in ['user-reference.png','character-master.png']:
    path=OUT/name;im=Image.open(path);im.load();hist=im.getchannel('A').histogram()
    assert im.size==(1024,1536) and hist[0]>0 and sum(hist[240:])>0
    files.append(dict(file=name,sha256=sha(path),size=list(im.size),mode=im.mode,
        alpha_extrema=im.getchannel('A').getextrema(),fully_transparent_pixels=hist[0],near_opaque_pixels=sum(hist[240:])))
result=dict(status='subtle exact-reference art candidate for review, not installed',tool='built-in image_gen',model_and_seed='not exposed',
    prompt='prompt.txt',files=files,source_output=str(original),postprocessing='none',runtime_modified=False,
    reference_policy='Only the user attachment was passed to ImageGen; Tactics screenshot was inspected as a visual guide',
    limits=['Generation may change details outside the face; no pixelwise identity claim','Not registered to FRM or tested in animation'])
(OUT/'result.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(files))
