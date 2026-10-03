# 等级缩放

来源：`wiki_export/world/source_inventory.json`，JSON pointer `/mechanisms/2`。

## 已有规则

- 现成README定位IsBossTrainerClassForLevelScaling等消费者及普通队伍level字段。

## 具体边界/缺字段

- 当前入口仅局部消费者证据；没有完整缩放公式/触发条件导出，不套官方规则，不把表内等级作为所有实际战斗等级。

## 证据入口

- `trainers_research/README.md`
- `trainers_research/out/trainers.json`

缺字段：完整缩放公式、触发条件、玩家队伍/徽章输入对应关系和最终等级求值。普通队伍基础level已完整导出，不套官方公式。
