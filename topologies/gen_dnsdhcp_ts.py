#!/usr/bin/env python3
"""社内DNS(BIND9)+DHCPリレー トラブルシュート生成器（Linuxサーバ構築ラボのTS版）。

組み立て問(gen_dnsdhcp_build.py)の姉妹編。「昨日まで動いていた DNS/DHCP が
今朝から壊れている」を復旧させる。健全構成（BIND ゾーン・dhcpd・リレー・
ルータの DNS クライアント）を day0 で丸ごと構築し、故障カタログから注入する。

正準トポロジ（build 版と同一・MAC 非依存）:
  SRV01(BIND9+isc-dhcp-server) --- RT01 --- RT02 --- PC01(DHCPクライアント)
  ※build 版と違い PC01 の「予約(固定割当)」は出さない（MAC が provision 毎に
    変わり healthy 設定に焼き込めないため）。台帳は gw.ccnp.local(=RT02 LAN GW)
    の A/PTR で置き換え、逆引き採点もそこで行う。

設計方針: 故障は「サーバ系」と「NW系」の2群。既定 --count 2 は各群から1つずつ
  選ぶ＝**サーバ屋とNW屋の切り分け**を必ず要求する。症状シグネチャ:
    DNS_PARTIAL   … 特定名/特定送信元だけ壊れる（末尾ドット・allow-query 等）
    DHCP_DOWN     … PC01 がリースを取れない（dhcpd 起動不能 / リレー欠落）
    DNS_PATH_DOWN … 経路上で UDP/53 だけ落ちる（ACL）
    RTR_RESOLVE   … ルータ自身だけ名前解決不能（name-server 欠落）
  新しい故障は FAULTS に mutate/fix を足すだけで追加できる。

採点: build 版と同じ挙動ベース（dig / resolvectl / リース / IOS ping by name /
  show hosts summary の実効ネームサーバ）。CNAME は行アンカー regex
  （部分文字列だと二重ドメイン srv01.<d>.<d>. を誤 PASS するため）。
  ゾーン TTL/negative TTL は 300/60 に短縮（fix 後のキャッシュ残りで採点が
  長引かないように。組み立て問で1週間TTLの怖さは学習済み）。

出力: problems/GEN-DNSTS-<seed>/
  {problem.yml, initial/{RT01,RT02}.cfg.j2, {SRV01,PC01}.cfg.j2(空),
   {SRV01,PC01}.sh.j2, grading.yml, task.md,
   solution/{fault.json, fix.json, SRV01_fix.sh, solution.md}}
使い方: gen_dnsdhcp_ts.py --repo . --seed <int> [--count 2] [--faults a,b]
検品:   fix.json→fix_generated.yml / SRV01_fix.sh→ansible script（引数不要・
        健全設定への全量復元なのでサーバ故障が何であっても直る）。
"""
import argparse
import json
import os
import random
import re

import yaml

DOMAIN = "ccnp.local"
SRV, PC = "SRV01", "PC01"
RTS = ["RT01", "RT02"]
SRV_IP = "10.99.0.2"
POOL = (101, 150)
ALIASES = ["intranet", "portal", "helpdesk"]


def rand_values(rnd):
    n = rnd.randint(20, 99)
    ks, lo = set(), {}
    for rt in RTS:
        while True:
            k = rnd.randint(1, 99)
            if k != 10 and k not in ks:
                ks.add(k)
                lo[rt] = f"{k}.{k}.{k}.{k}"
                break
    return {"n": n, "lo": lo, "alias": rnd.choice(ALIASES),
            "ns_victim": rnd.choice(RTS)}


# ---- 健全なサーバ設定ファイル群 ---------------------------------------------

def healthy_files(v):
    """path(識別キー) -> content。故障はこの辞書を書き換えて注入する。"""
    n, alias, lo = v["n"], v["alias"], v["lo"]
    soa = (f"@       IN SOA srv01.{DOMAIN}. admin.{DOMAIN}. "
           "( 2026070401 3600 600 86400 60 )")
    fwd = f"""$TTL 300
{soa}
@       IN NS  srv01.{DOMAIN}.
srv01   IN A   {SRV_IP}
rt01    IN A   {lo['RT01']}
rt02    IN A   {lo['RT02']}
gw      IN A   192.168.{n}.1
{alias:<7} IN CNAME srv01.{DOMAIN}.
"""
    rev = f"""$TTL 300
{soa}
@       IN NS  srv01.{DOMAIN}.
1       IN PTR gw.{DOMAIN}.
"""
    conf_local = f"""zone "{DOMAIN}" {{ type master; file "/etc/bind/db.{DOMAIN}"; }};
zone "{n}.168.192.in-addr.arpa" {{ type master; file "/etc/bind/db.192.168.{n}"; }};
"""
    options = f"""acl internal {{ 127.0.0.0/8; 10.0.0.0/8; 192.168.0.0/16; }};
options {{
        directory "/var/cache/bind";
        recursion yes;
        allow-query {{ internal; }};
        allow-recursion {{ internal; }};
        dnssec-validation no;
        listen-on {{ any; }};
        listen-on-v6 {{ any; }};
}};
"""
    dhcpd = f"""default-lease-time 600;
max-lease-time 7200;
authoritative;

# 待受IF(ens3)自身のサブネット宣言（無いと dhcpd が起動しない）
subnet 10.99.0.0 netmask 255.255.255.252 {{ }}

subnet 192.168.{n}.0 netmask 255.255.255.0 {{
  range 192.168.{n}.{POOL[0]} 192.168.{n}.{POOL[1]};
  option routers 192.168.{n}.1;
  option domain-name-servers {SRV_IP};
  option domain-name "{DOMAIN}";
}}
"""
    return {
        f"/etc/bind/db.{DOMAIN}": fwd,
        f"/etc/bind/db.192.168.{n}": rev,
        "/etc/bind/named.conf.local": conf_local,
        "/etc/bind/named.conf.options": options,
        "/etc/dhcp/dhcpd.conf": dhcpd,
        "IFACES": 'INTERFACESv4="ens3"',
    }


# ---- 故障カタログ ------------------------------------------------------------
# server 系: mutate(files, v) で healthy_files を書き換え
# nw 系:     ios(v) -> ノード別の追加/削除指示（rt_config が解釈）
# fix:       fix_generated.yml 互換エントリ（NW のみ。server は SRV01_fix.sh が全量復元）

FAULTS = {
    # --- server 系 ---
    "zone_dot_missing": {
        "group": "server", "difficulty": 4, "signature": "DNS_PARTIAL",
        "desc": "CNAME 右辺の末尾ドット欠落 → 二重ドメイン(srv01.<d>.<d>.)に展開",
        "mutate": lambda f, v: f.update({
            f"/etc/bind/db.{DOMAIN}":
                f[f"/etc/bind/db.{DOMAIN}"].replace(
                    f"IN CNAME srv01.{DOMAIN}.", f"IN CNAME srv01.{DOMAIN}")}),
    },
    "zone_file_path": {
        "group": "server", "difficulty": 3, "signature": "DNS_PARTIAL",
        "desc": "named.conf.local の逆引き file パスが実ファイル名と不一致 → SERVFAIL",
        "mutate": lambda f, v: f.update({
            "/etc/bind/named.conf.local":
                f["/etc/bind/named.conf.local"].replace(
                    f"/etc/bind/db.192.168.{v['n']}",
                    f"/etc/bind/db.{v['n']}.rev")}),
    },
    "allow_query_narrow": {
        "group": "server", "difficulty": 4, "signature": "DNS_PARTIAL",
        "desc": "allow-query の acl から 192.168.0.0/16 が漏れ → PC01 だけ REFUSED",
        "mutate": lambda f, v: f.update({
            "/etc/bind/named.conf.options":
                f["/etc/bind/named.conf.options"].replace(
                    " 192.168.0.0/16;", "")}),
    },
    "dhcpd_iface_blank": {
        "group": "server", "difficulty": 3, "signature": "DHCP_DOWN",
        "desc": "INTERFACESv4 が空 → dhcpd 起動失敗（journalctl に理由）",
        "mutate": lambda f, v: f.update({"IFACES": 'INTERFACESv4=""'}),
    },
    "dhcpd_subnet_missing": {
        "group": "server", "difficulty": 4, "signature": "DHCP_DOWN",
        "desc": "待受IFサブネットの空宣言が消失 → dhcpd 起動拒否",
        "mutate": lambda f, v: f.update({
            "/etc/dhcp/dhcpd.conf": re.sub(
                r"# 待受IF.*\nsubnet 10\.99\.0\.0[^\n]*\n\n", "",
                f["/etc/dhcp/dhcpd.conf"])}),
    },
    # --- NW 系 ---
    "helper_missing": {
        "group": "nw", "difficulty": 3, "signature": "DHCP_DOWN",
        "desc": "RT02 ユーザLAN IF の ip helper-address 欠落 → DISCOVER が届かない",
        "ios": lambda v: {"RT02": {"no_helper": True}},
        "fixes": lambda v: [{"node": "RT02",
                             "parents": ["interface Ethernet0/1"],
                             "lines": [f"ip helper-address {SRV_IP}"]}],
    },
    "acl_udp53": {
        "group": "nw", "difficulty": 4, "signature": "DNS_PATH_DOWN",
        "desc": "RT01 の RT02 側受信 ACL が UDP/53 だけ deny（ping/DHCP は通る）",
        "ios": lambda v: {"RT01": {"acl53": True}},
        "fixes": lambda v: [
            {"node": "RT01", "parents": ["interface Ethernet0/1"],
             "lines": ["no ip access-group DNSBLOCK in"]},
            {"node": "RT01", "lines": ["no ip access-list extended DNSBLOCK"]},
        ],
    },
    "name_server_removed": {
        "group": "nw", "difficulty": 3, "signature": "RTR_RESOLVE",
        "desc": "ルータ1台の ip name-server 欠落（名前 ping はキャッシュで一時的に通ることも）",
        "ios": lambda v: {v["ns_victim"]: {"no_ns": True}},
        "fixes": lambda v: [{"node": v["ns_victim"],
                             "lines": [f"ip name-server {SRV_IP}"]}],
    },
}


# ---- initial: ルータ ----------------------------------------------------------

def rt01_cfg(v, mods):
    lo = v["lo"]["RT01"]
    m = mods.get("RT01", {})
    lines = ["! --- data plane ---",
             "interface Loopback0",
             f" ip address {lo} 255.255.255.255",
             "interface Ethernet0/0",
             " description === to SRV01 (server segment) ===",
             " ip address 10.99.0.1 255.255.255.252",
             " no shutdown",
             "interface Ethernet0/1",
             " description === to RT02 ===",
             " ip address 10.1.12.1 255.255.255.252",
             " no shutdown"]
    if m.get("acl53"):
        lines += ["ip access-list extended DNSBLOCK",
                  f" deny udp any host {SRV_IP} eq domain",
                  " permit ip any any",
                  "interface Ethernet0/1",
                  " ip access-group DNSBLOCK in"]
    lines += ["router ospf 1",
              f" router-id {lo}",
              f" network {lo} 0.0.0.0 area 0",
              " network 10.99.0.0 0.0.0.3 area 0",
              " network 10.1.12.0 0.0.0.3 area 0"]
    if not m.get("no_ns"):
        lines.append(f"ip name-server {SRV_IP}")
    return "\n".join(lines) + "\n"


def rt02_cfg(v, mods):
    lo, n = v["lo"]["RT02"], v["n"]
    m = mods.get("RT02", {})
    lines = ["! --- data plane ---",
             "interface Loopback0",
             f" ip address {lo} 255.255.255.255",
             "interface Ethernet0/0",
             " description === to RT01 ===",
             " ip address 10.1.12.2 255.255.255.252",
             " no shutdown",
             "interface Ethernet0/1",
             " description === user LAN (PC01) ===",
             f" ip address 192.168.{n}.1 255.255.255.0"]
    if not m.get("no_helper"):
        lines.append(f" ip helper-address {SRV_IP}")
    lines += [" no shutdown",
              "router ospf 1",
              f" router-id {lo}",
              f" network {lo} 0.0.0.0 area 0",
              " network 10.1.12.0 0.0.0.3 area 0",
              f" network 192.168.{n}.0 0.0.0.255 area 0"]
    if not m.get("no_ns"):
        lines.append(f"ip name-server {SRV_IP}")
    return "\n".join(lines) + "\n"


# ---- initial: サーバ/クライアント init.sh ------------------------------------

def files_to_heredocs(files, n):
    """設定ファイル群を bash の cat heredoc 連結に変換（init.sh / fix.sh 共用）。"""
    out = []
    for path, content in files.items():
        if path == "IFACES":
            out.append("sed -i 's/^INTERFACESv4=.*/"
                       + files["IFACES"].replace("/", r"\/")
                       + "/' /etc/default/isc-dhcp-server")
            continue
        out.append(f"cat > {path} <<'CCNP_EOF'\n{content}CCNP_EOF")
    return "\n\n".join(out)


def srv_init_sh(v, files):
    n = v["n"]
    return (
        """#!/bin/bash
# SRV01 (DNS/DHCP サーバ・稼働中設定) 初期化 — 生成: gen_dnsdhcp_ts.py
set -e
export DEBIAN_FRONTEND=noninteractive
log() { echo "[$(date -Is)] $*"; }

log "in-band NIC / 社内への経路を netplan で永続化"
rm -f /etc/netplan/50-cloud-init.yaml
cat > /etc/netplan/60-ccnp.yaml <<'EOF'
network:
  version: 2
  ethernets:
    ens2:
      addresses: [{{ mgmt_ip }}/{{ mgmt_prefixlen }}]
      routes:
        - to: default
          via: {{ mgmt_gw }}
      nameservers:
        addresses: {{ mgmt_dns | to_json }}
    ens3:
      addresses: [""" + SRV_IP + """/30]
      routes:
        - to: 10.1.12.0/30
          via: 10.99.0.1
        - to: 192.168.""" + str(n) + """.0/24
          via: 10.99.0.1
EOF
chmod 600 /etc/netplan/60-ccnp.yaml
netplan apply

log "パッケージ導入 (bind9 / isc-dhcp-server / dnsutils)"
for i in 1 2 3; do
  apt-get update -qq && \\
  apt-get install -y -qq bind9 bind9utils isc-dhcp-server dnsutils && break
  sleep 10
done

log "稼働中サービスの設定を投入（TS: この中に故障が仕込まれている）"
""" + files_to_heredocs(files, n) + """

systemctl restart named || true
systemctl restart isc-dhcp-server || true
systemctl enable -q named isc-dhcp-server || true
log "DONE"
"""
    )


def pc_init_sh():
    return """#!/bin/bash
# PC01 (利用者端末) 初期化 — 生成: gen_dnsdhcp_ts.py
set -e
export DEBIAN_FRONTEND=noninteractive
log() { echo "[$(date -Is)] $*"; }

log "採点用ツール導入 (dnsutils)"
for i in 1 2 3; do
  apt-get update -qq && apt-get install -y -qq dnsutils && break
  sleep 10
done

log "netplan 差替え: ens2=mgmt静的(defaultなし) / ens3=DHCPクライアント"
rm -f /etc/netplan/50-cloud-init.yaml
cat > /etc/netplan/60-ccnp.yaml <<'EOF'
network:
  version: 2
  ethernets:
    ens2:
      addresses: [{{ mgmt_ip }}/{{ mgmt_prefixlen }}]
    ens3:
      dhcp4: true
      dhcp4-overrides:
        use-domains: true
EOF
chmod 600 /etc/netplan/60-ccnp.yaml
netplan apply
log "DONE"
"""


def srv_fix_sh(v):
    """健全設定への全量復元（サーバ側 fix・故障が何であっても直る）。"""
    return ("""#!/bin/bash
# GEN-DNSTS サーバ側修復（自己検品/解答開示用）: 健全設定へ全量復元
set -e
[ "$(id -u)" = 0 ] || exec sudo -n bash "$0" "$@"

""" + files_to_heredocs(healthy_files(v), v["n"]) + """

named-checkconf
systemctl restart named
systemctl restart isc-dhcp-server
systemctl is-active named isc-dhcp-server
echo FIXED
""")


# ---- 出力 ---------------------------------------------------------------------

def build(repo, seed, count, forced):
    rnd = random.Random(seed)
    pid = f"GEN-DNSTS-{seed}"
    v = rand_values(rnd)
    n, alias, lo = v["n"], v["alias"], v["lo"]

    # 故障選定: 既定はサーバ群/NW群から1つずつ（切り分けを強制）
    if forced:
        chosen = forced
    else:
        srv_pool = sorted(k for k, f in FAULTS.items() if f["group"] == "server")
        nw_pool = sorted(k for k, f in FAULTS.items() if f["group"] == "nw")
        if count == 1:
            chosen = [rnd.choice(sorted(FAULTS))]
        else:
            chosen = [rnd.choice(srv_pool), rnd.choice(nw_pool)]
            chosen += rnd.sample([x for x in sorted(FAULTS) if x not in chosen],
                                 k=max(0, count - 2))

    # サーバファイル群へ mutate、IOS mods を合成
    files = healthy_files(v)
    ios_mods = {}
    for name in chosen:
        f = FAULTS[name]
        if "mutate" in f:
            f["mutate"](files, v)
        if "ios" in f:
            for node, mod in f["ios"](v).items():
                ios_mods.setdefault(node, {}).update(mod)

    pdir = f"{repo}/problems/{pid}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)

    with open(f"{pdir}/initial/RT01.cfg.j2", "w", encoding="utf-8") as fp:
        fp.write(rt01_cfg(v, ios_mods))
    with open(f"{pdir}/initial/RT02.cfg.j2", "w", encoding="utf-8") as fp:
        fp.write(rt02_cfg(v, ios_mods))
    for node in (SRV, PC):
        with open(f"{pdir}/initial/{node}.cfg.j2", "w", encoding="utf-8") as fp:
            fp.write("# server ノードは baseline_server.cfg.j2 が全て描画（このスタブは連結対策の空ファイル）\n")
    with open(f"{pdir}/initial/{SRV}.sh.j2", "w", encoding="utf-8") as fp:
        fp.write(srv_init_sh(v, files))
    with open(f"{pdir}/initial/{PC}.sh.j2", "w", encoding="utf-8") as fp:
        fp.write(pc_init_sh())

    difficulty = max(FAULTS[x]["difficulty"] for x in chosen)
    pmeta = {
        "id": pid,
        "title": f"社内DNS/DHCP 障害復旧 TS (seed={seed})",
        "exam": "ENCOR",
        "topics": ["dns", "bind9", "dhcp", "dhcp-relay", "linux", "server",
                   "troubleshooting", "generated"],
        "difficulty": difficulty,
        "topology": "generated",
        "target_nodes": RTS + [SRV, PC],
        "points": 100,
        "access": "ssh",
        "node_image_families": {SRV: "ubuntu", PC: "ubuntu"},
        "lab": {"links": [
            {"a": SRV, "a_if": 1, "b": "RT01", "b_if": 0},
            {"a": "RT01", "a_if": 1, "b": "RT02", "b_if": 0},
            {"a": "RT02", "a_if": 1, "b": PC, "b_if": 1},
        ]},
    }
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as fp:
        fp.write(f"# 自動生成 (gen_dnsdhcp_ts.py) seed={seed}\n")
        yaml.safe_dump(pmeta, fp, allow_unicode=True, sort_keys=False, width=4096)

    # grading（build 版と同型・予約→gw 置換・CNAME は行アンカー）
    esc_ip = SRV_IP.replace(".", r"\.")
    cname_anchor = (r"(^|\n)srv01\." + DOMAIN.replace(".", r"\.") + r"\.(\n|$)")
    checks = [
        {"name": "SRV01: named が稼働", "node": SRV, "exec": "shell",
         "command": "systemctl is-active named",
         "raw": [{"regex": "^active"}], "points": 5},
        {"name": f"SRV01: 正引き srv01.{DOMAIN}", "node": SRV, "exec": "shell",
         "command": f"dig +short @127.0.0.1 srv01.{DOMAIN} A",
         "raw": [{"contains": SRV_IP}], "points": 8},
        {"name": f"SRV01: 正引き rt01.{DOMAIN}", "node": SRV, "exec": "shell",
         "command": f"dig +short @127.0.0.1 rt01.{DOMAIN} A",
         "raw": [{"contains": lo["RT01"]}], "points": 4},
        {"name": f"SRV01: 正引き rt02.{DOMAIN}", "node": SRV, "exec": "shell",
         "command": f"dig +short @127.0.0.1 rt02.{DOMAIN} A",
         "raw": [{"contains": lo["RT02"]}], "points": 4},
        {"name": f"SRV01: CNAME {alias}.{DOMAIN} → srv01 (正確なFQDN)",
         "node": SRV, "exec": "shell",
         "command": f"dig +short @127.0.0.1 {alias}.{DOMAIN} CNAME",
         "raw": [{"regex": cname_anchor}], "points": 7},
        {"name": f"SRV01: 逆引き 192.168.{n}.1 → gw", "node": SRV, "exec": "shell",
         "command": f"dig +short @127.0.0.1 -x 192.168.{n}.1",
         "raw": [{"contains": f"gw.{DOMAIN}"}], "points": 8},
        {"name": "SRV01: isc-dhcp-server が稼働", "node": SRV, "exec": "shell",
         "command": "systemctl is-active isc-dhcp-server",
         "raw": [{"regex": "^active"}], "points": 5},
        {"name": f"PC01: DHCP で 192.168.{n}.0/24 のアドレスを取得", "node": PC,
         "exec": "shell", "command": "ip -4 addr show ens3",
         "raw": [{"regex": rf"inet 192\.168\.{n}\.\d+/24"}], "points": 13},
        {"name": "PC01: DHCP 配布の DNS が SRV01", "node": PC, "exec": "shell",
         "command": "resolvectl dns ens3",
         "raw": [{"contains": SRV_IP}], "points": 5},
        {"name": f"PC01: DHCP 配布の検索ドメインが {DOMAIN}", "node": PC,
         "exec": "shell", "command": "resolvectl domain ens3",
         "raw": [{"contains": DOMAIN}], "points": 4},
        {"name": f"PC01: {alias}.{DOMAIN} を名前解決", "node": PC, "exec": "shell",
         "command": f"dig +short {alias}.{DOMAIN}",
         "raw": [{"contains": SRV_IP}], "points": 7},
        {"name": f"PC01: {alias}.{DOMAIN} へ ping", "node": PC, "exec": "shell",
         "command": f"ping -c 2 -W 1 {alias}.{DOMAIN}",
         "raw": [{"regex": " 0% packet loss"}], "points": 5},
        {"name": "RT02: ユーザLAN IF に DHCP リレー実効", "node": "RT02",
         "command": "show ip interface Ethernet0/1",
         "raw": [{"regex": "Helper address"}, {"contains": SRV_IP}], "points": 8},
        {"name": "RT01: 実効ネームサーバが SRV01", "node": "RT01",
         "command": "show hosts summary",
         "raw": [{"regex": f"Name servers are.*{esc_ip}"}], "points": 3},
        {"name": "RT02: 実効ネームサーバが SRV01", "node": "RT02",
         "command": "show hosts summary",
         "raw": [{"regex": f"Name servers are.*{esc_ip}"}], "points": 3},
        {"name": f"RT01: 名前で ping (srv01.{DOMAIN})", "node": "RT01",
         "command": f"ping srv01.{DOMAIN}",
         "raw": [{"contains": "!!!!"}], "points": 5},
        {"name": f"RT02: 名前で ping (srv01.{DOMAIN})", "node": "RT02",
         "command": f"ping srv01.{DOMAIN}",
         "raw": [{"contains": "!!!!"}], "points": 6},
    ]
    assert sum(c["points"] for c in checks) == 100
    grading = {"problem": pid, "total_points": 100,
               "defaults": {"genie_os": "iosxe"}, "checks": checks}
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as fp:
        fp.write(f"# 自動生成 (gen_dnsdhcp_ts.py) seed={seed}\n")
        yaml.safe_dump(grading, fp, allow_unicode=True, sort_keys=False, width=4096)

    # solution
    fixes = []
    for name in chosen:
        if "fixes" in FAULTS[name]:
            fixes += FAULTS[name]["fixes"](v)
    with open(f"{pdir}/solution/fault.json", "w", encoding="utf-8") as fp:
        json.dump({"count": len(chosen),
                   "faults": [{"type": x, "group": FAULTS[x]["group"],
                               "signature": FAULTS[x]["signature"],
                               "difficulty": FAULTS[x]["difficulty"],
                               "desc": FAULTS[x]["desc"]} for x in chosen]},
                  fp, ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/fix.json", "w", encoding="utf-8") as fp:
        json.dump({"fixes": fixes}, fp, ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/SRV01_fix.sh", "w", encoding="utf-8") as fp:
        fp.write(srv_fix_sh(v))
    os.chmod(f"{pdir}/solution/SRV01_fix.sh", 0o755)
    with open(f"{pdir}/solution/solution.md", "w", encoding="utf-8") as fp:
        fp.write(f"""# {pid} 解答（採点者用）

## 注入故障
{chr(10).join(f"- **{x}** ({FAULTS[x]['group']}): {FAULTS[x]['desc']}" for x in chosen)}

## 修復
- サーバ側: `SRV01_fix.sh`（健全設定へ全量復元・受験者は差分修正でよい）
- NW側: `fix.json`（fix_generated.yml で投入可）

## 受験者に期待する切り分け
症状（PC01 の名前解決/リース/ルータの解決）→ サーバか経路かの二分 →
dig の status(REFUSED/SERVFAIL/timeout) と journalctl / show access-lists で確定。
""")

    # task.md（TS: 故障の種類・場所・件数は伏せる。設計書=正 と操作ガイドは与える）
    task = f"""# 問題 {pid} : 社内DNS/DHCP 障害復旧（難易度{difficulty}）

## 障害チケット
> 昨日開通したユーザセグメント **192.168.{n}.0/24** の利用者から
> 「**PC01 がイントラ（{alias}.{DOMAIN}）に届かない／名前が引けない**」と申告。
> 昨日の開通試験ではすべて正常だった。**設計書どおりの状態に復旧**せよ。
> 原因は **1 箇所とは限らない**（サーバとネットワークの両方を疑うこと）。

```
 SRV01 ────── RT01 ────── RT02 ────── PC01
(DNS/DHCP)                          (利用者端末)
 10.99.0.0/30   10.1.12.0/30   192.168.{n}.0/24 (GW=.1)
```

## 設計書（正・この状態が採点される）
### DNS: `{DOMAIN}` ゾーン＋`192.168.{n}.0/24` 逆引き（サーバ=SRV01 {SRV_IP}）
| 名前 | 種別 | 値 |
|------|------|----|
| srv01.{DOMAIN} | A | {SRV_IP} |
| rt01.{DOMAIN} | A | {lo['RT01']} |
| rt02.{DOMAIN} | A | {lo['RT02']} |
| gw.{DOMAIN} | A | 192.168.{n}.1 |
| {alias}.{DOMAIN} | CNAME | srv01.{DOMAIN} |
| 192.168.{n}.1 | PTR | gw.{DOMAIN} |
- 応答・再帰とも社内 (10.0.0.0/8, 192.168.0.0/16) とローカルホストに許可

### DHCP（サーバ=SRV01 / isc-dhcp-server）
- ユーザLAN `192.168.{n}.0/24` に配布: レンジ .{POOL[0]}〜.{POOL[1]} /
  GW=`192.168.{n}.1` / DNS=`{SRV_IP}` / ドメイン名=`{DOMAIN}`
- ユーザLAN に DHCP サーバは無く、**RT02 がリレー**する設計

### ルータ
- RT01・RT02 とも SRV01 を DNS に使い、名前で ping できること

## 到達目標
- PC01 が DHCP でアドレス・GW・DNS・検索ドメインを取得し、
  `{alias}.{DOMAIN}` の名前解決と ping が成功
- SRV01 で正引き・逆引き・CNAME がすべて引ける（`dig @127.0.0.1`）
- RT01/RT02 から `ping srv01.{DOMAIN}` が成功

## 調査の道具箱（操作リファレンス。どこが壊れているかは自分で切り分けること）
- SRV01/PC01: SSH `SUZUKI / CCNP`（sudo 可）
- BIND9: 設定 `/etc/bind/`（named.conf.local / named.conf.options / db.*）。
  `named-checkconf` / `named-checkzone <ゾーン> <ファイル>` /
  `sudo journalctl -u named -e` / `dig @127.0.0.1 <名前>`（`dig` の
  status＝NOERROR/NXDOMAIN/SERVFAIL/REFUSED/timeout は最大の手がかり）
- isc-dhcp-server: `/etc/dhcp/dhcpd.conf` / `/etc/default/isc-dhcp-server` /
  `sudo journalctl -u isc-dhcp-server -e` / リース `/var/lib/dhcp/dhcpd.leases`
- PC01: `ip -4 addr show ens3` / `resolvectl dns ens3` / `resolvectl domain ens3` /
  リース再取得 `sudo networkctl reconfigure ens3` /
  キャッシュ掃除 `sudo resolvectl flush-caches`（サーバ側を直した後に）
- 反映: `sudo systemctl restart named` / `sudo systemctl restart isc-dhcp-server`

## 注意
- **設計書の値そのものは正しい**（設計ミスではなく、実装が設計とズレている）
- PC01 の ens2 (10.1.10.0/26) は管理・採点用。変更しないこと
- SRV01 のアドレス・経路（netplan）は正常。触るのはサービス設定のみ

## アクセス・採点
SSH `SUZUKI / CCNP`（MGMT: RT01=10.1.10.11, RT02=.12, SRV01=.13, PC01=.14）。
リース再取得・キャッシュの反映ラグがあるため attempts 多めで:
```
ansible-playbook playbooks/grade.yml -e problem={pid} -e max_attempts=20 \\
  --vault-password-file <(printf 'CCNP\\n')
```
"""
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as fp:
        fp.write(task)

    print(f"generated {pid}: faults={chosen} difficulty={difficulty} "
          f"LAN=192.168.{n}.0/24 alias={alias} lo={lo} ns_victim={v['ns_victim']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--count", type=int, default=2,
                    help="故障数（既定2: サーバ系1+NW系1で切り分けを強制）")
    ap.add_argument("--faults", help="カンマ区切りで故障を固定（既定 seed 乱択）")
    a = ap.parse_args()
    forced = a.faults.split(",") if a.faults else None
    if forced:
        for x in forced:
            if x not in FAULTS:
                raise SystemExit(f"unknown fault: {x} (candidates: {sorted(FAULTS)})")
    build(a.repo, a.seed, a.count, forced)


if __name__ == "__main__":
    main()
