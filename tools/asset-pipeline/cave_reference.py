"""Inspect a Fallout 1 MAP v19 and export its exact static-art references.

Python standard library only; archives are opened read-only. This module does
not render game lighting, infer dependencies from pixels, or change source art.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import zlib

from fallout_assets import (Assets, FormatError, Reader, decode_frm, export_frm,
                            lst_names, make_sheet, palette_rgb, png_chunk, safe_name,
                            write_bytes, write_json)

ART_DIRS = ("items", "critters", "scenery", "walls", "tiles", "misc",
            "intrface", "inven", "heads", "backgrnd", "skilldex")


def checked_count(value, label, maximum=100000):
    if not 0 <= value <= maximum:
        raise FormatError(f"Invalid {label}: {value}")
    return value


class MapInspector:
    def __init__(self, assets):
        self.assets = assets
        self.lists = {}
        self.protos = {}

    def names(self, path):
        if path not in self.lists:
            self.lists[path] = lst_names(self.assets.read(path))
        return self.lists[path]

    def prototype(self, pid):
        if pid not in self.protos:
            kind, index = (pid >> 24) & 255, pid & 0xffffff
            if not 0 <= kind <= 5 or index == 0:
                raise FormatError(f"Unsupported prototype PID {pid:#x}")
            directory = ART_DIRS[kind]
            list_path = f"proto/{directory}/{directory}.lst"
            names = self.names(list_path)
            if index > len(names) or not names[index-1]:
                raise FormatError(f"Prototype list index outside range: {pid:#x}")
            name = safe_name(f"proto/{directory}/{names[index-1]}")
            data = self.assets.read(name)
            if len(data) < 12 or struct.unpack_from(">I", data)[0] != pid:
                raise FormatError(f"Prototype PID/header mismatch: {name}")
            subtype = None
            if kind in (0, 2):
                if len(data) < 36:
                    raise FormatError(f"Truncated subtype in {name}")
                subtype = struct.unpack_from(">i", data, 32)[0]
            self.protos[pid] = {"pid": pid, "path": name,
                                "fid": struct.unpack_from(">I", data, 8)[0],
                                "subtype": subtype,
                                "sha256": hashlib.sha256(data).hexdigest()}
        return self.protos[pid]

    def art_path(self, fid):
        kind, index = (fid >> 24) & 15, fid & 4095
        # Critter and talking-head filenames require animation/alias resolution.
        if kind in (1, 8):
            return None
        if not 0 <= kind < len(ART_DIRS):
            raise FormatError(f"Invalid FID {fid:#x}")
        directory = ART_DIRS[kind]
        names = self.names(f"art/{directory}/{directory}.lst")
        if index >= len(names) or not names[index]:
            raise FormatError(f"Art list index outside range: {fid:#x}")
        return safe_name(f"art/{directory}/{names[index]}")

    def parse(self, path):
        data = self.assets.read(path)
        r = Reader(data)
        version = r.i32()
        if version != 19:
            raise FormatError(f"Only MAP version 19 is supported, got {version}")
        name = r.take(16).split(b"\0", 1)[0].decode("cp1252")
        labels = ("entering_tile", "entering_elevation", "entering_rotation",
                  "local_count", "script_index", "flags", "darkness",
                  "global_count", "map_index", "last_visit")
        header = {"version": version, "name": name,
                  **dict(zip(labels, r.unpack(">10i")))}
        r.take(44*4)
        for key in ("global_count", "local_count"):
            r.take(checked_count(header[key], key)*4)
        floors, roofs, tile_words = [], [], []
        for elevation in range(3):
            floor, roof, words = [], [], ()
            if not header["flags"] & (2 << elevation):
                words = r.unpack(">10000I")
                floor = [word & 4095 for word in words]
                roof = [(word >> 16) & 4095 for word in words]
            floors.append(floor)
            roofs.append(roof)
            tile_words.append(words)
        script_counts = []
        for kind in range(5):
            count = checked_count(r.i32(), "script count")
            script_counts.append(count)
            lengths = 0
            for extent in range((count+15)//16):
                for index in range(16):
                    sid, ignored_next = r.unpack(">2i")
                    sid_kind = (sid >> 24) & 255
                    if sid_kind == 1:
                        r.take(8)
                    elif sid_kind == 2:
                        r.take(4)
                    r.take(14*4)
                length, ignored_next = r.unpack(">2i")
                lengths += checked_count(length, "script extent length", 16)
            if lengths != count:
                raise FormatError(f"Script count mismatch for type {kind}: {lengths}!={count}")
        object_section_offset = r.pos
        total = checked_count(r.i32(), "object total")
        objects, root_counts = [], []

        def read_object(elevation, parent=None, quantity=None, depth=0):
            if depth > 64 or len(objects) >= 100000:
                raise FormatError("Object inventory exceeds safety limits")
            start = r.pos
            values = r.unpack(">18i")
            fields = ("id", "tile", "x", "y", "screen_x", "screen_y", "frame",
                      "rotation", "fid", "flags", "stored_elevation", "pid",
                      "combat_id", "light_distance", "light_intensity", "unused",
                      "sid", "script_index")
            obj = dict(zip(fields, values))
            obj.update({"offset": start, "elevation": elevation,
                        "parent_offset": parent, "quantity": quantity})
            inv_count, capacity, ignored_pointer = r.unpack(">3i")
            checked_count(inv_count, "inventory length")
            if capacity < inv_count:
                raise FormatError("Inventory capacity below length")
            kind = (obj["pid"] >> 24) & 255
            if kind == 1:
                r.take(11*4)
            else:
                r.take(4)
                if kind == 0:
                    subtype = self.prototype(obj["pid"])["subtype"]
                    if not 0 <= subtype <= 6:
                        raise FormatError(f"Unknown item subtype {subtype}")
                    r.take((2 if subtype == 3 else 1 if subtype in (4, 5, 6) else 0)*4)
                elif kind == 2:
                    subtype = self.prototype(obj["pid"])["subtype"]
                    if not 0 <= subtype <= 5:
                        raise FormatError(f"Unknown scenery subtype {subtype}")
                    r.take((1, 2, 2, 1, 1, 0)[subtype]*4)
                elif kind == 5 and 0x05000010 <= obj["pid"] <= 0x05000017:
                    r.take(16)
                elif kind not in (3, 4, 5):
                    raise FormatError(f"Unsupported object PID {obj['pid']:#x}")
            obj["art"] = self.art_path(obj["fid"])
            obj["inventory_length"] = inv_count
            objects.append(obj)
            for _ in range(inv_count):
                amount = r.i32()
                read_object(elevation, start, amount, depth+1)
            obj["end_offset"] = r.pos

        for elevation in range(3):
            count = checked_count(r.i32(), "elevation root objects")
            root_counts.append(count)
            for _ in range(count):
                read_object(elevation)
        if r.pos != len(data):
            raise FormatError(f"Unconsumed map data: {len(data)-r.pos} bytes")
        if sum(root_counts) != total:
            raise FormatError(f"Root object count mismatch: {sum(root_counts)}!={total}")
        return {"source": path, "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data), "header": header, "scripts_per_type": script_counts,
                "object_section_offset": object_section_offset,
                "root_object_count": total, "objects_per_elevation": root_counts,
                "parsed_objects_including_inventory": len(objects), "parsed_bytes": r.pos,
                "floor_ids": floors, "roof_ids": roofs, "tile_words": tile_words,
                "objects": objects}


def candidates(inspector, info):
    count = Counter(o["art"] for o in info["objects"] if o["art"] and
                    o["art"].startswith(("art/walls/", "art/scenery/")))
    rows = []
    for name, occurrences in sorted(count.items()):
        data = inspector.assets.read(name)
        meta, directions = decode_frm(data)
        frame = directions[0][0]
        rows.append({"path": name, "instances": occurrences,
                     "fids": sorted({o["fid"] for o in info["objects"] if o["art"] == name}),
                     "pids": sorted({o["pid"] for o in info["objects"] if o["art"] == name}),
                     "width": frame.width, "height": frame.height,
                     "frames": meta["frame_count"]})
    return rows


def rgba_png(frame, palette):
    """Only expand original palette indices to straight RGBA; no resampling."""
    pixels = b"".join(palette[index*3:index*3+3] + bytes((0 if index == 0 else 255,))
                      for index in frame.pixels)
    scanlines = b"".join(b"\0" + pixels[y*frame.width*4:(y+1)*frame.width*4]
                         for y in range(frame.height))
    result = b"\x89PNG\r\n\x1a\n" + png_chunk(
        b"IHDR", struct.pack(">IIBBBBB", frame.width, frame.height, 8, 6, 0, 0, 0))
    result += png_chunk(b"IDAT", zlib.compress(scanlines, 9)) + png_chunk(b"IEND", b"")
    return result, pixels


def validate_png(data, width, height, expected, color_type):
    """Independent container/CRC/raster check of our filter-0 PNG outputs."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise FormatError("PNG signature mismatch")
    r, compressed = Reader(data), bytearray()
    r.take(8)
    seen_header = False
    while r.pos < len(data):
        length = r.unpack(">I")[0]
        kind, payload = r.take(4), r.take(length)
        crc = r.unpack(">I")[0]
        if crc != zlib.crc32(kind+payload) & 0xffffffff:
            raise FormatError("PNG CRC mismatch")
        if kind == b"IHDR":
            if struct.unpack(">IIBBBBB", payload) != (width, height, 8, color_type, 0, 0, 0):
                raise FormatError("PNG header mismatch")
            seen_header = True
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            if payload or r.pos != len(data):
                raise FormatError("Unexpected PNG end data")
            break
    stride = width * (4 if color_type == 6 else 1)
    raw = zlib.decompress(compressed)
    if not seen_header or len(raw) != height*(stride+1):
        raise FormatError("PNG decoded size mismatch")
    if any(raw[y*(stride+1)] != 0 for y in range(height)):
        raise FormatError("Unexpected PNG filter")
    actual = b"".join(raw[y*(stride+1)+1:(y+1)*(stride+1)] for y in range(height))
    if actual != expected:
        raise FormatError("PNG pixels differ from decoded original FRM")


def export_sample(inspector, info, output):
    # Explicit art IDs were resolved from this MAP, never guessed from appearance.
    walls = [f"art/walls/{name}.frm" for name in
             ("ca063", "ca064", "ca013", "ca027", "ca011", "ca003", "ca007", "ca005")]
    rocks = ["art/scenery/rock03.frm", "art/scenery/rock06.frm"]
    floors = [f"art/tiles/{name}.frm" for name in
              ("cav1000", "cav1001", "cav1002", "cav1003", "cav3000", "cav4000", "cav4003", "cav4010")]
    selected = walls + rocks + floors
    used_objects = {obj["art"] for obj in info["objects"] if obj["art"]}
    visible_floor = {}
    for elevation, words in enumerate(info["tile_words"]):
        for cell, word in enumerate(words):
            index = word & 4095
            if not word & 0x1000 and index != 1:
                name = inspector.art_path(0x04000000 | index)
                if name != "art/tiles/grid001.frm":
                    visible_floor.setdefault(name, []).append({"elevation": elevation,
                                                               "cell": cell, "tile_art_id": index})
    for name in walls + rocks:
        if name not in used_objects:
            raise FormatError(f"Selected wall is not referenced by map: {name}")
    for name in floors:
        if name not in visible_floor:
            raise FormatError(f"Selected floor is not a visible non-default map tile: {name}")
    needed = {info["source"], "color.pal", "art/walls/walls.lst", "art/tiles/tiles.lst",
              "proto/walls/walls.lst", "art/scenery/scenery.lst", "proto/scenery/scenery.lst", *selected}
    reasons = {name: "Exact FID resolved from V13ENT.MAP objects via walls.lst" for name in walls}
    reasons.update({name: "Exact FID resolved from V13ENT.MAP objects via scenery.lst" for name in rocks})
    reasons.update({name: "Exact tile ID resolved from V13ENT.MAP floor block via tiles.lst" for name in floors})
    protos = {}
    for obj in info["objects"]:
        if obj["art"] in walls + rocks:
            proto = inspector.prototype(obj["pid"])
            protos[proto["pid"]] = proto
            needed.add(proto["path"])
    extracted = inspector.assets.extract(sorted(needed), output, reasons)
    source_records = {record["path"]: record for record in extracted}
    palette = palette_rgb(inspector.assets.read("color.pal"))
    records, first_frames = [], {}
    for name in selected:
        data = inspector.assets.read(name)
        meta, directions = decode_frm(data)
        if meta["frame_count"] != 1:
            raise FormatError(f"Expected static single-frame art: {name}")
        frame = directions[0][0]
        first_frames[name] = frame
        exports = export_frm(data, name, palette, output)
        indexed_name = "png/" + name + ".png"
        validate_png((output/indexed_name).read_bytes(), frame.width, frame.height, frame.pixels, 3)
        png, rgba = rgba_png(frame, palette)
        rgba_name = "rgba/" + name + ".png"
        target = write_bytes(output, rgba_name, png)
        validate_png(target.read_bytes(), frame.width, frame.height, rgba, 6)
        instances = [{key: obj[key] for key in ("offset", "id", "tile", "elevation", "fid", "pid", "frame", "rotation", "x", "y")}
                     for obj in info["objects"] if obj["art"] == name]
        records.append({"path": name, "source_sha256": hashlib.sha256(data).hexdigest(),
                        "source_archive": source_records[name]["archive"],
                        "source_archive_offset": source_records[name]["offset"],
                        "rgba_png": rgba_name, "rgba_png_sha256": hashlib.sha256(png).hexdigest(),
                        "indexed_png": indexed_name, "frame": 0, "direction": 0,
                        "width": frame.width, "height": frame.height,
                        "frame_shift_x": frame.shift_x, "frame_shift_y": frame.shift_y,
                        "frm": exports, "map_instances": instances,
                        "visible_floor_cells": visible_floor.get(name, [])})
    sheets = []
    for label, names, columns in (("walls-contact-original", walls, 4), ("rocks-contact-original", rocks, 2), ("floor-contact-original", floors, 4)):
        sheet, cells = make_sheet([first_frames[name] for name in names], palette, columns=columns)
        target = write_bytes(output, f"contact/{label}.png", sheet)
        for cell, name in zip(cells, names):
            cell["source"] = name
        sheets.append({"png": f"contact/{label}.png", "cells": cells,
                       "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
    manifest = {"map": {key: info[key] for key in ("source", "sha256", "size", "header", "root_object_count", "parsed_bytes")},
                "primary_wall": walls[0], "primary_floor": floors[0], "primary_img2img_candidate": rocks[0],
                "palette_source": "color.pal", "palette_sha256": source_records["color.pal"]["sha256"],
                "palette_conversion": "Original RGB6 channels << 2; invalid >63 triplets black, matching CE; no runtime lighting or palette cycling",
                "transparency": "Source palette index 0 -> alpha 0; all other pixels alpha 255; straight RGBA, no premultiplication",
                "processing": "Decode only. Original dimensions, indices and offsets preserved. No generation, resampling, filters or retouching. Contact sheets are a catalog, not connected map geometry.",
                "scope": "Selected static reference assets, not a complete playable map dependency package",
                "sources": extracted, "prototypes": sorted(protos.values(), key=lambda row: row["pid"]),
                "assets": records, "contact_sheets": sheets,
                "validation": {"map_parsed_to_eof": True, "root_count_matches": True,
                               "all_selected_assets_referenced_by_map": True,
                               "all_frm_declared_lengths_match": True,
                               "all_exported_individual_png_pixels_match_source": True}}
    write_json(output, "sample.json", manifest)
    print(json.dumps({"output": str(output.resolve()), "selected_assets": len(records),
                      "wall": {key: records[0][key] for key in ("path", "width", "height", "source_sha256")},
                      "rock": {key: records[len(walls)][key] for key in ("path", "width", "height", "source_sha256")},
                      "floor": {key: records[len(walls)+len(rocks)][key] for key in ("path", "width", "height", "source_sha256")}}))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", required=True, action="append", type=Path)
    p.add_argument("--map", default="maps/v13ent.map")
    p.add_argument("--output", type=Path)
    p.add_argument("--export-sample", action="store_true")
    args = p.parse_args()
    inspector = MapInspector(Assets(args.archive))
    info = inspector.parse(safe_name(args.map))
    if args.export_sample:
        if not args.output:
            p.error("--export-sample requires --output")
        export_sample(inspector, info, args.output)
        return
    rows = candidates(inspector, info)
    floor_rows = []
    for elevation, ids in enumerate(info["floor_ids"]):
        for index, count in sorted(Counter(ids).items()):
            name = inspector.art_path(0x04000000 | index)
            meta, directions = decode_frm(inspector.assets.read(name))
            frame = directions[0][0]
            floor_rows.append({"elevation": elevation, "tile_art_id": index,
                               "count": count, "path": name,
                               "width": frame.width, "height": frame.height,
                               "visible_flag_count": sum(1 for word in info["tile_words"][elevation]
                                                         if word & 4095 == index and not word & 0x1000),
                               "exclude_from_material_sample": index == 1 or name == "art/tiles/grid001.frm"})
    if args.output:
        write_json(args.output, "map.json", info)
        write_json(args.output, "candidates.json", {"static_objects": rows, "floor": floor_rows})
    print(json.dumps({"header": info["header"], "objects": info["root_object_count"],
                      "static_objects": rows, "floor": floor_rows}, indent=2))


if __name__ == "__main__":
    main()
