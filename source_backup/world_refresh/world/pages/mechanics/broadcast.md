# 广播

来源：`wiki_export/world/source_inventory.json`，JSON pointer `/mechanisms/3`。

## 已有规则

- consumer 0x09D647B0读取0x09DDDBE0，100条×26byte；每条3组各4物种。
- dayOfWeek数值3/4/0分别选set0/1/2，其他星期及未命中走现成fallback；星期标签和证据强度原样保留。
- 触发后槽权重40/20/20/20；Flag0x17A1==0、Flag31!=0、[sp+0xc]==0、rand%3!=0等为现成门控字段。

## 具体边界/缺字段

- 旧0x09DDDBC6/101条已撤回；内部槽权重不是总体遭遇率；收音机卡剧情与旗标实现、UI/状态生命周期未全面闭合。

## 证据入口

- `encounters_research/README.md`
- `encounters_research/out/encounters.json`

完整门控：

```json
{
 "day_condition": "gClock+5(dayOfWeek) ∈ {3,0,4} 才选到非 fallback set",
 "flag_0x17A1_6049": {
  "check": "0x09D64FB0 FlagGet(0x17A1)；==0 才进入广播候选路径，!=0 转入表 0x09E3CD50 的特殊遭遇路径",
  "setter_scripts": [
   "0x08F347F6 1:121/local55",
   "0x08F34F0B 3:107/local12",
   "0x08F353B3 55:41/local3",
   "0x08F3FB98 54:2/local7"
  ],
  "related_flag": "同批脚本同时 setflag 0x17A0(6048)；代码 0x088E5938 也置 0x17A0",
  "semantics": "setter 脚本均为 setwildbattle+dowildbattle 后置位；作为广播路径的否定条件，确切语义未证"
 },
 "flag_0x1F_31": {
  "getter_sites": [
   "0x09D6500E",
   "0x09D1C460",
   "0x09D513BA",
   "0x09D1A6DC"
  ],
  "getter_logic": "FlagGet(31)；==0 走普通遭遇/返回，!=0 才调用广播 getter 0x09D647B0 (或成员检查 0x09D64824)",
  "code_setter": "0x088E5998 FlagSet(31)，位于读取 gClock+5(dayOfWeek) 的例程内 (0x088E594E 读 gClock+5 并 cmp #6)，同例程 0x088E5938 FlagSet(0x17A0=6048)",
  "setter_context": "例程入口 0x088E5808（无直接 bl 调用；回调 0x088E5735 装到 [r7]，属任务/回调状态机）；据其读 gClock+5 与 flag 使用判定为地区音乐/广播例程",
  "script_setter_note": "script 索引的 setflag 31(0x08EC3624) 是华丽大赛 NPC 复用，不作为广播语义",
  "semantics": "据代码 setter：广播/地区音乐例程在匹配 dayOfWeek 时置 31，作为广播遭遇门控；与 0x17A0 一起置位"
 },
 "extra_conditions": "[sp+0xc]==0（0x09D65008-0C）且 rand%3!=0（0x09D6501C-2A）",
 "lore_enabling": "ROM 文本 0x08AA34C1/0x08AA37A3/0x08AA3A55：通过小茜的答题获得收音机卡，之后播放地区音乐可在草丛吸引不同地区宝可梦；未证明其以 0x1F/0x17A1 实现"
}
```

全部广播/后备槽见 `world/data/encounters.json`；内部40/20/20/20不能当总体概率。
