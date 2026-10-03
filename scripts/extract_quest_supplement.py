"""Supplement script extractor: decode ONLY the Main-provided quest catalog flag anchors.

The production extractor (maps_research/scripts/extract_scripts.py) is reused *in memory*:
its source text is patched and exec'd with __file__ still pointing at the original file, so
ROOT/PROJ keep resolving to the production tree and its INPUT roots stay
maps_research/out + maps_research/raw (opcode table, charmap, headers, events).

Only two things change:
  * the output roots OUT/RAW are redirected to player_guide/data/quest_supplement/{out,raw}
    (the production read paths are kept in OUT_IN/RAW_IN), and
  * the entry list is replaced, just before the "special (0x25)" block, with the six exact
    addresses from Main, kind "quest_catalog_flag_anchor".
No map root, object or coordinate claim is invented: these anchors stay flagged as
candidate roots supplied by the quest catalog work.

Address -> owning catalog number (verified against quest packet flags):
  0x09CD0194 -> 036  (flag 0x0C71)
  0x09CD3121 -> 059  (flag 0x0B93)
  0x09CD39C8 -> 065  (flag 0x0BA0)
  0x09CD2F40 -> 096  (flag 0x0CD2)
  0x09CD5B67 -> 006  (flag 0x0CE9)
  0x09CD08BA -> 096  (same flag 0x0CD2; dialogue branch of the 096 anchor)
  0x09CD3362 -> 004  (corrected start; 335E bytes 62 FE 65 FE are a standalone action, not a script)
  0x09CD404B -> 005  (Main-determined ROM neighbour root; reaches setflag 0x2943)
  0x09CD5CCF -> 006  (Main-determined ROM neighbour root; scene 1)
  0x09CD5E6C -> 006  (Main-determined ROM neighbour root; scene 2, reaches setflag 0x3307)

Additionally, strict byte-match flag-branch candidates from
data/quest_extra_roots.json (find_quest_roots.py) are appended, deduplicated against the
six anchors, as kind "quest_flag_branch_candidate" with the owning quest_ids in `where`.
These are candidate branch scripts, not map entries or reachability claims.
"""
import os

G = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # player_guide
R = os.path.dirname(G)                                                    # project root
EXTRACTOR = os.path.join(R, "maps_research", "scripts", "extract_scripts.py")
SUP = os.path.join(G, "data", "quest_supplement")
EXTRA_ROOTS = os.path.join(G, "data", "quest_extra_roots.json")
SUP_OUT = os.path.join(SUP, "out")
SUP_RAW = os.path.join(SUP, "raw")
os.makedirs(os.path.join(SUP_OUT, "scripts"), exist_ok=True)
os.makedirs(os.path.join(SUP_RAW, "scripts"), exist_ok=True)

src = open(EXTRACTOR, encoding="utf-8").read()

# --- 1) redirect output roots; keep production OUT/RAW as read-only inputs -------------
old_roots = 'OUT = os.path.join(ROOT, "out")\nRAW = os.path.join(ROOT, "raw")\n'
assert src.count(old_roots) == 1, "root definition block not found"
new_roots = ('OUT = os.path.join(ROOT, "out")\nRAW = os.path.join(ROOT, "raw")\n'
             'OUT_IN, RAW_IN = OUT, RAW\n'
             'OUT = %r\nRAW = %r\n' % (SUP_OUT, SUP_RAW))
src = src.replace(old_roots, new_roots, 1)

READ_EXPRS = [
    'os.path.join(OUT, "scripts", "opcode_table.json")',
    'os.path.join(OUT, "scripts", "opcode_args_from_rom.json")',
    'os.path.join(OUT, "maps", "headers.json")',
    'os.path.join(OUT, "events", "events.json")',
]
for e in READ_EXPRS:
    assert src.count(e) == 1, "read expression not found once: " + e
    src = src.replace(e, e.replace("os.path.join(OUT,", "os.path.join(OUT_IN,", 1), 1)

# --- 2) replace the entry list with the six exact supplement anchors -------------------
marker = "# special (0x25) handler"
assert src.count(marker) == 1, "special-block marker not found once"
entries_block = (
    "# --- supplement entries: Main-provided exact quest catalog flag anchors ---\n"
    "entries = [\n"
    '    (0x09CD0194, "quest_catalog_flag_anchor", "036"),\n'
    '    (0x09CD3121, "quest_catalog_flag_anchor", "059"),\n'
    '    (0x09CD39C8, "quest_catalog_flag_anchor", "065"),\n'
    '    (0x09CD2F40, "quest_catalog_flag_anchor", "096"),\n'
    '    (0x09CD5B67, "quest_catalog_flag_anchor", "006"),\n'
    '    (0x09CD08BA, "quest_catalog_flag_anchor", "096"),\n'
    '    (0x09CD3362, "quest_catalog_flag_anchor", "004"),\n'
    '    (0x09CD404B, "quest_catalog_flag_anchor", "005"),\n'
    '    (0x09CD5CCF, "quest_catalog_flag_anchor", "006"),\n'
    '    (0x09CD5E6C, "quest_catalog_flag_anchor", "006"),\n'
    "]\n"
    "# --- supplement entries: strict byte-match flag-branch candidates (quest_ids from "
    "find_quest_roots.py; candidate branch, NOT a map entry / reachability claim) ---\n"
    "_extra = json.load(open(%r, encoding='utf-8'))\n"
    "_seen = {a for a, _k, _w in entries}\n"
    "for _r in _extra['roots']:\n"
    "    _a = int(_r['root'], 16)\n"
    "    if _a in _seen:\n"
    "        continue\n"
    "    _seen.add(_a)\n"
    "    entries.append((_a, 'quest_flag_branch_candidate',\n"
    "                    'quest_ids=' + ','.join(str(q) for q in _r.get('quest_ids', []))))\n"
    "\n" % EXTRA_ROOTS)
src = src.replace(marker, entries_block + marker, 1)

# --- 3) execute the patched source; __file__ stays the original extractor --------------
scope = {"__name__": "__main__", "__file__": EXTRACTOR}
exec(compile(src, EXTRACTOR, "exec"), scope)
