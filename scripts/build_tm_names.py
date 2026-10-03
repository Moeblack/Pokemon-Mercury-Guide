# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Freeze native item sequence -> TM/HM slot -> move names for presentation."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
table = json.loads((ROOT.parent / 'wiki_export/core/data/tmhm.json').read_text(encoding='utf-8'))
items = json.loads((ROOT / 'data/items.json').read_text(encoding='utf-8'))['items']
slots = {row['slot']: row for row in table['entries']}
records = []
for item in items:
    if item['pocket']['symbol'] != 'TM_CASE':
        continue
    slot = item['unk19'] - 1
    move = slots[slot]
    raw = item['name']
    normalized = raw.replace('招式学习器', 'TM')
    if normalized != move['label']:
        raise ValueError(f'Item/slot mismatch: {item["index"]} {raw} {move["label"]}')
    records.append({'item_index': item['index'], 'item_id': item['item_id'], 'raw_name': raw,
                    'slot': slot, 'label': move['label'], 'move_id': move['move_id'],
                    'move_name': move['move_name'], 'display_name': move['label'] + ' · ' + move['move_name']})
if len(records) != table['count'] or len({row['slot'] for row in records}) != table['count']:
    raise ValueError('Incomplete or duplicated TM/HM item slots')
result = {'source': {'mapping': '../wiki_export/core/data/tmhm.json', 'items': 'data/items.json',
                     'join': 'TM_CASE item.unk19 - 1 = tmhm.slot', 'rom_move_table': '0x097E87AA'},
          'tm_count': table['num_tms'], 'hm_count': table['num_hms'], 'items': records}
(ROOT / 'data/tm_names.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'{table["num_tms"]} TM + {table["num_hms"]} HM names generated')
