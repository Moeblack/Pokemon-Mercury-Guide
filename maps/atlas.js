(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const data = window.ATLAS || {};
  const manifest = data.manifest || {}, maps = manifest.maps || {}, regions = manifest.regions || {};
  const kinds = {mega:'野生 Mega', quest:'任务', item:'道具', pokemon:'普通宝可梦', trainer:'训练家', warp:'出入口'};
  const rawPoints = Array.isArray(data.points) ? data.points : (data.points || {}).points || [];
  const points = rawPoints.map(p => ({...p, id:String(p.id), target:p.target || p.target_map}));
  // Warps are navigation only: never infer their coordinates or spatial connection.
  for (const [id, map] of Object.entries(maps)) {
    for (const [index, warp] of (Array.isArray(map.warps) ? map.warps : []).entries()) {
      if (!warp || typeof warp.target !== 'string') continue;
      if (points.some(p => p.map_id === id && p.kind === 'warp' && p.x === warp.x && p.y === warp.y && p.target === warp.target)) continue;
      points.push({id:`atlas-warp:${id}:${index}`, map_id:id, kind:'warp', title:warp.label || `前往 ${maps[warp.target]?.name || warp.target}`, geometry:Number.isFinite(warp.x) && Number.isFinite(warp.y) ? 'point' : 'area', x:warp.x, y:warp.y, target:warp.target, detail:'出入口仅提供地图间导航，不表示两张地图处于同一平面。', links:[]});
    }
  }
  const byId = new Map(points.map(p => [p.id, p]));
  const number = new Map(), mapCounts = new Map();
  for (const p of points) {
    const count = (mapCounts.get(p.map_id) || 0) + 1;
    mapCounts.set(p.map_id, count); number.set(p.id, count);
  }
  const viewport = $('viewport'), world = $('world'), markers = $('markers');
  document.querySelector('.skip-link').onclick = event => { event.preventDefault(); $('map-content').focus({preventScroll:false}); };
  const state = {map:null, point:null, page:'', mode:'map', screen:'world', worldSection:'', intent:'browse', section:'local', topic:'all', findType:'all', query:'', mapQuery:'', scale:1, tx:0, ty:0, tiles:[], bounds:null};
  const tileNodes = new Map(), markerNodes = new Map();
  let frame = 0, filtered = [], lastFocus = null;
  let writtenHash = null, searchTimer = 0, composing = false;
  const normalize = value => String(value || '').normalize('NFKC').toLocaleLowerCase();
  const searchText = new Map(points.map(p => [p.id, normalize(`${p.title || ''} ${p.detail || ''} ${(p.search_aliases || []).join(' ')} ${p.map_id} ${maps[p.map_id]?.name || ''}`)]));
  function quality(id) {
    const m = maps[id], report = data.render?.maps?.[id];
    if (report?.status === 'unavailable' || m?.render_status === 'unavailable') return {label:'无可用底图', warning:true};
    if (m?.source_issue) return {label:'来源异常 / 同名布局', warning:true};
    if (report?.status === 'partial' || m?.render_status === 'partial') return {label:'局部图块缺失', warning:true};
    if (report?.status === 'ok' || m?.render_status === 'ok') return {label:'图块可解码', warning:false};
    return {label:'渲染状态待确认', warning:true};
  }
  function setNavigation(patch) {
    const fromResults = $('results').contains(document.activeElement);
    clearTimeout(searchTimer);
    if (('query' in patch && patch.query !== state.query) || ('findType' in patch && patch.findType !== state.findType)) { state.point = null; $('detail').hidden = true; }
    Object.assign(state, patch);
    if (state.intent === 'browse' && (patch.section === 'places' || !state.map)) { state.screen = 'world'; state.section = 'places'; }
    else if (state.map && (patch.section === 'local' || patch.section === 'exits' || patch.intent === 'find')) selectMap(state.map, false);
    refreshResults(); writeHash();
    if (fromResults) $('results').focus({preventScroll:true});
  }
  function clearFilters() {
    setNavigation(state.intent === 'find' ? {query:'',findType:'all',page:''} : {mapQuery:''}); $('search').focus();
  }
  function element(tag, text, cls) { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; if (cls) e.className = cls; return e; }
  function badge(p) { return element('span', String(number.get(p.id)), `badge ${kinds[p.kind] ? p.kind : 'quest'}`); }
  function guideURL(page) {
    if (typeof page !== 'string' || !page || /^(?:[a-z]+:|[\/\\])|(?:^|[\/\\])\.\.(?:[\/\\]|$)/i.test(page)) return null;
    return '../' + page.replace(/\\/g, '/').replace(/\.md(?=($|#|\?))/i, '.html');
  }
  function normalizePage(page) { return String(page || '').replace(/^\.\//, '').replace(/\.html(?=($|#|\?))/i, '.md').split('#')[0]; }
  function pageMatch(p) {
    if (!state.page) return true;
    const page = normalizePage(state.page);
    const locations = (manifest.page_locations || {})[page] || [];
    return locations.some(loc => (loc.point_ids || []).includes(p.id)) || (p.links || []).some(link => normalizePage(link.page) === page);
  }
  function mapPageMatch(id) {
    if (!state.page) return true;
    const locations = (manifest.page_locations || {})[normalizePage(state.page)] || [];
    return locations.some(loc => loc.map_id === id) || points.some(p => p.map_id === id && pageMatch(p));
  }
  function placed(p) {
    const m = maps[p.map_id];
    return ['point','trigger'].includes(p.geometry) && m && Number.isFinite(p.x) && Number.isFinite(p.y) && p.x >= 0 && p.y >= 0 && p.x < m.width && p.y < m.height;
  }
  function geometryLabel(p) { return p.geometry === 'trigger' ? `走入标出的 ${p.trigger_tiles.length} 格区域可触发对应事件；不是宝可梦站立位置，剧情条件仍需满足。` : placed(p) ? `已标出这条记录的位置，可在地图上查看。` : p.geometry === 'area' ? '资料只定位到这张地图，没有精确站位；请结合下方攻略寻找。' : '这条记录的具体位置尚未确定，可先阅读关联攻略。'; }
  const navigation = window.createAtlasNavigation({state,maps,regions,points,manifest,quality,guideURL,pageMatch,mapPageMatch,normalize,badge,number,guides:data.guides,normalizePage,
    onPoint:p=>selectPoint(p), onState:setNavigation,
    onMap:chooseMap, onWorld:openWorldPicker, onArea:id=>worldPicker.openSection(id)
  });
  const worldPicker = window.createWorldPicker({state,maps,points,guideURL,onState:setNavigation,onMap:chooseMap});
  function chooseMap(id) { state.point=null; $('detail').hidden=true; Object.assign(state,{intent:'browse',section:'local',topic:'all'}); selectMap(id); refreshResults(); viewport.focus({preventScroll:false}); }
  function openWorldPicker() { state.point=null; $('detail').hidden=true; Object.assign(state,{screen:'world',intent:'browse',section:'places'}); refreshResults(); writeHash(true); $('world-place').focus({preventScroll:false}); }
  $('open-world').onclick = openWorldPicker;
  $('return-scene').onclick = () => { if (state.map) { state.section='local'; selectMap(state.map); refreshResults(); viewport.focus({preventScroll:false}); } };
  for (const [kind, label] of Object.entries(kinds)) {
    const key = element('span'); key.append(element('span', '·', `badge ${kind}`), document.createTextNode(label)); $('legend').append(key);
  }
  $('debug-mode').onchange = () => { document.body.classList.toggle('debug-mode', $('debug-mode').checked); schedule(); writeHash(); };
  function writeHash(push = false) {
    const hash = new URLSearchParams();
    if (state.map) hash.set('map', state.map);
    if (state.point) hash.set('point', state.point);
    if (state.page) hash.set('page', state.page);
    if (state.query) hash.set('q', state.query);
    hash.set('mode', state.mode);
    hash.set('intent',state.intent);
    if (state.section !== 'local') hash.set('view',state.section);
    if (state.topic !== 'all') hash.set('topic',state.topic);
    if (state.findType !== 'all') hash.set('kind',state.findType);
    if (state.mapQuery) hash.set('placeq',state.mapQuery);
    if (!$('show-markers').checked) hash.set('markers', '0');
    if (!$('boundaries').checked) hash.set('labels', '0');
    if ($('debug-mode').checked) hash.set('debug', '1');
    if (state.screen === 'world') hash.set('screen','world');
    if (state.worldSection) hash.set('area',state.worldSection);
    const value = '#' + hash.toString();
    if (location.hash === value) return;
    try { history[push ? 'pushState' : 'replaceState'](null, '', value); }
    catch { writtenHash = value; if (push) location.hash = value; else location.replace(value); }
  }
  function readHash() {
    if (writtenHash === location.hash) { writtenHash = null; return; }
    clearTimeout(searchTimer);
    const hash = new URLSearchParams(location.hash.slice(1));
    const point = byId.get(hash.get('point')), previousMode = state.mode;
    state.page = hash.get('page') || '';
    state.point = point?.id || null;
    state.query = hash.get('q') || '';
    state.mapQuery = hash.get('placeq') || '';
    state.mode = hash.get('mode') === 'region' ? 'region' : 'map';
    state.intent = hash.get('intent') === 'find' || (!hash.has('intent') && (state.query || state.page)) ? 'find' : 'browse';
    state.section = ['exits','places'].includes(hash.get('view')) ? hash.get('view') : 'local';
    state.topic = ['pokemon','item','quest','trainer'].includes(hash.get('topic')) ? hash.get('topic') : 'all';
    state.findType = ['pokemon','item','quest','trainer'].includes(hash.get('kind')) ? hash.get('kind') : 'all';
    $('show-markers').checked = hash.get('markers') !== '0'; $('boundaries').checked = hash.get('labels') !== '0';
    $('debug-mode').checked = hash.get('debug') === '1';
    document.body.classList.toggle('debug-mode', $('debug-mode').checked);
    const pageMap = (manifest.page_locations || {})[normalizePage(state.page)]?.[0]?.map_id;
    let remembered = null;
    if (!hash.size) { try { remembered = localStorage.getItem('mercury-atlas-last-map'); } catch {} }
    const id = maps[hash.get('map')] ? hash.get('map') : point && maps[point.map_id] ? point.map_id : maps[pageMap] ? pageMap : maps[remembered] ? remembered : null;
    if (id && (id !== state.map || previousMode !== state.mode || state.screen === 'world')) selectMap(id, false);
    if (!id) {
      state.map = null; state.tiles = []; state.bounds = null;
      world.replaceChildren(); markers.replaceChildren(); tileNodes.clear(); markerNodes.clear();
      $('map-title').textContent = '选择地点'; $('map-quality').textContent = ''; $('source-notice').replaceChildren(); $('map-reference-id').textContent = '';
      if (state.intent === 'browse') state.section = 'places';
    }
    state.screen = !id || hash.get('screen') === 'world' ? 'world' : 'scene';
    state.worldSection = Object.hasOwn(window.ATLAS_WORLD.sections, hash.get('area') || '') ? hash.get('area') : '';
    refreshResults();
    if (point) selectPoint(point, false, false, false);
    else { state.point = null; $('detail').hidden = true; refreshHighlight(); schedule(); }
  }
  function refreshResults() {
    const terms = normalize(state.query).trim().split(/\s+/).filter(Boolean);
    if (state.intent === 'find') {
      filtered = !terms.length && state.findType === 'all' && !state.page ? [] : points.filter(p => p.kind !== 'warp' && pageMatch(p) && (state.findType === 'all' || navigation.category(p) === state.findType) && terms.every(t => searchText.get(p.id).includes(t)));
    } else {
      filtered = points.filter(p => p.map_id === state.map && (state.section === 'exits' ? p.kind === 'warp' : p.kind !== 'warp' && pageMatch(p) && (state.section === 'places' || state.topic === 'all' || navigation.category(p) === state.topic)));
    }
    navigation.render(filtered); worldPicker.render(); refreshHighlight(); schedule();
  }
  function selectMap(id, sync = true) {
    if (!maps[id]) { $('empty').textContent = '地图数据尚未生成，请先运行离线数据生成器。'; return; }
    state.map = id;
    state.screen = 'scene'; state.worldSection = worldPicker.sectionFor(id); worldPicker.render();
    try { localStorage.setItem('mercury-atlas-last-map', id); } catch {}
    const m = maps[id], region = regions[m.region];
    const ids = state.mode === 'region' && region ? region.maps : [id];
    state.tiles = (ids || [id]).filter(key => maps[key]).map(key => {
      const map = maps[key], origin = state.mode === 'region' && region && Array.isArray(map.origin) ? map.origin : [0,0];
      return {id:key, map, x:(Number(origin[0]) || 0)*16, y:(Number(origin[1]) || 0)*16, w:Number(map.width)*16, h:Number(map.height)*16};
    }).filter(t => t.w > 0 && t.h > 0);
    state.bounds = state.tiles.length ? {x:Math.min(...state.tiles.map(t => t.x)), y:Math.min(...state.tiles.map(t => t.y)), right:Math.max(...state.tiles.map(t => t.x+t.w)), bottom:Math.max(...state.tiles.map(t => t.y+t.h))} : null;
    world.replaceChildren(); markers.replaceChildren(); tileNodes.clear(); markerNodes.clear();
    $('map-title').textContent = state.mode === 'region' && region ? `${m.name || id}及周边 · ${state.tiles.length}张地图` : m.name || id;
    $('map-reference-id').textContent = `地图编号 ${id} · ${m.width} × ${m.height} 格`;
    const q = quality(id); $('map-quality').textContent = q.label; $('map-quality').classList.toggle('warning', q.warning);
    $('map-quality').title = '渲染状态与场景身份是不同信息；图块可解码不代表已确认正常游戏用途。';
    const notice = $('source-notice'), report = data.render?.maps?.[id];
    notice.replaceChildren();
    if (m.source_issue) {
      notice.append(element('p', `${id}：${m.source_issue.note}`));
      for (const target of m.source_issue.alternatives || []) {
        if (!maps[target]) continue;
        const button = element('button', `查看 ${maps[target].name}（${target}）`);
        button.dataset.targetMap = target;
        button.onclick = () => { state.point = null; $('detail').hidden = true; selectMap(target); refreshResults(); };
        notice.append(button);
      }
    } else if (report?.status === 'unavailable') {
      notice.append(element('p', report.errors?.some(e => e.includes('0xFFFF')) ? `${id}：本图引用的图块描述表为FF填充，源数据失效；不再显示误生成的黑图。` : `${id}：ROM图块源无法解码，没有可用底图。`));
    }
    if (report?.status === 'partial') notice.append(element('p', `${id}：本图存在局部图块或调色板缺口；已保留可显示内容，未将其标为完整实景。`));
    if (report?.object_errors?.length) notice.append(element('p', `${id}：${report.object_errors.length}个大型固定对象未绘制，图形或调色板来源尚未解析；地形底图仍可浏览。`));
    notice.hidden = !notice.childNodes.length;
    $('map-reference').open = report?.status === 'unavailable';
    $('mode-region').setAttribute('aria-pressed', String(state.mode === 'region'));
    $('mode-map').setAttribute('aria-pressed', String(state.mode === 'map'));
    fit(); refreshHighlight(); if (sync) writeHash(true);
  }
  function fit() {
    const b = state.bounds; if (!b) return;
    state.scale = Math.max(.01, Math.min(4, (viewport.clientWidth-64)/(b.right-b.x), (viewport.clientHeight-100)/(b.bottom-b.y)));
    state.tx = viewport.clientWidth/2 - (b.x+b.right)/2*state.scale;
    state.ty = viewport.clientHeight/2 - (b.y+b.bottom)/2*state.scale;
    schedule();
  }
  function focusPoint(p) {
    const tile = state.tiles.find(t => t.id === p.map_id); if (!tile) return;
    if (!placed(p)) {
      state.scale = Math.max(.01, Math.min(3, (viewport.clientWidth-64)/tile.w, (viewport.clientHeight-100)/tile.h));
      state.tx = viewport.clientWidth/2-(tile.x+tile.w/2)*state.scale;
      state.ty = viewport.clientHeight/2-(tile.y+tile.h/2)*state.scale;
    } else {
      state.scale = Math.max(state.scale, 1.5);
      state.tx = viewport.clientWidth/2-(tile.x+p.x*16+8)*state.scale;
      state.ty = viewport.clientHeight/2-(tile.y+p.y*16+8)*state.scale;
    }
  }
  // A task can remain selected while its step changes the map being viewed.
  function selectPoint(p, sync = true, focus = true, move = true) {
    lastFocus = document.activeElement;
    state.point = p.id;
    if (move && maps[p.map_id] && (state.map !== p.map_id || state.screen === 'world')) selectMap(p.map_id, false);
    if (move) focusPoint(p);
    $('detail-kind').textContent = `${kinds[p.kind] || '地点'} · ${number.get(p.id)} 号`;
    $('detail-title').textContent = p.title || p.id;
    $('detail-map').textContent = `记录地点：${maps[p.map_id]?.name || '所属地图未知'}`;
    $('detail-text').textContent = p.detail || '暂无补充说明。';
    $('detail-geometry').textContent = geometryLabel(p);
    $('detail-record').textContent = `地图 ${p.map_id} · ${number.get(p.id)}号记录${placed(p) ? ` · 格坐标 ${p.x}, ${p.y}` : ''}\n${p.id}\n${p.source || ''}`;
    $('focus-detail').hidden = false;
    $('focus-detail').onclick = () => { selectMap(p.map_id, false); focusPoint(p); renderGuide(p); refreshResults(); writeHash(true); viewport.focus({preventScroll:false}); };
    renderGuide(p);
    $('detail-links').replaceChildren();
    for (const link of p.links || []) { const url = guideURL(link.page); if (url) { const a = element('a', '打开完整攻略 →'); a.href = url; $('detail-links').append(a); } }
    if (p.target && maps[p.target]) {
      const destination = byId.get(p.target_point);
      const go = element('button', destination ? `定位到 ${maps[p.target].name} ${number.get(destination.id)}号入口 →` : `打开 ${maps[p.target].name}（具体位置待补）→`);
      go.append(element('span', ` [${p.target}]`, 'debug-only'));
      go.onclick = () => {
        if (destination) selectPoint(destination);
        else { state.point = null; $('detail').hidden = true; selectMap(p.target); refreshResults(); }
      };
      $('detail-links').append(go);
    }
    $('detail').hidden = false;
    refreshResults();
    const activeRow = $('results').querySelector('.point-result.active');
    if (activeRow) $('results').scrollTop += activeRow.getBoundingClientRect().top - $('results').getBoundingClientRect().top - 8;
    schedule(); if (sync) writeHash(true);
    if (focus) $('close-detail').focus({preventScroll:!matchMedia('(max-width:760px)').matches});
  }
  function renderGuide(p) {
    $('detail-map').textContent = `记录地点：${maps[p.map_id]?.name || '所属地图未知'}${state.map !== p.map_id ? ` · 当前查看 ${maps[state.map]?.name || state.map}` : ''}`;
    const panel = $('guide-preview'); panel.replaceChildren();
    const guide = (p.links || []).map(l => data.guides?.[normalizePage(l.page)]).find(Boolean);
    if (!guide) return;
    for (const section of guide.sections || []) {
      const folded = ['注意事项','尚未整理的条件'].includes(section.title);
      const wrapper = element(folded ? 'details' : 'section', undefined, 'guide-section');
      wrapper.append(element(folded ? 'summary' : 'h3', section.title));
      const list = element(section.title === '行动步骤' ? 'ol' : 'ul');
      for (const item of section.items) {
        const li = element('li'); li.append(element('p',item.text));
        if (item.map_id && maps[item.map_id]) {
          const button = element('button',`在地图查看：${maps[item.map_id].name}`,'step-map');button.dataset.stepMap=item.map_id;
          if (item.map_id === state.map) { li.classList.add('current-step-map'); button.textContent = `当前地图：${maps[item.map_id].name}`; }
          button.onclick = () => { selectMap(item.map_id,false); renderGuide(p); refreshResults(); writeHash(true); viewport.focus({preventScroll:false}); };
          li.append(button);
        }
        list.append(li);
      }
      wrapper.append(list); panel.append(wrapper);
    }
  }
  function refreshHighlight() {
    for (const e of document.querySelectorAll('.point-result')) { const active = e.dataset.point === state.point; e.classList.toggle('active', active); e.setAttribute('aria-pressed', String(active)); }
    for (const e of document.querySelectorAll('.map-result')) { const active = e.dataset.map === state.map; e.classList.toggle('active', active); e.setAttribute('aria-pressed', String(active)); }
  }
  function schedule() { if (!frame) frame = requestAnimationFrame(draw); }
  function showCluster(members, anchor) {
    lastFocus = document.activeElement;
    state.point = null;
    $('guide-preview').replaceChildren(); $('focus-detail').hidden = true;
    $('detail-record').textContent = members.map(p => `${p.map_id} · ${p.id}`).join('\n');
    $('detail-kind').textContent = '地点聚合 · 屏幕邻近点';
    $('detail-title').textContent = `${members.length} 个地点`;
    const names = [...new Set(members.map(p => maps[p.map_id]?.name || p.map_id))];
    $('detail-map').textContent = names.join(' / ');
    $('detail-text').textContent = '选择下列地点查看条件与攻略。同一坐标的多条记录也可以逐一打开。';
    $('detail-geometry').textContent = '这些地点在当前比例下靠得较近。可以放大地图，或直接选择下面的记录。';
    const links = $('detail-links'); links.replaceChildren();
    const expand = element('button', '放大本处');
    expand.onclick = () => {
      state.scale = Math.min(12, state.scale * 2);
      state.tx = viewport.clientWidth/2 - anchor.x*state.scale;
      state.ty = viewport.clientHeight/2 - anchor.y*state.scale;
      schedule();
    };
    links.append(expand);
    for (const p of members) {
      const button = element('button', undefined, 'cluster-member');
      const text = element('span');
      text.append(element('strong', p.title || p.id), element('small', `${maps[p.map_id]?.name || p.map_id} · ${kinds[p.kind] || '地点'}`));
      button.append(badge(p), text); button.onclick = () => selectPoint(p); links.append(button);
    }
    $('detail').hidden = false;
    refreshHighlight(); schedule(); writeHash();
    $('close-detail').focus({preventScroll:true});
  }
  function draw() {
    frame = 0;
    const {scale:s, tx, ty} = state, width = viewport.clientWidth, height = viewport.clientHeight;
    world.style.transform = `translate(${tx}px,${ty}px) scale(${s})`;
    world.className = $('boundaries').checked ? 'show-bounds' : 'hide-bounds';
    const margin = 192;
    const visible = state.tiles.filter(t => tx+(t.x+t.w)*s >= -margin && ty+(t.y+t.h)*s >= -margin && tx+t.x*s <= width+margin && ty+t.y*s <= height+margin);
    const ids = new Set(visible.map(t => t.id));
    for (const [id, node] of tileNodes) if (!ids.has(id)) { node.remove(); tileNodes.delete(id); }
    const selection = byId.get(state.point);
    for (const t of visible) {
      let node = tileNodes.get(t.id);
      if (!node) {
        node = element('div', undefined, 'map-tile');
        Object.assign(node.style, {left:t.x+'px', top:t.y+'px', width:t.w+'px', height:t.h+'px'});
        const report = data.render?.maps?.[t.id];
        const unavailable = t.map.render_status === 'unavailable' || report?.status === 'unavailable';
        const path = guideURL(t.map.image || report?.image);
        if (!unavailable && path) {
          const img = element('img'); img.alt = ''; img.draggable = false; img.decoding = 'async';
          img.onerror = () => { img.remove(); node.classList.add('no-image'); node.querySelector('.map-name').textContent = `${t.map.name || t.id} · 底图不可用`; };
          img.src = path; node.append(img);
          if (t.map.objects_image) {
            const objects = element('img', undefined, 'object-layer'); objects.alt = '建筑与大型固定对象'; objects.draggable = false;
            objects.src = guideURL(t.map.objects_image); node.append(objects);
          }
        } else node.classList.add('no-image');
        const label = element('span', `${t.map.name || t.id}${unavailable || !path ? ' · 地图图片暂不可用' : ''}`, 'map-name');
        if (report?.status === 'partial') label.append(element('span', ' · 底图部分缺块', 'debug-only'));
        node.append(label);
        world.append(node); tileNodes.set(t.id, node);
      }
      node.querySelector('.map-name').style.transform = `scale(${1/s})`;
      node.classList.toggle('selected-area', $('show-markers').checked && !!selection && !placed(selection) && selection.map_id === t.id);
    }
    const tilesById = new Map(visible.map(t => [t.id,t]));
    const candidates = $('show-markers').checked ? filtered.slice() : [];
    if ($('show-markers').checked && selection && !candidates.includes(selection)) candidates.push(selection);
    for (const node of tileNodes.values()) node.querySelector('.trigger-regions')?.remove();
    for (const p of candidates.filter(p => p.geometry === 'trigger')) {
      const tile = tilesById.get(p.map_id), node = tileNodes.get(p.map_id); if (!tile || !node) continue;
      let svg = node.querySelector('.trigger-regions');
      if (!svg) {
        svg = document.createElementNS('http://www.w3.org/2000/svg','svg'); svg.classList.add('trigger-regions');
        svg.setAttribute('viewBox', `0 0 ${tile.w} ${tile.h}`); node.append(svg);
      }
      for (const [x,y] of p.trigger_tiles) {
        const rect = document.createElementNS(svg.namespaceURI,'rect');
        for (const [k,v] of Object.entries({x:x*16,y:y*16,width:16,height:16,fill:'#8650a340',stroke:'#8650a3','stroke-width':1,'vector-effect':'non-scaling-stroke'})) rect.setAttribute(k,String(v));
        svg.append(rect);
      }
    }
    const displayed = new Set(), groups = new Map();
    let selectedPosition = null;
    for (const p of candidates) {
      const tile = tilesById.get(p.map_id); if (!tile || !placed(p)) continue;
      const x = tx+(tile.x+p.x*16+8)*s, y = ty+(tile.y+p.y*16+8)*s;
      if (x < -30 || y < -30 || x > width+30 || y > height+30) continue;
      const selected = p.id === state.point;
      if (selected) selectedPosition = {x,y};
      const key = selected ? `selected:${p.id}` : `cell:${Math.floor(x/28)}:${Math.floor(y/28)}`;
      if (!groups.has(key)) groups.set(key, {members:[], x:0, y:0, selected});
      const group = groups.get(key); group.members.push(p); group.x += x; group.y += y;
    }
    for (const [key, group] of groups) {
      const {members, selected} = group, count = members.length, p = members[0];
      let x = group.x/count, y = group.y/count;
      const anchor = {x:(x-tx)/s, y:(y-ty)/s};
      // Offset only aggregate badges; individual point markers retain their exact location.
      if (count>1 && !selected && selectedPosition && Math.abs(x-selectedPosition.x)<28 && Math.abs(y-selectedPosition.y)<28) x += x+42<width ? 36 : -36;
      displayed.add(key);
      let node = markerNodes.get(key);
      if (!node) { node = element('button'); markers.append(node); markerNodes.set(key,node); }
      node.className = `marker${count>1 ? ' cluster' : ''}${selected ? ' active' : ''}`;
      node.replaceChildren(count>1 ? element('span', String(count), 'badge cluster-badge') : badge(p));
      if (count === 1 && p.kind === 'warp' && p.target_number && (s >= .65 || selected)) { const target = element('span', `${p.reciprocal ? '↔' : '→'} ${maps[p.target]?.name || '目的地'}`, 'warp-target'); target.append(element('span', ` · ${p.target} · ${p.target_number}号`, 'debug-only')); node.append(target); }
      node.setAttribute('aria-label', count>1 ? `${count} 个地点，打开成员列表` : `${maps[p.map_id]?.name || p.map_id} ${number.get(p.id)}号 ${kinds[p.kind] || '地点'}：${p.title}`);
      node.title = count>1 ? `${count} 个地点 · 点击逐项查看` : `${p.title} · ${maps[p.map_id]?.name || p.map_id}`;
      node.onclick = count>1 ? () => showCluster(members, anchor) : () => selectPoint(p);
      node.style.left = x+'px'; node.style.top = y+'px'; node.setAttribute('aria-pressed', String(selected));
    }
    for (const [id,node] of markerNodes) if (!displayed.has(id)) { node.remove(); markerNodes.delete(id); }
    const tileIds = new Set(state.tiles.map(t => t.id));
    const areas = filtered.filter(p => tileIds.has(p.map_id) && !placed(p));
    $('area-hint').textContent = selection && !placed(selection) ? `${selection.title}：${geometryLabel(selection)} 虚线框表示所属地图。` : areas.length ? `还有 ${areas.length} 项内容未标出精确位置，可在左侧查看。` : '';
    $('view-status').textContent = `${Math.round(s*100)}%${$('debug-mode').checked ? ` · ${visible.length} / ${state.tiles.length} 张底图` : ''}${$('show-markers').checked ? '' : ' · 标记已隐藏'}`;
    $('empty').textContent = state.map ? (state.tiles.length ? '' : '地图图片暂不可用，请从左侧继续查看攻略。') : '请选择要查看的地点。';
  }
  function zoom(factor, x = viewport.clientWidth/2, y = viewport.clientHeight/2) {
    const old = state.scale, next = Math.max(.01, Math.min(12, old*factor));
    state.tx = x-(x-state.tx)*next/old; state.ty = y-(y-state.ty)*next/old; state.scale = next; schedule();
  }
  function closeDetail() { state.point = null; $('detail').hidden = true; refreshHighlight(); schedule(); writeHash(); if (lastFocus?.isConnected) lastFocus.focus({preventScroll:true}); else viewport.focus({preventScroll:true}); }
  $('close-detail').onclick = closeDetail;
  $('zoom-in').onclick = () => zoom(1.4); $('zoom-out').onclick = () => zoom(1/1.4);
  $('fit').onclick = fit; $('native').onclick = () => zoom(1/state.scale);
  $('reset').onclick = () => { state.point = null; $('detail').hidden = true; selectMap(state.map); refreshHighlight(); };
  $('boundaries').onchange = () => { schedule(); writeHash(); };
  $('show-markers').onchange = () => { schedule(); writeHash(); };
  for (const button of document.querySelectorAll('[data-intent]')) button.onclick = () => setNavigation({intent:button.dataset.intent});
  for (const button of document.querySelectorAll('[data-section]')) button.onclick = () => setNavigation({section:button.dataset.section,topic:'all'});
  for (const input of $('finder-types').querySelectorAll('input')) input.onchange = () => setNavigation({findType:input.value});
  for (const tabs of document.querySelectorAll('[role="tablist"]')) tabs.addEventListener('keydown', event => {
    if (!['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) return;
    const buttons = [...tabs.querySelectorAll('[role="tab"]')], index = buttons.indexOf(document.activeElement); if (index < 0) return;
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length-1 : (index+(event.key === 'ArrowRight'?1:-1)+buttons.length)%buttons.length;
    event.preventDefault(); buttons[next].click(); buttons[next].focus();
  });
  $('clear-filters').onclick = clearFilters;
  $('toggle-nav').onclick = () => {
    const collapsed = document.body.classList.toggle('nav-collapsed');
    $('toggle-nav').textContent = collapsed ? '展开导航' : '收起导航';
    $('toggle-nav').setAttribute('aria-expanded', String(!collapsed)); schedule();
  };
  $('copy-location').onclick = async () => {
    writeHash(); $('copy-fallback').hidden = true;
    try { await navigator.clipboard.writeText(location.href); $('copy-status').textContent = '已复制当前地图、地点与筛选链接。'; }
    catch { $('copy-fallback').hidden = false; $('location-link').value = location.href; $('location-link').focus(); $('location-link').select(); $('copy-status').textContent = '浏览器未允许自动复制，请复制下面的链接。'; }
  };
  for (const mode of ['region','map']) $('mode-'+mode).onclick = () => { state.mode = mode; selectMap(state.map, false); const p = byId.get(state.point); if (p) focusPoint(p); refreshResults(); writeHash(); };
  const applySearch = () => setNavigation(state.intent === 'find' ? {query:$('search').value.trim()} : {mapQuery:$('search').value.trim()});
  $('search').addEventListener('compositionstart', () => { composing = true; clearTimeout(searchTimer); });
  $('search').addEventListener('compositionend', () => { composing = false; applySearch(); });
  $('search').oninput = () => { clearTimeout(searchTimer); if (!composing) searchTimer = setTimeout(applySearch, 120); };
  $('search').onkeydown = event => { if (event.isComposing) return; if (event.key === 'Enter') applySearch(); if (event.key === 'Escape') { event.stopPropagation(); $('search').value = ''; applySearch(); } };
  $('clear-page').onclick = () => { state.page = ''; refreshResults(); writeHash(); };
  viewport.addEventListener('wheel', event => { event.preventDefault(); const rect = viewport.getBoundingClientRect(); zoom(Math.exp(-Math.max(-120,Math.min(120,event.deltaY))*.002), event.clientX-rect.left, event.clientY-rect.top); }, {passive:false});
  let drag = null;
  viewport.addEventListener('pointerdown', event => { if (event.target.closest('button') || event.button !== 0) return; drag = {id:event.pointerId, x:event.clientX, y:event.clientY}; viewport.setPointerCapture(event.pointerId); viewport.classList.add('dragging'); viewport.focus({preventScroll:true}); });
  viewport.addEventListener('pointermove', event => { if (!drag || drag.id !== event.pointerId) return; state.tx += event.clientX-drag.x; state.ty += event.clientY-drag.y; drag.x = event.clientX; drag.y = event.clientY; schedule(); });
  const stopDrag = () => { drag = null; viewport.classList.remove('dragging'); };
  viewport.addEventListener('pointerup', stopDrag); viewport.addEventListener('pointercancel', stopDrag); viewport.addEventListener('lostpointercapture', stopDrag);
  viewport.addEventListener('keydown', event => {
    if (event.target !== viewport) return;
    const step = event.shiftKey ? 160 : 48;
    switch (event.key) { case 'ArrowLeft':state.tx+=step;break;case 'ArrowRight':state.tx-=step;break;case 'ArrowUp':state.ty+=step;break;case 'ArrowDown':state.ty-=step;break;case '+':case '=':zoom(1.4);break;case '-':zoom(1/1.4);break;case 'f':case 'F':fit();break;case '0':zoom(1/state.scale);break;default:return; }
    event.preventDefault(); schedule();
  });
  document.addEventListener('keydown', event => { if (event.key === 'Escape' && !$('detail').hidden) closeDetail(); });
  window.addEventListener('hashchange', readHash);
  let oldWidth = viewport.clientWidth, oldHeight = viewport.clientHeight;
  new ResizeObserver(() => {
    const w = viewport.clientWidth, h = viewport.clientHeight;
    if (oldWidth && oldHeight) { state.tx += (w-oldWidth)/2; state.ty += (h-oldHeight)/2; }
    oldWidth = w; oldHeight = h; schedule();
  }).observe(viewport);
  if (!Object.keys(maps).length) $('empty').textContent = '地图数据尚未生成，请先运行离线数据生成器。';
  readHash();
  writeHash();
})();
