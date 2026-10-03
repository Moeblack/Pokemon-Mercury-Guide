# 世界资料输入盘点

目的：供Main制定Wiki事件提取契约；不是完整导出器或全ROM覆盖报告。仅新增本目录两个盘点文件，未改旧数据。

完整字段名及观察类型在 `source_inventory.json` 的 `sources[].object_schema`；相同结构合并列出paths。代表记录仅为小型投影，附原源JSON pointer；不复制全部文本或大批原记录。

## 1. 下一阶段关键schema与关联

**地图**：`headers.json.maps[]` 用 `group,num` 标识，`map_name_zh` 为显示名，`map_name_ptr` 为名称来源，`region_map_section_id` 为地区段ID。871图均有中文名；165条地区段名称池见 `maps_research/out/maps/mapsec_names.json`，871图使用124个段ID。没有独立“大地区归属”字段；vanilla猜名不可用作改版身份。

**训练师队伍**：`trainers.json.trainers[]` 含 `id,name,trainerClass,partySize,partyPtr,party,scripts,script_types,special_rules,trainer_forced_shiny` 等。`party[]` 主要字段如下：

`slot,iv_raw,iv_semantics,level,species_id,species_name,species_types,raw,heldItem,heldItem_name,moves,ev_spread_index,ev_spread`；条件字段为 `ev_spread_gate,battle_types_camomons,battle_types_camomons_names,camomons_source_moves,forced_shiny`。

`moves[] = {id,name,type}`；`ev_spread = {index,address,nature,ivs,hp_ev,atk_ev,def_ev,spe_ev,spa_ev,spd_ev,ball,ability}`（可为null）。743普通记录，1892队员；273队员含有效spread，111的4只含Camomons派生，403的3只强制闪光。id0为NONE；919/920特殊builder不能补成普通记录。

**商店**：`shops[] = {script_addr,instr_addr,opcode,kind,list_addr,list_valid,item_count,items,maps,shared_flags,conditions_heuristic,raw_list}`。`items[] = {index,name,price,itemId}`；`maps[] = {group,num,name_zh}`。58个 `instr_addr` 唯一；库存道具join核心index，不能仅用itemId。price是现成道具表值，kind和启发式条件须保留，不能擅自当成全部动态实际价格/解锁保证。

**脚本**：`scripts.json.scripts` 是ROM地址键字典。块含 `addr,sources,instructions,unknown_at,bytes`，部分含 `runtime_stop,terminated_by_FF`。`instructions[]` 含 `addr,opcode,name,names,args,raw,layout_source`；`args[] = {width,value,addr,class?}`，value是整数，addr是参数ROM地址，class观察到script/text/raw/unclassified。

**地图→脚本→文本**：

- `events.maps["group:num"]` 的 objects/coord_events/bg_events 含script。对象可用local_id、各事件用kind+index定位。
- `scripts.sources[] = {kind,where}`；直接来源object/bg/coord/map_script/map_script_table的where含地图，例如`1:0/local1`、`0:4/tag5`、`52:0`。
- branch的where是父脚本地址，需递归继承地图来源并防环；std_script/code_referenced不要硬配地图。
- `text.strings[ROM地址] = {addr,text,bytes,raw,referenced_by}`；`referenced_by[] = {script,at,cmd}`。**at在已核查样本是参数地址，不是指令地址**。可用script+参数addr，或class=text的value关联文本键。
- 已核实例：`1:0/local1 → script 0x08160529 → loadpointer指令0x08160529 → args[1].addr 0x0816052B / value 0x08172255 → text 0x08172255`。
- 训练师已有trainer_usage与scripts引用可递归归图；商店已有maps。共享文本/脚本允许多地图，不去重丢来源。
- 文本保留`\n / \p / \l`和其他控制符、原raw。剧情只按NPC/事件及明确指令分组，不以词语出现证明可得，不臆造线性通关流程。

## 2. 14份明确输入与实际数量

| 文件 | 当前实际数量 | 稳定ID / 边界 |
|---|---|---|
| `maps_research/out/maps/headers.json` | {"maps": 871, "groups": 58, "nonempty_map_name_zh": 871, "distinct_used_region_map_section_ids": 124} | group + num（group:num）；本快照871唯一。header_addr为来源地址，map_name_zh不唯一。 |
| `maps_research/out/events/events.json` | {"maps": 871, "objects": 6412, "warps": 2861, "coord_events": 724, "bg_events": 1830, "hidden_items_kind7": 451} | maps的group:num键；子事件用(group,num,event_kind,index)，object另有local_id；addr为ROM来源，不把local_id跨图当唯一。 |
| `maps_research/out/scripts/text.json` | {"strings": 7513} | strings的ROM地址键及addr；同文本可有多个地址，不以text去重身份。 |
| `maps_research/out/scripts/scripts.json` | {"entry_count_field": 6680, "scripts": 12627, "instruction_count_field": 102298, "instruction_occurrences_including_stop_markers": 102322, "roots_with_runtime_stop": 24} | scripts的ROM地址键及addr；instruction addr可能在多个脚本块重复，应保留source script/raw，不以出现数作唯一指令数。 |
| `trainers_research/out/trainers.json` | {"ordinary_trainers": 743, "party_members": 1892, "ev_spread_members": 273, "forced_shiny_members": 3} | id（0..742普通表），party用(id,slot)；name不唯一；919/920不得补成普通记录。 |
| `trainers_research/out/trainer_usage.json` | {"trainer_ids": 547, "usage_records": 1133, "out_of_base_ids": ["919", "920", "921"]} | usage的训练家ID字符串键；引用用(trainer_id,script,insn_addr,role)，type/mode仅保留现成语义标签。 |
| `trainers_research/out/overrides.json` | {"ev_spreads": 126, "forced_shiny_records": 1, "mirror_candidate_records": 151, "deprecated_records_not_additional": 1} | spread index；forced_shiny trainerId及slot；mirror条目id/address/index按原字段保存，不作为再战选表依据。 |
| `encounters_research/out/encounters.json` | {"time_tables": 4, "map_records_by_time": {"day": 133, "morning": 94, "evening": 95, "night": 100}, "map_time_records": 422, "slot_rows": 6624, "swarm_records": 16, "broadcast_records": 100, "broadcast_sets": 300, "broadcast_species_slots": 1200} | table时间键 + map_group + map_num + method + slot；entry_addr/info_addr/wild_addr保留证据；广播index/table_addr+set.day_of_week+slot，群聚addr/mapsec_id。 |
| `encounters_research/out/shops.json` | {"valid_shops": 58, "rejected_invalid_pointer": 2, "item_rows": 518} | instr_addr本快照58唯一，保留script_addr与list_addr；库存列表可共享；道具用index关联核心，不只用itemId。 |
| `encounters_research/out/early_game_resources.json` | {"encounter_named_groups": 4, "encounter_map_keys": 8, "encounter_nonempty_map_keys": 6, "encounter_map_time_keys": 24, "shop_named_groups": 7, "goldenrod_counter_records": 16} | 命名分组只是检索标签；遭遇回链map group:num+time+method；商店回链instr_addr，不能将重复摘要当新来源。 |
| `parallel_acceleration/map_relations/nodes.json` | {"nodes": 871, "groups": 58} | id=group:num（871唯一），key=gNN_nNNN为文件名键。 |
| `parallel_acceleration/map_relations/edges.jsonl` | {"edges": 3105, "static_warps": 2816, "dynamic_warps": 45, "connections": 244} | edge_id为现成顺序ID，跨重建稳定性无保证；推荐来源复合键(source.map,source_object.kind,index)，本快照3105唯一，附source_object.addr。 |
| `parallel_acceleration/map_relations/dynamic_edges.json` | {"dynamic_edges": 45, "fixed_destinations_resolved": 0} | 同edges；edge_id用于本快照join；target.map=null，禁止生成127:127真实地图。 |
| `parallel_acceleration/map_relations/var_flag_index.jsonl` | {"records": 22419, "unique_instruction_addresses": 22419, "d0_records": 44} | addr本快照22419唯一；保留opcode/raw；变量或旗标须连同kind/flag_space/role解释，不能只按整数合并不同空间。 |

计数补充：脚本字段102298不含24个stop，实际指令数组出现102322；这些都不是去重指令数。事件6412对象／2861warp／724coord／1830bg，其中451隐藏道具。野生4时段133/94/95/100地图记录，共6624槽。

## 3. 已有结构化资料与待补提取

### 地图与地区

已有：871地图、中文地图/地区段名称、事件、坐标、地图类型、天气/music编号；静态关系图；165条mapsec名称池。

待补/边界：按地图合并字段/关联核心名称与媒体；若需要关都/城都等大地区分类，当前14输入无独立归属字段，须由Main决定是否补取或标注。

### 训练师与队伍

已有：743普通记录、1892队员、名字/等级/持物/招式/脚本引用、273 EV配置命中、111的Camomons与403的强制闪光。

待补/边界：玩家可读队伍目录及地图关联；训练师职业名、特殊ID人物/队伍、全等级缩放公式不在现成结构化字段内。

### 野生获取、广播与群聚

已有：422时段地图记录/6624槽，权重表及分钓竿组、16群聚、100广播。

待补/边界：把method/slot与全局权重/时段/地图join成获取目录，保留rate与槽权重区别；不计算未证总体概率。

### 商店

已有：58有效静态库存，item index/name/price/itemId、地图和启发式前文条件；2拒绝记录。

待补/边界：物品→商店反向目录、kind与价格语境展示；不把前文条件写成确定解锁攻略。

### 隐藏道具

已有：451条kind7事件有道具ID/数量/旗标偏移/坐标/underfoot，是结构化字段，不仅文本。

待补/边界：join核心道具名/index与地图名，原始flag offset不直接编造全局flag语义。

### 赠送/蛋/定点宝可梦与普通道具获取

已有：脚本已有givepokemon/giveegg/setwildbattle/additem参数结构，详acquisition_instruction_inventory；不是仅自然语言原文。

待补/边界：尚无独立可信获取目录；需从现成脚本有限提取来源/参数/变量/条件，保留候选级别与坏根排除；不能把78条setwildbattle地址直接说成78处可捕获宝可梦。

### 文本与剧情

已有：7513文本带引用，12627脚本带source/branch/args，22419变量旗标索引含根/地图。

待补/边界：生成文本检索与地图/事件/脚本相互链接即可复用；剧情章节/任务步骤/先后可达性不是已有字段，另按Main所选范围补取。

### 系统机制和音乐

已有：已证Camomons、EV、广播/群聚、时段、GB双曲表、mode9条件性机制等准确报告入口。

待补/边界：将现有规则与边界整理为目录；RTC仅启用记录且实际时钟未确认，完整缩放/特殊队伍不猜。

明确获取指令仅作候选：

| 指令名 | 出现次数 | 去重地址数 |
|---|---:|---:|
| givepokemon | 48 | 48 |
| giveegg | 7 | 7 |
| setwildbattle | 79 | 78 |
| dowildbattle | 52 | 52 |
| additem | 95 | 95 |

上述不是可信可获得地点数，尤其24stop根、变量参数、共享脚本及动态模板均不能忽略。隐藏道具已有字段，不是仅原文本；赠送/定点是已解码args，尚非完整获取目录。

## 4. 时段、概率与已证机制入口

### 第三道馆Camomons与小茜

入口：`README_解包说明.md`；`trainers_research/README.md`；`trainers_research/out/whitney.json`；`trainers_research/out/trainers.json`；`trainers_research/out/overrides.json`

- 规则对双方适用：所有宝可梦属性改为前两个招式的属性，不能按基础物种属性推断。
- 初战ID111：皮皮17、长耳兔19、姆克鸟21、大奶罐23；大奶罐嬉闹/铁头对应妖精/钢，持吃剩的东西。
- 仅ID111已有special_rules；ID392同名不构成同规则证据。
- 边界：派生属性和配队推论不等于实战验证。

### EV spreads与强制闪光

入口：`trainers_research/README.md`；`trainers_research/out/overrides.json`

- partyFlags==3且aiFlags>1、索引1..125时首u16低字节作spread索引；10B字段为nature/ivs/hp_ev/atk_ev/def_ev/spe_ev/spa_ev/spd_ev/ball/ability。
- 训练家403槽0/1/2强制闪光；不是队伍替换表。
- 边界：高字节含义未证；151镜像候选不作为选表；ability策略不保证每场观测值。

### 等级缩放

入口：`trainers_research/README.md`；`trainers_research/out/trainers.json`

- 现成README定位IsBossTrainerClassForLevelScaling等消费者及普通队伍level字段。
- 边界：当前入口仅局部消费者证据；没有完整缩放公式/触发条件导出，不套官方规则，不把表内等级作为所有实际战斗等级。

### 广播

入口：`encounters_research/README.md`；`encounters_research/out/encounters.json`

- consumer 0x09D647B0读取0x09DDDBE0，100条×26byte；每条3组各4物种。
- dayOfWeek数值3/4/0分别选set0/1/2，其他星期及未命中走现成fallback；星期标签和证据强度原样保留。
- 触发后槽权重40/20/20/20；Flag0x17A1==0、Flag31!=0、[sp+0xc]==0、rand%3!=0等为现成门控字段。
- 边界：旧0x09DDDBC6/101条已撤回；内部槽权重不是总体遭遇率；收音机卡剧情与旗标实现、UI/状态生命周期未全面闭合。

### 群聚

入口：`encounters_research/out/encounters.json`；`encounters_research/README.md`

- 0x09E3CDCE共16条{u16 mapsec_id,u16 species}，mapsec_id==0终止；按地区段关联，多地图可能共用。
- 边界：不凭静态表断言当前群聚已激活或可达。

### 时段与RTC

入口：`encounters_research/README.md`；`encounters_research/out/encounters.json`

- 现成表选择时段：清晨05:00–09:59、白天10:00–16:59、黄昏17:00–18:59、夜晚19:00–04:59。
- 边界：Main确认当前仅有模拟器RTC启用记录，未提供完整RTC报告路径；游戏实际时钟正确性未确认。此处不猜RTC报告路径，不全面反编译。

### mode9环境覆盖生命周期

入口：`parallel_acceleration/save_evidence/environment_override_lifecycle.md`；`parallel_acceleration/save_evidence/environment_override_lifecycle.json`；`parallel_acceleration/save_evidence/mode9_parameter_semantics.md`；`parallel_acceleration/save_evidence/mode9_end_callback_window.md`

- 状态conditional_resume_and_cleanup_mechanism_documented；14根写5007为12/19，mode9消费13byte并保存5C+14到0x020386C4。
- 存在config提前结束分支；callback汇合并安装priority10恢复task，满足条件才清外层门控；保存值保持且续接执行后，7根直接清5007为0、7根经clearflag再清0。
- 边界：C1–C8及7项open_conditions必须保留；不是全路径finally，不保证异步必执行/5007必清，不是恢复任意旧值。
- 边界：919/920走特殊builder，人物/队伍算法未证，普通743目录无join不是漏普通记录。

### GB播放器、双音乐表与音乐目录

入口：`audio_research/README.md`；`README_解包说明.md`

- flag0x174D清零用0x08960000常规表，置位用0x08DA0000 GB表；脚本0x08AEA158及文本确认开关语义。
- 两表各386项；主表385非空，第二表104差异曲目；现成MIDI/SF2/WAV保留。
- 叫声两个1554条视图按cry mode选择，不受GB曲目表开关支配。
- 边界：曲名中的原版/参考标签不是ROM内建中文标题；WAV为参考渲染非硬件录音，未做声学验收。

普通陆地权重20/20/10/10/10/10/5/5/4/4/1/1；水面与碎岩/撞树60/30/5/4/1；破旧钓竿70/30、好钓竿60/20/20、厉害钓竿40/40/15/4/1。权重在encounters.probabilities中，必须按方法/竿组映射槽位；不与时段或触发门控相乘生成未证全局概率。

## 5. 仅引用现成媒体

- static_map：`maps_research/out/MANIFEST.json`；`maps_research/out/maps/render_report.json`；`maps_research/out/maps/per_map/index.json`。仅引用现成静态PNG。render_report.skipped_or_tile_problems的413键含多类问题，不等于413张未渲染地图；9张未渲染与102张覆盖缺口按现成报告/README区分。
  - `maps_research/out/maps/png/gNN_nNNN.png`
- pokemon_sprites：`out/sprites/sprite_manifest.json`。仅提供现成manifest与路径；不在本任务读全媒体、渲染或重组frame×palette_page。
  - `out/sprites/frames/{front,back}/`；`out/sprites/frames_shiny/{front,back}/`
- music_audio：`audio_research/README.md`；`audio_research/out/cries/cries.json`。曲目目录/数目来自已读音频README，未扫描或重新验收媒体；不猜未在报告明确给出的manifest文件名。
  - `audio_research/out/midi/`；`audio_research/out/sf2/`；`audio_research/out/wav/`；`audio_research/out_alt_table/`

## 6. 必须保留的界限

- 本盘点服务Wiki版块选择，不以完整代码、全ROM字节覆盖、全函数追踪为完成标准；本次仅盘点，不实现完整导出器。
- 数据为既有静态提取，不证明任何特定存档的剧情可达、已解锁或实际战斗结果。
- 871张图；45动态warp固定目的地runtime未知，不能补造127:127地图；dangling=0不等于剧情图完整。
- 743只计普通trainer；919/920进入特殊builder，不是普通表漏项/非法。参考type名称不得覆盖本ROM特殊路径含义。
- 24越界stop根的停止机制已有解释，但来源/此前失步/可达性未因此确认；对候选获取/商店/剧情不得无条件信任。
- type、dow、广播槽权重与门控只按现成证据；内部权重不当总体概率。
- 已读地图README含旧计数/旧限制（如6102文本/12381脚本、中文名未恢复等），以本次实际JSON计数和根README现行纠正为准，不改旧文件。
- 已有shops README坏根原因属历史阶段；根README已指出0x08990B94落在map3:77方块数组且对象模板有runtime覆盖，不能只以静态坏指针断言游戏执行。
- source_sha256/sha256在多个原始JSON中为ROM摘要，不能替代文件摘要；本盘点file_sha256为实际文件字节hash。
- 地址与复合ID稳定性限当前精确ROM版本；中文标签用外部字表，参考vanilla/weekday/type语义须保留原证据级别。

## 7. 本次限定核对与交接

- 14输入及3补充JSON全部存在；仅6个父目录非递归列文件，路径修正为所有短名均相对于对应out或map_relations目录。实际列表在JSON，不遍历全工程。
- 全量聚合字段并核对关键数量、代表投影原源pointer、map→script→text参数地址join；输入文件SHA前后保持。未跑测试、游戏、反汇编、旧提取器或新媒体渲染。
- 成长经验转Main/core：`C:/Users/Moeblack/Downloads/PKHeX-Mercury/docs/mercury-save-format.md`，Main提供0803E830→09DFE8CC、步长0x400；本任务不读取/重复研究。
- 本轮不写export_world.py；等待Main明确事件提取契约后再制作871地图、743普通训练师、58库存、7513原文本等目录。
