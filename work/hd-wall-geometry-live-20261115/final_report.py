"""Record measured performance and compare rendered pixels before/after caching."""
from pathlib import Path
import sys
import numpy as np
from PIL import Image
from bake import B, W, read, save

if sys.argv[1]=='pixels':
 rows=[]
 for p in sorted((B/'final-performance').glob('*.png')):
  old=B/'final'/p.name
  if not old.exists():continue
  a=np.asarray(Image.open(old));b=np.asarray(Image.open(p))
  count=int(np.count_nonzero(np.any(a!=b,axis=2))) if a.shape==b.shape else -1
  rows.append(dict(file=p.name,differing_pixels=count))
 result=dict(compared_images=len(rows),identical_images=sum(r['differing_pixels']==0 for r in rows),rows=rows,
  before='final',after='final-performance',scope='Decoded actual SDL captures before and after cache optimization; no image alteration')
 save(B/'cache-image-comparison.json',result)
 print('Compared',len(rows),'captures;',result['identical_images'],'pixel-identical')
 for r in rows:
  if r['differing_pixels']:print(r)
else:
 old=read(B/'benchmark-baseline-repeat/benchmark.json');new=read(B/'benchmark-final/benchmark.json')
 assert old['failed']==new['failed']==0
 rows=[]
 for a,b in zip(old['rows'],new['rows']):
  for key in ['requested_width','requested_height','mode','workload']:assert a[key]==b[key]
  row={k:a[k] for k in ['requested_width','requested_height','mode','workload']}
  row.update(before_median_ms=a['median_ms'],after_median_ms=b['median_ms'],before_p95_ms=a['p95_ms'],after_p95_ms=b['p95_ms'],median_delta_ms=round(b['median_ms']-a['median_ms'],4))
  rows.append(row)
 result=dict(scope=new['scope'],sample_count_per_case=new['sample_count'],before='benchmark-baseline-repeat',after='benchmark-final',passed_before=old['passed'],passed_after=new['passed'],rows=rows,
  caveat='Sequential local measurement, subject to host load; not a gameplay FPS measurement. Original pre-optimization regression remains in benchmark-after for diagnosis.')
 save(B/'performance-comparison.json',result)
 for r in rows:
  if r['mode']=='hd_enabled':print(r['requested_width'],r['workload'],round(r['before_median_ms'],2),'->',round(r['after_median_ms'],2),'ms')
