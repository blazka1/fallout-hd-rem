import pipeline as p
panels={x['id']:x for x in p.read(p.OUT/'plan.json')['panels']}
for name in ['wall-01','floor']:
    p.qwen(panels[name],'a',attempt='full',current=True,full=True)
