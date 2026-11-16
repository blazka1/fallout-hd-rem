from pathlib import Path
import importlib.util,json,urllib.request,urllib.parse,sys
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('pipeline',ROOT/'work/hd-menu-seed-qwen/pipeline.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
OUT=ROOT/'assets/generated/main-menu/original-layout-20261114';OUT.mkdir(parents=True,exist_ok=True)
if sys.argv[1]=='submit':
 if (OUT/'run.json').exists():raise RuntimeError('Already submitted')
 m.helpers.idle();name=m.upload(m.OUT/'portrait-seed-qwen-1800x2160.png')
 g=json.loads((m.OUT/'qwen/prompt-api.json').read_text())
 g['1']=m.node('LoadImage',image=name)
 g['2']=m.node('ImageScale',image=['1',0],upscale_method='lanczos',width=720,height=864,crop='disabled')
 g['20']=m.node('EmptyImage',width=1536,height=864,batch_size=1,color=0x9D998F)
 g['21']=m.node('ImageCompositeMasked',destination=['20',0],source=['2',0],x=0,y=0,resize_source=False)
 g['7']['inputs']['images.image_1']=['21',0]
 g['7']['inputs']['images.image_2']=['2',0]
 g['7']['inputs']['prompt']='Extend this Fallout 1 power armor portrait into a complete widescreen background. The left part of image 1 is finished artwork and must stay exactly in place, with the same helmet size, framing and lighting; image 2 is the exact reference for it. Replace the empty grey right region with a seamless continuation of the ruined city already visible behind the helmet: distant broken concrete skyscrapers in muted grey ochre haze, damaged lower buildings and rubble near the bottom, overcast dusty sky above. Continue the cropped shoulder naturally at the lower edge next to the helmet. Keep buildings behind the helmet, same scale, perspective and horizon. Restrained 1997 Fallout prerendered style. Fill the entire canvas naturally to the right edge. No second helmet, extra characters, text, lettering, logo, interface, buttons, frame, vignette, gradient to black or artificial dark panel. Preserve the original illumination and exposure. Do not move or shrink the original portrait.'
 g['11']=m.node('ImageScale',image=['9',0],upscale_method='lanczos',width=3840,height=2160,crop='disabled')
 g['22']=m.node('SolidMask',value=1.0,width=1800,height=2160)
 g['23']=m.node('FeatherMask',mask=['22',0],left=0,top=0,right=96,bottom=0)
 g['24']=m.node('ImageCompositeMasked',destination=['11',0],source=['1',0],x=0,y=0,resize_source=False,mask=['23',0])
 g['10']=m.node('SaveImage',images=['9',0],filename_prefix='fallout1_menu_original_layout/raw')
 g['12']=m.node('SaveImage',images=['24',0],filename_prefix='fallout1_menu_original_layout/background-4k')
 m.save(OUT/'prompt-api.json',g);m.save(OUT/'workflow.json',m.helpers.workflow(g,m.helpers.req('/object_info')))
 m.helpers.idle();r=m.helpers.req('/prompt',dict(prompt=g,client_id='menu-original-layout-20261114'));m.save(OUT/'run.json',r);print(r)
else:
 pid=json.loads((OUT/'run.json').read_text())['prompt_id'];h=m.helpers.req('/history/'+pid)
 if pid not in h:print('RUNNING');sys.exit()
 job=h[pid];m.save(OUT/'history.json',job)
 assert job['status']['status_str']=='success',job['status']
 for nid,name in [('10','expanded-working.png'),('12','background-4k.png')]:
  with urllib.request.urlopen(m.helpers.BASE+'/view?'+urllib.parse.urlencode(job['outputs'][nid]['images'][0])) as r:(OUT/name).write_bytes(r.read())
 print('COMPLETED')
