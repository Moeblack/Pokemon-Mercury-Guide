# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow>=10"]
# ///
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit, parse_qs
from collections import Counter
import json, re
from PIL import Image
G=Path(__file__).resolve().parents[1]
expected={'quests':97,'items':750,'pokemon':1554,'trainers':743}
errors=[];counts={};links=0
manifest=json.loads((G/'data/atlas_manifest.json').read_text(encoding='utf-8'))
point_data=json.loads((G/'data/atlas_points.json').read_text(encoding='utf-8'))['points']
point_ids={p['id'] for p in point_data}
class Links(HTMLParser):
    def __init__(self):super().__init__();self.targets=[]
    def handle_starttag(self,tag,attrs):
        for k,v in attrs:
            if k in ('href','src') and v:self.targets.append(v)
def check(p,target):
    global links
    u=urlsplit(target)
    if u.scheme or u.netloc or not u.path:return
    links+=1
    dest=(p.parent/unquote(u.path)).resolve()
    if not dest.exists():errors.append({'page':p.relative_to(G).as_posix(),'target':target})
    if dest==G/'maps/index.html':
        params=parse_qs(u.fragment)
        if 'map' in params and params['map'][0] not in manifest['maps']:errors.append({'invalid_map_link':target})
        if 'point' in params and params['point'][0] not in point_ids:errors.append({'invalid_point_link':target})
        if 'page' in params and not (G/params['page'][0]).exists():errors.append({'invalid_page_filter':target})
for s,n in expected.items():
    ids={p.stem for p in (G/s).glob('*.md') if p.stem.isdigit()}
    htmlids={p.stem for p in (G/s).glob('*.html') if p.stem.isdigit()}
    counts[s]={'markdown':len(ids),'html':len(htmlids),'expected':n}
    if len(ids)!=n or ids!=htmlids:errors.append({'section':s,'coverage':counts[s]})
    for p in sorted((G/s).glob('*.html')):
        parser=Links();parser.feed(p.read_text(encoding='utf-8'))
        for t in parser.targets:check(p,t)
for name in ('index.html','README.html','maps/index.html'):
    p=G/name;parser=Links();parser.feed(p.read_text(encoding='utf-8'))
    for t in parser.targets:check(p,t)
home=(G/'index.html').read_text(encoding='utf-8')
payload=re.search(r'const DATA=(.*?);const q=',home,re.S)
records=json.loads(payload.group(1)) if payload else []
search_counts=dict(Counter(r['section'] for r in records if Path(r['url']).stem.isdigit()))
if search_counts!=expected:errors.append({'search_counts':search_counts,'expected':expected})
queries={q:[r['url'] for r in records if q in r['title']] for q in ('泥炭块','月月熊','阿四','红色火球','野生Mega')}
for q,rows in queries.items():
    if not rows:errors.append({'missing_search_title':q})
render=json.loads((G/'data/atlas_render_report.json').read_text(encoding='utf-8'))
images={r['image']:r for group in ('maps','regions') for r in render[group].values() if r['status']!='unavailable'}
for path,r in images.items():
    try:
        with Image.open(G/path) as image:
            if image.mode!='RGB' or list(image.size)!=r['size']:errors.append({'image':path,'mode':image.mode,'size':list(image.size),'expected':r['size']})
    except Exception as ex:errors.append({'image':path,'error':str(ex)})
for p in point_data:
    m=manifest['maps'].get(p['map_id'])
    if not m:errors.append({'point_missing_map':p['id']});continue
    if p['geometry']=='point' and not (0<=p['x']<m['width'] and 0<=p['y']<m['height']):errors.append({'point_out_of_bounds':p['id']})
card_pages=0
for page,rows in manifest['page_locations'].items():
    target=(G/page).with_suffix('.html')
    if not target.exists():errors.append({'missing_guide_page':page});continue
    if '<section class="atlas-cards">' not in target.read_text(encoding='utf-8'):errors.append({'missing_map_cards':page})
    else:card_pages+=1
mega=json.loads((G/'data/wild_mega_locations.json').read_text(encoding='utf-8'))['records']
if len(mega)!=28 or len({r['species_id'] for r in mega})!=28:errors.append({'mega_count':len(mega)})
for r in mega:
    for loc in r['locations']:
        if render['maps'][loc['map_id']]['status']=='unavailable':errors.append({'mega_map_unavailable':r['name'],'map':loc['map_id']})
report={'scope':'四类条目覆盖、生成页面本地链接与首页检索数据，不包含游戏运行验证','counts':counts,'local_links_checked':links,'search_counts':search_counts,'representative_search_titles':queries,'errors':errors}
report['atlas']={'rgb_images_checked':len(images),'points':len(point_data),'guide_pages_with_cards':card_pages,'mega_species':len(mega),'unavailable_maps':render['unavailable_maps'],'partial_maps':render['partial_maps']}
(G/'data/link_check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(1 if errors else 0)
