/* algo 共通: 目次・ナビ・ステップ実行エンジン・コードタブ */
(function(){
'use strict';
window.ALGO_TOPICS=[
 {id:'bitfull',   t:'全探索と bit 全探索', d:'「全部試す」を正しく速く。2^N 通りの選び方を整数1つで回す', lv:1},
 {id:'binsearch',t:'二分探索',           d:'「答えで二分探索」まで。ok/ng の めぐる式で境界を確実に取る', lv:1},
 {id:'prefixsum',t:'累積和・いもす法',   d:'区間の和を O(1) に。差分を積んで最後に累積するいもす法', lv:1},
 {id:'twoptr',   t:'尺取り法',           d:'条件を満たす区間を、左右のポインタを戻さずに数える', lv:1},
 {id:'bfs',      t:'BFS と DFS',         d:'グリッド・グラフの最短経路と連結成分。キューと再帰', lv:1},
 {id:'dp',       t:'動的計画法 (DP)',    d:'ナップサックで「表を埋める」感覚をつかむ。遷移の書き方', lv:2},
 {id:'unionfind',t:'Union-Find',         d:'グループ分けの合体と判定をほぼ O(1) で', lv:2},
 {id:'dijkstra', t:'ダイクストラ法',     d:'重み付きグラフの最短路。優先度付きキューで確定していく', lv:2},
 {id:'greedy',   t:'貪欲法とソート',     d:'区間スケジューリング。「終わりが早い順」が正しい理由', lv:2},
 {id:'math',     t:'整数論の道具',       d:'エラトステネスの篩、繰り返し二乗法、mod 逆元', lv:2},
 {id:'segtree',  t:'セグメント木',       d:'区間の和・最小を O(log N) で更新と取得', lv:3},
 {id:'doubling', t:'ダブリング',         d:'K 回先を O(log K) で。LCA への入口', lv:3}
];
var LV={1:'茶→緑',2:'緑→水',3:'水→青'};
var $=function(s,r){return (r||document).querySelector(s)};
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}

/* ---- ナビ ---- */
window.algoNav=function(id){
  var i=ALGO_TOPICS.findIndex(function(t){return t.id===id}),cur=ALGO_TOPICS[i];
  var top=$('#nav');if(top)top.innerHTML='<a href="../">トップ</a> · <a href="./">競プロ アルゴリズム図鑑</a> · '+(i+1)+' / '+ALGO_TOPICS.length;
  var h1=$('h1');if(h1&&cur){var lv=document.createElement('span');lv.className='lv lv'+cur.lv;lv.textContent=LV[cur.lv];h1.parentNode.insertBefore(lv,h1)}
  var pn=$('#pn');if(pn){var p=ALGO_TOPICS[i-1],n=ALGO_TOPICS[i+1];
    pn.className='pn';pn.innerHTML=(p?'<a href="'+p.id+'.html">← '+p.t+'</a>':'<a href="./">← 目次</a>')+'<span class="sp"></span>'+(n?'<a href="'+n.id+'.html">'+n.t+' →</a>':'<a href="./">目次 →</a>')}
};

/* ---- ステップ実行 ---- */
/* Viz(host, gen, {ms, extra:[{label, fn}]}) : gen() は [{h:html, c:caption}] を返す */
window.Viz=function(host,gen,opts){
  opts=opts||{};if(typeof host==='string')host=$(host);
  host.className='viz';
  host.innerHTML='<div class="stage"></div><div class="cap"></div><div class="bar">'+
    '<button type="button" data-a="first" aria-label="最初へ">⏮</button><button type="button" data-a="prev" aria-label="前へ">◀</button>'+
    '<button type="button" class="pri" data-a="play">▶ 再生</button><button type="button" data-a="next" aria-label="次へ">▶|</button>'+
    '<input type="range" min="0" value="0" aria-label="ステップ"><span class="n"></span></div>'+
    (opts.extra?'<div class="extra">'+opts.extra.map(function(e,i){return '<button type="button" data-x="'+i+'">'+e.label+'</button>'}).join('')+'</div>':'');
  var stage=$('.stage',host),cap=$('.cap',host),rng=$('input',host),num=$('.n',host),play=$('[data-a=play]',host);
  var frames=[],i=0,timer=null;
  function show(k){i=Math.max(0,Math.min(frames.length-1,k));stage.innerHTML=frames[i].h;cap.innerHTML=frames[i].c||'';rng.value=i;num.textContent=(i+1)+' / '+frames.length;
    $('[data-a=prev]',host).disabled=i===0;$('[data-a=next]',host).disabled=i===frames.length-1;if(i===frames.length-1)stop()}
  function stop(){if(timer){clearInterval(timer);timer=null}play.textContent='▶ 再生'}
  function start(){if(i===frames.length-1)show(0);timer=setInterval(function(){if(i<frames.length-1)show(i+1);else stop()},opts.ms||800);play.textContent='❚❚ 停止'}
  function load(){frames=gen();rng.max=frames.length-1;stop();show(0)}
  host.addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;
    if(b.dataset.a){var a=b.dataset.a;if(a==='first')show(0);else if(a==='prev'){stop();show(i-1)}else if(a==='next'){stop();show(i+1)}else if(a==='play'){timer?stop():start()}}
    if(b.dataset.x!==undefined){opts.extra[+b.dataset.x].fn();load()}});
  rng.addEventListener('input',function(){stop();show(+this.value)});
  load();
  return {reload:load};
};

/* ---- 部品 ---- */
window.cellsHTML=function(arr,cls,labels,tags){ /* cls[i] = class名, labels[i] = 上の小ラベル, tags[i] = 下のタグ */
  return '<div class="cells'+(labels||tags?' tall':'')+'">'+arr.map(function(v,i){return '<div class="c '+((cls&&cls[i])||'')+'">'+(labels&&labels[i]!=null?'<small>'+labels[i]+'</small>':'')+v+(tags&&tags[i]?'<span class="t">'+tags[i]+'</span>':'')+'</div>'}).join('')+'</div>';
};
window.svgGraph=function(nodes,edges,W,H){ /* nodes:[{x,y,l,cls,sub}], edges:[{a,b,w,cls}] */
  var s='<svg viewBox="0 0 '+W+' '+H+'" width="'+W+'"><defs><marker id="ah" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="userSpaceOnUse"><path d="M0 0L8 4L0 8z" fill="#98A2BC"/></marker><marker id="ahh" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="userSpaceOnUse"><path d="M0 0L8 4L0 8z" fill="#FFB93B"/></marker></defs>';
  edges.forEach(function(e){var a=nodes[e.a],b=nodes[e.b],x1=a.x,y1=a.y,x2=b.x,y2=b.y;
    if(e.dir){var dx=x2-x1,dy=y2-y1,L=Math.hypot(dx,dy)||1;x1+=dx/L*17;y1+=dy/L*17;x2-=dx/L*19;y2-=dy/L*19}
    s+='<line class="ed '+(e.cls||'')+'" x1="'+x1+'" y1="'+y1+'" x2="'+x2+'" y2="'+y2+'"'+(e.dir?' marker-end="url(#'+(e.cls==='hi'?'ahh':'ah')+')"':'')+'/>';
    if(e.w!=null){var mx=(a.x+b.x)/2,my=(a.y+b.y)/2;s+='<rect x="'+(mx-9)+'" y="'+(my-8)+'" width="18" height="16" rx="4" fill="#0C101B"/><text class="wl" x="'+mx+'" y="'+my+'">'+e.w+'</text>'}});
  nodes.forEach(function(n){s+='<circle class="nd '+(n.cls||'')+'" cx="'+n.x+'" cy="'+n.y+'" r="16"/><text x="'+n.x+'" y="'+n.y+'">'+n.l+'</text>'+(n.sub!=null?'<text class="sm" x="'+n.x+'" y="'+(n.y+27)+'">'+n.sub+'</text>':'')});
  return s+'</svg>';
};

/* ---- コードタブ ---- */
document.addEventListener('DOMContentLoaded',function(){
  document.querySelectorAll('.code').forEach(function(box){
    var srcs=[].slice.call(box.querySelectorAll('script[type="text/plain"]'));if(!srcs.length)return;
    var tabs=document.createElement('div');tabs.className='tabs';var pres=[];
    srcs.forEach(function(sc,k){var b=document.createElement('button');b.type='button';b.textContent=sc.dataset.lang;b.setAttribute('aria-selected',k===0);tabs.appendChild(b);
      var pre=document.createElement('pre');var code=sc.textContent.replace(/^\n/,'').replace(/\n\s*$/,'');
      pre.innerHTML=esc(code).replace(/(\/\/[^\n]*|#[^\n]*)/g,function(m){return /^#(include|define|if|endif|else|pragma)/.test(m)?m:'<span class="cm">'+m+'</span>'});
      if(k)pre.hidden=true;pres.push(pre);
      b.addEventListener('click',function(){pres.forEach(function(p,j){p.hidden=j!==k});[].forEach.call(tabs.querySelectorAll('button:not(.cp)'),function(x,j){x.setAttribute('aria-selected',j===k)})})});
    var cp=document.createElement('button');cp.type='button';cp.className='cp';cp.textContent='コピー';
    cp.addEventListener('click',function(){var p=pres.find(function(x){return !x.hidden});navigator.clipboard&&navigator.clipboard.writeText(p.textContent).then(function(){cp.textContent='コピーした';setTimeout(function(){cp.textContent='コピー'},1200)})});
    tabs.appendChild(cp);srcs.forEach(function(s){s.remove()});box.appendChild(tabs);pres.forEach(function(p){box.appendChild(p)});
  });
});
})();
