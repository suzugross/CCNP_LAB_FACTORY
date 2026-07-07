#!/usr/bin/env python3
"""OSPFv3(IPv6) 複合トラブルシュート生成器（Phase E 第一弾）。

IOL 実機検証済み構文に基づく([[ccnp-ospfv3-syntax]])。マルチエリア・tree(全リンクcritical)。
正準トポロジ(値seedランダム化): area0 chain s-a-d / area1 chain d-e-f, d=ABR。
役割 s/a/d/e/f を物理 RT01-05 に seed シャッフル。

OSPFv3 有効化を **2方式で混在**(--ospfv3-style, 既定 mixed):
  従来: ipv6 router ospf <pid> + IF `ipv6 ospf <pid> area N`
  AF  : router ospfv3 <pid> + address-family ipv6 unicast + IF `ospfv3 <pid> ipv6 area N`
(両方式は相互運用OK＝同一トポロジで混在可。受験者は両表記を読み分ける)

故障(--faults N, 非干渉に複数):
  shutdown / mtu_mismatch / hello_mismatch / dead_interval_mismatch / wrong_area /
  passive_interface / router_id_collision(隣接2機が同一RID) /
  ipsec_auth_mismatch(片端だけVL...いやIFにIPsec認証→不一致で隣接断・OSPFv3はMD5でなくIPsec) /
  stub_flag_mismatch(area1葉にstub→E-bit不一致) / missing_loopback(局所)

採点: 全ペアで宛先 Loopback を `show ipv6 route ospf` に学習しているか(raw・next-hopはLLなので
  プレフィクス有無で判定)。router-id手動必須(IPv6-onlyは自動選定不可)。

出力: problems/GEN-OSPFV3-<seed>/ {problem.yml, initial/*.cfg.j2, grading.yml,
       solution/{fault.json,fix.json}, task.md}。fix.json は fix_generated.yml 互換。
使い方: gen_ospfv3_complex_ts.py --repo . --seed <int> [--faults N] [--ospfv3-style ...]
"""
import argparse
import json
import os
import random

import yaml

ROLES = ["s", "a", "d", "e", "f"]
TOPO = [("s", "a", 0), ("a", "d", 0), ("d", "e", 1), ("e", "f", 1)]
PID = 1
IPSEC_KEY = "0123456789012345678901234567890123456789"   # 40hex (sha1)
IPSEC_SPI = 500

# 注: shutdown 故障は入れない。IOL の IPv6-only IF day0 admin-down 対策で lab_up が
# data IF を一括 no shutdown する(bringup_data_ifs)ため、shutdown 故障と衝突するため。
FAULT_DIFFICULTY = {
    "wrong_area": 3, "missing_loopback": 3,
    "mtu_mismatch": 4, "hello_mismatch": 4, "dead_interval_mismatch": 4,
    "passive_interface": 4, "router_id_collision": 5, "ipsec_auth_mismatch": 5,
    "stub_flag_mismatch": 5,
}
LINK_FAULTS = ["wrong_area", "passive_interface", "mtu_mismatch",
               "hello_mismatch", "dead_interval_mismatch", "router_id_collision",
               "ipsec_auth_mismatch"]
STUB_FAULTS = ["stub_flag_mismatch"]
DEST_FAULTS = ["missing_loopback"]


def if_enable(style, area):
    return f"ipv6 ospf {PID} area {area}" if style == "trad" else f"ospfv3 {PID} ipv6 area {area}"


def ipsec_line(style):
    base = "ipv6 ospf" if style == "trad" else "ospfv3"
    return f"{base} authentication ipsec spi {IPSEC_SPI} sha1 {IPSEC_KEY}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--faults", type=int, default=1)
    ap.add_argument("--ospfv3-style", choices=["trad", "af", "mixed"], default="mixed")
    a = ap.parse_args()
    if a.faults < 1:
        raise SystemExit("--faults は 1 以上")
    rnd = random.Random(a.seed)
    area0, area1 = 0, 1

    phys = [f"RT{i:02d}" for i in range(1, len(ROLES) + 1)]
    rnd.shuffle(phys)
    R = dict(zip(ROLES, phys))            # role -> RTxx
    role = {v: k for k, v in R.items()}   # RTxx -> role
    routers = [R[r] for r in ROLES]

    # アドレッシング: Loopback 2001:DB8:<rk>::<rk>/128 / リンク 2001:DB8:<p>::/64
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
            if k != 10 and k not in usedr:
                usedr.add(k); rid[r] = f"{k}.{k}.{k}.{k}"; break
    usedp = set(); pseg = {}
    for (ra, rb, ar) in TOPO:
        while True:
            p = rnd.randint(100, 999)
            if p not in usedp:
                usedp.add(p); pseg[(ra, rb)] = f"2001:DB8:{p}:"; break

    # 物理リンク・IF 索引
    slot = {r: 0 for r in routers}; links = []
    for (ra, rb, ar) in TOPO:
        x, y = R[ra], R[rb]
        seg = pseg[(ra, rb)]
        links.append({"a": x, "a_if": slot[x], "a_ip": f"{seg}:1",
                      "b": y, "b_if": slot[y], "b_ip": f"{seg}:2", "seg": seg, "area": ar})
        slot[x] += 1; slot[y] += 1
    ifaces = {r: [] for r in routers}     # (slot, my_ip, nb, area)
    for lk in links:
        ifaces[lk["a"]].append((lk["a_if"], lk["a_ip"], lk["b"], lk["area"]))
        ifaces[lk["b"]].append((lk["b_if"], lk["b_ip"], lk["a"], lk["area"]))

    # OSPFv3 有効化方式（ルータ単位・mixed は seed ランダム）
    if a.ospfv3_style == "mixed":
        style_of = {r: rnd.choice(["trad", "af"]) for r in routers}
    else:
        style_of = {r: a.ospfv3_style for r in routers}

    lo_area_of = {r: (area1 if role[r] in ("e", "f") else area0) for r in routers}
    leaf = R["f"]

    # ---- 故障選択（非干渉）----
    faults, used_if, used_edge, used_loop, used_stub = [], set(), set(), set(), set()
    catalog = LINK_FAULTS + STUB_FAULTS + DEST_FAULTS
    attempts = 0
    while len(faults) < a.faults and attempts < 600:
        attempts += 1
        ft = rnd.choice(catalog)
        if ft in STUB_FAULTS:
            es = next((s for (s, ip, nb, ar) in ifaces[leaf]), None)
            if leaf in used_stub or (leaf, es) in used_if:
                continue
            used_stub.add(leaf); used_if.add((leaf, es))
            faults.append({"type": ft, "node": leaf, "difficulty": FAULT_DIFFICULTY[ft]})
        elif ft in LINK_FAULTS:
            fr = rnd.choice(routers)
            cands = [(s, ip, nb, ar) for (s, ip, nb, ar) in ifaces[fr]
                     if (fr, s) not in used_if and frozenset({fr, nb}) not in used_edge]
            if not cands:
                continue
            s, ip, nb, ar = rnd.choice(cands)
            used_if.add((fr, s)); used_edge.add(frozenset({fr, nb}))
            faults.append({"type": ft, "node": fr, "slot": s, "neighbor": nb,
                           "iol_if": f"Ethernet0/{s}", "area": ar,
                           "difficulty": FAULT_DIFFICULTY[ft]})
        else:  # missing_loopback
            fr = rnd.choice(routers)
            if fr in used_loop:
                continue
            used_loop.add(fr)
            faults.append({"type": ft, "node": fr, "difficulty": FAULT_DIFFICULTY[ft]})
    if not faults:
        raise SystemExit("故障を配置できなかった")

    iff = {(f["node"], f["slot"]): f["type"] for f in faults if "slot" in f and f["type"] in LINK_FAULTS}
    rid_override = {f["node"]: rid[f["neighbor"]] for f in faults if f["type"] == "router_id_collision"}
    noloop = {f["node"] for f in faults if f["type"] == "missing_loopback"}
    stub_leaf = {f["node"] for f in faults if f["type"] == "stub_flag_mismatch"}
    broken = {frozenset({f["node"], f["neighbor"]}) for f in faults if f["type"] in LINK_FAULTS}
    for lf in stub_leaf:
        for (s, ip, nb, ar) in ifaces[lf]:
            broken.add(frozenset({lf, nb}))

    # ---- 到達性(症状) ----
    adj = {r: set() for r in routers}
    for lk in links:
        if frozenset({lk["a"], lk["b"]}) not in broken:
            adj[lk["a"]].add(lk["b"]); adj[lk["b"]].add(lk["a"])
    failing = []
    for s in routers:
        seen = {s}; st = [s]
        while st:
            x = st.pop()
            for y in adj[x]:
                if y not in seen:
                    seen.add(y); st.append(y)
        for t in routers:
            if t != s and not (t in seen and t not in noloop):
                failing.append((s, t))
    rep = sorted(failing)[0] if failing else (routers[0], routers[1])

    # ---- config 描画 ----
    def render(Rn):
        st = style_of[Rn]
        L = [f"! {Rn} (role={role[Rn]}, ospfv3={st}) 初期構成", "ipv6 unicast-routing", "!",
             "interface Loopback0", f" ipv6 address {lo[Rn]}/128"]
        if Rn not in noloop:
            L.append(f" {if_enable(st, lo_area_of[Rn])}")
        L.append("!")
        for (s, ip, nb, ar) in sorted(ifaces[Rn]):
            ft = iff.get((Rn, s))
            L += [f"interface {{{{ links[{s}] }}}}", f" ipv6 address {ip}/64"]
            if ft == "mtu_mismatch":
                L.append(" ipv6 mtu 1400")
            if ft == "hello_mismatch":
                L.append(f" ipv6 ospf hello-interval 5" if st == "trad" else " ospfv3 hello-interval 5")
            if ft == "dead_interval_mismatch":
                L.append(f" ipv6 ospf dead-interval 60" if st == "trad" else " ospfv3 dead-interval 60")
            if ft == "ipsec_auth_mismatch":
                L.append(f" {ipsec_line(st)}")
            put_area = (area1 if ar == area0 else area0) if ft == "wrong_area" else ar
            L.append(f" {if_enable(st, put_area)}")
            L.append(" shutdown" if ft == "shutdown" else " no shutdown")
            L.append("!")
        # プロセス/AF ブロック
        area_cmds = []
        if Rn in stub_leaf:
            area_cmds.append(f"area {area1} stub")
        passive = [f"passive-interface {{{{ links[{s}] }}}}"
                   for (s, ip, nb, ar) in sorted(ifaces[Rn]) if iff.get((Rn, s)) == "passive_interface"]
        rid_v = rid_override.get(Rn, rid[Rn])
        if st == "trad":
            L += [f"ipv6 router ospf {PID}", f" router-id {rid_v}"] \
                + [f" {c}" for c in area_cmds] + [f" {p}" for p in passive] + ["!"]
        else:
            L += [f"router ospfv3 {PID}", f" router-id {rid_v}", " address-family ipv6 unicast"] \
                + [f"  {c}" for c in area_cmds] + [f"  {p}" for p in passive] \
                + [" exit-address-family", "!"]
        return L

    # ---- fix ----
    def fault_fix(f):
        ft, Rn = f["type"], f["node"]
        st = style_of[Rn]
        iff_if = f.get("iol_if")
        if ft == "shutdown":
            return [{"node": Rn, "parents": f"interface {iff_if}", "lines": ["no shutdown"]}]
        if ft == "mtu_mismatch":
            return [{"node": Rn, "parents": f"interface {iff_if}", "lines": ["no ipv6 mtu 1400"]}]
        if ft == "hello_mismatch":
            cmd = "no ipv6 ospf hello-interval" if st == "trad" else "no ospfv3 hello-interval"
            return [{"node": Rn, "parents": f"interface {iff_if}", "lines": [cmd]}]
        if ft == "dead_interval_mismatch":
            cmd = "no ipv6 ospf dead-interval" if st == "trad" else "no ospfv3 dead-interval"
            return [{"node": Rn, "parents": f"interface {iff_if}", "lines": [cmd]}]
        if ft == "ipsec_auth_mismatch":
            base = "ipv6 ospf" if st == "trad" else "ospfv3"
            return [{"node": Rn, "parents": f"interface {iff_if}",
                     "lines": [f"no {base} authentication ipsec spi {IPSEC_SPI}"]}]
        if ft == "wrong_area":
            return [{"node": Rn, "parents": f"interface {iff_if}",
                     "lines": [if_enable(st, f["area"])]}]
        if ft == "passive_interface":
            line = f"no passive-interface {iff_if}"
            if st == "trad":
                return [{"node": Rn, "parents": f"ipv6 router ospf {PID}", "lines": [line]}]
            return [{"node": Rn, "parents": ["router ospfv3 {0}".format(PID), "address-family ipv6 unicast"],
                     "lines": [line]}]
        if ft == "router_id_collision":
            par = f"ipv6 router ospf {PID}" if st == "trad" else f"router ospfv3 {PID}"
            return [{"node": Rn, "parents": par, "lines": [f"router-id {rid[Rn]}"]},
                    {"node": Rn, "exec": [{"command": "clear ipv6 ospf process",
                                           "prompt": "Reset", "answer": "yes"}]}]
        if ft == "stub_flag_mismatch":
            if st == "trad":
                return [{"node": Rn, "parents": f"ipv6 router ospf {PID}", "lines": [f"no area {area1} stub"]}]
            return [{"node": Rn, "parents": ["router ospfv3 {0}".format(PID), "address-family ipv6 unicast"],
                     "lines": [f"no area {area1} stub"]}]
        # missing_loopback
        return [{"node": Rn, "parents": "interface Loopback0",
                 "lines": [if_enable(st, lo_area_of[Rn])]}]

    fixes = [fx for f in faults for fx in fault_fix(f)]

    # ---- 採点(全ペア・宛先Loopbackプレフィクス学習 raw) ----
    pairs = [(x, y) for x in routers for y in routers if x != y]
    n = len(pairs); base = 100 // n; rem = 100 - base * n
    checks = []
    for i, (x, y) in enumerate(pairs):
        pts = base + (1 if i < rem else 0)
        checks.append({"name": f"{x}: {lo[y]}/128 を OSPFv3 で学習(到達)",
                       "node": x, "command": "show ipv6 route ospf",
                       "raw": [{"regex": lo[y].replace(".", r"\.")}], "points": pts})

    diff = min(5, max(f["difficulty"] for f in faults) + (1 if len(faults) > 1 else 0))
    prob_id = f"GEN-OSPFV3-{a.seed}"
    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)
    problem = {"id": prob_id, "title": f"OSPFv3 複合TS マルチエリア (seed={a.seed})",
               "exam": "ENARSI", "topics": ["ipv6", "ospfv3", "multi-area", "troubleshooting", "generated"],
               "difficulty": diff, "topology": "generated", "target_nodes": routers,
               "points": 100, "access": "ssh", "bringup_data_ifs": True,
               "lab": {"links": [{"a": lk["a"], "a_if": lk["a_if"], "b": lk["b"], "b_if": lk["b_if"]}
                                 for lk in links],
                       # CMLキャンバス座標(area0横列→area1でL字に折る。見た目のみ)
                       "positions": {R[rl]: list(xy) for rl, xy in {
                           "s": (-560, -260), "a": (-330, -260), "d": (-100, -260),
                           "e": (130, -120), "f": (360, 20)}.items()}}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_ospfv3_complex_ts.py) seed={a.seed}\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)
    for Rn in routers:
        with open(f"{pdir}/initial/{Rn}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(render(Rn)) + "\n")
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_ospfv3_complex_ts.py) seed={a.seed}\n")
        yaml.safe_dump({"problem": prob_id, "total_points": 100,
                        "defaults": {"genie_os": "iosxe"}, "checks": checks},
                       f, sort_keys=False, allow_unicode=True)
    with open(f"{pdir}/solution/fault.json", "w", encoding="utf-8") as f:
        json.dump({"count": len(faults), "faults": faults,
                   "roles": {role[r]: r for r in routers},
                   "styles": style_of}, f, ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/fix.json", "w", encoding="utf-8") as f:
        json.dump({"fixes": fixes}, f, ensure_ascii=False, indent=2)

    ledger = "\n".join(f"| {r} | `{lo[r]}/128` | {'area0' if lo_area_of[r]==area0 else 'area1'} |"
                       for r in routers)
    task = f"""# 問題 {prob_id} : OSPFv3(IPv6) 複合トラブルシュート（難易度{diff}）

## 状況
**IPv6 のみ**・OSPFv3 のマルチエリア網で到達性障害。全ルータが全 Loopback へ相互到達する状態へ復旧してください。

## トラブルチケット（代表症状・1件）
> **{rep[0]} から {rep[1]} の Loopback (`{lo[rep[1]]}`) へ到達できない。** 原因は1か所とは限りません。

## ルータ / Loopback 台帳
| ルータ | Loopback0 | エリア |
|--------|-----------|--------|
{ledger}

## 到達目標 / 切り分け
- 全ルータが全 Loopback を `show ipv6 route ospf` で学習し相互到達。
- トポロジ/エリア/故障の種類・場所・件数は非公開。OSPFv3 有効化は **従来方式(`ipv6 ospf`)と AF方式(`ospfv3`)が混在**。
  `show ipv6 ospf neighbor` / `show ipv6 ospf interface brief` / `show ipv6 route ospf` / `show running-config | section ospf` で切り分け。
- OSPFv3 の認証は **IPsec**（MD5 ではない）。router-id は IPv6-only では手動必須。設定変更が即時反映されない場合あり。

## アクセス・採点
SSH `SUZUKI / CCNP`（mgmt は割当順に 10.1.10.11〜）。
```
ansible-playbook playbooks/grade.yml -e problem={prob_id} --vault-password-file <(printf 'CCNP\\n')
```
"""
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(task)
    print(f"wrote problems/{prob_id} : faults={[f['type'] for f in faults]} styles={style_of}")


if __name__ == "__main__":
    main()
