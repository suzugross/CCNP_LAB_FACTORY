#!/bin/bash
# XRT-14 の読み物の「やってみる」と出力の取り直し(解く側と同じ手順・模範解を入れた状態で)。usage: source poc/xr/env.sh; poc/xr/try_xrt14.sh <段…>
#   p1= 方策なしの EXP(d0 の try)・p2= ポリサの 3 色(d2 の try)・acl= ACL の hw の数(d4 の出力)・p3= ABF(d4 の try)・xe= IOS XE のポリサ(d2 の 3.4)
cd "$(dirname "$0")/../.."
M=topologies/_generated/XRT-14/mgmt_map.yml
ipof() { awk -v n="$1:" '$1==n{print $2}' "$M"; }
X1=$(ipof XR01) P1=$(ipof P1) E2=$(ipof PE2) C1=$(ipof CE1) C2=$(ipof CE2) IN=$(ipof INET)
S() { local h=$1; shift; .venv/bin/python poc/xr/xrsh.py "$h" "$@" 2>&1; }
H() { echo; echo "######## $(date +%T) $*"; }
p1() {
  H "p1: XR01 の CE1-IN を外して、AF21 が P1 のどのクラスに数えられるか"
  S "$X1" configure 'interface GigabitEthernet0/0/0/1' 'no service-policy input CE1-IN' commit end >/dev/null
  S "$P1" 'clear counters Ethernet0/0' '' >/dev/null
  S "$C1" 'ping 10.21.2.1 source Loopback21 repeat 10' | grep Success
  S "$P1" 'show policy-map interface Ethernet0/0 input'
  S "$X1" configure 'interface GigabitEthernet0/0/0/1' 'service-policy input CE1-IN' commit end >/dev/null
}
p2() {
  H "p2: ポリサの 3 色を送った側と受けた側で(すぐと 30 秒後)"
  S "$X1" 'clear qos counters interface GigabitEthernet0/0/0/1 input' >/dev/null; S "$C2" 'clear counters Ethernet0/0' '' >/dev/null
  S "$C1" 'ping 10.21.2.1 source Loopback21 repeat 1000 size 500 timeout 0' | grep Success
  echo "== すぐ"; S "$X1" 'show policy-map interface GigabitEthernet0/0/0/1 input' | sed -n '/Class DATA/,/Class class-default/p'
  sleep 30
  echo "== 30 秒後"; S "$X1" 'show policy-map interface GigabitEthernet0/0/0/1 input' | sed -n '/Class DATA/,/Class class-default/p'
  S "$C2" 'show policy-map interface Ethernet0/0 input'
}
acl() {
  H "acl: INET から基盤へ 5 発ずつ → ACL の行ごとの hw の数"
  S "$IN" 'ping 10.255.0.1 repeat 5 timeout 1' 'ping 10.0.2.2 repeat 5 timeout 1' 'ping 198.51.100.129 source Loopback0 repeat 5' | grep Success
  sleep 15; S "$X1" 'show access-lists ipv4 FROM-INTERNET hardware ingress location 0/0/CPU0' 'show access-lists ipv4 FROM-INTERNET'
}
p3() {
  H "p3: ABF= FROM-INTERNET に 45 行目(攻撃される宛てを CUST1 へ)を足す → Gi0/0/0/2 の出力の数"
  S "$X1" configure 'ipv4 access-list FROM-INTERNET' '45 permit ipv4 any host 198.51.100.130 nexthop1 ipv4 172.20.1.1' commit 'show configuration failed' end | grep -E "!!|%"
  S "$X1" 'show interfaces GigabitEthernet0/0/0/2 | include packets output'
  S "$IN" 'ping 198.51.100.130 source Loopback0 repeat 20 timeout 1' | grep Success
  sleep 15
  S "$X1" 'show interfaces GigabitEthernet0/0/0/2 | include packets output' 'show access-lists ipv4 FROM-INTERNET hardware ingress location 0/0/CPU0'
  S "$X1" configure 'ipv4 access-list FROM-INTERNET' 'no 45' commit end >/dev/null
}
xe() {
  H "xe: IOS XE(PE2)の 2 速度 3 色の書き方が通るか(CUST2 側の入力に一時的に当てて外す)"
  S "$E2" 'configure terminal' 'policy-map POLICE-DATA' 'class DATA' 'police cir 256000 pir 512000' 'conform-action transmit' 'exceed-action set-dscp-transmit af22' 'violate-action drop' 'end' \
    'configure terminal' 'interface Ethernet0/2' 'service-policy input POLICE-DATA' 'end' 'show policy-map POLICE-DATA' 'show policy-map interface Ethernet0/2 input'
  S "$E2" 'configure terminal' 'interface Ethernet0/2' 'no service-policy input POLICE-DATA' 'exit' 'no policy-map POLICE-DATA' 'end'
}
for p in "$@"; do "$p"; done
