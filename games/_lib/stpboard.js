/*
  STP のゲーム(STP パズル BL-268・STP 経路づくり BL-270)で共通の部品。配信は pack_server.py の /_games/lib/stpboard.js。
  - 小物: store(localStorage・失敗しても動く)・el / sv(要素を作る)・esc / inline / md(軽い Markdown)
  - geom(): 盤面の座標から、線・ポートの印・ポート名のラベル(ぶつからない置き場所を順に試す)を決める
  盤面の形(pz)= {switches:[{name,x,y}], links:[{a,ia,b,ib,off}], hosts:[{name,sw,if,x,y}], ports:[{key,…}], height}
*/
(function(){
'use strict';
var NS = 'http://www.w3.org/2000/svg';

function store(k, v){ try{ if (v === undefined) return localStorage.getItem(k); if (v === null) localStorage.removeItem(k); else localStorage.setItem(k, v); }catch(e){} return null; }
function el(tag, cls, txt){ var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }
function sv(tag, attrs, txt){ var e = document.createElementNS(NS, tag); for (var k in attrs) e.setAttribute(k, attrs[k]); if (txt != null) e.textContent = txt; return e; }
function esc(s){ return String(s).replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
function inline(s){ return esc(s).replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>'); }
function md(src){
  var out = [], list = null;
  String(src || '').split(/\n/).forEach(function(line){
    var m = line.match(/^\s*-\s+(.*)$/);
    if (m){ if (!list){ list = []; } list.push('<li>' + inline(m[1]) + '</li>'); return; }
    if (list){ out.push('<ul>' + list.join('') + '</ul>'); list = null; }
    if (line.trim()) out.push('<p>' + inline(line) + '</p>');
  });
  if (list) out.push('<ul>' + list.join('') + '</ul>');
  return out.join('');
}
function rectDist(px, py, cx, cy, hw, hh){
  return Math.hypot(Math.max(Math.abs(px - cx) - hw, 0), Math.max(Math.abs(py - cy) - hh, 0));
}
function txtW(s, px){ var w = 0; for (var i = 0; i < s.length; i++) w += s.charCodeAt(i) > 255 ? px : px * 0.57; return w; }
function hitBox(a, b){ return a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1; }

/*
  geom(pz, o)
    o.bw / o.bh  … スイッチの箱の幅と高さ
    o.hw / o.hh  … 端末の箱の幅と高さの半分(既定 26 / 14)
    o.label(p)   … ポート名のラベル {txt, ov}(ov= 既定から変えた値を含む)
    o.linkText(l, i) … リンクの中ほどに出す文字(速度・コスト)
  戻り値 {pos, mk(ポートの印の位置), lines(線・中点の文字), lbl(ラベルの位置と箱)}
*/
function geom(pz, o){
  var BW = o.bw, BH = o.bh, HW = o.hw || 26, HH = o.hh || 14;
  var pos = {};
  pz.switches.forEach(function(s){ pos[s.name] = s; });
  var mk = {}, lines = [], H = pz.height;
  // 箱(中心 cx,cy)から、線の始点 sx,sy・向き u に沿って、箱から 15 以上離れた最初の点
  function place(cx, cy, sx, sy, ux, uy, L){
    var d = 0;
    while (d < L / 2 && rectDist(sx + ux * d, sy + uy * d, cx, cy, BW / 2, BH / 2) < 15) d += 1;
    return {x:sx + ux * d, y:sy + uy * d};
  }
  pz.links.forEach(function(l, i){
    var A = pos[l.a], B = pos[l.b];
    var dx = B.x - A.x, dy = B.y - A.y, L = Math.hypot(dx, dy), ux = dx / L, uy = dy / L, nx = -uy, ny = ux;
    var off = l.off * 18;
    var ax = A.x + nx * off, ay = A.y + ny * off, bx = B.x + nx * off, by = B.y + ny * off;
    lines.push({x1:ax, y1:ay, x2:bx, y2:by, link:l, i:i, mx:(ax + bx) / 2, my:(ay + by) / 2});
    var sgn = l.off ? (l.off > 0 ? 1 : -1) : 1;
    var pa = place(A.x, A.y, ax, ay, ux, uy, L), pb = place(B.x, B.y, bx, by, -ux, -uy, L);
    mk[l.a + '|' + l.ia] = {x:pa.x, y:pa.y, nx:nx * sgn, ny:ny * sgn, ux:ux, uy:uy};
    mk[l.b + '|' + l.ib] = {x:pb.x, y:pb.y, nx:l.off ? nx * sgn : -nx, ny:l.off ? ny * sgn : -ny, ux:-ux, uy:-uy};
  });
  // 中点の文字: 中点が近い組は、それぞれの線に沿って逆向きにずらす(交差する対角線は中点が重なる)
  lines.forEach(function(a, i){
    lines.slice(i + 1).forEach(function(b){
      if (Math.hypot(a.mx - b.mx, a.my - b.my) < 18){
        var la = Math.hypot(a.x2 - a.x1, a.y2 - a.y1), lb = Math.hypot(b.x2 - b.x1, b.y2 - b.y1);
        a.mx += (a.x2 - a.x1) / la * 22; a.my += (a.y2 - a.y1) / la * 22;
        b.mx -= (b.x2 - b.x1) / lb * 22; b.my -= (b.y2 - b.y1) / lb * 22;
      }
    });
  });
  pz.hosts.forEach(function(h){
    var A = pos[h.sw], dx = h.x - A.x, dy = h.y - A.y, L = Math.hypot(dx, dy), ux = dx / L, uy = dy / L;
    lines.push({x1:A.x, y1:A.y, x2:h.x, y2:h.y, host:h});
    var pa = place(A.x, A.y, A.x, A.y, ux, uy, L);
    mk[h.sw + '|' + h.if] = {x:pa.x, y:pa.y, nx:-uy, ny:ux, ux:ux, uy:uy};
  });
  // ぶつかってはいけない物
  var obst = [];
  pz.switches.forEach(function(s){
    obst.push({w:3, x0:s.x - BW / 2 - 2, x1:s.x + BW / 2 + 2, y0:s.y - BH / 2 - 2, y1:s.y + BH / 2 + 2});
  });
  pz.hosts.forEach(function(h){ obst.push({w:3, x0:h.x - HW, x1:h.x + HW, y0:h.y - HH, y1:h.y + HH}); });
  Object.keys(mk).forEach(function(k){ var m = mk[k]; obst.push({w:2, x0:m.x - 13, x1:m.x + 13, y0:m.y - 13, y1:m.y + 13}); });
  lines.forEach(function(ln){
    if (!ln.link) return;
    ln.text = o.linkText(ln.link, ln.i);
    var w = txtW(ln.text, 10) / 2;
    obst.push({w:1, x0:ln.mx - w - 1, x1:ln.mx + w + 1, y0:ln.my - 6, y1:ln.my + 6});
  });
  // ポート名のラベル
  var lbl = {};
  pz.ports.forEach(function(p){
    var m = mk[p.key]; if (!m) return;
    var L = o.label(p), txt = L.txt, w = txtW(txt, 9.5), best = null;
    [[m.nx, m.ny], [-m.nx, -m.ny], [1, 0], [-1, 0], [0, -1], [0, 1], [0.7, -0.7], [-0.7, -0.7], [0.7, 0.7], [-0.7, 0.7]].forEach(function(d){
      var side = Math.abs(d[0]) > 0.45, anc = side ? (d[0] > 0 ? 'start' : 'end') : 'middle';
      var x = side ? m.x + (d[0] > 0 ? 15 : -15) : m.x + d[0] * 10 + m.ux * 10;      // 上下に置く時は線に沿って箱から離す
      var y = side ? m.y + d[1] * 13 : m.y + (d[1] > 0 ? 19 : -19);
      var x0 = anc === 'start' ? x : anc === 'end' ? x - w : x - w / 2;
      var bx = {x0:x0, x1:x0 + w, y0:y - 5.5, y1:y + 5.5}, score = 0;
      if (bx.x0 < 1 || bx.x1 > 399 || bx.y0 < 1 || bx.y1 > H - 1) score += 10;
      obst.forEach(function(q){ if (hitBox(bx, q)) score += q.w; });
      if (!best || score < best.score) best = {x:x, y:y, anc:anc, box:bx, score:score, txt:txt, ov:!!L.ov};
    });
    lbl[p.key] = best;
    obst.push({w:2, x0:best.box.x0, x1:best.box.x1, y0:best.box.y0, y1:best.box.y1});
  });
  return {pos:pos, mk:mk, lines:lines, lbl:lbl};
}

window.STPB = {NS:NS, store:store, el:el, sv:sv, esc:esc, inline:inline, md:md,
               rectDist:rectDist, txtW:txtW, hitBox:hitBox, geom:geom};
})();
