"""Resume recorded jobs; batch sequentially to avoid needless model swaps."""
import pipeline as p
for record in sorted(p.OUT.glob('**/run.json')):
    if not (record.parent/'result.json').exists():
        p.execute(record.parent,{}, {})
p.run('seed')
p.run('seed-current')
choices=p.read(p.OUT/'qwen-selection.json') if (p.OUT/'qwen-selection.json').exists() else {}
for panel in p.read(p.OUT/'plan.json')['panels']:
    group=choices.setdefault(panel['id'],{})
    for variant in 'abc'[:panel['variants']]:
        if panel['id']=='rocks-a' and variant=='a':
            group[variant]='a'
        else:
            p.qwen(panel,variant,attempt='hd',current=True)
            group[variant]=variant+'-hd'
        p.save(p.OUT/'qwen-selection.json',choices)
for panel in p.read(p.OUT/'plan.json')['panels']:
    p.run('prepare-assets',panel['id'])
    import review
    review.main()
    import context_review
    context_review.floor()
    context_review.walls()
print('Candidate generation and registration complete. Visual QA still required.',flush=True)
