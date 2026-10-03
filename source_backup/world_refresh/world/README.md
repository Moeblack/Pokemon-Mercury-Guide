# 世界Wiki导出

由 `wiki_export/scripts/export_world.py` 读取既有资料生成；未运行游戏/仿真/重绘，不改源数据。

## 完整可检索导航

- [871地图](pages/maps/index.md)
- [165地区段名称池](pages/regions/index.md)
- [743普通训练师与特殊引用](pages/trainers/index.md)
- [58静态商店](pages/shops/index.md)
- [7513原文本](pages/texts/index.md)
- [地图NPC/剧情事件证据](pages/story_events/index.md)
- [宝可梦与道具获取来源](pages/acquisitions/index.md)
- [系统机制与音乐](pages/mechanics/index.md)
- [全部未归图脚本](pages/story_events/unmapped_scripts.md)
- [全部未归图文本](pages/texts/unmapped.md)

## 数据与边界

`data/`提供全部结构化JSON及适用CSV。core直接合并`acquisition_by_species.json`与`acquisition_by_item.json`，字典键为内部species_id与道具index，不是内嵌itemId。

45动态warp目的runtime未知；24stop根及08990B94传播来源标记不可信。指令证据不保证剧情可达/获得成功；设置野战不等于可捕获。普通地面道具标准调用另列reference候选，不以95条additem代表全部获取。时段、encounter_rate与槽权重分别保留，不乘成全局概率。训练师等级/商店价格均为表值。地图名称为地区段，不猜大地区。音乐仅原始ID精确关联双表index，未复制音频。

## 制作摘要

```json
{
 "maps": 871,
 "regions_pool": 165,
 "regions_used": 124,
 "ordinary_trainers": 743,
 "party_members": 1892,
 "shops": 58,
 "rejected_shops": 2,
 "texts": 7513,
 "wild_slots": 6624,
 "broadcast_slots": 1200,
 "swarm_records": 16,
 "hidden_items": 451,
 "map_png_linked": 862,
 "map_png_missing": 9,
 "dynamic_warps": 45,
 "scripts": 12627,
 "unmapped_scripts": 59,
 "unmapped_texts": 9,
 "story_events": 9195,
 "script_acquisitions": {
  "additem": 95,
  "givepokemon": 48,
  "setwildbattle": 78,
  "giveegg": 7,
  "adjacent_assignments_callstd": 971
 },
 "source_untrusted_acquisitions": 0,
 "acquisition_species_keys": 404,
 "acquisition_item_keys": 489,
 "open_fields": [
  "RTC actual game clock correctness",
  "complete level scaling formula",
  "special trainer identity/party",
  "standard-call item semantic confirmation",
  "runtime dynamic warp destination",
  "story reachability is not statically asserted"
 ],
 "music_raw_ids_joined": 630,
 "music_raw_ids_unjoined": [
  393,
  401,
  402,
  403,
  404,
  405,
  407,
  410,
  414,
  421,
  422,
  423,
  424,
  425,
  428,
  429,
  431,
  432,
  435,
  438,
  440,
  443,
  452,
  455,
  460,
  462,
  463,
  464,
  466,
  469,
  471,
  472,
  473,
  477,
  478,
  479,
  481,
  484,
  485,
  486,
  491,
  493,
  502,
  508,
  509,
  514,
  518,
  522,
  523,
  530,
  534,
  536,
  537,
  545,
  552,
  555,
  567,
  568,
  569,
  570,
  65535
 ],
 "regions_name_unresolved": 31,
 "navigation_complete": true,
 "verification": {
  "generated_json_readback": true,
  "referenced_paths_exist": true,
  "link_targets_checked": 12618,
  "source_files_unchanged": true,
  "execution": "export command only; no game/emulator/new render/test suite"
 }
}
```
