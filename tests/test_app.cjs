const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const element = (extra = {}) => ({ hidden: false, value: '', dataset: {}, listeners: {}, attrs: {},
  addEventListener(name, fn) { this.listeners[name] = fn; },
  setAttribute(name, value) { this.attrs[name] = value; },
  removeAttribute(name) { delete this.attrs[name]; }, focus() {}, blur() {}, ...extra });
const entries = [
  element({ dataset: { kind: 'website', search: '树人 shuren.liyw.top 鲁迅' } }),
  element({ dataset: { kind: 'website', search: '数学 math.liyw.top' } }),
  element({ dataset: { kind: 'repository', search: '树人 shuren-luxun 鲁迅', category: 'life' } }),
  element({ dataset: { kind: 'repository', search: '数理 math-model-online', category: 'learning' } })
];
const sections = ['websites', 'repositories'].map(id => element({ id }));
const links = sections.map(section => element({ dataset: { view: section.id } }));
const search = element(), category = element(), empty = element(), results = element(), reset = element(), categoryLabel = element();
const selectors = { '#search': search, '#category': category, '.empty': empty, '#results': results, '#reset': reset, '.category': categoryLabel };
const document = { activeElement: { tagName: 'BODY' }, addEventListener() {},
  querySelector: selector => selectors[selector],
  querySelectorAll: selector => ({ '.entry': entries, '.gallery': sections, '[data-view]': links })[selector] };
const location = { hash: '#repositories' };
const context = { document, location, history: { replaceState(_a, _b, hash) { location.hash = hash; } }, window: { addEventListener() {} } };
vm.runInNewContext(fs.readFileSync('dist/app.js', 'utf8'), context);
assert.equal(sections[0].hidden, true);
assert.equal(sections[1].hidden, false);
assert.equal(results.textContent, '2 个仓库');
search.value = '鲁迅'; search.listeners.input();
assert.deepEqual(entries.map(entry => entry.hidden), [true, true, false, true]);
links[0].listeners.click({ preventDefault() {} });
assert.equal(categoryLabel.hidden, true);
assert.deepEqual(entries.map(entry => entry.hidden), [false, true, true, true]);
links[1].listeners.click({ preventDefault() {} });
search.value = ''; category.value = 'learning'; category.listeners.change();
assert.deepEqual(entries.map(entry => entry.hidden), [true, true, true, false]);
search.value = 'no match'; search.listeners.input(); assert.equal(empty.hidden, false);
reset.listeners.click(); assert.equal(empty.hidden, true); assert.equal(results.textContent, '2 个仓库');
console.log('View deep links, search, category filtering and empty-state reset passed.');
