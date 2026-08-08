#!/usr/bin/env python3
"""BL-097 P1 実機スポット確認: 生成インスタンスの state config を POC-OSPFV3PL に
投入し、モデル予測(t1/t3)と実測の R1/R3 経路表を突き合わせる。"""
import random
import re
import sys
import time

import urllib3
import yaml
from virl2_client import ClientLibrary
from pyats.topology import loader

urllib3.disable_warnings()
sys.path.insert(0, "/home/suzuki/ansible/CCNP01/topologies")
import gen_paper_ospfv3pl as G

CASES = [("dir_swap", "hide_all"), ("mask_off", "summarize"),
         ("dl_abr", "rib_only"), ("le_off", "area10_only"),
         ("seq_shadow", "rib_only"), ("mask_off", "dual_select"),
         ("seq_shadow", "dual_select")]
# ラボの固定リンク値(POC-OSPFV3PL 盤面)。抽選リンクをこの値へ上書きして突き合わせる
LAB_LNK = {"a1": (0x1, 0x1), "a1b": (0x2, 0x2), "a0": (0x0, 0xA),
           "a2": (0x3, 0x3)}


def hunt(kind, world):
    for seed in range(200000):
        rnd = random.Random(seed)
        try:
            d = G.draw(rnd, kind=kind, world=world)
        except ValueError:
            continue
        if (d["s"], d["a1"], d["a2"], d["proc"]) == (9, 10, 20, 10):
            return seed, d
    raise SystemExit(f"盤面一致 seed が見つからない: {kind}/{world}")


def live_cli(d, st):
    """state を実機投入する CLI(ghost は投入しない)。(R2行, R1行, 撤去R2, 撤去R1)"""
    lives = [fl[2] for fl in st["fl"]]
    if st["dl"]:
        lives.append(st["dl"][1])
    r2, r1, un2, un1 = [], [], [], []
    on_r1 = st["dl"] and st["dl"][0] == "R1"
    for live in lives:
        pls = [G.ent_cli(live, i * 5, e)
               for i, e in enumerate(st["pls"][live], 1)]
        (r1 if on_r1 else r2).extend(pls)
        (un1 if on_r1 else un2).append(f"no ipv6 prefix-list {live}")
    af, afno = [], []
    for fl in st["fl"]:
        af.append(G._fl_line(d, fl))
        afno.append(G._fl_line(d, fl, no=True))
    if st["range"]:
        af.append(G._range_line(d, st["range"]))
        afno.append(G._range_line(d, st["range"], no=True))
    if st["dl"]:
        af.append(f"distribute-list prefix-list {st['dl'][1]} in")
        afno.append(f"no distribute-list prefix-list {st['dl'][1]} in")
    wrap = lambda body: [f"router ospfv3 {d['proc']}",
                         "address-family ipv6 unicast"] + body + [
                             "exit-address-family", "exit"]
    if on_r1:
        r1.extend(wrap(af))
        un1[:0] = wrap(afno)
    else:
        r2.extend(wrap(af))
        un2[:0] = wrap(afno)
    return r2, r1, un2, un1


def parse_oi(text):
    return set(re.findall(r"^OI? {2,3}(\S+) \[110/\d+\]", text, re.M))


def main():
    c = ClientLibrary("https://10.1.10.10", "SUZUKI", "suzugross",
                      ssl_verify=False)
    lab = c.find_labs_by_title("POC-OSPFV3PL")[0]
    if lab.state() != "STARTED":
        print("lab start...", flush=True)
        lab.start(wait=True)
    tb = yaml.safe_load(lab.get_pyats_testbed())
    for name, dev in (tb.get("devices") or {}).items():
        creds = dev.setdefault("credentials", {})
        if dev.get("type") == "terminal_server" or name == "terminal_server":
            creds["default"] = {"username": "SUZUKI", "password": "suzugross"}
        else:
            creds["default"] = {"username": "cisco", "password": "cisco"}
            creds["enable"] = {"password": "cisco"}
    testbed = loader.load(tb)
    devs = {}
    for label in ["R1", "R2", "R3"]:
        dev = testbed.devices[label]
        for att in range(3):
            try:
                dev.connect(via="a", log_stdout=False, learn_hostname=True,
                            connection_timeout=120)
                dev.enable()
                dev.execute("terminal length 0")
                devs[label] = dev
                break
            except Exception as e:
                print(f"  {label} connect retry {att}: {type(e).__name__}",
                      flush=True)
                try:
                    dev.disconnect()
                except Exception:
                    pass
                time.sleep(8)

    # ★基線待ち: Ra の Lo 4本が R1 に OI で揃うまで(収束レース対策)
    for _ in range(40):
        got = parse_oi(devs["R1"].execute("show ipv6 route ospf"))
        if len(got) >= 6:
            break
        time.sleep(5)
    else:
        raise SystemExit(f"基線が揃わない: {sorted(got)}")
    print(f"baseline OK: {len(got)} OI routes", flush=True)

    ok_all = True
    import sys as _sys
    want_cases = _sys.argv[1:]
    for kind, world in CASES:
        if want_cases and kind not in want_cases \
                and f"{kind}/{world}" not in want_cases:
            continue
        seed, d = hunt(kind, world)
        d["lnk"] = dict(LAB_LNK)                 # 実機盤面のリンク値へ上書き
        G.verify_choices(d)                      # 上書き後も一意性が保たれること
        st = G.state(d)
        m = G.model(d, st)
        r2, r1, un2, un1 = live_cli(d, st)
        print(f"== {kind}/{world} (seed {seed}) ==", flush=True)
        if r2:
            devs["R2"].configure(r2, error_pattern=[])
        if r1:
            devs["R1"].configure(r1, error_pattern=[])
        time.sleep(15)
        got1 = parse_oi(devs["R1"].execute("show ipv6 route ospf"))
        got3 = parse_oi(devs["R3"].execute("show ipv6 route ospf"))
        want1 = {G.fmt_v(v, p) for (v, p) in m["t1"]}
        want3 = {G.fmt_v(v, p) for (v, p) in m["t3"]}
        ok = got1 == want1 and got3 == want3
        ok_all &= ok
        print(f"  R1 model={sorted(want1)}", flush=True)
        print(f"  R1 live ={sorted(got1)}  {'OK' if got1 == want1 else '★不一致'}",
              flush=True)
        print(f"  R3 model={sorted(want3)}", flush=True)
        print(f"  R3 live ={sorted(got3)}  {'OK' if got3 == want3 else '★不一致'}",
              flush=True)
        if un2:
            devs["R2"].configure(un2, error_pattern=[])
        if un1:
            devs["R1"].configure(un1, error_pattern=[])
        time.sleep(8)

    # ---- 追測: 未定義 prefix-list 参照の filter-list(P2 用の記録) ----
    print("== extra: 未定義PL参照 filter-list ==", flush=True)
    devs["R2"].configure(["router ospfv3 10", "address-family ipv6 unicast",
                          "area 10 filter-list prefix PL_GHOST_UNDEF in",
                          "exit-address-family"], error_pattern=[])
    time.sleep(15)
    t = parse_oi(devs["R1"].execute("show ipv6 route ospf"))
    print(f"  R1 with undefined-ref filter: {sorted(t)}", flush=True)
    devs["R2"].configure(["router ospfv3 10", "address-family ipv6 unicast",
                          "no area 10 filter-list prefix PL_GHOST_UNDEF in",
                          "exit-address-family"], error_pattern=[])
    time.sleep(10)
    base = parse_oi(devs["R1"].execute("show ipv6 route ospf"))
    print(f"  R1 baseline restored: {len(base)} OI routes", flush=True)
    for label, dev in devs.items():
        pl = dev.execute("show ipv6 prefix-list")
        print(f"  {label} 残存PL: {pl.strip() or 'なし'}", flush=True)
        try:
            dev.configure("logging console")
        except Exception:
            pass
        try:
            dev.sendline("exit")
        except Exception:
            pass
        try:
            dev.disconnect()
        except Exception:
            pass
    lab.stop(wait=True)
    print(f"lab stopped. RESULT: {'ALL OK' if ok_all else 'MISMATCH あり'}",
          flush=True)


if __name__ == "__main__":
    main()
