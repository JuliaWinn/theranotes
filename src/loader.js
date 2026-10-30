'use strict';
fetch('TRANSCRIPT_URL')
  .then((response) => {
    if (!response.ok) throw new Error('Transcript unavailable');
    return response.text();
  })
  .then((text) => {
    const data = document.createElement('script');
    data.type = 'application/json';
    data.id = 'transcript';
    data.textContent = text;
    document.body.appendChild(data);
    const app = document.createElement('script');
    app.src = 'READER_URL';
    document.body.appendChild(app);
  })
  .catch(() => {
    // The HTML archive and its links remain available when search cannot load.
  });
