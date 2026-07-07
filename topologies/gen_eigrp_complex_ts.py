#!/usr/bin/env python3
"""EIGRP 複合トラブルシュート生成器（named / classic / mixed）。

BUILD 問題 [[ccnp-eigrp-build-01]] の対になる TS 版。IPv4・単一 AS。
--style {named|classic|mixed}: named=全機named mode(既定・従来動作) / classic=全機従来
`router eigrp <AS>` / mixed=ルータ毎にseedランダム(両構文の読み分け＋wide/classicメトリック
interopを問う)。classicの認証はIF直下 `ip authentication mode eigrp <AS> md5` 系、
passive/K値/stub/networkはプロセス直下。SHA-256はnamed限定→auth_mode_mismatchの被疑は
named機のみに配置。
正準トポロジ(値 seed ランダム化): ダイヤモンド(s-a-d / s-b-d)=冗長 ＋ チェーン(d-e-f-g)。
役割 s/a/b/d/e/f/g を物理 RT01-07 に seed シャッフル。

■ 公平性: 冗長辺(ダイヤモンド4本)は単一故障が迂回で救済されるので故障を置かない。
  隣接系(LINK)故障は **クリティカル辺(d-e/e-f/f-g)** のみに配置（断で末端が孤立＝到達性で検出可）。
  全体系/スタブ系は下流を孤立させるチェーン内ノードに、宛先系は任意ノードに配置。

■ EIGRP 特有: hello/hold 不一致は隣接を壊さない(OSPFと違う)ので"壊す故障"に使わない。
  隣接を壊すのは K値/認証/passive/ACL遮断/network欠落/shutdown、下流孤立は stub-on-transit。

故障(--faults N, 非干渉に複数):
  authentication_mismatch(片側MD5) / passive_interface / shutdown / missing_network /
  acl_block_eigrp(ACLでEIGRP遮断) / k_values_mismatch(metric weights・全隣接断) /
  stub_on_transit(中継機をstub化→下流孤立/SIA) / missing_loopback_network(Loopback未広告)

採点: 全ペアで宛先 Loopback を `show ip route eigrp` に学習しているか(raw 正規表現・next-hop非依存)。

出力: problems/GEN-EIGRP-<seed>/ {problem.yml, initial/*.cfg.j2, grading.yml,
       solution/{fault.json,fix.json}, task.md}。fix.json は fix_generated.yml 互換。
使い方: gen_eigrp_complex_ts.py --repo . --seed <int> [--faults N]
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
STUB_ROLES = {"d", "e", "f"}          # 下流を持つ中継ノード（leaf g は無意味なので除外）
PROC = "CCNP"
AS = 100
KEY = "CCNPKEY"
KEY_BAD = "WRONGKEY"
SHA_PWD = "CCNPKEY"
KC = "KC"
ACL = "BLOCK-EIGRP"

FAULT_DIFFICULTY = {
    "missing_network": 3, "missing_loopback_network": 3, "shutdown": 3,
    "passive_interface": 4, "acl_block_eigrp": 4, "stub_on_transit": 4,
    "authentication_mismatch": 5, "k_values_mismatch": 5,
    "auth_key_mismatch": 5, "auth_mode_mismatch": 5,
}
# auth系3種: one-sided(片側のみMD5) / key不一致(両側MD5・key-string違い=configが対称に見える) /
# mode不一致(被疑側hmac-sha-256 vs 対向MD5・named mode限定機能)。後2者は両端IFを消費。
LINK_FAULTS = ["authentication_mismatch", "passive_interface", "shutdown",
               "missing_network", "acl_block_eigrp",
               "auth_key_mismatch", "auth_mode_mismatch"]
WHOLE_FAULTS = ["k_values_mismatch"]
STUB_FAULTS = ["stub_on_transit"]
DEST_FAULTS = ["missing_loopback_network"]


def netaddr(ip):
    return ip.rsplit(".", 1)[0] + ".0"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--faults", type=int, default=3)
    ap.add_argument("--style", choices=["named", "classic", "mixed"], default="named")
    a = ap.parse_args()
    if a.faults < 1:
        raise SystemExit("--faults は 1 以上")
    rnd = random.Random(a.seed)

    phys = [f"RT{i:02d}" for i in range(1, len(ROLES) + 1)]
    rnd.shuffle(phys)
    R = dict(zip(ROLES, phys))            # role -> RTxx
    role = {v: k for k, v in R.items()}   # RTxx -> role
    routers = [R[r] for r in ROLES]

    # 方式(ルータ単位)。named/classic は wide/classic メトリックだが相互運用可(隣接ごと交渉)。
    if a.style == "mixed":
        style_of = {r: rnd.choice(["named", "classic"]) for r in routers}
    else:
        style_of = {r: a.style for r in routers}

    # アドレッシング: Loopback 10.k.k.k/32 (k<100) / リンク 10.p.p.0/30 (p 101-199)
    used = set(); lo = {}
    for r in routers:
        while True:
            k = rnd.randint(1, 99)
            if k not in used:
                used.add(k); lo[r] = f"10.{k}.{k}.{k}"; break
    usedp = set(); pseg = {}
    for (ra, rb) in TOPO:
        while True:
            p = rnd.randint(101, 199)
            if p not in usedp:
                usedp.add(p); pseg[(ra, rb)] = f"10.{p}.{p}"; break

    # 物理リンク・IF 索引
    slot = {r: 0 for r in routers}; links = []
    for (ra, rb) in TOPO:
        x, y = R[ra], R[rb]
        seg = pseg[(ra, rb)]
        links.append({"a": x, "a_if": slot[x], "a_ip": f"{seg}.1",
                      "b": y, "b_if": slot[y], "b_ip": f"{seg}.2", "seg": seg})
        slot[x] += 1; slot[y] += 1
    ifaces = {r: [] for r in routers}     # (slot, my_ip, nb)
    for lk in links:
        ifaces[lk["a"]].append((lk["a_if"], lk["a_ip"], lk["b"]))
        ifaces[lk["b"]].append((lk["b_if"], lk["b_ip"], lk["a"]))

    crit_phys = {frozenset({R[x], R[y]}) for e in CRIT_ROLE_EDGES for (x, y) in [tuple(e)]}

    def peer_slot(node, nb):
        for (s, ip, n) in ifaces[nb]:
            if n == node:
                return s
        raise KeyError

    # ---- 故障選択（非干渉・auth両側系は両端IFを消費）----
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
            if ft == "authentication_mismatch":
                auth_of[(fr, s)] = "md5_good"
            elif ft == "auth_key_mismatch":
                auth_of[(fr, s)] = "md5_bad"; auth_of[(nb, ps)] = "md5_good"
                used_if.add((nb, ps))
            elif ft == "auth_mode_mismatch":
                auth_of[(fr, s)] = "sha256"; auth_of[(nb, ps)] = "md5_good"
                used_if.add((nb, ps))
            faults.append({"type": ft, "node": fr, "slot": s, "neighbor": nb,
                           "iol_if": f"Ethernet0/{s}", "seg": netaddr(ip),
                           "style": style_of[fr], "difficulty": FAULT_DIFFICULTY[ft]})
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
        else:  # missing_loopback_network
            fr = rnd.choice(routers)
            if fr in used_node:
                continue
            used_node.add(fr)
            faults.append({"type": ft, "node": fr, "style": style_of[fr],
                           "difficulty": FAULT_DIFFICULTY[ft]})
    if not faults:
        raise SystemExit("故障を配置できなかった")

    iff = {(f["node"], f["slot"]): f["type"] for f in faults if "slot" in f}
    missing_net = {(f["node"], f["slot"]) for f in faults if f["type"] == "missing_network"}
    noloop = {f["node"] for f in faults if f["type"] == "missing_loopback_network"}
    kval_nodes = {f["node"] for f in faults if f["type"] == "k_values_mismatch"}
    stub_nodes = {f["node"] for f in faults if f["type"] == "stub_on_transit"}

    # ---- 到達性(症状・代表ペア) ----
    # LINK/k値(全体)故障は隣接そのものを壊す→辺を除去。
    # stub_on_transit は隣接は張れるが EIGRP 学習経路を再広告しない＝「中継不可」。
    #   ∴ stub ノードは経路の"通過点"になれないが、自分の connected(Loopback) は隣接へ広告する。
    #   → dest_set(T): T の Loopback を学習できるノード集合 = T から辿れて、途中の中間ノードが
    #     すべて非stub な経路が存在するノード（端点が stub でも受信・保持は可）。
    broken = set()
    for f in faults:
        if f["type"] in LINK_FAULTS:
            broken.add(frozenset({f["node"], f["neighbor"]}))
        elif f["type"] in WHOLE_FAULTS:      # k_values: K不一致で全隣接断
            for (s, ip, nb) in ifaces[f["node"]]:
                broken.add(frozenset({f["node"], nb}))
    stubs = {f["node"] for f in faults if f["type"] in STUB_FAULTS}
    adj = {r: set() for r in routers}
    for lk in links:
        if frozenset({lk["a"], lk["b"]}) not in broken:
            adj[lk["a"]].add(lk["b"]); adj[lk["b"]].add(lk["a"])

    def dest_set(T):
        if T in noloop:                      # Loopback 未広告→誰も学習できない
            return set()
        seen = {T}; stk = [T]
        while stk:
            x = stk.pop()
            if x != T and x in stubs:        # stub 中間ノードは再広告しない＝先へ伝播不可
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
    def render(Rn):
        st = style_of[Rn]
        L = [f"! {Rn} (role={role[Rn]}, eigrp={st}) 初期構成 (AS {AS})"]
        # key chain: MD5系を持つノード＋SHA-256被疑ノード(修復でMD5へ揃える用)に配布。
        # key-string は md5_bad ノードのみ誤値(=configが対称に見える罠)。
        need_kc = any(auth_of.get((Rn, s)) in ("md5_good", "md5_bad", "sha256")
                      for (s, ip, nb) in ifaces[Rn])
        key = KEY_BAD if any(auth_of.get((Rn, s)) == "md5_bad" for (s, ip, nb) in ifaces[Rn]) \
            else KEY
        if need_kc:
            L += ["key chain " + KC, " key 1", f"  key-string {key}", "!"]
        if any(iff.get((Rn, s)) == "acl_block_eigrp" for (s, ip, nb) in ifaces[Rn]):
            L += [f"ip access-list extended {ACL}", " deny eigrp any any",
                  " permit ip any any", "!"]
        L += ["interface Loopback0", f" ip address {lo[Rn]} 255.255.255.255", "!"]
        for (s, ip, nb) in sorted(ifaces[Rn]):
            ft = iff.get((Rn, s))
            ak = auth_of.get((Rn, s))
            L += [f"interface {{{{ links[{s}] }}}}", f" ip address {ip} 255.255.255.252"]
            if ft == "acl_block_eigrp":
                L.append(f" ip access-group {ACL} in")
            if st == "classic" and ak in ("md5_good", "md5_bad"):
                L += [f" ip authentication mode eigrp {AS} md5",
                      f" ip authentication key-chain eigrp {AS} {KC}"]
            L.append(" shutdown" if ft == "shutdown" else " no shutdown")
            L.append("!")
        # network 文（named/classic 共通ロジック）
        nets = []
        if Rn not in noloop:
            nets.append(f"network {lo[Rn]} 0.0.0.0")
        for (s, ip, nb) in sorted(ifaces[Rn]):
            if (Rn, s) in missing_net:
                continue
            nets.append(f"network {netaddr(ip)} 0.0.0.3")
        if st == "classic":
            L += [f"router eigrp {AS}", f" eigrp router-id {lo[Rn]}"]
            if Rn in kval_nodes:
                L.append(" metric weights 0 2 0 1 0 0")
            if Rn in stub_nodes:
                L.append(" eigrp stub connected")
            L.append(" passive-interface Loopback0")
            for (s, ip, nb) in sorted(ifaces[Rn]):
                if iff.get((Rn, s)) == "passive_interface":
                    L.append(f" passive-interface {{{{ links[{s}] }}}}")
            L += [f" {nl}" for nl in nets]
            L.append("!")
        else:
            L += [f"router eigrp {PROC}",
                  f" address-family ipv4 unicast autonomous-system {AS}"]
            if Rn in kval_nodes:
                L.append("  metric weights 0 2 0 1 0 0")
            if Rn in stub_nodes:
                L.append("  eigrp stub connected")
            L += ["  af-interface Loopback0", "   passive-interface", "  exit-af-interface"]
            for (s, ip, nb) in sorted(ifaces[Rn]):
                ft = iff.get((Rn, s))
                ak = auth_of.get((Rn, s))
                blk = [f"  af-interface {{{{ links[{s}] }}}}"]
                if ft == "passive_interface":
                    blk.append("   passive-interface")
                if ak in ("md5_good", "md5_bad"):
                    blk += ["   authentication mode md5", f"   authentication key-chain {KC}"]
                elif ak == "sha256":
                    blk.append(f"   authentication mode hmac-sha-256 {SHA_PWD}")
                blk.append("  exit-af-interface")
                if len(blk) > 2:
                    L += blk
            L.append(f"  eigrp router-id {lo[Rn]}")
            L += [f"  {nl}" for nl in nets]
            L += [" exit-address-family", "!"]
        return L

    # ---- fix ----
    def af_parents(Rn, sub=None):
        p = [f"router eigrp {PROC}", f"address-family ipv4 unicast autonomous-system {AS}"]
        if sub:
            p.append(sub)
        return p

    def proc_parents(Rn):
        """プロセス直下(スタイル別): classic=router eigrp <AS> / named=AF 直下。"""
        if style_of[Rn] == "classic":
            return f"router eigrp {AS}"
        return af_parents(Rn)

    def fault_fix(f):
        ft, Rn = f["type"], f["node"]
        st = style_of[Rn]
        iol = f.get("iol_if")
        if ft == "shutdown":
            return [{"node": Rn, "parents": f"interface {iol}", "lines": ["no shutdown"]}]
        if ft == "acl_block_eigrp":
            return [{"node": Rn, "parents": f"interface {iol}",
                     "lines": [f"no ip access-group {ACL} in"]}]
        if ft == "passive_interface":
            if st == "classic":
                return [{"node": Rn, "parents": f"router eigrp {AS}",
                         "lines": [f"no passive-interface {iol}"]}]
            return [{"node": Rn, "parents": af_parents(Rn, f"af-interface {iol}"),
                     "lines": ["no passive-interface"]}]
        if ft == "authentication_mismatch":
            if st == "classic":
                return [{"node": Rn, "parents": f"interface {iol}",
                         "lines": [f"no ip authentication mode eigrp {AS} md5",
                                   f"no ip authentication key-chain eigrp {AS} {KC}"]}]
            return [{"node": Rn, "parents": af_parents(Rn, f"af-interface {iol}"),
                     "lines": ["no authentication mode md5",
                               f"no authentication key-chain {KC}"]}]
        if ft == "auth_key_mismatch":
            return [{"node": Rn, "parents": [f"key chain {KC}", "key 1"],
                     "lines": [f"key-string {KEY}"]}]
        if ft == "auth_mode_mismatch":   # 被疑は named 限定(選択時に保証)
            return [{"node": Rn, "parents": af_parents(Rn, f"af-interface {iol}"),
                     "lines": [f"no authentication mode hmac-sha-256 {SHA_PWD}",
                               "authentication mode md5",
                               f"authentication key-chain {KC}"]}]
        if ft == "missing_network":
            return [{"node": Rn, "parents": proc_parents(Rn),
                     "lines": [f"network {f['seg']} 0.0.0.3"]}]
        if ft == "k_values_mismatch":
            if st == "classic":
                return [{"node": Rn, "parents": f"router eigrp {AS}",
                         "lines": ["no metric weights"]}]
            return [{"node": Rn, "parents": af_parents(Rn),
                     "lines": ["metric weights 0 1 0 1 0 0"]}]
        if ft == "stub_on_transit":
            return [{"node": Rn, "parents": proc_parents(Rn), "lines": ["no eigrp stub"]}]
        # missing_loopback_network
        return [{"node": Rn, "parents": proc_parents(Rn),
                 "lines": [f"network {lo[Rn]} 0.0.0.0"]}]

    fixes = [fx for f in faults for fx in fault_fix(f)]

    # ---- 採点(全ペア・宛先 Loopback 学習 raw) ----
    pairs = [(x, y) for x in routers for y in routers if x != y]
    n = len(pairs); base = 100 // n; rem = 100 - base * n
    checks = []
    for i, (x, y) in enumerate(pairs):
        pts = base + (1 if i < rem else 0)
        checks.append({"name": f"{x}: {lo[y]}/32 を EIGRP で学習(到達)",
                       "node": x, "command": "show ip route eigrp",
                       "raw": [{"regex": lo[y].replace(".", r"\.") + r"/32"}], "points": pts})

    diff = min(5, max(f["difficulty"] for f in faults) + (1 if len(faults) > 1 else 0))
    prob_id = f"GEN-EIGRP-{a.seed}"
    pdir = f"{a.repo}/problems/{prob_id}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)
    problem = {"id": prob_id, "title": f"EIGRP 複合TS style={a.style} (seed={a.seed})",
               "exam": "ENARSI", "topics": ["eigrp", "igp", "troubleshooting", "generated"],
               "difficulty": diff, "topology": "generated", "target_nodes": routers,
               "points": 100, "access": "ssh",
               "lab": {"links": [{"a": lk["a"], "a_if": lk["a_if"], "b": lk["b"], "b_if": lk["b_if"]}
                                 for lk in links],
                       # CMLキャンバス座標(役割ベースの正準配置=ダイヤモンド＋チェーン。見た目のみ)
                       "positions": {R[rl]: list(xy) for rl, xy in {
                           "s": (-500, -360), "a": (-700, -180), "b": (-300, -180),
                           "d": (-500, 0), "e": (-240, 0), "f": (20, 0),
                           "g": (280, 0)}.items()}}}
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_eigrp_complex_ts.py) seed={a.seed}\n")
        yaml.safe_dump(problem, f, sort_keys=False, allow_unicode=True)
    for Rn in routers:
        with open(f"{pdir}/initial/{Rn}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("\n".join(render(Rn)) + "\n")
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_eigrp_complex_ts.py) seed={a.seed}\n")
        yaml.safe_dump({"problem": prob_id, "total_points": 100,
                        "defaults": {"genie_os": "iosxe"}, "checks": checks},
                       f, sort_keys=False, allow_unicode=True)
    with open(f"{pdir}/solution/fault.json", "w", encoding="utf-8") as f:
        json.dump({"count": len(faults), "faults": faults,
                   "roles": {role[r]: r for r in routers},
                   "styles": style_of}, f, ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/fix.json", "w", encoding="utf-8") as f:
        json.dump({"fixes": fixes}, f, ensure_ascii=False, indent=2)

    # mgmt は build_topology が target_nodes(=routers) 順に 10.1.10.11 から割当てる＝この表の行順。
    mixed = len(set(style_of.values())) > 1
    if mixed:
        ledger = "\n".join(f"| {r} | `{lo[r]}/32` | {style_of[r]} | 10.1.10.{11 + i} |"
                           for i, r in enumerate(routers))
        lhead = "| ルータ | Loopback0 | 方式 | mgmt(SSH) |\n|--------|-----------|------|-----------|"
        mode_ja = "**classic（`router eigrp <AS>`）と named（`router eigrp " + PROC + \
                  "` + address-family）がルータ毎に混在**"
    else:
        ledger = "\n".join(f"| {r} | `{lo[r]}/32` | 10.1.10.{11 + i} |"
                           for i, r in enumerate(routers))
        lhead = "| ルータ | Loopback0 | mgmt(SSH) |\n|--------|-----------|-----------|"
        only = list(set(style_of.values()))[0]
        mode_ja = ("全機 **named mode**（`router eigrp " + PROC +
                   "` / `address-family ipv4 unicast autonomous-system " + str(AS) + "`）"
                   if only == "named" else f"全機 **classic**（`router eigrp {AS}`）")
    task = f"""# 問題 {prob_id} : EIGRP 複合トラブルシュート（難易度{diff}）

## 状況
単一 AS **{AS}** の EIGRP 網（IPv4）で到達性障害。全ルータが全 Loopback へ
相互到達する状態へ復旧してください。

## トラブルチケット（代表症状・1件）
> **{rep[0]} から {rep[1]} の Loopback (`{lo[rep[1]]}`) へ到達できない。** 原因は1か所とは限りません。

## ルータ / Loopback 台帳（mgmt は割当順）
{lhead}
{ledger}

## 到達目標 / 切り分け
- 全ルータが全 Loopback を `show ip route eigrp` で学習し相互到達。
- トポロジ・故障の種類・場所・件数は非公開。有効化方式: {mode_ja}。
- 切り分け: `show ip eigrp neighbors` / `show ip eigrp interfaces` / `show ip protocols` /
  `show ip route eigrp` / `show running-config | section eigrp`。
- ヒント（EIGRP の勘所）: **hello/hold の不一致では隣接は落ちない**。隣接不形成は
  K値・認証・passive・ACL・network 欠落など。設定変更後に隣接が戻らない時は
  `clear ip eigrp neighbors`。中継機が **stub** だと下流が丸ごと落ちる。

## アクセス・採点
SSH `SUZUKI / CCNP`（mgmt は割当順に 10.1.10.11〜）。
```
ansible-playbook playbooks/grade.yml -e problem={prob_id} --vault-password-file <(printf 'CCNP\\n')
```
"""
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(task)
    print(f"wrote problems/{prob_id} : faults={[f['type'] for f in faults]} "
          f"roles={{{', '.join(f'{k}:{R[k]}' for k in ROLES)}}} styles={style_of}")


if __name__ == "__main__":
    main()
