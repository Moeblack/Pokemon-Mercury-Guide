# /// script
# requires-python = ">=3.10"
# ///
"""Decode Mercury's event scripts and referenced text.

Entry points come from ROM data only:
  * MapHeader.mapScripts            (tag,u32) entries, terminated by tag 0
      tag 2 / 4 point at (u16,u16,u32) tables terminated by u16 0
  * ObjectEventTemplate.script      (offset 0x10, verified in ROM code at 0x805FC32)
  * CoordEvent.script               (offset 0x0C)
  * BgEvent.script for kind 0        (offset 0x08)

Instruction lengths come from out/scripts/opcode_table.json, which is built
from CFRU's xse_commands.s (this ROM's engine family) and vanilla FireRed's
asm/macros/event.inc + map.inc.  Unknown opcodes are kept as raw bytes.
Text is decoded with the wiki-provided Chinese charmap (1-byte table + 2-byte
lead/trail table); nothing is invented when a byte is unmapped.
"""
import json, os, struct, hashlib, collections

ROM = r"C:/Users/Moeblack/Downloads/宝可梦水银/宝可梦水银FC~致150年后的你 Version 1.1 (1).gba"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJ = os.path.dirname(ROOT)
OUT = os.path.join(ROOT, "out")
RAW = os.path.join(ROOT, "raw")
BASE = 0x08000000
os.makedirs(os.path.join(OUT, "scripts"), exist_ok=True)
os.makedirs(os.path.join(RAW, "scripts"), exist_ok=True)

data = open(ROM, "rb").read()
SHA = hashlib.sha256(data).hexdigest()
ROMSZ = len(data)
inrom = lambda a: 0x08000000 <= a < 0x08000000 + ROMSZ
u8 = lambda a: data[a - BASE]
u16 = lambda a: struct.unpack_from("<H", data, a - BASE)[0]
u32 = lambda a: struct.unpack_from("<I", data, a - BASE)[0]

optab = json.load(open(os.path.join(OUT, "scripts", "opcode_table.json"), encoding="utf-8"))["opcodes"]
OP = {}
for k, v in optab.items():
    OP[int(k)] = v      # JSON keys are decimal opcode values

charmap = json.load(open(os.path.join(PROJ, "out", "charmap.json"), encoding="utf-8"))
ONE = {int(k, 16): v for k, v in charmap.items() if len(k) == 2}
TWO = {int(k, 16): v for k, v in charmap.items() if len(k) == 4}

# Text control codes.  Source of truth: the engine this hack is built on
# (pret/pokefirered include/characters.h + src/text.c switch).  Parameter byte counts are taken
# from that switch, never from the wiki charmap (whose FA/FB/FE entries are placeholders that
# would otherwise decode as the letters l/p/n).
CTRL_NOPARAM = {0xFA: "\\l", 0xFB: "\\p", 0xFE: "\\n"}          # prompt-scroll / prompt-clear / newline
CTRL_PARAM1 = {0xFD: "\\var", 0xF8: "\\keypad", 0xF9: "\\symbol"}  # placeholder / keypad icon / extra symbol
# 0xFC EXT_CTRL_CODE_BEGIN: control id -> number of parameter bytes (text.c)
EXT_CTRL_PARAMS = {0x01: 1, 0x02: 1, 0x03: 1, 0x04: 3, 0x05: 1, 0x06: 1, 0x07: 0, 0x08: 1,
                   0x09: 0, 0x0A: 0, 0x0B: 2, 0x0C: 1, 0x0D: 1, 0x0E: 1, 0x0F: 0, 0x10: 2,
                   0x11: 1, 0x12: 1, 0x13: 1, 0x14: 1, 0x15: 0, 0x16: 0, 0x17: 0, 0x18: 0}


TERMINATORS = {0x02, 0x03}          # end, return
BRANCH = {"goto", "jump", "call", "goto_if", "call_if", "goto_if_set", "goto_if_unset",
          "goto_if_defeated", "goto_if_not_defeated", "jump_if", "branch"}


def load_trainerbattle_types():
    """opcode 0x5C is variable length: first byte = type, the rest depends on it.

    ROM proof: the 0x5C handler is 0x0806C2C4 -> `ldr r0,[r4,#8]; bl #0x08080228;
    str r0,[r4,#8]`, i.e. the whole command is consumed by a helper instead of a fixed
    ScriptRead* sequence.  Per-type layouts come from CFRU trainerbattle0..16 macros in
    reference/cfru/xse_commands.s (only the variant that emits `.byte 0x5C` first).
    Returns {type_value: [field widths *after* the type byte]}.
    """
    import re as _re
    table = {}
    try:
        src = open(os.path.join(PROJ, "reference", "cfru", "xse_commands.s"),
                   encoding="utf-8", errors="replace").read()
    except OSError:
        return table
    for blk in _re.split(r"\.macro\s+", src):
        if not _re.match(r"trainerbattle\d+\b", blk):
            continue
        body = blk.split(".endm")[0]
        emitted = []
        for line in body.splitlines()[1:]:
            m = _re.match(r"^\.(byte|hword|word|2byte|4byte)\s+(\S+)", line.split("@")[0].strip())
            if not m:
                continue
            w = {"byte": 1, "2byte": 2, "hword": 2, "4byte": 4, "word": 4}[m.group(1)]
            emitted.append((m.group(1), m.group(2), w))
        if len(emitted) < 2 or emitted[0][1].lower() != "0x5c":
            continue
        try:
            ty = int(emitted[1][1], 16)
        except ValueError:
            continue
        table[ty] = [1] + [w for _, _, w in emitted[2:]]   # field 0 = the type byte
    return table


TB_TYPES = load_trainerbattle_types()


ROM_CONFIRMED_LAYOUTS = {}


def load_rom_arg_overrides():
    """ROM handler replay (scripts/verify_opcode_args.py) yields a proven field sequence for
    commands where the assembler-macro table was too short.  We only accept an override when
    the recorded field widths sum to the replayed pointer advance AND that advance is strictly
    larger than the macro width - a larger consumption from the real handler proves the macro
    is wrong, while a smaller one could just be a branch our replay missed."""
    over = {}
    try:
        j = json.load(open(os.path.join(OUT, "scripts", "opcode_args_from_rom.json"),
                           encoding="utf-8"))
    except OSError:
        j = {"commands": {}}
    for k, v in j["commands"].items():
        f = v.get("rom_fields") or []
        if f and sum(f) == v.get("rom_argbytes") and v["rom_argbytes"] > v["macro_argbytes"]:
            over[int(k, 16)] = f
    # Manual consumer proofs are a separate provenance class, never replay successes.
    confirmed_path = os.path.join(ROOT, "scripts", "confirmed_opcode_layouts.json")
    if os.path.isfile(confirmed_path):
        with open(confirmed_path, encoding="utf-8") as f:
            confirmed = json.load(f)
        if confirmed.get("schema_version") != 1 or confirmed.get("rom_sha256") != SHA:
            raise ValueError("confirmed opcode layouts schema/ROM SHA mismatch")
        for k, record in confirmed["commands"].items():
            opcode = int(k, 16)
            fields = record.get("fields")
            if (record.get("rom_sha256") != SHA or
                    record.get("layout_source") != "rom_confirmed_layout" or
                    not isinstance(fields, list) or not fields or
                    any(type(width) is not int or width not in (1, 2, 4) for width in fields) or
                    record.get("total_length") != 1 + sum(fields) or
                    not record.get("confirmation_method") or opcode not in OP):
                raise ValueError("invalid confirmed opcode layout: " + k)
            evidence_path = os.path.join(PROJ, record["evidence_path"])
            with open(evidence_path, "rb") as f:
                evidence_raw = f.read()
            if hashlib.sha256(evidence_raw).hexdigest() != record["evidence_sha256"]:
                raise ValueError("confirmed opcode evidence SHA mismatch: " + k)
            evidence = json.loads(evidence_raw)
            if (evidence.get("status") != "confirmed_rom_argument_layout" or
                    evidence["rom"]["sha256"] != SHA or int(evidence["opcode"], 16) != opcode or
                    evidence["fields"] != fields or evidence["total_length"] != record["total_length"]):
                raise ValueError("confirmed opcode evidence contract mismatch: " + k)
            over[opcode] = list(fields)
            ROM_CONFIRMED_LAYOUTS[opcode] = dict(record)
    return over


ROM_ARG_OVERRIDES = load_rom_arg_overrides()
if os.environ.get("MERCURY_NO_ARG_FIX"):
    # diagnostic mode: reproduce the pre-fix behaviour (macro widths only, fixed trainerbattle)
    ROM_ARG_OVERRIDES = {}
    TB_TYPES = {}


def load_opcode_range_stop():
    """Read dispatcher bounds from existing ROM-parameter evidence, not macro maxima."""
    evidence_relative = "parallel_acceleration/script_stops/opcode_range_stop_evidence.json"
    with open(os.path.join(PROJ, evidence_relative), "rb") as f:
        evidence_raw = f.read()
    evidence = json.loads(evidence_raw)
    source_data = {}
    for key in ("cmd_table", "dispatch_catalog", "runner_disassembly"):
        source = evidence["sources"][key]
        with open(os.path.join(PROJ, source["path"]), "rb") as f:
            raw = f.read()
        if hashlib.sha256(raw).hexdigest() != source["sha256"]:
            raise ValueError("opcode range evidence source SHA mismatch: " + key)
        source_data[key] = json.loads(raw) if key != "runner_disassembly" else None
    params = source_data["cmd_table"]
    catalog = source_data["dispatch_catalog"]
    if catalog["sha256"] != SHA:
        raise ValueError("opcode range evidence ROM SHA mismatch")
    start = int(params["gScriptCmdTable"], 16)
    end = int(params["gScriptCmdTableEnd"], 16)
    count = params["command_count"]
    table = catalog["tables"]["script_engine_handlers"]
    comparison = evidence["comparison"]
    if (type(count) is not int or count <= 0 or end - start != count * 4 or
            not inrom(start) or not inrom(end - 1) or
            int(table["start"], 16) != start or int(table["end_exclusive"], 16) != end or
            table["slot_count"] != count or table["declared_slot_count"] != count or
            int(comparison["table_start"], 16) != start or int(comparison["table_end"], 16) != end or
            comparison["slot_count"] != count):
        raise ValueError("opcode range evidence parameter disagreement")
    stop_handler = evidence["sources"]["runner_disassembly"]["stop_target"]["addr"]
    if not inrom(int(stop_handler, 16)):
        raise ValueError("opcode range stop handler is outside ROM")
    return {
        "table_start": "0x%08X" % start, "table_end": "0x%08X" % end,
        "table_count": count, "stop_handler": stop_handler,
        "condition": "unsigned (table_start + opcode * 4) >= table_end",
        "evidence": {"path": evidence_relative,
                     "sha256": hashlib.sha256(evidence_raw).hexdigest(),
                     "parameter_source": evidence["sources"]["cmd_table"],
                     "runner_source": evidence["sources"]["runner_disassembly"]["path"],
                     "runner_sha256": evidence["sources"]["runner_disassembly"]["sha256"],
                     "rom_sha256": SHA},
        "root_validity": "not_proven_by_stop_mechanism",
        "prior_desynchronization": "not_excluded",
    }


OPCODE_RANGE_STOP = load_opcode_range_stop()


def decode_text(p, limit=4000):
    """-> (text, nbytes, ended, mapped_ratio)

    Order matters: a 2-byte Chinese character (lead 0x01-0x1E + trail) is tested first, then the
    engine control codes, and only then the 1-byte character table - the wiki table maps 0xFA/0xFB/
    0xFE to the letters l/p/n, which must not win over the control codes.  Control bytes count as
    "mapped" so that strings containing them keep ratio 1.0.
    """
    o = p - BASE
    if o < 0 or o >= ROMSZ:
        return None
    out, i, mapped, total = [], 0, 0, 0
    while i < limit and o + i < ROMSZ:
        b = data[o + i]
        if b == 0xFF:                       # EOS
            i += 1
            return ("".join(out), i, True, mapped / max(1, total))
        k = (data[o + i] << 8) | data[o + i + 1] if o + i + 1 < ROMSZ else -1
        if 0x01 <= b <= 0x1E and k in TWO:  # Chinese lead/trail pair
            out.append(TWO[k]); i += 2; total += 2; mapped += 2
            continue
        if b in CTRL_NOPARAM:
            out.append(CTRL_NOPARAM[b]); i += 1; total += 1; mapped += 1
            continue
        if b == 0xFC:                       # extended control code
            cid = data[o + i + 1] if o + i + 1 < ROMSZ else None
            n = EXT_CTRL_PARAMS.get(cid)
            if cid is None or n is None:
                tok = "\\ctrl?[%02X]" % (cid if cid is not None else 0)
                consume = 2 if cid is not None else 1
            else:
                prm = data[o + i + 2:o + i + 2 + n]
                tok = "\\ctrl[%02X%s]" % (cid, (" " + prm.hex()) if n else "")
                consume = 2 + n
            out.append(tok); i += consume; total += consume; mapped += consume
            continue
        if b in CTRL_PARAM1:
            v = data[o + i + 1] if o + i + 1 < ROMSZ else 0
            out.append("%s[%02X]" % (CTRL_PARAM1[b], v)); i += 2; total += 2; mapped += 2
            continue
        if b in ONE:
            out.append(ONE[b]); mapped += 1
        else:
            out.append("<%02X>" % b)
        total += 1
        i += 1
    return ("".join(out), i, False, mapped / max(1, total))


TEXT_CMDS = {"loadpointer", "message", "preparemsg", "formatstring", "bufferstring",
             "vbufferstring", "bufferitemname", "buffermovename", "bufferspeciesname",
             "bufferdecorationname", "bufferstdstring", "braillemessage", "msgbox",
             "bufferitemnameplural", "buffernumberstring"}


def looks_like_text(p):
    """A pointer is text iff every byte decodes and the string is 0xFF-terminated."""
    if not inrom(p):
        return False
    r = decode_text(p)
    if not r:
        return False
    text, n, ended, ratio = r
    if not ended or n < 3 or ratio < 1.0:
        return False
    if "<" in text:                     # any unmapped byte disqualifies
        return False
    return True


# ------------------------------------------------------------------ entry pts
headers = json.load(open(os.path.join(OUT, "maps", "headers.json"), encoding="utf-8"))["maps"]
events = json.load(open(os.path.join(OUT, "events", "events.json"), encoding="utf-8"))["maps"]

entries = []       # (addr, kind, source)
map_script_tables = {}
for m in headers:
    key = "%d:%d" % (m["group"], m["num"])
    scr = int(m["map_scripts_addr"], 16)
    tabs = []
    if scr:
        p = scr
        for _ in range(64):
            tag = u8(p)
            if tag == 0:
                break
            ptr = u32(p + 1)
            tabs.append({"tag": tag, "pointer": "0x%08X" % ptr, "addr": "0x%08X" % p})
            if tag in (2, 4):
                q = ptr
                for _2 in range(256):
                    v1, v2 = u16(q), u16(q + 2)
                    if v1 == 0:      # ROM code: MapHeaderCheckScriptTable tests only var1
                        break
                    sp = u32(q + 4)
                    tabs[-1].setdefault("conditions", []).append(
                        {"var1": v1, "var2": v2, "script": "0x%08X" % sp})
                    if inrom(sp):
                        entries.append((sp, "map_script_table", key))
                    q += 8
            elif inrom(ptr):
                entries.append((ptr, "map_script", "%s/tag%d" % (key, tag)))
            p += 5
    map_script_tables[key] = tabs

sentinel_scripts = collections.Counter()
for key, m in events.items():
    for o in m.get("objects", []):
        s = int(o["script"], 16)
        if s in (0x08000000, 0x08000001):
            sentinel_scripts[("0x%08X" % s)] += 1
            continue
        if inrom(s):
            entries.append((s, "object", "%s/local%d" % (key, o["local_id"])))
    for c in m.get("coord_events", []):
        v = int(c["script"], 16)
        if v in (0x08000000, 0x08000001):
            sentinel_scripts["0x%08X" % v] += 1
        elif inrom(v):
            entries.append((v, "coord", key))
    for b in m.get("bg_events", []):
        if b.get("kind") == 0:
            v = int(b.get("script", "0x0"), 16)
            if v in (0x08000000, 0x08000001):
                sentinel_scripts["0x%08X" % v] += 1
            elif inrom(v):
                entries.append((v, "bg", key))

# ---------------------------------------------------- standard scripts / specials
# callstd (0x09) handler 0x0806A180 and gotostd (0x08) handler 0x0806A150 index a table whose
# bounds come from their literal pools: base 0x08160450, end 0x08160478 (10 entries).
STD_BASE = u32(0x0806A1A8)
STD_END = u32(0x0806A1AC)
std_scripts = []
for i in range((STD_END - STD_BASE) // 4):
    a = u32(STD_BASE + 4 * i)
    if inrom(a):
        std_scripts.append((a, "std_script", "gStdScripts[%d]" % i))
        entries.append(std_scripts[-1])
# Roots that are not reachable from map data or the std table: found by searching the ROM for
# 4-byte references to the script and confirming a code literal pool holds it.  Provenance is
# recorded in the JSON so it can be re-checked.
CODE_REFERENCED_ROOTS = [
    ("0x08AEA158", "referenced from the literal pool at 0x0896A314 (GB Player / GB Sounds toggle; "
                   "checkflag/setflag/clearflag 0x174D)"),
    ("0x081A4EC1", "current trainer-config handler 0x09D4A250 loads this returned script at "
                   "0x09D4A2E2 from literal pool 0x09D4A4BC; handler 0x0806C2C4 stores r0 "
                   "into script context +8 at 0x0806C2CE; see code_research/out/battle_init_chain"),
]
for addr_s, why in CODE_REFERENCED_ROOTS:
    a = int(addr_s, 16)
    if inrom(a):
        entries.append((a, "code_referenced", why))

# special (0x25) handler 0x08069EFC indexes a table of native functions:
# base 0x0815FD60, end 0x08160450 (444 entries).  These are machine code, not scripts,
# so they are only recorded as targets, never walked.
SP_BASE = u32(0x08069F18)
SP_END = u32(0x08069F1C)
specials = [{"index": i, "addr": "0x%08X" % u32(SP_BASE + 4 * i)}
            for i in range(min((SP_END - SP_BASE) // 4, 4096))]
json.dump({"gStdScripts_base": "0x%08X" % STD_BASE, "gStdScripts_end": "0x%08X" % STD_END,
           "count": len(std_scripts), "scripts": [{"addr": "0x%08X" % a, "slot": s}
                                                  for a, _, s in std_scripts],
           "specials": {"table": "0x%08X..0x%08X" % (SP_BASE, SP_END), "count": len(specials),
                        "targets": specials}},
          open(os.path.join(OUT, "scripts", "std_and_special.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("std scripts:", len(std_scripts), "specials:", len(specials))
print("entry scripts:", len(entries), "sentinel script uses:", dict(sentinel_scripts))

# ------------------------------------------------------------------- decoding
scripts = {}
queue = collections.deque()
for a, kind, src in entries:
    if a not in scripts:
        scripts[a] = {"addr": "0x%08X" % a, "sources": [], "instructions": [],
                      "unknown_at": None, "bytes": 0}
    scripts[a]["sources"].append({"kind": kind, "where": src})
    queue.append(a)

MAX_INSTR = 1_500_000
total_instr = 0
unknown_ops = collections.Counter()
while queue:
    a = queue.popleft()
    if scripts[a]["instructions"] or a in scripts and scripts[a].get("_done"):
        continue
    p = a
    ins = []
    for _ in range(4000):
        if total_instr > MAX_INSTR or not inrom(p):
            break
        op = u8(p)
        info = OP.get(op)
        if info is None or op >= OPCODE_RANGE_STOP["table_count"]:
            unknown_ops[op] += 1
            if op == 0xFF:
                # Compatibility/history field only: the runtime mechanism below is
                # the unsigned table-bound comparison, not a special FF command.
                ins.append({"addr": "0x%08X" % p, "opcode": "0xFF", "name": None,
                            "raw": "ff",
                            "note": "0xFF stops the script context via the dispatcher range check "
                                    "(0x08069866 bhs 0x08069838); recorded as a terminator"})
                scripts[a]["terminated_by_FF"] = True
            else:
                ins.append({"addr": "0x%08X" % p, "opcode": "0x%02X" % op, "name": None,
                            "raw": "%02x" % op, "note": "undefined opcode; stopped"})
                scripts[a]["unknown_at"] = "0x%08X" % p
            if op >= OPCODE_RANGE_STOP["table_count"]:
                runtime_stop = dict(OPCODE_RANGE_STOP, kind="opcode_out_of_range",
                                    opcode="0x%02X" % op)
                ins[-1]["runtime_stop"] = runtime_stop
                scripts[a]["runtime_stop"] = dict(runtime_stop)
                ins[-1]["note"] = (
                    "Opcode is outside the ROM dispatcher table: unsigned "
                    "table_start + opcode*4 >= table_end branches to the recorded stop handler. "
                    "This is the same mechanism for FF and non-FF opcodes. Legacy unknown_at/"
                    "terminated_by_FF diagnostics are retained; root validity and prior "
                    "instruction synchronization are not proven by this stop mechanism."
                )
            break
        if op == 0x5C and TB_TYPES:
            ty = data[p - BASE + 1]
            fields = TB_TYPES.get(ty)
            layout_src = "trainerbattle_type_table"
            if fields is None:
                unknown_ops[op] += 1
                ins.append({"addr": "0x%08X" % p, "opcode": "0x%02X" % op,
                            "name": info["names"][0],
                            "raw": data[p - BASE:p - BASE + 2].hex(),
                            "note": "trainerbattle with type 0x%02X has no known layout; stopped" % ty})
                scripts[a]["unknown_at"] = "0x%08X" % p
                break
        elif op in ROM_ARG_OVERRIDES:
            fields = list(ROM_ARG_OVERRIDES[op])
            layout_src = "rom_confirmed_layout" if op in ROM_CONFIRMED_LAYOUTS else "rom_handler"
        else:
            fields = info.get("fields") or [1] * info["argbytes"]
            layout_src = "macro"
        raw = data[p - BASE: p - BASE + 1 + sum(fields)]
        args = []
        off = p + 1
        for w in fields:
            v = int.from_bytes(data[off - BASE: off - BASE + w], "little")
            args.append({"width": w, "value": v, "addr": "0x%08X" % off})
            off += w
        ins.append({"addr": "0x%08X" % p, "opcode": "0x%02X" % op,
                    "name": info["names"][0], "names": info["names"],
                    "args": args, "raw": raw.hex(),
                    "layout_source": "trainerbattle_type_table" if op == 0x5C else layout_src})
        if layout_src == "rom_confirmed_layout":
            ins[-1]["layout_evidence"] = ROM_CONFIRMED_LAYOUTS[op]
        total_instr += 1
        p = off
        # follow branch targets
        name = info["names"][0]
        if name in BRANCH or op in (0x04, 0x05, 0x06, 0x07):
            for f in args:
                if f["width"] == 4 and inrom(f["value"]):
                    f["class"] = "script"
                    t = f["value"]
                    if t not in scripts:
                        scripts[t] = {"addr": "0x%08X" % t, "sources": [], "instructions": [],
                                      "unknown_at": None, "bytes": 0}
                        scripts[t]["sources"].append({"kind": "branch", "where": "0x%08X" % a})
                        queue.append(t)
                    break
        if op in TERMINATORS:
            break
        if op == 0x05:      # goto: unconditional
            break
    scripts[a]["instructions"] = ins
    scripts[a]["bytes"] = p - a
    scripts[a]["_done"] = True

print("scripts decoded:", len(scripts), "instructions:", total_instr,
      "undefined opcode hits:", dict(unknown_ops))

# ---------------------------------------------------------------------- text
texts = {}
for a, s in scripts.items():
    for i in s["instructions"]:
        for f in i.get("args", []):
            if f["width"] != 4:
                continue
            v = f["value"]
            if not inrom(v):
                continue
            if i["name"] in BRANCH or i["opcode"] in ("0x04", "0x05", "0x06", "0x07"):
                continue
            if i["name"] not in TEXT_CMDS:
                f["class"] = "raw"
                continue
            if looks_like_text(v):
                f["class"] = "text"
                if v not in texts:
                    t, n, ended, ratio = decode_text(v)
                    texts[v] = {"addr": "0x%08X" % v, "text": t, "bytes": n,
                                "raw": data[v - BASE:v - BASE + n].hex(),
                                "referenced_by": []}
                if len(texts[v]["referenced_by"]) < 8:
                    texts[v]["referenced_by"].append(
                        {"script": s["addr"], "at": f["addr"], "cmd": i["name"]})
            else:
                f["class"] = "raw" if not inrom(v) else "unclassified"

print("text strings:", len(texts))

# -------------------------------------------------------------------- output
for s in scripts.values():
    s.pop("_done", None)
failures = sorted(a for a, v in scripts.items()
                  if any(i["name"] is None for i in v["instructions"]))
json.dump({"failure_scripts": failures, "count": len(failures)},
          open(os.path.join(OUT, "scripts", "decode_failures.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump({"rom": os.path.basename(ROM), "sha256": SHA,
           "opcode_table_source": "cfru/xse_commands.s + pret event.inc/map.inc",
           "entry_count": len(entries), "script_count": len(scripts),
           "instruction_count": total_instr,
           "undefined_opcode_hits": {"0x%02X" % k: v for k, v in unknown_ops.items()},
           "sentinel_script_values": dict(sentinel_scripts),
           "scripts": {("0x%08X" % k): v for k, v in sorted(scripts.items())}},
          open(os.path.join(OUT, "scripts", "scripts.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

json.dump({"rom": os.path.basename(ROM), "sha256": SHA,
           "encoding": "2-byte lead(0x01-0x1E)/trail from the wiki charmap + engine control codes "
                       "decoded first (0xFA=\\l, 0xFB=\\p, 0xFE=\\n; 0xFD/0xF8/0xF9 one parameter; "
                       "0xFC control code with pret text.c parameter counts); 0xFF terminates",
           "count": len(texts),
           "strings": {("0x%08X" % k): v for k, v in sorted(texts.items())}},
          open(os.path.join(OUT, "scripts", "text.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

with open(os.path.join(OUT, "scripts", "text.txt"), "w", encoding="utf-8") as f:
    for k in sorted(texts):
        v = texts[k]
        f.write("%s\t%s\n" % (v["addr"], v["text"].replace("\n", "\\n")))

with open(os.path.join(RAW, "scripts", "map_script_tables.json"), "w", encoding="utf-8") as f:
    json.dump(map_script_tables, f, ensure_ascii=False, indent=1)
