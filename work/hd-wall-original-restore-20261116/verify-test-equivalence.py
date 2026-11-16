from pipeline import *
stock=B/'after-v1';validated=B/'native-check';a=read(stock/'manifest.json');b=read(validated/'manifest.json')
assert b['result']['passed']==1119 and b['result']['failed']==0
failures=[line for line in (stock/'checks.txt').read_text().splitlines() if line.startswith('FAIL')]
assert len(failures)==40 and all(s.startswith('FAIL registered geometry appears in SDL ') for s in failures)
rows=[];sampled=[]
for f in sorted(stock.glob('*.png')):
 if f.name.startswith(('wall-geometry-','new-form-')):
  sampled.append(f.name);continue
 g=validated/f.name;assert g.exists();exact=np.array_equal(np.array(Image.open(f)),np.array(Image.open(g)))
 rows.append(dict(file=f.name,exact=exact))
result=dict(frames=len(rows),all_exact=all(x['exact'] for x in rows),captures=rows,sampled_views_not_paired=sampled,sampled_view_reason='Diagnostic views selected by iteration over std::set<Object*>; different process addresses choose different representative objects/camera positions. These 38 views retain their independent in-engine assertions, not a cross-process pixel-equality requirement.',total_captures_each=155,legacy_passed=a['result']['passed'],legacy_failed=a['result']['failed'],legacy_failures=failures,updated_test_passed=b['result']['passed'],updated_test_failed=b['result']['failed'],test_only_source=read(B/'test-only-source-change.json'),installed_exe_restored=sha(W/'runtime/fallout-ce.exe')==sha(LIVE/'fallout-ce.exe'))
save(B/'test-render-equivalence.json',result)
assert len(rows)==117 and len(sampled)==38 and result['all_exact'] and result['installed_exe_restored'],[x for x in rows if not x['exact']]
print('1119 PASS, 0 FAIL; all 117 fixed-view SDL captures pixel-identical to stock EXE; 38 sampled diagnostic views retained; stock EXE restored')
