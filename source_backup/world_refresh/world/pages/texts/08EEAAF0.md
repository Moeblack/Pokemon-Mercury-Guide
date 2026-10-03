# 文本 0x08EEAAF0

来源：`maps_research/out/scripts/text.json`，JSON pointer `/strings/0x08EEAAF0`。

控制符按原导出保留；Unicode为外部字表注释。

## 完整解码原文

```text
\ctrl[06 00]获得了10点BracerPoints和12000$!
```

## 原字节

`fc0600057e030a089ea2a1032abce6d5d7d9e6cae3dde2e8e704f3a2a3a1a1a1b7abff`

bytes：35

## 来源引用

| 脚本 | 指令 | 参数at | 命令 | 地图 |
|---|---|---|---|---|
| 0x087B09AB | 0x087B0A08 | 0x087B0A0A | loadpointer | [52:20 真新镇](../maps/g52_n020.md) |
| 0x087B163F | 0x087B1644 | 0x087B1646 | loadpointer | [55:55 真新镇](../maps/g55_n055.md) |
| 0x087B3299 | 0x087B33BE | 0x087B33C0 | loadpointer | [56:76 30号道路](../maps/g56_n076.md) |
| 0x08EEA935 | 0x08EEA99A | 0x08EEA99C | loadpointer | [52:2 喇叭芽之塔](../maps/g52_n002.md) |

原referenced_by（完整）：

```json
[
 {
  "script": "0x087B163F",
  "at": "0x087B1646",
  "cmd": "loadpointer"
 },
 {
  "script": "0x087B3299",
  "at": "0x087B33C0",
  "cmd": "loadpointer"
 },
 {
  "script": "0x08EEA935",
  "at": "0x08EEA99C",
  "cmd": "loadpointer"
 },
 {
  "script": "0x087B09AB",
  "at": "0x087B0A0A",
  "cmd": "loadpointer"
 }
]
```
