(function(){
  var data=null;
  function load(cb){ if(data) return cb(); var b=document.querySelector('link[rel=icon]').getAttribute('href').replace('assets/favicon.svg','');
    fetch(b+'search-index.json').then(function(r){return r.json()}).then(function(j){data=j;cb()}).catch(function(){data=[];cb()}); }
  function base(){ return document.querySelector('link[rel=icon]').getAttribute('href').replace('assets/favicon.svg',''); }
  function esc(s){ return s.replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]}); }
  function run(q,ul){
    q=q.trim().toLowerCase(); if(!q){ul.innerHTML='';return;}
    var ws=q.split(/\s+/), out=[];
    data.forEach(function(e){ var h=(e.t+' '+e.d+' '+e.x).toLowerCase(), sc=0;
      for(var i=0;i<ws.length;i++){ if(h.indexOf(ws[i])<0){sc=-1;break;} sc+= e.t.toLowerCase().indexOf(ws[i])>-1?5:1; }
      if(sc>0) out.push([sc,e]); });
    out.sort(function(a,b){return b[0]-a[0]});
    ul.innerHTML=out.length?out.slice(0,12).map(function(r){return '<li><a href="'+base()+r[1].u+'"><b>'+esc(r[1].t)+'</b><span>'+esc(r[1].d)+'</span></a></li>'}).join(''):'<li><span>검색 결과가 없습니다.</span></li>';
  }
  var ov=document.getElementById('search'), q=document.getElementById('q'), ul=document.getElementById('results');
  var ob=document.getElementById('open-search'), cb=document.getElementById('close-search');
  if(ob&&ov){
    ob.addEventListener('click',function(){ov.hidden=false;load(function(){});q.focus();});
    cb.addEventListener('click',function(){ov.hidden=true;});
    ov.addEventListener('click',function(e){if(e.target===ov)ov.hidden=true;});
    document.addEventListener('keydown',function(e){if(e.key==='Escape')ov.hidden=true;});
    q.addEventListener('input',function(){load(function(){run(q.value,ul)})});
  }
  var q2=document.getElementById('q2'), r2=document.getElementById('results2');
  if(q2){ var m=location.search.match(/[?&]q=([^&]+)/); if(m){q2.value=decodeURIComponent(m[1].replace(/\+/g,' '));load(function(){run(q2.value,r2)});}
    q2.addEventListener('input',function(){load(function(){run(q2.value,r2)})}); }
})();
