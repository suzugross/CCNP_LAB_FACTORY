#!/bin/bash
# XRT-16(M14 マルチキャスト)の模範解を段ごとに入れる(E2E 用)。usage: source poc/xr/env.sh; poc/xr/solve_xrt16.sh <段…>
#   段= t1〜t6(模範解)・w*(誤答の型。E2E で部分点を見る)・show(状態の一覧)
# 盤面= problems/XRT-16/problem.yml。★実行中のこのファイルを書き換えない(bash は読みながら実行する)。
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

t1() {
  H "t1: PIM-SM・静的 RP= P1 の Lo0 を 239.0.0.0/8 だけに(XR 4 台+PE4)"
  for h in $XRS; do
    XC "$h" 'ipv4 access-list RP-P1-GROUPS' '10 permit ipv4 239.0.0.0 0.255.255.255 any' 'exit' \
      'multicast-routing' 'address-family ipv4' 'interface all enable' 'exit' 'exit' \
      'router pim' 'address-family ipv4' 'rp-address 10.255.0.11 RP-P1-GROUPS'
  done
  IC "$PE4" 'ip multicast-routing' 'access-list 10 permit 239.0.0.0 0.255.255.255' \
    'interface Ethernet0/0' 'ip pim sparse-mode' 'interface Ethernet0/1' 'ip pim sparse-mode' 'exit' \
    'ip pim rp-address 10.255.0.11 10'
}

t2() {
  H "t2: 239.17.0.0/16 を共有木に留める(受信者の側の PE2 と PE4・どのルータでも)"
  for h in $XRS; do
    XC "$h" 'ipv4 access-list UHD-GROUPS' '10 permit ipv4 239.17.0.0 0.0.255.255 any' 'exit' \
      'router pim' 'address-family ipv4' 'spt-threshold infinity group-list UHD-GROUPS'
  done
  IC "$PE4" 'access-list 17 permit 239.17.0.0 0.0.255.255' 'ip pim spt-threshold infinity group-list 17'
}

t3() {
  H "t3: SSM= 232/8 と 239.232/16(全ルータ)・PE4 の LAN 側を IGMPv3"
  for h in $XRS; do
    XC "$h" 'ipv4 access-list SSM-GROUPS' '10 permit ipv4 232.0.0.0 0.255.255.255 any' '20 permit ipv4 239.232.0.0 0.0.255.255 any' 'exit' \
      'router pim' 'address-family ipv4' 'ssm range SSM-GROUPS'
  done
  IC "$PE4" 'access-list 32 permit 232.0.0.0 0.255.255.255' 'access-list 32 permit 239.232.0.0 0.0.255.255' \
    'ip pim ssm range 32' 'interface Ethernet0/1' 'ip igmp version 3'
}

t4() {
  H "t4: BIDIR= 239.48.0.0/16・RP= PE3 の Lo0(全ルータ)"
  for h in $XRS; do
    XC "$h" 'ipv4 access-list CONF-GROUPS' '10 permit ipv4 239.48.0.0 0.0.255.255 any' 'exit' \
      'router pim' 'address-family ipv4' 'rp-address 10.255.0.3 CONF-GROUPS bidir'
  done
  # ★IOS は静的 RP の ACL が重なると 239.48 を ACL 10(P1・SM)の方に当てた(2026-11-18 実測)→ ACL 10 から 239.48 を外す
  IC "$PE4" 'ip pim bidir-enable' 'access-list 48 permit 239.48.0.0 0.0.255.255' 'ip pim rp-address 10.255.0.3 48 bidir' \
    'ip access-list standard 10' '5 deny 239.48.0.0 0.0.255.255'
}

t5() {
  H "t5: BSR= 239.16.0.0/15 の候補 RP は P1(10)・PE3(20)・PE4(200)・候補 BSR は PE1(100)と P1(既定)"
  XC "$P1" 'ipv4 access-list TV-GROUPS' '10 permit ipv4 239.16.0.0 0.1.255.255 any' 'exit' \
    'router pim' 'address-family ipv4' 'bsr candidate-rp 10.255.0.11 group-list TV-GROUPS priority 10 interval 30' \
    'bsr candidate-bsr 10.255.0.11 hash-mask-len 30'
  XC "$PE3" 'ipv4 access-list TV-GROUPS' '10 permit ipv4 239.16.0.0 0.1.255.255 any' 'exit' \
    'router pim' 'address-family ipv4' 'bsr candidate-rp 10.255.0.3 group-list TV-GROUPS priority 20 interval 30'
  XC "$PE1" 'router pim' 'address-family ipv4' 'bsr candidate-bsr 10.255.0.1 hash-mask-len 30 priority 100'
  IC "$PE4" 'access-list 16 permit 239.16.0.0 0.1.255.255' 'interface Loopback0' 'ip pim sparse-mode' 'exit' \
    'ip pim rp-candidate Loopback0 group-list 16 priority 200'
}

t6() {
  H "t6: IPv6 の TS= P1 の accept-register の一覧で見出しの permit を deny より先に・PE4 の RP を P1 に"
  XC "$P1" 'ipv6 access-list HEADEND-SOURCES' 'no 20' '5 permit ipv6 2001:db8:100:1::/64 any'
  IC "$PE4" 'no ipv6 pim rp-address 2001:DB8:255::3' 'ipv6 pim rp-address 2001:DB8:255::11'
}

show() {
  H "show: 状態の一覧"
  for h in $XRS; do echo "==== $h"; S "$h" 'show pim interface' 'show pim group-map' 'show pim rp mapping' 'show pim bsr election' 'show igmp interface brief'; done
  S "$PE4" 'show ip pim interface' 'show ip pim rp mapping' 'show ip pim bsr-router' 'show ip igmp interface Ethernet0/1'
}

# ---- 誤答の型(模範解が全部入った状態から 1 か所だけ崩す → その課題の確認 → 戻す)。e2e_wrong_xrt16.sh が呼ぶ ----
w1() { H "w1: M14-1 RP の一覧なし(全グループを P1 に)"
  for h in $XRS; do XC "$h" 'router pim' 'address-family ipv4' 'no rp-address 10.255.0.11 RP-P1-GROUPS' 'rp-address 10.255.0.11'; done
  IC "$PE4" 'no ip pim rp-address 10.255.0.11 10' 'ip pim rp-address 10.255.0.11'; }
r1() { H "r1: 戻す"
  for h in $XRS; do XC "$h" 'router pim' 'address-family ipv4' 'no rp-address 10.255.0.11' 'rp-address 10.255.0.11 RP-P1-GROUPS'; done
  IC "$PE4" 'no ip pim rp-address 10.255.0.11' 'ip pim rp-address 10.255.0.11 10'; }
w2() { H "w2: M14-2 PE4 に spt-threshold なし(XR だけ)"; IC "$PE4" 'no ip pim spt-threshold infinity group-list 17'; }
r2() { H "r2: 戻す"; IC "$PE4" 'ip pim spt-threshold infinity group-list 17'; }
w3() { H "w3: M14-3 PE4 に SSM の範囲も IGMPv3 もなし(XR だけ)"; IC "$PE4" 'no ip pim ssm range 32' 'interface Ethernet0/1' 'no ip igmp version'; }
r3() { H "r3: 戻す"; IC "$PE4" 'ip pim ssm range 32' 'interface Ethernet0/1' 'ip igmp version 3'; }
w4() { H "w4: M14-4 PE4 の一覧 10 から 239.48 を外さない"; IC "$PE4" 'ip access-list standard 10' 'no 5'; }
r4() { H "r4: 戻す"; IC "$PE4" 'ip access-list standard 10' '5 deny 239.48.0.0 0.0.255.255'; }
w5() { H "w5: M14-5 PE4 の候補 RP を既定の priority のまま"; IC "$PE4" 'ip pim rp-candidate Loopback0 group-list 16'; sleep 90; }
r5() { H "r5: 戻す"; IC "$PE4" 'ip pim rp-candidate Loopback0 group-list 16 priority 200'; sleep 90; }
w6() { H "w6: M14-6 P1 だけ直し PE4 の RP は取り違えのまま"; IC "$PE4" 'no ipv6 pim rp-address 2001:DB8:255::11' 'ipv6 pim rp-address 2001:DB8:255::3'; }
r6() { H "r6: 戻す"; IC "$PE4" 'no ipv6 pim rp-address 2001:DB8:255::3' 'ipv6 pim rp-address 2001:DB8:255::11'; }

for p in "$@"; do "$p"; done
