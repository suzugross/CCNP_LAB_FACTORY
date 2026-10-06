#!/usr/bin/env python3
"""ラボ単元ローテーション(BL-223・設計= problems/_drafts/LAB-ROTATION.design.md)。

デフォルト問題パックのラボを「単元の曜日表＋遅れ補正」で選ぶ。モード定義は lab_modes.yml。
ここは**どの単元を出すか**までを決める純粋な計算。単元 → ジャンル → 問題の解決(台数予算・
カタログ)は gen_pack.select_rotation_labs が行う。

  - 日付はノルマ日(JST 04:00 境界)。曜日もノルマ日で決める。
  - 「やった」= 採点記録(records/attempts.jsonl・private 側も)の日。採点記録が 1 件も無い単元だけ
    出題履歴(_history.md)の日で代用。今日すでに出題した単元(同日の再実行)も「やった」に数える。
  - 遅れ度 = 経過日数 ÷ (7 / per_week)。一度もやっていない単元は NEVER_RATIO。
  - 遅れ度 ≥ catchup_ratio の単元を曜日表の外から最大 max_catchup 枠 → 残りを曜日表から → なお空けば遅れ度順。
  - 発掘枠(BL-233): mode の `discovery.slots` 本は単元ローテーションの外(gen_pack.select_discovery_labs)。
    ここで計画する単元の枠数は `slots - discovery.slots`(rotation_slots)。

単体で動かすと今日(または --date)の選定表と、発掘枠の待ち行列を出す:
  python3 topologies/lab_rotation.py [--mode default] [--date 2026-09-28]
"""
import argparse
import datetime
import glob
import json
import os
import re
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
WEEKDAY_JA = dict(zip(WEEKDAYS, "月火水木金土日"))
NEVER_RATIO = 99.0


def _merge(dst, src):
    """辞書は再帰的に合流、それ以外は src で上書き(private 側の後勝ち)。"""
    for k, v in (src or {}).items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _merge(dst[k], v)
        else:
            dst[k] = v
    return dst


def load_mode(repo=REPO, name="default"):
    path = os.path.join(repo, "topologies", "lab_modes.yml")
    with open(path, encoding="utf-8") as fh:
        modes = (yaml.safe_load(fh) or {}).get("modes") or {}
    if name not in modes:
        sys.exit(f"[lab_rotation] モード {name!r} が lab_modes.yml にありません(候補: {', '.join(modes)})")
    mode = dict(modes[name])
    # ★PVT 系の ID に触れる設定(発掘枠の保留など)は private/lab_modes.yml に書く(units.yml と同じ後勝ちの合流)
    pvt = os.path.join(repo, "private", "lab_modes.yml")
    if os.path.exists(pvt):
        with open(pvt, encoding="utf-8") as fh:
            _merge(mode, ((yaml.safe_load(fh) or {}).get("modes") or {}).get(name))
    mode["name"] = name
    mode.setdefault("slots", 3)
    mode.setdefault("catchup_ratio", 2.0)
    mode.setdefault("max_catchup", 2)
    mode.setdefault("week", {})
    disc = mode.setdefault("discovery", {})
    disc.setdefault("slots", 0)
    disc.setdefault("min_diff", 3)
    disc.setdefault("kinds", ["generator", "static"])
    disc.setdefault("hold", {})
    disc.setdefault("args", {})
    for u, spec in mode["units"].items():
        spec.setdefault("label", u)
        spec.setdefault("per_week", 2)
        spec.setdefault("genres", [])
        spec.setdefault("also", [])
    return mode


def rotation_slots(mode):
    """単元ローテーションに回す枠数(= 全体の slots から発掘枠を引いた残り)。"""
    return max(0, mode["slots"] - mode["discovery"]["slots"])


def quota_today(repo=REPO):
    sys.path.insert(0, HERE)
    import quota
    cfg = quota.config(repo)
    return datetime.date.fromisoformat(quota.quota_day(quota.now_jst(), cfg["day_start"]))


def unit_matchers(mode, lab_genres):
    """単元 → 問題 ID を判定する正規表現の列。ジャンルの prefixes/ids から自動で作り、also を足す。"""
    out = {}
    for u, spec in mode["units"].items():
        pats = []
        for g in spec["genres"]:
            gs = lab_genres.get(g) or {}
            for p in list(gs.get("prefixes", [])) + list(gs.get("gap_families", [])):
                pats.append("^" + re.escape(p) + r"(-\d+)?$")
            for pid in [i for tier in gs.get("ids", []) for i in tier] + list(gs.get("gap_ids", [])):
                pats.append("^" + re.escape(pid) + "$")
        pats += list(spec["also"])
        out[u] = [re.compile(p) for p in pats]
    return out


def unit_of(ref, matchers):
    for u, pats in matchers.items():
        if any(p.search(ref) for p in pats):
            return u
    return None


def _attempt_days(repo):
    """採点記録のラボ行 → [(日付, ref)]。"""
    rows = []
    for rel in ("records/attempts.jsonl", "private/attempts.jsonl"):
        path = os.path.join(repo, rel)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get("kind") == "lab" and r.get("ref") and r.get("day"):
                    rows.append((r["day"], r["ref"]))
    return rows


def last_seen(repo, mode, lab_genres, today, hist):
    """単元 → (最後にやった日 or None, 根拠)。hist = gen_pack.parse_history() の [(日付, ID)]。"""
    matchers = unit_matchers(mode, lab_genres)
    by_attempt, by_issue, issued_today = {}, {}, set()
    for d, ref in _attempt_days(repo):
        u = unit_of(ref, matchers)
        if u and d <= today.isoformat() and d > by_attempt.get(u, ""):
            by_attempt[u] = d
    for d, pid in hist:
        u = unit_of(pid, matchers)
        if not u or d > today.isoformat():
            continue
        if d > by_issue.get(u, ""):
            by_issue[u] = d
        if d == today.isoformat():
            issued_today.add(u)
    out = {}
    for u in mode["units"]:
        if u in issued_today:
            out[u] = (today, "今日出題済")
        elif u in by_attempt:
            out[u] = (datetime.date.fromisoformat(by_attempt[u]), "採点")
        elif u in by_issue:
            out[u] = (datetime.date.fromisoformat(by_issue[u]), "出題(採点記録なし)")
        else:
            out[u] = (None, "記録なし")
    return out


def ratio(mode, unit, seen, today):
    d = seen[unit][0]
    if d is None:
        return NEVER_RATIO
    return (today - d).days / (7.0 / mode["units"][unit]["per_week"])


def plan_units(mode, today, seen, slots=None, exclude=()):
    """今日出す単元の順序つきリスト(picks)と、解決に失敗した時の代わり(fallback)と説明。

    slots= 単元に回す枠数(既定 rotation_slots)。exclude= 今日は発掘枠が同じ単元の問題を出すので外す単元。
    """
    units = list(mode["units"])
    r = {u: ratio(mode, u, seen, today) for u in units}
    done_today = {u for u in units if seen[u][0] == today} | set(exclude)
    by_ratio = sorted(units, key=lambda u: -r[u])
    wd = WEEKDAYS[today.weekday()]
    week = [u for u in (mode["week"].get(wd) or []) if u in mode["units"]]
    slots = rotation_slots(mode) if slots is None else slots
    picks, why = [], {}
    for u in week:
        if u in exclude:
            why[u] = "曜日表だが今日は発掘枠で出す"
        elif u in done_today:
            why[u] = "曜日表だが今日出題済"
    table = [u for u in sorted(week, key=lambda u: -r[u]) if u not in done_today]
    catch = [u for u in by_ratio if u not in week and u not in done_today
             and r[u] >= mode["catchup_ratio"]][:mode["max_catchup"]]
    # 1. 曜日表から最低 (slots - max_catchup) 枠は必ず出す(規則性の担保)
    keep = max(0, slots - mode["max_catchup"]) if week else 0
    for u in table[:keep]:
        picks.append(u)
        why[u] = "曜日表"
    # 2. 残り枠= 曜日表の残りと遅れ補正候補を遅れ度の大きい順に(補正は遅れていない曜日枠だけを押しのける)
    for u in sorted(table[keep:] + catch, key=lambda u: -r[u]):
        if len(picks) >= slots:
            break
        picks.append(u)
        why[u] = "曜日表" if u in week else "遅れ補正"
    # 3. まだ空きがあれば遅れ度順。ただし翌日の曜日表にある単元は後回しにする
    #    (遅れ度が最大なのはたいてい「明日が出番の単元」で、そのまま埋めると同じ単元が連日になる)
    nxt = set(mode["week"].get(WEEKDAYS[(today.weekday() + 1) % 7]) or [])
    for u in sorted(by_ratio, key=lambda u: u in nxt):
        if len(picks) >= slots:
            break
        if u not in picks and u not in done_today:
            picks.append(u)
            why[u] = "空き枠を遅れ度順で"
    fallback = [u for u in by_ratio if u not in picks and u not in done_today]
    return picks, fallback, {"ratio": r, "why": why, "weekday": wd, "week": week}


def genre_last_issued(repo):
    """ジャンル → 最後に出したノルマ日(パック manifest のラボ行に書いた genre から)。"""
    out = {}
    for path in glob.glob(os.path.join(repo, "packs", "PACK-*", "manifest.yml")):
        created, genres = "", []
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("dry_run:") and "true" in line:
                    genres = []
                    break                       # プレビューは出題していない
                if line.startswith("created:"):
                    created = line.split(":", 1)[1].strip().strip('"')[:10]
                m = re.match(r"^\s+genre:\s*(\S+)", line)
                if m:
                    genres.append(m.group(1).strip('"'))
        for g in genres:
            if created > out.get(g, ""):
                out[g] = created
    return out


def describe(mode, today, seen, plan):
    picks, fallback, info = plan
    wd = info["weekday"]
    lines = [f"[ローテ] モード {mode['name']}({mode.get('label', '')})/ ノルマ日 {today} "
             f"({WEEKDAY_JA[wd]}) / 曜日表: "
             + ("・".join(mode["units"][u]["label"] for u in info["week"]) or "(なし)")]
    for u in sorted(mode["units"], key=lambda u: -info["ratio"][u]):
        d, src = seen[u]
        mark = "★" if u in picks else "  "
        rr = info["ratio"][u]
        lines.append(f"[ローテ] {mark}{mode['units'][u]['label']:<10} 遅れ度 "
                     f"{'未実施' if rr >= NEVER_RATIO else f'{rr:4.2f}'}"
                     f"  最終 {d or '-'}({src})"
                     + (f"  → {info['why'][u]}" if u in info["why"] else ""))
    return lines


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mode", default="default")
    ap.add_argument("--date", help="ノルマ日を仮定(YYYY-MM-DD)")
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--all", action="store_true", help="発掘枠の待ち行列を全件出す(既定は先頭だけ)")
    a = ap.parse_args()
    sys.path.insert(0, HERE)
    import gen_pack
    mode = load_mode(a.repo, a.mode)
    today = datetime.date.fromisoformat(a.date) if a.date else quota_today(a.repo)
    hist = gen_pack.parse_history(a.repo)
    seen = last_seen(a.repo, mode, gen_pack.LAB_GENRES, today, hist)
    for line in describe(mode, today, seen, plan_units(mode, today, seen)):
        print(line)
    for line in gen_pack.describe_discovery(gen_pack.parse_catalog(a.repo), hist, mode, today,
                                            repo=a.repo, full=a.all):
        print(line)


if __name__ == "__main__":
    main()
