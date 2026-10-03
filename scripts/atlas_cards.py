"""Shared map cards: one frozen data load, reusable RGB images, vector markers."""
from pathlib import Path
from urllib.parse import quote
import json,html,os,re
CSS='''
.atlas-cards{margin:32px 0;padding-top:8px;border-top:1px solid #d9e0eb}.atlas-card-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,260px),1fr));gap:16px}.atlas-card{background:#fff;border:1px solid #d9e0eb;border-radius:10px;overflow:hidden}.atlas-card h3{font-size:16px;margin:12px 14px 6px}.atlas-card p{font-size:13px;line-height:1.6;margin:8px 14px 14px}.atlas-frame{height:240px;position:relative;background:#e8edf1}.atlas-frame img{position:absolute;width:100%;height:100%;object-fit:contain;image-rendering:pixelated}.atlas-frame svg{position:absolute;width:100%;height:100%;inset:0;pointer-events:none}.atlas-label{paint-order:stroke;stroke:#fff;stroke-width:3px;fill:#142b48;font-weight:bold;text-anchor:middle;dominant-baseline:central}.atlas-cards details{margin-top:16px}.atlas-cards summary{cursor:pointer;color:#155b9b;margin-bottom:12px}.atlas-feature{padding:12px 16px;background:#eaf0f8;border-radius:8px;margin:16px 0}.atlas-unavailable{height:240px;display:grid;place-items:center;color:#59677a;font-size:14px;padding:24px;text-align:center}
'''
class AtlasCards:
 def __init__(self,root):
  self.root=Path(root);self.manifest={};self.points={};self.render={}
  path=self.root/'data/atlas_manifest.json'
  if path.exists():
   self.manifest=json.loads(path.read_text(encoding='utf-8'))
   self.points={p['id']:p for p in json.loads((self.root/'data/atlas_points.json').read_text(encoding='utf-8'))['points']}
   r=self.root/'data/atlas_render_report.json'
   if r.exists():self.render=json.loads(r.read_text(encoding='utf-8'))
 def rel(self,target,page):return os.path.relpath(self.root/target,page.parent).replace('\\','/')
 def viewer(self,mid,page,pid=None):
  url=self.rel('maps/index.html',page)+'#map='+quote(mid,safe=':')+'&page='+quote(page.relative_to(self.root).as_posix(),safe='/')
  return url+('&point='+quote(pid) if pid else '')
 def rewrite_map(self,dest,page):
  m=re.search(r'(?:world/pages/maps|maps/png)/g(\d{2})_n(\d{3})\.(md|png)',dest)
  if not m or not self.manifest:return None
  mid=f'{int(m[1])}:{int(m[2])}'
  if mid not in self.manifest['maps']:return None
  if m[3]=='png':
   r=self.render.get('maps',{}).get(mid,{})
   if r.get('status') not in ('ok','partial'):return self.viewer(mid,page)
   return self.rel(r['image'],page)
  return self.viewer(mid,page)
 def cards(self,page):
  key=page.relative_to(self.root).as_posix();locations=self.manifest.get('page_locations',{}).get(key,[])
  if not locations:return ''
  cards=[]
  colors={'mega':'#b45309','quest':'#155b9b','item':'#157347','pokemon':'#6d28d9','trainer':'#a21caf'}
  for row in locations:
   mid=row['map_id'];m=self.manifest['maps'][mid];r=self.render.get('maps',{}).get(mid,{})
   pts=[self.points[p] for p in row['point_ids'] if p in self.points];placed=[p for p in pts if p['geometry'] in ('point','trigger')];link=self.viewer(mid,page,placed[0]['id'] if placed else None)
   title=html.escape(m['name']);body=f'<article class="atlas-card"><h3><a href="{html.escape(link,quote=True)}">{title}</a></h3>'
   if r.get('status') in ('ok','partial'):
    w,h=m['width']*16,m['height']*16;src=self.rel(r['image'],page)
    body+=f'<a href="{html.escape(link,quote=True)}" aria-label="在大地图中打开{title}"><div class="atlas-frame"><img src="{html.escape(src,quote=True)}" alt="{title}地图" loading="lazy" decoding="async" width="{w}" height="{h}">'
    if m.get('objects_image'):
     body+=f'<img src="{html.escape(self.rel(m["objects_image"],page),quote=True)}" alt="建筑与大型固定对象" loading="lazy" decoding="async" width="{w}" height="{h}">'
    body+=f'<svg viewBox="0 0 {w} {h}" aria-hidden="true">'
    radius=max(w/50,h/36,8);used=set();shown=[]
    for p in placed:
     xy=(p['x'],p['y'])
     if xy in used:continue
     used.add(xy);shown.append(p)
     if len(shown)>36:break
     x,y=p['x']*16+8,p['y']*16+8;color=colors.get(p['kind'],'#155b9b')
     if p['geometry']=='trigger':
      for tx,ty in p['trigger_tiles']:body+=f'<rect x="{tx*16}" y="{ty*16}" width="16" height="16" fill="#8650a340" stroke="#8650a3"/>'
     body+=f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{color}" stroke="white" stroke-width="{max(2,radius/5)}"/><text x="{x}" y="{y}" fill="white" font-family="sans-serif" font-weight="bold" font-size="{radius*1.3}" text-anchor="middle" dominant-baseline="central">{len(shown)}</text>'
    body+='</svg></div></a>'
    if shown:
     text='；'.join(f"{n} {p['title']}（"+(f"剧情触发区，{len(p['trigger_tiles'])}格" if p['geometry']=='trigger' else f"{p['x']},{p['y']}")+"）" for n,p in enumerate(shown[:6],1))
     if len(shown)>6:text+='；其余标记请打开大地图'
    else:text='地图范围记录：当前资料没有精确人物／遭遇坐标。'
    if r.get('missing_tiles'):text+=f" 底图有{r['missing_tiles']}个图块缺少原始数据。"
    body+='<p>'+html.escape(text)+'</p>'
   else:body+='<div class="atlas-unavailable">该地图的原始图块数据不可解码，保留地点与入口导航。</div>'
   if m.get('source_issue'):body+='<p>'+html.escape(m['source_issue']['note'])+'</p>'
   if r.get('object_errors'):body+='<p>部分大型固定对象的图形或调色板尚未解析，未绘制到对象层；详见地图说明。</p>'
   body+=f'<p><a href="{html.escape(link,quote=True)}">放大定位与查看相邻入口 →</a></p></article>';cards.append(body)
  first='<div class="atlas-card-grid">'+''.join(cards[:6])+'</div>'
  rest=('<details><summary>展开其余 '+str(len(cards)-6)+' 张地点地图</summary><div class="atlas-card-grid">'+''.join(cards[6:])+'</div></details>') if len(cards)>6 else ''
  return '<section class="atlas-cards"><h2>地点地图</h2><p>共享RGB底图；点击可缩放定位。数字对应本页相关地点，不代表地图上全部事件。</p>'+first+rest+'</section>'
