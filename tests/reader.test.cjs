const assert = require('node:assert/strict');
const fs = require('node:fs');
const test = require('node:test');
const vm = require('node:vm');

const read = (name) => JSON.parse(fs.readFileSync(`data/${name}.json`, 'utf8'));
const dataset = {
  messages: read('messages'),
  conversations: read('conversations'),
  report: read('import-report'),
  emails: read('emails'),
  highlights: read('highlights'),
  source_manifest: JSON.parse(fs.readFileSync('exhibits/reader-sources.json', 'utf8')).sources,
  ...read('discovery'),
};

function boot(hash = '') {
  const elements = new Map();
  function element(key) {
    if (!elements.has(key))
      elements.set(key, {
        textContent: key === 'transcript' ? JSON.stringify(dataset) : '',
        innerHTML: '',
        value: '',
        hidden: false,
        dataset: {},
        style: {},
        open: false,
        classList: { toggle() {}, add() {}, remove() {} },
        setAttribute() {},
        addEventListener() {},
        focus() {},
        querySelector: (selector) => element(selector),
        querySelectorAll: () => [],
      });
    return elements.get(key);
  }
  const navigations = [];
  const context = vm.createContext({
    location: {
      hostname: 'localhost',
      hash,
      pathname: '/',
      search: '',
      href: 'http://localhost/' + hash,
      replace: (url) => navigations.push(url),
      assign: (url) => navigations.push(url),
    },
    document: {
      getElementById: element,
      querySelector: element,
      querySelectorAll: () => [],
      addEventListener() {},
      body: element('body'),
      documentElement: element('html'),
    },
    history: { state: null, scrollRestoration: 'auto', replaceState() {}, pushState() {} },
    localStorage: { getItem: () => null },
    sessionStorage: { getItem: () => null },
    addEventListener() {},
    requestAnimationFrame() {},
    matchMedia: () => ({ matches: false }),
    URLSearchParams,
    clearTimeout,
    setTimeout,
  });
  context.window = context;
  for (const file of ['reader-data.js', 'analytics.js', 'discovery.js', 'reader.js']) {
    vm.runInContext(fs.readFileSync(`src/${file}`, 'utf8'), context, { filename: file });
  }
  return { context, elements, navigations };
}

test('homepage initializes its feed and browse indexes', () => {
  const { elements } = boot();
  assert.match(elements.get('discover').innerHTML, /Elizabeth Holmes/);
  assert.match(elements.get('themeIndex').innerHTML, /Explore/);
  assert.match(elements.get('emailIndex').innerHTML, /email-1675/);
  assert.equal(elements.get('searchBtn').hidden, false);
});

test('search still finds reviewed text and opens canonical conversation links', () => {
  const { elements } = boot('#search?q=Walgreens');
  assert.equal(elements.get('searchPanel').hidden, false);
  assert.match(elements.get('conversations').innerHTML, /<mark>Walgreens<\/mark>/i);
  assert.match(elements.get('toc').innerHTML, /\/texts\/c\d+\//);
});

test('legacy conversation, email and incident bookmarks resolve to static pages', () => {
  assert.deepEqual(boot('#conversation-c001').navigations, ['/texts/c001/']);
  assert.deepEqual(boot('#c053').navigations, ['/texts/c052/']);
  assert.deepEqual(boot('#email-1675').navigations, ['/emails/email-1675/']);
  const incident = dataset.incidents[0];
  assert.deepEqual(boot('#incident-' + incident.id).navigations, [
    `/texts/${incident.conversation}/#record-${encodeURIComponent(incident.record)}`,
  ]);
});
