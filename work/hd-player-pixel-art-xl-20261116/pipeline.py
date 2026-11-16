"""Pixel Art XL controlled comparison on four original Fallout poses."""
from pathlib import Path
import importlib.util,sys,json,struct,uuid,argparse,shutil
from PIL import Image
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/'assets/generated/player-male-vault13/three-pipelines-guide-v9-20261116'
OUT=ROOT/'assets/generated/player-male-vault13/pixel-art-xl-v10-20261116'
spec=importlib.util.spec_from_file_location('previous_pipeline',ROOT/'work/hd-player-three-pipelines-20261116/pipeline.py')
core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core);core.OUT=OUT
read,save,sha,node=core.read,core.save,core.sha,core.node
MODELS=core.MODELS
def prepare():
    if (OUT/'plan.json').exists():return
    (OUT/'inputs').mkdir(parents=True,exist_ok=True)
    previous=read(OLD/'plan.json')
    for p in previous['poses']:assert sha(ROOT/p['source'])==p['sha256']
    for name in ['original-atlas.png','original-lanczos-x4.png','original-nearest-x4.png']:
        shutil.copy2(OLD/'inputs'/name,OUT/'inputs'/name)
    inputs=[]
    for name,old in [('direct','dream-direct'),('seed','seed-dream')]:
        dst=OUT/'inputs'/(name+'-rgb.png');shutil.copy2(OLD/old/'d22/input-rgb.png',dst)
        assert sha(dst)==sha(OLD/old/'d22/input-rgb.png')
        inputs.append(dict(branch=name,source=str((OLD/old/'d22/input-rgb.png').relative_to(ROOT)),sha256=sha(dst)))
    lora=MODELS/'loras/pixel-art-xl.safetensors'
    with lora.open('rb') as f:
        n=struct.unpack('<Q',f.read(8))[0];header=json.loads(f.read(n))
    save(OUT/'lora-metadata.json',header.get('__metadata__',{}))
    lora_sha=sha(lora);assert lora_sha=='4234637cb80c998f41e348e6a6cb6bc20d8d038b2b0f256b6129b3b5e353eef7'
    ckpt=MODELS/'checkpoints/DreamShaperXL_Turbo_v2.safetensors'
    ckpt_sha=sha(ckpt);assert ckpt_sha=='4726d3bab1876f5c23734c871c47901fde305115e15fbfa3f33354ac45b11c67'
    save(OUT/'models.json',[dict(file=str(p),sha256=s,bytes=p.stat().st_size) for p,s in [(lora,lora_sha),(ckpt,ckpt_sha)]])
    tracked=[ROOT/'AGENTS.md',ROOT/'HD-TEXTURE-GUIDE.md',ROOT/'runtime/hd-world-pilot/fallout-ce.exe']+list((ROOT/'runtime/hd-world-pilot/data/art').rglob('*'))
    save(OUT/'protected-before.json',{str(p.relative_to(ROOT)):sha(p) for p in tracked if p.is_file()})
    save(OUT/'plan.json',dict(status='comparison experiment, not installed',poses=previous['poses'],inputs=inputs,
        branches=['original -> DreamShaper XL v2 Turbo + Pixel Art XL','original -> SeedVR2 -> DreamShaper XL v2 Turbo + Pixel Art XL'],
        working_atlas=[512,768],output_scales=[2,4],lora_strengths=[0,.35,.65],strength_model_equals_strength_clip=True,
        checkpoint='DreamShaperXL_Turbo_v2.safetensors',lora='pixel-art-xl.safetensors',
        sampler_settings=read(OLD/'dream-direct/d22/prompt-api.json')['6']['inputs'],
        seedvr2_source_reused='Verified existing SeedVR2 output from original FRM, same source bytes as V9; not generated again',
        prompts='Exact previous positive/negative, no trigger needed per author; only LoRA strength differs between controls',
        source_reference='https://huggingface.co/nerijs/pixel-art-xl',
        alpha='Original alpha from Lanczos x4 applied after SDXL RGB generation; no manual pixelation, sharpening or recoloring',
        downscale_note='Author nearest /8 pixel-perfect suggestion not applied: user wants only mild raster character at moderate HD',runtime_modified=False))
    print('PREPARED models, original frames and input hashes.',flush=True)

def run():
    if (OUT/'paused.json').exists():
        print('Paused at user request. Do not resume or resubmit until explicitly requested.',flush=True)
        return
    schemas=core.h.req('/object_info')
    assert 'pixel-art-xl.safetensors' in schemas['LoraLoader']['input']['required']['lora_name'][0]
    for branch in ['direct','seed']:
        for strength in [0,.35,.65]:
            name=f'{branch}/lora-{round(strength*100):02}'
            if (OUT/name/'run.json').exists():core.execute(name,{},{});continue
            g=read(OLD/'dream-direct/d22/prompt-api.json')
            g['2']['inputs']['image']=core.upload(OUT/'inputs'/(branch+'-rgb.png'))
            g['9']=node('LoraLoader',model=['1',0],clip=['1',1],lora_name='pixel-art-xl.safetensors',strength_model=strength,strength_clip=strength)
            g['3']['inputs']['clip']=['9',1];g['4']['inputs']['clip']=['9',1];g['6']['inputs']['model']=['9',0]
            g['8']['inputs']['filename_prefix']='fallout1_player_pixelart/'+uuid.uuid4().hex+'/'+branch+f'-lora{strength:.2f}'
            save(OUT/name/'text-prompts.json',dict(positive=g['3']['inputs']['text'],negative=g['4']['inputs']['text']))
            core.execute(name,g,{'8':'raw.png'})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','run']);a=p.parse_args();globals()[a.stage]()
