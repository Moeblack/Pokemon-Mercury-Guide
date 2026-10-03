# GB播放器、双音乐表与音乐目录

来源：`wiki_export/world/source_inventory.json`，JSON pointer `/mechanisms/7`。

## 已有规则

- flag0x174D清零用0x08960000常规表，置位用0x08DA0000 GB表；脚本0x08AEA158及文本确认开关语义。
- 两表各386项；主表385非空，第二表104差异曲目；现成MIDI/SF2/WAV保留。
- 叫声两个1554条视图按cry mode选择，不受GB曲目表开关支配。

## 具体边界/缺字段

- 曲名中的原版/参考标签不是ROM内建中文标题；WAV为参考渲染非硬件录音，未做声学验收。

## 证据入口

- `audio_research/README.md`
- `README_解包说明.md`
