/* Mednomics 웹앱: 하단 탭바 더보기, 앱 설치, 저장한 글, D-day, 뉴스 분야 필터, 오프라인 */
(function(){
  var EN = (document.documentElement.lang || '').indexOf('en') === 0;
  var S = EN ? {
    save: 'Save', saved: 'Saved', savedToast: 'Saved. Find it under More → Saved.', removed: 'Removed from saved.',
    today: 'Today', past: 'Done', on: 'On now', dplus: 'D+', news: 'News', article: 'Article', cleared: 'Cleared.'
  } : {
    save: '저장', saved: '저장됨', savedToast: '저장했습니다. 더보기 → 저장한 글에서 볼 수 있습니다.', removed: '저장을 취소했습니다.',
    today: '오늘', past: '지남', on: '진행 중', dplus: 'D+', news: '뉴스', article: '연재', cleared: '모두 지웠습니다.'
  };
  function root(){ var l = document.querySelector('link[rel=icon]'); return l ? l.getAttribute('href').replace('assets/favicon.svg','') : '/'; }
  function toast(m){
    var t = document.getElementById('toast'); if(!t) return;
    t.textContent = m; t.classList.add('on'); clearTimeout(t._h); t._h = setTimeout(function(){ t.classList.remove('on'); }, 2400);
  }

  /* 서비스 워커: 설치형 웹앱과 오프라인 읽기 */
  if('serviceWorker' in navigator && (location.protocol === 'https:' || location.hostname === 'localhost')){
    window.addEventListener('load', function(){ navigator.serviceWorker.register(root() + 'sw.js').catch(function(){}); });
  }

  /* 더보기 시트 */
  var sheet = document.getElementById('more-sheet'), mo = document.getElementById('more-open'), mc = document.getElementById('more-close');
  function closeSheet(){ if(sheet){ sheet.hidden = true; document.body.classList.remove('sheet-on'); } }
  if(sheet && mo){
    mo.addEventListener('click', function(){ sheet.hidden = false; document.body.classList.add('sheet-on'); });
    mc && mc.addEventListener('click', closeSheet);
    sheet.addEventListener('click', function(e){ if(e.target === sheet) closeSheet(); });
    document.addEventListener('keydown', function(e){ if(e.key === 'Escape') closeSheet(); });
  }

  /* 앱 설치 */
  var standalone = window.matchMedia('(display-mode: standalone)').matches || navigator.standalone;
  if(standalone) document.documentElement.classList.add('is-app');
  var deferred = null, ib = document.getElementById('install-app'), ios = document.getElementById('install-ios');
  window.addEventListener('beforeinstallprompt', function(e){ e.preventDefault(); deferred = e; if(ib) ib.hidden = false; });
  if(ib) ib.addEventListener('click', function(){ if(!deferred) return; deferred.prompt(); deferred.userChoice.finally(function(){ deferred = null; ib.hidden = true; }); });
  if(ios && !standalone && /iphone|ipad|ipod/i.test(navigator.userAgent)) ios.hidden = false;

  /* 저장한 글 */
  var KEY = 'mn-saved';
  function load(){ try { return JSON.parse(localStorage.getItem(KEY) || '[]'); } catch(e){ return []; } }
  function store(a){ try { localStorage.setItem(KEY, JSON.stringify(a)); } catch(e){} }
  function has(u){ return load().some(function(x){ return x.u === u; }); }
  function mark(b){ var on = has(b.getAttribute('data-save')); b.setAttribute('aria-pressed', on ? 'true' : 'false'); b.textContent = on ? S.saved : S.save; }
  function toggle(b){
    var u = b.getAttribute('data-save'), a = load(), i = -1;
    a.forEach(function(x, k){ if(x.u === u) i = k; });
    if(i > -1){ a.splice(i, 1); toast(S.removed); }
    else { a.unshift({u: u, t: b.getAttribute('data-title') || document.title, k: b.getAttribute('data-kind') || 'article', d: new Date().toISOString().slice(0, 10)}); toast(S.savedToast); }
    store(a.slice(0, 200)); document.querySelectorAll('[data-save]').forEach(mark); renderSaved();
  }
  var head = document.querySelector('.post-head .in');
  if(head && !head.querySelector('[data-save]')){
    var h1 = head.querySelector('h1'), b = document.createElement('button');
    b.type = 'button'; b.className = 'savebtn'; b.setAttribute('data-save', (document.querySelector('link[rel=canonical]') || location).href);
    b.setAttribute('data-title', h1 ? h1.textContent.trim() : document.title); b.setAttribute('data-kind', 'article');
    (h1 && h1.nextSibling) ? head.insertBefore(b, h1.nextSibling) : head.appendChild(b);
  }
  document.querySelectorAll('[data-save]').forEach(mark);
  document.addEventListener('click', function(e){ var b = e.target.closest && e.target.closest('[data-save]'); if(b){ e.preventDefault(); toggle(b); } });
  function esc(s){ return String(s).replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
  function renderSaved(){
    var ul = document.getElementById('saved-list'); if(!ul) return;
    var a = load();
    ul.innerHTML = a.length ? a.map(function(x){
      return '<li><a href="' + esc(x.u) + '"><span class="meta">' + (x.k === 'news' ? S.news : S.article) + ' · ' + esc(x.d) + '</span><h3>' + esc(x.t) + '</h3></a></li>';
    }).join('') : '<li class="empty"><p>' + esc(ul.getAttribute('data-empty')) + '</p></li>';
  }
  renderSaved();
  var clr = document.getElementById('saved-clear');
  if(clr) clr.addEventListener('click', function(){ store([]); renderSaved(); toast(S.cleared); });

  /* 일정 D-day */
  var now = new Date(); now.setHours(0, 0, 0, 0);
  document.querySelectorAll('[data-dday]').forEach(function(li){
    var d = new Date(li.getAttribute('data-dday') + 'T00:00:00'), end = li.getAttribute('data-end');
    var e = end ? new Date(end + 'T00:00:00') : d, diff = Math.round((d - now) / 864e5), slot = li.querySelector('.dd');
    if(!slot) return;
    if(now > e){ slot.textContent = S.past; li.classList.add('past'); }
    else if(now >= d && now <= e && diff !== 0){ slot.textContent = S.on; li.classList.add('near'); }
    else if(diff === 0){ slot.textContent = S.today; li.classList.add('near'); }
    else { slot.textContent = 'D-' + diff; if(diff <= 7) li.classList.add('near'); }
  });

  /* 뉴스 분야 필터 */
  var chips = document.querySelectorAll('.fchip[data-filter]'), list = document.getElementById('news-filter');
  if(chips.length && list){
    chips.forEach(function(c){ c.addEventListener('click', function(){
      var f = c.getAttribute('data-filter');
      chips.forEach(function(x){ x.setAttribute('aria-pressed', x === c ? 'true' : 'false'); });
      list.querySelectorAll('li').forEach(function(li){ li.hidden = !!f && li.getAttribute('data-cat') !== f; });
    }); });
  }
})();
