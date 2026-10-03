# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Reference world graphic/hotspots, joined only by native ROM map section IDs."""
from pathlib import Path
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT.parent
reference = RESEARCH / 'reference/azoth-wiki/docs/locations'
ref = json.loads((reference / 'worldmap_data.json').read_text(encoding='utf-8'))
native = json.loads((RESEARCH / 'wiki_export/world/data/maps.json').read_text(encoding='utf-8'))
manifest = json.loads((ROOT / 'data/atlas_manifest.json').read_text(encoding='utf-8'))
sections = {}
for row in native:
    map_id = row['id']
    if map_id not in manifest['maps']:
        continue
    section = str(row['region_map_section_id'])
    name = row['map_name_zh']
    if section in ref['secNames'] and ref['secNames'][section] != name:
        raise ValueError(f'Reference/native section name mismatch: {section}')
    record = sections.setdefault(section, {'name': name, 'maps': []})
    record['maps'].append({'id': map_id, 'type': row['map_type_name']})
hotspots = []
for cell in ref['grids']['world']:
    section = str(cell['mapsec'])
    if section not in sections:
        continue
    # These calibration values are copied from reference worldmap.html CONFIG.
    hotspots.append({'section': section, 'x': (-0.8 + cell['x'] * 75.8 / 97) * 512 / 100,
                     'y': (-1.6 + cell['y'] * 62.5 / 40) * 256 / 100,
                     'w': cell['w'] * 75.8 / 97 * 512 / 100,
                     'h': cell['h'] * 62.5 / 40 * 256 / 100})
output = ROOT / 'maps/world'
output.mkdir(exist_ok=True)
shutil.copy2(reference / 'worldmap.png', output / 'region.png')
data = {'image': 'maps/world/region.png', 'viewBox': [16, 0, 376, 160], 'sections': sections, 'hotspots': hotspots,
        'source': {'graphic_and_hotspots': 'reference/azoth-wiki/docs/locations/worldmap.png + worldmap_data.json + worldmap.html CONFIG',
                   'map_membership': 'wiki_export/world/data/maps.json region_map_section_id',
                   'semantics': 'Reference graphic; map membership from native ROM export; not a new ROM graphic extraction.'}}
text = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\u003c')
(ROOT / 'maps/world-data.js').write_text('window.ATLAS_WORLD=' + text + ';\n', encoding='utf-8')
print(f'{len(sections)} sections, {len(hotspots)} hotspots')
