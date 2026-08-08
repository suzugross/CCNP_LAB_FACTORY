#!/usr/bin/env python3
"""BL-095 PoC: EIGRP summary-address leak-map エッジ挙動スイープ (E1-E7)。

_POC-LEAKMAP (RT01-RT02, AS6571) に SSH し、RT01 の設定を組み替えながら
RT02 の受信経路を観測する。各シナリオは 基線→delta適用→clear→観測→revert。
結果は poc/leakmap/results-raw.md へ追記型で書く。

使い方: sweep.py [シナリオ名...]   (無指定=全部)
"""
import sys, time, re
from pathlib import Path

import paramiko
import yaml

REPO = Path(__file__).resolve().parents[2]
GEN = REPO / "topologies/_generated/_POC-LEAKMAP"
OUT = Path(__file__).resolve().parent / "results-raw.md"
USER, PW = "SUZUKI", "CCNP"
AS = 6571
SUMM = "1.1.1.0 255.255.255.252"


def hosts():
    return yaml.safe_load((GEN / "mgmt_map.yml").read_text())


def session(ip):
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(ip, username=USER, password=PW, look_for_keys=False,
                allow_agent=False, timeout=20)
    sh = cli.invoke_shell(width=511)
    _expect(sh, r"[>#]\s*$")
    sh.send("terminal length 0\n")
    _expect(sh, r"#\s*$")
    return cli, sh


def _expect(sh, pat, timeout=30):
    buf, t0 = "", time.time()
    while time.time() - t0 < timeout:
        if sh.recv_ready():
            buf += sh.recv(65535).decode("utf-8", "replace")
            last = buf.splitlines()[-1] if buf.splitlines() else ""
            if re.search(pat, last):
                return buf
        else:
            time.sleep(0.1)
    raise TimeoutError(f"prompt timeout; tail={buf[-300:]!r}")


def run(sh, cmd, timeout=60):
    sh.send(cmd + "\n")
    out = _expect(sh, r"(?:\(config[^)]*\))?#\s*$", timeout)
    lines = out.replace("\r", "").splitlines()
    return "\n".join(lines[1:-1] if len(lines) > 1 else lines)


def conf(sh, lines):
    run(sh, "configure terminal")
    for c in lines:
        r = run(sh, c)
        if r.strip():
            print(f"    ! {c} -> {r.strip()}")
    run(sh, "end")


def summ_lines(leak=None):
    """summary-address を張り替える(IF名は build 後の実IF)。"""
    add = f"ip summary-address eigrp {AS} {SUMM}" + (f" leak-map {leak}" if leak else "")
    return [f"interface {IF}", f"no ip summary-address eigrp {AS} {SUMM}", add]


# ---- シナリオ定義: (apply, revert) は RT01 の config 行リスト ----
def scenarios():
    baseline_summ = summ_lines("RMAP01")
    return {
        "BASE": ([], []),  # 基線そのまま観測
        "S0_no_leakmap": (summ_lines(None), baseline_summ),
        "E1_rmap_undefined": (summ_lines("RMAP_GHOST"), baseline_summ),
        "E2_pl_undefined": (
            ["route-map RMAP02 permit 10", "match ip address prefix-list PL_GHOST"]
            + summ_lines("RMAP02"),
            ["no route-map RMAP02"] + baseline_summ),
        "E3_permit_no_match": (
            ["route-map RMAP03 permit 10"] + summ_lines("RMAP03"),
            ["no route-map RMAP03"] + baseline_summ),
        "E4_pl_matches_nothing": (
            ["ip prefix-list PL_MISS seq 5 permit 99.99.99.99/32",
             "route-map RMAP04 permit 10", "match ip address prefix-list PL_MISS"]
            + summ_lines("RMAP04"),
            ["no route-map RMAP04", "no ip prefix-list PL_MISS"] + baseline_summ),
        "E5_external_component": (
            ["ip prefix-list PL_CONN seq 5 permit 1.1.1.3/32",
             "route-map RM_CONN permit 10", "match ip address prefix-list PL_CONN",
             f"router eigrp {AS}", "no network 1.1.1.3 0.0.0.0",
             "redistribute connected route-map RM_CONN"],
            [f"router eigrp {AS}", "no redistribute connected route-map RM_CONN",
             "network 1.1.1.3 0.0.0.0",
             "no route-map RM_CONN", "no ip prefix-list PL_CONN"]),
        "E6_acl_match": (
            ["access-list 10 permit 1.1.1.3",
             "route-map RMAP_ACL permit 10", "match ip address 10"]
            + summ_lines("RMAP_ACL"),
            ["no route-map RMAP_ACL", "no access-list 10"] + baseline_summ),
        "E7_single_component": (
            [f"router eigrp {AS}", "no network 1.1.1.1 0.0.0.0", "no network 1.1.1.2 0.0.0.0"],
            [f"router eigrp {AS}", "network 1.1.1.1 0.0.0.0", "network 1.1.1.2 0.0.0.0"]),
        # ---- 追加確認(BL-095 生成器の選択肢に登場する代替手段) ----
        # V1: summary-address を使わず static Null0 + redistribute static で集約。
        #     明細は network 1.1.1.3 のみ → 期待: D EX /30 + D 1.1.1.3/32
        "V1_null0_redist": (
            [f"interface {IF}", f"no ip summary-address eigrp {AS} {SUMM}",
             f"router eigrp {AS}", "no network 1.1.1.1 0.0.0.0",
             "no network 1.1.1.2 0.0.0.0",
             "ip route 1.1.1.0 255.255.255.252 Null0",
             f"router eigrp {AS}", "redistribute static"],
            ["no ip route 1.1.1.0 255.255.255.252 Null0",
             f"router eigrp {AS}", "no redistribute static",
             "network 1.1.1.1 0.0.0.0", "network 1.1.1.2 0.0.0.0",
             f"interface {IF}",
             f"ip summary-address eigrp {AS} {SUMM} leak-map RMAP01"]),
        # V2: 全Lo network のまま Null0+redistribute static・summary-address なし
        #     → 期待: 抑止が働かず D EX /30 + 全明細
        "V2_null0_no_suppress": (
            [f"interface {IF}", f"no ip summary-address eigrp {AS} {SUMM}",
             "ip route 1.1.1.0 255.255.255.252 Null0",
             f"router eigrp {AS}", "redistribute static"],
            ["no ip route 1.1.1.0 255.255.255.252 Null0",
             f"router eigrp {AS}", "no redistribute static",
             f"interface {IF}",
             f"ip summary-address eigrp {AS} {SUMM} leak-map RMAP01"]),
        # V4: ★エコ形(ユーザ発案 BL-096③): redistribute connected と leak-map が
        #     **同一 route-map を共用**(対象/32のみ投入)→ 期待: D /30 + D EX 1.1.1.3
        "V4_eco_shared": (
            ["ip prefix-list PL_ECO seq 5 permit 1.1.1.3/32",
             "route-map RM_ECO permit 10", "match ip address prefix-list PL_ECO",
             f"router eigrp {AS}", "no network 1.1.1.1 0.0.0.0",
             "no network 1.1.1.2 0.0.0.0", "no network 1.1.1.3 0.0.0.0",
             "redistribute connected route-map RM_ECO",
             f"interface {IF}", f"no ip summary-address eigrp {AS} {SUMM}",
             f"ip summary-address eigrp {AS} {SUMM} leak-map RM_ECO"],
            [f"router eigrp {AS}", "no redistribute connected route-map RM_ECO",
             "network 1.1.1.1 0.0.0.0", "network 1.1.1.2 0.0.0.0",
             "network 1.1.1.3 0.0.0.0",
             "no route-map RM_ECO", "no ip prefix-list PL_ECO",
             f"interface {IF}", f"no ip summary-address eigrp {AS} {SUMM}",
             f"ip summary-address eigrp {AS} {SUMM} leak-map RMAP01"]),
        # V5: 共用編集の副作用: V4 の PL_ECO を 1.1.1.2/32 へ「変更」した後の状態
        #     → 期待: 1.1.1.3 は投入ごと消える(経路表から消失)・1.1.1.2 が D EX で出現
        "V5_eco_edit_side_effect": (
            ["ip prefix-list PL_ECO seq 5 permit 1.1.1.2/32",
             "route-map RM_ECO permit 10", "match ip address prefix-list PL_ECO",
             f"router eigrp {AS}", "no network 1.1.1.1 0.0.0.0",
             "no network 1.1.1.2 0.0.0.0", "no network 1.1.1.3 0.0.0.0",
             "redistribute connected route-map RM_ECO",
             f"interface {IF}", f"no ip summary-address eigrp {AS} {SUMM}",
             f"ip summary-address eigrp {AS} {SUMM} leak-map RM_ECO"],
            [f"router eigrp {AS}", "no redistribute connected route-map RM_ECO",
             "network 1.1.1.1 0.0.0.0", "network 1.1.1.2 0.0.0.0",
             "network 1.1.1.3 0.0.0.0",
             "no route-map RM_ECO", "no ip prefix-list PL_ECO",
             f"interface {IF}", f"no ip summary-address eigrp {AS} {SUMM}",
             f"ip summary-address eigrp {AS} {SUMM} leak-map RMAP01"]),
        # V3: 成分が全て redistribute connected(external)のときの summary+leak
        #     → 期待: 集約 D [90] のまま・リーク明細 D EX [170]
        "V3_all_external": (
            ["ip prefix-list PL_CONN seq 5 permit 1.1.1.0/30 ge 32",
             "route-map RM_CONN permit 10", "match ip address prefix-list PL_CONN",
             f"router eigrp {AS}", "no network 1.1.1.1 0.0.0.0",
             "no network 1.1.1.2 0.0.0.0", "no network 1.1.1.3 0.0.0.0",
             "redistribute connected route-map RM_CONN"],
            [f"router eigrp {AS}", "no redistribute connected route-map RM_CONN",
             "network 1.1.1.1 0.0.0.0", "network 1.1.1.2 0.0.0.0",
             "network 1.1.1.3 0.0.0.0",
             "no route-map RM_CONN", "no ip prefix-list PL_CONN"]),
    }


def collect(sh1, sh2, tag, log):
    log.append(f"\n### {tag}\n")
    log.append("RT01 `show run interface " + IF + "`:\n```")
    log.append(run(sh1, f"show running-config interface {IF}"))
    log.append("```\nRT01 `show ip eigrp topology 1.1.1.0/30`:\n```")
    log.append(run(sh1, "show ip eigrp topology 1.1.1.0/30"))
    log.append("```\nRT02 `show ip route eigrp`:\n```")
    log.append(run(sh2, "show ip route eigrp"))
    log.append("```")


def wait_adj(sh2, tries=12):
    for _ in range(tries):
        if "172.16.17.1" in run(sh2, "show ip eigrp neighbors"):
            time.sleep(4)  # 隣接直後の更新流入を待つ
            return
        time.sleep(3)
    raise RuntimeError("RT02: EIGRP 隣接が回復しない")


def main():
    global IF
    h = hosts()
    cli1, sh1 = session(h["RT01"])
    cli2, sh2 = session(h["RT02"])
    # 実IF名の確定(summary-address が載っている IF)
    br = run(sh1, "show running-config | include ^interface|summary-address")
    IF = None
    cur = None
    for ln in br.splitlines():
        if ln.startswith("interface "):
            cur = ln.split()[1]
        elif "summary-address" in ln:
            IF = cur
    assert IF, f"summary-address IF が見つからない: {br!r}"
    print(f"[i] RT01 summary IF = {IF}")

    want = sys.argv[1:] or list(scenarios().keys())
    log = [f"\n## sweep run ({time.strftime('%Y-%m-%d %H:%M:%S')}) IF={IF}\n"]
    try:
        for name, (apply, revert) in scenarios().items():
            if name not in want:
                continue
            print(f"== {name} ==")
            if apply:
                conf(sh1, apply)
            run(sh1, "clear ip eigrp neighbors")
            time.sleep(3)
            wait_adj(sh2)
            collect(sh1, sh2, name, log)
            if revert:
                conf(sh1, revert)
        # 最終基線を復元確認
        run(sh1, "clear ip eigrp neighbors")
        time.sleep(3)
        wait_adj(sh2)
        collect(sh1, sh2, "FINAL_BASELINE_CHECK", log)
    finally:
        with OUT.open("a") as f:
            f.write("\n".join(log) + "\n")
        cli1.close()
        cli2.close()
    print(f"[i] 結果 -> {OUT}")


if __name__ == "__main__":
    main()
