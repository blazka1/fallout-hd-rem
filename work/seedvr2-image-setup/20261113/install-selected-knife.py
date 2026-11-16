"""Package the approved knife and install a reversible inventory FRM override."""
from pathlib import Path
import argparse,hashlib,json,sys,struct,shutil,datetime
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/asset-pipeline'))
from fallout_assets import Assets,palette_rgb,decode_frm
SRC=ROOT/'assets/generated/inventory-knife/qwen21-handle-fill-v6-20261113'
OUT=ROOT/'assets/hd/inventory/knife/v1'
RUNTIME=ROOT/'runtime/hd-world-pilot'
REPORT=ROOT/'build/hd-inventory-knife/selected-v1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def js(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def put(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.read_bytes()!=data:raise RuntimeError('Different existing artifact: '+str(path))
    path.write_bytes(data)
def prepare():
    OUT.mkdir(parents=True,exist_ok=True);REPORT.mkdir(parents=True,exist_ok=True)
    assert sha(SRC/'knife-handle-x4.png')=='aadca7c5909955ac922251a3690a2ba8abcf35daa442dbb4e4ce1125293a3c42'
    for name,source in [('knife-hd-x4.png','knife-handle-x4.png'),('knife-master.png','knife-handle-raw.png'),('workflow.json','workflow.json'),('prompt-api.json','prompt-api.json'),('prompt.txt','prompt.txt'),('source.json','source.json'),('generation-result.json','result.json')]:put(OUT/name,(SRC/source).read_bytes())
    archives=Assets([ROOT/'FALLOUT (extract.me)/MASTER.DAT']);raw=archives.read('art/inven/oknife.frm');pal=palette_rgb(archives.read('color.pal'))
    assert len(raw)==2978 and struct.unpack_from('>HH',raw,62)==(88,33)
    resized=Image.open(OUT/'knife-hd-x4.png').convert('RGBA').resize((88,33),Image.Resampling.LANCZOS)
    pixels=np.array(resized);colors=np.frombuffer(pal,dtype=np.uint8).reshape(256,3)[1:229].astype(np.int32)
    rgb=pixels[:,:,:3].reshape(-1,3).astype(np.int32)
    distance=((rgb[:,None,:]-colors[None,:,:])**2*np.array([2,4,1])).sum(axis=2)
    indices=(distance.argmin(axis=1)+1).astype(np.uint8).reshape(33,88)
    indices[pixels[:,:,3]<128]=0
    # Keep all original registration, FPS and frame fields. Only indexed pixels change.
    frm=raw[:74]+indices.tobytes();put(OUT/'oknife.frm',frm)
    # Decode through strict v4 layout in memory: original v3 uses identical fields.
    meta,dirs=decode_frm(struct.pack('>I',4)+frm[4:]);assert dirs[0][0].pixels==indices.tobytes()
    assert frm[:74]==raw[:74] and set(np.unique(indices)).issubset(set(range(229)))
    converted=Image.fromarray(indices).convert('P');converted.putpalette(pal);converted.info['transparency']=0
    converted.save(OUT/'knife-runtime-native.png',transparency=0)
    preview=Image.new('RGB',(800,220),(34,38,38));d=ImageDraw.Draw(preview);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17)
    for i,(im,label) in enumerate([(Image.open(OUT/'knife-hd-x4.png').convert('RGBA'),'Утверждённый HD-мастер'),(converted.convert('RGBA').resize((352,132),Image.Resampling.NEAREST),'Версия классического инвентаря ×4')]):
        d.text((i*400+14,14),label,font=font,fill='white');preview.paste(im,(i*400+24,60),im)
    preview.save(REPORT/'compatibility-preview.png')
    manifest=dict(status='user_approved_selected_asset',source_generation=str(SRC.relative_to(ROOT)),original_art='art/inven/oknife.frm',pid=4,inventory_fid=117440608,native_size=[88,33],hd_size=[352,132],master_size=[1152,576],runtime_file='data/art/inven/oknife.frm',render_mode='Classic inventory FRM override; HD source archived, no HD inventory renderer implemented',conversion='Lanczos 352x132 to 88x33; alpha threshold 128; nearest static Fallout palette entries 1..228; no dithering',source_frm_sha256=hashlib.sha256(raw).hexdigest(),files={p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name!='manifest.json'})
    js(OUT/'manifest.json',manifest);print(json.dumps(manifest,ensure_ascii=True),flush=True)
def install():
    assert (OUT/'manifest.json').exists()
    cfg=(RUNTIME/'fallout.cfg').read_text();assert 'master_patches=data' in cfg and 'critter_patches=data' in cfg
    exe=RUNTIME/'fallout-ce.exe';before=sha(exe)
    receipt=REPORT/'installation.json'
    if receipt.exists():
        old=json.loads(receipt.read_text());assert sha(RUNTIME/'data/art/inven/oknife.frm')==old['runtime_frm_sha256'];print('Already installed and verified.');return
    target=RUNTIME/'data/art/inven/oknife.frm';backup=None
    if target.exists():
        backup=REPORT/'before-install/oknife.frm';put(backup,target.read_bytes())
    target.parent.mkdir(parents=True,exist_ok=True)
    staged=target.with_suffix('.frm.new');staged.write_bytes((OUT/'oknife.frm').read_bytes());staged.replace(target)
    runtime_hd=RUNTIME/'data/art/hd/inventory/knife'
    for name in ['knife-hd-x4.png','knife-master.png','manifest.json']:put(runtime_hd/name,(OUT/name).read_bytes())
    assert sha(target)==sha(OUT/'oknife.frm') and sha(exe)==before
    js(receipt,dict(status='installed',runtime=str(RUNTIME.relative_to(ROOT)),launcher='Start-Fallout-HD-World-Pilot.cmd',installed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),runtime_frm=str(target.relative_to(ROOT)),runtime_frm_sha256=sha(target),hd_master_sha256=sha(runtime_hd/'knife-master.png'),executable_sha256=before,executable_changed=False,previous_override=str(backup.relative_to(ROOT)) if backup else None,rollback='Restore recorded previous override if present; otherwise remove only runtime/hd-world-pilot/data/art/inven/oknife.frm. Original DAT supplies classic icon.',validation='Header, dimensions, frame data roundtrip, palette index range, runtime copy hashes and patch-directory configuration verified; visual review of conversion. No live inventory screenshot yet.'))
    print('Installed selected knife into '+str(target),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','install']);a=p.parse_args();{'prepare':prepare,'install':install}[a.action]()
