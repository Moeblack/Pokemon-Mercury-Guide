# /// script
# requires-python = ">=3.10"
# ///
from pathlib import Path
import json, struct
G=Path(__file__).resolve().parents[1];R=G.parent
rom=(R.parent/'宝可梦水银FC~致150年后的你 Version 1.1 (1).gba').read_bytes()
rows=json.loads((G/'data/quest_catalog.json').read_text(encoding='utf-8'))['rows']
scripts=json.loads((R/'maps_research/out/scripts/scripts.json').read_text(encoding='utf-8'))['scripts']
known={int(i['addr'],16) for s in scripts.values() for i in s['instructions']}
records={}
for row in rows:
    if row['title']=='宝可梦大师之路':continue
    for role in ('accept_flag','complete_flag'):
        flag=row[role];pattern=b'\x2b'+struct.pack('<H',flag)+b'\x06'
        pos=0
        while (pos:=rom.find(pattern,pos))>=0:
            a=pos+0x08000000
            target=struct.unpack_from('<I',rom,pos+5)[0] if pos+9<=len(rom) else 0
            if a not in known and rom[pos+4]<=5 and 0x08000000<=target<0x08000000+len(rom):
                # lock/faceplayer prefix is an optional exact, known event-script boundary.
                root=a-2 if rom[max(0,pos-2):pos]==b'\x69\x5a' else a
                key=f'0x{root:08X}'
                rec=records.setdefault(key,{'root':key,'check_addr':f'0x{a:08X}','flag':flag,'target':f'0x{target:08X}','raw':rom[max(0,pos-2):pos+9].hex(),'quest_ids':[],'titles':[],'basis':'exact checkflag + conditional goto + ROM target; candidate entry, not map reachability proof'})
                if row['index'] not in rec['quest_ids']:rec['quest_ids'].append(row['index']);rec['titles'].append(row['title'])
            pos+=1
out={'roots':list(records.values()),'count':len(records)}
(G/'data/quest_extra_roots.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False))
