"""Prepare completed rat panels while the resumable Qwen batch continues."""
import importlib.util,time
from pathlib import Path
s=importlib.util.spec_from_file_location('rat_pipeline',Path(__file__).with_name('pipeline.py'))
p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
plans=p.read(p.OUT/'panels.json')
while True:
    pending=[v for v in plans if not (p.OUT/p.PREPARED_NAME/v['id']/'result.json').exists()]
    if not pending:break
    ready=[v for v in pending if (p.OUT/'qwen'/v['id']/'result.json').exists()]
    if ready:
        for panel in ready:p.prepare(panel)
    else:time.sleep(10)
print('ALL 376 UNIQUE FRAMES PREPARED',flush=True)
