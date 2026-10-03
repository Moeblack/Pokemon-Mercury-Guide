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
  const enabled = new Set(Object.keys(kinds));
  const viewport = $('viewport'), world = $('world'), markers = $('markers');
  const state = {map:null, point:null, page:'', mode:'region', query:'', currentOnly:false, scale:1, tx:0, ty:0, tiles:[], bounds:null};
  const tileNodes = new Map(), markerNodes = new Map();
  let frame = 0, filtered = [], lastFocus = null;
  let writtenHash = null, searchTimer = 0, composing = false;
  const normalize = value => String(value || '').normalize('NFKC').toLocaleLowerCase();
  const searchText = new Map(points.map(p => [p.id, normalize(`${p.title || ''} ${p.detail || ''} ${p.map_id} ${maps[p.map_id]?.name || ''}`)]));
  function quality(id) {
    const m = maps[id], report = data.render?.maps?.[id];
    if (report?.status === 'unavailable' || m?.render_status === 'unavailable') return {label:'无可用底图', warning:true};
    if (m?.source_issue) return {label:'来源异常 / 同名布局', warning:true};
    if (report?.status === 'partial' || m?.render_status === 'partial') return {label:'局部图块缺失', warning:true};
    if (report?.status === 'ok' || m?.render_status === 'ok') return {label:'图块可解码', warning:false};
    return {label:'渲染状态待确认', warning:true};
  }
  function clearFilters() {
    clearTimeout(searchTimer); state.query = ''; state.currentOnly = false; state.page = '';
    $('search').value = ''; $('current-map').checked = false;
    for (const input of $('filters').querySelectorAll('input')) { input.checked = true; enabled.add(input.dataset.kind); }
    refreshResults(); writeHash(); $('search').focus();
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
  function geometryLabel(p) { return p.geometry === 'trigger' ? `剧情触发区域 · ${p.trigger_tiles.length}格；不是宝可梦站立位置` : placed(p) ? `精确点位 · 格坐标 ${p.x}, ${p.y}` : p.geometry === 'area' ? '地图范围记录 · 未提供精确坐标' : '未定位记录 · 坐标缺失或越界，不在地图上打点'; }
  for (const [kind, label] of Object.entries(kinds)) {
    const wrap = element('label'), input = element('input'); input.type = 'checkbox'; input.checked = true; input.dataset.kind = kind;
    input.addEventListener('change', () => { input.checked ? enabled.add(kind) : enabled.delete(kind); refreshResults(); writeHash(); });
    wrap.append(input, document.createTextNode(label)); $('filters').append(wrap);
    const key = element('span'); key.append(element('span', '·', `badge ${kind}`), document.createTextNode(label)); $('legend').append(key);
  }
  function writeHash(push = false) {
    const hash = new URLSearchParams();
    if (state.map) hash.set('map', state.map);
    if (state.point) hash.set('point', state.point);
    if (state.page) hash.set('page', state.page);
    if (state.query) hash.set('q', state.query);
    hash.set('mode', state.mode);
    if (state.currentOnly) hash.set('scope', 'map');
    if (enabled.size !== Object.keys(kinds).length) hash.set('types', [...enabled].join(','));
    if (!$('show-markers').checked) hash.set('markers', '0');
    if (!$('boundaries').checked) hash.set('labels', '0');
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
    state.query = hash.get('q') || ''; $('search').value = state.query;
    state.mode = hash.get('mode') === 'map' ? 'map' : 'region';
    state.currentOnly = hash.get('scope') === 'map'; $('current-map').checked = state.currentOnly;
    $('show-markers').checked = hash.get('markers') !== '0'; $('boundaries').checked = hash.get('labels') !== '0';
    enabled.clear();
    for (const kind of (hash.has('types') ? hash.get('types').split(',') : Object.keys(kinds))) if (kinds[kind]) enabled.add(kind);
    for (const input of $('filters').querySelectorAll('input')) input.checked = enabled.has(input.dataset.kind);
    const pageMap = (manifest.page_locations || {})[normalizePage(state.page)]?.[0]?.map_id;
    const defaultMap = maps['3:76'] ? '3:76' : maps['3:66'] ? '3:66' : Object.keys(maps)[0];
    const id = point && maps[point.map_id] ? point.map_id : maps[hash.get('map')] ? hash.get('map') : maps[pageMap] ? pageMap : defaultMap;
    if (id !== state.map || previousMode !== state.mode) selectMap(id, false);
    refreshResults();
    if (point) selectPoint(point, false, false);
    else { state.point = null; $('detail').hidden = true; refreshHighlight(); schedule(); }
  }
  function refreshResults() {
    const terms = normalize(state.query).trim().split(/\s+/).filter(Boolean);
    const visibleMapIds = new Set(state.tiles.map(t => t.id));
    const currentRegion = maps[state.map]?.region;
    const sourceRank = id => maps[id]?.source_issue || data.render?.maps?.[id]?.status === 'unavailable' ? 1 : 0;
    const mapRank = id => id === state.map ? 0 : visibleMapIds.has(id) ? 1 : 2;
    const pointRank = p => p.map_id === state.map ? 0 : currentRegion != null && maps[p.map_id]?.region === currentRegion ? 1 : 2;
    const kindRank = {mega:0, quest:1, item:2, pokemon:3, trainer:4, warp:5};
    filtered = points.filter(p => enabled.has(p.kind) && pageMatch(p) && (!state.currentOnly || p.map_id === state.map) && terms.every(t => searchText.get(p.id).includes(t)));
    filtered.sort((a,b) => sourceRank(a.map_id)-sourceRank(b.map_id) || pointRank(a)-pointRank(b) || (kindRank[a.kind] ?? 6)-(kindRank[b.kind] ?? 6));
    const selectedIndex = filtered.findIndex(p => p.id === state.point);
    if (selectedIndex > 0) filtered.unshift(...filtered.splice(selectedIndex, 1));
    const mapResults = Object.entries(maps).filter(([id, m]) => mapPageMatch(id) && (!state.currentOnly || id === state.map) && terms.every(t => normalize(`${id} ${m.name || ''}`).includes(t)));
    mapResults.sort(([a],[b]) => sourceRank(a)-sourceRank(b) || mapRank(a)-mapRank(b));
    const results = $('results'); results.replaceChildren();
    if (!mapResults.length && !filtered.length) {
      const empty = element('div', undefined, 'no-results');
      empty.append(element('strong', '没有匹配的地图或地点'), element('p', '试试其他名称，或清除当前筛选。'));
      const clear = element('button', '清除筛选'); clear.onclick = clearFilters; empty.append(clear); results.append(empty);
    }
    // Incremental list avoids constructing thousands of buttons on every keystroke.
    results.append(element('h2', `地图 · ${mapResults.length}`));
    const mapList = element('div'); results.append(mapList);
    let mapOffset = 0, pointOffset = 0;
    function addMaps() {
      for (const [id, m] of mapResults.slice(mapOffset, mapOffset + 8)) {
        const button = element('button', undefined, 'result map-result'); button.dataset.map = id;
        const text = element('span'); text.append(element('strong', m.name || id), element('small', `${id} · ${m.width} × ${m.height} 格`)); button.append(text);
        const q = quality(id); text.append(element('small', q.label, `quality-label${q.warning ? ' source-warning' : ''}`));
        button.onclick = () => { state.point = null; $('detail').hidden = true; selectMap(id); refreshResults(); $('results').scrollTop = 0; };
        mapList.append(button);
      }
      mapOffset += 8; moreMaps.hidden = mapOffset >= mapResults.length; refreshHighlight();
    }
    const moreMaps = element('button', '显示更多地图'); moreMaps.onclick = addMaps; results.append(moreMaps);
    results.append(element('h2', `地点 · ${filtered.length}`));
    const pointList = element('div'); results.append(pointList);
    function addPoints() {
      for (const p of filtered.slice(pointOffset, pointOffset + 80)) {
        const button = element('button', undefined, 'result point-result'); button.dataset.point = p.id;
        const text = element('span'); text.append(element('strong', p.title || p.id), element('small', `${maps[p.map_id]?.name || p.map_id} · ${placed(p) ? kinds[p.kind] : p.geometry === 'area' ? '地图范围' : '未定位'}`));
        button.append(badge(p), text); button.onclick = () => selectPoint(p); pointList.append(button);
      }
      pointOffset += 80; morePoints.hidden = pointOffset >= filtered.length; refreshHighlight();
    }
    const morePoints = element('button', '显示更多地点'); morePoints.onclick = addPoints; results.append(morePoints);
    addMaps(); addPoints();
    $('count').textContent = `${state.currentOnly ? '当前地图' : '全部地图'} · ${mapResults.length} 张地图 / ${filtered.length} 条地点`;
    $('page-scope').hidden = !state.page;
    $('page-scope').querySelector('span').textContent = `攻略关联：${state.page}`;
    schedule();
  }
  function selectMap(id, sync = true) {
    if (!maps[id]) { $('empty').textContent = '地图数据尚未生成，请先运行离线数据生成器。'; return; }
    state.map = id;
    const m = maps[id], region = regions[m.region];
    const ids = state.mode === 'region' && region ? region.maps : [id];
    state.tiles = (ids || [id]).filter(key => maps[key]).map(key => {
      const map = maps[key], origin = state.mode === 'region' && region && Array.isArray(map.origin) ? map.origin : [0,0];
      return {id:key, map, x:(Number(origin[0]) || 0)*16, y:(Number(origin[1]) || 0)*16, w:Number(map.width)*16, h:Number(map.height)*16};
    }).filter(t => t.w > 0 && t.h > 0);
    state.bounds = state.tiles.length ? {x:Math.min(...state.tiles.map(t => t.x)), y:Math.min(...state.tiles.map(t => t.y)), right:Math.max(...state.tiles.map(t => t.x+t.w)), bottom:Math.max(...state.tiles.map(t => t.y+t.h))} : null;
    world.replaceChildren(); markers.replaceChildren(); tileNodes.clear(); markerNodes.clear();
    $('map-title').textContent = state.mode === 'region' && region ? `${m.name || id} [${id}] · ${state.tiles.length}张连通地图` : `${m.name || id} [${id}]`;
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
  function selectPoint(p, sync = true, focus = true) {
    lastFocus = document.activeElement;
    state.point = p.id;
    if (maps[p.map_id] && state.map !== p.map_id) selectMap(p.map_id, false);
    focusPoint(p);
    $('detail-kind').textContent = `${kinds[p.kind] || '地点'} · ${number.get(p.id)} 号`;
    $('detail-title').textContent = p.title || p.id;
    $('detail-map').textContent = `${maps[p.map_id]?.name || '所属地图未知'} [${p.map_id}]`;
    $('detail-text').textContent = p.detail || '暂无补充说明。';
    $('detail-geometry').textContent = geometryLabel(p);
    $('detail-links').replaceChildren();
    for (const link of p.links || []) { const url = guideURL(link.page); if (url) { const a = element('a', link.label || '阅读相关攻略 →'); a.href = url; $('detail-links').append(a); } }
    if (p.target && maps[p.target]) {
      const destination = byId.get(p.target_point);
      const go = element('button', destination ? `定位到 ${maps[p.target].name} [${p.target}] ${number.get(destination.id)}号入口 →` : `打开 ${maps[p.target].name} [${p.target}]（落点未定位）→`);
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
  function refreshHighlight() {
    for (const e of document.querySelectorAll('.point-result')) { const active = e.dataset.point === state.point; e.classList.toggle('active', active); e.setAttribute('aria-pressed', String(active)); }
    for (const e of document.querySelectorAll('.map-result')) { const active = e.dataset.map === state.map; e.classList.toggle('active', active); e.setAttribute('aria-pressed', String(active)); }
  }
  function schedule() { if (!frame) frame = requestAnimationFrame(draw); }
  function showCluster(members, anchor) {
    lastFocus = document.activeElement;
    $('detail-kind').textContent = '地点聚合 · 屏幕邻近点';
    $('detail-title').textContent = `${members.length} 个地点`;
    const names = [...new Set(members.map(p => maps[p.map_id]?.name || p.map_id))];
    $('detail-map').textContent = names.join(' / ');
    $('detail-text').textContent = '选择下列地点查看条件与攻略。同一坐标的多条记录也可以逐一打开。';
    $('detail-geometry').textContent = '按 28 像素屏幕网格聚合；编号为各自地图内的地点编号。';
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
        node.append(element('span', `${t.map.name || t.id}${unavailable || !path ? ' · 底图不可用' : report?.status === 'partial' ? ' · 底图部分缺块' : ''}`, 'map-name'));
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
      if (count === 1 && p.kind === 'warp' && p.target_number && (s >= .65 || selected)) node.append(element('span', `${p.reciprocal ? '↔' : '→'} ${p.target} · ${p.target_number}号`, 'warp-target'));
      node.setAttribute('aria-label', count>1 ? `${count} 个地点，打开成员列表` : `${maps[p.map_id]?.name || p.map_id} ${number.get(p.id)}号 ${kinds[p.kind] || '地点'}：${p.title}`);
      node.title = count>1 ? `${count} 个地点 · 点击逐项查看` : `${p.title} · ${maps[p.map_id]?.name || p.map_id}`;
      node.onclick = count>1 ? () => showCluster(members, anchor) : () => selectPoint(p);
      node.style.left = x+'px'; node.style.top = y+'px'; node.setAttribute('aria-pressed', String(selected));
    }
    for (const [id,node] of markerNodes) if (!displayed.has(id)) { node.remove(); markerNodes.delete(id); }
    const tileIds = new Set(state.tiles.map(t => t.id));
    const areas = filtered.filter(p => tileIds.has(p.map_id) && !placed(p));
    $('area-hint').textContent = selection && !placed(selection) ? `${selection.title}：${geometryLabel(selection)}。虚线框仅表示所属地图。` : areas.length ? `此视图有 ${areas.length} 条范围 / 未定位记录，可在导航列表查看；不绘制虚构点位。` : '';
    $('view-status').textContent = `${Math.round(s*100)}% · ${visible.length} / ${state.tiles.length} 张底图${$('show-markers').checked ? '' : ' · 标记已隐藏'}`;
    if (state.map) $('empty').textContent = state.tiles.length ? '' : '此地图尚无有效尺寸，无法显示底图。';
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
  $('current-map').onchange = () => { state.currentOnly = $('current-map').checked; refreshResults(); writeHash(); };
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
  const applySearch = () => { clearTimeout(searchTimer); state.query = $('search').value.trim(); refreshResults(); writeHash(); };
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
