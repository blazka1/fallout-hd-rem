import time
import pipeline as w
import materials,qa,accents
for c in w.p.read(w.OUT/'plan.json')['contexts']:
    while not (w.OUT/'qwen/material'/c['id']/'result.json').exists():time.sleep(5)
    materials.prepare(c['id'])
qa.material()
for theme in accents.THEMES:accents.run(theme)
