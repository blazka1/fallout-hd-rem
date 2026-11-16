"""Lossless alpha roundtrip: avoid one-byte float truncation in Comfy JoinAlpha."""
from pathlib import Path
import importlib.util,json,uuid,time,urllib.parse
s=importlib.util.spec_from_file_location('d',Path(__file__).with_name('detail-v5.py'));d=importlib.util.module_from_spec(s);s.loader.exec_module(d)
h=d.h;BASE=d.BASE;OUT=d.OUT/'exact';OUT.mkdir(exist_ok=True)
if not (OUT/'run.json').exists():
 h.require_idle(BASE);g={};outputs={};prefix='fallout1_terminal_alpha_exact/'+uuid.uuid4().hex
 def add(c,**kw):
  k=str(len(g)+1);g[k]=d.q.n(c,**kw);return [k,0]
 for state in ['off','on']:
  old=add('LoadImage',image=h.upload(BASE,d.OLD/('terminal-'+state+'.png'),'terminal-old-'+uuid.uuid4().hex+'.png'))
  new=add('LoadImage',image=h.upload(BASE,d.OUT/('terminal-'+state+'.png'),'terminal-new-'+uuid.uuid4().hex+'.png'))
  bias=add('SolidMask',value=0.00001,width=128,height=212)
  alpha=add('MaskComposite',destination=[old[0],1],source=bias,x=0,y=0,operation='subtract')
  result=add('JoinImageWithAlpha',image=new,alpha=alpha)
  k=add('SaveImage',images=result,filename_prefix=prefix+'/terminal-'+state);outputs[k[0]]='terminal-'+state+'.png'
 wf=h.make_workflow(g,h.request(BASE,'/object_info'))
 for n,v in [('workflow.json',wf),('prompt-api.json',g),('outputs.json',outputs)]: (OUT/n).write_text(json.dumps(v,indent=2),encoding='utf-8')
 h.require_idle(BASE);run=h.request(BASE,'/prompt',dict(prompt=g,client_id=prefix,extra_data={'extra_pnginfo':{'workflow':wf}}));(OUT/'run.json').write_text(json.dumps(run),encoding='utf-8')
pid=json.loads((OUT/'run.json').read_text())['prompt_id']
while pid not in h.request(BASE,'/history/'+pid):time.sleep(2)
job=h.request(BASE,'/history/'+pid)[pid];(OUT/'history.json').write_text(json.dumps(job,indent=2),encoding='utf-8');assert job['status']['status_str']=='success'
for node,name in json.loads((OUT/'outputs.json').read_text()).items():
 rec=job['outputs'][node]['images'][0];(OUT/name).write_bytes(h.request(BASE,'/view?'+urllib.parse.urlencode(rec)))
print('Exact-alpha candidates collected')
