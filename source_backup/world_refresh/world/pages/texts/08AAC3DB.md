# 文本 0x08AAC3DB

来源：`maps_research/out/scripts/text.json`，JSON pointer `/strings/0x08AAC3DB`。

控制符按原导出保留；Unicode为外部字表注释。

## 完整解码原文

```text
要踏上旅程了吗，\var[01]？\n现在我有些困扰……\p这只皮丘\n最近和他的玩伴走散了。\p我很想帮助他，\n可我手头还有工作需要处理，\l所以还不能离开……\p怎么样？\n你愿意帮他找到失散的伙伴吗？
```

## 原字节

`0ef10ca50bad08f4024e089e092a3bfd013dfe0e030fe60d980f7e0e34081c0b45b0b0fb1055108c0a5f0b12fe1126074e04f30c9e030b0d4e014811170b80089e37fb0d98050b0e18014e10cb0c9e3bfe07d70d980c1b0d1f05460f7e046c112f0e730ef1028608623bfa0c9c0f24054601d609d2086007b8b0b0fb100a094c0ee23dfe09d90fc40f32014e0c9e104503040be30b80030b057c0148092a3dff`

bytes：160

## 来源引用

| 脚本 | 指令 | 参数at | 命令 | 地图 |
|---|---|---|---|---|
| 0x089CCAC9 | 0x089CCAF8 | 0x089CCAFA | loadpointer | [3:66 若叶镇](../maps/g03_n066.md) |
| 0x089CCB10 | 0x089CCB33 | 0x089CCB35 | loadpointer | [3:66 若叶镇](../maps/g03_n066.md) |
| 0x089CCB4B | 0x089CCB6E | 0x089CCB70 | loadpointer | [3:66 若叶镇](../maps/g03_n066.md) |

原referenced_by（完整）：

```json
[
 {
  "script": "0x089CCB10",
  "at": "0x089CCB35",
  "cmd": "loadpointer"
 },
 {
  "script": "0x089CCB4B",
  "at": "0x089CCB70",
  "cmd": "loadpointer"
 },
 {
  "script": "0x089CCAC9",
  "at": "0x089CCAFA",
  "cmd": "loadpointer"
 }
]
```
