#!/usr/bin/env python3
"""BL-271 PoC: _POC-ROUTE の IOL 4 台で、route_model(計算器)の予測と実機を突き合わせる。

  drive.py show RT01 "show ip route" …        # そのまま show
  drive.py conf RT02 "ip route …" …           # config を流す
  drive.py case <名前>                         # 下の CASES の 1 件: 設定 → 実機の表と転送 → 計算器と照合 → 元に戻す
  drive.py all                                 # CASES を全部

盤面と config は route_model.build_net(四角＋対角線)から作る。RT0N = 計算器の RN。
mgmt IP は topologies/_generated/_POC-ROUTE/mgmt_map.yml。認証は SUZUKI/CCNP(ラボ内の機器の既定)。
"""
import re
import sys
import time
from pathlib import Path

import paramiko
import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "topologies"))
import route_model as rm  # noqa: E402

GEN = REPO / "topologies/_generated/_POC-ROUTE"
USER, PW = "SUZUKI", "CCNP"
IFMAP = {"Gi0/0": "Ethernet0/0", "Gi0/1": "Ethernet0/1", "Gi0/2": "Ethernet0/2", "Gi0/3": "Ethernet1/0"}
R2N = {"R1": "RT01", "R2": "RT02", "R3": "RT03", "R4": "RT04"}


def board():
    nw = rm.build_net(
        [{"name": "R%d" % i, "site": i} for i in (1, 2, 3, 4)],
        [{"a": "R1", "b": "R2"}, {"a": "R1", "b": "R3"}, {"a": "R2", "b": "R4"}, {"a": "R3", "b": "R4"},
         {"a": "R2", "b": "R3"}],
        [{"router": "R%d" % i, "k": 1} for i in (1, 2, 3, 4)], lo=True)
    return nw, rm.Index(nw)


def hosts():
    return yaml.safe_load((GEN / "mgmt_map.yml").read_text())


class Sess:
    def __init__(self, node):
        self.node = node
        self.cli = paramiko.SSHClient()
        self.cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.cli.connect(hosts()[node], username=USER, password=PW, look_for_keys=False, allow_agent=False, timeout=20)
        self.sh = self.cli.invoke_shell(width=511)
        self._expect(r"[>#]\s*$")
        self.run("terminal length 0")
        self.run("terminal width 300")

    def _expect(self, pat, timeout=60):
        buf, t0 = "", time.time()
        while time.time() - t0 < timeout:
            if self.sh.recv_ready():
                buf += self.sh.recv(65535).decode("utf-8", "replace")
                last = buf.replace("\r", "").splitlines()[-1] if buf.strip() else ""
                if re.search(pat, last):
                    return buf
            else:
                time.sleep(0.05)
        raise TimeoutError(f"{self.node}: prompt timeout; tail={buf[-300:]!r}")

    def run(self, cmd, timeout=90):
        self.sh.send(cmd + "\n")
        out = self._expect(r"^[\w.-]+(?:\(config[^)]*\))?#\s*$", timeout)
        lines = out.replace("\r", "").splitlines()
        return "\n".join(lines[1:-1] if len(lines) > 1 else lines)

    def conf(self, lines):
        out = [self.run("configure terminal")]
        for l in lines:
            out.append(self.run(l))
        out.append(self.run("end"))
        return "\n".join(o for o in out if o.strip())

    def close(self):
        try:
            self.sh.send("exit\n")
            self.cli.close()
        except Exception:
            pass


_S = {}


def sess(node):
    if node not in _S:
        _S[node] = Sess(node)
    return _S[node]


def log(*a):
    print(*a, flush=True)


# ==========================================================================
# 実機の経路表(show ip route)を読む
# ==========================================================================
ROUTE_RE = re.compile(r"^([A-Z][A-Za-z0-9 ]{0,3}?\*?)\s+(\d+\.\d+\.\d+\.\d+/\d+)\s+(.*)$")


def parse_route(text):
    """show ip route → {prefix: {"code","ad","via":[…],"out":…}}(粗い自前パーサ。IOS の行の形だけ見る)。
    「x.x.x.x/nn is subnetted」の段の行はマスクを持たないので、見出しのマスクを補う。"""
    rows, cur, mask = {}, None, None
    fixed = []
    for line in text.splitlines():
        m = re.match(r"^\s+(\d+\.\d+\.\d+\.\d+)/(\d+) is subnetted", line)
        if m:
            mask = m.group(2)
        elif re.match(r"^\s+\S+ is variably subnetted", line) or re.match(r"^[A-Z]", line):
            if not re.match(r"^[A-Z][A-Za-z0-9 ]{0,3}?\*?\s+\d+\.\d+\.\d+\.\d+ ", line):
                mask = None if re.match(r"^\s+\S+ is variably", line) else mask
        m2 = re.match(r"^([A-Z][A-Za-z0-9 ]{0,3}?\*?\s+)(\d+\.\d+\.\d+\.\d+)( .*)$", line)
        if m2 and mask:
            line = m2.group(1) + m2.group(2) + "/" + mask + m2.group(3)
        fixed.append(line)
    for line in fixed:
        m = ROUTE_RE.match(line.strip()) if not line.startswith(" " * 6) or line.strip()[:1].isalpha() else None
        if m and not line.strip().endswith("masks") and "is subnetted" not in line and "variably" not in line:
            code, p, rest = m.group(1).strip(), m.group(2), m.group(3)
            cur = {"code": code, "ad": None, "via": [], "out": None}
            rows[p] = cur
            _rest(cur, rest)
            continue
        s = line.strip()
        if cur and s.startswith("[") and " via " in s:
            _rest(cur, s)
    return rows


def _rest(cur, rest):
    m = re.search(r"\[(\d+)/(\d+)\] via (\S+?)(?:,|$)", rest)
    if m:
        cur["ad"] = int(m.group(1))
        cur["via"].append(m.group(3))
        return
    m = re.search(r"is directly connected, (\S+)", rest)
    if m:
        cur["out"] = m.group(1)


def model_rows(table):
    out = {}
    for x in table["rows"]:
        out[x["p"]] = {"code": x["code"] + ("*" if x["net"].prefixlen == 0 else ""), "ad": x["ad"] if x["code"] == "S" else None,
                       "via": [] if x["via"] == ["Null0"] else list(x["via"]),
                       "out": ("Null0" if x["via"] == ["Null0"] else None) if x["code"] == "S" else IFMAP.get(x["out"], x["out"])}
        if out[x["p"]]["out"] == "Null0":
            out[x["p"]]["ad"] = None          # IOS は Null0 の static に [AD/metric] を出さない(表示の違いだけ)
    return out


def cmp_table(r, real, model):
    """違いの一覧(空なら一致)。via は並び順を区別しない(並び順は別に記録)。"""
    diffs = []
    for p in sorted(set(real) | set(model)):
        a, b = real.get(p), model.get(p)
        if a is None:
            diffs.append(f"{r} {p}: 計算器だけにある {b}")
            continue
        if b is None:
            diffs.append(f"{r} {p}: 実機だけにある {a}")
            continue
        ka = (a["code"], a["ad"], tuple(sorted(a["via"])), a["out"])
        kb = (b["code"], b["ad"], tuple(sorted(b["via"])), b["out"])
        if ka != kb:
            diffs.append(f"{r} {p}: 実機 {ka} / 計算器 {kb}")
    return diffs


# ==========================================================================
# 転送(show ip cef <宛先>)を読む
# ==========================================================================
def parse_cef(text):
    """→ ("attached", IF) / ("nexthop", [ip …]) / ("drop",) / ("receive",) / ("noroute",) / ("raw", text)"""
    t = text
    if re.search(r"^\s*receive", t, re.M) or "receive for" in t:
        return ("receive",)
    if re.search(r"Null0|\bdrop\b|discard", t):
        return ("drop",)
    nh = re.findall(r"nexthop (\d+\.\d+\.\d+\.\d+) (\S+)", t)
    if nh:
        return ("nexthop", sorted({x[0] for x in nh}))
    m = re.search(r"attached to (\S+)", t)
    if m:
        return ("attached", m.group(1))
    if "0.0.0.0/0" in t and "no route" in t:
        return ("noroute",)
    if re.search(r"^0\.0\.0\.0/0\s*$", t.strip(), re.M) or "no route" in t:
        return ("noroute",)
    return ("raw", t.strip()[:200])


def model_fwd(ix, table, r, dst):
    d = rm.decide(ix, table, r, dst)
    if d[0] == "fwd":
        row = d[2]
        return ("nexthop", sorted({x[0] for x in row["res"]}))
    if d[0] == "null0":
        return ("drop",)
    if d[0] in ("local",):
        return ("receive",)
    if d[0] in ("deliver", "nohost", "router"):
        row = rm._lpm(table["rows"], dst)
        return ("attached", IFMAP.get(row["out"], row["out"]))
    return ("noroute",)


# ==========================================================================
# 照合の 1 件
# ==========================================================================
def S(p, nh, ad=1):
    return {"p": p, "nh": nh, "ad": ad}


# 名前: {"note", "cfg": {R: [static]}, "down": [リンク番号], "shut": [(R, IF, 両端か)], "dst": [宛先 …],
#        "trace": [(R, 宛先)], "extra": {R: [show …]}}
# リンク番号: 0= R1–R2・1= R1–R3・2= R2–R4・3= R3–R4・4= R2–R3
CASES = {
    "base": {"note": "1. connected と local・ループバック /32(static なし)", "cfg": {}, "dst": ["10.4.1.1", "10.255.0.1"]},
    "lpm": {"note": "1. ロンゲストマッチ・AD は同じ宛先の中だけ(/24 AD 250 vs /16 AD 1)",
            "cfg": {"R1": [S("10.4.0.0/16", "172.16.12.2"), S("10.4.1.0/24", "172.16.13.2", 250)],
                    "R2": [S("10.4.0.0/16", "172.16.24.2")], "R3": [S("10.4.0.0/16", "172.16.34.2")]},
            "dst": ["10.4.1.1", "10.4.2.9"], "trace": [("R1", "10.4.1.1"), ("R1", "10.4.2.9")]},
    "conn_vs_static": {"note": "1. 同じ宛先の connected と static・/32 の static は connected の /24 より長い",
                       "cfg": {"R4": [S("10.4.1.0/24", "172.16.24.1"), S("10.4.1.77/32", "172.16.34.1")]},
                       "dst": ["10.4.1.77", "10.4.1.66"]},
    "floating": {"note": "2. フローティング(AD 1 と AD 5)", "cfg": {"R1": [S("10.4.0.0/16", "172.16.12.2"),
                                                                      S("10.4.0.0/16", "172.16.13.2", 5)]},
                 "dst": ["10.4.1.1"]},
    "recursive": {"note": "3. 再帰(ループバック宛ての next-hop を /32 の static で解決)",
                  "cfg": {"R1": [S("10.4.0.0/16", "10.255.0.4"), S("10.255.0.4/32", "172.16.13.2")],
                          "R3": [S("10.4.0.0/16", "172.16.34.2")]},
                  "dst": ["10.4.1.1"], "trace": [("R1", "10.4.1.1")]},
    "rec_default": {"note": "3. next-hop をデフォルト経路だけで解決できるか",
                    "cfg": {"R1": [S("0.0.0.0/0", "172.16.12.2"), S("10.4.0.0/16", "10.255.0.4")]},
                    "dst": ["10.4.1.1"]},
    "rec_self": {"note": "3. 自分の宛先で自分を解決する static", "cfg": {"R1": [S("10.255.0.0/16", "10.255.0.4")]},
                 "dst": ["10.255.0.4"]},
    "rec_null": {"note": "3. Null0 の行を通る再帰", "cfg": {"R1": [S("10.255.0.0/16", "Null0"), S("10.4.0.0/16", "10.255.0.4")]},
                 "dst": ["10.4.1.1", "10.255.0.4"]},
    "rec_chain": {"note": "3. 再帰の 2 段(next-hop → /16 の static → 隣)",
                  "cfg": {"R1": [S("10.4.1.0/24", "10.255.0.4"), S("10.255.0.0/16", "172.16.12.2")]},
                  "dst": ["10.4.1.1"]},
    "ecmp": {"note": "4. ECMP(同じ宛先・同じ AD・別の next-hop)",
             "cfg": {"R1": [S("10.4.0.0/16", "172.16.13.2"), S("10.4.0.0/16", "172.16.12.2")]}, "dst": ["10.4.1.1"]},
    "loop": {"note": "6. デフォルトどうしの向け合い(R1 ⇄ R2)", "cfg": {"R1": [S("0.0.0.0/0", "172.16.12.2")],
                                                                     "R2": [S("0.0.0.0/0", "172.16.12.1")]},
             "dst": ["10.9.9.9"], "trace": [("R1", "10.9.9.9")]},
    "null0": {"note": "6. Null0 の集約でループを止める",
              "cfg": {"R1": [S("0.0.0.0/0", "172.16.12.2")], "R2": [S("0.0.0.0/0", "172.16.12.1"), S("10.9.0.0/16", "Null0")]},
              "dst": ["10.9.9.9"], "trace": [("R1", "10.9.9.9")]},
    "format": {"note": "7. show ip route の書式(いろいろな長さ・デフォルト・Null0・ECMP)",
               "cfg": {"R2": [S("0.0.0.0/0", "172.16.12.1"), S("10.4.0.0/16", "172.16.24.2"), S("10.4.1.0/24", "172.16.23.2"),
                              S("10.3.0.0/16", "172.16.23.2"), S("10.3.0.0/16", "172.16.24.2"), S("10.9.0.0/16", "Null0"),
                              S("192.168.50.0/24", "172.16.24.2"), S("192.168.60.0/26", "172.16.24.2"),
                              S("10.1.1.10/32", "172.16.12.1")]},
               "dst": ["10.4.1.1"]},
}


FLOAT = {"R1": [S("10.4.0.0/16", "172.16.12.2"), S("10.4.0.0/16", "172.16.13.2", 5)]}
CASES.update({
    "rec_default_wait": {"note": "3. デフォルト経由の再帰(30 秒待って show ip static route も)", "wait": 30,
                         "cfg": {"R1": [S("0.0.0.0/0", "172.16.12.2"), S("10.4.0.0/16", "10.255.0.4")]},
                         "dst": ["10.4.1.1"], "extra": {"R1": ["show ip static route", "show running-config | include ip route"]}},
    "float_down_both": {"note": "2. フローティング: R1–R2 を両端で shutdown → AD 5 が入る", "cfg": FLOAT,
                        "shut": [("R1", "Gi0/1"), ("R2", "Gi0/1")], "down": [0], "wait": 6, "dst": ["10.4.1.1"],
                        "extra": {"R1": ["show ip static route", "show ip interface brief"]}},
    "float_down_far": {"note": "2. フローティング: R1–R2 を相手(R2)側だけ shutdown(IOL は伝わらない)", "cfg": FLOAT,
                       "shut": [("R2", "Gi0/1")], "down": [], "wait": 10, "dst": ["10.4.1.1"],
                       "extra": {"R1": ["show ip interface brief", "ping 10.4.1.1 repeat 2 timeout 1"]}},
    "float_down_near": {"note": "2. フローティング: R1–R2 を自分(R1)側だけ shutdown", "cfg": FLOAT,
                        "shut": [("R1", "Gi0/1")], "down": [0], "wait": 6, "dst": ["10.4.1.1"]},
    "ecmp_order": {"note": "4. ECMP の via の並び順(設定の順を逆に)",
                   "cfg": {"R1": [S("10.4.0.0/16", "172.16.12.2"), S("10.4.0.0/16", "172.16.13.2")]}, "dst": ["10.4.1.1"]},
})

STEPS = {
    "input_form2": {"note": "追加 PoC(2026-11-12)の続き: next-hop の特別なアドレスと AD 1 の書き方", "steps": [
        {"note": '15. next-hop 127.0.0.1', "node": "RT01", "conf": ['ip route 10.4.1.0 255.255.255.0 127.0.0.1'], "wait": 4, "show": ['show running-config | include ^ip route', 'show ip static route'] + ["show ip route 10.4.1.0", "show ip route 10.1.1.0"]},
        {"note": '15 の後始末', "node": "RT01", "conf": ['no ip route 10.4.1.0 255.255.255.0 127.0.0.1'], "wait": 2, "show": ["show running-config | include ^ip route"]},
        {"note": '16. next-hop 240.0.0.1(クラス E)', "node": "RT01", "conf": ['ip route 10.4.1.0 255.255.255.0 240.0.0.1'], "wait": 4, "show": ['show running-config | include ^ip route', 'show ip static route'] + ["show ip route 10.4.1.0", "show ip route 10.1.1.0"]},
        {"note": '16 の後始末', "node": "RT01", "conf": ['no ip route 10.4.1.0 255.255.255.0 240.0.0.1'], "wait": 2, "show": ["show running-config | include ^ip route"]},
        {"note": '17. AD 1 を明示', "node": "RT01", "conf": ['ip route 10.4.1.0 255.255.255.0 172.16.12.2 1'], "wait": 4, "show": ['show running-config | include ^ip route', 'show ip static route'] + ["show ip route 10.4.1.0", "show ip route 10.1.1.0"]},
        {"note": '17 の後始末', "node": "RT01", "conf": ['no ip route 10.4.1.0 255.255.255.0 172.16.12.2'], "wait": 2, "show": ["show running-config | include ^ip route"]},
        {"note": '18. 先頭に 0 のついた数(010.4.1.0)', "node": "RT01", "conf": ['ip route 010.4.1.0 255.255.255.0 172.16.12.2'], "wait": 4, "show": ['show running-config | include ^ip route', 'show ip static route'] + ["show ip route 10.4.1.0", "show ip route 10.1.1.0"]},
        {"note": '18 の後始末', "node": "RT01", "conf": ['no ip route 10.4.1.0 255.255.255.0 172.16.12.2'], "wait": 2, "show": ["show running-config | include ^ip route"]},
        {"note": '19. 宛先 0.0.0.0 マスク 0.0.0.0 で next-hop が隣', "node": "RT01", "conf": ['ip route 0.0.0.0 0.0.0.0 172.16.12.2'], "wait": 4, "show": ['show running-config | include ^ip route', 'show ip static route'] + ["show ip route 10.4.1.0", "show ip route 10.1.1.0"]},
        {"note": '19 の後始末', "node": "RT01", "conf": ['no ip route 0.0.0.0 0.0.0.0 172.16.12.2'], "wait": 2, "show": ["show running-config | include ^ip route"]},
        {"note": '20. 宛先が自分の LAN(connected と同じ 10.1.1.0/24)', "node": "RT01", "conf": ['ip route 10.1.1.0 255.255.255.0 172.16.12.2'], "wait": 4, "show": ['show running-config | include ^ip route', 'show ip static route'] + ["show ip route 10.4.1.0", "show ip route 10.1.1.0"]},
        {"note": '20 の後始末', "node": "RT01", "conf": ['no ip route 10.1.1.0 255.255.255.0 172.16.12.2'], "wait": 2, "show": ["show running-config | include ^ip route"]},
    ]},
    "input_form": {"note": "追加 PoC(2026-11-12): 穴埋めで入れ間違えたときの IOS の反応(マスク・AD・next-hop)", "steps": [
        {"note": "基準", "node": "RT01", "show": ['show running-config | include ^ip route', 'show ip static route']},
        {"note": '1. ホスト部が 0 でない宛先(10.4.1.1 255.255.255.0)', "node": "RT01", "conf": ['ip route 10.4.1.1 255.255.255.0 172.16.12.2'], "wait": 4, "show": ['show running-config | include ^ip route', 'show ip static route'] + ["show ip route 10.4.1.0"]},
        {"note": '1 の後始末', "node": "RT01", "conf": ['no ip route 10.4.1.1 255.255.255.0 172.16.12.2'], "wait": 2, "show": ["show running-config | include ^ip route"]},
        {"note": '2. 1 が続かないマスク(255.0.255.0)', "node": "RT01", "conf": ['ip route 10.4.0.0 255.0.255.0 172.16.12.2'], "wait": 4, "show": ['show running-config | include ^ip route', 'show ip static route'] + ["show ip route 10.4.1.0"]},
        {"note": '2 の後始末', "node": "RT01", "conf": ['no ip route 10.4.0.0 255.0.255.0 172.16.12.2'], "wait": 2, "show": ["show running-config | include ^ip route"]},
        {"note": '3. マスクを /24 で書く', "node": "RT01", "conf": ['ip route 10.4.1.0 /24 172.16.12.2'], "wait": 4, "show": ['show running-config | include ^ip route', 'show ip static route'] + ["show ip route 10.4.1.0"]},
        {"note": '4. AD 0', "node": "RT01", "conf": ['ip route 10.4.1.0 255.255.255.0 172.16.12.2 0'], "wait": 4, "show": ['show running-config | include ^ip route', 'show ip static route'] + ["show ip route 10.4.1.0"]},
        {"note": '4 の後始末', "node": "RT01", "conf": ['no ip route 10.4.1.0 255.255.255.0 172.16.12.2 0'], "wait": 2, "show": ["show running-config | include ^ip route"]},
        {"note": '5. AD 256', "node": "RT01", "conf": ['ip route 10.4.1.0 255.255.255.0 172.16.12.2 256'], "wait": 4, "show": ['show running-config | include ^ip route', 'show ip static route'] + ["show ip route 10.4.1.0"]},
        {"note": '6. AD 255(入るが表に出ないはず)', "node": "RT01", "conf": ['ip route 10.4.1.0 255.255.255.0 172.16.12.2 255'], "wait": 4, "show": ['show running-config | include ^ip route', 'show ip static route'] + ["show ip route 10.4.1.0"]},
        {"note": '6 の後始末', "node": "RT01", "conf": ['no ip route 10.4.1.0 255.255.255.0 172.16.12.2 255'], "wait": 2, "show": ["show running-config | include ^ip route"]},
        {"note": '7. next-hop 0.0.0.0', "node": "RT01", "conf": ['ip route 10.4.1.0 255.255.255.0 0.0.0.0'], "wait": 4, "show": ['show running-config | include ^ip route', 'show ip static route'] + ["show ip route 10.4.1.0"]},
        {"note": '7 の後始末', "node": "RT01", "conf": ['no ip route 10.4.1.0 255.255.255.0 0.0.0.0'], "wait": 2, "show": ["show running-config | include ^ip route"]},
        {"note": '8. next-hop がマルチキャスト(224.0.0.1)', "node": "RT01", "conf": ['ip route 10.4.1.0 255.255.255.0 224.0.0.1'], "wait": 4, "show": ['show running-config | include ^ip route', 'show ip static route'] + ["show ip route 10.4.1.0"]},
        {"note": '8 の後始末', "node": "RT01", "conf": ['no ip route 10.4.1.0 255.255.255.0 224.0.0.1'], "wait": 2, "show": ["show running-config | include ^ip route"]},
        {"note": '9. next-hop 255.255.255.255', "node": "RT01", "conf": ['ip route 10.4.1.0 255.255.255.0 255.255.255.255'], "wait": 4, "show": ['show running-config | include ^ip route', 'show ip static route'] + ["show ip route 10.4.1.0"]},
        {"note": '9 の後始末', "node": "RT01", "conf": ['no ip route 10.4.1.0 255.255.255.0 255.255.255.255'], "wait": 2, "show": ["show running-config | include ^ip route"]},
        {"note": '10. 同じ宛先・同じ next-hop で AD だけ変える(1 → 200)', "node": "RT01", "conf": ['ip route 10.4.1.0 255.255.255.0 172.16.12.2', 'ip route 10.4.1.0 255.255.255.0 172.16.12.2 200'], "wait": 4, "show": ['show running-config | include ^ip route', 'show ip static route'] + ["show ip route 10.4.1.0"]},
        {"note": '10 の続き: AD を書かずにもう一度(200 → ?)', "node": "RT01", "conf": ['ip route 10.4.1.0 255.255.255.0 172.16.12.2'], "wait": 4, "show": ['show running-config | include ^ip route', 'show ip static route'] + ["show ip route 10.4.1.0"]},
        {"note": '10 の続き: no を AD なしで', "node": "RT01", "conf": ['no ip route 10.4.1.0 255.255.255.0 172.16.12.2'], "wait": 4, "show": ['show running-config | include ^ip route', 'show ip static route'] + ["show ip route 10.4.1.0"]},
        {"note": '11. 宛先 0.0.0.0 マスク 255.255.255.0(ホスト部 0 だが 0.0.0.0/24)', "node": "RT01", "conf": ['ip route 0.0.0.0 255.255.255.0 172.16.12.2'], "wait": 4, "show": ['show running-config | include ^ip route', 'show ip static route'] + ["show ip route 10.4.1.0"]},
        {"note": '11 の後始末', "node": "RT01", "conf": ['no ip route 0.0.0.0 255.255.255.0 172.16.12.2'], "wait": 2, "show": ["show running-config | include ^ip route"]},
        {"note": '12. 宛先 10.4.1.0 マスク 0.0.0.0', "node": "RT01", "conf": ['ip route 10.4.1.0 0.0.0.0 172.16.12.2'], "wait": 4, "show": ['show running-config | include ^ip route', 'show ip static route'] + ["show ip route 10.4.1.0"]},
        {"note": '12 の後始末', "node": "RT01", "conf": ['no ip route 10.4.1.0 0.0.0.0 172.16.12.2'], "wait": 2, "show": ["show running-config | include ^ip route"]},
        {"note": '13. 宛先の IP が 4 つ目の数字を欠く(10.4.1)', "node": "RT01", "conf": ['ip route 10.4.1 255.255.255.0 172.16.12.2'], "wait": 4, "show": ['show running-config | include ^ip route', 'show ip static route'] + ["show ip route 10.4.1.0"]},
        {"note": '14. マスク 255.255.255.256', "node": "RT01", "conf": ['ip route 10.4.1.0 255.255.255.256 172.16.12.2'], "wait": 4, "show": ['show running-config | include ^ip route', 'show ip static route'] + ["show ip route 10.4.1.0"]},
        {"note": "後始末の確認", "node": "RT01", "show": ["show running-config | include ^ip route"]},
    ]},
    "nh_choice": {"note": "追加 PoC(2026-11-12): next-hop の選び方(自分の IP・隣でない IP・ブロードキャスト・ネットワーク アドレス)", "steps": [
        {"note": "基準", "node": "RT01", "show": ['show running-config | include ^ip route', 'show ip route static', 'show ip static route']},
        {"note": "1. 自分の IP(Et0/1 = 172.16.12.1)を next-hop に", "node": "RT01",
         "conf": ["ip route 10.4.0.0 255.255.0.0 172.16.12.1"], "wait": 5, "show": ['show running-config | include ^ip route', 'show ip route static', 'show ip static route']},
        {"note": "1 の後始末", "node": "RT01", "conf": ["no ip route 10.4.0.0 255.255.0.0 172.16.12.1"], "wait": 2,
         "show": ["show running-config | include ^ip route"]},
        {"note": "2. 隣でない IP(R4 の 172.16.34.2。R1 はこのサブネットにつながっていない)", "node": "RT01",
         "conf": ["ip route 10.4.0.0 255.255.0.0 172.16.34.2"], "wait": 8,
         "show": ['show running-config | include ^ip route', 'show ip route static', 'show ip static route'] + ["show ip cef 10.4.1.1"]},
        {"note": "2 の後始末", "node": "RT01", "conf": ["no ip route 10.4.0.0 255.255.0.0 172.16.34.2"], "wait": 2,
         "show": ["show running-config | include ^ip route"]},
        {"note": "3. /30 のブロードキャスト(172.16.12.3)を next-hop に", "node": "RT01",
         "conf": ["ip route 10.4.0.0 255.255.0.0 172.16.12.3"], "wait": 8, "show": ['show running-config | include ^ip route', 'show ip route static', 'show ip static route'] + ["show ip cef 10.4.1.1", "show ip arp 172.16.12.3"]},
        {"note": "3 の後始末", "node": "RT01", "conf": ["no ip route 10.4.0.0 255.255.0.0 172.16.12.3"], "wait": 2,
         "show": ["show running-config | include ^ip route"]},
        {"note": "4. ネットワーク アドレス(172.16.12.0)を next-hop に", "node": "RT01",
         "conf": ["ip route 10.4.0.0 255.255.0.0 172.16.12.0"], "wait": 8, "show": ['show running-config | include ^ip route', 'show ip route static', 'show ip static route'] + ["show ip cef 10.4.1.1"]},
        {"note": "4 の後始末", "node": "RT01", "conf": ["no ip route 10.4.0.0 255.255.0.0 172.16.12.0"], "wait": 2,
         "show": ["show running-config | include ^ip route", "show ip route static"]},
    ]},
    "rec_default_long": {"note": "3. デフォルト経由の再帰(70 秒待つ・install-routes-recurse-via-nexthop の有無)", "steps": [
        {"note": "default と 10.4.0.0/16 via 10.255.0.4", "node": "RT01",
         "conf": ["ip route 0.0.0.0 0.0.0.0 172.16.12.2", "ip route 10.4.0.0 255.255.0.0 10.255.0.4"], "wait": 70,
         "show": ["show ip route static", "show ip static route", "show ip cef 10.4.1.1"]},
        {"note": "ip route static install-routes-recurse-via-nexthop を入れる", "node": "RT01",
         "conf": ["ip route static install-routes-recurse-via-nexthop"], "wait": 70,
         "show": ["show ip route static", "show ip static route", "show ip cef 10.4.1.1"]},
        {"note": "後始末", "node": "RT01",
         "conf": ["no ip route static install-routes-recurse-via-nexthop", "no ip route 0.0.0.0 0.0.0.0 172.16.12.2",
                  "no ip route 10.4.0.0 255.255.0.0 10.255.0.4"], "wait": 3, "show": ["show ip route static"]},
    ]},
    "connected": {"note": "5. connected の段(shutdown・IP なし・別のサブネット・重なる IP)", "steps": [
        {"note": "基準", "node": "RT04", "show": ["show ip route connected", "show ip interface brief"]},
        {"note": "IP 付きで shutdown", "node": "RT04", "conf": ["interface Ethernet0/0", "shutdown"], "wait": 3,
         "show": ["show ip route connected", "show ip interface brief | include Ethernet0/0"]},
        {"note": "no shutdown", "node": "RT04", "conf": ["interface Ethernet0/0", "no shutdown"], "wait": 5,
         "show": ["show ip route connected", "show ip interface brief | include Ethernet0/0"]},
        {"note": "IP を外す(no ip address)", "node": "RT04", "conf": ["interface Ethernet0/0", "no ip address"], "wait": 3,
         "show": ["show ip route connected", "show ip interface brief | include Ethernet0/0"]},
        {"note": "別のサブネットの IP(10.4.2.1/24)", "node": "RT04", "conf": ["interface Ethernet0/0", "ip address 10.4.2.1 255.255.255.0"],
         "wait": 3, "show": ["show ip route connected"]},
        {"note": "元に戻す(10.4.1.1/24)", "node": "RT04", "conf": ["interface Ethernet0/0", "ip address 10.4.1.1 255.255.255.0"],
         "wait": 3, "show": ["show ip route connected"]},
        {"note": "重なるサブネット: up の IF(Ethernet0/0= 10.4.1.0/24)と同じサブネットを Loopback9 に",
         "node": "RT04", "conf": ["interface Loopback9", "ip address 10.4.1.5 255.255.255.0"], "show": ["show ip interface brief | include Loopback9"]},
        {"note": "重なるサブネット: リンクの IF に(Ethernet0/1 に 10.4.1.9/24)", "node": "RT04",
         "conf": ["interface Ethernet0/1", "ip address 10.4.1.9 255.255.255.0"], "show": ["show ip interface brief | include Ethernet0/1"]},
        {"note": "重なるサブネット: shutdown 中の IF に付けてから no shutdown", "node": "RT04",
         "conf": ["interface Loopback9", "shutdown", "ip address 10.4.1.5 255.255.255.0", "no shutdown"], "wait": 3,
         "show": ["show ip interface brief | include Loopback9|Ethernet0/0", "show ip route connected", "show logging | include overlap|incorrect|IP address"]},
        {"note": "後始末", "node": "RT04", "conf": ["no interface Loopback9", "interface Ethernet0/1", "ip address 172.16.24.2 255.255.255.252"],
         "wait": 3, "show": ["show ip interface brief", "show ip route connected"]},
    ]},
}


def apply_cfg(cfg, undo=False):
    for r, routes in cfg.items():
        lines = [rm.route_cli(s, no=undo) for s in routes]
        out = sess(R2N[r]).conf(lines)
        if out.strip():
            log(f"### {r} conf\n{out}")


def snapshot(nw, ix, cfg, dsts, down=()):
    t = rm.tables(ix, cfg, down)
    diffs = []
    for r in ("R1", "R2", "R3", "R4"):
        s = sess(R2N[r])
        txt = s.run("show ip route")
        log(f"### {r}: show ip route\n{txt}")
        diffs += cmp_table(r, parse_route(txt), model_rows(t[r]))
        for d in dsts:
            c = s.run(f"show ip cef {d}")
            real, mod = parse_cef(c), model_fwd(ix, t[r], r, d)
            ok = real == mod
            log(f"### {r}: show ip cef {d}  → 実機 {real} / 計算器 {mod} {'一致' if ok else '★不一致'}\n{c}")
            if not ok:
                diffs.append(f"{r} cef {d}: 実機 {real} / 計算器 {mod}")
    return t, diffs


def trace_r(ix, t, start, dst):
    """ルータ start から dst への道(計算器)。ECMP は分かれた道をすべて。"""
    out = []

    def walk(r, hops):
        if r in hops:
            out.append((hops + [r], "loop"))
            return
        hops = hops + [r]
        d = rm.decide(ix, t[r], r, dst)
        if d[0] == "fwd":
            for p in d[1]:
                walk(p, hops)
            return
        out.append((hops, d[0]))
    walk(start, [])
    return out


def run_steps(name):
    c = STEPS[name]
    log(f"\n======== {name}: {c['note']} ========")
    for st in c["steps"]:
        if "note" in st:
            log(f"--- {st['note']}")
        if st.get("conf"):
            log(f"### {st['node']}: conf {st['conf']}\n{sess(st['node']).conf(st['conf'])}")
        if st.get("wait"):
            time.sleep(st["wait"])
        for cmd in st.get("show", []):
            log(f"### {time.strftime('%H:%M:%S')} {st['node']}: {cmd}\n{sess(st['node']).run(cmd, timeout=120)}")
    return []


def run_case(name):
    nw, ix = board()
    c = CASES[name]
    log(f"\n======== {name}: {c['note']} ========")
    apply_cfg(c["cfg"])
    for r, ifn in c.get("shut", []):
        log(f"### {r}: shutdown {IFMAP[ifn]}\n" + sess(R2N[r]).conf(["interface " + IFMAP[ifn], "shutdown"]))
    time.sleep(c.get("wait", 4))
    t, diffs = snapshot(nw, ix, c["cfg"], c.get("dst", []), c.get("down", ()))
    for r, d in c.get("trace", []):
        out = sess(R2N[r]).run(f"traceroute {d} numeric timeout 1 probe 1 ttl 1 8", timeout=120)
        paths = trace_r(ix, t, r, d)
        log(f"### {r}: traceroute {d}\n{out}\n### 計算器の道(ルータから): {paths}")
    for r, cmds in c.get("extra", {}).items():
        for cmd in cmds:
            log(f"### {r}: {cmd}\n{sess(R2N[r]).run(cmd)}")
    log(f"######## {name}: 違い {len(diffs)} 件")
    for d in diffs:
        log("  ★ " + d)
    for r, ifn in c.get("shut", []):
        sess(R2N[r]).conf(["interface " + IFMAP[ifn], "no shutdown"])
    apply_cfg(c["cfg"], undo=True)
    time.sleep(2)
    return diffs


def main():
    a = sys.argv[1:]
    try:
        if a[0] == "show":
            for cmd in a[2:]:
                log(f"### {a[1]}: {cmd}\n{sess(a[1]).run(cmd)}")
        elif a[0] == "conf":
            log(sess(a[1]).conf(a[2:]))
        elif a[0] == "case":
            for n in a[1:]:
                (run_steps if n in STEPS else run_case)(n)
        elif a[0] == "all":
            res = {n: run_case(n) for n in CASES}
            log("\n======== まとめ ========")
            for n, d in res.items():
                log(f"{n}: {'一致' if not d else '不一致 %d 件' % len(d)}")
    finally:
        for s in _S.values():
            s.close()


if __name__ == "__main__":
    main()
