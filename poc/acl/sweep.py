#!/usr/bin/env python3
"""BL-106 P0 PoC: ACL 単独読解 紙面ファミリの前提挙動スイープ。

設計メモ= problems/_drafts/ACL-PAPER.design.md §8(P1〜P10)。
CML に POC-ACL(IOL 3台)を作成し、コンソール直駆動で RT01 の ACL を組み替えて観測する。
mgmt/SSH は使わない(CVAC 罠回避・poc/ospfv3-pl の型を踏襲)。

トポロジ:
    RT03 --e0/0---e0/0-- RT01 --e0/1---e0/0-- RT02
    10.0.13.0/24                 10.0.12.0/24

  RT02(経路の出し手): Lo0 2.2.2.2/32
      Lo11 172.30.16.0/24  Lo12 172.30.17.0/26  Lo13 172.30.18.0/30  Lo14 172.30.32.0/24
  RT03(トラフィックの出し手 + 同一ネットワークアドレスで長さ違い):
      Lo0 3.3.3.3/32  Lo11 172.30.16.0/28  Lo99 203.0.113.5/32(EIGRP 非広告=uRPF 用の偽装元)

観測軸:
  P1  未定義 ACL 参照の帰結(interface / distribute-list / CoPP / uRPF / NAT)
  P2  distribute-list × 拡張 ACL の特殊解釈(src=ネットワーク・dst=サブネットマスク)
  P3  distribute-list × 標準 ACL はプレフィックス長を区別しない
  P4  outbound ACL は自機生成トラフィックに効かない
  P5  named ACL の seq 挿入・resequence・カウンタ保持 / 再作成での消滅
  P6  番号付き ACL の追記位置・同番再定義・named モードでの seq 挿入可否
  P7  time-range periodic の境界と非アクティブ ACE の扱い・show 書式
  P8  CoPP の deny ACE は class-default に落ちる
  P9  %SEC-6-IPACCESSLOGP の書式 / log 無しの行では記録が出ない
  P10 ワイルドカードにサブネットマスクを書いた場合の受理と表示
  P11 show ip access-lists の表示書式(remark / log / time-range 付き)
  P12 空の named ACL を適用した場合(暗黙 deny のみ)

使い方: sweep.py [チェック名...]   (無指定=全部)。結果は results-raw.md へ追記。
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
LAB_TITLE = "POC-ACL"
NODES = ["RT01", "RT02", "RT03"]

# EIGRP で RT01 が学ぶはずの経路(基線判定に使う)
LEARNED = ["2.2.2.2/32", "172.30.16.0/24", "172.30.17.0/26",
           "172.30.18.0/30", "172.30.32.0/24", "3.3.3.3/32", "172.30.16.0/28"]

BASE = {
    "RT01": [
        "no ip domain lookup", "ip routing",
        "interface Ethernet0/0", "description === to RT03 ===",
        "ip address 10.0.13.1 255.255.255.0", "no shutdown", "exit",
        "interface Ethernet0/1", "description === to RT02 ===",
        "ip address 10.0.12.1 255.255.255.0", "no shutdown", "exit",
        "interface Loopback0", "ip address 1.1.1.1 255.255.255.255", "exit",
        "router eigrp 100", "no auto-summary",
        "network 10.0.0.0 0.0.255.255", "network 1.1.1.1 0.0.0.0", "exit",
        "logging buffered 64000 informational",
        "no logging console",
    ],
    "RT02": [
        "no ip domain lookup", "ip routing",
        "interface Ethernet0/0", "description === to RT01 ===",
        "ip address 10.0.12.2 255.255.255.0", "no shutdown", "exit",
        "interface Loopback0", "ip address 2.2.2.2 255.255.255.255", "exit",
        "interface Loopback11", "ip address 172.30.16.1 255.255.255.0", "exit",
        "interface Loopback12", "ip address 172.30.17.1 255.255.255.192", "exit",
        "interface Loopback13", "ip address 172.30.18.1 255.255.255.252", "exit",
        "interface Loopback14", "ip address 172.30.32.1 255.255.255.0", "exit",
        "router eigrp 100", "no auto-summary",
        "network 10.0.0.0 0.0.255.255", "network 2.2.2.2 0.0.0.0",
        "network 172.30.0.0 0.0.255.255", "exit",
    ],
    "RT03": [
        "no ip domain lookup", "ip routing",
        "interface Ethernet0/0", "description === to RT01 ===",
        "ip address 10.0.13.3 255.255.255.0", "no shutdown", "exit",
        "interface Loopback0", "ip address 3.3.3.3 255.255.255.255", "exit",
        # ★RT02 の 172.30.16.0/24 と**同じネットワークアドレスで長さだけ違う**経路
        "interface Loopback11", "ip address 172.30.16.1 255.255.255.240", "exit",
        # EIGRP に載せない偽装元(uRPF 用)
        "interface Loopback99", "ip address 203.0.113.5 255.255.255.255", "exit",
        "router eigrp 100", "no auto-summary",
        "network 10.0.0.0 0.0.255.255", "network 3.3.3.3 0.0.0.0",
        "network 172.30.16.0 0.0.0.15", "exit",
    ],
}


# ---------------- CML / コンソール ----------------
# 張るリンク: (ノードA, A の IF, ノードB, B の IF)
LINKS = [("RT01", "Ethernet0/0", "RT03", "Ethernet0/0"),
         ("RT01", "Ethernet0/1", "RT02", "Ethernet0/0")]


def _iface(lab, label, ifname):
    """IF をラベルで引く。生成直後はクライアント側キャッシュが空なので sync する。"""
    for attempt in range(4):
        node = lab.get_node_by_label(label)
        for i in node.interfaces():
            if i.label == ifname:
                return i
        lab.sync(topology_only=True)
        time.sleep(1)
    raise RuntimeError(f"{label} に {ifname} が見つからない")


def ensure_lab(client):
    labs = client.find_labs_by_title(LAB_TITLE)
    if labs:
        lab = labs[0]
        print(f"[i] 既存ラボ {LAB_TITLE} ({lab.state()})")
    else:
        print(f"[i] ラボ {LAB_TITLE} を新規作成")
        lab = client.create_lab(LAB_TITLE)
    # --- ノード(不足分のみ作る) ---
    pos = {"RT03": (-220, 0), "RT01": (0, 0), "RT02": (220, 0)}
    have = {n.label for n in lab.nodes()}
    for label in NODES:
        if label in have:
            continue
        n = lab.create_node(label, "iol-xe", *pos[label],
                            populate_interfaces=True)
        n.configuration = f"hostname {label}\nno ip domain lookup\n"
    lab.sync(topology_only=True)
    # --- リンク(未結線のものだけ張る) ---
    # ★connect_two_nodes は新規 E1/x を作るため create_link で IF を明示する
    for a, aif, b, bif in LINKS:
        ia, ib = _iface(lab, a, aif), _iface(lab, b, bif)
        if ia.connected or ib.connected:
            continue
        print(f"[i] link {a} {aif} <-> {b} {bif}")
        lab.create_link(ia, ib)
    if lab.state() != "STARTED":
        print("[i] lab start...")
        lab.start(wait=True)
    for n in lab.nodes():
        print(f"    {n.label}: {n.state}")
    return lab


def connect_all(lab, required=("RT01",)):
    """★1台でも掴めなければ落とす、はやめる。

    コンソールは前回実行の残留セッションで一時的に掴めないことがある
    (AAA の PoC でも同じ事故があった)。RT01 以外は測定に使わないチェックが多いので、
    **必須ノードだけ**を落第条件にし、他は警告に留めて続行する。
    """
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
            print(f"    [!] {label}: console 接続不能 — このノードを使う"
                  f"チェックはスキップされる")
    return devs


def conf(dev, lines, log=None):
    """error 検知を切って流し、% 行だけ拾って記録する(受理/拒否の観測が主目的)。"""
    out = dev.configure(lines, error_pattern=[], timeout=120)
    text = out if isinstance(out, str) else "\n".join(
        v for v in out.values() if isinstance(v, str))
    errs = [ln.strip() for ln in text.splitlines() if ln.strip().startswith("%")]
    for e in errs:
        print(f"    ! {e}")
        if log is not None:
            log.append(f"- CLI応答: `{e}`")
    return errs


def sh(dev, cmd):
    return dev.execute(cmd, timeout=120)


def block(log, title, text):
    log.append(f"\n{title}:\n```\n{text.strip()}\n```")


PING_RX = re.compile(r"Success rate is (\d+) percent")


def ping(dev, dst, source=None, repeat=5, extra=""):
    cmd = f"ping {dst} repeat {repeat}"
    if source:
        cmd += f" source {source}"
    if extra:
        cmd += f" {extra}"
    out = dev.execute(cmd, timeout=120)
    m = PING_RX.search(out)
    return (int(m.group(1)) if m else -1), out


def routes(dev):
    return sh(dev, "show ip route eigrp | include /")


HDR_RX = re.compile(r"^\s+(\d+\.\d+\.\d+\.\d+)/(\d+) is (?:variably )?subnetted")
RT_RX = re.compile(r"^D(?:\s+EX)?\s+(\d+\.\d+\.\d+\.\d+)(?:/(\d+))?\s")


def learned_set(text):
    """`show ip route eigrp` から学習プレフィックス集合 {"net/len"} を作る。

    ★罠= 固定長ブロック(`1.0.0.0/32 is subnetted, 1 subnets`)配下の経路行には
    プレフィックス長が付かない(`D  2.2.2.2 [90/...]`)。長さは直前の見出し行から採る。
    """
    got, hdr_len = set(), None
    for line in (text or "").splitlines():
        m = HDR_RX.match(line)
        if m:
            hdr_len = m.group(2)
            continue
        m = RT_RX.match(line)
        if m:
            ln = m.group(2) or hdr_len
            if ln:
                got.add(f"{m.group(1)}/{ln}")
    return got


def eigrp_routes_detail(dev):
    """プレフィックス長まで確実に読める形で取る。"""
    return sh(dev, "show ip route eigrp")


def has_pfx(text, pfx):
    return pfx in learned_set(text)


def push_base(devs):
    """★毎回全ノードに投入する(全行が冪等)。

    「RT01 に router eigrp があれば全ノードskip」という判定にしていたら、
    途中で中断した前回実行の RT01 だけが設定済みで RT02/RT03 が素のまま、
    という状態を「設定済み」と誤認して基線が永久に揃わなかった(実測)。
    """
    for label in NODES:
        if label not in devs:
            print(f"[i] {label}: 未接続のため base 投入をスキップ")
            continue
        print(f"[i] {label}: base 設定を投入")
        conf(devs[label], BASE[label])


def wait_baseline(devs, timeout=240):
    t0 = time.time()
    out, got = "", set()
    while time.time() - t0 < timeout:
        out = eigrp_routes_detail(devs["RT01"])
        got = learned_set(out)
        if all(p in got for p in LEARNED):
            return time.time() - t0, out
        print(f"    基線待ち {time.time() - t0:.0f}s: "
              f"{len(got & set(LEARNED))}/{len(LEARNED)} 本")
        time.sleep(6)
    missing = [p for p in LEARNED if p not in got]
    raise RuntimeError(f"基線が揃わない(不足={missing}):\n{out}")


# =========================================================================
# チェック本体
# =========================================================================
def check_P1_undef(devs, log):
    """★未定義 ACL 参照の帰結をロール別に確定する。"""
    r1, r3 = devs["RT01"], devs["RT03"]

    # --- (a) interface: ip access-group(名前/番号とも未定義) ---
    log.append("\n#### P1a interface `ip access-group <未定義> in`")
    conf(r1, ["interface Ethernet0/0", "ip access-group NOEXIST-A in", "exit"], log)
    pct, out = ping(r3, "10.0.12.2", repeat=5)
    log.append(f"- RT03→RT02 通過率(名前・未定義): **{pct}%**")
    block(log, "RT01 `show ip interface Ethernet0/0 | include access list`",
          sh(r1, "show ip interface Ethernet0/0 | include access list"))
    conf(r1, ["interface Ethernet0/0", "no ip access-group NOEXIST-A in",
              "ip access-group 177 in", "exit"], log)
    pct2, _ = ping(r3, "10.0.12.2", repeat=5)
    log.append(f"- RT03→RT02 通過率(番号 177・未定義): **{pct2}%**")
    conf(r1, ["interface Ethernet0/0", "no ip access-group 177 in", "exit"])

    # --- (b) distribute-list ---
    log.append("\n#### P1b `distribute-list <未定義> in`(EIGRP)")
    conf(r1, ["router eigrp 100", "distribute-list NOEXIST-D in", "exit"], log)
    time.sleep(12)
    out = eigrp_routes_detail(r1)
    kept = [p for p in LEARNED if has_pfx(out, p)]
    log.append(f"- 残った学習経路: **{len(kept)}/{len(LEARNED)}** {kept}")
    block(log, "RT01 `show ip route eigrp`", out)
    conf(r1, ["router eigrp 100", "no distribute-list NOEXIST-D in", "exit"])
    time.sleep(10)

    # --- (c) CoPP class-map match access-group name <未定義> ---
    log.append("\n#### P1c CoPP `match access-group name <未定義>`")
    conf(r1, ["class-map match-all CM-UNDEF",
              "match access-group name NOEXIST-C", "exit",
              "policy-map PM-UNDEF", "class CM-UNDEF",
              "police 8000 conform-action transmit exceed-action transmit",
              "exit", "exit",
              "control-plane", "service-policy input PM-UNDEF", "exit"], log)
    sh(r1, "clear counters")
    ping(r3, "10.0.13.1", repeat=10)
    time.sleep(3)
    block(log, "RT01 `show policy-map control-plane input`",
          sh(r1, "show policy-map control-plane input"))
    conf(r1, ["control-plane", "no service-policy input PM-UNDEF", "exit",
              "no policy-map PM-UNDEF", "no class-map match-all CM-UNDEF"])

    # --- (d) uRPF 例外 ACL が未定義 ---
    log.append("\n#### P1d uRPF `ip verify unicast source reachable-via rx <未定義>`")
    conf(r1, ["interface Ethernet0/0",
              "ip verify unicast source reachable-via rx 178", "exit"], log)
    before = sh(r1, "show ip interface Ethernet0/0 | include verif|drop")
    ping(r3, "10.0.12.2", source="Loopback99", repeat=5)   # 203.0.113.5=経路なし
    after = sh(r1, "show ip interface Ethernet0/0 | include verif|drop")
    block(log, "偽装前 `show ip interface Ethernet0/0`(抜粋)", before)
    block(log, "偽装後(203.0.113.5 発を5発)", after)
    conf(r1, ["interface Ethernet0/0",
              "no ip verify unicast source reachable-via rx 178", "exit"])

    # --- (e) NAT ---
    log.append("\n#### P1e NAT `ip nat inside source list <未定義>`")
    conf(r1, ["interface Ethernet0/0", "ip nat inside", "exit",
              "interface Ethernet0/1", "ip nat outside", "exit",
              "ip nat inside source list NOEXIST-N interface Ethernet0/1 "
              "overload"], log)
    sh(r1, "clear ip nat translation *")
    ping(r3, "2.2.2.2", source="Loopback0", repeat=5)
    block(log, "RT01 `show ip nat translations`",
          sh(r1, "show ip nat translations"))
    conf(r1, ["no ip nat inside source list NOEXIST-N interface Ethernet0/1 "
              "overload",
              "interface Ethernet0/0", "no ip nat inside", "exit",
              "interface Ethernet0/1", "no ip nat outside", "exit"])


def check_P2_dl_ext(devs, log):
    """★distribute-list × 拡張 ACL: src=ネットワーク・dst=サブネットマスク。"""
    r1 = devs["RT01"]
    log.append("\n#### P2a 拡張 ACL で「/26 だけ」を通す "
               "(`permit ip host 172.30.17.0 host 255.255.255.192`)")
    conf(r1, ["ip access-list extended DL-EXT",
              "permit ip host 172.30.17.0 host 255.255.255.192", "exit",
              "router eigrp 100", "distribute-list DL-EXT in", "exit"], log)
    time.sleep(15)
    out = eigrp_routes_detail(r1)
    kept = [p for p in LEARNED if has_pfx(out, p)]
    log.append(f"- 残った学習経路: **{kept}**")
    block(log, "RT01 `show ip route eigrp`", out)
    block(log, "RT01 `show ip access-lists DL-EXT`",
          sh(r1, "show ip access-lists DL-EXT"))

    log.append("\n#### P2b 送信元をワイルドカード・宛先を any "
               "(`permit ip 172.30.16.0 0.0.15.255 any`)")
    conf(r1, ["ip access-list extended DL-EXT", "no permit ip host 172.30.17.0 "
              "host 255.255.255.192",
              "permit ip 172.30.16.0 0.0.15.255 any", "exit"], log)
    time.sleep(15)
    out = eigrp_routes_detail(r1)
    kept = [p for p in LEARNED if has_pfx(out, p)]
    log.append(f"- 残った学習経路: **{kept}**")
    block(log, "RT01 `show ip route eigrp`", out)
    conf(r1, ["router eigrp 100", "no distribute-list DL-EXT in", "exit",
              "no ip access-list extended DL-EXT"])
    time.sleep(12)


def check_P3_dl_std(devs, log):
    """★標準 ACL はプレフィックス長を区別しない(同一ネットワークアドレスの /24 と /28)。"""
    r1 = devs["RT01"]
    log.append("\n#### P3 標準 ACL `deny 172.30.16.0` + `permit any`")
    conf(r1, ["access-list 20 deny 172.30.16.0",
              "access-list 20 permit any",
              "router eigrp 100", "distribute-list 20 in", "exit"], log)
    time.sleep(15)
    out = eigrp_routes_detail(r1)
    log.append(f"- 172.30.16.0/24 残存: **{has_pfx(out, '172.30.16.0/24')}** / "
               f"172.30.16.0/28 残存: **{has_pfx(out, '172.30.16.0/28')}**")
    block(log, "RT01 `show ip route eigrp`", out)
    block(log, "RT01 `show ip access-lists 20`", sh(r1, "show ip access-lists 20"))
    conf(r1, ["router eigrp 100", "no distribute-list 20 in", "exit",
              "no access-list 20"])
    time.sleep(12)


def check_P4_out_self(devs, log):
    """★outbound ACL は自機生成トラフィックに効かない。"""
    r1, r3 = devs["RT01"], devs["RT03"]
    log.append("\n#### P4 `ip access-group BLOCK-ALL out` を RT01 e0/1 に適用")
    conf(r1, ["ip access-list extended BLOCK-ALL",
              "deny icmp any any", "permit ip any any", "exit",
              "interface Ethernet0/1", "ip access-group BLOCK-ALL out",
              "exit"], log)
    time.sleep(3)
    pct_self, _ = ping(r1, "10.0.12.2", repeat=5)
    pct_transit, _ = ping(r3, "10.0.12.2", repeat=5)
    log.append(f"- **RT01 自身 → RT02: {pct_self}%**(自機生成)")
    log.append(f"- **RT03 → RT02(RT01 を通過): {pct_transit}%**(転送)")
    block(log, "RT01 `show ip access-lists BLOCK-ALL`",
          sh(r1, "show ip access-lists BLOCK-ALL"))
    conf(r1, ["interface Ethernet0/1", "no ip access-group BLOCK-ALL out",
              "exit", "no ip access-list extended BLOCK-ALL"])


def check_P5_named_seq(devs, log):
    """★named ACL の seq 挿入・resequence・カウンタの保持/消滅。"""
    r1, r3 = devs["RT01"], devs["RT03"]
    log.append("\n#### P5 named ACL の seq 挿入・resequence・カウンタ")
    conf(r1, ["ip access-list extended SEQT",
              "10 permit icmp host 10.0.13.3 any",
              "20 permit ip host 3.3.3.3 any",
              "30 permit ip any any", "exit",
              "interface Ethernet0/0", "ip access-group SEQT in", "exit"], log)
    ping(r3, "10.0.12.2", repeat=5)
    block(log, "① 初期状態(5発通した後)", sh(r1, "show ip access-lists SEQT"))
    conf(r1, ["ip access-list extended SEQT",
              "15 deny udp any any eq 9999", "exit"], log)
    block(log, "② `15 deny udp any any eq 9999` を挿入した直後"
               "(★他行のカウンタが残るか)", sh(r1, "show ip access-lists SEQT"))
    conf(r1, ["ip access-list resequence SEQT 100 100"], log)
    block(log, "③ `ip access-list resequence SEQT 100 100` 後"
               "(★カウンタが残るか)", sh(r1, "show ip access-lists SEQT"))
    conf(r1, ["no ip access-list extended SEQT",
              "ip access-list extended SEQT",
              "10 permit icmp host 10.0.13.3 any",
              "20 permit ip any any", "exit"], log)
    block(log, "④ `no ip access-list` → 作り直した後(★カウンタは消えるか)",
          sh(r1, "show ip access-lists SEQT"))
    conf(r1, ["interface Ethernet0/0", "no ip access-group SEQT in", "exit",
              "no ip access-list extended SEQT"])


def check_P6_numbered(devs, log):
    """★番号付き ACL: 追記は末尾か・同番再定義は置換か・named モードで挿入できるか。"""
    r1 = devs["RT01"]
    log.append("\n#### P6 番号付き ACL の編集規則")
    conf(r1, ["access-list 150 permit ip host 10.0.13.3 any",
              "access-list 150 permit ip host 3.3.3.3 any"], log)
    block(log, "① 2行を順に追加", sh(r1, "show ip access-lists 150"))
    conf(r1, ["access-list 150 deny ip host 172.30.16.1 any"], log)
    block(log, "② さらに1行追加(★末尾に付くか・置換されないか)",
          sh(r1, "show ip access-lists 150"))
    errs = conf(r1, ["ip access-list extended 150",
                     "15 permit tcp any any eq 22", "exit"], log)
    block(log, "③ ★`ip access-list extended 150` に入って `15 permit ...` "
               "(番号付きでも seq 挿入できるか)", sh(r1, "show ip access-lists 150"))
    log.append(f"- ③ の CLI エラー: {errs or 'なし(受理)'}")
    conf(r1, ["no access-list 150"])
    block(log, "④ `no access-list 150` 後", sh(r1, "show ip access-lists 150"))


def check_P7_timerange(devs, log):
    """★time-range periodic の境界・非アクティブ ACE の扱い・show 書式。"""
    r1, r3 = devs["RT01"], devs["RT03"]
    log.append("\n#### P7 time-range periodic")
    conf(r1, ["time-range WORKHOURS", "periodic weekdays 09:00 to 17:00", "exit",
              "ip access-list extended TRT",
              "10 deny icmp any any time-range WORKHOURS",
              "20 permit ip any any", "exit",
              "interface Ethernet0/0", "ip access-group TRT in", "exit"], log)
    for label, clock in [("平日 10:00(範囲内)", "10:00:00 10 Aug 2026"),
                         ("平日 18:30(範囲外)", "18:30:00 10 Aug 2026"),
                         ("土曜 10:00(曜日外)", "10:00:00 15 Aug 2026")]:
        sh(r1, f"clock set {clock}")
        time.sleep(3)
        pct, _ = ping(r3, "10.0.12.2", repeat=3)
        log.append(f"\n- **{label}** → RT03→RT02 の ICMP 通過率: **{pct}%**")
        block(log, "  `show time-range WORKHOURS`",
              sh(r1, "show time-range WORKHOURS"))
        block(log, "  `show ip access-lists TRT`(★非アクティブ時の表示)",
              sh(r1, "show ip access-lists TRT"))
    conf(r1, ["interface Ethernet0/0", "no ip access-group TRT in", "exit",
              "no ip access-list extended TRT", "no time-range WORKHOURS"])


def check_P8_copp_deny(devs, log):
    """★CoPP: deny の ACE は「通す」ではなく class-default へ落ちる。"""
    r1, r3 = devs["RT01"], devs["RT03"]
    log.append("\n#### P8 CoPP の deny ACE は class-default 行き")
    conf(r1, ["ip access-list extended CP-ICMP",
              "deny icmp host 10.0.13.3 any",     # ★この deny が主題
              "permit icmp any any", "exit",
              "class-map match-all CM-ICMP", "match access-group name CP-ICMP",
              "exit",
              "policy-map PM-COPP",
              "class CM-ICMP",
              "police 8000 conform-action transmit exceed-action transmit",
              "exit",
              "class class-default",
              "police 8000 conform-action transmit exceed-action transmit",
              "exit", "exit",
              "control-plane", "service-policy input PM-COPP", "exit"], log)
    sh(r1, "clear counters")
    time.sleep(2)
    ping(r3, "10.0.13.1", repeat=10)            # ★deny 対象(10.0.13.3 発)
    ping(devs["RT02"], "10.0.12.1", repeat=10)  # permit 対象(RT02 発)
    time.sleep(3)
    block(log, "RT01 `show policy-map control-plane input`"
               "(★10.0.13.3 発の 10発がどちらのクラスに計上されるか)",
          sh(r1, "show policy-map control-plane input"))
    block(log, "RT01 `show ip access-lists CP-ICMP`",
          sh(r1, "show ip access-lists CP-ICMP"))
    conf(r1, ["control-plane", "no service-policy input PM-COPP", "exit",
              "no policy-map PM-COPP", "no class-map match-all CM-ICMP",
              "no ip access-list extended CP-ICMP"])


def check_P9_log(devs, log):
    """★%SEC-6-IPACCESSLOGP の書式 / log 無しの行では記録が出ない。"""
    r1, r3 = devs["RT01"], devs["RT03"]
    log.append("\n#### P9 ACL ログの書式")
    conf(r1, ["ip access-list extended LOGT",
              "10 deny tcp any any eq 22 log",
              "20 deny icmp any any",            # ★log 無し=記録されないはず
              "30 permit ip any any", "exit",
              "interface Ethernet0/0", "ip access-group LOGT in", "exit"], log)
    sh(r1, "clear logging")
    r3.execute("telnet 10.0.12.2 22 /source-interface Loopback0 /timeout 3",
               timeout=90)
    ping(r3, "10.0.12.2", repeat=3)
    time.sleep(8)
    block(log, "RT01 `show logging | include SEC-6`",
          sh(r1, "show logging | include SEC-6"))
    block(log, "RT01 `show ip access-lists LOGT`(★log 無しの行もカウンタは進む)",
          sh(r1, "show ip access-lists LOGT"))
    conf(r1, ["interface Ethernet0/0", "no ip access-group LOGT in", "exit",
              "no ip access-list extended LOGT"])


def check_P10_mask(devs, log):
    """★ワイルドカードにサブネットマスクを書いた場合の受理と表示。"""
    r1 = devs["RT01"]
    log.append("\n#### P10 ワイルドカード ⇄ サブネットマスク取り違え")
    errs = conf(r1, ["access-list 90 permit 10.0.0.0 255.0.0.0",
                     "access-list 91 permit 192.168.1.0 255.255.255.0",
                     "access-list 92 permit 10.0.0.0 0.255.255.255"], log)
    log.append(f"- CLI エラー: {errs or 'なし(3本とも受理)'}")
    block(log, "RT01 `show ip access-lists 90`(255.0.0.0 と書いた場合)",
          sh(r1, "show ip access-lists 90"))
    block(log, "RT01 `show ip access-lists 91`(255.255.255.0 と書いた場合)",
          sh(r1, "show ip access-lists 91"))
    block(log, "RT01 `show ip access-lists 92`(正しく 0.255.255.255)",
          sh(r1, "show ip access-lists 92"))
    block(log, "RT01 `show running-config | include access-list 9`",
          sh(r1, "show running-config | include access-list 9"))
    conf(r1, ["no access-list 90", "no access-list 91", "no access-list 92"])


def check_P11_display(devs, log):
    """★show ip access-lists の表示書式(remark / log / 名前ポート / 非連続WC)。"""
    r1 = devs["RT01"]
    log.append("\n#### P11 表示書式(紙面の read 形の忠実性のため)")
    conf(r1, ["ip access-list extended DISPT",
              "remark === display test ===",
              "10 permit tcp 10.0.13.0 0.0.0.255 any eq 22",
              "20 permit tcp any host 172.30.16.1 eq www log",
              "30 permit udp any any range 16384 32767",
              "40 permit icmp any any echo-reply",
              "50 deny tcp any any established",
              "60 permit ip 10.0.0.0 0.0.1.255 any", "exit"], log)
    block(log, "RT01 `show ip access-lists DISPT`",
          sh(r1, "show ip access-lists DISPT"))
    block(log, "RT01 `show running-config | section ip access-list extended DISPT`",
          sh(r1, "show running-config | section ip access-list extended DISPT"))
    conf(r1, ["no ip access-list extended DISPT"])


def check_P12_empty(devs, log):
    """★空の named ACL を適用したら全断か全通か。"""
    r1, r3 = devs["RT01"], devs["RT03"]
    log.append("\n#### P12 空の named ACL を適用")
    conf(r1, ["ip access-list extended EMPTYT", "exit",
              "interface Ethernet0/0", "ip access-group EMPTYT in", "exit"], log)
    time.sleep(3)
    pct, _ = ping(r3, "10.0.12.2", repeat=5)
    log.append(f"- RT03→RT02 通過率: **{pct}%**")
    block(log, "RT01 `show ip access-lists EMPTYT`",
          sh(r1, "show ip access-lists EMPTYT"))
    conf(r1, ["interface Ethernet0/0", "no ip access-group EMPTYT in", "exit",
              "no ip access-list extended EMPTYT"])


def conf_each(dev, lines, log=None):
    """【使用禁止・失敗の記録】1行ずつ別セッションで投入する版。

    ★これは**壊れている**。`dev.configure([1行])` は毎回 config モードに入り直すため、
    `ip access-list extended X` の次の `permit ...` や `router eigrp` の次の
    `distribute-list ...` が**グローバル config で実行され** `% Invalid input` になる。
    P2 の 2 回目の測定はこれで「拡張 ACL は distribute-list に使えない」という
    偽の結論を出しかけた。階層を保ったまま行ごとの応答を採るには conf_trace を使う。
    """
    raise RuntimeError("conf_each は階層を壊す。conf_trace を使うこと")


def conf_trace(dev, lines, log=None):
    """★階層を保ったまま(1セッション)投入し、応答を**行に帰属**させて記録する。

    出力は「コマンドのエコー」→「その応答」の並びなので、次のコマンドのエコーが
    現れるまでに出た `%` 行を直前のコマンドの応答とみなす。
    """
    out = dev.configure(lines, error_pattern=[], timeout=120)
    text = out if isinstance(out, str) else "\n".join(
        v for v in out.values() if isinstance(v, str))
    pending = list(lines)
    cur, res = None, []
    for raw in text.splitlines():
        s = raw.strip()
        if pending and s.endswith(pending[0].strip()):
            cur = pending.pop(0)
            res.append([cur, []])
            continue
        if s.startswith("%") and res:
            res[-1][1].append(s)
    if log is not None:
        for cmd, errs in res:
            log.append(f"- `{cmd}` → " + (f"**{errs[0]}**" if errs else "受理"))
        for cmd in pending:
            log.append(f"- `{cmd}` → (エコー未検出)")
    return res


def check_P2C_dl_ext(devs, log):
    """★P2 三度目: 拡張 ACL × distribute-list(階層を保って投入)。

    2回目は conf_each の不具合で全コマンドがグローバル config に落ちており、
    「拡張 ACL は使えない」という誤結論を出しかけた。今回は 1 セッションで投入し、
    `show ip protocols` で**distribute-list が実際に効いている**ことも確認する。
    """
    r1 = devs["RT01"]

    def protocols():
        return sh(r1, "show ip protocols | include Incoming|Outgoing|filter|list")

    for label, setup, teardown in [
        ("P2C-a 名前付き拡張 ACL",
         ["ip access-list extended DLX",
          "permit ip host 172.30.17.0 host 255.255.255.192", "exit",
          "router eigrp 100", "distribute-list DLX in", "exit"],
         ["router eigrp 100", "no distribute-list DLX in", "exit",
          "no ip access-list extended DLX"]),
        ("P2C-b 番号付き拡張 ACL 130(/26 のマスクをちょうど指定)",
         ["access-list 130 permit ip host 172.30.17.0 host 255.255.255.192",
          "router eigrp 100", "distribute-list 130 in", "exit"],
         ["router eigrp 100", "no distribute-list 130 in", "exit",
          "no access-list 130"]),
        ("P2C-c 番号付き拡張 130(送信元=網をWC・宛先=マスクは any)",
         ["access-list 130 permit ip 172.30.16.0 0.0.15.255 any",
          "router eigrp 100", "distribute-list 130 in", "exit"],
         ["router eigrp 100", "no distribute-list 130 in", "exit",
          "no access-list 130"]),
        ("P2C-d 番号付き拡張 130(★宛先=マスクだけ /24 に固定)",
         ["access-list 130 permit ip any host 255.255.255.0",
          "router eigrp 100", "distribute-list 130 in", "exit"],
         ["router eigrp 100", "no distribute-list 130 in", "exit",
          "no access-list 130"]),
    ]:
        log.append(f"\n#### {label}")
        conf_trace(r1, setup, log)
        time.sleep(15)
        out = eigrp_routes_detail(r1)
        log.append(f"- 残った学習経路: **{sorted(learned_set(out) & set(LEARNED))}**")
        block(log, "  `show ip protocols`(適用の確認)", protocols())
        conf(r1, teardown)
        time.sleep(12)


def check_P2E_dl_semantics(devs, log):
    """★P2 四度目: 拡張 ACL × distribute-list の**実際の意味**を切り分ける。

    P2C で「番号付き拡張 ACL は受理・適用されるが、どの書き方でも全経路が消えた」
    (= permit 行が何にも一致していない)。定説の「src=ネットワーク・dst=サブネット
    マスク」がこの機種で成り立っていない可能性が高い。
    以下の4本で「そもそも評価されているか」「src は何を指すか」を確定する。
    """
    r1 = devs["RT01"]
    cases = [
        ("E1 `permit ip any any`(健全性確認=評価されているなら全部残る)",
         "access-list 131 permit ip any any"),
        ("E2 `permit ip host 172.30.17.0 any`(src=ネットワークだけ・dst 無指定)",
         "access-list 131 permit ip host 172.30.17.0 any"),
        ("E3 `permit ip host 10.0.12.2 any`(★src=広告元ルータ説の検証)",
         "access-list 131 permit ip host 10.0.12.2 any"),
        ("E4 `permit ip host 172.30.17.0 host 255.255.255.192`(定説どおりの書式)",
         "access-list 131 permit ip host 172.30.17.0 host 255.255.255.192"),
        ("E5 `permit ip 172.30.0.0 0.0.255.255 any`(src=網をWCで広く)",
         "access-list 131 permit ip 172.30.0.0 0.0.255.255 any"),
    ]
    for label, ace in cases:
        log.append(f"\n#### P2E-{label}")
        conf_trace(r1, ["no access-list 131", ace,
                        "router eigrp 100", "distribute-list 131 in", "exit"], log)
        time.sleep(15)
        out = eigrp_routes_detail(r1)
        got = sorted(learned_set(out) & set(LEARNED))
        log.append(f"- 残った学習経路 **{len(got)}/{len(LEARNED)}**: {got}")
        block(log, "  `show ip access-lists 131`(★どの行が何回当たったか)",
              sh(r1, "show ip access-lists 131"))
        conf(r1, ["router eigrp 100", "no distribute-list 131 in", "exit"])
        time.sleep(10)
    conf(r1, ["no access-list 131"])


def check_P2F_dst_field(devs, log):
    """★P2 五度目: 拡張 ACL の**宛先フィールド**が何を指すかを確定する。

    P2E で src = **広告元の隣接ルータ**と判明した(`host 10.0.12.2` で RT02 発の
    5本だけ残った)。定説の「src=ネットワーク・dst=サブネットマスク」は不成立。
    残るは dst が「広告されたネットワーク」かどうか。
    """
    r1 = devs["RT01"]
    RT02_ROUTES = ["2.2.2.2/32", "172.30.16.0/24", "172.30.17.0/26",
                   "172.30.18.0/30", "172.30.32.0/24"]
    cases = [
        ("F1 `permit ip any host 172.30.17.0`(dst=広告された網 説)",
         "access-list 132 permit ip any host 172.30.17.0"),
        ("F2 `permit ip host 10.0.12.2 host 172.30.17.0`(src と dst の両掛け)",
         "access-list 132 permit ip host 10.0.12.2 host 172.30.17.0"),
        ("F3 `permit ip any 172.30.16.0 0.0.15.255`(dst をWCで 16〜31 に)",
         "access-list 132 permit ip any 172.30.16.0 0.0.15.255"),
        ("F4 ★`permit ip any host 172.30.16.0`(同一網アドレスの /24 と /28 を"
         "区別できるか)",
         "access-list 132 permit ip any host 172.30.16.0"),
    ]
    for label, ace in cases:
        log.append(f"\n#### P2F-{label}")
        conf_trace(r1, ["no access-list 132", ace,
                        "router eigrp 100", "distribute-list 132 in", "exit"], log)
        time.sleep(15)
        out = eigrp_routes_detail(r1)
        got = sorted(learned_set(out) & set(LEARNED))
        log.append(f"- 残った学習経路 **{len(got)}/{len(LEARNED)}**: {got}")
        if set(got) == set(RT02_ROUTES):
            log.append("  → **RT02 発の5本とちょうど一致**")
        block(log, "  `show ip access-lists 132`", sh(r1, "show ip access-lists 132"))
        conf(r1, ["router eigrp 100", "no distribute-list 132 in", "exit"])
        time.sleep(10)
    conf(r1, ["no access-list 132"])


def check_P15_undef_vs_empty(devs, log):
    """★P15(BL-106 P1c 用): 「未定義」「空」「名前付き拡張」は**出力で区別できるか**。

    紙面の evidence 形(「次に取得すべき出力はどれか」)は、この3つが症状では
    区別できないことを前提に成立する。区別の手掛かりがどの出力に現れるかを確定する。
    ★特に未検証だったのは「**未定義の名前を distribute-list が参照すると、
    IOS が空の標準 ACL を自動生成してしまうのか**」。生成されるなら
    「未定義」と「空」は同一になり、仮説として立てられない。
    """
    r1 = devs["RT01"]

    def snapshot(tag):
        block(log, f"  {tag} `show ip access-lists`",
              sh(r1, "show ip access-lists") or "(空)")
        block(log, f"  {tag} `show running-config | include distribute-list`",
              sh(r1, "show running-config | include distribute-list") or "(空)")
        block(log, f"  {tag} `show ip protocols | include Incoming`",
              sh(r1, "show ip protocols | include Incoming"))

    log.append("\n#### P15-a 未定義の**名前**を distribute-list が参照する")
    conf_trace(r1, ["router eigrp 100", "distribute-list NOSUCHLIST in",
                    "exit"], log)
    time.sleep(8)
    snapshot("未定義(名前)")
    out = eigrp_routes_detail(r1)
    log.append(f"- 残った学習経路: **{len(learned_set(out) & set(LEARNED))}/7**")
    conf(r1, ["router eigrp 100", "no distribute-list NOSUCHLIST in", "exit",
              "no ip access-list standard NOSUCHLIST"])

    log.append("\n#### P15-b 未定義の**番号**を distribute-list が参照する")
    conf_trace(r1, ["router eigrp 100", "distribute-list 77 in", "exit"], log)
    time.sleep(8)
    snapshot("未定義(番号)")
    conf(r1, ["router eigrp 100", "no distribute-list 77 in", "exit",
              "no access-list 77"])

    log.append("\n#### P15-c **空**の名前付き標準 ACL を参照する")
    conf_trace(r1, ["ip access-list standard EMPTYLIST", "exit",
                    "router eigrp 100", "distribute-list EMPTYLIST in",
                    "exit"], log)
    time.sleep(8)
    snapshot("空")
    conf(r1, ["router eigrp 100", "no distribute-list EMPTYLIST in", "exit",
              "no ip access-list standard EMPTYLIST"])

    log.append("\n#### P15-d **名前付き拡張**を参照する(拒否されるはず)")
    conf_trace(r1, ["ip access-list extended EXTLIST",
                    "permit ip host 10.0.12.2 any", "exit",
                    "router eigrp 100", "distribute-list EXTLIST in",
                    "exit"], log)
    time.sleep(8)
    snapshot("名前付き拡張")
    conf(r1, ["router eigrp 100", "no distribute-list EXTLIST in", "exit",
              "no ip access-list extended EXTLIST"])
    time.sleep(8)


# ===========================================================================
# V系(BL-106 P3): IPv6 traffic-filter の挙動。IPv4 ACL との**差分**が主題。
# ===========================================================================
V6 = {
    "RT01": ["ipv6 unicast-routing",
             "interface Ethernet0/0", "ipv6 address 2001:DB8:13::1/64",
             "ipv6 enable", "exit",
             "interface Ethernet0/1", "ipv6 address 2001:DB8:12::1/64",
             "ipv6 enable", "exit",
             "ipv6 route 2001:DB8:2::2/128 2001:DB8:12::2",
             "ipv6 route 2001:DB8:3::3/128 2001:DB8:13::3"],
    "RT02": ["ipv6 unicast-routing",
             "interface Ethernet0/0", "ipv6 address 2001:DB8:12::2/64",
             "ipv6 enable", "exit",
             "interface Loopback0", "ipv6 address 2001:DB8:2::2/128", "exit",
             "ipv6 route 2001:DB8:3::3/128 2001:DB8:12::1",
             "ipv6 route 2001:DB8:13::/64 2001:DB8:12::1"],
    "RT03": ["ipv6 unicast-routing",
             "interface Ethernet0/0", "ipv6 address 2001:DB8:13::3/64",
             "ipv6 enable", "exit",
             "interface Loopback0", "ipv6 address 2001:DB8:3::3/128", "exit",
             "ipv6 route 2001:DB8:2::2/128 2001:DB8:13::1",
             "ipv6 route 2001:DB8:12::/64 2001:DB8:13::1"],
}


def _v6_base(devs, log):
    for label in ("RT01", "RT02", "RT03"):
        if label in devs:
            conf(devs[label], V6[label], log)
    time.sleep(3)


def _ping6(dev, dst, source=None, repeat=5):
    cmd = f"ping ipv6 {dst} repeat {repeat}"
    if source:
        cmd += f" source {source}"
    out = dev.execute(cmd, timeout=120)
    m = PING_RX.search(out)
    return (int(m.group(1)) if m else -1), out


def check_V1_ipv6_basics(devs, log):
    """★V1: `show ipv6 access-list` の書式 / プレフィックス長表記 / 暗黙 permit の有無。"""
    r1 = devs["RT01"]
    log.append("\n#### V1 IPv6 ACL の基本(書式・表記・暗黙のエントリ)")
    _v6_base(devs, log)
    pct, _ = _ping6(devs["RT03"], "2001:DB8:2::2", source="Loopback0")
    log.append(f"- 基線(RT03→RT02 の v6 疎通): **{pct}%**")
    conf_trace(r1, ["ipv6 access-list V6T",
                    "permit tcp 2001:DB8:13::/64 any eq 22",
                    "permit ipv6 host 2001:DB8:3::3 host 2001:DB8:2::2",
                    "exit"], log)
    block(log, "RT01 `show ipv6 access-list V6T`(★書式と暗黙エントリ)",
          sh(r1, "show ipv6 access-list V6T"))
    block(log, "RT01 `show running-config | section ipv6 access-list`",
          sh(r1, "show running-config | section ipv6 access-list"))
    # ★ワイルドカード表記が使えるか(IPv4 との差分)
    errs = conf(r1, ["ipv6 access-list V6WC",
                     "permit ipv6 2001:DB8:13::/64 0.0.0.255 any", "exit"], log)
    log.append(f"- ワイルドカード表記の可否: "
               f"**{'拒否' if errs else '受理(要確認)'}**")
    conf(r1, ["no ipv6 access-list V6WC"])


def check_V2_implicit_nd(devs, log):
    """★★V2(本命): 暗黙の deny では ND が生き、**明示 deny を書くと隣接が壊れる**か。

    IPv4 ACL には無い IPv6 固有の落とし穴。紙面の最大の考えさせポイントになる。
    """
    r1, r3 = devs["RT01"], devs["RT03"]
    log.append("\n#### V2 ★暗黙 deny と明示 deny で ND の生死が変わるか")

    def probe(tag):
        sh(r1, "clear ipv6 neighbors")
        time.sleep(3)
        pct, _ = _ping6(r1, "2001:DB8:13::3", repeat=5)
        nb = sh(r1, "show ipv6 neighbors 2001:DB8:13::3")
        thr, _ = _ping6(r3, "2001:DB8:2::2", source="Loopback0", repeat=5)
        log.append(f"\n- **{tag}**: RT01→RT03 直結 ping **{pct}%** / "
                   f"RT03→RT02 通過 **{thr}%**")
        block(log, "  `show ipv6 neighbors 2001:DB8:13::3`", nb or "(空)")

    log.append("\n**(a) 暗黙の deny のみ**(明示の deny 行を書かない)")
    conf(r1, ["ipv6 access-list V6ND",
              "permit ipv6 2001:DB8:13::/64 any", "exit",
              "interface Ethernet0/0", "ipv6 traffic-filter V6ND in", "exit"], log)
    probe("暗黙 deny のみ")
    block(log, "  `show ipv6 access-list V6ND`", sh(r1, "show ipv6 access-list V6ND"))

    log.append("\n**(b) 末尾に明示の `deny ipv6 any any` を追加**")
    conf(r1, ["ipv6 access-list V6ND", "deny ipv6 any any", "exit"], log)
    probe("明示 deny あり")
    block(log, "  `show ipv6 access-list V6ND`", sh(r1, "show ipv6 access-list V6ND"))

    log.append("\n**(c) 明示 deny の手前に ND を明示許可**"
               "(`permit icmp any any nd-ns` / `nd-na`)")
    conf_trace(r1, ["ipv6 access-list V6ND",
                    "no deny ipv6 any any",
                    "permit icmp any any nd-ns",
                    "permit icmp any any nd-na",
                    "deny ipv6 any any", "exit"], log)
    probe("ND 明示許可あり")
    block(log, "  `show ipv6 access-list V6ND`", sh(r1, "show ipv6 access-list V6ND"))
    conf(r1, ["interface Ethernet0/0", "no ipv6 traffic-filter V6ND in", "exit",
              "no ipv6 access-list V6ND"])


def check_V3_undef_empty(devs, log):
    """★V3: 未定義 / 空の `ipv6 traffic-filter` の帰結(IPv4 は全許可だった)。"""
    r1, r3 = devs["RT01"], devs["RT03"]
    log.append("\n#### V3 未定義・空の IPv6 ACL")
    for tag, setup, teardown in [
        ("未定義",
         ["interface Ethernet0/0", "ipv6 traffic-filter NOSUCH6 in", "exit"],
         ["interface Ethernet0/0", "no ipv6 traffic-filter NOSUCH6 in", "exit",
          "no ipv6 access-list NOSUCH6"]),
        ("空",
         ["ipv6 access-list EMPTY6", "exit",
          "interface Ethernet0/0", "ipv6 traffic-filter EMPTY6 in", "exit"],
         ["interface Ethernet0/0", "no ipv6 traffic-filter EMPTY6 in", "exit",
          "no ipv6 access-list EMPTY6"]),
    ]:
        conf_trace(r1, setup, log)
        time.sleep(3)
        pct, _ = _ping6(r3, "2001:DB8:2::2", source="Loopback0", repeat=5)
        log.append(f"- **{tag}**: RT03→RT02 通過 **{pct}%**")
        block(log, f"  `show ipv6 access-list`({tag})",
              sh(r1, "show ipv6 access-list") or "(空)")
        block(log, f"  `show ipv6 interface Ethernet0/0 | include filter|list`",
              sh(r1, "show ipv6 interface Ethernet0/0 | include filter|list"))
        conf(r1, teardown)


def check_V4_seq(devs, log):
    """★V4: sequence 番号による挿入・カウンタ・resequence(IPv4 との差)。"""
    r1, r3 = devs["RT01"], devs["RT03"]
    log.append("\n#### V4 sequence の扱いとカウンタ")
    conf_trace(r1, ["ipv6 access-list V6SEQ",
                    "sequence 10 permit ipv6 2001:DB8:13::/64 any",
                    "sequence 30 deny ipv6 any any", "exit",
                    "interface Ethernet0/0", "ipv6 traffic-filter V6SEQ in",
                    "exit"], log)
    _ping6(r3, "2001:DB8:2::2", source="Loopback0", repeat=3)
    block(log, "① 通した後", sh(r1, "show ipv6 access-list V6SEQ"))
    conf_trace(r1, ["ipv6 access-list V6SEQ",
                    "sequence 20 deny tcp any any eq 23", "exit"], log)
    block(log, "② `sequence 20` を挿入(★他行のカウンタが残るか)",
          sh(r1, "show ipv6 access-list V6SEQ"))
    errs = conf(r1, ["ipv6 access-list resequence V6SEQ 100 100"], log)
    log.append(f"- resequence の可否: **{'不可' if errs else '可'}**")
    block(log, "③ resequence 後", sh(r1, "show ipv6 access-list V6SEQ"))
    conf(r1, ["interface Ethernet0/0", "no ipv6 traffic-filter V6SEQ in", "exit",
              "no ipv6 access-list V6SEQ"])


def check_C1_routemap_semantics(devs, log):
    """★★C1: **route-map 経由だと拡張 ACL の意味論が切り替わる**という仮説の検証。

    ユーザ提供の外部レポート(2件)が「EIGRP inbound × 番号付き拡張 ACL の**直接指定**は
    src=route source / dst=網。**route-map 経由**では src=網 / dst=サブネットマスク」
    と述べている。前者は P2E/P2F の実測と一致する。後者が本当なら、
    **拡張 ACL でもプレフィックス長を絞れる**ことになり、紙面 shape=acl の
    要件世界 `prefixlen_exact`(「prefix-list しか手がない」)が**崩れる**。
    """
    r1 = devs["RT01"]
    log.append("\n#### C1 route-map 経由の拡張 ACL の意味論")
    cases = [
        ("C1a 対照 `permit ip any any`(機構が動くか)",
         "access-list 150 permit ip any any"),
        ("C1b ★教科書形 `permit ip host 172.30.17.0 host 255.255.255.192`"
         "(網+マスク)",
         "access-list 150 permit ip host 172.30.17.0 host 255.255.255.192"),
        ("C1c `permit ip host 10.0.12.2 any`(src=広告元 の読み)",
         "access-list 150 permit ip host 10.0.12.2 any"),
        ("C1d ★★`permit ip any host 255.255.255.0`(dst=マスク=/24 だけ通す)",
         "access-list 150 permit ip any host 255.255.255.0"),
        ("C1e `permit ip any host 172.30.17.0`(dst=網 の読み)",
         "access-list 150 permit ip any host 172.30.17.0"),
    ]
    for label, ace in cases:
        log.append(f"\n##### {label}")
        conf_trace(r1, ["no access-list 150", ace,
                        "no route-map RM-IN",
                        "route-map RM-IN permit 10",
                        " match ip address 150", "exit",
                        "router eigrp 100", "distribute-list route-map RM-IN in",
                        "exit"], log)
        time.sleep(15)
        out = eigrp_routes_detail(r1)
        got = sorted(learned_set(out) & set(LEARNED))
        log.append(f"- 残った学習経路 **{len(got)}/{len(LEARNED)}**: {got}")
        block(log, "  `show ip access-lists 150`", sh(r1, "show ip access-lists 150"))
        conf(r1, ["router eigrp 100", "no distribute-list route-map RM-IN in",
                  "exit"])
        time.sleep(10)
    conf(r1, ["no route-map RM-IN", "no access-list 150"])


def check_C2_out_direction(devs, log):
    """★C2: out 方向では src=広告元 の論理が効かない、という主張の検証。"""
    r1, r2 = devs["RT01"], devs["RT02"]
    log.append("\n#### C2 out 方向の拡張 ACL")
    log.append("RT01 が RT02 へ広告する経路(3.3.3.3/32・172.30.16.0/28)を、"
               "RT02 側で観測する。")

    def seen():
        return sh(r2, "show ip route eigrp | include 3.3.3.3|172.30.16.0")

    block(log, "基線(RT02 の学習)", seen())
    for label, ace in [
        ("C2a `deny ip host 10.0.13.3 any` + permit any(src=広告元 の読み)",
         "access-list 160 deny ip host 10.0.13.3 any"),
        ("C2b `deny ip host 3.3.3.3 any` + permit any(src=網 の読み)",
         "access-list 160 deny ip host 3.3.3.3 any"),
    ]:
        log.append(f"\n##### {label}")
        conf_trace(r1, ["no access-list 160", ace,
                        "access-list 160 permit ip any any",
                        "router eigrp 100", "distribute-list 160 out", "exit"],
                   log)
        time.sleep(20)
        block(log, "  RT02 の学習", seen() or "(該当なし)")
        conf(r1, ["router eigrp 100", "no distribute-list 160 out", "exit"])
        time.sleep(15)
    conf(r1, ["no access-list 160"])
    block(log, "復旧後の RT02 の学習", seen())


def check_C3_named_workaround(devs, log):
    """★C3: 名前付き拡張 ACL を「先に参照してから定義する」と通るか、という回避策。"""
    r1 = devs["RT01"]
    log.append("\n#### C3 名前付き拡張 ACL の回避策(先に参照→後から定義)")
    conf(r1, ["no ip access-list extended NAMEDEXT"])
    log.append("\n**(a) 先に distribute-list で参照する(ACL 未定義の状態)**")
    conf_trace(r1, ["router eigrp 100", "distribute-list NAMEDEXT in", "exit"],
               log)
    log.append("\n**(b) 後から名前付き拡張 ACL として定義する**")
    conf_trace(r1, ["ip access-list extended NAMEDEXT",
                    "permit ip host 10.0.12.2 any", "exit"], log)
    time.sleep(15)
    out = eigrp_routes_detail(r1)
    log.append(f"- 残った学習経路 **{len(learned_set(out) & set(LEARNED))}/7**: "
               f"{sorted(learned_set(out) & set(LEARNED))}")
    block(log, "  `show ip protocols | include Incoming`",
          sh(r1, "show ip protocols | include Incoming"))
    block(log, "  `show ip access-lists NAMEDEXT`",
          sh(r1, "show ip access-lists NAMEDEXT") or "(空)")
    conf(r1, ["router eigrp 100", "no distribute-list NAMEDEXT in", "exit",
              "no ip access-list extended NAMEDEXT"])
    time.sleep(10)


def check_A1_outbound_selfgen(devs, log):
    """★監査A1: 「outbound ACL は自機生成トラフィックに効く」(P4)の再検証。

    P4 は定説（router 生成トラフィックは outbound ACL を素通りする）と食い違う結論を
    出した。ND の件で「観測が対象を捉えていない」失敗をしたので、
    **対照つき**で測り直す。宛先で当たり外れを分ける ACL にして、
    (i) 自機生成×一致 (ii) 自機生成×不一致(対照) (iii) 転送×一致(対照) を比べる。
    """
    r1, r3 = devs["RT01"], devs["RT03"]
    log.append("\n#### A1 outbound ACL と自機生成トラフィック(対照つき再検証)")
    ping(r1, "2.2.2.2", source="Loopback0", repeat=2)      # ARP/経路を温める
    ping(r3, "2.2.2.2", source="Loopback0", repeat=2)
    conf(r1, ["ip access-list extended SELFT",
              "10 deny icmp any host 2.2.2.2",
              "20 permit ip any any", "exit",
              "interface Ethernet0/1", "ip access-group SELFT out", "exit"], log)
    time.sleep(2)

    def snap(tag):
        return sh(r1, "show ip access-lists SELFT")

    block(log, "適用直後(基点)", snap("base"))
    p1, _ = ping(r1, "2.2.2.2", source="Loopback0", repeat=5)
    log.append(f"\n- (i) **自機生成×deny に一致**(RT01→2.2.2.2): **{p1}%**")
    block(log, "  カウンタ", snap("i"))
    p2, _ = ping(r1, "10.0.12.2", repeat=5)
    log.append(f"\n- (ii) 対照= 自機生成×deny に不一致(RT01→10.0.12.2): **{p2}%**")
    block(log, "  カウンタ", snap("ii"))
    p3, _ = ping(r3, "2.2.2.2", source="Loopback0", repeat=5)
    log.append(f"\n- (iii) 対照= 転送×deny に一致(RT03→2.2.2.2): **{p3}%**")
    block(log, "  カウンタ", snap("iii"))
    conf(r1, ["interface Ethernet0/1", "no ip access-group SELFT out", "exit",
              "no ip access-list extended SELFT"])


def check_A2_bgp_update_source(devs, log):
    """★★監査A2: 「片側だけ update-source 欠けでもセッションは UP する」の検証。

    poc/bgpdbg 発見1 と BL-061 で報告された挙動。
    ★これが本当なら `gen_bgp_complex_ts.py` の症状シミュレータ `sim_missing()` は
      `no_upd_src` を**片側でもセッション断**として扱っており**実機と食い違う**
      → 生成されるトラブルチケットが「存在しない症状」を述べることになる。
    """
    r1, r2 = devs["RT01"], devs["RT02"]
    log.append("\n#### A2 片側だけ update-source 欠け(iBGP・Lo ピア)")
    conf(r1, ["router bgp 65000", "bgp router-id 1.1.1.1",
              "no bgp default ipv4-unicast",
              "neighbor 2.2.2.2 remote-as 65000",
              "neighbor 2.2.2.2 update-source Loopback0",
              "address-family ipv4", "neighbor 2.2.2.2 activate", "exit",
              "exit"], log)
    conf(r2, ["router bgp 65000", "bgp router-id 2.2.2.2",
              "no bgp default ipv4-unicast",
              "neighbor 1.1.1.1 remote-as 65000",
              "neighbor 1.1.1.1 update-source Loopback0",
              "address-family ipv4", "neighbor 1.1.1.1 activate", "exit",
              "exit"], log)

    def state(tag, wait=70):
        t0 = time.time()
        out = ""
        while time.time() - t0 < wait:
            out = sh(r1, "show ip bgp summary | begin Neighbor")
            if "Estab" in out or "Active" in out or "Idle" in out:
                if "Estab" in out:
                    break
            time.sleep(6)
        log.append(f"\n- **{tag}**")
        block(log, "  RT01 `show ip bgp summary`", out)
        block(log, "  RT02 `show ip bgp summary`",
              sh(r2, "show ip bgp summary | begin Neighbor"))

    sh(r1, "clear ip bgp * ")
    state("(a) 両側に update-source あり(基線)")

    conf(r2, ["router bgp 65000",
              "no neighbor 1.1.1.1 update-source Loopback0"], log)
    sh(r1, "clear ip bgp * ")
    sh(r2, "clear ip bgp * ")
    state("(b) ★RT02 側だけ update-source を外す")

    conf(r1, ["router bgp 65000",
              "no neighbor 2.2.2.2 update-source Loopback0"], log)
    sh(r1, "clear ip bgp * ")
    sh(r2, "clear ip bgp * ")
    state("(c) 対照= 両側とも update-source なし")

    conf(r1, ["no router bgp 65000"])
    conf(r2, ["no router bgp 65000"])


def check_V7_nd_retest(devs, log):
    """★★V7: V2 の測定は**無効**だったので測り直す。

    V2 の ACL は `permit ipv6 2001:DB8:13::/64 any` を先頭に置いたまま
    RT01 から **RT03 のグローバルアドレス 2001:DB8:13::3** を ping していた。
    グローバルアドレスを解決するときの **NA の送信元は解決対象そのもの**なので、
    NA は `2001:DB8:13::/64` の permit に一致して通っていた。
    = 「暗黙の ND 許可で通った」のではなく「自分で書いた permit で通した」だけ。
    deny 行のカウンタが Loopback 発の 5 発とぴったり一致していたのが傍証。

    → **オンリンクの /64 を許可しない ACL**で測り直し、
      (a) 暗黙の拒否のみ / (b) 明示 `deny ipv6 any any` / (c) ND を明示許可
      の3段で近隣探索の生死を比べる。
    """
    r1, r3 = devs["RT01"], devs["RT03"]
    log.append("\n#### V7 ★近隣探索の再測(V2 の測定は無効だった)")
    block(log, "RT03 のリンクローカル(参考)",
          sh(r3, "show ipv6 interface Ethernet0/0 | include link-local"))

    def probe(tag):
        sh(r1, "clear ipv6 neighbors")
        time.sleep(4)
        pct, _ = _ping6(r1, "2001:DB8:13::3", repeat=5)
        nb = sh(r1, "show ipv6 neighbors 2001:DB8:13::3")
        acl = sh(r1, "show ipv6 access-list V6ND2")
        log.append(f"\n- **{tag}**: RT01→RT03(オンリンクのグローバル) ping "
                   f"**{pct}%**")
        block(log, "  `show ipv6 neighbors 2001:DB8:13::3`", nb or "(空=解決できず)")
        block(log, "  `show ipv6 access-list V6ND2`", acl)

    # ★許可するのは**遠端の Loopback だけ**。オンリンクの /64 は含めない
    conf(r1, ["no ipv6 access-list V6ND2",
              "ipv6 access-list V6ND2",
              "permit ipv6 host 2001:DB8:3::3 any", "exit",
              "interface Ethernet0/0", "ipv6 traffic-filter V6ND2 in",
              "exit"], log)
    probe("(a) 暗黙の拒否のみ")

    conf(r1, ["ipv6 access-list V6ND2", "deny ipv6 any any", "exit"], log)
    probe("(b) 末尾に明示の deny ipv6 any any")

    conf(r1, ["ipv6 access-list V6ND2", "no deny ipv6 any any",
              "permit icmp any any nd-ns", "permit icmp any any nd-na",
              "deny ipv6 any any", "exit"], log)
    probe("(c) ND を明示許可した上で明示の deny")

    conf(r1, ["interface Ethernet0/0", "no ipv6 traffic-filter V6ND2 in",
              "exit", "no ipv6 access-list V6ND2"])


def check_V6_empty_persist(devs, log):
    """★V6: 空の IPv6 ACL は**存在として保持されるのか**。

    V3 で「空の EMPTY6 を適用しても `show ipv6 access-list` に現れない」と出た。
    IPv4 では空でもヘッダが表示されたので、ここは IPv4 との差分になり得る。
    ただし「表示されないだけ」なのか「そもそも作られない」のかで
    紙面の故障種として成立するかが変わるため、running-config で確かめる。
    """
    r1 = devs["RT01"]
    log.append("\n#### V6 空の IPv6 ACL は保持されるか")
    conf_trace(r1, ["ipv6 access-list EMPTY6B", "exit"], log)
    block(log, "  `show ipv6 access-list`(引数なし)",
          sh(r1, "show ipv6 access-list") or "(空)")
    block(log, "  `show running-config | section ipv6 access-list`",
          sh(r1, "show running-config | section ipv6 access-list") or "(空)")
    block(log, "  `show ipv6 access-list EMPTY6B`(名指し)",
          sh(r1, "show ipv6 access-list EMPTY6B") or "(空)")
    conf(r1, ["no ipv6 access-list EMPTY6B", "no ipv6 access-list V6T"])
    block(log, "  片付け後 `show ipv6 access-list`",
          sh(r1, "show ipv6 access-list") or "(空)")


def check_V5_cleanup(devs, log):
    r1 = devs["RT01"]
    log.append("\n#### V5 後片付け(IPv6)")
    block(log, "RT01 `show ipv6 access-list`(残骸が無いこと)",
          sh(r1, "show ipv6 access-list") or "(空)")
    block(log, "RT01 `show running-config | include traffic-filter`",
          sh(r1, "show running-config | include traffic-filter") or "(空)")


def check_P9C_icmp_log(devs, log):
    """★P9 三度目: ICMP のログ書式(2回目は残骸 ACL と seq 衝突して採れなかった)。"""
    r1, r3 = devs["RT01"], devs["RT03"]
    log.append("\n#### P9C ICMP の ACL ログ書式")
    conf(r1, ["interface Ethernet0/0", "no ip access-group LOGT in",
              "no ip access-group LOGT2 in", "exit",
              "no ip access-list extended LOGT",
              "no ip access-list extended LOGT2"])
    conf(r1, ["ip access-list extended LOG3",
              "10 deny icmp any any echo log",
              "20 permit ip any any", "exit",
              "interface Ethernet0/0", "ip access-group LOG3 in", "exit"], log)
    sh(r1, "clear logging")
    time.sleep(2)
    pct, _ = ping(r3, "10.0.12.2", repeat=3)
    time.sleep(10)
    log.append(f"- RT03→RT02 通過率: **{pct}%**")
    block(log, "RT01 `show logging | include SEC-6`",
          sh(r1, "show logging | include SEC-6"))
    block(log, "RT01 `show ip access-lists LOG3`", sh(r1, "show ip access-lists LOG3"))
    conf(r1, ["interface Ethernet0/0", "no ip access-group LOG3 in", "exit",
              "no ip access-list extended LOG3"])


def check_P14_cleanup(devs, log):
    """時計を戻し、測定で残った設定が無いことを確認する(次の測定の汚染防止)。"""
    r1 = devs["RT01"]
    sh(r1, "clock set 12:00:00 12 Aug 2026")
    log.append("\n#### P14 後片付け")
    block(log, "RT01 `show ip access-lists`(残骸が無いこと)",
          sh(r1, "show ip access-lists"))
    block(log, "RT01 `show running-config | include access-group|distribute-list|"
               "service-policy|ip nat|verify unicast`",
          sh(r1, "show running-config | include access-group|distribute-list|"
                 "service-policy|ip nat|verify unicast"))


def check_P2N_dl_num(devs, log):
    """★P2 再測: distribute-list に**番号付き**拡張 ACL を使う。

    1回目の測定では**名前付き**拡張 ACL を使い、`% The ACL cannot be created or
    an ACL with the same name but incompatible type already exists.` が出て
    フィルタが一切効かなかった(7/7 残存)。どのコマンドが弾かれたのかを
    1行ずつ投入して特定し、番号付き(130)で測り直す。
    """
    r1 = devs["RT01"]
    log.append("\n#### P2N-0 まず「名前付き拡張 ACL を distribute-list に使う」の可否を1行ずつ")
    conf_each(r1, ["ip access-list extended DL-EXT2",
                   "permit ip host 172.30.17.0 host 255.255.255.192",
                   "exit",
                   "router eigrp 100",
                   "distribute-list DL-EXT2 in",
                   "exit"], log)
    time.sleep(12)
    out = eigrp_routes_detail(r1)
    log.append(f"- 残った学習経路: **{sorted(learned_set(out) & set(LEARNED))}**")
    conf(r1, ["router eigrp 100", "no distribute-list DL-EXT2 in", "exit",
              "no ip access-list extended DL-EXT2"])
    time.sleep(10)

    log.append("\n#### P2N-a 番号付き拡張 ACL 130 で「/26 だけ」を通す")
    conf_each(r1, ["access-list 130 permit ip host 172.30.17.0 "
                   "host 255.255.255.192",
                   "router eigrp 100", "distribute-list 130 in", "exit"], log)
    time.sleep(15)
    out = eigrp_routes_detail(r1)
    log.append(f"- 残った学習経路: **{sorted(learned_set(out) & set(LEARNED))}**")
    block(log, "RT01 `show ip route eigrp`", out)
    block(log, "RT01 `show ip access-lists 130`", sh(r1, "show ip access-lists 130"))

    log.append("\n#### P2N-b 送信元にワイルドカード・宛先(=マスク)を any にする")
    conf(r1, ["no access-list 130",
              "access-list 130 permit ip 172.30.16.0 0.0.15.255 any"], log)
    time.sleep(15)
    out = eigrp_routes_detail(r1)
    log.append(f"- 残った学習経路: **{sorted(learned_set(out) & set(LEARNED))}**")

    log.append("\n#### P2N-c 宛先(=マスク)だけを /24 に固定 "
               "(`permit ip any host 255.255.255.0`)")
    conf(r1, ["no access-list 130",
              "access-list 130 permit ip any host 255.255.255.0"], log)
    time.sleep(15)
    out = eigrp_routes_detail(r1)
    log.append(f"- 残った学習経路: **{sorted(learned_set(out) & set(LEARNED))}**")
    block(log, "RT01 `show ip route eigrp`", out)
    conf(r1, ["router eigrp 100", "no distribute-list 130 in", "exit",
              "no access-list 130"])
    time.sleep(12)


def check_P4B_selfgen(devs, log):
    """★P4 再測: outbound ACL と自機生成トラフィック。

    1回目は RT01 自身の ping も 0% だった(定説「outbound ACL は自機生成に効かない」
    と食い違う)。ACL カウンタを発ごとに読んで**どの発が deny 行に当たったか**を
    帰属させる。
    """
    r1, r3 = devs["RT01"], devs["RT03"]
    log.append("\n#### P4B outbound ACL は自機生成トラフィックに効くか(帰属つき再測)")
    # 事前に ARP を温めておく(初回ロスを ACL の効果と誤認しないため)
    ping(r3, "10.0.12.2", repeat=3)
    ping(r1, "10.0.12.2", repeat=3)
    conf(r1, ["ip access-list extended OUTT",
              "10 deny icmp any any", "20 permit ip any any", "exit",
              "interface Ethernet0/1", "ip access-group OUTT out", "exit"], log)
    time.sleep(2)

    def counters():
        return sh(r1, "show ip access-lists OUTT")

    block(log, "適用直後(カウンタ基点)", counters())
    pct, _ = ping(r1, "10.0.12.2", repeat=5)
    log.append(f"\n- **RT01 自身 → 10.0.12.2(直結・既定送信元): {pct}%**")
    block(log, "  直後のカウンタ", counters())
    pct, _ = ping(r1, "2.2.2.2", source="Loopback0", repeat=5)
    log.append(f"\n- **RT01 自身 → 2.2.2.2(Lo0 発・1ホップ先): {pct}%**")
    block(log, "  直後のカウンタ", counters())
    pct, _ = ping(r3, "10.0.12.2", repeat=5)
    log.append(f"\n- **RT03 → 10.0.12.2(RT01 を通過): {pct}%**")
    block(log, "  直後のカウンタ", counters())
    conf(r1, ["interface Ethernet0/1", "no ip access-group OUTT out", "exit",
              "no ip access-list extended OUTT"])


def check_P9B_log(devs, log):
    """★P9 再測: ログ書式。telnet の /source-interface は IOL で不可だったので外す。"""
    r1, r3 = devs["RT01"], devs["RT03"]
    log.append("\n#### P9B ACL ログの書式(ICMP と TCP の両方)")
    conf(r1, ["ip access-list extended LOGT",
              "10 deny tcp any any eq 22 log",
              "20 deny icmp any any echo log",
              "30 permit ip any any", "exit",
              "interface Ethernet0/0", "ip access-group LOGT in", "exit"], log)
    sh(r1, "clear logging")
    time.sleep(2)
    ping(r3, "10.0.12.2", repeat=3)
    try:
        r3.execute("telnet 10.0.12.2 22", timeout=60,
                   error_pattern=[], allow_state_change=True)
    except Exception as e:
        log.append(f"- telnet 起動時の応答: `{type(e).__name__}`")
    time.sleep(10)
    block(log, "RT01 `show logging | include SEC-6`",
          sh(r1, "show logging | include SEC-6"))
    block(log, "RT01 `show ip access-lists LOGT`", sh(r1, "show ip access-lists LOGT"))

    log.append("\n#### P9B-b ★log の無い行で落ちた場合は記録が出ないか")
    conf(r1, ["ip access-list extended LOGT2",
              "10 deny icmp any any echo",          # log なし
              "20 permit ip any any", "exit",
              "interface Ethernet0/0", "ip access-group LOGT2 in", "exit"], log)
    sh(r1, "clear logging")
    time.sleep(2)
    ping(r3, "10.0.12.2", repeat=3)
    time.sleep(8)
    out = sh(r1, "show logging | include SEC-6")
    log.append(f"- log 無しの deny で落とした後の SEC-6 行数: "
               f"**{len([x for x in out.splitlines() if 'SEC-6' in x])}**")
    block(log, "RT01 `show logging | include SEC-6`", out)
    block(log, "RT01 `show ip access-lists LOGT2`(カウンタは進む)",
          sh(r1, "show ip access-lists LOGT2"))
    conf(r1, ["interface Ethernet0/0", "no ip access-group LOGT2 in", "exit",
              "no ip access-list extended LOGT", "no ip access-list extended LOGT2"])


def check_P1F_ctrl(devs, log):
    """★P1 の対照実験: 「未定義=素通り」なのか「観測できていないだけ」なのかを切り分ける。"""
    r1, r3 = devs["RT01"], devs["RT03"]

    log.append("\n#### P1F-a 未定義 ACL の interface 適用(ARP を温めてから再測)")
    ping(r3, "10.0.12.2", repeat=3)                     # 温め
    pct0, _ = ping(r3, "10.0.12.2", repeat=5)
    log.append(f"- ACL 適用前(基準): **{pct0}%**")
    conf(r1, ["interface Ethernet0/0", "ip access-group NOEXIST-A in", "exit"])
    pct1, _ = ping(r3, "10.0.12.2", repeat=5)
    log.append(f"- 未定義の**名前付き**を in に適用: **{pct1}%**")
    block(log, "  `show ip access-lists`(未定義参照で ACL が作られるか)",
          sh(r1, "show ip access-lists NOEXIST-A"))
    conf(r1, ["interface Ethernet0/0", "no ip access-group NOEXIST-A in", "exit"])

    log.append("\n#### P1F-b CoPP: 定義済み ACL なら計上されるか(観測方法の対照)")
    conf(r1, ["ip access-list extended CTRL-A", "permit icmp any any", "exit",
              "class-map match-all CM-CTRL", "match access-group name CTRL-A",
              "exit",
              "policy-map PM-CTRL", "class CM-CTRL",
              "police 8000 conform-action transmit exceed-action transmit",
              "exit", "class class-default",
              "police 8000 conform-action transmit exceed-action transmit",
              "exit", "exit",
              "control-plane", "service-policy input PM-CTRL", "exit"], log)
    sh(r1, "clear counters")
    time.sleep(2)
    ping(r3, "10.0.13.1", repeat=10)
    time.sleep(3)
    block(log, "定義済み ACL の場合", sh(r1, "show policy-map control-plane input"))
    conf(r1, ["control-plane", "no service-policy input PM-CTRL", "exit",
              "no policy-map PM-CTRL", "no class-map match-all CM-CTRL",
              "no ip access-list extended CTRL-A"])

    log.append("\n#### P1F-c CoPP: 未定義 ACL(class-default にも police を置いて行き先を見る)")
    conf(r1, ["class-map match-all CM-UND2", "match access-group name NOEXIST-C",
              "exit",
              "policy-map PM-UND2", "class CM-UND2",
              "police 8000 conform-action transmit exceed-action transmit",
              "exit", "class class-default",
              "police 8000 conform-action transmit exceed-action transmit",
              "exit", "exit",
              "control-plane", "service-policy input PM-UND2", "exit"], log)
    sh(r1, "clear counters")
    time.sleep(2)
    ping(r3, "10.0.13.1", repeat=10)
    time.sleep(3)
    block(log, "未定義 ACL の場合(★どちらのクラスに 10発が入るか)",
          sh(r1, "show policy-map control-plane input"))
    conf(r1, ["control-plane", "no service-policy input PM-UND2", "exit",
              "no policy-map PM-UND2", "no class-map match-all CM-UND2"])

    log.append("\n#### P1F-d NAT: 定義済み ACL との対照")
    conf(r1, ["interface Ethernet0/0", "ip nat inside", "exit",
              "interface Ethernet0/1", "ip nat outside", "exit",
              "access-list 60 permit 3.3.3.3",
              "ip nat inside source list 60 interface Ethernet0/1 overload"], log)
    sh(r1, "clear ip nat translation *")
    ping(r3, "2.2.2.2", source="Loopback0", repeat=5)
    block(log, "定義済み ACL 60(3.3.3.3 を許可)", sh(r1, "show ip nat translations"))
    conf(r1, ["no ip nat inside source list 60 interface Ethernet0/1 overload",
              "no access-list 60",
              "ip nat inside source list NOEXIST-N interface Ethernet0/1 "
              "overload"], log)
    sh(r1, "clear ip nat translation *")
    ping(r3, "2.2.2.2", source="Loopback0", repeat=5)
    block(log, "未定義 ACL の場合", sh(r1, "show ip nat translations"))
    conf(r1, ["no ip nat inside source list NOEXIST-N interface Ethernet0/1 "
              "overload",
              "interface Ethernet0/0", "no ip nat inside", "exit",
              "interface Ethernet0/1", "no ip nat outside", "exit"])


def check_P13_empty_vs_undef(devs, log):
    """★空 ACL と未定義 ACL の差(P12 で空=100% 通過だった)を各ロールで確認。"""
    r1 = devs["RT01"]
    log.append("\n#### P13 空の named ACL を distribute-list に使う")
    conf(r1, ["ip access-list standard EMPTYD", "exit",
              "router eigrp 100", "distribute-list EMPTYD in", "exit"], log)
    time.sleep(15)
    out = eigrp_routes_detail(r1)
    log.append(f"- 残った学習経路: **{sorted(learned_set(out) & set(LEARNED))}**")
    block(log, "RT01 `show ip route eigrp`", out)
    conf(r1, ["router eigrp 100", "no distribute-list EMPTYD in", "exit",
              "no ip access-list standard EMPTYD"])
    time.sleep(12)


CHECKS = {
    "P1_undef": check_P1_undef,
    "P1F_ctrl": check_P1F_ctrl,
    # P2N_dl_num / P9B_log は conf_each の不具合と残骸 ACL で無効。P2C / P9C が後継
    # (関数は失敗の記録として残すが、実行対象からは外す)。
    "P2C_dl_ext": check_P2C_dl_ext,
    "P2E_dl_semantics": check_P2E_dl_semantics,
    "P2F_dst_field": check_P2F_dst_field,
    "P15_undef_vs_empty": check_P15_undef_vs_empty,
    "V1_ipv6_basics": check_V1_ipv6_basics,
    "V2_implicit_nd": check_V2_implicit_nd,
    "V3_undef_empty": check_V3_undef_empty,
    "V4_seq": check_V4_seq,
    "C1_routemap_semantics": check_C1_routemap_semantics,
    "C2_out_direction": check_C2_out_direction,
    "C3_named_workaround": check_C3_named_workaround,
    "A1_outbound_selfgen": check_A1_outbound_selfgen,
    "A2_bgp_update_source": check_A2_bgp_update_source,
    "V7_nd_retest": check_V7_nd_retest,
    "V6_empty_persist": check_V6_empty_persist,
    "V5_cleanup": check_V5_cleanup,
    "P4B_selfgen": check_P4B_selfgen,
    "P9C_icmp_log": check_P9C_icmp_log,
    "P13_empty_vs_undef": check_P13_empty_vs_undef,
    "P14_cleanup": check_P14_cleanup,
    "P2_dl_ext": check_P2_dl_ext,
    "P3_dl_std": check_P3_dl_std,
    "P4_out_self": check_P4_out_self,
    "P5_named_seq": check_P5_named_seq,
    "P6_numbered": check_P6_numbered,
    "P7_timerange": check_P7_timerange,
    "P8_copp_deny": check_P8_copp_deny,
    "P9_log": check_P9_log,
    "P10_mask": check_P10_mask,
    "P11_display": check_P11_display,
    "P12_empty": check_P12_empty,
}


def main():
    client = ClientLibrary(*CML, ssl_verify=False)
    lab = ensure_lab(client)
    devs = connect_all(lab)
    push_base(devs)
    t, base_out = wait_baseline(devs)
    print(f"[i] 基線OK ({t:.0f}s)")

    want = sys.argv[1:] or list(CHECKS.keys())
    log = [f"\n## sweep run ({time.strftime('%Y-%m-%d %H:%M:%S')}) "
           f"— checks: {', '.join(want)}\n"]
    block(log, "基線 RT01 `show ip route eigrp`", base_out)
    try:
        for name in want:
            fn = CHECKS.get(name)
            if fn is None:
                print(f"[!] 未知のチェック: {name}")
                continue
            print(f"== {name} ==")
            log.append(f"\n### {name}\n")
            try:
                fn(devs, log)
            except Exception as e:
                print(f"    !! {type(e).__name__}: {e}")
                log.append(f"\n**測定失敗**: `{type(e).__name__}: {e}`\n")
    finally:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open("a", encoding="utf-8") as f:
            f.write("\n".join(log) + "\n")
        print(f"[i] 追記: {OUT}")
        for d in devs.values():
            try:
                d.disconnect()
            except Exception:
                pass


if __name__ == "__main__":
    main()
