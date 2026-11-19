#!/bin/bash
# 読み物 章 F0(M14)の設定例と出力を、XRT-16 の盤面の上で読み物の値のまま測る(解く側と同じ機器・同じ手順)。
# 読み物の値(課題とは変えてある)= RP は P1 の Lo0 で全グループ(一覧なし)・SPT の止めは PE2 と PE4 で全グループ・SSM の例は 239.100.0.0/16・
#   BIDIR は P1 の Loopback1 10.255.1.11 で 239.2.0.0/16・BSR は P1 を候補 RP(既定の priority)・PE1 を候補 BSR・Auto-RP は P1 と PE1。
# usage: source poc/xr/env.sh; poc/xr/try_xrt16.sh <段…>   ★構築直後(lab.sh reset の後)から順に流す。記録= poc/xr/expM14-try-<段>.log
cd "$(dirname "$0")/../.."
PID=${PID:-XRT-16}
M=topologies/_generated/$PID/mgmt_map.yml
ip() { awk -v n="$1:" '$1==n{print $2}' "$M"; }
PE1=$(ip PE1) PE2=$(ip PE2) P1=$(ip P1) PE3=$(ip PE3) PE4=$(ip PE4) SRC=$(ip SRC1) RV2=$(ip RCV2) RV3=$(ip RCV3)
XRS="$PE1 $PE2 $P1 $PE3"
S() { local h=$1; shift; .venv/bin/python poc/xr/xrsh.py "$h" "$@" 2>&1; }
H() { echo; echo "######## $(date +%T) $*"; }
XC() { local h=$1; shift; S "$h" configure "$@" commit 'show configuration failed' end; }
IC() { local h=$1; shift; S "$h" 'configure terminal' "$@" end; }
name() { case $1 in $PE1) echo PE1;; $PE2) echo PE2;; $P1) echo P1;; $PE3) echo PE3;; $PE4) echo PE4;; esac; }
ping4() { echo "==== SRC1: ping $1"; S "$SRC" "ping $1 repeat ${2:-10} timeout 1" | grep -E "Reply|Sending" ; }

base() {
  H "base: 構築直後(IPv4 のマルチキャストなし)。router pim だけを P1 に入れても IF は有効にならない"
  S "$PE2" 'show pim interface' 'show igmp interface' 'show running-config multicast-routing'
  XC "$P1" 'router pim' 'address-family ipv4' 'rp-address 10.255.0.11'
  S "$P1" 'show pim interface' 'show running-config router pim'
}

enable() {
  H "enable: XR 4 台= multicast-routing の address-family ipv4 で interface all enable・RP は P1(全グループ)。PE4= ip multicast-routing・2 本に sparse-mode・RP"
  for h in $XRS; do XC "$h" 'multicast-routing' 'address-family ipv4' 'interface all enable' 'exit' 'exit' 'router pim' 'address-family ipv4' 'rp-address 10.255.0.11'; done
  IC "$PE4" 'ip multicast-routing' 'interface Ethernet0/0' 'ip pim sparse-mode' 'interface Ethernet0/1' 'ip pim sparse-mode' 'exit' 'ip pim rp-address 10.255.0.11'
  sleep 45
  S "$PE2" 'show running-config multicast-routing' 'show running-config router pim' 'show pim interface' 'show pim neighbor' \
    'show igmp interface GigabitEthernet0/0/0/3' 'show pim group-map'
  S "$P1" 'show pim group-map 239.1.1.1'
  H "enable2: 共用の LAN(ACCESS-3)の DR と querier"
  S "$PE3" 'show pim interface GigabitEthernet0/0/0/1 detail' 'show igmp interface GigabitEthernet0/0/0/1' 'show pim neighbor GigabitEthernet0/0/0/1'
  S "$PE4" 'show ip pim interface Ethernet0/1 detail' 'show ip igmp interface Ethernet0/1' 'show ip pim neighbor'
}

join() {
  H "join: RCV2・RCV3 が 239.1.1.1 に参加(IOS のホストの既定= IGMPv2)。送る前の状態= 共有ツリーだけ"
  IC "$RV2" 'interface Ethernet0/0' 'ip igmp join-group 239.1.1.1'
  IC "$RV3" 'interface Ethernet0/0' 'ip igmp join-group 239.1.1.1'
  sleep 15
  S "$PE2" 'show igmp groups 239.1.1.1 detail' 'show pim topology 239.1.1.1' 'show mrib route 239.1.1.1'
  S "$P1" 'show pim topology 239.1.1.1'
  S "$PE4" 'show ip igmp groups 239.1.1.1 detail' 'show ip mroute 239.1.1.1'
  S "$PE1" 'show pim topology 239.1.1.1'
}

send() {
  H "send: SRC1 から 239.1.1.1 へ 10 発 → 受けた数・送った後の状態(Register・最短パス ツリーへの切り替え)"
  ping4 239.1.1.1 10
  for h in $PE1 $P1 $PE2; do echo "==== $(name $h)"; S "$h" 'show pim topology 239.1.1.1' 'show mrib route 239.1.1.1'; done
  S "$P1" 'show mfib route 239.1.1.1 detail'
  S "$PE4" 'show ip mroute 239.1.1.1'
  S "$PE2" 'show pim rpf' 'show pim rpf 192.168.1.1' 'show pim rpf 10.255.0.11'
}

spt() {
  H "spt: PE2 と PE4 に spt-threshold infinity(全グループ)。新しいグループ 239.1.1.2 で共有ツリーに留まるか"
  XC "$PE2" 'router pim' 'address-family ipv4' 'spt-threshold infinity'
  IC "$PE4" 'ip pim spt-threshold infinity'
  IC "$RV2" 'interface Ethernet0/0' 'ip igmp join-group 239.1.1.2'
  IC "$RV3" 'interface Ethernet0/0' 'ip igmp join-group 239.1.1.2'
  sleep 15; ping4 239.1.1.2 3 > /dev/null; sleep 3; ping4 239.1.1.2 10
  S "$PE2" 'show pim topology 239.1.1.2' 'show mrib route 239.1.1.2'
  S "$P1" 'show pim topology 239.1.1.2' 'show mfib route 239.1.1.2 detail'
  S "$PE4" 'show ip mroute 239.1.1.2'
  H "spt2: 片付け(PE2 と PE4 の spt-threshold を外す)"
  XC "$PE2" 'router pim' 'address-family ipv4' 'no spt-threshold infinity'
  IC "$PE4" 'no ip pim spt-threshold infinity'
}

ssm() {
  H "ssm: 既定の SSM の範囲(232/8)。RCV2 を IGMPv3 にして (192.168.1.1, 232.1.1.1) に参加"
  S "$PE2" 'show pim group-map 232.1.1.1'
  IC "$RV2" 'interface Ethernet0/0' 'ip igmp version 3' 'ip igmp join-group 232.1.1.1 source 192.168.1.1'
  sleep 10
  S "$PE2" 'show igmp groups 232.1.1.1 detail' 'show pim topology 232.1.1.1'
  ping4 232.1.1.1 10
  S "$PE2" 'show pim topology 232.1.1.1'; S "$P1" 'show pim topology 232.1.1.1'; S "$PE1" 'show pim topology 232.1.1.1'
  H "ssm2: SSM の範囲を広げる例= 232/8 と 239.100.0.0/16(XR は router pim の下・PE4 は ip pim ssm range)"
  for h in $XRS; do XC "$h" 'ipv4 access-list SSM-RANGE' '10 permit ipv4 232.0.0.0 0.255.255.255 any' '20 permit ipv4 239.100.0.0 0.0.255.255 any' 'exit' \
    'router pim' 'address-family ipv4' 'ssm range SSM-RANGE'; done
  IC "$PE4" 'access-list 30 permit 232.0.0.0 0.255.255.255' 'access-list 30 permit 239.100.0.0 0.0.255.255' 'ip pim ssm range 30'
  S "$PE2" 'show pim group-map'
  S "$PE4" 'show ip igmp interface Ethernet0/1 | include version'
  IC "$RV2" 'interface Ethernet0/0' 'no ip igmp join-group 232.1.1.1 source 192.168.1.1' 'no ip igmp version'
}

bidir() {
  H "bidir: 239.2.0.0/16 を双方向に。RP= P1 の Loopback1 10.255.1.11(IS-IS に載せる)。PE4= bidir-enable と一覧 20"
  XC "$P1" 'interface Loopback1' 'ipv4 address 10.255.1.11 255.255.255.255' 'exit' 'router isis CORE' 'interface Loopback1' 'passive' 'address-family ipv4 unicast'
  for h in $XRS; do XC "$h" 'ipv4 access-list BIDIR-GROUPS' '10 permit ipv4 239.2.0.0 0.0.255.255 any' 'exit' \
    'router pim' 'address-family ipv4' 'rp-address 10.255.1.11 BIDIR-GROUPS bidir'; done
  IC "$PE4" 'ip pim bidir-enable' 'access-list 20 permit 239.2.0.0 0.0.255.255' 'ip pim rp-address 10.255.1.11 20 bidir'
  for h in $SRC $RV2 $RV3; do IC "$h" 'interface Ethernet0/0' 'ip igmp join-group 239.2.2.2'; done
  sleep 20
  S "$PE2" 'show pim group-map 239.2.2.2' 'show pim df winner' 'show pim topology 239.2.2.2'
  S "$PE3" 'show pim df winner'
  S "$PE4" 'show ip pim rp mapping' 'show ip pim interface df'
  echo "==== RCV3: ping 239.2.2.2"; S "$RV3" 'ping 239.2.2.2 repeat 10 timeout 1' | grep -E "Reply|Sending"
  ping4 239.2.2.2 10
  for h in $PE1 $P1 $PE2; do echo "==== $(name $h)"; S "$h" 'show pim topology 239.2.2.2' 'show mrib route 239.2.2.2'; done
  S "$PE4" 'show ip mroute 239.2.2.2'
  for h in $SRC $RV2 $RV3; do IC "$h" 'interface Ethernet0/0' 'no ip igmp join-group 239.2.2.2'; done
}

bsr() {
  H "bsr: 静的 RP 10.255.0.11 を外す(BIDIR の静的は残す)。P1 を候補 RP(priority を書かない)・PE1 を候補 BSR に"
  for h in $XRS; do XC "$h" 'router pim' 'address-family ipv4' 'no rp-address 10.255.0.11'; done
  IC "$PE4" 'no ip pim rp-address 10.255.0.11'
  XC "$P1" 'router pim' 'address-family ipv4' 'bsr candidate-rp 10.255.0.11'
  XC "$PE1" 'router pim' 'address-family ipv4' 'bsr candidate-bsr 10.255.0.1'
  sleep 75
  S "$P1" 'show running-config router pim' 'show pim bsr candidate-rp'
  S "$PE1" 'show running-config router pim' 'show pim bsr election'
  S "$PE2" 'show pim bsr election' 'show pim rp mapping' 'show pim group-map 239.1.1.1'
  S "$PE4" 'show ip pim bsr-router' 'show ip pim rp mapping'
  H "bsr2: PE3 も候補 RP(priority 50)→ 小さい方が勝つ"
  XC "$PE3" 'router pim' 'address-family ipv4' 'bsr candidate-rp 10.255.0.3 priority 50'
  sleep 75
  S "$PE2" 'show pim rp mapping' 'show pim group-map 239.1.1.1'
  S "$PE4" 'show ip pim rp mapping' 'show ip pim rp-hash 239.1.1.1'
}

autorp() {
  H "autorp: BSR を外す。P1 を Auto-RP の候補 RP・PE1 を mapping agent に(PE4 は何もしない)"
  XC "$PE3" 'router pim' 'address-family ipv4' 'no bsr candidate-rp 10.255.0.3'
  XC "$P1" 'router pim' 'address-family ipv4' 'no bsr candidate-rp 10.255.0.11' 'auto-rp candidate-rp Loopback0 scope 16 interval 30'
  XC "$PE1" 'router pim' 'address-family ipv4' 'no bsr candidate-bsr 10.255.0.1' 'auto-rp mapping-agent Loopback0 scope 16 interval 30'
  sleep 90
  S "$PE1" 'show auto-rp mapping-agent'
  S "$P1" 'show auto-rp candidate-rp'
  S "$PE2" 'show pim rp mapping' 'show pim group-map' 'show pim topology 224.0.1.40'
  S "$PE4" 'show ip pim rp mapping' 'show ip mroute 224.0.1.40'
}

v6() {
  H "v6: IPv6 の土台(静的 RP= P1)。PIMv6 の IF・隣接・MLD の既定・LAN の DR(リンクローカルの大きい方)"
  S "$PE2" 'show running-config multicast-routing' 'show pim ipv6 interface' 'show pim ipv6 neighbor' 'show mld interface GigabitEthernet0/0/0/3' 'show pim ipv6 group-map ff0e::1:1'
  S "$PE3" 'show pim ipv6 interface GigabitEthernet0/0/0/1' 'show mld interface GigabitEthernet0/0/0/1'
  S "$PE4" 'show ipv6 pim interface Ethernet0/1' 'show ipv6 mld interface Ethernet0/1'
}

for p in "$@"; do "$p"; done
