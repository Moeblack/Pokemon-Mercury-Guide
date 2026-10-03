# /// script
# requires-python = ">=3.10"
# ///
"""Freeze atlas topology and guide locations in one pass; no image rendering here."""
from pathlib import Path
from collections import defaultdict,deque,Counter
from functools import lru_cache
import json,re,hashlib
G=Path(__file__).resolve().parents[1];R=G.parent
load=lambda p:json.loads((R/p).read_text(encoding='utf-8-sig'))
def save(p,v):(G/p).write_text(json.dumps(v,ensure_ascii=False,indent=1),encoding='utf-8')
def clean(s):
 s=re.sub(r'\\(?:ctrl|var)\[[^]]*\]','',str(s));s=re.sub(r'\\[npl]',' ',s)
 return re.sub(r'\s+',' ',s).strip()
world=load('wiki_export/world/data/maps.json');headers=load('maps_research/out/maps/headers.json')['maps']
from atlas_runtime_layouts import resolve_layouts
rom_path=R.parent/load('maps_research/out/tilesets/manifest.json')['rom']
runtime_layouts,layout_resolution=resolve_layouts(rom_path.read_bytes(),headers)
save('data/atlas_layout_resolution.json',layout_resolution)
events=load('maps_research/out/events/events.json')['maps'];maps={};points={};page_locations=defaultdict(lambda:defaultdict(set))
aliases={'3:75':'满金市·住宅区','3:76':'满金市·商业区','3:77':'满金市·酒吧所在城区','3:78':'满金市·港湾区','52:27':'宝石海星集会场景','53:14':'满金市·黑鲁加所在楼层'}
source_issues=load('player_guide/data/atlas_source_issues.json')['maps']
for m in headers:
 mid=f"{m['group']}:{m['num']}";L=runtime_layouts[mid];key=hashlib.sha1(json.dumps([L[k] for k in ['map','width','height','primary_tileset','secondary_tileset']]).encode()).hexdigest()[:16]
 maps[mid]={'id':mid,'name':aliases.get(mid,m['map_name_zh']),'raw_name':m['map_name_zh'],'width':L['width'],'height':L['height'],'layout':L,'image':f'maps/base/{key}.png','layout_key':key,'region':None,'origin':[0,0],'points':[],'warps':[],'render_status':'pending'}
 maps[mid]['layout_resolution']=layout_resolution['maps'][mid]
 if mid in source_issues:
  maps[mid]['source_issue']=source_issues[mid]
  maps[mid]['name']=source_issues[mid]['label']
def add(mid,kind,title,page,x=None,y=None,detail='',source='',suffix=''):
 if mid not in maps:return None
 m=maps[mid];numeric=isinstance(x,(int,float)) and isinstance(y,(int,float))
 geo='point' if numeric and 0<=x<m['width'] and 0<=y<m['height'] else ('unplaced' if numeric else 'area')
 raw=[mid,kind,title,page,x,y,suffix];pid=kind+'-'+hashlib.sha1(json.dumps(raw,ensure_ascii=False).encode()).hexdigest()[:14]
 if pid not in points:
  points[pid]={'id':pid,'map_id':mid,'kind':kind,'title':title,'geometry':geo,'x':x,'y':y,'detail':clean(detail),'links':[{'page':page.replace('.md','.html'),'label':'查看攻略'}] if page else [],'source':source}
  m['points'].append(pid)
 if page:page_locations[page][mid].add(pid)
 return pid
# Event identity must survive ancestry resolution; coordinates are not events.
from atlas_event_locations import EventLocations
scripts=load('maps_research/out/scripts/scripts.json')['scripts']
event_locations=EventLocations(events,scripts)
emission_stats=Counter()
old_points_path=G/'data/atlas_points.json'
old_points=json.loads(old_points_path.read_text(encoding='utf-8'))['points'] if old_points_path.exists() else []
def emit_event(row,mid,kind,title,page,detail,source):
 for loc in event_locations.resolve(row,mid):
  pid=add(mid,kind,title,page,loc.get('x'),loc.get('y'),detail,source,loc['identity'])
  if not pid:continue
  p=points[pid];emission_stats['source_location_rows']+=1
  if 'event_identity' in p:emission_stats['merged_location_rows']+=1
  p.update(event_identity=loc['identity'],event_entry=loc.get('event_entry'),event_condition=loc.get('condition'),event_records=loc.get('event_records',[]),resolution_reason=loc.get('resolution_reason'))
  if loc['geometry']=='trigger':
   valid=[t for t in loc['trigger_tiles'] if 0<=t[0]<maps[mid]['width'] and 0<=t[1]<maps[mid]['height']]
   p['outside_trigger_tiles']=[t for t in loc['trigger_tiles'] if t not in valid]
   if valid:p.update(geometry='trigger',trigger_tiles=valid,x=valid[len(valid)//2][0],y=valid[len(valid)//2][1])
  details=p.setdefault('details',[])
  if detail not in details:details.append(detail)
  record={k:row[k] for k in ('category','quantity','price','level','fields','conditions_heuristic','condition_status','hidden_item_flag_offset','parameter_role') if k in row}
  record['instruction_address']=event_locations.instruction_address(row)
  if record['instruction_address'] is None:record['unresolved_source']=row.get('source') or row.get('acquisition_id') or row.get('acquisition_ids') or row
  evidence=p.setdefault('instruction_records',[])
  if record not in evidence:evidence.append(record)
  else:emission_stats['repeated_instruction_evidence']+=1
  ref={k:row[k] for k in ('source','script','source_scripts','source_roots','acquisition_id','acquisition_ids') if k in row}
  refs=p.setdefault('source_references',[])
  if ref not in refs:refs.append(ref)
  p['detail']='；'.join(details)
  if p['geometry']=='trigger':p['detail']+=f"；同一事件的{len(p['trigger_tiles'])}格触发区域，不是人物或宝可梦站立位置"
  if len(evidence)>1:p['detail']+=f"；同一入口关联{len(evidence)}条指令，各自条件见原攻略，数量不相加"
# Items, all acquisition categories, with actual object coordinates where recorded.
for it in load('player_guide/data/items.json')['items']:
 page=f"items/{it['index']:04}.md"
 for group,rows in it['groups'].items():
  for row in rows:
   mid=row.get('map_id')
   if mid not in maps:continue
   detail=group+(f"；数量{row['quantity']}" if row.get('quantity') else '')+(f"；标价{row['price']}" if row.get('price') is not None else '')
   emit_event(row,mid,'item',it['name'],page,detail,'player_guide/data/items.json')
# Wild slots are map-level distributions, not invented point encounters.
ps={r['species_id']:r for r in load('player_guide/data/pokemon.json')['records']}
acq=load('wiki_export/world/data/acquisition_by_species.json');times={'day':'白天','morning':'清晨','evening':'黄昏','night':'夜晚'}
methods={'land':'草丛／洞内行走','surf':'水面冲浪','old_rod':'破旧钓竿','good_rod':'好钓竿','super_rod':'厉害钓竿','rock_smash_headbutt':'碎岩／撞树共用表'}
for sid,rows in acq.items():
 if int(sid) not in ps:continue
 p=ps[int(sid)];page=f'pokemon/{int(sid):04}.md';groups=defaultdict(list)
 for r in rows:
  mid=r.get('map_id')
  if mid in maps:groups[(mid,r['category'])].append(r)
 for (mid,cat),rr in groups.items():
  if cat in ['wild','broadcast','swarm']:
   modes=sorted({methods.get(r.get('method'),r.get('method') or '') for r in rr}-{''});tm=sorted({times.get(r.get('time'),r.get('time') or '') for r in rr}-{''})
   desc={'wild':'野生分布','broadcast':'广播遭遇','swarm':'群聚遭遇'}[cat]+'；'+ '、'.join(modes+tm)+'；位置为地图范围，详见物种页'
   add(mid,'pokemon',p['name'],page,detail=desc,source='wiki_export/world/data/acquisition_by_species.json',suffix=cat)
  else:
   desc={'gift':'赠送事件','egg':'赠蛋事件','static_battle_candidate':'剧情对战；捕获条件见原攻略'}.get(cat,cat)
   for r in rr:
    emit_event(r,mid,'pokemon',p['name'],page,desc,'wiki_export/world/data/acquisition_by_species.json')
# Quests: explicit start coordinates; later steps get only their recorded map extent.
for q in load('player_guide/data/quests.json')['quests']:
 page=f"quests/{q['id']:03}.md"
 for s in q['start_locations']:
  add(s.get('map_id'),'quest',q['title'],page,s.get('x'),s.get('y'),'接取：'+s.get('npc_hint','见攻略'),'data/quests/'+f"{q['id']:03}.json",'start')
 for n,step in enumerate(q['steps'],1):
  mid=step.get('map_id')
  if mid not in maps:continue
  x,y=step.get('x'),step.get('y')
  if x is None and y is None and mid in page_locations[page]:continue
  add(mid,'quest',q['title'],page,x,y,f'第{n}步：'+step['text'],'data/quests/'+f"{q['id']:03}.json",f'step{n}')
# Trainers: shared arenas are not real trainer positions. Confirmed overrides get city extent.
shared={'52:10','52:4','52:9','55:37'}
for t in load('player_guide/data/trainers.json')['trainers']:
 mids=[m for m in t['map_ids'] if m not in shared]
 if t.get('location_kind')=='override':mids=[m for m,x in maps.items() if x['raw_name']==t['location'] and m.startswith('3:')]
 for mid in mids:add(mid,'trainer',t['display_name'],t['page'],detail='训练家队伍；接战人物坐标未定位',source='player_guide/data/trainers.json')
# Newly proven Mega dispatch and runtime story override locations.
mega=load('player_guide/data/wild_mega_locations.json')['records']
for r in mega:
 groups=defaultdict(list)
 for loc in r['locations']:
  key=(loc['map_id'],r['root'],loc.get('entry'),loc.get('kind'),loc.get('variable'),loc.get('value'),loc.get('elevation'),loc.get('predicate'))
  if loc.get('kind') not in ('story_coord','coord_events'):key+= (loc.get('x'),loc.get('y'),loc.get('local_id'),loc.get('flag_id'))
  groups[key].append(loc)
 for key,locations in groups.items():
  loc=locations[0];detail=f"Lv.{r['level']}；{r['category']}"
  tiles=sorted({(v['x'],v['y']) for v in locations if v.get('x') is not None and v.get('y') is not None})
  trigger=loc.get('kind') in ('story_coord','coord_events') and bool(tiles)
  x,y=(tiles[len(tiles)//2] if trigger else (loc.get('x'),loc.get('y')))
  if trigger:detail+=f"；同一剧情的{len(tiles)}格触发区域，不是宝可梦站立位置"
  pid=add(loc['map_id'],'mega','超级'+r['name'],'pokemon/wild_mega.md',x,y,detail,'data/wild_mega_locations.json',json.dumps(key))
  if pid and trigger:
   points[pid].update(geometry='trigger',trigger_tiles=[list(t) for t in tiles],event_entry=loc.get('entry') or r['root'],trigger_condition={'variable':loc.get('variable'),'value':loc.get('value'),'elevation':loc.get('elevation'),'predicate':loc.get('predicate')},event_records=locations)
# The Starmie scene is entered through a real NPC in Olivine, not via the 40-route header label.
add('3:72','mega','超级宝石海星：集会入口','pokemon/wild_mega.md',35,50,'晚上只带一只宝石海星，与神秘人物对话进入集会。','quests/086.md','entrance')
# Read every authored guide once so map references without structured coordinates still have a card.
for section in ('quests','items','pokemon','trainers'):
 for p in (G/section).glob('*.md'):
  if not p.stem.isdigit():continue
  page=p.relative_to(G).as_posix();text=p.read_text(encoding='utf-8-sig');title=re.search(r'^#\s+(.+)',text,re.M)
  for g,n in set(re.findall(r'g(\d{2})_n(\d{3})\.(?:md|png)',text)):
   mid=f'{int(g)}:{int(n)}'
   if mid in shared and section=='trainers':continue
   if mid in maps and mid not in page_locations[page]:add(mid,{'quests':'quest','items':'item','pokemon':'pokemon','trainers':'trainer'}[section],title.group(1) if title else p.stem,page,detail='攻略中关联的地图；具体位置见正文',source=page,suffix='page_reference')
# Cardinal connection graph. Warps remain navigable portals, never spatial stitching edges.
adj=defaultdict(list);connection_edges=[]
for m in world:
 mid=m['id']
 for e in m['edges']:
  target=e['target']['map']
  if target not in maps:continue
  f=e['source_object']['fields']
  if e['type']=='connection' and f['direction'] in (1,2,3,4):
   d=f['direction'];off=f['offset_s32'];A=maps[mid];B=maps[target]
   dx,dy={1:(off,A['height']),2:(off,-B['height']),3:(-B['width'],off),4:(A['width'],off)}[d]
   adj[mid].append((target,dx,dy,e['edge_id']));adj[target].append((mid,-dx,-dy,e['edge_id']))
   connection_edges.append({'source':mid,'target':target,'direction':d,'offset':off,'edge':e['edge_id']})
  elif e['type']=='warp' and target!='0:0' and 0<=f.get('x',-1)<maps[mid]['width'] and 0<=f.get('y',-1)<maps[mid]['height']:
   label='入口 → '+maps[target]['name'];w={'target':target,'map_id':mid,'x':f['x'],'y':f['y'],'label':label,'source_warp':e['source_object']['index'],'target_warp':e['target'].get('target_warp_id')};maps[mid]['warps'].append(w)
   pid=add(mid,'warp',label,'',f['x'],f['y'],'进入 '+maps[target]['name'],'world/data/maps.json',e['edge_id']);points[pid].update(target_map=target,source_warp=w['source_warp'],target_warp=w['target_warp']);w['point_id']=pid
# Resolve actual destination warp records after every map's portals exist.
portal_index={(mid,w['source_warp']):w for mid,m in maps.items() for w in m['warps']}
display_counts=defaultdict(int)
for p in points.values():
 display_counts[p['map_id']]+=1;p['display_number']=display_counts[p['map_id']]
for mid,m in maps.items():
 for w in m['warps']:
  p=points[w['point_id']];target=portal_index.get((w['target'],w['target_warp']))
  if target:
   dest=points[target['point_id']];reciprocal=target['target']==mid and target['target_warp']==w['source_warp']
   arrow='↔' if reciprocal else '→'
   p.update(target_point=dest['id'],target_number=dest['display_number'],target_x=dest['x'],target_y=dest['y'],reciprocal=reciprocal)
   p['title']=f"{p['display_number']}号 {arrow} {maps[w['target']]['name']} [{w['target']}] {dest['display_number']}号"
   p['detail']=f"本图{p['display_number']}号（{w['x']},{w['y']}）{arrow}目标{dest['display_number']}号（{dest['x']},{dest['y']}）。"+('两端传送记录互相对应。' if reciprocal else '已定位目的入口；该入口的回程记录不是原入口，不推断可原路返回。')
   w.update(target_point=dest['id'],target_number=dest['display_number'],reciprocal=reciprocal)
  else:
   p['title']=f"{p['display_number']}号 → {maps[w['target']]['name']} [{w['target']}]"
   p['detail']=f"目标地图已知；原始目标warp索引为{w['target_warp']}，尚无有效目标点位，不能标注准确落点。"
  w['label']=p['title']
regions={};assigned=set();conflicts=[]
def overlap(x,y,w,h,a,b,c,d):return x<a+c and a<x+w and y<b+d and b<y+h
for seed in sorted(maps,key=lambda k:(not k.startswith('3:'),tuple(map(int,k.split(':'))))):
 if seed in assigned:continue
 placed={seed:(0,0)};assigned.add(seed);q=deque([seed])
 while q:
  s=q.popleft();sx,sy=placed[s]
  for t,dx,dy,eid in adj[s]:
   xy=(sx+dx,sy+dy)
   if t in placed:
    if placed[t]!=xy:conflicts.append({'edge':eid,'reason':'inconsistent_offset','source':s,'target':t})
    continue
   if t in assigned:continue
   if any(overlap(*xy,maps[t]['width'],maps[t]['height'],x,y,maps[k]['width'],maps[k]['height']) for k,(x,y) in placed.items()):conflicts.append({'edge':eid,'reason':'overlapping_rectangles','source':s,'target':t});continue
   placed[t]=xy;assigned.add(t);q.append(t)
 left=min(x for x,y in placed.values());top=min(y for x,y in placed.values());right=max(x+maps[k]['width'] for k,(x,y) in placed.items());bottom=max(y+maps[k]['height'] for k,(x,y) in placed.items())
 rid='region_'+seed.replace(':','_');name=maps[seed]['name']+('周边' if len(placed)>1 else '')
 regions[rid]={'id':rid,'name':name,'maps':list(placed),'width':right-left,'height':bottom-top,'overview':f'maps/overview/{rid}.png'}
 for mid,(x,y) in placed.items():maps[mid]['region']=rid;maps[mid]['origin']=[x-left,y-top]
pageout={p:[{'map_id':m,'point_ids':sorted(ids)} for m,ids in mm.items()] for p,mm in sorted(page_locations.items())}
manifest={'schema_version':1,'tile_px':16,'maps':maps,'regions':regions,'page_locations':pageout,'points_file':'data/atlas_points.json','connection_edges':connection_edges,'connection_conflicts':conflicts,'notes':['仅基于方向连接拼接；室内/跨层入口另行跳转。','没有精确坐标的来源展示地图范围，不虚构定位点。','满金广播塔危机Mega坐标来自已核实的运行时事件覆盖表。']}
save('data/atlas_manifest.json',manifest);save('data/atlas_points.json',{'schema_version':1,'points':list(points.values())})
identity_report={'policy':'相同地图、入口脚本、条件与事件类型归并触发格；不同对象、不同条件及不同地图分别保留；指令按ROM地址去重，来源引用保留。','before':{'points':len(old_points),'geometry':dict(Counter(p['geometry'] for p in old_points))},'after':{'points':len(points),'geometry':dict(Counter(p['geometry'] for p in points.values()))},'emissions':dict(emission_stats),'resolver':event_locations.audit(),'multi_instruction_points':[{'id':p['id'],'map_id':p['map_id'],'title':p['title'],'instruction_records':p['instruction_records'],'source_references':p['source_references']} for p in points.values() if len(p.get('instruction_records',[]))>1]}
save('data/atlas_event_identity_report.json',identity_report)
summary={'maps':len(maps),'unique_layouts':len({m['image'] for m in maps.values()}),'regions':len(regions),'stitched_regions':sum(len(r['maps'])>1 for r in regions.values()),'points':len(points),'point_types':dict(Counter(p['kind'] for p in points.values())),'geometry':dict(Counter(p['geometry'] for p in points.values())),'guide_pages_with_maps':len(pageout),'connection_conflicts':len(conflicts),'largest_regions':sorted([(r['width']*r['height'],r['id'],len(r['maps']),r['width'],r['height']) for r in regions.values()],reverse=True)[:10]}
save('data/atlas_data_summary.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2))
