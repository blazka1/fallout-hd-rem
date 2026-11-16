from pathlib import Path
import importlib.util,json,uuid,shutil,time,urllib.request,urllib.parse,argparse
ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'assets/generated/inventory-10mm-pistol/qwen21-geometry-reference-v3-20261114'
OUT=ROOT/'assets/generated/inventory-10mm-pistol/qwen21-raw-preview-v4-20261114'
spec=importlib.util.spec_from_file_location('h',ROOT/'work/hd-inventory-pistol/20261113/seed-pistol.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
def save(name,obj):(OUT/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def submit():
 OUT.mkdir(parents=True,exist_ok=True)
 if (OUT/'run.json').exists():raise RuntimeError('Already submitted; collect.')
 h.idle()
 graph=json.loads((SOURCE/'prompt-api.json').read_text())
 graph.pop('13',None)
 token=uuid.uuid4().hex
 graph['11']['inputs']['filename_prefix']='fallout1_pistol_raw_preview/'+token+'/pistol-first-image'
 schemas=h.req('/object_info');wf=h.workflow(graph,schemas);wf['extra']['notes']='Raw Qwen output only, requested by user. Original art plus geometry reference. No inventory crop, alpha cleanup, resizing, F1HD packing or installation.'
 for name in ['source-native.png','source.json','user-geometry-reference.png','prompt.txt']:
  shutil.copy2(SOURCE/name,OUT/name)
 save('prompt-api.json',graph);save('workflow.json',wf)
 save('plan.json',dict(output='One raw generated image',working=[960,960],geometry_reference=[512,288],model=graph['4']['inputs']['unet_name'],seed=graph['9']['inputs']['seed'],steps=25,postprocessing=False,installation=False,backend='Existing ComfyUI restarted with --disable-dynamic-vram --reserve-vram 1',source_run=str(SOURCE.relative_to(ROOT))))
 result=h.req('/prompt',dict(prompt=graph,client_id='pistol-raw-'+token,extra_data={'extra_pnginfo':{'workflow':wf}}));save('run.json',result)
 if result.get('node_errors'):raise RuntimeError(result)
 print(json.dumps(result),flush=True)
def collect():
 pid=json.loads((OUT/'run.json').read_text())['prompt_id'];start=time.monotonic()
 while True:
  hist=h.req('/history/'+pid)
  if pid in hist:break
  if time.monotonic()-start>7200:raise TimeoutError('Resume collection; job not cancelled.')
  print('Waiting for raw Qwen image',flush=True);time.sleep(20)
 job=hist[pid];save('history.json',job)
 if job['status']['status_str']!='success':raise RuntimeError(job['status'])
 rec=job['outputs']['11']['images'][0]
 with urllib.request.urlopen(h.BASE+'/view?'+urllib.parse.urlencode(rec),timeout=30) as response:(OUT/'pistol-first-image.png').write_bytes(response.read())
 save('result.json',dict(status='raw_image_completed',prompt_id=pid,sha256=h.sha(OUT/'pistol-first-image.png'),postprocessed=False,installed=False))
 print(str(OUT/'pistol-first-image.png'),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['submit','collect']);args=p.parse_args();{'submit':submit,'collect':collect}[args.action]()
