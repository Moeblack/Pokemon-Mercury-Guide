# -*- coding: utf-8 -*-
"""人类友好训练家攻略生成器。

输入（只读）：
  wiki_export/world/data/trainers.json   —— 743 条普通记录 + 919/920/921 特殊引用
  wiki_export/world/data/maps.json       —— 地图（地区段）名称
  wiki_export/core/data/items.json       —— 训练家道具中文名
  wiki_export/core/data/moves.json       —— 招式属性中文名
  wiki_export/core/data/species.json     —— 宝可梦中文名（兜底）
  wiki_export/core/data/learnsets.json   —— 默认招式来源（level_up 表）
  trainers_research/README.md            —— 规则文字依据（人工核对，不在脚本内解析）

自有配置：
  data/trainer_location_overrides.json   —— 仅收录有明确依据的实际地点更正，
                                            以及被判为“共用对战场景”的地图键。

输出（只写 player_guide 下自有路径）：
  trainers/NNNN.md  × 743
  trainers/index.md  按实际地区导航
  trainers/by_name.md  同名分记录
  trainers/special.md  919/920/921 特殊构建器
  data/trainers.json / data/trainers_summary.json

正文只保留中文姓名、实际地区／场景区别、队伍配招与性格努力个体；
不展示职业编号、partyFlags／AI 等实现字段，也不展示 ROM 地址与原始字节。
用法：python build_trainers.py [输出根目录]   # 省略时为 player_guide 本身
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

GUIDE = Path(__file__).resolve().parents[1]          # player_guide/
ROOT = GUIDE.parent                                   # 解包研究/
W = ROOT / "wiki_export" / "world" / "data"
C = ROOT / "wiki_export" / "core" / "data"

# 性格对照采用 CFRU asm_defines 的 NATURE_* 常量（NATURE_HARDY=0 …）。
# 本 ROM 研究 README 已确认 15=Modest、11=Hasty，与该对照一致。
NATURE_ZH = {
    0: "勤奋", 1: "孤独", 2: "勇敢", 3: "固执", 4: "顽皮",
    5: "大胆", 6: "坦率", 7: "悠闲", 8: "淘气", 9: "乐天",
    10: "胆小", 11: "急躁", 12: "认真", 13: "爽朗", 14: "天真",
    15: "内敛", 16: "慢吞吞", 17: "冷静", 18: "害羞", 19: "马虎",
    20: "温和", 21: "温顺", 22: "狂妄", 23: "慎重", 24: "浮躁",
}
NATURE_EN = {
    0: "Hardy", 1: "Lonely", 2: "Brave", 3: "Adamant", 4: "Naughty",
    5: "Bold", 6: "Docile", 7: "Relaxed", 8: "Impish", 9: "Lax",
    10: "Timid", 11: "Hasty", 12: "Serious", 13: "Jolly", 14: "Naive",
    15: "Modest", 16: "Mild", 17: "Quiet", 18: "Bashful", 19: "Rash",
    20: "Calm", 21: "Gentle", 22: "Sassy", 23: "Careful", 24: "Quirky",
}
EV_ORDER = [("hp_ev", "HP"), ("atk_ev", "攻击"), ("def_ev", "防御"),
            ("spe_ev", "速度"), ("spa_ev", "特攻"), ("spd_ev", "特防")]

CLASS_LEADER = 84          # 0x54，ROM 中由 cmp #0x54 与馆主队伍确认
SPECIAL_IDS = ["919", "920", "921"]
MOVES_FALLBACK = "按等级生成，未逐只展开"
LEARNSET_MISSING = "缺少该物种的学习表，未生成默认招式"
DEFAULT_MOVES_LABEL = "按基础等级生成的默认招式"
NO_MAP_TEXT = "尚未定位出场地点"
SHARED_DEFAULT = "共用对战场景，实际接战地点未定位"


def load(name, base=W):
    with open(base / name, encoding="utf-8") as fh:
        return json.load(fh)


def pid(i):
    return "%04d" % i


def build(out_root):
    trainers = load("trainers.json")
    recs = trainers["trainers"]
    special = trainers["special_references"]
    maps = load("maps.json")
    items = load("items.json", C)
    moves = load("moves.json", C)
    species = load("species.json", C)
    learnsets = load("learnsets.json", C)
    level_up = (learnsets.get("level_up") or {})

    ov_path = GUIDE / "data" / "trainer_location_overrides.json"
    ov_data = json.loads(ov_path.read_text(encoding="utf-8")) if ov_path.exists() else {}
    shared_label = ov_data.get("shared_scene_label") or SHARED_DEFAULT
    shared_maps = set((ov_data.get("shared_battle_scene_maps") or {}).keys())
    overrides = {int(o["id"]): o for o in ov_data.get("overrides", [])}

    map_index = {(m["group"], m["num"]): m for m in maps}
    item_name = {it["index"]: it["name"] for it in items}
    species_name = {s["species_id"]: s["name"] for s in species}
    type_name = {}
    move_type = {}
    move_name = {}
    for mv in moves:
        t = mv.get("type") or {}
        if t.get("id") is not None:
            type_name.setdefault(t["id"], t.get("name"))
        move_type[mv["move_id"]] = t.get("name")
        move_name[mv["move_id"]] = mv.get("name")

    def area_of(mid):
        try:
            g, n = mid.split(":")
            m = map_index.get((int(g), int(n)))
        except ValueError:
            m = None
        if not m:
            return mid
        return m.get("map_name_zh") or m.get("key") or mid

    def type_label(tid_type):
        return type_name.get(tid_type) or "属性ID %s" % tid_type

    def default_moves(species_id, level):
        """按 ROM 0x09D41E54–0x09D41EC8 算法生成默认招式。

        读学习表（原表顺序），遇首个 level>当前等级停止；取已读最后 4 条；
        依次登记，重复招式跳过不回填。返回 (moves, status)。
        """
        entries = level_up.get(str(species_id))
        if entries is None:
            return None, "learnset_missing"
        read = []
        for e in entries:
            if e.get("level", 0) > level:
                break
            read.append(e)
        picked, seen = [], set()
        for e in read[-4:]:
            mid = e.get("move_id")
            if mid in seen:
                continue
            seen.add(mid)
            picked.append({"move_id": mid,
                           "name": e.get("move_name") or move_name.get(mid, "招式 %s" % mid),
                           "type": move_type.get(mid) or "属性ID %s" % mid})
        return picked, "level_up_default"

    def item_label(pid_):
        if not pid_:
            return "无"
        return item_name.get(pid_, "道具 %s" % pid_)

    def display_name(tid, name):
        if name:
            return name
        return "（空名称 · TRAINER_NONE）" if tid == 0 else "（名称未解出）"

    name_to_ids = defaultdict(list)
    for r in recs:
        name_to_ids[r["name"]].append(r["id"])

    pages = {}
    data_records = []
    area_groups = defaultdict(list)
    empty_ids = []
    nomap_ids = []
    shared_ids = []
    override_ids = []
    null_move_pages = 0
    ev_member_total = 0
    rebuilt_members = 0
    missing_learnset_members = 0
    custom_move_members = 0
    pages_with_default = 0
    double_ids = []
    leader_ids = []

    for r in recs:
        tid = r["id"]
        raw_areas = []
        real_areas = []
        shared_hit = False
        for mid in r["map_ids"]:
            a = area_of(mid)
            if a not in raw_areas:
                raw_areas.append(a)
            if mid in shared_maps:
                shared_hit = True
            elif a not in real_areas:
                real_areas.append(a)

        ov = overrides.get(tid)
        if ov:
            loc_label, loc_kind = ov["actual_location"], "override"
        elif real_areas:
            loc_label, loc_kind = "；".join(real_areas), "real"
        elif shared_hit:
            loc_label, loc_kind = shared_label, "shared"
        else:
            loc_label, loc_kind = NO_MAP_TEXT, "none"

        if not r["map_ids"]:
            nomap_ids.append(tid)
        if r["partySize"] == 0:
            empty_ids.append(tid)
        if ov:
            override_ids.append(tid)
        elif real_areas:
            for a in real_areas:
                area_groups[a].append(tid)
        elif shared_hit:
            shared_ids.append(tid)
        if r["doubleBattle"]:
            double_ids.append(tid)
        if r["trainerClass"] == CLASS_LEADER:
            leader_ids.append(tid)

        party_rows = []
        stats_rows = []
        camomons_note = []
        member_moves = []
        page_has_null_move = False
        page_has_default = False
        custom = r["partyFlags"]["custom_moves"]
        for p in r["party"]:
            sp_name = p.get("species_name") or species_name.get(p.get("species_id")) or "未知"
            if p.get("moves"):
                mlist = [{"name": m["name"], "type": type_label(m["type"])} for m in p["moves"]]
                mv = " ／ ".join("%s（%s）" % (x["name"], x["type"]) for x in mlist)
                m_src = "custom"
                custom_move_members += 1
            elif custom:
                mlist = None
                mv = MOVES_FALLBACK
                m_src = "custom_moves_missing"
                page_has_null_move = True
            else:
                gen, status = default_moves(p.get("species_id"), p.get("level"))
                if status == "learnset_missing":
                    mlist = None
                    mv = LEARNSET_MISSING
                    m_src = "learnset_missing"
                    missing_learnset_members += 1
                else:
                    mlist = gen
                    m_src = "level_up_default"
                    rebuilt_members += 1
                    page_has_default = True
                    mv = "按基础等级生成的默认招式：" + (
                        " ／ ".join("%s（%s）" % (x["name"], x["type"]) for x in gen)
                        if gen else "无")
            member_moves.append((mlist, m_src))
            held = p.get("heldItem_name") or item_label(p.get("heldItem"))
            party_rows.append((p.get("slot", 0) + 1, sp_name, p.get("level"), held, mv,
                               m_src == "level_up_default"))
            spread = p.get("ev_spread")
            if spread:
                ev_member_total += 1
                nid = spread.get("nature")
                evs = " / ".join("%s%d" % (lbl, spread[k]) for k, lbl in EV_ORDER
                                 if spread.get(k))
                ab = spread.get("ability")
                stats_rows.append({
                    "species": sp_name,
                    "nature": NATURE_ZH.get(nid, "性格值 %s" % nid),
                    "nature_en": NATURE_EN.get(nid, str(nid)),
                    "ivs": spread.get("ivs"), "evs": evs or "无分配",
                    "ability_note": ("随机第1/第2特性（Random 1&2）" if ab == 3
                                     else "策略值 %s（不写成确定实际特性）" % ab),
                })
            if p.get("battle_types_camomons_names"):
                camomons_note.append("%s：%s → 实战属性 %s" % (
                    sp_name, " + ".join(p.get("camomons_source_moves") or []),
                    " / ".join(p["battle_types_camomons_names"])))
        if page_has_null_move:
            null_move_pages += 1
        if page_has_default:
            pages_with_default += 1

        pages[tid] = {
            "name": r["name"], "raw_areas": raw_areas, "real_areas": real_areas,
            "shared_hit": shared_hit, "loc_label": loc_label, "loc_kind": loc_kind,
            "ov": ov, "double": r["doubleBattle"], "party_rows": party_rows,
            "has_default": page_has_default,
            "stats_rows": stats_rows, "camomons_note": camomons_note,
            "size": r["partySize"],
            "items": [item_label(x) for x in r["items"] if x],
            "special_rules": r["special_rules"], "forced_shiny": r["trainer_forced_shiny"],
        }
        data_records.append({
            "id": tid, "name": r["name"],
            "display_name": display_name(tid, r["name"]),
            "location": loc_label,
            "location_kind": loc_kind,
            "raw_areas": raw_areas, "map_ids": r["map_ids"],
            "double_battle": bool(r["doubleBattle"]), "party_size": r["partySize"],
            "trainer_items": [item_label(x) for x in r["items"] if x],
            "special_rules": r["special_rules"],
            "forced_shiny": r["trainer_forced_shiny"],
            "party": [{
                "slot": p.get("slot"),
                "species_id": p.get("species_id"),
                "species": p.get("species_name") or species_name.get(p.get("species_id")),
                "level": p.get("level"),
                "held_item": p.get("heldItem_name") or item_label(p.get("heldItem")),
                "moves": member_moves[idx][0],
                "moves_source": member_moves[idx][1],
                "moves_note": (None if member_moves[idx][0] else
                               (LEARNSET_MISSING if member_moves[idx][1] == "learnset_missing"
                                else MOVES_FALLBACK)),
                "moves_algorithm": ("level_up_last4_by_base_level"
                                    if member_moves[idx][1] == "level_up_default" else None),
                "nature": None if not p.get("ev_spread") else
                          NATURE_ZH.get(p["ev_spread"].get("nature")),
                "ivs": None if not p.get("ev_spread") else p["ev_spread"].get("ivs"),
                "evs": None if not p.get("ev_spread") else
                       {k: p["ev_spread"][k] for k, _ in EV_ORDER if p["ev_spread"].get(k)},
                "ability_strategy": None if not p.get("ev_spread") else p["ev_spread"].get("ability"),
                "forced_shiny": p.get("forced_shiny"),
                "camomons_battle_types": p.get("battle_types_camomons_names"),
            } for idx, p in enumerate(r["party"])],
            "page": "trainers/%s.md" % pid(tid),
        })

    # ---------- 单页 ----------
    def render_page(tid):
        pg = pages[tid]
        name = display_name(tid, pg["name"])
        L = []
        L.append("# %s｜%s" % (name, pg["loc_label"]))
        L.append("")
        L.append("> %s ｜ 队伍 %d 只 ｜ %s" % (
            "双打" if pg["double"] else "单打", pg["size"], pg["loc_label"]))
        L.append("")
        L.append("## 概况")
        L.append("")
        L.append("- **名称**：%s" % name)
        L.append("- **对战形式**：%s" % ("双打" if pg["double"] else "单打"))
        L.append("- **队伍规模**：%d 只" % pg["size"])
        L.append("- **实际地区／场景**：%s" % pg["loc_label"])
        if pg["loc_kind"] == "override":
            L.append("- **更正依据**：%s" % (pg["ov"].get("evidence") or "用户及本轮对白确认"))
        if pg["loc_kind"] == "shared" or (pg["shared_hit"] and pg["loc_kind"] != "override"):
            L.append("- **场景说明**：资料关联的是共用对战场景，不能作为 NPC 的实际接战地点；"
                     "实际接战地点未定位。")
        if pg["loc_kind"] == "none":
            L.append("- **场景说明**：资料没有关联到任何出场地点，也未据此猜测城市。")
        L.append("- **训练家道具**：%s" % ("、".join(pg["items"]) if pg["items"] else "无"))
        peers = [i for i in name_to_ids[pg["name"]] if i != tid]
        if peers and pg["name"]:
            L.append("- **同名记录（不合并）**：%s" % "、".join(
                "[%s %s](%s.md)" % (pid(i), pages[i]["name"], pid(i)) for i in peers))
        L.append("")

        L.append("## 队伍")
        L.append("")
        if tid == 0:
            L.append("该记录为空队伍占位（TRAINER_NONE），没有任何队伍成员。")
        else:
            L.append("*等级为该记录内的基础队伍等级。*")
            L.append("")
            L.append("| # | 宝可梦 | 等级 | 携带 | 招式 |")
            L.append("|---|--------|------|------|------|")
            for slot, sp, lv, held, mv, _dft in pg["party_rows"]:
                L.append("| %d | %s | %s | %s | %s |" % (slot, sp, lv, held, mv))
            if pg["has_default"]:
                L.append("")
                L.append("*标注“%s”的成员由该物种等级学习表按基础等级生成；"
                         "运行时等级缩放时不代表最终招式。*" % DEFAULT_MOVES_LABEL)
        L.append("")

        L.append("## 性格 · 努力值 · 个体值")
        L.append("")
        if pg["stats_rows"]:
            for s in pg["stats_rows"]:
                L.append("- **%s**：性格 %s（%s）；个体值 %s；努力值 %s；特性：%s。" % (
                    s["species"], s["nature"], s["nature_en"], s["ivs"], s["evs"],
                    s["ability_note"]))
        else:
            L.append("该记录未提供逐只的性格／努力值／个体值配置；不套用原版生成算法。")
        L.append("")

        L.append("## 已知特殊规则")
        L.append("")
        rule_lines = []
        if "camomons_first_two_moves" in pg["special_rules"]:
            rule_lines.append(
                "- **满金道馆拟态规则（CAMOMONS）**：战斗内所有宝可梦的属性改为前两个招式的属性"
                "（双方适用）。")
            for c in pg["camomons_note"]:
                rule_lines.append("  - %s" % c)
        if pg["forced_shiny"]:
            slots = "、".join(str(x + 1) for x in pg["forced_shiny"].get("slots", []))
            rule_lines.append(
                "- **强制闪光**：第 %s 号队伍成员被强制闪光（循环重掷，保留原派生值）。" % slots)
        if not rule_lines:
            rule_lines.append("该记录无已确认的特殊规则。")
        L.extend(rule_lines)
        if peers and pg["name"]:
            L.append("")
            L.append("> 同名提示：本页规则只属于编号 %s，不套用到其它同名记录。" % tid)
        L.append("")
        L.append("---")
        L.append("")
        L.append("溯源：`wiki_export/world/data/trainers.json` 指针 `/trainers/%d`；"
                 "地区名来自 `wiki_export/world/data/maps.json`；道具名来自 "
                 "`wiki_export/core/data/items.json`；特殊规则文字依据 "
                 "`trainers_research/README.md`。稳定编号 %s。" % (tid, pid(tid)))
        if pg["loc_kind"] == "override" or pg["loc_kind"] == "shared" or (
                pg["shared_hit"] and pg["loc_kind"] != "override"):
            L.append("")
            L.append("资料原关联场景（未更正的原值）：%s。" % (
                "；".join(pg["raw_areas"]) if pg["raw_areas"] else NO_MAP_TEXT))
        L.append("")
        L.append("正文不展示 ROM 地址与原始字节。")
        L.append("")
        return "\n".join(L)

    # ---------- index.md ----------
    def render_index():
        L = ["# 训练家名录（按实际地区导航）", ""]
        L.append("共 **743** 条普通训练家记录（编号 0–742），同名记录不合并；"
                 "每条记录指向独立页面。")
        L.append("")
        if override_ids:
            L.append("## 实际地区更正")
            L.append("")
            L.append("以下记录依据用户及本轮对白确认更正了实际地区；"
                     "资料原关联场景保留在各页溯源。")
            L.append("")
            for i in sorted(override_ids):
                L.append("- [%s %s](%s.md) —— %s（队伍 %d 只）" % (
                    pid(i), pages[i]["name"], pid(i), pages[i]["loc_label"],
                    pages[i]["size"]))
            L.append("")
        if empty_ids:
            L.append("## 空队伍占位")
            L.append("")
            for i in empty_ids:
                L.append("- [%s %s](%s.md) —— 无队伍成员" % (
                    pid(i), display_name(i, pages[i]["name"]), pid(i)))
            L.append("")
        L.append("## 道馆馆主快捷链接")
        L.append("")
        L.append("下表为馆主记录，按记录与实际地区列出，不推断再战阶段。")
        L.append("")
        for i in sorted(leader_ids):
            pg = pages[i]
            L.append("- [%s %s](%s.md) —— %s（队伍 %d 只）" % (
                pid(i), pg["name"], pid(i), pg["loc_label"], pg["size"]))
        L.append("")
        L.append("## 地区导航")
        L.append("")
        for area in sorted(area_groups, key=lambda a: (a or "")):
            L.append("### %s" % area)
            L.append("")
            for i in area_groups[area]:
                L.append("- [%s %s](%s.md)" % (pid(i), pages[i]["name"], pid(i)))
            L.append("")
        if shared_ids:
            L.append("## 共用对战场景（实际接战地点未定位）")
            L.append("")
            L.append("以下记录只关联到共用对战场景，不能当作 NPC 实际所在地。")
            L.append("")
            for i in shared_ids:
                L.append("- [%s %s](%s.md)" % (
                    pid(i), display_name(i, pages[i]["name"]), pid(i)))
            L.append("")
        L.append("## 尚未定位出场地点")
        L.append("")
        L.append("以下 %d 条记录没有取到已关联地图。" % len(nomap_ids))
        L.append("")
        for i in nomap_ids:
            L.append("- [%s %s](%s.md)" % (
                pid(i), display_name(i, pages[i]["name"]), pid(i)))
        L.append("")
        L.append("## 特殊编号")
        L.append("")
        L.append("编号 %s 属超出普通 743 表的特殊构建器引用，"
                 "队伍与人物未确证，另见 [special.md](special.md)。" % "、".join(SPECIAL_IDS))
        L.append("")
        L.append("同名分记录见 [by_name.md](by_name.md)。")
        L.append("")
        return "\n".join(L)

    # ---------- by_name.md ----------
    def render_by_name():
        groups = [(n, sorted(ids)) for n, ids in name_to_ids.items()]
        groups.sort(key=lambda kv: kv[1][0])
        dup_groups = [g for g in groups if len(g[1]) > 1]
        L = ["# 按名称检索（同名分记录）", ""]
        L.append("共 **%d** 个不同名称、**743** 条记录；其中 **%d** 个名称对应多条记录，"
                 "同名一律不合并。" % (len(groups), len(dup_groups)))
        L.append("")
        for nm, ids in groups:
            disp = display_name(ids[0], nm)
            if len(ids) > 1:
                L.append("## %s（%d 条）" % (disp, len(ids)))
            else:
                L.append("## %s" % disp)
            L.append("")
            for i in ids:
                pg = pages[i]
                L.append("- [%s %s](%s.md) —— %s；%s；队伍 %d 只" % (
                    pid(i), display_name(i, pg["name"]), pid(i), pg["loc_label"],
                    "双打" if pg["double"] else "单打", pg["size"]))
            L.append("")
        return "\n".join(L)

    # ---------- special.md ----------
    def render_special():
        L = ["# 特殊编号（超普通表）", ""]
        L.append("编号 919／920／921 属现行队伍构建器在普通 743 表之外的引用分支，"
                 "**不是**普通表的缺失记录，也不能按普通记录补齐队伍。其实际人物与队伍未确证。")
        L.append("")
        for sid in SPECIAL_IDS:
            info = special.get(sid)
            L.append("## 编号 %s" % sid)
            L.append("")
            if not info:
                L.append("该编号在特殊引用资料中没有记录。")
                L.append("")
                continue
            usages = info.get("usages", [])
            modes = Counter(u.get("mode") for u in usages)
            stypes = info.get("script_types") or []
            cls = info.get("classification")
            cls_zh = {"special_builder_not_missing_ordinary_record":
                      "特殊构建器引用（非普通 743 表缺失记录）"}.get(cls, cls or "未注明")
            L.append("- **归类**：%s" % cls_zh)
            L.append("- **脚本类型**：%s" % (
                "、".join("trainerbattle 类型 %s（教程战）" % t for t in stypes)
                if stypes else "未注明"))
            L.append("- **引用模式**：%s" % (
                "、".join("%s×%d" % (m, c) for m, c in sorted(
                    ((k, v) for k, v in modes.items() if k is not None), key=lambda x: x[0]))
                if modes else "未注明"))
            L.append("- **引用次数**：%d" % len(usages))
            L.append("- **人物身份**：未确证")
            L.append("- **队伍**：未确证（不套用普通表／不自行生成）")
            L.append("- **说明**：%s" % (info.get("reason") or "未注明"))
            L.append("")
        L.append("---")
        L.append("")
        L.append("溯源：`wiki_export/world/data/trainers.json` 的 `special_references`；"
                 "依据与边界见 `trainers_research/README.md` 特殊 ID 分流一节。")
        L.append("")
        L.append("正文不展示 ROM 地址与原始字节。")
        L.append("")
        return "\n".join(L)

    # ---------- 写出 ----------
    outdir = out_root / "trainers"
    outdir.mkdir(parents=True, exist_ok=True)
    for r in recs:
        (outdir / (pid(r["id"]) + ".md")).write_text(render_page(r["id"]), encoding="utf-8")
    (outdir / "index.md").write_text(render_index(), encoding="utf-8")
    (outdir / "by_name.md").write_text(render_by_name(), encoding="utf-8")
    (outdir / "special.md").write_text(render_special(), encoding="utf-8")

    summary = {
        "generated_pages": len(recs),
        "special_ids": SPECIAL_IDS,
        "areas": len(area_groups),
        "location_overrides": len(override_ids),
        "shared_battle_scene_records": len(shared_ids),
        "trainers_with_area": sum(len(v) for k, v in area_groups.items()),
        "trainers_without_area": len(nomap_ids),
        "empty_party_placeholders": len(empty_ids),
        "double_battle": len(double_ids),
        "pages_with_level_generated_moves": null_move_pages,
        "members_with_default_moves": rebuilt_members,
        "pages_with_default_moves": pages_with_default,
        "members_missing_learnset": missing_learnset_members,
        "members_using_custom_moves": custom_move_members,
        "members_with_ev_spread": ev_member_total,
        "forced_shiny_records": sum(1 for r in recs if r["trainer_forced_shiny"]),
        "special_rule_records": sum(1 for r in recs if r["special_rules"]),
        "gym_leader_records_class_0x54": len(leader_ids),
        "duplicate_name_groups": sum(1 for n, ids in name_to_ids.items() if len(ids) > 1),
        "distinct_names": len(name_to_ids),
        "unnamed_records": sum(1 for r in recs if not r["name"]),
    }
    (out_root / "data").mkdir(parents=True, exist_ok=True)
    (out_root / "data" / "trainers.json").write_text(json.dumps({
        "note": "人类友好结构化导出；正文页面见 trainers/NNNN.md。"
                "party.moves_source: custom=原配招，level_up_default=按基础等级生成的默认招式，"
                "learnset_missing=缺少学习表未生成；"
                "level_up_default 的算法标记见 data/trainer_default_moves_evidence.json，"
                "运行时等级缩放时不代表最终招式。",
        "trainers": data_records,
        "special_references": special,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    (out_root / "data" / "trainers_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    build(Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else GUIDE)
