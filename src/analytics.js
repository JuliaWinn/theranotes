// A separate GoatCounter site for Theranotes. The endpoint is public, not a secret.
// Only production loads analytics; previews and local copies never contact GoatCounter.
const recordReaderView = (() => {
  if (location.hostname !== 'theranotes.juliawinn.com') return () => {};
  window.goatcounter = { no_onload: true, no_events: true };
  let pending = [],
    lastPath = '';
  function flush() {
    if (typeof window.goatcounter.count !== 'function' || document.visibilityState === 'hidden')
      return;
    const views = pending;
    pending = [];
    for (const view of views) {
      try {
        window.goatcounter.count(view);
      } catch (error) {
        /* Analytics must not interrupt reading. */
      }
    }
  }
  const script = document.createElement('script');
  script.async = true;
  script.src = 'https://gc.zgo.at/count.js';
  script.dataset.goatcounter = 'https://theranotes.goatcounter.com/count';
  script.onload = flush;
  script.onerror = () => {
    pending = [];
  };
  document.head.appendChild(script);
  document.addEventListener('visibilitychange', flush);
  return (path, title) => {
    if (path === lastPath) return;
    lastPath = path;
    // Bound the queue if an ad blocker prevents the script from loading.
    pending.push({ path, title });
    pending = pending.slice(-50);
    flush();
  };
})();
