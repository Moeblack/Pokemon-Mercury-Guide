/* Navigation presents places and player goals, never raw global event rows. */
window.createAtlasNavigation = function(api) {
  'use strict';
  const {state,maps,regions,points,manifest,quality,guideURL,onMap,onPoint,onState,pageMatch,mapPageMatch,normalize,badge} = api;
  const $ = id => document.getElementById(id);
  const el = (tag,text,cls) => { const n=document.createElement(tag); if(text!==undefined)n.textContent=text; if(cls)n.className=cls; return n; };
  const categories = {pokemon:'宝可梦',item:'道具',quest:'任务',trainer:'对战'};
  const category = p => p.kind==='mega' ? 'pokemon' : p.kind;
  const groups = rows => {
    const found=new Map();
    for(const p of rows){const key=JSON.stringify([p.kind,p.title,p.links?.[0]?.page||'']);if(!found.has(key))found.set(key,{title:p.title,kind:p.kind,rows:[]});found.get(key).rows.push(p);}
    return [...found.values()];
  };
  const geometry = p => p.geometry==='trigger'?'剧情触发区域':p.geometry==='point'?'有位置标记':p.geometry==='area'?'地图范围记录':'位置待定位';
  let viewKey = '', total = '';
  function action(text,fn,cls) {const b=el('button',text,cls);b.type='button';b.onclick=fn;return b;}
  function pointRow(p, title) {
    const b=action('',()=>onPoint(p),'result point-result');b.dataset.point=p.id;
    const text=el('span');text.append(el('strong',title||p.title),el('small',geometry(p)));
    if(p.kind==='mega'&&p.detail)text.append(el('small',p.detail.split('；').slice(0,2).join(' · ')));
    b.append(badge(p),text);return b;
  }
  function recordsList(rows) {
    const list=el('div',undefined,'record-choices');
    rows.forEach((p,i)=>list.append(pointRow(p,rows.length===1?p.title:`记录 ${i+1} · ${geometry(p)}`)));
    return list;
  }
  function subject(group, local=false) {
    if(local&&group.rows.length===1)return pointRow(group.rows[0]);
    const d=el('details',undefined,'subject-group');const s=el('summary');
    const destinations=new Map();for(const p of group.rows){if(!destinations.has(p.map_id))destinations.set(p.map_id,[]);destinations.get(p.map_id).push(p);}
    s.append(el('strong',group.title),el('small',local?`${group.rows.length} 条独立记录，展开选择`:`${destinations.size} 张地图 · ${group.rows.length} 条地点记录`));d.append(s);
    if(local)d.append(recordsList(group.rows));
    else for(const [id,rows]of destinations){const block=el('section',undefined,'destination-group');block.append(el('h4',maps[id]?.name||id),el('small',`地图 ${id} · ${quality(id).label}`));block.append(recordsList(rows));d.append(block);}
    if(group.rows.some(p=>p.id===state.point))d.open=true;
    return d;
  }
  function paged(parent, rows, make, size=12) {
    const list=el('div',undefined,'nav-page');const more=action('继续显示',append,'nav-more');parent.append(list,more);let shown=0;
    function append(){const end=Math.min(shown+size,rows.length);for(const row of rows.slice(shown,end))list.append(make(row));shown=end;const complete=shown>=rows.length;more.hidden=complete&&document.activeElement!==more;more.setAttribute('aria-disabled',String(complete));more.textContent=complete?'已显示全部':`再显示 ${Math.min(size,rows.length-shown)} 项 · 剩余 ${rows.length-shown} 项`;}
    append();
  }
  function empty(parent,title,body,recover) {const e=el('div',undefined,'nav-empty');e.append(el('h3',title),el('p',body));if(recover)e.append(action(recover.text,recover.fn));parent.append(e);}
  function mapCard(id) {
    const m=maps[id],b=action('',()=>onMap(id),'place-card map-result');b.dataset.map=id;
    const thumb=el('span',undefined,'place-thumbnail');
    const url=guideURL(m.image);
    if(url&&quality(id).label!=='无可用底图'){const img=el('img');img.src=url;img.alt='';img.loading='lazy';img.onerror=()=>{img.remove();thumb.textContent='底图待补';};thumb.append(img);}else thumb.textContent='底图待补';
    const label=el('span');label.append(el('strong',m.name||id),el('small',`地图 ${id} · ${m.width} × ${m.height}`));
    const q=quality(id);if(q.warning)label.append(el('small',q.label,'source-warning'));
    b.append(thumb,label);return b;
  }
  function mapGroups(parent, ids) {
    const names=new Map();for(const id of ids){const name=maps[id].raw_name||maps[id].name||id;if(!names.has(name))names.set(name,[]);names.get(name).push(id);}
    paged(parent,[...names],([name,members])=>{
      if(members.length===1)return mapCard(members[0]);
      const d=el('details',undefined,'place-group');const s=el('summary');s.append(el('strong',name),el('small',`${members.length} 张同名地图 · 展开比较缩略图`));d.append(s);
      d.addEventListener('toggle',()=>{if(d.open&&!d.dataset.loaded){const grid=el('div',undefined,'place-grid');for(const id of members)grid.append(mapCard(id));d.append(grid);d.dataset.loaded='1';}});
      return d;
    });
  }
  function localOverview(parent, rows) {
    const all=points.filter(p=>p.map_id===state.map&&p.kind!=='warp'&&pageMatch(p));
    if(state.topic!=='all'){
      parent.append(action('← 返回本地概览',()=>onState({topic:'all'}),'back-overview'),el('h3',`${categories[state.topic]}记录`,'nav-heading'));
      const subjectRows=groups(rows);
      if(!subjectRows.length)empty(parent,'尚未收录这类内容','没有记录不代表游戏里不存在。可查看其它类别或完整攻略。');
      else paged(parent,subjectRows,g=>subject(g,true));
      total=`本地图 · ${subjectRows.length} 个条目 / ${rows.length} 条地点记录`;return;
    }
    parent.append(el('p','先选感兴趣的内容，再在地图上定位。','nav-intro'));
    const tiles=el('div',undefined,'category-overview');
    for(const [key,label]of Object.entries(categories)){
      const subjects=groups(all.filter(p=>category(p)===key));const b=action('',()=>onState({topic:key}),'category-card');
      b.append(el('span',label),el('strong',String(subjects.length)),el('small',subjects.length?subjects.slice(0,2).map(g=>g.title).join('、'):'暂无收录'));
      tiles.append(b);
    }
    parent.append(tiles);
    const special=groups(all.filter(p=>p.kind==='mega'));
    if(special.length){parent.append(el('h3','野生 Mega 记录','nav-heading'));for(const g of special)parent.append(subject(g,true));}
    parent.append(action('看看从这里能去哪里 →',()=>onState({section:'exits'}),'nav-next'));
    total=`本地图 · ${groups(all).length} 个攻略条目`;
  }
  function exits(parent,rows) {
    parent.append(el('p','按目的地选择入口。这里只显示已有连接，不推断解锁条件或最短路线。','nav-intro'));
    const connections=(manifest.connection_edges||[]).filter(e=>e.source===state.map&&maps[e.target]);
    if(connections.length){parent.append(el('h3','相邻地图','nav-heading'));const seen=new Set();for(const e of connections){const k=e.target+':'+e.direction;if(seen.has(k))continue;seen.add(k);parent.append(action(`${{1:'南侧',2:'北侧',3:'西侧',4:'东侧'}[e.direction]||'连接'} · ${maps[e.target].name}`,()=>onMap(e.target),'neighbor-link'));}}
    const destinations=new Map();for(const p of rows){const key=p.target||p.id;if(!destinations.has(key))destinations.set(key,[]);destinations.get(key).push(p);}
    if(destinations.size)parent.append(el('h3','门、楼梯与传送入口','nav-heading'));
    paged(parent,[...destinations],([target,entries])=>{const d=el('details',undefined,'exit-group');const s=el('summary');s.append(el('strong',maps[target]?.name||entries[0].title),el('small',`${entries.length} 个入口${maps[target]?' · 地图 '+target:''}`));d.append(s);entries.forEach(p=>d.append(pointRow(p,`入口 ${api.number.get(p.id)} · ${p.reciprocal?'有对应回程':'回程关系见详情'}`)));return d;});
    if(!connections.length&&!destinations.size)empty(parent,'尚无可用入口记录','可以通过“换个地方”浏览其它地图。',{text:'换个地方',fn:()=>onState({section:'places'})});
    total=`${connections.length} 条相邻连接 · ${rows.length} 条入口记录`;
  }
  function places(parent) {
    const terms=normalize(state.mapQuery).trim().split(/\s+/).filter(Boolean);
    let ids=Object.keys(maps).filter(id=>mapPageMatch(id)&&terms.every(t=>normalize(`${maps[id].name} ${maps[id].raw_name||''} ${id}`).includes(t)));
    total=`${ids.length} 张地图 · 同名地图分组展示`;
    if(!ids.length){empty(parent,'没有找到这个地方','试试地图名称或编号。',{text:'清除地点搜索',fn:()=>onState({mapQuery:''})});return;}
    if(terms.length){mapGroups(parent,ids);return;}
    const nearby=(regions[maps[state.map]?.region]?.maps||[]).filter(id=>id!==state.map&&ids.includes(id));
    if(nearby.length){parent.append(el('h3','当前区域的其它地图','nav-heading'));mapGroups(parent,nearby);}
    const all=el('details',undefined,'all-places');all.append(el('summary',`浏览全部 ${ids.length} 张地图`));
    all.addEventListener('toggle',()=>{if(all.open&&!all.dataset.loaded){mapGroups(all,ids);all.dataset.loaded='1';}});parent.append(all);
    if(!nearby.length)all.open=true;
  }
  function find(parent,rows) {
    if(!state.query&&state.findType==='all'&&!state.page){
      empty(parent,'你想找什么？','输入宝可梦、道具、任务或训练家的名称；也可以输入地点，看看那里有哪些攻略。');
      const samples=['胡地','吃剩的东西','阿四'];const choices=el('div',undefined,'search-examples');for(const title of samples)choices.append(action(title,()=>onState({query:title})));parent.append(choices);total='搜索全库 · 先找目标，再选地点';return;
    }
    const subjects=groups(rows);const query=normalize(state.query);
    subjects.sort((a,b)=>Number(normalize(b.title)===query)-Number(normalize(a.title)===query)||Number(normalize(b.title).includes(query))-Number(normalize(a.title).includes(query)));
    if(!subjects.length)empty(parent,'没有找到匹配的攻略地点','可以换关键词、取消分类，或到攻略首页查完整正文。',{text:'清除攻略筛选',fn:()=>onState({query:'',findType:'all',page:''})});
    else {parent.append(el('p','先展开目标，再选择想去的地点；同一目标的不同获取记录分别保留。','nav-intro'));paged(parent,subjects,g=>{const d=subject(g);if(subjects.length<=3||normalize(g.title)===query)d.open=true;return d;});}
    const link=el('a','去攻略首页查完整正文 →','full-search-link');link.href='../index.html'+(state.query?'#q='+encodeURIComponent(state.query):'');parent.append(link);
    total=`${subjects.length} 个目标 · ${new Set(rows.map(p=>p.map_id)).size} 张地图 · ${rows.length} 条记录`;
  }
  function render(rows) {
    for(const b of document.querySelectorAll('[data-intent]')){const active=b.dataset.intent===state.intent;b.setAttribute('aria-selected',String(active));b.tabIndex=active?0:-1;}
    for(const b of document.querySelectorAll('[data-section]')){const active=b.dataset.section===state.section;b.setAttribute('aria-selected',String(active));b.tabIndex=active?0:-1;}
    $('browse-tabs').hidden=state.intent!=='browse';$('finder-types').hidden=state.intent!=='find';
    $('search-panel').hidden=state.intent==='browse'&&state.section!=='places';
    $('search-label').textContent=state.intent==='find'?'想找什么攻略？':'想去哪个地方？';
    $('search').placeholder=state.intent==='find'?'宝可梦、道具、任务、训练家…':'地图名称或编号…';
    const query=state.intent==='find'?state.query:state.mapQuery;if($('search').value!==query)$('search').value=query;
    for(const r of $('finder-types').querySelectorAll('input'))r.checked=r.value===state.findType;
    $('nav-place-name').textContent=state.intent==='find'?'查找攻略地点':maps[state.map]?.name||'选择地图';
    $('nav-context').textContent=state.intent==='find'?'查找全库攻略；展开目标选择地点':'围绕当前地图，查看内容或继续探索';
    $('page-scope').hidden=!state.page;
    const guide=api.guides?.[api.normalizePage(state.page)];$('page-scope').querySelector('span').textContent=state.page?`当前攻略：${guide?.title||state.page}`:'';
    $('view-purpose').textContent=state.intent==='find'?(state.query?`正在查找「${state.query}」· 地图显示匹配地点`:'查攻略：先搜索目标，再选择地点定位'):state.section==='exits'?'当前地图的出入口 · 选择入口可查看目的地':state.topic!=='all'?`当前地图 · ${categories[state.topic]}记录`:'当前地图概览 · 点击看点或地图标记了解详情';
    const key=JSON.stringify([state.intent,state.section,state.topic,state.findType,state.query,state.mapQuery,state.page,state.intent==='browse'?state.map:null]);
    if(key!==viewKey){viewKey=key;const parent=$('results');parent.replaceChildren();parent.scrollTop=0;
      if(state.intent==='find')find(parent,rows);else if(state.section==='places')places(parent);else if(state.section==='exits')exits(parent,rows);else localOverview(parent,rows);
    }
    $('count').textContent=total;
    for(const button of $('results').querySelectorAll('[data-point]'))if(button.dataset.point===state.point){for(let p=button.parentElement;p&&p!==$('results');p=p.parentElement)if(p.tagName==='DETAILS')p.open=true;}
  }
  return {render,category};
};
