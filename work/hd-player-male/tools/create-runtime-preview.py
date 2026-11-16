"""Package actual CE SDL screenshots without artwork edits or image scaling.

PNG sheets and lossless animated WebP retain every pasted source RGB pixel.
GIF is also supplied for compatibility; its format requires a 256-color palette.
This script never launches CE and never modifies assets or source screenshots.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageSequence

ROOT = Path(__file__).resolve().parents[3]
LABELS = ("NE", "E", "SE", "SW", "W", "NW")
PANEL = 320
HEADER = 32
BACKGROUND = (21, 24, 25)
FOREGROUND = (220, 221, 205)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size: int = 17):
    path = Path("C:/Windows/Fonts/segoeui.ttf")
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def sheet(images: list[Image.Image], labels: list[str], columns: int) -> Image.Image:
    if any(image.size != (PANEL, PANEL) for image in images):
        raise ValueError("Expected original 320x320 SDL crops, without resizing")
    rows = (len(images) + columns - 1) // columns
    result = Image.new("RGB", (columns * PANEL, rows * (PANEL + HEADER)), BACKGROUND)
    draw = ImageDraw.Draw(result)
    for index, (source, label) in enumerate(zip(images, labels, strict=True)):
        x, y = index % columns * PANEL, index // columns * (PANEL + HEADER)
        result.paste(source, (x, y + HEADER))
        draw.text((x + 10, y + 5), label, font=font(), fill=FOREGROUND)
        # Packaging must not change even one source pixel in a lossless sheet.
        assert result.crop((x, y + HEADER, x + PANEL, y + HEADER + PANEL)).tobytes() == source.tobytes()
    return result


def gif_durations(durations: list[int]) -> list[int]:
    # Quantize cumulative boundaries, preventing cumulative timing drift.
    elapsed, previous = 0, 0
    result = []
    for duration in durations:
        elapsed += duration
        boundary = int(round(elapsed / 10.0)) * 10
        result.append(max(10, boundary - previous))
        previous = boundary
    return result


def animations(frames: list[Image.Image], durations: list[int], destination: Path) -> dict:
    if len(frames) != len(durations) or not all(duration > 0 for duration in durations):
        raise ValueError("Every animation frame requires a positive duration")
    webp = destination.with_suffix(".webp")
    frames[0].save(webp, save_all=True, append_images=frames[1:], duration=durations,
        loop=0, lossless=True, quality=100, method=6, minimize_size=False)
    with Image.open(webp) as decoded:
        assert decoded.n_frames == len(frames)
        for actual, expected in zip(ImageSequence.Iterator(decoded), frames, strict=True):
            assert actual.convert("RGB").tobytes() == expected.tobytes(), "Lossless preview changed pixels"

    # Derive one shared palette from every frame so palette changes cannot flicker.
    palette_source = Image.new("RGB", (frames[0].width, frames[0].height * len(frames)))
    for index, frame in enumerate(frames):
        palette_source.paste(frame, (0, index * frame.height))
    palette = palette_source.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    gif = destination.with_suffix(".gif")
    encoded_durations = gif_durations(durations)
    indexed[0].save(gif, save_all=True, append_images=indexed[1:], duration=encoded_durations,
        loop=0, optimize=False, disposal=2)
    with Image.open(gif) as decoded:
        assert decoded.n_frames == len(frames)
        actual_durations = [frame.info["duration"] for frame in ImageSequence.Iterator(decoded)]
        assert actual_durations == encoded_durations
    return {"frames": len(frames), "dimensions": list(frames[0].size), "durations_ms": durations,
        "gif_durations_ms": encoded_durations, "lossless_webp": webp.name,
        "compatibility_gif": gif.name, "gif_note": "256-color encoding; shared palette, no dithering; 10 ms time units"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, nargs="?",
        default=ROOT / "build/hd-player-male/preview/integration-v1")
    args = parser.parse_args()
    source = args.source.resolve()
    output = source / "gallery"
    output.mkdir(exist_ok=True)
    inputs: dict[str, str] = {}

    def read(name: str) -> Image.Image:
        path = source / name
        inputs[name] = sha(path)
        with Image.open(path) as opened:
            return opened.convert("RGB")

    result = json.loads((source / "result.json").read_text(encoding="utf-8-sig"))
    if result["failed"] or result["loaded_player_frames"] != 54:
        raise ValueError("A successful complete 54-frame integration run is required")
    walk = [[read(f"walk-d{direction}-f{frame:03}.png") for frame in range(8)] for direction in range(6)]
    stand = [read(f"stand-d{direction}-f000.png") for direction in range(6)]
    sheet(stand, [f"Stand: {label} / d{direction}" for direction, label in enumerate(LABELS)], 3).save(output / "six-directions-stand.png")
    six = [sheet([walk[direction][frame] for direction in range(6)],
        [f"Walk: {label} / d{direction}" for direction, label in enumerate(LABELS)], 3) for frame in range(8)]
    six[0].save(output / "six-directions-cave-still.png")
    six_info = animations(six, [100] * 8, output / "six-directions-cave")
    sheet([walk[direction][frame] for direction in range(6) for frame in range(8)],
        [f"{LABELS[direction]} / d{direction} / f{frame}" for direction in range(6) for frame in range(8)], 8).save(output / "walk-48-contact-sheet.png")

    with (source / "timed-walk.tsv").open(encoding="utf-8-sig", newline="") as stream:
        samples = [{key: int(value) for key, value in row.items()} for row in csv.DictReader(stream, delimiter="\t")]
    walk_samples = [row for row in samples if row["animation"] == 1]
    timed_paths = sorted(source.glob("timed-walk-*.png"), key=lambda path:
        int(path.stem.rsplit("-", 1)[-1]) if path.stem.rsplit("-", 1)[-1].isdigit() else 100000)
    timed_paths = [path for path in timed_paths if path.stem.rsplit("-", 1)[-1].isdigit()]
    indices = [int(path.stem.rsplit("-", 1)[-1]) for path in timed_paths]
    if indices != list(range(len(timed_paths))) or len(walk_samples) <= len(timed_paths):
        raise ValueError("Timed captures must be consecutive and have a following timestamp")
    matched = walk_samples[:len(timed_paths)]
    timed = [read(path.name) for path in timed_paths]
    durations = [walk_samples[index + 1]["elapsed_ms"] - row["elapsed_ms"] for index, row in enumerate(matched)]
    timed_info = animations(timed, durations, output / "timed-ce-walk")
    timed_info.update({"capture_start_ms": matched[0]["elapsed_ms"],
        "last_capture_ms": matched[-1]["elapsed_ms"], "next_capture_ms": walk_samples[len(timed_paths)]["elapsed_ms"],
        "full_walk_end_ms": samples[-1]["elapsed_ms"], "full_walk_end_tile": samples[-1]["tile"],
        "source_rows": matched,
        "mapping": "Test saves timed-walk-N only for animation==1 before appending that same sample row; first consecutive walking rows map directly.",
        "limit": "Only first 24 captures. Crop follows the actor tile at each hex and is not the game camera. Timestamps are recorded after screenshot/crop capture and include capture overhead; these are observed sample intervals, not a precise real-time gameplay recording. The loop jump is a preview restart."})
    selected = [0, 3, 6, 9, 12, 15, 18, 23]
    sheet([timed[index] for index in selected],
        [f"{matched[index]['elapsed_ms']} ms / tile {matched[index]['tile']} / f{matched[index]['frame']}" for index in selected], 4).save(output / "timed-walk-contact-sheet.png")

    for stem, left_name, right_name, left_label, right_label in [
        ("classic-hd-comparison", "player-classic-cave-hd.png", "player-hd-cave-hd.png", "Classic actor / HD cave", "HD actor / HD cave"),
        ("occlusion-comparison", "player-behind-geometry-hidden.png", "player-behind-geometry-hd.png", "Actor hidden (control)", "Actor behind cave geometry")]:
        left, right = read(left_name), read(right_name)
        bounds = ImageChops.difference(left, right).getbbox()
        if not bounds:
            raise ValueError(f"No changed pixels found for {stem}")
        center_x, center_y = (bounds[0] + bounds[2]) // 2, (bounds[1] + bounds[3]) // 2
        x, y = max(0, min(left.width - PANEL, center_x - PANEL // 2)), max(0, min(left.height - PANEL, center_y - PANEL // 2))
        box = (x, y, x + PANEL, y + PANEL)
        sheet([left.crop(box), right.crop(box)], [left_label, right_label], 2).save(output / f"{stem}.png")

    manifest = {"source_directory": str(source), "integration_result": result,
        "source_pixels": "Original SDL screenshot RGB pixels pasted at 1:1 scale. No art edits, recoloring, or resampling. Labels are outside image panels.",
        "six_directions": six_info,
        "six_directions_limit": "All 48 actual CE rendered frame selections on one fixed tile; assembled at source FRM 10 fps. This montage is not six simultaneous live characters or a recording of six timed paths.",
        "timed_ce_walk": timed_info, "input_sha256": inputs,
        "output_sha256": {path.name: sha(path) for path in sorted(output.iterdir()) if path.is_file() and path.suffix in (".gif", ".png", ".webp")}}
    (output / "preview-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "walk_frames": len(six), "timed_captures": len(timed),
        "timed_duration_ms": sum(durations), "pixel_exact_webp_verified": True}, indent=2))


if __name__ == "__main__":
    main()
