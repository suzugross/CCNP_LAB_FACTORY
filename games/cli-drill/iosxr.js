/* コマンドの素振り台(BL-278)— IOS XR の CLI の動き。DOM に依らない(画面は index.html)。
 *
 * 約束(CLAUDE.md「コマンドの素振り台の約束」): 実機の動きを確かめて、外れない形に落とし込む。
 *   出す文の出どころで色を分ける: dev= 実機の記録にある文言・dim= 語と形は骨組みにあるが ? の説明を採っていない・
 *   sim= 素振り台の注記(実機の文言を採っていない場面と、扱わないこと)。実機の文言を採っていない場面は作らず sim で出す。
 * 根拠の記録: private/cli-drill/iosxr/raw/*.log(XRT-01 の XR01・IOS XRv 9000 24.3.1)・raw/xrd-26.1.1/*.log(XRT-16 と同じ盤面の PE2・
 * IOS XRd 26.1.1。M14)。台本は games/cli-drill/capture/iosxr/。? の一覧は組ごと(盤面の helpset)。
 * 設計: problems/_drafts/CLI-DRILL.design.md §8・§10。
 *
 * データ(bundle.os.iosxr): schema= syntax/iosxr.txt を cli_drill.py が JSON にしたもの・help= 実機の ? の一覧(非公開)。
 * 盤面(単元の devices): 実機の記録から作った JSON(稼働中の設定・コミットの履歴と各回の中身)。
 */
(function (root) {
'use strict';

/* ---------------- 実機の文言(出どころの記録は design §8) ---------------- */
const DEV = {
  invalid: "% Invalid input detected at '^' marker.",
  incomplete: '% Incomplete command.',
  ambig: s => `% Ambiguous command:  "${s}"`,
  noItem: '% No such configuration item(s)',
  noChanges: 'No configuration changes to commit.',
  labelUsed: '% Failed to commit .. As the specified label is already assigned to a previous commit. Please recommit the changes with a different label.',
  pseudoFail: "% Failed to commit one or more configuration items during a pseudo-atomic operation. All changes made have been reverted. Please issue 'show configuration failed [inheritance]' from this session to view the errors",
  confirmTrial: '% Confirming commit for trial session.',
  uncAsk: 'Uncommitted changes found, commit them before exiting(yes/no/cancel)? [cancel]:',
  badAnswer: '% Invalid input.',
  trialExit: "You are exiting after a 'commit confirm' with an active rollback session.  If you exit the configuration awaiting confirmation will not be confirmed and the router will immediately rollback to the previous configuration.",
  trialAsk: 'Do you wish to exit? [no]: ',
  yesNo: "% Please answer 'yes' or 'no'.",
  others: ['One or more commits have occurred from other', 'configuration sessions since this session started',
    'or since the last commit was made from this session.', "You can use the 'show configuration commit changes'",
    'command to browse the changes.'],
  othersAsk: 'Do you wish to proceed with this commit anyway? [no]: ',
  rbHead: ['', 'Loading Rollback Changes.', 'Loaded Rollback Changes in 1 sec ', 'Committing.'],
  rbTail: ['Updating.', 'Updated Commit database in 1 sec '],
  rbLast: n => `Configuration successfully rolled back ${n} commits.`,
  rbToEx: x => `Configuration successfully rolled back to excluding '${x}'.`,
  loading: 'Loading.',
  building: '!! Building configuration...',
  semHead: ['!! SEMANTIC ERRORS: This configuration was rejected by ', '!! the system due to semantic errors. The individual ',
    '!! errors with each failed configuration command can be ', '!! found below.', '', ''],
  policyErr: p => `!!% Could not find entry in list: Policy [${p}] must be defined before it can be attached.`,
  listHead: ['SNo. Label/ID              User      Line                Client      Time Stamp',
    '~~~~ ~~~~~~~~              ~~~~      ~~~~                ~~~~~~      ~~~~~~~~~~'],
};
function dev(s) { return { c: 'dev', s }; }
/* 素振り台の注記(黄)の言語= create の opt.lang(en / ja。既定 ja)。実機の文言(dev)は言語に依らない。
   J(ja, en) は create と checkDrill の中で、その素振り台の言語の方を返す */
const SIM_PREFIX = { ja: '素振り台: ', en: 'Drill: ' };
function langOf(l) { return l === 'en' ? 'en' : 'ja'; }
/* XR の語(キーワード・口の型・選ぶ値)は大小文字を区別しない(INTERFACE・Router ospf・IPV4・network POINT-TO-POINT・
   SHOW RUNNING-CONFIG・COMMIT・END の問いへの NO。記録 ifnames.log・ifnames2.log・ifnames3.log)。名前・ラベル・説明などの値は区別する */
const lc = s => String(s).toLowerCase();
const pfx = (canon, typed) => lc(canon).startsWith(lc(typed));
const same = (a, b) => lc(a) === lc(b);

/* ---------------- 時刻(実機の形: 記録の各 show の先頭行・コミットの一覧) ---------------- */
const DOW = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const p2 = n => String(n).padStart(2, '0');
function tsLine(d) {      // Mon Nov 16 04:28:53.822 UTC(日付の 1 桁の日の形は未採取= design §8.4)
  return `${DOW[d.getUTCDay()]} ${MON[d.getUTCMonth()]} ${d.getUTCDate()} ${p2(d.getUTCHours())}:${p2(d.getUTCMinutes())}:${p2(d.getUTCSeconds())}.${String(d.getUTCMilliseconds()).padStart(3, '0')} UTC`;
}
function tsCommit(d) {    // Mon Nov 16 04:28:15 2026
  return `${DOW[d.getUTCDay()]} ${MON[d.getUTCMonth()]} ${d.getUTCDate()} ${p2(d.getUTCHours())}:${p2(d.getUTCMinutes())}:${p2(d.getUTCSeconds())} ${d.getUTCFullYear()}`;
}

/* ---------------- 字句 ---------------- */
function tokenize(line) {
  const out = [];
  const re = /\S+/g;
  let m;
  while ((m = re.exec(line))) out.push({ s: m[0], st: m.index, en: m.index + m[0].length });
  return out;
}

/* ---------------- 値の型(骨組みの {型})。返り値 {ok, v?, at?(誤りの字の位置・字句の頭からの相対)} ---------------- */
const IFTYPES = [   // 素振り台が扱う IF の種類(実機の interface ? の一覧にある名前)。並びは running-config の並び(記録 orders.log)
  // kind: 番号の ? の出方。range= <0-2147483647> の一覧の形・inst= 機器にある口の番号を横に並べる形(記録 ifnames.log・ifnames3.log)
  { full: 'Loopback', re: /^\d+$/, kind: 'range' },
  { full: 'MgmtEth', re: /^0\/RP0\/CPU0\/\d+$/, kind: 'inst' },
  { full: 'GigabitEthernet', re: /^0\/0\/0\/\d+$/, kind: 'inst' },
  { full: 'Null', re: /^0$/, kind: 'range' },
];
function ipv4At(s) {      // 誤りの位置= 誤った区切りの頭(記録 modes.log の 10.20.20.300)
  const parts = s.split('.');
  let pos = 0;
  for (let i = 0; i < parts.length; i++) {
    const p = parts[i];
    if (i > 3 || !/^\d{1,3}$/.test(p) || +p > 255) return pos;
    pos += p.length + 1;
  }
  return parts.length === 4 ? -1 : s.length;
}
function ifParse(s) {
  for (const t of IFTYPES) {
    for (let k = 1; k <= Math.min(s.length, t.full.length); k++) {
      const pre = s.slice(0, k), rest = s.slice(k);
      if (t.full.toLowerCase().startsWith(pre.toLowerCase()) && (k === t.full.length || !/^[A-Za-z]/.test(rest)) && t.re.test(rest)) {
        if (k < 2 && t.full !== 'Null') continue;
        return t.full + rest;
      }
    }
  }
  return null;
}
// 型だけの語(Lo・loopback・LOOPBACK・gi …)→ 型。頭 2 字から(Null は 1 字から)= ifParse と同じ
function ifTypeOf(s) {
  if (!s || /[\d/]/.test(s)) return null;
  return IFTYPES.find(t => pfx(t.full, s) && (s.length >= 2 || t.full === 'Null')) || null;
}
// 型と番号を分けて打った形(interface Loopback 40・Lo 44・LOOPBACK 42 は通り、Loopback40 にまとまる。記録 ifnames.log)
function ifJoin(a, b) {
  if (!a || !b || ifParse(a) || !ifTypeOf(a)) return null;
  return ifParse(a + b);
}
// 続けて打った型と番号の途中(Loopback40・Gi0/0/0/)→ {type, typed, num}
function ifSplit(s) {
  const m = /^([A-Za-z-]+)([\d/].*)$/.exec(s || '');
  const t = m && ifTypeOf(m[1]);
  return t ? { type: t, typed: m[1], num: m[2] } : null;
}
const ifTypeOfName = v => IFTYPES.find(t => String(v).startsWith(t.full)) || null;   // 正規の名前(Loopback40)→ 型
// ? の一覧の鍵で口の名前を置く印: Loopback は *・ほかは *@<型>(口の型で一覧が違う。記録 ifnames3.log・ifnames4.log)
function ifStar(v) { const t = ifTypeOfName(v); return !t || t.full === 'Loopback' ? '*' : '*@' + t.full; }
function checkVal(tok, s) {
  const [vt, arg] = [tok.v, tok.arg];
  switch (vt) {
    case 'word': case 'ref': return s && !/[?]/.test(s) ? { ok: true, v: s } : { ok: false, at: 0 };
    case 'line': return { ok: true, v: s };
    case 'uint': {
      if (!/^\d+$/.test(s)) return { ok: false, at: 0 };
      const [lo, hi] = (arg || '0-4294967295').split('-').map(Number);
      return +s >= lo && +s <= hi ? { ok: true, v: String(+s) } : { ok: false, at: 0 };
    }
    case 'asn': return /^\d+$/.test(s) && +s >= 1 && +s <= 4294967295 ? { ok: true, v: String(+s) } : { ok: false, at: 0 };
    case 'ipv4': { const at = ipv4At(s); return at < 0 ? { ok: true, v: s } : { ok: false, at }; }
    case 'mask': { const at = ipv4At(s); return at < 0 ? { ok: true, v: s } : { ok: false, at }; }
    case 'area': {
      if (/^\d+$/.test(s)) return { ok: true, v: String(+s) };
      const at = ipv4At(s); return at < 0 ? { ok: true, v: s } : { ok: false, at };
    }
    case 'v4pfx': {
      const m = /^([^/]+)\/(\d{1,2})$/.exec(s);
      if (!m) { const at = ipv4At(s.split('/')[0]); return { ok: false, at: at < 0 ? s.split('/')[0].length : at }; }
      const at = ipv4At(m[1]);
      return at < 0 && +m[2] <= 32 ? { ok: true, v: s } : { ok: false, at: at < 0 ? m[1].length + 1 : at };
    }
    case 'v6pfx': return /^[0-9a-fA-F:]+\/\d{1,3}$/.test(s) && s.includes(':') ? { ok: true, v: s.toLowerCase() } : { ok: false, at: 0 };
    case 'ifname': { const v = ifParse(s); return v ? { ok: true, v } : { ok: false, at: 0 }; }
    case 'nexthop': {
      if (/^\d/.test(s)) { const at = ipv4At(s); return at < 0 ? { ok: true, v: s } : { ok: false, at }; }
      const v = ifParse(s); return v ? { ok: true, v } : { ok: false, at: 0 };
    }
    case 'enum': {
      const opts = arg.split('|');
      const ex = opts.find(o => same(o, s));
      if (ex) return { ok: true, v: ex };
      const hit = opts.filter(o => pfx(o, s));
      return hit.length === 1 ? { ok: true, v: hit[0] } : { ok: false, at: 0, ambig: hit.length > 1 };
    }
    case 'ipn': {          // IP name or address(rp-address)。誤りの印= アドレスの頭として読めなくなった字(記録 m14cfg.log の 10.255.0.300 → 最後の 0)
      if (ipv4At(s) < 0) return { ok: true, v: s };
      let k = 0;
      while (k < s.length && /^(\d{1,3}(\.\d{1,3}){0,3}\.?)?$/.test(s.slice(0, k + 1)) && s.slice(0, k + 1).split('.').every(x => x === '' || +x <= 255)) k++;
      return { ok: false, at: k };
    }
    case 'acl6a': {        // IPv6 の ACL の番地(any・X:X::X/長さ)
      if (s && /^[a-z]/i.test(s) && pfx('any', s) && !s.includes(':')) return { ok: true, v: 'any' };
      return /^[0-9a-fA-F:]+\/\d{1,3}$/.test(s || '') && s.includes(':') ? { ok: true, v: s.toLowerCase() } : { ok: false, at: 0 };
    }
    case 'ipv6': return /^[0-9a-fA-F:]+$/.test(s) && s.includes(':') ? { ok: true, v: s.toLowerCase() } : { ok: false, at: 0 };
    case 'acla': {          // 1 つの字句で済む形だけ(any・A.B.C.D/長さ)。host A・A W は aclaRead
      if (s && /^[a-z]/i.test(s) && pfx('any', s)) return { ok: true, v: 'any' };
      if (s && s.includes('/')) { const r = checkVal({ v: 'v4pfx' }, s); return r.ok ? { ok: true, v: s } : r; }
      return { ok: false, at: 0 };
    }
    default: return { ok: true, v: s };
  }
}
// ACL の番地(記録 m14cfg.log・m14cfg4.log): any・host A.B.C.D・A.B.C.D/長さ・A.B.C.D ワイルドカード。打った形のまま持つ
// (any・host は正規の綴りに)。返り値 {v, adv} | {err:'incomplete'} | {err:'invalid', at(j からの字句の数), off}
function aclaRead(w, j) {
  const a = w[j];
  if (a == null) return { err: 'incomplete' };
  if (/^[a-z]/i.test(a) && pfx('any', a)) return { v: 'any', adv: 1 };
  if (/^[a-z]/i.test(a) && pfx('host', a)) {
    const b = w[j + 1];
    if (b == null) return { err: 'incomplete' };
    const at = ipv4At(b);
    return at < 0 ? { v: 'host ' + b, adv: 2 } : { err: 'invalid', at: 1, off: at };
  }
  if (a.includes('/')) { const r = checkVal({ v: 'v4pfx' }, a); return r.ok ? { v: a, adv: 1 } : { err: 'invalid', at: 0, off: r.at }; }
  const at = ipv4At(a);
  if (at >= 0) return { err: 'invalid', at: 0, off: at };
  const b = w[j + 1];
  if (b == null) return { err: 'incomplete' };        // 10 permit ipv4 238.5.0.0 → % Incomplete command.(記録 m14cfg4.log)
  const at2 = ipv4At(b);
  return at2 < 0 ? { v: a + ' ' + b, adv: 2 } : { err: 'invalid', at: 1, off: at2 };
}
// ? の一覧の鍵で ACL の番地を置く印: 打ち終えた番地= *・host だけ= host・アドレスだけ(ワイルドカード待ち)= *a
function aclaNorm(w, j) {
  const a = w[j];
  if (/^[a-z]/i.test(a) && pfx('any', a)) return { n: ['*'], adv: 1 };
  if (/^[a-z]/i.test(a) && pfx('host', a)) return w[j + 1] == null ? { n: ['host'], adv: 1 } : { n: ['*'], adv: 2 };
  if (a.includes('/')) return { n: ['*'], adv: 1 };
  if (ipv4At(a) >= 0) return null;
  return w[j + 1] == null ? { n: ['*a'], adv: 1 } : { n: ['*'], adv: 2 };
}

/* ---------------- type 7(XR の OSPF の鍵の表示。盤面の 3 つの鍵を復号して同じ方式と確かめた= design §8) ---------------- */
const X7 = 'dsfd;kfoA,.iyewrkldJKDHSUBsgvca69834ncxv9873254k;fg87';
function t7enc(plain) {
  const salt = Math.floor(Math.random() * 16);
  let out = p2(salt);
  for (let i = 0; i < plain.length; i++) out += (plain.charCodeAt(i) ^ X7.charCodeAt((salt + i) % X7.length)).toString(16).toUpperCase().padStart(2, '0');
  return out;
}

/* ---------------- 骨組み ---------------- */
function prepSchema(s) {
  const all = {};
  const walk = (n, parent) => {
    n.parent = parent;
    all[n.uid] = n;
    (n.ch || []).forEach((c, i) => { c.ord = i; walk(c, n); });
  };
  walk(s, null);
  return all;
}
const isW = t => 'w' in t;
function idn(sch) {       // 区別に使う値の数
  const nv = sch.toks.filter(t => !isW(t)).length;
  if (sch.t === 'K') return sch.idn != null ? sch.idn : nv;
  if (sch.t === 'M') return nv;
  return 0;
}
const nHead = sch => sch.toks.filter(t => !isW(t)).length;    // 頭の値の数(選べる語の値はその後ろに並ぶ)
function optsLine(sch, vals) {   // 選べる語の表示(骨組みに書いた順。記録 m14cfg.log)
  const out = [];
  const b = nHead(sch);
  (sch.opts || []).forEach((o, k) => {
    const v = vals[b + k];
    if (v == null || v === '') return;
    out.push(o.o);
    if (o.val) out.push(v);
  });
  return out;
}
function lineOf(sch, vals) {
  const out = [];
  let vi = 0;
  for (const t of sch.toks) {
    if (isW(t)) { out.push(t.w); continue; }
    const v = vals[vi++];
    if (v == null || v === '') continue;
    if (t.v === 'md5key') out.push(v);          // 値は「encrypted <16 進>」の形で持つ
    else out.push(v);
  }
  out.push(...optsLine(sch, vals));
  return out.join(' ');
}
// @delkey・@deldef の消した行の形(no の後ろ): 区別の値まで＋区別に使う選べる語(＋ @deldef は既定のある語を既定の値で)。
// 記録 m14cfg2.log: no 20・no rp-address 10.255.0.4・no bsr candidate-rp 10.255.0.2 priority 192 interval 60
function delForm(sch, vals) {
  const n = idn(sch), b = nHead(sch);
  const out = [];
  let vi = 0;
  for (const t of sch.toks) {
    if (vi >= n) break;
    if (isW(t)) out.push(t.w);
    else { const v = vals[vi++]; if (v != null && v !== '') out.push(v); }
  }
  (sch.opts || []).forEach((o, k) => {
    const v = vals[b + k];
    if (o.id) { if (v) out.push(o.o); return; }
    if (sch.deldef && o.val && o.val.def != null) out.push(o.o, o.val.def);
  });
  return out.join(' ');
}
function keyVals(sch, vals) {    // 文の区別(区別の値＋区別に使う選べる語の有無)
  let k = vals.slice(0, idn(sch)).join(' ');
  const b = nHead(sch);
  (sch.opts || []).forEach((o, i) => { if (o.id) k += '|' + (vals[b + i] ? o.o : ''); });
  return k;
}
function noLineOf(sch, vals, full, form) {      // 消す時の表示。full= コミットの中身・戻しの形(値まで)。そうでなければ編集中の形(語だけ)
  if (form === 'target' && (sch.delkey || sch.deldef)) return 'no ' + delForm(sch, vals);
  if (sch.t === 'L' && !full) {
    const words = sch.toks.filter(isW).map(t => t.w).join(' ');
    const tr = sch.toks.some(t => t.tr);
    return 'no ' + words + (tr ? ' ' : '');
  }
  const tr = sch.t === 'L' && sch.toks.some(t => t.tr);
  return 'no ' + lineOf(sch, vals) + (tr ? ' ' : '');
}

/* ---------------- 設定の木 ----------------
   節= {sch, vals, k?(M の子), raw?(O・読めない行の中身)}。根= {sch: 根, k: []} */
function idKey(n) {
  if (!n.sch || n.sch.t === 'O' || n.opaque) return 'O|' + n.raw[0];
  return n.sch.uid + '|' + keyVals(n.sch, n.vals);
}
const IFORD = { Loopback: 0, MgmtEth: 1, GigabitEthernet: 2, Null: 3 };
function ifKey(s) {
  const m = /^([A-Za-z-]+)(.*)$/.exec(s) || [null, s, ''];
  return [IFORD[m[1]] != null ? IFORD[m[1]] : 9].concat(m[2].split(/[/.]/).map(x => (/^\d+$/.test(x) ? +x : x)));
}
function cmpArr(a, b) {
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    if (a[i] === undefined) return -1;
    if (b[i] === undefined) return 1;
    if (a[i] < b[i]) return -1;
    if (a[i] > b[i]) return 1;
  }
  return 0;
}
function cmpNodes(a, b) {
  const oa = a.sch ? a.sch.ord : 1e6, ob = b.sch ? b.sch.ord : 1e6;
  if (oa !== ob) return oa - ob;
  if (!a.sch || a.sch !== b.sch || a.sch.t === 'O') return 0;
  const va = a.vals[0] || '', vb = b.vals[0] || '';
  switch (a.sch.sort) {
    case 'if': return cmpArr(ifKey(va), ifKey(vb));
    case 'len': return va.length - vb.length || (va < vb ? -1 : va > vb ? 1 : 0);
    case 'num': return cmpArr(va.split('.').map(Number), vb.split('.').map(Number));
    case 'rp': {      // override → 印なし → bidir、それぞれアドレスの順(記録 m14cfg2・m14cfg3・m14cfg4.log)
      const cat = n => { const h = nHead(n.sch), os = n.sch.opts || [], at = w => n.vals[h + os.findIndex(o => o.o === w)];
        return at('bidir') ? 2 : at('override') ? 0 : 1; };
      return cat(a) - cat(b) || cmpArr(va.split('.').map(Number), vb.split('.').map(Number));
    }
    default: return 0;
  }
}
function sortKids(list) {
  return list.map((n, i) => [n, i]).sort((x, y) => cmpNodes(x[0], y[0]) || x[1] - y[1]).map(x => x[0]);
}
function clone(x) {
  if (Array.isArray(x)) return x.map(clone);
  const n = { sch: x.sch, vals: x.vals ? x.vals.slice() : undefined };
  if (x.k) n.k = x.k.map(clone);
  if (x.raw) n.raw = x.raw.slice();
  if (x.opaque) n.opaque = true;
  if (x.stub) n.stub = true;
  return n;
}
function findKid(par, sch, vals) {
  const key = sch.uid + '|' + keyVals(sch, vals);
  return (par.k || []).find(n => idKey(n) === key);
}

/* ---------------- 表示 ---------------- */
// 中身の無い @gone の塊(router pim の address-family)は無いのと同じ(記録 m14cfg2.log・m14cfg3.log)
function goneEmpty(n) { return !!(n.sch && n.sch.gone && !(n.k || []).some(c => !goneEmpty(c))); }
function renderNode(n, d, out, nostub) {
  const ind = ' '.repeat(d);
  if (!n.sch || n.sch.t === 'O' || n.opaque) {
    for (const r of n.raw) out.push(ind + r);
    if (n.raw.length > 1) out.push(ind + '!');        // 中身を持つ塊(username・line など)の後ろ(記録 board.log)
    return;
  }
  if (goneEmpty(n)) return;
  out.push(ind + lineOf(n.sch, n.vals));
  if (n.sch.t === 'M') {
    for (const c of sortKids(n.k)) renderNode(c, d + 1, out, nostub);
    out.push(ind + '!');
    // 入った時にできた空の塊は本体の後ろに別に出る(multicast-routing・router igmp。記録 m14cfg.log)。差分の表示には出ない(記録 m14cfg4.log)
    if (n.stub && !nostub && n.k.some(c => !goneEmpty(c))) out.push(ind + lineOf(n.sch, n.vals), ind + '!');
  }
}
function renderTree(t, nostub) {
  const out = [];
  for (const c of sortKids(t.k)) renderNode(c, 0, out, nostub);
  return out;
}

/* ---------------- 差分 ----------------
   2 つの子の並び → [{kind: add|del|chg|blk, a, b, sub}](表示の並び)。blk= 両方にある M で中に変化がある */
function diffKids(ak, bk, touched) {
  ak = (ak || []).filter(n => !goneEmpty(n));
  const akeys = new Set(ak.map(idKey));
  bk = (bk || []).filter(n => !goneEmpty(n) || akeys.has(idKey(n)));     // 中身を消して空になった @gone の塊は「中を消した」形で出す(記録 m14cfg2.log)
  const amap = new Map((ak || []).map(n => [idKey(n), n]));
  const bmap = new Map((bk || []).map(n => [idKey(n), n]));
  const keys = [];
  for (const n of sortKids((ak || []).concat((bk || []).filter(n => !amap.has(idKey(n)))))) {
    const k = idKey(n);
    if (!keys.includes(k)) keys.push(k);
  }
  const out = [];
  for (const k of keys) {
    const a = amap.get(k), b = bmap.get(k);
    if (a && !b) out.push({ kind: 'del', a });
    else if (!a && b) out.push({ kind: 'add', b });
    else if (a.sch && a.sch.t === 'M' && !a.opaque) {
      const sub = diffKids(a.k, b.k, touched);
      if (sub.length || (touched && b.touched) || !!a.stub !== !!b.stub || b.stubSet) out.push({ kind: 'blk', a, b, sub });   // 入っただけの塊も編集中の表示には出る(記録 explore1.log)
    } else if (JSON.stringify(a.vals || a.raw) !== JSON.stringify(b.vals || b.raw)) out.push({ kind: 'chg', a, b });
  }
  return out;
}
// form: 'target'(編集中の show configuration)・'full'(コミットの中身と戻し)
function renderChanges(diff, d, form, out) {
  const ind = ' '.repeat(d);
  for (const e of diff) {
    if (e.kind === 'add') renderNode(e.b, d, out);
    else if (e.kind === 'chg') renderNode(e.b, d, out);
    else if (e.kind === 'blk') {
      // 空の塊は、この編集で入った時に(既にあっても)編集中の表示とコミットの中身に出る(記録 m14cfg3.log の router igmp・
      // 1 行の no で辿っただけでは出ない= m14cfg2.log)。stubSet= この編集で入った印(コミットの後の木には写さない)
      const stubShow = e.b.stubSet, stubGone = e.a.stub && !e.b.stub;
      if (e.sub.length || !stubGone) {
        out.push(ind + lineOf(e.b.sch, e.b.vals));
        renderChanges(e.sub, d + 1, form, out);
        out.push(ind + '!');
        if (stubShow && e.sub.length) out.push(ind + lineOf(e.b.sch, e.b.vals), ind + '!');
      }
      if (stubGone) stubDel(e.a, d, out);
    } else if (e.kind === 'del') {
      const a = e.a;
      if (!a.sch || a.sch.t === 'O' || a.opaque) { out.push(ind + 'no ' + a.raw[0].trim()); continue; }
      if (form === 'full' && a.sch.t === 'M' && a.sch.stub) {
        // 空の塊を持つ塊を丸ごと消す戻し: 本体の中を 1 つずつ消し、空の塊は別に消す(記録 m14cfg.log の「router igmp / no interface … / ! / no router igmp」)
        const kids = (a.k || []).filter(c => !goneEmpty(c));
        if (kids.length) { out.push(ind + lineOf(a.sch, a.vals)); renderChanges(kids.map(c => ({ kind: 'del', a: c })), d + 1, form, out); out.push(ind + '!'); }
        if (a.stub || !kids.length) stubDel(a, d, out);
        continue;
      }
      if (a.sch.t === 'M' && (a.sch.nest || (a.sch.nestfull && form === 'full')) && (a.k || []).some(c => !goneEmpty(c))) {     // router static など: 中の文を 1 つずつ消す形(記録 gaps1.log)。ACL・pim の af はコミットの中身と戻しだけ(記録 m14cfg.log)
        out.push(ind + lineOf(a.sch, a.vals));
        renderChanges(a.k.map(c => ({ kind: 'del', a: c })), d + 1, form, out);
        out.push(ind + '!');
      } else out.push(ind + noLineOf(a.sch, a.vals, form === 'full' || a.sch.t !== 'L', form));
    }
  }
}
// 空の塊を消す時の形: keep= 「名前 / !」(multicast-routing)・no= 「no 名前」(router igmp)。記録 m14cfg.log の戻し
function stubDel(a, d, out) {
  const ind = ' '.repeat(d);
  if (a.sch.stub === 'no') out.push(ind + 'no ' + lineOf(a.sch, a.vals));
  else out.push(ind + lineOf(a.sch, a.vals), ind + '!');
}
// show commit changes diff の形(印の欄 3 字＋字下げ。記録 explore1/m1/orders.log)
function allDel(diff) { return diff.every(e => e.kind === 'del' || (e.kind === 'blk' && allDel(e.sub))); }
function renderDiff(diff, d, out) {
  const ind = ' '.repeat(d);
  const put = (mk, s) => out.push(mk.padEnd(3) + s);
  const whole = (n, mk, dd) => {
    const lines = [];
    renderNode(n, dd, lines, true);
    for (const l of lines) put(l.trim() === '!' ? ' ' : mk, l);
  };
  for (const e of diff) {
    if (e.kind === 'add') whole(e.b, '+', d);
    else if (e.kind === 'del' && e.a.sch && e.a.sch.deldef) put('-', ind + delForm(e.a.sch, e.a.vals));    // 記録 m14cfg2.log の「-    bsr candidate-rp 10.255.0.2 priority 192 interval 60」
    else if (e.kind === 'del') whole(e.a, '-', d);
    else if (e.kind === 'chg') { put('<-', ind + lineOf(e.a.sch, e.a.vals)); put('+>', ind + lineOf(e.b.sch, e.b.vals)); }
    else {
      if (!e.sub.length && e.b.sch.stub) continue;     // 空の塊だけの違いは差分に出ない(記録 m14cfg4.log。中身の無い差分の形は未採取)
      // 中を消すだけの塊の行は -(記録 orders.log の router ospf 1)。@dkeep の塊(M14 のマルチキャストと ACL)は印なし
      // (記録 m14cfg2.log の ipv4 access-list MC-SM・multicast-routing・address-family ipv4・router igmp・router pim)
      put(allDel(e.sub) && !e.b.sch.dkeep ? '-' : ' ', ind + lineOf(e.b.sch, e.b.vals));
      renderDiff(e.sub, d + 1, out);
      put(' ', ind + '!');
    }
  }
}

/* ---------------- 作る ---------------- */
function create(bundle, opt) {
  const lang = langOf(opt.lang);
  const J = (ja, en) => lang === 'en' ? en : ja;
  const sim = s => ({ c: 'sim', s: SIM_PREFIX[lang] + s });
  const simSoft = s => ({ c: 'sim', s: SIM_PREFIX[lang] + s, soft: true });   // 実機の行を 1 つ省いた注記(答えの例で出てよい)
  const schema = bundle.schema;
  const ALL = prepSchema(schema);
  const board = opt.base || {};
  // ? の一覧は版・機種ごとの組(盤面の helpset。無ければ既定の組= XRT-01 の XRv 9000 24.3.1)。組どうしは混ぜない
  const HELP = (board.helpset && (bundle.helpSets || {})[board.helpset]) || bundle.help || {};
  const host = board.host || opt.host;
  const ver = board.version || '24.3.1';
  const S = {
    mode: 'exec', stack: [], R: null, T: null, hist: [], ask: null, failed: null, trial: null,
    sessBase: null, log: [], lastChange: null, onAsync: null,
  };
  const baseErr = [], candErr = [];

  /* ---- 実機の ? の一覧(文脈の鍵を骨組みに沿って正規化) ---- */
  const H = {};            // 鍵 → 一覧
  function modeSch(mode) {
    mode = mode.split('@')[0];
    if (mode === 'config') return schema;
    return Object.values(ALL).find(n => n.mode === mode) || null;
  }
  // 打ってある語 → 正規化した鍵(値は *)。骨組みで読めない所は、一覧に無い語を値とみなす
  function normKey(mode, words) { return normInfo(mode, words).key; }
  // last= 最後に読んだ文 {r(matchPrefixSchema の返り値), pre(その文の前までの鍵), rest(その文の後ろに残った語)}
  function normInfo(mode, words) {
    const out = [];
    let cont = modeSch(mode);
    let i = 0;
    let last = null;
    // 骨組みに沿って読めるだけ読む
    if (cont && words.length) {
      let w = words.slice();
      const isNo = same(w[0], 'no');
      if (isNo) { out.push('no'); w = w.slice(1); i = 1; }
      while (w.length && cont) {
        const r = matchPrefixSchema(cont, w);
        if (!r) break;
        last = { r, pre: `${mode}|${out.join(' ')}`, rest: w.slice(r.used) };
        out.push(...r.norm); w = w.slice(r.used); i += r.used;
        cont = r.sch.t === 'M' ? r.sch : null;
        if (!r.sch || r.sch.t !== 'M') break;
      }
    }
    let key = `${mode}|${out.join(' ')}`;
    for (; i < words.length; i++) {
      const list = H[key] || HELP[key];
      const t = words[i];
      const lit = list && list.find(it => same(it.n, t) && !/^\d{10}$/.test(it.h) && it.h !== 'Commit ID');
      key += (key.endsWith('|') ? '' : ' ') + (lit ? lit.n : !list && !/^[\d.:/]+$/.test(t) ? t : '*');
    }
    return { key, last };
  }
  // 骨組みの文の頭が語の並びに完全に合うか(正規化用・省略なし)。返り値 {sch, used, norm}
  function matchPrefixSchema(cont, w) {
    let best = null;
    for (const c of cont.ch || []) {
      if (c.t === 'O') continue;
      const norm = [];
      let j = 0, ok = true, ti = 0;
      if (c.seq && w.length && !/^\d+$/.test(w[0])) { norm.push('*'); ti = 1; }   // 番号を省いた ACL の行(記録: permit ? と 10 permit ? は同じ一覧)
      for (; ti < c.toks.length; ti++) {
        const t = c.toks[ti];
        if (j >= w.length) { ok = j > 0 && !isW(t); break; }
        if (isW(t)) { if (!same(w[j], t.w)) { ok = false; break; } norm.push(t.w); j++; }
        else {
          if (t.v === 'line') { norm.push('*'); j = w.length; break; }
          if (t.v === 'ifname') {     // 口の名前は型ごとの印。型だけ(番号の前)は値でない(鍵は interface Loopback のまま)
            const one = ifParse(w[j]), v = one || ifJoin(w[j], w[j + 1]);
            if (!v) { ok = false; break; }
            norm.push(ifStar(v)); j += one ? 1 : 2; continue;
          }
          if (t.v === 'acla') { const r = aclaNorm(w, j); if (!r) { ok = false; break; } norm.push(...r.n); j += r.adv; continue; }
          if (t.opt && c.opts && c.opts.some(o => same(o.o, w[j]))) continue;     // 値を省いて選べる語へ
          norm.push('*'); j++;
        }
      }
      // 選べる語(頭を打ち終えた後)。used= 使った語の番号・pending= 値を待つ語
      const hn = norm.length, used = [];
      let pending = null;
      if (ok && c.opts && ti >= c.toks.length) {
        while (j < w.length) {
          let k = c.opts.findIndex(o => same(o.o, w[j]));
          if (k < 0) {        // 略した語(pri → priority)。使っていない語の中で 1 つに決まる時だけ
            const hit = c.opts.map((o, x) => x).filter(x => !used.includes(x) && pfx(c.opts[x].o, w[j]));
            if (hit.length === 1) k = hit[0];
          }
          if (k < 0) break;
          norm.push(c.opts[k].o); j++; used.push(k);
          if (c.opts[k].val) { if (j >= w.length) { pending = k; break; } norm.push('*'); j++; }
        }
      }
      if (ok && j > 0 && (!best || j > best.used)) best = { sch: c, used: j, norm, hn, opts: used, pending };
    }
    return best;
  }
  // 選べる語の途中の一覧で、記録に無い組み合わせ: 頭だけの一覧から使った語を除く。値を待つ所はその語だけを書いた時の一覧、
  // 終わりの語(bidir)の後ろは <cr> だけ(記録 m14cfg.log: priority 100 ?・group-list … ?・group-list … priority 50 ? が、頭だけの一覧から使った語を除いた形)
  function optHelp(mode, words) {
    const ni = normInfo(mode, words), L = ni.last;
    if (!L || !L.r.sch.opts || L.rest.length || (!L.r.opts.length && L.r.pending == null)) return null;
    const r = L.r, c = r.sch;
    const head = L.pre + (L.pre.endsWith('|') ? '' : ' ') + r.norm.slice(0, r.hn).join(' ');
    if (r.pending != null) {
      const l = H[head + ' ' + c.opts[r.pending].o];
      return l ? { items: l, key: null, derived: true } : null;
    }
    const base = H[head];
    if (!base) return null;
    if (r.opts.some(k => c.opts[k].term)) return { items: base.filter(it => it.n === '<cr>'), key: null, derived: true };
    const usedNames = r.opts.map(k => c.opts[k].o);
    return { items: base.filter(it => !usedNames.includes(it.n)), key: null, derived: true };
  }
  for (const [k, items] of Object.entries(HELP)) {
    const [mode, text] = [k.slice(0, k.indexOf('|')), k.slice(k.indexOf('|') + 1)];
    const nk = normKey(mode, text ? text.split(' ') : []);
    if (!H[nk]) H[nk] = items;
  }
  // 下位モードの一覧にだけある語(commit・do・end など)= 1 行で深く打った時の一覧には出ない語
  const GEN = new Set();
  (function () {
    const pairs = [['config-ospf-ar-if|', 'config|router ospf * area * interface *'],
      ['config-pim-default-ipv4|', 'config|router pim address-family ipv4']];     // XRd 26.1.1 の組(記録 m14explore.log・m14cfg4.log)
    for (const [a, b] of pairs) {
      const inMode = H[a], path = H[b];
      if (inMode && path) for (const it of inMode) if (!path.some(p => p.n === it.n)) GEN.add(it.n);
    }
  })();
  // 一覧の鍵のモード: 口の下位モード(config-if・config-ospf-ar-if)は口の型ごと(Loopback は印なし。記録 ifnames4.log)
  function keyMode(mode, st) {
    if (!st || !/-if$/.test(mode) || !st.vals || !st.vals[0]) return mode;
    const t = ifTypeOfName(st.vals[0]);
    return !t || t.full === 'Loopback' ? mode : `${mode}@${t.full}`;
  }
  const curKeyMode = () => S.mode !== 'cfg' ? 'exec' : keyMode(curMode(), S.stack[S.stack.length - 1]);
  function helpAt(mode, words, viaPath) {
    const k = normKey(mode, words);
    if (H[k]) return { items: H[k], key: k };
    const oh = optHelp(mode, words);
    if (oh) return oh;
    if (viaPath) {          // 1 行で深く打った: その下位モードの一覧から、下位モードでだけ打てる語を除く
      const vk = normKey(viaPath.mode, viaPath.rest);
      const m = H[vk] || (optHelp(viaPath.mode, viaPath.rest) || {}).items;
      if (m) return { items: viaPath.rest.length ? m : m.filter(it => !GEN.has(it.n)), key: null, derived: true };
    }
    return null;
  }
  const KWPH = /^(<.*>|[A-Z][A-Z.]*(\/\w+)?|A\.B\.C\.D.*|X:X::X.*|WORD|LINE|Hostname.*|IP subnet mask|R\/S\/I\/P.*|\||\()$/;
  // 値の途中の ? で、その形の値の札も並べる(cost 5? → <1-65535>・address 10.1? → A.B.C.D/prefix・GigabitEthernet 0/0? → R/S/I/P…。記録 ifnames3.log)
  function phTakes(n, p) {
    if (/^<\d+-\d+>$/.test(n)) return /^\d+$/.test(p);
    if (/^A\.B\.C\.D/.test(n)) return /^[\d.]+(\/\d*)?$/.test(p);
    if (/^R\/S\/I\/P/.test(n)) return /^[\d/]+$/.test(p);
    return false;
  }
  const kwNames = items => items.filter(it => !KWPH.test(it.n) && it.n !== '<cr>').map(it => it.n);

  /* ---- 盤面 ---- */
  function parseConfig(text, errs) {
    // ! の行は読み飛ばすが、骨組みで扱わない塊(router isis など)の中の ! はその中身として残す(記録 board-pe2.log)
    const lines = text.split('\n').filter(l => l.trim() && !l.startsWith('!!') && l.trim() !== 'end');
    const t = { sch: schema, k: [] };
    let i = 0;
    function block(par, cont, d) {
      while (i < lines.length) {
        const l = lines[i];
        if (/^\s*!\s*$/.test(l)) { i++; continue; }
        const ind = l.length - l.trimStart().length;
        if (ind < d) return;
        if (ind > d) { i++; continue; }
        const w = l.trim().split(/\s+/);
        const r = cont ? matchExact(cont, w) : null;
        if (r && r.sch.t !== 'O') {
          i++;
          const n = setNode(par, r.sch, r.vals);
          if (r.sch.t === 'M') block(n, r.sch, d + 1);
        } else {
          // 骨組みで扱わない文: 中身ごと持つ(並びは O の位置)
          const raw = [l.trim()];
          i++;
          while (i < lines.length && lines[i].length - lines[i].trimStart().length > d) { raw.push(lines[i].slice(d)); i++; }
          const o = { sch: r && r.sch.t === 'O' ? r.sch : null, raw, opaque: !(r && r.sch.t === 'O') };
          if (!o.sch && errs) errs.push(raw[0]);
          par.k.push(o);
        }
      }
    }
    block(t, schema, 0);
    return t;
  }
  // 記録の行(省略なし)を骨組みに合わせる。返り値 {sch, vals}
  function matchExact(cont, w) {
    for (const c of cont.ch || []) {
      if (c.t === 'O') { if (c.toks.every((t, k) => w[k] === t.w)) return { sch: c, vals: [] }; continue; }
      const r = matchToks(c, w, 0, true);
      if (r && r.end === w.length) return { sch: c, vals: r.vals };
    }
    return null;
  }
  // 1 つの文の型(c.toks)に語を合わせる(exact= 省略なし)。返り値 {vals, end} か null
  function matchToks(c, w, i, exact) {
    const vals = [];
    let j = i;
    for (let ti = 0; ti < c.toks.length; ti++) {
      const t = c.toks[ti];
      if (j >= w.length) {
        if (!isW(t) && t.opt) { vals.push(t.def || ''); continue; }
        return null;
      }
      if (isW(t)) {
        if (exact ? w[j] !== t.w : !pfx(t.w, w[j])) return null;
        j++;
      } else if (t.v === 'acla') {
        const r = aclaRead(w, j);
        if (!r.v) return null;
        vals.push(r.v); j += r.adv;
      } else if (t.opt && c.opts && c.opts.some(o => o.o === w[j])) {
        vals.push(t.def || '');          // 値を省いて選べる語へ(rp-address 10.255.0.3 bidir)
      } else if (t.v === 'line') { vals.push(w.slice(j).join(' ')); j = w.length; }
      else if (t.v === 'md5key') {
        if (w[j] === 'encrypted' && w[j + 1]) { vals.push('encrypted ' + w[j + 1]); j += 2; }
        else if (w[j] === 'clear' && w[j + 1]) { vals.push('encrypted ' + t7enc(w[j + 1])); j += 2; }
        else { vals.push('encrypted ' + t7enc(w[j])); j++; }
      } else {
        const r = checkVal(t, w[j]);
        if (!r.ok) {
          if (t.opt) { vals.push(t.def || ''); continue; }
          return null;
        }
        vals.push(r.v); j++;
      }
    }
    if (c.opts) {                         // 選べる語(@any は順が自由。記録 m14cfg.log)
      const ov = c.opts.map(o => (o.val && o.val.def != null ? o.val.def : ''));
      let last = -1;
      while (j < w.length) {
        const k = c.opts.findIndex((o, x) => o.o === w[j] && (c.any || x > last));
        if (k < 0) break;
        const o = c.opts[k];
        if (o.val) {
          if (w[j + 1] == null) return null;
          const r = checkVal(o.val, w[j + 1]);
          if (!r.ok) return null;
          ov[k] = r.v; j += 2;
        } else { ov[k] = o.o; j++; }
        last = k;
        if (o.term) break;
      }
      vals.push(...ov);
    }
    return { vals, end: j };
  }
  function setNode(par, sch, vals) {
    let n = findKid(par, sch, vals);
    if (n) {
      if (sch.t !== 'M') n.vals = vals.slice();
      return n;
    }
    n = { sch, vals: vals.slice() };
    if (sch.t === 'M') n.k = [];
    par.k.push(n);
    return n;
  }
  function delNode(par, sch, vals) {
    const key = sch.t === 'L' || sch.t === 'F' ? sch.uid + '|' : sch.uid + '|' + keyVals(sch, vals);
    const i = (par.k || []).findIndex(n => idKey(n) === key);
    if (i >= 0) par.k.splice(i, 1);
    return i >= 0;
  }
  // 変更の文(「no …」を含む・字下げで入れ子)を木に当てる(戻し・load rollback changes・盤面の過去の再現)
  function applyText(tree, text) {
    const lines = text.split('\n').filter(l => l.trim() && !l.startsWith('!!') && l.trim() !== 'end' && !/^\s*!\s*$/.test(l));
    let i = 0, bad = 0;
    function block(par, cont, d) {
      while (i < lines.length) {
        const l = lines[i];
        const ind = l.length - l.trimStart().length;
        if (ind < d) return;
        i++;
        if (ind > d) continue;
        let w = l.trim().split(/\s+/);
        const no = w[0] === 'no';
        if (no) w = w.slice(1);
        let r = null;
        for (const c of cont.ch || []) {
          if (c.t === 'O') continue;
          const m = matchToks(c, w, 0, true);
          if (m && m.end === w.length) { r = { sch: c, vals: m.vals }; break; }
          if (no && m === null && c.t === 'L') {        // no cost 50 など(値まで書いてある)
            const words = c.toks.filter(isW).map(t => t.w);
            if (words.every((x, k) => w[k] === x)) { r = { sch: c, vals: [] }; break; }
          }
        }
        if (!r) {
          if (no && w[0] === 'interface' && cont === schema) { r = null; }
          bad++; continue;
        }
        if (no) { delNode(par, r.sch, r.vals); while (i < lines.length && lines[i].length - lines[i].trimStart().length > d) i++; }
        else {
          const n = setNode(par, r.sch, r.vals);
          if (r.sch.t === 'M') block(n, r.sch, d + 1);
        }
      }
    }
    block(tree, schema, 0);
    return bad;
  }

  /* ---- 盤面を作る: 稼働中の設定と、コミットの履歴(各回の後の木は、今の木から戻しを逆にたどって作る) ---- */
  S.R = parseConfig(board.running || '', baseErr);
  const lastCh = /^!! Last configuration change at (.*)$/m.exec(board.running || '');
  S.lastChange = lastCh ? lastCh[1] : null;
  S.noChange = /^!! No configuration change since last restart$/m.test(board.running || '');   // XRd の day0 の盤面(記録 board-pe2.log)
  S.hist = (board.commits || []).map(c => Object.assign({}, c, { after: null }));
  // 履歴の空の盤面(XRd の day0)は、最初のコミットの前の設定= 盤面そのもの(戻しの行き先にできる)
  const base0 = (board.commits || []).length ? null : clone(S.R);
  const afterAt = k => (k >= 0 ? S.hist[k].after : k === -1 ? base0 : null);
  if (S.hist.length) {
    let cur = clone(S.R);
    for (let k = S.hist.length - 1; k >= 0; k--) {
      S.hist[k].after = cur;
      if (k === 0) break;
      if (!S.hist[k].rollback) { cur = null; for (let j = k - 1; j >= 0; j--) S.hist[j].after = null; break; }
      cur = clone(cur);
      if (applyText(cur, S.hist[k].rollback)) candErr.push(J(`コミット ${S.hist[k].label || S.hist[k].id} の戻しに読めない行`, `unreadable line in the rollback of commit ${S.hist[k].label || S.hist[k].id}`));
    }
  }

  const promptBase = () => `RP/0/RP0/CPU0:${host}`;
  function curMode() {
    if (S.mode !== 'cfg') return 'exec';
    const top = S.stack[S.stack.length - 1];
    return top ? top.sch.mode : 'config';
  }
  function promptText() {
    if (S.ask) return S.ask.prompt;
    if (S.mode === 'cfg') return `${promptBase()}(${curMode()})#`;
    return `${promptBase()}#`;
  }
  const now = () => new Date();

  /* ---- 木の上の位置(編集のモードの並び)。木を作り直しても辿れるよう、型と値で持つ ---- */
  function nodeAt(tree, stack, create) {
    let n = tree;
    for (const st of stack) {
      let c = findKid(n, st.sch, st.vals);
      if (!c) { if (!create) return null; c = setNode(n, st.sch, st.vals); }
      n = c;
    }
    return n;
  }
  const changed = () => S.T && diffKids(S.R.k, S.T.k).length > 0;

  /* ---- 語を決める(実機の一覧で曖昧さと誤りの位置を決める・無ければ骨組みの語で) ---- */
  // 返り値 {w} | {err:'ambig'} | {err:'invalid', at} | {unsup: w}(実機にはあるが素振り台に無い語)
  function pickKw(tok, schemaWords, devList) {
    const pool = devList ? kwNames(devList) : schemaWords;
    const exS = schemaWords.find(w => same(w, tok)), exP = pool.find(w => same(w, tok));
    if (exS) return { w: exS };
    if (exP) return { unsup: exP };
    const hit = [...new Set(pool.filter(w => pfx(w, tok)))];
    if (hit.length === 1) return schemaWords.includes(hit[0]) ? { w: hit[0] } : { unsup: hit[0] };
    if (hit.length > 1) {
      // Enter で略した語を決める時は cisco-support の語を数えない(記録 gaps5.log: conf → configure・co は曖昧)。Tab・? の一覧には出る
      if (devList) {
        const pub = hit.filter(w => !devList.some(it => it.n === w && /\(cisco-support\)$/.test(it.h)));
        if (pub.length === 1) return schemaWords.includes(pub[0]) ? { w: pub[0] } : { unsup: pub[0] };
      }
      return { err: 'ambig' };
    }
    let k = tok.length;
    while (k > 0 && !pool.some(w => pfx(w, tok.slice(0, k)))) k--;
    return { err: 'invalid', at: k };
  }

  /* ---- 1 つの文を読む(省略あり・実機の一覧で曖昧さを決める)。
     cont から toks[i..] を読み、M を辿り、文の終わりまで。返り値 {steps:[{sch, vals}], end} か {err, at(字句の番号), off} */
  function readStmt(cont, toks, i, baseMode, typedWords) {
    const isNo = typedWords[0] === 'no';
    const steps = [];
    let mode = baseMode;
    let viaRest = [];          // 1 行で下位モードへ入った後に打った語(一覧の文脈)
    const crossed = () => steps.length && steps[steps.length - 1].sch.t === 'M';
    while (true) {
      if (i >= toks.length) {
        if (!steps.length) return { err: 'incomplete' };
        return { steps, end: i };
      }
      // この位置で置ける文の候補
      let cands = (cont.ch || []).filter(c => c.t !== 'O');
      const words0 = typedWords.concat(toks.slice(typedWords.length, i).map(t => t.s));
      let posTok = 0;
      let vals = new Map(cands.map(c => [c, []]));
      let j = i;
      const viaPath = crossed() ? { mode, rest: [] } : null;
      while (true) {
        // 頭を打ち終えた文の後ろの選べる語
        const solo = cands.length === 1 ? cands[0] : null;
        if (solo && solo.opts && posTok >= solo.toks.length && j < toks.length) {
          const r = readOpts(solo, toks, j, vals.get(solo), baseMode, typedWords);
          if (r.err) return r;
          steps.push({ sch: solo, vals: r.vals });
          i = r.end;
          break;
        }
        // 番号を打たない ACL の行(記録 m14cfg2.log の permit … → 10・20・30)
        if (posTok === 0 && solo && solo.seq && j < toks.length && !/^\d+$/.test(toks[j].s)) { vals.get(solo).push('@next'); posTok++; continue; }
        // 候補の pos 番目の型
        const active = cands.filter(c => posTok < c.toks.length);
        const done = cands.filter(c => posTok >= c.toks.length || c.toks.slice(posTok).every(t => !isW(t) && (t.opt || (isNo && c.t === 'L')))
          || (isNo && c.t === 'K' && c.idn != null && vals.get(c).length >= c.idn));
        if (j >= toks.length || !active.length) {
          const fin = done.length === 1 ? done[0] : done.find(c => posTok >= c.toks.length) || null;
          if (!fin) return { err: 'incomplete' };
          const vv = vals.get(fin).slice();
          for (const t of fin.toks.slice(posTok)) if (!isW(t)) vv.push(t.def || '');
          if (fin.opts) vv.push(...fin.opts.map(o => (o.val && o.val.def != null ? o.val.def : '')));
          steps.push({ sch: fin, vals: vv });
          i = j;
          break;
        }
        const tok = toks[j];
        const kwC = active.filter(c => isW(c.toks[posTok]));
        const vC = active.filter(c => !isW(c.toks[posTok]));
        const typedSoFar = toks.slice(i, j).map(t => t.s);
        const hl = helpAt(baseMode, typedWords.concat(toks.slice(typedWords.length, j).map(t => t.s)),
          viaPath ? { mode, rest: typedSoFar } : (crossed() ? null : null));
        const hl2 = hl || helpAt(mode, typedSoFar, null);
        // 省ける値の所に選べる語(rp-address 10.255.0.3 bi → bidir。記録 m14cfg3.log)
        const skipV = vC.find(c => c.toks[posTok].opt && c.opts && c.opts.some(o => pfx(o.o, tok.s)));
        if (skipV) { cands = [skipV]; vals.get(skipV).push(skipV.toks[posTok].def || ''); posTok++; continue; }
        // 値として読めるか
        let vHit = null;
        for (const c of vC) {
          const t = c.toks[posTok];
          if (t.v === 'line') { vHit = { c, v: toks.slice(j).map(x => x.s).join(' '), adv: toks.length - j }; break; }
          if (t.v === 'acla') {
            const r = aclaRead(toks.map(x => x.s), j);
            if (r.err === 'incomplete') return { err: 'incomplete' };
            if (r.err) { if (vC.length > 1) continue; return { err: 'invalid', at: j + r.at, off: r.off }; }
            vHit = { c, v: r.v, adv: r.adv }; break;
          }
          if (t.v === 'md5key') {
            const a = toks[j].s, b = toks[j + 1] && toks[j + 1].s;
            if ((same(a, 'encrypted') || same(a, 'clear')) && b) vHit = { c, v: 'encrypted ' + (same(a, 'clear') ? t7enc(b) : b), adv: 2 };
            else vHit = { c, v: 'encrypted ' + t7enc(a), adv: 1 };
            break;
          }
          if (t.v === 'ipv4' && c.toks[posTok + 1] && c.toks[posTok + 1].v === 'mask' && /\//.test(tok.s)) {
            const m = /^([^/]+)\/(\d{1,2})$/.exec(tok.s);
            if (m && ipv4At(m[1]) < 0 && +m[2] <= 32) {
              const len = +m[2], mask = [0, 1, 2, 3].map(q => { const b = Math.max(0, Math.min(8, len - q * 8)); return 256 - (1 << (8 - b)); }).join('.');
              vHit = { c, v: [m[1], mask], adv: 1, two: true };
              break;
            }
          }
          if (t.v === 'ifname' && !ifParse(tok.s) && ifTypeOf(tok.s)) {     // 型と番号を分けて打った形(記録 ifnames.log・ifnames5.log)
            const nx = toks[j + 1];
            if (!nx) return { err: 'incomplete' };                          // interface Loopback → % Incomplete command.
            const v = ifJoin(tok.s, nx.s);
            if (!v) return { err: 'invalid', at: j + 1, off: 0 };          // interface Loopback abc → 誤りの印は abc の頭
            vHit = { c, v, adv: 2 }; break;
          }
          const r = checkVal(t, tok.s);
          if (r.ok) { vHit = { c, v: r.v, adv: 1 }; break; }
        }
        let kw = null;
        if (kwC.length) {
          const sw = [...new Set(kwC.map(c => c.toks[posTok].w))];
          const pk = pickKw(tok.s, sw, hl2 ? hl2.items : null);
          if (pk.w) kw = pk.w;
          else if (!vHit) {
            if (pk.unsup) return { err: 'unsup', at: j, word: pk.unsup };
            if (pk.err === 'ambig') return { err: 'ambig', at: j };
            return { err: 'invalid', at: j, off: pk.at };
          }
        }
        if (kw) {
          cands = kwC.filter(c => c.toks[posTok].w === kw);
          j++; posTok++;
          continue;
        }
        if (vHit) {
          cands = [vHit.c];
          const arr = vals.get(vHit.c);
          if (vHit.two) { arr.push(vHit.v[0], vHit.v[1]); posTok += 2; }
          else { arr.push(vHit.v); posTok++; }
          j += vHit.adv;
          continue;
        }
        // 値の誤り: 誤りの位置は型ごと(ipv4 は誤った区切りの頭・ほかは字句の頭)
        if (vC.length) {
          const t = vC[0].toks[posTok];
          const r = checkVal(t, tok.s);
          if (r.ambig) return { err: 'ambig', at: j };
          if (hl2) { const pk = pickKw(tok.s, [], hl2.items); if (pk.unsup) return { err: 'unsup', at: j, word: pk.unsup }; }   // 10 remark …・10 permit tcp …
          return { err: 'invalid', at: j, off: r.at || 0 };
        }
        if (hl2) return { err: 'invalid', at: j, off: 0 };
        return { err: 'invalid', at: j, off: 0 };
      }
      const last = steps[steps.length - 1];
      if (last.sch.t === 'M' && i < toks.length) { cont = last.sch; mode = keyMode(cont.mode, last); continue; }
      if (i < toks.length) {
        // 文の後ろに余計な語
        const tok = toks[i];
        const hl = helpAt(baseMode, typedWords.concat(toks.slice(typedWords.length, i).map(t => t.s)), null);
        let off = 0;
        if (hl) { const pk0 = pickKw(tok.s, [], hl.items); if (pk0.unsup) return { err: 'unsup', at: i, word: pk0.unsup }; }   // ACL の行の後ろの log など
        if (hl) { const pool = kwNames(hl.items); let k = tok.s.length; while (k > 0 && !pool.some(w => pfx(w, tok.s.slice(0, k)))) k--; off = k; }
        return { err: 'invalid', at: i, off };
      }
      return { steps, end: i };
    }
  }

  // 選べる語を読む(頭を打ち終えた後)。@any は順が自由・ほかは書いた順。終わりの語($)の後ろには何も書けない(記録 m14cfg.log の … bidir override)
  function readOpts(c, toks, j, hv, baseMode, typedWords) {
    const ov = c.opts.map(o => (o.val && o.val.def != null ? o.val.def : ''));
    const used = new Set();
    let last = -1;
    while (j < toks.length) {
      const avail = c.opts.map((o, k) => ({ o, k })).filter(x => !used.has(x.k) && (c.any || x.k > last));
      const tok = toks[j];
      const hl = helpAt(baseMode, typedWords.concat(toks.slice(typedWords.length, j).map(t => t.s)), null);
      const pk = pickKw(tok.s, avail.map(x => x.o.o), hl ? hl.items : null);
      if (!pk.w) {
        if (pk.unsup) return { err: 'unsup', at: j, word: pk.unsup };
        if (pk.err === 'ambig') return { err: 'ambig', at: j };
        return { err: 'invalid', at: j, off: pk.at || 0 };
      }
      const x = avail.find(y => y.o.o === pk.w);
      if (!x) return { err: 'invalid', at: j, off: 0 };
      j++;
      if (x.o.val) {
        if (j >= toks.length) return { err: 'incomplete' };
        const r = checkVal(x.o.val, toks[j].s);
        if (!r.ok) return { err: 'invalid', at: j, off: r.at || 0 };
        ov[x.k] = r.v; j++;
      } else ov[x.k] = x.o.o;
      used.add(x.k); last = x.k;
      if (x.o.term && j < toks.length) return { err: 'invalid', at: j, off: 0 };
    }
    return { vals: hv.concat(ov), end: j };
  }
  function nextSeq(par, sch) {       // 番号を省いた ACL の行の番号= 今の最大＋10(記録 m14cfg2.log)
    const nums = (par.k || []).filter(n => n.sch === sch).map(n => +n.vals[0]).filter(n => n > 0);
    return String(nums.length ? Math.max(...nums) + 10 : 10);
  }

  /* ---- 誤りの出力 ---- */
  function errOut(line, toks, r, promptLen) {
    if (r.err === 'incomplete') return [dev(DEV.incomplete)];
    if (r.err === 'ambig') return [dev(DEV.ambig(line.trim()))];
    if (r.err === 'unsup') return [sim(J(`「${r.word}」は実機にある語ですが、素振り台では扱いません(この単元の範囲外)。`, `"${r.word}" exists on the real device, but the drill does not handle it (outside this unit).`))];
    const tok = toks[r.at] || { st: line.length };
    return [dev(' '.repeat(promptLen + tok.st + (r.off || 0)) + '^'), dev(DEV.invalid)];
  }

  /* ---- 設定モードの 1 行 ---- */
  const CFG_CMDS = ['abort', 'commit', 'do', 'end', 'exit', 'load', 'no', 'root', 'show', 'clear', 'describe', 'pwd'];
  function execCfg(line, toks, quiet) {
    const mode = curKeyMode();
    const plen = promptText().length;
    const devList = (H[`${mode}|`] || null);
    const first = toks[0].s;
    // 設定モードの共通のコマンド(実機の一覧で語を決める)
    const pool = devList ? kwNames(devList) : CFG_CMDS;
    const ex = pool.find(w => same(w, first));
    let hit = ex ? [ex] : [...new Set(pool.filter(w => pfx(w, first)))];
    // 下位モードの一覧に無い共通のコマンドは、一番上の一覧で決める(abort は下位モードの ? に出ないが通る。記録 ifnames2.log・ifnames5.log)
    if (!hit.length && mode !== 'config' && H['config|']) {
      const top = kwNames(H['config|']).filter(w => CFG_CMDS.includes(w) && w !== 'no');
      const ex2 = top.find(w => same(w, first));
      hit = ex2 ? [ex2] : top.filter(w => pfx(w, first));
    }
    const generic = hit.length === 1 && CFG_CMDS.includes(hit[0]) && hit[0] !== 'no' ? hit[0] : null;
    if (generic) return cfgGeneric(generic, line, toks);
    // 文(no を含む)。今のモードで読めなければ上のモードで試す(記録 explore1/modes.log)
    const isNo = hit.length === 1 && hit[0] === 'no' || same(first, 'no');
    const off = isNo ? 1 : 0;
    if (isNo && toks.length === 1) return { out: [dev(DEV.incomplete)] };
    let firstErr = null;
    for (let lv = S.stack.length; lv >= 0; lv--) {
      const cont = lv === 0 ? schema : S.stack[lv - 1].sch;
      const r = readStmt(cont, toks, off, lv === 0 ? 'config' : keyMode(cont.mode, S.stack[lv - 1]), isNo ? ['no'] : []);
      if (!r.err) {
        S.stack = S.stack.slice(0, lv);
        return applyStmt(r.steps, isNo);
      }
      if (!firstErr) firstErr = r;
      if (lv === S.stack.length && r.err === 'unsup' && r.at === off) break;   // 今のモードの語(pim の af の interface。記録 m14explore.log)は上で試さない
    }
    return { out: errOut(line, toks, firstErr, plen), err: firstErr.err };
  }
  function applyStmt(steps, isNo) {
    const par = nodeAt(S.T, S.stack, true);
    if (isNo) {
      let p = par;
      for (let k = 0; k < steps.length - 1; k++) { p = findKid(p, steps[k].sch, steps[k].vals); if (!p) return { out: [] }; }
      const last = steps[steps.length - 1];
      delNode(p, last.sch, last.vals);
      return { out: [] };
    }
    let p = par;
    const path = [];
    for (const st of steps) {
      if (st.sch.seq && st.vals[0] === '@next') st.vals[0] = nextSeq(p, st.sch);
      p = setNode(p, st.sch, st.vals);
      if (st.sch.t === 'M') {
        p.touched = true;
        if (st.sch.stub) { p.stub = true; p.stubSet = true; }     // 入ると空の塊ができる(multicast-routing・router igmp。記録 m14cfg2.log・m14cfg3.log)
        path.push({ sch: st.sch, vals: st.vals.slice(0, idn(st.sch)) });
      }
    }
    const last = steps[steps.length - 1];
    if (last.sch.t === 'M') S.stack = S.stack.concat(path);      // 下位モードへ入る(1 行で辿った時も)
    return { out: [] };
  }

  /* ---- 設定モードの共通のコマンド ---- */
  function cfgGeneric(cmd, line, toks) {
    const t = now();
    const rest = toks.slice(1).map(x => x.s);
    if (cmd === 'exit') {
      if (S.stack.length) { S.stack.pop(); return { out: [] }; }
      return leaveCfg();
    }
    if (cmd === 'end') return leaveCfg();
    if (cmd === 'root') { S.stack = []; return { out: [] }; }
    if (cmd === 'abort') { S.T = null; S.mode = 'exec'; S.stack = []; return { out: [] }; }
    if (cmd === 'do') return execOp(line.slice(toks[1] ? toks[1].st : line.length), tokenize(line.slice(toks[1] ? toks[1].st : line.length)), true);
    if (cmd === 'commit') return commitCmd(rest, line, toks);
    if (cmd === 'show') return showCmd(toks.slice(1), line, true);
    if (cmd === 'load') {
      const w = rest;
      if (!w.length || !pfx('rollback', w[0]) || !w[1] || !pfx('changes', w[1])) {
        return { out: [sim(J('load は「load rollback changes …」だけを扱います。', 'Of the load commands, the drill handles only "load rollback changes …".'))] };
      }
      const sel = selectCommits(w.slice(2));
      if (sel.err) return { out: sel.err };
      if (sel.list.length !== 1) return { out: [sim(J('素振り台は 1 回ぶんの「load rollback changes <ID か ラベル>」と「last 1」だけを扱います。', 'The drill handles "load rollback changes" for a single commit only (<ID or label>, or "last 1").'))] };
      const c = sel.list[0];
      if (!c.rollback) return { out: [sim(J('このコミットの戻しの中身は記録していません(盤面の記録より前)。', 'The rollback of this commit was not recorded (it is older than the board\'s capture).'))] };
      applyText(S.T, c.rollback);
      return { out: [dev(DEV.loading), simSoft(J('実機はここに読み込んだ字数の行(… bytes parsed in 1 sec …)を出します。数え方は採っていないので省きます。', 'The real device prints a byte count here ("… bytes parsed in 1 sec …"). How it counts has not been captured, so the line is left out.'))] };
    }
    return { out: [sim(J(`「${cmd}」は扱いません。`, `The drill does not handle "${cmd}".`))] };
  }
  function leaveCfg() {
    if (S.trial) {
      S.ask = { kind: 'trial', prompt: DEV.trialAsk };
      return { out: [dev(''), dev(DEV.trialExit)], ask: true };
    }
    if (changed()) { S.ask = { kind: 'unc', prompt: DEV.uncAsk }; return { out: [], ask: true }; }
    S.mode = 'exec'; S.stack = []; S.T = null;
    return { out: [] };
  }
  function execAsk(line) {
    const a = lc(line.trim());          // END の問いへの NO も通る(記録 ifnames2.log)
    const k = S.ask.kind;
    if (k === 'unc') {
      if (a === 'yes') {
        S.ask = null;
        const r = doCommit({}, true);
        if (r.failed) return { out: [sim(J('実機はここでコミットに失敗した時の表示を出します(採っていません)。', 'The real device shows its commit-failure output here (not captured).'))] };
        S.mode = 'exec'; S.stack = []; S.T = null;
        return { out: [] };
      }
      if (a === 'no') { S.ask = null; S.mode = 'exec'; S.stack = []; S.T = null; return { out: [] }; }
      if (a === 'cancel' || a === '') { S.ask = null; S.stack = []; return { out: [] }; }   // 設定モードの一番上へ(記録 m1.log)
      return { out: [dev(DEV.badAnswer)], ask: true };
    }
    if (k === 'trial') {
      if (a === 'yes') { S.ask = null; trialRollback('rollback'); S.mode = 'exec'; S.stack = []; S.T = null; return { out: [] }; }
      if (a === 'no' || a === '') { S.ask = null; S.stack = []; return { out: [] }; }
      return { out: [dev(DEV.yesNo)], ask: true };
    }
    if (k === 'others') {
      if (a === 'yes') { S.ask = null; S.sessBase = lastId(); const r = commitCmd(S.pendingCommit, '', [], true); return r; }
      if (a === 'no' || a === '') { S.ask = null; return { out: [sim(J('実機はここでコミットを取りやめた時の表示を出します(採っていません)。編集中の設定は残しています。', 'The real device shows its output for a declined commit here (not captured). Your uncommitted changes are kept.'))] }; }
      return { out: [dev(DEV.yesNo)], ask: true };
    }
    S.ask = null;
    return { out: [] };
  }

  /* ---- コミット ---- */
  const lastId = () => S.hist.length ? S.hist[S.hist.length - 1].id : '1000000000';
  const nextId = () => String(Number(lastId()) + 1);
  function commitCmd(w, line, toks, again) {
    const t = now();
    const o = { label: null, comment: null, confirmed: null };
    for (let i = 0; i < w.length; i++) {
      const x = lc(w[i]);
      if ('label'.startsWith(x) && x.length >= 1 && x !== 'l' || x === 'label') { o.label = w[++i]; if (!o.label) return { out: [dev(DEV.incomplete)] }; continue; }
      if ('comment'.startsWith(x) && x.length >= 3) { o.comment = w.slice(i + 1).join(' '); if (!o.comment) return { out: [dev(DEV.incomplete)] }; break; }
      if ('confirmed'.startsWith(x) && x.length >= 3) {
        let sec = 600;
        if (w[i + 1] && /^\d+$/.test(w[i + 1])) { sec = +w[++i]; if (sec < 30 || sec > 65535) return { out: [sim(J('確認つきコミットの秒は 30〜65535 です(範囲外の時の実機の文言は採っていません)。', 'commit confirmed takes 30 to 65535 seconds (the real device\'s message for a value out of range has not been captured).'))] }; }
        else if (w[i + 1] && pfx('minutes', w[i + 1])) { i++; if (!/^\d+$/.test(w[i + 1] || '')) return { out: [dev(DEV.incomplete)] }; sec = 60 * +w[++i]; }
        else if (!w[i + 1]) return { out: [sim(J('秒を省いた「commit confirmed」の既定の時間は採っていません。秒を付けてください。', 'The default time of "commit confirmed" without seconds has not been captured. Give the seconds.'))] };
        o.confirmed = sec; continue;
      }
      return { out: [sim(J(`commit の「${w[i]}」は扱いません(label・comment・confirmed だけ)。`, `The drill does not handle "${w[i]}" on commit (only label, comment and confirmed).`))] };
    }
    const out = again ? [] : [dev(tsLine(t))];
    if (S.trial && !o.confirmed) {
      if (changed()) return { out: out.concat([sim(J('確認待ちのコミットがある時に、さらに変更を足したコミットは扱いません(実機の動きを採っていません)。', 'A commit that adds more changes while a confirmed commit is pending is not handled (the real device\'s behaviour has not been captured).'))]) };
      clearTimeout(S.trial.timer);
      S.trial = null;
      return { out: out.concat([dev(''), dev(DEV.confirmTrial)]) };
    }
    if (!changed()) return { out: out.concat([dev(DEV.noChanges)]) };
    if (!again && S.sessBase != null && S.hist.some(c => Number(c.id) > Number(S.sessBase) && !c.mine)) {
      S.ask = { kind: 'others', prompt: DEV.othersAsk };
      S.pendingCommit = w;
      return { out: out.concat([dev('')], DEV.others.map(dev)), ask: true };
    }
    if (o.label && S.hist.some(c => c.label === o.label)) return { out: out.concat([dev(''), dev(DEV.labelUsed)]) };
    if (o.label && !/^[A-Za-z]/.test(o.label)) return { out: out.concat([sim(J('ラベルは英字で始めます(実機の誤りの文言は採っていません)。', 'A label starts with a letter (the real device\'s error text has not been captured).'))]) };
    const r = doCommit(o, false);
    if (r.failed) return { out: out.concat(r.out) };
    if (o.confirmed) startTrial(o.confirmed, r.entry);
    return { out };
  }
  // 意味の検査(実機の記録で確かめたものだけ: 定義の無いポリシーを付けた隣接= m1.log)
  function semantic(tree) {
    const errs = [];
    const walk = (n, path) => {
      for (const c of n.k || []) {
        if (c.sch && c.sch.t === 'L' && c.sch.toks[0].w === 'route-policy') errs.push({ path: path.concat([c]), kind: 'policy', name: c.vals[0] });
        if (c.sch && c.sch.t === 'M' && c.sch.toks[0].w === 'neighbor' && !(c.k || []).some(x => x.sch && x.sch.toks[0].w === 'remote-as')) errs.push({ path: path.concat([c]), kind: 'noas' });
        if (c.k) walk(c, path.concat([c]));
      }
    };
    walk(tree, []);
    return errs;
  }
  function doCommit(o, quiet) {
    const errs = semantic(S.T);
    if (errs.length) {
      S.failed = errs;
      return { failed: true, out: [dev(''), dev(DEV.pseudoFail)] };
    }
    const before = S.R, after = clone(S.T);
    const t = now();
    const entry = {
      id: nextId(), label: o.label || null, user: 'SUZUKI', line: o.line || 'vty0:node0_RP0_CPU0', client: o.client || 'CLI',
      time: tsCommit(t), comment: o.comment != null ? `   ${o.comment} ` : '  NONE',
      changes: changesText(before, S.T), rollback: changesText(after, before), after: clone(after), mine: !o.other,   // 中身は S.T から(この編集で入った空の塊の印 stubSet を見る)
    };
    S.hist.push(entry);
    S.R = after;
    S.T = clone(after);
    S.failed = null;
    S.lastChange = `${tsCommit(t)} by SUZUKI`;
    S.sessBase = entry.id;
    return { entry };
  }
  function changesText(a, b) {
    const out = [DEV.building, `!! IOS XR Configuration ${ver}`];
    renderChanges(diffKids(a.k, b.k), 0, 'full', out);
    out.push('end', '');
    return out.join('\n');
  }
  function startTrial(sec, entry) {
    const before = S.hist[S.hist.length - 2];
    S.trial = { entry, before: before ? before.after : base0 };
    S.trial.timer = setTimeout(() => {
      if (!S.trial) return;
      trialRollback('vty0:node0_RP0_CPU0', true);
      if (S.onAsync) S.onAsync([sim(J(`確認つきコミットの期限(${sec} 秒)が来たので、実機と同じく元の設定に戻しました(履歴に Rollback が 1 件増えます)。実機の画面には何も出ません。`, `The confirmed commit expired (${sec} seconds), so the configuration was rolled back, as on the real device (one Rollback entry is added to the history). The real device prints nothing at this point.`))]);
    }, sec * 1000);
  }
  function trialRollback(lineName, other) {
    if (!S.trial) return;
    clearTimeout(S.trial.timer);
    const target = S.trial.before;
    S.trial = null;
    if (!target) return;
    const saveT = S.T;
    S.T = clone(target);
    doCommit({ client: 'Rollback', line: lineName, other }, true);
    if (other) { S.T = S.mode === 'cfg' ? clone(S.R) : null; S.sessBase = S.hist[S.hist.length - 2] ? S.hist[S.hist.length - 2].id : S.sessBase; }
    else S.T = saveT && S.mode === 'cfg' ? clone(S.R) : null;
  }

  /* ---- コミットを選ぶ(ID・ラベル・last N・to・to-exclude) ---- */
  function findCommit(x) { return S.hist.find(c => c.id === x || c.label === x); }
  function selectCommits(w) {
    if (!w.length) return { err: [dev(DEV.incomplete)] };
    if (pfx('last', w[0]) && w[0].length >= 2) {
      if (!w[1]) return { err: [dev(DEV.incomplete)] };
      const n = +w[1];
      return { list: S.hist.slice(-n).reverse(), n, how: 'last' };
    }
    const c = findCommit(w[0]);
    if (!c) return { err: [sim(J(`「${w[0]}」というコミットの ID・ラベルはありません(実機の誤りの文言は採っていません)。`, `There is no commit ID or label "${w[0]}" (the real device's error text has not been captured).`))] };
    return { list: [c], how: 'one' };
  }

  /* ---- show ---- */
  function hdr() { return [DEV.building, `!! IOS XR Configuration ${ver}`]; }
  function showCmd(w, line, inCfg) {
    const t = now();
    const s = w.map(x => x.s);
    const ts = dev(tsLine(t));
    const pick = (x, list) => { const ex = list.find(y => same(y, x)); if (ex) return ex; const h = list.filter(y => pfx(y, x)); return h.length === 1 ? h[0] : null; };
    const a = s[0] && pick(s[0], ['running-config', 'configuration', 'commit', 'clock']);
    if (!a) return { out: [sim(J(`show ${s.join(' ')} は扱いません(素振り台が作るのは設定と履歴の表示だけ。ルーティング テーブル・隣接などの状態はラボで)。`, `The drill does not handle "show ${s.join(' ')}". It builds only the configuration and commit-history displays; for routing tables, neighbors and other state, use the lab.`))] };
    if (a === 'clock') {
      const d = t;
      return { out: [ts, dev(`${p2(d.getUTCHours())}:${p2(d.getUTCMinutes())}:${p2(d.getUTCSeconds())}.${String(d.getUTCMilliseconds()).padStart(3, '0')} UTC ${DOW[d.getUTCDay()]} ${MON[d.getUTCMonth()]} ${d.getUTCDate()} ${d.getUTCFullYear()}`)] };
    }
    if (a === 'running-config') return { out: [ts].concat(showRun(s.slice(1)).map(dev)) };
    if (a === 'commit') {
      if (!inCfg) return { out: [sim(J('show commit は設定モードの中だけです。', '"show commit" is available only in configuration mode.'))] };
      if (s[1] && pfx('changes', s[1]) && s[2] && pfx('diff', s[2])) {
        const out = hdr();
        renderDiff(diffKids(S.R.k, S.T.k), 0, out);
        out.push('end', '');
        return { out: [ts].concat(out.map(dev)) };
      }
      return { out: [dev(DEV.incomplete)] };
    }
    // configuration …
    const b = s[1] && pick(s[1], ['commit', 'rollback', 'failed', 'merge', 'running', 'history', 'changes', 'formal', 'lock', 'sessions']);
    if (!s[1]) {
      if (!inCfg) return { out: [sim(J('運用モードの「show configuration」は扱いません。', 'The drill does not handle "show configuration" in EXEC mode.'))] };
      const out = hdr();
      renderChanges(diffKids(S.R.k, S.T.k, true), 0, 'target', out);
      out.push('end', '');
      return { out: [ts].concat(out.map(dev)) };
    }
    if (b === 'commit') {
      const c = s[2] && pick(s[2], ['list', 'changes']);
      if (!c) return { out: [dev(DEV.incomplete)] };
      if (c === 'list') {
        let n = null, detail = false;
        for (const x of s.slice(3)) { if (/^\d+$/.test(x)) n = +x; else if (pfx('detail', x)) detail = true; else return { out: [sim(J(`「${x}」は扱いません。`, `The drill does not handle "${x}".`))] }; }
        return { out: [ts].concat(commitList(n, detail).map(dev)) };
      }
      const sel = selectCommits(s.slice(3));
      if (sel.err) return { out: sel.err };
      if (sel.list.length !== 1) return { out: [sim(J('複数回をまとめた表示(last 2 以上)は扱いません。実機は各回の中身をつなげた形で出します(記録 gaps1.log)。', 'Showing several commits at once (last 2 or more) is not handled. The real device prints the changes of each commit one after another.'))] };
      return { out: [ts].concat(sel.list[0].changes.split('\n').map(dev)) };
    }
    if (b === 'rollback') {
      if (!s[2] || !pfx('changes', s[2])) return { out: [dev(DEV.incomplete)] };
      const sel = selectCommits(s.slice(3));
      if (sel.err) return { out: sel.err };
      if (sel.list.length !== 1) return { out: [sim(J('複数回をまとめた表示(last 2 以上)は扱いません。', 'Showing several commits at once (last 2 or more) is not handled.'))] };
      if (!sel.list[0].rollback) return { out: [sim(J('このコミットの戻しの中身は記録していません(盤面の記録より前)。', 'The rollback of this commit was not recorded (it is older than the board\'s capture).'))] };
      return { out: [ts].concat(sel.list[0].rollback.split('\n').map(dev)) };
    }
    if (b === 'failed') {
      if (!inCfg) return { out: [sim(J('show configuration failed は設定モードで打ちます。', 'Enter "show configuration failed" in configuration mode.'))] };
      if (!S.failed) return { out: [sim(J('失敗したコミットがありません(この時の実機の表示は採っていません)。', 'There is no failed commit (the real device\'s output for this case has not been captured).'))] };
      return { out: [ts].concat(failedOut()) };
    }
    return { out: [sim(J(`show configuration ${s.slice(1).join(' ')} は扱いません。`, `The drill does not handle "show configuration ${s.slice(1).join(' ')}".`))] };
  }
  function failedOut() {
    const out = DEV.semHead.map(dev);
    const notes = [];
    for (const e of S.failed) {
      const d0 = e.path.length - 1;
      e.path.forEach((n, i) => out.push(dev(' '.repeat(i) + lineOf(n.sch, n.vals))));
      if (e.kind === 'policy') out.push(dev(DEV.policyErr(e.name)));
      else notes.push(sim(J('この誤り(remote-as の無い隣接)の実機の文言は採っていません。', 'The real device\'s text for this error (a neighbor without remote-as) has not been captured.')));
      for (let i = d0 - 1; i >= 0; i--) out.push(dev(' '.repeat(i) + '!'));
    }
    out.push(dev('end'), dev(''));
    return out.concat(notes);
  }
  function commitList(n, detail) {
    if (!S.hist.length) return ['The commit database is empty.'];      // XRd の day0 の盤面(記録 board-pe2.log)
    const list = S.hist.slice().reverse().slice(0, n || 100);
    if (detail) {
      const out = [];
      list.forEach((c, i) => {
        out.push('');
        out.push(`${String(i + 1).padStart(4)}) CommitId: ${c.id.padEnd(27)}Label: ${c.label || 'NONE'}`);
        out.push(`      UserId:   ${c.user.padEnd(27)}Line:  ${c.line}`);
        out.push(`      Client:   ${c.client.padEnd(27)}Time:  ${c.time}`);
        out.push(`      Comment:${c.comment}`);
      });
      return out;
    }
    return DEV.listHead.concat(list.map((c, i) => `${String(i + 1).padEnd(5)}${(c.label || c.id).padEnd(22)}${c.user.padEnd(10)}${c.line.slice(0, 18).padEnd(20)}${c.client.padEnd(12)}${c.time}`));
  }
  // show running-config [道]
  function showRun(w) {
    const tree = S.R;
    if (!w.length) {
      const out = hdr();
      if (S.lastChange) out.push(`!! Last configuration change at ${S.lastChange}`);
      else if (S.noChange) out.push('!! No configuration change since last restart');
      out.push('!');
      out.push(...renderTree(tree), 'end', '');
      return out;
    }
    // 道を骨組みで辿る(値を省いた所はその並びの全部)
    let sel = [{ node: tree, keep: true }];
    let cont = schema;
    let i = 0;
    let wraps = [];
    const picked = [];
    function walk(nodes, cont, i) {
      if (i >= w.length) { picked.push(...nodes); return; }
      for (const nd of nodes) {
        const kids = nd.k || [];
        // この位置の文
        const words = [];
        let best = null;
        for (const c of (nd.sch && nd.sch.ch) || cont.ch || []) {
          if (c.t === 'O') { if (pfx(c.toks[0].w, w[i])) best = best || { c, used: 1 }; continue; }
          let j = i, ok = true, vals = [];
          for (const t of c.toks) {
            if (j >= w.length) break;
            if (isW(t)) { if (!pfx(t.w, w[j])) { ok = false; break; } j++; }
            else {
              const r = checkVal(t, w[j]);
              const jn = !r.ok && t.v === 'ifname' ? ifJoin(w[j], w[j + 1]) : null;      // show running-config interface Loopback 0(記録 ifnames.log)
              if (jn) { vals.push(jn); j += 2; continue; }
              if (!r.ok) { ok = false; break; } vals.push(r.v); j++;
            }
          }
          if (ok && j > i && (!best || j - i > best.used)) best = { c, used: j - i, vals };
        }
        if (!best) continue;
        const nv = best.vals ? best.vals.length : 0;
        const match = kids.filter(k => k.sch === best.c && (nv === 0 || k.vals.slice(0, nv).join(' ') === best.vals.join(' ')));
        for (const m of match) {
          const consumed = i + best.used;
          if (consumed >= w.length || m.sch.t !== 'M') picked.push({ m, anc: nd });
          else walk([m], m.sch, consumed);
        }
      }
    }
    walk([tree], schema, 0);
    if (!picked.length) return [DEV.noItem, ''];
    // 祖先ごと描く
    const anc = n => { const chain = []; let p = parentOf(tree, n); while (p && p !== tree) { chain.unshift(p); p = parentOf(tree, p); } return chain; };
    const out = [];
    const items = picked.map(x => x.m || x);
    const filtered = { sch: schema, k: [] };
    for (const m of items) {
      const chain = anc(m);
      let cur = filtered;
      for (const a of chain) {
        let c = cur.k.find(x => x.src === a);
        if (!c) { c = { sch: a.sch, vals: a.vals, k: [], src: a }; cur.k.push(c); }
        cur = c;
      }
      cur.k.push(m);
    }
    out.push(...renderTree(filtered, true), '');      // 部分の表示には空の塊は出ない(記録 m14cfg.log)
    return out;
  }
  function parentOf(tree, n) {
    for (const c of tree.k || []) {
      if (c === n) return tree;
      if (c.k) { const p = parentOf(c, n); if (p) return p; }
    }
    return null;
  }

  /* ---- 運用モード ---- */
  const OP = ['configure', 'show', 'rollback', 'terminal', 'exit', 'quit'];
  function execOp(line, toks, viaDo) {
    if (!toks.length) return { out: [] };
    const plen = (viaDo ? promptText().length + (line.length ? 3 : 0) : promptText().length);
    const devList = H['exec|'];
    const pool = devList ? kwNames(devList) : OP;
    const first = toks[0].s;
    const pk = pickKw(first, OP, devList);
    if (pk.err === 'ambig') return { out: [dev(DEV.ambig(line.trim()))] };
    if (pk.err === 'invalid') return { out: [dev(' '.repeat(plen + toks[0].st + pk.at) + '^'), dev(DEV.invalid)] };
    if (pk.unsup) return { out: [sim(J(`「${pk.unsup}」は実機にあるコマンドですが、素振り台では扱いません。`, `"${pk.unsup}" is a command on the real device, but the drill does not handle it.`))] };
    const cmd = pk.w;
    const t = now();
    if (cmd === 'configure') {
      if (viaDo) return { out: [sim(J('設定モードの中で do configure は扱いません。', 'The drill does not handle "do configure" inside configuration mode.'))] };
      const w2 = toks[1] && toks[1].s;
      if (w2 && pfx('exclusive', w2)) return { out: [sim(J('configure exclusive(排他)は扱いません。素振り台はセッションが 1 つだけです。', 'configure exclusive is not handled. The drill has only one session.'))] };
      if (w2 && !pfx('terminal', w2)) return { out: [dev(' '.repeat(plen + toks[1].st) + '^'), dev(DEV.invalid)] };
      S.mode = 'cfg'; S.stack = []; S.T = clone(S.R); S.sessBase = lastId();
      return { out: [dev(tsLine(t))] };
    }
    if (cmd === 'terminal') return { out: [dev(tsLine(t))] };
    if (cmd === 'exit' || cmd === 'quit') return { out: [sim(J('実機ではここでセッションが閉じます。素振り台は続けます(最初からやり直す時は「やり直す」)。', 'On the real device the session closes here. The drill carries on (to start over, press Reset).'))] };
    if (cmd === 'show') return showCmd(toks.slice(1), line, viaDo);
    if (cmd === 'rollback') {
      if (viaDo) return { out: [sim(J('設定モードの中で do rollback は扱いません。', 'The drill does not handle "do rollback" inside configuration mode.'))] };
      const w = toks.slice(1).map(x => x.s);
      if (!w[0] || !pfx('configuration', w[0])) return { out: [dev(DEV.incomplete)] };
      return rollbackCmd(w.slice(1), t);
    }
    return { out: [sim(J(`「${cmd}」は扱いません。`, `The drill does not handle "${cmd}".`))] };
  }
  function rollbackCmd(w, t) {
    if (!w.length) return { out: [dev(DEV.incomplete)] };
    let target = null, how = '', name = '';
    if (pfx('last', w[0]) && w[0].length >= 2) {
      const n = +w[1];
      if (!w[1] || !(n >= 1)) return { out: [dev(DEV.incomplete)] };
      const k = S.hist.length - n - 1;
      if (!afterAt(k)) return { out: [sim(J('素振り台は盤面の記録より前へは戻せません。', 'The drill cannot roll back past the oldest commit in the board\'s capture.'))] };
      target = afterAt(k); how = 'last'; name = n;
    } else if (pfx('to-exclude', w[0]) && w[0].length >= 4) {
      const c = w[1] && findCommit(w[1]);
      if (!c) return { out: [w[1] ? sim(J(`「${w[1]}」というコミットはありません(実機の文言は採っていません)。`, `There is no commit "${w[1]}" (the real device's text has not been captured).`)) : dev(DEV.incomplete)] };
      if (!c.after) return { out: [sim(J('素振り台は盤面の記録より前へは戻せません。', 'The drill cannot roll back past the oldest commit in the board\'s capture.'))] };
      target = c.after; how = 'toex'; name = w[1];
    } else if (same(w[0], 'to')) {
      const c = w[1] && findCommit(w[1]);
      if (!c) return { out: [w[1] ? sim(J(`「${w[1]}」というコミットはありません(実機の文言は採っていません)。`, `There is no commit "${w[1]}" (the real device's text has not been captured).`)) : dev(DEV.incomplete)] };
      const k = S.hist.indexOf(c) - 1;
      if (!afterAt(k)) return { out: [sim(J('素振り台は盤面の記録より前へは戻せません。', 'The drill cannot roll back past the oldest commit in the board\'s capture.'))] };
      target = afterAt(k); how = 'to'; name = w[1];
    } else return { out: [sim(J('rollback configuration は last・to・to-exclude の形を扱います。', 'Of rollback configuration, the drill handles the last, to and to-exclude forms.'))] };
    if (S.trial) return { out: [sim(J('確認待ちのコミットがある間の rollback は扱いません。', 'Rollback while a confirmed commit is pending is not handled.'))] };
    S.T = clone(target);
    const out = [dev(tsLine(t))].concat(DEV.rbHead.map(dev));
    if (!changed()) { S.T = null; return { out: out.concat([sim(J('戻す変化がありません(この時の実機の表示は採っていません)。', 'There is nothing to roll back (the real device\'s output for this case has not been captured).'))]) }; }
    doCommit({ client: 'Rollback' }, true);
    S.T = null;
    out.push(simSoft(J('実機はここに確定した項目の数の行(… items committed in 1 sec …)を出します。数え方は採っていないので省きます。', 'The real device prints an item count here ("… items committed in 1 sec …"). How it counts has not been captured, so the line is left out.')));
    out.push(...DEV.rbTail.map(dev));
    if (how === 'last') out.push(dev(DEV.rbLast(name)));
    else if (how === 'toex') out.push(dev(DEV.rbToEx(name)));
    else out.push(sim(J(`実機はここで「to」で戻した時の結びの行を出します(採っていません)。戻した先= ${name} の前。`, `The real device prints a closing line here for a rollback with "to" (not captured). Rolled back to just before ${name}.`)));
    return { out };
  }

  /* ---- ? と Tab ---- */
  function fmtList(items) {
    const w = Math.max(...items.map(it => it.n.length)) + 2;
    return items.map(it => `  ${it.n.padEnd(w)}${it.h}`);
  }
  function tabCols(names) {      // Tab・語の途中の ? の候補(字の順・横に 4 列・4 列目は詰める。記録 explore1/gaps1.log)
    const rows = [];
    const ncol = 4;
    const widths = [];
    names.forEach((n, i) => { const c = i % ncol; widths[c] = Math.max(widths[c] || 0, n.length + 2); });
    for (let i = 0; i < names.length; i += ncol) {
      rows.push(names.slice(i, i + ncol).map((n, c) => (c === ncol - 1 ? n : n.padEnd(widths[c]))).join(''));
    }
    return rows;
  }
  // 打った行 → その位置の一覧(実機の一覧があれば実機の行・無ければ骨組みの語を薄く)
  function listAt(line) {
    const toks = tokenize(line);
    const endsSpace = /\s$/.test(line) || line === '';
    const done = endsSpace ? toks : toks.slice(0, -1);
    const partial = endsSpace ? '' : toks[toks.length - 1].s;
    const mode = curKeyMode();
    const words = done.map(t => t.s);
    // 動く一覧(既にある名前・コミットの履歴)
    const dyn = dynamicList(mode, words);
    if (dyn) return { items: dyn, partial, dyn: true };
    // 打ってある語を読めるか(誤りなら誤りを返す)
    let ctxMode = mode, ctxWords = words;
    if (S.mode === 'cfg' && words.length) {
      const res = locate(words);
      if (res.err) return { err: res.err, toks: done };
      if (res.found) { ctxMode = res.mode; ctxWords = res.words; }
    }
    let h = helpAt(ctxMode, ctxWords, null);
    if (!h && S.mode === 'cfg' && ctxMode !== mode) h = helpAt(ctxMode, ctxWords, null);
    if (!h && S.mode === 'cfg') {
      const res = locate(words);
      if (res.via) h = helpAt(res.via.mode, res.via.rest, res.via);
    }
    if (h) return { items: h.items, partial, raw: !h.derived };
    return { items: schemaWordsAt(words).map(n => ({ n, h: '', raw: null, dim: true })), partial, dim: true };
  }
  // 設定モードで、打ってある語が骨組みのどこにあたるか(? の文脈)
  function locate(words) {
    const toks = words.map((s, i) => ({ s, st: 0 }));
    for (let lv = S.stack.length; lv >= 0; lv--) {
      const cont = lv === 0 ? schema : S.stack[lv - 1].sch;
      const mode = lv === 0 ? 'config' : keyMode(cont.mode, S.stack[lv - 1]);
      const key = normKey(mode, words);
      if (H[key]) return { found: true, mode, words };
      // 文の途中まで読めるか
      const isNo = same(words[0], 'no');
      const off = isNo ? 1 : 0;
      let steps = [], c = cont, i = off, ok = true;
      while (i < words.length) {
        const r = matchPrefixLoose(c, words.slice(i));
        if (!r) { ok = false; break; }
        steps.push(r); i += r.used;
        if (r.sch.t !== 'M' || r.partial) break;
        c = r.sch;
      }
      if (ok && i === words.length) {
        const lastM = [...steps].reverse().find(s => s.sch.t === 'M' && !s.partial);
        if (lastM && steps[steps.length - 1] === lastM) return { via: { mode: keyMode(lastM.sch.mode, lastM), rest: [] }, mode };
        if (lastM) {
          const idx = steps.indexOf(lastM);
          const restWords = words.slice(off + steps.slice(0, idx + 1).reduce((a, s) => a + s.used, 0));
          return { via: { mode: keyMode(lastM.sch.mode, lastM), rest: restWords }, mode };
        }
        return { found: true, mode, words };
      }
    }
    return { err: 'invalid' };
  }
  // 語の並びの頭を骨組みの文に合わせる(省略あり・文の途中で終わってよい)
  function matchPrefixLoose(cont, w) {
    let best = null;
    for (const c of cont.ch || []) {
      if (c.t === 'O') continue;
      let j = 0, ok = true, ti = 0;
      const vals = [];
      if (c.seq && w.length && !/^\d+$/.test(w[0])) { vals.push('@next'); ti = 1; }
      for (; ti < c.toks.length; ti++) {
        const t = c.toks[ti];
        if (j >= w.length) break;
        if (isW(t)) { if (!pfx(t.w, w[j])) { ok = false; break; } j++; }
        else if (t.v === 'line') { j = w.length; break; }
        else if (t.v === 'acla') {
          const r = aclaRead(w, j);
          if (r.v) { vals.push(r.v); j += r.adv; continue; }
          if (r.err === 'incomplete') { j = w.length; break; }      // host・アドレスだけ(続きを待つ)
          ok = false; break;
        } else if (t.opt && c.opts && c.opts.some(o => pfx(o.o, w[j]))) { vals.push(''); continue; }
        else {
          const r = checkVal(t, w[j]);
          if (!r.ok && t.v === 'ifname') {         // 型と番号を分けて打った形。型だけ(番号の前)は値でない
            const v = ifJoin(w[j], w[j + 1]);
            if (v) { vals.push(v); j += 2; continue; }
            if (ifTypeOf(w[j])) { ok = false; break; }
          }
          if (!r.ok && !t.opt) { ok = false; break; }
          if (r.ok) { vals.push(r.v); j++; }
        }
      }
      if (ok && c.opts && ti >= c.toks.length) {      // 選べる語(略してよい)と、その値
        while (j < w.length) {
          const k = c.opts.findIndex(o => pfx(o.o, w[j]));
          if (k < 0) break;
          j++;
          if (c.opts[k].val) { if (j >= w.length) break; j++; }
        }
      }
      if (ok && j > 0 && (!best || j > best.used)) best = { sch: c, used: j, partial: j < c.toks.filter(t => isW(t) || !t.opt).length, vals };
    }
    return best;
  }
  function schemaWordsAt(words) {
    const out = new Set();
    const cont = S.mode === 'cfg' ? (S.stack.length ? S.stack[S.stack.length - 1].sch : schema) : null;
    if (cont && !words.length) for (const c of cont.ch || []) if (c.t !== 'O' && isW(c.toks[0])) out.add(c.toks[0].w);
    return [...out].sort();
  }
  function dynamicList(mode, words) {
    const k = normKey(mode, words);
    const isRb = /\|(rollback configuration|load rollback changes|show configuration (commit|rollback) changes)$/.test(k);
    if (isRb && (H[k] || /rollback configuration$/.test(k))) {
      const fixed = (H[k] || []).filter(it => !/^\d{10}$/.test(it.n) && !/^\d{10}$/.test(it.h) && it.h !== 'Commit ID');
      const labs = S.hist.filter(c => c.label).map(c => ({ n: c.label, h: c.id }));
      const ids = S.hist.slice().reverse().map(c => ({ n: c.id, h: 'Commit ID' }));
      return labs.concat(fixed, ids).map(it => ({ n: it.n, h: it.h }));
    }
    // 名前の並び(vrf ? の MGMT・CUST-A など): 記録の一覧のうち、WORD と同じ説明の名前を今の名前に置き換える
    const list = H[k];
    if (!list) return null;
    const ph = list.find(it => it.n === 'WORD');
    if (!ph) return null;
    const names = list.filter(it => it.h === ph.h && it.n !== 'WORD');
    if (!names.length) return null;
    const cur = currentNames(mode, words);
    if (!cur) return null;
    const rest = list.filter(it => !(it.h === ph.h && it.n !== 'WORD'));
    const wi = rest.indexOf(ph);
    return rest.slice(0, wi).concat(cur.map(n => ({ n, h: ph.h })), rest.slice(wi)).map(it => ({ n: it.n, h: it.h }));
  }
  function currentNames(mode, words) {
    const cont = mode === 'config' ? schema : modeSch(mode);
    if (!cont) return null;
    const r = matchPrefixLoose(cont, words);
    if (!r || r.used !== words.length) return null;
    const tree = S.T || S.R;
    const vt = r.sch.toks.find(t => !isW(t));
    if (vt && vt.v === 'ref') {             // interface の下の vrf ? など= 一番上の vrf の名前(記録 modes.log)
      const top = schema.ch.find(c => c.t === 'M' && c.toks[0].w === vt.arg);
      return top ? sortKids(tree.k.filter(n => n.sch === top)).map(n => n.vals[0]) : null;
    }
    const par = nodeAt(tree, S.stack, false) || tree;
    return sortKids((par.k || []).filter(n => n.sch === r.sch)).map(n => n.vals[0]);
  }
  // 打ってある語を Enter の時と同じに読み、曖昧・誤りならその文言(記録: s ? → % Ambiguous command:  "s ")
  function checkTyped(line) {
    const toks = tokenize(line);
    const done = /\s$/.test(line) ? toks : toks.slice(0, -1);
    if (!done.length) return null;
    if (S.mode !== 'cfg') {
      let key = 'exec|';
      for (let i = 0; i < done.length; i++) {
        const list = H[key];
        if (!list) return null;
        const pool = kwNames(list);
        if (!pool.length) return null;
        const pk = pickKw(done[i].s, pool, list);
        if (pk.err === 'ambig') return [dev(DEV.ambig(line))];
        if (pk.err === 'invalid') return [dev(' '.repeat(promptText().length + done[i].st + pk.at) + '^'), dev(DEV.invalid)];
        key += (key.endsWith('|') ? '' : ' ') + (pk.w || pk.unsup);
      }
      return null;
    }
    const first = done[0].s;
    const ml = H[`${curKeyMode()}|`];
    const pool = ml ? kwNames(ml) : CFG_CMDS;
    const ex = pool.find(w => same(w, first));
    const hit = ex ? [ex] : [...new Set(pool.filter(w => pfx(w, first)))];
    if (hit.length === 1 && CFG_CMDS.includes(hit[0]) && hit[0] !== 'no') return null;   // commit・show などは打たずに一覧へ
    // 打ち終えた語だけを読む(打ちかけの最後の語は一覧の側で見る: int Loopback0 ipv + Tab → ipv4  ipv6。記録 ifnames6.log)
    const probe = (/\s$/.test(line) ? line : line.slice(0, toks[toks.length - 1].st)).replace(/\s+$/, '');
    if (!probe) return null;
    const r = execCfgDry(probe);
    if (!r) return null;
    if (r.ambig) return [dev(DEV.ambig(line))];
    if (r.unsup && helpForUnsup(line)) return null;      // 扱わない語でも、実機の一覧があればそれを出す(ipv6 ?・accept-register ?。記録 m14explore.log)
    return r.out;
  }
  function helpForUnsup(line) {
    const r = listAt(line);
    return !!(r && !r.err && !r.dim && r.items && r.items.length);
  }
  function help(line) {
    if (S.ask) return { out: [] };
    const bad = checkTyped(line);
    if (bad) return { out: bad };
    const r = listAt(line);
    const plen = promptText().length;
    if (r.err) {
      const toks = tokenize(line);
      // 誤りの位置を、Enter で打った時と同じに決める
      const res = S.mode === 'cfg' ? execCfgDry(line) : null;
      if (res && res.out) return { out: res.out };
      return { out: [dev(' '.repeat(plen) + '^'), dev(DEV.invalid)] };
    }
    if (r.partial) {
      const ifn = ifNumHelp(line, r);
      if (ifn) return { out: ifn };
      // 語の途中の ?: その字で始まる語(正規の綴りで。lo? → Loopback)＋その形の値の札(cost 5? → <1-65535>。記録 ifnames2/3.log)
      const hit = r.items.filter(it => !KWPH.test(it.n) && pfx(it.n, r.partial)).map(it => it.n)
        .concat(r.items.filter(it => KWPH.test(it.n) && phTakes(it.n, r.partial)).map(it => it.n));
      if (!hit.length) {
        const res = S.mode === 'cfg' ? execCfgDry(line) : execOpDry(line);
        return { out: res || [dev(DEV.invalid)] };
      }
      return { out: tabCols([...new Set(hit)].sort()).map(dev) };
    }
    if (/^\s*\S+$/.test(line) === false && /\s$/.test(line) && tokenize(line).length === 1 && !r.items.length) return { out: [] };
    const out = [];
    if (r.dim) {
      for (const it of r.items) out.push({ c: 'dim', s: `  ${it.n}` });
      out.push(sim(J('薄い行は、実機の ? の一覧をまだ採っていない場所の語です(語と形は骨組みから)。', 'Dim lines are words at a place where the real device\'s ? list has not been captured yet (the words and forms come from the drill\'s schema).')));
      return { out };
    }
    if (r.dyn || !r.raw) return { out: fmtList(r.items).map(dev) };
    for (const it of r.items) for (const l of it.raw) out.push(dev(l));
    return { out };
  }
  // 口の番号の途中の ?(記録 ifnames.log・ifnames3.log)。
  //   型と分けて打った番号(interface Loopback 4?)・続けて打った番号(Loopback40?・Gi0/0/0/?)の 2 つの形。
  //   range の型(Loopback・Null)は番号の一覧の形のまま(  <0-2147483647>  )、inst の型は口の番号を横に並べる(語の途中の ? と同じ形)
  function ifNumHelp(line, r) {
    const toks = tokenize(line);
    const prev = toks.length > 1 ? toks[toks.length - 2].s : '';
    const spaced = ifTypeOf(prev) && !ifParse(prev) ? ifTypeOf(prev) : null;
    const sp = spaced ? null : ifSplit(r.partial);
    const type = spaced || (sp && sp.type);
    if (!type) return null;
    let items = r.items, num = r.partial;
    if (sp) {
      const r2 = listAt(line.slice(0, toks[toks.length - 1].st) + type.full + ' ');
      if (r2.err || !r2.items || r2.dim) return null;
      items = r2.items; num = sp.num;
    }
    if (type.kind === 'range') { const out = []; for (const it of items) for (const l of it.raw || []) out.push(dev(l)); return out.length ? out : null; }
    const hit = items.filter(it => !KWPH.test(it.n) && pfx(it.n, num)).map(it => it.n)
      .concat(items.filter(it => KWPH.test(it.n) && phTakes(it.n, num || '0')).map(it => it.n));
    return hit.length ? tabCols([...new Set(hit)].sort()).map(dev) : null;
  }
  // 「s ?」のような曖昧な語の ? (記録: % Ambiguous command:  "s ")
  function execCfgDry(line) {
    const toks = tokenize(line);
    const save = JSON.stringify({ st: S.stack.map(x => [x.sch.uid, x.vals]) });
    const T0 = S.T;
    S.T = clone(S.T);
    const stack0 = S.stack.slice();
    const r = execCfg(line, toks, true);
    S.T = T0; S.stack = stack0;
    if (r.err === 'ambig') return { ambig: true, out: [dev(DEV.ambig(line))] };
    if (r.err === 'invalid' || r.err === 'unsup') return { out: r.out, unsup: r.err === 'unsup' };
    return null;
  }
  function execOpDry(line) {
    const toks = tokenize(line);
    if (!toks.length) return null;
    const pk = pickKw(toks[0].s, OP, H['exec|']);
    if (pk.err === 'ambig') return [dev(DEV.ambig(line))];
    if (pk.err === 'invalid') return [dev(' '.repeat(promptText().length + toks[0].st + pk.at) + '^'), dev(DEV.invalid)];
    return null;
  }
  // Tab(と空白)。XR は空白では語を補わない(int + 空白 + Lo + Tab → int Loopback 。記録 ifnames6.log)。
  // Tab は打った字の大小をそのまま残して残りを足す(lo → loopback ・LOO → LOOpback ・ROU → ROUte。記録 ifnames.log・ifnames2.log)
  function complete(line, bySpace) {
    if (bySpace || S.ask) return { line: bySpace ? line + ' ' : line };
    const toks = tokenize(line);
    if (!toks.length || /\s$/.test(line)) return { line };
    // 前の語が曖昧なら、その文言(rou ospf 1 ar + Tab → % Ambiguous command:  "rou ospf 1 ar"。記録 ifnames6.log)
    const bad = checkTyped(line);
    if (bad && bad.length === 1 && bad[0].s === DEV.ambig(line)) return { line, out: bad };   // 記録の形= 打った行のまま
    const r = listAt(line);
    if (r.err || !r.partial) return { line };
    const names = (items, p) => [...new Set(items.filter(it => !KWPH.test(it.n) && pfx(it.n, p)).map(it => it.n))].sort();
    const head = line.slice(0, toks[toks.length - 1].st);
    let hit = names(r.items, r.partial), partial = r.partial, typed = '';
    if (!hit.length) {          // 続けて打った型と番号(Gi0/0 → Gi0/0/0/・Gi0/0/0/3 → Gi0/0/0/3 。記録 ifnames3.log・ifnames5.log)
      const sp = ifSplit(r.partial);
      if (sp) {
        const r2 = listAt(head + sp.type.full + ' ');
        if (!r2.err && r2.items && !r2.dim) { hit = names(r2.items, sp.num); partial = sp.num; typed = sp.typed; }
      }
    }
    if (hit.length === 1) return { line: head + typed + partial + hit[0].slice(partial.length) + ' ' };
    if (hit.length > 1) {
      let n = hit[0].length;
      for (const w of hit) { let k = 0; while (k < n && k < w.length && lc(w[k]) === lc(hit[0][k])) k++; n = k; }
      if (n > partial.length) return { line: head + typed + partial + hit[0].slice(partial.length, n) };
      return { line, out: tabCols(hit).map(dev) };
    }
    return { line };
  }

  /* ---- 打つ ---- */
  function exec(line) {
    S.log.push({ mode: curMode(), line });
    if (S.ask) return execAsk(line);
    const toks = tokenize(line);
    if (!toks.length) return { out: [] };
    if (toks[0].s.startsWith('!') || toks[0].s.startsWith('#')) return { out: [] };
    return S.mode === 'cfg' ? execCfgTop(line, toks) : execOp(line, toks, false);
  }
  function execCfgTop(line, toks) {
    const r = execCfg(line, toks, false);
    return r;
  }
  function prompt() { return { text: promptText(), mode: S.mode }; }

  /* ---- お題の確かめ用: 稼働中の設定を 1 行 1 文の形に(道を全部つないだ形) ---- */
  function flatLines(tree) {
    const out = [];
    const walk = (n, pre) => {
      for (const c of sortKids(n.k || [])) {
        if (!c.sch || c.sch.t === 'O' || c.opaque) { out.push(pre.concat([c.raw[0].trim()]).join(' ')); continue; }
        const l = lineOf(c.sch, c.vals);
        if (c.sch.t === 'M') { out.push(pre.concat([l]).join(' ')); walk(c, pre.concat([l])); }
        else out.push(pre.concat([l]).join(' '));
      }
    };
    walk(tree, []);
    return out;
  }

  for (const c of opt.setupCommits || []) {     // お題の前置き(盤面の上で済ませたコミット)
    S.T = clone(S.R);
    S.mode = 'cfg'; S.stack = [];
    for (const ln of c.lines.split('\n')) if (ln.trim()) { const r = execCfg(ln, tokenize(ln), true); if (r.err) candErr.push(`${ln}: ${r.err}`); }
    doCommit({ label: c.label || null, comment: c.comment || null }, true);
    S.mode = 'exec'; S.T = null;
  }
  return {
    S, schema, baseErr, candErr, prompt, exec, help, complete, lang,
    runningLines: () => flatLines(S.R), targetLines: () => S.T ? flatLines(S.T) : null,
    history: () => S.hist, changed,
    set onAsync(f) { S.onAsync = f; },
  };
}

/* ---------------- お題の確かめ ---------------- */
function matchLines(lines, pat, bind) {
  const P = pat.split(/\s+/);
  const hits = [];
  for (const l of lines) {
    const W = l.split(/\s+/);
    const b = Object.assign({}, bind);
    if (unify(P, 0, W, 0, b)) hits.push({ line: l, bind: b });
  }
  return hits;
}
function unify(P, i, W, j, b) {
  if (i === P.length) return j === W.length;
  const p = P[i];
  if (p === '**') { for (let k = j; k <= W.length; k++) if (unify(P, i + 1, W, k, b)) return true; return false; }
  if (j >= W.length) return false;
  if (p === '*') return unify(P, i + 1, W, j + 1, b);
  if (p.startsWith('$')) {
    if (b[p] != null) return b[p] === W[j] && unify(P, i + 1, W, j + 1, b);
    b[p] = W[j];
    if (unify(P, i + 1, W, j + 1, b)) return true;
    delete b[p];
    return false;
  }
  return p === W[j] && unify(P, i + 1, W, j + 1, b);
}
function checkDrill(sim_, d) {
  const lang = langOf(sim_.lang);
  const J = (ja, en) => lang === 'en' ? en : ja;
  const T = v => v == null || typeof v === 'string' ? v : (v[lang] || v.ja || v.en);   // お題の文言(言語ごとの {ja, en} か 1 つの文字列)
  const lines = sim_.runningLines();
  const items = [];
  let bind = {};
  for (const w of d.want || []) {
    const alts = Array.isArray(w) ? w : [w];
    let ok = false;
    for (const a of alts) { const h = matchLines(lines, a, bind); if (h.length) { bind = h[0].bind; ok = true; break; } }
    items.push({ ok, s: ok ? J('求める設定が commit 済みの設定にある', 'The required configuration is in the committed configuration') : J('求める設定のうち、commit 済みの設定に無いものがある', 'Part of the required configuration is missing from the committed configuration') });
  }
  for (const f of d.forbid || []) {
    const h = matchLines(lines, f, bind);
    items.push({ ok: !h.length, s: h.length ? J('commit 済みの設定に、あってはならない設定がある', 'The committed configuration contains something that must not be there') : J('あってはならない設定は無い', 'Nothing that must not be there is in the committed configuration') });
  }
  for (const c of d.commits || []) {
    const hs = sim_.history().filter(x => (!c.label || x.label === c.label) && (!c.client || x.client === c.client) &&
      (!c.comment || x.comment.includes(c.comment)) && (!c.after || Number(x.id) > Number((sim_.history().find(y => y.label === c.after) || { id: 0 }).id)));
    items.push({ ok: hs.length > 0, s: hs.length ? J('コミットの履歴に求める記録がある', 'The commit history has the required entry') : J('コミットの履歴に求める記録が無い(ラベル・コメント・種類を確かめる)', 'The commit history lacks the required entry (check the label, the comment and the type)') });
  }
  for (const c of d.cmd || []) {
    const re = new RegExp(c.line);
    const ok = sim_.S.log.some(x => re.test(x.line) && (!c.mode || new RegExp(c.mode).test(x.mode)));
    items.push({ ok, s: ok ? (T(c.say) || J('お題の求める手順で打っている', 'You used the steps the task asks for')) : (T(c.sayNg) || T(c.say) || J('お題の求める手順のコマンドを打った記録が無い', 'There is no record of the command the task asks for')) });
  }
  if (d.trialDone) {
    const ok = !sim_.S.trial;
    items.push({ ok, s: ok ? J('確認待ちのコミットは残っていない', 'No confirmed commit is left pending') : J('確認待ちのコミットが残っている(期限が来ると戻る)', 'A confirmed commit is still pending (it rolls back when it expires)') });
  }
  if (d.exec) {
    const ok = sim_.S.mode === 'exec';
    items.push({ ok, s: ok ? J('設定モードを抜けている', 'You have left configuration mode') : J('まだ設定モードの中にいる', 'You are still in configuration mode') });
  }
  return { ok: items.every(x => x.ok), items };
}

root.XrSim = { create, checkDrill, tokenize, t7enc };
})(typeof window !== 'undefined' ? window : globalThis);
