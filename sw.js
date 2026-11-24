/* Mednomics 설치형 웹앱 서비스 워커: 한 번 본 페이지는 인터넷이 없어도 열린다. */
const CACHE = 'mn-7613ccee85';
const CORE = ["/", "/en/", "/style.css", "/protect.js", "/assets/app.js", "/assets/news.js", "/assets/search.js", "/assets/favicon.svg", "/assets/icons/icon-192.png", "/manifest.webmanifest", "/en/manifest.webmanifest", "/news/", "/en/news/", "/insight/", "/en/insight/", "/series/", "/en/series/", "/saved.html", "/en/saved.html"];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k.startsWith('mn-') && k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== location.origin) return;
  const url = new URL(req.url);
  if (req.mode === 'navigate' || url.pathname.endsWith('.json') || url.pathname.endsWith('.xml')) {   // 페이지·데이터: 새 것을 먼저
    e.respondWith(fetch(req).then(res => {
      if (res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); }
      return res;
    }).catch(() => caches.match(req, { ignoreSearch: true }).then(hit => hit || caches.match(url.pathname.startsWith('/en/') ? '/en/' : '/'))));
    return;
  }
  e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(res => {   // 그 밖: 저장해 둔 것을 먼저
    if (res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); }
    return res;
  })));
});
