#!/usr/bin/env python3
"""紙面の単元ローテーション(BL-224・設計= problems/_drafts/LAB-ROTATION.design.md §7)。

デフォルト問題パックの紙面 3 枠(思考・瞬発・穴埋め)を、**資格で絞らず** units.yml の単元から
均等に出す。単元ごとの「最後にやった日」が古い順に 1 問ずつ割り当て、その単元の shape/kind だけに
絞って(`--only-kinds`)生成する。ラボ(lab_rotation.py)と同じく「やった」は採点記録基準。

  思考枠: 単元の plain shape(chain/acl/…/mpls)か、知識ファミリの THINK_KINDS を持つ単元
  瞬発枠: 知識ファミリの SPEED_KINDS(無指定は全 kind)か mpls の SPEED_KINDS を持つ単元
  穴埋め: cloze の範囲内 kind(scope=beyond 以外)を持つ単元

単体で動かすと単元ごとの最終日と、各枠の次の候補順を出す:
  python3 topologies/paper_rotation.py [--mode default] [--date 2026-09-28]
"""
import argparse
import datetime
import fnmatch
import glob
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
KIND_RE = re.compile(r"種別:\s*`?([a-z0-9]+)/([a-z0-9_]+)")
SHAPE_RE = re.compile(r"生成:\s*`?gen_paper_\w+\.py --shape ([a-z0-9]+)")
SLOTS = ("think", "speed", "cloze")
SLOT_JA = {"think": "思考", "speed": "瞬発", "cloze": "穴埋め"}


def _kind_tables():
    """shape → {"think": [kind], "speed": [kind]}、と cloze の範囲内 kind。"""
    sys.path.insert(0, HERE)
    import gen_paper_mcq as gm
    import gen_paper_cloze as gc
    tab = {}
    for f, m in gm.KB_FAMILIES.items():
        if f == "cloze":
            continue
        think = list(getattr(m, "THINK_KINDS", None) or [])
        sk = getattr(m, "SPEED_KINDS", None)
        tab[f] = {"think": think, "speed": list(m.KINDS if sk is None else sk), "kb": True}
    tab["mpls"] = {"think": list(gm.gpm.KINDS), "speed": list(gm.gpm.SPEED_KINDS), "kb": False}
    return tab, list(gc.KINDS)


def _match(kinds, kpat):
    return [k for k in kinds if fnmatch.fnmatchcase(k, kpat)]


def slot_specs(globs, tab, cloze_kinds):
    """単元の shape/kind グロブ → 枠ごとの生成指定 [(shape 引数, only-kinds グロブ列)]。"""
    think, speed, cloze = {}, [], []
    for gl in globs:
        shape, _, kpat = gl.partition("/")
        kpat = kpat or "*"
        if shape == "cloze":
            if _match(cloze_kinds, kpat):
                cloze.append(gl)
            continue
        t = tab.get(shape)
        if t is None:                                   # plain shape(chain/acl/pref/…)
            think.setdefault(shape, []).append(gl)
            continue
        if _match(t["think"], kpat):
            # 知識ファミリの思考 kind は --shape mixed --only-kinds で引く(BL-216 の経路)
            key = "mixed" if t["kb"] else shape
            think.setdefault(key, []).append(
                gl if not t["kb"] else ",".join(f"{shape}/{k}" for k in _match(t["think"], kpat)))
        if _match(t["speed"], kpat):
            speed.append(",".join(f"{shape}/{k}" for k in _match(t["speed"], kpat)))
    out = {"think": [(sh, gl) for sh, gl in think.items()],
           "speed": [("speed", speed)] if speed else [],
           "cloze": [("cloze", cloze)] if cloze else []}
    return out


def load_mode_units(repo, mode_name="default"):
    """モードの紙面単元 → {uid: {"name", "globs", "specs"}}。"""
    sys.path.insert(0, HERE)
    import gen_pack
    import lab_rotation
    mode = lab_rotation.load_mode(repo, mode_name)
    pconf = mode.get("paper") or {"units": "all"}
    data = gen_pack.load_units(repo)
    if pconf.get("units", "all") == "all":
        uids = [u for u, d in data["units"].items() if d["paper"]["kinds"]]
    else:
        uids = [u for u in pconf["units"] if u in data["units"]]
    uids = [u for u in uids if u not in set(pconf.get("exclude") or [])]
    tab, cloze_kinds = _kind_tables()
    out = {}
    for u in uids:
        globs = sorted(set(data["units"][u]["paper"]["kinds"]))
        specs = slot_specs(globs, tab, cloze_kinds)
        if any(specs[s] for s in SLOTS):
            out[u] = {"name": data["units"][u]["name"], "globs": globs, "specs": specs}
    return out


def units_of_kind(sk, units):
    return [u for u, d in units.items() if any(fnmatch.fnmatchcase(sk, g) for g in d["globs"])]


def _kind_of_stamp(repo, stamp):
    """answers の `種別:` 行 → shape/kind。種別行が無い shape(ospfbgp 等)は `生成:` 行の shape で shape/*。"""
    try:
        with open(os.path.join(repo, "answers", f"{stamp}.md"), encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return None
    m = KIND_RE.search(text)
    if m:
        return f"{m.group(1)}/{m.group(2)}"
    m = SHAPE_RE.search(text)
    return f"{m.group(1)}/*" if m else None


def last_seen(repo, units, today):
    """単元 → 最後にやった日(採点記録の紙面行)。今日のパック(本番)に載った紙面も今日として数える。"""
    seen = {}
    t = today.isoformat()

    def bump(stamp, day):
        sk = _kind_of_stamp(repo, stamp)
        if not sk:
            return
        for u in units_of_kind(sk, units):
            if day > seen.get(u, ""):
                seen[u] = day

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
                if r.get("kind") == "paper" and r.get("day", "") <= t and re.match(r"^\d{8}-\d+$", str(r.get("ref"))):
                    bump(r["ref"], r["day"])
    for path in glob.glob(os.path.join(repo, "packs", "PACK-*", "manifest.yml")):
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        if "dry_run: true" in text or f"created: {t}" not in text:
            continue
        for st in re.findall(r"^\s+ref:\s*(\d{8}-\d+)\s*$", text, re.M):
            bump(st, t)
    return seen


class PaperRotation:
    """1 日ぶん(3 パック)を通して単元を配る。pick(slot) のたびに選んだ単元を最後尾へ回す。"""

    def __init__(self, repo, mode_name, today, rnd, log=print):
        self.units = load_mode_units(repo, mode_name)
        self.today = today
        seen = last_seen(repo, self.units, today)
        self.seen = seen
        # 並び順キー= (最終日, 今日の中での通し番号, 乱数)。未実施は最前
        self.key = {u: (seen.get(u, ""), 0, rnd.random()) for u in self.units}
        self.seq = 0
        self.rnd = rnd
        self.log = log

    def order(self, slot):
        return sorted((u for u, d in self.units.items() if d["specs"][slot]),
                      key=lambda u: self.key[u])

    def take(self, uid):
        self.seq += 1
        self.key[uid] = (self.today.isoformat(), self.seq, self.key[uid][2])

    def args_for(self, uid, slot):
        """単元 uid を slot で 1 問出す生成指定 (shape, [--only-kinds …])。思考枠は shape を乱択。"""
        specs = self.units[uid]["specs"][slot]
        shape, globs = self.rnd.choice(specs)
        return shape, ["--only-kinds", ",".join(globs)]

    def describe(self, top=6):
        lines = [f"[紙面ローテ] 単元 {len(self.units)} / ノルマ日 {self.today}"
                 f" / 未実施 {sum(1 for u in self.units if u not in self.seen)}"]
        for s in SLOTS:
            od = self.order(s)
            lines.append(f"[紙面ローテ] {SLOT_JA[s]}枠の候補 {len(od)} 単元・次: "
                         + " → ".join(f"{u}{self.units[u]['name']}({self.seen.get(u, '未')})"
                                      for u in od[:top]))
        return lines


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mode", default="default")
    ap.add_argument("--date", help="ノルマ日を仮定(YYYY-MM-DD)")
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--all", action="store_true", help="単元ごとの枠と最終日を全部出す")
    a = ap.parse_args()
    sys.path.insert(0, HERE)
    import lab_rotation
    today = datetime.date.fromisoformat(a.date) if a.date else lab_rotation.quota_today(a.repo)
    rot = PaperRotation(a.repo, a.mode, today, random.Random(0))
    for line in rot.describe():
        print(line)
    if a.all:
        for u, d in sorted(rot.units.items(), key=lambda x: rot.key[x[0]]):
            slots = "/".join(SLOT_JA[s] for s in SLOTS if d["specs"][s])
            print(f"  {u:6} {d['name']:<18} 最終 {rot.seen.get(u, '未実施'):<10} 枠 {slots}")


if __name__ == "__main__":
    main()
