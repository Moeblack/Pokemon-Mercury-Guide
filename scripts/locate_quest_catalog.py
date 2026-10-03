#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Locate + extract the sidequest catalog (read-only data extraction).

Stage 1 (locate): encode 红色火球之谜, find ROM occurrences + 32-bit LE refs,
dump +/-128 hex  ->  player_guide/data/quest_catalog_candidates.json

Stage 2 (extract): read the two confirmed layouts and merge descriptions:
  * current  candidate: anchor 0xE3B028, stride 20
      u32 title_ptr, u32 desc_ptr, u16 unknown, u16 accept_flag,
      u16 complete_flag, u8 map_group, u8 map_num, 4 tail bytes
  * legacy   table: anchor 0xE39444, stride 16
      u32 title_ptr, u32 desc_ptr, u16 +8, u16 +10 (constant 0x1400),
      u16 +12 complete_flag, u16 +14
Boundaries are data-driven: a row is valid iff BOTH first two pointers are in
ROM range AND both strings decode fully with the wiki charmap up to 0xFF.
No table length is forced to 97; no quest flow is inferred.
  ->  player_guide/data/quest_catalog.json
"""
import hashlib
import json
import os
import struct
from datetime import datetime, timezone

R = r"C:/Users/Moeblack/Downloads/宝可梦水银/解包研究"
G = os.path.join(R, "player_guide")
ROM_PATH = r"C:/Users/Moeblack/Downloads/宝可梦水银/宝可梦水银FC~致150年后的你 Version 1.1 (1).gba"
CHARMAP = os.path.join(R, "out", "charmap.json")
CAND_OUT = os.path.join(G, "data", "quest_catalog_candidates.json")
CATALOG_OUT = os.path.join(G, "data", "quest_catalog.json")

QUEST_NAME = "红色火球之谜"
NEW_ANCHOR, NEW_STRIDE = 0xE3B028, 20
OLD_ANCHOR, OLD_STRIDE = 0xE39444, 16
ROM_BASE = 0x08000000


def load_rom():
    with open(ROM_PATH, "rb") as f:
        return f.read()


def load_charmap():
    with open(CHARMAP, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------- stage 1
def encode_name(cm, name):
    inv = {}
    for k, v in cm.items():
        inv.setdefault(v, []).append(k)
    per_char, ambiguous = {}, {}
    for ch in name:
        codes = sorted(c for c in inv.get(ch, []) if len(c) == 4)
        per_char[ch] = codes
        if len(codes) != 1:
            ambiguous[ch] = codes
    be = bytearray()
    for ch in name:
        if len(per_char[ch]) == 1:
            c = per_char[ch][0]
            be += bytes([int(c[0:2], 16), int(c[2:4], 16)])
    return per_char, ambiguous, bytes(be)


def find_all(hay, needle):
    out, i = [], hay.find(needle)
    while i != -1:
        out.append(i)
        i = hay.find(needle, i + 1)
    return out


def hex_block(rom, center, radius=128):
    lo, hi = max(0, center - radius), min(len(rom), center + radius)
    lines = ["%08X  %s" % (o, rom[o:o + 16].hex(" ")) for o in range(lo, hi, 16)]
    return {"range": [hex(lo), hex(hi - 1)], "text": "\n".join(lines)}


def stage1(rom, cm):
    per_char, ambiguous, pattern = encode_name(cm, QUEST_NAME)
    hits_be = find_all(rom, pattern)
    swapped = bytearray()
    for i in range(0, len(pattern), 2):
        swapped += bytes([pattern[i + 1], pattern[i]])
    hits_le = find_all(rom, bytes(swapped))
    hits, refs = [], []
    for h in hits_be:
        addr = ROM_BASE + h
        ref_offs = find_all(rom, addr.to_bytes(4, "little"))
        hits.append({
            "rom_offset": hex(h), "rom_addr": hex(addr),
            "string_bytes_hex": pattern.hex(),
            "u32_le_pointer_ref_offsets": [hex(r) for r in ref_offs],
            "u32_le_pointer_ref_count": len(ref_offs),
            "hex_pm128": hex_block(rom, h),
        })
        for r in ref_offs:
            refs.append({
                "hit_rom_offset": hex(h), "hit_rom_addr": hex(addr),
                "ref_rom_offset": hex(r), "ref_rom_addr": hex(ROM_BASE + r),
                "ref_bytes_le": rom[r:r + 4].hex(" "),
                "ref_hex_pm128": hex_block(rom, r),
            })
    return {
        "generated_by": "player_guide/scripts/locate_quest_catalog.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "Locate ROM strings + 32-bit LE pointer refs for the sidequest catalog; Main chooses the structure.",
        "rom": {"path": ROM_PATH, "size": len(rom), "size_hex": hex(len(rom)),
                "sha256": hashlib.sha256(rom).hexdigest()},
        "reference_notes": {
            "file": "reference/azoth-wiki/docs/news/index.md",
            "lines": {"70": "- 97个支线任务",
                      "10": "2. 完成阿球的支线任务后改为传送回满金市，避免导致后续 CosPlay 大会支线时序错误",
                      "20": "12. 精灵爷爷的支线去除了徽章检测，一开始就可以领取通信电缆，以防后面忘记",
                      "193": "支线设计沿用了《Z-A》/《究极日月》…充实了城镇里的每一个支线和微小事件"},
            "claim": "官方新闻宣称 97 个支线任务"},
        "search_string": QUEST_NAME,
        "encoding": {
            "source": "out/charmap.json",
            "structure": "2-byte CJK codes, lead byte in 0x01-0x1E, stored big-endian (lead,trail)",
            "corroboration": "maps_research/out/scripts/text.json encoding note",
            "per_char_codes": per_char, "ambiguous": ambiguous},
        "rom_pattern_big_endian_hex": pattern.hex(),
        "rom_pattern_little_endian_hex": bytes(swapped).hex(),
        "hits": hits, "pointer_ref_slots": refs,
        "counts": {"big_endian_hits": len(hits_be), "little_endian_hits": len(hits_le),
                   "pointer_ref_slots": len(refs)},
        "old_text_json": {
            "file": "maps_research/out/scripts/text.json", "count": 7513,
            "contains_quest_name": False,
            "note": "name absent from decoded script-text dump (3 copies checked)"},
        "code_research_entry": {"quest_table_doc_filename": None,
                                "note": "no filename in code_research mentions quest/任务/支线; MANIFEST.md index-only"},
    }


# ---------------------------------------------------------------- stage 2
def make_decoder(rom, cm):
    leads = set(int(k[:2], 16) for k in cm if len(k) == 4)
    soft = {0xFA: "\\l", 0xFB: "\\p", 0xFE: "\\n"}

    def dec(ptr):
        if not (ROM_BASE <= ptr < ROM_BASE + len(rom)):
            return None
        i, out, n = ptr - ROM_BASE, [], 0
        while i < len(rom) and n < 4000:
            b = rom[i]
            n += 1
            if b == 0xFF:
                return "".join(out)
            if b in soft:
                out.append(soft[b]); i += 1; continue
            if b in (0xFC, 0xFD, 0xF8, 0xF9):
                return None  # unknown parameter count -> treat as stop
            if b in leads:
                code = rom[i:i + 2].hex().upper()
                if code in cm:
                    out.append(cm[code]); i += 2; continue
                return None
            h = "%02X" % b
            if h in cm:
                out.append(cm[h]); i += 1; continue
            return None
        return None
    return dec


def read_new_row(rom, dec, r):
    t, d = struct.unpack_from("<II", rom, r)
    unk, acc, comp = struct.unpack_from("<HHH", rom, r + 8)
    title, desc = dec(t), dec(d)
    if title is None or desc is None:
        return None
    return {"row_offset": hex(r), "title": title, "title_address": hex(t),
            "description": desc, "description_address": hex(d),
            "unknown_u16": unk, "unknown_u16_hex": "0x%04X" % unk,
            "accept_flag": acc, "accept_flag_hex": "0x%04X" % acc,
            "complete_flag": comp, "complete_flag_hex": "0x%04X" % comp,
            "map_group": rom[r + 14], "map_num": rom[r + 15],
            "tail_hex": rom[r + 16:r + 20].hex(" ")}


def read_old_row(rom, dec, r):
    t, d = struct.unpack_from("<II", rom, r)
    f8, f10, comp, f14 = struct.unpack_from("<HHHH", rom, r + 8)
    title, desc = dec(t), dec(d)
    if title is None or desc is None:
        return None
    return {"row_offset": hex(r), "title": title, "title_address": hex(t),
            "description": desc, "description_address": hex(d),
            "field_8_hex": "0x%04X" % f8, "field_10_hex": "0x%04X" % f10,
            "complete_flag": comp, "complete_flag_hex": "0x%04X" % comp,
            "field_14_hex": "0x%04X" % f14}


def walk_table(rom, reader, anchor, stride, region=(0xE38000, 0xE3D000)):
    def ok(r):
        if r < 0 or r + stride > len(rom):
            return False
        return reader(rom, r) is not None
    lo = anchor
    while ok(lo - stride):
        lo -= stride
    hi = anchor
    while ok(hi + stride):
        hi += stride
    rows = []
    r = lo
    while r <= hi:
        rows.append(reader(rom, r))
        r += stride
    return lo, hi, rows


def stage2(rom, cm):
    dec = make_decoder(rom, cm)
    new_reader = lambda rr, r: read_new_row(rom, dec, r)
    old_reader = lambda rr, r: read_old_row(rom, dec, r)
    new_lo, new_hi, new_rows = walk_table(rom, new_reader, NEW_ANCHOR, NEW_STRIDE)
    old_lo, old_hi, old_rows = walk_table(rom, old_reader, OLD_ANCHOR, OLD_STRIDE)

    # boundary evidence: the exact failing rows just outside each block
    def boundary(r, stride, reader):
        if r < 0 or r + stride > len(rom):
            return {"row_offset": hex(r), "in_range": False}
        t, d = struct.unpack_from("<II", rom, r)
        return {"row_offset": hex(r), "title_ptr": hex(t), "desc_ptr": hex(d),
                "title_decodes": dec(t) is not None, "desc_decodes": dec(d) is not None,
                "raw_hex": rom[r:r + stride].hex(" ")}
    new_bounds = {"below_start": boundary(new_lo - NEW_STRIDE, NEW_STRIDE, new_reader),
                  "above_end": boundary(new_hi + NEW_STRIDE, NEW_STRIDE, new_reader)}
    old_bounds = {"below_start": boundary(old_lo - OLD_STRIDE, OLD_STRIDE, old_reader),
                  "above_end": boundary(old_hi + OLD_STRIDE, OLD_STRIDE, old_reader)}

    # merge descriptions by complete flag; keep every same-flag candidate
    old_by_flag = {}
    for row in old_rows:
        old_by_flag.setdefault(row["complete_flag"], []).append(row)

    merged = []
    matched_old = set()
    for i, row in enumerate(new_rows):
        cands = old_by_flag.get(row["complete_flag"], [])
        for c in cands:
            matched_old.add(c["row_offset"])
        entry = dict(row)
        entry["index"] = i
        entry["legacy_description_candidates"] = [
            {"row_offset": c["row_offset"], "title": c["title"],
             "description_address": c["description_address"], "description": c["description"]}
            for c in cands
        ]
        if cands:
            entry["description_source"] = "legacy_by_complete_flag"
            entry["description"] = cands[0]["description"]
            entry["description_address_merged"] = cands[0]["description_address"]
        else:
            entry["description_source"] = "current_row"
            entry["description_address_merged"] = row["description_address"]
        entry["legacy_match_count"] = len(cands)
        merged.append(entry)

    legacy_only = [dict(r, note="complete_flag not present in current table") for r in old_rows
                   if r["row_offset"] not in matched_old]

    titles = [r["title"] for r in new_rows]
    return {
        "generated_by": "player_guide/scripts/locate_quest_catalog.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "Sidequest catalog extracted from two confirmed E3 layouts, merged by complete flag.",
        "rom": {"path": ROM_PATH, "size": len(rom), "sha256": hashlib.sha256(rom).hexdigest()},
        "encoding": {"source": "out/charmap.json",
                     "note": "2-byte codes big-endian (lead,trail); 0xFA/0xFB/0xFE soft; 0xFC/0xFD/0xF8/0xF9 abort decode"},
        "tables": {
            "current_anchor_E3B028_stride20": {
                "anchor": hex(NEW_ANCHOR), "stride": NEW_STRIDE,
                "start": hex(new_lo), "end": hex(new_hi), "row_count": len(new_rows),
                "fields": ["u32 title_ptr", "u32 desc_ptr", "u16 unknown", "u16 accept_flag",
                           "u16 complete_flag", "u8 map_group", "u8 map_num", "4 tail bytes"],
                "boundary": new_bounds,
                "other_valid_blocks_in_region": "none contiguous (singleton coincidences only)"},
            "legacy_anchor_E39444_stride16": {
                "anchor": hex(OLD_ANCHOR), "stride": OLD_STRIDE,
                "start": hex(old_lo), "end": hex(old_hi), "row_count": len(old_rows),
                "fields": ["u32 title_ptr", "u32 desc_ptr", "u16 +8 unknown",
                           "u16 +10 constant 0x1400 (NOT accept flag)", "u16 +12 complete_flag",
                           "u16 +14"],
                "boundary": old_bounds,
                "other_valid_blocks_in_region": "none contiguous (singleton coincidences only)"},
        },
        "boundary_rule": ("row valid iff title_ptr and desc_ptr both in [0x08000000, 0x08000000+rom_size) "
                          "AND both decode fully to 0xFF via the wiki charmap; no forced length"),
        "merge_rule": "current rows keyed by complete_flag; legacy description candidates attached by equal complete_flag; no candidate dropped",
        "counts": {"current_rows": len(new_rows), "legacy_rows": len(old_rows),
                   "merged_rows": len(merged), "legacy_only_rows": len(legacy_only),
                   "legacy_rows_matched_by_complete_flag": len(matched_old)},
        "rows": merged,
        "legacy_only_rows": legacy_only,
        "title_list": titles,
    }


# ---------------------------------------------------------------- stage 3
# Collection only for Main: raw flag-pattern hits + text keyword hits.
# This does NOT claim any raw hit is a script or a new production entry.
MISSING_OUT = os.path.join(G, "data", "quest_missing_anchors.json")
TARGET_QUEST_IDS = [4, 5, 6, 36, 59, 63, 64, 65, 96]
TEXT_KEYWORDS = ["阿笔", "黑曜", "皮可西", "冰壁", "潜能", "头巾", "8bit", "怯场", "遗忘"]
SCRIPTS_JSON = os.path.join(R, "maps_research", "out", "scripts", "scripts.json")
TEXT_JSON = os.path.join(R, "maps_research", "out", "scripts", "text.json")


def hex_block48(rom, center):
    lo, hi = max(0, center - 48), min(len(rom), center + 48)
    lines = ["%08X  %s" % (o, rom[o:o + 16].hex(" ")) for o in range(lo, hi, 16)]
    return {"range": [hex(lo), hex(hi - 1)], "text": "\n".join(lines)}


def load_script_index():
    """Return (all_instruction_addrs, {(opcode,flag): [ (script_addr, ins_addr, name) ]})."""
    with open(SCRIPTS_JSON, encoding="utf-8") as f:
        data = json.load(f)
    addrs, by_flag = set(), {}
    for key, sc in data["scripts"].items():
        for ins in sc.get("instructions", []):
            a = int(ins["addr"], 16)
            addrs.add(a)
            op = ins.get("opcode")
            if op in ("0x2B", "0x29"):
                val = None
                for ar in ins.get("args") or []:
                    if ar.get("width") == 2:
                        val = ar.get("value")
                by_flag.setdefault((op, val), []).append(
                    {"script": key, "ins_addr": ins["addr"], "name": ins.get("name")})
    return addrs, by_flag


def stage3(rom, catalog):
    rows = {r["index"]: r for r in catalog["rows"]}
    all_addrs, by_flag = load_script_index()
    targets, hits = [], []

    def allpos(pat):
        out, i = [], rom.find(pat)
        while i != -1:
            out.append(i)
            i = rom.find(pat, i + 1)
        return out

    for qid in TARGET_QUEST_IDS:
        row = rows.get(qid)
        if row is None:
            targets.append({"quest_id": qid, "error": "not in current catalog rows"})
            continue
        flags = [("accept", row["accept_flag"])]
        if row["complete_flag"] != row["accept_flag"]:
            flags.append(("complete", row["complete_flag"]))
        targets.append({"quest_id": qid, "title": row["title"], "catalog_row": qid,
                        "catalog_row_offset": row["row_offset"],
                        "accept_flag": "0x%04X" % row["accept_flag"],
                        "complete_flag": "0x%04X" % row["complete_flag"],
                        "map": [row["map_group"], row["map_num"]]})
        for kind, f in flags:
            for mode, pat in (("checkflag_2B_flag_06", bytes([0x2B, f & 0xFF, f >> 8, 0x06])),
                              ("setflag_29_flag", bytes([0x29, f & 0xFF, f >> 8]))):
                for off in allpos(pat):
                    addr = ROM_BASE + off
                    opcode = "0x2B" if mode.startswith("checkflag") else "0x29"
                    existing = by_flag.get((opcode, f), [])
                    exact_script = next((e for e in existing if int(e["ins_addr"], 16) == addr), None)
                    hits.append({
                        "quest_id": qid, "title": row["title"], "flag_kind": kind,
                        "flag": "0x%04X" % f, "mode": mode, "pattern_hex": pat.hex(),
                        "rom_offset": hex(off), "rom_addr": hex(addr),
                        "is_existing_instruction_address": addr in all_addrs,
                        "existing_exact_instruction": exact_script,
                        "existing_scripts_with_same_flag": existing,
                        "hex_pm48": hex_block48(rom, off),
                    })

    with open(TEXT_JSON, encoding="utf-8") as f:
        tj = json.load(f)
    strings = tj["strings"]
    text_hits = {}
    for kw in TEXT_KEYWORDS:
        found = []
        for k, v in strings.items():
            if kw in v.get("text", ""):
                found.append({"addr": v.get("addr", k), "text": v.get("text"),
                              "bytes": v.get("bytes"), "raw": v.get("raw"),
                              "referenced_by": v.get("referenced_by")})
        text_hits[kw] = {"count": len(found), "hits": found}

    return {
        "generated_by": "player_guide/scripts/locate_quest_catalog.py (stage 3)",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "Collection only: raw flag-pattern hits (+/-48 hex) and text keyword hits for Main's judgment.",
        "disclaimer": "Raw ROM matches are NOT asserted to be scripts or new production entries; no interpretation applied.",
        "rom": {"path": ROM_PATH, "size": len(rom), "sha256": hashlib.sha256(rom).hexdigest()},
        "patterns": {"checkflag": "2B <flag u16 le> 06 (checkflag immediately followed by goto_if)",
                     "setflag": "29 <flag u16 le>"},
        "sources": {"scripts_json": SCRIPTS_JSON, "text_json": TEXT_JSON},
        "target_quests": targets,
        "flag_pattern_hits": hits,
        "flag_pattern_hit_counts": {
            "total": len(hits),
            "already_existing_instruction_address": sum(1 for h in hits if h["is_existing_instruction_address"]),
        },
        "text_keyword_hits": text_hits,
    }


def main():
    rom = load_rom()
    cm = load_charmap()
    os.makedirs(os.path.dirname(CAND_OUT), exist_ok=True)
    with open(CAND_OUT, "w", encoding="utf-8") as f:
        json.dump(stage1(rom, cm), f, ensure_ascii=False, indent=2)
    cat = stage2(rom, cm)
    with open(CATALOG_OUT, "w", encoding="utf-8") as f:
        json.dump(cat, f, ensure_ascii=False, indent=2)
    anchors = stage3(rom, cat)
    with open(MISSING_OUT, "w", encoding="utf-8") as f:
        json.dump(anchors, f, ensure_ascii=False, indent=2)
    print("wrote", CAND_OUT)
    print("wrote", CATALOG_OUT, cat["counts"])
    print("wrote", MISSING_OUT, anchors["flag_pattern_hit_counts"])


if __name__ == "__main__":
    main()
