#!/bin/bash
# M9 の読み物の書き直し(BL-261 ③)のための測り直し。XRT-09 を全課題を解き終えた状態(solve_xrt09.sh)で流す。各段の最後で元に戻す。
# usage: source poc/xr/env.sh; poc/xr/m9rw_poc.sh <段…>
#   段= out1(仕組みのページの出力)・cap(線の上のラベル)・overlap(2 つのお客さまで同じアドレス)・soo(site-of-origin)・
#       perce(label mode per-ce)・out3(共有サービスのページの出力)・cfg(設定例の元になる running-config)
cd "$(dirname "$0")/../.."
PID=${PID:-XRT-09}
M=topologies/_generated/$PID/mgmt_map.yml
ipof() { awk -v n="$1:" '$1==n{print $2}' "$M"; }
S() { local h; h=$(ipof "$1"); shift; .venv/bin/python poc/xr/xrsh.py "$h" "$@" 2>&1 | grep -v "^\s*$"; }
H() { echo; echo "######## $(date +%T) $*"; }
CAP() { .venv/bin/python poc/xr/cml_cap.py "$PID" "$@" 2>&1 | tail -1; }
DEC() { echo "---- $1"; tcpdump -r "$1" -nn -e -c "${2:-8}" 2>/dev/null | cut -c1-400; }
TR='numeric timeout 1 probe 1'

out1() {
  H "out1: 仕組みのページ(1 つのパケットを 1 ホップずつ・PE が覚えるもの・コアが知らないもの)"
  S CEA1 "traceroute 10.101.2.1 source Loopback10 $TR" "traceroute 10.102.2.1 source Loopback10 $TR"
  S CEA2 "traceroute 10.101.1.1 source Loopback10 $TR"
  S CEB1 "traceroute 10.102.2.1 source Loopback10 $TR"
  S XR01 'show vrf CUST-A detail' 'show bgp vpnv4 unicast' 'show bgp vrf CUST-A' 'show bgp vrf CUST-A labels' \
    'show route vrf CUST-A' 'show cef vrf CUST-A 10.101.2.0/24' 'show mpls forwarding' \
    'show bgp vpnv4 unicast rd 10.255.0.12:101 10.101.2.0/24' 'show route 10.101.2.0/24'
  S RT01 'show mpls forwarding-table' 'show ip route 10.101.2.1' 'show ip bgp summary' 'show ip route vrf *'
  S RT02 'show mpls forwarding-table' 'show ip bgp vpnv4 all labels' 'show ip bgp vpnv4 all' \
    'show ip route vrf CUST-A' 'show ip cef vrf CUST-A 10.101.1.0 detail'
  S XR02 'show bgp vpnv4 unicast' 'show route 10.101.1.0/24' 'show mpls forwarding'
}

cap() {
  H "cap: 線の上のラベル(CEA1→CEA2・CEB1→CEB2。行きと帰りが同じ線に乗る)"
  local d=poc/xr/pcap; mkdir -p $d
  for c in A B; do
    CAP XR01 RT01 start mpls; CAP RT01 RT02 start mpls; sleep 3
    if [ $c = A ]; then S CEA1 'ping 10.101.2.1 source Loopback10 repeat 3'
    else S CEB1 'ping 10.102.2.1 source Loopback10 repeat 3'; fi
    sleep 3; CAP XR01 RT01 stop $d/m9-$c-xr01rt01.pcap; CAP RT01 RT02 stop $d/m9-$c-rt01rt02.pcap
    DEC $d/m9-$c-xr01rt01.pcap; DEC $d/m9-$c-rt01rt02.pcap
  done
}

overlap() {
  H "overlap: 顧客 B のサイト 2 にも 10.101.2.0/24 を置く(顧客 A のサイト 2 と同じ)→ RD で別の経路のまま・VRF ごとに正しい方へ → 戻す"
  S CEB2 'configure terminal' 'interface Loopback11' 'ip address 10.101.2.1 255.255.255.0' 'exit' \
    'router bgp 65202' 'address-family ipv4' 'network 10.101.2.0 mask 255.255.255.0' end
  sleep 60
  S XR02 'show bgp vpnv4 unicast | include "Route Distinguisher|10.101.2.0"'
  S XR01 'show bgp vpnv4 unicast | include "Route Distinguisher|10.101.2.0"' \
    'show bgp vrf CUST-A 10.101.2.0/24' 'show bgp vrf CUST-B 10.101.2.0/24' 'show cef vrf CUST-A 10.101.2.0/24' 'show cef vrf CUST-B 10.101.2.0/24'
  S RT02 'show ip bgp vpnv4 all | include Route Distinguisher|10.101.2.0'
  S CEA1 "traceroute 10.101.2.1 source Loopback10 $TR"
  S CEB1 "traceroute 10.101.2.1 source Loopback10 $TR" 'ping 10.101.2.1 source Loopback10 repeat 5'
  S CEB2 'configure terminal' 'router bgp 65202' 'address-family ipv4' 'no network 10.101.2.0 mask 255.255.255.0' 'exit' 'exit' 'no interface Loopback11' end
  sleep 30
  S XR01 'show bgp vrf CUST-B 10.101.2.0/24'
}

soo() {
  H "soo: XR01 で CEA1 に site-of-origin を付ける → RT02 に SoO が届く。RT02 で CEA2 にも同じ値 → 同じサイトとみなして送らない → 戻す"
  S XR01 configure 'router bgp 65000' 'vrf CUST-A' 'neighbor 172.16.11.2' 'address-family ipv4 unicast' 'site-of-origin 65101:1' commit end
  sleep 30
  S RT02 'show ip bgp vpnv4 vrf CUST-A 10.101.1.0'
  S CEA2 'show ip bgp 10.101.1.0'
  S XR01 'show bgp vrf CUST-A 10.101.1.0/24'
  S RT02 'configure terminal' 'router bgp 65000' 'address-family ipv4 vrf CUST-A' 'neighbor 172.16.12.2 soo 65101:1' end
  sleep 45
  S RT02 'show ip bgp vpnv4 vrf CUST-A 10.101.1.0' 'show ip bgp vpnv4 vrf CUST-A neighbors 172.16.12.2 advertised-routes'
  S CEA2 'show ip bgp'
  S XR01 'show bgp vrf CUST-A 10.101.2.0/24' 'show bgp vrf CUST-A neighbors 172.16.11.2 advertised-routes'
  S CEA1 'show ip bgp'
  S RT02 'configure terminal' 'router bgp 65000' 'address-family ipv4 vrf CUST-A' 'no neighbor 172.16.12.2 soo 65101:1' end
  S XR01 configure 'router bgp 65000' 'vrf CUST-A' 'neighbor 172.16.11.2' 'address-family ipv4 unicast' 'no site-of-origin 65101:1' commit end
  sleep 60
  S CEA1 'show ip bgp'; S CEA2 'show ip bgp'
}

perce() {
  H "perce: CUST-A を label mode per-ce に → 戻す"
  S XR01 configure 'router bgp 65000' 'vrf CUST-A' 'address-family ipv4 unicast' 'label mode per-ce' commit end
  sleep 20
  S XR01 'show bgp vrf CUST-A labels' 'show mpls forwarding'
  S RT02 'show ip bgp vpnv4 vrf CUST-A labels'
  S CEA2 'ping 10.101.1.1 source Loopback10 repeat 5' 'ping 198.51.100.1 source Loopback11 repeat 5'
  S XR01 configure 'router bgp 65000' 'vrf CUST-A' 'address-family ipv4 unicast' 'no label mode' commit end
  sleep 20
  S XR01 'show bgp vrf CUST-A labels'
  H "perce-xe: IOS XE の書き方(RT02 の CUST-B を VRF ごとに → 戻す)"
  S RT02 'show ip bgp vpnv4 vrf CUST-B labels'
  S RT02 'configure terminal' 'mpls label mode vrf CUST-B protocol bgp-vpnv4 per-vrf' end
  sleep 20
  S RT02 'show ip bgp vpnv4 vrf CUST-B labels' 'show mpls forwarding-table vrf CUST-B'
  S CEB1 'ping 10.102.2.1 source Loopback10 repeat 5'
  S RT02 'configure terminal' 'no mpls label mode vrf CUST-B protocol bgp-vpnv4 per-vrf' end
  sleep 20
  S RT02 'show ip bgp vpnv4 vrf CUST-B labels'
}

out3() {
  H "out3: 共有サービスとインターネットのページ"
  S XR01 'show bgp vrf SVC' 'show route vrf SVC' 'show route vrf CUST-B' 'show bgp vrf SVC 10.99.1.0/24' 'show bgp vrf SVC 10.99.2.0/24' \
    'show bgp vrf CUST-A 10.99.1.0/24' 'show bgp ipv4 unicast' 'show route vrf CUST-A 0.0.0.0/0'
  S RT02 'show ip bgp vpnv4 all 10.99.1.0' 'show ip route vrf CUST-B'
  S CEA1 'ping 10.102.1.1 source Loopback10 repeat 3' 'ping 10.99.1.1 source Loopback10 repeat 3' 'ping 10.99.2.1 source Loopback10 repeat 3'
  S INET 'show ip bgp'
  S CEB1 'show ip route'
}

cfg() {
  H "cfg: 設定例の元(全課題を解き終えた状態)"
  S XR01 'show running-config vrf' 'show running-config interface GigabitEthernet0/0/0/2' 'show running-config interface GigabitEthernet0/0/0/3' \
    'show running-config interface GigabitEthernet0/0/0/4' 'show running-config interface GigabitEthernet0/0/0/5' \
    'show running-config route-policy' 'show running-config router static' 'show running-config router bgp'
  S XR02 'show running-config router bgp'
  S RT02 'show running-config | section ^vrf definition' 'show running-config | section ^router bgp' \
    'show running-config interface Ethernet0/2'
}

xevrf() {
  H "xevrf: IOS XE でアドレスの付いた IF を VRF に入れる(RT02 の使っていない Loopback99 で)→ 消す"
  S RT02 'configure terminal' 'interface Loopback99' 'ip address 10.250.0.1 255.255.255.255' 'vrf forwarding CUST-B' end
  S RT02 'show running-config interface Loopback99' 'show ip interface brief | include Loopback99'
  S RT02 'configure terminal' 'no interface Loopback99' end
}

for s in "$@"; do "$s"; done
