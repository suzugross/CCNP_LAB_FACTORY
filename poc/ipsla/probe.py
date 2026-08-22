#!/usr/bin/env python3
"""BL-134 PoC: IP SLA/track TS 生成器(gen_ipsla_ts)の前提挙動+書式スイープ。

設計メモ= problems/_drafts/GEN-IPSLA-TS.design.md §7。
CML に _POC-IPSLA(IOL 4台・ENCOR-IPSLA-02 盤面の写し)を作成し、
コンソール直駆動(mgmt/SSH 不使用・poc/pref の型)で以下を単離観測する。

  RT01 ─e0/0 10.0.12.0/30─ RT02(primary) ─e0/2 10.0.24.0/30─ RT04
      ╲e0/1 10.0.13.0/30─ RT03(backup)  ─e0/2 10.0.34.0/30─┘
                （RT02 e0/1 ↔ RT03 e0/1 = 10.0.23.0/30）
  RT04: Lo10=8.8.8.8/32(両ISP到達可) Lo20=100.64.0.1/32(ビーコン・primary専用)
  戻り経路ポリシー(実証済み・IPSLA-02 流用):
    RT04→10.0.12.1 は primary 経由のみ / RT04→1.1.1.1 は backup 優先+AD200

チェック名(無指定=全部):
  p0 基線+奥障害切替タイミング     p1 スケジュール済み SLA の編集ロック
  p2 未 schedule                    p3 存在しない SLA 参照 track
  p4 path-echo×no ip source-route  p5 udp-jitter×responder
  p6 tcp-connect 実在/誤ポート      p7 source 誤り(backup側IF/Lo0 非対称)
  p8 timeout>frequency・threshold・AD同値
結果は results-raw.md へ追記。
"""
import re
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
LAB_TITLE = "_POC-IPSLA"

NODES = ["RT01", "RT02", "RT03", "RT04"]
LINKS = [("RT01", 0, "RT02", 0), ("RT01", 1, "RT03", 0),
         ("RT02", 1, "RT03", 1), ("RT02", 2, "RT04", 0),
         ("RT03", 2, "RT04", 1)]
POS = {"RT01": (-320, 0), "RT02": (0, -140), "RT03": (0, 140), "RT04": (320, 0)}

BEACON = "100.64.0.1"
DATA = "8.8.8.8"

BASE = {
    "RT01": [
        "no ip domain lookup",
        "interface Ethernet0/0", "ip address 10.0.12.1 255.255.255.252",
        "no shutdown", "exit",
        "interface Ethernet0/1", "ip address 10.0.13.1 255.255.255.252",
        "no shutdown", "exit",
        "interface Loopback0", "ip address 1.1.1.1 255.255.255.255", "exit",
        "no logging console",
    ],
    "RT02": [
        "no ip domain lookup",
        "interface Ethernet0/0", "ip address 10.0.12.2 255.255.255.252",
        "no shutdown", "exit",
        "interface Ethernet0/1", "ip address 10.0.23.1 255.255.255.252",
        "no shutdown", "exit",
        "interface Ethernet0/2", "ip address 10.0.24.1 255.255.255.252",
        "no shutdown", "exit",
        "interface Loopback0", "ip address 2.2.2.2 255.255.255.255", "exit",
        f"ip route {DATA} 255.255.255.255 10.0.24.2",
        f"ip route {BEACON} 255.255.255.255 10.0.24.2",
        "ip route 1.1.1.1 255.255.255.255 10.0.12.1",
        "no logging console",
    ],
    "RT03": [
        "no ip domain lookup",
        "interface Ethernet0/0", "ip address 10.0.13.2 255.255.255.252",
        "no shutdown", "exit",
        "interface Ethernet0/1", "ip address 10.0.23.2 255.255.255.252",
        "no shutdown", "exit",
        "interface Ethernet0/2", "ip address 10.0.34.1 255.255.255.252",
        "no shutdown", "exit",
        "interface Loopback0", "ip address 3.3.3.3 255.255.255.255", "exit",
        f"ip route {DATA} 255.255.255.255 10.0.34.2",
        "ip route 1.1.1.1 255.255.255.255 10.0.13.1",
        "no logging console",
    ],
    "RT04": [
        "no ip domain lookup",
        "interface Ethernet0/0", "ip address 10.0.24.2 255.255.255.252",
        "no shutdown", "exit",
        "interface Ethernet0/1", "ip address 10.0.34.2 255.255.255.252",
        "no shutdown", "exit",
        "interface Loopback0", "ip address 4.4.4.4 255.255.255.255", "exit",
        f"interface Loopback10", f"ip address {DATA} 255.255.255.255", "exit",
        f"interface Loopback20", f"ip address {BEACON} 255.255.255.255", "exit",
        "ip route 1.1.1.1 255.255.255.255 10.0.34.1",
        "ip route 1.1.1.1 255.255.255.255 10.0.24.1 200",
        "ip route 10.0.12.0 255.255.255.252 10.0.24.1",
        "no logging console",
    ],
}


# ---------------- CML / コンソール(poc/pref の型) ----------------
def _ifname(slot):
    return f"Ethernet{slot // 4}/{slot % 4}"


def _iface(lab, label, slot):
    name = _ifname(slot)
    node = lab.get_node_by_label(label)
    for _ in range(4):
        for i in node.interfaces():
            if i.label == name:
                return i
        try:
            node.create_interface(slot=slot, wait=True)
        except Exception as e:
            print(f"    create_interface({label},{slot}): {type(e).__name__}")
        lab.sync(topology_only=True)
        time.sleep(1)
    raise RuntimeError(f"{label} に {name} が作れない")


def ensure_lab(client):
    labs = client.find_labs_by_title(LAB_TITLE)
    if labs:
        lab = labs[0]
        print(f"[i] 既存ラボ {LAB_TITLE} ({lab.state()})")
    else:
        print(f"[i] ラボ {LAB_TITLE} を新規作成")
        lab = client.create_lab(LAB_TITLE)
    have = {n.label for n in lab.nodes()}
    for label in NODES:
        if label in have:
            continue
        n = lab.create_node(label, "iol-xe", *POS[label],
                            populate_interfaces=True)
        n.configuration = f"hostname {label}\nno ip domain lookup\n"
    lab.sync(topology_only=True)
    for a, aslot, b, bslot in LINKS:
        ia, ib = _iface(lab, a, aslot), _iface(lab, b, bslot)
        if ia.connected or ib.connected:
            continue
        print(f"[i] link {a} {_ifname(aslot)} <-> {b} {_ifname(bslot)}")
        lab.create_link(ia, ib)
    if lab.state() != "STARTED":
        print("[i] lab start...")
        lab.start(wait=True)
    for n in lab.nodes():
        print(f"    {n.label}: {n.state}")
    return lab


def connect_all(lab, required=("RT01",)):
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
            if label in required:
                raise RuntimeError(f"{label}: console 接続不能(必須ノード)")
            print(f"    [!] {label}: console 接続不能")
    return devs


def conf(dev, lines, log=None):
    out = dev.configure(lines, error_pattern=[], timeout=180)
    text = out if isinstance(out, str) else "\n".join(
        v for v in out.values() if isinstance(v, str))
    errs = [ln.strip() for ln in text.splitlines()
            if ln.strip().startswith("%")]
    for e in errs:
        print(f"    ! {e}")
        if log is not None:
            log.append(f"- CLI応答: `{e}`")
    return errs, text


def sh(dev, cmd):
    return dev.execute(cmd, timeout=180)


def block(log, title, text):
    log.append(f"\n{title}:\n```\n{text.strip()}\n```")


def wait(pred, timeout=240, every=5, label=""):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            if pred():
                return round(time.time() - t0, 1)
        except Exception as e:
            print(f"    wait({label}): {type(e).__name__}")
        time.sleep(every)
    print(f"    [!] wait timeout: {label}")
    return -1


def push_base(devs):
    for label in NODES:
        if label not in devs:
            print(f"[i] {label}: 未接続のため base 投入をスキップ")
            continue
        print(f"[i] {label}: base 設定を投入")
        conf(devs[label], BASE[label])


# ---------------- RT01 の SLA まわりヘルパ ----------------
def reset_rt01(devs):
    """RT01 の SLA/track/static を全撤去(冪等・%エラーは握りつぶし)。"""
    d = devs["RT01"]
    conf(d, [
        "no ip sla schedule 1", "no ip sla schedule 2", "no ip sla schedule 3",
        "no ip sla 1", "no ip sla 2", "no ip sla 3",
        "no track 1", "no track 2",
        f"no ip route {BEACON} 255.255.255.255 10.0.12.2",
        f"no ip route {BEACON} 255.255.255.255 10.0.13.2",
        "no ip route 0.0.0.0 0.0.0.0 10.0.12.2 track 1",
        "no ip route 0.0.0.0 0.0.0.0 10.0.12.2",
        "no ip route 0.0.0.0 0.0.0.0 10.0.13.2 200",
        "no ip route 0.0.0.0 0.0.0.0 10.0.13.2",
    ])
    time.sleep(2)


def golden(devs, *, schedule=True, sla_lines=None, track_sla=1):
    """IPSLA-02 の正解構成を RT01 へ投入。sla_lines で SLA 定義を差し替え可。"""
    d = devs["RT01"]
    lines = sla_lines or ["ip sla 1",
                          f"icmp-echo {BEACON} source-ip 10.0.12.1",
                          "frequency 10", "exit"]
    conf(d, lines)
    if schedule:
        conf(d, ["ip sla schedule 1 life forever start-time now"])
    conf(d, [f"track 1 ip sla {track_sla} reachability",
             f"ip route {BEACON} 255.255.255.255 10.0.12.2",
             "ip route 0.0.0.0 0.0.0.0 10.0.12.2 track 1",
             "ip route 0.0.0.0 0.0.0.0 10.0.13.2 200"])


def track_state(dev, n=1):
    out = sh(dev, f"show track {n}")
    m = re.search(r"(Reachability|State)\s+is\s+(\S+)", out)
    return (m.group(2) if m else "?"), out


def ping_ok(dev, target, source="Loopback0", repeat=10):
    out = sh(dev, f"ping {target} source {source} repeat {repeat}")
    m = re.search(r"Success rate is (\d+) percent", out)
    return (int(m.group(1)) if m else -1), out


def sla_stats(dev, n=""):
    return sh(dev, f"show ip sla statistics {n}".strip())


# ---------------- 探針 ----------------
def p0(devs, log):
    """基線: golden で track Up・疎通・書式採取・奥障害切替/復帰タイミング。"""
    d = devs["RT01"]
    reset_rt01(devs)
    golden(devs)
    t_up = wait(lambda: track_state(d)[0] == "Up", timeout=120, label="track up")
    log.append(f"- golden 投入から track Up まで **{t_up}s**")
    st, out = track_state(d)
    block(log, "`show track 1`(健全)", out)
    block(log, "`show ip sla configuration`", sh(d, "show ip sla configuration"))
    block(log, "`show ip sla statistics`(健全)", sla_stats(d))
    block(log, "`show ip route track-table`", sh(d, "show ip route track-table"))
    block(log, "`show ip route 0.0.0.0`(健全)", sh(d, "show ip route 0.0.0.0"))
    rate, out = ping_ok(d, DATA)
    log.append(f"- 健全時 ping {DATA} source Lo0: **{rate}%**")
    # 奥障害= RT02-RT04 断
    print("[i] p0: 奥障害(RT02 e0/2 shutdown)")
    conf(devs["RT02"], ["interface Ethernet0/2", "shutdown", "exit"])
    t_down = wait(lambda: track_state(d)[0] == "Down", timeout=180,
                  every=3, label="track down")
    log.append(f"- 奥障害から track Down まで **{t_down}s**"
               "(SLA frequency 10s・track delay 既定)")
    block(log, "`show track 1`(奥障害)", track_state(d)[1])
    block(log, "`show ip sla statistics`(奥障害・return code)", sla_stats(d))
    block(log, "`show ip route 0.0.0.0`(切替後)", sh(d, "show ip route 0.0.0.0"))
    rate, out = ping_ok(d, DATA)
    log.append(f"- 切替後 ping {DATA} source Lo0: **{rate}%**(backup 経由)")
    block(log, "切替後 ping", out)
    print("[i] p0: 復旧(no shutdown)")
    conf(devs["RT02"], ["interface Ethernet0/2", "no shutdown", "exit"])
    t_rec = wait(lambda: track_state(d)[0] == "Up", timeout=180,
                 every=3, label="track re-up")
    log.append(f"- 復旧から track Up まで **{t_rec}s**")
    rate, _ = ping_ok(d, DATA)
    log.append(f"- 復帰後 ping: **{rate}%**")


def p1(devs, log):
    """スケジュール済み SLA の編集ロック(%文言)と解除手順。"""
    d = devs["RT01"]
    # p0 の golden が生きている前提。稼働中の再入を試す
    errs, text = conf(d, ["ip sla 1"], log)
    block(log, "稼働中に `ip sla 1` 再入", text)
    errs, text = conf(d, ["ip sla 1", f"icmp-echo {DATA}"], log)
    block(log, "稼働中に定義変更を試行", text)
    # unschedule 後は編集できるか
    conf(d, ["no ip sla schedule 1"])
    errs, text = conf(d, ["ip sla 1", "frequency 20", "exit"], log)
    block(log, "unschedule 後に `frequency 20`", text)
    block(log, "unschedule 後の `show ip sla configuration`",
          sh(d, "show ip sla configuration"))
    # 再スケジュール→また動くか
    conf(d, ["ip sla schedule 1 life forever start-time now"])
    time.sleep(25)
    block(log, "再 schedule 後の `show ip sla statistics`", sla_stats(d))


def p2(devs, log):
    """schedule 未投入: track/statistics の見え方。"""
    d = devs["RT01"]
    reset_rt01(devs)
    golden(devs, schedule=False)
    time.sleep(45)
    st, out = track_state(d)
    log.append(f"- 未 schedule での track 状態: **{st}**")
    block(log, "`show track 1`(未 schedule)", out)
    block(log, "`show ip sla statistics`(未 schedule)", sla_stats(d))
    block(log, "`show ip route 0.0.0.0`(未 schedule)",
          sh(d, "show ip route 0.0.0.0"))
    rate, _ = ping_ok(d, DATA)
    log.append(f"- ping {DATA} source Lo0: **{rate}%**(どちら経由かは上の RIB)")


def p3(devs, log):
    """track が存在しない SLA を参照。"""
    d = devs["RT01"]
    reset_rt01(devs)
    golden(devs, track_sla=2)     # SLA 1 は稼働・track は SLA 2 を見る
    time.sleep(45)
    st, out = track_state(d)
    log.append(f"- 存在しない SLA 2 参照の track 状態: **{st}**")
    block(log, "`show track 1`(SLA 2 参照)", out)
    block(log, "`show ip route 0.0.0.0`", sh(d, "show ip route 0.0.0.0"))


def p4(devs, log):
    """path-echo: IOL での成立・no ip source-route の影響・return code。"""
    d = devs["RT01"]
    reset_rt01(devs)
    block(log, "RT02 `show run all | include source-route`(既定値)",
          sh(devs["RT02"], "show running-config all | include source-route"))
    errs, text = conf(d, ["ip sla 1",
                          f"path-echo {BEACON} source-ip 10.0.12.1",
                          "frequency 30", "exit"], log)
    block(log, "`path-echo` 定義の CLI 応答", text)
    if any("Invalid" in e or "Incomplete" in e for e in errs):
        log.append("- ★IOL は path-echo 非対応の疑い → icmp-path-echo 構文も試す")
        errs2, text2 = conf(d, ["ip sla 1",
                                f"icmp-path-echo {BEACON} source-ip 10.0.12.1",
                                "frequency 30", "exit"], log)
        block(log, "`icmp-path-echo` 定義の CLI 応答", text2)
        if any("Invalid" in e or "Incomplete" in e for e in errs2):
            log.append("- ★★path-echo 系は IOL で構成不可 → optype 層は udp/tcp 系で構成")
            return
    conf(d, ["ip sla schedule 1 life forever start-time now",
             "track 1 ip sla 1 reachability",
             f"ip route {BEACON} 255.255.255.255 10.0.12.2",
             "ip route 0.0.0.0 0.0.0.0 10.0.12.2 track 1",
             "ip route 0.0.0.0 0.0.0.0 10.0.13.2 200"])
    t_up = wait(lambda: track_state(d)[0] == "Up", timeout=150,
                label="pathecho up")
    log.append(f"- path-echo 健全時 track Up まで: **{t_up}s**(-1=上がらず)")
    block(log, "`show ip sla statistics`(path-echo 健全)", sla_stats(d))
    st, out = track_state(d)
    block(log, "`show track 1`(path-echo 健全)", out)
    # 経路上のハードニング
    print("[i] p4: RT02 no ip source-route")
    conf(devs["RT02"], ["no ip source-route"])
    time.sleep(90)
    st, out = track_state(d)
    log.append(f"- RT02 `no ip source-route` 後の track: **{st}**")
    block(log, "`show track 1`(source-route 遮断)", out)
    block(log, "`show ip sla statistics`(source-route 遮断・return code)",
          sla_stats(d))
    rate, _ = ping_ok(d, BEACON, source="Ethernet0/0")
    log.append(f"- 同時点の通常 ping ビーコン(source e0/0): **{rate}%**"
               "(ping は通るのに SLA だけ落ちるかの実証)")
    conf(devs["RT02"], ["ip source-route"])


def p5(devs, log):
    """udp-jitter: responder 無し/有りの return code。"""
    d = devs["RT01"]
    reset_rt01(devs)
    errs, text = conf(d, ["ip sla 1",
                          f"udp-jitter {BEACON} 17000 source-ip 10.0.12.1",
                          "frequency 10", "exit"], log)
    block(log, "`udp-jitter` 定義の CLI 応答", text)
    conf(d, ["ip sla schedule 1 life forever start-time now",
             "track 1 ip sla 1 reachability",
             f"ip route {BEACON} 255.255.255.255 10.0.12.2",
             "ip route 0.0.0.0 0.0.0.0 10.0.12.2 track 1",
             "ip route 0.0.0.0 0.0.0.0 10.0.13.2 200"])
    time.sleep(45)
    st, out = track_state(d)
    log.append(f"- responder 無しの track: **{st}**")
    block(log, "`show track 1`(responder 無し)", out)
    block(log, "`show ip sla statistics`(responder 無し・return code)",
          sla_stats(d))
    print("[i] p5: RT04 ip sla responder")
    conf(devs["RT04"], ["ip sla responder"])
    t_up = wait(lambda: track_state(d)[0] == "Up", timeout=120,
                label="jitter up")
    log.append(f"- responder 投入から track Up まで: **{t_up}s**")
    block(log, "`show ip sla statistics`(responder 有り・jitter 書式)",
          sla_stats(d))
    conf(devs["RT04"], ["no ip sla responder"])


def p6(devs, log):
    """tcp-connect: 実在ポート(RT04 vty telnet) vs 誤ポート。"""
    d = devs["RT01"]
    reset_rt01(devs)
    conf(devs["RT04"], ["line vty 0 4", "password cisco", "login",
                        "transport input telnet", "exit"])
    conf(d, ["ip sla 1",
             f"tcp-connect {DATA} 23 source-ip 10.0.12.1 control disable",
             "frequency 10", "exit",
             "ip sla schedule 1 life forever start-time now",
             "ip sla 2",
             f"tcp-connect {DATA} 8080 source-ip 10.0.12.1 control disable",
             "frequency 10", "exit",
             "ip sla schedule 2 life forever start-time now",
             "track 1 ip sla 1 reachability",
             "track 2 ip sla 2 reachability",
             f"ip route {BEACON} 255.255.255.255 10.0.12.2"], log)
    time.sleep(45)
    st1, out1 = track_state(d, 1)
    st2, out2 = track_state(d, 2)
    log.append(f"- tcp-connect 23(実在): track **{st1}** / "
               f"8080(誰も listen せず): track **{st2}**")
    block(log, "`show ip sla statistics 1`(port 23)", sla_stats(d, 1))
    block(log, "`show ip sla statistics 2`(port 8080・return code)",
          sla_stats(d, 2))


def p7(devs, log):
    """source 誤り2形: backup側IF(全滅するはず) / Lo0(非対称に成功するはず)。"""
    d = devs["RT01"]
    reset_rt01(devs)
    conf(d, ["ip sla 1",
             f"icmp-echo {BEACON} source-ip 10.0.13.1",   # backup 側 IF
             "frequency 10", "exit",
             "ip sla schedule 1 life forever start-time now",
             "ip sla 2",
             f"icmp-echo {BEACON} source-ip 1.1.1.1",     # Lo0(戻りは backup 経由)
             "frequency 10", "exit",
             "ip sla schedule 2 life forever start-time now",
             "track 1 ip sla 1 reachability",
             "track 2 ip sla 2 reachability",
             f"ip route {BEACON} 255.255.255.255 10.0.12.2",
             "ip route 0.0.0.0 0.0.0.0 10.0.12.2 track 1",
             "ip route 0.0.0.0 0.0.0.0 10.0.13.2 200"])
    time.sleep(45)
    st1, out1 = track_state(d, 1)
    st2, out2 = track_state(d, 2)
    log.append(f"- source=10.0.13.1(backup側IF): track **{st1}** / "
               f"source=1.1.1.1(Lo0): track **{st2}**")
    log.append("  (Lo0 は RT04 の戻りが backup 優先なので**非対称に成功**し、"
               "primary 監視になっていない不感形が成立するかの実証)")
    block(log, "`show ip sla statistics 1`(backup側IF source)", sla_stats(d, 1))
    block(log, "`show ip sla statistics 2`(Lo0 source)", sla_stats(d, 2))
    block(log, "`show track 1`", out1)
    block(log, "`show track 2`", out2)


def p8(devs, log):
    """こまごま: timeout>frequency・threshold 制約・AD 同値スタティック。"""
    d = devs["RT01"]
    reset_rt01(devs)
    errs, text = conf(d, ["ip sla 1",
                          f"icmp-echo {BEACON} source-ip 10.0.12.1",
                          "frequency 5", "timeout 20000", "exit"], log)
    block(log, "`timeout 20000`×`frequency 5` の CLI 応答", text)
    errs, text = conf(d, ["ip sla 1", "threshold 30000", "exit"], log)
    block(log, "`threshold 30000`(> timeout) の CLI 応答", text)
    block(log, "定義後の `show ip sla configuration`",
          sh(d, "show ip sla configuration"))
    # AD 同値の floating 不成立形
    reset_rt01(devs)
    golden(devs)
    wait(lambda: track_state(d)[0] == "Up", timeout=120, label="p8 up")
    conf(d, ["no ip route 0.0.0.0 0.0.0.0 10.0.13.2 200",
             "ip route 0.0.0.0 0.0.0.0 10.0.13.2"])   # AD1 で並置
    time.sleep(5)
    block(log, "`show ip route 0.0.0.0`(backup AD1 並置=ECMP?)",
          sh(d, "show ip route 0.0.0.0"))
    rate, _ = ping_ok(d, DATA, repeat=20)
    log.append(f"- ECMP 状態の ping {DATA}: **{rate}%**")
    conf(d, ["no ip route 0.0.0.0 0.0.0.0 10.0.13.2",
             "ip route 0.0.0.0 0.0.0.0 10.0.13.2 200"])


def p4b(devs, log):
    """path-echo 続編: 経路上の ip source-route を有効化すれば動くのか。

    ★run1 の発見= IOL(iol-xe)は `no ip source-route` が既定 → path-echo は
    健全構成でも Timeout。有効化で成立するなら「既定ハードニング×path-echo」が
    そのまま故障種になり、成立しないならプラットフォーム制約として記録する。
    """
    d = devs["RT01"]
    reset_rt01(devs)
    for r in ("RT01", "RT02", "RT03", "RT04"):
        conf(devs[r], ["ip source-route"])
    conf(d, ["ip sla 1",
             f"path-echo {BEACON} source-ip 10.0.12.1",
             "frequency 30", "exit",
             "ip sla schedule 1 life forever start-time now",
             "track 1 ip sla 1 reachability",
             f"ip route {BEACON} 255.255.255.255 10.0.12.2",
             "ip route 0.0.0.0 0.0.0.0 10.0.12.2 track 1",
             "ip route 0.0.0.0 0.0.0.0 10.0.13.2 200"])
    t_up = wait(lambda: track_state(d)[0] == "Up", timeout=180,
                label="pathecho up (source-route on)")
    log.append(f"- 全機 `ip source-route` 有効化での path-echo track Up: "
               f"**{t_up}s**(-1=上がらず)")
    block(log, "`show ip sla statistics`(path-echo・source-route 有効)",
          sla_stats(d))
    block(log, "`show ip sla statistics 1 details`(per-hop が出るか)",
          sh(d, "show ip sla statistics 1 details"))
    block(log, "`show track 1`", track_state(d)[1])
    if t_up >= 0:
        print("[i] p4b: RT02 だけ no ip source-route(故障種の単離)")
        conf(devs["RT02"], ["no ip source-route"])
        time.sleep(90)
        st, out = track_state(d)
        log.append(f"- RT02 のみ `no ip source-route` 後の track: **{st}**")
        block(log, "`show ip sla statistics`(RT02 のみ遮断)", sla_stats(d))
        rate, _ = ping_ok(d, BEACON, source="Ethernet0/0")
        log.append(f"- 同時点の通常 ping ビーコン: **{rate}%**")
    # 既定へ戻す
    for r in ("RT01", "RT02", "RT03", "RT04"):
        conf(devs[r], ["no ip source-route"])


def p6b(devs, log):
    """tcp-connect 再試: timeout 5000 を明示して schedule を通す。"""
    d = devs["RT01"]
    reset_rt01(devs)
    conf(devs["RT04"], ["line vty 0 4", "password cisco", "login",
                        "transport input telnet", "exit"])
    conf(d, ["ip sla 1",
             f"tcp-connect {DATA} 23 source-ip 10.0.12.1 control disable",
             "timeout 5000", "frequency 10", "exit",
             "ip sla schedule 1 life forever start-time now",
             "ip sla 2",
             f"tcp-connect {DATA} 8080 source-ip 10.0.12.1 control disable",
             "timeout 5000", "frequency 10", "exit",
             "ip sla schedule 2 life forever start-time now",
             "track 1 ip sla 1 reachability",
             "track 2 ip sla 2 reachability",
             f"ip route {BEACON} 255.255.255.255 10.0.12.2"], log)
    time.sleep(45)
    st1, _ = track_state(d, 1)
    st2, _ = track_state(d, 2)
    log.append(f"- tcp-connect 23(vty telnet): track **{st1}** / "
               f"8080(listen なし): track **{st2}**")
    block(log, "`show ip sla statistics 1`(port 23)", sla_stats(d, 1))
    block(log, "`show ip sla statistics 2`(port 8080・return code)",
          sla_stats(d, 2))


def p8b(devs, log):
    """schedule 時拒否の文言採取: timeout>frequency と threshold>timeout。"""
    d = devs["RT01"]
    reset_rt01(devs)
    conf(d, ["ip sla 1",
             f"icmp-echo {BEACON} source-ip 10.0.12.1",
             "frequency 5", "timeout 20000", "exit"])
    errs, text = conf(d, ["ip sla schedule 1 life forever start-time now"], log)
    block(log, "timeout 20000×frequency 5 の schedule 試行", text)
    block(log, "直後の `show ip sla statistics`(未稼働の指紋確認)", sla_stats(d))
    conf(d, ["ip sla 1", "timeout 4000", "threshold 30000", "exit"])
    errs, text = conf(d, ["ip sla schedule 1 life forever start-time now"], log)
    block(log, "threshold 30000×timeout 4000 の schedule 試行", text)
    # threshold は schedule を拒否するのか・稼働後 reachability に効かないのか
    conf(d, ["ip sla 1", "threshold 4000", "exit",
             "ip sla schedule 1 life forever start-time now",
             "track 1 ip sla 1 reachability",
             f"ip route {BEACON} 255.255.255.255 10.0.12.2"])
    time.sleep(30)
    st, out = track_state(d)
    log.append(f"- threshold 4000(=timeout・RTT よりはるか上)で稼働: track **{st}**"
               "(threshold は reachability 判定に効かないことの傍証は紙面用に別途)")


def p9(devs, log):
    """pin_missing= ビーコン /32 固定漏れ。平常時は機能し、障害→復旧後に
    フェイルバック不能のラッチになるか(プローブが backup 側 default を追い続ける)。"""
    d = devs["RT01"]
    reset_rt01(devs)
    golden(devs)
    conf(d, [f"no ip route {BEACON} 255.255.255.255 10.0.12.2"])   # 固定だけ抜く
    t_up = wait(lambda: track_state(d)[0] == "Up", timeout=120,
                label="p9 initial up")
    log.append(f"- /32 固定なしでも平常時は track Up(**{t_up}s**)="
               "プローブは default(primary) を追って成功=潜在故障")
    print("[i] p9: 奥障害(RT02 e0/2 shutdown)")
    conf(devs["RT02"], ["interface Ethernet0/2", "shutdown", "exit"])
    t_down = wait(lambda: track_state(d)[0] == "Down", timeout=120, every=3,
                  label="p9 down")
    log.append(f"- 奥障害→track Down: **{t_down}s**(切替自体は機能する)")
    print("[i] p9: 復旧(no shutdown)")
    conf(devs["RT02"], ["interface Ethernet0/2", "no shutdown", "exit"])
    t_back = wait(lambda: track_state(d)[0] == "Up", timeout=150, every=5,
                  label="p9 fail-back")
    if t_back < 0:
        log.append("- ★★復旧後 150s 経っても track Down のまま= "
                   "**フェイルバック不能ラッチの成立**(プローブが backup 側 "
                   "default を追ってビーコンに届かない)")
    else:
        log.append(f"- 復旧後 {t_back}s で track Up= ラッチは成立せず(要再考)")
    block(log, "復旧後の `show track 1`", track_state(d)[1])
    block(log, "復旧後の `show ip route 0.0.0.0`",
          sh(d, "show ip route 0.0.0.0"))
    block(log, "復旧後の `show ip sla statistics`", sla_stats(d))
    # fix= /32 固定の投入 → 回復するか
    conf(d, [f"ip route {BEACON} 255.255.255.255 10.0.12.2"])
    t_fix = wait(lambda: track_state(d)[0] == "Up", timeout=120, every=3,
                 label="p9 fix")
    log.append(f"- fix(/32 固定投入)から track Up まで: **{t_fix}s**")
    rate, _ = ping_ok(d, DATA)
    log.append(f"- fix 後 ping {DATA}: **{rate}%**(primary 復帰)")


def p6c(devs, log):
    """tcp-connect 再々試: p6/p6b は default route 抜きの自業自得(8.8.8.8 へ経路無し)。
    今回は素の default を入れ、まず telnet 素疎通を確認してから測る。"""
    d = devs["RT01"]
    reset_rt01(devs)
    conf(d, ["ip route 0.0.0.0 0.0.0.0 10.0.12.2"])
    conf(devs["RT04"], ["line vty 0 4", "password cisco", "login",
                        "transport input telnet", "exit"])
    out = sh(d, "telnet 8.8.8.8 /source-interface Ethernet0/0")
    block(log, "素の telnet 8.8.8.8(ベースライン)", out[:600])
    try:
        d.execute("\x1d", timeout=10)   # ^] で抜ける(開いていれば)
        d.execute("quit", timeout=10)
    except Exception:
        pass
    try:
        d.enable()
    except Exception:
        pass
    conf(d, ["ip sla 1",
             "tcp-connect 8.8.8.8 23 source-ip 10.0.12.1 control disable",
             "timeout 5000", "frequency 10", "exit",
             "ip sla schedule 1 life forever start-time now",
             "ip sla 2",
             "tcp-connect 8.8.8.8 8080 source-ip 10.0.12.1 control disable",
             "timeout 5000", "frequency 10", "exit",
             "ip sla schedule 2 life forever start-time now",
             "track 1 ip sla 1 reachability",
             "track 2 ip sla 2 reachability"], log)
    time.sleep(45)
    st1, _ = track_state(d, 1)
    st2, _ = track_state(d, 2)
    log.append(f"- tcp-connect 23(vty telnet): track **{st1}** / "
               f"8080(listen なし): track **{st2}**")
    block(log, "`show ip sla statistics 1`(port 23)", sla_stats(d, 1))
    block(log, "`show ip sla statistics 2`(port 8080・return code)",
          sla_stats(d, 2))
    conf(d, ["no ip route 0.0.0.0 0.0.0.0 10.0.12.2"])


CHECKS = {"p0": p0, "p1": p1, "p2": p2, "p3": p3, "p4": p4,
          "p5": p5, "p6": p6, "p7": p7, "p8": p8,
          "p4b": p4b, "p6b": p6b, "p8b": p8b, "p9": p9, "p6c": p6c}


def main():
    names = [a for a in sys.argv[1:] if a in CHECKS] or list(CHECKS)
    client = ClientLibrary(CML[0], CML[1], CML[2], ssl_verify=False)
    lab = ensure_lab(client)
    print("[i] コンソール接続...")
    devs = connect_all(lab)
    push_base(devs)
    stamp = time.strftime("%Y-%m-%d %H:%M")
    results = [f"\n\n# probe run {stamp} ({' '.join(names)})"]
    for name in names:
        print(f"[i] ==== {name} ====")
        log = [f"\n## {name}"]
        try:
            CHECKS[name](devs, log)
        except Exception as e:
            log.append(f"- ★探針が例外で中断: {type(e).__name__}: {e}")
            print(f"    [!] {name}: {type(e).__name__}: {e}")
        results += log
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("a") as f:
        f.write("\n".join(results) + "\n")
    print(f"[i] 結果を {OUT} へ追記した")


if __name__ == "__main__":
    main()
