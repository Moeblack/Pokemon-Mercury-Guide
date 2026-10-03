"""Resolve guide rows to event identities without conflating script instructions."""
from collections import Counter, defaultdict, deque
from copy import deepcopy
import json
import math
import re


_RECORD_FIELDS = (
    'addr', 'index', 'local_id', 'script', 'x', 'y', 'elevation',
    'trigger', 'index_var', 'flag_id', 'flag_id2', 'kind',
)
_FINGERPRINT_FIELDS = (
    'source', 'acquisition_id', 'acquisition_ids', 'script', 'source_scripts',
    'source_roots', 'category', 'quantity', 'price', 'level',
    'hidden_item_flag_offset',
)


def _stable(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _sequence(value):
    if value is None:
        return []
    return list(value) if isinstance(value, (list, tuple, set)) else [value]


def _coordinate(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


class EventLocations:
    """Index immutable input snapshots; resolve() counts the locations it returns.

    Identities are stable JSON strings. Object/background locations use geometry
    ``point``; coordinate events always use ``trigger`` when coordinates exist.
    Audit counts are per returned location, while trigger_groups are unique among
    the groups actually returned (not all groups merely present in the inputs).
    """

    def __init__(self, events, scripts):
        self.events = deepcopy(events)
        self.scripts = deepcopy(scripts)
        self.parents = defaultdict(set)
        self._script_aliases = {}
        for script in self.scripts:
            self._script_aliases[str(script)] = script
            try:
                self._script_aliases[int(str(script), 0)] = script
            except (ValueError, TypeError):
                pass
        for script, record in self.scripts.items():
            for instruction in record.get('instructions', []):
                for operand in instruction.get('args', []):
                    if operand.get('class') != 'script':
                        continue
                    target = self._script_key(operand.get('value'))
                    if target in self.scripts:
                        self.parents[target].add(script)
            for source in record.get('sources', []):
                if source.get('kind') == 'branch':
                    parent = self._script_key(source.get('where'))
                    if parent in self.scripts:
                        self.parents[script].add(parent)
        self._groups = {}
        self._event_at = defaultdict(set)
        self._map_groups = defaultdict(set)
        self._ancestor_cache = {}
        self._geometry_counts = Counter()
        self._reason_counts = Counter()
        self._issue_counts = Counter()
        self._trigger_groups = {}
        self._resolve_calls = 0
        for mid, map_events in self.events.items():
            for category in ('objects', 'coord_events', 'bg_events'):
                for ordinal, event in enumerate(map_events.get(category, [])):
                    script = event.get('script')
                    if category == 'coord_events':
                        identity = [mid, category, script, event.get('trigger'),
                                    event.get('index_var'), event.get('elevation')]
                        condition = {'variable': event.get('trigger'),
                                     'value': event.get('index_var'),
                                     'elevation': event.get('elevation')}
                    elif category == 'objects':
                        identity = [mid, category, event.get('local_id'), script,
                                    event.get('flag_id'), event.get('flag_id2'),
                                    event.get('x'), event.get('y')]
                        condition = {key: event[key] for key in ('flag_id', 'flag_id2') if key in event}
                    else:
                        identity = [mid, category, event.get('index', ordinal), script,
                                    event.get('kind'), event.get('x'), event.get('y')]
                        condition = {}
                    key = _stable(identity)
                    group = self._groups.setdefault(key, {
                        'identity': key, 'mid': mid, 'category': category,
                        'event_entry': script, 'condition': condition, 'records': [],
                    })
                    group['records'].append(event)
                    self._map_groups[mid].add(key)
                    if script is not None:
                        self._event_at[self._script_key(script)].add(key)

    def _script_key(self, value):
        if isinstance(value, (str, int)):
            if value in self._script_aliases:
                return self._script_aliases[value]
            if isinstance(value, str):
                try:
                    return self._script_aliases.get(int(value, 0), value)
                except ValueError:
                    pass
            return value
        return None

    def _ancestors(self, script, allow_shared):
        cache_key = (script, allow_shared)
        if cache_key not in self._ancestor_cache:
            queue = deque([script])
            seen = {script}
            ancestors = set()
            ambiguous = False
            while queue:
                current = queue.popleft()
                parents = self.parents.get(current, set())
                if len(parents) > 20 and not allow_shared:
                    ambiguous = True
                    continue
                ancestors.add(current)
                for parent in sorted(parents, key=str):
                    if parent not in seen:
                        seen.add(parent)
                        queue.append(parent)
            self._ancestor_cache[cache_key] = (frozenset(ancestors), ambiguous)
        return self._ancestor_cache[cache_key]

    def _fingerprint(self, row):
        return {key: row[key] for key in _FINGERPRINT_FIELDS if key in row}

    def _location(self, key):
        group = self._groups[key]
        records = group['records']
        tiles = sorted({(event.get('x'), event.get('y')) for event in records
                        if _coordinate(event.get('x')) and _coordinate(event.get('y'))})
        result = {
            'identity': key,
            'geometry': 'trigger' if group['category'] == 'coord_events' else 'point',
            'x': None, 'y': None,
            'event_entry': group['event_entry'],
            'condition': deepcopy(group['condition']),
            'event_records': sorted(
                [{field: deepcopy(event[field]) for field in _RECORD_FIELDS if field in event}
                 for event in records], key=_stable),
        }
        if tiles:
            result['x'], result['y'] = tiles[len(tiles) // 2]
            if result['geometry'] == 'trigger':
                result['trigger_tiles'] = [list(tile) for tile in tiles]
            result['resolution_reason'] = 'event_evidence'
        else:
            result['geometry'] = 'area'
            result['resolution_reason'] = 'event_coordinates_missing'
        return result

    def resolve(self, row, mid) -> list[dict]:
        """Return evidence-backed event locations, or a fingerprinted fallback."""
        self._resolve_calls += 1
        roots = _sequence(row.get('source_roots'))
        object_roots = []
        categories = set()
        recognized_roots = False
        for root in roots:
            match = re.fullmatch(r'object:(\d+:\d+)/local(\d+)', str(root))
            if match:
                recognized_roots = True
                if match.group(1) == mid:
                    object_roots.append(int(match.group(2)))
                continue
            match = re.fullmatch(r'(coord|bg):(\d+:\d+)', str(root))
            if match:
                recognized_roots = True
                if match.group(2) == mid:
                    categories.add('coord_events' if match.group(1) == 'coord' else 'bg_events')
            if re.fullmatch(r'map_script_table:\d+:\d+', str(root)):
                recognized_roots = True
        candidates = set()
        ambiguous = False
        if object_roots:
            for key in self._map_groups.get(mid, ()):
                group = self._groups[key]
                if group['category'] == 'objects' and any(
                    str(event.get('local_id')) in {str(local_id) for local_id in object_roots}
                    for event in group['records']
                ):
                    candidates.add(key)
        if not recognized_roots or categories:
            scripts = _sequence(row.get('script') or row.get('source_scripts'))
            for script in scripts:
                script = self._script_key(script)
                if script is None:
                    continue
                ancestors, blocked = self._ancestors(script, bool(categories))
                ambiguous = ambiguous or blocked
                for ancestor in ancestors:
                    for key in self._event_at.get(ancestor, ()):
                        group = self._groups[key]
                        if group['mid'] == mid and (not categories or group['category'] in categories):
                            candidates.add(key)
        explicit = _coordinate(row.get('x')) and _coordinate(row.get('y'))
        if explicit:
            candidates = {
                key for key in candidates
                if any(event.get('x') == row['x'] and event.get('y') == row['y']
                       for event in self._groups[key]['records'])
            }
        locations = [self._location(key) for key in sorted(candidates)]
        if ambiguous:
            self._issue_counts['ambiguous_shared_script'] += 1
        if not locations:
            reason = ('ambiguous_shared_script' if ambiguous else
                      'explicit_unclassified' if explicit else
                      'explicit_root_unmatched' if recognized_roots else 'no_event_evidence')
            geometry = 'point' if explicit else 'area'
            x, y = (row['x'], row['y']) if explicit else (None, None)
            locations = [{
                'identity': _stable([mid, 'explicit_unclassified' if explicit else 'area',
                                     x, y, self._fingerprint(row)]),
                'geometry': geometry, 'x': x, 'y': y,
                'event_entry': None, 'condition': {}, 'event_records': [],
                'resolution_reason': reason,
            }]
        for location in locations:
            self._geometry_counts[location['geometry']] += 1
            reason = location['resolution_reason']
            self._reason_counts[reason] += 1
            if ambiguous:
                location['resolution_warnings'] = ['ambiguous_shared_script']
            if location['geometry'] == 'trigger':
                self._trigger_groups[location['identity']] = {
                    'mid': mid, 'script': location['event_entry'],
                    'condition': deepcopy(location['condition']),
                    'tiles': deepcopy(location['trigger_tiles']),
                    'event_records': deepcopy(location['event_records']),
                }
        return locations

    def instruction_address(self, row) -> str | None:
        """Read the addressed instruction itself, never substitute its script root."""
        source = row.get('source')
        if not isinstance(source, dict):
            return None
        pointer = source.get('json_pointer')
        if not isinstance(pointer, str):
            return None
        match = re.fullmatch(r'/scripts/([^/]+)/instructions/(0|[1-9]\d*)', pointer)
        if not match:
            return None
        script = match.group(1).replace('~1', '/').replace('~0', '~')
        record = self.scripts.get(script)
        if not isinstance(record, dict):
            return None
        instructions = record.get('instructions', [])
        index = int(match.group(2))
        if index >= len(instructions):
            return None
        instruction = instructions[index]
        if not isinstance(instruction, dict):
            return None
        address = instruction.get('addr')
        if isinstance(address, str):
            return address
        if isinstance(address, int) and not isinstance(address, bool):
            return f'0x{address:08X}'
        return None

    def audit(self) -> dict:
        """Return a detached snapshot of actual resolutions and unique trigger groups."""
        groups = [self._trigger_groups[key] for key in sorted(self._trigger_groups)]
        return deepcopy({
            'resolve_calls': self._resolve_calls,
            'location_count': sum(self._geometry_counts.values()),
            'geometry_counts': dict(sorted(self._geometry_counts.items())),
            'issue_counts': dict(sorted(self._issue_counts.items())),
            'reason_counts': dict(sorted(self._reason_counts.items())),
            'trigger_groups': groups,
            'multi_tile_group_count': sum(len(group['tiles']) > 1 for group in groups),
        })
