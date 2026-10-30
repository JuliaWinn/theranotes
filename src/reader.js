function formatText(text) {
  if (!text) return '<span class="blank">[No message text printed]</span>';
  return text
    .split('[REDACTED]')
    .map((piece) => {
      if (!query) return esc(piece);
      const lower = piece.toLowerCase(),
        needle = query.toLowerCase();
      let out = '',
        at = 0,
        found;
      while ((found = lower.indexOf(needle, at)) !== -1) {
        out +=
          esc(piece.slice(at, found)) +
          '<mark>' +
          esc(piece.slice(found, found + needle.length)) +
          '</mark>';
        at = found + needle.length;
      }
      return out + esc(piece.slice(at));
    })
    .join('<span class="redact" aria-label="Redacted">[REDACTED]</span>');
}
function sourceLink(s) {
  return /* HTML */ `
    <a
      href="#source-${s.exhibit}-${s.page}"
      data-source="${s.exhibit}"
      data-page="${s.page}"
      title="View original exhibit page"
    >
      ${esc(s.exhibit)} · p. ${s.page} · ${esc(s.bates)}
    </a>
  `;
}
function sources(c) {
  return Object.entries(c.sources)
    .map(([part, s]) => {
      const b = s.bates,
        range = b.length > 1 ? b[0] + '–' + b[b.length - 1] : b[0];
      return /* HTML */ `
        <a
          href="#source-${part}-${s.pages[0]}"
          data-source="${part}"
          data-page="${s.pages[0]}"
          title="View original exhibit, pages ${s.pages.join(', ')}"
        >
          ${part} · ${esc(range)}
        </a>
      `;
    })
    .join(' ');
}
function conversationAction(c) {
  return /* HTML */ `
    <button class="conversation-action" data-context="${c.id}">
      See full conversation →
      <small>
        ${c.messages.length === 1 ? '1 message' : 'All ' + c.messages.length + ' messages'}
        available in this exchange
      </small>
    </button>
  `;
}
function card(c, n, indices) {
  const counts = Object.entries(c.counts)
    .map(([name, num]) => `${esc(shortName(name))} ${num}`)
    .join(' · ');
  let html = /* HTML */ `
    <section class="chapter" id="${c.id}">
      <div class="ch-card">
        <div class="ch-tab">
          ${date(c.start)}${date(c.end) !== date(c.start) ? ' – ' + date(c.end) : ''}
        </div>
        <h2>${esc(c.title)}</h2>
        <p>${esc(c.description)}</p>
        ${conversationAction(c)}
        <details class="source-details">
          <summary>About this exchange &amp; sources</summary>
          <div class="chips">
            ${c.tags
              .map(
                (t) => /* HTML */ `
                  <button class="chip sm" data-tag="${t}">${esc(topicLabels[t])}</button>
                `,
              )
              .join('')}
          </div>
          <p>
            ${counts} · ${c.messages.length} available messages. The court exhibits are selections;
            gaps may remain.
          </p>
          <div class="source-summary">${sources(c)}</div>
        </details>
      </div>
    </section>
  `;
  let prev = null,
    who = null;
  indices.forEach((index, j) => {
    const m = messages[index],
      t = Date.parse(m.datetime_iso),
      gap = prev === null || t - prev > 900000;
    if (gap) {
      html += /* HTML */ `
        <div class="stamp">
          <b>${date(m.datetime_iso)}</b>
          · ${time(m.datetime_iso)}
        </div>
      `;
      who = null;
    }
    const side = m.sender === 'Elizabeth Holmes' ? 'e' : 's',
      first = who !== m.sender;
    const next = messages[indices[j + 1]],
      last = !next || next.sender !== m.sender || Date.parse(next.datetime_iso) - t > 900000;
    html += /* HTML */ `
      <div
        class="row ${side}${first ? ' first' : ''}${last ? ' last' : ''}"
        id="message-${index}"
        data-record="${esc(m.record)}"
      >
        ${
          first
            ? /* HTML */ `
                <div class="name">${esc(m.sender)}</div>
              `
            : ''
        }
        <button
          class="bubble"
          type="button"
          aria-expanded="false"
          aria-controls="meta-${index}"
          aria-label="${esc(m.sender + ': ' + (m.text || '[No message text printed]') + '. ' + m.datetime_raw)}"
        >
          ${formatText(m.text)}
        </button>
        ${
          m.uncertain
            ? /* HTML */ `
                <div class="uncertain">Reading note: ${esc(m.notes.join(' '))}</div>
              `
            : ''
        }
        <div class="t" id="meta-${index}" hidden>
          <button class="conversation-inline" data-context="${c.id}">
            See full conversation →
          </button>
          <div>${esc(m.datetime_raw)} · presumed UTC</div>
          <details class="source-details">
            <summary>Sources &amp; record details</summary>
            <div>${esc(m.record)}</div>
            <div>To: ${esc(m.recipient || '[Not printed]')}</div>
            <div>${m.sources.map(sourceLink).join(' ')}</div>
            ${
              m.attachments
                ? /* HTML */ `
                    <div>Attachments: ${esc(m.attachments)}</div>
                  `
                : ''
            }
          </details>
        </div>
      </div>
    `;
    prev = t;
    who = m.sender;
  });
  return (
    html + /* HTML */ `<div class="conversation-footer">${conversationAction(c)}</div></section>`
  );
}
function renderToc() {
  $('timelineStatus').textContent =
    tag || query
      ? `Showing ${visible.length} conversations matching the message search and theme filter. Theme and incident indexes always cover all exhibits.`
      : `All ${conversations.length} conversations, grouped by season.`;
  let html = '',
    period = '';
  visible.forEach(({ c, n, indices }) => {
    if (period !== c.period) {
      if (period) html += '</ul>';
      period = c.period;
      html += /* HTML */ `
        <div class="era">${esc(period)}</div>
        <ul class="toc"></ul>
      `;
    }
    html += /* HTML */ `
      <li>
        <a href="${textURL(c.id)}" data-go="${c.id}">
          <span class="n">${n + 1}</span>
          <span class="tt">${esc(c.title)}</span>
          <span class="dd">
            ${date(c.start)} · ${indices.length} ${indices.length === 1 ? 'record' : 'records'}
          </span>
          <span class="ds">${esc(c.description)}</span>
        </a>
      </li>
    `;
  });
  $('toc').innerHTML =
    html + (period ? '</ul>' : '<p class="empty">No matching conversations.</p>');
}
function conversationLink(id) {
  const c = byConversation.get(id);
  return /* HTML */ `
    <li>
      <a href="${textURL(id)}" data-jump-conversation="${id}">
        ${esc(c.title)}
        <small>
          ${date(c.start)} · ${c.messages.length} ${c.messages.length === 1 ? 'record' : 'records'}
        </small>
      </a>
    </li>
  `;
}
function renderThemes() {
  $('themeIndex').innerHTML = themes
    .map((t) => {
      const groups = conversations.filter((c) => c.tags.includes(t.id)),
        topicIncidents = incidents.filter((i) => i.tags.includes(t.id)),
        emails = emailThreads.filter((e) => e.themes.includes(t.id));
      return /* HTML */ `
        <details class="theme-group">
          <summary>
            ${esc(t.label)}
            <span>
              ${groups.length} text conversations · ${topicIncidents.length}
              incidents${emails.length ? ' · ' + emails.length + ' email exchanges' : ''}
            </span>
          </summary>
          <div class="theme-content">
            <p>${esc(t.description)}</p>
            <button class="open-toc" data-theme-conversations="${t.id}">
              Read all ${groups.length} text conversations →
            </button>
            <button class="open-toc" data-theme-incidents="${t.id}">
              Explore ${topicIncidents.length} incidents →
            </button>
            ${
              emails.length
                ? /* HTML */ `
                    <button class="open-toc" data-theme-emails="${t.id}">
                      Read ${emails.length} email exchanges →
                    </button>
                  `
                : ''
            }
            <ul class="index-links">
              ${groups.map((c) => conversationLink(c.id)).join('')}
            </ul>
          </div>
        </details>
      `;
    })
    .join('');
}
function renderIncidents() {
  const theme = $('incidentTheme').value,
    needle = $('incidentSearch').value.trim().toLowerCase();
  const found = incidents.filter(
    (i) =>
      (!theme || i.tags.includes(theme)) &&
      (!needle ||
        [
          i.title,
          i.description,
          i.quote,
          ...i.tags.map((t) => topicLabels[t]),
          ...[i.conversation, ...i.related].map((id) => byConversation.get(id).title),
        ]
          .join(' ')
          .toLowerCase()
          .includes(needle)),
  );
  $('incidentStatus').textContent =
    `${found.length} of ${incidents.length} selected incidents${theme ? ' · ' + topicLabels[theme] : ''}`;
  $('incidentIndex').innerHTML = found.length
    ? found
        .map((i) => {
          const m = messages[byRecord.get(i.record)],
            ids = [i.conversation, ...i.related].sort((a, b) =>
              byConversation.get(a).start.localeCompare(byConversation.get(b).start),
            );
          const start = byConversation.get(ids[0]).start,
            end = byConversation.get(ids[ids.length - 1]).end;
          return /* HTML */ `
            <article class="incident-card" id="incident-card-${i.id}">
              <div class="incident-date">
                ${date(start)}${date(start) !== date(end) ? ' – ' + date(end) : ''}
              </div>
              <h4>${esc(i.title)}</h4>
              <p>${esc(i.description)}</p>
              <blockquote>
                “${esc(i.quote)}”
                <cite>${esc(m.sender)} · ${date(m.datetime_iso)}</cite>
              </blockquote>
              <div class="chips">
                ${i.tags
                  .map(
                    (t) => /* HTML */ `
                      <button class="chip sm" data-theme-incidents="${t}">
                        ${esc(topicLabels[t])}
                      </button>
                    `,
                  )
                  .join('')}
              </div>
              <a
                class="jump-link"
                href="${incidentURL(i.id)}"
                data-incident="${i.id}"
                aria-label="Jump to passage: ${esc(i.title)}"
              >
                Jump to passage →
              </a>
              <button class="conversation-action" data-context="${i.conversation}">
                See full conversation →
              </button>
              ${
                ids.length > 1
                  ? /* HTML */ `
                      <details class="related">
                        <summary>
                          ${ids.length - 1} related
                          ${ids.length === 2 ? 'conversation' : 'conversations'}
                        </summary>
                        <ul class="index-links">
                          ${ids
                            .filter((id) => id !== i.conversation)
                            .map(conversationLink)
                            .join('')}
                        </ul>
                      </details>
                    `
                  : ''
              }
            </article>
          `;
        })
        .join('')
    : '<p class="empty">No incidents match. Try a different word or choose another theme.</p>';
}
function renderEmails() {
  const theme = $('emailTheme').value,
    needle = $('emailSearch').value.trim().toLowerCase();
  const found = emailThreads.filter(
    (t) =>
      (!theme || t.themes.includes(theme)) &&
      (!needle ||
        [
          t.title,
          t.summary,
          t.subject,
          ...t.participants,
          ...t.themes.map((x) => topicLabels[x] || x),
          ...t.messages.flatMap((m) => [m.sender, m.subject, m.text, m.editorial_note || '']),
        ]
          .join(' ')
          .toLowerCase()
          .includes(needle)),
  );
  $('emailStatus').textContent =
    `${found.length} of ${emailThreads.length} email exchanges${theme ? ' · ' + topicLabels[theme] : ''}`;
  $('emailIndex').innerHTML = found.length
    ? found
        .map(
          (t) => /* HTML */ `
            <article class="incident-card email-card" id="email-card-${esc(t.id)}">
              <div class="incident-date">
                ${date(t.date_start)}${t.date_end !== t.date_start ? ' – ' + date(t.date_end) : ''}
                · ${t.messages.length} ${t.messages.length === 1 ? 'email' : 'emails'}
              </div>
              <h4>${esc(t.title)}</h4>
              <p>${esc(t.summary)}</p>
              <p class="email-participants">${esc(t.participants.join(' · '))}</p>
              ${
                t.quote
                  ? /* HTML */ `
                      <blockquote>“${esc(t.quote)}”</blockquote>
                    `
                  : ''
              }
              <div class="chips">
                ${t.themes
                  .map(
                    (theme) => /* HTML */ `
                      <button class="chip sm" data-theme-emails="${esc(theme)}">
                        ${esc(topicLabels[theme] || theme)}
                      </button>
                    `,
                  )
                  .join('')}
              </div>
              <a class="conversation-action" href="${emailURL(t.id)}" data-email="${esc(t.id)}">
                Read email exchange →
                <small>
                  ${t.messages.length === 1 ? 'The email' : 'All ' + t.messages.length + ' emails'}
                  included in the source
                </small>
              </a>
            </article>
          `,
        )
        .join('')
    : '<p class="empty">No email exchanges match. Try another word or choose another theme.</p>';
}

function showIndex(view) {
  if (indexView !== view) $('indexBody').scrollTop = 0;
  indexView = view;
  ['themes', 'incidents', 'emails', 'timeline', 'about'].forEach(
    (v) => ($(v + 'Panel').hidden = v !== view),
  );
  document
    .querySelectorAll('[data-view]')
    .forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.view === view)));
}
let drawerNavigating = false;
function openDrawer(view = indexView) {
  showIndex(view);
  if (!$('drawer').open) {
    drawerTrigger = document.activeElement;
    $('drawer').showModal();
    document.body.style.overflow = 'hidden';
    $('menuBtn').setAttribute('aria-expanded', 'true');
    $('closeBtn').focus();
  }
}
function closeDrawer(navigating = false) {
  if ($('drawer').open) {
    drawerNavigating = navigating;
    $('drawer').close();
  }
}
$('drawer').addEventListener('close', () => {
  document.body.style.overflow = '';
  $('menuBtn').setAttribute('aria-expanded', 'false');
  if (!drawerNavigating)
    (drawerTrigger?.isConnected ? drawerTrigger : $('menuBtn')).focus({ preventScroll: true });
  drawerNavigating = false;
});
$('drawer').addEventListener('click', (e) => {
  if (e.target === $('drawer')) closeDrawer();
});
$('menuBtn').onclick = () => openDrawer();
$('closeBtn').onclick = () => closeDrawer();
$('searchBtn').onclick = () => openSearch();
const sourcePageCounts = Object.fromEntries(publicSources.map((s) => [s.id, s.pages]));
let sourcePart = '',
  sourcePage = 1,
  sourceTrigger = null,
  sourceReturnHash = '',
  sourceHistoryEntry = false,
  sourceOverflow = '';
function showSourcePage(part, page) {
  sourcePart = part;
  sourcePage = page;
  const source = bySource.get(part);
  $('sourceTitle').firstChild.textContent = source.label;
  $('sourceCaption').textContent =
    source.public_copy_note || 'Original court exhibit · scanned page';
  $('sourcePage').textContent = `${page} / ${sourcePageCounts[part]}`;
  $('sourcePrev').disabled = page === 1;
  $('sourceNext').disabled = page === sourcePageCounts[part];
  $('sourcePDF').href = `${source.file}#page=${page}`;
  $('sourceStatus').textContent = 'Loading original page…';
  $('sourceImage').hidden = true;
  $('sourceImage').alt = `${source.label}, original PDF page ${page}`;
  $('sourceImage').src = `${source.image_prefix}${String(page).padStart(3, '0')}.webp`;
  $('sourceStage').scrollTo(0, 0);
}
function openSource(part, page, updateURL = true) {
  if (
    !sourcePageCounts[part] ||
    !Number.isInteger(page) ||
    page < 1 ||
    page > sourcePageCounts[part]
  )
    return;
  if (!$('sourceViewer').open) {
    sourceTrigger = document.activeElement;
    sourceReturnHash = location.hash.startsWith('#source-') ? '' : location.hash;
    sourceHistoryEntry = updateURL;
    sourceOverflow = document.body.style.overflow;
    $('sourceStage').classList.remove('zoomed');
    $('sourceZoom').textContent = 'Zoom in';
    $('sourceZoom').setAttribute('aria-pressed', 'false');
    $('sourceViewer').showModal();
    document.body.style.overflow = 'hidden';
    $('sourceClose').focus();
  }
  showSourcePage(part, page);
  if (updateURL) setHash(`source-${part}-${page}`);
}
function closeSource() {
  if (sourceHistoryEntry && location.hash.startsWith('#source-')) history.back();
  else {
    $('sourceViewer').close();
    history.replaceState(null, '', location.pathname + location.search + sourceReturnHash);
  }
}
$('sourceImage').onload = () => {
  $('sourceImage').hidden = false;
  $('sourceStatus').textContent =
    'Zoom in for small print, then scroll or swipe to move around the page.';
};
$('sourceImage').onerror = () => {
  $('sourceStatus').textContent =
    'This page could not load. Try the previous/next controls or open the full PDF.';
};
$('sourceClose').onclick = closeSource;
$('sourceViewer').addEventListener('cancel', (e) => {
  e.preventDefault();
  closeSource();
});
$('sourceViewer').addEventListener('close', () => {
  document.body.style.overflow = sourceOverflow;
  if (sourceTrigger?.isConnected) sourceTrigger.focus({ preventScroll: true });
});
function turnSourcePage(delta) {
  const page = sourcePage + delta;
  if (page < 1 || page > sourcePageCounts[sourcePart]) return;
  showSourcePage(sourcePart, page);
  history.replaceState(null, '', `#source-${sourcePart}-${page}`);
}
$('sourcePrev').onclick = () => turnSourcePage(-1);
$('sourceNext').onclick = () => turnSourcePage(1);
$('sourceZoom').onclick = () => {
  const zoomed = $('sourceStage').classList.toggle('zoomed');
  $('sourceZoom').textContent = zoomed ? 'Fit page' : 'Zoom in';
  $('sourceZoom').setAttribute('aria-pressed', String(zoomed));
};
$('incidentTheme').innerHTML =
  '<option value="">All themes</option>' +
  themes
    .map(
      (t) => /* HTML */ `
        <option value="${t.id}">${esc(t.label)}</option>
      `,
    )
    .join('');
$('incidentSearch').addEventListener('input', renderIncidents);
$('incidentTheme').addEventListener('change', renderIncidents);
$('emailTheme').innerHTML =
  '<option value="">All themes</option>' +
  themes
    .filter((t) => emailThreads.some((e) => e.themes.includes(t.id)))
    .map(
      (t) => /* HTML */ `
        <option value="${t.id}">${esc(t.label)}</option>
      `,
    )
    .join('');
$('emailSearch').addEventListener('input', renderEmails);
$('emailTheme').addEventListener('change', renderEmails);
$('emailScope').textContent = data.emails.scope_note;
renderThemes();
renderIncidents();
renderEmails();
$('filterChips').innerHTML =
  '<button class="chip on" data-filter="" aria-pressed="true">All</button>' +
  Object.entries(topicLabels)
    .map(
      ([k, v]) => /* HTML */ `
        <button class="chip" data-filter="${k}" aria-pressed="false">${esc(v)}</button>
      `,
    )
    .join('');
$('stats').textContent =
  `${messages.length.toLocaleString()} text records · ${conversations.length} text conversations · ${emailThreads.length} email exchanges`;
$('about').innerHTML = /* HTML */ `
  <details open>
    <summary>About this collection</summary>
    <div class="about-copy">
      <p>
        The text timeline combines Trial Exhibits 5387A–I and additional public docket exhibits from
        <i>United States v. Holmes</i>
        and
        <i>United States v. Balwani</i>
        . These sources contain excerpts of iPhone and Skype records, not a complete message
        history. Gaps can hide texts that were not included. Spelling and typos are retained; black
        bars mark redactions. A blank-message marker is editorial, not message text.
      </p>
      <p>
        Timestamps are copied as printed. They appear to be UTC rather than California time: on
        September 22, 2015 a “lunch break” falls at 7:52 PM, approximately 12:52 PM Pacific.
        Late-night times may belong to the previous evening locally. No local-time conversion is
        applied.
      </p>
      <p>
        A new conversation begins after a gap of three hours or more. Titles, descriptions, and
        theme tags are editorial navigation aids based on the messages. A tag applies to the
        conversation as a whole.
      </p>
      <p>
        Repeated record IDs across exhibits appear once in the timeline, with every source retained.
        Different record IDs with identical text remain separate. The clearer checked transcription
        is used where scans overlap. The supplied Part B reader was used to check all 293 Part B
        records.
      </p>
      <table>
        <thead>
          <tr>
            <th>Source</th>
            <th>PDF pages</th>
            <th>Source rows</th>
          </tr>
        </thead>
        <tbody>
          ${Object.entries(importReport.rows_per_exhibit)
            .map(
              ([p, n]) => /* HTML */ `
                <tr>
                  <td><a href="#source-${p}-1" data-source="${p}" data-page="1">${p}</a></td>
                  <td>${sourcePageCounts[p] ?? '—'}</td>
                  <td>${n.toLocaleString()}</td>
                </tr>
              `,
            )
            .join('')}
        </tbody>
      </table>
      <p>
        ${importReport.source_rows.toLocaleString()} source rows;
        ${importReport.distinct_records.toLocaleString()} distinct records.
        ${importReport.pages_reviewed.toLocaleString()} source pages reviewed. The source documents
        remain available for checking omissions and uncertain readings.
      </p>
      ${publicSources
        .filter((s) => s.public_copy_note)
        .map(
          (s) => /* HTML */ `
            <p>${esc(s.label)}: ${esc(s.public_copy_note)}</p>
          `,
        )
        .join('')}
      <p>
        <a href="data/messages.json" download>Transcript JSON</a>
        ·
        <a href="data/page-review.csv" download>Page-by-page row audit</a>
        ·
        <a href="exhibits/manifest.json">Court source URLs and file checksums</a>
      </p>
      <p>
        The Emails explorer contains ${emailThreads.length} selected exchanges
        (${emailThreads.reduce((n, t) => n + t.messages.length, 0)} emails) from public trial
        exhibits. Email dates retain their printed timezones. Selection notes and original pages are
        available within each exchange.
      </p>
      <p><a href="data/emails.json" download>Email transcript JSON</a></p>
      <h4>Reading notes</h4>
      ${importReport.uncertain_records
        .map(
          (u) => /* HTML */ `
            <p>${esc(u.record)}: ${esc(u.notes.join(' '))}</p>
          `,
        )
        .join('')}
      <h4>Shorthand</h4>
      <dl>
        <dt>CTN</dt>
        <dd>Capillary tube nanotainer</dd>
        <dt>fs · vp</dt>
        <dd>Fingerstick · venipuncture</dd>
        <dt>PSC</dt>
        <dd>Patient service center</dd>
        <dt>wag · swy</dt>
        <dd>Walgreens · Safeway</dd>
        <dt>tat</dt>
        <dd>Turnaround time</dd>
        <dt>LDT</dt>
        <dd>Lab-developed test</dd>
        <dt>PMA</dt>
        <dd>Premarket approval</dd>
        <dt>Normandy</dt>
        <dd>Name for part of the clinical lab</dd>
      </dl>
    </div>
  </details>
`;
let timer;
$('search').addEventListener('input', () => {
  clearTimeout(timer);
  timer = setTimeout(updateSearch, 150);
});
$('clear').onclick = () => {
  tag = '';
  $('search').value = '';
  updateSearch();
  $('search').focus();
};
document.addEventListener('click', (e) => {
  const nativeLink = e.target.closest('a[href]');
  if (nativeLink && (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0)) return;
  const home = e.target.closest('[data-home],[data-return-reading],[data-return-emails]');
  if (home) {
    e.preventDefault();
    backToBrowsing();
    return;
  }
  if (e.target.closest('[data-open-search]')) {
    e.preventDefault();
    openSearch();
    return;
  }
  const topic = e.target.closest('[data-home-theme]');
  if (topic) {
    e.preventDefault();
    homeTheme = topic.dataset.homeTheme;
    feedLimit = 8;
    navigate(homeTheme ? 'highlights-' + homeTheme : '', 0);
    return;
  }
  const suggested = e.target.closest('[data-search]');
  if (suggested) {
    $('search').value = suggested.dataset.search;
    updateSearch();
    return;
  }
  const source = e.target.closest('[data-source]');
  if (source) {
    e.preventDefault();
    openSource(source.dataset.source, Number(source.dataset.page));
    return;
  }
  const email = e.target.closest('[data-email]');
  if (email) {
    e.preventDefault();
    jumpEmail(email.dataset.email);
    return;
  }
  const incident = e.target.closest('[data-incident]');
  if (incident) {
    e.preventDefault();
    jumpIncident(incident.dataset.incident);
    return;
  }
  const view = e.target.closest('[data-view],[data-open-view]');
  if (view) {
    e.preventDefault();
    openDrawer(view.dataset.view ?? view.dataset.openView);
    return;
  }
  const emailsTheme = e.target.closest('[data-theme-emails]');
  if (emailsTheme) {
    $('emailTheme').value = emailsTheme.dataset.themeEmails;
    $('emailSearch').value = '';
    renderEmails();
    openDrawer('emails');
    $('indexBody').scrollTop = 0;
    return;
  }
  const incidentsTheme = e.target.closest('[data-theme-incidents]');
  if (incidentsTheme) {
    $('incidentTheme').value = incidentsTheme.dataset.themeIncidents;
    $('incidentSearch').value = '';
    renderIncidents();
    openDrawer('incidents');
    $('indexBody').scrollTop = 0;
    return;
  }
  const theme = e.target.closest('[data-theme-conversations]');
  if (theme) {
    openSearch(theme.dataset.themeConversations);
    return;
  }
  const conversation = e.target.closest('[data-jump-conversation],[data-go],[data-context]');
  if (conversation) {
    e.preventDefault();
    jumpConversation(
      conversation.dataset.jumpConversation ||
        conversation.dataset.go ||
        conversation.dataset.context,
    );
    return;
  }
  const filter = e.target.closest('[data-filter],[data-tag]');
  if (filter) {
    tag = filter.dataset.filter ?? filter.dataset.tag;
    if (pageMode !== 'search') openSearch(tag);
    else updateSearch();
    return;
  }
  const bubble = e.target.closest('button.bubble');
  if (bubble) {
    const meta = $(bubble.getAttribute('aria-controls'));
    meta.hidden = !meta.hidden;
    bubble.setAttribute('aria-expanded', String(!meta.hidden));
  }
});
function theme() {
  return (
    document.documentElement.dataset.theme ||
    (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
  );
}
function themeLabel() {
  $('themeBtn').setAttribute(
    'aria-label',
    `Switch to ${theme() === 'dark' ? 'light' : 'dark'} mode`,
  );
}
try {
  const saved = localStorage.getItem('hbt-theme');
  if (['dark', 'light'].includes(saved)) document.documentElement.dataset.theme = saved;
} catch (e) {}
$('themeBtn').onclick = () => {
  document.documentElement.dataset.theme = theme() === 'dark' ? 'light' : 'dark';
  try {
    localStorage.setItem('hbt-theme', theme());
  } catch (e) {}
  themeLabel();
};
themeLabel();
addEventListener('hashchange', followHash);
$('searchBtn').hidden = false;
$('menuBtn').hidden = false;
followHash(true);
