#!/bin/bash
# BL-246 M11 追補(XRT-12・Catalyst 8000V)の実測。設計= design §25.3。usage: source poc/xr/env.sh; poc/xr/xrt12_poc.sh <phase…>
# 出力は標準出力(呼び出し側で poc/xr/expM11b-<phase>.log へ)。
cd "$(dirname "$0")/../.."
PID=${PID:-XRT-12}
M=topologies/_generated/$PID/mgmt_map.yml
ip() { awk -v n="$1:" '$1==n{print $2}' "$M"; }
E1=$(ip XE1) E2=$(ip XE2) E3=$(ip XE3) P1=$(ip P1) C1=$(ip CE1) C2=$(ip CE2) C3=$(ip CE3) SW=$(ip SW1)
S() { local h=$1; shift; .venv/bin/python poc/xr/xrsh.py "$h" "$@" 2>&1 | grep -v '^\s*$'; }
H() { echo; echo "######## $(date +%T) $*"; }
PING210() {
  S "$C1" 'ping 172.31.210.2 repeat 5' 'ping 172.31.210.3 repeat 5' | grep -E 'Success|^ping'
  S "$C2" 'ping 172.31.210.3 repeat 5' | grep -E 'Success|^ping'
}

v1() {
  H "v1: 前任者の VPLS 210 のまま(XE1・XE3 は XE2 だけ・XE3 の EFP に rewrite なし)"
  PING210
  for h in $E1 $E2 $E3; do S "$h" 'show l2vpn vfi name VPLS210' 'show l2vpn atom vc' 'show bridge-domain 210' 'show ethernet service instance id 210 interface GigabitEthernet2 detail'; done
}
v2() {
  H "v2: XE3 の EFP 210 に rewrite を足す → 拠点 2⇔3 は通り、1⇔3 は通らないはず(スプリット ホライズン)"
  S "$E3" 'configure terminal' 'interface GigabitEthernet2' 'service instance 210 ethernet' 'rewrite ingress tag pop 1 symmetric' 'end'
  sleep 10
  PING210
  S "$E2" 'show bridge-domain 210'
  S "$E1" 'show bridge-domain 210'
}
v3() {
  H "v3: XE1⇔XE3 の member を足す(フルメッシュ)→ 全部通るはず"
  S "$E1" 'configure terminal' 'l2vpn vfi context VPLS210' 'member 10.255.0.43 encapsulation mpls' 'end'
  S "$E3" 'configure terminal' 'l2vpn vfi context VPLS210' 'member 10.255.0.41 encapsulation mpls' 'end'
  sleep 20
  PING210
  S "$E1" 'show l2vpn vfi name VPLS210' 'show bridge-domain 210' 'show l2vpn atom vc vcid 210 detail'
}
v4() {
  H "v4: (候補 B) XE3 の VPN ID を 211 にした時の症状 → 戻す"
  S "$E3" 'configure terminal' 'l2vpn vfi context VPLS210' 'vpn id 211' 'end' 'show running-config | section vfi'
  sleep 20
  PING210
  S "$E3" 'show l2vpn vfi name VPLS210' 'show l2vpn atom vc'
  S "$E2" 'show l2vpn atom vc' 'show l2vpn atom vc vcid 210 detail | include Peer|state|Status|status|error|Last'
  S "$E3" 'configure terminal' 'l2vpn vfi context VPLS210' 'vpn id 210' 'end' 'show running-config | section vfi'
  sleep 20
  PING210
}
v5() {
  H "v5: 分割ホライズンの裏どり= 前任者の形(XE1・XE3 は XE2 だけ)に戻し、XE2 の BD の MAC を見る"
  S "$E1" 'configure terminal' 'l2vpn vfi context VPLS210' 'no member 10.255.0.43 encapsulation mpls' 'end'
  S "$E3" 'configure terminal' 'l2vpn vfi context VPLS210' 'no member 10.255.0.41 encapsulation mpls' 'end'
  S "$C1" 'clear arp-cache' 'ping 172.31.210.3 repeat 5' | grep -E 'Success|^ping'
  S "$E2" 'show bridge-domain 210' 'show l2vpn vfi name VPLS210 detail'
}

PING200() {
  S "$C1" 'ping 172.31.200.2 repeat 5' 'ping 172.31.200.3 repeat 5' | grep -E 'Success|^ping'
  S "$C2" 'ping 172.31.200.3 repeat 5' | grep -E 'Success|^ping'
}
XE() { echo "$E1:10.255.0.41 $E2:10.255.0.42 $E3:10.255.0.43"; }
e1() {
  H "e1: PE に BGP(RR= P1・l2vpn evpn)"
  for p in $(XE); do
    S "${p%%:*}" 'configure terminal' 'router bgp 65000' "bgp router-id ${p##*:}" 'bgp log-neighbor-changes' 'no bgp default ipv4-unicast' \
      'neighbor 10.255.0.51 remote-as 65000' 'neighbor 10.255.0.51 update-source Loopback0' \
      'address-family l2vpn evpn' 'neighbor 10.255.0.51 activate' 'neighbor 10.255.0.51 send-community both' 'end'
  done
  sleep 30
  S "$P1" 'show bgp l2vpn evpn summary'
}
e2() {
  H "e2: EVI 200(vlan-based)+BD 200。l2vpn evpn の全体設定(replication-type)は書かない。拠点 3 はタグなし"
  for h in $E1 $E2; do
    S "$h" 'configure terminal' 'l2vpn evpn instance 200 vlan-based' 'exit' \
      'interface GigabitEthernet2' 'service instance 200 ethernet' 'encapsulation dot1q 200' 'rewrite ingress tag pop 1 symmetric' 'exit' 'exit' \
      'bridge-domain 200' 'member GigabitEthernet2 service-instance 200' 'member evpn-instance 200' 'end'
  done
  S "$E3" 'configure terminal' 'l2vpn evpn instance 200 vlan-based' 'exit' \
    'interface GigabitEthernet2' 'service instance 200 ethernet' 'encapsulation untagged' 'exit' 'exit' \
    'bridge-domain 200' 'member GigabitEthernet2 service-instance 200' 'member evpn-instance 200' 'end'
  sleep 40
  PING200
  S "$E1" 'show l2vpn evpn evi 200 detail' 'show bgp l2vpn evpn summary' 'show bgp l2vpn evpn' 'show l2vpn evpn mac' 'show l2vpn evpn imet'
}
e3() {
  H "e3: l2vpn evpn の全体に replication-type ingress と router-id Loopback0"
  for h in $E1 $E2 $E3; do
    S "$h" 'configure terminal' 'l2vpn evpn' 'replication-type ingress' 'router-id Loopback0' 'end'
  done
  sleep 40
  PING200
  S "$E1" 'show l2vpn evpn evi 200 detail' 'show bgp l2vpn evpn' 'show l2vpn evpn mac' 'show l2vpn evpn imet' 'show bridge-domain 200'
  S "$E3" 'show l2vpn evpn mac' 'show ethernet service instance id 200 interface GigabitEthernet2 detail'
  S "$P1" 'show bgp l2vpn evpn summary' 'show bgp l2vpn evpn'
}
e4() {
  H "e4: 拠点 3 を dot1q 200 で書いた誤り(CE3 はタグなし)"
  S "$E3" 'configure terminal' 'interface GigabitEthernet2' 'no service instance 200 ethernet' 'service instance 200 ethernet' 'encapsulation dot1q 200' 'rewrite ingress tag pop 1 symmetric' 'exit' 'exit' \
    'bridge-domain 200' 'member GigabitEthernet2 service-instance 200' 'end'
  sleep 15
  S "$C1" 'clear arp-cache' 'ping 172.31.200.3 repeat 5' | grep -E 'Success|^ping'
  S "$E3" 'configure terminal' 'interface GigabitEthernet2' 'no service instance 200 ethernet' 'service instance 200 ethernet' 'encapsulation untagged' 'exit' 'exit' \
    'bridge-domain 200' 'member GigabitEthernet2 service-instance 200' 'end'
  sleep 15
  S "$C1" 'ping 172.31.200.3 repeat 5' | grep -E 'Success|^ping'
}

SWS() { .venv/bin/python poc/xr/xrsh.py "$SW" "$@" 2>&1 | grep -v '^\s*$'; }
MHCFG() {  # $1= ホスト $2= lacp device-id の行(空なら書かない)
  S "$1" 'configure terminal' 'l2vpn evpn ethernet-segment 4' 'identifier type 0 00.00.00.00.00.00.00.04.01' 'redundancy all-active' 'exit' \
    'interface Port-channel1' 'no ip address' ${2:+"$2"} 'evpn ethernet-segment 4' \
    'service instance 200 ethernet' 'encapsulation dot1q 200' 'rewrite ingress tag pop 1 symmetric' 'exit' 'exit' \
    'interface GigabitEthernet3' 'no ip address' 'channel-group 1 mode active' 'exit' \
    'bridge-domain 200' 'member Port-channel1 service-instance 200' 'end'
}
m1() {
  H "m1: XE1・XE2 に ES 4(種類 0・all-active)と Port-channel1。lacp device-id は XE1 だけ(片側の書き忘れ)"
  MHCFG "$E1" 'lacp device-id 0000.0000.0004'
  MHCFG "$E2" ''
  sleep 45
  SWS 'show etherchannel summary' 'show lacp neighbor'
  S "$E1" 'show etherchannel summary' 'show lacp sys-id'
  S "$E2" 'show etherchannel summary' 'show lacp sys-id'
  SWS 'ping 172.31.200.3 repeat 5' | grep -E 'Success|^ping'
}
m2() {
  H "m2: XE2 にも lacp device-id → SW1 は 2 本を束ねるはず"
  S "$E2" 'configure terminal' 'interface Port-channel1' 'lacp device-id 0000.0000.0004' 'end'
  sleep 60
  SWS 'show etherchannel summary' 'show lacp neighbor'
  SWS 'ping 172.31.200.1 repeat 5' 'ping 172.31.200.2 repeat 5' 'ping 172.31.200.3 repeat 5' | grep -E 'Success|^ping'
  S "$E1" 'show l2vpn evpn ethernet-segment detail' 'show bgp l2vpn evpn route-type 1' 'show bgp l2vpn evpn route-type 4' 'show l2vpn evpn mac'
  S "$E2" 'show l2vpn evpn ethernet-segment detail'
  S "$E3" 'show l2vpn evpn mac' 'show bgp l2vpn evpn route-type 1' 'show l2vpn evpn evi 200 detail'
}
m3() {
  H "m3: XE1 の Gi3 を落とす → XE3 の MAC の次ホップ・SW1 の束(IOL-L2 はリンク断を受け取らない)"
  SWS 'ping 172.31.200.3 repeat 3' | grep -E 'Success'
  S "$E1" 'configure terminal' 'interface GigabitEthernet3' 'shutdown' 'end'
  for t in 3 10 20; do sleep $t; echo "== +$t"; S "$E3" 'show l2vpn evpn mac' | grep -A2 0401; SWS 'show etherchannel summary' | grep Po1; SWS 'ping 172.31.200.3 repeat 5 timeout 1' | grep Success; done
  S "$E1" 'configure terminal' 'interface GigabitEthernet3' 'no shutdown' 'end'
  sleep 40
  SWS 'show etherchannel summary' | grep Po1
  S "$E3" 'show l2vpn evpn mac' | grep -A2 0401
}

CFMSHOW() { for h in $E1 $E3; do S "$h" 'show ethernet cfm maintenance-points local' 'show ethernet cfm maintenance-points remote'; done; }
c1() {
  H "c1: CFM(PROV レベル 4・MA E130・EVC E130・MEP 1/3)。まず ethernet cfm global なし・CC の間隔は既定"
  for p in "$E1:1" "$E3:3"; do
    S "${p%%:*}" 'configure terminal' 'ethernet cfm domain PROV level 4' 'service E130 evc E130' 'continuity-check' 'exit' 'exit' \
      'interface GigabitEthernet2' 'service instance 130 ethernet E130' "cfm mep domain PROV mpid ${p##*:}" 'end' \
      'show running-config | section cfm'
  done
  sleep 30
  CFMSHOW
}
c2() {
  H "c2: ethernet cfm global を足す"
  for h in $E1 $E3; do S "$h" 'configure terminal' 'ethernet cfm global' 'end' 'show running-config | include ^ethernet cfm'; done
  sleep 40
  CFMSHOW
  S "$E1" 'show ethernet cfm domain PROV' 'show ethernet cfm maintenance-points remote detail' 'ping ethernet mpid 3 domain PROV service E130' 'traceroute ethernet mpid 3 domain PROV service E130'
}
c3() {
  H "c3: 既定の CC の間隔のまま、XE3⇔P1 に黙った故障(リンク条件 loss 100)→ XE1 の相手の MEP を 1 秒ごとに"
  .venv/bin/python topologies/login_probe.py $PID watch XE1 'show ethernet cfm maintenance-points remote' --samples 8 --interval 1 \
    --fail-link XE3:P1 --post-settle 15 2>&1 | grep -E "== |^3 |^1 |Total"
}
c4() {
  H "c4: CC の間隔を 1 秒にして同じ故障"
  for h in $E1 $E3; do S "$h" 'configure terminal' 'ethernet cfm domain PROV level 4' 'service E130 evc E130' 'continuity-check interval 1s' 'end'; done
  sleep 15
  .venv/bin/python topologies/login_probe.py $PID watch XE1 'show ethernet cfm maintenance-points remote' --samples 8 --interval 1 \
    --fail-link XE3:P1 --post-settle 15 2>&1 | grep -E "== |^3 |^1 |Total"
  .venv/bin/python topologies/login_probe.py $PID watch XE3 'show ethernet cfm maintenance-points remote' --samples 8 --interval 1 \
    --fail-link XE3:P1 --post-settle 15 2>&1 | grep -E "== |^3 |^1 |Total"
  S "$E1" 'show ethernet cfm errors' 'show logging | include CFM|ETHER_CFM|CC'
  S "$P1" 'show isis neighbors' 'show mpls ldp neighbor | include Peer|Up time'
}
c5() {
  H "c5: Y.1731 の往復の遅延(IP SLA 130)"
  S "$E1" 'configure terminal' 'ip sla 130' 'ethernet y1731 delay DMM domain PROV evc E130 mpid 3 cos 0 source mpid 1' '?' 'exit' \
    'ip sla schedule 130 start-time now life forever' 'end'
  sleep 40
  S "$E1" 'show ip sla summary' 'show ip sla statistics 130' 'show ip sla configuration 130'
}
for p in "$@"; do "$p"; done
