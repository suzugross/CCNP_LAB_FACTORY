#!/usr/bin/env python3
"""XRT-16 の確認(grading.m14t<n>.yml と最終の grading.yml)を組む。確認の中身は CHECKS に 1 か所で持つ。
usage: python3 poc/xr/gen_grading_xrt16.py(リポの根で)。配点= (課題ごとの確認, 最終の確認)。"""
import yaml, sys
P = "problems/XRT-16"
PROBE = ".venv/bin/python topologies/mcast_probe.py XRT-16 run"

def join(node, groups, v3=False, src=None):
    lines = ["configure terminal", "interface Ethernet0/0"]
    if v3:
        lines.append("ip igmp version 3")
    for g in groups:
        lines.append(f"ip igmp join-group {{{g}}}" + (f" source {src}" if src else ""))
    lines.append("end")
    return f"'{node}:" + ";;".join(lines) + "'"

def leave(node, groups, src=None):
    lines = ["configure terminal", "interface Ethernet0/0"]
    for g in groups:
        lines.append(f"no ip igmp join-group {{{g}}}" + (f" source {src}" if src else ""))
    lines += ["no ip igmp version", "end"]
    return f"'{node}:" + ";;".join(lines) + "'"

def mld(node, groups, add=True):
    lines = ["configure terminal", "interface Ethernet0/0"]
    for g in groups:
        lines.append(("" if add else "no ") + f"ipv6 mld join-group {{{g}}}")
    lines.append("end")
    return f"'{node}:" + ";;".join(lines) + "'"

def probe(*parts):
    return PROBE + " " + " ".join(parts)

R2, R3, S1 = "192.168.2.1", "192.168.3.1", "192.168.1.1"
def got(sender, addr, n8=True):
    a = addr.replace(".", r"\.")
    return {"regex": rf"== REPLY {sender} {a} (?:8|9|10)\n"} if n8 else {"regex": rf"== REPLY {sender} {a} 0\n"}

def send(g, sender="SRC1", frm=(R2, R3)):
    s = f"--warm '{sender}:ping {{{g}}} repeat 3 timeout 1' --send '{sender}:ping {{{g}}} repeat 10 timeout 1'"
    return s + "".join(f" --from {a}" for a in frm)

CHECKS = {
 "m14t1": [
  dict(name="M14-1 RCV2 and RCV3 receive a channel in 239.16.0.0/16 from SRC1", pts=(60, 9),
       command=probe("--group G=239.16.0.0/16", "--pre-cli", join("RCV2", ["G"]), "--pre-cli", join("RCV3", ["G"]), "--settle 10", send("G"),
                     "--post-cli", leave("RCV2", ["G"]), "--post-cli", leave("RCV3", ["G"])),
       raw=[got("SRC1", R2), got("SRC1", R3)]),
  dict(name="M14-1 Multicast runs on both of PE4's links and on PE3, and a group outside 239.0.0.0/8 has no RP (PE2, PE4)", pts=(40, 6),
       command=probe("--group H=225.0.0.0/8", "--pre-cli", join("RCV3", ["H"]), "--settle 10",
                     "--show 'PE4:show ip pim interface'", "--show 'PE3:show pim interface'", "--show 'PE2:show pim group-map {H}'",
                     "--show 'PE4:show ip mroute {H} | begin \\('", "--post-cli", leave("RCV3", ["H"])),
       raw=[{"regex": r"Ethernet0/0\s+v2/S"}, {"regex": r"Ethernet0/1\s+v2/S"},
            {"regex": r"GigabitEthernet0/0/0/0\s+on\s"}, {"regex": r"GigabitEthernet0/0/0/1\s+on\s"},
            {"regex": r"== SHOW PE2: show pim group-map[\s\S]*?\n\S+\*\s+SM\s+static\s+\d+\s+0\.0\.0\.0\s"},
            {"regex": r"\(\*, 225\.\d+\.\d+\.\d+\), [^\n]*RP 0\.0\.0\.0,"}]),
 ],
 "m14t2": [
  dict(name="M14-2 An ultra-HD channel (239.17.0.0/16) reaches RCV2 and RCV3 and stays on the shared tree (no source state on PE2 and PE4)", pts=(60, 9),
       command=probe("--group G=239.17.0.0/16", "--pre-cli", join("RCV2", ["G"]), "--pre-cli", join("RCV3", ["G"]), "--settle 10", send("G"),
                     "--show 'PE2:show pim topology {G} | include ,239'", "--show 'PE4:show ip mroute {G} | begin \\('",
                     "--post-cli", leave("RCV2", ["G"]), "--post-cli", leave("RCV3", ["G"])),
       raw=[got("SRC1", R2), got("SRC1", R3), {"regex": r"== SHOW PE2: [\s\S]*\(\*,239\.17\.\d+\.\d+\) SM"},
            {"regex": r"\(\*, 239\.17\.\d+\.\d+\), [^\n]*RP 10\.255\.0\.11"},
            {"not_regex": r"\(192\.168\.1\.1, ?239\.17\."}]),
  dict(name="M14-2 A TV channel (239.16.0.0/16) still switches to the shortest-path tree on PE2, over the direct link to PE1", pts=(40, 6),
       command=probe("--group G=239.16.0.0/16", "--pre-cli", join("RCV2", ["G"]), "--pre-cli", join("RCV3", ["G"]), "--settle 10", send("G"),
                     "--show 'PE2:show pim topology {G}'",
                     "--post-cli", leave("RCV2", ["G"]), "--post-cli", leave("RCV3", ["G"])),
       raw=[got("SRC1", R2), got("SRC1", R3),
            {"regex": r"\(192\.168\.1\.1,239\.16\.\d+\.\d+\)SPT SM[^\n]*\n[^\n]*RPF: GigabitEthernet0/0/0/0,10\.0\.12\.1"}]),
 ],
 "m14t3": [
  dict(name="M14-3 A receiver naming SRC1 gets a channel in 239.232.0.0/16 as SSM: RCV2 and RCV3 receive it and the RP holds no state", pts=(40, 8),
       command=probe("--group G=239.232.0.0/16", "--pre-cli", join("RCV2", ["G"], v3=True, src=S1), "--pre-cli", join("RCV3", ["G"], v3=True, src=S1),
                     "--settle 10", send("G"), "--show 'P1:show pim topology {G} | include ,239'", "--show 'PE2:show pim topology {G} | include ,239'",
                     "--show 'PE4:show ip mroute {G} | begin \\('",
                     "--post-cli", leave("RCV2", ["G"], src=S1), "--post-cli", leave("RCV3", ["G"], src=S1)),
       raw=[got("SRC1", R2), got("SRC1", R3), {"regex": r"== SHOW PE2: [\s\S]*\(192\.168\.1\.1,239\.232\.\d+\.\d+\)SPT SSM"},
            {"regex": r"\(192\.168\.1\.1, 239\.232\.\d+\.\d+\), [^\n]*flags: s"},
            {"regex": r"== SHOW P1: show pim topology[^\n]*\n(?:(?!\(192\.168\.1\.1)[^\n]*\n)*?== SHOW PE2"}]),
  dict(name="M14-3 232.0.0.0/8 is still SSM: RCV2 and RCV3 receive a channel in it from SRC1", pts=(30, 6),
       command=probe("--group G=232.0.0.0/8", "--pre-cli", join("RCV2", ["G"], v3=True, src=S1), "--pre-cli", join("RCV3", ["G"], v3=True, src=S1),
                     "--settle 10", send("G"), "--show 'PE1:show pim topology {G} | include ,232'", "--show 'PE4:show ip mroute {G} | begin \\('",
                     "--post-cli", leave("RCV2", ["G"], src=S1), "--post-cli", leave("RCV3", ["G"], src=S1)),
       raw=[got("SRC1", R2), got("SRC1", R3), {"regex": r"\(192\.168\.1\.1,232\.\d+\.\d+\.\d+\)SPT SSM"},
            {"regex": r"\(192\.168\.1\.1, 232\.\d+\.\d+\.\d+\), [^\n]*flags: s"}]),
  dict(name="M14-3 A receiver that names no source gets nothing in 239.232.0.0/16, and P1 and PE3 treat both ranges as SSM", pts=(30, 6),
       command=probe("--group G=239.232.0.0/16 --group B=232.0.0.0/8", "--pre-cli", join("RCV2", ["G"]), "--pre-cli", join("RCV3", ["G"]),
                     "--settle 10", send("G"), "--show 'P1:show pim group-map {G}'", "--show 'PE3:show pim group-map {G}'",
                     "--show 'P1:show pim group-map {B}'", "--show 'PE3:show pim group-map {B}'",
                     "--post-cli", leave("RCV2", ["G"]), "--post-cli", leave("RCV3", ["G"])),
       raw=[got("SRC1", R2, n8=False), got("SRC1", R3, n8=False),
            {"regex": r"== SHOW P1: show pim group-map 239[\s\S]*?239\.232\.0\.0/16\*\s+SSM"},
            {"regex": r"== SHOW PE3: show pim group-map 239[\s\S]*?239\.232\.0\.0/16\*\s+SSM"},
            {"regex": r"== SHOW P1: show pim group-map 232[\s\S]*?232\.0\.0\.0/8\*\s+SSM"},
            {"regex": r"== SHOW PE3: show pim group-map 232[\s\S]*?232\.0\.0\.0/8\*\s+SSM"}]),
 ],
}
CHECKS["m14t4"] = [
  dict(name="M14-4 In 239.48.0.0/16 any host can send: RCV3's packets reach SRC1 and RCV2, and SRC1's reach RCV2 and RCV3", pts=(60, 9),
       command=probe("--group G=239.48.0.0/16", "--pre-cli", join("SRC1", ["G"]), "--pre-cli", join("RCV2", ["G"]), "--pre-cli", join("RCV3", ["G"]),
                     "--settle 10", "--warm 'RCV3:ping {G} repeat 3 timeout 1' --warm 'SRC1:ping {G} repeat 3 timeout 1'",
                     "--send 'RCV3:ping {G} repeat 10 timeout 1' --send 'SRC1:ping {G} repeat 10 timeout 1'",
                     f"--from {S1} --from {R2} --from {R3}",
                     "--post-cli", leave("SRC1", ["G"]), "--post-cli", leave("RCV2", ["G"]), "--post-cli", leave("RCV3", ["G"])),
       raw=[got("RCV3", S1), got("RCV3", R2), got("SRC1", R2), got("SRC1", R3)]),
  dict(name="M14-4 239.48.0.0/16 is bidirectional with RP 10.255.0.3 on PE2 and PE4, and no router keeps per-source state after traffic from two sources", pts=(40, 6),
       command=probe("--group G=239.48.0.0/16", "--pre-cli", join("SRC1", ["G"]), "--pre-cli", join("RCV2", ["G"]), "--pre-cli", join("RCV3", ["G"]),
                     "--settle 10", "--send 'RCV3:ping {G} repeat 5 timeout 1' --send 'SRC1:ping {G} repeat 5 timeout 1'",
                     "--show 'PE2:show pim group-map {G}'", "--show 'PE2:show pim topology {G} | include ,239'",
                     "--show 'P1:show pim topology {G} | include ,239'", "--show 'PE1:show pim topology {G} | include ,239'",
                     "--show 'PE4:show ip mroute {G} | begin \\('",
                     "--post-cli", leave("SRC1", ["G"]), "--post-cli", leave("RCV2", ["G"]), "--post-cli", leave("RCV3", ["G"])),
       raw=[{"regex": r"239\.48\.0\.0/16\*\s+BD\s+config\s+\d+\s+10\.255\.0\.3\s"},
            {"regex": r"\(\*,239\.48\.\d+\.\d+\) BD Up"},
            {"regex": r"\(\*, 239\.48\.\d+\.\d+\), [^\n]*RP 10\.255\.0\.3, flags: B"},
            {"not_regex": r"\(192\.168\.\d\.1, ?239\.48\."}]),
]

CHECKS["m14t5"] = [
  dict(name="M14-5 PE1 is the BSR on PE2 and PE4, and P1 is a candidate BSR that is not elected", pts=(30, 6),
       command=probe("--settle 0", "--show 'PE2:show pim bsr election'", "--show 'PE4:show ip pim bsr-router'", "--show 'P1:show pim bsr election'"),
       raw=[{"regex": r"== SHOW PE2:[\s\S]*?Accept-Pref\s+\S+\s+\S+\s+10\.255\.0\.1 \[\d+, \d+\]"},
            {"regex": r"BSR address: 10\.255\.0\.1 "},
            {"regex": r"== SHOW P1:[\s\S]*?Not-Elected/\S+\s+\S+\s+\S+\s+10\.255\.0\.1 \[\d+, \d+\]\s+10\.255\.0\.11 \[\d+, \d+\]"}]),
  dict(name="M14-5 PE2 and PE4 learn three candidate RPs for 239.16.0.0/15 through BSR, ranked P1, PE3, PE4", pts=(40, 8),
       command=probe("--settle 0", "--rporder 'PE2:239.16.0.0/15'", "--rporder 'PE4:239.16.0.0/15'"),
       raw=[{"regex": r"== RPORDER PE2 239\.16\.0\.0/15 10\.255\.0\.11,10\.255\.0\.3,10\.255\.0\.4\n"},
            {"regex": r"== RPORDER PE4 239\.16\.0\.0/15 10\.255\.0\.11,10\.255\.0\.3,10\.255\.0\.4\n"}]),
  dict(name="M14-5 A TV channel reaches RCV2 and RCV3 with P1 as the RP learned through BSR (PE1, PE2, PE3, PE4)", pts=(30, 6),
       command=probe("--group G=239.16.0.0/16", "--pre-cli", join("RCV2", ["G"]), "--pre-cli", join("RCV3", ["G"]), "--settle 10", send("G"),
                     "--show 'PE1:show pim group-map {G}'", "--show 'PE2:show pim group-map {G}'", "--show 'PE3:show pim group-map {G}'",
                     "--show 'PE4:show ip mroute {G} | include RP'",
                     "--post-cli", leave("RCV2", ["G"]), "--post-cli", leave("RCV3", ["G"])),
       raw=[got("SRC1", R2), got("SRC1", R3),
            {"regex": r"== SHOW PE1:[\s\S]*?239\.16\.0\.0/15\*\s+SM\s+bsr\+?\s+\d+\s+10\.255\.0\.11\s[\s\S]*== SHOW PE2"},
            {"regex": r"== SHOW PE2:[\s\S]*?239\.16\.0\.0/15\*\s+SM\s+bsr\+?\s+\d+\s+10\.255\.0\.11\s[\s\S]*== SHOW PE3"},
            {"regex": r"== SHOW PE3:[\s\S]*?239\.16\.0\.0/15\*\s+SM\s+bsr\+?\s+\d+\s+10\.255\.0\.11\s[\s\S]*== SHOW PE4"},
            {"regex": r"\(\*, 239\.16\.\d+\.\d+\), [^\n]*RP 10\.255\.0\.11"}]),
]

V2, V3 = "2001:db8:100:2::1", "2001:db8:100:3::1"
def got6(addr):
    return {"regex": rf"== REPLY SRC1 {addr} (?:8|9|10)\n"}
V6SEND = f"--warm 'SRC1:ping {{G}} repeat 3 timeout 1' --send 'SRC1:ping {{G}} repeat 10 timeout 1' --from {V2} --from {V3}"
CHECKS["m14t6"] = [
  dict(name="M14-6 RCV2 receives an IPv6 channel in FF0E::16:0/112 from SRC1, and the RP still filters Register messages (accept-register, ending in a deny)", pts=(50, 8),
       command=probe("--group G=FF0E::16:0/112", "--pre-cli", mld("RCV2", ["G"]), "--pre-cli", mld("RCV3", ["G"]), "--settle 10", V6SEND,
                     "--show 'P1:show running-config router pim address-family ipv6'", "--show 'P1:show running-config ipv6 access-list'",
                     "--post-cli", mld("RCV2", ["G"], add=False), "--post-cli", mld("RCV3", ["G"], add=False)),
       raw=[got6(V2), {"regex": r"address-family ipv6[\s\S]*?accept-register \S+"},
            {"regex": r"== SHOW P1: show running-config ipv6 access-list[\s\S]*?\bdeny ipv6 any any"}]),
  dict(name="M14-6 RCV3 receives an IPv6 channel in FF0E::16:0/112 from SRC1", pts=(50, 7),
       command=probe("--group G=FF0E::16:0/112", "--pre-cli", mld("RCV2", ["G"]), "--pre-cli", mld("RCV3", ["G"]), "--settle 10", V6SEND,
                     "--post-cli", mld("RCV2", ["G"], add=False), "--post-cli", mld("RCV3", ["G"], add=False)),
       raw=[got6(V3)]),
]

HEAD = {
 "m14t1": "M14-1: PIM-SM と静的 RP。白紙= マルチキャストなし → 0 点。",
 "m14t2": "M14-2: 239.17 を共有ツリーに留める(PE2 と PE4)・239.16 は切り替える。",
 "m14t3": "M14-3: SSM= 232/8 と 239.232/16・PE4 の IGMPv3。",
 "m14t4": "M14-4: BIDIR= 239.48/16・RP= PE3。PE4 は静的 RP の一覧の重なり(IOS は大きい RP アドレスを選ぶ)に注意。",
 "m14t5": "M14-5: BSR= 239.16/15。候補 RP の並び= P1・PE3・PE4、BSR= PE1。",
 "m14t6": "M14-6: IPv6 の TS(前任者の試行)。故障= P1 の accept-register の一覧の並び順・PE4 の RP の取り違え。",
}

def write():
    import os
    final = []
    for key, checks in CHECKS.items():
        doc = {"problem": "XRT-16", "total_points": 100, "checks": []}
        for c in checks:
            ent = {"name": c["name"], "node": "PE1", "exec": "local", "command": c["command"], "raw": c["raw"]}
            doc["checks"].append(dict(ent, points=c["pts"][0]))
            final.append(dict(ent, points=c["pts"][1]))
        assert sum(c["points"] for c in doc["checks"]) == 100, key
        with open(f"{P}/grading.{key}.yml", "w", encoding="utf-8") as fh:
            fh.write(f"# {HEAD[key]}\n# 確認は poc/xr/gen_grading_xrt16.py で組んだ(中身を直したら組み直す)。確認ごとに範囲の中から乱数でグループを選ぶ(topologies/mcast_probe.py)。\n")
            yaml.safe_dump(doc, fh, allow_unicode=True, sort_keys=False, width=250)
    assert sum(c["points"] for c in final) == 100, sum(c["points"] for c in final)
    with open(f"{P}/grading.yml", "w", encoding="utf-8") as fh:
        fh.write("# XRT-16 最終確認(M14-1〜6 を終えた状態。配点= 15/15/20/15/20/15)。学習目的のラボ= パック・ノルマの対象外。\n"
                 "# 中身は課題ごとの確認(grading.m14t<n>.yml)と同じもの(poc/xr/gen_grading_xrt16.py が両方を組む)。試験のトラフィックを流して数えるので 15 分ほどかかる。\n")
        yaml.safe_dump({"problem": "XRT-16", "total_points": 100, "checks": final}, fh, allow_unicode=True, sort_keys=False, width=250)

if __name__ == "__main__":
    write()
    print("ok", {k: len(v) for k, v in CHECKS.items()})
