# EV spreads与强制闪光

来源：`wiki_export/world/source_inventory.json`，JSON pointer `/mechanisms/1`。

## 已有规则

- partyFlags==3且aiFlags>1、索引1..125时首u16低字节作spread索引；10B字段为nature/ivs/hp_ev/atk_ev/def_ev/spe_ev/spa_ev/spd_ev/ball/ability。
- 训练家403槽0/1/2强制闪光；不是队伍替换表。

## 具体边界/缺字段

- 高字节含义未证；151镜像候选不作为选表；ability策略不保证每场观测值。

## 证据入口

- `trainers_research/README.md`
- `trainers_research/README.md`
- `trainers_research/out/overrides.json`
