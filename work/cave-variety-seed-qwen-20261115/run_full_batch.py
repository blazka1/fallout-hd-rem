"""Reviewed full-size material series; preserves all small-resolution trials."""
import pipeline as p
choices=p.read(p.OUT/'qwen-selection.json') if (p.OUT/'qwen-selection.json').exists() else {}
for panel in p.read(p.OUT/'plan.json')['panels']:
    group=choices.setdefault(panel['id'],{})
    for v in 'abc'[:panel['variants']]:
        if panel['id']=='rocks-a' and v=='a':group[v]='a'
        else:
            p.qwen(panel,v,attempt='full',current=True,full=True)
            group[v]=v+'-full'
        p.save(p.OUT/'qwen-selection.json',choices)
for panel in p.read(p.OUT/'plan.json')['panels']:
    p.run('prepare-assets',panel['id'])
import review,context_review
review.main()
context_review.floor();context_review.walls()
review.main()
print('Full-size candidates generated, registered and checked. Manual visual review remains.',flush=True)
