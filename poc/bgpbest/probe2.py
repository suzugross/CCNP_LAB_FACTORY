#!/usr/bin/env python3
"""BL-112 PoC 追試(probe.py の再測定分)。probe.py のヘルパを import して使う。

- b7b : origin i vs ?(初回は Null0 静的が connected に負けて空振り→ redistribute
        connected でやり直す)
- b13b: ★best 側を flap する(初回は非 best を flap してしまい判別力が無かった)。
        oldest の持続= flap した旧 best が戻っても、新 best が維持されること。
- b13c: b13b の直後(古い方= RT03=RID大)に compare-routerid → RID 小(RT02)へ
        反転すれば「RID は oldest に勝つ」が判別できる。
- b17 : ★真の MED 欠落(2 AS ホップ経路= MED は非遷移で次の AS へ渡らない)の
        表・detail 表示。RT06 を AS65400 に付け替え、新プレフィックスを
        RT06→RT03→RT01 と運ぶ。
- cfgref: RT01 の `show run | section router bgp`(紙面 cfg 抜粋の忠実性参照)。
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import probe as P                                            # noqa: E402

OUT = Path(__file__).resolve().parent / "results-raw.md"


def best_from(dev, pfx=P.PFX):
    """detail から best 経路の from を返す(★Paths: 見出しの ", best" を除外)。"""
    out = P.sh(dev, f"show ip bgp {pfx}")
    frm = None
    for line in out.splitlines():
        m = re.search(r"^\s+\S+(?: \(\S+ ?\d*\))? from (\S+) \(", line)
        if m:
            frm = m.group(1)
        if "Origin" in line and ", best" in line:
            return frm, out
    return None, out


def wait_best(dev, want, timeout=90, label=""):
    return P.wait(lambda: best_from(dev)[0] == want, timeout=timeout,
                  label=label)


def b7b(devs, log):
    log.append("\n## B7b: origin i vs ?(redistribute connected でやり直し)")
    rt = devs["RT01"]
    P.only_neighbors(devs, ["RT02", "RT03"], log)
    P.conf(devs["RT03"], [
        "router bgp 65200", "address-family ipv4",
        "no network 198.51.100.0 mask 255.255.255.0",
        "redistribute connected",
        "exit-address-family", "exit"])
    P.sh(devs["RT03"], "clear ip bgp 10.0.13.1 soft out")
    P.wait(lambda: "?" in P.sh(rt, f"show ip bgp {P.PFX}"), timeout=90,
           label="origin ? 反映")
    frm, out = best_from(rt)
    log.append(f"- best from = `{frm}` (期待= {P.E['RT02']}・i が ? に勝つ)")
    P.block(log, f"RT01 show ip bgp {P.PFX} (i vs ?)", out)
    P.block(log, "RT01 show ip bgp (Path 列の ? 表示)", P.sh(rt, "show ip bgp"))
    P.conf(devs["RT03"], [
        "router bgp 65200", "address-family ipv4",
        "no redistribute connected",
        "network 198.51.100.0 mask 255.255.255.0",
        "exit-address-family", "exit"])
    P.sh(devs["RT03"], "clear ip bgp 10.0.13.1 soft out")
    time.sleep(5)


def b13b(devs, log):
    log.append("\n## B13b: ★best 側を flap → oldest の持続を判別")
    rt = devs["RT01"]
    P.only_neighbors(devs, ["RT02", "RT03"], log)
    time.sleep(5)
    frm0, out0 = best_from(rt)
    P.block(log, f"タイ状態(best from = {frm0})", out0)
    flap = "RT02" if frm0 == P.E["RT02"] else "RT03"
    other = "RT03" if flap == "RT02" else "RT02"
    log.append(f"- ★best 側({flap})を flap する")
    P.rt01_shut(devs, [flap], True)
    wait_best(rt, P.E[other], label="takeover")
    P.rt01_shut(devs, [flap], False)
    P.wait(lambda: P.E[flap] in P.up_neighbors(rt), timeout=120, label="re-est")
    P.wait(lambda: P.n_paths(rt) == 2, timeout=90, label="2 paths")
    time.sleep(10)
    frm1, out1 = best_from(rt)
    log.append(f"- 再確立後の best from = `{frm1}` (期待= `{P.E[other]}` の維持="
               "oldest 勝ち。戻った側は新しいので奪還できない)")
    P.block(log, "flap 後", out1)
    return other      # いま best(=older)のノード名


def b13c(devs, log, older):
    log.append("\n## B13c: ★compare-routerid は oldest に勝つか")
    rt = devs["RT01"]
    # いまの best= older(= b13b の結果)。RID は RT02(2.2.2.2) < RT03(3.3.3.3)。
    # older が RT03 のとき crid で RT02 へ反転すれば判別成立。
    if older == "RT02":
        # RT02 が older だと RID でも RT02 のまま= 判別不能 → RT02 を flap して
        # RT03 を older にする
        log.append("- older が RT02(RID小)なので、RT02 を flap して older を"
                   "RT03 に付け替える")
        P.rt01_shut(devs, ["RT02"], True)
        wait_best(rt, P.E["RT03"], label="rt03 take")
        P.rt01_shut(devs, ["RT02"], False)
        P.wait(lambda: P.n_paths(rt) == 2, timeout=120, label="2 paths")
        time.sleep(10)
    frm0, out0 = best_from(rt)
    log.append(f"- crid 投入前の best from = `{frm0}` (期待= {P.E['RT03']}=older)")
    P.conf(rt, ["router bgp 65100", "bgp bestpath compare-routerid", "exit"])
    dt = wait_best(rt, P.E["RT02"], timeout=120, label="crid flip")
    frm1, out1 = best_from(rt)
    log.append(f"- `bgp bestpath compare-routerid` → best from = `{frm1}` "
               f"(期待= {P.E['RT02']}=RID 2.2.2.2。oldest より優先・"
               f"clear 無し所要 {dt:.0f}s)")
    P.block(log, "compare-routerid 後(detail 冒頭の BGP Bestpath: 行にも注目)",
            out1)
    P.conf(rt, ["router bgp 65100", "no bgp bestpath compare-routerid", "exit"])


def b17(devs, log):
    log.append("\n## B17: ★真の MED 欠落(2 AS ホップ)の表示")
    rt = devs["RT01"]
    P.only_neighbors(devs, ["RT02", "RT03"], log)
    # RT06 を AS65400 化し、新プレフィックスを RT06→RT03→RT01 と運ぶ
    P.conf(devs["RT06"], [
        "no router bgp 65100",
        "interface Loopback177", "ip address 172.20.77.6 255.255.255.0", "exit",
        "router bgp 65400", "bgp router-id 6.6.6.6",
        "neighbor 10.0.36.3 remote-as 65200",
        "address-family ipv4",
        "network 172.20.77.0 mask 255.255.255.0",
        "neighbor 10.0.36.3 activate",
        "exit-address-family", "exit"])
    P.conf(devs["RT03"], [
        "router bgp 65200",
        "neighbor 10.0.36.6 remote-as 65400", "exit"])
    P.wait(lambda: "172.20.77.0" in P.sh(rt, "show ip bgp"), timeout=180,
           label="2hop prefix 伝播")
    P.block(log, "RT01 show ip bgp (172.20.77.0 行の Metric 列= 欠落の表示)",
            P.sh(rt, "show ip bgp"))
    P.block(log, "RT01 show ip bgp 172.20.77.0 (detail の metric 表示)",
            P.sh(rt, "show ip bgp 172.20.77.0"))
    P.block(log, "RT03 show ip bgp 172.20.77.0 (RT03 では MED 受信済のはず)",
            P.sh(devs["RT03"], "show ip bgp 172.20.77.0"))
    # 復元
    P.conf(devs["RT06"], [
        "no router bgp 65400",
        "no interface Loopback177"] + P.BASE["RT06"][
            P.BASE["RT06"].index("router bgp 65100"):])
    P.conf(devs["RT03"], [
        "router bgp 65200",
        "neighbor 10.0.36.6 remote-as 65100", "exit"])
    time.sleep(5)


def cfgref(devs, log):
    log.append("\n## cfgref: 紙面 cfg 抜粋の忠実性参照")
    P.block(log, "RT01 show running-config | section router bgp",
            P.sh(devs["RT01"], "show running-config | section router bgp"))
    P.block(log, "RT05 show running-config | section router bgp",
            P.sh(devs["RT05"], "show running-config | section router bgp"))


def restore(devs, log):
    P.rt01_shut(devs, list(P.E), False)
    dt = P.wait(lambda: P.up_neighbors(devs["RT01"]) == set(P.E.values()),
                timeout=240, label="restore")
    log.append(f"\n## 復元: 全隣接 no shutdown(収束 {dt:.0f}s)")


def main():
    client = P.ClientLibrary(P.CML[0], P.CML[1], P.CML[2], ssl_verify=False)
    lab = P.ensure_lab(client)
    devs = P.connect_all(lab, required=tuple(P.NODES))
    log = [f"\n---\n# probe2 実行 {time.strftime('%Y-%m-%d %H:%M')}"]
    try:
        b7b(devs, log)
        older = b13b(devs, log)
        b13c(devs, log, older)
        b17(devs, log)
        cfgref(devs, log)
        restore(devs, log)
    finally:
        with OUT.open("a") as f:
            f.write("\n".join(log) + "\n")
        print(f"[i] 結果を {OUT} に追記した")


if __name__ == "__main__":
    main()
