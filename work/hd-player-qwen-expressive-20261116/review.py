"""Layout previews and measure generated silhouettes; never retouch candidate pixels."""
from pathlib import Path
import argparse, hashlib, json
import numpy as np
from scipy import ndimage
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'assets/generated/player-male-vault13/qwen-expressive-4poses-v2-20261116'

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()

def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')

def composite(im, color=(62, 64, 66)):
    bg = Image.new('RGBA', im.size, (*color, 255))
    bg.alpha_composite(im)
    return bg.convert('RGB')

def metrics(reference, candidate):
    a = np.asarray(reference)[:, :, 3] >= 128
    b = np.asarray(candidate)[:, :, 3] >= 128
    if b.mean() > 0.95:
        return {'valid_silhouette_measurement': False,
                'reason': 'Generated alpha is opaque across the cell; cannot compare sprite silhouette using alpha',
                'opaque_fraction': float(b.mean())}
    def outline(mask):
        return mask & ~ndimage.binary_erosion(mask, border_value=0)
    ea, eb = outline(a), outline(b)
    distances = np.concatenate((ndimage.distance_transform_edt(~eb)[ea],
                                ndimage.distance_transform_edt(~ea)[eb]))
    ay, ax = np.nonzero(a)
    by, bx = np.nonzero(b)
    labels, _ = ndimage.label(b)
    sizes = np.bincount(labels.ravel())[1:]
    return {
        'valid_silhouette_measurement': True,
        'mask_iou_including_ground_shadow': round(float((a & b).sum() / max(1, (a | b).sum())), 5),
        'symmetric_boundary_hd95_x4_pixels': round(float(np.percentile(distances, 95)), 3),
        'centroid_shift_x4_pixels': [round(float(bx.mean() - ax.mean()), 3), round(float(by.mean() - ay.mean()), 3)],
        'reference_bbox_xyxy': [int(ax.min()), int(ay.min()), int(ax.max()) + 1, int(ay.max()) + 1],
        'candidate_bbox_xyxy': [int(bx.min()), int(by.min()), int(bx.max()) + 1, int(by.max()) + 1],
        'candidate_pixels_touching_cell_border': int(b[0].sum() + b[-1].sum() + b[:, 0].sum() + b[:, -1].sum()),
        'candidate_connected_components_at_least_16_pixels': sorted([int(n) for n in sizes if n >= 16], reverse=True),
        'foreground_area_ratio': round(float(b.sum() / max(1, a.sum())), 4),
    }

def panels(images, titles, path):
    w, h = images[0].size
    sheet = Image.new('RGB', (16 + len(images) * (w + 16), h + 68), (23, 25, 28))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 22)
    for i, (im, title) in enumerate(zip(images, titles)):
        x = 16 + i * (w + 16)
        draw.text((x, 10), title, font=font, fill=(235, 235, 225))
        sheet.paste(composite(im), (x, 48))
    sheet.save(path)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--attempt', default='qwen')
    args = parser.parse_args()
    qdir = OUT / args.attempt
    preview = OUT / ('preview' if args.attempt == 'qwen' else args.attempt + '-preview')
    preview.mkdir(exist_ok=True)
    seed = Image.open(OUT / 'inputs/seed-registered-x4.png').convert('RGBA')
    first = Image.open(OUT / 'inputs/first-qwen-registered-x4.png').convert('RGBA')
    candidate = Image.open(qdir / 'candidate-x4.png').convert('RGBA')
    raw = Image.open(qdir / 'raw-x6.png').convert('RGBA')
    assert seed.size == first.size == candidate.size == (512, 768)
    assert raw.size == (768, 1152)
    panels([seed, first, candidate], ['SeedVR2: исходная основа', 'Qwen: первый вариант', 'Qwen: выразительнее + контуры'], preview / 'seed-qwen-expressive-comparison.png')
    panels([first, candidate], ['Qwen: первый вариант', 'Qwen: выразительнее + контуры'], preview / 'before-after.png')
    composite(candidate).save(preview / 'expressive-neutral-x4.png')
    composite(raw).save(preview / 'expressive-neutral-x6.png')
    composite(candidate, (230, 230, 225)).save(preview / 'expressive-light.png')
    composite(candidate, (18, 20, 23)).save(preview / 'expressive-dark.png')
    poses = []
    for i, record in enumerate(read(OUT / 'plan.json')['poses']):
        box = ((i % 2) * 256, (i // 2) * 384, (i % 2 + 1) * 256, (i // 2 + 1) * 384)
        cell = candidate.crop(box)
        cell.save(preview / (record['name'] + '.png'))
        poses.append({'name': record['name'], 'label': record['label'],
                      'first_qwen_vs_seed': metrics(seed.crop(box), first.crop(box)),
                      'expressive_qwen_vs_seed': metrics(seed.crop(box), cell)})
    baseline = read(OUT / 'runtime-art-baseline.json')
    changed = [path for path, digest in baseline.items() if not (ROOT / path).is_file() or sha(ROOT / path) != digest]
    assert not changed, changed
    result = {
        'status': 'generated preview only, not installed',
        'attempt': args.attempt,
        'source': 'The same four original hmjmpsaa/hmjmpsab poses, reusing existing SeedVR2 output; no ImageGen reference',
        'guide': 'old-new-persons-model-converter.md',
        'guide_sha256': sha(ROOT / 'old-new-persons-model-converter.md'),
        'control': read(OUT / 'control-v2/result.json'),
        'qwen': read(qdir / 'result.json'),
        'poses': poses,
        'metrics_note': 'Alpha >= 128, each 256x384 cell, including ground shadow. HD95 uses concatenated bidirectional boundary distances in x4 pixels. These are silhouette diagnostics, not joint or foot-anchor errors.',
        'postprocessing': 'ComfyUI Lanczos x6 to x4; preview-only alpha compositing and labels. Raw generated RGBA is preserved. No forced original mask, repaint, palette correction or post-generation registration.',
        'unchanged_runtime_art_and_executable_files': len(baseline),
        'runtime_modified': False,
        'limits': ['Four poses cannot establish temporal consistency of a full animation',
                   'Input anchors and contour conditioning do not guarantee exact generated FRM registration',
                   'Complete RGB edge extension and constrained matting converter are not implemented in this trial'],
        'files': {str(p.relative_to(OUT)): sha(p) for p in preview.iterdir() if p.is_file()},
    }
    write(OUT / ('result.json' if args.attempt == 'qwen' else args.attempt + '-result.json'), result)
    print(json.dumps({'attempt': args.attempt, 'seconds': result['qwen']['elapsed_seconds'],
        'runtime_files_unchanged': len(baseline), 'poses': poses}, ensure_ascii=False))

if __name__ == '__main__':
    main()
