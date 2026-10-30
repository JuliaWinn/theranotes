'use strict';
// Optional enhancements. The transcript, citations and navigation are all HTML.
const copyButton = document.querySelector('[data-copy-link]');
if (copyButton && navigator.clipboard && window.isSecureContext) {
  copyButton.hidden = false;
  copyButton.addEventListener('click', async () => {
    const status = document.querySelector('[data-copy-status]');
    try {
      await navigator.clipboard.writeText(document.querySelector('link[rel="canonical"]').href);
      status.textContent = 'Link copied';
    } catch {
      status.textContent = 'You can copy the address from your browser.';
    }
  });
}
const readingKey = document.body.dataset.readingKey;
if (readingKey) {
  try {
    const seen = new Set(JSON.parse(localStorage.getItem('tn-seen') || '[]'));
    seen.add(readingKey);
    localStorage.setItem('tn-seen', JSON.stringify([...seen].slice(-500)));
  } catch {
    /* Reading works with storage disabled. */
  }
}
// Same production-only analytics as the existing reader; never record a query or fragment.
recordReaderView(location.pathname, document.title);
