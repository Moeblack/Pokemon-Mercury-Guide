# /// script
# requires-python = ">=3.10"
# dependencies = ["Markdown>=3.7"]
# ///
"""Render the player guide Markdown into a searchable, offline HTML guide."""
from pathlib import Path
import json, re, html, os
import markdown
from atlas_cards import AtlasCards, CSS as ATLAS_CSS
from tm_names import TMNames
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
<meta name="description" content="宝可梦水银1.1玩家攻略：查宝可梦获取地点、道具出处、支线任务步骤、训练家队伍与交互地图。">
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
    tm_names=TMNames(ROOT)
    for section in SECTIONS:
        for p in sorted((ROOT/section).rglob('*.md')):
            text=tm_names.markdown(p.read_text(encoding='utf-8-sig'))
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
            body += tm_names.markdown(atlas.cards(p))
            depth=len(p.relative_to(ROOT).parts)-1
            out=p.with_suffix('.html')
            out.write_text(shell(title,body,'../'*depth,section=section,is_index=p == ROOT/section/'index.md',mega=p == ROOT/'pokemon/wild_mega.md'),encoding='utf-8')
            if p.stem not in ('index','by_location','by_name','forms','special'):
                plain=re.sub(r'\[[^\]]*\]\([^)]*\)',lambda m:m.group(0).split(']')[0][1:],text)
                plain=re.sub(r'[`#*|>]|0x[0-9A-Fa-f]+',' ',plain)
                plain=re.sub(r'\s+',' ',plain)
                if section == 'items' and p.stem.isdigit():
                    plain += ' ' + tm_names.search_aliases(int(p.stem))
                records.append({'title':title,'section':section,'url':out.relative_to(ROOT).as_posix(),'text':plain})
    p=ROOT/'README.md'
    if p.exists():
        text=p.read_text(encoding='utf-8')
        rendered_text=re.sub(r'(\]\()([^\s)]+)(\))',rewrite,text)
        body=render_article(rendered_text)
        (ROOT/'README.html').write_text(shell('使用说明',body,''),encoding='utf-8')
    counts={k:sum(r['section']==k and Path(r['url']).stem.isdigit() for r in records) for k in SECTIONS}
    card_copy = {'pokemon': ('找宝可梦', '捕获地点、进化方式与不同形态。'), 'items': ('找道具', '获取地点、购买渠道与道具用途。'), 'quests': ('做支线', '从接取条件到步骤与报酬。'), 'trainers': ('准备对战', '先看对手的队伍、等级与配招。')}
    cards=''.join(f'<a class="browse-card" href="{k}/index.html"><span class="browse-number">0{i}</span><h3>{card_copy[k][0]} <span aria-hidden="true">↗</span></h3><p>{card_copy[k][1]}</p><small>{counts[k]:,} 条资料 · 浏览目录</small></a>' for i,k in enumerate(card_copy,1))
    filters = '<label><input type="radio" name="section" value="" checked>全部资料</label>' + ''.join(f'<label><input type="radio" name="section" value="{k}">{v}</label>' for k,v in SECTIONS.items())
    body = f'''<div class="home-hero"><div class="hero-copy"><p class="eyebrow"><span class="version-tag">水银 1.1</span></p><h1>宝可梦水银攻略</h1>
<form id="search-form" class="search-panel" role="search" aria-label="攻略搜索"><label for="q">搜索攻略</label><div class="searchbox"><input id="q" type="search" placeholder="宝可梦、道具、任务、训练家或地点" autocomplete="off" aria-describedby="search-help"><button class="search-submit" type="submit">搜索</button><button id="clear-search" type="button">重置</button></div><p id="search-help" class="muted">多个关键词用空格分隔，查找同时包含这些词的资料。</p><div id="random-search" class="quick-search" aria-label="随机词条" hidden><span>随机词条</span><span id="random-search-links"></span><button id="shuffle-search" type="button">换一组</button></div><fieldset><legend>搜索范围</legend><div class="section-options">{filters}</div></fieldset></form></div>
<a class="hero-map" href="maps/index.html"><div class="hero-map-image"><img src="maps/base/2f598d152e313dd7.png" width="1056" height="1024" alt="地图预览"><img class="hero-map-objects" src="maps/objects/3_76.png" width="1056" height="1024" alt=""></div><div class="hero-map-caption"><strong>地图图鉴 <span aria-hidden="true">→</span></strong><span>宝可梦 · 道具 · 任务 · 出入口</span></div></a></div>
<section class="search-output" aria-label="搜索结果"><div class="search-status"><p id="status" class="muted" role="status" aria-live="polite">输入关键词开始搜索，或浏览下方攻略。</p><a id="map-search-link" href="maps/index.html" hidden>在地图中找地点 →</a></div><div id="results"></div><button id="load-more" type="button" hidden>再显示60条</button></section>
<div id="cards"><div class="section-heading"><h2>攻略目录</h2></div><div class="browse-grid">{cards}</div><a class="mega-feature" href="pokemon/wild_mega.html"><div><h2>野生 Mega</h2><p>28种野生 Mega 的所在地与挑战记录。</p></div><span class="feature-arrow" aria-hidden="true">→</span></a></div>
<noscript><p>搜索需要启用JavaScript；仍可使用栏目导航和目录阅读全部攻略。</p></noscript><details class="guide-about"><summary>关于这份攻略</summary><p>对应水银1.1版本。资料中的“待补”表示条件尚未整理清楚。</p><a href="README.html">阅读资料说明</a> · <a href="data/delivery_summary.json">制作与覆盖记录</a></details>'''
    payload=json.dumps(records,ensure_ascii=False).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    (ROOT/'assets').mkdir(exist_ok=True)
    (ROOT/'assets/search-data.js').write_text('window.GUIDE_SEARCH_DATA = '+payload+';\n',encoding='utf-8')
    extra='<script defer src="assets/search-data.js"></script><script defer src="assets/search.js"></script>'
    (ROOT/'index.html').write_text(shell('首页',body,'',extra,home=True),encoding='utf-8')
    (ROOT/'data').mkdir(exist_ok=True)
    (ROOT/'data/site_summary.json').write_text(json.dumps({'counts':counts,'search_records':len(records),'homepage':'index.html'},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(counts,ensure_ascii=False))
if __name__=='__main__':main()
