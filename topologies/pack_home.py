#!/usr/bin/env python3
"""パック一覧ページ(pack_server の `/`)— 2026-09-27 ユーザ指示。

素の Directory listing の代わりに、パックを日付ごとに並べて
「解答の進み具合」と「採点済みかどうか」を一目で分かるようにする。

採点状態の判定(どれもパックを作り直さずに既存の成果物から読む):
  - 紙面: `report.html` がある = `pack.sh grade`(--no-lab 含む)を実行済み。
          点数は records/attempts.jsonl の `src=pack:<ID>` の**初回**記録から数える
          (ノルマ集計と同じ dedupe。report.html だけあって記録が無い古いパックは点数なし)。
  - ラボ: manifest の `lab_score`(grade が書く)か、attempts.jsonl の lab 記録。
          `error:` 付きの問(dry-run・構築失敗)は採点対象から外す。
  - 解答: 解答.md の `状態: [x]` か、`解答:` 欄の記入。

単体で `python3 pack_home.py --out /tmp/x.html` とすればページを書き出して確認できる。
"""

import argparse
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_pack                                        # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLOT_LABEL = {"think": "思考", "speed": "瞬発", "cloze": "穴埋め"}


def load_attempts(repo):
    """(by_pack, by_ref)。by_pack = {pack_id: {(kind, ref): 初回の記録}}(再挑戦は数えない)、
    by_ref = {ref: [ラボの記録…]}(パック外で `lab.sh grade` した分の拾い上げ用)。
    PVT の記録は private/attempts.jsonl にある(quota.py の台帳分離)ので両方読む。"""
    by_pack, by_ref, rows = {}, {}, []
    for rel in ("records/attempts.jsonl", "private/attempts.jsonl"):
        try:
            with open(os.path.join(repo, rel), encoding="utf-8") as fh:
                for line in fh:
                    try:
                        rows.append(json.loads(line))
                    except ValueError:
                        continue
        except OSError:
            continue
    rows.sort(key=lambda r: r.get("ts") or "")
    for r in rows:
        src = r.get("src") or ""
        if src.startswith("pack:"):
            per = by_pack.setdefault(src[5:], {})
            per.setdefault((r.get("kind"), r.get("ref")), r)
        if r.get("kind") == "lab":
            by_ref.setdefault(r.get("ref"), []).append(r)
    return by_pack, by_ref


def pack_summary(pdir, attempts):
    pid = os.path.basename(pdir)
    man = gen_pack.read_manifest(pdir)
    try:
        sheet = gen_pack.parse_answer_sheet(os.path.join(pdir, "解答.md"))
    except OSError:
        sheet = {}
    by_pack, by_ref = attempts
    rec = by_pack.get(pid, {})
    papers = [i for i in man["items"] if i.get("kind") == "paper"]
    labs = [i for i in man["items"] if i.get("kind") != "paper"]
    live_labs = [i for i in labs if not i.get("error")]
    created = man.get("created") or ""
    has_report = os.path.exists(os.path.join(pdir, "report.html"))

    p_answered = sum(1 for i in papers
                     if sheet.get(i["no"], {}).get("done")
                     or sheet.get(i["no"], {}).get("answer"))
    answered = sum(1 for i in man["items"]
                   if sheet.get(i["no"], {}).get("done")
                   or sheet.get(i["no"], {}).get("answer"))

    # 紙面
    p_ok = p_n = 0
    for i in papers:
        r = rec.get(("paper", i.get("ref")))
        if r:
            p_n += 1
            p_ok += 1 if r.get("result") == "ok" else 0
    paper_graded = bool(papers) and (has_report or p_n > 0)

    # ラボ
    lab_res = []                    # [(ref, "got/total" | None)]
    for i in live_labs:
        sc = i.get("lab_score")
        if not sc:
            r = rec.get(("lab", i.get("ref")))
            if not r:
                # パック外(lab.sh grade・手動記録)で採点した分: パック作成日以降の初回
                r = next((x for x in by_ref.get(i.get("ref"), [])
                          if (x.get("day") or "") >= created), None)
            if r and r.get("score") is not None:
                sc = f"{r['score']}/{r.get('total', 100)}"
        lab_res.append((i.get("ref"), i.get("genre", ""), sc))
    labs_done = sum(1 for _r, _g, sc in lab_res if sc)

    need_paper = bool(papers)
    need_lab = bool(live_labs)
    fully = ((not need_paper or paper_graded) and (not need_lab or labs_done == len(live_labs))
             and (need_paper or need_lab))
    partly = paper_graded or labs_done > 0
    if fully:
        state = "graded"
    elif partly:
        state = "partial"
    elif answered:
        state = "doing"
    else:
        state = "todo"

    slots = {}
    for i in papers:
        s = SLOT_LABEL.get(i.get("slot"), "思考")
        slots[s] = slots.get(s, 0) + 1
    m = re.match(r"PACK-(\d{4})(\d{2})(\d{2})", pid)
    date = man.get("created") or (f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else "")
    return {
        "id": pid, "date": date, "dry": man.get("dry_run") == "true",
        "papers": len(papers), "slots": slots, "labs": len(labs),
        "live_labs": len(live_labs), "items": len(man["items"]),
        "answered": answered, "p_answered": p_answered, "has_report": has_report,
        "paper_graded": paper_graded, "p_ok": p_ok, "p_n": p_n,
        "lab_res": lab_res, "labs_done": labs_done, "state": state,
    }


STATE_MARK = {"graded": "✓", "partial": "◐", "doing": "○", "todo": "○"}


def _esc(s):
    return html.escape(str(s), quote=True)


def _row(p, first=False):
    pid = _esc(p["id"])
    st = p["state"]
    name = f'<a href="{pid}/index.html">{pid}</a>'

    paper = ""
    if p["papers"]:
        if p["paper_graded"] and p["p_n"]:
            v = f'<a href="{pid}/report.html">{p["p_ok"]}/{p["p_n"]}</a>'
        elif p["paper_graded"]:
            v = f'<a href="{pid}/report.html">✓</a>'
        else:
            v = f'<span class="dim">{p["p_answered"]}/{p["papers"]}</span>'
        paper = f'<span class="k">Paper</span>{v}'

    lab = ""
    if p["labs"]:
        vs = []
        for ref, _g, sc in p["lab_res"]:
            if sc:
                got, _, tot = sc.partition("/")
                vs.append(f'<span class="{"" if got == tot else "ng"}" title="{_esc(ref)}">{_esc(got)}</span>')
            else:
                vs.append(f'<span class="dim" title="{_esc(ref)}">…</span>')
        lab = f'<span class="k">Lab</span>' + (" ".join(vs) or '<span class="dim">—</span>')

    return (f'<tr class="st-{st}{" first" if first else ""}" data-d="{_esc(p["date"])}">'
            f'<td class="m m-{st}">{STATE_MARK[st]}</td><td class="n">{name}</td>'
            f'<td class="p">{paper}</td><td class="l">{lab}</td></tr>')


CSS = """
:root{ color-scheme: light; }
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:@@PAPER@@;color:#111}
body{font-family:"Segoe UI","Yu Gothic UI",Meiryo,"Hiragino Kaku Gothic ProN",system-ui,sans-serif;
     font-size:15px;line-height:1.5}
a{color:#0645ad;text-decoration:none} a:hover{text-decoration:underline}
main{max-width:640px;margin:0 auto;padding:1.2rem 1rem 4rem}
header{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:.8rem}
h1{font-size:1.2rem;font-weight:600;margin:0}
label{font-size:.85rem;color:#666;cursor:pointer}
table{border-collapse:collapse;width:100%}
td{padding:.3rem .5rem;vertical-align:middle;font-variant-numeric:tabular-nums}
tr.first td{border-top:1px solid #e3e3e3}
td.m{width:1.5rem;text-align:center}
td.n{font-family:Consolas,"DejaVu Sans Mono",monospace;font-size:.88rem;white-space:nowrap}
.m-graded{color:#2e7d32}
.m-partial{color:#b07a00}
.m-doing,.m-todo{color:#bbb}
td.p{width:7.5rem;white-space:nowrap}
.k{color:#999;font-size:.78rem;margin-right:.4rem}
td.l span{display:inline-block;min-width:2.1em}
.ng{color:#c62828}
.dim{color:#aaa}
body.hide tr.st-graded{display:none}
details{margin-top:2rem;font-size:.85rem;color:#666}
summary{cursor:pointer}
.foot{margin-top:1.5rem;font-size:.8rem}
.foot a{color:#999}
"""

JS = """
(function(){
  var cb=document.getElementById('hide');
  function apply(){ document.body.classList.toggle('hide', cb.checked);
    document.querySelectorAll('main > table').forEach(function(t){
      var last=null;
      t.querySelectorAll('tr').forEach(function(r){
        var vis=!(cb.checked && r.classList.contains('st-graded'));
        var first=vis && r.dataset.d!==last;
        r.classList.toggle('first', first);
        if(vis) last=r.dataset.d;
      });
    });
    try{ localStorage.setItem('packhome.hide', cb.checked?'1':'0'); }catch(e){} }
  try{ cb.checked = localStorage.getItem('packhome.hide')==='1'; }catch(e){}
  cb.addEventListener('change', apply); apply();
})();
"""


def _rows(ps):
    """日が変わる行に区切り線(「採点済を隠す」時は JS が見えている先頭行へ付け直す)。"""
    out, last = [], None
    for p in ps:
        out.append(_row(p, p["date"] != last))
        last = p["date"]
    return out


def build_home(packs_root, repo=REPO):
    attempts = load_attempts(repo)
    packs, broken = [], []
    for name in sorted(os.listdir(packs_root)):
        full = os.path.join(packs_root, name)
        if name.startswith("PACK-") and os.path.isdir(full):
            try:
                packs.append(pack_summary(full, attempts))
            except Exception as e:           # 1 パックの破損で一覧全体を落とさない
                broken.append((name, str(e)))

    # dry-run(ラボ未構築の試し作り)とテスト用は本流から外して下の折りたたみへ
    drys = sorted((p for p in packs if p["dry"]), key=lambda p: p["id"], reverse=True)
    tests = sorted((p for p in packs if not p["dry"] and p["id"].startswith("PACK-TEST")),
                   key=lambda p: p["id"])
    daily = sorted((p for p in packs if not p["dry"] and not p["id"].startswith("PACK-TEST")),
                   key=lambda p: (p["date"], p["id"]), reverse=True)

    css = CSS.replace("@@PAPER@@", gen_pack.render_html.PAPER)      # 紙の色は問題ページと同じ値
    out = [f"<title>Question Packs</title><style>{css}</style>",
           '<main><header><h1>Question Packs</h1>'
           '<label><input type="checkbox" id="hide"> Hide graded</label></header>',
           "<table>"] + _rows(daily) + ["</table>"]
    for label, ps in (("dry-run", drys), ("Tests", tests)):
        if ps:
            out += [f"<details><summary>{label} ({len(ps)})</summary><table>"]
            out += [_row(p) for p in ps] + ["</table></details>"]
    if broken:
        out += ["<details open><summary>Unreadable packs</summary><ul>"]
        out += [f"<li>{_esc(n)}: {_esc(e)}</li>" for n, e in broken] + ["</ul></details>"]
    out.append('<p class="foot"><a href="/?raw=1">File list</a></p>')
    out.append(f"</main><script>{JS}</script>")
    return ("<!doctype html><html lang=\"ja\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            + out[0] + "</head><body>" + "".join(out[1:]) + "</body></html>")


def main():
    ap = argparse.ArgumentParser(description="パック一覧ページを書き出す(確認用)")
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    page = build_home(os.path.join(a.repo, "packs"), a.repo)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(page)
    print(a.out)


if __name__ == "__main__":
    main()
