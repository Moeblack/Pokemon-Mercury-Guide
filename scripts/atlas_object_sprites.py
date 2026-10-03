"""Render verified 64x64, unconditional fixed objects, not all NPCs/events."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import struct

import numpy as np
from PIL import Image


VERSION = "large-fixed-objects-v2-native-foreground"
BASE = 0x08000000
EVENT_FIELDS = ("index", "local_id", "graphics_id", "x", "y", "movement_type", "flag_id")


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode("utf-8")).hexdigest()


def render_object_layers(guide: Path, rom: bytes, manifest: dict, foreground_provider=None) -> dict:
    """Write transparent object PNGs/report and augment manifest in place.

    Width/height and positions in the input manifest/events are map-tile units.
    All ROM accesses are checked GBA addresses; unsupported graphics are omitted.
    """
    guide = Path(guide).resolve()
    object_dir = guide / "maps" / "objects"
    data_dir = guide / "data"
    # Refuse redirected output directories, including symlinks outside the guide.
    for directory in (object_dir, data_dir):
        if directory.resolve() != directory:
            raise ValueError(f"redirected output directory: {directory}")
    report_path = data_dir / "atlas_objects_report.json"
    if report_path.is_symlink():
        raise ValueError("object report must not be a symlink")
    events = json.loads((guide.parent / "maps_research/out/events/events.json")
                        .read_text(encoding="utf-8"))["maps"]
    try:
        previous = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previous = {}
    if not isinstance(previous, dict) or previous.get("version") != VERSION:
        previous = {}
    old_maps = previous.get("maps", {})
    if not isinstance(old_maps, dict):
        old_maps = {}
    rom_sha = hashlib.sha256(rom).hexdigest()
    report = {"version": VERSION, "rom_sha256": rom_sha,
              "scope": "64x64 fixed objects, movement 0/7/8/9/10, flag_id 0 only",
              "maps": {}, "errors": []}

    def read(address, size):
        offset = address - BASE
        if size < 0 or offset < 0 or offset > len(rom) - size:
            raise ValueError(f"ROM range out of bounds: 0x{address:08X}+{size}")
        return rom[offset:offset + size]

    def u16(address):
        return struct.unpack("<H", read(address, 2))[0]

    def u32(address):
        return struct.unpack("<I", read(address, 4))[0]

    bank0 = None
    palette_addresses = {}
    palette_error = None
    try:
        banks = u32(0x09D0D328)
        bank0 = u32(banks)
        read(bank0, 240 * 4)
    except ValueError as exc:
        report["errors"].append({"stage": "graphics_bank", "error": str(exc)})
    try:
        table = u32(0x0805F4D8)
        for index in range(8192):
            record = read(table + index * 8, 8)
            colors, tag = struct.unpack_from("<IH", record)
            if tag == 0xFFFF:
                break
            palette_addresses.setdefault(tag, colors)
        else:
            raise ValueError("palette table has no terminator within 8192 records")
    except ValueError as exc:
        palette_error = str(exc)
        report["errors"].append({"stage": "palette_table", "error": palette_error})

    graphics_cache = {}
    palette_cache = {}
    sprite_cache = {}

    def graphics(gid):
        if gid not in graphics_cache:
            try:
                if bank0 is None:
                    raise ValueError("graphics bank unavailable")
                address = u32(bank0 + gid * 4)
                record = read(address, 36)
                width, height = struct.unpack_from("<hh", record, 8)
                graphics_cache[gid] = (width, height, struct.unpack_from("<H", record, 2)[0],
                                       struct.unpack_from("<I", record, 24)[0],
                                       struct.unpack_from("<I", record, 28)[0])
            except ValueError as exc:
                graphics_cache[gid] = str(exc)
        result = graphics_cache[gid]
        if isinstance(result, str):
            raise ValueError(result)
        return result

    def palette(tag):
        if tag not in palette_cache:
            if palette_error:
                raise ValueError(palette_error)
            if tag not in palette_addresses:
                raise ValueError(f"missing palette tag 0x{tag:04X}")
            words = np.frombuffer(read(palette_addresses[tag], 32), dtype="<u2")
            rgba = np.empty((16, 4), dtype=np.uint8)
            for channel, shift in enumerate((0, 5, 10)):
                rgba[:, channel] = ((words >> shift) & 31) * 255 // 31
            rgba[:, 3] = 255
            rgba[0] = 0
            palette_cache[tag] = rgba
        return palette_cache[tag]

    def sprite(gid, movement):
        facing = read(0x0839FD5D + movement, 1)[0]
        if facing not in (1, 2, 3, 4):
            raise ValueError(f"unsupported facing {facing} for movement {movement}")
        anim = facing - 1
        key = (gid, anim)
        if key not in sprite_cache:
            try:
                width, height, tag, anims, images = graphics(gid)
                if (width, height) != (64, 64):
                    raise ValueError(f"unexpected sprite dimensions {width}x{height}")
                command = u32(anims + anim * 4)
                frame, flags = struct.unpack("<HH", read(command, 4))
                if frame >= 0xFFFD:
                    raise ValueError(f"animation begins with control command 0x{frame:04X}")
                data, size = struct.unpack_from("<IH", read(images + frame * 8, 8))
                if size != 2048:
                    raise ValueError(f"expected raw 2048-byte frame, got {size}")
                raw = np.frombuffer(read(data, size), dtype=np.uint8).reshape(64, 8, 4)
                tiles = np.empty((64, 8, 8), dtype=np.uint8)
                tiles[:, :, 0::2] = raw & 15
                tiles[:, :, 1::2] = raw >> 4
                indices = tiles.reshape(8, 8, 8, 8).transpose(0, 2, 1, 3).reshape(64, 64)
                pixels = palette(tag)[indices]
                if flags & 0x40:
                    pixels = pixels[:, ::-1]
                if flags & 0x80:
                    pixels = pixels[::-1]
                sprite_cache[key] = (Image.fromarray(np.ascontiguousarray(pixels)), frame, tag, anim)
            except ValueError as exc:
                sprite_cache[key] = str(exc)
        result = sprite_cache[key]
        if isinstance(result, str):
            raise ValueError(result)
        return result

    jobs = []
    for mid, item in manifest["maps"].items():
        item.pop("objects_image", None)
        item["objects_count"] = 0
        result = {"objects": [], "conditional_skipped": [], "errors": [], "reused": False}
        report["maps"][mid] = result
        try:
            if not re.fullmatch(r"[0-9]+:[0-9]+", mid):
                raise ValueError(f"invalid map id: {mid}")
            width, height = int(item["width"]), int(item["height"])
            if width <= 0 or height <= 0:
                raise ValueError("nonpositive map dimensions")
            selected = [{field: event.get(field, index if field == "index" else None)
                         for field in EVENT_FIELDS}
                        for index, event in enumerate(events.get(mid, {}).get("objects", []))]
            fingerprint = _digest([VERSION, rom_sha, foreground_provider is not None,
                                   mid, width, height, selected])
            result["fingerprint"] = fingerprint
            relative = f"maps/objects/{mid.replace(':', '_')}.png"
            path = guide / relative
            if path.is_symlink():
                raise ValueError(f"object image must not be a symlink: {relative}")
            old = old_maps.get(mid, {})
            if (isinstance(old, dict) and old.get("fingerprint") == fingerprint
                    and not old.get("errors") and not report["errors"]
                    and old.get("objects") and old.get("image") == relative and path.is_file()):
                result.update(old)
                result["reused"] = True
                item["objects_image"] = relative
                item["objects_count"] = len(result["objects"])
                continue
            layers = []
            for event in selected:
                try:
                    gid = int(event["graphics_id"])
                    if not 0 <= gid < 240:
                        continue
                    w, h, tag, _, _ = graphics(gid)
                    if (w, h) != (64, 64):
                        continue
                    x, y = int(event["x"]), int(event["y"])
                    movement, flag = int(event["movement_type"]), int(event["flag_id"])
                    info = {"local_id": event["local_id"], "index": event["index"],
                            "gfx": gid, "x": x, "y": y, "movement": movement,
                            "frame": None, "palette": tag}
                    if flag != 0:
                        result["conditional_skipped"].append(dict(info, flag_id=flag))
                        continue
                    if movement not in (0, 7, 8, 9, 10) or not (0 <= x < width and 0 <= y < height):
                        continue
                    image, frame, tag, anim = sprite(gid, movement)
                    info.update(frame=frame, palette=tag, anim=anim)
                    layers.append((y, int(event["index"]), image, x * 16 + 8 - w // 2,
                                   (y + 1) * 16 - h, info))
                except (ValueError, TypeError, KeyError) as exc:
                    result["errors"].append({"local_id": event["local_id"],
                                             "gfx": event["graphics_id"], "error": str(exc)})
            layers.sort(key=lambda layer: (layer[0], layer[1]))
            if layers:
                result["objects"] = [layer[5] for layer in layers]
                jobs.append((mid, width, height, relative, path, layers))
        except (ValueError, TypeError, KeyError) as exc:
            result["errors"].append({"error": str(exc)})

    def save(job):
        mid, width, height, relative, path, layers = job
        try:
            with Image.new("RGBA", (width * 16, height * 16), (0, 0, 0, 0)) as canvas:
                for _, _, image, left, top, _ in layers:
                    canvas.alpha_composite(image, dest=(left, top))
                if foreground_provider is not None:
                    mask = foreground_provider(mid)
                    if mask.dtype != np.bool_ or mask.shape != (height * 16, width * 16):
                        raise ValueError("foreground mask must be a map-sized boolean array")
                    pixels = np.array(canvas, dtype=np.uint8, copy=True)
                    pixels[mask, 3] = 0
                    with Image.fromarray(pixels) as masked:
                        masked.save(path, format="PNG", compress_level=3)
                else:
                    canvas.save(path, format="PNG", compress_level=3)
            return mid, relative, None
        except (OSError, ValueError, MemoryError) as exc:
            return mid, relative, str(exc)

    if jobs:
        object_dir.mkdir(parents=True, exist_ok=True)
        with ThreadPoolExecutor(max_workers=min(6, len(jobs))) as pool:
            for mid, relative, error in pool.map(save, jobs):
                result = report["maps"][mid]
                if error is not None:
                    result["errors"].append({"stage": "png", "error": error})
                    result["objects"] = []
                else:
                    result["image"] = relative
                    manifest["maps"][mid]["objects_image"] = relative
                    manifest["maps"][mid]["objects_count"] = len(result["objects"])
    records = list(report["maps"].values())
    unique = {(obj["gfx"], obj["anim"]) for row in records for obj in row["objects"]}
    report["summary"] = {
        "image_maps": sum(bool(row.get("image")) for row in records),
        "objects": sum(len(row["objects"]) for row in records),
        "unique_sprites": len(unique),
        "errors": len(report["errors"]) + sum(len(row["errors"]) for row in records),
        "conditional_skipped": sum(len(row["conditional_skipped"]) for row in records),
    }
    report["fingerprint"] = _digest([VERSION, rom_sha, foreground_provider is not None,
                                    {mid: row.get("fingerprint") for mid, row in report["maps"].items()}])
    data_dir.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
