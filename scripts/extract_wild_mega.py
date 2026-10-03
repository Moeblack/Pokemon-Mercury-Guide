# /// script
# requires-python = ">=3.10"
# ///
from pathlib import Path
from collections import defaultdict,deque
import json,re
G=Path(__file__).resolve().parents[1];R=G.parent
load=lambda p:json.loads((R/p).read_text(encoding='utf-8'))
scripts=load('maps_research/out/scripts/scripts.json')['scripts'];texts=load('maps_research/out/scripts/text.json')['strings']
events=load('maps_research/out/events/events.json')['maps'];maps={m['id']:m['map_name_zh'] for m in load('wiki_export/world/data/maps.json')}
names={x['index']:x['name'] for x in load('out/species.json')}
parents=defaultdict(set);children=defaultdict(set);roots=defaultdict(list)
for k,r in scripts.items():
 for i in r['instructions']:
  for a in i.get('args',[]):
   t=f"0x{a['value']:08X}"
   if a.get('class')=='script' and t in scripts:children[k].add(t);parents[t].add(k)
 for src in r.get('sources',[]):
  if src['kind']=='branch' and src['where'] in scripts:parents[k].add(src['where']);children[src['where']].add(k)
for mid,ev in events.items():
 for field in ['objects','coord_events','bg_events']:
  for e in ev.get(field,[]):
   if e.get('script') in scripts:roots[e['script']].append({'map_id':mid,'place':maps.get(mid,mid),'kind':field,'x':e.get('x'),'y':e.get('y'),'local_id':e.get('local_id'),'flag_id':e.get('flag_id')})
def chain(seeds,graph):
 out=set(seeds);q=deque(seeds)
 while q:
  k=q.popleft()
  for t in graph[k]:
   if t not in out and len(parents[t])<20:out.add(t);q.append(t)
 return out
seeds=[]
for k,r in scripts.items():
 if any(i['name']=='setflag' and i.get('args') and i['args'][0]['value']==2749 for i in r['instructions']):seeds.append(k)
result=[]
for seed in seeds:
 ancestors=chain([seed],parents);scope=chain(ancestors,children)
 blocks=[]
 for k in sorted(scope):
  ins=[]
  for i in scripts[k]['instructions']:
   vals=[a['value'] for a in i.get('args',[])];row={'at':i['addr'],'cmd':i['name'],'args':vals}
   tx=[{'address':f'0x{a:08X}','text':texts[f'0x{a:08X}']['text']} for a in vals if f'0x{a:08X}' in texts]
   if tx:row['texts']=tx
   if i['name']=='setwildbattle':row['species']=names.get(vals[0])
   ins.append(row)
  blocks.append({'script':k,'sources':scripts[k].get('sources',[]),'instructions':ins})
 result.append({'seed':seed,'roots':[{'script':k,**v} for k in sorted(ancestors) for v in roots[k]],'blocks':blocks})
out={'criterion':'setflag2749 scripts and their parsed event ancestry; Mega identity additionally requires battle/form or explicit dialogue evidence','events':result}
(G/'data/wild_mega_evidence.json').write_text(json.dumps(out,ensure_ascii=False,indent=1),encoding='utf-8')
for r in result:
 print('\nSEED',r['seed'],'ROOTS',json.dumps(r['roots'],ensure_ascii=False))
 for b in r['blocks']:
  for i in b['instructions']:
   if i['cmd']=='setwildbattle':print('BATTLE',b['script'],i['args'],i.get('species'))
   for t in i.get('texts',[]):
    if re.search('超级|失控|波动|钓|需要|瀑布',t['text']):print('TEXT',t['address'],t['text'])
