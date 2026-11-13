const search = document.querySelector('#search');
const category = document.querySelector('#category');
const entries = [...document.querySelectorAll('.entry')];
let view = location.hash === '#repositories' ? 'repositories' : 'websites';

function filterEntries() {
  const query = search.value.trim().toLocaleLowerCase();
  const kind = view === 'websites' ? 'website' : 'repository';
  let count = 0;
  for (const entry of entries) {
    const matches = entry.dataset.kind === kind
      && entry.dataset.search.toLocaleLowerCase().includes(query)
      && (kind !== 'repository' || !category.value || entry.dataset.category === category.value);
    entry.hidden = !matches;
    if (matches) count++;
  }
  document.querySelector('.empty').hidden = count !== 0;
  document.querySelector('#results').textContent = `${count} 个${view === 'websites' ? '网站' : '仓库'}`;
}

function showView(next) {
  view = next === 'repositories' ? next : 'websites';
  for (const section of document.querySelectorAll('.gallery')) section.hidden = section.id !== view;
  for (const link of document.querySelectorAll('[data-view]')) {
    if (link.dataset.view === view) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  }
  document.querySelector('.category').hidden = view !== 'repositories';
  filterEntries();
}

document.querySelectorAll('[data-view]').forEach(link => link.addEventListener('click', event => {
  event.preventDefault();
  history.replaceState(null, '', `#${link.dataset.view}`);
  showView(link.dataset.view);
}));
window.addEventListener('hashchange', () => showView(location.hash.slice(1)));
search.addEventListener('input', filterEntries);
category.addEventListener('change', filterEntries);
document.querySelector('#reset').addEventListener('click', () => {
  search.value = '';
  category.value = '';
  filterEntries();
  search.focus();
});
document.addEventListener('keydown', event => {
  if (event.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
    event.preventDefault();
    search.focus();
  }
  if (event.key === 'Escape' && document.activeElement === search) {
    search.value = '';
    filterEntries();
    search.blur();
  }
});
showView(view);
