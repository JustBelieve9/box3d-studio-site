'use strict';
(() => {
  const pages = [...document.querySelectorAll('.page')];
  const toc = document.querySelector('#toc');
  const navigation = document.querySelector('#navigation');
  const search = document.querySelector('#search');
  const results = document.querySelector('#search-results');
  const count = document.querySelector('#search-count');
  const theme = document.querySelector('#theme');
  let current;
  let observer;
  let printing = [];
  const normalized = text => text.toLocaleLowerCase().replaceAll('ё', 'е');
  const route = (name, lang, section = '') => '#/' + (lang === 'en' ? 'en/' : '') + name + (section ? '?section=' + encodeURIComponent(section) : '');
  const activeSections = () => [...current.querySelectorAll('section[data-title]')];

  function clearSearch() { search.value = ''; results.replaceChildren(); count.textContent = ''; }
  function renderSearch() {
    results.replaceChildren();
    const query = normalized(search.value.trim());
    if (!query) { count.textContent = ''; return; }
    const terms = query.split(/\s+/);
    const matches = activeSections().filter(section => terms.every(term => normalized(section.textContent).includes(term)));
    count.textContent = current.dataset.lang === 'en' ? `${matches.length} sections found` : `Найдено разделов: ${matches.length}`;
    for (const section of matches) {
      const li = document.createElement('li');
      const link = document.createElement('a');
      link.href = route(current.dataset.route, current.dataset.lang, section.dataset.key);
      link.textContent = section.dataset.title;
      link.addEventListener('click', () => {
        section.querySelectorAll('details').forEach(detail => {
          if (terms.every(term => normalized(detail.textContent).includes(term))) detail.open = true;
        });
      });
      const text = section.textContent.replace(/\s+/g, ' ').trim();
      const offset = Math.max(0, normalized(text).indexOf(terms[0]) - 25);
      const snippet = document.createElement('small');
      snippet.textContent = (offset ? '…' : '') + text.slice(offset, offset + 115) + '…';
      link.append(snippet); li.append(link); results.append(li);
    }
  }

  function updateToc() {
    toc.replaceChildren();
    observer?.disconnect();
    for (const section of activeSections()) {
      const link = document.createElement('a');
      link.href = route(current.dataset.route, current.dataset.lang, section.dataset.key);
      link.textContent = section.dataset.title;
      link.dataset.section = section.dataset.key;
      toc.append(link);
    }
    if ('IntersectionObserver' in window) {
      observer = new IntersectionObserver(entries => {
        const visible = entries.filter(entry => entry.isIntersecting);
        if (!visible.length) return;
        const target = visible[0].target.dataset.key;
        for (const link of toc.querySelectorAll('a')) {
          if (link.dataset.section === target) link.setAttribute('aria-current', 'location');
          else link.removeAttribute('aria-current');
        }
      }, {rootMargin: '-90px 0px -65% 0px'});
      activeSections().forEach(section => observer.observe(section));
    }
  }

  function applyRoute() {
    const raw = location.hash.slice(1) || '/physx';
    // Keep old section links useful within the selected product.
    if (!raw.startsWith('/')) {
      const name = current?.dataset.route || 'physx';
      location.replace(route(name, current?.dataset.lang || 'ru', raw));
      return;
    }
    const [path, query = ''] = raw.split('?');
    let lang = path.startsWith('/en/') ? 'en' : 'ru';
    let name = path.replace(/^\/(en\/)?/, '') || 'physx';
    if (name === 'physx/guide') lang = 'ru';
    let target = pages.find(page => page.dataset.route === name && page.dataset.lang === lang);
    if (!target) { location.replace(route('physx', lang)); return; }
    const switched = target !== current;
    current = target;
    pages.forEach(page => { page.hidden = page !== current; });
    document.documentElement.lang = lang;
    document.title = `${name.includes('guide') ? 'Памятка zhb PhysX 0.57.0' : 'zhb PhysX 0.57.0'} — Box3D для Blender`;
    document.querySelector('#nav-caption').textContent = name.includes('guide') ? 'ПАМЯТКА / 0.57.0' : lang === 'en' ? 'ON THIS PAGE' : 'НА ЭТОЙ СТРАНИЦЕ';
    document.querySelector('.search-label').textContent = lang === 'en' ? 'Search this page' : 'Поиск по этой странице';
    search.placeholder = lang === 'en' ? 'For example: emitters' : 'Например: эмиттер';
    document.querySelector('.header-guide').textContent = lang === 'en' ? 'User guide · RU' : 'Памятка';
    document.querySelectorAll('[data-language]').forEach(button => {
      button.setAttribute('aria-pressed', String(button.dataset.language === lang));
      button.disabled = name.includes('guide') && button.dataset.language === 'en';
      button.title = button.disabled ? 'Памятка пока доступна на русском' : '';
    });
    if (switched) { clearSearch(); updateToc(); }
    const id = new URLSearchParams(query).get('section');
    const section = activeSections().find(item => item.dataset.key === id);
    if (section) {
      section.scrollIntoView({behavior:'instant',block:'start'});
      const heading = section.querySelector('h1,h2');
      heading.setAttribute('tabindex','-1'); heading.focus({preventScroll:true});
    } else if (switched || !id) window.scrollTo({top:0,behavior:'instant'});
  }

  document.querySelectorAll('[data-language]').forEach(button => button.addEventListener('click', () => {
    location.hash = route(current.dataset.route, button.dataset.language);
  }));
  document.querySelector('.skip-link').addEventListener('click',event => {
    event.preventDefault();
    document.querySelector('#main-content').focus();
    document.querySelector('#main-content').scrollIntoView();
  });
  document.addEventListener('click',event => {
    const link = event.target.closest('a[href^="#/"]');
    if (link && link.hash === location.hash) {
      event.preventDefault();
      applyRoute();
    }
  });
  document.querySelectorAll('[data-benchmark]').forEach(button => button.addEventListener('click', () => {
    const section = button.closest('section');
    section.querySelectorAll('[data-benchmark]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    section.querySelectorAll('[data-benchmark-panel]').forEach(panel => {panel.hidden = panel.dataset.benchmarkPanel !== button.dataset.benchmark;});
  }));
  theme.value = document.documentElement.dataset.theme || 'auto';
  theme.addEventListener('change', () => {
    if (theme.value === 'auto') delete document.documentElement.dataset.theme;
    else document.documentElement.dataset.theme = theme.value;
    try {if (theme.value === 'auto') localStorage.removeItem('studio-theme'); else localStorage.setItem('studio-theme',theme.value);}
    catch(error) {console.info('Theme preference not saved:',error.name);}
  });
  search.addEventListener('input',renderSearch);
  search.addEventListener('keydown',event => {
    if (event.key === 'Escape') clearSearch();
    if (event.key === 'Enter') { const first = results.querySelector('a'); if(first) first.click(); }
  });
  document.querySelectorAll('[data-print]').forEach(button => button.addEventListener('click',() => window.print()));
  window.addEventListener('beforeprint',() => {
    printing = [...current.querySelectorAll('details:not([open])')]; printing.forEach(detail => {detail.open = true;});
  });
  window.addEventListener('afterprint',() => {printing.forEach(detail => {detail.open = false;}); printing = [];});
  const mobile = matchMedia('(max-width:1000px)');
  const setNavigation = () => {navigation.open = !mobile.matches;};
  mobile.addEventListener('change',setNavigation); setNavigation();
  toc.addEventListener('click',event => {if(event.target.closest('a') && mobile.matches) navigation.open = false;});
  window.addEventListener('hashchange',applyRoute);
  applyRoute();
})();
