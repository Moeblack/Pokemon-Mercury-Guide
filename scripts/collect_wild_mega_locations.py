# /// script
# requires-python = ">=3.10"
# ///
from pathlib import Path
from collections import defaultdict,deque
import json,struct
G=Path(__file__).resolve().parents[1];R=G.parent
load=lambda p:json.loads((R/p).read_text(encoding='utf-8'))
rom=(R.parent/'宝可梦水银FC~致150年后的你 Version 1.1 (1).gba').read_bytes()
u32=lambda a:struct.unpack_from('<I',rom,a-0x08000000)[0]
scripts=load('maps_research/out/scripts/scripts.json')['scripts'];texts=load('maps_research/out/scripts/text.json')['strings']
for k,v in load('player_guide/data/mega_supplement/out/scripts/scripts.json')['scripts'].items():scripts.setdefault(k,v)
for k,v in load('player_guide/data/mega_supplement/out/scripts/text.json')['strings'].items():texts.setdefault(k,v)
events=load('maps_research/out/events/events.json')['maps'];maps={m['id']:m for m in load('wiki_export/world/data/maps.json')};names={x['index']:x['name'] for x in load('out/species.json')}
parents=defaultdict(set);children=defaultdict(set);locations=defaultdict(list);dispatch=[]
def adr(a):return f'0x{a:08X}'
for k,r in scripts.items():
 for i in r['instructions']:
  for a in i.get('args',[]):
   t=adr(a['value'])
   if a.get('class')=='script' and t in scripts:children[k].add(t);parents[t].add(k)
 for src in r.get('sources',[]):
  if src['kind']=='branch' and src['where'] in scripts:children[src['where']].add(k);parents[k].add(src['where'])
 index=None
 for i in r['instructions']:
  v=[a['value'] for a in i.get('args',[])]
  if i['name']=='setvar' and v[0]==0x8004:index=v[1]
  if i['name']=='callasm' and v==[0x0896A6C1] and index is not None and index<=118:
   target=adr(u32(0x09DD9E2C+index*4));dispatch.append({'wrapper':k,'index':index,'target':target})
   if target in scripts:children[k].add(target);parents[target].add(k)
for mid,ev in events.items():
 for field in ('objects','coord_events','bg_events'):
  for e in ev.get(field,[]):
   if e.get('script') in scripts:
    locations[e['script']].append({'map_id':mid,'place':maps[mid]['map_name_zh'],'kind':field,'x':e.get('x'),'y':e.get('y'),'local_id':e.get('local_id'),'flag_id':e.get('flag_id'),'source':'static_map_event','variable':e.get('trigger'),'value':e.get('index_var'),'elevation':e.get('elevation'),'event_address':e.get('addr')})
for k,r in scripts.items():
 for src in r.get('sources',[]):
  if src['kind']=='map_script_table' and src['where'] in maps:
   mid=src['where'];locations[k].append({'map_id':mid,'place':maps[mid]['map_name_zh'],'kind':'map_script','x':None,'y':None,'source':'map_script_table'})
# ROM consumer 09D21C98 selects 16-byte rows by current map group+number,
# invokes row+4 predicate and installs row+8 event header into gMapHeader+4.
overrides=[];a=0x09DF9B6C
while rom[a-0x08000000]!=255:
 p=a-0x08000000;group,num=rom[p:p+2];pred,header,ms=struct.unpack_from('<III',rom,p+4)
 overrides.append({'row':adr(a),'map_id':f'{group}:{num}','predicate':adr(pred),'events':adr(header),'map_scripts':adr(ms)})
 if header in (0x09DFC9C4,0x09DFC0C4):
  o=header-0x08000000;n=rom[o+2];coords=u32(header+12)
  for j in range(n):
   pos=coords+j*16;z=pos-0x08000000;x,y=struct.unpack_from('<HH',rom,z);var,val=struct.unpack_from('<HH',rom,z+6);target=adr(u32(pos+12));mid=f'{group}:{num}'
   if target in scripts:locations[target].append({'map_id':mid,'place':maps[mid]['map_name_zh'],'kind':'story_coord','x':x,'y':y,'variable':var,'value':val,'elevation':rom[z+4],'source':'runtime_event_override','row':adr(a),'predicate':adr(pred),'event_address':adr(pos)})
 a+=16
 if a>=0x09DFA000:raise RuntimeError('override table boundary missing')
def closure(start,graph):
 out={start};q=deque([start])
 while q:
  s=q.popleft()
  for t in graph[s]:
   if t not in out and len(parents[t])<20:out.add(t);q.append(t)
 return out
selected=[(adr(u32(0x09DD9E2C+i*4)),'定点挑战') for i in range(12,28)]
selected += [(k,'剧情与特殊定点') for k in ['0x087B3A28','0x087B5827','0x087BCCF0','0x087BD272','0x08ED523D','0x08EDE95F','0x08EECE52','0x09CE056B']]
selected += [(k,'广播塔危机剧情') for k in ['0x09CDCA89','0x09CDCD1D','0x09CDCF65','0x09CDD7BC']]
records=[]
for root,category in selected:
 scope=closure(root,children);anc=closure(root,parents);battles=[];tx=[];flags=[]
 for k in sorted(scope):
  for i in scripts[k]['instructions']:
   vals=[a['value'] for a in i.get('args',[])]
   if i['name']=='setwildbattle':battles.append({'at':i['addr'],'species_id':vals[0],'name':names[vals[0]],'level':vals[1],'item':vals[2]})
   if i['name'] in ('setflag','checkflag'):flags.append({'at':i['addr'],'command':i['name'],'value':vals[0]})
   for v in vals:
    if adr(v) in texts:tx.append({'address':adr(v),'text':texts[adr(v)]['text']})
 locs=[dict(v,entry=k) for k in sorted(anc) for v in locations[k]]
 locs=list({json.dumps(x,sort_keys=True):x for x in locs}.values())
 battles=list({v['at']:v for v in battles}.values())
 tx=list({v['address']:v for v in tx}.values())
 flags=list({(v['at'],v['command'],v['value']):v for v in flags}.values())
 if not battles:raise RuntimeError('no battle '+root)
 records.append({'root':root,'category':category,'name':battles[0]['name'],'species_id':battles[0]['species_id'],'level':battles[0]['level'],'locations':locs,'battles':battles,'scripts':sorted(scope),'texts':tx,'flags':flags})
out={'records':records,'dispatch_evidence':{'wrapper':'0x0896A6C0 loads [0x0896A6B0]=0x09D606A4','consumer':'0x09D606A4–0x09D606E0 reads Var8004, range<=118, indexes 0x09DD9E2C, calls ScriptContext1_SetupScript','bindings':dispatch},'runtime_event_evidence':{'consumer':'0x09D21C98–0x09D21CDC','rows':overrides},'excluded':[{'root':'0x08ED5252','reason':'妙蛙种子45级测试样式分支，未定位地图入口且无Mega进化边，不计为野生Mega地点'},{'roots':['0x087B4136','0x087B44DF'],'reason':'勾魂眼28级的另外两段分支，未定位当前地图入口，不另外添加地点'},{'root':'0x087BD9C5','reason':'洛奇亚特殊形态战斗只有共用战斗旗标，不具有本清单的Mega开关及超级进化对白'}]}
(G/'data/wild_mega_locations.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
for r in records:print(r['name'],r['level'],r['root'],json.dumps(r['locations'],ensure_ascii=False))
