/* junos.js — Junos のコマンドの素振り台(BL-278)のエンジン。DOM に依らない(画面は index.html)。

   データは組み立て(topologies/cli_drill.py build)が作る bundle.json:
     schema … 構文の骨組み(games/cli-drill/syntax/junos.txt を JSON にしたもの)
     help   … 実機から採った ? の一覧(階層ごと。採った文言は private/ に置き、公開側に置かない)
     doc    … 公式文書(CLI User Guide)にある文言(モードのコマンドの一覧など)

   端末に出す文は 3 種類に分ける(out の c):
     'dev'  実機の記録にある文言そのもの(エラー・commit の結果・? の一覧の行)
     'doc'  公式文書にある文言
     'sim'  素振り台の注記(実機の文言を採っていない・扱わない、など)。画面で色を変え、実機の文と取り違えない
   ★実機の文言を採っていない応答は、それらしい文を作らずに sim の注記で出す。 */
(function (root) {
'use strict';

/* ---------------- 実機の文言(記録の出どころ= poc/junos/*.log) ---------------- */
const DEV = {
  missing: 'missing argument.',                                   // expJ1-chain.log ほか
  unknownCmd: 'unknown command.',                                 // expJ1-*.log(運用モードの deactivate)
  expectCmd: 'syntax error, expecting <command>.',                // expJ2-*.log(運用モードの set firewall)
  ambiguous: s => `'${s}' is ambiguous.`,                         // expJ0-commit.log
  possible: 'Possible completions:',
  notFound: 'warning: statement not found',                       // expJ1-*.log(delete)
  stmtNotFound: s => `error: statement '${s}' not found`,         // expJ2-*.log(insert)
  loadComplete: 'load complete',
  commitComplete: 'commit complete',
  checkOk: 'configuration check succeeds',
  checkoutFailed: 'error: configuration check-out failed',
  polUndef: p => `    Policy error: Policy ${p} referenced but not defined`,                         // expJ1-*.log
  plUndef: (pl, t) => `    Policy error: ${pl} prefix-list referenced (in term ${t}) but not defined`,  // expJ1-*.log
  license: p => ['[edit protocols]', `  '${p}'`, `    warning: requires '${p.toUpperCase()}' license`],
  entering: 'Entering configuration mode',
  exiting: 'Exiting configuration mode',
  changedNotCommitted: 'The configuration has been changed but not committed',
  exitAsk: 'Exit with uncommitted changes? [yes,no] (yes) ',
};

/* ---------------- 値の型 ---------------- */
function ipv4ok(s) {
  const m = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/.exec(s);
  return !!m && m.slice(1).every(x => +x <= 255);
}
function prefixok(s) {
  const m = /^([\d.]+)\/(\d{1,2})$/.exec(s);
  return !!m && ipv4ok(m[1]) && +m[2] <= 32;
}
const ENUMISH = vt => vt.startsWith('enum:') || vt.startsWith('?enum:');
function enumOpts(vt) { return vt.replace(/^\?/, '').slice(5).split('|'); }

// 値を読む。読めれば正規化した値、読めなければ null。
function readValue(vt, s) {
  if (s == null || s === '') return null;
  if (vt === 'word' || vt.startsWith('ref:')) return /^[^\s"[\]|;{}]+$/.test(s) ? s : null;
  if (vt === 'text') return s;
  if (vt === 'uint' || vt === 'asn') return /^\d+$/.test(s) ? String(+s) : null;
  if (vt.startsWith('int:')) {
    const [a, b] = vt.slice(4).split('-').map(Number);
    return /^\d+$/.test(s) && +s >= a && +s <= b ? String(+s) : null;
  }
  if (vt === 'ipv4') return ipv4ok(s) ? s : null;
  if (vt === 'prefix') return prefixok(s) ? s : null;
  if (vt === 'area') {
    if (ipv4ok(s)) return s;
    if (/^\d+$/.test(s)) { const n = +s >>> 0; return [n >>> 24, (n >> 16) & 255, (n >> 8) & 255, n & 255].join('.'); }
    return null;
  }
  if (vt === 'plen') return /^\/\d{1,2}$/.test(s) && +s.slice(1) <= 32 ? s : null;
  if (vt === 'plrange') return /^\/\d{1,2}-\/\d{1,2}$/.test(s) ? s : null;
  if (ENUMISH(vt)) { const r = pickWord(enumOpts(vt), s); return r.one || null; }
  return null;
}
const TYPE_JA = {
  word: '名前', text: '文字列', uint: '数', asn: 'AS 番号', ipv4: 'IPv4 アドレス', prefix: 'プレフィックス(a.b.c.d/n)',
  area: 'エリア番号', plen: '長さ(/n)', plrange: '長さの範囲(/a-/b)',
};
function typeJa(vt) {
  if (TYPE_JA[vt]) return TYPE_JA[vt];
  if (vt.startsWith('int:')) return `数(${vt.slice(4).replace('-', '〜')})`;
  if (vt.startsWith('ref:')) return `${vt.slice(4)} の名前`;
  if (ENUMISH(vt)) return enumOpts(vt).join(' か ');
  return vt;
}

// 語の候補から 1 つ選ぶ(完全一致 → 前方一致が 1 つ)。
function pickWord(words, s) {
  if (words.includes(s)) return { one: s };
  const pre = words.filter(w => w.startsWith(s));
  if (pre.length === 1) return { one: pre[0] };
  if (pre.length > 1) return { amb: pre };
  return {};
}

/* route-filter の一致の型(rfmatch)。語のあとに値を 1 つ取るものがある。 */
const RFMATCH = { exact: null, longer: null, orlonger: null, upto: 'plen', 'prefix-length-range': 'plrange', through: 'prefix', 'address-mask': 'ipv4' };

/* ---------------- 字句 ---------------- */
function tokenize(s) {
  const toks = []; let i = 0;
  while (i < s.length) {
    const ch = s[i];
    if (ch === ' ' || ch === '\t') { i++; continue; }
    if (ch === '"') {
      let j = i + 1; while (j < s.length && s[j] !== '"') j++;
      toks.push({ s: s.slice(i + 1, j), st: i, en: Math.min(j + 1, s.length), q: true }); i = j + 1; continue;
    }
    if (ch === '[' || ch === ']' || ch === '|') { toks.push({ s: ch, st: i, en: i + 1, sym: true }); i++; continue; }
    let j = i; while (j < s.length && !' \t"[]|'.includes(s[j])) j++;
    toks.push({ s: s.slice(i, j), st: i, en: j }); i = j;
  }
  return toks;
}

/* ---------------- 骨組み ---------------- */
const CONTAINERISH = n => n.t === 'R' || n.t === 'C' || n.t === 'NE' || n.t === '?';
function kids(n) { return n.t === 'N' ? n.ch : n.ch || []; }

// 実機の ? の一覧を骨組みに結ぶ。骨組みに無い語は「一覧にだけある語」(t='?')として足す。
function attachHelp(node, ctx, help) {
  const list = help[ctx];
  if (list) {
    node.helpList = list;
    for (const h of list) {
      let c = (node.ch || []).find(x => x.kw === h.n);
      if (!c) {
        c = { t: '?', kw: h.n, ch: [], lo: true };
        (node.ch = node.ch || []).push(c);
      }
      c.h = h.h; c.m = h.m; c.raw = h.raw;
    }
  }
  for (const c of node.ch || []) {
    if (c.kw === '-' || c.t === 'N') attachHelp(c, ctx ? ctx + ' ' + (c.kw === '-' ? '*' : c.kw + ' *') : (c.kw === '-' ? '*' : c.kw + ' *'), help);
    else if (c.t === 'C' || c.t === '?') attachHelp(c, ctx ? ctx + ' ' + c.kw : c.kw, help);
  }
}
function markOf(c) {
  if (c.m != null) return c.m;
  if (c.t === 'C' || c.t === 'N') return '>';
  if (c.t === 'M') return '+';
  return ' ';
}

/* ---------------- 設定の木 ----------------
   入れ物= {k:{語: 子}}。N の子= {e:[[鍵, {k:{}}], …]}。L= {v}。M= {vs:[]}。F= {f:1}。T= {ts:[[…]]}。 */
function clone(x) { return JSON.parse(JSON.stringify(x)); }
function emptyCfg() { return { k: {} }; }

/* ---------------- 文の道を読む ----------------
   start(骨組みの入れ物)から toks[i..] を読み、steps と終わり方を返す。
   want: 'set'(値まで要る)・'edit'(入れ物で終わる)・'path'(どこで終わってもよい= delete/show)
   返り値 {steps, err?}。err= {at: 字句の番号, kind: 'missing'|'syntax'|'ambig'|'value'|'unsup'|'extra', ...} */
function walkPath(start, toks, i, want) {
  const steps = [];
  let node = start;
  while (true) {
    if (i >= toks.length) {
      if (want === 'path') return { steps, end: i };
      if (want === 'edit') return { steps, end: i };
      // set: 入れ物で終わってよいのは「子のない名前の並び」か「@e」の並びだけ
      const last = steps[steps.length - 1];
      if (last && last.n.t === 'N' && last.key != null && (last.n.ch.length === 0 || last.n.e)) return { steps, end: i };
      return { steps, err: { at: i, kind: 'missing' } };
    }
    const tk = toks[i];
    if (tk.sym) {
      if (tk.s === '|' && want === 'path') return { steps, end: i };
      return { steps, err: { at: i, kind: 'syntax' } };
    }
    const ch = kids(node);
    const kws = ch.filter(c => c.kw !== '-');
    const keyless = ch.find(c => c.kw === '-');
    const r = pickWord(kws.map(c => c.kw), tk.s);
    let c = null;
    if (r.one && !(keyless && readValue(keyless.vt, tk.s) && r.one !== tk.s)) c = kws.find(x => x.kw === r.one);
    else if (keyless && readValue(keyless.vt, tk.s) != null) {
      const key = readValue(keyless.vt, tk.s);
      steps.push({ n: keyless, key });
      node = { t: 'NE', ch: keyless.ch, of: keyless };
      i++;
      if (keyless.ch.length === 0) {
        if (i < toks.length && !(toks[i].sym && toks[i].s === '|' && want === 'path')) return { steps, err: { at: i, kind: 'extra' } };
        return { steps, end: i };
      }
      continue;
    } else if (r.amb) return { steps, err: { at: i, kind: 'ambig', cands: r.amb, node } };
    if (!c) return { steps, err: { at: i, kind: 'syntax', node } };
    if (c.lo) return { steps, err: { at: i, kind: 'unsup', word: c.kw } };
    i++;
    if (c.t === 'C') { steps.push({ n: c }); node = c; continue; }
    if (c.t === 'N') {
      if (i >= toks.length || (toks[i].sym && toks[i].s === '|')) {
        if (want === 'set') return { steps, err: { at: i, kind: 'missing' } };
        steps.push({ n: c }); return { steps, end: i };
      }
      const key = readValue(c.vt, toks[i].s);
      if (key == null) return { steps, err: { at: i, kind: 'value', vt: c.vt, word: c.kw } };
      steps.push({ n: c, key }); i++;
      node = { t: 'NE', ch: c.ch, of: c };
      if (c.ch.length === 0) {
        if (i < toks.length && !(toks[i].sym && toks[i].s === '|' && want === 'path')) return { steps, err: { at: i, kind: 'extra' } };
        return { steps, end: i };
      }
      continue;
    }
    // ここから下は葉(値を持つ文)
    if (want === 'edit') return { steps, err: { at: i - 1, kind: 'notcontainer', word: c.kw } };
    const pipeAt = j => j < toks.length && toks[j].sym && toks[j].s === '|';
    const endOk = j => j >= toks.length || (want === 'path' && pipeAt(j));
    if (c.t === 'F') {
      steps.push({ n: c });
      if (!endOk(i)) return { steps, err: { at: i, kind: 'extra' } };
      return { steps, end: i };
    }
    if (c.t === 'L') {
      if (endOk(i)) { if (want === 'set') return { steps, err: { at: i, kind: 'missing' } }; steps.push({ n: c }); return { steps, end: i }; }
      const v = readValue(c.vt, toks[i].s);
      if (v == null) return { steps, err: { at: i, kind: 'value', vt: c.vt, word: c.kw } };
      steps.push({ n: c, val: v, q: toks[i].q }); i++;
      if (!endOk(i)) return { steps, err: { at: i, kind: 'extra' } };
      return { steps, end: i };
    }
    if (c.t === 'M') {
      if (endOk(i)) { if (want === 'set') return { steps, err: { at: i, kind: 'missing' } }; steps.push({ n: c }); return { steps, end: i }; }
      const vals = [];
      if (toks[i].sym && toks[i].s === '[') {
        i++;
        while (i < toks.length && !(toks[i].sym && toks[i].s === ']')) {
          const v = readValue(c.vt, toks[i].s);
          if (v == null) return { steps, err: { at: i, kind: 'value', vt: c.vt, word: c.kw } };
          vals.push(v); i++;
        }
        if (i >= toks.length) return { steps, err: { at: i, kind: 'missing' } };
        i++;
      } else {
        const v = readValue(c.vt, toks[i].s);
        if (v == null) return { steps, err: { at: i, kind: 'value', vt: c.vt, word: c.kw } };
        vals.push(v); i++;
      }
      steps.push({ n: c, vals });
      if (!endOk(i)) return { steps, err: { at: i, kind: 'extra' } };
      return { steps, end: i };
    }
    if (c.t === 'T') {
      const tup = [];
      if (endOk(i) && want === 'path') { steps.push({ n: c }); return { steps, end: i }; }
      for (const vt of c.vts) {
        const opt = vt.startsWith('?');
        if (endOk(i)) {
          if (opt) break;
          return { steps, err: { at: i, kind: 'missing' } };
        }
        if (vt === 'rfmatch') {
          const r2 = pickWord(Object.keys(RFMATCH), toks[i].s);
          if (r2.amb) return { steps, err: { at: i, kind: 'ambig', cands: r2.amb } };
          if (!r2.one) return { steps, err: { at: i, kind: 'value', vt, word: c.kw } };
          tup.push(r2.one); i++;
          const sub = RFMATCH[r2.one];
          if (sub) {
            if (endOk(i)) return { steps, err: { at: i, kind: 'missing' } };
            const v = readValue(sub, toks[i].s);
            if (v == null) return { steps, err: { at: i, kind: 'value', vt: sub, word: r2.one } };
            tup.push(v); i++;
          }
          continue;
        }
        const v = readValue(vt.replace(/^\?/, ''), toks[i].s);
        if (v == null) {
          if (opt) break;
          return { steps, err: { at: i, kind: 'value', vt, word: c.kw } };
        }
        tup.push(v); i++;
      }
      steps.push({ n: c, tup });
      if (!endOk(i)) return { steps, err: { at: i, kind: 'extra' } };
      return { steps, end: i };
    }
    return { steps, err: { at: i, kind: 'syntax' } };
  }
}

/* ---------------- 設定の木を辿る・変える ---------------- */
function childInst(inst, n, create) {
  const key = n.kw;
  if (!inst.k[key]) {
    if (!create) return null;
    inst.k[key] = n.t === 'C' ? { k: {} } : n.t === 'N' ? { e: [] } : n.t === 'M' ? { vs: [] } : n.t === 'T' ? { ts: [] } : n.t === 'F' ? { f: 1 } : {};
  }
  return inst.k[key];
}
function entryOf(list, key, create) {
  let e = list.e.find(x => x[0] === key);
  if (!e && create) { e = [key, { k: {} }]; list.e.push(e); }
  return e ? e[1] : null;
}
// 入れ物までの steps を辿る(create=true なら作りながら)。入れ物の inst を返す。
function descend(cfg, steps, create) {
  let inst = cfg;
  for (const s of steps) {
    if (s.n.t === 'C') { inst = childInst(inst, s.n, create); if (!inst) return null; }
    else if (s.n.t === 'N' && s.key != null) {
      const list = childInst(inst, s.n, create); if (!list) return null;
      inst = entryOf(list, s.key, create); if (!inst) return null;
    } else return inst; // 葉で止まる
  }
  return inst;
}
const sameTup = (a, b) => a.length === b.length && a.every((x, i) => x === b[i]);

function applySet(cfg, steps) {
  const last = steps[steps.length - 1];
  const parent = descend(cfg, steps.slice(0, -1), true);
  const n = last.n;
  if (n.t === 'C') { childInst(parent, n, true); return; }
  if (n.t === 'N') { const list = childInst(parent, n, true); entryOf(list, last.key, true); return; }
  if (n.t === 'L') { parent.k[n.kw] = { v: last.val, q: last.q }; return; }
  if (n.t === 'F') {
    if (n.xg) for (const o of n.xg.split('|')) delete parent.k[o];
    parent.k[n.kw] = { f: 1 }; return;
  }
  if (n.t === 'M') { const m = childInst(parent, n, true); for (const v of last.vals) if (!m.vs.includes(v)) m.vs.push(v); return; }
  if (n.t === 'T') { const t = childInst(parent, n, true); if (!t.ts.some(x => sameTup(x, last.tup))) t.ts.push(last.tup); return; }
}
function isEmptyInst(x) {
  if (!x) return true;
  if (x.k) return Object.keys(x.k).length === 0;
  if (x.e) return x.e.length === 0;
  if (x.vs) return x.vs.length === 0;
  if (x.ts) return x.ts.length === 0;
  return false;
}
// 空になった入れ物(C)を上へ向かって片付ける。名前の並びの項目は残す(Junos は空の項目を残す)。
function prune(cfg, steps) {
  for (let d = steps.length; d >= 1; d--) {
    const s = steps[d - 1];
    const parent = descend(cfg, steps.slice(0, d - 1), false);
    if (!parent) continue;
    const x = parent.k[s.n.kw];
    if (!x) continue;
    if ((s.n.t === 'C' && isEmptyInst(x)) || (s.n.t === 'N' && x.e && x.e.length === 0) || (x.vs && !x.vs.length) || (x.ts && !x.ts.length))
      delete parent.k[s.n.kw];
  }
}
function applyDelete(cfg, steps) {
  if (!steps.length) { const had = Object.keys(cfg.k).length > 0; cfg.k = {}; return had; }
  const last = steps[steps.length - 1];
  const parent = descend(cfg, steps.slice(0, -1), false);
  if (!parent) return false;
  const n = last.n, x = parent.k[n.kw];
  if (!x) return false;
  let ok = true;
  if (n.t === 'N' && last.key != null) {
    const idx = x.e.findIndex(e => e[0] === last.key);
    if (idx < 0) return false;
    x.e.splice(idx, 1);
  } else if (n.t === 'M' && last.vals) {
    const before = x.vs.length;
    x.vs = x.vs.filter(v => !last.vals.includes(v));
    ok = x.vs.length < before;
  } else if (n.t === 'T' && last.tup) {
    const before = x.ts.length;
    x.ts = x.ts.filter(t => !sameTup(t, last.tup));
    ok = x.ts.length < before;
  } else if (n.t === 'L' && last.val != null && x.v !== last.val) {
    return false;
  } else delete parent.k[n.kw];
  prune(cfg, steps.slice(0, -1).concat(parent.k[n.kw] ? [last] : []));
  prune(cfg, steps.slice(0, -1));
  return ok;
}

/* ---------------- 表示(カーリー・display set・compare) ---------------- */
function fmtVal(v, q) { return (q || /[\s;{}"]/.test(v) || v === '') ? `"${v.replace(/"/g, '\\"')}"` : v; }
// 子の文を 1 行ずつ(深さ d)。返り値は [{d, s}] の並び(s は字下げ前)。
function renderKids(node, inst, d) {
  const out = [];
  for (const c of kids(node)) {
    if (c.lo) continue;
    const x = inst.k[c.kw];
    if (!x) continue;
    if (c.t === 'C') {
      // @1 の入れ物は、子の文が 1 つならその文と 1 行にまとめる(then accept; family inet {)
      const flat = c.one ? renderKids(c, x, d) : null;
      if (flat && flat.filter(l => l.d === d && l.s !== '}').length === 1) {
        out.push({ d, s: `${c.kw} ${flat[0].s}` }, ...flat.slice(1));
        continue;
      }
      const sub = renderKids(c, x, d + 1);
      out.push({ d, s: `${c.kw} {` }, ...sub, { d, s: '}' });
    } else if (c.t === 'N') {
      const head = c.kw === '-' ? '' : c.kw + ' ';
      for (const [key, ent] of x.e) {
        const sub = renderKids({ ch: c.ch }, ent, d + 1);
        if (!sub.length) out.push({ d, s: `${head}${key};` });
        else if (c.one && sub.length === 1) out.push({ d, s: `${head}${key} ${sub[0].s}` });
        else out.push({ d, s: `${head}${key} {` }, ...sub, { d, s: '}' });
      }
    } else if (c.t === 'L') out.push({ d, s: `${c.kw} ${fmtVal(x.v, x.q)};` });
    else if (c.t === 'F') out.push({ d, s: `${c.kw};` });
    else if (c.t === 'M') out.push({ d, s: x.vs.length === 1 ? `${c.kw} ${x.vs[0]};` : `${c.kw} [ ${x.vs.join(' ')} ];` });
    else if (c.t === 'T') for (const t of x.ts) out.push({ d, s: `${c.kw} ${t.join(' ')};` });
  }
  return out;
}
const indent = d => '    '.repeat(d);
function curly(node, inst) { return renderKids(node, inst, 0).map(l => indent(l.d) + l.s); }

function setLines(node, inst, prefix, out) {
  out = out || [];
  for (const c of kids(node)) {
    if (c.lo) continue;
    const x = inst.k[c.kw];
    if (!x) continue;
    const p = prefix ? prefix + ' ' : '';
    if (c.t === 'C') { const n0 = out.length; setLines(c, x, p + c.kw, out); if (out.length === n0) out.push(`set ${p}${c.kw}`); }
    else if (c.t === 'N') {
      for (const [key, ent] of x.e) {
        const pk = p + (c.kw === '-' ? '' : c.kw + ' ') + key;
        const n0 = out.length; setLines({ ch: c.ch }, ent, pk, out);
        if (out.length === n0) out.push(`set ${pk}`);
      }
    } else if (c.t === 'L') out.push(`set ${p}${c.kw} ${fmtVal(x.v, x.q)}`);
    else if (c.t === 'F') out.push(`set ${p}${c.kw}`);
    else if (c.t === 'M') for (const v of x.vs) out.push(`set ${p}${c.kw} ${v}`);
    else if (c.t === 'T') for (const t of x.ts) out.push(`set ${p}${c.kw} ${t.join(' ')}`);
  }
  return out;
}
function stepsPrefix(steps) {
  return steps.map(s => s.n.t === 'N' ? (s.n.kw === '-' ? s.key : `${s.n.kw} ${s.key}`) : s.n.kw).join(' ');
}

/* show | compare。見出し [edit …] は「両方にある一番深い入れ物」。子の語ごとに見出しを分ける(実機の記録の形)。
   ★字下げは「印＋(4×深さ−1)の空白」に揃える(実機は見出しごとに揺れる。design §4)。 */
function compare(node, A, B) {
  const blocks = [];
  function block(path, lines) { if (lines.length) blocks.push({ path, lines }); }
  // 実機の字下げは見出しによって 3〜6 桁と揺れる(記録 10 例)。ここでは多数の 4 桁(印＋空白 3)に揃える。
  function signed(sign, items) { return items.map(l => sign + ' '.repeat(4 * l.d - 1) + l.s); }
  function walk(nd, a, b, path) {
    for (const c of kids(nd)) {
      if (c.lo) continue;
      const xa = a && a.k[c.kw], xb = b && b.k[c.kw];
      if (!xa && !xb) continue;
      const only = (sign, x) => {
        const items = renderKids({ ch: [c] }, { k: { [c.kw]: x } }, 1);
        block(path, signed(sign, items));
      };
      if (c.t === 'C') {
        if (xa && xb) walk(c, xa, xb, path.concat(c.kw));
        else only(xb ? '+' : '-', xb || xa);
      } else if (c.t === 'N') {
        if (!xa || !xb) { only(xb ? '+' : '-', xb || xa); continue; }
        const lines = [];
        const keysB = xb.e.map(e => e[0]), keysA = xa.e.map(e => e[0]);
        const head = k => c.kw === '-' ? [k] : [c.kw, k];
        for (const [k, ent] of xb.e) {
          if (!keysA.includes(k)) lines.push(...signed('+', renderKids({ ch: [c] }, { k: { [c.kw]: { e: [[k, ent]] } } }, 1)));
        }
        for (const [k, ent] of xa.e) {
          if (!keysB.includes(k)) lines.push(...signed('-', renderKids({ ch: [c] }, { k: { [c.kw]: { e: [[k, ent]] } } }, 1)));
        }
        block(path, lines);
        for (const [k, entB] of xb.e) {
          const entA = keysA.includes(k) ? xa.e.find(e => e[0] === k)[1] : null;
          if (entA) walk({ ch: c.ch }, entA, entB, path.concat(head(k)));
        }
        const common = keysB.filter(k => keysA.includes(k));
        const orderA = keysA.filter(k => common.includes(k));
        if (common.join('\n') !== orderA.join('\n')) blocks.push({ path: path.concat(c.kw === '-' ? [] : [c.kw]), lines: [], note: '並びの変わった項目があります(並びの変更の表示は採っていません)' });
      } else {
        const ra = xa ? renderKids({ ch: [c] }, { k: { [c.kw]: xa } }, 1) : [];
        const rb = xb ? renderKids({ ch: [c] }, { k: { [c.kw]: xb } }, 1) : [];
        const sa = ra.map(l => l.s), sb = rb.map(l => l.s);
        const del = ra.filter(l => !sb.includes(l.s)), add = rb.filter(l => !sa.includes(l.s));
        block(path, [...signed('-', del), ...signed('+', add)]);
      }
    }
  }
  walk(node, A, B, []);
  const out = [];
  for (const b of blocks) {
    out.push({ c: 'dev', s: `[edit${b.path.length ? ' ' + b.path.join(' ') : ''}]` });
    for (const l of b.lines) out.push({ c: 'dev', s: l });
    if (b.note) out.push({ c: 'sim', s: b.note });
  }
  return out;
}

/* ---------------- ? の一覧 ---------------- */
function fmtComp(mark, name, help) {
  const pad = name.length >= 20 ? name + '  ' : (name + ' '.repeat(20)).slice(0, 20) + ' ';
  return `${mark} ${pad}${help || ''}`.replace(/\s+$/, '');
}

/* ---------------- 本体 ---------------- */
function create(bundle, opt) {
  const schema = clone(bundle.schema);
  attachHelp(schema, '', bundle.help || {});
  const doc = bundle.doc || {};
  const S = {
    host: opt.host || 'router', user: opt.user || 'admin',
    mode: 'op',          // 'op' | 'cfg' | 'ask'(exit の yes/no)
    edit: [],            // 編集中の階層(steps)
    editStack: [],
    active: emptyCfg(), cand: emptyCfg(), commits: [],
    log: [],             // 打ったコマンドの記録(採点で使う)
  };
  function loadLines(lines, into) {
    const errs = [];
    for (const ln of lines || []) {
      const t = tokenize(ln);
      if (!t.length || t[0].s !== 'set') { errs.push(ln); continue; }
      const r = walkPath(schema, t, 1, 'set');
      if (r.err) { errs.push(ln); continue; }
      applySet(into, r.steps);
    }
    return errs;
  }
  const baseErr = loadLines(opt.base, S.active);
  S.cand = clone(S.active);
  S.commits.push(clone(S.active));
  const candErr = loadLines(opt.candidate, S.cand);

  const editNode = () => {
    let n = schema;
    for (const s of S.edit) n = s.n.t === 'N' ? { t: 'NE', ch: s.n.ch, of: s.n } : s.n;
    return n;
  };
  const banner = () => `[edit${S.edit.length ? ' ' + stepsPrefix(S.edit) : ''}]`;
  const promptText = () => S.mode === 'ask' ? DEV.exitAsk : `${S.user}@${S.host}${S.mode === 'cfg' ? '#' : '>'} `;
  const changed = () => JSON.stringify(S.active) !== JSON.stringify(S.cand);

  const dev = s => ({ c: 'dev', s });
  const sim = s => ({ c: 'sim', s });
  const caret = (line, at) => dev(' '.repeat(promptText().length + at) + '^');

  // err から端末の出力を作る(文言のある型だけ dev。ほかは sim の注記)
  function errOut(line, toks, err, node) {
    const at = err.at < toks.length ? toks[err.at].st : line.replace(/\s+$/, '').length + 1;
    const out = [caret(line, at)];
    if (err.kind === 'missing') out.push(dev(DEV.missing));
    else if (err.kind === 'ambig') {
      out.push(dev(DEV.ambiguous(toks[err.at].s)), dev(DEV.possible));
      const nd = err.node;
      for (const w of err.cands) {
        const c = nd && kids(nd).find(x => x.kw === w);
        out.push(c && c.raw ? dev(c.raw) : { c: 'dim', s: fmtComp(c ? markOf(c) : ' ', w, '') });
      }
    } else if (err.kind === 'unsup') out.push(sim(`素振り台: '${err.word}' は実機の一覧にある語ですが、この素振り台では扱っていません。`));
    else if (err.kind === 'value') out.push(sim(`素振り台: ここには ${typeJa(err.vt)} を書きます(実機のこの場面の文言は採っていません)。`));
    else if (err.kind === 'notcontainer') out.push(sim(`素振り台: '${err.word}' は値を持つ文なので、edit で中に入れません。set で書きます。`));
    else out.push(sim(`素振り台: ここに置ける語ではありません(実機のこの場面の文言は採っていません)。? で置ける語を見られます。`));
    return out;
  }

  /* ---- ? と Tab のための「次に来るもの」 ---- */
  // 返り値 {cands:[{mark,name,help,raw,dim,kw?}], partial, ctxNode, enter:bool}
  function nextAt(line) {
    const toks = tokenize(line);
    const endsSpace = /\s$/.test(line) || line === '';
    const partial = endsSpace ? '' : (toks.length ? toks[toks.length - 1].s : '');
    const done = endsSpace ? toks : toks.slice(0, -1);
    const res = { cands: [], partial, enter: false };
    const cmdList = S.mode === 'op' ? doc.opCommands : doc.cfgCommands;
    const pushNode = (nd) => {
      // 入れ物の中で次に置ける語・値
      const ch = kids(nd);
      res.ctx = nd;
      for (const c of ch) {
        if (c.kw === '-') {
          res.cands.push({ mark: ' ', name: c.ph || '<value>', dim: true, ph: true });
          continue;
        }
        res.cands.push({ mark: markOf(c), name: c.kw, help: c.h, raw: c.raw, dim: !c.raw, kw: true });
      }
    };
    if (!done.length) {
      for (const c of cmdList || []) res.cands.push({ mark: ' ', name: c[0], help: c[1], doc: true, kw: true });
      return res;
    }
    const cmd = done[0].s;
    const cmdWord = pickWord((cmdList || []).map(c => c[0]), cmd).one;
    let start = null, i0 = 1, want = 'set';
    if (S.mode === 'cfg' && ['set', 'delete', 'edit', 'show', 'insert'].includes(cmdWord)) {
      start = editNode(); want = cmdWord === 'set' ? 'set' : cmdWord === 'edit' ? 'edit' : 'path';
    } else if (S.mode === 'op' && cmdWord === 'show' && done[1] && pickWord(['configuration'], done[1].s).one) {
      start = schema; i0 = 2; want = 'path';
    } else if (S.mode === 'op' && cmdWord === 'show' && done.length === 1) {
      res.cands.push({ mark: '>', name: 'configuration', dim: true, kw: true }, { mark: '>', name: 'route', dim: true, kw: true, unsup: true });
      return res;
    } else return res;
    // done[i0..] を読んで、終わった所の状態を知る
    const r = walkPath(start, done, i0, 'path');
    if (r.err) { res.err = r.err; return res; }
    const last = r.steps[r.steps.length - 1];
    if (r.end < done.length) { // パイプ
      res.cands.push({ mark: ' ', name: 'compare', dim: true }, { mark: ' ', name: 'display', dim: true });
      return res;
    }
    if (!last) { pushNode(start); if (want !== 'set') res.enter = true; return res; }
    const n = last.n;
    if (n.t === 'C') { pushNode(n); res.enter = want !== 'set'; return res; }
    if (n.t === 'N') {
      if (last.key == null) {
        res.cands.push({ mark: ' ', name: n.ph || '<value>', dim: true, ph: true });
        const list = descend(S.cand, r.steps.slice(0, -1).concat([]), false);
        const x = list && list.k && list.k[n.kw];
        for (const [k] of (x && x.e) || []) res.cands.push({ mark: ' ', name: k, dim: true, key: true });
        res.valueOf = n; res.enter = want === 'path';
        return res;
      }
      pushNode({ ch: n.ch, helpList: null });
      res.enter = want !== 'set' || n.ch.length === 0 || !!n.e;
      return res;
    }
    if ((n.t === 'L' || n.t === 'M') && last.val == null && !last.vals) {
      if (ENUMISH(n.vt)) for (const o of enumOpts(n.vt)) res.cands.push({ mark: ' ', name: o, dim: true, kw: true });
      else {
        res.cands.push({ mark: ' ', name: '<' + typeJa(n.vt) + '>', dim: true, ph: true });
        if (n.vt.startsWith('ref:')) for (const k of refNames(n.vt.slice(4))) res.cands.push({ mark: ' ', name: k, dim: true, key: true });
      }
      res.valueOf = n; res.enter = want === 'path';
      return res;
    }
    if (n.t === 'T' && want !== 'set' && !last.tup) { res.enter = true; return res; }
    res.enter = true;
    return res;
  }
  function refNames(kind) {
    const po = S.cand.k['policy-options'];
    const key = kind === 'policy' ? 'policy-statement' : kind;
    const x = po && po.k[key];
    return x && x.e ? x.e.map(e => e[0]) : [];
  }
  // T(route-filter など)の途中の候補
  function tupleNext(line) {
    const toks = tokenize(line);
    const endsSpace = /\s$/.test(line);
    const done = endsSpace ? toks : toks.slice(0, -1);
    // 末尾から T の語を探す
    for (let j = done.length - 1; j >= 0; j--) {
      const w = done[j].s;
      const t = ['route-filter', 'prefix-list-filter', 'community'].find(x => x === w);
      if (!t) continue;
      const rest = done.slice(j + 1).map(x => x.s);
      if (t === 'route-filter') {
        if (rest.length === 0) return [{ name: '<' + typeJa('prefix') + '>', ph: true }];
        if (rest.length === 1) return Object.keys(RFMATCH).map(k => ({ name: k, kw: true }));
        if (rest.length === 2 && RFMATCH[rest[1]]) return [{ name: '<' + typeJa(RFMATCH[rest[1]]) + '>', ph: true }];
        return [{ name: 'accept', kw: true }, { name: 'reject', kw: true }, { name: '<[Enter]>', enter: true }];
      }
      if (t === 'prefix-list-filter') {
        if (rest.length === 0) return [{ name: '<prefix-list の名前>', ph: true }].concat(refNames('prefix-list').map(k => ({ name: k, key: true })));
        if (rest.length === 1) return ['exact', 'longer', 'orlonger'].map(k => ({ name: k, kw: true }));
        return [{ name: '<[Enter]>', enter: true }];
      }
      if (t === 'community' && done[j - 1] && done[j - 1].s.startsWith('then')) {
        if (rest.length === 0) return ['add', 'delete', 'set'].map(k => ({ name: k, kw: true }));
        if (rest.length === 1) return [{ name: '<community の名前>', ph: true }].concat(refNames('community').map(k => ({ name: k, key: true })));
        return [{ name: '<[Enter]>', enter: true }];
      }
      return null;
    }
    return null;
  }

  function helpOut(line) {
    const out = [];
    let nx = nextAt(line);
    let cands = nx.cands;
    if (nx.err && (nx.err.kind === 'missing' || nx.err.kind === 'value' || nx.err.kind === 'syntax')) {
      const tn = tupleNext(line);
      if (tn) cands = tn.map(x => ({ mark: ' ', name: x.name, dim: true, kw: x.kw, ph: x.ph, key: x.key, enter: x.enter }));
      else return { out: errOut(line, tokenize(line), nx.err) };
    } else if (nx.err) return { out: errOut(line, tokenize(line), nx.err) };
    const tn0 = !nx.err && tupleNext(line);
    if (tn0 && nx.cands.length === 0) cands = tn0.map(x => ({ mark: ' ', name: x.name, dim: true, kw: x.kw, ph: x.ph, key: x.key, enter: x.enter }));
    const p = nx.partial;
    let list = cands.filter(c => !p || c.ph || c.name.startsWith(p));
    if (p) list = list.filter(c => !c.ph || readValue((nx.valueOf && nx.valueOf.vt) || 'word', p) != null);
    out.push(dev(DEV.possible));
    if (nx.enter && !p) out.push({ c: 'doc', s: fmtComp(' ', '<[Enter]>', doc.enter || 'Execute this command') });
    // 値の札と既にある名前を先に。語は実機の一覧があればその順、無ければ字の順(実機の一覧は字の順)
    const phs = list.filter(c => c.ph), keys = list.filter(c => c.key && !c.ph), rest = list.filter(c => !c.ph && !c.key);
    const hl = nx.ctx && nx.ctx.helpList ? nx.ctx.helpList.map(h => h.n) : null;
    const rank = c => { const i = hl ? hl.indexOf(c.name) : -1; return i < 0 ? 1e6 : i; };
    rest.sort((a, b) => rank(a) - rank(b) || (a.name < b.name ? -1 : a.name > b.name ? 1 : 0));
    for (const c of phs.concat(keys, rest)) {
      if (c.enter) { out.push({ c: 'doc', s: fmtComp(' ', '<[Enter]>', doc.enter || 'Execute this command') }); continue; }
      if (c.raw) out.push(dev(c.raw));
      else if (c.doc) out.push({ c: c.help ? 'doc' : 'dim', s: fmtComp(' ', c.name, c.help) });
      else out.push({ c: 'dim', s: fmtComp(c.mark || ' ', c.name, '') });
    }
    if (list.some(c => (c.dim && !c.raw && !c.doc) || (c.doc && !c.help))) out.push(sim('素振り台: 薄い行は、実機の説明の文をまだ採っていない語です(語と形は実機の設定から)。'));
    return { out };
  }

  // Tab / 空白での補完。返り値 {line, out?}
  function complete(line, bySpace) {
    const toks = tokenize(line);
    if (!toks.length || /\s$/.test(line)) {
      if (bySpace) return { line: line + ' ' };
      return { line, out: helpOut(line).out };
    }
    const lastTok = toks[toks.length - 1];
    if (lastTok.q || lastTok.sym) return { line: bySpace ? line + ' ' : line };
    const nx = nextAt(line);
    // 空白で補うのは語(キーワード)だけ。名前(既にあるポリシー名など)は Tab のときだけ補う
    const okc = c => (c.kw || (c.key && !bySpace)) && c.name.startsWith(nx.partial);
    let words = nx.cands.filter(okc).map(c => c.name);
    if (nx.err || !nx.cands.length) {
      const tn = tupleNext(line);
      if (tn) words = tn.filter(okc).map(x => x.name);
    }
    words = [...new Set(words)];
    const head = line.slice(0, lastTok.st);
    if (words.length === 1) return { line: head + words[0] + ' ' };
    if (words.includes(nx.partial)) return { line: head + nx.partial + ' ' };
    if (bySpace) return { line: line + ' ' };       // 値の途中などの空白はそのまま
    if (words.length > 1) {
      // 共通の頭まで伸ばし、候補を見せる
      let pre = words[0];
      for (const w of words) while (!w.startsWith(pre)) pre = pre.slice(0, -1);
      return { line: head + pre, out: helpOut(head + pre).out };
    }
    return { line };
  }

  /* ---- コマンドを実行 ---- */
  function exec(line) {
    S.log.push({ mode: S.mode, line, edit: stepsPrefix(S.edit) });
    const toks = tokenize(line);
    if (S.mode === 'ask') return execAsk(line);
    if (!toks.length) return { out: [] };
    if (toks[0].s.startsWith('#')) return { out: [] };
    return S.mode === 'op' ? execOp(line, toks) : execCfg(line, toks);
  }
  function execAsk(line) {
    const a = line.trim();
    const r = a === '' ? { one: 'yes' } : pickWord(['yes', 'no'], a);
    if (r.one === 'yes') { S.mode = 'op'; S.edit = []; S.editStack = []; return { out: [dev(''), dev(DEV.exiting)], gap: true }; }
    if (r.one === 'no') { S.mode = 'cfg'; return { out: [] }; }
    return { out: [sim('素振り台: yes か no で答えます。')], keepAsk: true };
  }
  function execOp(line, toks) {
    const ops = (doc.opCommands || []).map(c => c[0]);
    const r = pickWord(ops, toks[0].s);
    if (r.amb) return { out: [caret(line, toks[0].st), dev(DEV.ambiguous(toks[0].s))] };
    if (!r.one) return { out: [caret(line, toks[0].st), dev(DEV.unknownCmd)] };
    const cmd = r.one;
    if (cmd === 'configure') {
      if (toks.length > 1) return { out: [sim('素振り台: configure private・exclusive は扱っていません。configure だけで入ります。')] };
      S.mode = 'cfg'; S.edit = []; S.editStack = [];
      const out = [dev(DEV.entering)];
      if (changed()) out.push(dev(DEV.changedNotCommitted));
      return { out, banner: true };
    }
    if (cmd === 'show') {
      if (toks.length < 2) return { out: [caret(line, line.length + 1), dev(DEV.missing)] };
      const r2 = pickWord(['configuration', 'route', 'bgp', 'ospf', 'interfaces'], toks[1].s);
      if (r2.one === 'configuration') return showCfg(line, toks, 2, S.active, schema, true);
      return { out: [sim('素振り台: show は show configuration だけを扱います(ルーティング テーブルなどの状態は、この素振り台では作りません)。')] };
    }
    if (cmd === 'test') return { out: [sim('素振り台: test policy は扱っていません(ルーティング テーブルを作らないため)。ラボで確かめます。')] };
    if (cmd === 'set' && toks[1] && !pickWord(['cli', 'date'], toks[1].s).one)   // 設定モードに入り忘れた set(記録 expJ2-*.log)
      return { out: [caret(line, toks[1].st), dev(DEV.expectCmd), sim('素振り台: 設定を変えるのは設定モードです。configure で入ります。')] };
    return { out: [sim(`素振り台: 運用モードの ${cmd} は扱っていません。configure で設定モードに入ります。`)] };
  }
  function showCfg(line, toks, i, cfg, from, fromTop) {
    const r = walkPath(from, toks, i, 'path');
    if (r.err) return { out: errOut(line, toks, r.err) };
    let pipe = null;
    if (r.end < toks.length) {
      const rest = toks.slice(r.end + 1).map(t => t.s);
      if (rest.length && pickWord(['compare'], rest[0]).one && !fromTop) pipe = 'compare';
      else if (rest.length >= 2 && pickWord(['display'], rest[0]).one && pickWord(['set'], rest[1]).one) pipe = 'set';
      else return { out: [sim('素振り台: パイプは | display set と、設定モードの | compare だけを扱います。')] };
    }
    const abs = (fromTop ? [] : S.edit).concat(r.steps);
    if (pipe === 'compare') {
      if (abs.length) return { out: [sim('素振り台: 階層を絞った compare は扱っていません。top で一番上に戻ってから show | compare です。')] };
      return { out: compare(schema, S.active, S.cand) };
    }
    // 対象の入れ物と骨組み
    const last = abs[abs.length - 1];
    let node = schema, inst = cfg;
    if (abs.length) {
      if (last.n.t === 'C' || (last.n.t === 'N' && last.key != null)) {
        inst = descend(cfg, abs, false);
        node = last.n.t === 'N' ? { ch: last.n.ch } : last.n;
      } else {
        const parent = descend(cfg, abs.slice(0, -1), false);
        inst = parent ? { k: parent.k[last.n.kw] ? { [last.n.kw]: parent.k[last.n.kw] } : {} } : null;
        node = { ch: [last.n] };
        if (inst && last.n.t === 'N') { /* N の並び全体 */ }
      }
    }
    if (!inst) return { out: [] };
    if (pipe === 'set') {
      const pre = abs.length && (last.n.t === 'C' || (last.n.t === 'N' && last.key != null)) ? stepsPrefix(abs) : stepsPrefix(abs.slice(0, -1));
      return { out: setLines(node, inst, pre).map(dev) };
    }
    return { out: curly(node, inst).map(dev) };
  }
  function execCfg(line, toks) {
    const cmds = (doc.cfgCommands || []).map(c => c[0]);
    let w = toks[0].s;
    const r = pickWord(cmds, w);
    if (r.amb) return { out: [caret(line, toks[0].st), dev(DEV.ambiguous(w)), dev(DEV.possible), ...r.amb.map(x => ({ c: 'doc', s: fmtComp(' ', x, (doc.cfgCommands.find(c => c[0] === x) || [])[1]) }))], banner: true };
    if (!r.one) return { out: [caret(line, toks[0].st), sim('素振り台: 設定モードのコマンドではありません(実機のこの場面の文言は採っていません)。? で一覧を見られます。')], banner: true };
    const cmd = r.one;
    const wrap = o => Object.assign({ banner: S.mode === 'cfg' }, o);
    if (cmd === 'set' || cmd === 'delete') {
      const rr = walkPath(editNode(), toks, 1, cmd === 'set' ? 'set' : 'path');
      if (rr.err) return wrap({ out: errOut(line, toks, rr.err) });
      if (cmd === 'delete' && rr.end < toks.length) return wrap({ out: [sim('素振り台: delete にパイプは付けません。')] });
      const abs = S.edit.concat(rr.steps);
      if (cmd === 'set') { applySet(S.cand, abs); return wrap({ out: [] }); }
      if (!applyDelete(S.cand, abs)) return wrap({ out: [dev(DEV.notFound)] });
      return wrap({ out: [] });
    }
    if (cmd === 'edit') {
      const rr = walkPath(editNode(), toks, 1, 'edit');
      if (rr.err) return wrap({ out: errOut(line, toks, rr.err) });
      const last = rr.steps[rr.steps.length - 1];
      if (last && last.n.t === 'N' && last.key == null) return wrap({ out: [caret(line, line.length + 1), dev(DEV.missing)] });
      S.editStack.push(S.edit); S.edit = S.edit.concat(rr.steps);
      return wrap({ out: [] });
    }
    if (cmd === 'show') return wrap(showCfg(line, toks, 1, S.cand, editNode(), false));
    if (cmd === 'top' || cmd === 'up') {
      let n = 1, k = 1;
      if (cmd === 'up' && toks[1] && /^\d+$/.test(toks[1].s)) { n = +toks[1].s; k = 2; }
      const prev = S.edit;
      if (cmd === 'top') S.edit = [];
      else {
        // 1 段= 入れ物 1 つか、名前の並びの項目 1 つ
        let e = S.edit.slice();
        for (let j = 0; j < n && e.length; j++) e.pop();
        S.edit = e;
      }
      if (toks.length > k) {   // top show などの相対のコマンド
        const rest = line.slice(toks[k].st);
        const res = execCfg(rest, tokenize(rest));
        S.edit = prev;
        return res;
      }
      S.editStack = [];
      return wrap({ out: [] });
    }
    if (cmd === 'exit' || cmd === 'quit') {
      const all = toks[1] && pickWord(['configuration-mode'], toks[1].s).one;
      if (S.edit.length && !all) { S.edit = S.editStack.pop() || []; return wrap({ out: [] }); }
      if (changed()) { S.mode = 'ask'; return { out: [dev(DEV.changedNotCommitted)], ask: true }; }
      S.mode = 'op'; S.edit = []; S.editStack = [];
      return { out: [dev(DEV.exiting)], gap: true };
    }
    if (cmd === 'commit') {
      const sub = toks[1] ? pickWord(['check', 'and-quit', 'comment', 'confirmed'], toks[1].s).one : null;
      if (toks[1] && !sub) return wrap({ out: errOut(line, toks, { at: 1, kind: 'syntax' }) });
      if (sub === 'confirmed') return wrap({ out: [sim('素振り台: commit confirmed は扱っていません(時間で戻る動きを作らないため)。')] });
      const chk = commitCheck();
      const out = chk.out;
      if (!chk.ok) { out.push(dev(DEV.checkoutFailed)); return wrap({ out }); }
      if (sub === 'check') { out.push(dev(DEV.checkOk)); return wrap({ out }); }
      S.active = clone(S.cand); S.commits.push(clone(S.active));
      out.push(dev(DEV.commitComplete));
      if (sub === 'and-quit') { S.mode = 'op'; S.edit = []; S.editStack = []; out.push(dev(DEV.exiting)); return { out, gap: true }; }
      return wrap({ out });
    }
    if (cmd === 'rollback') {
      const n = toks[1] ? toks[1].s : '0';
      if (!/^\d+$/.test(n)) return wrap({ out: errOut(line, toks, { at: 1, kind: 'syntax' }) });
      const idx = S.commits.length - 1 - (+n);
      if (idx < 0) return wrap({ out: [sim(`素振り台: この素振りの中では rollback ${n} にあたる commit がありません(始めてから ${S.commits.length - 1} 回)。`)] });
      S.cand = clone(S.commits[idx]);
      return wrap({ out: [dev(DEV.loadComplete)] });
    }
    if (cmd === 'run') {
      const rest = line.slice(toks[1] ? toks[1].st : line.length);
      if (!rest.trim()) return wrap({ out: [caret(line, line.length + 1), dev(DEV.missing)] });
      const res = execOp(rest, tokenize(rest));
      return wrap({ out: res.out });
    }
    if (cmd === 'insert') return wrap(execInsert(line, toks));
    return wrap({ out: [sim(`素振り台: ${cmd} は扱っていません。`)] });
  }
  function execInsert(line, toks) {
    // insert <道> <語> <名前> before|after <語> <名前>
    let bi = toks.findIndex((t, j) => j > 1 && (t.s === 'before' || t.s === 'after'));
    if (bi < 0) return { out: [caret(line, line.length + 1), dev(DEV.missing)] };
    const head = toks.slice(0, bi);
    const rr = walkPath(editNode(), head, 1, 'path');
    if (rr.err) return { out: errOut(line, toks, rr.err) };
    const last = rr.steps[rr.steps.length - 1];
    if (!last || last.n.t !== 'N' || last.key == null) return { out: [sim('素振り台: insert は名前の並び(term など)の項目の並べ替えだけを扱います。')] };
    const ref = toks.slice(bi + 1);
    if (ref.length < 2) return { out: [caret(line, line.length + 1), dev(DEV.missing)] };
    if (pickWord([last.n.kw], ref[0].s).one !== last.n.kw) return { out: [sim(`素振り台: before・after の後ろは同じ並びの項目(${last.n.kw} <名前>)を書きます。`)] };
    const abs = S.edit.concat(rr.steps);
    const parent = descend(S.cand, abs.slice(0, -1), false);
    const list = parent && parent.k[last.n.kw];
    const refKey = ref[1].s;
    if (!list || !list.e.some(e => e[0] === refKey)) return { out: [dev(DEV.stmtNotFound(refKey))] };
    const idx = list.e.findIndex(e => e[0] === last.key);
    if (idx < 0) return { out: [sim(`素振り台: 動かす項目 ${last.key} がまだありません(先に set で書きます)。`)] };
    const [ent] = list.e.splice(idx, 1);
    let at = list.e.findIndex(e => e[0] === refKey);
    if (toks[bi].s === 'after') at++;
    list.e.splice(at, 0, ent);
    return { out: [] };
  }

  /* commit の前の検査。実機の文言を採ってある検査だけ dev。 */
  function commitCheck() {
    const out = [];
    const pr = S.cand.k.protocols;
    for (const p of ['bgp', 'ospf']) if (pr && pr.k[p]) out.push(...DEV.license(p).map(dev));
    const pols = new Set(refNamesIn(S.cand, 'policy'));
    const plists = new Set(refNamesIn(S.cand, 'prefix-list'));
    const comms = new Set(refNamesIn(S.cand, 'community'));
    const errs = [];
    // プロトコルの import/export に当てた名前
    const refs = [];
    if (pr) {
      const bgp = pr.k.bgp;
      for (const [, g] of (bgp && bgp.k.group && bgp.k.group.e) || []) {
        for (const kk of ['import', 'export']) for (const v of (g.k[kk] && g.k[kk].vs) || []) refs.push(v);
        for (const [, nb] of (g.k.neighbor && g.k.neighbor.e) || []) for (const kk of ['import', 'export']) for (const v of (nb.k[kk] && nb.k[kk].vs) || []) refs.push(v);
      }
      const ospf = pr.k.ospf;
      for (const kk of ['import', 'export']) for (const v of (ospf && ospf.k[kk] && ospf.k[kk].vs) || []) refs.push(v);
    }
    for (const p of [...new Set(refs)]) if (!pols.has(p)) errs.push(DEV.polUndef(p));
    const simErrs = [];
    const po = S.cand.k['policy-options'];
    for (const [, ps] of (po && po.k['policy-statement'] && po.k['policy-statement'].e) || []) {
      const termsOf = [];
      for (const [tn, t] of (ps.k.term && ps.k.term.e) || []) termsOf.push([tn, t]);
      termsOf.push([null, ps]);
      for (const [tn, t] of termsOf) {
        const fr = t.k.from, th = t.k.then;
        const pl = [];
        for (const [k] of (fr && fr.k['prefix-list'] && fr.k['prefix-list'].e) || []) pl.push(k);
        for (const tup of (fr && fr.k['prefix-list-filter'] && fr.k['prefix-list-filter'].ts) || []) pl.push(tup[0]);
        for (const k of pl) if (!plists.has(k)) {
          if (tn) errs.push(DEV.plUndef(k, tn));
          else simErrs.push(`素振り台: prefix-list ${k} が定義されていません。実機ではここで断られます(term の外の場合の文言は採っていません)。`);
        }
        const cm = [];
        for (const v of (fr && fr.k.community && fr.k.community.vs) || []) cm.push(v);
        for (const tup of (th && th.k.community && th.k.community.ts) || []) cm.push(tup[1]);
        for (const k of cm) if (!comms.has(k)) simErrs.push(`素振り台: community ${k} が定義されていません。実機では commit で断られるはずです(確かめておらず、文言も採っていません)。`);
      }
    }
    if (errs.length) { out.push(dev('[edit]'), dev("  'policy-options'"), ...errs.map(dev)); }
    for (const s of simErrs) out.push(sim(s));
    return { ok: !errs.length && !simErrs.length, out };
  }
  function refNamesIn(cfg, kind) {
    const po = cfg.k['policy-options'];
    const key = kind === 'policy' ? 'policy-statement' : kind;
    const x = po && po.k[key];
    return x && x.e ? x.e.map(e => e[0]) : [];
  }

  return {
    S, schema,
    baseErr, candErr,
    prompt: () => ({ banner: S.mode === 'cfg' ? banner() : null, text: promptText() }),
    exec, help: helpOut, complete,
    activeSet: () => setLines(schema, S.active, ''),
    candSet: () => setLines(schema, S.cand, ''),
    changed,
  };
}

/* ---------------- 採点(お題の確かめ) ----------------
   want の行は display set の形。$X は同じお題の中で同じ値、* は何でも 1 語。
   返り値 {ok, miss:[行], bind} */
function matchLines(lines, wants, forbids, bind) {
  const L = lines.map(l => tokenize(l).map(t => t.s));
  // 1 行の照合。$X は束ねる、* は 1 語、** は何語でも。
  function m1(pat, toks, b) {
    function rec(i, j, nb) {
      if (i === pat.length) return j === toks.length ? nb : null;
      const p = pat[i];
      if (p === '**') {
        for (let k = j; k <= toks.length; k++) { const r = rec(i + 1, k, nb); if (r) return r; }
        return null;
      }
      if (j >= toks.length) return null;
      if (p === '*') return rec(i + 1, j + 1, nb);
      if (p.startsWith('$')) {
        if (nb[p] != null) return nb[p] === toks[j] ? rec(i + 1, j + 1, nb) : null;
        const n2 = Object.assign({}, nb); n2[p] = toks[j];
        return rec(i + 1, j + 1, n2);
      }
      return p === toks[j] ? rec(i + 1, j + 1, nb) : null;
    }
    return rec(0, 0, b);
  }
  const pats = w => (Array.isArray(w) ? w : [w]).map(x => tokenize(x).map(t => t.s));
  const P = wants.map(pats);
  let best = null;
  function rec(k, b, missed) {
    if (best && missed.length >= best.missed.length) return;
    if (k === P.length) { best = { b, missed }; return; }
    for (const alt of P[k]) for (const t of L) {
      const nb = m1(alt, t, b);
      if (nb) rec(k + 1, nb, missed);
      if (best && best.missed.length === 0) return;
    }
    rec(k + 1, b, missed.concat([wants[k]]));
  }
  rec(0, bind || {}, []);
  const bb = best.b;
  const hits = [];
  for (const f of forbids || []) {
    const fp = tokenize(f).map(t => t.s);
    for (let j = 0; j < L.length; j++) if (m1(fp, L[j], bb)) hits.push(lines[j]);
  }
  return { ok: !best.missed.length && !hits.length, miss: best.missed, hits, bind: bb };
}

/* お題 1 つの確かめ。drill= {want, forbid, order:[[前, 後]], cmd:[正規表現], cmd_ja:[説明]}。
   返り値 {ok, items:[{ok, s}]}(s は日本語の短い説明。正しい設定の行そのものは出さない)。 */
function checkDrill(sim, drill) {
  const act = sim.activeSet(), cand = sim.candSet();
  const items = [];
  const r = matchLines(act, drill.want || [], drill.forbid || [], {});
  const rc = matchLines(cand, drill.want || [], drill.forbid || [], {});
  if (r.ok) items.push({ ok: true, s: 'commit 済みの設定がお題を満たしています' });
  else if (rc.ok) items.push({ ok: false, s: '候補の設定はお題を満たしていますが、まだ commit していません' });
  else {
    items.push({ ok: false, s: `お題の要素のうち ${(drill.want || []).length - r.miss.length}/${(drill.want || []).length} が commit 済みの設定にあります` });
    if (r.hits.length) items.push({ ok: false, s: 'お題が「入れない」とした設定が入っています' });
  }
  let ok = r.ok;
  for (const [a, b] of drill.order || []) {
    const pa = a.replace(/\$(\w+)/g, (m) => r.bind['$' + m.slice(1)] || m), pb = b.replace(/\$(\w+)/g, (m) => r.bind['$' + m.slice(1)] || m);
    const ia = act.findIndex(l => matchLines([l], [pa], [], {}).ok), ib = act.findIndex(l => matchLines([l], [pb], [], {}).ok);
    const good = ia >= 0 && ib >= 0 && ia < ib;
    if (!good) ok = false;
    items.push({ ok: good, s: drill.order_ja || '並びの順' });
  }
  (drill.cmd || []).forEach((c, j) => {
    const rx = new RegExp(typeof c === 'string' ? c : c.line), ex = c.edit ? new RegExp(c.edit) : null;
    const good = sim.S.log.some(x => x.mode === 'cfg' && rx.test(x.line.trim()) && (!ex || ex.test(x.edit)));
    if (!good) ok = false;
    items.push({ ok: good, s: (drill.cmd_ja || [])[j] || '使うコマンド' });
  });
  if (ok && sim.changed()) items.push({ ok: true, s: '(commit していない変更が候補に残っています)' });
  return { ok, items };
}

root.JunosSim = { create, tokenize, matchLines, readValue, checkDrill };
})(typeof window !== 'undefined' ? window : globalThis);
