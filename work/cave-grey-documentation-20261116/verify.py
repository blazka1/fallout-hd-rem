from pathlib import Path
import hashlib,json,struct,shutil
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[2];W=Path(__file__).parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def decode(p):
 data=p.read_bytes();magic,version,w,h,c=struct.unpack('<4sIIII',data[:20]);assert (magic,version,c)==(b'F1HD',1,4)
 return np.frombuffer(data[20:],np.uint8).reshape(h,w,4)
def main():
 receipt=read(R/'build/hd-wall-grey-match-20261116/integration.json')
 live=R/'runtime/hd-world-pilot';data=live/'data/art/hd/world-pilot';pkg=R/'assets/hd/v13ent/original-seed-qwen-grey-v2'
 manifest=read(data/'manifest.json');assert manifest['wall_geometry']['component']==receipt['component']=='original-seed-qwen-grey-v2'
 baseline=read(R/'work/hd-wall-grey-match-20261116/baseline.json');backup=R/receipt['backup'];state=read(backup/'state.json')
 assert state['status']=='installed' and len(state['files'])==538
 rows=receipt['images'];assert len(rows)==537
 for row in rows:
  file=row['file'];current=data/file;assert sha(current)==row['sha256'],file
  pixels=decode(current);png=pkg/Path(row['png']).name
  assert np.array_equal(pixels,np.array(Image.open(png).convert('RGBA'))),file
  before=decode(backup/file);assert pixels.shape==before.shape and np.array_equal(pixels[:,:,3],before[:,:,3]),file
  assert np.max(np.ptp(pixels[:,:,:3].astype(int),axis=2))==0,file
 for item in state['files']:assert sha(backup/item['name'])==item['before_sha256']
 assert sha(live/'fallout-ce.exe')==receipt['installed_exe_sha256']==baseline['exe_sha256']
 assert sha(R/'build/hd-world-pilot/msvc/RelWithDebInfo/fallout-ce.exe')==sha(live/'fallout-ce.exe')
 targets={'data/art/hd/world-pilot/'+x['file'] for x in rows}|{'data/art/hd/world-pilot/manifest.json'}
 unchanged_art=[];registries=[]
 for rel,hsh in baseline['files'].items():
  if rel.startswith('data/art/') and rel not in targets:
   assert sha(live/rel)==hsh,rel;unchanged_art.append(rel)
   if rel.endswith('.tsv'):registries.append(rel)
 checked=read(R/'build/hd-wall-grey-match-20261116/after-v1/manifest.json');assert checked['result']['passed']==1119 and checked['result']['failed']==0
 captures=R/'build/hd-wall-grey-match-20261116/after-v1'
 for c in checked['captures']:assert sha(captures/c['file'])==c['sha256'].lower()
 test=R/'build/hd-wall-original-restore-20261116/test-msvc/RelWithDebInfo/fallout-ce.exe';assert sha(test)==checked['executable_sha256'].lower()
 comparison=read(R/'build/hd-wall-grey-match-20261116/comparison.json');assert comparison['classic_all_exact'] and len(comparison['classic_frames'])==18
 for c in comparison['classic_frames']:
  assert np.array_equal(np.array(Image.open(captures/c['file'])),np.array(Image.open(R/comparison['before']/c['file'])))
 for ref in read(R/'assets/generated/v13ent-wall-original/grey-match-20261116/reference-measurements.json'):assert sha(data/ref['file'])==ref['sha256']
 provenance=read(R/'assets/generated/v13ent-wall-original/seed-qwen-20261116/provenance.json')
 for path,hsh in provenance['blender_package'].items():assert sha(R/path)==hsh
 archive=R/'build/backups/before-cave-grey-doc-20261116';archive.mkdir(parents=True,exist_ok=True)
 if (archive/'AGENTS.md').exists():assert sha(archive/'AGENTS.md')==sha(R/'AGENTS.md')
 else:shutil.copy2(R/'AGENTS.md',archive/'AGENTS.md')
 result=dict(status='verified',date='2026-11-16',component=receipt['component'],runtime_images=537,png_decode_exact=537,alpha_exact_previous=537,neutral_grey_images=537,backup_files_verified=538,unchanged_other_art_files=len(unchanged_art),unchanged_registries=registries,stock_exe_sha256=sha(live/'fallout-ce.exe'),test_only_exe_sha256=sha(test),recorded_checks=checked['result'],capture_hashes_verified=len(checked['captures']),classic_frames_exact=18,blender_archive_files_verified=len(provenance['blender_package']),runtime_manifest_sha256=sha(data/'manifest.json'),agents_before_sha256=sha(R/'AGENTS.md'),agents_backup=str((archive/'AGENTS.md').relative_to(R)),new_game_tests_run=False)
 (W/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:v for k,v in result.items() if k not in ['unchanged_registries','recorded_checks']},ensure_ascii=False))
if __name__=='__main__':main()
