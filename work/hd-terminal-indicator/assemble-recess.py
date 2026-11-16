"""Composite only the repaired recess into the frame through ComfyUI nodes."""
from pathlib import Path
import importlib.util,json,uuid,argparse,urllib.parse
spec=importlib.util.spec_from_file_location('recess',Path(__file__).with_name('prepare-recess.py'))
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
h=r.h;BASE=r.BASE;OUT=r.OUT/'prepared'
def save(n,v):(OUT/n).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def submit():
    OUT.mkdir(exist_ok=True)
    if (OUT/'run.json').exists():raise RuntimeError('Collect saved run')
    h.require_idle(BASE)
    inputs={k:h.upload(BASE,p,'recess-mask-'+uuid.uuid4().hex+'.png') for k,p in [('frame',r.FRAME),('repair',r.OUT/'recess-raw.png')]}
    g={}
    def add(kind,**kw):
        k=str(len(g)+1);g[k]=r.q.n(kind,**kw);return [k,0]
    frame=add('LoadImage',image=inputs['frame']);raw=add('LoadImage',image=inputs['repair'])
    raw=add('ImageScale',image=raw,upscale_method='lanczos',width=352,height=448,crop='disabled')
    patch=add('SolidMask',value=1.0,width=160,height=244)
    patch=add('FeatherMask',mask=patch,left=8,top=8,right=8,bottom=8)
    mask=add('SolidMask',value=0.0,width=352,height=448)
    mask=add('MaskComposite',destination=mask,source=patch,x=84,y=160,operation='add')
    rgb=add('ImageCompositeMasked',destination=frame,source=raw,x=192,y=448,resize_source=False,mask=mask)
    alpha=add('InvertMask',mask=[frame[0],1])
    fill=add('SolidMask',value=1.0,width=132,height=212)
    alpha=add('MaskComposite',destination=alpha,source=fill,x=292,y=628,operation='add')
    inv=add('InvertMask',mask=alpha);rgba=add('JoinImageWithAlpha',image=rgb,alpha=inv)
    prefix='fallout1_terminal_recess_prepared/'+uuid.uuid4().hex;outputs={}
    for image,name in [(rgba,'vault-frame'),(raw,'repair-registered')]:
        k=add('SaveImage',images=image,filename_prefix=prefix+'/'+name);outputs[k[0]]=name+'.png'
    wf=h.make_workflow(g,h.request(BASE,'/object_info'))
    save('workflow.json',wf);save('prompt-api.json',g);save('outputs.json',outputs)
    save('plan.json',dict(source=str(r.FRAME),source_sha256=h.sha_file(r.FRAME),repair_sha256=h.sha_file(r.OUT/'recess-raw.png'),rgb_patch=[276,608,160,244],feather=8,alpha_addition=[292,628,132,212],original_canvas=[1368,896],native_recess=[73,157,33,53],diffusion=False))
    h.require_idle(BASE);run=h.request(BASE,'/prompt',dict(prompt=g,client_id=prefix,extra_data={'extra_pnginfo':{'workflow':wf}}));save('run.json',run);print(json.dumps(run))
def collect():
    pid=json.loads((OUT/'run.json').read_text())['prompt_id'];hist=h.request(BASE,'/history/'+pid)
    if pid not in hist:print('Running '+pid);return
    job=hist[pid];save('history.json',job)
    if job['status']['status_str']!='success':raise RuntimeError(job['status'])
    for node,name in json.loads((OUT/'outputs.json').read_text()).items():
        rec=job['outputs'][node]['images'][0];(OUT/name).write_bytes(h.request(BASE,'/view?'+urllib.parse.urlencode(rec)))
    print('Collected prepared recess')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['submit','collect']);a=p.parse_args();{'submit':submit,'collect':collect}[a.action]()
