"""Export existing Mercury world evidence to wiki data/pages; no ROM/game/media work."""
from __future__ import annotations
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
from collections import defaultdict, deque, Counter

ROOT = Path(__file__).resolve().parents[2]
WIKI = ROOT / 'wiki_export'
OUT = WIKI / 'world'
SOURCES = {}
GENERATED = []
LINKS = set()

def load(path):
    p = ROOT / path
    raw = p.read_bytes()
    SOURCES[path] = hashlib.sha256(raw).hexdigest()
    if p.suffix == '.jsonl':
        return [json.loads(line) for line in raw.decode('utf-8-sig').splitlines() if line.strip()]
    return json.loads(raw.decode('utf-8-sig'))

def save(path, value):
    p = OUT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    GENERATED.append(p)

def csvsave(path, rows):
    if not rows:
        save(path, '')
        return
    fields = list(dict.fromkeys(k for r in rows for k in r))
    f = io.StringIO(newline='')
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    for r in rows:
        writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k, v in r.items()})
    save(path, f.getvalue())

def adr(value):
    return f'0x{int(value, 16) if isinstance(value, str) else value:08X}'

def hexname(value):
    return adr(value)[2:]

def mapid(g, n):
    return f'{g}:{n}'

def mapkey(mid):
    g, n = map(int, mid.split(':'))
    return f'g{g:02}_n{n:03}'

def mpage(mid):
    return f'world/pages/maps/{mapkey(mid)}.md'

def tpage(a):
    return f'world/pages/texts/{hexname(a)}.md'

def j(v):
    return json.dumps(v, ensure_ascii=False, separators=(',', ':'))

def esc(v):
    return str(v).replace('|', '\\|').replace('\n', '<br>')

def link(page, target, label):
    LINKS.add(target.split('#')[0])
    rel = os.path.relpath(WIKI / target.split('#')[0], (WIKI / page).parent).replace('\\', '/')
    if '#' in target:
        rel += '#' + target.split('#', 1)[1]
    return f'[{esc(label)}]({rel})'

def source(path, pointer):
    return {'path': path, 'json_pointer': pointer, 'file_sha256': SOURCES.get(path)}

def source_line(s):
    return f"来源：`{s['path']}`，JSON pointer `{s['json_pointer']}`。"

def table(headers, rows):
    return ['| ' + ' | '.join(headers) + ' |', '|' + '|'.join(['---'] * len(headers)) + '|'] + ['| ' + ' | '.join(esc(v) for v in r) + ' |' for r in rows]

def corelink(page, category, ident, label=None):
    if ident is None:
        return '原记录未提供（null）'
    if category == 'items' and ident == 0:
        return '无 (0)'
    target = f'core/pages/{category}/{ident:04}.md'
    return link(page, target, label if label is not None else ident) if (WIKI / target).is_file() else f'{label or ident} ({ident}; 核心页未提供)'

HP = 'maps_research/out/maps/headers.json'
EP = 'maps_research/out/events/events.json'
SP = 'maps_research/out/scripts/scripts.json'
TP = 'maps_research/out/scripts/text.json'
TRP = 'trainers_research/out/trainers.json'
UP = 'trainers_research/out/trainer_usage.json'
ENP = 'encounters_research/out/encounters.json'
SHOPP = 'encounters_research/out/shops.json'
NP = 'parallel_acceleration/map_relations/nodes.json'
EDP = 'parallel_acceleration/map_relations/edges.jsonl'
VP = 'parallel_acceleration/map_relations/var_flag_index.jsonl'
RGP = 'maps_research/out/maps/mapsec_names.json'


def main():
    headers = load(HP)['maps']
    event_maps = load(EP)['maps']
    scripts = load(SP)['scripts']
    texts = load(TP)['strings']
    trainers = load(TRP)['trainers']
    usage = load(UP)
    encounters = load(ENP)
    shop_src = load(SHOPP)
    nodes = load(NP)['nodes']
    edges = load(EDP)
    vf = load(VP)
    region_src = load(RGP)
    render = load('maps_research/out/maps/render_report.json')
    standard = load('maps_research/out/scripts/std_and_special.json')
    assets = load('wiki_export/assets/index.json')['records']
    music = load('wiki_export/assets/music.json')
    music_by_id = defaultdict(list)
    for mi, track in enumerate(music['tracks']):
        music_by_id[track['index']].append({**track, 'source': source('wiki_export/assets/music.json', f'/tracks/{mi}')})
    inventory = load('wiki_export/world/source_inventory.json')
    items = {v['index']: v for v in load('out/items.json')}
    species = {v['index']: v for v in load('out/species.json')}
    macro_path = 'reference/cfru/xse_commands.s'
    macro_text = (ROOT / macro_path).read_text(encoding='utf-8')
    SOURCES[macro_path] = hashlib.sha256((ROOT / macro_path).read_bytes()).hexdigest()
    # Widths are checked against these exact, bounded reference macros AND each decoded occurrence.
    widths = {}
    macro_fields = {'givepokemon': ['species_id', 'level', 'held_item_index', 'unknown1', 'unknown2', 'unknown3'], 'giveegg': ['species_id'], 'setwildbattle': ['species_id', 'level', 'held_item_index'], 'additem': ['item_index', 'quantity']}
    for name in macro_fields:
        block = re.search(r'^\.macro ' + name + r'\b.*?^\.endm', macro_text, re.M | re.S).group(0)
        directives = re.findall(r'^\s*\.(byte|hword|2byte|word|4byte)\s+', block, re.M)
        widths[name] = [{'byte': 1, 'hword': 2, '2byte': 2, 'word': 4, '4byte': 4}[x] for x in directives[1:]]
    assert widths == {'givepokemon': [2, 1, 2, 4, 4, 1], 'giveegg': [2], 'setwildbattle': [2, 1, 2], 'additem': [2, 2]}
    map_by_id = {mapid(h['group'], h['num']): h for h in headers}
    node_by_id = {n['id']: n for n in nodes}
    def mapname(mid):
        return map_by_id[mid]['map_name_zh'] if mid in map_by_id else None
    assets_by_key = {r['render_name']: r for r in assets if r.get('category') == 'map' and r.get('render_name')}
    edge_by_map = defaultdict(list)
    for i, edge in enumerate(edges):
        edge_by_map[edge['source']['map']].append({**edge, 'source_ref': source(EDP, f'/{i}')})

    # Existing branch provenance is an explicit directed graph. Fixed point preserves shared roots/cycles.
    children = defaultdict(set)
    roots = {a: set() for a in scripts}
    root_sources = {}
    untrusted_roots = {a for a, s in scripts.items() if s.get('runtime_stop')} | {'0x08990B94'}
    taint = {a: ({a} if a in untrusted_roots else set()) for a in scripts}
    unresolved_parents = []
    for a, s in scripts.items():
        for z in s['sources']:
            if z['kind'] == 'branch':
                parent = z['where']
                if parent in scripts:
                    children[parent].add(a)
                else:
                    unresolved_parents.append({'script': a, 'parent': parent})
            else:
                rid = z['kind'] + ':' + z['where']
                roots[a].add(rid)
                root_sources[rid] = z
    queue = deque(scripts)
    queued = set(scripts)
    while queue:
        parent = queue.popleft()
        queued.discard(parent)
        for child in children[parent]:
            before = (len(roots[child]), len(taint[child]))
            roots[child].update(roots[parent])
            taint[child].update(taint[parent])
            if before != (len(roots[child]), len(taint[child])) and child not in queued:
                queue.append(child)
                queued.add(child)
    root_map = {}
    for rid, z in root_sources.items():
        match = re.match(r'^(\d+:\d+)(?:/|$)', z['where'])
        if match and match.group(1) in map_by_id:
            root_map[rid] = match.group(1)
    script_maps = {a: sorted({root_map[r] for r in rr if r in root_map}) for a, rr in roots.items()}
    scripts_by_map = defaultdict(list)
    scripts_by_root = defaultdict(list)
    for a in scripts:
        for mid in script_maps[a]: scripts_by_map[mid].append(a)
        for rid in roots[a]: scripts_by_root[rid].append(a)
    text_by_script = defaultdict(set)
    text_refs = defaultdict(list)
    text_join_unresolved = []
    for a, s in scripts.items():
        for i in s['instructions']:
            for arg in i.get('args', []):
                if arg.get('class') == 'text':
                    dest = adr(arg['value'])
                    if dest in texts:
                        text_by_script[a].add(dest)
                        text_refs[dest].append({'script': a, 'instruction_addr': i['addr'], 'argument_addr': arg['addr'], 'cmd': i['name'], 'maps': script_maps[a]})
                    else: text_join_unresolved.append({'script': a, 'argument': arg, 'reason': 'text pointer absent from strings'})
    # Retain reverse-only references, checking at against parameter addr, never assuming instruction addr.
    for a, tx in texts.items():
        for ref in tx['referenced_by']:
            if ref['script'] in scripts:
                text_by_script[ref['script']].add(a)
                if not any(r['script'] == ref['script'] and r['argument_addr'] == ref['at'] for r in text_refs[a]):
                    matches = [i['addr'] for i in scripts[ref['script']]['instructions'] for arg in i.get('args', []) if arg.get('addr') == ref['at']]
                    text_refs[a].append({'script': ref['script'], 'instruction_addr': matches[0] if len(matches) == 1 else None, 'argument_addr': ref['at'], 'cmd': ref['cmd'], 'maps': script_maps[ref['script']], 'reverse_reference': True})
    text_rows = []
    for a, tx in texts.items():
        mids = sorted({m for r in text_refs[a] for m in r['maps']})
        text_rows.append({**tx, 'map_ids': mids, 'joined_references': text_refs[a], 'page_path': tpage(a), 'source': source(TP, '/strings/' + a)})
    save('data/texts.json', text_rows)
    csvsave('data/texts.csv', text_rows)

    vf_by_script = defaultdict(list)
    for v in vf:
        for a in v['source_scripts']: vf_by_script[a].append(v)
    flow_ops = {'call', 'goto', 'goto_if', 'call_if', 'callstd', 'gotostd', 'gotostd_if', 'callstd_if', 'special', 'specialvar', 'compare', 'comparevars', 'comparelocaltovalue', 'checkflag', 'setflag', 'clearflag', 'setvar', 'copyvar', 'setorcopyvar', 'addvar', 'subvar'}
    script_index = {}
    for a, s in scripts.items():
        script_index[a] = {'addr': a, 'sources': s['sources'], 'source_roots': sorted(roots[a]), 'map_ids': script_maps[a], 'source_untrusted': sorted(taint[a]), 'text_addresses': sorted(text_by_script[a]), 'calls_conditions_and_state': [i for i in s['instructions'] if i.get('name') in flow_ops or any(x in str(i.get('name')) for x in ('compare', 'checkflag', 'goto', 'call'))], 'variable_flag_references': vf_by_script[a], 'source': source(SP, '/scripts/' + a)}
    story_events = []
    for mid, em in event_maps.items():
        for field, kind in [('objects', 'object'), ('coord_events', 'coord'), ('bg_events', 'bg')]:
            for pos, event in enumerate(em[field]):
                sa = event.get('script')
                if not sa: continue
                direct = [rid for rid in roots.get(sa, []) if root_map.get(rid) == mid and root_sources[rid]['kind'] == kind]
                # Use the actual direct sources of this root; avoid inherited unrelated NPC roots.
                direct = [rid for rid in direct if root_sources[rid] in scripts.get(sa, {}).get('sources', [])]
                if kind == 'object': direct = [rid for rid in direct if root_sources[rid]['where'] == f"{mid}/local{event['local_id']}"]
                reach = sorted({a for rid in direct for a in scripts_by_root[rid]} | ({sa} if sa in scripts else set()))
                story_events.append({'event_id': f'{mid}:{kind}:{event["index"]}', 'map_id': mid, 'kind': kind, 'index': event['index'], 'local_id': event.get('local_id'), 'event': event, 'root_script': sa, 'source_roots': direct, 'script_addresses': reach, 'text_addresses': sorted({t for a in reach for t in text_by_script[a]}), 'source_untrusted': sorted({u for a in reach for u in taint[a]}), 'source': source(EP, f'/maps/{mid}/{field}/{pos}'), 'page_path': mpage(mid)})
    for rid, z in root_sources.items():
        if z['kind'] in ('map_script', 'map_script_table') and rid in root_map:
            mid = root_map[rid]
            aa = sorted(scripts_by_root[rid])
            story_events.append({'event_id': rid, 'map_id': mid, 'kind': z['kind'], 'local_id': None, 'source_roots': [rid], 'script_addresses': aa, 'text_addresses': sorted({t for a in aa for t in text_by_script[a]}), 'source_untrusted': sorted({u for a in aa for u in taint[a]}), 'source': source(SP, '/scripts/' + aa[0] + '/sources'), 'page_path': mpage(mid)})
    story_by_map = defaultdict(list)
    for row in story_events: story_by_map[row['map_id']].append(row)
    save('data/story_events.json', {'events': story_events, 'script_index': script_index, 'unmapped_scripts': [a for a in scripts if not script_maps[a]], 'unmapped_texts': [r['addr'] for r in text_rows if not r['map_ids']], 'unresolved_branch_parents': unresolved_parents, 'unresolved_text_joins': text_join_unresolved, 'note': '按事件及指令证据组织，不是线性通关流程；归图不证明可达。'})
    csvsave('data/story_events.csv', story_events)

    by_species = defaultdict(list)
    by_item = defaultdict(list)
    def add_index(dest, ident, record):
        if ident is not None and ident != 0:
            dest[str(ident)].append(record)
    def backlink(category, aid, mid, page, src, **values):
        r = {'category': category, 'acquisition_id': aid, 'map_id': mid, 'map_name': mapname(mid), 'time': None, 'method': None, 'level': None, 'weight': None, 'encounter_rate': None, 'conditional_slot_weight': None, 'script': None, 'condition_status': 'existing_static_evidence_not_reachability', 'source': src, 'page_path': page, 'null_reason': '字段不适用于此类别或现成证据未给出；null不是零概率。'}
        r.update(values)
        return r
    wild = []
    broadcast = []
    swarms = []
    encounter_by_map = defaultdict(list)
    for time, tt in encounters['tables'].items():
        for ei, entry in enumerate(tt['entries']):
            mid = mapid(entry['map_group'], entry['map_num'])
            for method in ('land', 'water', 'rock_smash_headbutt', 'fishing'):
                info = entry.get(method)
                if not info: continue
                for si, slot in enumerate(info['slots']):
                    display_method = method
                    if method == 'fishing':
                        display_method = next(rod for rod in ('old_rod', 'good_rod', 'super_rod') if slot['slot'] in encounters['probabilities']['fishing'][rod]['slots'])
                        prob = encounters['probabilities']['fishing'][display_method]
                        weight = prob['weights'][prob['slots'].index(slot['slot'])]
                    else: weight = encounters['probabilities'][method]['weights'][slot['slot']]
                    src = source(ENP, f'/tables/{time}/entries/{ei}/{method}/slots/{si}')
                    row = {**slot, 'acquisition_id': f'wild:{time}:{mid}:{method}:{slot["slot"]}', 'map_id': mid, 'map_name': mapname(mid), 'time': time, 'hour_band': tt['hour_band'], 'time_band_zh': tt['time_band_zh'], 'method': display_method, 'raw_method': method, 'encounter_rate': info['rate'], 'conditional_slot_weight': weight, 'probability_note': '方法/钓竿内选槽权重，不是总体出现或捕获概率。', 'info_addr': info['info_addr'], 'wild_addr': info['wild_addr'], 'source': src, 'page_path': mpage(mid)}
                    wild.append(row)
                    encounter_by_map[mid].append(row)
                    add_index(by_species, slot['species_id'], backlink('wild', row['acquisition_id'], mid, mpage(mid), src, time=time, method=display_method, level={'min': slot['min_level'], 'max': slot['max_level']}, weight=weight, encounter_rate=info['rate'], conditional_slot_weight=weight))
    for bi, entry in enumerate(encounters['broadcast']['entries']):
        mid = mapid(entry['map_group'], entry['map_num'])
        for seti, ss in enumerate(entry['sets']):
            for si, slot in enumerate(ss['species']):
                src = source(ENP, f'/broadcast/entries/{bi}/sets/{seti}/species/{si}')
                aid = f'broadcast:{entry["index"]}:{ss["day_of_week"]}:{slot["slot"]}'
                row = {**slot, 'acquisition_id': aid, 'map_id': mid, 'map_name': mapname(mid), 'day_of_week': ss['day_of_week'], 'day_name': ss['day_name'], 'region_label_reference': ss['wiki_region'], 'conditional_slot_weight': slot['weight_percent'], 'source': src, 'page_path': mpage(mid), 'gating_ref': '/broadcast_metadata/gating'}
                broadcast.append(row)
                add_index(by_species, slot['species_id'], backlink('broadcast', aid, mid, mpage(mid), src, method='broadcast', weight=slot['weight_percent'], conditional_slot_weight=slot['weight_percent'], day_of_week=ss['day_of_week'], condition_status='broadcast_gating_required_internal_slot_weight_only'))
    maps_by_section = defaultdict(list)
    for mid, h in map_by_id.items(): maps_by_section[h['region_map_section_id']].append(mid)
    for si, entry in enumerate(encounters['swarm']['entries']):
        mids = sorted(maps_by_section[entry['mapsec_id']])
        src = source(ENP, f'/swarm/entries/{si}')
        row = {**entry, 'acquisition_id': f'swarm:{hexname(entry["addr"])}', 'map_ids': mids, 'source': src}
        swarms.append(row)
        for mid in mids or [None]:
            add_index(by_species, entry['species_id'], backlink('swarm', row['acquisition_id'] + ':' + str(mid), mid, mpage(mid) if mid else 'world/pages/mechanics/swarm.md', src, method='swarm', mapsec_id=entry['mapsec_id'], condition_status='swarm_activation_not_proven_by_static_table'))
    fallback_rows = []
    for group, f in encounters['broadcast']['fallback_tables'].items():
        for si, s in enumerate(f['species']):
            row = backlink('broadcast', f'broadcast:fallback:{group}:{si}', None, 'world/pages/mechanics/broadcast.md', source(ENP, f'/broadcast/fallback_tables/{group}/species/{si}'), method='broadcast_fallback', weight=encounters['broadcast']['slot_weights_percent'][si], conditional_slot_weight=encounters['broadcast']['slot_weights_percent'][si], condition_status='fallback_selection_and_broadcast_gates_required', fallback_group=group)
            fallback_rows.append({**row, **s})
            add_index(by_species, s['species_id'], row)
    save('data/encounters.json', {'wild_slots': wild, 'broadcast_slots': broadcast, 'swarm': swarms, 'broadcast_fallback_slots': fallback_rows, 'broadcast_metadata': {k: v for k, v in encounters['broadcast'].items() if k != 'entries'}, 'swarm_metadata': {k: v for k, v in encounters['swarm'].items() if k != 'entries'}, 'probabilities': encounters['probabilities'], 'time_tables_metadata': {k: {a: b for a, b in v.items() if a != 'entries'} for k, v in encounters['tables'].items()}, 'unresolved': encounters.get('unresolved', [])})
    csvsave('data/encounters.csv', wild)
    csvsave('data/broadcast.csv', broadcast)
    csvsave('data/swarm.csv', swarms)

    hidden = []
    for mid, em in event_maps.items():
        for pos, e in enumerate(em['bg_events']):
            if e.get('kind') != 7: continue
            iid = e['hidden_item_id']
            src = source(EP, f'/maps/{mid}/bg_events/{pos}')
            row = {**e, 'item_index': iid, 'item_name': items.get(iid, {}).get('name'), 'map_id': mid, 'map_name': mapname(mid), 'acquisition_id': f'hidden:{mid}:{e["index"]}', 'source': src, 'page_path': mpage(mid)}
            hidden.append(row)
            add_index(by_item, iid, backlink('hidden_item', row['acquisition_id'], mid, mpage(mid), src, quantity=e['quantity'], x=e['x'], y=e['y'], hidden_item_flag_offset=e['hidden_item_flag_offset'], underfoot=e['underfoot']))
    save('data/hidden_items.json', hidden)
    csvsave('data/hidden_items.csv', hidden)

    shop_rows = []
    shops_by_map = defaultdict(list)
    for si, s in enumerate(shop_src['shops']):
        pp = f'world/pages/shops/{hexname(s["instr_addr"])}.md'
        src = source(SHOPP, f'/shops/{si}')
        row = {**s, 'source': src, 'page_path': pp}
        shop_rows.append(row)
        for m in s['maps']:
            mid = mapid(m['group'], m['num'])
            shops_by_map[mid].append(row)
            for ii, item in enumerate(s['items']):
                add_index(by_item, item['index'], backlink('shop', f'shop:{hexname(s["instr_addr"])}:{ii}:{mid}', mid, pp, source(SHOPP, f'/shops/{si}/items/{ii}'), script=s['script_addr'], price=item['price'], currency_semantics='core_item_table_price; no_dynamic_price_or_unlock_claim', conditions_heuristic=s['conditions_heuristic'], condition_status='heuristic_conditions_not_unlock_proof'))
    save('data/shops.json', {'shops': shop_rows, 'rejected_invalid_pointer': shop_src['rejected_invalid_pointer'], 'note': shop_src['note']})
    csvsave('data/shops.csv', [{**{k: v for k, v in s.items() if k != 'items'}, 'stock_position': ii, **item} for s in shop_rows for ii, item in enumerate(s['items'])])

    def value_field(arg, allow_variable=True):
        val = arg['value']
        if allow_variable and arg['width'] == 2 and val >= 0x4000:
            return {'kind': 'variable_ref', 'value': val, 'variable_ref': f'0x{val:04X}', 'reason': 'variable-capable u16 operand; not looked up as species/item ID'}
        return {'kind': 'literal', 'value': val}
    acquisitions = {}
    std_candidates = {}
    barriers = {'call', 'goto', 'goto_if', 'call_if', 'callstd', 'gotostd', 'callstd_if', 'gotostd_if', 'special', 'specialvar', 'return', 'end', 'setwildbattle', 'vgoto', 'vcall', 'vgoto_if', 'vcall_if'}
    def merge_acq(store, key, base, a, occurrence):
        if key not in store: store[key] = {**base, 'source_scripts': [], 'source_roots': [], 'map_ids': [], 'source_untrusted': [], 'occurrences': []}
        row = store[key]
        if row.get('raw_args') != base.get('raw_args'): row.setdefault('unresolved', []).append('same-address conflicting decoded arguments')
        row['source_scripts'] = sorted(set(row['source_scripts']) | {a})
        row['source_roots'] = sorted(set(row['source_roots']) | roots[a])
        row['map_ids'] = sorted(set(row['map_ids']) | set(script_maps[a]))
        row['source_untrusted'] = sorted(set(row['source_untrusted']) | taint[a])
        row['occurrences'].append(occurrence)
        if 'observed_following_start' in base:
            row['observed_following_start'] = sorted(set(row.get('observed_following_start', [])) | set(base['observed_following_start']))
    for a, ss in scripts.items():
        pending = {}
        pending_insns = []
        instructions = ss['instructions']
        for ip, ins in enumerate(instructions):
            name = ins.get('name')
            args = ins.get('args', [])
            if name in widths:
                valid = [z['width'] for z in args] == widths[name]
                fields = {k: value_field(arg, k not in ('unknown1', 'unknown2', 'unknown3', 'level')) for k, arg in zip(macro_fields[name], args)} if valid else {}
                following = []
                if name == 'setwildbattle':
                    previous_end = int(ins['addr'], 16) + len(bytes.fromhex(ins['raw']))
                    for later in instructions[ip + 1:]:
                        if int(later['addr'], 16) != previous_end: break
                        if later.get('name') == 'dowildbattle':
                            following.append(later['addr'])
                            break
                        if later.get('name') in barriers or any(x in str(later.get('name')) for x in ('call', 'goto', 'jump', 'special')) or later.get('runtime_stop') or later.get('name') is None: break
                        previous_end += len(bytes.fromhex(later['raw']))
                category = {'givepokemon': 'gift', 'giveegg': 'egg', 'setwildbattle': 'static_battle_candidate', 'additem': 'script_item_candidate'}[name]
                base = {'acquisition_id': f'{category}:{hexname(ins["addr"])}', 'category': category, 'instruction_addr': ins['addr'], 'command': name, 'raw_args': args, 'raw': ins['raw'], 'fields': fields, 'field_contract': {'reference': macro_path, 'macro': name, 'expected_widths': widths[name], 'matches': valid}, 'unresolved': [] if valid else ['decoded argument widths do not match reference macro'], 'condition_status': 'instruction_evidence_not_story_reachability', 'observed_following_start': following, 'following_start_note': '仅同一已解码直线序列观测，不证明必执行或可捕获。', 'source': source(SP, f'/scripts/{a}/instructions/{ip}')}
                merge_acq(acquisitions, ins['addr'], base, a, {'script': a, 'instruction_index': ip, 'observed_following_start': following})
            # Strict adjacency: ONLY constant/variable assignments immediately followed by callstd.
            if name in ('setvar', 'setorcopyvar') and [x['width'] for x in args] == [2, 2] and args[0]['value'] in (0x8000, 0x8001):
                if pending_insns and int(ins['addr'], 16) != int(pending_insns[-1]['addr'], 16) + len(bytes.fromhex(pending_insns[-1]['raw'])):
                    pending = {}; pending_insns = []
                pending[args[0]['value']] = value_field(args[1], name == 'setorcopyvar')
                pending_insns.append(ins)
            elif name == 'callstd' and pending:
                if args and args[0]['value'] in (0, 1) and 0x8000 in pending and 0x8001 in pending and int(ins['addr'], 16) == int(pending_insns[-1]['addr'], 16) + len(bytes.fromhex(pending_insns[-1]['raw'])):
                    std_id = args[0]['value']
                    base = {'acquisition_id': f'script_item_candidate:std:{hexname(ins["addr"])}', 'category': 'script_item_candidate', 'instruction_addr': ins['addr'], 'command': 'adjacent_assignments_callstd', 'raw_args': args, 'assignment_evidence': list(pending_insns), 'fields': {'item_index': pending[0x8000], 'quantity': pending[0x8001]}, 'standard_id': std_id, 'standard_target': standard['scripts'][std_id]['addr'], 'reference_label': 'MSG_OBTAIN' if std_id == 0 else 'MSG_FIND', 'condition_status': 'reference_pattern_candidate_not_confirmed_runtime_obtain', 'unresolved': ['std_and_special.json confirms slot target only, not this ROM complete standard-script acquisition semantics'], 'source': source(SP, f'/scripts/{a}/instructions/{ip}')}
                    merge_acq(std_candidates, ins['addr'], base, a, {'script': a, 'instruction_index': ip})
                pending = {}; pending_insns = []
            else:
                pending = {}; pending_insns = []
    acquisition_rows = list(acquisitions.values()) + list(std_candidates.values())
    for row in acquisition_rows:
        row['page_paths'] = [mpage(m) for m in row['map_ids']] or ['world/pages/mechanics/script_acquisitions.md']
        for mid in row['map_ids'] or [None]:
            pp = mpage(mid) if mid else 'world/pages/mechanics/script_acquisitions.md'
            base = backlink(row['category'], row['acquisition_id'] + ':' + str(mid), mid, pp, row['source'], script=row['source_scripts'], source_roots=row['source_roots'], source_untrusted=row['source_untrusted'], condition_status='source_untrusted' if row['source_untrusted'] else row['condition_status'], fields=row['fields'], observed_following_start=row.get('observed_following_start', []))
            for field, dest in [('species_id', by_species), ('item_index', by_item), ('held_item_index', by_item)]:
                f = row['fields'].get(field)
                if f and f['kind'] == 'literal':
                    catalog = species if field == 'species_id' else items
                    if f['value'] in catalog:
                        add_index(dest, f['value'], {**base, 'parameter_role': field, 'level': row['fields'].get('level'), 'quantity': row['fields'].get('quantity')})
                    elif f['value'] != 0:
                        row['unresolved'].append(f'{field} literal outside current core catalog: {f["value"]}')
    save('data/script_acquisitions.json', {'records': acquisition_rows, 'source_untrusted': [r['acquisition_id'] for r in acquisition_rows if r['source_untrusted']], 'known_untrusted_roots': sorted(untrusted_roots), 'reference_macros': widths, 'standard_call_contract': 'strict adjacent 8000/8001 assignments + callstd0/1; reference candidate, ROM standard semantics not promoted', 'note': '指令证据不保证可达、成功、已获得或可捕获。变量参数保留variable_ref，禁止整数表误查。'})
    csvsave('data/script_acquisitions.csv', acquisition_rows)
    save('data/acquisition_by_species.json', dict(sorted(by_species.items(), key=lambda x: int(x[0]))))
    save('data/acquisition_by_item.json', dict(sorted(by_item.items(), key=lambda x: int(x[0]))))

    trainer_rows = []
    trainers_by_map = defaultdict(set)
    for ti, tr in enumerate(trainers):
        refs = usage['usage'].get(str(tr['id']), [])
        mids = sorted({m for r in refs for m in script_maps.get(r['script'], [])})
        row = {**tr, 'map_ids': mids, 'usage_records': refs, 'page_path': f'world/pages/trainers/{tr["id"]:04}.md', 'source': source(TRP, f'/trainers/{ti}'), 'level_note': '基础队伍表等级，不保证每场实际缩放后等级。'}
        trainer_rows.append(row)
        for mid in mids: trainers_by_map[mid].add(tr['id'])
    special = {k: {**v, 'classification': 'special_builder_not_missing_ordinary_record' if int(k) in range(0x395, 0x39A) else 'out_of_ordinary_table', 'identity': None, 'party': None, 'reason': '普通743表不适用；不由参考type标签推人物或队伍。'} for k, v in usage['out_of_table'].items()}
    save('data/trainers.json', {'trainers': trainer_rows, 'special_references': special})
    csvsave('data/trainers.csv', [{**{k: v for k, v in tr.items() if k not in ('party', 'party_raw')}, 'party_member': p} for tr in trainer_rows for p in tr['party']])
    region_rows = []
    for key, rg in region_src['names'].items():
        section_id = rg.get('mapsec_id', int(rg['mapsec'], 16))
        region_rows.append({**rg, 'mapsec_id': section_id, 'pool_index': int(key), 'map_ids': sorted(maps_by_section[section_id]), 'source': source(RGP, '/names/' + key), 'region_semantics': 'ROM map section; not inferred major region', 'page_path': f'world/pages/regions/{section_id:04}.md'})
    save('data/regions.json', region_rows)
    csvsave('data/regions.csv', region_rows)

    for tx in text_rows:
        pp = tx['page_path']
        content = ['# 文本 ' + tx['addr'], '', source_line(tx['source']), '', '控制符按原导出保留；Unicode为外部字表注释。', '', '## 完整解码原文', '', '```text', tx['text'], '```', '', '## 原字节', '', '`' + tx['raw'] + '`', '', 'bytes：' + str(tx['bytes']), '', '## 来源引用', '']
        content += table(['脚本', '指令', '参数at', '命令', '地图'], [[r['script'], r['instruction_addr'], r['argument_addr'], r['cmd'], ' / '.join(link(pp, mpage(m), m + ' ' + mapname(m)) for m in r['maps']) or '未归图'] for r in tx['joined_references']])
        content += ['', '原referenced_by（完整）：', '', '```json', json.dumps(tx['referenced_by'], ensure_ascii=False, indent=1), '```']
        save(pp.removeprefix('world/'), '\n'.join(content) + '\n')
    for tr in trainer_rows:
        pp = tr['page_path']
        content = [f'# 训练师 {tr["id"]}：{tr["name"] or "NONE"}', '', source_line(tr['source']), '', tr['level_note'], '', f'职业ID：{tr["trainerClass"]}（没有已恢复职业名称表）；partyFlags={tr["partyFlags_raw"]}；aiFlags={tr["aiFlags"]}；doubleBattle={tr["doubleBattle"]}。', '', '地图：' + (' / '.join(link(pp, mpage(m), m + ' ' + mapname(m)) for m in tr['map_ids']) or '当前未关联地图'), '', '特殊规则：`' + j(tr['special_rules']) + '`', '', '## 完整队伍', '']
        for p in tr['party']:
            content += [f'### 槽{p["slot"]}：' + corelink(pp, 'species', p['species_id'], p['species_name']), '', f'基础等级：{p["level"]}；物种基础属性ID：{j(p["species_types"])}；携带：' + corelink(pp, 'items', p['heldItem'], p['heldItem_name']), '', '招式：' + (' / '.join(corelink(pp, 'moves', mv['id'], mv['name']) + f' (type {mv["type"]})' for mv in (p['moves'] or [])) or '本记录没有自定义招式列表；不是实战无招式'), '', '首字段：`' + str(p['iv_raw']) + '`；' + p['iv_semantics'], '', 'EV spread：`' + j(p['ev_spread']) + '`', '', 'gate：`' + j(p.get('ev_spread_gate')) + '`', '', 'Camomons战斗属性：`' + j(p.get('battle_types_camomons_names')) + '`；来源前两招：`' + j(p.get('camomons_source_moves')) + '`', '', '强制闪光：`' + j(p.get('forced_shiny')) + '`', '', '队员原字节：`' + p['raw'] + '`', '']
        content += ['## 训练师使用道具', '', ' / '.join(corelink(pp, 'items', x, items.get(x, {}).get('name')) for x in tr['items']), '', '## 完整脚本引用', '', '```json', json.dumps(tr['usage_records'], ensure_ascii=False, indent=1), '```', '', '记录原字节：`' + tr['record_raw'] + '`']
        save(pp.removeprefix('world/'), '\n'.join(content) + '\n')
    for sh in shop_rows:
        pp = sh['page_path']
        content = ['# 静态商店 ' + sh['instr_addr'], '', source_line(sh['source']), '', f'指令类型：{sh["kind"]}；脚本：{sh["script_addr"]}；列表：{sh["list_addr"]}。', '', '价格为道具表值，不保证动态价格或剧情已解锁。', '', '## 完整库存', '']
        content += table(['序号', '道具index', '内嵌itemId', '道具表price'], [[ii, corelink(pp, 'items', x['index'], x['name']), x['itemId'], x['price']] for ii, x in enumerate(sh['items'])])
        content += ['', '地图：' + ' / '.join(link(pp, mpage(mapid(m['group'], m['num'])), m['name_zh']) for m in sh['maps']), '', '启发式前文条件（不是解锁证明）：`' + j(sh['conditions_heuristic']) + '`', '', '共享旗标：`' + j(sh['shared_flags']) + '`', '', '原库存：`' + sh['raw_list'] + '`']
        save(pp.removeprefix('world/'), '\n'.join(content) + '\n')

    # Mechanics retain existing rules and open fields; technical lifecycle is an appendix, not a blocker.
    mechanics_names = ['camomons', 'ev_spreads', 'level_scaling', 'broadcast', 'swarm', 'rtc', 'mode9_appendix', 'gb_player']
    mechanic_rows = []
    for slug, mech in zip(mechanics_names, inventory['mechanisms']):
        pp = f'world/pages/mechanics/{slug}.md'
        row = {**mech, 'page_path': pp, 'source': source('wiki_export/world/source_inventory.json', '/mechanisms/' + str(len(mechanic_rows)))}
        mechanic_rows.append(row)
        content = ['# ' + mech['topic'], '', source_line(row['source']), '', '## 已有规则', ''] + ['- ' + x for x in mech['confirmed_rules']] + ['', '## 具体边界/缺字段', ''] + ['- ' + x for x in mech['limits']] + ['', '## 证据入口', ''] + ['- `' + r + '`' for r in mech['reports']]
        if slug == 'broadcast': content += ['', '完整门控：', '', '```json', json.dumps(encounters['broadcast']['gating'], ensure_ascii=False, indent=1), '```', '', '全部广播/后备槽见 `world/data/encounters.json`；内部40/20/20/20不能当总体概率。']
        if slug == 'level_scaling': content += ['', '缺字段：完整缩放公式、触发条件、玩家队伍/徽章输入对应关系和最终等级求值。普通队伍基础level已完整导出，不套官方公式。']
        save(pp.removeprefix('world/'), '\n'.join(content) + '\n')
    save('data/mechanics.json', mechanic_rows)
    save('pages/mechanics/script_acquisitions.md', '# 脚本获取指令候选\n\n完整记录见 `world/data/script_acquisitions.json`。givepokemon/giveegg不保证剧情可达或赠送成功；setwildbattle只设置野战，不等于可捕获。additem不包含全部地面道具。紧邻8000/8001赋值加callstd0/1另列参考模式候选，编号运行语义未升级。变量与不可信根分别保留。\n\n未归图候选：\n\n' + '\n'.join('- `' + r['acquisition_id'] + '`；脚本`' + j(r['source_scripts']) + '`；参数`' + j(r['fields']) + '`' for r in acquisition_rows if not r['map_ids']) + '\n')
    save('pages/trainers/special_references.md', '# 普通表之外的特殊训练师引用\n\n919/920/921引用保留。ROM谓词(id-0x395)<=4的特殊分流不走普通743表；不以OAK_TUTORIAL等参考type标签命名人物，不伪造队伍。人物、队伍算法及实际运行可达性未证。\n\n来源：`trainers_research/out/trainer_usage.json` `/out_of_table`；`trainers_research/README.md`末节。\n\n```json\n' + json.dumps(special, ensure_ascii=False, indent=1) + '\n```\n')
    save('pages/shops/rejected_sources.md', '# 拒绝计入库存的源\n\n两处非法列表指针不计58有效库存。坏根0x08990B94来源已知不可信，不能据此断言游戏实际坏店。\n\n来源：`encounters_research/out/shops.json` `/rejected_invalid_pointer`。\n\n```json\n' + json.dumps(shop_src['rejected_invalid_pointer'], ensure_ascii=False, indent=1) + '\n```\n')

    map_rows = []
    hidden_by_map = defaultdict(list)
    for r in hidden: hidden_by_map[r['map_id']].append(r)
    broadcast_by_map = defaultdict(list)
    for r in broadcast: broadcast_by_map[r['map_id']].append(r)
    acquisitions_by_map = defaultdict(list)
    for r in acquisition_rows:
        for mid in r['map_ids']: acquisitions_by_map[mid].append(r)
    text_row_by_addr = {t['addr']: t for t in text_rows}
    for hi, h in enumerate(headers):
        mid = mapid(h['group'], h['num'])
        key = node_by_id[mid]['key']
        assert key == mapkey(mid)
        asset = assets_by_key.get(key)
        if asset: assert asset['source_path'] == f'maps_research/out/maps/png/{key}.png'
        em = event_maps[mid]
        pp = mpage(mid)
        row = {**h, 'id': mid, 'key': key, 'page_path': pp, 'events': em, 'edges': edge_by_map[mid], 'map_png': asset['export_path'] if asset else None, 'media_join_evidence': 'nodes.key == render_maps.py g%02d_n%03d file stem == assets.render_name; not name-text guessing', 'media_missing_reason': None if asset else '现成渲染缺失；不新绘制', 'tile_gap': render['maps_with_out_of_range_tile_ids'].get(mid), 'render_notes': {k: v for k, v in render['skipped_or_tile_problems'].items() if k == mid or k.startswith(mid + '/')}, 'script_addresses': sorted(scripts_by_map[mid]), 'text_addresses': sorted({t for a in scripts_by_map[mid] for t in text_by_script[a]}), 'trainer_ids': sorted(trainers_by_map[mid]), 'shop_instructions': [s['instr_addr'] for s in shops_by_map[mid]], 'wild_acquisition_ids': [w['acquisition_id'] for w in encounter_by_map[mid]], 'hidden_acquisition_ids': [w['acquisition_id'] for w in hidden_by_map[mid]], 'script_acquisition_ids': [w['acquisition_id'] for w in acquisitions_by_map[mid]], 'story_event_ids': [s['event_id'] for s in story_by_map[mid]], 'source': source(HP, f'/maps/{hi}'), 'music_id': h['music'], 'music_page': None, 'music_link_reason': '保留音乐编号；音乐导出目录尚未提供，不能猜曲目路径/中文名'}
        row['music_tracks'] = music_by_id.get(h['music'], [])
        row['music_page'] = 'assets/music.md' if row['music_tracks'] else None
        row['music_link_reason'] = 'exact raw numeric music ID == tracks.index; no masking' if row['music_tracks'] else 'raw music ID absent from tracks.index; no bit masking or title guessing'
        map_rows.append(row)
        content = [f'# {mid} {h["map_name_zh"]}', '', source_line(row['source']), '', f'地区段：{h["region_map_section_id"]}；尺寸{h["layout"]["width"]}×{h["layout"]["height"]}；天气{h["weather"]} / {h["weather_name"]}；地图类型{h["map_type"]} / {h["map_type_name"]}；music ID={h["music"]}（只按编号，不猜曲名）。', '', '## 静态地图', '']
        if asset: content += ['!' + link(pp, asset['export_path'], key)]
        else: content += ['现成PNG缺失（9张之一）；事件和数据保留，不新绘制。']
        content += ['', '音乐：' + (link(pp, 'assets/music.md', '双表曲目索引') + '；' + ' / '.join(f"{t['table']}:{t['index']} {t['name']} (flag {t['flag_174D']})" for t in row['music_tracks']) if row['music_tracks'] else f"原始music={h['music']}无法精确关联，不擅自去高位掩码。") + '。每表386条，主表385非空，第二表104差异；音频只保留外部引用，未复制。']
        content += ['', '渲染限制：`' + j(row['render_notes']) + '`；静态缺块：`' + j(row['tile_gap']) + '`。动画/历史VRAM不由静态图保证。', '', '## 连接与传送', '']
        content += table(['类型', '源事件', '目的地图', '目标warp', '字段/边界'], [[e['type'], e['source_object']['index'], link(pp, mpage(e['target']['map']), e['target']['map'] + ' ' + mapname(e['target']['map'])) if e['target'].get('map') in map_by_id else '动态runtime目的未知', e['target'].get('target_warp_id'), j(e['source_object'].get('fields')) + ('；动态保存warp，不创建127:127节点' if e['target'].get('resolution') else '')] for e in edge_by_map[mid]])
        for field, title in [('objects', '完整对象/NPC'), ('coord_events', '完整坐标事件'), ('bg_events', '完整背景事件'), ('warps', '完整原warp事件')]:
            content += ['', '## ' + title, '', f'来源：`{EP}` `/maps/{mid}/{field}`。', '']
            content += table(['index', 'localId', 'x,y,elevation', '脚本', '全部原字段'], [[e['index'], e.get('local_id'), f"{e.get('x')},{e.get('y')},{e.get('elevation')}", e.get('script'), j(e)] for e in em[field]])
        content += ['', '## 隐藏道具', '']
        content += table(['道具', '数量', '坐标', 'flag offset / underfoot'], [[corelink(pp, 'items', e['item_index'], e['item_name']), e['quantity'], f"{e['x']},{e['y']}", f"{e['hidden_item_flag_offset']} / {e['underfoot']}"] for e in hidden_by_map[mid]])
        content += ['', '## 野生遭遇', '', 'rate和槽权重分列，不相乘为全局出现/捕获概率；碎岩/撞树是共用字段。', '']
        content += table(['时段', '方法/槽', '宝可梦', '等级', 'encounter_rate', 'conditional_slot_weight'], [[w['time_band_zh'] + ' ' + w['hour_band'], w['method'] + '/' + str(w['slot']), corelink(pp, 'species', w['species_id'], w['species_name']), f"{w['min_level']}–{w['max_level']}", w['encounter_rate'], w['conditional_slot_weight']] for w in encounter_by_map[mid]])
        content += ['', '## 广播与群聚', '', link(pp, 'world/pages/mechanics/broadcast.md', '广播门控与概率说明'), '']
        content += table(['dow/标签', '槽', '宝可梦', '内部权重'], [[str(w['day_of_week']) + '/' + w['day_name'], w['slot'], corelink(pp, 'species', w['species_id'], w['species_name']), w['conditional_slot_weight']] for w in broadcast_by_map[mid]])
        content += ['- 群聚地区段候选：' + ' / '.join(corelink(pp, 'species', w['species_id'], w['species_name']) for w in swarms if mid in w['map_ids']) + '；不保证当前激活。', '', '## 训练师与商店', '']
        content += ['- ' + link(pp, trainer_rows[tid]['page_path'], f'{tid} {trainer_rows[tid]["name"]}') for tid in row['trainer_ids']]
        content += ['- ' + link(pp, s['page_path'], '商店 ' + s['instr_addr']) for s in shops_by_map[mid]]
        special_here = [(tid, r) for tid, v in special.items() for r in v['usages'] if mid in script_maps.get(r['script'], [])]
        if special_here: content += ['- ' + link(pp, 'world/pages/trainers/special_references.md', '特殊训练师引用') + '：' + j(sorted({tid for tid, _ in special_here}))]
        content += ['', '## 明确获取指令/标准调用候选', '', '不是可达性或获得成功保证；source_untrusted单独标注。', '']
        content += table(['ID/命令', '字段', '脚本', '不可信源', '后续野战启动观测'], [[r['acquisition_id'], j(r['fields']), j(r['source_scripts']), j(r['source_untrusted']), j(r.get('observed_following_start', []))] for r in acquisitions_by_map[mid]])
        content += ['', '## NPC/事件文字关联', '']
        for e in story_by_map[mid]:
            content += ['### ' + e['event_id'], '', '脚本：`' + j(e['script_addresses']) + '`；不可信源：`' + j(e['source_untrusted']) + '`', '', ' / '.join(link(pp, tpage(t), t) for t in e['text_addresses']) or '当前无已提取文字引用。', '']
        content += ['## 关联脚本条件、调用与变量旗标', '', '保留原操作数；以下不是已解锁保证或线性主线。', '']
        for a in row['script_addresses']:
            sx = script_index[a]
            content += ['### 脚本 ' + a, '', f'来源：`{SP}` `/scripts/{a}`；source_untrusted=`{j(sx["source_untrusted"])}`。', '', ' / '.join(link(pp, tpage(t), t) for t in sx['text_addresses']) or '无直接文字引用。', '']
            content += table(['addr', '指令', '原args', 'raw'], [[i['addr'], i.get('name'), j(i.get('args')), i['raw']] for i in sx['calls_conditions_and_state']])
            content += ['', '变量/旗标引用：`' + j(sx['variable_flag_references']) + '`', '']
        save(pp.removeprefix('world/'), '\n'.join(content) + '\n')
    save('data/maps.json', map_rows)
    csvsave('data/maps.csv', [{k: v for k, v in m.items() if k not in ('events', 'edges')} for m in map_rows])

    # Complete named navigation: no top-N truncation and no dependence on directory browsing.
    def navigation(path, title, navrows):
        pp = 'world/' + path
        content = ['# ' + title, '', f'共{len(navrows)}行；同名记录不合并。可按显示名/稳定ID搜索。', '']
        content += table(['稳定ID', '显示名', '页面'], [[ident, label, link(pp, target, label or ident)] for ident, label, target in navrows])
        save(path, '\n'.join(content) + '\n')
    navigation('pages/maps/index.md', '全部地图', [(m['id'], m['map_name_zh'], m['page_path']) for m in map_rows])
    navigation('pages/trainers/index.md', '全部普通训练师', [(str(t['id']), t['name'] or 'NONE', t['page_path']) for t in trainer_rows] + [('special', '919/920/921特殊引用（不是普通队伍）', 'world/pages/trainers/special_references.md')])
    navigation('pages/shops/index.md', '全部静态商店', [(s['instr_addr'], ' / '.join(m['name_zh'] for m in s['maps']) + ' ' + s['kind'], s['page_path']) for s in shop_rows] + [('rejected', '2处拒绝源', 'world/pages/shops/rejected_sources.md')])
    navigation('pages/texts/index.md', '全部原文本', [(t['addr'], t['text'][:90].replace('\n', ' '), t['page_path']) for t in text_rows])
    for rg in region_rows:
        pp = rg['page_path']
        content = [f"# 地区段 {rg['mapsec_id']}：{rg.get('name') or '名称未解析'}", '', source_line(rg['source']), '', '地区段编号不是推断的大地区归属。空/非法名称指针原样保留：`' + j({k: v for k, v in rg.items() if k not in ('map_ids', 'source')}) + '`', '', '## 全部关联地图', '']
        content += table(['地图ID', '名称'], [[m, link(pp, mpage(m), mapname(m))] for m in rg['map_ids']])
        save(pp.removeprefix('world/'), '\n'.join(content) + '\n')
    navigation('pages/regions/index.md', '全部地区段名称池（165）', [(str(r['mapsec_id']), r.get('name') or '名称未解析 / ' + str(r.get('error')), r['page_path']) for r in region_rows])
    navigation('pages/story_events/index.md', '全部地图NPC与剧情事件证据', [(e['event_id'], mapname(e['map_id']) + ' / ' + e['kind'] + ' / localId=' + str(e.get('local_id')), e['page_path']) for e in story_events])
    unmapped_nav = []
    for a in scripts:
        if script_maps[a]: continue
        pp = f'world/pages/story_events/unmapped/{hexname(a)}.md'
        content = ['# 未归图脚本 ' + a, '', source_line(source(SP, '/scripts/' + a)), '', '没有从现成branch来源归图，不强行分配地图；解码本身不证明来源可信。', '', '文字：' + (' / '.join(link(pp, tpage(t), t) for t in sorted(text_by_script[a])) or '无'), '', '```json', json.dumps(scripts[a], ensure_ascii=False, indent=1), '```']
        save(pp.removeprefix('world/'), '\n'.join(content) + '\n')
        unmapped_nav.append((a, '未归图脚本 ' + a + (' / source_untrusted' if taint[a] else ''), pp))
    navigation('pages/story_events/unmapped_scripts.md', '全部未归图脚本', unmapped_nav)
    navigation('pages/texts/unmapped.md', '全部未归图文本', [(t['addr'], t['text'][:90], t['page_path']) for t in text_rows if not t['map_ids']])
    acquisition_navigation = []
    for category, lookup, catalog in [('species', by_species, species), ('items', by_item, items)]:
        navrows = []
        for ident, refs in sorted(lookup.items(), key=lambda kv: int(kv[0])):
            name = catalog.get(int(ident), {}).get('name') or ident
            pp = f'world/pages/acquisitions/{category}/{int(ident):04}.md'
            content = [f'# {name} ({ident}) 获取证据', '', '按来源类别分开。所有条目都是既有证据，不保证剧情可达、购买解锁、获得成功或可捕获；概率不跨触发条件相乘。', '', corelink(pp, category, int(ident), name), '']
            content += table(['稳定获取ID', '类别', '地图', '来源页', '时段/方法/等级', '条件/参数'], [[r['acquisition_id'], r['category'], str(r['map_id']) + ' ' + str(r['map_name']), link(pp, r['page_path'], r['page_path']), j({k: r.get(k) for k in ('time', 'method', 'level', 'encounter_rate', 'conditional_slot_weight')}), j({k: r.get(k) for k in ('condition_status', 'source_untrusted', 'fields', 'quantity', 'price', 'day_of_week')})] for r in refs])
            content += ['', '完整来源JSON pointers：', '', '```json', json.dumps([{'acquisition_id': r['acquisition_id'], 'source': r['source']} for r in refs], ensure_ascii=False, indent=1), '```']
            save(pp.removeprefix('world/'), '\n'.join(content) + '\n')
            navrows.append((ident, name, pp))
        navigation(f'pages/acquisitions/{category}/index.md', '获取索引 / ' + category, navrows)
        acquisition_navigation.append((category, category + '全部获取来源', f'world/pages/acquisitions/{category}/index.md'))
    acquisition_navigation.append(('script_candidates', '脚本候选说明与未归图记录', 'world/pages/mechanics/script_acquisitions.md'))
    navigation('pages/acquisitions/index.md', '获取资料入口', acquisition_navigation)
    navigation('pages/mechanics/index.md', '系统机制入口', [(mechanics_names[i], r['topic'], r['page_path']) for i, r in enumerate(mechanic_rows)] + [('script_acquisitions', '脚本获取证据边界', 'world/pages/mechanics/script_acquisitions.md'), ('music', 'GB双表音乐772条元数据/外部链接', 'assets/music.md')])
    nav_sections = [('maps', '871地图'), ('regions', '165地区段名称池'), ('trainers', '743普通训练师与特殊引用'), ('shops', '58静态商店'), ('texts', '7513原文本'), ('story_events', '地图NPC/剧情事件证据'), ('acquisitions', '宝可梦与道具获取来源'), ('mechanics', '系统机制与音乐')]
    readme_navigation = '\n'.join('- ' + link('world/README.md', f'world/pages/{slug}/index.md', title) for slug, title in nav_sections)
    readme_navigation += '\n- ' + link('world/README.md', 'world/pages/story_events/unmapped_scripts.md', '全部未归图脚本') + '\n- ' + link('world/README.md', 'world/pages/texts/unmapped.md', '全部未归图文本')

    summary = {'maps': len(map_rows), 'regions_pool': len(region_rows), 'regions_used': len({h['region_map_section_id'] for h in headers}), 'ordinary_trainers': len(trainer_rows), 'party_members': sum(len(t['party']) for t in trainers), 'shops': len(shop_rows), 'rejected_shops': len(shop_src['rejected_invalid_pointer']), 'texts': len(text_rows), 'wild_slots': len(wild), 'broadcast_slots': len(broadcast), 'swarm_records': len(swarms), 'hidden_items': len(hidden), 'map_png_linked': sum(bool(m['map_png']) for m in map_rows), 'map_png_missing': sum(not m['map_png'] for m in map_rows), 'dynamic_warps': sum(e['target'].get('resolution') == 'dynamic_saved_warp' for e in edges), 'scripts': len(scripts), 'unmapped_scripts': sum(not m for m in script_maps.values()), 'unmapped_texts': sum(not t['map_ids'] for t in text_rows), 'story_events': len(story_events), 'script_acquisitions': dict(Counter(r['command'] for r in acquisition_rows)), 'source_untrusted_acquisitions': sum(bool(r['source_untrusted']) for r in acquisition_rows), 'acquisition_species_keys': len(by_species), 'acquisition_item_keys': len(by_item), 'source_manifest': SOURCES, 'open_fields': ['RTC actual game clock correctness', 'complete level scaling formula', 'special trainer identity/party', 'standard-call item semantic confirmation', 'music index export path not yet provided', 'runtime dynamic warp destination', 'story reachability is not statically asserted']}
    summary['open_fields'].remove('music index export path not yet provided')
    summary['music_raw_ids_joined'] = sum(bool(m['music_tracks']) for m in map_rows)
    summary['music_raw_ids_unjoined'] = sorted({m['music_id'] for m in map_rows if not m['music_tracks']})
    summary['regions_name_unresolved'] = sum(not r.get('name') for r in region_rows)
    summary['navigation_complete'] = True
    assert (summary['maps'], summary['ordinary_trainers'], summary['party_members'], summary['shops'], summary['texts'], summary['wild_slots'], summary['hidden_items'], summary['broadcast_slots'], summary['swarm_records']) == (871, 743, 1892, 58, 7513, 6624, 451, 1200, 16)
    assert summary['map_png_linked'] == 862 and summary['dynamic_warps'] == 45
    # Scoped production verification: every written page/data file and every generated link exists.
    missing_links = sorted(p for p in LINKS if not (WIKI / p).is_file())
    assert not missing_links, missing_links[:20]
    for path in (p for p in GENERATED if p.suffix == '.json'):
        json.loads(path.read_text(encoding='utf-8'))
    assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == digest for p, digest in SOURCES.items())
    summary['verification'] = {'generated_json_readback': True, 'referenced_paths_exist': True, 'link_targets_checked': len(LINKS), 'source_files_unchanged': True, 'execution': 'export command only; no game/emulator/new render/test suite'}
    save('summary.json', summary)
    save('README.md', '# 世界Wiki导出\n\n由 `wiki_export/scripts/export_world.py` 读取既有资料生成；未运行游戏/仿真/重绘，不改源数据。\n\n## 完整可检索导航\n\n' + readme_navigation + '\n\n## 数据与边界\n\n`data/`提供全部结构化JSON及适用CSV。core直接合并`acquisition_by_species.json`与`acquisition_by_item.json`，字典键为内部species_id与道具index，不是内嵌itemId。\n\n45动态warp目的runtime未知；24stop根及08990B94传播来源标记不可信。指令证据不保证剧情可达/获得成功；设置野战不等于可捕获。普通地面道具标准调用另列reference候选，不以95条additem代表全部获取。时段、encounter_rate与槽权重分别保留，不乘成全局概率。训练师等级/商店价格均为表值。地图名称为地区段，不猜大地区。音乐仅原始ID精确关联双表index，未复制音频。\n\n## 制作摘要\n\n```json\n' + json.dumps({k: v for k, v in summary.items() if k != 'source_manifest'}, ensure_ascii=False, indent=1) + '\n```\n')
    print(json.dumps({k: v for k, v in summary.items() if k != 'source_manifest'}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
