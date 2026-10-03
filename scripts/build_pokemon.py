# -*- coding: utf-8 -*-
"""生成 player_guide 宝可梦版块。

输入（只读）：
  wiki_export/core/data/species.json
  wiki_export/core/data/evolutions.json
  wiki_export/core/data/national_dex.json
  wiki_export/world/data/acquisition_by_species.json
  wiki_export/world/data/maps.json
  wiki_export/world/data/encounters.json
  wiki_export/core/data/items.json / moves.json（进化道具名/招式名对应表）
  wiki_export/enrichment/reference_only/evolution_methods.json（method 符号）

输出：
  player_guide/pokemon/NNNN.md（内部槽 0000..1553 全量）
  player_guide/pokemon/index.md
  player_guide/pokemon/by_location.md
  player_guide/pokemon/forms.md
  player_guide/data/pokemon.json
  player_guide/data/pokemon_summary.json

运行：python player_guide/scripts/build_pokemon.py
"""
import hashlib
import json
import os
import re
from collections import OrderedDict, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
WIKI = os.path.join(ROOT, "wiki_export")
GUIDE = os.path.join(ROOT, "player_guide")
OUT_POKE = os.path.join(GUIDE, "pokemon")
OUT_DATA = os.path.join(GUIDE, "data")

# 从 player_guide/pokemon/*.md 指向 wiki_export 的相对前缀
REL = "../../wiki_export/"
REL_DATA = "../wiki_export/"

TIME_ZH = {
    "morning": "清晨 05:00–09:59",
    "day": "白天 10:00–16:59",
    "evening": "黄昏 17:00–18:59",
    "night": "夜晚 19:00–04:59",
}
TIME_ORDER = ["morning", "day", "evening", "night"]

METHOD_ZH = {
    "land": "地面·草丛/洞窟",
    "water": "水面·冲浪",
    "old_rod": "钓鱼·旧钓竿",
    "good_rod": "钓鱼·好钓竿",
    "super_rod": "钓鱼·超级钓竿",
    "fishing": "钓鱼",
    "rock_smash_headbutt": "碎岩 / 撞树（共用槽，未区分）",
    "broadcast": "广播遭遇",
    "broadcast_fallback": "广播（兜底表）",
}

WEEKDAY_ZH = {
    0: ("周日", "伽勒尔之声"),
    3: ("周三", "丰缘之声"),
    4: ("周四", "神奥之声"),
}

FALLBACK_ZH = {
    "default_and_sunday": "周日及未匹配日期的默认兜底表",
    "wednesday_miss": "周三未播放对应地区之声时的兜底表",
    "thursday_miss": "周四未播放对应地区之声时的兜底表",
}

CONDITION_ZH = {
    "existing_static_evidence_not_reachability": "静态遭遇表证据；未证明实际可达性",
    "broadcast_gating_required_internal_slot_weight_only": "仅有内部选槽权重；广播门控旗标语义未穷举",
    "fallback_selection_and_broadcast_gates_required": "兜底选择与广播门控条件未穷举",
    "instruction_evidence_not_story_reachability": "脚本指令证据；未证明剧情可达性",
    "swarm_activation_not_proven_by_static_table": "群聚激活方式未由静态表证明",
}

CATEGORY_ZH = {
    "wild": "野生遭遇",
    "broadcast": "广播遭遇",
    "swarm": "群聚（大量出现）",
    "gift": "赠送",
    "egg": "蛋",
    "static_battle_candidate": "剧情战斗候选",
}

# 进化 method 符号 -> 中文条件模板。{} 为参数渲染结果。
EVO_SYMBOL_ZH = {
    "EVO_NONE": "无进化（与前一进化条件重复的占位项）",
    "EVO_FRIENDSHIP": "亲密度足够后升级",
    "EVO_FRIENDSHIP_DAY": "白天亲密度足够后升级",
    "EVO_FRIENDSHIP_NIGHT": "夜晚亲密度足够后升级",
    "EVO_LEVEL": "达到 Lv.{p}",
    "EVO_TRADE": "通信交换",
    "EVO_TRADE_ITEM": "携带{p}通信交换",
    "EVO_ITEM": "使用{p}",
    "EVO_LEVEL_ATK_GT_DEF": "攻击 > 防御时达到 Lv.{p}",
    "EVO_LEVEL_ATK_EQ_DEF": "攻击 = 防御时达到 Lv.{p}",
    "EVO_LEVEL_ATK_LT_DEF": "攻击 < 防御时达到 Lv.{p}",
    "EVO_LEVEL_SILCOON": "达到 Lv.{p}（性格值分支·甲壳茧型）",
    "EVO_LEVEL_CASCOON": "达到 Lv.{p}（性格值分支·盾甲茧型）",
    "EVO_LEVEL_NINJASK": "达到 Lv.{p}（土居忍士分支·铁面忍者）",
    "EVO_LEVEL_SHEDINJA": "达到 Lv.{p}（队伍留有空位并持有精灵球时·脱壳忍者）",
    "EVO_BEAUTY": "美丽度达标后升级",
    "EVO_RAINY_FOGGY_OW": "在雨天或雾天（野外天气）下升级",
    "EVO_MOVE_TYPE": "学会{p}后升级（新招式属性判定）",
    "EVO_TYPE_IN_PARTY": "队伍中存在特定类型宝可梦时升级（类型参数 {p} 未释明）",
    "EVO_MAP": "在特定地点升级：{p}",
    "EVO_MALE_LEVEL": "雄性达到 Lv.{p}",
    "EVO_FEMALE_LEVEL": "雌性达到 Lv.{p}",
    "EVO_LEVEL_NIGHT": "夜晚达到 Lv.{p}",
    "EVO_LEVEL_DAY": "白天达到 Lv.{p}",
    "EVO_HOLD_ITEM_NIGHT": "夜晚携带{p}升级",
    "EVO_HOLD_ITEM_DAY": "白天携带{p}升级",
    "EVO_MOVE": "学会{p}后升级",
    "EVO_OTHER_PARTY_MON": "队伍中持有{p}时升级",
    "EVO_LEVEL_SPECIFIC_TIME_RANGE": "在特定时段内达到 Lv.{p}（时段参数未在数据中给出）",
    "EVO_FLAG_SET": "满足特定事件旗标条件（旗标语义未释明）",
    "EVO_CRITICAL_HIT": "满足特定战斗条件后升级（EVO_CRITICAL_HIT；阈值参数 {p}，语义未释明）",
    "EVO_NATURE_HIGH": "持有特定高影响性格时升级（性格参数 {p}，名称未释明）",
    "EVO_NATURE_LOW": "持有特定低影响性格时升级（性格参数 {p}，名称未释明）",
    "EVO_DAMAGE_LOCATION": "在特定地点受伤后升级（地点参数 {p}，语义未释明）",
    "EVO_ITEM_LOCATION": "在特定地点使用{p}",
    "EVO_LEVEL_HOLD_ITEM": "携带特定道具时达到 Lv.{p}",
    "EVO_ITEM_HOLD_ITEM": "对携带{p}的宝可梦使用特定道具（第二道具参数未在数据中给出）",
    "EVO_MOVE_MALE": "雄性学会{p}后升级",
    "EVO_MOVE_FEMALE": "雌性学会{p}后升级",
    "EVO_ITEM_NIGHT": "夜晚使用{p}",
    "EVO_GIGANTAMAX": "超极巨化（GFactor）",
    "EVO_MEGA": "Mega 进化（附加 Mega 石）",
}

# 参数语义：按符号决定 param 的渲染方式
P_LEVEL = {"EVO_LEVEL", "EVO_LEVEL_ATK_GT_DEF", "EVO_LEVEL_ATK_EQ_DEF",
           "EVO_LEVEL_ATK_LT_DEF", "EVO_LEVEL_SILCOON", "EVO_LEVEL_CASCOON",
           "EVO_LEVEL_NINJASK", "EVO_LEVEL_SHEDINJA", "EVO_RAINY_FOGGY_OW",
           "EVO_MALE_LEVEL", "EVO_FEMALE_LEVEL", "EVO_LEVEL_NIGHT",
           "EVO_LEVEL_DAY", "EVO_LEVEL_SPECIFIC_TIME_RANGE",
           "EVO_LEVEL_HOLD_ITEM"}
P_ITEM = {"EVO_ITEM", "EVO_TRADE_ITEM", "EVO_ITEM_NIGHT", "EVO_ITEM_LOCATION",
          "EVO_HOLD_ITEM_NIGHT", "EVO_HOLD_ITEM_DAY", "EVO_MEGA",
          "EVO_ITEM_HOLD_ITEM"}
P_MOVE = {"EVO_MOVE", "EVO_MOVE_TYPE", "EVO_MOVE_MALE", "EVO_MOVE_FEMALE"}
P_PARAM_NUM = {"EVO_TYPE_IN_PARTY", "EVO_FLAG_SET", "EVO_CRITICAL_HIT",
               "EVO_NATURE_HIGH", "EVO_NATURE_LOW", "EVO_DAMAGE_LOCATION"}

BATTLE_FORM_SYMBOLS = {"EVO_MEGA", "EVO_GIGANTAMAX"}


def load(rel):
    with open(os.path.join(WIKI, rel), encoding="utf-8") as f:
        return json.load(f)


def sha256_of(rel):
    h = hashlib.sha256()
    with open(os.path.join(WIKI, rel), "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    species = load("core/data/species.json")
    evolutions = load("core/data/evolutions.json")
    national = load("core/data/national_dex.json")
    acq = load("world/data/acquisition_by_species.json")
    maps = load("world/data/maps.json")
    enc = load("world/data/encounters.json")
    items = load("core/data/items.json")
    moves = load("core/data/moves.json")
    evo_methods = load("enrichment/reference_only/evolution_methods.json")

    item_by_index = {i["index"]: i["name"] for i in items}
    item_price_by_index = {i["index"]: i.get("price") for i in items}
    move_by_id = {m["move_id"]: m["name"] for m in moves}
    move_by_index = {i: m["name"] for i, m in enumerate(moves)}
    method_by_value = {r["value"]: r["name"] for r in evo_methods["records"]}

    map_by_id = {}
    mapsec_name = {}
    for m in maps:
        mid = "%s:%s" % (m["group"], m["num"])
        map_by_id[mid] = m
        s = m.get("region_map_section_id")
        if s is not None and s not in mapsec_name and m.get("map_name_zh"):
            mapsec_name[s] = m["map_name_zh"]

    n_maps = len(map_by_id)
    n_items = len(item_by_index)
    n_moves = len(move_by_id)
    n_methods = len(method_by_value)

    # ---------- 索引构建 ----------
    evo_out = {}          # species_id -> [evolution dict + source]
    for e in evolutions:
        evo_out.setdefault(e["species_id"], []).extend(e["evolutions"])
    evo_in = defaultdict(list)  # target -> [(src_id, src_name, evo)]
    for sid, evs in evo_out.items():
        sname = None
        for ev in evs:
            evo_in[ev["target_species_id"]].append((sid, ev))

    name_by_id = {}
    for s in species:
        name_by_id[s["species_id"]] = s["name"]

    acq_by_id = {}
    for k, v in acq.items():
        acq_by_id[int(k)] = v

    # 无全国号的槽被引用情况
    slots = sorted(species, key=lambda s: s["species_id"])

    # 统计
    stats = {
        "total_slots": len(slots),
        "slots_with_national_dex": sum(1 for s in slots if s["national_dex_number"] is not None),
        "placeholder_slots": sum(1 for s in slots if s.get("is_placeholder_warning")),
        "slots_without_national_dex": sum(1 for s in slots if s["national_dex_number"] is None),
        "by_category": defaultdict(int),
        "species_with_acquisition": len(acq_by_id),
        "species_with_evolution_out": len(evo_out),
        "species_with_evolution_in": len(evo_in),
        "mega_target_slots": 0,
        "gmax_target_slots": 0,
        "unresolved_evo_symbols": defaultdict(int),
        "unknown_item_params": 0,
        "item_param_zero_price": 0,
        "unknown_move_params": 0,
        "eval_map_param_unmapped": 0,
        "plain_slots_no_source": 0,
        "field_gaps": [],
    }

    placeholders_without_dex = sum(
        1 for s in slots if s.get("is_placeholder_warning") and s["national_dex_number"] is None)
    placeholders_with_dex = sum(
        1 for s in slots if s.get("is_placeholder_warning") and s["national_dex_number"] is not None)
    special_no_dex = sum(
        1 for s in slots if (not s.get("is_placeholder_warning")) and s["national_dex_number"] is None)
    stats.update({
        "placeholders_without_dex": placeholders_without_dex,
        "placeholders_with_dex": placeholders_with_dex,
        "special_no_dex": special_no_dex,
    })

    out_pages = {}
    page_records = {}
    by_location = defaultdict(list)   # map_id -> [record]
    forms_placeholder = []
    forms_national_dup = []
    dex_counter = defaultdict(list)
    for s in slots:
        if s["national_dex_number"] is not None:
            dex_counter[s["national_dex_number"]].append(s["species_id"])

    # ---------- 渲染辅助 ----------
    def sprite_link(s):
        media = s.get("media") or {}
        groups = (media.get("groups") or {}).get("front_normal") or []
        if media.get("status") == "linked" and groups:
            p = groups[0].get("export_path")
            if p:
                return REL + p
        return None

    def map_link(mid):
        m = map_by_id.get(mid)
        if not m or not m.get("page_path"):
            return None, (m.get("map_name_zh") if m else None)
        return REL + m["page_path"], m.get("map_name_zh")

    def map_png_link(mid):
        m = map_by_id.get(mid)
        if m and m.get("map_png"):
            return REL + m["map_png"]
        return None

    def fmt_level(level):
        if not level:
            return None
        if "value" in level:
            return "Lv.%s" % level["value"]
        if level.get("min") is not None and level.get("max") is not None:
            if level["min"] == level["max"]:
                return "Lv.%s" % level["min"]
            return "Lv.%s–%s" % (level["min"], level["max"])
        return None

    def item_name(idx):
        if idx in item_by_index:
            return item_by_index[idx]
        stats["unknown_item_params"] += 1
        return "道具编号 %s（名称未在道具表命中）" % idx

    def item_link(idx):
        """进化道具名 -> ../items/NNNN.md 链接。"""
        nm = item_by_index.get(idx)
        if nm is None:
            stats["unknown_item_params"] += 1
            return "道具编号 %s（名称未在道具表命中）" % idx
        return "[%s](../items/%04d.md)" % (nm, idx)

    def move_name(pid):
        if pid in move_by_id:
            return move_by_id[pid]
        if pid in move_by_index:
            return move_by_index[pid]
        stats["unknown_move_params"] += 1
        return "招式编号 %s（名称未在招式表命中）" % pid

    def render_evo_condition(ev, target):
        method = ev["method"]
        sym = ev.get("reference_method_symbol") or method_by_value.get(method)
        p = ev.get("param")
        if sym is None:
            stats["unresolved_evo_symbols"]["method=%s" % method] += 1
            return "条件未释明（进化方式编号 %s）" % method, None, None
        if sym in P_LEVEL:
            pz = p
        elif sym in P_ITEM:
            pz = item_link(p)
        elif sym in P_MOVE:
            pz = move_name(p)
        elif sym == "EVO_MAP":
            nm = mapsec_name.get(p)
            if nm:
                pz = nm
            else:
                stats["eval_map_param_unmapped"] += 1
                pz = "地图区域编号 %s（名称未在地图表命中）" % p
        elif sym == "EVO_OTHER_PARTY_MON":
            pz = name_by_id.get(p, "物种编号 %s" % p)
        elif sym in P_PARAM_NUM:
            pz = p
        else:
            pz = p
        tmpl = EVO_SYMBOL_ZH.get(sym)
        if tmpl is None:
            stats["unresolved_evo_symbols"][sym] += 1
            return "条件未释明（符号 %s）" % sym, sym, None
        text = tmpl.format(p=pz)
        if sym in P_ITEM and sym != "EVO_MEGA" and p is not None and item_price_by_index.get(p) == 0:
            text += "（该道具表项标价 0，疑为占位值，未能确认）"
            stats["item_param_zero_price"] += 1
        return text, sym, p

    # ---------- 获取分组 ----------
    def group_wild(entries):
        """返回 (合并展示行, 逐地图行)。

        合并规则：同一物种在同一地图、同一方式、同一时段的槽合并；
        完全相同（同名地图、同方式、同时段、同等级与权重）的行再合并为一行，
        并保留全部地图链接。
        """
        per = OrderedDict()
        for e in entries:
            key = (e.get("map_id"), e.get("map_name"), e.get("method"), e.get("time"))
            per.setdefault(key, []).append(e)
        rows = []
        for (mid, mname, method, time), es in per.items():
            lv = fmt_level({"min": min(x["level"]["min"] for x in es),
                            "max": max(x["level"]["max"] for x in es)}) if es and es[0].get("level") else None
            weights = [x.get("conditional_slot_weight") for x in es]
            weights = [w for w in weights if w is not None]
            rates = sorted({x.get("encounter_rate") for x in es if x.get("encounter_rate") is not None})
            sec = None
            mm = map_by_id.get(mid)
            if mm:
                sec = mapsec_name.get(mm.get("region_map_section_id"))
            rows.append({
                "map_id": mid, "map_name": mname, "method": method, "time": time,
                "level": lv, "weights": weights, "rate": rates,
                "section": sec,
                "slots": len(es),
                "condition_status": es[0].get("condition_status"),
            })
        per_map = list(rows)
        merged = OrderedDict()
        for r in rows:
            k = (r["map_name"], r["method"], r["time"], r["level"],
                 tuple(r["weights"]), tuple(r["rate"]))
            if k not in merged:
                merged[k] = dict(r, map_ids=[r["map_id"]])
            else:
                if r["map_id"] not in merged[k]["map_ids"]:
                    merged[k]["map_ids"].append(r["map_id"])
        out = list(merged.values())
        out.sort(key=lambda r: (TIME_ORDER.index(r["time"]) if r["time"] in TIME_ORDER else 9,
                                r["map_name"] or "", r["method"] or ""))
        return out, per_map

    def group_broadcast(entries):
        g = OrderedDict()
        for e in entries:
            if e.get("method") == "broadcast_fallback":
                key = ("fallback", e.get("fallback_group"))
            else:
                key = ("weekday", e.get("day_of_week"), e.get("map_id"), e.get("map_name"))
            g.setdefault(key, []).append(e)
        rows = []
        for key, es in g.items():
            if key[0] == "fallback":
                rows.append({"kind": "fallback", "group": key[1],
                             "weights": [x.get("conditional_slot_weight") for x in es],
                             "status": es[0].get("condition_status")})
            else:
                _, dow, mid, mname = key
                rows.append({"kind": "weekday", "dow": dow, "map_id": mid, "map_name": mname,
                             "weights": [x.get("conditional_slot_weight") for x in es],
                             "status": es[0].get("condition_status")})
        rows.sort(key=lambda r: (0 if r["kind"] == "weekday" else 1, r.get("dow") if r.get("dow") is not None else 9))
        return rows

    def group_swarm(entries):
        g = OrderedDict()
        for e in entries:
            key = (e.get("mapsec_id"), e.get("map_name"))
            g.setdefault(key, []).append(e)
        return [{"mapsec_id": k[0], "map_name": k[1], "count": len(v),
                 "status": v[0].get("condition_status")} for k, v in g.items()]

    def group_scripted(entries):
        g = OrderedDict()
        for e in entries:
            key = (e.get("map_id"), e.get("map_name"))
            g.setdefault(key, []).append(e)
        rows = []
        for (mid, mname), es in g.items():
            lvs = sorted({fmt_level(x.get("level")) for x in es if x.get("level")})
            rows.append({"map_id": mid, "map_name": mname, "levels": lvs,
                         "count": len(es), "status": es[0].get("condition_status")})
        return rows

    # ---------- 生成每页 ----------
    def build_page(s, rec):
        sid = s["species_id"]
        num = s["internal_number"]
        dex = s["national_dex_number"]
        ph = bool(s.get("is_placeholder_warning"))
        title = s["name"] + ("（全国图鉴 No.%04d）" % dex if dex is not None else "（无全国图鉴号）")
        lv = ["# %s" % title, ""]
        if ph:
            lv.append("> **占位/无效槽**：本槽不是一种可获得的宝可梦，不作为正常物种页陈列。")
            lv.append("")
        elif rec.get("is_battle_form_only"):
            lv.append("> **战斗形态槽**：只在战斗中通过 Mega 进化 / 超极巨化出现，"
                      "不是可永久获得的独立个体。")
            lv.append("")
        sp = sprite_link(s) if not ph else None
        if sp:
            lv.append("![%s 正面图](%s)" % (s["name"], sp))
            lv.append("")

        entries = rec.get("entries", [])
        cats = defaultdict(list)
        for e in entries:
            cats[e["category"]].append(e)

        lv.append("## 怎样获得")
        lv.append("")
        pre = rec.get("pre_evolutions", [])
        if ph:
            lv.append("占位/无效槽，没有获取方式。完整清单见 [forms.md](forms.md)。")
            lv.append("")
        else:
            if pre:
                lv.append("**进化获得**")
                lv.append("")
                for item in pre:
                    src_id = item["source_species_id"]
                    cond, sym, p = render_evo_condition(item["evolution"], sid)
                    sname = name_by_id.get(src_id, "内部槽 %04d" % src_id)
                    lv.append("- ← [%s](%04d.md) ｜ %s" % (sname, src_id, cond))
                    if sym in BATTLE_FORM_SYMBOLS:
                        lv.append("  - 战斗形态变化来源，不是永久获得一只独立个体。")
                lv.append("")

            got_any = False
            if cats.get("wild"):
                got_any = True
                lv.append("### 野生遭遇")
                lv.append("")
                merged_wild, per_map_wild = group_wild(cats["wild"])
                for r in merged_wild:
                    lv.append("- **%s**%s ｜ %s ｜ %s ｜ %s ｜ 选槽权重 %s%s%s"
                              % (r["map_name"] or r["map_ids"][0],
                                 ("（地区：%s）" % r["section"]) if r.get("section") and r["section"] != r["map_name"] else "",
                                 TIME_ZH.get(r["time"], r["time"] or "时段未标"),
                                 METHOD_ZH.get(r["method"], r["method"] or "方式未标"),
                                 r["level"] or "等级未标",
                                 "、".join(str(w) for w in r["weights"]) or "未标",
                                 "（合计 %s）" % sum(r["weights"]) if len(r["weights"]) > 1 else "",
                                 (" ｜ 遇敌率表值 %s" % "、".join(str(x) for x in r["rate"])) if r["rate"] else ""))
                    links = []
                    for mid in r["map_ids"]:
                        lk, nm = map_link(mid)
                        if lk:
                            links.append("[%s %s](%s)" % (nm, mid, lk))
                    if links:
                        lv.append("  - 地图条目：%s" % "、".join(links))
                for r in per_map_wild:
                    by_location[r["map_id"] or "?"].append({
                        "species_id": sid, "name": s["name"], "internal_number": num,
                        "kind": "野生", "map_name": r["map_name"],
                        "time_label": TIME_ZH.get(r["time"], r["time"] or "-"),
                        "rest": "%s ｜ %s" % (
                            METHOD_ZH.get(r["method"], r["method"] or "-"),
                            r["level"] or "-"),
                    })
                lv.append("")

            if cats.get("broadcast"):
                got_any = True
                lv.append("### 广播遭遇")
                lv.append("")
                for r in group_broadcast(cats["broadcast"]):
                    if r["kind"] == "weekday":
                        dow = r["dow"]
                        wd, music = WEEKDAY_ZH.get(dow, ("星期编号 %s" % dow, "地区之声未释明"))
                        m = map_by_id.get(r["map_id"]) or {}
                        lk = REL + m["page_path"] if m.get("page_path") else "#"
                        lv.append("- **%s** ｜ %s（需播放「%s」） ｜ 槽权重 %s ｜ 地图：[%s](%s)"
                                  % (r["map_name"] or r["map_id"], wd, music,
                                     "、".join(str(w) for w in r["weights"]),
                                     r["map_name"] or r["map_id"], lk))
                        by_location[r["map_id"] or "?"].append({
                            "species_id": sid, "name": s["name"], "internal_number": num,
                            "kind": "广播", "map_name": r["map_name"],
                            "detail": "%s（需播放「%s」）" % (wd, music)})
                    else:
                        lv.append("- %s ｜ 槽权重 %s ｜ 未播放对应地区之声时的兜底出现"
                                  % (FALLBACK_ZH.get(r["group"], r["group"]), "、".join(str(w) for w in r["weights"])))
                lv.append("")

            if cats.get("swarm"):
                got_any = True
                lv.append("### 群聚（大量出现）")
                lv.append("")
                lv.append("> 按区域关联，同一区域的多张地图共用；激活方式未由静态表证明。")
                lv.append("")
                for r in group_swarm(cats["swarm"]):
                    lv.append("- **%s**（区域 %s）" % (r["map_name"] or "区域名未标", r["mapsec_id"]))
                    if r["map_name"]:
                        by_location["swarm:" + str(r["mapsec_id"])].append({
                            "species_id": sid, "name": s["name"], "internal_number": num,
                            "kind": "群聚", "map_name": r["map_name"],
                            "detail": "区域 %s" % r["map_name"]})
                lv.append("")

            if cats.get("gift"):
                got_any = True
                lv.append("### 赠送")
                lv.append("")
                for r in group_scripted(cats["gift"]):
                    lv.append("- **%s** ｜ %s" % (r["map_name"] or r["map_id"],
                                                  "、".join(r["levels"]) if r["levels"] else "等级未标"))
                    lk, _ = map_link(r["map_id"])
                    if lk:
                        lv.append("  - 地图：[%s](%s)" % (r["map_name"] or r["map_id"], lk))
                    by_location[r["map_id"] or "?"].append({
                        "species_id": sid, "name": s["name"], "internal_number": num,
                        "kind": "赠送", "map_name": r["map_name"],
                        "detail": "、".join(r["levels"]) if r["levels"] else "等级未标"})
                lv.append("")

            if cats.get("egg"):
                got_any = True
                lv.append("### 蛋")
                lv.append("")
                lv.append("> 脚本中的蛋赠予/孵化事件线索；繁殖途径未在数据中证明，不代为补写。")
                lv.append("")
                for r in group_scripted(cats["egg"]):
                    lv.append("- **%s** ｜ %s" % (r["map_name"] or r["map_id"],
                                                  "、".join(r["levels"]) if r["levels"] else "等级未标"))
                    lk, _ = map_link(r["map_id"])
                    if lk:
                        lv.append("  - 地图：[%s](%s)" % (r["map_name"] or r["map_id"], lk))
                    by_location[r["map_id"] or "?"].append({
                        "species_id": sid, "name": s["name"], "internal_number": num,
                        "kind": "蛋", "map_name": r["map_name"], "detail": "蛋事件"})
                lv.append("")

            if cats.get("static_battle_candidate"):
                got_any = True
                lv.append("### 剧情战斗候选")
                lv.append("")
                lv.append("> `setwildbattle` 只说明脚本会发起这场战斗，不保证可捕获或可获得。")
                lv.append("")
                for r in group_scripted(cats["static_battle_candidate"]):
                    lv.append("- **%s** ｜ %s" % (r["map_name"] or r["map_id"],
                                                  "、".join(r["levels"]) if r["levels"] else "等级未标"))
                    lk, _ = map_link(r["map_id"])
                    if lk:
                        lv.append("  - 地图：[%s](%s)" % (r["map_name"] or r["map_id"], lk))
                    by_location[r["map_id"] or "?"].append({
                        "species_id": sid, "name": s["name"], "internal_number": num,
                        "kind": "剧情战斗候选", "map_name": r["map_name"],
                        "detail": "、".join(r["levels"]) if r["levels"] else "等级未标"})
                lv.append("")

            if not got_any and not pre:
                lv.append("当前资料未定位直接获取地点。")
                lv.append("")

        # 进化
        lv.append("## 进化")
        lv.append("")
        evs = rec.get("evolutions_out", [])
        if evs:
            lv.append("**本槽的进化去向**")
            lv.append("")
            for ev in evs:
                cond, sym, p = render_evo_condition(ev, ev["target_species_id"])
                tname = name_by_id.get(ev["target_species_id"], ev.get("target_species_name"))
                tl = "%04d.md" % ev["target_species_id"]
                if sym in BATTLE_FORM_SYMBOLS:
                    if rec.get("is_battle_form_only"):
                        lv.append("- ⇄ [%s](%s) ｜ %s ｜ 反向记录：本槽在形态变化结束后对应回通常形态，"
                                  "不是一次永久获得的进化。" % (tname, tl, cond))
                    else:
                        lv.append("- → [%s](%s) ｜ %s（战斗形态变化候选，非永久获得）" % (tname, tl, cond))
                        if sym == "EVO_MEGA":
                            lv.append("  - 符号 **254** = `EVO_MEGA`：战斗中借助 Mega 石暂时改变形态。")
                        else:
                            lv.append("  - 符号 **253** = `EVO_GIGANTAMAX`：超极巨化形态。")
                else:
                    lv.append("- → [%s](%s) ｜ %s" % (tname, tl, cond))
            lv.append("")
        if pre:
            lv.append("**进化前来源**")
            lv.append("")
            for item in pre:
                src_id = item["source_species_id"]
                cond, sym, p = render_evo_condition(item["evolution"], sid)
                sname = name_by_id.get(src_id, "内部槽 %04d" % src_id)
                lv.append("- ← [%s](%04d.md) ｜ %s" % (sname, src_id, cond))
            lv.append("")
        if not evs and not pre:
            lv.append("本数据集没有该槽的进化记录。")
            lv.append("")

        # 数据来源（统一 details，内部槽编号在此）
        lv.append("<details><summary>数据来源</summary>")
        lv.append("")
        lv.append("- 内部槽：%s" % num)
        if not ph:
            types = " / ".join(dict.fromkeys(t["name"] for t in s["types"] if t.get("name"))) or "未释明"
            bs = s.get("base_stats") or {}
            lv.append("- 属性：%s ｜ 种族值合计 %s" % (types, s.get("base_stats_total")))
            lv.append("- 种族值：HP %s ｜ 攻击 %s ｜ 防御 %s ｜ 特攻 %s ｜ 特防 %s ｜ 速度 %s"
                      % (bs.get("hp"), bs.get("atk"), bs.get("def"), bs.get("spa"), bs.get("spd"), bs.get("spe")))
            if s.get("catch_rate") is not None:
                lv.append("- 捕获率字段：%s（表值；实际捕获还受精灵球/状态/等级影响）" % s.get("catch_rate"))
            egg = s.get("egg_groups") or []
            lv.append("- 蛋群：%s ｜ 成长曲线：%s"
                      % (" / ".join(e.get("zh") or e.get("symbol") for e in egg) or "未释明",
                         (s.get("growth_rate") or {}).get("symbol") or "未释明"))
        lv.append("- 基础数据：`wiki_export/core/data/species.json`")
        lv.append("- 全国图鉴映射：`wiki_export/core/data/national_dex.json`")
        lv.append("- 进化数据：`wiki_export/core/data/evolutions.json`")
        if entries:
            lv.append("- 获取数据：`wiki_export/world/data/acquisition_by_species.json`（species_id %s）" % sid)
        if rec.get("used_encounters"):
            lv.append("- 遭遇表：`wiki_export/world/data/encounters.json`")
        if rec.get("used_maps"):
            lv.append("- 地图：`wiki_export/world/data/maps.json`")
        lv.append("- 进化方式符号：`wiki_export/enrichment/reference_only/evolution_methods.json`（参考表）")
        lv.append("- 道具/招式名称：`wiki_export/core/data/items.json`、`wiki_export/core/data/moves.json`")
        statuses = sorted({CONDITION_ZH.get(e.get("condition_status"), e.get("condition_status"))
                           for e in entries if e.get("condition_status")})
        for st in statuses:
            lv.append("- 证据状态：%s" % st)
        lv.append("")
        lv.append("</details>")
        lv.append("")
        lv.append("[返回宝可梦索引](index.md) ｜ [地点索引](by_location.md) ｜ [形态与占位](forms.md)")
        lv.append("")
        return "\n".join(lv)

    # 预计算：战斗形态槽
    battle_form_slots = set()
    for sid, evs in evo_out.items():
        for ev in evs:
            if (ev.get("reference_method_symbol") in BATTLE_FORM_SYMBOLS):
                battle_form_slots.add(ev["target_species_id"])

    for s in slots:
        sid = s["species_id"]
        entries = acq_by_id.get(sid, [])
        rec = {
            "species_id": sid,
            "internal_number": s["internal_number"],
            "national_dex_number": s["national_dex_number"],
            "name": s["name"],
            "is_placeholder": bool(s.get("is_placeholder_warning")),
            "types": list(dict.fromkeys(t.get("name") for t in s["types"] if t.get("name"))),
            "base_stats_total": s.get("base_stats_total"),
            "entries": entries,
            "evolutions_out": evo_out.get(sid, []),
            "pre_evolutions": [{"source_species_id": src, "evolution": ev}
                               for src, ev in evo_in.get(sid, [])],
            "is_battle_form_only": sid in battle_form_slots,
            "used_encounters": any(e["category"] in ("wild", "broadcast", "swarm") for e in entries),
            "used_maps": bool(entries),
        }
        text = build_page(s, rec)
        out_pages[s["internal_number"]] = text
        page_records[sid] = rec
        for e in entries:
            stats["by_category"][e["category"]] += 1

        if s.get("is_placeholder_warning"):
            forms_placeholder.append({
                "species_id": sid, "internal_number": s["internal_number"],
                "name": s["name"], "national_dex_number": s["national_dex_number"],
                "warnings": s.get("warnings", []),
            })
        elif s["national_dex_number"] is None:
            forms_placeholder.append({
                "species_id": sid, "internal_number": s["internal_number"],
                "name": s["name"], "national_dex_number": None,
                "warnings": ["no_national_dex_number"],
            })

    # Mega/Gmax 目标槽计数
    for sid in battle_form_slots:
        syms = {ev.get("reference_method_symbol") for src, ev in evo_in.get(sid, [])}
        if "EVO_MEGA" in syms:
            stats["mega_target_slots"] += 1
        if "EVO_GIGANTAMAX" in syms:
            stats["gmax_target_slots"] += 1

    # ---------- 写每页 ----------
    os.makedirs(OUT_POKE, exist_ok=True)
    for num, text in out_pages.items():
        with open(os.path.join(OUT_POKE, "%s.md" % num), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)

    # ---------- index.md ----------
    def short_summary(sid, rec):
        if rec["is_placeholder"]:
            return "占位槽"
        cats = {e["category"] for e in rec["entries"]}
        parts = []
        if "wild" in cats:
            n = len({(e.get("map_id"), e.get("method"), e.get("time")) for e in rec["entries"] if e["category"] == "wild"})
            parts.append("野生 %d 处" % n)
        if "broadcast" in cats:
            parts.append("广播")
        if "swarm" in cats:
            parts.append("群聚")
        if "gift" in cats:
            parts.append("赠送")
        if "egg" in cats:
            parts.append("蛋")
        if "static_battle_candidate" in cats:
            parts.append("剧情战斗候选")
        if not parts:
            if rec["pre_evolutions"]:
                parts.append("由进化获得")
            else:
                parts.append("无直接记录")
        return "、".join(parts)

    idx = []
    idx.append("# 宝可梦索引（按全国图鉴号与中文名）")
    idx.append("")
    idx.append("本索引覆盖全部 **%d** 个内部槽。" % stats["total_slots"])
    idx.append("")
    idx.append("- **%d** 个槽有全国图鉴号（正常物种与形态，同一全国号的多个槽不合并）；"
               % stats["slots_with_national_dex"])
    idx.append("- **%d** 个槽没有全国图鉴号（其中 %d 个是占位槽，另 %d 个是特殊内码槽）；"
               % (stats["slots_without_national_dex"],
                  stats["placeholders_without_dex"], stats["special_no_dex"]))
    idx.append("- 另有 **%d** 个槽虽映射到全国图鉴号，但种族值全为 0、属占位槽；"
               % stats["placeholders_with_dex"])
    idx.append("- 合计占位/无效槽 **%d** 个，它们不当作宝可梦陈列，清单见 [forms.md](forms.md)。"
               % stats["placeholder_slots"])
    idx.append("")
    idx.append("- 地点索引：[by_location.md](by_location.md)")
    idx.append("- 形态与占位：[forms.md](forms.md)")
    idx.append("- 同一个中文名/全国号的多个内部槽（形态）**不合并**，各自独立成页。")
    idx.append("- 内部槽编号即页面文件名（如 `0001.md`），是稳定的链接 ID。")
    idx.append("")
    idx.append("## 阅读说明")
    idx.append("")
    idx.append("**Mega / 战斗形态**：进化方式符号 **254** = `EVO_MEGA`（Mega 进化），"
               "**253** = `EVO_GIGANTAMAX`。两者都是战斗中的形态变化候选，不作为永久获得，"
               "也不与基础物种合并。")
    idx.append("")
    idx.append("**权重口径**：野生与广播的「选槽权重」是同一地图/方式/时段内的选槽比例，"
               "不是整体遇见概率，也不是捕获概率；「遇敌率表值」是遭遇表的出现率字段。")
    idx.append("")
    idx.append("**时段口径**：清晨 05:00–09:59 ｜ 白天 10:00–16:59 ｜ "
               "黄昏 17:00–18:59 ｜ 夜晚 19:00–04:59。")
    idx.append("")
    idx.append("**碎岩与撞树**：两者共用同一张槽表（`rock_smash_headbutt`），"
               "本资料不把它强行判定为其中一种。")
    idx.append("")
    idx.append("**广播遭遇**：需要在宝可梦齿轮收音机播放对应地区之声（周三/丰缘之声、"
               "周四/神奥之声、周日/伽勒尔之声），且当天星期匹配，才会替换当地普通遭遇；"
               "未播放时有兜底出现表。")
    idx.append("")
    idx.append("**群聚（大量出现）**：按区域（mapsec）关联，同一区域的多张地图共用同一只宝可梦。")
    idx.append("")
    idx.append("**剧情战斗候选**：`setwildbattle` 只说明脚本会发起战斗，不保证可捕获或可获得。")
    idx.append("")
    idx.append("**未记录 ≠ 不存在**：数据集里没有的字段写作未释明/未覆盖，"
               "不代表该游戏内一定没有；本资料不把缺失推断成零概率，也不写成无法获得。")
    idx.append("")
    idx.append("**进化道具**：页面中的进化道具名称链接到道具版块（`../items/NNNN.md`）。")
    idx.append("")

    dex_slots = [s for s in slots if s["national_dex_number"] is not None]
    dex_slots.sort(key=lambda s: (s["national_dex_number"], s["species_id"]))
    cur_block = None
    dup_dex = {d for d, ids in dex_counter.items() if len(ids) > 1}
    for s in dex_slots:
        d = s["national_dex_number"]
        block = d // 100
        if block != cur_block:
            cur_block = block
            lo = block * 100 if block > 0 else 1
            idx.append("## No.%04d–%04d" % (lo, block * 100 + 99))
            idx.append("")
            idx.append("| 全国号 | 中文名 | 内部槽 | 属性 | 获取要点 |")
            idx.append("|---|---|---|---|---|")
        rec = page_records[s["species_id"]]
        name = s["name"]
        if d in dup_dex:
            name = "%s（形态槽 %s）" % (name, s["internal_number"])
        idx.append("| %04d | %s | [%s](%04d.md) | %s | %s |"
                   % (d, name, s["internal_number"], s["species_id"],
                      " / ".join(dict.fromkeys(t["name"] for t in s["types"] if t.get("name"))) or "-",
                      short_summary(s["species_id"], rec)))
    idx.append("")
    idx.append("## 无全国图鉴号的槽（%d 个）" % stats["slots_without_national_dex"])
    idx.append("")
    idx.append("这些槽没有有效全国图鉴号：%d 个为占位槽，另 %d 个是特殊内码槽"
               "（如 MISSINGNO. 类，名称存在但无有效图鉴号）。"
               "再加上 %d 个有全国号但种族值全 0 的占位槽，合计 %d 个占位/无效槽。"
               "逐个说明见 [forms.md](forms.md)。"
               % (stats["placeholders_without_dex"], stats["special_no_dex"],
                  stats["placeholders_with_dex"], stats["placeholder_slots"]))
    idx.append("")
    for f in forms_placeholder:
        idx.append("- [%s](%s.md) ｜ 内部槽 %s%s"
                   % (f["name"], f["internal_number"], f["internal_number"],
                      "（占位）" if "all_base_stats_zero" in f["warnings"] else "（无全国图鉴号）"))
    idx.append("")
    idx.append("---")
    idx.append("")
    idx.append("数据来源与字段缺口见 [../data/pokemon_summary.json](../data/pokemon_summary.json)。")
    idx.append("")
    with open(os.path.join(OUT_POKE, "index.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(idx))

    # ---------- by_location.md ----------
    loc = []
    loc.append("# 地点索引（按地图看能遇到/获得哪些宝可梦）")
    loc.append("")
    loc.append("按地点汇总野生、广播、群聚、赠送、蛋与剧情战斗候选。同一物种在同一地图、"
               "同一方式、同一时段的多条槽已合并，多个时段合并为一行。"
               "权重是方法内选槽比例，不是整体遇见概率或捕获概率。")
    loc.append("")
    loc.append("- [返回宝可梦索引](index.md) ｜ [形态与占位](forms.md)")
    loc.append("")

    def loc_sort_key(mid):
        if mid.startswith("swarm:"):
            return (1, 0, mid)
        try:
            g, n = mid.split(":")
            return (0, int(g) * 1000 + int(n), mid)
        except Exception:
            return (2, 0, mid)

    for mid in sorted(by_location.keys(), key=loc_sort_key):
        rows = by_location[mid]
        merged_loc = OrderedDict()
        for r in rows:
            if "time_label" in r:
                k = (r["species_id"], r["kind"], r["rest"])
                if k not in merged_loc:
                    merged_loc[k] = dict(r, times=[r["time_label"]])
                elif r["time_label"] not in merged_loc[k]["times"]:
                    merged_loc[k]["times"].append(r["time_label"])
            else:
                k = (r["species_id"], r["kind"], r.get("detail", ""))
                merged_loc.setdefault(k, r)
        uniq = list(merged_loc.values())
        for r in uniq:
            if "times" in r:
                order = {t: i for i, t in enumerate(TIME_ZH.values())}
                r["detail"] = "%s ｜ %s" % ("、".join(sorted(r["times"], key=lambda x: order.get(x, 9))), r["rest"])
        uniq.sort(key=lambda r: (r["kind"], r["species_id"]))
        if mid.startswith("swarm:"):
            sec = mid.split(":", 1)[1]
            title = (uniq[0].get("map_name") if uniq else None) or ("区域 %s" % sec)
            loc.append("## 群聚区域：%s（mapsec %s）" % (title, sec))
            loc.append("")
            loc.append("群聚按区域关联，同一区域的多个地图共用同一只宝可梦。")
            loc.append("")
        else:
            m = map_by_id.get(mid)
            mname = (m or {}).get("map_name_zh") or (uniq[0].get("map_name") if uniq else None) or mid
            loc.append("## %s（地图 %s）" % (mname, mid))
            loc.append("")
            if m and m.get("page_path"):
                loc.append("- 地图页：[%s](%s)" % (mname, REL + m["page_path"]))
                png = map_png_link(mid)
                if png:
                    loc.append("- 地图图像：`%s`" % png)
                loc.append("")
        loc.append("| 宝可梦 | 内部槽 | 方式 | 详情 |")
        loc.append("|---|---|---|---|")
        for r in uniq:
            loc.append("| %s | [%s](../pokemon/%s.md) | %s | %s |"
                       % (r["name"], r["internal_number"], r["internal_number"], r["kind"], r["detail"]))
        loc.append("")
    with open(os.path.join(OUT_POKE, "by_location.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(loc))

    # ---------- forms.md ----------
    fm = []
    fm.append("# 形态、重复全国号与占位槽")
    fm.append("")
    fm.append("内部槽共有 **%d** 个；全国图鉴号 %d 个槽有、%d 个槽没有。"
              "全国号可重复（同一全国号的多个槽代表不同形态/数据槽），本资料**不合并**同名形态，"
              "也不据重复编号擅自命名形态。"
              % (stats["total_slots"], stats["slots_with_national_dex"], stats["slots_without_national_dex"]))
    fm.append("")
    fm.append("- [返回宝可梦索引](index.md) ｜ [地点索引](by_location.md)")
    fm.append("")
    fm.append("## 1. 占位 / 无效槽")
    fm.append("")
    fm.append("共 %d 行：%d 个占位槽（种族值全为 0，其中 %d 个还带有全国图鉴号映射）"
              "与 %d 个无全国图鉴号的特殊内码槽。"
              "它们**不是**可获得或可遭遇的宝可梦，单独列出以便区分「1554 个槽 ≠ 1554 种宝可梦」。"
              % (len(forms_placeholder), stats["placeholder_slots"],
                 stats["placeholders_with_dex"] + stats["placeholders_without_dex"],
                 stats["special_no_dex"]))
    fm.append("")
    fm.append("| 内部槽 | 名称 | 全国号 | 标记 |")
    fm.append("|---|---|---|---|")
    for f_ in forms_placeholder:
        fm.append("| [%s](%s.md) | %s | %s | %s |"
                  % (f_["internal_number"], f_["internal_number"], f_["name"],
                     f_["national_dex_number"] if f_["national_dex_number"] is not None else "无",
                     "、".join(f_["warnings"])))
    fm.append("")
    fm.append("## 2. 全国图鉴号重复的槽（同名形态不合并）")
    fm.append("")
    fm.append("同一全国号出现在多个内部槽时，各自独立成页。共 %d 个全国号出现重复，"
              "涉及 %d 个槽。" % (len(dup_dex), sum(len(v) for k, v in dex_counter.items() if len(v) > 1)))
    fm.append("")
    fm.append("| 全国号 | 中文名 | 内部槽 |")
    fm.append("|---|---|---|")
    for d in sorted(dup_dex):
        for sid in dex_counter[d]:
            s = species[sid]
            fm.append("| %04d | %s | [%s](%04d.md) |" % (d, s["name"], s["internal_number"], sid))
    fm.append("")
    fm.append("## 3. Mega / 超极巨化等战斗形态槽")
    fm.append("")
    fm.append("这些槽只作为 Mega 进化（符号 `EVO_MEGA`，编号 254）或超极巨化"
              "（符号 `EVO_GIGANTAMAX`，编号 253）的目标存在。它们是**战斗中的形态变化候选**，"
              "不是可永久获得的独立个体，因此不并入基础物种页。")
    fm.append("")
    fm.append("| 内部槽 | 名称 | 全国号 | 来源战斗形态 |")
    fm.append("|---|---|---|---|")
    seenbf = set()
    for sid in sorted(battle_form_slots):
        for src, ev in evo_in.get(sid, []):
            sym = ev.get("reference_method_symbol")
            if sym in BATTLE_FORM_SYMBOLS and (sid, sym) not in seenbf:
                seenbf.add((sid, sym))
                s = species[sid]
                fm.append("| [%s](%04d.md) | %s | %s | %s（由 %s 变化） |"
                          % (s["internal_number"], sid, s["name"],
                             s["national_dex_number"] if s["national_dex_number"] is not None else "无",
                             "Mega 进化" if sym == "EVO_MEGA" else "超极巨化",
                             name_by_id.get(src, "内部槽 %04d" % src)))
    fm.append("")
    fm.append("## 4. 物种页上的形态提示")
    fm.append("")
    fm.append("- 形态同名不合并：每个内部槽都有自己的页面与稳定链接 ID（文件名）。")
    fm.append("- 若某槽同时是普通物种又是战斗形态目标，页面会同时标出两者。")
    fm.append("- 全国号为 0 或缺失不代表 0% 出现概率，只表示该槽没有有效全国图鉴号。")
    fm.append("")
    with open(os.path.join(OUT_POKE, "forms.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(fm))

    # ---------- 数据文件 ----------
    data = []
    for s in slots:
        sid = s["species_id"]
        rec = page_records[sid]
        data.append({
            "species_id": sid,
            "internal_number": s["internal_number"],
            "page": "pokemon/%s.md" % s["internal_number"],
            "name": s["name"],
            "national_dex_number": s["national_dex_number"],
            "is_placeholder": rec["is_placeholder"],
            "is_battle_form_only": rec["is_battle_form_only"],
            "types": rec["types"],
            "base_stats_total": rec["base_stats_total"],
            "acquisition": entries_summary(rec, item_by_index=item_by_index),
            "evolutions_out": simplify_evos(rec["evolutions_out"], name_by_id, item_by_index, move_by_id, mapsec_name, method_by_value),
            "evolution_sources": [dict(simplify_evos([p["evolution"]], name_by_id, item_by_index, move_by_id, mapsec_name, method_by_value)[0],
                                       source_species_id=p["source_species_id"],
                                       source_name=name_by_id.get(p["source_species_id"]),
                                       source_page="pokemon/%04d.md" % p["source_species_id"])
                                  for p in rec["pre_evolutions"]],
        })
    with open(os.path.join(OUT_DATA, "pokemon.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump({"schema_version": 1,
                   "note": "内部槽全量记录；页面链接 ID 为内部槽编号。字段缺口逐条列出，不推断不存在的条件。",
                   "counts": {"total_slots": len(slots)},
                   "records": data}, f, ensure_ascii=False, indent=1)

    # 缺口统计
    no_source_no_pre = 0
    for s in slots:
        rec = page_records[s["species_id"]]
        if rec["is_placeholder"]:
            continue
        if not rec["entries"] and not rec["pre_evolutions"]:
            no_source_no_pre += 1
            stats["plain_slots_no_source"] += 1

    statuses = {}
    for v in acq_by_id.values():
        for e in v:
            statuses[e.get("condition_status")] = statuses.get(e.get("condition_status"), 0) + 1

    summary = {
        "schema_version": 1,
        "generator": "player_guide/scripts/build_pokemon.py",
        "sources": {
            "species": "wiki_export/core/data/species.json",
            "evolutions": "wiki_export/core/data/evolutions.json",
            "national_dex": "wiki_export/core/data/national_dex.json",
            "acquisition_by_species": "wiki_export/world/data/acquisition_by_species.json",
            "maps": "wiki_export/world/data/maps.json",
            "encounters": "wiki_export/world/data/encounters.json",
            "items": "wiki_export/core/data/items.json",
            "moves": "wiki_export/core/data/moves.json",
            "evolution_methods": "wiki_export/enrichment/reference_only/evolution_methods.json",
        },
        "source_sha256": {rel: sha256_of(rel) for rel in [
            "core/data/species.json",
            "core/data/evolutions.json",
            "core/data/national_dex.json",
            "world/data/acquisition_by_species.json",
            "world/data/maps.json",
            "world/data/encounters.json",
            "core/data/items.json",
            "core/data/moves.json",
            "enrichment/reference_only/evolution_methods.json",
        ]},
        "source_counts": {
            "maps": n_maps,
            "items": n_items,
            "moves": n_moves,
            "evolution_method_symbols": n_methods,
        },
        "counts": {
            "internal_slots": stats["total_slots"],
            "slots_with_national_dex": stats["slots_with_national_dex"],
            "slots_without_national_dex": stats["slots_without_national_dex"],
            "placeholder_slots": stats["placeholder_slots"],
            "placeholders_without_national_dex": stats["placeholders_without_dex"],
            "placeholders_with_national_dex": stats["placeholders_with_dex"],
            "special_slots_without_national_dex": stats["special_no_dex"],
            "slots_with_acquisition_records": len(acq_by_id),
            "acquisition_records_by_category": dict(stats["by_category"]),
            "slots_with_evolutions_out": len(evo_out),
            "slots_with_evolution_sources": len(evo_in),
            "mega_target_edges": stats["mega_target_slots"],
            "gmax_target_edges": stats["gmax_target_slots"],
            "slots_no_direct_source_and_no_pre_evolution": no_source_no_pre,
        },
        "condition_status_counts": statuses,
        "field_gaps": [
            {"field": "wild.level", "note": "遭遇表给出的等级范围；个别槽等级缺失时不写成固定值。"},
            {"field": "broadcast.level", "note": "广播遭遇不携带等级字段，等级未在数据中给出。"},
            {"field": "swarm.level", "note": "群聚按 mapsec 关联，无等级字段。"},
            {"field": "gift/egg/static_battle_candidate.level", "symbolic": "level.kind=literal 时取字面值；否则未释明"},
            {"field": "broadcast.gating", "note": "广播门控旗标（FlagGet 0x1f/0x17A1）与 0x17a1 语义未穷举。"},
            {"field": "condition_status", "note": "所有获取记录均为静态证据，未证明剧情可达性/实际可捕获性。"},
            {"field": "evolution.method_param", "note": "部分 method 的 param 语义未释明（如 EVO_TYPE_IN_PARTY、EVO_NATURE_*、EVO_CRITICAL_HIT、EVO_FLAG_SET），页面保留编号并标注未释明。"},
            {"field": "EVO_MAP.param", "note": "按地图区域编号查地图表名称；未命中时保留编号。"},
            {"field": "EVO_ITEM.param", "note": "按道具表索引取名称；其中 4 条 param=1 命中『大师球』（标价 0），疑为占位值，页面已就地标注未确认。"},
            {"field": "rock_smash/headbutt", "note": "共用同一槽表 rock_smash_headbutt，不强行判定为碎岩或撞树其中之一。"},
            {"field": "numbering", "note": "1554 个内部槽不等于 1554 种宝可梦；%d 个为占位/无效槽。" % stats["placeholder_slots"]},
        ],
        "unresolved": {
            "unknown_item_param_count": stats["unknown_item_params"],
            "unknown_move_param_count": stats["unknown_move_params"],
            "evo_map_param_unmapped": stats["eval_map_param_unmapped"],
            "evolution_item_param_zero_price": stats["item_param_zero_price"],
            "unresolved_evolution_symbols": dict(stats["unresolved_evo_symbols"]),
        },
        "outputs": {
            "pokemon_pages": len(out_pages),
            "index": "pokemon/index.md",
            "by_location": "pokemon/by_location.md",
            "forms": "pokemon/forms.md",
            "data": "data/pokemon.json",
        },
    }
    with open(os.path.join(OUT_DATA, "pokemon_summary.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)

    print(json.dumps(summary["counts"], ensure_ascii=False, indent=1))
    print("pages:", len(out_pages), "locations:", len(by_location))
    print("unresolved:", json.dumps(summary["unresolved"], ensure_ascii=False))


def entries_summary(rec, item_by_index):
    out = []
    for e in rec["entries"]:
        d = {
            "category": e["category"],
            "map_id": e.get("map_id"),
            "map_name": e.get("map_name"),
            "method": e.get("method"),
            "time": e.get("time"),
            "level": e.get("level"),
            "slot_weight": e.get("conditional_slot_weight"),
            "encounter_rate": e.get("encounter_rate"),
            "day_of_week": e.get("day_of_week"),
            "fallback_group": e.get("fallback_group"),
            "mapsec_id": e.get("mapsec_id"),
            "condition_status": e.get("condition_status"),
            "page_path": e.get("page_path"),
        }
        # Preserve event/instruction identity in the condensed player dataset.
        for key in ('acquisition_id','script','source_roots','source','source_untrusted','fields','observed_following_start'):
            if key in e:
                d[key] = e[key]
        out.append(d)
    return out


def simplify_evos(evos, name_by_id, item_by_index, move_by_id, mapsec_name, method_by_value):
    out = []
    for ev in evos:
        sym = ev.get("reference_method_symbol") or method_by_value.get(ev["method"])
        p = ev.get("param")
        d = {
            "symbol": sym,
            "method_value": ev["method"],
            "param": p,
            "target_species_id": ev["target_species_id"],
            "target_name": name_by_id.get(ev["target_species_id"], ev.get("target_species_name")),
            "target_page": "pokemon/%04d.md" % ev["target_species_id"],
        }
        if sym and sym.startswith("EVO_MEGA"):
            d["battle_form"] = True
        if sym in P_ITEM and p in item_by_index:
            d["param_name"] = item_by_index[p]
        elif sym in P_MOVE and p in move_by_id:
            d["param_name"] = move_by_id[p]
        elif sym == "EVO_MAP" and p in mapsec_name:
            d["param_name"] = mapsec_name[p]
        elif sym == "EVO_OTHER_PARTY_MON":
            d["param_name"] = name_by_id.get(p)
        out.append(d)
    return out


if __name__ == "__main__":
    main()
