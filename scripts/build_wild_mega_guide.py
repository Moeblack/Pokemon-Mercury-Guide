# /// script
# requires-python = ">=3.10"
# ///
from pathlib import Path
import json
G=Path(__file__).resolve().parents[1]
d=json.loads((G/'data/wild_mega_locations.json').read_text(encoding='utf-8'))
a=json.loads((G/'data/atlas_manifest.json').read_text(encoding='utf-8'));p=json.loads((G/'data/atlas_points.json').read_text(encoding='utf-8'))['points']
notes={
 '大嘴娃':'连接洞内，与定点精灵互动。',
 '头巾混混':'满金商业区北侧，靠近东北方向的定点精灵。',
 '麻麻鳗鱼王':'浅葱市东侧的定点精灵。',
 '大针蜂':'桐树林北部，与定点精灵互动。',
 '水晶灯火灵':'不知名遗迹内，靠北侧的定点精灵。',
 '冰鬼护':'42号道路东段，靠北侧。',
 '阿勃梭鲁':'48号道路的定点精灵。',
 '火焰鸡':'同一挑战在45号道路与擂钵山各有地图事件记录，完成状态共用；两个位置都保留在地图中。',
 '暴雪王':'擂钵山内，与定点精灵互动。',
 '波士可多拉':'断崖通道内。',
 '巨沼怪':'破海洞穴内，靠北侧。',
 '恰雷姆':'喇叭芽之塔内。',
 '蜥蜴王':'幻影之森内。',
 '巨牙鲨':'47号道路的定点精灵。',
 '赫拉克罗斯':'自然公园内。',
 '班基拉斯':'寂静之丘内，与定点精灵互动。',
 '宝石海星':'接取《海星连接宇宙》：晚上只带一只宝石海星，到浅葱市（35,50）找神秘人物，由他带往集会；挑战在仪式过程中发生。',
 '暴鲤龙':'愤怒之湖中，与定点暴鲤龙互动；不是普通钓鱼分布。',
 '黑鲁加':'满金市的剧情楼层内，位于东北侧楼梯口；本层形状见地图。',
 '风铃铃':'铃铛塔内，位于本层北侧偏东；可从地图中的楼梯入口逐层导航。',
 '姆克鹰':'寂静之丘走到（17,14），出现失控超级进化警告后选择应对。',
 '呆壳兽':'接取《异样的呆呆兽》，在呆呆兽之井调查异常呆壳兽；委托人在（12,7），战斗对象在（20,8）。',
 '大食花':'《喇叭芽塔的妖怪》相关任务链后的大食花救援事件；桔梗市北侧，按任务《僧侣的请求》后续说明推进。',
 '勾魂眼':'城都矿山的小碎钻与勾魂眼追逐剧情，按《钻石与宝石》任务流程进入战斗。',
 '化石翼龙':'满金广播塔危机期间，在住宅区推进剧情，与蜜柑共同作战。',
 '凯罗斯':'紧接化石翼龙事件，在住宅区通道继续前进，与阿笔共同作战。',
 '长耳兔':'继续向广播塔方向推进，与阿速共同作战。',
 '胡地':'在满金港湾区通往广播塔的剧情路线上，与松叶共同作战。'
}
# Exact existing quest titles are read rather than invented from species names.
q27=json.loads((G/'data/quests/027.json').read_text(encoding='utf-8'))
q68=json.loads((G/'data/quests/068.json').read_text(encoding='utf-8'))
notes['大食花']=f"任务《{q27['title']}》中的救援战斗；目标在桔梗市北侧。先按任务页推进，再前往该位置。"
notes['勾魂眼']=f"任务《{q68['title']}》中的小碎钻与勾魂眼追逐事件；战斗在城都矿山内发生。"
qmap={'宝石海星':'086','呆壳兽':'042','大食花':'027','勾魂眼':'068'}
lines=['# 野生Mega精灵所在地','', '**已定位28种：16种定点挑战、8种剧情／特殊定点、4种满金广播塔危机剧情战。**','', '[打开可缩放地图](../maps/index.html#map=3:76) · [返回攻略首页](../index.html)','', '这里整理的是以野生战斗形式出现的超级进化事件，不是“普通形态可在哪里捕捉”的分布表。战后会将相应超级进化波动储存在超级石中；捕获记录与波动解锁不混为一项。','', '## 怎样查找','', '- 点击地点即可在正常RGB地图中定位；地图支持缩放、拖动、地点搜索和楼梯入口跳转。','- 数字坐标以地图左上角为起点。精确点位已标记；剧情过场没有固定人物坐标时，显示场景范围或实际进入该场景的人物。','- 定点精灵可能随剧情进度出现或消失；普通挑战与广播塔危机期间的剧情战分开列出。','', '## 一、定点挑战（16种）','','与图中精灵互动，出现“是否应对失控超级进化”的提示后选择挑战。','', '| 宝可梦 | 等级 | 地点与地图定位 | 寻找提示 |','|---|---:|---|---|']
def location_text(r):
 parts=[];seen=set()
 for loc in r['locations']:
  mid=loc['map_id']
  if mid in seen:continue
  seen.add(mid);name=a['maps'][mid]['name'];pid=next((x['id'] for x in p if x['kind']=='mega' and x['map_id']==mid and x['title']=='超级'+r['name']),None)
  xy=f"（{loc['x']},{loc['y']}）" if loc.get('x') is not None else ''
  if r['category']=='广播塔危机剧情':xy='（剧情触发通道）'
  link=f'../maps/index.html#map={mid}'+(f'&point={pid}' if pid else '')+'&page=pokemon/wild_mega.md'
  parts.append(f'[{name}{xy}]({link})')
 if r['name']=='宝石海星':parts.insert(0,'[浅葱市入口（35,50）](../maps/index.html#map=3:72&page=pokemon/wild_mega.md)')
 return '；'.join(parts)
for category,title in [('定点挑战',None),('剧情与特殊定点','## 二、剧情与特殊定点（8种）'),('广播塔危机剧情','## 三、满金广播塔危机（4种）')]:
 if title:
  lines+=['',title,'']
  if category=='广播塔危机剧情':lines+=['这四场只在广播塔危机的相应剧情阶段出现，不是平时在城里反复刷新的精灵。路线顺序为：**化石翼龙 → 凯罗斯 → 长耳兔 → 胡地**。','']
  lines+=['| 宝可梦 | 等级 | 地点与地图定位 | 触发方式 |','|---|---:|---|---|']
 for r in d['records']:
  if r['category']!=category:continue
  name=r['name'];note=notes[name]
  if name in qmap:note+=f" [查看任务](../quests/{qmap[name]}.md)。"
  lines.append(f"| [超级{name}]({r['species_id']:04}.md) | {r['level']} | {location_text(r)} | {note} |")
lines+=['','## 地图显示约定','','- 火焰鸡的两个位置属于同一挑战的两份地图事件记录，不计成两种精灵。','- 广播塔危机的标记是一段通道上的触发格，战斗演出中的人物会移动。','- 宝石海星集会场景的地图头写作“40号水路”，实际参加方式是从浅葱市神秘人物处进入；本页使用真实进入方式导航。','','<details><summary>数据来源</summary>','','- [完整地点与脚本证据](../data/wild_mega_locations.json)','- [统一地图与地点数据](../data/atlas_manifest.json)','- 动态脚本入口：ROM `0x0896A6C0 → 0x09D606A4`，读取变量8004后索引119项指针表 `0x09DD9E2C`。定点挑战使用编号12–27。','- 广播塔危机的坐标来自运行时地图事件覆盖表 `0x09DF9B6C`，消费者 `0x09D21C98`，不是旧静态事件表的推测。','- 额外排除了无地图入口的妙蛙种子测试样式分支、两段未定位入口的重复勾魂眼分支，以及不属于本清单Mega机制的洛奇亚形态战斗。','','</details>','']
(G/'pokemon/wild_mega.md').write_text('\n'.join(lines),encoding='utf-8')
print('野生Mega攻略：28种，完成')
