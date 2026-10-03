"""ROM-backed, conservative input-count BFS for ice map 53:6 only."""
import hashlib
import json
import struct
from collections import Counter, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'player_guide/data/ice_53_6_route.json'

def solve(rock_present=True):
    headers = json.loads((ROOT / 'maps_research/out/maps/headers.json').read_text(encoding='utf-8'))
    manifest = json.loads((ROOT / 'maps_research/out/tilesets/manifest.json').read_text(encoding='utf-8'))
    events = json.loads((ROOT / 'maps_research/out/events/events.json').read_text(encoding='utf-8'))['maps']['53:6']
    rom = (ROOT.parent / headers['rom']).read_bytes()
    def u32(address):
        return struct.unpack_from('<I', rom, address - 0x08000000)[0]
    def raw(address, count):
        return rom[address - 0x08000000:address - 0x08000000 + count].hex(' ')
    header = next(v for v in headers['maps'] if v['group'] == 53 and v['num'] == 6)
    layout = header['layout']
    width, height = layout['width'], layout['height']
    masks, shifts = u32(0x08058F40), u32(0x08058F44)
    # MapGridGetMetatileBehaviorAt: movs r2,#0 at 08058F82.
    mask, shift = u32(masks), rom[shifts - 0x08000000]
    attr_addresses = [int(manifest['tilesets'][layout[k]]['metatile_attributes'], 16)
                      for k in ('primary_tileset', 'secondary_tileset')]
    grid = {}
    for y in range(height):
        for x in range(width):
            address = int(layout['map'], 16) + 2 * (y * width + x)
            cell = struct.unpack_from('<H', rom, address - 0x08000000)[0]
            tile = cell & 0x3FF
            attr_address = attr_addresses[tile >= 640] + 4 * (tile if tile < 640 else tile - 640)
            attr = u32(attr_address)
            grid[x, y] = dict(x=x, y=y, cell_address=f'0x{address:08X}', cell=f'0x{cell:04X}',
                              metatile_id=tile, collision=(cell >> 10) & 3, elevation=cell >> 12,
                              attribute_address=f'0x{attr_address:08X}', attribute=f'0x{attr:08X}',
                              behavior=(attr & mask) >> shift)
    objects = {(v['x'], v['y']): v for v in events['objects']}
    if not rock_present:
        del objects[10, 12]
    warps = {(v['x'], v['y']): v for v in events['warps']}
    start, target = (24, 9), (14, 16)
    directions = [('up', '上', (0, -1)), ('down', '下', (0, 1)),
                  ('left', '左', (-1, 0)), ('right', '右', (1, 0))]
    rejected = {}
    def obstruction(a, b):
        if b not in grid:
            return 'map_boundary'
        if grid[b]['collision']:
            return 'collision'
        if b in objects:
            return 'object_assumed_present'
        ea, eb = grid[a]['elevation'], grid[b]['elevation']
        if ea != eb and ea != 0 and eb != 0:
            rejected[a, b] = 'unverified_elevation_transition'
            return 'unverified_elevation_transition'
        if grid[b]['behavior'] not in (0, 0x23, 0x60):
            rejected[a, b] = 'unverified_behavior'
            return 'unverified_behavior'
        return None
    def move(pos, direction, chinese, delta):
        traversed, sliding, reason = [], False, None
        current = pos
        while True:
            nxt = current[0] + delta[0], current[1] + delta[1]
            reason = obstruction(current, nxt)
            if reason:
                break
            traversed.append(nxt)
            current = nxt
            if current in warps:
                reason = 'warp'
                break
            if grid[current]['behavior'] != 0x23:
                reason = 'non_ice'
                break
            sliding = True
        if not traversed:
            return None
        return dict(direction=direction, direction_zh=chinese, start=list(pos),
                    traversed=[grid[p] for p in traversed], start_evidence=grid[pos],
                    end=list(current), sliding=sliding, stop_reason=reason,
                    blocked_next=grid.get(nxt) if reason not in ('warp', 'non_ice') else None,
                    final_warp=warps.get(current))
    queue, previous = deque([start]), {start: None}
    while queue and target not in previous:
        pos = queue.popleft()
        for direction, chinese, delta in directions:
            action = move(pos, direction, chinese, delta)
            if action is None:
                continue
            end = tuple(action['end'])
            if end in warps and end != target:
                continue
            if end not in previous:
                previous[end] = pos, action
                queue.append(end)
    route = []
    if target in previous:
        pos = target
        while pos != start:
            pos, action = previous[pos]
            route.append(action)
        route.reverse()
    for index, action in enumerate(route, 1):
        action['input_number'] = index
    groups = []
    for action in route:
        if not action['sliding'] and groups and not groups[-1]['sliding'] and groups[-1]['direction'] == action['direction']:
            groups[-1]['steps'] += 1
            groups[-1]['end'] = action['end']
        else:
            groups.append(dict(direction=action['direction'], direction_zh=action['direction_zh'],
                               sliding=action['sliding'], steps=1, start=action['start'], end=action['end']))
    result = dict(map='53:6', coordinates='zero-based map tile x,y; x right, y down',
                  rom_sha256=hashlib.sha256(rom).hexdigest(), layout=layout,
                  entrance=dict(old_display_number=23, **warps[start]),
                  destination=dict(old_display_number=24, **warps[target]),
                  extraction=dict(mask_table=f'0x{masks:08X}', shift_table=f'0x{shifts:08X}',
                                  selector=0, mask=mask, shift=shift,
                                  behavior_function_bytes=raw(0x08058F78, 20),
                                  extract_function_bytes=raw(0x08058F18, 48),
                                  ice_predicate_bytes=raw(0x08059DAC, 20),
                                  attribute_addresses=[f'0x{v:08X}' for v in attr_addresses]),
                  behavior_histogram=dict(Counter(v['behavior'] for v in grid.values())),
                  collision_histogram=dict(Counter(v['collision'] for v in grid.values())),
                  elevation_histogram=dict(Counter(v['elevation'] for v in grid.values())),
                  objects=events['objects'], warps=events['warps'],
                  assumptions=['All objects blocked except local_id 1 when rock_present is false.',
                               'Every warp terminates movement; non-target warps cannot be crossed.',
                               'Different nonzero elevations blocked pending mechanism verification.',
                               'Elevation zero treated as neutral; all transitions retained in evidence.',
                               'Ice behavior 0x23; collision != 0 blocked; no emulator used.'],
                  rock_present=rock_present,
                  found=target in previous, input_count=len(route), route=route, player_groups=groups,
                  unverified_transitions=[dict(start=a, end=b, reason=r) for (a, b), r in rejected.items()])
    return result

def main():
    present = json.loads(OUT.read_text(encoding='utf-8')) if OUT.exists() else solve(True)
    present['rock_present'] = True
    cleared = solve(False)
    present['object_cleared_scenario'] = cleared
    scripts = json.loads((ROOT / 'maps_research/out/scripts/scripts.json').read_text(encoding='utf-8'))
    texts = json.loads((ROOT / 'maps_research/out/scripts/text.json').read_text(encoding='utf-8'))
    present['object_script_evidence'] = dict(
        coordinate=[10, 12], local_id=1, flag_id=5726,
        script=scripts['scripts']['0x08AAC706'], text=texts['strings']['0x08AAC777'],
        conclusion='Root only loads text, callstd 6, end; no setflag/removeobject or direct script-address call. Text says stuck in ice and cannot push; not evidence of Rock Smash removability.',
        limitation='Engine standard-script dispatch for callstd 6 not expanded; no claims about other scripts changing the flag.')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(present, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for result in (present, cleared):
        print(json.dumps(dict(rock_present=result['rock_present'], found=result['found'],
                              input_count=result['input_count'], groups=result['player_groups']),
                         ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
