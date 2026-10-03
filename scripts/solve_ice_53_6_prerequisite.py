"""Single-boulder prerequisite BFS on 53:5; no emulator or unrelated maps."""
import json
import struct
from collections import Counter, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'player_guide/data/ice_53_6_prerequisite.json'

def main():
    headers = json.loads((ROOT / 'maps_research/out/maps/headers.json').read_text(encoding='utf-8'))
    manifest = json.loads((ROOT / 'maps_research/out/tilesets/manifest.json').read_text(encoding='utf-8'))
    events = json.loads((ROOT / 'maps_research/out/events/events.json').read_text(encoding='utf-8'))['maps']['53:5']
    layout = next(v['layout'] for v in headers['maps'] if v['group'] == 53 and v['num'] == 5)
    rom = (ROOT.parent / headers['rom']).read_bytes()
    attrs = [int(manifest['tilesets'][layout[k]]['metatile_attributes'], 16) for k in ('primary_tileset', 'secondary_tileset')]
    def u32(address):
        return struct.unpack_from('<I', rom, address - 0x08000000)[0]
    mask = u32(u32(0x08058F40))
    shift = rom[u32(0x08058F44) - 0x08000000]
    grid = {}
    for y in range(layout['height']):
        for x in range(layout['width']):
            address = int(layout['map'], 16) + 2 * (y * layout['width'] + x)
            cell = struct.unpack_from('<H', rom, address - 0x08000000)[0]
            tile = cell & 1023
            ap = attrs[tile >= 640] + 4 * (tile if tile < 640 else tile - 640)
            attr = u32(ap)
            grid[x, y] = dict(x=x, y=y, cell=f'0x{cell:04X}', cell_address=f'0x{address:08X}',
                              collision=(cell >> 10) & 3, elevation=cell >> 12, metatile_id=tile,
                              behavior=(attr & mask) >> shift, attribute=f'0x{attr:08X}')
    target_object = next(o for o in events['objects'] if o['local_id'] == 3)
    fixed = {(o['x'], o['y']) for o in events['objects'] if o['local_id'] != 3}
    warps = {(w['x'], w['y']): w for w in events['warps']}
    start = ((24, 7), (10, 12))
    hole = (11, 9)
    directions = [('上', (0, -1)), ('下', (0, 1)), ('左', (-1, 0)), ('右', (1, 0))]
    def plus(a, d):
        return a[0] + d[0], a[1] + d[1]
    def terrain_ok(a, b):
        if b not in grid or grid[b]['collision'] or b in fixed:
            return False
        ea, eb = grid[a]['elevation'], grid[b]['elevation']
        return (ea == eb or ea == 0 or eb == 0) and grid[b]['behavior'] in (0, 0x23, 0x60, 0x66)
    queue, previous = deque([start]), {start: None}
    final = None
    while queue:
        state = queue.popleft()
        p, rock = state
        if rock == hole:
            final = state
            break
        for direction, delta in directions:
            nxt = plus(p, delta)
            if nxt == rock:
                dest = plus(rock, delta)
                if not terrain_ok(p, rock) or not terrain_ok(rock, dest):
                    continue
                if dest in warps and dest != hole:
                    continue
                # No unverified boulder-on-ice movement is assumed.
                if grid[dest]['behavior'] == 0x23:
                    continue
                end_state = (rock, dest)
                action = dict(kind='push', direction=direction, start=p, end=rock,
                              rock_start=rock, rock_end=dest, traversed=[grid[rock]],
                              rock_destination_evidence=grid[dest], sliding=False)
            else:
                if not terrain_ok(p, nxt) or nxt in warps:
                    continue
                traversed, current, sliding = [], nxt, False
                while True:
                    traversed.append(grid[current])
                    if grid[current]['behavior'] != 0x23:
                        break
                    sliding = True
                    nxt = plus(current, delta)
                    if nxt == rock or nxt in warps or not terrain_ok(current, nxt):
                        break
                    current = nxt
                # A warp in the slide direction would terminate this map, not stop at its lip.
                if sliding and nxt in warps and terrain_ok(current, nxt):
                    continue
                end_state = (current, rock)
                action = dict(kind='walk', direction=direction, start=p, end=current,
                              traversed=traversed, sliding=sliding)
            if end_state not in previous:
                previous[end_state] = state, action
                queue.append(end_state)
    route = []
    state = final
    while state is not None and state != start:
        state, action = previous[state]
        route.append(action)
    route.reverse()
    def groups(actions):
        result = []
        for a in actions:
            if result and not a['sliding'] and not result[-1]['sliding'] and result[-1]['direction'] == a['direction']:
                result[-1]['steps'] += 1
                result[-1]['end'] = a['end']
            else:
                result.append(dict(direction=a['direction'], steps=1, start=a['start'], end=a['end'], sliding=a['sliding']))
        return result
    pushes, approach = [], []
    for number, action in enumerate(route, 1):
        action['input_number'] = number
        if action['kind'] == 'push':
            pushes.append(dict(push_number=len(pushes) + 1, approach=groups(approach), push=action))
            approach = []
        else:
            approach.append(action)
    scripts = json.loads((ROOT / 'maps_research/out/scripts/scripts.json').read_text(encoding='utf-8'))['scripts']
    texts = json.loads((ROOT / 'maps_research/out/scripts/text.json').read_text(encoding='utf-8'))['strings']
    root_script = scripts['0x081BE11D']
    addresses = ['0x081BE11D'] + [f"0x{a['value']:08X}" for i in root_script['instructions'] for a in i['args'] if a.get('class') == 'script']
    evidence = []
    for address in addresses:
        rec = scripts.get(address)
        if rec:
            text_addresses = [f"0x{a['value']:08X}" for i in rec['instructions'] for a in i['args'] if a.get('class') == 'text']
            evidence.append(dict(address=address, instructions=rec['instructions'], texts=[texts[a] for a in text_addresses if a in texts]))
    result = dict(map='53:5', coordinates='zero-based x,y', layout=layout, start=start,
                  target_object=target_object, target_hole=warps[hole], objects=events['objects'], warps=events['warps'],
                  behavior_histogram=dict(Counter(v['behavior'] for v in grid.values())),
                  collision_histogram=dict(Counter(v['collision'] for v in grid.values())),
                  behavior_0x66_cells=[v for v in grid.values() if v['behavior'] == 0x66],
                  found=final is not None, input_count=len(route), push_count=len(pushes), route=route, pushes=pushes,
                  strength_script_evidence=evidence,
                  assumptions=['Only local3 boulder moves; all other objects block.',
                               'Player never enters a warp; boulder may enter target hole and finish.',
                               'Elevation zero connects adjacent nonzero elevations.',
                               'Behavior 0x23 slides player; boulder pushes onto ice excluded as unverified.',
                               'Behavior 0x66 is new on this map and occurs at its four hole warps.',
                               'Strength must already be usable/enabled; menu interaction is not counted.',
                               'ROM model calculation only, not emulator verification.'])
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(found=result['found'], input_count=len(route), push_count=len(pushes),
                         pushes=[dict(push_number=p['push_number'], approach=p['approach'],
                                      direction=p['push']['direction'], rock_start=p['push']['rock_start'],
                                      rock_end=p['push']['rock_end'], player_end=p['push']['end']) for p in pushes],
                         behavior_histogram=result['behavior_histogram']), ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
