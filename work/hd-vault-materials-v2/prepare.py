"""Registered Comfy crops, clean/original boundary guards and animation consistency."""
from pathlib import Path
import importlib.util,json,uuid,argparse,urllib.parse
s=importlib.util.spec_from_file_location('gen',Path(__file__).with_name('generate.py'));z=importlib.util.module_from_spec(s);s.loader.exec_module(z)
ROOT=z.ROOT;h=z.h;BASE=z.BASE;OLD=z.OLD
def submit(kind):
 out=z.RUN/kind/'prepared';out.mkdir(exist_ok=True)
 if (out/'run.json').exists():raise RuntimeError('Collect existing preparation')
 h.require_idle(BASE);g={};outputs={};specs=[];prefix='fallout1_vault_materials_prepared/'+kind+'-'+uuid.uuid4().hex
 def add(c,**kw):
  k=str(len(g)+1);g[k]=z.q.n(c,**kw);return [k,0]
 def load(p):return add('LoadImage',image=h.upload(BASE,p,'vault-prep-'+uuid.uuid4().hex+'.png'))
 def save(n,v):z.save(out,n,v)
 runtime=json.loads((ROOT/'runtime/hd-world-pilot/data/art/hd/world-pilot/manifest.json').read_text())
 rows={r['asset_id']:r for r in runtime['assets']}
 if kind=='walls':
  size=[1916,1364]
  for a in json.loads((OLD/'tools/walls-spec.json').read_text())['assets']:
   row=next(r for r in rows.values() if r.get('original_resource')==a['source'])
   specs.append(dict(id=row['asset_id'],crop=a['crop'],baseline=str(ROOT/'assets/hd/v13ent/v4-wall-coherent-x4'/(a['source']+'.png')),alpha=row['source_png'],guard=4))
 elif kind=='floor':
  size=[320,144];specs=[dict(id=88,crop=[0,0,*size],baseline=rows[88]['source_png'],alpha=rows[88]['source_png'],guard=4)]
 elif kind=='frame':
  size=[1368,896];specs=[dict(id=16,crop=[0,0,*size],baseline=rows[16]['source_png'],alpha=rows[16]['source_png'],guard=4)]
 else:
  size=[3876,1948]
  for slot in json.loads((OLD/'atlas-input/run.json').read_text())['slots']:
   i=160+slot['frame'];specs.append(dict(id=i,crop=[v*2 for v in slot['atlas_rect']],baseline=rows[i]['source_png'],alpha=rows[i]['source_png'],guard=4))
 raw=load(z.RUN/kind/'raw.png');raw=add('ImageScale',image=raw,upscale_method='lanczos',width=size[0],height=size[1],crop='disabled')
 stationary=None;common=None
 if kind=='door':
  sm=load(OLD/'analysis/masks/v13secr2-static-opaque-allframes.png')
  sm=add('ImageToMask',image=sm,channel='red');sm=add('GrowMask',mask=sm,expand=-1,tapered_corners=False)
  sm=add('MaskToImage',mask=sm);sm=add('ImageScale',image=sm,upscale_method='nearest-exact',width=756,height=628,crop='disabled')
  stationary=add('ImageToMask',image=sm,channel='red')
 for a in specs:
  x,y,w,ht=a['crop'];base=load(Path(a['baseline']));original=load(Path(a['alpha']))
  donor=add('ImageCrop',image=raw,width=w,height=ht,x=x,y=y)
  alpha=add('InvertMask',mask=[original[0],1]);inner=add('GrowMask',mask=alpha,expand=-a['guard'],tapered_corners=False)
  inner=add('FeatherMask',mask=inner,left=4,top=4,right=4,bottom=4)
  rgb=add('ImageCompositeMasked',destination=base,source=donor,x=0,y=0,resize_source=False,mask=inner)
  if stationary:
   if common is None:common=rgb
   else:rgb=add('ImageCompositeMasked',destination=rgb,source=common,x=0,y=0,resize_source=False,mask=stationary)
  rgba=add('JoinImageWithAlpha',image=rgb,alpha=[original[0],1])
  k=add('SaveImage',images=rgba,filename_prefix=prefix+f"/asset-{a['id']:03}");outputs[k[0]]=f"asset-{a['id']:03}.png"
 wf=h.make_workflow(g,h.request(BASE,'/object_info'));save('workflow.json',wf);save('prompt-api.json',g);save('outputs.json',outputs);save('specs.json',specs)
 h.require_idle(BASE);run=h.request(BASE,'/prompt',dict(prompt=g,client_id=prefix,extra_data={'extra_pnginfo':{'workflow':wf}}));save('run.json',run);print(json.dumps(run))
def collect(kind):
 out=z.RUN/kind/'prepared';pid=json.loads((out/'run.json').read_text())['prompt_id'];hist=h.request(BASE,'/history/'+pid)
 if pid not in hist:print('Running '+pid);return
 job=hist[pid];z.save(out,'history.json',job)
 if job['status']['status_str']!='success':raise RuntimeError(job['status'])
 for node,name in json.loads((out/'outputs.json').read_text()).items():
  rec=job['outputs'][node]['images'][0];(out/name).write_bytes(h.request(BASE,'/view?'+urllib.parse.urlencode(rec)))
 print('Collected prepared '+kind)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['submit','collect']);p.add_argument('kind',choices=['walls','frame','door','floor']);a=p.parse_args();{'submit':submit,'collect':collect}[a.action](a.kind)
