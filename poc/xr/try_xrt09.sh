#!/bin/bash
# XRT-09 の読み物の出力と「やってみる」の実測(全課題を解き終えた状態で流す。各段の最後で元に戻す)。
# usage: source poc/xr/env.sh; poc/xr/try_xrt09.sh <段…>  段= out(表示の採取)・policy・labelmode・filter・asov・additive・advertise
cd "$(dirname "$0")/../.."
M=topologies/_generated/${PID:-XRT-09}/mgmt_map.yml
ipof() { awk -v n="$1:" '$1==n{print $2}' "$M"; }
S() { local h; h=$(ipof "$1"); shift; .venv/bin/python poc/xr/xrsh.py "$h" "$@" 2>&1 | grep -v "^\s*$"; }
H() { echo; echo "######## $(date +%T) $*"; }

out() {
  H "out: 表示の採取"
  S XR01 'show bgp vpnv4 unicast summary' 'show bgp vpnv4 unicast rd 10.255.0.12:101 10.101.2.0/24' \
    'show bgp vrf CUST-A labels' 'show mpls forwarding' 'show bgp vrf CUST-A' 'show bgp vrf SVC 10.99.1.0/24' \
    'show bgp vrf CUST-A 0.0.0.0/0' 'show route vrf CUST-A 0.0.0.0/0' 'show bgp ipv4 unicast 198.51.100.128/25' \
    'show route 198.51.100.128/25' 'show cef 198.51.100.128/25' 'show bgp ipv4 unicast neighbors 192.0.2.2 advertised-routes' \
    'show bgp vpnv4 unicast neighbors 10.255.0.21 | include "refresh|Refresh|accepted|denied|Failed"'
  S XR02 'show bgp vpnv4 unicast summary' 'show bgp vpnv4 unicast neighbors 10.255.0.1 | include "Route-Reflector|accepted|address family"'
  S RT02 'show ip bgp vpnv4 vrf CUST-A 10.101.1.0' 'show ip route vrf CUST-A'
  S CEA1 'show ip bgp'
  S INET 'show ip bgp' 'traceroute 198.51.100.129 source Loopback10 numeric timeout 1 probe 1'
  S CEA2 'traceroute 203.0.113.10 source Loopback11 numeric timeout 1 probe 1'
}

policy() {
  H "policy: CEB1 の近隣から入出の方針を外す → 0! と No policy → 戻す"
  S XR01 configure 'router bgp 65000' 'vrf CUST-B' 'neighbor 172.16.21.2' 'address-family ipv4 unicast' 'no route-policy PASS in' 'no route-policy PASS out' commit end
  sleep 20
  S XR01 'show bgp vrf CUST-B summary' 'show bgp vrf CUST-B neighbors 172.16.21.2 | include "policy|accepted|denied|No policy"' 'show route vrf CUST-B bgp'
  S CEB1 'show ip bgp summary | begin Neighbor' 'show ip route bgp'
  S XR01 configure 'router bgp 65000' 'vrf CUST-B' 'neighbor 172.16.21.2' 'address-family ipv4 unicast' 'route-policy PASS in' 'route-policy PASS out' commit end
  sleep 30
  S XR01 'show bgp vrf CUST-B summary'
  S CEB1 'show ip route bgp'
}

labelmode() {
  H "labelmode: CUST-A を label mode per-vrf → 戻す"
  S XR01 configure 'router bgp 65000' 'vrf CUST-A' 'address-family ipv4 unicast' 'label mode per-vrf' commit end
  sleep 20
  S XR01 'show bgp vrf CUST-A labels' 'show mpls forwarding'
  S RT02 'show ip bgp vpnv4 vrf CUST-A labels'
  S CEA2 'ping 10.101.1.1 source Loopback10 repeat 5'
  S XR01 configure 'router bgp 65000' 'vrf CUST-A' 'address-family ipv4 unicast' 'no label mode' commit end
  sleep 20
  S XR01 'show bgp vrf CUST-A labels'
}

filter() {
  H "filter: CUST-B の取り込み RT から 65000:102 を外す → soft in で送り直させる → Failed RT match → 戻す → Route refresh"
  S XR01 'show bgp vpnv4 unicast neighbors 10.255.0.21 | include "Route refresh request|Failed RT"'
  S XR01 configure 'vrf CUST-B' 'address-family ipv4 unicast' 'import route-target' 'no 65000:102' commit end
  sleep 10
  S XR01 'show bgp vpnv4 unicast rd 10.255.0.12:102'
  S XR01 'clear bgp vpnv4 unicast 10.255.0.21 soft in'
  sleep 10
  S XR01 'show bgp vpnv4 unicast rd 10.255.0.12:102' 'show bgp vpnv4 unicast neighbors 10.255.0.21 | include "Route refresh request|Failed RT|denied"'
  S XR01 configure 'vrf CUST-B' 'address-family ipv4 unicast' 'import route-target' '65000:102' commit end
  sleep 5
  S XR01 'show bgp vrf CUST-B' 'show bgp vpnv4 unicast neighbors 10.255.0.21 | include "Route refresh request|Failed RT"'
  sleep 20
  S CEB1 'ping 10.102.2.1 source Loopback10 repeat 5'
}

asov() {
  H "asov: as-override を外す → 送らない → 戻す"
  S XR01 configure 'router bgp 65000' 'vrf CUST-A' 'neighbor 172.16.11.2' 'address-family ipv4 unicast' 'no as-override' commit end
  sleep 20
  S XR01 'show bgp vrf CUST-A 10.101.2.0/24' 'show bgp vrf CUST-A neighbors 172.16.11.2 advertised-routes'
  S CEA1 'show ip bgp' 'show ip bgp neighbors 172.16.11.1 | include Prefixes|denied'
  S XR01 configure 'router bgp 65000' 'vrf CUST-A' 'neighbor 172.16.11.2' 'address-family ipv4 unicast' 'as-override' commit end
  sleep 20
  S XR01 'show bgp vrf CUST-A neighbors 172.16.11.2 advertised-routes'
  S CEA1 'show ip bgp'
}

additive() {
  H "additive: SVC-EXPORT から additive を外す → 999 が消える → 戻す"
  S XR01 configure 'route-policy SVC-EXPORT' 'if destination in (10.99.1.0/24) then' 'set extcommunity rt (65000:900)' 'endif' 'pass' 'end-policy' commit end
  sleep 20
  S XR01 'show bgp vrf SVC 10.99.1.0/24 | include "Extended"'
  S RT02 'show ip bgp vpnv4 all 10.99.1.0'
  S CEA2 'ping 10.99.1.1 source Loopback10 repeat 5'
  S XR01 configure 'route-policy SVC-EXPORT' 'if destination in (10.99.1.0/24) then' 'set extcommunity rt (65000:900) additive' 'endif' 'pass' 'end-policy' commit end
  sleep 20
  S XR01 'show bgp vrf SVC 10.99.1.0/24 | include "Extended"'
}

advertise() {
  H "advertise: advertise-as-vpn を外す → RT02/CEA2 の既定経路が消える → 戻す"
  S XR01 configure 'vrf CUST-A' 'address-family ipv4 unicast' 'import from default-vrf route-policy DEFAULT-ONLY' commit end
  sleep 30
  S XR01 'show bgp vrf CUST-A 0.0.0.0/0 | include "Advertised|Not advertised|172.16|10.255"'
  S RT02 'show ip route vrf CUST-A 0.0.0.0'
  S CEA1 'show ip route 0.0.0.0'
  S CEA2 'show ip route 0.0.0.0' 'ping 203.0.113.10 source Loopback11 repeat 5'
  S XR01 configure 'vrf CUST-A' 'address-family ipv4 unicast' 'import from default-vrf route-policy DEFAULT-ONLY advertise-as-vpn' commit end
  sleep 60
  S CEA2 'show ip route 0.0.0.0' 'ping 203.0.113.10 source Loopback11 repeat 5'
}

for p in "$@"; do "$p"; done
