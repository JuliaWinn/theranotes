// Discovery is the default; the full transcript and source tools remain one step away.
const byIncident = new Map(incidents.map((i) => [i.id, i]));
const textURL = (id) => '/texts/' + resolveConversation(id) + '/';
const emailURL = (id) => '/emails/' + id + '/';
const incidentURL = (id) => {
  const i = byIncident.get(id);
  return textURL(i.conversation) + '#record-' + encodeURIComponent(i.record);
};
const featured = data.highlights || [];
const highlightKeys = new Set(featured.map((i) => i.type + ':' + i.id));
const curatedAt = new Map(featured.map((item, n) => [item.type + ':' + item.id, n]));
const heatOf = (item) =>
  (item.type === 'email'
    ? data.email_heat?.[item.id]
    : item.type === 'incident'
      ? byIncident.get(item.id).heat
      : 0) || 1;
const tagsOf = (item) =>
  item.type === 'email'
    ? byEmail.get(item.id).themes
    : item.type === 'incident'
      ? byIncident.get(item.id).tags
      : byConversation.get(item.id).tags;
const leadTag = (item) => tagsOf(item)[0];
// Spread a ranked list so neighbours differ in topic (and email cards don't stack) within the same tier.
function spread(pool, tierOf) {
  const out = [];
  pool = pool.slice();
  while (pool.length) {
    const prev = out[out.length - 1],
      at = pool.findIndex(
        (x) =>
          tierOf(x) === tierOf(pool[0]) &&
          (!prev ||
            (leadTag(x) !== leadTag(prev) && !(prev.type === 'email' && x.type === 'email'))),
      );
    out.push(pool.splice(Math.max(at, 0), 1)[0]);
  }
  return out;
}
// Feed order: the curated lead, then editorial heat (never shown), curated picks first within a tier.
function rankHighlights() {
  const pool = [
    ...featured.slice(1),
    ...incidents
      .filter((i) => !highlightKeys.has('incident:' + i.id))
      .map((i) => ({ type: 'incident', id: i.id })),
    ...emailThreads
      .filter((e) => !highlightKeys.has('email:' + e.id))
      .map((e) => ({ type: 'email', id: e.id })),
  ]
    .map((item, n) => ({ item, n, curated: curatedAt.get(item.type + ':' + item.id) ?? Infinity }))
    .sort((a, b) => heatOf(b.item) - heatOf(a.item) || a.curated - b.curated || a.n - b.n)
    .map((x) => x.item);
  return [...featured.slice(0, 1), ...spread(pool, heatOf)];
}
const highlights = rankHighlights();
// After the highlights, the feed continues through every other multi-message conversation, weightiest topics first.
const topicWeights = { alarm: 3, power: 3, press: 3, regulators: 3, money: 2, ops: 2, personal: 1 };
const highlightedConversations = new Set(incidents.map((i) => i.conversation));
const conversationScore = (c) =>
  c.tags.reduce((s, t) => s + (topicWeights[t] || 1), 0) + Math.min(c.messages.length, 80) / 40;
const moreConversations = spread(
  conversations
    .filter((c) => !highlightedConversations.has(c.id) && c.messages.length > 1)
    .sort((a, b) => conversationScore(b) - conversationScore(a) || a.start.localeCompare(b.start))
    .map((c) => ({ type: 'conversation', id: c.id })),
  (item) => Math.round(conversationScore(byConversation.get(item.id)) / 3),
);
const years = [...new Set(conversations.map((c) => c.start.slice(0, 4)))];
let pageMode = 'home',
  homeTheme = '',
  feedLimit = 8,
  homeScroll = 0,
  homeFeedLimit = 8,
  renderedHash = null;

// Reading history stays in this browser; it only steers recommendations and marks cards as read.
const seen = new Set(
  (() => {
    try {
      return JSON.parse(localStorage.getItem('tn-seen') || '[]');
    } catch (e) {
      return [];
    }
  })(),
);

// One key per thing a reader opens: incidents share their conversation's key.
const conversationOf = (item) =>
  item.type === 'incident'
    ? byIncident.get(item.id).conversation
    : item.type === 'conversation'
      ? item.id
      : '';
const keyOf = (item) =>
  item.type === 'email' ? 'email:' + item.id : 'conversation:' + conversationOf(item);

function highlightData(item) {
  const email = item.type === 'email',
    source = email ? byEmail.get(item.id) : byIncident.get(item.id);
  return {
    item,
    email,
    source,
    title: item.title || source.title,
    tags: email ? source.themes : source.tags,
    href: email ? emailURL(source.id) : incidentURL(source.id),
  };
}
function itemInfo(item) {
  if (item.type === 'conversation') {
    const c = byConversation.get(item.id);
    return { title: c.title, tags: c.tags, href: textURL(c.id), attr: `data-context="${c.id}"` };
  }
  const h = highlightData(item);
  return {
    title: h.title,
    tags: h.tags,
    href: h.href,
    attr: `${h.email ? 'data-email' : 'data-incident'}="${h.source.id}"`,
  };
}

function peek(indices) {
  return /* HTML */ `
    <div class="peek-transcript" aria-label="Conversation excerpt">
      ${indices
        .map((n, j) => {
          const m = messages[n],
            first = !j || messages[indices[j - 1]].sender !== m.sender;
          return /* HTML */ `
            <div class="row ${m.sender === 'Elizabeth Holmes' ? 'e' : 's'}${first ? ' first' : ''}">
              ${
                first
                  ? /* HTML */ `
                      <div class="name">${esc(m.sender)}</div>
                    `
                  : ''
              }
              <div class="bubble">${formatText(m.text)}</div>
            </div>
          `;
        })
        .join('')}
    </div>
  `;
}
function takeWithin(candidates, limit) {
  let length = 0;
  const indices = [];
  for (const n of candidates) {
    if (indices.length && length + messages[n].text.length > limit) break;
    indices.push(n);
    length += messages[n].text.length;
  }
  return indices;
}
const readMark = (item) => (seen.has(keyOf(item)) ? ' · Read' : '');
function highlightCard(item, lead = false) {
  const h = highlightData(item),
    i = h.source;
  let preview = '',
    count,
    when;
  if (h.email) {
    const speaker = i.messages.find((m) => m.text.includes(i.quote));
    preview = /* HTML */ `
      <blockquote class="email-peek">
        <p>“${esc(i.quote)}”</p>
        <cite>${esc(speaker?.sender || i.participants[0])}</cite>
      </blockquote>
    `;
    count = i.messages.length + ' ' + (i.messages.length === 1 ? 'email' : 'emails');
    when = i.date_start;
  } else {
    const c = byConversation.get(i.conversation),
      anchor = byRecord.get(i.record),
      at = c.messages.indexOf(anchor);
    preview = peek(takeWithin(c.messages.slice(at, at + 1 + (item.after ?? 1)), 520));
    count = c.messages.length + ' messages';
    when = messages[anchor].datetime_iso;
  }
  // The whole card is the link; only the lead keeps a full-width button.
  const action = h.email ? 'Read the emails' : 'Read the full exchange',
    target = `href="${h.href}" ${h.email ? 'data-email' : 'data-incident'}="${i.id}" aria-label="${action}: ${esc(h.title)}"`;
  return /* HTML */ `
    <article class="highlight-card${lead ? ' featured' : ''}">
      <div class="highlight-eyebrow">
        <span>
          ${lead ? 'Start here' : h.email ? 'From the inbox' : topicLabels[h.tags[0]] || 'In their texts'}
        </span>
        <time>${date(when)}${readMark(item)}</time>
      </div>
      <h2>${esc(h.title)}</h2>
      ${
        item.setup
          ? /* HTML */ `
              <p class="highlight-setup">${esc(item.setup)}</p>
            `
          : ''
      }${preview}${
        lead
          ? /* HTML */ `
              <a class="conversation-action card-target" ${target}>
                ${action}
                <span aria-hidden="true">→</span>
              </a>
              <p class="peek-count">${count} in the available exchange</p>
            `
          : /* HTML */ `
              <a class="card-link card-target" ${target}>
                <span>
                  ${action}
                  <small>· ${count}</small>
                </span>
                <span aria-hidden="true">→</span>
              </a>
            `
      }
    </article>
  `;
}
function conversationCard(item) {
  const c = byConversation.get(item.id);
  // Preview from the longest readable message without a link, so the card opens on substance rather than "Hi".
  let at = 0,
    best = -1;
  c.messages.forEach((n, j) => {
    const l = messages[n].text.length;
    if (l <= 220 && l > best && !/https?:|www\./.test(messages[n].text)) {
      best = l;
      at = j;
    }
  });
  return /* HTML */ `
    <article class="highlight-card">
      <div class="highlight-eyebrow">
        <span>${esc(topicLabels[c.tags[0]] || 'In their texts')}</span>
        <time>${date(c.start)}${readMark(item)}</time>
      </div>
      <h2>${esc(c.title)}</h2>
      <p class="highlight-setup">${esc(c.description)}</p>
      ${peek(takeWithin(c.messages.slice(at, at + 3), 420))}
      <a
        class="card-link card-target"
        href="${textURL(c.id)}"
        data-context="${c.id}"
        aria-label="Read the conversation: ${esc(c.title)}"
      >
        <span>
          Read the conversation
          <small>· ${c.messages.length} messages</small>
        </span>
        <span aria-hidden="true">→</span>
      </a>
    </article>
  `;
}
// Category cards keep the feed branching: a topic, a year, the inbox, or search.
function categoryCard(eyebrow, meta, title, body, teasers, link) {
  return /* HTML */ `
    <article class="highlight-card topic-card">
      <div class="highlight-eyebrow">
        <span>${eyebrow}</span>
        <span>${meta}</span>
      </div>
      <h2>${title}</h2>
      <p class="highlight-setup">${body}</p>
      ${
        teasers.length
          ? /* HTML */ `
              <ul class="topic-teasers">
                ${teasers
                  .map(
                    (t) => /* HTML */ `
                      <li>${esc(t)}</li>
                    `,
                  )
                  .join('')}
              </ul>
            `
          : ''
      }${link}
    </article>
  `;
}
const unseenFirst = (items) => [
  ...items.filter((x) => !seen.has(keyOf(x))),
  ...items.filter((x) => seen.has(keyOf(x))),
];
function feedCard(item) {
  if (item.type === 'incident' || item.type === 'email') return highlightCard(item);
  if (item.type === 'conversation') return conversationCard(item);
  if (item.type === 'topic') {
    const t = themes.find((x) => x.id === item.id),
      count = conversations.filter((c) => c.tags.includes(t.id)).length;
    return categoryCard(
      'Explore a topic',
      `${count} conversations`,
      esc(t.label),
      esc(t.description),
      unseenFirst(highlights.filter((h) => tagsOf(h).includes(t.id)))
        .slice(0, 3)
        .map((h) => itemInfo(h).title),
      /* HTML */ `
        <a class="card-link card-target" href="#highlights-${t.id}" data-home-theme="${t.id}">
          <span>Explore ${esc(t.label)}</span>
          <span aria-hidden="true">→</span>
        </a>
      `,
    );
  }
  if (item.type === 'year') {
    const list = conversations.filter((c) => c.start.startsWith(item.id)),
      start = list.find((c) => !seen.has('conversation:' + c.id)) || list[0];
    return categoryCard(
      'From the timeline',
      `${list.length} conversations`,
      item.id,
      `Every exchange from ${item.id} in the exhibits, in order, beginning ${date(start.start)}.`,
      list
        .slice()
        .sort((a, b) => conversationScore(b) - conversationScore(a))
        .slice(0, 3)
        .map((c) => c.title),
      /* HTML */ `
        <a class="card-link card-target" href="${textURL(start.id)}" data-context="${start.id}">
          <span>
            Read ${item.id} from ${start === list[0] ? 'the start' : 'where you left off'}
          </span>
          <span aria-hidden="true">→</span>
        </a>
      `,
    );
  }
  if (item.type === 'inbox')
    return categoryCard(
      'From the inbox',
      `${emailThreads.length} exchanges`,
      'The company emails',
      'Demos, investors, lab concerns and the press, from emails entered as trial exhibits.',
      unseenFirst(emailThreads.map((e) => ({ type: 'email', id: e.id })))
        .slice(0, 3)
        .map((e) => itemInfo(e).title),
      /* HTML */ `
        <a class="card-link card-target" href="#emails" data-open-view="emails">
          <span>Browse the emails</span>
          <span aria-hidden="true">→</span>
        </a>
      `,
    );
  if (item.type === 'search')
    return categoryCard(
      'Search',
      `${messages.length.toLocaleString()} texts`,
      'Looking for something specific?',
      'Search every text by name, word or phrase.',
      ['Tyler', 'Walgreens', 'FDA', 'love'].map((w) => 'Try “' + w + '”'),
      /* HTML */ `
        <a class="card-link card-target" href="#search" data-open-search>
          <span>Search the texts</span>
          <span aria-hidden="true">→</span>
        </a>
      `,
    );
  if (item.type === 'divider')
    return /* HTML */ `
      <p class="feed-divider">
        That’s every ${esc(topicLabels[item.id])} moment. More from the archive:
      </p>
    `;
  return /* HTML */ `
    <article class="highlight-card topic-card feed-finale">
      <h2>You’ve reached the end of the archive.</h2>
      <p class="highlight-setup">
        Every conversation in the exhibits is also in the timeline, and every text is searchable.
        Pick a topic to read it again from its best moments.
      </p>
      <nav class="home-filters" aria-label="Topics">
        ${Object.entries(topicLabels)
          .map(
            ([id, label]) => /* HTML */ `
              <button data-home-theme="${id}">${esc(label)}</button>
            `,
          )
          .join('')}
      </nav>
      <button class="text-button" data-open-view="timeline">Open the full timeline →</button>
      <button class="text-button" data-open-view="about">About the collection &amp; sources</button>
    </article>
  `;
}
function feedSequence({ theme = '', exclude = new Set(), skip = null } = {}) {
  let all = [...highlights, ...moreConversations].filter(
    (item) => item !== skip && !exclude.has(keyOf(item)),
  );
  let items = all;
  if (theme) {
    const own = all.filter((item) => tagsOf(item).includes(theme));
    items = [...own, { type: 'divider', id: theme }, ...all.filter((item) => !own.includes(item))];
  }
  const pattern = ['topic', 'year', 'topic', 'inbox', 'topic', 'search'],
    topics = themes.map((t) => t.id).filter((t) => t !== theme),
    out = [];
  let n = 0,
    t = 0,
    y = 0;
  for (const item of items) {
    out.push(item);
    if (item.type === 'divider') continue;
    if (++n % 5) continue;
    const kind = pattern[(n / 5 - 1) % pattern.length];
    out.push(
      kind === 'topic'
        ? { type: 'topic', id: topics[t++ % topics.length] }
        : kind === 'year'
          ? { type: 'year', id: years[years.length - 1 - (y++ % years.length)] }
          : { type: kind },
    );
  }
  return [...out, { type: 'end' }];
}
let feedItems = [],
  feedShown = 0;
function mountFeed(items, heading) {
  feedItems = items;
  feedShown = Math.min(Math.max(feedLimit, 8), items.length);
  $('endlessFeed').innerHTML = /* HTML */ `
    <div class="feed-heading">
      <h2>${heading}</h2>
      <button class="text-button" data-open-view="themes">Browse topics ↗</button>
    </div>
    <div class="highlight-feed" id="feedList">
      ${items.slice(0, feedShown).map(feedCard).join('')}
    </div>
    <div id="feedMore" class="feed-sentinel" aria-hidden="true"></div>
  `;
}
// Load the next cards well before the reader reaches the bottom, so there is never a "more" button to tap.
function fillFeed() {
  while (
    feedShown < feedItems.length &&
    $('feedMore').getBoundingClientRect().top < innerHeight + 1600
  ) {
    const next = feedItems.slice(feedShown, feedShown + 8);
    feedShown += next.length;
    feedLimit = feedShown;
    $('feedList').insertAdjacentHTML('beforeend', next.map(feedCard).join(''));
  }
}
addEventListener('scroll', fillFeed, { passive: true });
addEventListener('resize', fillFeed, { passive: true });
function renderHome() {
  const chips = /* HTML */ `
    <nav id="homeFilters" class="home-filters" aria-label="Highlight topics">
      <button data-home-theme="" aria-pressed="${!homeTheme}">Top moments</button>
      ${Object.entries(topicLabels)
        .map(
          ([id, label]) => /* HTML */ `
            <button data-home-theme="${id}" aria-pressed="${homeTheme === id}">
              ${esc(label)}
            </button>
          `,
        )
        .join('')}
    </nav>
  `;
  const intro = /* HTML */ `
    <div class="home-intro">
      <h1 class="framing">
        The real texts between
        <b>Elizabeth Holmes</b>
        and
        <b>Sunny Balwani</b>
        , from the evidence at their fraud trials.
      </h1>
      <button class="search-pill" type="button" data-open-search>
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          aria-hidden="true"
        >
          <circle cx="10.5" cy="10.5" r="6.5" />
          <path d="m16 16 5 5" />
        </svg>
        <span>Search ${messages.length.toLocaleString()} texts</span>
        <small>Tyler, Walgreens…</small>
      </button>
      ${chips}
    </div>
  `;
  $('discover').innerHTML = intro + (homeTheme ? '' : highlightCard(highlights[0], true));
  if (homeTheme) {
    const strip = $('homeFilters'),
      selected = strip.querySelector('[aria-pressed=true]');
    strip.scrollLeft =
      selected.offsetLeft - strip.offsetLeft - (strip.clientWidth - selected.offsetWidth) / 2;
  }
}

function render() {
  query = $('search').value.trim();
  let matches = 0;
  visible = conversations
    .map((c, n) => ({
      c,
      n,
      indices: c.messages.filter(
        (i) => !query || messages[i].text.toLowerCase().includes(query.toLowerCase()),
      ),
    }))
    .filter((x) => (!tag || x.c.tags.includes(tag)) && x.indices.length);
  $('discover').hidden = pageMode !== 'home';
  $('searchPanel').hidden = pageMode !== 'search';
  $('conversations').hidden = pageMode === 'home';
  document.querySelector('.end-note').hidden = pageMode !== 'search' || (!query && !tag);
  if (pageMode === 'home') renderHome();
  const showTranscript = pageMode === 'search' && (tag || query);
  $('conversations').innerHTML = showTranscript
    ? visible.length
      ? visible
          .map((x) => {
            matches += x.indices.length;
            return card(x.c, x.n, x.indices);
          })
          .join('')
      : '<p class="empty">No messages match. Try another word, or keep exploring below.</p>'
    : '';
  $('filterStatus').textContent =
    query || tag
      ? `${matches.toLocaleString()} ${query ? 'matching ' : ''}messages in ${visible.length} conversations${query ? ' · open a conversation for context' : ''}`
      : 'Search a name, a phrase, or a subject.';
  $('searchSuggestions').hidden = Boolean(query || tag);
  $('clear').hidden = !query && !tag;
  document.querySelectorAll('[data-filter]').forEach((b) => {
    b.classList.toggle('on', b.dataset.filter === tag);
    b.setAttribute('aria-pressed', String(b.dataset.filter === tag));
  });
  const exclude = new Set(pageMode === 'home' ? [] : seen);
  mountFeed(
    feedSequence({
      theme: pageMode === 'home' ? homeTheme : '',
      exclude,
      skip: pageMode === 'home' && !homeTheme ? highlights[0] : null,
    }),
    pageMode === 'home'
      ? homeTheme
        ? esc(topicLabels[homeTheme])
        : 'Keep reading'
      : 'Keep exploring',
  );
  renderToc();
  requestAnimationFrame(fillFeed);
}
function savePosition() {
  if (pageMode === 'home') {
    homeScroll = window.scrollY;
    homeFeedLimit = feedLimit;
  }
  history.replaceState({ ...history.state, scroll: window.scrollY, feedLimit }, '', location.href);
}
function setHash(value) {
  const hash = value ? '#' + value : '';
  if (location.hash === hash) return;
  savePosition();
  history.pushState({ scroll: null }, '', location.pathname + location.search + hash);
}
function navigate(hash, scroll = null, limit = null) {
  clearTimeout(timer);
  closeDrawer(true);
  setHash(hash);
  if (scroll !== null)
    history.replaceState(
      { ...history.state, scroll, ...(limit ? { feedLimit: limit } : {}) },
      '',
      location.href,
    );
  followHash(true);
}
// Full HTML pages are the normal destinations. Old bookmarks still resolve below.
function jumpConversation(id) {
  id = resolveConversation(id);
  if (byConversation.has(id)) location.assign(textURL(id));
}
function jumpIncident(id) {
  if (byIncident.has(id)) location.assign(incidentURL(id));
}
function jumpEmail(id) {
  if (byEmail.has(id)) location.assign(emailURL(id));
}
function backToBrowsing() {
  navigate(homeTheme ? 'highlights-' + homeTheme : '', homeScroll, homeFeedLimit);
}

function searchHash() {
  const params = new URLSearchParams();
  if ($('search').value.trim()) params.set('q', $('search').value.trim());
  if (tag) params.set('theme', tag);
  return 'search' + (params.size ? '?' + params : '');
}
function updateSearch() {
  clearTimeout(timer);
  history.replaceState({ scroll: 0 }, '', '#' + searchHash());
  renderedHash = location.hash.slice(1);
  render();
}
function openSearch(theme = '') {
  tag = theme;
  navigate('search' + (theme ? '?theme=' + encodeURIComponent(theme) : ''));
  if (!theme) $('search').focus({ preventScroll: true });
}
function followHash(force = false) {
  const hash = location.hash.slice(1),
    source = hash.match(/^source-([A-Za-z0-9_-]+)-(\d+)$/);
  const legacyConversation = resolveConversation(
    hash.startsWith('conversation-') ? hash.slice(13) : hash,
  );
  if (byEmail.has(hash)) {
    location.replace(emailURL(hash));
    return;
  }
  if (hash.startsWith('incident-') && byIncident.has(hash.slice(9))) {
    location.replace(incidentURL(hash.slice(9)));
    return;
  }
  if (byConversation.has(legacyConversation)) {
    location.replace(textURL(legacyConversation));
    return;
  }
  if (
    source &&
    sourcePageCounts[source[1]] &&
    Number(source[2]) >= 1 &&
    Number(source[2]) <= sourcePageCounts[source[1]]
  ) {
    if (renderedHash === null) {
      pageMode = 'home';
      render();
      recordReadingPage();
      renderedHash = '';
    }
    openSource(source[1], Number(source[2]), false);
    return;
  }
  if ($('sourceViewer').open) {
    $('sourceViewer').close();
    if (renderedHash === hash && !force) return;
  }
  if (renderedHash === hash && !force) return;
  tag = '';
  query = '';
  $('search').value = '';
  pageMode = 'home';
  homeTheme = '';
  if (hash.startsWith('search')) {
    pageMode = 'search';
    const p = new URLSearchParams(hash.split('?')[1] || '');
    $('search').value = p.get('q') || '';
    tag = topicLabels[p.get('theme')] ? p.get('theme') : '';
  } else if (hash.startsWith('highlights-'))
    homeTheme = topicLabels[hash.slice(11)] ? hash.slice(11) : '';
  feedLimit = history.state?.feedLimit || 8;
  renderedHash = hash;
  render();
  recordReadingPage();
  requestAnimationFrame(() =>
    window.scrollTo({ top: typeof history.state?.scroll === 'number' ? history.state.scroll : 0 }),
  );
}

function recordReadingPage() {
  if (pageMode === 'search') return;
  recordReaderView(
    homeTheme ? '/#highlights-' + homeTheme : '/',
    homeTheme ? 'Highlights: ' + topicLabels[homeTheme] : 'Theranotes · Texts & emails',
  );
}
