(() => {
  'use strict';
  document.querySelectorAll('#main-content table').forEach((table) => {
    if (table.closest('.table-scroll')) return;
    const wrapper = document.createElement('div');
    wrapper.className = 'table-scroll';
    wrapper.tabIndex = 0;
    wrapper.setAttribute('role', 'region');
    wrapper.setAttribute('aria-label', '攻略表格，可横向滚动');
    table.before(wrapper);
    wrapper.append(table);
  });
  const button = document.querySelector('#back-to-top');
  const main = document.querySelector('#main-content');
  if (!button || !main) return;
  const update = () => { button.hidden = window.scrollY <= 500; };
  window.addEventListener('scroll', update, { passive: true });
  update();
  button.addEventListener('click', () => {
    main.focus({ preventScroll: true });
    main.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
  });
})();
