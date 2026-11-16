"""Serial, resumable local candidates only; never installs or clears shared jobs."""
from pathlib import Path
import importlib.util,json,time
HERE=Path(__file__).parent
def module(name):
 s=importlib.util.spec_from_file_location(name,HERE/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
gen=module('generate');prep=module('prepare')
for kind in ['walls','frame','door','floor']:
 for m,out in [(gen,gen.RUN/kind),(prep,gen.RUN/kind/'prepared')]:
  if not (out/'run.json').exists():
   while True:
    q=gen.h.request(gen.BASE,'/queue')
    if not q['queue_running'] and not q['queue_pending']:break
    time.sleep(10)
   m.submit(kind);print('SUBMITTED',kind,out.name,flush=True)
  pid=json.loads((out/'run.json').read_text())['prompt_id']
  while pid not in gen.h.request(gen.BASE,'/history/'+pid):time.sleep(10)
  m.collect(kind);print('READY',kind,out.name,flush=True)
print('ALL CANDIDATES READY, NOT INSTALLED',flush=True)
