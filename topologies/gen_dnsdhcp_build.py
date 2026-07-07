#!/usr/bin/env python3
"""社内DNS(BIND9)構築＋DHCPリレー 組み立て問題の生成器（Linuxサーバ構築ラボ第1弾）。

正準トポロジ(2RT+サーバ+クライアント端末):
  SRV01 --- RT01 --- RT02 --- PC01
  - SRV01(ubuntu): bind9/isc-dhcp-server を導入済み・未設定で渡す（構築が課題）。
    ens2=MGMT(採点/SSH), ens3=インバンド 10.99.0.2/30。アドレス/経路は netplan で
    永続化済み（受験者が reboot しても壊れない）。
  - PC01(ubuntu): ens3 が DHCP クライアント（netplan dhcp4, use-domains）。
    サーバとリレーが正しく構築されるまでリースは取れない＝「電源を入れれば
    IP が付く」を到達目標にする利用者視点の問題設計。
  - RT01/RT02: IF/OSPF は健全構成で投入済み。受験者の NW 課題は
    DHCP リレー（RT02）と ルータ自身の DNS クライアント化（両RT）。
    ※リレーのコマンドは task.md では明かさない（ヒント控えめポリシー）。

サーバ操作ガイド方針（ユーザ指示 2026-07-03）:
  受験者は NW ほどサーバに詳しくない → task.md に「ファイルの場所・検証コマンド・
  ハマりどころ（dhcpd の待受IFサブネット宣言等）」は詳しく書く。
  ただし設定値・設定文そのものは要件表から組み立てさせる（丸write禁止）。

採点（grade.yml の exec:shell）: すべて挙動ベース。
  SRV01 の dig(正引き/逆引き/CNAME)・サービス稼働 / PC01 の取得IP(予約一致)・
  DHCP配布DNS/ドメイン・名前解決/ping / RT の relay 実効値と名前 ping。

出力: problems/GEN-DNSDHCP-<seed>/
  {problem.yml, initial/{RT01,RT02}.cfg.j2, {SRV01,PC01}.cfg.j2(空), {SRV01,PC01}.sh.j2,
   grading.yml, task.md, solution/{solution.md, fix.json, SRV01_solve.sh}}
使い方: gen_dnsdhcp_build.py --repo . --seed <int>
検品:   fix.json は fix_generated.yml で投入、SRV01_solve.sh は
        ansible SRV01 -m script -a "SRV01_solve.sh <PC01のens3 MAC>" で投入。
"""
import argparse
import json
import os
import random

import yaml

DOMAIN = "ccnp.local"
SRV, PC = "SRV01", "PC01"
RTS = ["RT01", "RT02"]
SRV_IP = "10.99.0.2"            # SRV01 ens3（インバンド /30、.1=RT01）
POOL = (101, 150)               # DHCP 配布レンジ（第4オクテット）
ALIASES = ["intranet", "portal", "helpdesk"]


def rand_values(rnd):
    """seed から採番: LAN 第3オクテット / 予約IP / Loopback / CNAME 名。"""
    n = rnd.randint(20, 99)                       # ユーザLAN 192.168.<n>.0/24
    r = rnd.randint(50, 99)                       # PC01 予約（レンジ外）
    ks, lo = set(), {}
    for rt in RTS:
        while True:
            k = rnd.randint(1, 99)
            if k != 10 and k not in ks:
                ks.add(k)
                lo[rt] = f"{k}.{k}.{k}.{k}"
                break
    return {"n": n, "r": r, "lo": lo, "alias": rnd.choice(ALIASES)}


# ---- initial: ルータ（健全・変更不可の土台） -------------------------------

def rt01_cfg(v):
    lo = v["lo"]["RT01"]
    return f"""! --- data plane (構築済み・変更不可) ---
interface Loopback0
 ip address {lo} 255.255.255.255
interface Ethernet0/0
 description === to SRV01 (server segment) ===
 ip address 10.99.0.1 255.255.255.252
 no shutdown
interface Ethernet0/1
 description === to RT02 ===
 ip address 10.1.12.1 255.255.255.252
 no shutdown
router ospf 1
 router-id {lo}
 network {lo} 0.0.0.0 area 0
 network 10.99.0.0 0.0.0.3 area 0
 network 10.1.12.0 0.0.0.3 area 0
"""


def rt02_cfg(v):
    lo, n = v["lo"]["RT02"], v["n"]
    return f"""! --- data plane (構築済み・変更不可) ---
interface Loopback0
 ip address {lo} 255.255.255.255
interface Ethernet0/0
 description === to RT01 ===
 ip address 10.1.12.2 255.255.255.252
 no shutdown
interface Ethernet0/1
 description === user LAN (PC01) ===
 ip address 192.168.{n}.1 255.255.255.0
 no shutdown
router ospf 1
 router-id {lo}
 network {lo} 0.0.0.0 area 0
 network 10.1.12.0 0.0.0.3 area 0
 network 192.168.{n}.0 0.0.0.255 area 0
"""


# ---- initial: サーバ/クライアントの init.sh（cloud-init が実行） ------------

def srv_init_sh(v):
    """SRV01: パッケージ導入とネットワーク永続化まで。サービス設定は受験者の課題。
    ※受験者が触る箱なので、SNMPTS(ZBX01) と違い netplan で reboot 耐性を持たせる。"""
    n = v["n"]
    return (
        """#!/bin/bash
# SRV01 (DNS/DHCP サーバ素体) 初期化 — 生成: gen_dnsdhcp_build.py
set -e
export DEBIAN_FRONTEND=noninteractive
log() { echo "[$(date -Is)] $*"; }

log "in-band NIC / 社内への経路を netplan で永続化（reboot 耐性）"
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
# isc-dhcp-server は未設定のため起動失敗のまま = 正常（構築は受験者の課題）
log "DONE"
"""
    )


def pc_init_sh():
    """PC01: 採点用ツールを入れてから ens3 を DHCP クライアント化。
    default 経路は DHCP の option routers 頼み（mgmt 側に default を残さない
    —— 採点/SSH は同一セグメント 10.1.10.0/26 内で完結する）。"""
    return """#!/bin/bash
# PC01 (利用者端末) 初期化 — 生成: gen_dnsdhcp_build.py
set -e
export DEBIAN_FRONTEND=noninteractive
log() { echo "[$(date -Is)] $*"; }

log "採点用ツール導入 (dnsutils) — この時点は mgmt 側 default 経路で internet 到達可"
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


# ---- solution（自己検品・解答開示用） ---------------------------------------

def srv_solve_sh(v):
    """模範解答（SRV01）。PC01 の ens3 MAC を引数に取る（予約用）。"""
    n, r, alias, lo = v["n"], v["r"], v["alias"], v["lo"]
    zone_fwd = f"""$TTL 3600
@       IN SOA srv01.{DOMAIN}. admin.{DOMAIN}. ( 2026070301 3600 600 86400 3600 )
@       IN NS  srv01.{DOMAIN}.
srv01   IN A   {SRV_IP}
rt01    IN A   {lo['RT01']}
rt02    IN A   {lo['RT02']}
pc01    IN A   192.168.{n}.{r}
{alias:<7} IN CNAME srv01
"""
    zone_rev = f"""$TTL 3600
@       IN SOA srv01.{DOMAIN}. admin.{DOMAIN}. ( 2026070301 3600 600 86400 3600 )
@       IN NS  srv01.{DOMAIN}.
{r}      IN PTR pc01.{DOMAIN}.
"""
    return f"""#!/bin/bash
# GEN-DNSDHCP 模範解答投入（自己検品用）
# usage: SRV01_solve.sh <PC01のens3 MAC (xx:xx:xx:xx:xx:xx)>
set -e
[ "$(id -u)" = 0 ] || exec sudo -n bash "$0" "$@"
MAC="${{1:?usage: SRV01_solve.sh <PC01 ens3 MAC>}}"

# --- BIND9: ゾーン宣言・ゾーンファイル・オプション ---
cat > /etc/bind/named.conf.local <<'EOF'
zone "{DOMAIN}" {{ type master; file "/etc/bind/db.{DOMAIN}"; }};
zone "{n}.168.192.in-addr.arpa" {{ type master; file "/etc/bind/db.192.168.{n}"; }};
EOF

cat > /etc/bind/db.{DOMAIN} <<'EOF'
{zone_fwd}EOF

cat > /etc/bind/db.192.168.{n} <<'EOF'
{zone_rev}EOF

cat > /etc/bind/named.conf.options <<'EOF'
acl internal {{ 127.0.0.0/8; 10.0.0.0/8; 192.168.0.0/16; }};
options {{
        directory "/var/cache/bind";
        recursion yes;
        allow-query {{ internal; }};
        allow-recursion {{ internal; }};
        forwarders {{ 8.8.8.8; 8.8.4.4; }};
        dnssec-validation no;
        listen-on {{ any; }};
        listen-on-v6 {{ any; }};
}};
EOF

named-checkconf
named-checkzone {DOMAIN} /etc/bind/db.{DOMAIN}
named-checkzone {n}.168.192.in-addr.arpa /etc/bind/db.192.168.{n}
systemctl restart named

# --- isc-dhcp-server: スコープ・オプション・PC01 予約 ---
cat > /etc/dhcp/dhcpd.conf <<EOF
default-lease-time 3600;
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

host pc01 {{
  hardware ethernet $MAC;
  fixed-address 192.168.{n}.{r};
}}
EOF
sed -i 's/^INTERFACESv4=.*/INTERFACESv4="ens3"/' /etc/default/isc-dhcp-server
systemctl restart isc-dhcp-server
systemctl is-active named isc-dhcp-server
echo SOLVED
"""


def solution_md(v):
    n, r, alias = v["n"], v["r"], v["alias"]
    return f"""# GEN-DNSDHCP 模範解答（採点者用）

## サーバ側（SRV01）
`SRV01_solve.sh <PC01のens3 MAC>` が全設定を投入する（内容がそのまま模範解答）。
要点:
- `/etc/bind/named.conf.local` … `{DOMAIN}`（正引き）と `{n}.168.192.in-addr.arpa`
  （逆引き）の zone 宣言
- `/etc/bind/db.{DOMAIN}` … SOA/NS + A(srv01, rt01, rt02, pc01) + CNAME({alias})
- `/etc/bind/db.192.168.{n}` … PTR {r} → pc01.{DOMAIN}.
- `/etc/bind/named.conf.options` … allow-query/allow-recursion を社内
  (10.0.0.0/8, 192.168.0.0/16, 127.0.0.0/8) に限定・forwarders 8.8.8.8
- `/etc/dhcp/dhcpd.conf` … 待受IFサブネットの空宣言 + 192.168.{n}.0/24 スコープ
  (range .{POOL[0]}-.{POOL[1]}, routers .1, dns {SRV_IP}, domain {DOMAIN})
  + host 宣言で PC01 を 192.168.{n}.{r} に固定
- `/etc/default/isc-dhcp-server` … INTERFACESv4="ens3"

## ネットワーク側（fix.json = fix_generated.yml で投入可）
- RT02 `interface Ethernet0/1` に `ip helper-address {SRV_IP}`
  （ユーザLANのブロードキャスト DHCP をユニキャストで SRV01 へリレー）
- RT01/RT02 に `ip name-server {SRV_IP}`（+`ip domain lookup`）

## 採点後レビュー観点
- helper-address を「LAN 側 IF（giaddr になる IF）」に付けたか。SRV01 側 IF や
  グローバルに付けても機能しない点が定番の落とし穴。
- dhcpd の「待受IFのサブネット宣言必須」に気づけたか（journalctl を読む力）。
- 予約 IP をレンジ外に置く設計（レンジ内予約は重複配布の温床）。
- CNAME 先を A で持つ srv01 に張ったか（CNAME→CNAME 連鎖や A 直書きは減点対象外だが
  台帳どおりが原則。intranet を A で書くと CNAME チェックは FAIL）。
- 補足: 外部名の解決は forwarders 経由（SRV01 は mgmt 側から internet 到達可）。
  PC01 から外部への ping は NAT が無いため通らない（名前解決だけは通る）。
"""


# ---- 出力 -------------------------------------------------------------------

def build(repo, seed):
    rnd = random.Random(seed)
    pid = f"GEN-DNSDHCP-{seed}"
    v = rand_values(rnd)
    n, r, alias, lo = v["n"], v["r"], v["alias"], v["lo"]
    res_ip = f"192.168.{n}.{r}"

    pdir = f"{repo}/problems/{pid}"
    os.makedirs(f"{pdir}/initial", exist_ok=True)
    os.makedirs(f"{pdir}/solution", exist_ok=True)

    # initial
    with open(f"{pdir}/initial/RT01.cfg.j2", "w", encoding="utf-8") as f:
        f.write(rt01_cfg(v))
    with open(f"{pdir}/initial/RT02.cfg.j2", "w", encoding="utf-8") as f:
        f.write(rt02_cfg(v))
    for node in (SRV, PC):
        with open(f"{pdir}/initial/{node}.cfg.j2", "w", encoding="utf-8") as f:
            f.write("# server ノードは baseline_server.cfg.j2 が全て描画（このスタブは連結対策の空ファイル）\n")
    with open(f"{pdir}/initial/{SRV}.sh.j2", "w", encoding="utf-8") as f:
        f.write(srv_init_sh(v))
    with open(f"{pdir}/initial/{PC}.sh.j2", "w", encoding="utf-8") as f:
        f.write(pc_init_sh())

    # problem.yml
    pmeta = {
        "id": pid,
        "title": f"社内DNS(BIND9)構築＋DHCPリレー (seed={seed})",
        "exam": "ENCOR",
        "topics": ["dns", "bind9", "dhcp", "dhcp-relay", "linux", "server", "generated"],
        "difficulty": 3,
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
    with open(f"{pdir}/problem.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_dnsdhcp_build.py) seed={seed}\n")
        yaml.safe_dump(pmeta, f, allow_unicode=True, sort_keys=False, width=4096)

    # grading.yml（全て挙動ベース。config の grep はしない）
    checks = [
        # --- SRV01: DNS 構築 (41) ---
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
        # 行アンカーregex: 末尾ドット欠落の二重ドメイン(srv01.<d>.<d>.)を
        # contains だと誤 PASS するため(GEN-DNSDHCP-101 で判明した盲点)
        {"name": f"SRV01: CNAME {alias}.{DOMAIN} → srv01", "node": SRV, "exec": "shell",
         "command": f"dig +short @127.0.0.1 {alias}.{DOMAIN} CNAME",
         "raw": [{"regex": r"(^|\n)srv01\." + DOMAIN.replace(".", r"\.") + r"\.(\n|$)"}],
         "points": 7},
        {"name": f"SRV01: 逆引き {res_ip} → pc01", "node": SRV, "exec": "shell",
         "command": f"dig +short @127.0.0.1 -x {res_ip}",
         "raw": [{"contains": f"pc01.{DOMAIN}"}], "points": 8},
        {"name": "SRV01: isc-dhcp-server が稼働", "node": SRV, "exec": "shell",
         "command": "systemctl is-active isc-dhcp-server",
         "raw": [{"regex": "^active"}], "points": 5},
        # --- PC01: DHCP リレー越しの利用者体験 (34) ---
        {"name": f"PC01: DHCP で予約 IP {res_ip} を取得", "node": PC, "exec": "shell",
         "command": "ip -4 addr show ens3",
         "raw": [{"contains": f"{res_ip}/24"}], "points": 13},
        {"name": "PC01: DHCP 配布の DNS が SRV01", "node": PC, "exec": "shell",
         "command": "resolvectl dns ens3",
         "raw": [{"contains": SRV_IP}], "points": 5},
        {"name": f"PC01: DHCP 配布の検索ドメインが {DOMAIN}", "node": PC, "exec": "shell",
         "command": "resolvectl domain ens3",
         "raw": [{"contains": DOMAIN}], "points": 4},
        {"name": f"PC01: {alias}.{DOMAIN} を名前解決", "node": PC, "exec": "shell",
         "command": f"dig +short {alias}.{DOMAIN}",
         "raw": [{"contains": SRV_IP}], "points": 7},
        {"name": f"PC01: {alias}.{DOMAIN} へ ping", "node": PC, "exec": "shell",
         "command": f"ping -c 2 -W 1 {alias}.{DOMAIN}",
         "raw": [{"regex": " 0% packet loss"}], "points": 5},
        # --- ルータ: リレー実効値と DNS クライアント (25) ---
        # ★名前 ping は IOS の DNS キャッシュ(TTL 長いと1週間)でも通ってしまう
        #   (GEN-DNSDHCP-101 実機で name-server 消失をキャッシュがマスクした実例)。
        #   → show hosts summary の実効ネームサーバも併せて確認する。
        {"name": "RT02: ユーザLAN IF に DHCP リレー実効", "node": "RT02",
         "command": "show ip interface Ethernet0/1",
         "raw": [{"regex": "Helper address"}, {"contains": SRV_IP}], "points": 8},
        {"name": "RT01: 実効ネームサーバが SRV01", "node": "RT01",
         "command": "show hosts summary",
         "raw": [{"regex": f"Name servers are.*{SRV_IP.replace('.', chr(92) + '.')}"}],
         "points": 3},
        {"name": "RT02: 実効ネームサーバが SRV01", "node": "RT02",
         "command": "show hosts summary",
         "raw": [{"regex": f"Name servers are.*{SRV_IP.replace('.', chr(92) + '.')}"}],
         "points": 3},
        {"name": f"RT01: 名前で ping (srv01.{DOMAIN})", "node": "RT01",
         "command": f"ping srv01.{DOMAIN}",
         "raw": [{"contains": "!!!!"}], "points": 5},
        {"name": f"RT02: 名前で ping (pc01.{DOMAIN})", "node": "RT02",
         "command": f"ping pc01.{DOMAIN}",
         "raw": [{"contains": "!!!!"}], "points": 6},
    ]
    assert sum(c["points"] for c in checks) == 100
    grading = {"problem": pid, "total_points": 100,
               "defaults": {"genie_os": "iosxe"}, "checks": checks}
    with open(f"{pdir}/grading.yml", "w", encoding="utf-8") as f:
        f.write(f"# 自動生成 (gen_dnsdhcp_build.py) seed={seed}\n")
        yaml.safe_dump(grading, f, allow_unicode=True, sort_keys=False, width=4096)

    # solution
    with open(f"{pdir}/solution/fix.json", "w", encoding="utf-8") as f:
        json.dump({"fixes": [
            {"node": "RT02", "parents": ["interface Ethernet0/1"],
             "lines": [f"ip helper-address {SRV_IP}"]},
            {"node": "RT01", "lines": ["ip domain lookup", f"ip name-server {SRV_IP}"]},
            {"node": "RT02", "lines": ["ip domain lookup", f"ip name-server {SRV_IP}"]},
        ]}, f, ensure_ascii=False, indent=2)
    with open(f"{pdir}/solution/SRV01_solve.sh", "w", encoding="utf-8") as f:
        f.write(srv_solve_sh(v))
    os.chmod(f"{pdir}/solution/SRV01_solve.sh", 0o755)
    with open(f"{pdir}/solution/solution.md", "w", encoding="utf-8") as f:
        f.write(solution_md(v))

    # task.md（サーバ操作=詳しめガイド / NW=控えめ、のハイブリッド）
    task = f"""# 問題 {pid} : 社内DNS(BIND9)構築＋DHCPリレー（難易度3）

## シナリオ
新オフィスのユーザセグメント **192.168.{n}.0/24** を開設します。サーバセグメントの
**SRV01 (Ubuntu 24.04)** を社内 DNS/DHCP サーバとして構築し、ユーザ端末 **PC01** が
「電源を入れれば IP が付き、名前でイントラサーバに届く」状態に仕上げてください。

```
 SRV01 ────── RT01 ────── RT02 ────── PC01
(DNS/DHCP)                          (利用者端末)
 10.99.0.0/30   10.1.12.0/30   192.168.{n}.0/24 (GW=.1)
```

## 構成（初期状態で投入済み・変更不可）
- ルーティング(OSPF)・各 IF の IP は設定済み（RT02 E0/1 = 192.168.{n}.1 がユーザLANのGW）
- SRV01: ens3 = `{SRV_IP}/30`。**bind9 / isc-dhcp-server / dnsutils 導入済み（未設定）**
- PC01: ens3 は DHCP クライアント設定済み（サーバ側が正しく動けば自動でリースを取る）

## 要件
### A. 社内 DNS（SRV01 / BIND9）
台帳のとおり `{DOMAIN}` ゾーン（正引き）と `192.168.{n}.0/24` の逆引きゾーンを提供する:

| 名前 | 種別 | 値 |
|------|------|----|
| srv01.{DOMAIN} | A | {SRV_IP} |
| rt01.{DOMAIN} | A | {lo['RT01']} |
| rt02.{DOMAIN} | A | {lo['RT02']} |
| pc01.{DOMAIN} | A | {res_ip} |
| **{alias}.{DOMAIN}** | **CNAME** | srv01.{DOMAIN} |
| {res_ip} | PTR | pc01.{DOMAIN} |

- 問い合わせ応答・再帰は **社内 (10.0.0.0/8, 192.168.0.0/16) とローカルホストのみ**許可

### B. DHCP（SRV01 / isc-dhcp-server）
- 対象: ユーザLAN `192.168.{n}.0/24`、配布レンジ **.{POOL[0]}〜.{POOL[1]}**
- 配布オプション: GW=`192.168.{n}.1` / DNS=`{SRV_IP}` / ドメイン名=`{DOMAIN}`
- **PC01 は予約（固定割当）**: 常に `{res_ip}` を受け取ること（MAC は PC01 で確認）

### C. ネットワーク（RT01 / RT02）
- ユーザLAN に DHCP サーバは存在しない。**PC01 の DHCP 要求が SRV01 に届き、応答が
  返る**構成にすること（どの機器に何を入れるかは自分で判断）
- RT01・RT02 自身も SRV01 で名前解決できること（例: `ping srv01.{DOMAIN}` が成功）

## 到達目標（最終状態）
- PC01 が電源投入だけで `{res_ip}/24`・GW・DNS・検索ドメインを取得
- PC01 から `{alias}.{DOMAIN}` の名前解決と ping が成功
- SRV01 で正引き・逆引き・CNAME がすべて引ける
- RT01/RT02 から名前で ping が通る

## サーバ操作ガイド（NW 機器と勝手が違う所だけ。設定値は上の要件から組み立てること）
SRV01/PC01 へは SSH `SUZUKI / CCNP`（sudo 可）。基本サイクルは
**「ファイル編集 → 構文チェック → サービス再起動 → 状態確認」**。

### BIND9（設定は /etc/bind/ 配下）
- ゾーンの宣言（どのゾーンをどのファイルで持つか）: `/etc/bind/named.conf.local`
- 全体オプション（allow-query 等）: `/etc/bind/named.conf.options`
- ゾーンファイルは `/etc/bind/db.<名前>` を作る流儀。**$TTL・SOA・NS が無いと
  ゾーンはロードされない**（雛形として `/etc/bind/db.local` が使える）
- 逆引きゾーン名は `<第3オクテット>.<第2>.<第1>.in-addr.arpa` 形式
- 検証と反映:
  - `named-checkconf`（named.conf 構文） / `named-checkzone <ゾーン名> <ファイル>`
  - `sudo systemctl restart named` → `systemctl status named`
  - 動作確認 `dig @127.0.0.1 <名前>`、ログ `sudo journalctl -u named -e`
- ゾーンファイルを直したら SOA のシリアル値を増やすのが作法

### isc-dhcp-server
- 配布定義: `/etc/dhcp/dhcpd.conf`（既定ファイルにコメント形式の記述例が豊富。
  スコープは `subnet ... {{ }}`、固定割当は `host ... {{ }}` 宣言）
- 待受 IF の指定: `/etc/default/isc-dhcp-server` の `INTERFACESv4`
- ★ハマりどころ: **dhcpd は「待受 IF 自身のサブネット」の subnet 宣言が無いと起動を
  拒否する**（中身は空でよい）。起動失敗の理由は `sudo journalctl -u isc-dhcp-server -e`
- 反映: `sudo systemctl restart isc-dhcp-server`。リース状況: `/var/lib/dhcp/dhcpd.leases`

### PC01（利用者端末の視点で確認）
- MAC 確認: `ip link show ens3` / 取得 IP 確認: `ip -4 addr show ens3`
- DHCP で受けた DNS・ドメイン: `resolvectl dns ens3` / `resolvectl domain ens3`
- リース再取得を急ぐとき: `sudo networkctl reconfigure ens3`（放置でも数分内に再試行）

## 注意
- PC01 の ens2 (10.1.10.0/26) は管理・採点用。**ens2 側は変更しないこと**
- SRV01 のアドレス・経路は設定済み。SRV01 で触るのは**サービス設定のみ**
- 外部名（例: www.google.com）の解決可否は採点対象外

## アクセス・採点
SSH `SUZUKI / CCNP`（MGMT: RT01=10.1.10.11, RT02=.12, SRV01=.13, PC01=.14）。
DHCP リースの反映待ちがあるため attempts 多めで:
```
ansible-playbook playbooks/grade.yml -e problem={pid} -e max_attempts=20 \\
  --vault-password-file <(printf 'CCNP\\n')
```
"""
    with open(f"{pdir}/task.md", "w", encoding="utf-8") as f:
        f.write(task)

    print(f"generated {pid}: LAN=192.168.{n}.0/24 予約={res_ip} alias={alias} "
          f"lo={lo}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--seed", type=int, required=True)
    a = ap.parse_args()
    build(a.repo, a.seed)


if __name__ == "__main__":
    main()
