"""Corrupt isolated copies; validate graceful fallback and stable other slots."""
import subprocess,os
from pipeline import *
CLONE=BUILD/'fallback-runtime'
def run():
 if not CLONE.exists():
  shutil.copytree(RT,CLONE,ignore=shutil.ignore_patterns('*.exe'))
  shutil.copy2(RT/'fallout-floor-test.exe',CLONE/'fallout-floor-test.exe')
 target=CLONE/'data/art/hd/world-pilot';table=target/'tile-variants.tsv'
 original_table=(PACK/'tile-variants.tsv').read_bytes()
 filename='tile-001-v1.rgba';payload=(PACK/filename).read_bytes();allresults=[]
 before=read(BUILD/'world-final'/'manifest.json');baseline=(BUILD/'world-final'/'tile-variant-assignments.tsv').read_text().splitlines()[1:]
 reference={int(t[0]):(int(t[1]),int(t[2]),int(t[3])) for t in map(str.split,baseline)}
 for name in ['missing-file','invalid-header','wrong-dimensions','invalid-alpha','changed-edge','omitted-slot','unsafe-name','duplicate','missing-table']:
  table.write_bytes(original_table);(target/filename).write_bytes(payload);count=29
  if name=='missing-file':(target/filename).unlink()
  if name=='invalid-header':(target/filename).write_bytes(b'BAD!'+payload[4:])
  if name=='wrong-dimensions':
   b=bytearray(payload);struct.pack_into('<I',b,8,316);(target/filename).write_bytes(b)
  if name=='invalid-alpha':
   b=bytearray(payload);b[20+(72*320+160)*4+3]=254;(target/filename).write_bytes(b)
  if name=='changed-edge':
   b=bytearray(payload);b[20+4*320+1]^=32;(target/filename).write_bytes(b)
  if name=='omitted-slot':table.write_bytes(('\n'.join(line for line in original_table.decode().splitlines() if line!='1\t1\ttile-001-v1.rgba')+'\n').encode())
  if name=='unsafe-name':table.write_bytes(original_table.replace(b'1\t1\ttile-001-v1.rgba',b'1\t1\t../tile-001-v1.rgba'))
  if name=='duplicate':table.write_bytes(original_table+b'1\t1\ttile-001-v1.rgba\n');count=30
  if name=='missing-table':table.unlink();count=0
  out=BUILD/'fallbacks'/name
  if (out/'manifest.json').exists() and read(out/'manifest.json')['result']['failed']:
   out=BUILD/'fallbacks'/(name+'-v2')
  cmd=['pwsh','-NoProfile','-ExecutionPolicy','Bypass','-File',str(R/'work/hd-cave-floor-cutaway-20261115/test.ps1'),'-Mode','smoke','-ExpectedTileVariants',str(count),'-OutputDirectory',str(out.relative_to(R)),'-RuntimeDirectory',str(CLONE.relative_to(R)),'-Executable',str((CLONE/'fallout-floor-test.exe').relative_to(R))]
  if not (out/'manifest.json').exists():
   result=subprocess.run(cmd,capture_output=True,text=True);print(name,result.stdout.strip(),flush=True)
   if result.returncode:raise RuntimeError(result.stderr)
  m=read(out/'manifest.json');assert m['result']['failed']==0
  rows=[line.split() for line in (out/'tile-variant-assignments.tsv').read_text().splitlines()[1:]]
  for t in rows:
   cell,fid,base,slot=map(int,t);oldfid,oldbase,oldslot=reference[cell]
   expected=0 if name=='missing-table' or (name!='duplicate' and base==1 and oldslot==1) else oldslot
   assert (fid,base,slot)==(oldfid,oldbase,expected),(name,cell,slot,expected)
  allresults.append(dict(case=name,compatible_pages=count,all_10000_assignments_preserved_except_missing_slot=True,**m['result']))
 write(BUILD/'fallback-summary.json',dict(cases=allresults,passed=sum(a['passed'] for a in allresults),failed=0,executable_sha256=p.sha(CLONE/'fallout-floor-test.exe')))
 print('Validated nine isolated fallback cases and stable 10000-cell assignments',flush=True)
if __name__=='__main__':run()
