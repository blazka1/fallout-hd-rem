"""Read-only Fallout 1 DAT1 / FRM inspection and lossless-format export.

Python 3.10+, standard library only. Does not alter DAT files or game data.
Binary layouts ported from fallout1-ce src/plib/{assoc,db} and src/game/art.cc.
All resource outputs retain the original, decompressed bytes under raw/.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import struct
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath

MAX_RESOURCE = 256 * 1024 * 1024
MAX_PIXELS = 64 * 1024 * 1024


class FormatError(ValueError):
    pass


def safe_name(name: str) -> str:
    name = name.replace("\\", "/")
    if not name or name.startswith("/") or any(ord(c) < 32 for c in name):
        raise FormatError(f"Unsafe resource path: {name!r}")
    parts = name.split("/")
    reserved = {"CON", "PRN", "AUX", "NUL"} | {f"{p}{i}" for p in ("COM", "LPT") for i in range(1, 10)}
    for part in parts:
        if (part in ("", ".", "..") or any(c in part for c in ':<>"|?*')
                or part.endswith((" ", ".")) or part.split(".")[0].upper() in reserved):
            raise FormatError(f"Unsafe resource path: {name!r}")
    return "/".join(parts).lower()


def output_path(root: Path, relative: str) -> Path:
    root = root.resolve()
    candidate = root.joinpath(*PurePosixPath(safe_name(relative)).parts).resolve()
    if not candidate.is_relative_to(root):
        raise FormatError(f"Output escapes destination: {relative!r}")
    return candidate


def write_bytes(root: Path, relative: str, data: bytes) -> Path:
    target = output_path(root, relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Refuse accidental replacement of a different original or artifact.
    if target.exists():
        if target.read_bytes() != data:
            raise FileExistsError(f"Different content already exists: {target}")
    else:
        target.write_bytes(data)
    return target


def write_json(root: Path, relative: str, value) -> Path:
    return write_bytes(root, relative, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode())


class Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def take(self, size: int) -> bytes:
        if size < 0 or self.pos + size > len(self.data):
            raise FormatError(f"Truncated data at {self.pos}, requested {size}, total {len(self.data)}")
        result = self.data[self.pos:self.pos + size]
        self.pos += size
        return result

    def unpack(self, fmt: str):
        return struct.unpack(fmt, self.take(struct.calcsize(fmt)))

    def i32(self) -> int:
        return self.unpack(">i")[0]


def lzss_decode(data: bytes, limit: int) -> bytes:
    """Fallout 1's 4 KiB LZSS ring, LSB-first flags, matches CE lzss.cc.

    Ring tail starts zeroed, as in the static buffer on initial invocation.
    Valid streams initialize any referenced tail bytes before using them.
    """
    ring = bytearray(b" " * 4078 + b"\0" * 18)
    cursor, pos = 4078, 0
    out = bytearray()
    while pos < len(data):
        flags = data[pos]
        pos += 1
        for bit in range(8):
            if pos == len(data):
                break
            if flags & (1 << bit):
                values = (data[pos],)
                pos += 1
                for value in values:
                    out.append(value)
                    ring[cursor] = value
                    cursor = (cursor + 1) & 4095
            else:
                if pos + 2 > len(data):
                    raise FormatError("Truncated LZSS backreference")
                lo, hi = data[pos:pos + 2]
                pos += 2
                start = lo | ((hi & 240) << 4)
                count = (hi & 15) + 3
                for j in range(count):
                    value = ring[(start + j) & 4095]
                    out.append(value)
                    ring[cursor] = value
                    cursor = (cursor + 1) & 4095
            if len(out) > limit:
                raise FormatError(f"LZSS output exceeds declared size {limit}")
    return bytes(out)


@dataclass(frozen=True)
class Entry:
    path: str
    original_path: str
    flags: int
    offset: int
    size: int
    packed_size: int

    @property
    def mode(self) -> int:
        return ((self.flags or 16) & 240)


class Dat1:
    def __init__(self, path: Path):
        self.path = path.resolve()
        self.size = self.path.stat().st_size
        self.entries: dict[str, Entry] = {}
        with self.path.open("rb") as f:
            def take(n):
                if n < 0 or f.tell() + n > self.size:
                    raise FormatError("DAT directory exceeds archive bounds")
                data = f.read(n)
                if len(data) != n:
                    raise FormatError("Truncated DAT directory")
                return data

            def table():
                count, capacity, item_size, ignored_pointer = struct.unpack(">4I", take(16))
                if count > 200000 or capacity < count or item_size > 4096:
                    raise FormatError("Invalid DAT association table")
                rows = []
                for _ in range(count):
                    length = take(1)[0]
                    if not length:
                        raise FormatError("Empty DAT name")
                    name = take(length).decode("cp1252")
                    rows.append((name, take(item_size)))
                return rows, item_size

            directories, root_item_size = table()
            for directory, ignored in directories:
                files, item_size = table()
                if item_size != 16:
                    raise FormatError(f"Expected 16-byte DAT file records, got {item_size}")
                for name, record in files:
                    original = name if directory == "." else directory + "\\" + name
                    key = safe_name(original)
                    entry = Entry(key, original, *struct.unpack(">4I", record))
                    length = entry.size if entry.mode == 32 else entry.packed_size
                    if entry.mode not in (16, 32, 64):
                        raise FormatError(f"Unsupported DAT mode {entry.flags:#x}: {key}")
                    if entry.offset > self.size or length > self.size - entry.offset:
                        raise FormatError(f"DAT resource exceeds archive: {key}")
                    if key in self.entries:
                        raise FormatError(f"Duplicate DAT path: {key}")
                    self.entries[key] = entry
            self.directory_end = f.tell()
            if any(e.offset < self.directory_end for e in self.entries.values() if e.size):
                raise FormatError("Resource overlaps DAT directory")

    def read(self, name: str) -> bytes:
        entry = self.entries[safe_name(name)]
        if entry.size > MAX_RESOURCE:
            raise FormatError(f"Resource exceeds safety limit: {name}")
        stored = entry.size if entry.mode == 32 else entry.packed_size
        if stored > MAX_RESOURCE:
            raise FormatError(f"Packed resource exceeds safety limit: {name}")
        with self.path.open("rb") as f:
            f.seek(entry.offset)
            packed = f.read(stored)
        if len(packed) != stored:
            raise FormatError("Truncated DAT resource")
        if entry.mode == 32:
            result = packed
        elif entry.mode == 16:
            result = lzss_decode(packed, entry.size)
        else:
            r, out = Reader(packed), bytearray()
            while len(out) < entry.size:
                word = r.unpack(">H")[0]
                length = word & 32767
                if not length:
                    raise FormatError("Zero-length DAT block")
                block = r.take(length)
                decoded = block if word & 32768 else lzss_decode(block, entry.size - len(out))
                out.extend(decoded)
                if len(out) > entry.size:
                    raise FormatError("Blocked DAT output exceeds size")
            if r.pos != len(packed):
                raise FormatError(f"Unconsumed DAT block data: {name} ({len(packed) - r.pos})")
            result = bytes(out)
        if len(result) != entry.size:
            raise FormatError(f"DAT size mismatch for {name}: {len(result)} != {entry.size}")
        return result

    def catalog(self):
        return {"archive": str(self.path), "archive_size": self.size,
                "directory_end": self.directory_end, "entry_count": len(self.entries),
                "entries": [asdict(e) for e in self.entries.values()]}


class Assets:
    def __init__(self, archives: list[Path]):
        self.archives = [Dat1(p) for p in archives]
        self.index = {}
        for archive in self.archives:
            for name in archive.entries:
                if name in self.index:
                    raise FormatError(f"Ambiguous resource in multiple archives: {name}")
                self.index[name] = archive

    def read(self, name: str) -> bytes:
        key = safe_name(name)
        return self.index[key].read(key)

    def extract(self, names: list[str], output: Path, reasons=None):
        records = []
        for key in sorted({safe_name(n) for n in names}):
            data = self.read(key)
            archive = self.index[key]
            target = write_bytes(output, "raw/" + key, data)
            records.append({**asdict(archive.entries[key]), "archive": str(archive.path),
                            "sha256": hashlib.sha256(data).hexdigest(),
                            "output": target.relative_to(output.resolve()).as_posix(),
                            "reason": (reasons or {}).get(key, "explicit selection")})
        return records


@dataclass
class Frame:
    width: int
    height: int
    shift_x: int
    shift_y: int
    pixels: bytes


def decode_frm(data: bytes):
    r = Reader(data)
    version, fps, action, count = r.unpack(">I3H")
    x = r.unpack(">6h")
    y = r.unpack(">6h")
    offsets = r.unpack(">6I")
    size = r.unpack(">I")[0]
    if version != 4 or not 0 < count <= 4096:
        raise FormatError(f"Unsupported FRM header: version={version}, frames={count}")
    if size != len(data) - 62:
        raise FormatError(f"FRM data size mismatch: {size} != {len(data)-62}")
    directions = {}
    unique = {}
    for direction, offset in enumerate(offsets):
        if offset not in unique:
            if offset >= size:
                raise FormatError("FRM direction offset outside frame data")
            r.pos = 62 + offset
            frames = []
            for _ in range(count):
                w, h, n, dx, dy = r.unpack(">HHIhh")
                if w == 0 or h == 0 or w*h > MAX_PIXELS or n != w*h:
                    raise FormatError(f"Invalid FRM frame dimensions/data: {w}x{h}, {n}")
                frames.append(Frame(w, h, dx, dy, r.take(n)))
            unique[offset] = frames
        directions[direction] = unique[offset]
    return {"version": version, "fps": fps or 10, "stored_fps": fps,
            "action_frame": action, "frame_count": count,
            "direction_x": x, "direction_y": y, "direction_offsets": offsets,
            "unique_directions": len(unique), "data_size": size}, directions


def palette_rgb(data: bytes) -> bytes:
    if len(data) < 768:
        raise FormatError("Palette needs at least 768 bytes")
    result = bytearray()
    for index in range(256):
        color = data[index*3:index*3+3]
        # Match color.cc loadColorTable and svga.cc 6-bit -> 8-bit conversion.
        result.extend(bytes(v << 2 for v in color) if max(color) <= 63 else b"\0\0\0")
    return bytes(result)


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)


def png_indexed(w: int, h: int, pixels: bytes, palette: bytes, transparent=True) -> bytes:
    if w*h != len(pixels) or w*h > MAX_PIXELS or len(palette) != 768:
        raise FormatError("Invalid PNG raster")
    raw = b"".join(b"\0" + pixels[row*w:(row+1)*w] for row in range(h))
    result = b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 3, 0, 0, 0))
    result += png_chunk(b"PLTE", palette)
    if transparent:
        result += png_chunk(b"tRNS", b"\0" + b"\xff" * 255)
    return result + png_chunk(b"IDAT", zlib.compress(raw, 9)) + png_chunk(b"IEND", b"")


def make_sheet(frames: list[Frame], palette: bytes, columns=8, transparent=True):
    if not frames:
        raise FormatError("Empty sheet")
    columns = min(columns, len(frames))
    cell_w = max(f.width for f in frames) + 4
    cell_h = max(f.height for f in frames) + 4
    width, height = columns * cell_w, ((len(frames) + columns - 1)//columns)*cell_h
    if width*height > MAX_PIXELS:
        raise FormatError("Sheet exceeds pixel limit; export fewer frames per sheet")
    raster = bytearray(width*height)
    cells = []
    for index, frame in enumerate(frames):
        x = (index % columns)*cell_w + 2
        y = (index // columns)*cell_h + 2
        for row in range(frame.height):
            start = (y+row)*width+x
            raster[start:start+frame.width] = frame.pixels[row*frame.width:(row+1)*frame.width]
        cells.append({"index": index, "x": x, "y": y, "width": frame.width, "height": frame.height,
                      "shift_x": frame.shift_x, "shift_y": frame.shift_y})
    return png_indexed(width, height, bytes(raster), palette, transparent), cells


def export_frm(data: bytes, name: str, palette: bytes, output: Path, all_frames=False):
    meta, directions = decode_frm(data)
    key = safe_name(name)
    transparent = not key.startswith("art/intrface/")
    first = directions[0][0]
    write_bytes(output, "png/" + key + ".png", png_indexed(first.width, first.height, first.pixels, palette, transparent))
    exports = []
    seen = set()
    for direction, frames in directions.items():
        off = meta["direction_offsets"][direction]
        if off in seen:
            continue
        seen.add(off)
        if all_frames:
            for index, frame in enumerate(frames):
                write_bytes(output, f"frames/{key}/d{direction}-f{index:03}.png", png_indexed(frame.width, frame.height, frame.pixels, palette, transparent))
        # Sheets deliberately retain unscaled source pixels and per-frame shifts in JSON.
        sheet, cells = make_sheet(frames, palette, transparent=transparent)
        sheet_name = f"sheets/{key}/d{direction}.png"
        write_bytes(output, sheet_name, sheet)
        exports.append({"direction": direction, "png": sheet_name, "cells": cells})
    result = {"source": key, **meta, "transparent_index": 0 if transparent else None, "sheets": exports}
    write_json(output, "metadata/" + key + ".json", result)
    return result


def lst_names(data: bytes) -> list[str]:
    # Keep empty/comment physical lines: CE treats their line numbers as IDs.
    return [re.split(r"[ ,;\r\t\n]", line)[0][:12].lower()
            for line in data.decode("cp1252").splitlines()]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", action="append", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("catalog")
    ex = sub.add_parser("extract")
    ex.add_argument("patterns", nargs="+")
    ex.add_argument("--png", action="store_true")
    ex.add_argument("--all-frames", action="store_true")
    args = p.parse_args()
    assets = Assets(args.archive)
    if args.command == "catalog":
        for archive in assets.archives:
            write_json(args.output, f"catalog/{archive.path.stem.lower()}.json", archive.catalog())
        print(json.dumps({"entries": len(assets.index), "output": str(args.output.resolve())}))
    else:
        names = [name for name in assets.index if any(fnmatch.fnmatchcase(name, pat.replace("\\", "/").lower()) for pat in args.patterns)]
        if not names:
            p.error("No resources match the requested patterns")
        records = assets.extract(names, args.output)
        if args.png:
            palette = palette_rgb(assets.read("color.pal"))
            for name in names:
                if re.search(r"\.fr[m0-5]$", name):
                    export_frm(assets.read(name), name, palette, args.output, args.all_frames)
        write_json(args.output, "extraction.json", records)
        print(json.dumps({"extracted": len(records), "bytes": sum(r["size"] for r in records)}))


if __name__ == "__main__":
    main()
