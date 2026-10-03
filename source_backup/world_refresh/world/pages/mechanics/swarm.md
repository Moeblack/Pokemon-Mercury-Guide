# 群聚

来源：`wiki_export/world/source_inventory.json`，JSON pointer `/mechanisms/4`。

## 已有规则

- 0x09E3CDCE共16条{u16 mapsec_id,u16 species}，mapsec_id==0终止；按地区段关联，多地图可能共用。

## 具体边界/缺字段

- 不凭静态表断言当前群聚已激活或可达。

## 证据入口

- `encounters_research/out/encounters.json`
- `encounters_research/README.md`
