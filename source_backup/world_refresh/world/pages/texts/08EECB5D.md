# 文本 0x08EECB5D

来源：`maps_research/out/scripts/text.json`，JSON pointer `/strings/0x08EECB5D`。

控制符按原导出保留；Unicode为外部字表注释。

## 完整解码原文

```text
\ctrl[0D 10]打开精灵齿轮中的地图，\n\ctrl[0D 10]对已去过的城镇按下A键\n\ctrl[0D 10]可以立刻飞翔至该城镇了。
```

## 原字节

`fc0d1002d207b8075b08bc025f091010a1030b031f0d243bfefc0d1003790f210b2504c5030b0249106501130de6bb05e7fefc0d1007d70f24087507da03cc0e151092042d02491065089e37ff`

bytes：77

## 来源引用

| 脚本 | 指令 | 参数at | 命令 | 地图 |
|---|---|---|---|---|
| 0x08EECC0D | 0x08EECC17 | 0x08EECC19 | loadpointer | [44:1 31号道路](../maps/g44_n001.md) |

原referenced_by（完整）：

```json
[
 {
  "script": "0x08EECC0D",
  "at": "0x08EECC19",
  "cmd": "loadpointer"
 }
]
```
