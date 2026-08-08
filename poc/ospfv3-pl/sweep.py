#!/usr/bin/env python3
"""BL-097 PoC: OSPFv3 マルチエリア prefix-list フィルタ挙動スイープ。

CML に POC-OSPFV3PL(IOL 4台・3エリア)を作成し、コンソール直駆動で
R2(ABR) 等の設定を組み替えながら R1/R3/Ra の経路表を観測する。
mgmt/SSH は使わない(day0 は hostname のみ・CVAC 罠回避)。

トポロジ:
  R1(Area10) --e0/0---e0/0-- R2(ABR) --e0/1---e0/0-- Ra(Area0, Lo9/A/B/C)
                              +--e0/2---e0/0-- R3(Area20)
  R1 e0/0 はセカンダリ 2001:DB8:2:2::/64 持ち(intra-area 免疫素材)。

観測軸: E1=filter-list in/out 方向意味論(第3エリアで非等価) E2=distribute-list の効く層
E3=area range not-advertise E4=intra-area 免疫 E5=ge/le 構文受理 E6=変更の自動伝播(clear要否)
E7=/46・/47 中間マスク被覆と ::/0 単体。

使い方: sweep.py [シナリオ名...]   (無指定=全部)。結果は results-raw.md へ追記。
"""
import sys
import time
from pathlib import Path

import urllib3
import yaml
from virl2_client import ClientLibrary
from pyats.topology import loader

urllib3.disable_warnings()

OUT = Path(__file__).resolve().parent / "results-raw.md"
CML = ("https://10.1.10.10", "SUZUKI", "suzugross")
LAB_TITLE = "POC-OSPFV3PL"
NODES = ["R1", "R2", "R3", "Ra"]
POLL_SEC, POLL_MAX = 3, 75

BASE = {
    "R1": [
        "ipv6 unicast-routing",
        "interface Ethernet0/0", "no shutdown", "ipv6 enable",
        "ipv6 address 2001:DB8:1:1::1/64",
        "ipv6 address 2001:DB8:2:2::1/64",
        "ipv6 ospf 10 area 10", "exit",
        "router ospfv3 10", "router-id 1.1.1.1",
        "address-family ipv6 unicast", "exit-address-family",
    ],
    "R2": [
        "ipv6 unicast-routing",
        "interface Ethernet0/0", "no shutdown", "ipv6 enable",
        "ipv6 address 2001:DB8:1:1::2/64", "ipv6 ospf 10 area 10", "exit",
        "interface Ethernet0/1", "no shutdown", "ipv6 enable",
        "ipv6 address 2001:DB8:0:A::2/64", "ipv6 ospf 10 area 0", "exit",
        "interface Ethernet0/2", "no shutdown", "ipv6 enable",
        "ipv6 address 2001:DB8:3:3::2/64", "ipv6 ospf 10 area 20", "exit",
        "router ospfv3 10", "router-id 2.2.2.2",
        "address-family ipv6 unicast", "exit-address-family",
    ],
    "R3": [
        "ipv6 unicast-routing",
        "interface Ethernet0/0", "no shutdown", "ipv6 enable",
        "ipv6 address 2001:DB8:3:3::3/64", "ipv6 ospf 10 area 20", "exit",
        "router ospfv3 10", "router-id 3.3.3.3",
        "address-family ipv6 unicast", "exit-address-family",
    ],
    "Ra": [
        "ipv6 unicast-routing",
        "interface Ethernet0/0", "no shutdown", "ipv6 enable",
        "ipv6 address 2001:DB8:0:A::A/64", "ipv6 ospf 10 area 0", "exit",
    ] + sum([[f"interface Loopback{n}", "ipv6 enable",
              f"ipv6 address 2001:DB8:{h}:{h}::1/64",
              "ipv6 ospf network point-to-point",
              "ipv6 ospf 10 area 0", "exit"]
             for n, h in [(9, "9"), (10, "A"), (11, "B"), (12, "C")]], [])
    + ["router ospfv3 10", "router-id 10.10.10.10",
       "address-family ipv6 unicast", "exit-address-family"],
}

AF = ["router ospfv3 10", "address-family ipv6 unicast"]
AF_END = ["exit-address-family", "exit"]


def deny_one_permit_all(name, prefix):
    return [f"ipv6 prefix-list {name} seq 5 deny {prefix}",
            f"ipv6 prefix-list {name} seq 10 permit ::/0 le 128"]


# ---- シナリオ: (適用ノード, apply, revert, 予告predicate(R1固定), 追観測) ----
# predicate は R1 の `show ipv6 route ospf` 出力に対する期待(効果発現の検知に使用)。
def scenarios():
    has = lambda s: (lambda out: s in out)
    lacks = lambda s: (lambda out: s not in out)
    return {
        # E1a: area 0 out で C:C 遮断 → R1・R3 両方から消えるはず
        "E1a_area0_out_denyC": dict(
            node="R2",
            apply=deny_one_permit_all("PL_E1", "2001:DB8:C:C::/64")
            + AF + ["area 0 filter-list prefix PL_E1 out"] + AF_END,
            revert=AF + ["no area 0 filter-list prefix PL_E1 out"] + AF_END
            + ["no ipv6 prefix-list PL_E1"],
            pred=lacks("2001:DB8:C:C::/64"),
            observe={"R3": ["show ipv6 route ospf"],
                     "R2": ["show ipv6 route ospf"]}),
        # E1b: 同じリストを area 10 in へ → R1 だけ消え R3 は残るはず(非等価の証明)
        "E1b_area10_in_denyC": dict(
            node="R2",
            apply=deny_one_permit_all("PL_E1", "2001:DB8:C:C::/64")
            + AF + ["area 10 filter-list prefix PL_E1 in"] + AF_END,
            revert=AF + ["no area 10 filter-list prefix PL_E1 in"] + AF_END
            + ["no ipv6 prefix-list PL_E1"],
            pred=lacks("2001:DB8:C:C::/64"),
            observe={"R3": ["show ipv6 route ospf"]}),
        # E4: area 10 out で R1 セカンダリ 2:2 を遮断 → Ra/R3 から消え、
        #     R2 自身の RIB では intra-area O のまま残るはず(免疫)
        "E4_area10_out_deny22": dict(
            node="R2",
            apply=deny_one_permit_all("PL_E4", "2001:DB8:2:2::/64")
            + AF + ["area 10 filter-list prefix PL_E4 out"] + AF_END,
            revert=AF + ["no area 10 filter-list prefix PL_E4 out"] + AF_END
            + ["no ipv6 prefix-list PL_E4"],
            pred=has("2001:DB8:C:C::/64"),  # R1 は変化しない(基線のまま)
            settle=20,
            observe={"Ra": ["show ipv6 route ospf"],
                     "R3": ["show ipv6 route ospf"],
                     "R2": ["show ipv6 route ospf"]}),
        # E2a: R1(内部ルータ)で distribute-list in → RIB からのみ消え LSDB は残るはず
        "E2a_distlist_R1_in": dict(
            node="R1",
            apply=deny_one_permit_all("PL_E2", "2001:DB8:A:A::/64")
            + AF + ["distribute-list prefix-list PL_E2 in"] + AF_END,
            revert=AF + ["no distribute-list prefix-list PL_E2 in"] + AF_END
            + ["no ipv6 prefix-list PL_E2"],
            pred=lacks("2001:DB8:A:A::/64"),
            observe={"R1": ["show ipv6 ospf database inter-area prefix",
                            "show running-config | section router ospfv3"]}),
        # E2b: R2(ABR)で distribute-list in → R2 RIB から消えた経路の Type-3 を
        #      まだ他エリアへ広告するか?(RIB 依存か LSDB 依存かの確定)
        "E2b_distlist_R2_in": dict(
            node="R2",
            apply=deny_one_permit_all("PL_E2B", "2001:DB8:9:9::/64")
            + AF + ["distribute-list prefix-list PL_E2B in"] + AF_END,
            revert=AF + ["no distribute-list prefix-list PL_E2B in"] + AF_END
            + ["no ipv6 prefix-list PL_E2B"],
            pred=lambda out: True,  # R1 側は present/absent どちらも知見。固定待ちで観測
            settle=30,
            observe={"R2": ["show ipv6 route ospf"],
                     "R3": ["show ipv6 route ospf"]}),
        # E3a: area 0 range not-advertise → /45 成分4本が R1/R3 から全て消えるはず
        "E3a_range_notadv": dict(
            node="R2",
            apply=AF + ["area 0 range 2001:DB8:8::/45 not-advertise"] + AF_END,
            revert=AF + ["no area 0 range 2001:DB8:8::/45 not-advertise"] + AF_END,
            pred=lacks("2001:DB8:9:9::/64"),
            observe={"R3": ["show ipv6 route ospf"]}),
        # E3b: area 0 range(広告あり) → R1/R3 は /45 集約1本のみ。R2 の discard 経路有無も見る
        "E3b_range_adv": dict(
            node="R2",
            apply=AF + ["area 0 range 2001:DB8:8::/45"] + AF_END,
            revert=AF + ["no area 0 range 2001:DB8:8::/45"] + AF_END,
            pred=lambda out: "2001:DB8:8::/45" in out
            and "2001:DB8:9:9::/64" not in out,
            observe={"R3": ["show ipv6 route ospf"],
                     "R2": ["show ipv6 route ospf | include /45|Null"]}),
        # E7a: permit /46 のみ(暗黙deny) → R1 は 9/A/B が残り C と非包含リンク網が消えるはず
        "E7a_bit46_only": dict(
            node="R2",
            apply=["ipv6 prefix-list PL_E7 seq 5 permit 2001:DB8:8::/46 le 64"]
            + AF + ["area 10 filter-list prefix PL_E7 in"] + AF_END,
            revert=AF + ["no area 10 filter-list prefix PL_E7 in"] + AF_END
            + ["no ipv6 prefix-list PL_E7"],
            pred=lambda out: "2001:DB8:C:C::/64" not in out
            and "2001:DB8:9:9::/64" in out),
        # E7b: permit 2001:DB8:A::/47 のみ → R1 は A/B の2本だけ残るはず
        "E7b_bit47_only": dict(
            node="R2",
            apply=["ipv6 prefix-list PL_E7B seq 5 permit 2001:DB8:A::/47 le 64"]
            + AF + ["area 10 filter-list prefix PL_E7B in"] + AF_END,
            revert=AF + ["no area 10 filter-list prefix PL_E7B in"] + AF_END
            + ["no ipv6 prefix-list PL_E7B"],
            pred=lambda out: "2001:DB8:9:9::/64" not in out
            and "2001:DB8:A:A::/64" in out and "2001:DB8:B:B::/64" in out),
        # E7c: permit ::/0 単体(le なし) → デフォルトのみマッチ=inter-area 全滅のはず
        "E7c_default_only": dict(
            node="R2",
            apply=["ipv6 prefix-list PL_E7C seq 5 permit ::/0"]
            + AF + ["area 10 filter-list prefix PL_E7C in"] + AF_END,
            revert=AF + ["no area 10 filter-list prefix PL_E7C in"] + AF_END
            + ["no ipv6 prefix-list PL_E7C"],
            pred=lambda out: "OI" not in out),
        # E5: ge/le 構文受理スイープ(設定は show 後すぐ全削除)
        "E5_gele_syntax": dict(
            node="R2",
            apply=["ipv6 prefix-list T1 permit 2001:DB8:8::/45 ge 44",
                   "ipv6 prefix-list T2 permit 2001:DB8:8::/45 ge 45",
                   "ipv6 prefix-list T3 permit 2001:DB8:8::/45 ge 64 le 48",
                   "ipv6 prefix-list T4 permit 2001:DB8:8::/45 le 44",
                   "ipv6 prefix-list T5 permit 2001:DB8:8::/45 ge 46 le 64",
                   "ipv6 prefix-list T6 permit ::/0 le 128",
                   "ipv6 prefix-list T7 permit ::/0 ge 1"],
            revert=[f"no ipv6 prefix-list T{i}" for i in range(1, 8)],
            pred=lambda out: True, settle=2,
            observe={"R2": ["show ipv6 prefix-list"]}),
    }


# ---------------- CML / コンソール ----------------
def ensure_lab(client):
    labs = client.find_labs_by_title(LAB_TITLE)
    if labs:
        lab = labs[0]
        print(f"[i] 既存ラボ {LAB_TITLE} ({lab.state()})")
    else:
        print(f"[i] ラボ {LAB_TITLE} を新規作成")
        lab = client.create_lab(LAB_TITLE)
        pos = {"R1": (-200, 0), "R2": (0, 0), "R3": (200, 100), "Ra": (200, -100)}
        nodes = {}
        for label in NODES:
            n = lab.create_node(label, "iol-xe", *pos[label],
                                populate_interfaces=True)
            n.configuration = f"hostname {label}\nno ip domain lookup\n"
            nodes[label] = n
        # ★connect_two_nodes は既存の空き e0/x を使わず新規 E1/x を作って結線する
        #   (初回実走で確認)ため、IF ラベル明示で create_link する
        def iface(label, ifname):
            return next(i for i in nodes[label].interfaces()
                        if i.label == ifname)
        lab.create_link(iface("R1", "Ethernet0/0"), iface("R2", "Ethernet0/0"))
        lab.create_link(iface("R2", "Ethernet0/1"), iface("Ra", "Ethernet0/0"))
        lab.create_link(iface("R2", "Ethernet0/2"), iface("R3", "Ethernet0/0"))
    if lab.state() != "STARTED":
        print("[i] lab start...")
        lab.start(wait=True)
    for n in lab.nodes():
        print(f"    {n.label}: {n.state}")
    return lab


def connect_all(lab):
    tb = yaml.safe_load(lab.get_pyats_testbed())
    for name, dev in (tb.get("devices") or {}).items():
        creds = dev.setdefault("credentials", {})
        if dev.get("type") == "terminal_server" or name == "terminal_server":
            creds["default"] = {"username": CML[1], "password": CML[2]}
        else:
            creds["default"] = {"username": "cisco", "password": "cisco"}
            creds["enable"] = {"password": "cisco"}
    testbed = loader.load(tb)
    devs = {}
    for label in NODES:
        dev = testbed.devices[label]
        for attempt in range(1, 4):
            try:
                dev.connect(via="a", log_stdout=False, learn_hostname=True,
                            connection_timeout=120)
                dev.enable()
                dev.execute("terminal length 0")
                devs[label] = dev
                break
            except Exception as e:
                print(f"    {label}: connect attempt {attempt} failed "
                      f"({type(e).__name__})")
                try:
                    dev.disconnect()
                except Exception:
                    pass
                time.sleep(8)
        else:
            raise RuntimeError(f"{label}: console 接続不能")
    return devs


def conf(dev, lines, log=None):
    """error 検知を切って流し、% 行だけ拾って記録する。"""
    out = dev.configure(lines, error_pattern=[], timeout=90)
    text = out if isinstance(out, str) else "\n".join(
        v for v in out.values() if isinstance(v, str))
    errs = [ln.strip() for ln in text.splitlines() if ln.strip().startswith("%")]
    for e in errs:
        print(f"    ! {e}")
        if log is not None:
            log.append(f"    CLI応答: `{e}`")
    return text


def push_base(devs):
    if "router ospfv3" in devs["R2"].execute(
            "show running-config | include router ospfv3"):
        print("[i] base 設定済み(スキップ)")
        return
    print("[i] base 設定を投入")
    for label in NODES:
        conf(devs[label], BASE[label])


def wait_baseline(devs, timeout=180):
    """R1 が 4本の Lo /64 を OI で持つまで待つ。"""
    t0 = time.time()
    while time.time() - t0 < timeout:
        out = devs["R1"].execute("show ipv6 route ospf")
        if all(f"2001:DB8:{h}:{h}::/64" in out for h in "9ABC"):
            return time.time() - t0
        time.sleep(5)
    raise RuntimeError(f"基線が揃わない:\n{out}")


def main():
    client = ClientLibrary(*CML, ssl_verify=False)
    lab = ensure_lab(client)
    devs = connect_all(lab)
    push_base(devs)
    t = wait_baseline(devs)
    print(f"[i] 基線OK ({t:.0f}s)")

    want = sys.argv[1:] or list(scenarios().keys())
    log = [f"\n## sweep run ({time.strftime('%Y-%m-%d %H:%M:%S')})\n"]
    try:
        for name, sc in scenarios().items():
            if name not in want:
                continue
            print(f"== {name} ==")
            log.append(f"\n### {name}\n")
            conf(devs[sc["node"]], sc["apply"], log)
            t0 = time.time()
            # 効果発現を R1 でポーリング(E6: clear なしで伝わるか+所要時間)
            settle = sc.get("settle")
            if settle:
                time.sleep(settle)
                out = devs["R1"].execute("show ipv6 route ospf")
                log.append(f"(固定待ち {settle}s)\n")
            else:
                out, met = "", False
                while time.time() - t0 < POLL_MAX:
                    out = devs["R1"].execute("show ipv6 route ospf")
                    if sc["pred"](out):
                        met = True
                        break
                    time.sleep(POLL_SEC)
                el = time.time() - t0
                log.append(f"効果発現(clearなし): "
                           f"{'%.0fs で確認' % el if met else '75s 以内に発現せず'}\n")
                print(f"    -> {'OK %.0fs' % el if met else 'NOT CONVERGED'}")
            log.append("R1 `show ipv6 route ospf`:\n```")
            log.append(out.strip())
            log.append("```")
            for obs_node, cmds in (sc.get("observe") or {}).items():
                for cmd in cmds:
                    log.append(f"{obs_node} `{cmd}`:\n```")
                    log.append(devs[obs_node].execute(cmd).strip())
                    log.append("```")
            conf(devs[sc["node"]], sc["revert"], log)
            # 基線復帰を確認してから次へ
            time.sleep(3)
            wait_baseline(devs)
    finally:
        with OUT.open("a") as f:
            f.write("\n".join(log) + "\n")
        for dev in devs.values():
            try:
                dev.disconnect()
            except Exception:
                pass
    print(f"[i] 結果 -> {OUT}")


if __name__ == "__main__":
    main()
