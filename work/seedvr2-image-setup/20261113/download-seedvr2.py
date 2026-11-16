"""Install the two user-requested official SeedVR2 3B INT8 weights only."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
OUT = HERE / 'model-install'
DEST = Path('C:/Users/Administrator/AppData/Local/Comfy-Desktop/ComfyUI-Shared/models')
REPO = 'Comfy-Org/SeedVR2'
FILES = ['diffusion_models/seedvr2_3b_int8_convrot.safetensors',
         'vae/seedvr2_ema_vae_fp16.safetensors']

def write(path, value):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, path)

def get_json(url):
    data = subprocess.check_output(['curl.exe', '-4', '--fail', '--silent', '--show-error',
        '--location', '--connect-timeout', '15', '--max-time', '60',
        '--retry', '5', '--retry-all-errors', '--retry-delay', '2', url])
    return json.loads(data)

def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()

def partial_path(target):
    return target.with_suffix(target.suffix + '.codex-seedvr2-download.part')

def download(item, revision):
    relative, size, expected = item['path'], item['size'], item['lfs']['oid']
    target = DEST / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = partial_path(target)
    progress = OUT / (target.stem + '.progress.json')
    if target.exists():
        if target.stat().st_size != size or digest(target) != expected:
            raise RuntimeError('Different existing model preserved: ' + str(target))
        return dict(item, destination=str(target), sha256=expected, reused=True)
    started = time.monotonic()
    for attempt in range(1, 7):
        offset = partial.stat().st_size if partial.exists() else 0
        if offset > size:
            raise RuntimeError('Oversized partial preserved: ' + str(partial))
        if offset == size:
            break
        url = f'https://huggingface.co/{REPO}/resolve/{revision}/{relative}?download=true'
        with (OUT / (target.stem + '.curl.log')).open('ab') as log:
            process = subprocess.Popen(['curl.exe', '-4', '--fail', '--silent', '--show-error',
                '--location', '--connect-timeout', '20', '--speed-limit', '1024',
                '--speed-time', '90', '--continue-at', '-', '--output', str(partial), url],
                stdout=subprocess.DEVNULL, stderr=log)
            last_report = 0
            while process.poll() is None:
                now = time.monotonic()
                if now - last_report >= 15:
                    received = partial.stat().st_size if partial.exists() else 0
                    state = dict(file=relative, downloaded=received, total=size,
                        percent=round(received / size * 100, 2), attempt=attempt,
                        elapsed_seconds=round(now-started, 1), status='downloading')
                    write(progress, state)
                    print(f'{target.name}: {state["percent"]}% ({received//1048576}/{size//1048576} MiB)', flush=True)
                    last_report = now
                time.sleep(1)
            if process.returncode == 0 and partial.stat().st_size == size:
                break
            print(f'{target.name}: interrupted; resumable partial retained, attempt {attempt}', flush=True)
        time.sleep(min(2 * attempt, 10))
    if not partial.exists() or partial.stat().st_size != size:
        raise RuntimeError('Download incomplete; partial retained: ' + str(partial))
    write(progress, dict(file=relative, status='verifying_sha256', total=size, downloaded=size))
    actual = digest(partial)
    if actual != expected:
        raise RuntimeError('SHA256 mismatch; partial retained: ' + str(partial))
    if target.exists():
        raise RuntimeError('Destination appeared; both files preserved')
    partial.rename(target)
    write(progress, dict(file=relative, status='verified', sha256=actual, total=size, downloaded=size))
    print('Installed and SHA256 verified: ' + target.name, flush=True)
    return dict(item, destination=str(target), sha256=actual, reused=False)

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    plan_path = OUT / 'download-plan.json'
    if plan_path.exists():
        plan = json.loads(plan_path.read_text(encoding='utf-8'))
    else:
        revision = get_json(f'https://huggingface.co/api/models/{REPO}')['sha']
        entries = []
        for folder in ('diffusion_models', 'vae'):
            rows = get_json(f'https://huggingface.co/api/models/{REPO}/tree/{revision}/{folder}')
            entries.extend(row for row in rows if row['path'] in FILES)
        if {row['path'] for row in entries} != set(FILES):
            raise RuntimeError('Official model inventory incomplete')
        if any(not row.get('lfs', {}).get('oid') or row['lfs']['size'] != row['size'] for row in entries):
            raise RuntimeError('Missing official size or SHA256')
        plan = dict(repository=REPO, revision=revision, files=entries,
            requested_by_user=True, created_utc=datetime.now(timezone.utc).isoformat())
        write(plan_path, plan)
    if plan['repository'] != REPO or {row['path'] for row in plan['files']} != set(FILES):
        raise RuntimeError('Unexpected saved plan')
    needed = sum(max(0, row['size'] - (partial_path(DEST/row['path']).stat().st_size
        if partial_path(DEST/row['path']).exists() else 0))
        for row in plan['files'] if not (DEST/row['path']).exists())
    free = shutil.disk_usage(DEST).free
    if free < needed + 4 * 1024**3:
        raise RuntimeError('Insufficient free disk; nothing deleted')
    print(f'Official revision {plan["revision"]}; need {needed/1e9:.2f} GB; free {free/1e9:.2f} GB', flush=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda row: download(row, plan['revision']), plan['files']))
    write(OUT/'installed.json', dict(repository=REPO, revision=plan['revision'], files=results,
        verified_utc=datetime.now(timezone.utc).isoformat()))
    print('Both SeedVR2 model files installed and verified.', flush=True)

if __name__ == '__main__':
    main()
