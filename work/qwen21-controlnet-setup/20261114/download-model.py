"""Stage the requested official Qwen 2.1 ControlNet INT8; no environment changes."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil
import struct
import subprocess
import time

HERE = Path(__file__).resolve().parent
REPO = 'Comfy-Org/Qwen-Image-2.1'
REL = 'model_patches/qwen_image_2.1_fun_controlnet_union_int8_convrot.safetensors'
EXPECTED = '07aa961570ac0e03d4ca936aecd76854d077a33cde69b5092399afba01b3715d'
TARGET = HERE / Path(REL).name
PART = TARGET.with_suffix('.safetensors.part')

def save(name, obj):
    (HERE / name).write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')

def get_json(url):
    return json.loads(subprocess.check_output(['curl.exe', '-4', '--fail', '--silent',
        '--show-error', '--location', '--connect-timeout', '15', '--max-time', '60', url]))

def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def main():
    plan_path = HERE / 'download-plan.json'
    if plan_path.exists():
        plan = json.loads(plan_path.read_text(encoding='utf-8'))
    else:
        info = get_json(f'https://huggingface.co/api/models/{REPO}?blobs=true')
        item = next(x for x in info['siblings'] if x['rfilename'] == REL)
        plan = dict(repository=REPO, revision=info['sha'], file=REL,
                    size=item['size'], sha256=item['lfs']['sha256'],
                    created_utc=datetime.now(timezone.utc).isoformat())
        save('download-plan.json', plan)
    assert plan['repository'] == REPO and plan['file'] == REL
    assert plan['sha256'] == EXPECTED, 'Published checksum changed; inspect before proceeding'
    size = plan['size']
    assert shutil.disk_usage(HERE).free > size * 2 + 4 * 1024**3, 'Insufficient free space'
    if not TARGET.exists():
        started = time.monotonic()
        url = f'https://huggingface.co/{REPO}/resolve/{plan["revision"]}/{REL}?download=true'
        for attempt in range(1, 5):
            if PART.exists() and PART.stat().st_size == size:
                break
            assert not PART.exists() or PART.stat().st_size < size, 'Oversized partial preserved'
            with (HERE / 'download.log').open('ab') as log:
                p = subprocess.Popen(['curl.exe', '-4', '--fail', '--silent', '--show-error',
                    '--location', '--connect-timeout', '20', '--speed-limit', '1024',
                    '--speed-time', '60', '--continue-at', '-', '--output', str(PART), url],
                    stdout=subprocess.DEVNULL, stderr=log)
                reported = 0
                while p.poll() is None:
                    now = time.monotonic()
                    if now - reported >= 15:
                        received = PART.stat().st_size if PART.exists() else 0
                        state = dict(status='downloading', received=received, total=size,
                            percent=round(received / size * 100, 1), attempt=attempt,
                            elapsed_seconds=round(now - started, 1))
                        save('progress.json', state)
                        print(json.dumps(state), flush=True)
                        reported = now
                    time.sleep(1)
            if p.returncode == 0:
                break
            print(f'Download interrupted, preserving partial; attempt {attempt}', flush=True)
        assert PART.exists() and PART.stat().st_size == size, 'Incomplete download retained'
        save('progress.json', dict(status='verifying', total=size))
        assert sha256(PART) == EXPECTED, 'Checksum mismatch; partial retained'
        PART.rename(TARGET)
    assert TARGET.stat().st_size == size and sha256(TARGET) == EXPECTED
    with TARGET.open('rb') as f:
        header_size = struct.unpack('<Q', f.read(8))[0]
        assert 0 < header_size < 32 * 1024 * 1024
        header = json.loads(f.read(header_size))
    tensors = {k: v for k, v in header.items() if k != '__metadata__'}
    assert 'control_img_in.weight' in tensors
    assert 'control_blocks.0.img_mlp.out.weight' in tensors
    assert max(v['data_offsets'][1] for v in tensors.values()) == size - 8 - header_size
    save('staged.json', dict(**plan, staged_path=str(TARGET), tensor_count=len(tensors),
         verified_utc=datetime.now(timezone.utc).isoformat(), status='sha256_and_header_verified'))
    save('progress.json', dict(status='verified', total=size, sha256=EXPECTED))
    print('Staged and verified: ' + str(TARGET), flush=True)

if __name__ == '__main__':
    main()
