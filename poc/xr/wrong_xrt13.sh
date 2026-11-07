#!/bin/bash
# XRT-13 の誤答の判別(BL-261)。模範解を入れた状態から 1 つずつ壊し、その課題の確認で落ちる段を見てから戻す。
# usage: source poc/xr/env.sh; poc/xr/wrong_xrt13.sh <w1 … w7> …   出力= 壊した内容・確認の結果(e2e_xrt13.sh)・戻した後の確認
cd "$(dirname "$0")/../.."
M=topologies/_generated/XRT-13/mgmt_map.yml
ip() { awk -v n="$1:" '$1==n{print $2}' "$M"; }
E1=$(ip XE1) E2=$(ip XE2) E3=$(ip XE3) X1=$(ip XR01)
S() { local h=$1; shift; .venv/bin/python poc/xr/xrsh.py "$h" "$@" 2>&1 | grep -E "^%|Invalid|failed" ; }
E() { poc/xr/e2e_xrt13.sh "$@"; }
XNB=('router bgp 65000' 'vrf CUST-D' 'neighbor 172.20.4.1' 'address-family ipv4 unicast')
w1() { echo "== w1 S-1: XR01 の CE4 との eBGP からポリシーを外す"
  S "$X1" configure "${XNB[@]}" 'no route-policy PASS in' 'no route-policy PASS out' commit end; sleep 40; E svc1
  S "$X1" configure "${XNB[@]}" 'route-policy PASS in' 'route-policy PASS out' commit end; sleep 40; E svc1; }
w2() { echo "== w2 S-1: XE3 の VRF の静的経路を BGP に渡さない"
  S "$E3" 'configure terminal' 'router bgp 65000' 'address-family ipv4 vrf CUST-D' 'no redistribute static' 'end'; sleep 30; E svc1
  S "$E3" 'configure terminal' 'router bgp 65000' 'address-family ipv4 vrf CUST-D' 'redistribute static' 'end'; sleep 30; E svc1; }
w3() { echo "== w3 S-2: XR01 の AC の rewrite を外す"
  S "$X1" configure 'interface GigabitEthernet0/0/0/1.321 l2transport' 'no rewrite ingress tag pop 1 symmetric' commit end; sleep 30; E svc2
  .venv/bin/python poc/xr/xrsh.py "$X1" 'show l2vpn xconnect detail | include "state|Error|MTU"' | head -12
  S "$X1" configure 'interface GigabitEthernet0/0/0/1.321 l2transport' 'rewrite ingress tag pop 1 symmetric' commit end; sleep 30; E svc2; }
w4() { echo "== w4 S-3: ハブ アンド スポーク(XE1 と XE3 の間の疑似回線を消す)"
  S "$E1" 'configure terminal' 'l2vpn vfi context VPLS330' 'no member 10.255.0.43 encapsulation mpls' 'end'
  S "$E3" 'configure terminal' 'l2vpn vfi context VPLS330' 'no member 10.255.0.41 encapsulation mpls' 'end'; sleep 30; E svc3
  S "$E1" 'configure terminal' 'l2vpn vfi context VPLS330' 'member 10.255.0.43 encapsulation mpls' 'end'
  S "$E3" 'configure terminal' 'l2vpn vfi context VPLS330' 'member 10.255.0.41 encapsulation mpls' 'end'; sleep 30; E svc3; }
w5() { echo "== w5 S-4: RT は書いたが自動の RT を止めない(auto-route-target のまま= 65000:340 も付く)"
  for h in $E1 $E2 $E3; do S "$h" 'configure terminal' 'l2vpn evpn instance 340 vlan-based' 'auto-route-target' 'end'; done
  sleep 40; E svc4
  .venv/bin/python poc/xr/xrsh.py "$E1" 'show l2vpn evpn evi 340 detail | include RTs'
  for h in $E1 $E2 $E3; do S "$h" 'configure terminal' 'l2vpn evpn instance 340 vlan-based' 'no auto-route-target' 'end'; done
  sleep 40; E svc4; }
w6() { echo "== w6 S-4: replication-type ingress を外す(全 PE)"
  for h in $E1 $E2 $E3; do S "$h" 'configure terminal' 'l2vpn evpn' 'no replication-type ingress' 'end'; done; sleep 40; E svc4 svc5
  for h in $E1 $E2 $E3; do S "$h" 'configure terminal' 'l2vpn evpn' 'replication-type ingress' 'end'; done; sleep 40; E svc4 svc5; }
w7() { echo "== w7 S-5: XE2 の target と source を取り違える"
  S "$E2" 'configure terminal' 'l2vpn evpn instance 350 point-to-point' 'vpws context CE2-CE1' 'no service target 1 source 2' 'service target 2 source 1' 'end'; sleep 30; E svc5
  S "$E2" 'configure terminal' 'l2vpn evpn instance 350 point-to-point' 'vpws context CE2-CE1' 'no service target 2 source 1' 'service target 1 source 2' 'end'; sleep 30; E svc5; }
w8() { echo "== w8 S-1/S-4: XE3 が RR1 でなく P1(10.255.0.51)に iBGP を張る(P1 は BGP を持たない)"
  S "$E3" 'configure terminal' 'router bgp 65000' 'no neighbor 10.255.0.52' 'neighbor 10.255.0.51 remote-as 65000' 'neighbor 10.255.0.51 update-source Loopback0' \
    'address-family vpnv4' 'neighbor 10.255.0.51 activate' 'neighbor 10.255.0.51 send-community both' 'exit-address-family' \
    'address-family l2vpn evpn' 'neighbor 10.255.0.51 activate' 'neighbor 10.255.0.51 send-community both' 'end'; sleep 40; E svc1 svc4
  .venv/bin/python poc/xr/xrsh.py "$E3" 'show bgp vpnv4 unicast all summary | begin Neighbor'
  S "$E3" 'configure terminal' 'router bgp 65000' 'no neighbor 10.255.0.51' 'neighbor 10.255.0.52 remote-as 65000' 'neighbor 10.255.0.52 update-source Loopback0' \
    'address-family vpnv4' 'neighbor 10.255.0.52 activate' 'neighbor 10.255.0.52 send-community both' 'exit-address-family' \
    'address-family l2vpn evpn' 'neighbor 10.255.0.52 activate' 'neighbor 10.255.0.52 send-community both' 'end'; sleep 60; E svc1 svc4; }
for p in "$@"; do "$p"; done
