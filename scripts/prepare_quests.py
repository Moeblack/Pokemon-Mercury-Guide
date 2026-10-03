# /// script
# requires-python = ">=3.10"
# ///
from pathlib import Path
from collections import defaultdict, deque
import json, re, struct
G=Path(__file__).resolve().parents[1]; R=G.parent
load=lambda p:json.loads((R/p).read_text(encoding='utf-8-sig'))
scripts=load('maps_research/out/scripts/scripts.json')['scripts']
texts=load('maps_research/out/scripts/text.json')['strings']
supplement=load('player_guide/data/quest_supplement/out/scripts/scripts.json')['scripts']
supplement_only=set(supplement)-set(scripts)
for key,value in supplement.items():scripts.setdefault(key,value)
for key,value in load('player_guide/data/quest_supplement/out/scripts/text.json')['strings'].items():texts.setdefault(key,value)
events=load('maps_research/out/events/events.json')['maps']
headers=load('maps_research/out/maps/headers.json')['maps']
worldmaps=load('wiki_export/world/data/maps.json')
mapnames={m['id']:m['map_name_zh'] for m in worldmaps}
species={x['index']:x['name'] for x in load('out/species.json')}
items={x['index']:x['name'] for x in load('out/items.json')}
moves={i:x['name'] for i,x in enumerate(load('out/moves.json'))}
catalog=load('player_guide/data/quest_catalog.json')['rows']
rom=(R.parent/'宝可梦水银FC~致150年后的你 Version 1.1 (1).gba').read_bytes()
charmap=load('out/charmap.json'); one={int(k,16):v for k,v in charmap.items() if len(k)==2}; two={int(k,16):v for k,v in charmap.items() if len(k)==4}
ext={1:1,2:1,3:1,4:3,5:1,6:1,7:0,8:1,9:0,10:0,11:2,12:1,13:1,14:1,15:0,16:2,17:1,18:1,19:1,20:1,21:0,22:0,23:0,24:0}
def decode(a):
    p=a-0x08000000; out=[]
    if not 0<=p<len(rom):return ''
    for _ in range(4000):
        b=rom[p];p+=1
        if b==255:return ''.join(out)
        if 1<=b<=30 and p<len(rom) and (b<<8|rom[p]) in two:out.append(two[b<<8|rom[p]]);p+=1
        elif b in (250,251,254):out.append('\n')
        elif b==252:
            c=rom[p];p+=1+ext.get(c,0)
        elif b in (253,248,249):
            c=rom[p];p+=1;out.append('[玩家/变量]' if b==253 else '')
        elif b in one:out.append(one[b])
        else:return ''
    return ''
def clean(t):
    t=re.sub(r'\\(?:ctrl|symbol|keypad)\[[^]]*\]','',t)
    t=re.sub(r'\\var\[[^]]*\]','[玩家/变量]',t)
    return re.sub(r'\\[npl]','\n',t)
def adr(a):return f'0x{a:08X}'
children=defaultdict(set);parents=defaultdict(set);roots=defaultdict(list)
for mid,emap in events.items():
    for kind,field in [('人物','objects'),('坐标事件','coord_events'),('调查点','bg_events')]:
        for e in emap.get(field,[]):
            s=e.get('script')
            if s not in scripts:continue
            roots[s].append({'map_id':mid,'place':mapnames.get(mid,mid),'kind':kind,'local_id':e.get('local_id'),'event_index':e.get('index'),'x':e.get('x'),'y':e.get('y'),'facing':e.get('kind_name') if kind=='调查点' else None,'map_page':f"../../wiki_export/world/pages/maps/g{int(mid.split(':')[0]):02}_n{int(mid.split(':')[1]):03}.md"})
for s,rec in scripts.items():
    for i in rec['instructions']:
        for a in i.get('args',[]):
            if a.get('class')=='script':
                target=adr(a['value'])
                if target in scripts:children[s].add(target);parents[target].add(s)
    for src in rec.get('sources',[]):
        if src.get('kind')=='branch' and src['where'] in scripts:
            children[src['where']].add(s);parents[s].add(src['where'])
flag_scripts=defaultdict(set)
for s,rec in scripts.items():
    for i in rec['instructions']:
        if i['name'] in ('checkflag','setflag','clearflag') and i.get('args'):
            flag_scripts[i['args'][0]['value']].add(s)
# Shared flag inventory carries only identity; it is not a prerequisite graph.
all_flags=defaultdict(list)
for row in catalog:
    for fld in ('accept_flag','complete_flag'):all_flags[row[fld]].append({'title':row['title'],'role':fld})

def gather(row):
    seeds=flag_scripts[row['accept_flag']]|flag_scripts[row['complete_flag']]
    # Fixed supplement anchors belonging to this row are first-class seeds, so they enter the
    # packet body without being presented as map objects or reachability proof.
    anchor_tag=f"{row['index']:03d}"
    seeds=seeds|{s for s,rec in scripts.items()
                 if any(x.get('kind')=='quest_catalog_flag_anchor' and x.get('where')==anchor_tag
                        for x in rec.get('sources',[]))}
    ancestors=set(seeds);q=deque(seeds)
    while q:
        s=q.popleft()
        for p in parents[s]:
            if p not in ancestors:ancestors.add(p);q.append(p)
    # Only use event roots reached from these specific flag checks, not unrelated same-map NPCs.
    eventroots={s for s in ancestors if roots.get(s)}
    closure=set(seeds)|eventroots;q=deque(closure); skipped=set()
    while q:
        s=q.popleft()
        for t in children[s]:
            if len(parents[t])>30 and t not in seeds:
                skipped.add(t);continue
            if t not in closure:closure.add(t);q.append(t)
    out=[]
    for s in sorted(closure):
        seq=[]
        for i in scripts[s]['instructions']:
            vals=[a['value'] for a in i.get('args',[])]
            cmd={'at':i['addr'],'command':i['name'],'args':vals}
            if i['name'] in ('goto','call','goto_if','call_if'):cmd['targets']=[adr(a['value']) for a in i['args'] if a.get('class')=='script']
            tx=[]
            for a in i.get('args',[]):
                key=adr(a['value']) if a['width']==4 else ''
                if key in texts:tx.append({'address':key,'text':clean(texts[key]['text'])})
                elif i['name'] in ('loadpointer','preparemsg') and a['width']==4 and 0x08000000<=a['value']<0x0A000000:
                    t=decode(a['value'])
                    if t:tx.append({'address':key,'text':t})
            if tx:cmd['texts']=tx
            if i['name'] in ('checkflag','setflag','clearflag') and vals and vals[0] in all_flags:cmd['task_flag_labels']=all_flags[vals[0]]
            if i['name'] in ('givepokemon','giveegg','setwildbattle') and vals:cmd['species_name']=species.get(vals[0])
            if i['name'] in ('additem','checkitem','removeitem') and vals:cmd['item_name']=items.get(vals[0])
            # Specific known variable argument namespaces remain explicit rather than guessed.
            if i['name'] in ('setvar','setorcopyvar','comparevartovalue') and len(vals)>1:
                cmd['possible_names_not_semantics']={'species':species.get(vals[1]),'item':items.get(vals[1]),'move':moves.get(vals[1])}
            seq.append(cmd)
        out.append({'script':s,'event_roots':roots.get(s,[]),'instructions':seq,'source_kind':'supplemental_branch_candidate' if s in supplement_only else 'production_script','sources':scripts[s].get('sources',[]),'decode_stop':scripts[s].get('stop')})
    merged=dict(row)
    merged['current_description']=decode(int(row['description_address'],16))
    merged['description']=clean(row['description'])
    mid=f"{row['map_group']}:{row['map_num']}"
    merged['catalog_map']=None if mid=='0:0' else {'id':mid,'name':mapnames.get(mid,mid)}
    return {'quest':merged,'direct_flag_scripts':sorted(seeds),'event_roots':[{'script':s,**x} for s in sorted(eventroots) for x in roots[s]],'scripts':out,'shared_helpers_not_expanded':sorted(skipped),'source_files':['player_guide/data/quest_catalog.json','maps_research/out/scripts/scripts.json','maps_research/out/scripts/text.json','maps_research/out/events/events.json']}

def main():
    outdir=G/'data/quest_packets_expanded';outdir.mkdir(parents=True,exist_ok=True)
    summaries=[]
    groups=defaultdict(list)
    for row in catalog:groups[row['title']].append(row)
    for n,(title,rows) in enumerate(groups.items()):
        if title=='宝可梦大师之路':continue
        qid=min(r['index'] for r in rows)
        packet={'title':title,'quest_id':qid,'records':[gather(r) for r in rows]}
        p=outdir/f'{qid:03}.json';p.write_text(json.dumps(packet,ensure_ascii=False,indent=1),encoding='utf-8')
        summaries.append({'id':qid,'title':title,'file':p.relative_to(G).as_posix(),'catalog_rows':[r['index'] for r in rows],'script_count':sum(len(x['scripts']) for x in packet['records']),'root_count':sum(len(x['event_roots']) for x in packet['records']),'bytes':p.stat().st_size})
    (G/'data/quest_manifest_expanded.json').write_text(json.dumps({'quest_count':len(summaries),'quests':summaries,'excluded_main_story_rows':[r for r in catalog if r['title']=='宝可梦大师之路'],'supplement_source':'data/quest_supplement','candidate_boundary':'Supplemental flag branches do not establish map reachability; production event roots are unchanged.'},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summaries,ensure_ascii=False))
if __name__=='__main__':main()
