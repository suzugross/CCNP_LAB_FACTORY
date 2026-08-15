#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""1日の学習ノルマ(紙面10問・ラボ3問/3ジャンル)の記録と集計。BL-114。

  記録:  quota.py log paper 20260812-024 ok
         quota.py log lab   GEN-DMVPN-48222 --score 100 --total 100
  進捗:  quota.py today [--brief] [--date 2026-08-12]
  採点:  quota.py grade-lab GEN-DMVPN-48222 [--variant base]   ← 実走＋自動記録
  集計:  quota.py report [--days 30] [--out /path/report.html]
  取込:  quota.py backfill [--apply]        ← _history.md から過去分を取り込む

設計方針:
  - **正準は追記専用の JSONL**(records/attempts.jsonl)。_history.md は人間向けの
    叙述で書き換えも起きるため、ノルマ計数の土台には使わない(取り込みは backfill のみ)。
  - 記録は**採点が確定した瞬間**に打つ。日付は「そのとき」の JST であって、
    パックの作成日ではない(夜に作って翌朝解く運用で前日に計上されるのを防ぐ)。
  - 1日の境界は JST 04:00(records/quota.yml)。深夜に解いた分は前日のノルマ。
  - ★PVT系(ref が PVT- で始まる)の記録は private/attempts.jsonl に分離する
    (CLAUDE.md の台帳分離。公開リポに PVT の ID を出さない)。
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

import yaml

JST = datetime.timezone(datetime.timedelta(hours=9), "JST")
SCORE_RE = re.compile(r"合計:\s*(\d+)\s*/\s*(\d+)\s*点")
BAR_W = 10


# ==========================================================================
# 設定・パス
# ==========================================================================
def repo_root(repo=None):
    return os.path.abspath(repo or os.path.join(os.path.dirname(__file__), ".."))


def load_yaml(path, default=None):
    if not os.path.exists(path):
        return default if default is not None else {}
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or (default if default is not None else {})


def config(repo):
    c = load_yaml(os.path.join(repo, "records", "quota.yml"))
    c.setdefault("day_start", "04:00")
    c.setdefault("paper_per_day", 10)
    c.setdefault("lab_per_day", 3)
    c.setdefault("lab_min_genres", 3)
    c.setdefault("lab_require_full_score", True)
    c.setdefault("genre_order",
                 ["igp", "bgp", "vpn", "services", "security", "l2", "automation"])
    return c


def store_paths(repo, ref=""):
    """(書き込み先, 全読み込み先) — PVT は private/ 側に分ける。"""
    pub = os.path.join(repo, "records", "attempts.jsonl")
    pvt = os.path.join(repo, "private", "attempts.jsonl")
    write = pvt if str(ref).startswith("PVT-") else pub
    return write, [pub, pvt]


# ==========================================================================
# 日付(JST・04:00 境界)
# ==========================================================================
def now_jst():
    return datetime.datetime.now(JST)


def quota_day(ts, day_start="04:00"):
    """時刻 → その時刻が属するノルマ日(YYYY-MM-DD)。"""
    h, m = (int(x) for x in str(day_start).split(":"))
    shifted = ts - datetime.timedelta(hours=h, minutes=m)
    return shifted.date().isoformat()


def day_range(day, day_start="04:00"):
    """ノルマ日 → (開始 datetime, 終了 datetime)。表示用。"""
    h, m = (int(x) for x in str(day_start).split(":"))
    d = datetime.date.fromisoformat(day)
    start = datetime.datetime.combine(d, datetime.time(h, m), tzinfo=JST)
    return start, start + datetime.timedelta(days=1)


# ==========================================================================
# ジャンル判定
# ==========================================================================
def genre_tables(repo):
    g = load_yaml(os.path.join(repo, "records", "genres.yml"))
    # ★PVT系の接頭辞・上書きは公開ファイルに書かない(private 側を後勝ちで合流)
    pvt = load_yaml(os.path.join(repo, "private", "genres.yml"))
    for key in ("tags", "shapes", "families", "overrides"):
        if pvt.get(key):
            merged = dict(g.get(key) or {})
            for k, v in pvt[key].items():
                merged[k] = (list(merged.get(k) or []) + list(v)
                             if isinstance(v, list) else v)
            g[key] = merged
    tag2genre = {}
    for genre, tags in (g.get("tags") or {}).items():
        for t in tags or []:
            tag2genre[str(t).strip().lower()] = genre
    shape2genre = {}
    for genre, shapes in (g.get("shapes") or {}).items():
        for s in shapes or []:
            shape2genre[str(s).strip().lower()] = genre
    fam = []
    for genre, prefixes in (g.get("families") or {}).items():
        for p in prefixes or []:
            fam.append((str(p), genre))
    fam.sort(key=lambda x: -len(x[0]))          # 最長一致を先に見る
    return {
        "tag": tag2genre,
        "shape": shape2genre,
        "family": fam,
        "ignore": {str(t).lower() for t in (g.get("ignore_tags") or [])},
        "overrides": {str(k): str(v) for k, v in (g.get("overrides") or {}).items()},
    }


def vote(tags, tbl, order):
    """タグ列 → 大ジャンル(多数決・同数は genre_order の順)。"""
    score = {}
    for t in tags:
        t = str(t).strip().lower()
        if not t or t in tbl["ignore"]:
            continue
        genre = tbl["tag"].get(t)
        if genre:
            score[genre] = score.get(genre, 0) + 1
    if not score:
        return None
    best = max(score.values())
    for genre in order:
        if score.get(genre) == best:
            return genre
    return sorted(score)[0]


def catalog_tags(repo, prob_id):
    """CATALOG.md(公開/private)の「分野」列から ID のタグを引く。

    完全一致が無ければ GEN 系の族接頭辞(GEN-DMVPN-)で引く(新 seed 対応)。
    """
    exact, family = None, None
    fam = None
    m = re.match(r"^(GEN-[A-Z0-9]+)-", str(prob_id))
    if m:
        fam = m.group(1) + "-"
    for rel in ("problems/CATALOG.md", "private/CATALOG.md"):
        path = os.path.join(repo, rel)
        if not os.path.exists(path):
            continue
        col = None
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if not line.startswith("|"):
                    continue
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if "分野" in cells:
                    col = cells.index("分野")
                    continue
                if col is None or col >= len(cells) or not cells[0]:
                    continue
                if cells[0] == prob_id:
                    exact = cells[col]
                elif fam and family is None and cells[0].startswith(fam):
                    family = cells[col]
    src = exact or family
    return [t.strip() for t in src.split(",")] if src else []


def paper_shape(repo, ref):
    """answers/<ID>.md の「種別: `shape/kind`」行から shape を取る。"""
    for rel in (f"answers/{ref}.md", f"private/answers/{ref}.md"):
        path = os.path.join(repo, rel)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            m = re.search(r"^-?\s*種別:\s*`([^`]+)`", fh.read(), re.M)
        if m:
            return m.group(1).split("/")[0].strip().lower()
    return None


def genre_for(repo, kind, ref):
    """問題 → 大ジャンル。判定できなければ 'other'。"""
    tbl = genre_tables(repo)
    order = config(repo)["genre_order"]
    if ref in tbl["overrides"]:
        return tbl["overrides"][ref]
    if kind == "paper":
        shape = paper_shape(repo, ref)
        if shape:
            return tbl["shape"].get(shape) or vote([shape], tbl, order) or "other"
        return "other"
    # ラボ: problem.yml の topics を最優先(新 seed の GEN でも当たる)
    for rel in (f"problems/{ref}/problem.yml",
                f"topologies/_generated/{ref}/problem.yml"):
        p = load_yaml(os.path.join(repo, rel))
        if p.get("topics"):
            g = vote(p["topics"], tbl, order)
            if g:
                return g
    g = vote(catalog_tags(repo, ref), tbl, order)
    if g:
        return g
    for prefix, genre in tbl["family"]:            # 撤収済みで実体が無い過去分
        if str(ref).startswith(prefix):
            return genre
    return "other"


# ==========================================================================
# 記録(追記)・読み出し
# ==========================================================================
def log_attempt(repo, kind, ref, *, result=None, score=None, total=None,
                genre=None, src="manual", memo="", ts=None, quiet=False):
    repo = repo_root(repo)
    cfg = config(repo)
    ts = ts or now_jst()
    if genre in (None, "", "auto"):
        genre = genre_for(repo, kind, ref)
    if result is None:
        if score is not None and total:
            result = "ok" if int(score) >= int(total) else "partial"
        else:
            result = "ok"
    rec = {"ts": ts.isoformat(timespec="seconds"),
           "day": quota_day(ts, cfg["day_start"]),
           "kind": kind, "ref": ref, "genre": genre, "result": result,
           "score": score, "total": total, "src": src, "memo": memo}
    path, _ = store_paths(repo, ref)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    if not quiet:
        got = f" {score}/{total}点" if score is not None else ""
        print(f"[ノルマ] 記録: {rec['day']} {kind} {ref} ({genre}) {result}{got}")
    return rec


def read_events(repo):
    repo = repo_root(repo)
    _, paths = store_paths(repo)
    evs = []
    for path in paths:
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    evs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    evs.sort(key=lambda e: e.get("ts", ""))
    return evs


def dedupe(events):
    """同じ日・同じ問題の複数回採点は1件に畳む(最後の結果を採る)。

    ラボは broken→fix で何度も grade を回すため、これが無いと水増しになる。
    """
    out = {}
    for e in events:
        out[(e.get("day"), e.get("kind"), e.get("ref"))] = e
    return list(out.values())


# ==========================================================================
# 集計
# ==========================================================================
def summarize(repo, day, events=None):
    repo = repo_root(repo)
    cfg = config(repo)
    evs = dedupe([e for e in (events or read_events(repo)) if e.get("day") == day])
    papers = [e for e in evs if e.get("kind") == "paper"]
    labs = [e for e in evs if e.get("kind") == "lab"]

    def full(e):
        if not cfg["lab_require_full_score"]:
            return e.get("result") != "ng"
        if e.get("score") is not None and e.get("total"):
            return int(e["score"]) >= int(e["total"])
        return e.get("result") == "ok"

    done = [e for e in labs if full(e)]
    wip = [e for e in labs if not full(e)]
    genres = []
    for e in done:
        if e.get("genre") not in genres:
            genres.append(e.get("genre"))
    ok = len([e for e in papers if e.get("result") == "ok"])
    need_g = max(0, cfg["lab_min_genres"] - len(genres))
    return {
        "day": day, "cfg": cfg,
        "paper_n": len(papers), "paper_ok": ok,
        "paper_need": max(0, cfg["paper_per_day"] - len(papers)),
        "lab_n": len(done), "lab_need": max(0, cfg["lab_per_day"] - len(done)),
        "lab_genres": genres, "lab_genre_need": need_g,
        "lab_wip": wip, "papers": papers, "labs": done,
        "rest_genres": [g for g in cfg["genre_order"] if g not in genres],
        "met": (len(papers) >= cfg["paper_per_day"]
                and len(done) >= cfg["lab_per_day"] and need_g == 0),
    }


def streak(repo, day, events=None):
    """day を末尾とする連続達成日数(day 自身が未達なら前日までを数える)。"""
    evs = events if events is not None else read_events(repo)
    n, cur = 0, datetime.date.fromisoformat(day)
    if not summarize(repo, day, evs)["met"]:
        cur -= datetime.timedelta(days=1)
    while summarize(repo, cur.isoformat(), evs)["met"]:
        n += 1
        cur -= datetime.timedelta(days=1)
    return n


def bar(n, need):
    filled = BAR_W if n >= need else int(BAR_W * n / need) if need else BAR_W
    return "█" * filled + "░" * (BAR_W - filled)


def render_today(s, brief=False):
    cfg = s["cfg"]
    if brief:
        head = "達成" if s["met"] else (
            f"残り 紙面{s['paper_need']}・ラボ{s['lab_need']}"
            + (f"(要 {s['lab_genre_need']}ジャンル)" if s["lab_genre_need"] else ""))
        return (f"[ノルマ {s['day'][5:]}] 紙面 {s['paper_n']}/{cfg['paper_per_day']}"
                f"・ラボ {s['lab_n']}/{cfg['lab_per_day']}"
                f"(ジャンル {len(s['lab_genres'])}/{cfg['lab_min_genres']}) — {head}")
    L = [f"== 学習ノルマ {s['day']} (JST・{cfg['day_start']} 切替) =="]
    acc = (f"  正答 {s['paper_ok']}/{s['paper_n']}" if s["paper_n"] else "")
    L.append(f"  紙面  {bar(s['paper_n'], cfg['paper_per_day'])} "
             f"{s['paper_n']}/{cfg['paper_per_day']} 問{acc}")
    gl = "・".join(s["lab_genres"]) or "-"
    L.append(f"  ラボ  {bar(s['lab_n'], cfg['lab_per_day'])} "
             f"{s['lab_n']}/{cfg['lab_per_day']} 問   "
             f"ジャンル {len(s['lab_genres'])}/{cfg['lab_min_genres']} [{gl}]")
    for e in s["lab_wip"]:
        got = f"{e.get('score')}/{e.get('total')}点" if e.get("score") is not None else "-"
        L.append(f"        ↳ 挑戦中: {e['ref']} ({e.get('genre')}) {got}")
    if s["met"]:
        L.append(f"  ★達成。連続 {streak(None, s['day'])} 日目。")
    else:
        rest = []
        if s["paper_need"]:
            rest.append(f"紙面 あと{s['paper_need']}問")
        if s["lab_need"]:
            rest.append(f"ラボ あと{s['lab_need']}問")
        if s["lab_genre_need"]:
            rest.append(f"未消化ジャンル {'・'.join(s['rest_genres'][:4])} から"
                        f"{s['lab_genre_need']}つ")
        L.append("  残り: " + " / ".join(rest))
    return "\n".join(L)


# ==========================================================================
# サブコマンド
# ==========================================================================
def cmd_log(a):
    repo = repo_root(a.repo)
    log_attempt(repo, a.kind, a.ref, result=a.result, score=a.score,
                total=a.total, genre=a.genre, src=a.src, memo=a.memo or "")
    if not a.no_progress:
        print(render_today(summarize(repo, quota_day(now_jst(),
                                                     config(repo)["day_start"]))))


def cmd_today(a):
    repo = repo_root(a.repo)
    day = a.date or quota_day(now_jst(), config(repo)["day_start"])
    print(render_today(summarize(repo, day), brief=a.brief))


def cmd_grade_lab(a):
    """grade.yml を実走(出力はそのまま流す)→ 得点を記録する。"""
    repo = repo_root(a.repo)
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
        fh.write("CCNP\n")                     # vault パスワード(プロジェクト規約)
        vault = fh.name
    cmd = [os.path.join(repo, ".venv/bin/ansible-playbook"),
           os.path.join(repo, "playbooks/grade.yml"),
           "-e", f"problem={a.ref}", "--vault-password-file", vault]
    if a.variant:
        cmd += ["-e", f"variant={a.variant}"]
    buf = []
    try:
        p = subprocess.Popen(cmd, cwd=repo, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in p.stdout:                   # 素の実行と同じように流しながら控える
            sys.stdout.write(line)
            buf.append(line)
        p.wait()
    finally:
        os.unlink(vault)
    out = "".join(buf)
    hits = SCORE_RE.findall(out)
    if not hits:
        print("[ノルマ] 得点行を読めなかったため記録しません", file=sys.stderr)
        return 1
    got, total = int(hits[-1][0]), int(hits[-1][1])
    log_attempt(repo, "lab", a.ref, score=got, total=total, src="lab.sh",
                memo=a.variant or "")
    print(render_today(summarize(repo, quota_day(now_jst(),
                                                 config(repo)["day_start"]))))
    return 0


def cmd_report(a):
    repo = repo_root(a.repo)
    cfg = config(repo)
    evs = read_events(repo)
    today = a.date or quota_day(now_jst(), cfg["day_start"])
    end = datetime.date.fromisoformat(today)
    days = [(end - datetime.timedelta(days=i)).isoformat()
            for i in range(a.days - 1, -1, -1)]
    rows, met_n, p_tot, p_ok, l_tot = [], 0, 0, 0, 0
    for d in days:
        s = summarize(repo, d, evs)
        if not (s["paper_n"] or s["lab_n"] or s["lab_wip"]):
            continue
        met_n += 1 if s["met"] else 0
        p_tot += s["paper_n"]
        p_ok += s["paper_ok"]
        l_tot += s["lab_n"]
        rows.append((d, s))
    md = [f"# 学習ノルマ 集計 — {days[0]} 〜 {days[-1]}", "",
          f"- ノルマ: 紙面 {cfg['paper_per_day']}問 / ラボ {cfg['lab_per_day']}問"
          f"({cfg['lab_min_genres']}ジャンル以上) ・ 1日の境界 = JST {cfg['day_start']}",
          f"- 達成 **{met_n}** 日 / 記録のある {len(rows)} 日 ・ 連続 "
          f"**{streak(repo, today, evs)}** 日",
          f"- 紙面 計 {p_tot} 問(正答 {p_ok}・"
          f"{(100 * p_ok // p_tot) if p_tot else 0}%) ・ ラボ 計 {l_tot} 問", "",
          "| 日付 | 達成 | 紙面 | 正答 | ラボ | ジャンル |",
          "|------|------|------|------|------|----------|"]
    for d, s in reversed(rows):
        md.append(f"| {d} | {'★' if s['met'] else '—'} | "
                  f"{s['paper_n']}/{cfg['paper_per_day']} | "
                  f"{s['paper_ok']}/{s['paper_n'] or '-'} | "
                  f"{s['lab_n']}/{cfg['lab_per_day']} | "
                  f"{'・'.join(s['lab_genres']) or '-'} |")
    md += ["", "## ジャンル別のラボ消化数", "",
           "| ジャンル | 問数 |", "|----------|------|"]
    tally = {}
    for _, s in rows:
        for e in s["labs"]:
            tally[e.get("genre")] = tally.get(e.get("genre"), 0) + 1
    for g in cfg["genre_order"] + sorted(set(tally) - set(cfg["genre_order"])):
        md.append(f"| {g} | {tally.get(g, 0)} |")
    text = "\n".join(md)
    if a.out:
        sys.path.insert(0, os.path.join(repo, "topologies"))
        import render_html
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(render_html.render(text, title="学習ノルマ 集計",
                                        mermaid_mode="none"))
        print(f"書き出し: {a.out}")
    else:
        print(text)


HIST_ROW = re.compile(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*([^|]+?)\s*\|"
                      r"\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|")


def cmd_backfill(a):
    """_history.md の「採点済/撤収済」行を JSONL に取り込む(過去分の初期化)。

    ★日付は履歴の出題日をそのまま使う(当時の実際の解答時刻は分からない)。
    既に JSONL にある (day, kind, ref) は飛ばすので、何度流しても増えない。
    """
    repo = repo_root(a.repo)
    have = {(e.get("day"), e.get("kind"), e.get("ref")) for e in read_events(repo)}
    add = []
    for rel in ("problems/_history.md", "private/_history.md"):
        path = os.path.join(repo, rel)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                m = HIST_ROW.match(line)
                if not m:
                    continue
                day, label, _diff, state, score = (m.group(i) for i in range(1, 6))
                if state not in ("採点済", "撤収済"):
                    continue
                paper = label.startswith("紙面")
                ref = label.replace("紙面", "").strip().split(" ")[0].split("(")[0]
                if not ref or ref in ("問題ID",):
                    continue
                kind = "paper" if paper else "lab"
                if (day, kind, ref) in have:
                    continue
                if kind == "paper":
                    result = "ok" if "正解" in score and "不正解" not in score else (
                        "ng" if "不正解" in score else "ok")
                    rec = dict(result=result, score=None, total=None)
                else:
                    m2 = re.search(r"(\d+)", score)
                    got = int(m2.group(1)) if m2 else None
                    rec = dict(result=None, score=got, total=100 if got is not None else None)
                add.append((day, kind, ref, rec))
                have.add((day, kind, ref))
    print(f"取り込み候補 {len(add)} 件"
          + ("" if a.apply else " (--apply で実行。いまは下見)"))
    for day, kind, ref, rec in add[: (10 ** 6 if a.apply else 15)]:
        if a.apply:
            ts = datetime.datetime.fromisoformat(day + "T12:00:00").replace(tzinfo=JST)
            log_attempt(repo, kind, ref, src="backfill", ts=ts, quiet=True, **rec)
        else:
            print(f"  {day} {kind} {ref} {rec}")
    if a.apply:
        print("完了。quota.py today で確認してください。")


def cmd_regenre(a):
    """genres.yml を直したあと、既存の記録のジャンルを引き直す。"""
    repo = repo_root(a.repo)
    _, paths = store_paths(repo)
    changed = 0
    for path in paths:
        if not os.path.exists(path):
            continue
        out = []
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            g = genre_for(repo, e.get("kind"), e.get("ref"))
            if g != e.get("genre"):
                print(f"  {e['ref']}: {e.get('genre')} → {g}")
                changed += 1
                e["genre"] = g
            out.append(json.dumps(e, ensure_ascii=False))
        if a.apply and out:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(out) + "\n")
    print(f"{changed} 件" + ("を書き換えました" if a.apply else " (--apply で反映)"))


def main():
    ap = argparse.ArgumentParser(description="学習ノルマの記録と集計 (BL-114)")
    ap.add_argument("--repo", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("log", help="1件記録する")
    p.add_argument("kind", choices=["paper", "lab"])
    p.add_argument("ref")
    p.add_argument("result", nargs="?", choices=["ok", "ng", "partial"], default=None)
    p.add_argument("--score", type=int)
    p.add_argument("--total", type=int)
    p.add_argument("--genre", default=None, help="既定は自動判定")
    p.add_argument("--src", default="manual")
    p.add_argument("--memo", default="")
    p.add_argument("--no-progress", action="store_true")
    p.set_defaults(func=cmd_log)

    p = sub.add_parser("today", help="当日の進捗")
    p.add_argument("--brief", action="store_true", help="1行で出す(フック用)")
    p.add_argument("--date", default=None)
    p.set_defaults(func=cmd_today)

    p = sub.add_parser("grade-lab", help="grade.yml を実走して得点を記録")
    p.add_argument("ref")
    p.add_argument("--variant", default=None)
    p.set_defaults(func=cmd_grade_lab)

    p = sub.add_parser("report", help="期間集計")
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--date", default=None)
    p.add_argument("--out", default=None, help="HTML の書き出し先")
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("backfill", help="_history.md から過去分を取り込む")
    p.add_argument("--apply", action="store_true")
    p.set_defaults(func=cmd_backfill)

    p = sub.add_parser("regenre", help="genres.yml 変更後にジャンルを引き直す")
    p.add_argument("--apply", action="store_true")
    p.set_defaults(func=cmd_regenre)

    a = ap.parse_args()
    sys.exit(a.func(a) or 0)


if __name__ == "__main__":
    main()
