"""Supplement script extractor for wild-Mega battle branches.

Scans the ROM for the exact 5-byte pattern 16 40 50 01 00 (setvar 0x5040 = 1) and derives
roots from it, then decodes them with the *unmodified* production decoder
(maps_research/scripts/extract_scripts.py) reused in memory, exactly like
extract_quest_supplement.py. Inputs stay at maps_research/out + raw; every write lands in
player_guide/data/mega_supplement/{out,raw}.

Root rules (Main):
  * For every pattern at address a with the 3 bytes before it equal to 29 BD 0A
    (setflag 0x0ABD), add root = a - 3 (battle branch; NOT presented as a map entry).
  * For the 16 patterns in 0x09CD47FE..0x09CD505F (stride 0x8F), additionally add
    root = a - 0x43. The 6 bytes at the start of that root must be 69 19 07 80 0F 80
    (faceplayer / lockall / ...); a mismatch is recorded for Main, never guessed.

All roots are byte-match candidates, not map objects and not reachability proof.
"""
import os, re, json

G = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # player_guide
R = os.path.dirname(G)                                                    # project root
EXTRACTOR = os.path.join(R, "maps_research", "scripts", "extract_scripts.py")
SUP = os.path.join(G, "data", "mega_supplement")
SUP_OUT = os.path.join(SUP, "out")
SUP_RAW = os.path.join(SUP, "raw")
os.makedirs(os.path.join(SUP_OUT, "scripts"), exist_ok=True)
os.makedirs(os.path.join(SUP_RAW, "scripts"), exist_ok=True)

BASE = 0x08000000
PATTERN = bytes.fromhex("1640500100")          # setvar 0x5040, 1
PRE3 = bytes.fromhex("29BD0A")                 # setflag 0x0ABD
SCENE_SIG = bytes.fromhex("691907800F80")      # first 6 bytes of a scene root
WIN_LO, WIN_HI = 0x09CD47FE, 0x09CD505F
PTR_TABLE = 0x09DD9E5C

src = open(EXTRACTOR, encoding="utf-8").read()
rom_path = re.search(r'^ROM = r"(.*)"$', src, re.M).group(1)
rom = open(rom_path, "rb").read()

positions = []
i = 0
while True:
    j = rom.find(PATTERN, i)
    if j < 0:
        break
    positions.append(j + BASE)
    i = j + 1

entries, seen, records = [], set(), []
def add(root, kind, where):
    if root not in seen:
        seen.add(root)
        entries.append((root, kind, where))

for a in positions:
    rec = {"pattern": "0x%08X" % a, "roots": [], "battle_branch": False,
           "scene_root": None, "notes": []}
    if rom[a - len(PRE3) - BASE:a - BASE] == PRE3:
        root = a - 3
        add(root, "mega_battle_branch", "after setflag 0x0ABD, setvar 0x5040=1 @0x%08X" % a)
        rec["battle_branch"] = True
        rec["roots"].append("0x%08X" % root)
    else:
        rec["notes"].append("no 29 BD 0A immediately before pattern")
    if WIN_LO <= a <= WIN_HI:
        r = a - 0x43
        head = rom[r - BASE:r - BASE + 6]
        rec["scene_root_addr"] = "0x%08X" % r
        rec["scene_root_head"] = head.hex(" ")
        if head == SCENE_SIG:
            add(r, "mega_scene_root",
                "pointer table 0x%08X stride 0x8F; pattern@0x%08X" % (PTR_TABLE, a))
            rec["scene_root"] = "0x%08X" % r
            rec["roots"].append("0x%08X" % r)
        else:
            rec["notes"].append("scene root header mismatch (expected 69 19 07 80 0f 80)")
    records.append(rec)

# 4 precise roots referenced by extended coordinate-event tables (Main): not map objects.
EXTENDED_COORD_ROOTS = [
    (0x09CDCA89, "coord event table 0x09DFCA74 / events header 0x09DFC9C4"),
    (0x09CDCD1D, "coord event table 0x09DFCA74 / events header 0x09DFC9C4"),
    (0x09CDCF65, "coord event table 0x09DFCA74 / events header 0x09DFC9C4"),
    (0x09CDD7BC, "coord event table 0x09DFC0F0 / events header 0x09DFC0C4"),
]
for _a, _w in EXTENDED_COORD_ROOTS:
    add(_a, "extended_coord_script", _w)

manifest = {
    "rom": os.path.basename(rom_path),
    "pattern": "16 40 50 01 00 (setvar 0x5040 = 1)",
    "pattern_count": len(positions),
    "window": "0x%08X..0x%08X (stride 0x8F, %d entries)" % (
        WIN_LO, WIN_HI, sum(1 for a in positions if WIN_LO <= a <= WIN_HI)),
    "scene_signature": "69 19 07 80 0F 80 at root start; pointer table 0x%08X" % PTR_TABLE,
    "battle_branch_rule": "bytes 29 BD 0A immediately before pattern -> root = a - 3",
    "scene_root_rule": "window patterns: root = a - 0x43, header must equal 69 19 07 80 0F 80",
    "root_count": len(entries),
    "extended_coord_roots": [{"root": "0x%08X" % a, "kind": "extended_coord_script", "basis": w}
                             for a, w in EXTENDED_COORD_ROOTS],
    "records": records,
}
json.dump(manifest, open(os.path.join(SUP, "root_manifest.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# ---- reuse the production decoder in memory (same redirection as the quest supplement) ----
old_roots = 'OUT = os.path.join(ROOT, "out")\nRAW = os.path.join(ROOT, "raw")\n'
assert src.count(old_roots) == 1, "root definition block not found"
src = src.replace(old_roots,
                  'OUT = os.path.join(ROOT, "out")\nRAW = os.path.join(ROOT, "raw")\n'
                  'OUT_IN, RAW_IN = OUT, RAW\n'
                  'OUT = %r\nRAW = %r\n' % (SUP_OUT, SUP_RAW), 1)
for e in ('os.path.join(OUT, "scripts", "opcode_table.json")',
          'os.path.join(OUT, "scripts", "opcode_args_from_rom.json")',
          'os.path.join(OUT, "maps", "headers.json")',
          'os.path.join(OUT, "events", "events.json")'):
    assert src.count(e) == 1, "read expression not found once: " + e
    src = src.replace(e, e.replace("os.path.join(OUT,", "os.path.join(OUT_IN,", 1), 1)

marker = "# special (0x25) handler"
assert src.count(marker) == 1, "special-block marker not found once"
block = ("# --- supplement entries: wild-Mega roots from the 16 40 50 01 00 scan ---\n"
         "entries = [\n"
         + "".join("    (0x%08X, %r, %r),\n" % (a, k, w) for a, k, w in entries)
         + "]\n\n")
src = src.replace(marker, block + marker, 1)

scope = {"__name__": "__main__", "__file__": EXTRACTOR}
exec(compile(src, EXTRACTOR, "exec"), scope)
