# 文本 0x08AFCBBC

来源：`maps_research/out/scripts/text.json`，JSON pointer `/strings/0x08AFCBBC`。

控制符按原导出保留；Unicode为外部字表注释。

## 完整解码原文

```text
\ctrl[01 02]\ctrl[03 03]将外卖交给了顾客！
```

## 原字节

`fc0102fc030305f40d4a092e070d0462089e049307db3cff`

bytes：24

## 来源引用

| 脚本 | 指令 | 参数at | 命令 | 地图 |
|---|---|---|---|---|
| 0x08AFCBA3 | 0x08AFCBAF | 0x08AFCBB1 | loadpointer | [49:6 浅葱市](../maps/g49_n006.md) |
| 0x08AFCCAD | 0x08AFCCFB | 0x08AFCCFD | loadpointer | [3:95 40号水路](../maps/g03_n095.md) |
| 0x08F5EE8A | 0x08F5EE8A | 0x08F5EE8C | loadpointer | [49:8 浅葱市](../maps/g49_n008.md) |

原referenced_by（完整）：

```json
[
 {
  "script": "0x08AFCCAD",
  "at": "0x08AFCCFD",
  "cmd": "loadpointer"
 },
 {
  "script": "0x08AFCBA3",
  "at": "0x08AFCBB1",
  "cmd": "loadpointer"
 },
 {
  "script": "0x08F5EE8A",
  "at": "0x08F5EE8C",
  "cmd": "loadpointer"
 }
]
```
