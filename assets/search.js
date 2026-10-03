(() => {
  'use strict';
  const q = document.querySelector('#q');
  if (!q) return;
  const labels = { quests: '支线攻略', items: '道具搜集', pokemon: '宝可梦获取', trainers: '训练家配队' };
  const radios = [...document.querySelectorAll('input[name="section"]')];
  const status = document.querySelector('#status');
  const results = document.querySelector('#results');
  const cards = document.querySelector('#cards');
  const more = document.querySelector('#load-more');
  const clear = document.querySelector('#clear-search');
  const mapLink = document.querySelector('#map-search-link');
  document.querySelector('#search-form')?.addEventListener('submit', event => { event.preventDefault(); if (Array.isArray(window.GUIDE_SEARCH_DATA) && !composing) { update(); status.scrollIntoView({block:'nearest'}); } });
  const normalize = (value) => value.trim().toLocaleLowerCase().normalize('NFKC');
  const source = window.GUIDE_SEARCH_DATA;
  if (!Array.isArray(source)) {
    status.textContent = '搜索数据未能加载。请使用下方目录浏览攻略，或重新打开首页。';
    more.hidden = true;
    return;
  }
  const data = source.map((record) => ({ ...record, normalizedTitle: normalize(record.title), normalizedText: normalize(record.text), haystack: normalize(record.title + ' ' + record.text) }));
  let hits = [], shown = 0, terms = [], composing = false, timer;
  const section = () => radios.find((radio) => radio.checked)?.value || '';
  const randomLinks = document.querySelector('#random-search-links');
  const randomPool = [...new Set(source.filter(record => /\/\d+\.html$/.test(record.url)).map(record => record.title.replace(/[（(].*$/, '').trim()).filter(title => title && !/未解出|占位|未使用|空白/.test(title)))];
  function shuffleExamples() {
    if (!randomLinks || !randomPool.length) return;
    const previous = new Set([...randomLinks.querySelectorAll('a')].map(link => link.textContent));
    let pool = randomPool.filter(title => !previous.has(title));
    if (pool.length < Math.min(3, randomPool.length)) pool = randomPool.slice();
    randomLinks.replaceChildren();
    for (let i = 0; i < 3 && pool.length; i++) {
      const title = pool.splice(Math.floor(Math.random() * pool.length), 1)[0];
      const link = document.createElement('a');
      link.textContent = title; link.href = '#q=' + encodeURIComponent(title);
      randomLinks.append(link);
    }
    document.querySelector('#random-search').hidden = false;
  }
  document.querySelector('#shuffle-search')?.addEventListener('click', shuffleExamples);
  shuffleExamples();
  function save() {
    const params = new URLSearchParams();
    if (q.value.trim()) params.set('q', q.value.trim());
    if (section()) params.set('section', section());
    const hash = params.toString();
    const url = location.pathname + location.search + (hash ? '#' + hash : '');
    try { history.replaceState(null, '', url); }
    catch (_) { location.replace(hash ? '#' + hash : location.href.split('#')[0]); }
  }
  function snippet(record) {
    // Normalization may change string lengths; map only the chosen excerpt on demand.
    const position = terms.length ? Math.min(...terms.map((term) => record.normalizedText.indexOf(term)).filter((index) => index >= 0)) : 0;
    if (!Number.isFinite(position) || position === 0) return record.text.slice(0, 190) + (record.text.length > 190 ? '…' : '');
    const start = Math.max(0, position - 48);
    const end = Math.min(record.normalizedText.length, start + 190);
    return (start ? '…' : '') + record.normalizedText.slice(start, end) + (end < record.normalizedText.length ? '…' : '');
  }
  function appendBatch() {
    const end = Math.min(shown + 60, hits.length);
    const fragment = document.createDocumentFragment();
    for (let index = shown; index < end; index++) {
      const record = hits[index];
      const item = document.createElement('section');
      item.className = 'result';
      const category = document.createElement('small');
      category.textContent = labels[record.section] || record.section;
      const heading = document.createElement('h2');
      const link = document.createElement('a');
      link.href = record.url;
      link.textContent = record.title;
      heading.append(link);
      const excerpt = document.createElement('p');
      excerpt.textContent = snippet(record);
      item.append(category, heading, excerpt);
      fragment.append(item);
    }
    results.append(fragment);
    shown = end;
    more.hidden = shown >= hits.length;
    more.textContent = '再显示' + Math.min(60, hits.length - shown) + '条';
    status.textContent = '找到 ' + hits.length + ' 项，已显示 ' + shown + ' 项。';
  }
  function update(writeHash = true) {
    clearTimeout(timer);
    terms = normalize(q.value).split(/\s+/).filter(Boolean);
    const selected = section();
    if (writeHash) save();
    results.replaceChildren();
    shown = 0;
    more.hidden = true;
    more.removeAttribute('aria-disabled');
    cards.hidden = Boolean(terms.length || selected);
    if (mapLink) { mapLink.hidden = !q.value.trim(); mapLink.href = 'maps/index.html#intent=find&q=' + encodeURIComponent(q.value.trim()); }
    if (!terms.length && !selected) {
      hits = [];
      status.textContent = '输入关键词或选择栏目开始搜索，也可浏览下方目录。';
      return;
    }
    hits = data.filter((record) => (!selected || record.section === selected) && terms.every((term) => record.haystack.includes(term)));
    if (terms.length) hits.sort((a, b) => Number(terms.every((term) => b.normalizedTitle.includes(term))) - Number(terms.every((term) => a.normalizedTitle.includes(term))));
    if (!hits.length) {
      status.textContent = '找到 0 项。请换个关键词，或清除筛选后重新浏览。';
      const recovery = document.createElement('button');
      recovery.type = 'button';
      recovery.textContent = '清除筛选，返回目录';
      recovery.addEventListener('click', reset);
      results.append(recovery);
      return;
    }
    appendBatch();
  }
  function reset() {
    composing = false;
    q.value = '';
    radios.forEach((radio) => { radio.checked = radio.value === ''; });
    update();
    q.focus();
  }
  function restore() {
    clearTimeout(timer);
    composing = false;
    const params = new URLSearchParams(location.hash.slice(1));
    q.value = params.get('q') || '';
    const saved = params.get('section') || '';
    const selected = Object.hasOwn(labels, saved) ? saved : '';
    radios.forEach((radio) => { radio.checked = radio.value === selected; });
    update(false);
  }
  q.addEventListener('compositionstart', () => { composing = true; clearTimeout(timer); });
  q.addEventListener('compositionend', () => { composing = false; clearTimeout(timer); timer = setTimeout(update, 120); });
  q.addEventListener('input', (event) => {
    clearTimeout(timer);
    if (!composing && !event.isComposing) timer = setTimeout(update, 120);
  });
  q.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !composing && !event.isComposing) {
      event.preventDefault();
      q.value = '';
      update();
    }
  });
  radios.forEach((radio) => radio.addEventListener('change', () => update()));
  clear.addEventListener('click', reset);
  more.addEventListener('click', () => {
    if (shown >= hits.length) return;
    appendBatch();
    // Retain the activating control, including after the final batch.
    if (more.hidden) {
      more.hidden = false;
      more.setAttribute('aria-disabled', 'true');
      more.textContent = '已显示全部结果';
    }
  });
  window.addEventListener('hashchange', restore);
  window.addEventListener('popstate', restore);
  restore();
})();
