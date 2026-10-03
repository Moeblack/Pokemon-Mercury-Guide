# 拒绝计入库存的源

两处非法列表指针不计58有效库存。坏根0x08990B94来源已知不可信，不能据此断言游戏实际坏店。

来源：`encounters_research/out/shops.json` `/rejected_invalid_pointer`。

```json
[
 {
  "script_addr": "0x08990B94",
  "instr_addr": "0x08990C8E",
  "opcode": "0x88",
  "kind": "pokemartbp",
  "list_addr": "0x2b072b07",
  "list_valid": false,
  "item_count": 0,
  "items": [],
  "maps": [
   {
    "group": 3,
    "num": 67,
    "name_zh": "吉野市"
   }
  ],
  "shared_flags": [],
  "conditions_heuristic": [
   "0x08990B95:goto_if",
   "0x08990B9B:goto_if",
   "0x08990BA1:call_if",
   "0x08990BA7:call_if",
   "0x08990BAD:call_if",
   "0x08990BB3:goto_if",
   "0x08990BB9:goto_if",
   "0x08990BBF:goto_if",
   "0x08990BCB:call_if",
   "0x08990BD9:goto_if"
  ],
  "raw_list": "",
  "classification": "suspected_desync",
  "root_cause": "列表参数不是 ROM 道具指针（0x2b072b07 / 0x88328732），据此拒绝计入有效库存；疑似上游脚本解析失步：根脚本 0x08990B94(map 3:67/local12 对象 script) 位于 0x0898-0x0899 数据/文本区（该字节型 32063306 全 ROM 出现 469 次），解码器可能把数据当指令前进。根因尚待上游脚本解析/第一处分派失步确认。原始记录保留，不作库存结论。"
 },
 {
  "script_addr": "0x08990B94",
  "instr_addr": "0x08990CA8",
  "opcode": "0x86",
  "kind": "pokemart",
  "list_addr": "0x88328732",
  "list_valid": false,
  "item_count": 0,
  "items": [],
  "maps": [
   {
    "group": 3,
    "num": 67,
    "name_zh": "吉野市"
   }
  ],
  "shared_flags": [],
  "conditions_heuristic": [
   "0x08990B95:goto_if",
   "0x08990B9B:goto_if",
   "0x08990BA1:call_if",
   "0x08990BA7:call_if",
   "0x08990BAD:call_if",
   "0x08990BB3:goto_if",
   "0x08990BB9:goto_if",
   "0x08990BBF:goto_if",
   "0x08990BCB:call_if",
   "0x08990BD9:goto_if",
   "0x08990C93:call_if",
   "0x08990C99:call_if"
  ],
  "raw_list": "",
  "classification": "suspected_desync",
  "root_cause": "列表参数不是 ROM 道具指针（0x2b072b07 / 0x88328732），据此拒绝计入有效库存；疑似上游脚本解析失步：根脚本 0x08990B94(map 3:67/local12 对象 script) 位于 0x0898-0x0899 数据/文本区（该字节型 32063306 全 ROM 出现 469 次），解码器可能把数据当指令前进。根因尚待上游脚本解析/第一处分派失步确认。原始记录保留，不作库存结论。"
 }
]
```
