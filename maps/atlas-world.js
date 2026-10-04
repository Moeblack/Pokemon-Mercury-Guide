window.createWorldPicker = function(api) {
  'use strict';
  const {state,maps,points,onState,onMap,guideURL} = api;
  const data=window.ATLAS_WORLD, $=id=>document.getElementById(id);
  const el=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
  const panel=$('world-picker'), selector=$('world-place'), stage=$('world-stage'), results=$('world-destinations');
  const sections=data.sections, sectionOf=new Map();
  const types={CITY:'城市',TOWN:'城镇',ROUTE:'道路',INDOOR:'建筑 / 设施',UNDERGROUND:'洞穴 / 地下',OCEAN_ROUTE:'水路'};
  for(const [id,section] of Object.entries(sections))for(const m of section.maps)sectionOf.set(m.id,id);
  for(const [id,section]of Object.entries(sections).sort((a,b)=>a[1].name.localeCompare(b[1].name,'zh'))){const option=el('option',section.name);option.value=id;selector.append(option);}
  const contentCounts=new Map();for(const p of points)if(p.kind!=='warp')contentCounts.set(p.map_id,(contentCounts.get(p.map_id)||0)+1);
  const outdoor=row=>['CITY','TOWN','ROUTE','OCEAN_ROUTE'].includes(row.type);
  function ordered(id){return (sections[id]?.maps||[]).filter(row=>maps[row.id]).slice().sort((a,b)=>{
    const am=maps[a.id],bm=maps[b.id];
    return Number(!!am.source_issue)-Number(!!bm.source_issue)||Number(!am.image||am.render_status==='unavailable')-Number(!bm.image||bm.render_status==='unavailable')||Number(outdoor(b))-Number(outdoor(a))||(contentCounts.get(b.id)||0)-(contentCounts.get(a.id)||0);
  });}
  function choose(id){const first=ordered(id)[0];if(first)onMap(first.id);}
  selector.onchange=()=>choose(selector.value);
  const ns='http://www.w3.org/2000/svg';
  const svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox',data.viewBox.join(' '));svg.setAttribute('aria-label','区域地图，选择城镇或道路');
  const image=document.createElementNS(ns,'image');image.setAttribute('href',guideURL(data.image));image.setAttribute('width','512');image.setAttribute('height','256');svg.append(image);
  const isTown=spot=>sections[spot.section].maps.some(row=>['CITY','TOWN'].includes(row.type)&&!maps[row.id]?.source_issue);
  for(const spot of data.hotspots.slice().sort((a,b)=>Number(isTown(a))-Number(isTown(b))||b.w*b.h-a.w*a.h)){
    const rect=document.createElementNS(ns,'rect');for(const key of ['x','y','w','h'])rect.setAttribute(({w:'width',h:'height'})[key]||key,spot[key]);
    rect.setAttribute('class','world-hotspot');rect.dataset.worldSection=spot.section;rect.setAttribute('tabindex','0');rect.setAttribute('role','button');rect.setAttribute('aria-label',sections[spot.section].name);
    const title=document.createElementNS(ns,'title');title.textContent=sections[spot.section].name;rect.append(title);
    rect.onclick=()=>choose(spot.section,true);rect.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose(spot.section,true);}};
    svg.append(rect);
  }
  stage.append(svg);
  function card(row){
    const m=maps[row.id],button=el('button',undefined,'place-card world-place-card');button.type='button';button.dataset.map=row.id;button.onclick=()=>onMap(row.id);
    const thumb=el('span',undefined,'place-thumbnail'),path=guideURL(m.image);if(path){const img=el('img');img.alt='';img.loading='lazy';img.src=path;img.onerror=()=>{img.remove();thumb.textContent='暂无图片';};thumb.append(img);}else thumb.textContent='暂无图片';
    const label=el('span');label.append(el('strong',m.name),el('small',types[row.type]||'场景'),el('small',row.id,'debug-only'));button.append(thumb,label);return button;
  }
  let last=null;
  const sceneSelect=$('scene-select');let sceneKey=null;
  sceneSelect.onchange=()=>onMap(sceneSelect.value);
  function render(){
    const open=state.screen==='world';panel.hidden=!open;document.body.classList.toggle('world-open',open);
    const sceneSection=sectionOf.get(state.map)||'',sceneRows=ordered(sceneSection);
    $('scene-switch').hidden=open||sceneRows.length<2;
    if(sceneSection!==sceneKey){sceneKey=sceneSection;sceneSelect.replaceChildren();sceneRows.forEach((row,i)=>{const option=el('option',`${maps[row.id].name} · ${types[row.type]||'场景'} ${i+1}${i===0?'（默认）':''}`);option.value=row.id;sceneSelect.append(option);});}
    sceneSelect.value=state.map||'';
    $('open-world').setAttribute('aria-pressed',String(open));$('return-scene').hidden=!open||!state.map;
    if(!open)return;
    $('map-title').textContent='游戏内地图';$('view-purpose').textContent='点击地点直接进入地图；同地点的其他场景可在进入后切换。';
    const id=state.worldSection||sectionOf.get(state.map)||'';selector.value=id;
    for(const rect of stage.querySelectorAll('.world-hotspot')){const selected=rect.dataset.worldSection===id;rect.classList.toggle('selected',selected);rect.setAttribute('aria-pressed',String(selected));}
    if(id===last)return;last=id;results.replaceChildren();
    const heading=el('h3',sections[id]?.name||'选择地点');heading.id='world-selection-title';heading.tabIndex=-1;results.append(heading);
    if(!sections[id]){results.append(el('p','点击总图上的城镇或道路即可进入。','muted'));return;}
    const rows=sections[id].maps.filter(row=>maps[row.id]);
    const primary=rows.filter(row=>['CITY','TOWN','ROUTE','OCEAN_ROUTE'].includes(row.type)&&!maps[row.id].source_issue);
    const others=rows.filter(row=>!primary.includes(row));
    const grid=el('div',undefined,'world-place-grid');for(const row of primary)grid.append(card(row));results.append(grid);
    if(others.length){const details=el('details',undefined,'world-other-places');details.append(el('summary',`建筑、洞穴与其他场景（${others.length}）`));const more=el('div',undefined,'world-place-grid');for(const row of others)more.append(card(row));details.append(more);details.open=!primary.length;results.append(details);}
  }
  function sceneName(id) {
    const rows=ordered(sectionOf.get(id)), index=rows.findIndex(row=>row.id===id);
    return index<0 ? maps[id]?.name||'目的地待确认' : `${maps[id].name} · ${types[rows[index].type]||'场景'} ${index+1}`;
  }
  return {render,sceneName,sectionFor:id=>sectionOf.get(id)||'',openSection:choose};
};
