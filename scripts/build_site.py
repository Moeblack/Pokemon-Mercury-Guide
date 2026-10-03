# /// script
# requires-python = ">=3.10"
# dependencies = ["Markdown>=3.7"]
# ///
"""Render the player guide Markdown into a searchable, offline HTML guide."""
from pathlib import Path
import json, re, html, os
import markdown
from atlas_cards import AtlasCards, CSS as ATLAS_CSS
ROOT = Path(__file__).resolve().parents[1]
SECTIONS = {'quests':'支线攻略','items':'道具搜集','pokemon':'宝可梦获取','trainers':'训练家配队'}
CSS = '''*{box-sizing:border-box}body{margin:0;color:#243247;background:#f5f7fb;font:16px/1.8 system-ui,"Microsoft YaHei",sans-serif}header{background:#142b48;color:white;padding:22px max(22px,calc((100vw - 1180px)/2))}header a{color:#e5efff;text-decoration:none}nav{display:flex;gap:20px;flex-wrap:wrap;font-size:15px}main{max-width:1180px;margin:auto;padding:28px 22px 60px}h1{font-size:30px;line-height:1.4}h2{margin-top:32px;border-bottom:1px solid #d9e0eb;padding-bottom:8px}a{color:#155b9b}table{border-collapse:collapse;width:100%;font-size:14px;display:block;overflow:auto;background:white}td,th{padding:10px 12px;border:1px solid #dde4ed;text-align:left;min-width:65px}th{background:#eaf0f8}tr:nth-child(even){background:#f7f9fc}code{font-size:.88em;background:#edf0f5;padding:2px 4px;border-radius:3px;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere;padding:15px;background:#edf0f5}img{max-width:100%;height:auto;image-rendering:pixelated}blockquote{border-left:4px solid #809cbe;background:#edf2f8;margin:18px 0;padding:10px 18px}input,select{font:inherit;padding:10px 14px;border:1px solid #bccbdd;border-radius:7px}input{flex:1;min-width:180px}.searchbox{display:flex;gap:10px;flex-wrap:wrap;margin:20px 0}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:15px}.card{background:white;border:1px solid #dbe3ee;border-radius:10px;padding:20px}.result{background:white;margin:10px 0;padding:14px 18px;border-radius:7px;border:1px solid #e0e6ee}.result small,.muted{color:#60718a}.badge{background:#e7eff9;border-radius:4px;padding:2px 7px;font-size:13px}details{margin:15px 0}footer{margin-top:40px;border-top:1px solid #dde4ed;padding-top:15px;color:#60718a;font-size:13px}@media(max-width:600px){main{padding:16px 12px}h1{font-size:25px}td,th{padding:8px}}'''
CSS += ATLAS_CSS

def shell(title, body, relroot, extra=''):
    links=''.join(f'<a href="{relroot}{k}/index.html">{v}</a>' for k,v in SECTIONS.items())
    links += f'<a href="{relroot}maps/index.html">地点地图</a><a href="{relroot}pokemon/wild_mega.html">野生Mega</a>'
    return f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)} · 水银攻略</title><style>{CSS}</style><header><a href="{relroot}index.html"><strong>宝可梦水银 1.1 · 玩家攻略</strong></a><nav>{links}</nav></header><main>{body}<footer>资料依据指定水银1.1 ROM及解包记录。正文的“待补”表示该获取条件尚未整理清楚，不代表无法获得。</footer></main>{extra}</html>'

def main():
    records=[]
    atlas=AtlasCards(ROOT)
    for section in SECTIONS:
        for p in sorted((ROOT/section).rglob('*.md')):
            text=p.read_text(encoding='utf-8-sig')
            match=re.search(r'^#\s+(.+)',text,re.M)
            title=match.group(1) if match else p.stem
            # Rewrite only guide Markdown links with existing local targets. Evidence links remain unchanged.
            def rewrite(m):
                dest=m.group(2)
                dest=atlas.rewrite_map(dest,p) or dest
                pathpart=dest.split('#')[0]
                if pathpart.endswith('.md') and not re.match(r'https?://',dest):
                    target=(p.parent/pathpart).resolve()
                    if target.is_relative_to(ROOT) and target.exists():
                        dest=dest.replace('.md','.html',1)
                return m.group(1)+dest+m.group(3)
            rendered_text=re.sub(r'(\]\()([^\s)]+)(\))',rewrite,text)
            rendered_text=rendered_text.replace('<details>','<details markdown="1">')
            body=markdown.markdown(rendered_text,extensions=['tables','fenced_code','sane_lists','toc','md_in_html'])
            body += atlas.cards(p)
            depth=len(p.relative_to(ROOT).parts)-1
            out=p.with_suffix('.html')
            out.write_text(shell(title,body,'../'*depth),encoding='utf-8')
            if p.stem not in ('index','by_location','by_name','forms','special'):
                plain=re.sub(r'\[[^\]]*\]\([^)]*\)',lambda m:m.group(0).split(']')[0][1:],text)
                plain=re.sub(r'[`#*|>]|0x[0-9A-Fa-f]+',' ',plain)
                plain=re.sub(r'\s+',' ',plain)
                records.append({'title':title,'section':section,'url':out.relative_to(ROOT).as_posix(),'text':plain})
    p=ROOT/'README.md'
    if p.exists():
        text=p.read_text(encoding='utf-8')
        rendered_text=re.sub(r'(\]\()([^\s)]+)(\))',rewrite,text)
        body=markdown.markdown(rendered_text,extensions=['tables','fenced_code','sane_lists'])
        (ROOT/'README.html').write_text(shell('使用说明',body,''),encoding='utf-8')
    counts={k:sum(r['section']==k and Path(r['url']).stem.isdigit() for r in records) for k in SECTIONS}
    cards=''.join(f'<div class="card"><h2><a href="{k}/index.html">{v}</a></h2><p>{counts[k]} 个条目</p><a href="{k}/index.html">打开目录</a></div>' for k,v in SECTIONS.items())
    body='<h1>想找什么？直接输入名称或地点</h1><p>查任务步骤、道具出处、捕获地点与对手队伍。也可以按下方四个目录浏览。</p><div class="searchbox"><input id="q" placeholder="例如：红色火球、泥炭块、月月熊、阿四"><select id="section"><option value="">全部资料</option>'+''.join(f'<option value="{k}">{v}</option>' for k,v in SECTIONS.items())+'</select></div><div id="status" class="muted"></div><div id="results"></div><div id="cards" class="cards">'+cards+'</div><p><a href="README.md">阅读资料说明</a> · <a href="data/delivery_summary.json">制作与覆盖记录</a></p>'
    body=body.replace('href="README.md"','href="README.html"')
    body='<div class="atlas-feature"><strong>新增地图攻略：</strong> <a href="pokemon/wild_mega.html">28种野生Mega所在地</a> · <a href="maps/index.html#map=3:76">打开RGB区域大地图</a></div>'+body
    payload=json.dumps(records,ensure_ascii=False).replace('</','<\\/')
    js='''<script>const DATA=PAYLOAD;const q=document.querySelector('#q'),sel=document.querySelector('#section');function esc(s){return s.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}function update(){const terms=q.value.toLowerCase().trim().split(/\\s+/).filter(Boolean),sec=sel.value;document.querySelector('#cards').style.display=terms.length||sec?'none':'grid';if(!terms.length&&!sec){document.querySelector('#results').innerHTML='';document.querySelector('#status').textContent='';return;}let hits=DATA.filter(x=>(!sec||x.section===sec)&&terms.every(t=>(x.title+' '+x.text).toLowerCase().includes(t)));hits.sort((a,b)=>Number(terms.every(t=>b.title.toLowerCase().includes(t)))-Number(terms.every(t=>a.title.toLowerCase().includes(t))));document.querySelector('#status').textContent='找到 '+hits.length+' 项，显示前100项；输入更具体的名称可缩小范围。';document.querySelector('#results').innerHTML=hits.slice(0,100).map(x=>'<div class="result"><a href="'+x.url+'"><strong>'+esc(x.title)+'</strong></a><br><small>'+esc(x.text.slice(0,190))+'</small></div>').join('');}q.addEventListener('input',update);sel.addEventListener('change',update);</script>'''.replace('PAYLOAD',payload)
    (ROOT/'index.html').write_text(shell('首页',body,'',js),encoding='utf-8')
    (ROOT/'data').mkdir(exist_ok=True)
    (ROOT/'data/site_summary.json').write_text(json.dumps({'counts':counts,'search_records':len(records),'homepage':'index.html'},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(counts,ensure_ascii=False))
if __name__=='__main__':main()
