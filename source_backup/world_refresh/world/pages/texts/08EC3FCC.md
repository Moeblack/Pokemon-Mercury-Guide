# 文本 0x08EC3FCC

来源：`maps_research/out/scripts/text.json`，JSON pointer `/strings/0x08EC3FCC`。

控制符按原导出保留；Unicode为外部字表注释。

## 完整解码原文

```text
善哉，善哉。\p施主察觉到了吗？\n你的宝可梦已经获得新的力量。
```

## 原字节

`0ba40fe13b0ba40fe137fb0be510c8021007a50304089e092a3dfe09d9030b016307d709660f21075d057e030a0e4d030b0879089237ff`

bytes：55

## 来源引用

| 脚本 | 指令 | 参数at | 命令 | 地图 |
|---|---|---|---|---|
| 0x08EC3B7A | 0x08EC3BC8 | 0x08EC3BCA | loadpointer | [56:52 满金市](../maps/g56_n052.md) |
| 0x08EC3BF0 | 0x08EC3C37 | 0x08EC3C39 | loadpointer | [56:52 满金市](../maps/g56_n052.md) |
| 0x08EC3C48 | 0x08EC3CA1 | 0x08EC3CA3 | loadpointer | [56:52 满金市](../maps/g56_n052.md) |

原referenced_by（完整）：

```json
[
 {
  "script": "0x08EC3B7A",
  "at": "0x08EC3BCA",
  "cmd": "loadpointer"
 },
 {
  "script": "0x08EC3BF0",
  "at": "0x08EC3C39",
  "cmd": "loadpointer"
 },
 {
  "script": "0x08EC3C48",
  "at": "0x08EC3CA3",
  "cmd": "loadpointer"
 }
]
```
