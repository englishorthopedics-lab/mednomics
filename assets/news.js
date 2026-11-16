/* Mednomics 뉴스 공유: 기본 공유창, 카톡·문자용 텍스트 복사, 링크 복사, SNS */
(function(){
  var el = document.getElementById('brief-data');
  var B = null;
  try { B = el ? JSON.parse(el.textContent) : null; } catch(e) {}
  var pageUrl = (B && B.url) || location.href.split('#')[0];
  var pageTitle = B ? (B.label + ' 의료 뉴스 · ' + B.headline) : document.title;

  function toast(msg){
    var t = document.getElementById('toast'); if(!t) return;
    t.textContent = msg; t.classList.add('on');
    clearTimeout(t._h); t._h = setTimeout(function(){ t.classList.remove('on'); }, 2200);
  }
  function copy(text){
    if(navigator.clipboard && window.isSecureContext){
      return navigator.clipboard.writeText(text).then(function(){ return true; }, function(){ return legacy(text); });
    }
    return Promise.resolve(legacy(text));
  }
  function legacy(text){
    var ta = document.createElement('textarea');
    ta.value = text; ta.setAttribute('readonly',''); ta.style.position='fixed'; ta.style.opacity='0';
    document.body.appendChild(ta); ta.select();
    var ok = false; try { ok = document.execCommand('copy'); } catch(e) {}
    document.body.removeChild(ta); return ok;
  }
  function briefText(){
    if(!B) return pageTitle + '\n' + pageUrl;
    var lines = ['[Mednomics 의료 뉴스 · ' + B.label + ']', B.headline, ''];
    B.items.forEach(function(it){ lines.push(it.n + '. ' + it.title); });
    lines.push('', '요약과 원문 링크 ▶ ' + pageUrl, '(닥터조단, mednomics.co.kr)');
    return lines.join('\n');
  }
  function itemText(n){
    var it = B && B.items.filter(function(x){ return String(x.n) === String(n); })[0];
    if(!it) return briefText();
    return '[Mednomics 의료 뉴스 · ' + B.label + ']\n' + it.title + '\n\n' + it.summary +
      '\n\n원문 링크와 전체 브리핑 ▶ ' + pageUrl + '#n' + it.n + '\n(닥터조단, mednomics.co.kr)';
  }
  function open(u){ window.open(u, '_blank', 'noopener,width=620,height=640'); }
  var enc = encodeURIComponent;

  document.addEventListener('click', function(e){
    var b = e.target.closest && e.target.closest('[data-share]'); if(!b) return;
    var kind = b.getAttribute('data-share');
    if(kind === 'native'){
      if(navigator.share){ navigator.share({title: pageTitle, text: B ? B.headline : '', url: pageUrl}).catch(function(){}); }
      else { copy(briefText()).then(function(){ toast('브리핑이 복사됐습니다. 카톡이나 문자에 붙여 넣으세요.'); }); }
    } else if(kind === 'text'){
      copy(briefText()).then(function(){ toast('브리핑이 복사됐습니다. 카톡이나 문자에 붙여 넣으세요.'); });
    } else if(kind === 'link'){
      copy(pageUrl).then(function(){ toast('링크가 복사됐습니다.'); });
    } else if(kind === 'item'){
      var n = b.getAttribute('data-n'), t = itemText(n);
      if(navigator.share && /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent)){
        navigator.share({title: pageTitle, text: t}).catch(function(){});
      } else { copy(t).then(function(){ toast('이 소식이 복사됐습니다.'); }); }
    } else if(kind === 'naver'){
      open('https://share.naver.com/web/shareView?url=' + enc(pageUrl) + '&title=' + enc(pageTitle));
    } else if(kind === 'band'){
      open('https://band.us/plugin/share?body=' + enc(pageTitle + '\n' + pageUrl) + '&route=' + enc(location.hostname));
    } else if(kind === 'facebook'){
      open('https://www.facebook.com/sharer/sharer.php?u=' + enc(pageUrl));
    } else if(kind === 'x'){
      open('https://twitter.com/intent/tweet?text=' + enc(pageTitle) + '&url=' + enc(pageUrl));
    }
  });

  /* 공유 링크로 들어온 소식은 잠깐 강조 */
  if(location.hash && /^#n\d+$/.test(location.hash)){
    var t = document.querySelector(location.hash);
    if(t){ t.classList.add('hit'); setTimeout(function(){ t.classList.remove('hit'); }, 2600); }
  }
})();
