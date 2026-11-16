"""Compare unedited SDL BMP captures; no image processing dependencies."""
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'build/hd-world-viewport'


def bmp(path):
    data = path.read_bytes()
    assert data[:2] == b'BM'
    offset, = struct.unpack_from('<I', data, 10)
    width, height = struct.unpack_from('<ii', data, 18)
    bits, = struct.unpack_from('<H', data, 28)
    compression, = struct.unpack_from('<I', data, 30)
    assert width > 0 and height != 0 and bits in (24, 32) and compression in (0, 3)
    pixel_size = bits // 8
    stride = (width * pixel_size + 3) & ~3
    rows = [data[offset + y * stride:offset + y * stride + width * pixel_size]
            for y in range(abs(height))]
    if height > 0:
        rows.reverse()
    return width, abs(height), pixel_size, rows


old = bmp(OUT / 'disabled-v1/viewport-hd.bmp')
new = bmp(OUT / 'world-v1/viewport-hd.bmp')
assert old[:3] == new[:3]
w, h, pixel_size, old_rows = old
new_rows = new[3]
assert (w, h) == (1920, 1080)
hud_top, hud_left, hud_right = 880, 320, 1600


def differences(x0, y0, x1, y1):
    changed = old_black = new_black = 0
    for y in range(y0, y1):
        for x in range(x0, x1):
            offset = x * pixel_size
            a, b = old_rows[y][offset:offset + 3], new_rows[y][offset:offset + 3]
            changed += a != b
            old_black += a == b'\0\0\0'
            new_black += b == b'\0\0\0'
    return dict(pixels=(x1 - x0) * (y1 - y0), changed=changed,
                old_black=old_black, new_black=new_black)


result = {
    'comparison': 'same executable; full_height_world=0 versus default 1',
    'resolution': [w, h],
    'upper_world': differences(0, 0, w, hud_top),
    'hud': differences(hud_left, hud_top, hud_right, h),
    'left_wing': differences(0, hud_top, hud_left, h),
    'right_wing': differences(hud_right, hud_top, w, h),
}
assert result['upper_world']['changed'] == 0, result
assert result['hud']['changed'] == 0, result
for key in ('left_wing', 'right_wing'):
    assert result[key]['old_black'] == result[key]['pixels'], result
    assert result[key]['new_black'] < result[key]['pixels'] // 10, result
result['passed'] = True
(OUT / 'pixel-comparison.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, indent=2))
