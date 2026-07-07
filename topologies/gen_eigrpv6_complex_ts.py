#!/usr/bin/env python3
"""EIGRPv6(IPv6) 複合トラブルシュート生成器 — classic/named 混在。

v4版 gen_eigrp_complex_ts.py の IPv6 焼き直し＋方式混在(OSPFv3生成器のtrad/AF混在と同じ軸)。
実機プローブ済(IOL 17.15, 2026-07-02):
  - classic: `ipv6 router eigrp <AS>`(router-id必須) + IF `ipv6 eigrp <AS>`。
    ※旧IOSの「プロセスがshutdownで生まれる」罠は 17.15 には無い(プローブ確認)→故障に使わない。
  - named: `router eigrp <NAME>` + `address-family ipv6 unicast autonomous-system <AS>`。
    ★IPv6 AF は network 文が無く **IPv6が付いた全IFが自動参加**。除外は af-interface `shutdown`。
  - 方式は同一リンクで相互運用OK。認証: classic IF `ipv6 authentication mode eigrp <AS> md5`
    +`ipv6 authentication key-chain eigrp <AS> <KC>` / named af-IF `authentication mode md5`
    +`authentication key-chain <KC>` または `authentication mode hmac-sha-256 <pwd>`(named限定)。
    MD5⇔SHA-256不一致・key-string不一致は隣接断(実機確認)。

トポロジ/公平性は v4 と同一: ダイヤモンド(s-a-d/s-b-d)=冗長 ＋ チェーン(d-e-f-g)。
隣接系故障はクリティカル辺(d-e/e-f/f-g)のみ。stubは「端点到達可・中継不可」でチケット選定。

故障(--faults N):
  link_dead(classic=IF有効化漏れ / named=af-interface shutdown) / passive_interface /
  auth_one_sided(片側のみMD5) / auth_key_mismatch(両側MD5だがkey-string不一致) /
  auth_mode_mismatch(named被疑側SHA-256 vs 対向MD5) /
  k_values_mismatch(全隣接断) / stub_on_transit(下流孤立) / missing_loopback(未広告)

採点: 全ペアで宛先 Loopback を `show ipv6 route eigrp` に学習しているか(raw・next-hopはLL)。
出力: problems/GEN-EIGRPV6-<seed>/。fix.json は fix_generated.yml 互換。
使い方: gen_eigrpv6_complex_ts.py --repo . --seed <int> [--faults N] [--style classic|named|mixed]
"""
import argparse
import json
import os
import random

import yaml

ROLES = ["s", "a", "b", "d", "e", "f", "g"]
TOPO = [("s", "a"), ("s", "b"), ("a", "d"), ("b", "d"),
        ("d", "e"), ("e", "f"), ("f", "g")]
CRIT_ROLE_EDGES = {frozenset({"d", "e"}), frozenset({"e", "f"}), frozenset({"f", "g"})}
STUB_ROLES = {"d", "e", "f"}
PROC = "CCNP6"          # named プロセス名
AS = 100
KC = "KC6"
KEY_GOOD = "CCNP6"
KEY_BAD = "WRONG6"
SHA_PWD = "CCNP6"

FAULT_DIFFICULTY = {
    "link_dead": 4, "passive_interface": 4, "auth_one_sided": 4,
    "auth_key_mismatch": 5, "auth_mode_mismatch": 5,
    "k_values_mismatch": 5, "stub_on_transit": 4, "missing_loopback": 3,
}
LINK_FAULTS = ["link_dead", "passive_interface", "auth_one_sided",
               "auth_key_mismatch", "auth_mode_mismatch"]
WHOLE_FAULTS = ["k_values_mismatch"]
STUB_FAULTS = ["stub_on_transit"]
DEST_FAULTS = ["missing_loopback"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--faults", type=int, default=3)
    ap.add_argument("--style", choices=["classic", "named", "mixed"], default="mixed")
    a = ap.parse_args()
    if a.faults < 1:
        raise SystemExit("--faults は 1 以上")
    rnd = random.Random(a.seed)

    phys = [f"RT{i:02d}" for i in range(1, len(ROLES) + 1)]
    rnd.shuffle(phys)
    R = dict(zip(ROLES, phys))
    role = {v: k for k, v in R.items()}
    routers = [R[r] for r in ROLES]

    # 方式(ルータ単位)
    if a.style == "mixed":
        style_of = {r: rnd.choice(["classic", "named"]) for r in routers}
    else:
        style_of = {r: a.style for r in routers}

    # アドレッシング: Loopback 2001:DB8:<k>::<k>/128 / リンク 2001:DB8:<p>::/64
    used = set(); lo = {}
    for r in routers:
        while True:
            k = rnd.randint(1, 99)
            if k not in used:
                used.add(k); lo[r] = f"2001:DB8:{k}::{k}"; break
    rid = {}; usedr = set()
    for r in routers:
        while True:
            k = rnd.randint(1, 99)
            if k not in usedr:
                usedr.add(k); rid[r] = f"{k}.{k}.{k}.{k}"; break
    usedp = set(); pseg = {}
    for e in TOPO:
        while True:
            p = rnd.randint(100, 999)
            if p not in usedp:
                usedp.add(p); pseg[e] = f"2001:DB8:{p}:"; break

    slot = {r: 0 for r in routers}; links = []
    for (ra, rb) in TOPO:
        x, y = R[ra], R[rb]
        seg = pseg[(ra, rb)]
        links.append({"a": x, "a_if": slot[x], "a_ip": f"{seg}:1",
                      "b": y, "b_if": slot[y], "b_ip": f"{seg}:2", "seg": seg})
        slot[x] += 1; slot[y] += 1
    ifaces = {r: [] for r in routers}     # (slot, my_ip, nb)
    for lk in links:
        ifaces[lk["a"]].append((lk["a_if"], lk["a_ip"], lk["b"]))
        ifaces[lk["b"]].append((lk["b_if"], lk["b_ip"], lk["a"]))

    def peer_slot(node, nb):
        for (s, ip, n) in ifaces[nb]:
            if n == node:
                return s
        raise KeyError

    crit_phys = {frozenset({R[x], R[y]}) for e in CRIT_ROLE_EDGES for (x, y) in [tuple(e)]}

    # ---- 故障選択（非干渉・auth系は両端IFを消費）----
    faults, used_if, used_edge, used_node = [], set(), set(), set()
    catalog = LINK_FAULTS + WHOLE_FAULTS + STUB_FAULTS + DEST_FAULTS
    # auth_of[(node,slot)] = "md5_good" | "md5_bad" | "sha256"
    auth_of = {}
    attempts = 0
    while len(faults) < a.faults and attempts < 800:
        attempts += 1
        ft = rnd.choice(catalog)
        if ft in LINK_FAULTS:
            fr = rnd.choice(routers)
            if ft == "auth_mode_mismatch" and style_of[fr] != "named":
                continue                      # SHA-256 は named 限定
            cands = [(s, ip, nb) for (s, ip, nb) in ifaces[fr]
                     if frozenset({fr, nb}) in crit_phys
                     and (fr, s) not in used_if and frozenset({fr, nb}) not in used_edge
                     and fr not in used_node and nb not in used_node]
            if not cands:
                continue
            s, ip, nb = rnd.choice(cands)
            ps = peer_slot(fr, nb)
            used_if.add((fr, s)); used_edge.add(frozenset({fr, nb}))
            used_node.add(fr); used_node.add(nb)
            if ft == "auth_one_sided":
                auth_of[(fr, s)] = "md5_good"
            elif ft == "auth_key_mismatch":
                auth_of[(fr, s)] = "md5_bad"; auth_of[(nb, ps)] = "md5_good"
                used_if.add((nb, ps))
            elif ft == "auth_mode_mismatch":
                auth_of[(fr, s)] = "sha256"; auth_of[(nb, ps)] = "md5_good"
                used_if.add((nb, ps))
            faults.append({"type": ft, "node": fr, "slot": s, "neighbor": nb,
                           "iol_if": f"Ethernet0/{s}", "style": style_of[fr],
                           "difficulty": FAULT_DIFFICULTY[ft]})
        elif ft in WHOLE_FAULTS:
            fr = rnd.choice(routers)
            if fr in used_node:
                continue
            used_node.add(fr)
            faults.append({"type": ft, "node": fr, "style": style_of[fr],
                           "difficulty": FAULT_DIFFICULTY[ft]})
        elif ft in STUB_FAULTS:
            cand = [r for r in routers if role[r] in STUB_ROLES and r not in used_node]
            if not cand:
                continue
            fr = rnd.choice(cand); used_node.add(fr)
            faults.append({"type": ft, "node": fr, "style": style_of[fr],
                           "difficulty": FAULT_DIFFICULTY[ft]})
        else:  # missing_loopback
            fr = rnd.choice(routers)
            if fr in used_node:
                continue
            used_node.add(fr)
            faults.append({"type": ft, "node": fr, "style": style_of[fr],
                           "difficulty": FAULT_DIFFICULTY[ft]})
    if not faults:
        raise SystemExit("故障を配置できなかった")

    iff = {(f["node"], f["slot"]): f["type"] for f in faults if "slot" in f}
    noloop = {f["node"] for f in faults if f["type"] == "missing_loopback"}
    kval_nodes = {f["node"] for f in faults if f["type"] == "k_values_mismatch"}
    stub_nodes = {f["node"] for f in faults if f["type"] == "stub_on_transit"}

    # ---- 到達性(症状・代表ペア): v4 と同じ修正済みモデル(stub=端点可・中継不可) ----
    broken = set()
    for f in faults:
        if f["type"] in LINK_FAULTS:
            broken.add(frozenset({f["node"], f["neighbor"]}))
        elif f["type"] in WHOLE_FAULTS:
            for (s, ip, nb) in ifaces[f["node"]]:
                broken.add(frozenset({f["node"], nb}))
    adj = {r: set() for r in routers}
    for lk in links:
        if frozenset({lk["a"], lk["b"]}) not in broken:
            adj[lk["a"]].add(lk["b"]); adj[lk["b"]].add(lk["a"])

    def dest_set(T):
        if T in noloop:
            return set()
        seen = {T}; stk = [T]
        while stk:
            x = stk.pop()
            if x != T and x in stub_nodes:
                continue
            for y in adj[x]:
                if y not in seen:
                    seen.add(y); stk.append(y)
        seen.discard(T)
        return seen

    failing = []
    for t in routers:
        ds = dest_set(t)
        for sN in routers:
            if sN != t and sN not in ds:
                failing.append((sN, t))
    rep = sorted(failing)[0] if failing else (routers[0], routers[1])

    # ---- config 描画 ----
    def auth_lines_classic(kind):
        L = [f" ipv6 authentication mode eigrp {AS} md5",
             f" ipv6 authentication key-chain eigrp {AS} {KC}"]
        return L if kind in ("md5_good", "md5_bad") else L   # classic は md5 のみ

    def render(Rn):
        st = style_of[Rn]
        need_kc = any(auth_of.get((Rn, s)) in ("md5_good", "md5_bad")
                      for (s, ip, nb) in ifaces[Rn])
        # sha256 被疑ノードにも(修復でMD5へ揃える用に) key chain を配る
        need_kc = need_kc or any(auth_of.get((Rn, s)) == "sha256" for (s, ip, nb) in ifaces[Rn])
        key = KEY_BAD if any(auth_of.get((Rn, s)) == "md5_bad" for (s, ip, nb) in ifaces[Rn]) \
            else KEY_GOOD
        L = [f"! {Rn} (role={role[Rn]}, eigrpv6={st}) 初期構成", "ipv6 unicast-routing", "!"]
        if need_kc:
            L += [f"key chain {KC}", " key 1", f"  key-string {key}", "!"]
        # Loopback
        L += ["interface Loopback0", f" ipv6 address {lo[Rn]}/128"]
        if st == "classic" and Rn not in noloop:
            L.append(f" ipv6 eigrp {AS}")
        L.append("!")
        # 物理IF
        for (s, ip, nb) in sorted(ifaces[Rn]):
            ft = iff.get((Rn, s))
            L += [f"interface {{{{ links[{s}] }}}}", f" ipv6 address {ip}/64"]
            if st == "classic":
                ak = auth_of.get((Rn, s))
                if ak in ("md5_good", "md5_bad"):
                    L += auth_lines_classic(ak)
                if ft != "link_dead":
                    L.append(f" ipv6 eigrp {AS}")
            L.append(" no shutdown")
            L.append("!")
        # プロセス
        if st == "classic":
            L += [f"ipv6 router eigrp {AS}", f" eigrp router-id {rid[Rn]}"]
            if Rn in kval_nodes:
                L.append(" metric weights 0 2 0 1 0 0")
            if Rn in stub_nodes:
                L.append(" eigrp stub connected")
            for (s, ip, nb) in sorted(ifaces[Rn]):
                if iff.get((Rn, s)) == "passive_interface":
                    L.append(f" passive-interface {{{{ links[{s}] }}}}")
            L.append("!")
        else:
            L += [f"router eigrp {PROC}",
                  f" address-family ipv6 unicast autonomous-system {AS}"]
            if Rn in kval_nodes:
                L.append("  metric weights 0 2 0 1 0 0")
            if Rn in stub_nodes:
                L.append("  eigrp stub connected")
            if Rn in noloop:
                L += ["  af-interface Loopback0", "   shutdown", "  exit-af-interface"]
            for (s, ip, nb) in sorted(ifaces[Rn]):
                ft = iff.get((Rn, s))
                ak = auth_of.get((Rn, s))
                blk = [f"  af-interface {{{{ links[{s}] }}}}"]
                if ft == "link_dead":
                    blk.append("   shutdown")
                if ft == "passive_interface":
                    blk.append("   passive-interface")
                if ak in ("md5_good", "md5_bad"):
                    blk += ["   authentication mode md5",
                            f"   authentication key-chain {KC}"]
                elif ak == "sha256":
                    blk.append(f"   authentication mode hmac-sha-256 {SHA_PWD}")
                blk.append("  exit-af-interface")
                if len(blk) > 2:
                    L += blk
            L += [f"  eigrp router-id {rid[Rn]}", " exit-address-family", "!"]
        return L

    # ---- fix ----
    def clas_proc():
        return f"ipv6 router eigrp {AS}"

    def af_parents(sub=None):
        p = [f"router eigrp {PROC}", f"address-family ipv6 unicast autonomous-system {AS}"]
        if sub:
            p.append(sub)
        return p

    def fault_fix(f):
        ft, Rn, st = f["type"], f["node"], f["style"]
        iol = f.get("iol_if")
        if ft == "link_dead":
            if st == "classic":
                return [{"node": Rn, "parents": f"interface {iol}", "lines": [f"ipv6 eigrp {AS}"]}]
            return [{"node": Rn, "parents": af_parents(f"af-interface {iol}"),
                     "lines": ["no shutdown"]}]
        if ft == "passive_interface":
            if st == "classic":
                return [{"node": Rn, "parents": clas_proc(),
                         "lines": [f"no passive-interface {iol}"]}]
            return [{"node": Rn, "parents": af_parents(f"af-interface {iol}"),
                     "lines": ["no passive-interface"]}]
        if ft == "auth_one_sided":
            if st == "classic":
                return [{"node": Rn, "parents": f"interface {iol}",
                         "lines": [f"no ipv6 authentication mode eigrp {AS} md5",
                                   f"no ipv6 authentication key-chain eigrp {AS} {KC}"]}]
            return [{"node": Rn, "parents": af_parents(f"af-interface {iol}"),
                     "lines": ["no authentication mode md5",
                               f"no authentication key-chain {KC}"]}]
        if ft == "auth_key_mismatch":
            return [{"node": Rn, "parents": [f"key chain {KC}", "key 1"],
                     "lines": [f"key-string {KEY_GOOD}"]}]
        if ft == "auth_mode_mismatch":   # named 限定
            return [{"node": Rn, "parents": af_parents(f"af-interface {iol}"),
                     "lines": [f"no authentication mode hmac-sha-256 {SHA_PWD}",
                               "authentication mode md5",
                               f"authentication key-chain {KC}"]}]
        if ft == "k_values_mismatch":
            if st == "classic":
                return [{"node": Rn, "parents": clas_proc(), "lines": ["no metric weights"]}]
            return [{"node": Rn, "parents": af_parents(),
                     "lines": ["metric weights 0 1 0 1 0 0"]}]
        if ft == "stub_on_transit":
            par = clas_proc() if st == "classic" else af_parents()
            return [{"node": Rn, "parents": par, "lines": ["no eigrp stub"]}]
        # missing_loopback
        if st == "classic":
            return [{"node": Rn, "parents": "interface Loopback0", "lines": [f"ipv6 eigrp {AS}"]}]
        return [{"node": Rn, "parents": af_parents("af-interface Loopback0"),
                 "lines": ["no shutdown"]}]

    fixes = [fx for f in faults for fx in fault_fix(f)]

    # ---- 採点(全ペア・宛先 Loopback 学習 raw) ----
    pairs = [(x, y) for x in routers for y in routers if x != y]
    n = len(pairs); base = 100 // n; rem = 100 - base * n
    checks = []
    for i, (x, y) in enumerate(pairs):
        pts = base + (1 if i < rem else 0)
        checks.append({"name": f"{x}: {lo[y]}/128 を EIGRPv6 で学習(到達)",
                       "node": x, "command": "show ipv6 route eigrp",
                       "raw": [{"regex": lo[y].replace(".", r"\.")}], "points": pts})

    diff = min(5, max(f["difficulty"] for f in faults) + (1 if len(faults) > 1 else 0))
    prob_id = f"GEN-EIGRPV6-{a.seed}"
    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)
    problem = {"id": prob_id, "title": f"EIGRPv6 複合TS classic/named混在 (seed={a.seed})",
               "exam": "ENARSI", "topics": ["eigrp", "ipv6", "troubleshooting", "generated"],
               "difficulty": diff, "topology": "generated", "target_nodes": routers,
               "points": 100, "access": "ssh", "bringup_data_ifs": True,
               "lab": {"links": [{"a": lk["a"], "a_if": lk["a_if"], "b": lk["b"], "b_if": lk["b_if"]}
                                 for lk in links],
                       # CMLキャンバス座標(役割ベースの正準配置。見た目のみ)
                       "positions": {R[rl]: list(xy) for rl, xy in {
                           "s": (-500, -360), "a": (-700, -180), "b": (-300, -180),
                           "d": (-500, 0), "e": (-240, 0), "f": (20, 0),
                           "g": (280, 0)}.items()}}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_eigrpv6_complex_ts.py) seed={a.seed}\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)
    for Rn in routers:
        with open(f"{pdir}/initial/{Rn}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(render(Rn)) + "\n")
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_eigrpv6_complex_ts.py) seed={a.seed}\n")
        yaml.safe_dump({"problem": prob_id, "total_points": 100,
                        "defaults": {"genie_os": "iosxe"}, "checks": checks},
                       f, sort_keys=False, allow_unicode=True)
    with open(f"{pdir}/solution/fault.json", "w", encoding="utf-8") as f:
        json.dump({"count": len(faults), "faults": faults,
                   "roles": {role[r]: r for r in routers},
                   "styles": style_of}, f, ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/fix.json", "w", encoding="utf-8") as f:
        json.dump({"fixes": fixes}, f, ensure_ascii=False, indent=2)

    ledger = "\n".join(f"| {r} | `{lo[r]}/128` | {style_of[r]} | 10.1.10.{11 + i} |"
                       for i, r in enumerate(routers))
    task = f"""# 問題 {prob_id} : EIGRPv6(IPv6) 複合トラブルシュート — classic/named 混在（難易度{diff}）

## 状況
**IPv6 のみ**・単一 AS **{AS}** の EIGRPv6 網で到達性障害。全ルータが全 Loopback へ相互到達する
状態へ復旧してください。**有効化方式は classic（`ipv6 router eigrp`）と named
（`router eigrp {PROC}` + `address-family ipv6`）がルータ毎に混在**しています。

## トラブルチケット（代表症状・1件）
> **{rep[0]} から {rep[1]} の Loopback (`{lo[rep[1]]}`) へ到達できない。** 原因は1か所とは限りません。

## ルータ / Loopback 台帳（mgmt は割当順）
| ルータ | Loopback0 | 方式 | mgmt(SSH) |
|--------|-----------|------|-----------|
{ledger}

## 到達目標 / 切り分け
- 全ルータが全 Loopback を `show ipv6 route eigrp` で学習し相互到達。
- トポロジ・故障の種類・場所・件数は非公開。
- **EIGRPv6 の勘所**:
  - classic は **インタフェースで `ipv6 eigrp {AS}`** を打った所だけ参加。
  - named の IPv6 AF は **network 文が無く、IPv6 が付いた全IFが自動参加**。
    除外・停止は `af-interface <IF>` 配下の `shutdown`（＝ここが落とし穴になり得る）。
  - 認証は classic=IF直下 `ipv6 authentication ...`、named=af-interface 配下。
    named は **hmac-sha-256** も選べる（**両端で方式・鍵が一致しないと隣接不可**）。
  - hello/hold 不一致では隣接は落ちない。K値不一致は全隣接断。中継機の stub は下流丸ごと欠落。
- 切り分け: `show ipv6 eigrp neighbors` / `show ipv6 eigrp interfaces` / `show ipv6 protocols` /
  `show ipv6 route eigrp` / `show running-config | section eigrp`。

## アクセス・採点
SSH `SUZUKI / CCNP`。
```
ansible-playbook playbooks/grade.yml -e problem={prob_id} --vault-password-file <(printf 'CCNP\\n')
```
"""
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(task)
    print(f"wrote problems/{prob_id} : faults={[(f['type'], f['node']) for f in faults]} "
          f"styles={style_of}")


if __name__ == "__main__":
    main()
