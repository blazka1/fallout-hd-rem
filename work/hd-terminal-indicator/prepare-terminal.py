"""Deterministic Comfy preparation: local Qwen lamp, original body and alpha."""
from pathlib import Path
import importlib.util, json, uuid, argparse, urllib.parse
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('gen',Path(__file__).with_name('qwen-terminal.py'))
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
OUT=h.OUT/'prepared'
def save(name,value):(OUT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def submit():
 OUT.mkdir(exist_ok=True)
 if (OUT/'run.json').exists():raise RuntimeError('Use collect')
 h.h.require_idle(h.BASE)
 old=h.h.upload(h.BASE,h.OUT/'source.png','terminal-base-'+uuid.uuid4().hex+'.png')
 raw=h.h.upload(h.BASE,h.OUT/'terminal-raw.png','terminal-qwen-'+uuid.uuid4().hex+'.png')
 graph={}
 def add(kind,**kw):
  key=str(len(graph)+1);graph[key]=h.n(kind,**kw);return [key,0]
 base=add('LoadImage',image=old)
 alpha=[base[0],1]
 opacity=add('InvertMask',mask=alpha)
 inner=add('GrowMask',mask=opacity,expand=-3,tapered_corners=True)
 rim=add('MaskComposite',destination=opacity,source=inner,x=0,y=0,operation='subtract')
 darker=add('AdjustBrightness',images=base,factor=0.28)
 clean=add('ImageCompositeMasked',destination=base,source=darker,x=0,y=0,resize_source=False,mask=rim)
 inner2=add('GrowMask',mask=opacity,expand=-5,tapered_corners=True)
 band=add('MaskComposite',destination=inner,source=inner2,x=0,y=0,operation='subtract')
 medium=add('AdjustBrightness',images=base,factor=0.65)
 clean=add('ImageCompositeMasked',destination=clean,source=medium,x=0,y=0,resize_source=False,mask=band)
 q=add('LoadImage',image=raw)
 q=add('ImageScale',image=q,upscale_method='lanczos',width=128,height=212,crop='disabled')
 empty=add('SolidMask',value=0.0,width=128,height=212)
 patch=add('SolidMask',value=1.0,width=18,height=20)
 patch=add('FeatherMask',mask=patch,left=2,top=2,right=2,bottom=2)
 patch=add('MaskComposite',destination=empty,source=patch,x=92,y=53,operation='add')
 lit=add('ImageCompositeMasked',destination=clean,source=q,x=0,y=0,resize_source=False,mask=patch)
 green=add('ImageToMask',image=q,channel='green')
 red=add('ImageToMask',image=q,channel='red')
 lens=add('MaskComposite',destination=green,source=red,x=0,y=0,operation='subtract')
 lens=add('ThresholdMask',mask=lens,value=0.12)
 lens=add('GrowMask',mask=lens,expand=1,tapered_corners=True)
 lens=add('MaskComposite',destination=lens,source=patch,x=0,y=0,operation='multiply')
 dim=add('AdjustBrightness',images=lit,factor=0.13)
 unlit=add('ImageCompositeMasked',destination=lit,source=dim,x=0,y=0,resize_source=False,mask=lens)
 on=add('JoinImageWithAlpha',image=lit,alpha=alpha)
 off=add('JoinImageWithAlpha',image=unlit,alpha=alpha)
 prefix='fallout1_terminal_prepared/'+uuid.uuid4().hex
 nodes={}
 for name,img in [('terminal-on',on),('terminal-off',off),('lamp-mask',add('MaskToImage',mask=lens)),('rim-mask',add('MaskToImage',mask=rim))]:
  node=add('SaveImage',images=img,filename_prefix=prefix+'/'+name);nodes[node[0]]=name+'.png'
 workflow=h.h.make_workflow(graph,h.h.request(h.BASE,'/object_info'))
 save('workflow.json',workflow);save('prompt-api.json',graph);save('outputs.json',nodes)
 save('plan.json',dict(operation='Qwen local lamp patch; Comfy neutral edge cleanup; exact original alpha; off state from shared base',patch=[92,53,18,20],source_sha256=h.h.sha_file(h.OUT/'source.png'),qwen_sha256=h.h.sha_file(h.OUT/'terminal-raw.png')))
 h.h.require_idle(h.BASE)
 run=h.h.request(h.BASE,'/prompt',dict(prompt=graph,client_id=prefix,extra_data={'extra_pnginfo':{'workflow':workflow}}));save('run.json',run);print(json.dumps(run))
def collect():
 pid=json.loads((OUT/'run.json').read_text())['prompt_id'];hist=h.h.request(h.BASE,'/history/'+pid)
 if pid not in hist:print('Running '+pid);return
 job=hist[pid];save('history.json',job)
 if job['status']['status_str']!='success':raise RuntimeError(job['status'])
 for node,name in json.loads((OUT/'outputs.json').read_text()).items():
  rec=job['outputs'][node]['images'][0];(OUT/name).write_bytes(h.h.request(h.BASE,'/view?'+urllib.parse.urlencode(rec)))
 print('Prepared '+str(OUT))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['submit','collect']);a=p.parse_args();{'submit':submit,'collect':collect}[a.action]()
