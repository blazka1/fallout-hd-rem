"""Collect only submitted jobs, then record an explicit user-requested pause."""
from pathlib import Path
import importlib.util,json,time
spec=importlib.util.spec_from_file_location('rat_pipeline',Path(__file__).with_name('pipeline.py'))
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
collected=[];uncertain=[]
previous=p.OUT/'pause-state.json'
if previous.exists():
    old=p.read(previous);stamp=old.get('paused_utc','unknown').replace(':','').replace('-','')
    archived=p.OUT/'pause-history'/('pause-'+stamp+'.json')
    if not archived.exists():p.save(archived,old)
p.save(Path(__file__).with_name('task.json'),dict(status='pausing after currently submitted job finishes',
    user_request='ставь паузу, как джоба закончится',new_gpu_jobs_allowed=False))
for stage in ['seed','qwen','prepared','prepared-v2']:
    for d in sorted((p.OUT/stage).glob('*')):
        if not d.is_dir():continue
        if (d/'run.json').exists() and not (d/'result.json').exists():
            # execute sees run.json and only collects this exact prompt ID.
            result=p.execute(d,{},{});collected.append(dict(stage=stage,panel=d.name,prompt_id=result['prompt_id']))
        elif (d/'submission.json').exists() and not (d/'run.json').exists():
            uncertain.append(dict(stage=stage,panel=d.name,submission=p.read(d/'submission.json')))
plans=p.read(p.OUT/'panels.json')
done={stage:[v['id'] for v in plans if (p.OUT/stage/v['id']/'result.json').exists()] for stage in ['seed','qwen','prepared-v2']}
q=p.h.req('/queue')
record=dict(status='paused at explicit user request',paused_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
    user_request='ставь паузу, как джоба закончится',
    new_gpu_jobs_submitted_by_pause=False,collected_existing_jobs=collected,uncertain_submissions=uncertain,
    completed_panels=done,remaining_qwen_panels=[v['id'] for v in plans if v['id'] not in done['qwen']],
    remaining_preparation_panels=[v['id'] for v in plans if v['id'] not in done['prepared-v2']],
    shared_gpu_queue_running=len(q['queue_running']),shared_gpu_queue_pending=len(q['queue_pending']),
    resume_only_after_user_request=True,selected_package_created=False,hd_rat_assets_installed=False,
    isolated_runtime='runtime/hd-rat-pilot',shared_runtime_modified=False,
    known_remaining_work=['Finish remaining Qwen panels, then exact-mask preparation.',
        'Aimed-shot opaque-black HUD support and the green wireframe prompt are implemented. Its protected-line mask is saved; final preparation and visual/byte checks are still required.',
        'Inspect all animation loops, create the complete package, install only isolated rat pilot and run loaded/corrupt/missing checks.',
        'Run final world regression and loaded/corrupt/missing asset checks after finishing the package.'],
    regression_passed=dict(menu=dict(passed=139,failed=0,report='build/hd-rat-20261115/menu/manifest.json'),
        package_absent=dict(passed=560,failed=0,report='build/hd-rat-20261115/preview/package-absent-resumed/manifest.json'),
        earlier_world=dict(passed=577,failed=0,report='build/hd-rat-20261115/world-regression/manifest.json',
            note='Earlier executable; rerun after final code changes.')),
    isolated_executable_sha256=p.sha(p.ROOT/'runtime/hd-rat-pilot/fallout-ce.exe'))
record['unique_qwen_frames']=sum(len(v['slots']) for v in plans if v['id'] in done['qwen'])
record['unique_prepared_frames']=sum(len(v['slots']) for v in plans if v['id'] in done['prepared-v2'])
p.save(p.OUT/'pause-state.json',record);p.save(Path(__file__).with_name('task.json'),record)
print(json.dumps(dict(status=record['status'],completed={k:len(v) for k,v in done.items()},
    remaining_qwen=len(record['remaining_qwen_panels']),collected=collected,uncertain=uncertain,
    queue_running=record['shared_gpu_queue_running'],queue_pending=record['shared_gpu_queue_pending']),ensure_ascii=False),flush=True)
