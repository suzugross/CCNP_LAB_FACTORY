#!/usr/bin/env python3
"""BL-215 distribute-list 道場 PoC(IOL iol-xe・EIGRP AS 100)。

盤面 POC-DLIST = IOL 4 台。
    RT03(e0/0 10.0.13.3) ── (e0/1 10.0.13.1) RT01 (e0/0 10.0.12.1) ── (e0/0 10.0.12.2) RT02
                                                                        RT02 e0/1 10.0.24.2 ── e0/0 10.0.24.4 RT04
経路(battery)は各ルータの `ip route … Null0` + `redistribute static`(同アドレス異長を 1 台に置ける)。

使い方: sweep.py build | D0 D1 D2 D3 D4 D5 | teardown   結果は results-raw.md へ追記。
"""
import re
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "paper-kb"))
import sweep as kb  # noqa: E402

NODES = ["RT01", "RT02", "RT03", "RT04"]
AS = 100
BATTERY = {
    "RT02": ["10.50.0.0/24", "10.50.0.0/26", "10.50.0.0/22", "10.50.0.16/28",
             "10.50.1.0/24", "10.50.2.0/24", "10.50.3.0/24", "10.50.2.128/25"],
    "RT03": ["10.50.0.0/24", "10.50.0.0/28", "10.50.2.0/24", "10.50.9.0/24"],
    "RT04": ["10.60.0.0/24", "10.60.0.0/28", "10.60.1.0/24"],
}
NH = {"RT02": "10.0.12.2", "RT03": "10.0.13.3"}          # RT01 から見た next-hop
ALL = sorted({p for v in BATTERY.values() for p in v},
             key=lambda p: (tuple(int(x) for x in p.split("/")[0].split(".")), int(p.split("/")[1])))


def mask(bits):
    m = (0xFFFFFFFF << (32 - bits)) & 0xFFFFFFFF
    return ".".join(str((m >> s) & 255) for s in (24, 16, 8, 0))


def statics(label):
    L = []
    for p in BATTERY.get(label, []):
        a, b = p.split("/")
        L.append(f"ip route {a} {mask(int(b))} Null0")
    return L


BASE = {
    "RT01": ["interface Ethernet0/0", "ip address 10.0.12.1 255.255.255.0", "no shutdown", "exit",
             "interface Ethernet0/1", "ip address 10.0.13.1 255.255.255.0", "no shutdown", "exit",
             f"router eigrp {AS}", "eigrp router-id 1.1.1.1", "network 10.0.12.0 0.0.0.255",
             "network 10.0.13.0 0.0.0.255", "exit"],
    "RT02": ["interface Ethernet0/0", "ip address 10.0.12.2 255.255.255.0", "no shutdown", "exit",
             "interface Ethernet0/1", "ip address 10.0.24.2 255.255.255.0", "no shutdown", "exit"]
            + statics("RT02") +
            [f"router eigrp {AS}", "eigrp router-id 2.2.2.2", "network 10.0.12.0 0.0.0.255",
             "network 10.0.24.0 0.0.0.255", "redistribute static metric 10000 100 255 1 1500", "exit"],
    "RT03": ["interface Ethernet0/0", "ip address 10.0.13.3 255.255.255.0", "no shutdown", "exit"]
            + statics("RT03") +
            [f"router eigrp {AS}", "eigrp router-id 3.3.3.3", "network 10.0.13.0 0.0.0.255",
             "redistribute static metric 10000 100 255 1 1500", "exit"],
    "RT04": ["interface Ethernet0/0", "ip address 10.0.24.4 255.255.255.0", "no shutdown", "exit"]
            + statics("RT04") +
            [f"router eigrp {AS}", "eigrp router-id 4.4.4.4", "network 10.0.24.0 0.0.0.255",
             "redistribute static metric 10000 100 255 1 1500", "exit"],
}

kb.LAB_TITLE = "POC-DLIST"
kb.NODES = NODES
kb.OUT = HERE / "results-raw.md"
kb.BASE = BASE
kb.LINKS = [("RT01", "Ethernet0/0", "RT02", "Ethernet0/0"),
            ("RT01", "Ethernet0/1", "RT03", "Ethernet0/0"),
            ("RT02", "Ethernet0/1", "RT04", "Ethernet0/0")]
block, note, flush, conf, sh = kb.block, kb.note, kb.flush, kb.conf, kb.sh


# =========================================================================
def routes(dev):
    """RT01 の EIGRP 経路 → {prefix: set(next-hop)}(10.50/10.60 だけ)。"""
    out = sh(dev, "show ip route eigrp")
    res, cur = {}, None
    for ln in out.splitlines():
        m = re.match(r"^D(?: EX)?\s+(?:\S+\s+)?(10\.[56]0\.\d+\.\d+/\d+)", ln.strip())
        if m:
            cur = m.group(1)
            res.setdefault(cur, set())
        elif not re.match(r"^\s", ln):
            cur = None if not ln.startswith(" ") else cur
        for v in re.findall(r"via (10\.0\.\d+\.\d+)", ln):
            if cur:
                res[cur].add(v)
    return res, out


def fmt(res):
    who = {v: k for k, v in NH.items()}
    return " / ".join(f"{p}({'+'.join(sorted(who.get(v, v) for v in res[p]))})"
                      for p in ALL if p in res) or "(なし)"


def clear_dl(r1):
    run = sh(r1, "show running-config | section router eigrp")
    lines = [ln.strip() for ln in run.splitlines() if ln.strip().startswith("distribute-list")]
    if lines:
        conf(r1, [f"router eigrp {AS}"] + [f"no {x}" for x in lines])


def settle(r1, want=None, timeout=120, before=None, min_wait=0):
    """経路表が落ち着くまで待つ(want= 期待件数・None なら 3 回連続同じ)。
    ★before= 投入前の状態。これと違う状態になるまで(最大 min_wait 秒)は「安定」と見なさない
      (EIGRP は distribute-list の変更を隣接の再同期で反映するので数秒〜十数秒遅れる。
       2 回連続同じ= 安定、で判定すると変化前を掴む= D1a 初回の誤判定)。"""
    t0, hist = time.time(), []
    while time.time() - t0 < timeout:
        res, _ = routes(r1)
        key = fmt(res)
        if want is not None and len(res) == want:
            return time.time() - t0, res
        hist.append(key)
        changed = before is None or key != before or time.time() - t0 >= min_wait
        if want is None and changed and len(hist) >= 3 and hist[-1] == hist[-2] == hist[-3]:
            return time.time() - t0, res
        time.sleep(5)
    return None, routes(r1)[0]


def case(devs, tag, desc, cfg, expect=None, show=()):
    """distribute-list を全部外して基線へ戻す → cfg を入れる → 経路と ACL カウンタを記録。"""
    r1 = devs["RT01"]
    clear_dl(r1)
    t, _ = settle(r1, want=len(ALL), timeout=150)
    sh(r1, "clear ip access-list counters")
    note(f"== {tag}: {desc}(基線復帰 {'%.0fs' % t if t is not None else '★未復帰'})")
    before = fmt(routes(r1)[0])
    kb.clear_log(r1)
    conf(r1, cfg, f"{tag} 投入")
    t, res = settle(r1, timeout=180, before=before, min_wait=90)
    got = fmt(res)
    block(f"{tag} 残った経路({'%.0fs' % t if t else '?'} で安定)", got)
    if expect is not None:
        exp = " / ".join(expect) if expect else "(なし)"
        ok = sorted(res) == sorted(p.split("(")[0] for p in expect) if expect else not res
        note(f"{tag}: 期待 {'一致' if ok else '★不一致'}  期待= {exp}")
    for c in show:
        sh(r1, c, f"{tag}")
    kb.logtail(r1, f"{tag} log", include="DUAL|EIGRP")
    flush(f"{tag} {desc}")
    return res


# =========================================================================
def D0(devs):
    r1 = devs["RT01"]
    t, res = settle(r1, want=len(ALL), timeout=240)
    note(f"D0: 基線 {len(res)}/{len(ALL)} 経路({'%.0fs' % t if t is not None else '★未達'})")
    block("D0 基線の経路", fmt(res))
    sh(r1, "show ip route eigrp", "D0")
    sh(r1, "show ip eigrp neighbors", "D0")
    flush("D0 基線")


def D1(devs):
    acl = ["access-list 10 permit 10.50.0.0",
           "access-list 110 permit ip any host 10.50.0.0",
           "access-list 111 permit ip host 10.50.0.0 any",
           "access-list 112 permit ip host 10.0.13.3 any",
           "access-list 113 permit ip host 10.0.24.4 any",
           "access-list 114 permit ip host 10.0.12.2 host 10.60.0.0",
           "access-list 120 permit ip host 10.50.0.0 host 255.255.255.0",
           "access-list 11 permit 10.50.0.0 0.0.2.255",
           "route-map RM120 permit 10", "match ip address 120", "exit",
           "ip prefix-list P1 seq 5 permit 10.50.0.0/16 ge 24 le 24"]
    conf(devs["RT01"], acl, "D1 部品の定義")
    R = [f"router eigrp {AS}"]
    case(devs, "D1a", "標準 ACL `permit 10.50.0.0`(K1)", R + ["distribute-list 10 in"],
         show=("show access-lists 10",))
    case(devs, "D1b", "拡張・直接 `permit ip any host 10.50.0.0`(K2 dst=網)", R + ["distribute-list 110 in"],
         show=("show access-lists 110",))
    case(devs, "D1c", "拡張・直接 `permit ip host 10.50.0.0 any`(K2 src に網を書く)", R + ["distribute-list 111 in"],
         show=("show access-lists 111",))
    case(devs, "D1d", "拡張・直接 `permit ip host 10.0.13.3 any`(K2 src=広告元 RT03)", R + ["distribute-list 112 in"],
         show=("show access-lists 112",))
    case(devs, "D1e", "拡張・直接 `permit ip host 10.0.24.4 any`(K3 RT04= 作ったルータ)", R + ["distribute-list 113 in"],
         show=("show access-lists 113",))
    case(devs, "D1f", "拡張・直接 `permit ip host 10.0.12.2 host 10.60.0.0`(K3 広告元 RT02 × 網)",
         R + ["distribute-list 114 in"], show=("show access-lists 114",))
    case(devs, "D1g", "route-map 経由 `permit ip host 10.50.0.0 host 255.255.255.0`(K4)",
         R + ["distribute-list route-map RM120 in"], show=("show access-lists 120",))
    case(devs, "D1h", "prefix-list `10.50.0.0/16 ge 24 le 24`(K5)", R + ["distribute-list prefix P1 in"],
         show=("show ip prefix-list P1",))
    case(devs, "D1i", "標準 ACL 非連続 `permit 10.50.0.0 0.0.2.255`(K6)", R + ["distribute-list 11 in"],
         show=("show access-lists 11",))


def D2(devs):
    """インターフェイス単位 + 全体の併用: 積(両方)か、インターフェイス単位が優先か。"""
    conf(devs["RT01"], ["access-list 30 permit 10.50.0.0",
                        "ip prefix-list P24 seq 5 permit 0.0.0.0/0 ge 24 le 24"], "D2 部品")
    R = [f"router eigrp {AS}"]
    # 全体= /24 だけ(prefix)・RT03 側 IF= 10.50.0.0(長さ問わず)
    # 積なら RT03 由来は 10.50.0.0/24 だけ / IF 優先なら RT03 由来は 10.50.0.0/24 と /28
    case(devs, "D2a", "全体 prefix P24(/24 だけ) + IF(e0/1=RT03) ACL 30(10.50.0.0 のみ)",
         R + ["distribute-list prefix P24 in", "distribute-list 30 in Ethernet0/1"],
         show=("show ip protocols | include filter|Distribute|Ethernet",))


def D3(devs):
    """同一 IF で ACL 形・prefix 形・route-map 形を重ねたらどうなるか。"""
    r1 = devs["RT01"]
    conf(r1, ["ip prefix-list P26 seq 5 permit 0.0.0.0/0 ge 26 le 26",
              "access-list 31 permit 10.50.0.0 0.0.0.255"], "D3 部品")
    R = [f"router eigrp {AS}"]
    case(devs, "D3a", "同 IF(e0/0=RT02) に ACL 31(10.50.0.x)→ prefix P26(/26) の順で投入",
         R + ["distribute-list 31 in Ethernet0/0", "distribute-list prefix P26 in Ethernet0/0"],
         show=("show running-config | section router eigrp", "show ip protocols | include filter|Distribute|Ethernet"))
    case(devs, "D3b", "同 IF(e0/0) に ACL 31 → route-map RM120 の順で投入",
         R + ["distribute-list 31 in Ethernet0/0", "distribute-list route-map RM120 in Ethernet0/0"],
         show=("show running-config | section router eigrp",))


def D4(devs):
    """route-map 経由の dst にマスクのワイルドカード。"""
    conf(devs["RT01"], ["access-list 121 permit ip 10.50.0.0 0.0.255.255 255.255.255.0 0.0.0.255",
                        "route-map RM121 permit 10", "match ip address 121", "exit",
                        "access-list 122 permit ip 10.50.0.0 0.0.255.255 host 255.255.255.0",
                        "route-map RM122 permit 10", "match ip address 122", "exit"], "D4 部品")
    R = [f"router eigrp {AS}"]
    case(devs, "D4a", "route-map 経由 dst= `255.255.255.0 0.0.0.255`(マスク /24〜/32 のつもり)",
         R + ["distribute-list route-map RM121 in"], show=("show access-lists 121",))
    case(devs, "D4b", "route-map 経由 dst= `host 255.255.255.0`・src= 10.50/16(/24 ちょうど)",
         R + ["distribute-list route-map RM122 in"], show=("show access-lists 122",))


def D5(devs):
    """反映時間(clear なし): 基線 → ACL 10 → 経路が減り切るまで。"""
    r1 = devs["RT01"]
    clear_dl(r1)
    settle(r1, want=len(ALL), timeout=150)
    t0 = time.time()
    conf(r1, [f"router eigrp {AS}", "distribute-list 10 in"])
    seen = []
    while time.time() - t0 < 120:
        res, _ = routes(r1)
        seen.append((round(time.time() - t0), len(res)))
        if len(res) < len(ALL) and len(seen) > 1 and seen[-1][1] == seen[-2][1]:
            break
        time.sleep(3)
    note(f"D5: 反映の推移(秒, 経路数)= {seen}")
    kb.logtail(r1, "D5 log", include="DUAL|EIGRP")
    clear_dl(r1)
    flush("D5 反映時間")


STEPS = {"D0": D0, "D1": D1, "D2": D2, "D3": D3, "D4": D4, "D5": D5}


def main():
    args = sys.argv[1:] or ["D0"]
    cl, creds = kb.client()
    if args == ["teardown"]:
        kb.teardown(cl)
        return
    if args[0] == "build":
        kb.ensure_lab(cl)
        args = args[1:]
        if not args:
            return
    lab = kb.get_lab(cl)
    devs = kb.connect_all(lab, creds, labels=NODES)
    for s in args:
        print(f"\n===== {s} =====", flush=True)
        try:
            STEPS[s](devs)
        except Exception:
            tb = traceback.format_exc()
            print(tb)
            block(f"{s} EXCEPTION", tb)
            flush(f"{s} (失敗)")
    for d in devs.values():
        try:
            d.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    main()
