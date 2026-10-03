# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy>=1.24", "pillow>=10"]
# ///
"""Batch ROM atlas renderer. Run with uv run scripts/render_atlas.py.

Only writes manifest-designated PNGs and data/atlas_render_report.json.
Caches are built before the single thread pool starts; no subprocesses.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image
from atlas_object_sprites import render_object_layers
from atlas_runtime_layouts import resolve_layouts

VERSION = "mercury-rgb-atlas-2-native-layers"
BASE = 0x08000000


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def number(value):
    return int(value, 0) if isinstance(value, str) else int(value)


def address(value):
    return f"0x{number(value):08X}"


def output_path(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or path.suffix.lower() != ".png":
        raise ValueError(f"invalid output PNG path: {relative}")
    return path


def save_png(image, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    try:
        image.save(temp, format="PNG", compress_level=3)
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)
    return file_hash(path)


def reusable(previous, fingerprint, path, size):
    if (previous.get("fingerprint") != fingerprint
            or previous.get("status") not in ("ok", "partial")
            or previous.get("size") != list(size)
            or previous.get("mode") != "RGB" or not path.is_file()):
        return False
    try:
        if file_hash(path) != previous.get("png_sha256"):
            return False
        with Image.open(path) as image:
            if image.mode != "RGB" or image.size != tuple(size):
                return False
            image.verify()
        return True
    except (OSError, ValueError, SyntaxError):
        return False


class Renderer:
    def __init__(self, rom, research, tilesets, animations):
        self.rom = rom
        self.research = research
        self.tilesets = tilesets
        self.animations = animations
        self.sources = {}
        self.frames = {}
        self.pairs = {}
        self.metatile_tables = {}

    def read_rom(self, pointer, size):
        offset = number(pointer) - BASE
        if size < 0 or offset < 0 or offset + size > len(self.rom):
            raise ValueError(f"ROM range outside source: {pointer}, {size}")
        return self.rom[offset:offset + size]

    def lz77(self, pointer):
        offset = number(pointer)
        header = self.read_rom(offset, 4)
        if header[0] != 0x10:
            raise ValueError(f"not GBA LZ77 at {pointer}")
        size = int.from_bytes(header[1:4], "little")
        if not 0 < size <= 32 * 1024:
            raise ValueError(f"invalid tileset LZ77 output size: {size}")
        offset += 4
        result = bytearray()
        while len(result) < size:
            flags = self.read_rom(offset, 1)[0]
            offset += 1
            for bit in range(7, -1, -1):
                if len(result) == size:
                    break
                if flags & (1 << bit):
                    a, b = self.read_rom(offset, 2)
                    offset += 2
                    length = (a >> 4) + 3
                    distance = ((a & 15) << 8 | b) + 1
                    if distance > len(result):
                        raise ValueError("invalid LZ77 backward reference")
                    for _ in range(min(length, size - len(result))):
                        result.append(result[-distance])
                else:
                    result.extend(self.read_rom(offset, 1))
                    offset += 1
        return bytes(result)

    def source(self, key):
        if key in self.sources:
            return self.sources[key]
        meta = self.tilesets.get(key)
        result = {"meta": meta, "error": None}
        self.sources[key] = result
        try:
            if meta is None:
                raise ValueError(f"tileset metadata absent: {key}")
            if "error" in meta:
                raise ValueError(f"tileset metadata error: {meta['error']}")
            secondary = number(meta["is_secondary"]) == 1
            raw_path = self.research / meta["raw_tiles"] if meta.get("raw_tiles") else None
            if raw_path is not None and raw_path.is_file():
                raw = raw_path.read_bytes()
                method = "raw_tiles"
            elif number(meta["is_compressed"]):
                raw = self.lz77(meta["tiles"])
                method = "lz77"
            else:
                length = int(meta.get("tiles_decompressed_size",
                                      int(meta["tile_count_declared"]) * 32))
                raw = self.read_rom(meta["tiles"], length)
                method = "uncompressed"
            if "tiles_decompressed_size" in meta and len(raw) != int(meta["tiles_decompressed_size"]):
                raise ValueError("raw tile length disagrees with metadata")
            if not raw or len(raw) % 32:
                raise ValueError("empty or incomplete 4bpp tile source")
            # Never pad by reading the bytes following the declared source.
            count = len(raw) // 32
            palette_start = number(meta["palettes"]) + (0xE0 if secondary else 0)
            palette = self.read_rom(palette_start, 7 * 32)
            result.update(raw=raw, palette=palette,
                          secondary=secondary, count=count, method=method,
                          raw_sha256=hashlib.sha256(raw).hexdigest())
        except (OSError, ValueError, KeyError, TypeError) as exc:
            result["error"] = str(exc)
        return result

    def frame(self, pointer, size):
        key = (address(pointer), size)
        if key not in self.frames:
            self.frames[key] = self.read_rom(pointer, size)
        return self.frames[key]

    def metatile_table(self, pointer, count):
        key = (address(pointer), count)
        if key not in self.metatile_tables:
            raw = self.read_rom(pointer, count * 16)
            table = np.frombuffer(raw, dtype="<u2").reshape(count, 8)
            table.setflags(write=False)
            self.metatile_tables[key] = table
        return self.metatile_tables[key]

    def pair(self, keys):
        if keys in self.pairs:
            return self.pairs[keys]
        sources = [self.source(k) for k in keys]
        result = {"errors": [], "source_errors": []}
        self.pairs[keys] = result
        for key, source in zip(keys, sources):
            if source["error"]:
                result["source_errors"].append(f"{key}: {source['error']}")
        if result["source_errors"]:
            return result
        graphics = bytearray(1024 * 32)
        known_bytes = np.zeros(1024 * 32, dtype=np.bool_)
        palettes = bytearray(16 * 32)
        known_palette = np.zeros(16 * 32, dtype=np.bool_)
        descriptors = np.zeros((1024, 12), dtype=np.uint16)
        known_mt = np.zeros(1024, dtype=np.bool_)
        layer_types = np.zeros(1024, dtype=np.uint8)
        for source, base, slot, capacity, banks in zip(sources, (0, 640), (0, 7), (640, 384), (7, 6)):
            start = base * 32
            # Graphics capacity follows the caller's destination, not isSecondary.
            raw = source["raw"][:capacity * 32]
            graphics[start:start + len(raw)] = raw
            known_bytes[start:start + len(raw)] = True
            start = slot * 32
            pal = source["palette"][:banks * 32]
            palettes[start:start + len(pal)] = pal
            known_palette[start:start + len(pal)] = True
            if not source["secondary"]:
                palettes[start:start + 2] = b"\0\0"
            try:
                # Metatile IDs are partitioned by GetMetatile, independently of
                # the flag used to select the palette source offset.
                mts = self.metatile_table(source["meta"]["metatiles"], capacity)
                attrs = np.frombuffer(self.read_rom(source['meta']['metatile_attributes'], capacity * 4), dtype='<u4')
                types = ((attrs >> 28) & 7).astype(np.uint8)
                layer_types[base:base + capacity] = types
                # 09C8BDC0 reads 12 words for layer type 3, while the ID stride
                # remains 16 bytes at 0805A99C. The extra words overlap the next ID.
                for local_id in np.flatnonzero(types == 3):
                    extra = self.read_rom(number(source['meta']['metatiles']) + int(local_id) * 16 + 16, 8)
                    descriptors[base + int(local_id), 8:12] = np.frombuffer(extra, dtype='<u2')
            except (ValueError, KeyError, TypeError) as exc:
                result["source_errors"].append(str(exc))
                return result
            descriptors[base:base + len(mts), :8] = mts
            known_mt[base:base + len(mts)] = ~np.all(mts == 0xFFFF, axis=1) & (types <= 4)
        plans = []
        for key, source in zip(keys, sources):
            table = self.animations.get(key)
            if table is None and number(source["meta"].get("callback", 0)):
                result["errors"].append(f"animation plan absent: {key}")
            plans.append(table.get("plan", {}) if table else {})
        for counter in (*range(1, 256), 0):
            for key, plan in zip(keys, plans):
                for write in plan.get(str(counter), []):
                    try:
                        if "error" in write:
                            raise ValueError(str(write["error"]))
                        size = int(write["len_bytes"])
                        start = int(write["dest_tile"]) * 32
                        kind = write["path"]
                        if kind == "tilemap":
                            target, valid = graphics, known_bytes
                        elif kind == "palette":
                            target, valid = palettes, known_palette
                        else:
                            raise ValueError(f"unknown animation path: {kind}")
                        if size <= 0 or start < 0 or start + size > len(target):
                            raise ValueError(f"animation destination outside BG {kind} memory")
                        frame = self.frame(write["src"], size)
                        target[start:start + size] = frame
                        valid[start:start + size] = True
                    except (ValueError, KeyError, TypeError) as exc:
                        result["errors"].append(f"{key} tick {counter}: {exc}")
        tile_bytes = np.frombuffer(graphics, dtype=np.uint8).reshape(1024, 8, 4)
        tiles = np.empty((1024, 8, 8), dtype=np.uint8)
        tiles[:, :, 0::2] = tile_bytes & 15
        tiles[:, :, 1::2] = tile_bytes >> 4
        values = np.frombuffer(palettes, dtype="<u2").reshape(16, 16)
        rgb = np.stack([(values >> shift & 31) * 255 // 31 for shift in (0, 5, 10)], axis=-1).astype(np.uint8)
        known_tiles = known_bytes.reshape(1024, 32).all(axis=1)
        known_colors = known_palette.reshape(16, 16, 2).all(axis=2)
        atlas = np.empty((1024, 16, 16, 3), dtype=np.uint8)
        atlas[:] = rgb[0, 0]
        foreground = np.zeros((1024, 16, 16), dtype=np.bool_)
        missing_by_mt = []
        missing_palette_by_mt = []
        for mid, words in enumerate(descriptors):
            missing = set()
            missing_palette = set()
            if known_mt[mid]:
                layer = int(layer_types[mid])
                if layer in (0, 1):
                    words = np.concatenate((np.full(4, 0x3014, dtype=np.uint16), words[:8]))
                    foreground_start = 8
                elif layer == 3:
                    foreground_start = 8
                else:
                    words = words[:8]
                    foreground_start = 4 if layer == 4 else None
                for index, word in enumerate(words):
                    word = int(word)
                    tid, slot = word & 1023, word >> 12
                    if not known_tiles[tid]:
                        missing.add(tid)
                        continue
                    pixels = tiles[tid]
                    if word & 0x400:
                        pixels = pixels[:, ::-1]
                    if word & 0x800:
                        pixels = pixels[::-1, :]
                    opaque = pixels != 0
                    present = known_colors[slot, pixels]
                    if np.any(opaque & ~present):
                        missing_palette.add(slot)
                    y, x = ((index % 4) // 2) * 8, (index % 2) * 8
                    target = atlas[mid, y:y + 8, x:x + 8]
                    np.copyto(target, rgb[slot, pixels], where=(opaque & present)[..., None])
                    if foreground_start is not None and index >= foreground_start:
                        foreground[mid, y:y + 8, x:x + 8] |= opaque & present
            missing_by_mt.append(frozenset(missing))
            missing_palette_by_mt.append(frozenset(missing_palette))
        for array in (atlas, descriptors, known_mt, known_tiles, foreground, layer_types):
            array.setflags(write=False)
        result.update(atlas=atlas, descriptors=descriptors, known_mt=known_mt, foreground=foreground, layer_types=layer_types,
                      missing_by_mt=tuple(missing_by_mt),
                      missing_palette_by_mt=tuple(missing_palette_by_mt))
        result["errors"] = sorted(set(result["errors"]))
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    default_guide = Path(__file__).resolve().parents[1]
    parser.add_argument("--guide", type=Path, default=default_guide)
    parser.add_argument("--research", type=Path)
    parser.add_argument("--rom", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    guide = args.guide.resolve()
    research = (args.research or guide.parent / "maps_research").resolve()
    manifest = load_json(args.manifest or guide / "data/atlas_manifest.json")
    headers = load_json(research / "out/maps/headers.json")
    tileset_document = load_json(research / "out/tilesets/manifest.json")
    animation_document = load_json(research / "out/tilesets/anim_tables.json")
    rom_path = args.rom or guide.parent.parent / tileset_document["rom"]
    rom = rom_path.read_bytes()  # Exactly one ROM file read per invocation.
    rom_sha = hashlib.sha256(rom).hexdigest()
    for label, document in (("headers", headers), ("tilesets", tileset_document)):
        if document.get("sha256") != rom_sha:
            raise ValueError(f"{label} ROM SHA256 does not match source ROM")
    renderer = Renderer(rom, research, tileset_document["tilesets"], animation_document["tables"])
    header_maps = {f"{m['group']}:{m['num']}": m for m in headers["maps"]}
    selected_layouts, layout_resolution = resolve_layouts(rom, headers['maps'])
    report_path = guide / "data/atlas_render_report.json"
    previous = {}
    if report_path.is_file() and not args.force:
        try:
            previous = load_json(report_path)
        except (OSError, ValueError):
            pass
    jobs = {}
    map_jobs = {}
    invalid = {}
    layout_keys = set()
    for map_id, item in manifest["maps"].items():
        try:
            layout = item["layout"]
            width, height = int(item["width"]), int(item["height"])
            if width <= 0 or height <= 0 or (width, height) != (int(layout["width"]), int(layout["height"])):
                raise ValueError("manifest/layout dimensions disagree or are invalid")
            if map_id not in header_maps or layout != selected_layouts.get(map_id):
                raise ValueError("manifest layout does not match live ROM layout table")
            pair = (address(layout["primary_tileset"]), address(layout["secondary_tileset"]))
            layout_key = digest([address(layout["map"]), width, height, pair])
            layout_keys.add(layout_key)
            image = item["image"]
            path = output_path(guide, image)
            if image in jobs and jobs[image]["layout_key"] != layout_key:
                raise ValueError("one image path assigned to different layouts")
            jobs.setdefault(image, dict(image=image, path=path, layout=layout, pair=pair,
                                        width=width, height=height, layout_key=layout_key))
            map_jobs[map_id] = image
        except (ValueError, KeyError, TypeError) as exc:
            invalid[map_id] = dict(image=item.get("image"), status="unavailable", missing_tiles=None,
                                   size=None, mode=None, errors=[str(exc)], reused=False)
    for unavailable in invalid.values():
        image = unavailable.get("image")
        if image and image not in jobs:
            try:
                output_path(guide, image).unlink(missing_ok=True)
            except ValueError:
                pass  # Never delete a path outside the guide output tree.
    # Prebuild every source/frame/pair once, entirely before worker submission.
    for job in jobs.values():
        renderer.pair(job["pair"])
    pair_fingerprints = {}
    for pair in renderer.pairs:
        pair_fingerprints[pair] = digest({
            "version": VERSION, "rom_sha256": rom_sha,
            "tilesets": [renderer.sources[k]["meta"] for k in pair],
            "raw_sha256": [renderer.sources[k].get("raw_sha256") for k in pair],
            "source_errors": [renderer.sources[k]["error"] for k in pair],
            "animation_model": animation_document.get("model"),
            "animation": [renderer.animations.get(k) for k in pair],
            "semantics": "ticks=1..255,0;primary-then-secondary;secondary-pal+E0;low-nibble-left;RGB255/31;transparent-zero;black-initial-BG0",
        })
        primary_meta = renderer.sources[pair[0]]["meta"]
        secondary_meta = renderer.sources[pair[1]]["meta"]
        if ((primary_meta and number(primary_meta["is_secondary"]) == 1)
                or (secondary_meta and number(secondary_meta["is_secondary"]) != 1)):
            # Keep the previous normal-role digest exactly stable: only the
            # formerly rejected combinations need this semantic invalidation.
            pair_fingerprints[pair] = digest([
                pair_fingerprints[pair],
                "caller-roles-v1:tiles640/384;metatiles640/384;palbanks7/6;flag1-src+E0;flag0-dest-first-color-black",
            ])
        erased = np.flatnonzero(~renderer.pairs[pair].get("known_mt", np.ones(1024, dtype=bool))).tolist()
        if erased:
            pair_fingerprints[pair] = digest([pair_fingerprints[pair], "reject-ff-metatiles-v1", erased])
    old_images = {r.get("image"): r for r in previous.get("maps", {}).values() if r.get("image")}

    def render_map(job):
        path = job["path"]
        width, height = job["width"], job["height"]
        pair = renderer.pairs[job["pair"]]
        fingerprint = digest([VERSION, rom_sha, job["layout"], pair_fingerprints[job["pair"]]])
        result = dict(image=job["image"], fingerprint=fingerprint, layout_key=job["layout_key"],
                      size=[width * 16, height * 16], mode="RGB", reused=False,
                      status="unavailable", missing_tiles=None)
        try:
            if pair["source_errors"]:
                raise ValueError("; ".join(pair["source_errors"]))
            cells = renderer.read_rom(job["layout"]["map"], width * height * 2)
            mids = (np.frombuffer(cells, dtype="<u2") & 1023).reshape(height, width)
            used = np.unique(mids)
            missing = sorted(set().union(*(pair["missing_by_mt"][i] for i in used)))
            missing_palettes = sorted(set().union(*(pair["missing_palette_by_mt"][i] for i in used)))
            missing_mt = [int(i) for i in used if not pair["known_mt"][i]]
            result.update(missing_tiles=len(missing), missing_tile_ids=missing,
                          missing_metatiles=missing_mt, missing_palette_slots=missing_palettes,
                          errors=pair["errors"],
                          status="partial" if missing or missing_mt or missing_palettes or pair["errors"] else "ok")
            if len(missing_mt) == len(used):
                raise ValueError("All referenced metatile descriptors are erased (0xFFFF); ROM source cannot render this layout")
            old = old_images.get(job["image"], {})
            if reusable(old, fingerprint, path, result["size"]):
                result.update(reused=True, png_sha256=old["png_sha256"])
                return result
            pixels = pair["atlas"][mids].transpose(0, 2, 1, 3, 4).reshape(height * 16, width * 16, 3)
            with Image.fromarray(pixels) as image:
                result["png_sha256"] = save_png(image, path)
        except (OSError, ValueError, KeyError, TypeError, MemoryError) as exc:
            result.update(status="unavailable", errors=[str(exc)], mode=None)
            # A failed new render must not leave a stale PNG pretending to be current.
            path.unlink(missing_ok=True)
        return result

    def render_overview(entry, map_results):
        region_id, region = entry
        path = output_path(guide, region["overview"])
        native = (int(region["width"]) * 16, int(region["height"]) * 16)
        if min(native) <= 0:
            raise ValueError(f"invalid region dimensions: {region_id}")
        scale = max(1, math.ceil(max(native) / 4096))
        size = tuple(math.ceil(n / scale) for n in native)
        members = [(mid, manifest["maps"][mid], map_results[mid]) for mid in region["maps"]]
        fingerprint = digest([VERSION, region, [(mid, m.get("origin"), r.get("fingerprint"),
                                                r.get("status"), r.get("png_sha256")) for mid, m, r in members]])
        fingerprint = digest([fingerprint, [(mid, object_report['maps'][mid].get('fingerprint'), m.get('objects_image')) for mid, m, _ in members]])
        available = [(mid, m, r) for mid, m, r in members if r["status"] != "unavailable"]
        result = dict(image=region["overview"], fingerprint=fingerprint, size=list(size),
                      native_size=list(native), scale=scale, mode="RGB", reused=False,
                      status="ok" if all(r["status"] == "ok" for _, _, r in members) else "partial",
                      unavailable_maps=[mid for mid, _, r in members if r["status"] == "unavailable"])
        if not available:
            path.unlink(missing_ok=True)
            result.update(status="unavailable", mode=None, errors=["no available base maps"])
            return region_id, result
        if len(members) == 1:
            _, _, rendered = available[0]
            result.update(image=rendered['image'], size=rendered['size'], scale=1,
                          png_sha256=rendered['png_sha256'], reused=True, shared_base=True)
            return region_id, result
        old = previous.get("regions", {}).get(region_id, {})
        if reusable(old, fingerprint, path, size):
            result.update(reused=True, png_sha256=old["png_sha256"])
            return region_id, result
        try:
            # Only allocate the <=4096 preview, never a native-size world canvas.
            with Image.new("RGB", size, (0, 0, 0)) as canvas:
                for _, item, rendered in available:
                    ox, oy = (int(v) * 16 for v in item["origin"])
                    w, h = rendered["size"]
                    left, top = ox // scale, oy // scale
                    right, bottom = math.ceil((ox + w) / scale), math.ceil((oy + h) / scale)
                    with Image.open(output_path(guide, rendered["image"])) as image:
                        # Affine sampling preserves the common integer-scale grid,
                        # including origins not divisible by the overview scale.
                        with image.transform((right - left, bottom - top), Image.Transform.AFFINE,
                                             (scale, 0, left * scale - ox,
                                              0, scale, top * scale - oy),
                                             resample=Image.Resampling.NEAREST) as preview:
                            canvas.paste(preview, (left, top))
                    if item.get('objects_image'):
                        with Image.open(output_path(guide, item['objects_image'])) as overlay:
                            with overlay.transform((right - left, bottom - top), Image.Transform.AFFINE,
                                                   (scale, 0, left * scale - ox, 0, scale, top * scale - oy),
                                                   resample=Image.Resampling.NEAREST) as preview:
                                canvas.paste(preview, (left, top), preview)
                result["png_sha256"] = save_png(canvas, path)
        except (OSError, ValueError, KeyError, TypeError, MemoryError) as exc:
            path.unlink(missing_ok=True)
            result.update(status="unavailable", mode=None, errors=[str(exc)])
        return region_id, result

    def foreground_for_map(mid):
        item = manifest['maps'][mid]
        width, height = item['width'], item['height']
        job = jobs.get(map_jobs.get(mid))
        if job is None or renderer.pairs[job['pair']]['source_errors']:
            return np.zeros((height * 16, width * 16), dtype=np.bool_)
        cells = renderer.read_rom(item['layout']['map'], width * height * 2)
        mids = (np.frombuffer(cells, dtype='<u2') & 1023).reshape(height, width)
        return renderer.pairs[job['pair']]['foreground'][mids].transpose(0, 2, 1, 3).reshape(height * 16, width * 16)

    object_report = render_object_layers(guide, rom, manifest, foreground_for_map)
    workers = min(6, max(1, args.workers))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        images = {r["image"]: r for r in pool.map(render_map, jobs.values())}
        map_results = {mid: dict(images[image]) for mid, image in map_jobs.items()}
        map_results.update(invalid)
        for mid, result in map_results.items():
            result['object_errors'] = object_report['maps'][mid]['errors']
            result['objects_count'] = manifest['maps'][mid].get('objects_count', 0)
        # Only multi-map regions write overviews; single-map regions reuse base files.
        region_entries = list(manifest["regions"].items())
        overview_paths = [output_path(guide, r['overview']) for _, r in region_entries if len(r['maps']) > 1]
        if len(overview_paths) != len(set(overview_paths)) or set(overview_paths) & {j["path"] for j in jobs.values()}:
            raise ValueError("overview destinations collide with another output")
        regions = dict(pool.map(lambda entry: render_overview(entry, map_results), region_entries))
    report = dict(version=VERSION, rom_sha256=rom_sha, maps=map_results, regions=regions,
                  unique_layouts=len(layout_keys), unique_images=len(jobs),
                  cache_pairs=len(renderer.pairs), cache_sources=len(renderer.sources),
                  cache_frames=len(renderer.frames), overviews=len(regions), workers=workers,
                  shared_overview_base_images=sum(r.get('shared_base', False) for r in regions.values()),
                  rendered_overview_images=sum(r['status'] != 'unavailable' and not r.get('shared_base', False) and not r['reused'] for r in regions.values()),
                  rendered_images=sum(r["status"] != "unavailable" and not r["reused"] for r in images.values()),
                  reused_images=sum(r["reused"] for r in images.values()),
                  unavailable_maps=sum(r["status"] == "unavailable" for r in map_results.values()),
                  partial_maps=sum(r["status"] == "partial" for r in map_results.values()),
                  sources={key: {field: source.get(field) for field in
                                 ("error", "method", "count", "raw_sha256")} for key, source in renderer.sources.items()})
    report['objects'] = object_report['summary']
    report['runtime_layout_changes'] = layout_resolution['changed_count']
    manifest_path = args.manifest or guide / 'data/atlas_manifest.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding='utf-8')
    report_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = report_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(report_path)
    print(json.dumps({k: v for k, v in report.items() if k not in ("maps", "regions", "sources")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
