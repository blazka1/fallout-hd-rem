"""Read-only dense-pixel regression analysis for frozen SDL fade captures.

Run with the already installed ComfyUI Python (Pillow/numpy). Capture all frames
without world ticks/camera/cursor changes. No generated art or captures are edited.
RGB6 white normally becomes RGB8 252, not255. Intermediate frames allow a few
levels for RGB6 palette rounding and final integer texture writes.
"""
from pathlib import Path
import argparse
import json

import numpy as np
from PIL import Image


def read(path):
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--normal", type=Path, required=True)
    parser.add_argument("--dark25", type=Path)
    parser.add_argument("--dark50", type=Path)
    parser.add_argument("--white50", type=Path)
    parser.add_argument("--white", type=Path)
    parser.add_argument("--classic-white", type=Path,
                        help="Pixel-exact white endpoint reference; also excludes black SDL letterboxing")
    parser.add_argument("--owner-mask", type=Path,
                        help="Optional black/white HD-owner mask; native resolution is expanded with nearest sampling")
    parser.add_argument("--normal-classic", type=Path,
                        help="Optional filter to pixels actually changed by HD; an ownership mask is preferred")
    parser.add_argument("--viewport", type=int, nargs=4, metavar=("X", "Y", "W", "H"))
    parser.add_argument("--white-level", type=int, default=252)
    parser.add_argument("--tolerance", type=float, default=4.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    normal = read(args.normal)
    height, width, _ = normal.shape
    mask = np.ones((height, width), dtype=bool)
    if args.viewport:
        x, y, w, h = args.viewport
        if min(x, y) < 0 or min(w, h) <= 0 or x + w > width or y + h > height:
            parser.error("Viewport must be inside the capture")
        mask[:] = False
        mask[y:y + h, x:x + w] = True
    classic_white = None
    if args.classic_white:
        classic_white = read(args.classic_white)
        if classic_white.shape != normal.shape:
            parser.error("Classic white capture size differs")
        mask &= np.max(classic_white, axis=2) != 0
    if args.owner_mask:
        owner = Image.open(args.owner_mask).convert("L")
        owner = owner.resize((width, height), Image.Resampling.NEAREST)
        mask &= np.asarray(owner) != 0
    if args.normal_classic:
        classic = read(args.normal_classic)
        if classic.shape != normal.shape:
            parser.error("Classic normal capture size differs")
        mask &= np.any(classic != normal, axis=2)
    if not mask.any():
        parser.error("No pixels remain in the analysis mask")
    frames = []
    for label, path, gain, offset in (
        ("dark25", args.dark25, 0.25, 0.0),
        ("dark50", args.dark50, 0.5, 0.0),
        ("white50", args.white50, 0.5, args.white_level * 0.5),
        ("white", args.white, 0.0, float(args.white_level)),
    ):
        if path is None:
            continue
        actual = read(path)
        if actual.shape != normal.shape:
            parser.error("Capture size differs: " + str(path))
        expected = np.clip(normal * gain + offset, 0.0, 255.0)
        tolerance = args.tolerance
        if label == "white" and classic_white is not None:
            expected = classic_white
            tolerance = 0.0
        delta = np.abs(actual - expected)[mask]
        bad = np.max(delta, axis=1) > tolerance
        frames.append({
            "frame": label, "path": str(path.resolve()), "pixels_checked": int(mask.sum()),
            "expected_gain": gain, "expected_offset": offset,
            "pixel_exact_classic_endpoint": label == "white" and classic_white is not None,
            "tolerance": tolerance, "max_channel_error": float(delta.max()),
            "mean_absolute_channel_error": float(delta.mean()),
            "p99_channel_error": float(np.percentile(delta, 99)),
            "pixels_over_tolerance": int(bad.sum()), "failed_fraction": float(bad.mean()),
            "pass": not bool(bad.any()),
        })
    if not frames:
        parser.error("Provide at least one fade capture")
    result = {"normal": str(args.normal.resolve()), "size": [width, height],
              "scope": "Dense samples in a frozen rendered frame, not only image mean; detects native-block gain differences",
              "frames": frames, "passed": sum(row["pass"] for row in frames),
              "failed": sum(not row["pass"] for row in frames)}
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text)
    if result["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
