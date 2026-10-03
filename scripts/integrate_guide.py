# /// script
# requires-python = ">=3.10"
# ///
"""Assemble indexes and derived cross-links from the authored quest records."""
from pathlib import Path
from collections import defaultdict, Counter
import json, re
G=Path(__file__).resolve().parents[1]
def load(p):return json.loads((G/p).read_text(encoding='utf-8-sig'))
def save(p,d):(G/p).write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
def cell(s):return str(s).replace('|','／').replace('\n',' ')
def label(s):
    s=re.sub(r'（[^）]*(?:目录关联|地图页标题|local_id|旗标|0x)[^）]*）','',str(s))
    return cell(s)
quests=[json.loads(p.read_text(encoding='utf-8')) for p in sorted((G/'data/quests').glob('*.json'))]
manifest=load('data/quest_manifest.json')
refs={s:defaultdict(list) for s in ('items','pokemon','trainers')}
for q in quests:
    for field,section in [('related_items','items'),('related_species','pokemon'),('related_trainers','trainers')]:
        for v in q[field]:
            if isinstance(v,int):refs[section][v].append({'id':q['id'],'title':q['title'],'page':f"quests/{q['id']:03}.md"})
# Managed generated blocks can be rebuilt after any section generator runs.
for section,mapping in refs.items():
    for sid,rows in mapping.items():
        p=G/section/f'{sid:04}.md'
        if not p.exists():continue
        body=p.read_text(encoding='utf-8')
        body=re.sub(r'\n?<!-- quest-links:start -->.*?<!-- quest-links:end -->\n?','\n',body,flags=re.S)
        rows={x['id']:x for x in rows}
        block='\n<!-- quest-links:start -->\n## 相关支线\n\n'
        if section!='trainers':block+='任务可能要求携带本条目，或将其作为奖励；具体用途见任务步骤。\n\n'
        block+='\n'.join(f"- [{x['title']}](../{x['page']})" for x in sorted(rows.values(),key=lambda x:x['id']))+'\n<!-- quest-links:end -->\n'
        p.write_text(body.rstrip()+'\n'+block,encoding='utf-8')
save('data/quest_crosslinks.json',{s:{str(k):v for k,v in m.items()} for s,m in refs.items()})
lines=['# 支线攻略','',f'共 **{len(quests)} 条支线**。按任务名称查找，进入页面可看接取地点、准备条件、行动步骤、报酬和相关队伍。','', '原任务目录共100行；主线「宝可梦大师之路」不列入支线，同名「8bit的感动」两行合并为一页。','', '[按接取地点浏览](by_location.md) · [返回攻略首页](../index.html)','', '| 任务 | 接取地点／人物 | 页面内容 |','|---|---|---|']
places=defaultdict(list)
for q in quests:
    starts=q['start_locations']
    loc='；'.join(label(x.get('place') or x.get('map_id') or '地点待补') for x in starts) or '接取地点待补'
    status='步骤与报酬已整理' if q['status']=='compiled' else '已整理已知流程，仍有步骤待补'
    lines.append(f"| [{q['title']}]({q['id']:03}.md) | {loc} | {status} |")
    for x in starts or [{'place':'接取地点待补'}]:places[label(x.get('place') or x.get('map_id') or '接取地点待补')].append(q)
lines+=['','## 阅读方式','','- 相邻任务可能连续推进或共用结算；共享奖励只领取一次。','- 出现剧情对战不等于可以捕获，赠送与对战在页面中分开说明。','- 「待补」直接指出缺少的接取条件或中间步骤；已知剧情、奖励与队伍仍可查阅。','- 地图中的部分「真新镇」是共用过场标签，不能当作实际接取地点。','']
(G/'quests/index.md').write_text('\n'.join(lines),encoding='utf-8')
lines=['# 按接取地点查支线','','[任务总目录](index.md) · [攻略首页](../index.html)','']
for place,rows in sorted(places.items()):
    lines+=['## '+place,'']
    for q in {q['id']:q for q in rows}.values():lines.append(f"- [{q['title']}]({q['id']:03}.md)")
    lines.append('')
(G/'quests/by_location.md').write_text('\n'.join(lines),encoding='utf-8')
status=Counter(q['status'] for q in quests)
summary={'scope':'水银1.1指定ROM的玩家攻略','homepage':'index.html','counts':{'quests':len(quests),'items':len(list((G/'items').glob('[0-9][0-9][0-9][0-9].md'))),'pokemon_internal_slots':len(list((G/'pokemon').glob('[0-9][0-9][0-9][0-9].md'))),'trainers':len(list((G/'trainers').glob('[0-9][0-9][0-9][0-9].md')))},'quest_statuses':dict(status),'quests_with_remaining_steps':[{'id':q['id'],'title':q['title'],'open_questions':q['open_questions']} for q in quests if q['status']!='compiled'],'crosslink_targets':{s:len(m) for s,m in refs.items()},'items_summary':load('data/items_summary.json'),'pokemon_summary_file':'data/pokemon_summary.json','trainers_summary_file':'data/trainers_summary.json','quest_catalog_rows':100,'merged_rows':[63,64],'excluded_main_story_rows':[r['index'] for r in manifest['excluded_main_story_rows']],'source_policy':'ROM提取记录与脚本整理；补充分支不自动证明地图入口。未改动ROM或存档。'}
atlas_stats=None
if (G/'data/atlas_render_report.json').exists():
    ar=load('data/atlas_render_report.json');am=load('data/atlas_manifest.json');ast=load('data/atlas_data_summary.json')
    for mid,rr in ar['maps'].items():
        am['maps'][mid]['render_status']=rr['status']
        am['maps'][mid]['missing_tiles']=rr.get('missing_tiles')
    for rid,rr in ar['regions'].items():
        am['regions'][rid]['render_status']=rr['status']
        am['regions'][rid]['overview']=rr['image']
    save('data/atlas_manifest.json',am)
    atlas_stats={'map_count':len(ar['maps']),'rgb_maps':sum(r['status']!='unavailable' for r in ar['maps'].values()),'shared_base_images':len({r['image'] for r in ar['maps'].values() if r['status']!='unavailable'}),'stitched_regions':ast['stitched_regions'],'points':ast['points'],'guide_pages_with_maps':ast['guide_pages_with_maps'],'unavailable_maps':ar['unavailable_maps'],'partial_maps':ar['partial_maps'],'mega_species':28,'viewer':'maps/index.html','mega_guide':'pokemon/wild_mega.html','plan':'data/atlas_plan.json','render_report':'data/atlas_render_report.json'}
    summary['atlas']=atlas_stats
save('data/delivery_summary.json',summary)
save('data/quests.json',{'quests':quests})
readme=f'''# 宝可梦水银 1.1 · 玩家攻略

**直接打开 [攻略首页](index.html)**。这是本地离线攻略，不需要启动服务器；首页可按名称、地点或关键词搜索。

## 四类目录

| 内容 | 数量 | 入口 |
|---|---:|---|
| 支线攻略 | {len(quests)} 条 | [任务目录](quests/index.html) · [按地点](quests/by_location.html) |
| 道具搜集 | {summary['counts']['items']} 条 | [道具目录](items/index.html) · [按地点](items/by_location.html) |
| 宝可梦获取 | {summary['counts']['pokemon_internal_slots']} 个内部槽位 | [图鉴目录](pokemon/index.html) · [按地点](pokemon/by_location.html) · [形态与占位](pokemon/forms.html) |
| 训练家配队 | {summary['counts']['trainers']} 条 | [训练家目录](trainers/index.html) · [按姓名](trainers/by_name.html) |

1554个内部槽位包含形态与占位，不等于1554种不同宝可梦。道具已有491条定位到来源；其余条目仍保留用途与相关支线。训练家共1892名队伍成员，608名保留自定义配招，1284名按基础等级重建默认配招。

## 怎样使用

- 首页搜索示例：泥炭块、月月熊、阿四、红色火球，或城市名称。
- 支线页提供准备条件、行动顺序、完成方式与报酬；相关宝可梦、道具、训练家可交叉跳转。
- 宝可梦页先显示获取与进化方式；地图页及静态地图保留原资料链接。
- 条件未解析的位置直接标记待补。支线目前有{status.get('compiled',0)}页整理了主要步骤与报酬，{sum(v for k,v in status.items() if k!='compiled')}页仍缺中间步骤；具体名单见[覆盖记录](data/delivery_summary.json)。
- 正文面向游戏操作；原始编号、脚本证据与资料来源放在页底或data目录。

## 文件组织

- `index.html`：离线全文检索与四类入口。
- `quests/`、`items/`、`pokemon/`、`trainers/`：每条资料同时保存Markdown和HTML。
- `data/`：结构化记录、目录范围、覆盖统计与补提取证据。
- `scripts/`：各分类生成器与整合脚本；重生成某分类后运行`integrate_guide.py`，最后运行`build_site.py`。

精灵图片与原始资料仍引用同级工程中的`../wiki_export/`资源，新地图底图保存在本攻略`maps/`内。移动攻略时应保留原资料的相对位置。ROM和存档未修改。
'''
if atlas_stats:
    readme+=f'''

## RGB地图与野生Mega

- [打开可缩放区域大地图](maps/index.html#map=3:76)
- [28种野生Mega所在地](pokemon/wild_mega.html)
- 保留{atlas_stats['map_count']}张源地图记录，其中{atlas_stats['rgb_maps']}张可生成地形底图，复用{atlas_stats['shared_base_images']}份独立图像；{atlas_stats['stitched_regions']}组区域提供拼接总览。源地图记录不等于当前可游玩地点，同名旧布局另有标注。
- 已整理{atlas_stats['points']}条地点记录，{atlas_stats['guide_pages_with_maps']}篇攻略接入地图卡片；独立地点、剧情触发区域、地图范围和未定位记录分开处理。同一事件的多个触发格不再算作多个遭遇或奖励。
- 固定对象层覆盖{ar.get('objects',{}).get('image_maps',0)}张地图、{ar.get('objects',{}).get('objects',0)}个大型对象，恢复由精灵拼成的建筑，并应用原生前景遮挡；非零隐藏旗标的剧情对象不混入基础场景，未解析对象来源保留在报告中。
- {atlas_stats['unavailable_maps']}张源地图的图块包或metatile描述表失效；{atlas_stats['partial_maps']}张有局部图块或调色板缺口。全部28种野生Mega所在地均有可用底图。

### 制作方案

副调色板按ROM实际加载方式读取`palettes+0xE0`，修正旧图配色偏差。图块包按地址缓存，主副组合生成一次图块图集；地图布局去重；一次批处理最多6路并行编码，攻略之间只复用图像并叠加矢量标记。区域只按连接方向和偏移拼接；楼梯和洞口作为入口跳转，冲突连接不强行拼合。

界面离线运行，不加载CDN或服务器数据；支持搜索、筛选、缩放、点位与列表联动。出入口显示目标地图ID及对应入口编号，点击精确定位；双向对应与回程不同的记录分别标注。事件按入口、条件、类型归并；不同对象、条件、地图保留，奖励指令不累加为一次收益。详见[data/atlas_event_identity_report.json](data/atlas_event_identity_report.json)。

完整设计与字段约定见[data/atlas_plan.json](data/atlas_plan.json)。生成顺序：`build_atlas_data.py` → `render_atlas.py` → `build_wild_mega_guide.py` → `integrate_guide.py` → `build_atlas_ui.py` → `build_site.py`。以上均通过`uv run`执行，地图渲染器按指纹增量复用，不逐张启动进程。

截图来源问题见[data/atlas_source_issues.json](data/atlas_source_issues.json)，建筑层明细见[data/atlas_objects_report.json](data/atlas_objects_report.json)。已交付的冰天地[第二阶段路线图](maps/routes/ice_53_6_23_to_24.png)及[前置条件与证据](data/ice_53_6_route.json)保留供查阅。
'''
(G/'README.md').write_text(readme,encoding='utf-8')
print(json.dumps({'counts':summary['counts'],'quest_statuses':dict(status),'crosslink_targets':summary['crosslink_targets']},ensure_ascii=False))
