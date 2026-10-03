# 文本 0x08AE9DEA

来源：`maps_research/out/scripts/text.json`，JSON pointer `/strings/0x08AE9DEA`。

控制符按原导出保留；Unicode为外部字表注释。

## 完整解码原文

```text
如果你想让你的宝可梦\n学习顺风的话，欢迎随时来找我。
```

## 原字节

`0b6704c309d90e180b4309d9030b016307d70966fe0e900dd40c5603ea030b053d3b05430f5b0c890bed082910450d9837ff`

bytes：50

## 来源引用

| 脚本 | 指令 | 参数at | 命令 | 地图 |
|---|---|---|---|---|
| 0x08AE9D23 | 0x08AE9D46 | 0x08AE9D48 | loadpointer | [56:10 满金市](../maps/g56_n010.md) |
| 0x08AE9D50 | 0x08AE9D5B | 0x08AE9D5D | loadpointer | [56:10 满金市](../maps/g56_n010.md) |
| 0x08AE9D65 | 0x08AE9D79 | 0x08AE9D7B | loadpointer | [56:10 满金市](../maps/g56_n010.md) |

原referenced_by（完整）：

```json
[
 {
  "script": "0x08AE9D65",
  "at": "0x08AE9D7B",
  "cmd": "loadpointer"
 },
 {
  "script": "0x08AE9D50",
  "at": "0x08AE9D5D",
  "cmd": "loadpointer"
 },
 {
  "script": "0x08AE9D23",
  "at": "0x08AE9D48",
  "cmd": "loadpointer"
 }
]
```
