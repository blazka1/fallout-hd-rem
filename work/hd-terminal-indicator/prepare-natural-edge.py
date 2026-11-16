"""Comfy matte correction of the approved Qwen terminal; lamp pixels protected."""
from pathlib import Path
import importlib.util,json,uuid,urllib.parse,argparse
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('gen',Path(__file__).with_name('qwen-terminal.py'))
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
OUT=ROOT/'assets/generated/v13ent-terminal/natural-edge-v3-20261114'
OLD=ROOT/'assets/hd/v13ent/terminal-indicator-v1'
def save(name,v):(OUT/name).write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def submit():
 OUT.mkdir(parents=True,exist_ok=True)
 if (OUT/'run.json').exists():raise RuntimeError('Use collect')
 h.h.require_idle(h.BASE)
 uploaded={name:h.h.upload(h.BASE,p,'terminal-edge-'+uuid.uuid4().hex+'.png') for name,p in [('original',h.OUT/'source.png'),('on',OLD/'terminal-on.png'),('off',OLD/'terminal-off.png')]}
 g={}
 def add(kind,**kw):
  k=str(len(g)+1);g[k]=h.n(kind,**kw);return [k,0]
 original=add('LoadImage',image=uploaded['original']);opacity=add('InvertMask',mask=[original[0],1])
 inner5=add('GrowMask',mask=opacity,expand=-5,tapered_corners=True)
 ring=add('MaskComposite',destination=opacity,source=inner5,x=0,y=0,operation='subtract')
 inner2=add('GrowMask',mask=opacity,expand=-2,tapered_corners=True)
 inner3=add('GrowMask',mask=opacity,expand=-3,tapered_corners=True)
 half=add('SolidMask',value=0.5,width=128,height=212)
 a=add('MaskComposite',destination=inner2,source=half,x=0,y=0,operation='multiply')
 b=add('MaskComposite',destination=inner3,source=half,x=0,y=0,operation='multiply')
 edge=add('MaskComposite',destination=a,source=b,x=0,y=0,operation='add')
 # Keep the original narrow cable along the very top instead of eroding it away.
 top=add('SolidMask',value=1.0,width=128,height=22)
 empty=add('SolidMask',value=0.0,width=128,height=212)
 top=add('MaskComposite',destination=empty,source=top,x=0,y=0,operation='add')
 top=add('MaskComposite',destination=top,source=opacity,x=0,y=0,operation='multiply')
 # Maximum of the two masks via subtract/add (masks clamp to [0,1]).
 difference=add('MaskComposite',destination=top,source=edge,x=0,y=0,operation='subtract')
 edge=add('MaskComposite',destination=edge,source=difference,x=0,y=0,operation='add')
 alpha=add('InvertMask',mask=edge)
 outputs={};prefix='fallout1_terminal_natural_edge/'+uuid.uuid4().hex
 for state in ['off','on']:
  old=add('LoadImage',image=uploaded[state])
  rgb=add('ImageCompositeMasked',destination=old,source=original,x=0,y=0,resize_source=False,mask=ring)
  rgba=add('JoinImageWithAlpha',image=rgb,alpha=alpha)
  node=add('SaveImage',images=rgba,filename_prefix=prefix+'/terminal-'+state);outputs[node[0]]='terminal-'+state+'.png'
 for name,mask in [('opacity',edge),('restored-edge-rgb-mask',ring)]:
  image=add('MaskToImage',mask=mask);node=add('SaveImage',images=image,filename_prefix=prefix+'/'+name);outputs[node[0]]=name+'.png'
 wf=h.h.make_workflow(g,h.h.request(h.BASE,'/object_info'))
 save('prompt-api.json',g);save('workflow.json',wf);save('outputs.json',outputs)
 save('plan.json',dict(method='Restore original edge RGB, remove artificial dark band, trim 2 HD pixels and antialias the next pixel over actual background. Preserve top cable and lamp exactly.',original=str(h.OUT/'source.png'),approved=str(OLD),no_new_diffusion=True))
 h.h.require_idle(h.BASE);run=h.h.request(h.BASE,'/prompt',dict(prompt=g,client_id=prefix,extra_data={'extra_pnginfo':{'workflow':wf}}));save('run.json',run);print(json.dumps(run))
def collect():
 pid=json.loads((OUT/'run.json').read_text())['prompt_id'];hist=h.h.request(h.BASE,'/history/'+pid)
 if pid not in hist:print('Running '+pid);return
 job=hist[pid];save('history.json',job)
 if job['status']['status_str']!='success':raise RuntimeError(job['status'])
 for n,name in json.loads((OUT/'outputs.json').read_text()).items():
  rec=job['outputs'][n]['images'][0];(OUT/name).write_bytes(h.h.request(h.BASE,'/view?'+urllib.parse.urlencode(rec)))
 print('Collected natural edge')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['submit','collect']);a=p.parse_args();{'submit':submit,'collect':collect}[a.action]()
