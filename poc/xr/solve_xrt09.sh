#!/bin/bash
# XRT-09 の模範解(learn.yml の solution と同じもの)を管理 IF の SSH で XR01/XR02 に入れる。PoC/E2E 用。
# usage: source poc/xr/env.sh; poc/xr/solve_xrt09.sh [m9t1 m9t2 m9t3 m9t4 …](既定= 全部)。管理 IP は _generated の mgmt_map から引く
#   誤答の確かめ用: m9t2-rr(XR02 だけ直す= as-override なし)・m9t2-as(as-override だけ= RR は直さない)・
#                   m9t3-noadd(additive なし= 999 が消える)・m9t3-rt900(900 を export route-target に足す= 10.99.2 にも付く)・
#                   m9t4-noadv(advertise-as-vpn なし)・m9t4-noallow(allow-imported-vpn なし)・undo-<課題>(その課題の設定を外す)
#   別解: m9t2-clean(RR クライアントを足し、ipv4 の AF と retain を消す)・m9t3-set(additive を使わず、10.99.1 には 900 と 999 を、他には 999 を set)
cd "$(dirname "$0")/../.."
M=topologies/_generated/${PID:-XRT-09}/mgmt_map.yml
ipof() { awk -v n="$1:" '$1==n{print $2}' "$M"; }
XR=$(ipof XR01) RR=$(ipof XR02)
steps=${*:-m9t1 m9t2 m9t3 m9t4}
run() { local h=$1; shift; .venv/bin/python poc/xr/xrsh.py "$h" "$@" 2>&1 | grep -iE "^%|fail|error|invalid|!!%" || true; }
X() { run "$XR" "$@"; }
Q() { run "$RR" "$@"; }
G2=GigabitEthernet0/0/0/2 G3=GigabitEthernet0/0/0/3 G4=GigabitEthernet0/0/0/4 G5=GigabitEthernet0/0/0/5
VRFS=('vrf CUST-A' 'address-family ipv4 unicast' 'import route-target' '65000:101' '65000:900' 'exit' 'export route-target' '65000:101' 'root'
  'vrf CUST-B' 'address-family ipv4 unicast' 'import route-target' '65000:102' '65000:900' 'exit' 'export route-target' '65000:102' 'root')
SVC_BASE=("interface $G4" 'vrf SVC' 'ipv4 address 172.16.91.1 255.255.255.0' 'root'
  'vrf SVC' 'address-family ipv4 unicast' 'import route-target' '65000:101' '65000:102' 'exit' 'export route-target' '65000:999' 'root'
  'router static' 'vrf SVC' 'address-family ipv4 unicast' '10.99.1.0/24 172.16.91.2' '10.99.2.0/24 172.16.91.2' 'root'
  'router bgp 65000' 'vrf SVC' 'rd 10.255.0.1:900' 'address-family ipv4 unicast' 'redistribute static' 'root')
INET_BASE=("interface $G5" 'ipv4 address 192.0.2.1 255.255.255.0' 'root'
  'route-policy TO-INTERNET' 'if destination in (198.51.100.0/25, 198.51.100.128/25) then' 'pass' 'endif' 'end-policy'
  'route-policy DEFAULT-ONLY' 'if destination in (0.0.0.0/0) then' 'pass' 'endif' 'end-policy'
  'route-policy CUST-A-PUBLIC' 'if destination in (198.51.100.0/25, 198.51.100.128/25) then' 'pass' 'endif' 'end-policy'
  'router bgp 65000' 'address-family ipv4 unicast' 'exit' 'neighbor 192.0.2.2' 'remote-as 64500' 'address-family ipv4 unicast'
  'route-policy PASS in' 'route-policy TO-INTERNET out' 'root')
for s in $steps; do case $s in
m9t1)
  X configure "${VRFS[@]}" "interface $G2" 'vrf CUST-A' 'ipv4 address 172.16.11.1 255.255.255.0' 'root' \
    "interface $G3" 'vrf CUST-B' 'ipv4 address 172.16.21.1 255.255.255.0' 'root' 'route-policy PASS' 'pass' 'end-policy' \
    'router bgp 65000' 'bgp router-id 10.255.0.1' 'address-family vpnv4 unicast' 'exit' \
    'neighbor 10.255.0.21' 'remote-as 65000' 'update-source Loopback0' 'address-family vpnv4 unicast' 'root' \
    'router bgp 65000' 'vrf CUST-A' 'rd 10.255.0.1:101' 'address-family ipv4 unicast' 'exit' 'neighbor 172.16.11.2' 'remote-as 65101' 'address-family ipv4 unicast' 'route-policy PASS in' 'route-policy PASS out' 'root' \
    'router bgp 65000' 'vrf CUST-B' 'rd 10.255.0.1:102' 'address-family ipv4 unicast' 'exit' 'neighbor 172.16.21.2' 'remote-as 65201' 'address-family ipv4 unicast' 'route-policy PASS in' 'route-policy PASS out' 'root' \
    commit end ;;
undo-m9t1)
  X configure 'no router bgp 65000' 'no route-policy PASS' "interface $G2" 'no ipv4 address' 'no vrf' 'root' \
    "interface $G3" 'no ipv4 address' 'no vrf' 'root' 'no vrf CUST-A' 'no vrf CUST-B' commit end ;;
m9t2|m9t2-rr)
  Q configure 'router bgp 65000' 'neighbor 10.255.0.1' 'address-family vpnv4 unicast' 'route-reflector-client' 'root' \
    'router bgp 65000' 'neighbor 10.255.0.12' 'address-family vpnv4 unicast' 'route-reflector-client' commit end
  [ "$s" = m9t2 ] && X configure 'router bgp 65000' 'vrf CUST-A' 'neighbor 172.16.11.2' 'address-family ipv4 unicast' 'as-override' commit end ;;
m9t2-as)
  X configure 'router bgp 65000' 'vrf CUST-A' 'neighbor 172.16.11.2' 'address-family ipv4 unicast' 'as-override' commit end ;;
m9t2-clean)
  Q configure 'router bgp 65000' 'address-family vpnv4 unicast' 'no retain route-target' 'root' \
    'router bgp 65000' 'neighbor 10.255.0.1' 'no address-family ipv4 unicast' 'address-family vpnv4 unicast' 'route-reflector-client' 'root' \
    'router bgp 65000' 'neighbor 10.255.0.12' 'no address-family ipv4 unicast' 'address-family vpnv4 unicast' 'route-reflector-client' 'root' \
    'router bgp 65000' 'no address-family ipv4 unicast' commit end
  X configure 'router bgp 65000' 'vrf CUST-A' 'neighbor 172.16.11.2' 'address-family ipv4 unicast' 'as-override' commit end ;;
undo-m9t2)
  Q configure 'router bgp 65000' 'neighbor 10.255.0.1' 'address-family vpnv4 unicast' 'no route-reflector-client' 'root' \
    'router bgp 65000' 'neighbor 10.255.0.12' 'address-family vpnv4 unicast' 'no route-reflector-client' commit end
  X configure 'router bgp 65000' 'vrf CUST-A' 'neighbor 172.16.11.2' 'address-family ipv4 unicast' 'no as-override' commit end ;;
m9t3)
  X configure 'route-policy SVC-EXPORT' 'if destination in (10.99.1.0/24) then' 'set extcommunity rt (65000:900) additive' 'endif' 'pass' 'end-policy' \
    "${SVC_BASE[@]}" 'vrf SVC' 'address-family ipv4 unicast' 'export route-policy SVC-EXPORT' commit end ;;
m9t3-noadd)
  X configure 'route-policy SVC-EXPORT' 'if destination in (10.99.1.0/24) then' 'set extcommunity rt (65000:900)' 'endif' 'pass' 'end-policy' \
    "${SVC_BASE[@]}" 'vrf SVC' 'address-family ipv4 unicast' 'export route-policy SVC-EXPORT' commit end ;;
m9t3-rt900)
  X configure "${SVC_BASE[@]}" 'vrf SVC' 'address-family ipv4 unicast' 'export route-target' '65000:900' commit end ;;
m9t3-set)
  X configure 'route-policy SVC-EXPORT' 'if destination in (10.99.1.0/24) then' 'set extcommunity rt (65000:900, 65000:999)' \
    'else' 'set extcommunity rt (65000:999)' 'endif' 'end-policy' \
    "${SVC_BASE[@]}" 'vrf SVC' 'address-family ipv4 unicast' 'export route-policy SVC-EXPORT' commit end ;;
undo-m9t3)
  X configure 'router bgp 65000' 'no vrf SVC' 'root' 'router static' 'no vrf SVC' 'root' "interface $G4" 'no ipv4 address' 'no vrf' 'root' \
    'no vrf SVC' 'no route-policy SVC-EXPORT' commit end ;;
m9t4)
  X configure "${INET_BASE[@]}" 'vrf CUST-A' 'address-family ipv4 unicast' \
    'import from default-vrf route-policy DEFAULT-ONLY advertise-as-vpn' 'export to default-vrf route-policy CUST-A-PUBLIC allow-imported-vpn' commit end ;;
m9t4-noadv)
  X configure "${INET_BASE[@]}" 'vrf CUST-A' 'address-family ipv4 unicast' \
    'import from default-vrf route-policy DEFAULT-ONLY' 'export to default-vrf route-policy CUST-A-PUBLIC allow-imported-vpn' commit end ;;
m9t4-noallow)
  X configure "${INET_BASE[@]}" 'vrf CUST-A' 'address-family ipv4 unicast' \
    'import from default-vrf route-policy DEFAULT-ONLY advertise-as-vpn' 'export to default-vrf route-policy CUST-A-PUBLIC' commit end ;;
undo-m9t4)
  X configure 'vrf CUST-A' 'address-family ipv4 unicast' 'no import from default-vrf route-policy DEFAULT-ONLY' 'no export to default-vrf route-policy CUST-A-PUBLIC' 'root' \
    'router bgp 65000' 'no neighbor 192.0.2.2' 'no address-family ipv4 unicast' 'root' "interface $G5" 'no ipv4 address' 'root' \
    'no route-policy TO-INTERNET' 'no route-policy DEFAULT-ONLY' 'no route-policy CUST-A-PUBLIC' commit end ;;
*) echo "unknown step $s"; exit 2 ;;
esac; done
