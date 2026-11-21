#!/usr/bin/env python3
"""XRT-17 の確認(grading.m6t<n>.yml と最終の grading.yml)を組む。確認の中身は CHECKS に 1 か所で持つ。
usage: python3 poc/xr/gen_grading_xrt17.py(リポの根で)。配点= (課題ごとの確認, 最終の確認)。
正規表現の文言は実機の記録から採った(poc/xr/expXRT17-*.log・design §32)。"""
import yaml
P = "problems/XRT-17"
PROBE = ".venv/bin/python topologies/bgpops_probe.py XRT-17 run"
PFX = "203.0.113.0/24"
# PE1 と CE1 のセッションが確立している(経路の数が出ている)/上限を超えて Idle (PfxCt) になった(どちらも待つ条件)
EST = r"PE1|show bgp summary|^172\.16\.1\.1\s+\d+\s+65001(?:\s+\d+){5}\s+\S+\s+\d+\s*$|120"
PFXCT = r"PE1|show bgp summary|^172\.16\.1\.1\s+\d+\s+65001.*Idle \(PfxCt\)|60"


def probe(*parts):
    return PROBE + " " + " ".join(parts)


def show(node, cmd):
    return f"--show '{node}:{cmd}'"


def sec(node, cmd):
    """`== SHOW <node>: <cmd>` の出力の塊だけに当てる正規表現の頭(次の `== ` まで)。"""
    import re
    return rf"== SHOW {node}: {re.escape(cmd)}\n(?:(?!== )[\s\S])*?"


CHECKS = {
 "m6t5": [
  dict(name="M6-5 RR1 receives PE3's path through X2 as an additional path, and PE1 learns it as a second path", pts=(60, 12),
       command=probe(show("RR1", f"show bgp {PFX}"), show("PE1", f"show bgp {PFX}")),
       raw=[{"regex": sec("RR1", f"show bgp {PFX}") + r"from 10\.255\.0\.3 \(10\.255\.0\.3\)\n\s+Origin[^\n]*add-path\n\s+Received Path ID [1-9]"},
            {"regex": sec("PE1", f"show bgp {PFX}") + r"from 10\.255\.0\.21 \(10\.255\.0\.3\)\n\s+Origin[^\n]*\n\s+Received Path ID [1-9]"}]),
  dict(name="M6-5 The path through PE2 is still the best on PE1 and PE3, and PE3 does not use best-external", pts=(40, 8),
       command=probe(show("PE1", f"show bgp {PFX}"), show("PE3", f"show bgp {PFX}"), show("PE3", "show running-config router bgp")),
       raw=[{"regex": sec("PE1", f"show bgp {PFX}") + r"Paths: \(2 available, best #1\)"},
            {"regex": sec("PE1", f"show bgp {PFX}") + r"from 10\.255\.0\.21 \(10\.255\.0\.2\)\n\s+Origin[^\n]*localpref 200, valid, internal, best"},
            {"regex": sec("PE3", f"show bgp {PFX}") + r"from 10\.255\.0\.21 \(10\.255\.0\.2\)\n\s+Origin[^\n]*localpref 200, valid, internal, best"},
            {"not_regex": r"best-external"}]),
 ],
 "m6t6": [
  dict(name="M6-6 PE1 holds the path through PE3 as a backup path in the RIB and in CEF", pts=(40, 8),
       command=probe(show("PE1", f"show route {PFX} detail"), show("PE1", f"show cef {PFX} detail")),
       raw=[{"regex": r"10\.255\.0\.3, from 10\.255\.0\.21, BGP backup path"},
            {"regex": r"via 10\.255\.0\.3/32, \d+ dependencies, recursive, backup"}]),
  dict(name="M6-6 When the link between PE2 and P1 goes down, traffic from CE1 to T stops for less than one second", pts=(60, 12),
       command=probe("--failover 'CE1:192.168.1.1:203.0.113.1:P1:GigabitEthernet0/0/0/1'", "--recover 60",
                     "--after 'PE1:show bgp summary'"),
       raw=[{"regex": r"== FAILOVER PERIODS \d+ MAXLEN (?:\d|[1-9]\d) TAIL 0 VALID 1"}]),
 ],
 "m6t7": [
  dict(name="M6-7 The PE2–X1 session is established with GTSM on both ends (X1 accepts TTL 254 and above for one hop, sends 255)", pts=(60, 9),
       command=probe(show("X1", "show ip bgp neighbors 172.16.2.254"), show("PE2", "show bgp neighbor 172.16.2.1")),
       raw=[{"regex": sec("X1", "show ip bgp neighbors 172.16.2.254") + r"BGP state = Established"},
            {"regex": r"Mininum incoming TTL 254, Outgoing TTL 255"},
            {"regex": sec("PE2", "show bgp neighbor 172.16.2.1") + r"TTL security is configured"}]),
  dict(name="M6-7 PE2 still learns 203.0.113.0/24 from X1, and PE1 still uses the path through PE2", pts=(40, 6),
       command=probe(show("PE2", "show bgp neighbor 172.16.2.1 routes"), show("PE1", f"show bgp {PFX}"), show("PE2", "show bgp neighbor 172.16.2.1")),
       raw=[{"regex": sec("PE2", "show bgp neighbor 172.16.2.1") + r"TTL security is configured"},
            {"regex": sec("PE2", "show bgp neighbor 172.16.2.1 routes") + r"203\.0\.113\.0/24\s+172\.16\.2\.1"},
            {"regex": sec("PE1", f"show bgp {PFX}") + r"from 10\.255\.0\.21 \(10\.255\.0\.2\)\n\s+Origin[^\n]*valid, internal, best"}]),
 ],
 "m6t8": [
  dict(name="M6-8 The PE3–X2 session is established with TCP-AO (key 7 of AS65100-AO active on PE3)", pts=(60, 9),
       command=probe(show("X2", "show ip bgp neighbors 172.16.3.254"), show("PE3", "show tcp authentication keychain AS65100-AO")),
       raw=[{"regex": sec("X2", "show ip bgp neighbors 172.16.3.254") + r"BGP state = Established"},
            {"regex": r"Option Flags:[^\n]*TCP AO"},
            {"regex": r"Key ID: 7, Active, Valid"}]),
  dict(name="M6-8 PE3 still learns 203.0.113.0/24 from X2, and RR1 still has PE3's path", pts=(40, 6),
       command=probe(show("PE3", "show bgp neighbor 172.16.3.1 routes"), show("RR1", f"show bgp {PFX}"), show("PE3", "show tcp authentication keychain AS65100-AO")),
       raw=[{"regex": r"Key ID: 7, Active, Valid"},
            {"regex": sec("PE3", "show bgp neighbor 172.16.3.1 routes") + r"203\.0\.113\.0/24\s+172\.16\.3\.1"},
            {"regex": sec("RR1", f"show bgp {PFX}") + r"from 10\.255\.0\.3 \(10\.255\.0\.3\)"}]),
 ],
 "m6t9": [
  dict(name="M6-9 PE1 limits CE1 to four prefixes with a warning at 75% and a restart after two minutes; the session is up with CE1's two routes", pts=(40, 6),
       command=probe(f"--waitfor '{EST}'", show("PE1", "show bgp neighbor 172.16.1.1"), show("PE1", "show bgp summary")),
       raw=[{"regex": r"Maximum prefixes allowed 4\n\s+Threshold for warning message 75%, restart interval 2 min"},
            {"regex": sec("PE1", "show bgp summary") + r"172\.16\.1\.1\s+\d+\s+65001(?:\s+\d+){5}\s+\S+\s+2\n"}]),
  dict(name="M6-9 When CE1 sends five routes, PE1 tears the session down (Idle, PfxCt)", pts=(60, 9),
       command=probe("--pre 'CE1:interface Loopback11;;ip address 192.168.11.1 255.255.255.0;;interface Loopback12;;ip address 192.168.12.1 255.255.255.0;;"
                     "interface Loopback13;;ip address 192.168.13.1 255.255.255.0;;router bgp 65001;;address-family ipv4;;network 192.168.11.0;;network 192.168.12.0;;network 192.168.13.0'",
                     "--settle 5", f"--waitfor '{PFXCT}'", show("PE1", "show bgp summary"),
                     "--post 'CE1:router bgp 65001;;address-family ipv4;;no network 192.168.11.0;;no network 192.168.12.0;;no network 192.168.13.0;;exit;;exit;;"
                     "no interface Loopback11;;no interface Loopback12;;no interface Loopback13'",
                     "--post 'PE1:@clear bgp 172.16.1.1'", f"--postwait '{EST}'"),
       raw=[{"regex": sec("PE1", "show bgp summary") + r"172\.16\.1\.1\s+\d+\s+65001[^\n]*Idle \(PfxCt\)"}]),
 ],
 "m6t10": [
  dict(name="M6-10 After three flaps of 198.51.100.0/24 from X1, PE2 suppresses it (half-life 10 minutes)", pts=(50, 8),
       command=probe("--flap 'X1:172.16.2.254:198.51.100.0/24:3:5'", "--wait 5", "--after 'PE2:show bgp 198.51.100.0/24'",
                     "--post 'PE2:@clear bgp ipv4 unicast dampening'"),
       raw=[{"regex": r"\(suppressed due to dampening\)\n\s+172\.16\.2\.1 from 172\.16\.2\.1[\s\S]*?half life 00:10:00"}]),
  dict(name="M6-10 X1 and X2 receive 192.168.0.0/22 from PE2 and PE3, and none of the /24 routes inside it", pts=(50, 7),
       command=probe(show("X1", "show ip bgp neighbors 172.16.2.254 routes"), show("X2", "show ip bgp neighbors 172.16.3.254 routes")),
       raw=[{"regex": sec("X1", "show ip bgp neighbors 172.16.2.254 routes") + r"192\.168\.0\.0/22\s+172\.16\.2\.254"},
            {"regex": sec("X2", "show ip bgp neighbors 172.16.3.254 routes") + r"192\.168\.0\.0/22\s+172\.16\.3\.254"},
            {"not_regex": r"\n\s*\S*\s+192\.168\.[12]\.0(?:/24)?\s+172\.16\.[23]\.254"}]),
 ],
}

HEAD = {
 "m6t5": "M6-5: 追加パス。白紙= PE3 は X2 の経路を出さない → 0 点(2 つ目も PE1 が 2 本を持つことを条件にした)。",
 "m6t6": "M6-6: PIC。白紙= 予備なし・途切れ 2〜3 秒 → 0 点。確認は P1 の PE2 向けの IF を落として IP SLA で測る(2 分ほど)。",
 "m6t7": "M6-7: GTSM。白紙= TTL セキュリティなし → 0 点。",
 "m6t8": "M6-8: TCP-AO。白紙= 認証なし → 0 点。",
 "m6t9": "M6-9: maximum-prefix。白紙= 上限なし → 0 点。確認は CE1 に 3 本足して外し、PE1 で張り直す。",
 "m6t10": "M6-10: ダンプニングと集約。白紙= なし → 0 点。確認は X1 から PE2 への 198.51.100.0/24 を 3 回揺らし、PE2 のダンプニングを消す。",
}


def checks(step, final):
    out = []
    for c in CHECKS[step]:
        out.append({"name": c["name"], "node": "PE1", "exec": "local", "command": c["command"],
                    "raw": c["raw"], "points": c["pts"][1 if final else 0]})
    return out


def dump(path, head, data):
    with open(path, "w", encoding="utf-8") as f:
        f.write(head)
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, width=200)


for step in CHECKS:
    cs = checks(step, False)
    assert sum(c["points"] for c in cs) == 100, step
    dump(f"{P}/grading.{step}.yml",
         f"# {HEAD[step]}\n# 確認は poc/xr/gen_grading_xrt17.py で組んだ(中身を直したら組み直す)。道具= topologies/bgpops_probe.py。\n",
         {"problem": "XRT-17", "total_points": 100, "checks": cs})
allc = [c for step in CHECKS for c in checks(step, True)]
assert sum(c["points"] for c in allc) == 100, sum(c["points"] for c in allc)
dump(f"{P}/grading.yml", "# XRT-17 の最終の確認(M6-5〜M6-10)。poc/xr/gen_grading_xrt17.py で組んだ。\n",
     {"problem": "XRT-17", "total_points": 100, "checks": allc})
print("ok", len(allc), "checks")
