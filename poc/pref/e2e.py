#!/usr/bin/env python3
"""BL-127 E2E: 紙面盤面(shape=pref)の実機照合。

紙面の盤面を `_POC-PREF` に流し込み、**レンダラの出力と実機の show を行単位で
照合**する(copp の E5 と同じ手法)。検証したいのは次の 3 点:

  A. メトリックの算術  — FD/RD・E1 の累積・E2 の forward metric が実機と一致
  B. 書式             — 行の構成・語順・句の有無(★E2 にしか出ない forward metric)
  C. 見える経路の集合  — スプリット・ホライズンの窓(check_board)が正しいか
                         / `show ip eigrp topology` が successor と FS しか出さないか

照合は **volatile な欄(LS age・Seq・Checksum・uptime・serno・refcount・SPF 番号・
U フラグ)をマスク**した上での完全一致。next-hop は盤面とラボでアドレス体系が
違うので、盤面→ラボの置換表を作ってからレンダラ側に適用する
(★数値・語句は一切いじらない= 算術と書式は素で一致しなければ NG)。

盤面とラボの対応:
  EIGRP  観測点 RE1 / 経路 i → RE2(e0/0) RE3(e0/1) RE4(e0/2) RE6(e0/3)
         宛先= RE5 の Lo99(10.99.9.0/24)。delay は盤面の near/far をそのまま投入。
  OSPF   観測点 RO1 / 経路 0 → RO2(e0/0) 経路 1 → RO3(e0/1)
         ★RO3 は E2E 中だけ area 2 を外して **ASBR 専任**にする
         (ABR 兼務だと border-routers の役割欄が変わり、盤面と別物になる)。
         RO5 は再配送を止めて ASBR から降ろす。

使い方: e2e.py [ケース名...] (無指定=全部)。結果は e2e-raw.md へ追記。
"""
import re
import sys
import time
from pathlib import Path

import urllib3

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "topologies"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import gen_paper_pref as gpr     # noqa: E402
import probe as P                # noqa: E402  (ensure_lab/connect_all/conf/sh)
from virl2_client import ClientLibrary  # noqa: E402

urllib3.disable_warnings()

OUT = Path(__file__).resolve().parent / "e2e-raw.md"
LAB_PFX = "10.99.9.0"
E_NBR = ["RE2", "RE3", "RE4", "RE6"]          # 盤面の経路 i に対応するノード
E_FAR = "Ethernet0/1"                         # 各隣接の「宛先の側」の IF
O_NBR = ["RO2", "RO3"]

# ケース: (名前, kind, 盤面探索の開始 seed)
CASES = [
    ("e_fc_strict", "fc_strict", 700),
    ("e_variance_bound", "variance_bound", 710),
    ("e_variance_nonfc", "variance_nonfc", 720),
    ("e_fs_allthat", "fs_allthat", 730),
    ("o_type_e1e2", "type_e1e2", 740),
    ("o_e2_fwd", "e2_fwd", 750),
    ("o_e1_accum", "e1_accum", 760),
]

# volatile(盤面の正しさと無関係に毎回変わる欄)= 両側で伏せる
MASKS = [
    (r"LS age: \d+", "LS age: <n>"),
    (r"LS Seq Number: \S+", "LS Seq Number: <n>"),
    (r"Checksum: \S+", "Checksum: <n>"),
    (r"\d\d:\d\d:\d\d ago", "<uptime> ago"),
    (r", serno \d+", ""),
    (r", refcount \d+", ""),
    (r", anchored", ""),
    (r", U\b", ""),
    (r"SPF \d+", "SPF <n>"),
]


def norm(text, subs=None):
    for pat, rep in MASKS:
        text = re.sub(pat, rep, text)
    for a, b in (subs or {}).items():
        text = text.replace(a, b)
    return "\n".join(ln.rstrip() for ln in text.strip().splitlines())


def pick(kind, seed0):
    import random
    for k in range(600):
        try:
            return gpr.draw(random.Random(seed0 + k * 17), kind=kind)
        except ValueError:
            continue
    raise RuntimeError(f"{kind}: 盤面が引けない")


def topo_block(text, pfx):
    m = re.search(rf"^P {re.escape(pfx)}/24,.*?(?=^P |\Z)", text, re.M | re.S)
    return m.group(0).rstrip() if m else "(該当プレフィックスの行が無い)"


# ------------------------------------------------------------------ EIGRP
def e_setup(devs, d):
    """盤面の delay をラボへ投入。使わない経路は shut して盤面と本数を合わせる。"""
    n = len(d["paths"])
    P.conf(devs["RE1"], [f"router eigrp 100", " no variance", " exit"])
    for i, p in enumerate(d["paths"]):
        P.conf(devs["RE1"], [f"interface Ethernet0/{i}", f" delay {p['near']}",
                             " no shutdown", "exit"])
        P.conf(devs[E_NBR[i]], [f"interface {E_FAR}", f" delay {p['far']}",
                                " no shutdown", "exit"])
    for j in range(n, 4):
        P.conf(devs["RE1"], [f"interface Ethernet0/{j}", " shutdown", "exit"])


def e_subs(d):
    s = {}
    for i, p in enumerate(d["paths"]):
        s[p["nh"]] = {0: "10.20.12.2", 1: "10.20.13.3",
                      2: "10.20.14.4", 3: "10.20.16.6"}[i]
    s[d["pfx"]] = LAB_PFX
    s[f"AS({d['asn']})"] = "AS(100)"
    s[f"ID({d['obs_rid']})"] = "ID(11.11.11.11)"
    return s


def stable_block(dev, cmd, pfx, tries=12, every=15):
    """出力が 2 回連続で同じになるまで待ってから返す。

    ★初回 E2E の失敗録: 経路の**本数**だけで収束を判定すると、メトリックが
    まだ流れている途中(前ケースの RD が残っている)の表を採ってしまう。
    """
    prev = None
    for _ in range(tries):
        cur = topo_block(P.sh(dev, cmd), pfx)
        if cur == prev:
            return cur
        prev = cur
        time.sleep(every)
    return prev


def e_case(devs, d, log):
    e_setup(devs, d)
    dev = devs["RE1"]
    want = len(d["paths"])
    # ★FD は「前回 Active になってから既知の最小距離」なので、delay を上げた
    #   だけだと**古い(小さい)FD が居座る**(初回 E2E で実測)。紙面の盤面は
    #   「素で収束した網」の写しなので、隣接を張り直して再計算させる。
    P.sh(dev, "clear ip eigrp 100 neighbors")
    time.sleep(25)
    took = P.wait(lambda: P.n_links(dev, LAB_PFX) == want, timeout=300,
                  label=f"{want} 経路の収束")
    subs = e_subs(d)
    ng = 0
    # ① all-links(variance 適用前)= 盤面のレンダラと完全一致するか
    real = stable_block(dev, "show ip eigrp topology all-links", LAB_PFX)
    paper = topo_block(gpr.eigrp_topology(d, all_links=True), d["pfx"])
    ng += cmp_block(log, "all-links", norm(paper, subs), norm(real))
    # ② successor と FS しか出ない(非 FC は消える)
    real2 = stable_block(dev, "show ip eigrp topology", LAB_PFX)
    paper2 = topo_block(gpr.eigrp_topology(d, all_links=False), d["pfx"])
    ng += cmp_block(log, "topology(既定)", norm(paper2, subs), norm(real2))
    # ③ variance 適用後に RIB へ載る本数・経路
    P.conf(dev, ["router eigrp 100", f" variance {d['variance']}", "exit"])
    time.sleep(20)
    rt = P.sh(dev, f"show ip route {LAB_PFX}")
    got = set(re.findall(r"(?:\* )?(\d+\.\d+\.\d+\.\d+), from", rt))
    exp = {subs[k.split()[-1]] for k in d["_installed"]}
    ok = got == exp
    log.append(f"- ③ variance {d['variance']} 適用後の搭載= 実機 {sorted(got)} / "
               f"モデル {sorted(exp)} → {'一致' if ok else '★不一致'}")
    P.conf(dev, ["router eigrp 100", " no variance", "exit"])
    return ng + (0 if ok else 1), took


# ------------------------------------------------------------------- OSPF
def o_setup(devs, d):
    """盤面の外部メトリック・型・観測点コストをラボへ投入。"""
    # RO3 を ASBR 専任にする(ABR 兼務だと border-routers の役割欄が変わる)
    P.conf(devs["RO3"], ["router ospf 1", " no network 10.10.34.0 0.0.0.255 area 2",
                         " exit", "interface Ethernet0/1", " shutdown", "exit"])
    # ★iol-xe 17.15 は running-config で `subnets` を暗黙化するため、
    #   完全形の `no redistribute static subnets route-map ...` は当たらない
    #   (初回 E2E で RO5 が ASBR のまま残った)。オプション無しで消す。
    P.conf(devs["RO5"], ["router ospf 1", " no redistribute static", " exit"])
    pfx = d["pfx"]
    for i, p in enumerate(d["paths"]):
        node = O_NBR[i]
        mt = 1 if p["kind"] in ("e1", "n1") else 2
        P.conf(devs[node], [
            f"ip route {pfx} 255.255.255.0 Null0",
            f"ip prefix-list PLE2E permit {pfx}/24",
            "route-map RM-E2E permit 10",
            " match ip address prefix-list PLE2E",
            f" set metric {p['ext']}", f" set metric-type type-{mt}", "exit",
            "router ospf 1",
            " redistribute static subnets route-map RM-E2E", " exit"])
        P.conf(devs["RO1"], [f"interface Ethernet0/{i}",
                             f" ip ospf cost {p['nbr']['cost']}", "exit"])


def o_teardown(devs, d):
    for i in range(len(d["paths"])):
        P.conf(devs[O_NBR[i]], [
            "router ospf 1", " no redistribute static", " exit",
            f"no ip route {d['pfx']} 255.255.255.0 Null0",
            "no route-map RM-E2E", f"no ip prefix-list PLE2E"])


def o_subs(d):
    s = {}
    for i, p in enumerate(d["paths"]):
        s[p["nbr"]["nh"]] = {0: "10.10.12.2", 1: "10.10.13.3"}[i]
    return s


def o_case(devs, d, log):
    o_setup(devs, d)
    dev = devs["RO1"]
    pfx = d["pfx"]
    took = P.wait(lambda: P.route_seen(dev, pfx), timeout=240,
                  label="外部経路の搭載")
    time.sleep(10)
    subs = o_subs(d)
    ng = 0
    # ① detail 1 行目(型の句・forward metric の有無)+ メトリック
    real = P.sh(dev, f"show ip route {pfx}")
    m = re.search(r'  Known via "ospf 1".*', real)
    win = [p for p in d["paths"] if p["key"] == d["_winner"]][0]
    exp_metric = gpr.opm.metric_eff(win)
    exp_line = (f'  Known via "ospf 1", distance 110, metric {exp_metric}, '
                + ("type extern 1" if win["kind"] == "e1"
                   else f"type extern 2, forward metric {win['fwd']}"))
    got_line = m.group(0).rstrip() if m else "(該当行なし)"
    ok1 = got_line == exp_line
    log.append(f"- ① detail 行\n  - モデル: `{exp_line}`\n"
               f"  - 実機　: `{got_line}`\n  → {'一致' if ok1 else '★不一致'}")
    ng += 0 if ok1 else 1
    # ② 勝者(next-hop)がモデルどおりか
    nh = re.search(r"\* (\d+\.\d+\.\d+\.\d+), from", real)
    exp_nh = subs[win["nbr"]["nh"]]
    ok2 = bool(nh) and nh.group(1) == exp_nh
    log.append(f"- ② 勝者の next-hop= 実機 {nh.group(1) if nh else '?'} / "
               f"モデル {exp_nh} → {'一致' if ok2 else '★不一致'}")
    ng += 0 if ok2 else 1
    # ③ 外部 LSA の断片(Metric Type の注釈まで)
    real3 = P.sh(dev, f"show ip ospf database external {pfx}")
    paper3 = gpr.ospf_db_external(d)
    def fields(t):
        return [ln.strip() for ln in t.splitlines()
                if ln.strip().startswith(("Metric Type:", "Metric:",
                                          "Advertising Router:",
                                          "Forward Address:",
                                          "External Route Tag:"))]
    ok3 = fields(paper3) == fields(real3)
    log.append(f"- ③ 外部 LSA の主要欄 → {'一致' if ok3 else '★不一致'}")
    if not ok3:
        P.block(log, "  モデル", "\n".join(fields(paper3)))
        P.block(log, "  実機", "\n".join(fields(real3)))
    ng += 0 if ok3 else 1
    # ④ border-routers(ASBR までの内部コスト)
    real4 = P.sh(dev, "show ip ospf border-routers")
    paper4 = gpr.ospf_border_routers(d)
    def brl(t):
        return sorted(ln.strip() for ln in t.splitlines()
                      if ln.strip().startswith("i "))
    ok4 = brl(norm(paper4, subs)) == brl(norm(real4))
    log.append(f"- ④ border-routers 行 → {'一致' if ok4 else '★不一致'}")
    if not ok4:
        P.block(log, "  モデル", "\n".join(brl(norm(paper4, subs))))
        P.block(log, "  実機", "\n".join(brl(norm(real4))))
    ng += 0 if ok4 else 1
    o_teardown(devs, d)
    return ng, took


def cmp_block(log, title, paper, real):
    if paper == real:
        log.append(f"- ① {title} → **一致**")
        return 0
    log.append(f"- ① {title} → ★**不一致**")
    P.block(log, "  モデル(紙面レンダラ)", paper)
    P.block(log, "  実機", real)
    return 1


def main():
    want = [a for a in sys.argv[1:]] or [c[0] for c in CASES]
    client = ClientLibrary(P.CML[0], P.CML[1], P.CML[2], ssl_verify=False)
    lab = P.ensure_lab(client)
    print("[i] console 接続...")
    # ★OSPF ケースは RO1〜RO3・RO5 が揃っていないと成立しない(2 回目の実行で
    #   RO3 の console が落ち、KeyError で 3 ケースが不成立になった)。必須指定する。
    need = ["RE1", "RO1"] + (["RO2", "RO3", "RO5"]
                             if any(c[0].startswith("o_") for c in CASES
                                    if c[0] in want) else [])
    devs = P.connect_all(lab, required=tuple(need))
    P.push_base(devs)
    log = [f"\n\n# E2E 実行 {time.strftime('%Y-%m-%d %H:%M:%S')} — cases={want}"]
    total_ng = 0
    for name, kind, seed0 in CASES:
        if name not in want:
            continue
        print(f"[i] === {name} ===")
        d = pick(kind, seed0)
        log.append(f"\n## {name} (kind={kind} world={d['world']})")
        try:
            ng, took = (e_case if d["fam"] == "eigrp" else o_case)(devs, d, log)
        except Exception as e:
            log.append(f"- **失敗**: {type(e).__name__}: {e}")
            print(f"    [!] {type(e).__name__}: {e}")
            ng = 1
        total_ng += ng
        print(f"    NG={ng}")
        OUT.write_text((OUT.read_text() if OUT.exists() else "")
                       + "\n".join(log) + "\n")
        log = []
    print(f"[i] 合計 NG={total_ng} / 結果: {OUT}")
    return 1 if total_ng else 0


if __name__ == "__main__":
    raise SystemExit(main())
