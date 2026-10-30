'use strict';
if ('scrollRestoration' in history) history.scrollRestoration = 'manual';
const data = JSON.parse(document.getElementById('transcript').textContent);
const { messages, conversations, report: importReport, themes, incidents } = data;
const emailThreads = (data.emails?.threads || [])
    .slice()
    .sort((a, b) => a.date_start.localeCompare(b.date_start) || a.id.localeCompare(b.id)),
  publicSources = data.source_manifest || [];
const byEmail = new Map(emailThreads.map((t) => [t.id, t])),
  bySource = new Map(publicSources.map((s) => [s.id, s]));
const topicLabels = Object.fromEntries(themes.map((t) => [t.id, t.label]));
const byConversation = new Map(conversations.map((c) => [c.id, c])),
  byRecord = new Map(messages.map((m, n) => [m.record, n]));
function resolveConversation(id) {
  const seen = new Set();
  while (data.conversation_aliases?.[id] && !seen.has(id)) {
    seen.add(id);
    id = data.conversation_aliases[id];
  }
  return id;
}
const $ = (id) => document.getElementById(id);
const esc = (s) =>
  String(s).replace(
    /[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c],
  );
const shortName = (s) =>
  s === 'Elizabeth Holmes' ? 'Elizabeth' : s === 'Sunny Balwani' ? 'Sunny' : s;
const date = (iso) =>
  new Intl.DateTimeFormat('en-US', {
    timeZone: 'UTC',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(new Date(iso));
const time = (iso) =>
  new Intl.DateTimeFormat('en-US', { timeZone: 'UTC', hour: 'numeric', minute: '2-digit' }).format(
    new Date(iso),
  );
let tag = '',
  query = '',
  visible = [],
  indexView = 'incidents',
  drawerTrigger = null;
