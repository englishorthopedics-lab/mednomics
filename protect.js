/* 저작권 보호: 우클릭·드래그·복사·인쇄 제한, 복사 시 출처 추가 */
(function(){
  var SRC = '닥터조단, mednomics.co.kr';
  function inMail(t){ return t && t.closest && t.closest('a[href^="mailto:"], input, textarea'); }
  document.addEventListener('contextmenu', function(e){ if(!inMail(e.target)) e.preventDefault(); });
  document.addEventListener('dragstart', function(e){ e.preventDefault(); });
  document.addEventListener('selectstart', function(e){ if(!inMail(e.target)) e.preventDefault(); });
  document.addEventListener('keydown', function(e){
    var k = (e.key || '').toLowerCase();
    if((e.ctrlKey || e.metaKey) && ['c','a','s','u','p'].indexOf(k) > -1){
      var sel = window.getSelection ? String(window.getSelection()) : '';
      if(k === 'c' && sel && inMail(document.activeElement)) return;
      e.preventDefault();
    }
  });
  document.addEventListener('copy', function(e){
    var sel = window.getSelection ? String(window.getSelection()) : '';
    if(!sel || !e.clipboardData) return;
    e.clipboardData.setData('text/plain', sel + '\n\n출처: ' + SRC + ' (' + location.href + ')');
    e.preventDefault();
  });
  /* 읽기 진행 막대 */
  var bar = document.getElementById('progress');
  if(bar){
    var upd = function(){
      var h = document.documentElement, max = h.scrollHeight - h.clientHeight;
      bar.style.width = (max > 0 ? (h.scrollTop / max) * 100 : 0) + '%';
    };
    window.addEventListener('scroll', upd, {passive:true}); upd();
  }
})();
