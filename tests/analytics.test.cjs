const assert = require('node:assert/strict');
const fs = require('node:fs');
const test = require('node:test');
const vm = require('node:vm');

function setup(hostname) {
  const scripts = [];
  const events = {};
  const context = vm.createContext({
    location: { hostname },
    window: {},
    document: {
      visibilityState: 'visible',
      createElement: () => ({ dataset: {} }),
      head: { appendChild: (script) => scripts.push(script) },
      addEventListener: (name, handler) => {
        events[name] = handler;
      },
    },
  });
  vm.runInContext(fs.readFileSync('src/analytics.js', 'utf8'), context);
  const record = vm.runInContext('recordReaderView', context);
  return { scripts, events, context, record };
}

test('local, fork and Cloudflare preview hosts never load GoatCounter', () => {
  for (const host of ['localhost', '127.0.0.1', 'fork.example.com', 'preview.pages.dev']) {
    const { scripts, record } = setup(host);
    record('/texts/c001/', 'Example');
    assert.equal(scripts.length, 0);
  }
});

test('production retains the existing account and queues one view per navigation', () => {
  const { scripts, context, record } = setup('theranotes.juliawinn.com');
  assert.equal(scripts.length, 1);
  assert.equal(scripts[0].dataset.goatcounter, 'https://theranotes.goatcounter.com/count');
  assert.equal(scripts[0].src, 'https://gc.zgo.at/count.js');
  assert.equal(context.window.goatcounter.no_onload, true);
  const views = [];
  record('/', 'Home');
  record('/', 'Home');
  context.window.goatcounter.count = (view) => views.push({ ...view });
  scripts[0].onload();
  record('/texts/c001/', 'Conversation');
  assert.deepEqual(views, [
    { path: '/', title: 'Home' },
    { path: '/texts/c001/', title: 'Conversation' },
  ]);
});

test('a hidden tab waits until visible to send queued views', () => {
  const { scripts, events, context, record } = setup('theranotes.juliawinn.com');
  const views = [];
  context.document.visibilityState = 'hidden';
  context.window.goatcounter.count = (view) => views.push(view);
  record('/', 'Home');
  scripts[0].onload();
  assert.equal(views.length, 0);
  context.document.visibilityState = 'visible';
  events.visibilitychange();
  assert.equal(views.length, 1);
});
