/* electronics 共通: ページ一覧・前後リンク・スケッチの読み込み */
(function(){
'use strict';
window.ELEC_PAGES=[
  {id:'setup',        t:'開発環境と最初の一歩', d:'Arduino IDE に ESP32 を入れて、配線なしで動かす。ブレッドボードへの挿し方'},
  {id:'parts',        t:'部品と道具',           d:'買った部品の一覧、はんだ付けが要るもの、買い足すと楽になるもの'},
  {id:'light-seeker', t:'首振りガジェット',     d:'CdS で明るさを測り、サーボで首を振っていちばん明るい方向を向く'},
  {id:'obstacle-car', t:'障害物回避カー',       d:'超音波で前を見て、DRV8835 で左右のモーターを回し、ぶつかる前によける'},
  {id:'wireless-rc',  t:'ワイヤレス操縦',       d:'2 台目の ESP32 とジョイスティックでコントローラーを作り、ESP-NOW で車を操縦する'},
  {id:'needle-meter', t:'針で指す温度計',       d:'サーミスターで温度を測り、ステッピングモーターの針で目盛りを指す'},
  {id:'ir-remote',    t:'赤外線リモコン',       d:'リモコンの信号を自分で読み解き、色と音を出し、車を操縦する'},
  {id:'light-message',t:'光で文字を送る',       d:'2 台の ESP32 で、LED の点滅と CdS で文字をやりとりする可視光通信'}
];
var $=function(s,r){return (r||document).querySelector(s)};

/* パンくずと前後リンク: <p class="top" id="nav"></p> と <nav id="pn"></nav> を置いておく */
window.elecNav=function(id){
  var P=ELEC_PAGES,i=P.findIndex(function(p){return p.id===id});
  var top=$('#nav');
  if(top)top.innerHTML='<a href="../">トップ</a> · <a href="./">電子工作ノート</a>'+(i>=0?' · '+(i+1)+' / '+P.length:'');
  var pn=$('#pn');
  if(pn&&i>=0){var p=P[i-1],n=P[i+1];
    pn.className='pn';
    pn.innerHTML=(p?'<a href="'+p.id+'.html">← '+p.t+'</a>':'<a href="./">← 目次</a>')+'<span class="sp"></span>'+
      (n?'<a href="'+n.id+'.html">'+n.t+' →</a>':'<a href="./">目次 →</a>');}
};

function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}

/* ざっくりした色付け: コメント・よく出るキーワード・数値だけ */
var KW=/\b(const|int|float|bool|void|if|else|for|while|return|switch|case|break|enum|unsigned|long|uint8_t|uint32_t|uint64_t|char|true|false|static)\b/g;
function paint(line){
  var i=line.indexOf('//'),code=i>=0?line.slice(0,i):line,cm=i>=0?line.slice(i):'';
  // 文字列の中はいじらない
  var parts=code.split(/("(?:[^"\\]|\\.)*")/),out='';
  for(var k=0;k<parts.length;k++){
    var t=esc(parts[k]);
    if(k%2===0)t=t.replace(KW,'<span class="kw">$1</span>').replace(/\b(\d+(?:\.\d+)?)(f|UL|U|L)?\b/g,'<span class="num">$1$2</span>');
    out+=t;
  }
  return out+(cm?'<span class="cm">'+esc(cm)+'</span>':'');
}

/* <div class="sketch" data-src="sketches/x/x.ino"></div> を、中身・コピー・ダウンロード付きのブロックにする */
function buildSketch(el){
  var src=el.getAttribute('data-src'),name=src.split('/').pop();
  el.innerHTML='<div class="bar"><span class="fn">'+esc(name)+'</span>'+
    '<button type="button" class="cp">コピー</button><a href="'+src+'" download>ダウンロード</a></div>'+
    '<pre><code>読み込み中…</code></pre>';
  var code=$('code',el),cp=$('.cp',el),text='';
  fetch(src).then(function(r){if(!r.ok)throw new Error(r.status);return r.text()}).then(function(t){
    text=t;
    code.innerHTML=t.replace(/\n$/,'').split('\n').map(paint).join('\n');
    if(t.split('\n').length>40&&!el.hasAttribute('data-open')){
      el.classList.add('collapsed');
      var b=document.createElement('button');b.type='button';b.className='fold';b.textContent='全部表示する ▼';
      b.addEventListener('click',function(){var c=el.classList.toggle('collapsed');b.textContent=c?'全部表示する ▼':'たたむ ▲'});
      el.appendChild(b);
    }
  }).catch(function(){
    code.innerHTML='読み込めませんでした。<a href="'+src+'" style="color:inherit">'+esc(name)+'</a> を直接開いてください。';
  });
  cp.addEventListener('click',function(){
    if(!text)return;
    var done=function(){cp.textContent='コピーしました';setTimeout(function(){cp.textContent='コピー'},1500)};
    if(navigator.clipboard&&navigator.clipboard.writeText)navigator.clipboard.writeText(text).then(done,fallback);else fallback();
    function fallback(){var ta=document.createElement('textarea');ta.value=text;ta.style.position='fixed';ta.style.opacity='0';
      document.body.appendChild(ta);ta.select();try{document.execCommand('copy');done()}catch(e){}document.body.removeChild(ta)}
  });
}
document.addEventListener('DOMContentLoaded',function(){
  Array.prototype.forEach.call(document.querySelectorAll('.sketch[data-src]'),buildSketch);
});
})();
