# -*- coding: utf-8 -*-
"""
人类友好·全量道具攻略生成器（面向玩家）。

只读现有解包产物，机械映射字段，不推断业务。
正文只保留玩家需要的信息：中文名、用途、标价、地点、坐标、数量、条件状态；
技术字段与完整 ID 收进每页底部 <details> 与 data/items.json。

输入（相对项目根 R）：
  wiki_export/core/data/items.json
  wiki_export/world/data/acquisition_by_item.json
  wiki_export/world/data/shops.json
  wiki_export/world/data/hidden_items.json
  wiki_export/world/data/maps.json
输出（相对项目根 R）：
  player_guide/items/NNNN.md
  player_guide/items/index.md
  player_guide/items/by_location.md
  player_guide/data/items.json
  player_guide/data/items_summary.json

不修改 ROM / 存档 / 现有 wiki_export 产物。
"""

import json
import os
import re

R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
G = os.path.join(R, "player_guide")
ITEMS_DIR = os.path.join(G, "items")
DATA_DIR = os.path.join(G, "data")

UP = "../../"  # 从 player_guide/items/ 回到项目根


def rel(path):
    if not path:
        return ""
    return UP + path.replace("\\", "/").lstrip("/")


def relw(path):
    if not path:
        return ""
    return UP + "wiki_export/" + path.replace("\\", "/").lstrip("/")


def load(*parts):
    with open(os.path.join(R, *parts), encoding="utf-8") as f:
        return json.load(f)


def strip_control(text):
    """去控制码：本批说明文字中的控制码为字面量 \\n，替换为空格。"""
    if not text:
        return ""
    t = text.replace("\\n", " ")
    t = re.sub(r"[\x00-\x1f\x7f]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def first_sentence(text):
    if not text:
        return ""
    m = re.split(r"(?<=[。！？!?])", text, maxsplit=1)
    return m[0].strip() if m and m[0].strip() else text


# 口袋中文（机械对应 symbol -> 中文）
POCKET_ZH = {
    "ITEMS": "道具",
    "KEY_ITEMS": "重要物品",
    "POKE_BALLS": "精灵球",
    "TM_CASE": "招式学习器",
    "BERRY_POUCH": "树果袋",
}

# 分类 -> 攻略分组（未知分类落到其它线索）
GROUP_OF = {
    "shop": "购买",
    "hidden_item": "地面隐藏",
    "script_item_candidate": "人物剧情",
    "gift": "人物剧情",
    "static_battle_candidate": "其它线索",
}
GROUPS = ["购买", "地面隐藏", "人物剧情", "其它线索"]

# 条件状态 -> 是否需要在正文标注“触发条件待补”
CONDITION_GROUPS = {"购买", "人物剧情", "其它线索"}

# ---------------------------------------------------------------- 载入数据
items = load("wiki_export", "core", "data", "items.json")
acq = load("wiki_export", "world", "data", "acquisition_by_item.json")
maps = load("wiki_export", "world", "data", "maps.json")
# 作为来源文档核验读取；库存以 acquisition_by_item 的 shop 记录为准
shops = load("wiki_export", "world", "data", "shops.json")
hidden = load("wiki_export", "world", "data", "hidden_items.json")

maps_by_id = {m["id"]: m for m in maps}

obj_coord = {}
for m in maps:
    for o in (m.get("events") or {}).get("objects") or []:
        lid = o.get("local_id")
        if lid is not None:
            obj_coord.setdefault(m["id"], {})[lid] = (
                o.get("x"), o.get("y"), o.get("elevation"))


def event_coord(map_id, scripts, kind):
    entries = ((maps_by_id.get(map_id) or {}).get("events") or {}).get(kind) or []
    ss = set(scripts or [])
    for e in entries:
        if e.get("script") in ss:
            return (e.get("x"), e.get("y"), e.get("elevation"))
    return None


def _root_map(s):
    if s.startswith("object:"):
        return s.split(":", 1)[1].split("/local")[0]
    if s.startswith("coord:") or s.startswith("bg:"):
        return ":".join(s.split(":")[1:3])
    return None


def record_map_variants(r):
    """同一脚本若出现在多张地图，按地图拆成多条；不同地图不可漏。"""
    roots = sorted(set(r.get("source_roots") or []))
    mids = []
    for s in roots:
        mid = _root_map(s)
        if mid and mid not in mids:
            mids.append(mid)
    if not mids:
        return [r]
    out = []
    for mid in mids:
        rr = dict(r)
        rr["map_id"] = mid
        rr["source_roots"] = [s for s in roots if _root_map(s) == mid]
        mm = maps_by_id.get(mid) or {}
        if mm.get("map_name_zh"):
            rr["map_name"] = mm["map_name_zh"]
        if mm.get("page_path"):
            rr["page_path"] = mm["page_path"]
        out.append(rr)
    return out


def intval(v):
    if isinstance(v, dict):
        return v.get("value") if v.get("kind") == "literal" else None
    return v


def fmt_qty(r):
    if r["category"] == "hidden_item":
        return r.get("quantity")
    q = r.get("quantity")
    if isinstance(q, dict):
        if q.get("kind") == "literal":
            return q.get("value")
        return None
    return q


def merge_sig(r):
    if r.get("category") == "shop":
        # Keep distinct vendors/conditions; equal prices do not identify an event.
        return json.dumps(
            {k:r.get(k) for k in ('category','map_id','price','source','source_roots','script','conditions_heuristic','condition_status')},
            ensure_ascii=False, sort_keys=True)
    sig = {
        "category": r.get("category"),
        "map_id": r.get("map_id"),
        "page_path": r.get("page_path"),
        "x": r.get("x"),
        "y": r.get("y"),
        "underfoot": r.get("underfoot"),
        "hidden_item_flag_offset": r.get("hidden_item_flag_offset"),
        "source_roots": sorted(set(r.get("source_roots") or [])),
        "script": sorted(r.get("script") or []) if isinstance(r.get("script"), list) else r.get("script"),
        "price": r.get("price"),
        "condition_status": r.get("condition_status"),
        "parameter_role": r.get("parameter_role"),
        "level": json.dumps(r.get("level"), ensure_ascii=False, sort_keys=True),
        "quantity": json.dumps(r.get("quantity"), ensure_ascii=False, sort_keys=True),
        "method": r.get("method"),
        "time": r.get("time"),
        "fields": json.dumps(r.get("fields"), ensure_ascii=False, sort_keys=True),
        "source": r.get("source"),
        "conditions_heuristic": r.get("conditions_heuristic"),
    }
    return json.dumps(sig, ensure_ascii=False, sort_keys=True)


def map_meta(map_id):
    m = maps_by_id.get(map_id) or {}
    return {
        "name": m.get("map_name_zh") or m.get("name_guess_vanilla") or map_id,
        "page_path": m.get("page_path"),
        "map_png": m.get("map_png"),
        "region": m.get("region_map_section_id"),
    }


def coord_of(r):
    """解析记录坐标（对象 localId -> 事件脚本 -> 记录自带 x/y）。"""
    coord = None
    for s in sorted(set(r.get("source_roots") or [])):
        if s.startswith("object:"):
            mid = _root_map(s)
            try:
                lid = int(s.split("/local")[1])
            except (IndexError, ValueError):
                lid = None
            c = (obj_coord.get(mid) or {}).get(lid)
            if c and coord is None:
                coord = c
        elif s.startswith("coord:"):
            entries=((maps_by_id.get(_root_map(s)) or {}).get('events') or {}).get('coord_events') or []
            roots=r.get('script') or []
            roots={roots} if isinstance(roots,str) else set(roots)
            triggers=[e for e in entries if e.get('script') in roots]
            if triggers:
                labels=sorted({f"({e['x']},{e['y']})[变量{e.get('trigger')}={e.get('index_var')}]" for e in triggers})
                return '触发格：'+'、'.join(labels)
        elif s.startswith("bg:"):
            c = event_coord(_root_map(s), r.get("script"), "bg_events")
            if c and coord is None:
                coord = c
    if coord is None and r.get("x") is not None and r.get("y") is not None:
        coord = (r.get("x"), r.get("y"), r.get("elevation"))
    if coord and coord[0] is not None and coord[1] is not None:
        return "%s,%s" % (coord[0], coord[1])
    return None


def place_short(r):
    """首屏用短地点：商店加·商店，坐标附括号。"""
    m = map_meta(r.get("map_id"))
    name = m["name"]
    if r["category"] == "shop":
        return "%s·商店" % name
    c = coord_of(r)
    if c:
        return "%s(%s)" % (name, c)
    return name


def map_links(m):
    out = []
    if m.get("page_path"):
        out.append("[地图](%s)" % relw(m["page_path"]))
    if m.get("map_png"):
        out.append("[静态图](%s)" % relw(m["map_png"]))
    return "｜".join(out)


def render_line(r, cnt):
    """一条获取线索：地点 / 地图链接 / 坐标 / 数量 / 条件状态。"""
    m = map_meta(r.get("map_id"))
    reg = "（区域%s）" % m["region"] if m.get("region") is not None else ""
    bits = ["**%s**%s" % (m["name"], reg)]
    c = coord_of(r)
    if c:
        bits.append("(%s)" % c)
    if r["category"] == "hidden_item":
        bits.append("数量 %s" % (fmt_qty(r) if fmt_qty(r) is not None else "—"))
    elif r["category"] == "script_item_candidate":
        bits.append("与坐标处人物交互")
        q = fmt_qty(r)
        if q is not None:
            bits.append("数量 %s" % q)
    elif r["category"] == "gift":
        lv = intval(r.get("level"))
        bits.append("赠予宝可梦携带%s" % ("（等级 %s）" % lv if lv is not None else ""))
    elif r["category"] == "static_battle_candidate":
        lv = intval(r.get("level"))
        bits.append("野生宝可梦携带%s" % ("（等级 %s）" % lv if lv is not None else ""))
    elif r["category"] == "shop":
        bits.append("标价 %s" % (r.get("price") if r.get("price") is not None else "—"))
    links = map_links(m)
    if links:
        bits.append(links)
    if GROUP_OF.get(r["category"]) in CONDITION_GROUPS:
        bits.append("触发条件待补")
    if cnt > 1:
        bits.append("相同来源 %d 条" % cnt)
    return "- " + " · ".join(bits)


def source_doc_link(r):
    src = r.get("source") or {}
    if src.get("path"):
        return "[%s](%s)" % (src["path"], rel(src["path"]))
    return None


def build_item(it):
    idx = it["index"]
    name = it.get("name") or ""
    records = acq.get(str(idx), [])

    grouped = {g: {} for g in GROUPS}
    for r0 in records:
        for r in record_map_variants(r0):
            grp = GROUP_OF.get(r["category"], "其它线索")
            slot = grouped[grp].setdefault(merge_sig(r), {"rec": r, "count": 0, "ids": []})
            slot["count"] += 1
            if r0.get("acquisition_id"):
                slot["ids"].append(r0["acquisition_id"])

    has_source = bool(records)
    desc = strip_control(it.get("description"))
    pocket = it.get("pocket") or {}
    pocket_zh = POCKET_ZH.get(pocket.get("symbol"), pocket.get("symbol"))
    price = it.get("price")

    # 首屏线索
    short = []
    for g in GROUPS:
        for key in grouped[g]:
            lab = place_short(grouped[g][key]["rec"])
            if lab not in short:
                short.append(lab)

    lines = ["# %s" % name, ""]
    if desc:
        lines.append(first_sentence(desc))
        lines.append("")
    if has_source:
        shown = short[:8]
        head = " ／ ".join(shown)
        if len(short) > 8:
            head += " ／ …等 %d 处" % len(short)
        lines.append("获取：%s" % head)
    else:
        lines.append("当前资料未定位获取地点。")
    lines.append("")

    # 用途
    lines.append("## 用途")
    lines.append("")
    lines.append(desc if desc else "—")
    lines.append("")
    detail = []
    if price is not None:
        detail.append("标价 %s" % price)
    if pocket_zh:
        detail.append("口袋：%s" % pocket_zh)
    if detail:
        lines.append("　".join(detail))
        lines.append("")

    # 获取方式
    if has_source:
        lines.append("## 获取方式")
        lines.append("")
        for g in GROUPS:
            if not grouped[g]:
                continue
            lines.append("### %s" % g)
            lines.append("")
            for key in grouped[g]:
                slot = grouped[g][key]
                lines.append(render_line(slot["rec"], slot["count"]))
            lines.append("")

    # 页底数据来源
    lines.append("<details><summary>数据来源</summary>")
    lines.append("")
    src = it.get("source") or {}
    if src.get("path"):
        lines.append("- 来源文档：[%s](%s)（`%s`）" % (src["path"], rel(src["path"]), src.get("json_pointer", "")))
    lines.append("- 表索引 index %04d；内嵌 itemId %s；口袋 %s (id=%s)；type %s；hold_effect %s/%s；importance %s；unk19 %s" % (
        idx, it.get("item_id"), pocket.get("symbol"), pocket.get("id"),
        it.get("type"), it.get("hold_effect"), it.get("hold_effect_param"),
        it.get("importance"), it.get("unk19")))
    doc_links = []
    ids = []
    for g in GROUPS:
        for key in grouped[g]:
            slot = grouped[g][key]
            dl = source_doc_link(slot["rec"])
            if dl and dl not in doc_links:
                doc_links.append(dl)
            for i in slot["ids"]:
                if i not in ids:
                    ids.append(i)
    if doc_links:
        lines.append("- 获取来源文档：" + "、".join(doc_links))
    if ids:
        lines.append("- 获取记录 ID：" + "、".join("`%s`" % i for i in ids))
    pg = it.get("description_provenance") or {}
    if pg.get("charmap_source"):
        lines.append("- 说明文字解码来源：`%s`" % pg["charmap_source"])
    lines.append("")
    lines.append("</details>")
    lines.append("")

    md = "\n".join(lines).rstrip() + "\n"

    data_rec = {
        "index": idx,
        "file": "items/%04d.md" % idx,
        "name": name,
        "item_id": it.get("item_id"),
        "pocket": it.get("pocket"),
        "pocket_zh": pocket_zh,
        "price": it.get("price"),
        "price_note": it.get("price_note"),
        "hold_effect": it.get("hold_effect"),
        "hold_effect_param": it.get("hold_effect_param"),
        "importance": it.get("importance"),
        "unk19": it.get("unk19"),
        "type": it.get("type"),
        "description": desc,
        "description_control_code_count": it.get("description_control_code_count"),
        "source": it.get("source"),
        "acquisition_status": it.get("acquisition", {}).get("status"),
        "has_source": has_source,
        "groups": {},
    }
    for g in GROUPS:
        if not grouped[g]:
            continue
        data_rec["groups"][g] = [
            summarize_record(grouped[g][k]["rec"], grouped[g][k]["count"], grouped[g][k]["ids"])
            for k in grouped[g]
        ]
    return "%04d.md" % idx, md, data_rec


def summarize_record(r, cnt, ids):
    return {
        "category": r.get("category"),
        "acquisition_ids": sorted(set(ids)),
        "map_id": r.get("map_id"),
        "map_name": r.get("map_name"),
        "page_path": r.get("page_path"),
        "source": r.get("source"),
        "source_roots": r.get("source_roots"),
        "script": r.get("script"),
        "x": r.get("x"),
        "y": r.get("y"),
        "elevation": r.get("elevation"),
        "quantity": fmt_qty(r),
        "price": r.get("price"),
        "currency_semantics": r.get("currency_semantics"),
        "conditions_heuristic": r.get("conditions_heuristic"),
        "condition_status": r.get("condition_status"),
        "underfoot": r.get("underfoot"),
        "hidden_item_flag_offset": r.get("hidden_item_flag_offset"),
        "parameter_role": r.get("parameter_role"),
        "level": r.get("level"),
        "merged_count": cnt,
    }


# ---------------------------------------------------------------- 生成
if not os.path.isdir(ITEMS_DIR):
    os.makedirs(ITEMS_DIR)
if not os.path.isdir(DATA_DIR):
    os.makedirs(DATA_DIR)

all_data = []
n_pages = 0
for it in items:
    fname, md, data_rec = build_item(it)
    with open(os.path.join(ITEMS_DIR, fname), "w", encoding="utf-8", newline="\n") as f:
        f.write(md)
    all_data.append(data_rec)
    n_pages += 1

# ---- index.md（按名称）
idx_lines = ["# 道具总表（按名称）", ""]
idx_lines.append("共 %d 个道具槽。索引对应文件名 items/NNNN.md。" % len(all_data))
idx_lines.append("")
idx_lines.append("| 名称 | 索引 | 标价 | 获取 |")
idx_lines.append("|---|---|---|---|")
for d in sorted(all_data, key=lambda x: (x["name"], x["index"])):
    src_flag = "有" if d["has_source"] else "当前资料未定位获取地点"
    idx_lines.append("| [%s](%s) | %04d | %s | %s |" % (
        d["name"], d["file"].split("/")[-1], d["index"], d["price"], src_flag))
idx_lines.append("")
idx_lines.append("- [按地点反查](by_location.md)")
with open(os.path.join(ITEMS_DIR, "index.md"), "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(idx_lines).rstrip() + "\n")
n_pages += 1

# ---- by_location.md（按地点反查）
by_location = {}
for d in all_data:
    for g, entries in d["groups"].items():
        for e in entries:
            mid = e.get("map_id")
            if mid:
                by_location.setdefault(mid, {}).setdefault(d["index"], set()).add(g)

loc_lines = ["# 按地点反查道具", ""]
loc_lines.append("按地图聚合的获取线索；地图页与静态图指向既有解包产物。")
loc_lines.append("")
name_by_idx = {d["index"]: d["name"] for d in all_data}
for mid in sorted(by_location, key=lambda k: ((maps_by_id.get(k) or {}).get("map_name_zh") or k)):
    m = maps_by_id.get(mid) or {}
    title = m.get("map_name_zh") or m.get("name_guess_vanilla") or mid
    loc_lines.append("## %s（%s）" % (title, mid))
    loc_lines.append("")
    meta = []
    if m.get("region_map_section_id") is not None:
        meta.append("区域编号 %s" % m["region_map_section_id"])
    if m.get("page_path"):
        meta.append("[地图页](%s)" % relw(m["page_path"]))
    if m.get("map_png"):
        meta.append("[静态图](%s)" % relw(m["map_png"]))
    if meta:
        loc_lines.append("　".join(meta))
        loc_lines.append("")
    grp_items = {}
    for idx, gs in by_location[mid].items():
        for g in gs:
            grp_items.setdefault(g, []).append(idx)
    for g in GROUPS:
        if g not in grp_items:
            continue
        loc_lines.append("**%s**：" % g)
        for idx in sorted(grp_items[g]):
            loc_lines.append("- [%s](../items/%04d.md)" % (name_by_idx.get(idx, idx), idx))
        loc_lines.append("")
with open(os.path.join(ITEMS_DIR, "by_location.md"), "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(loc_lines).rstrip() + "\n")
n_pages += 1

# ---- data/items.json
with open(os.path.join(DATA_DIR, "items.json"), "w", encoding="utf-8", newline="\n") as f:
    json.dump({"schema_note": "机械映射 wiki_export 现有字段，不推断业务；完整 ID 保留在此",
               "count": len(all_data), "items": all_data}, f, ensure_ascii=False, indent=1)
    f.write("\n")

# ---- summary
summary = {
    "条目数": len(all_data),
    "有来源条目数": sum(1 for d in all_data if d["has_source"]),
    "空来源条目数": sum(1 for d in all_data if not d["has_source"]),
    "来源记录数": sum(len(v) for v in acq.values()),
    "输出文件数": n_pages,
    "输出文件": {
        "道具页": len(all_data),
        "index.md": 1,
        "by_location.md": 1,
        "data/items.json": 1,
        "data/items_summary.json": 1,
    },
    "输入文件": [
        "wiki_export/core/data/items.json",
        "wiki_export/world/data/acquisition_by_item.json",
        "wiki_export/world/data/shops.json",
        "wiki_export/world/data/hidden_items.json",
        "wiki_export/world/data/maps.json",
    ],
}
with open(os.path.join(DATA_DIR, "items_summary.json"), "w", encoding="utf-8", newline="\n") as f:
    json.dump(summary, f, ensure_ascii=False, indent=1)
    f.write("\n")

print(json.dumps(summary, ensure_ascii=False, indent=1))
