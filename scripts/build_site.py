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


def shell(title, body, relroot, extra='', section='', is_index=False, home=False, mega=False):
    navigation = [(k, f'{k}/index.html', v) for k, v in SECTIONS.items()]
    navigation += [('maps', 'maps/index.html', '地点地图'), ('mega', 'pokemon/wild_mega.html', '野生Mega')]
    active = 'mega' if mega else section
    links = ''.join(f'<a href="{relroot}{url}"' + (' aria-current="page"' if key == active else '') + f'>{label}</a>' for key, url, label in navigation)
    crumbs = '<span aria-current="page">首页</span>' if home else f'<a href="{relroot}index.html">首页</a>'
    if not home:
        if section and not is_index:
            crumbs += f'<span aria-hidden="true"> / </span><a href="{relroot}{section}/index.html">{SECTIONS[section]}</a>'
        crumbs += f'<span aria-hidden="true"> / </span><span aria-current="page">{html.escape(SECTIONS[section] if section and is_index else title)}</span>'
    return f'''<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} · 水银攻略</title>
<link rel="stylesheet" href="{relroot}assets/guide.css"><style>{ATLAS_CSS}</style>
<script defer src="{relroot}assets/guide.js"></script>{extra}</head>
<body><a class="skip-link" href="#main-content">跳到主要内容</a>
<header class="site-header"><a class="brand" href="{relroot}index.html"><strong>宝可梦水银 1.1 · 玩家攻略</strong></a><nav aria-label="主要导航">{links}</nav></header>
<main id="main-content" tabindex="-1"><nav class="breadcrumbs" aria-label="面包屑">{crumbs}</nav>
<article class="{'home-content' if home else 'article-content'}">{body}</article>
<footer>资料依据指定水银1.1 ROM及解包记录。正文的“待补”表示该获取条件尚未整理清楚，不代表无法获得。</footer></main>
<button id="back-to-top" type="button" hidden>返回顶部</button></body></html>'''


def render_article(text):
    md = markdown.Markdown(extensions=['tables','fenced_code','sane_lists','toc','md_in_html'])
    body = md.convert(text)
    headings = []
    def collect(tokens):
        for token in tokens:
            if token['level'] in (2, 3) and token.get('id'):
                headings.append(token)
            collect(token.get('children', []))
    collect(md.toc_tokens)
    if len(headings) >= 3:
        links = ''.join(f'<li class="chapter-level-{t["level"]}"><a href="#{html.escape(t["id"], quote=True)}">{html.escape(html.unescape(re.sub("<[^>]+>", "", t["name"])))}</a></li>' for t in headings)
        toc = f'<details class="chapter-nav"><summary>本页目录</summary><ul>{links}</ul></details>'
        title_end = re.search(r'</h1>', body)
        if title_end:
            body = body[:title_end.end()] + toc + body[title_end.end():]
        else:
            body = toc + body
    return re.sub(r'<table>(.*?)</table>', r'<div class="table-scroll" role="region" tabindex="0" aria-label="攻略表格，可横向滚动"><table>\1</table></div>', body, flags=re.S)


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
                if pathpart.endswith('.md') and not re.match(r'(?:[a-z][a-z0-9+.-]*:|//)',dest,re.I):
                    target=(p.parent/pathpart).resolve()
                    if target.is_relative_to(ROOT) and target.exists():
                        dest=dest.replace('.md','.html',1)
                return m.group(1)+dest+m.group(3)
            rendered_text=re.sub(r'(\]\()([^\s)]+)(\))',rewrite,text)
            rendered_text=rendered_text.replace('<details>','<details markdown="1">')
            body=render_article(rendered_text)
            body += atlas.cards(p)
            depth=len(p.relative_to(ROOT).parts)-1
            out=p.with_suffix('.html')
            out.write_text(shell(title,body,'../'*depth,section=section,is_index=p == ROOT/section/'index.md',mega=p == ROOT/'pokemon/wild_mega.md'),encoding='utf-8')
            if p.stem not in ('index','by_location','by_name','forms','special'):
                plain=re.sub(r'\[[^\]]*\]\([^)]*\)',lambda m:m.group(0).split(']')[0][1:],text)
                plain=re.sub(r'[`#*|>]|0x[0-9A-Fa-f]+',' ',plain)
                plain=re.sub(r'\s+',' ',plain)
                records.append({'title':title,'section':section,'url':out.relative_to(ROOT).as_posix(),'text':plain})
    p=ROOT/'README.md'
    if p.exists():
        text=p.read_text(encoding='utf-8')
        rendered_text=re.sub(r'(\]\()([^\s)]+)(\))',rewrite,text)
        body=render_article(rendered_text)
        (ROOT/'README.html').write_text(shell('使用说明',body,''),encoding='utf-8')
    counts={k:sum(r['section']==k and Path(r['url']).stem.isdigit() for r in records) for k in SECTIONS}
    cards=''.join(f'<section class="card"><h2><a href="{k}/index.html">{v}</a></h2><p>{counts[k]} 个条目</p><a href="{k}/index.html">打开目录</a></section>' for k,v in SECTIONS.items())
    filters = '<label><input type="radio" name="section" value="" checked>全部资料</label>' + ''.join(f'<label><input type="radio" name="section" value="{k}">{v}</label>' for k,v in SECTIONS.items())
    body = f'''<div class="home-heading"><p class="eyebrow">水银 1.1 · 离线攻略</p><h1>查攻略，从名称或地点开始</h1><p>查任务步骤、道具出处、捕获地点与对手队伍，也可以按目录浏览。</p></div>
<div class="atlas-feature"><strong>地图与野生Mega：</strong> <a href="pokemon/wild_mega.html">28种野生Mega所在地</a> · <a href="maps/index.html#map=3:76">打开RGB区域大地图</a></div>
<section class="search-panel" aria-label="攻略搜索"><label for="q">搜索名称、地点或关键词</label><div class="searchbox"><input id="q" type="search" placeholder="例如：红色火球、泥炭块、月月熊、阿四" autocomplete="off" aria-describedby="search-help"><button id="clear-search" type="button">清除筛选</button></div><p id="search-help" class="muted">多个关键词用空格分隔，将查找同时包含这些词的资料。</p><fieldset><legend>筛选栏目</legend><div class="section-options">{filters}</div></fieldset></section>
<p id="status" class="muted" role="status" aria-live="polite">输入关键词或选择栏目开始搜索，也可浏览下方目录。</p><div id="results"></div><button id="load-more" type="button" hidden>再显示60条</button>
<div id="cards" class="cards">{cards}</div><noscript><p>搜索需要启用JavaScript；仍可使用上方栏目导航或目录阅读全部攻略。</p></noscript><p><a href="README.html">阅读资料说明</a> · <a href="data/delivery_summary.json">制作与覆盖记录</a></p>'''
    payload=json.dumps(records,ensure_ascii=False).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    (ROOT/'assets').mkdir(exist_ok=True)
    (ROOT/'assets/search-data.js').write_text('window.GUIDE_SEARCH_DATA = '+payload+';\n',encoding='utf-8')
    extra='<script defer src="assets/search-data.js"></script><script defer src="assets/search.js"></script>'
    (ROOT/'index.html').write_text(shell('首页',body,'',extra,home=True),encoding='utf-8')
    (ROOT/'data').mkdir(exist_ok=True)
    (ROOT/'data/site_summary.json').write_text(json.dumps({'counts':counts,'search_records':len(records),'homepage':'index.html'},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(counts,ensure_ascii=False))
if __name__=='__main__':main()
