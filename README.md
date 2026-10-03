# 宝可梦水银 1.1 · 玩家攻略

**[在线攻略](https://moeblack.github.io/Pokemon-Mercury-Guide/)** · [GitHub仓库](https://github.com/Moeblack/Pokemon-Mercury-Guide) · [本地攻略首页](index.html)。首页可按名称、地点或关键词搜索；发布包也支持直接打开HTML离线阅读。

## 四类目录

| 内容 | 数量 | 入口 |
|---|---:|---|
| 支线攻略 | 97 条 | [任务目录](quests/index.html) · [按地点](quests/by_location.html) |
| 道具搜集 | 750 条 | [道具目录](items/index.html) · [按地点](items/by_location.html) |
| 宝可梦获取 | 1554 个内部槽位 | [图鉴目录](pokemon/index.html) · [按地点](pokemon/by_location.html) · [形态与占位](pokemon/forms.html) |
| 训练家配队 | 743 条 | [训练家目录](trainers/index.html) · [按姓名](trainers/by_name.html) |

1554个内部槽位包含形态与占位，不等于1554种不同宝可梦。道具已有491条定位到来源；其余条目仍保留用途与相关支线。训练家共1892名队伍成员，608名保留自定义配招，1284名按基础等级重建默认配招。

## 怎样使用

- 首页搜索示例：泥炭块、月月熊、阿四、红色火球，或城市名称。
- 支线页提供准备条件、行动顺序、完成方式与报酬；相关宝可梦、道具、训练家可交叉跳转。
- 宝可梦页先显示获取与进化方式；地图页及静态地图保留原资料链接。
- 条件未解析的位置直接标记待补。支线目前有84页整理了主要步骤与报酬，13页仍缺中间步骤；具体名单见[覆盖记录](data/delivery_summary.json)。
- 正文面向游戏操作；原始编号、脚本证据与资料来源放在页底或data目录。

## 文件组织

- `index.html`：离线全文检索与四类入口。
- `quests/`、`items/`、`pokemon/`、`trainers/`：每条资料同时保存Markdown和HTML。
- `data/`：结构化记录、目录范围、覆盖统计与补提取证据。
- `scripts/`：各分类生成器与整合脚本；重生成某分类后运行`integrate_guide.py`，最后运行`build_site.py`。

研究工作区的精灵图片与原始资料引用同级工程`../wiki_export/`，地图底图保存在`maps/`内。公开发布使用独立的`_site/`：所需精灵图已收录到`assets/vendor/`，打包时改写图片路径；仅在本地工程存在的原始证据链接在网页版保留为文字说明。ROM与存档不包含在发布包内。


## RGB地图与野生Mega

- [打开地图图鉴](maps/index.html)：首次进入先选地点，再次进入恢复上次场景；指定地点链接优先于浏览记录。
- [28种野生Mega所在地](pokemon/wild_mega.html)
- 保留871张源地图记录，其中858张可生成地形底图，复用742份独立图像；11组区域提供拼接总览。源地图记录不等于当前可游玩地点，同名旧布局另有标注。
- 已整理8756条地点记录，1535篇攻略接入地图卡片；独立地点、剧情触发区域、地图范围和未定位记录分开处理。同一事件的多个触发格不再算作多个遭遇或奖励。
- 固定对象层覆盖58张地图、128个大型对象，恢复由精灵拼成的建筑，并应用原生前景遮挡；非零隐藏旗标的剧情对象不混入基础场景，未解析对象来源保留在报告中。
- 13张源地图的图块包或metatile描述表失效；121张有局部图块或调色板缺口。全部28种野生Mega所在地均有可用底图。

### 制作方案

副调色板按ROM实际加载方式读取`palettes+0xE0`，修正旧图配色偏差。图块包按地址缓存，主副组合生成一次图块图集；地图布局去重；一次批处理最多6路并行编码，攻略之间只复用图像并叠加矢量标记。区域只按连接方向和偏移拼接；楼梯和洞口作为入口跳转，冲突连接不强行拼合。

界面离线运行，不加载CDN或服务器数据；支持搜索、筛选、缩放、点位与列表联动。出入口显示目标地图ID及对应入口编号，点击精确定位；双向对应与回程不同的记录分别标注。事件按入口、条件、类型归并；不同对象、条件、地图保留，奖励指令不累加为一次收益。详见[data/atlas_event_identity_report.json](data/atlas_event_identity_report.json)。

完整设计与字段约定见[data/atlas_plan.json](data/atlas_plan.json)。生成顺序：`build_atlas_data.py` → `render_atlas.py` → `build_wild_mega_guide.py` → `integrate_guide.py` → `build_atlas_ui.py` → `build_site.py`。以上均通过`uv run`执行，地图渲染器按指纹增量复用，不逐张启动进程。

截图来源问题见[data/atlas_source_issues.json](data/atlas_source_issues.json)，建筑层明细见[data/atlas_objects_report.json](data/atlas_objects_report.json)。已交付的冰天地[第二阶段路线图](maps/routes/ice_53_6_23_to_24.png)及[前置条件与证据](data/ice_53_6_route.json)保留供查阅。

## GitHub Pages 发布

- 发布分支为远端`main`，工作流为`.github/workflows/pages.yml`。推送后自动打包并部署。
- 现有生成页面与数据已提交，打包执行`uv run scripts/package_pages.py`，输出`_site/`，不需要父工程、ROM或存档。
- 修改页面生成器后执行`uv run scripts/build_site.py`；地图摘要修改后执行`uv run scripts/build_atlas_ui.py`。提交生成产物后再推送。
- 只有新增外部精灵图片时，在完整本地研究工作区执行`uv run scripts/package_pages.py --vendor-assets`，将新增`assets/vendor/`图片一并提交。
- 首页仅保留名称、功能与操作说明，不使用宣传句；随机词条每次打开抽取三个，可“换一组”，点击执行搜索。
- “游戏内地图”的地点点击、名称选择及左侧城镇按钮均直接打开场景，不再先筛选卡片。进入后可用“同地点场景”切换其他地图。默认场景按无来源异常、有底图、室外地图优先，同级优先攻略地点记录较多的场景；这只是浏览默认顺序，不定义游戏剧情入口。
- 区域底图、热点与标定来源：原研究工程`reference/azoth-wiki/docs/locations/worldmap.png`、`worldmap_data.json`、`worldmap.html`；不是本轮新提取的ROM图形。场景归属取本ROM导出的`wiki_export/world/data/maps.json`地区编号，已核对参考地区名称一致；不导入参考百科的遭遇数据。
- 区域导航生成器为`uv run scripts/build_world_picker.py`，需要完整本地研究工程；生成的`maps/world-data.js`和`maps/world/region.png`已随仓库发布，Pages部署不需要父工程。技术信息仍由默认关闭的Debug开关控制。
