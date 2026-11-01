#!/bin/bash
# BL-246 M11 の補足 PoC= IOS XE の仮想ルータ(Catalyst 8000V 17.15)で E-LAN・EVPN のマルチホーム・CFM が動くか。盤面= problems/_POC-XRL2XE
#   XE1/XE2/XE3= Cat8000v の PE・P1= IOL・XR01= XRv9000 の PE・XR02= XRd(l2vpn evpn の RR)・CE1〜4= IOL・SW1= IOL-L2(XE1+XE2 に束で二重に収容)
# 記録= design §24。usage: source poc/xr/env.sh; poc/xr/l2xe_poc.sh <phase…>   出力は標準出力(呼び出し側で poc/xr/l2xe-<phase>.log へ)
cd "$(dirname "$0")/../.."
PID=${PID:-_POC-XRL2XE}
M=topologies/_generated/$PID/mgmt_map.yml
ip() { awk -v n="$1:" '$1==n{print $2}' "$M"; }
E1=$(ip XE1) E2=$(ip XE2) E3=$(ip XE3) P1=$(ip P1) X1=$(ip XR01) X2=$(ip XR02)
C1=$(ip CE1) C2=$(ip CE2) C3=$(ip CE3) C4=$(ip CE4) SW=$(ip SW1)
S() { local h=$1; shift; .venv/bin/python poc/xr/xrsh.py "$h" "$@" 2>&1; }
H() { echo; echo "######## $(date +%T) $*"; }
T() { .venv/bin/python poc/xr/tcpprobe.py "$@" 2>&1 | tail -2; }
XE() { echo "$E1:10.255.0.41 $E2:10.255.0.42 $E3:10.255.0.43"; }

a() {
  H "a-1: 版・ライセンスの段階・IS-IS・LDP(XE1〜3)と XR01"
  for h in $E1 $E2 $E3; do
    S "$h" 'show version | include Version|License|level|Technology' 'show license summary' 'show isis neighbors' 'show mpls ldp neighbor | include Peer|State' \
      'show platform hardware throughput level'
  done
  S "$X1" 'show version | include Version' 'show isis adjacency' 'show mpls ldp neighbor brief'
  S "$P1" 'show isis neighbors' 'show ip route isis | include /32'
}

rr() {
  H "rr: XR02(XRd)を l2vpn evpn の RR に・XE1〜3 と XR01 をクライアントに"
  S "$X2" configure 'router bgp 65000' 'bgp router-id 10.255.0.21' 'address-family l2vpn evpn' 'exit' \
    'neighbor-group PE' 'remote-as 65000' 'update-source Loopback0' 'address-family l2vpn evpn' 'route-reflector-client' 'exit' 'exit' \
    'neighbor 10.255.0.41' 'use neighbor-group PE' 'exit' 'neighbor 10.255.0.42' 'use neighbor-group PE' 'exit' \
    'neighbor 10.255.0.43' 'use neighbor-group PE' 'exit' 'neighbor 10.255.0.1' 'use neighbor-group PE' \
    'root' commit 'show configuration failed' end
  S "$X1" configure 'router bgp 65000' 'bgp router-id 10.255.0.1' 'address-family l2vpn evpn' 'exit' \
    'neighbor 10.255.0.21' 'remote-as 65000' 'update-source Loopback0' 'address-family l2vpn evpn' 'root' commit 'show configuration failed' end
  for p in $(XE); do
    S "${p%%:*}" 'configure terminal' 'router bgp 65000' "bgp router-id ${p##*:}" 'bgp log-neighbor-changes' 'no bgp default ipv4-unicast' \
      'neighbor 10.255.0.21 remote-as 65000' 'neighbor 10.255.0.21 update-source Loopback0' \
      'address-family l2vpn evpn' 'neighbor 10.255.0.21 activate' 'neighbor 10.255.0.21 send-community both' 'end'
  done
  sleep 30
  S "$X2" 'show bgp l2vpn evpn summary'
}

b() {
  H "b-1: EVPN の E-LAN(vlan-based・EVI 200・BD 200)を XE1〜3 に。AC= service instance 200(dot1q 200・pop 1)"
  for p in $(XE); do
    S "${p%%:*}" 'configure terminal' 'l2vpn evpn' 'replication-type ingress' 'router-id Loopback0' 'exit' \
      'l2vpn evpn instance 200 vlan-based' 'exit' \
      'interface GigabitEthernet2' 'service instance 200 ethernet' 'encapsulation dot1q 200' 'rewrite ingress tag pop 1 symmetric' 'exit' 'exit' \
      'bridge-domain 200' 'member GigabitEthernet2 service-instance 200' 'member evpn-instance 200' 'end' \
      'show running-config | section l2vpn|bridge-domain 200'
  done
  sleep 30
  S "$E1" 'show l2vpn evpn evi 200 detail' 'show bgp l2vpn evpn' 'show bridge-domain 200'
  H "b-2: CE1 ⇔ CE2・CE3(VLAN 200)"
  S "$C1" 'ping 192.168.200.2 repeat 5' 'ping 192.168.200.3 repeat 5'
  S "$C2" 'ping 192.168.200.3 repeat 5'
  T "$C1" 192.168.200.3
  S "$E1" 'show l2vpn evpn mac' 'show bridge-domain 200' 'show bgp l2vpn evpn route-type 2'
}

c() {
  H "c-1: VPLS(LDP・VFI・VPN ID 210・BD 210)を XE1〜3 の全メッシュで。AC= service instance 210"
  for p in "$E1:10.255.0.42:10.255.0.43" "$E2:10.255.0.41:10.255.0.43" "$E3:10.255.0.41:10.255.0.42"; do
    IFS=: read -r h n1 n2 <<<"$p"
    S "$h" 'configure terminal' 'l2vpn vfi context VPLS210' 'vpn id 210' "member $n1 encapsulation mpls" "member $n2 encapsulation mpls" 'exit' \
      'interface GigabitEthernet2' 'service instance 210 ethernet' 'encapsulation dot1q 210' 'rewrite ingress tag pop 1 symmetric' 'exit' 'exit' \
      'bridge-domain 210' 'member GigabitEthernet2 service-instance 210' 'member vfi VPLS210' 'end'
  done
  sleep 30
  S "$E1" 'show l2vpn vfi' 'show l2vpn atom vc' 'show bridge-domain 210'
  S "$C1" 'ping 192.168.210.2 repeat 5' 'ping 192.168.210.3 repeat 5'
  T "$C2" 192.168.210.3
  S "$E1" 'show bridge-domain 210 | include Gi|vfi|pseudowire|MAC|mac|aabb'
}

d() {
  H "d-1: XE1 ⇔ XR01 の LDP の疑似回線(VLAN 100・pw-id 100)"
  S "$E1" 'configure terminal' 'interface GigabitEthernet2' 'service instance 100 ethernet' 'encapsulation dot1q 100' 'rewrite ingress tag pop 1 symmetric' 'exit' 'exit' \
    'l2vpn xconnect context CE1-CE4' 'member GigabitEthernet2 service-instance 100' 'member 10.255.0.1 100 encapsulation mpls' 'end'
  S "$X1" configure 'interface GigabitEthernet0/0/0/1.100 l2transport' 'encapsulation dot1q 100' 'rewrite ingress tag pop 1 symmetric' 'root' \
    'l2vpn' 'xconnect group POC' 'p2p CE4-CE1' 'interface GigabitEthernet0/0/0/1.100' 'neighbor ipv4 10.255.0.41 pw-id 100' 'root' commit 'show configuration failed' end
  H "d-2: XE3 ⇔ XR01 の EVPN-VPWS(VLAN 110・EVI 110・XE3 source 3・XR01 source 1)"
  S "$E3" 'configure terminal' 'interface GigabitEthernet2' 'service instance 110 ethernet' 'encapsulation dot1q 110' 'rewrite ingress tag pop 1 symmetric' 'exit' 'exit' \
    'l2vpn evpn instance 110 point-to-point' 'vpws context CE3-CE4' 'service target 1 source 3' 'member GigabitEthernet2 service-instance 110' 'end'
  S "$X1" configure 'interface GigabitEthernet0/0/0/1.110 l2transport' 'encapsulation dot1q 110' 'rewrite ingress tag pop 1 symmetric' 'root' \
    'l2vpn' 'xconnect group POC' 'p2p CE4-CE3' 'interface GigabitEthernet0/0/0/1.110' 'neighbor evpn evi 110 target 3 source 1' 'root' commit 'show configuration failed' end
  sleep 30
  S "$X1" 'show l2vpn xconnect'
  S "$E1" 'show l2vpn atom vc'
  S "$E3" 'show l2vpn evpn vpws vc id 110 detail'
  S "$C4" 'ping 192.168.100.1 repeat 5' 'ping 192.168.110.3 repeat 5'
  T "$C4" 192.168.110.3
  S "$E3" 'show l2vpn evpn vpws vc id 110 detail | include packets|drops'
}

e0() {
  H "e0: マルチホームの書き方をヘルプで探る(XE1)"
  S "$E1" 'configure terminal' 'l2vpn evpn ethernet-segment 1' '?' 'exit' 'interface Port-channel1' '?' 'end' 'show running-config | section ethernet-segment|Port-channel'
}

e() {
  H "e-1: EVPN のマルチホーム(all-active・ES 1・種類 3 system-mac 0000.0000.0001)= SW1 の束を XE1 と XE2 の Port-channel1 で受ける。BD 200 に参加"
  for h in $E1 $E2; do
    S "$h" 'configure terminal' 'l2vpn evpn ethernet-segment 1' 'identifier type 3 system-mac 0000.0000.0001' 'redundancy all-active' 'exit' \
      'interface Port-channel1' 'no ip address' 'lacp device-id 0000.0000.0001' 'evpn ethernet-segment 1' \
      'service instance 200 ethernet' 'encapsulation dot1q 200' 'rewrite ingress tag pop 1 symmetric' 'exit' 'exit' \
      'interface GigabitEthernet3' 'no ip address' 'channel-group 1 mode active' 'exit' \
      'bridge-domain 200' 'member Port-channel1 service-instance 200' 'end' \
      'show running-config | section ethernet-segment|Port-channel1|GigabitEthernet3'
  done
  sleep 60
  S "$E1" 'show etherchannel summary' 'show lacp neighbor' 'show l2vpn evpn ethernet-segment detail' 'show bgp l2vpn evpn route-type 1' 'show bgp l2vpn evpn route-type 4'
  S "$E2" 'show etherchannel summary' 'show l2vpn evpn ethernet-segment detail'
  .venv/bin/python poc/xr/swsh.py "$SW" 'show etherchannel summary' 'show lacp neighbor' 'ping 192.168.200.1 repeat 5' 'ping 192.168.200.2 repeat 5' 'ping 192.168.200.3 repeat 5'
  S "$E3" 'show l2vpn evpn mac' 'show bgp l2vpn evpn route-type 1'
}

e2() {
  H "e2-1: XE1 の SW1 向き(Gi3)を落とす → SW1 から CE3 へ(XE2 経由で残るか)"
  .venv/bin/python poc/xr/swsh.py "$SW" 'ping 192.168.200.3 repeat 3'
  S "$E1" 'configure terminal' 'interface GigabitEthernet3' 'shutdown' 'end'
  sleep 10
  .venv/bin/python poc/xr/swsh.py "$SW" 'show etherchannel summary' 'show lacp neighbor' 'ping 192.168.200.3 repeat 10'
  sleep 20
  .venv/bin/python poc/xr/swsh.py "$SW" 'show etherchannel summary' 'show lacp neighbor' 'ping 192.168.200.3 repeat 10'
  S "$E3" 'show l2vpn evpn mac' 'show bgp l2vpn evpn route-type 1'
  S "$E1" 'configure terminal' 'interface GigabitEthernet3' 'no shutdown' 'end'
}

f0() {
  H "f0: CFM の書き方をヘルプで探る(XE1)"
  S "$E1" 'configure terminal' 'ethernet cfm ieee' 'ethernet cfm global' 'ethernet evc E120' 'exit' 'ethernet cfm domain CUST level 5' \
    'service E-LINE-120 evc E120 ?' 'service E-LINE-120 evc E120 vlan 120 ?' 'end'
  S "$E1" 'configure terminal' 'interface GigabitEthernet2' 'service instance 120 ethernet E120' '?' 'end'
}

f() {
  H "f-1: CFM(802.1ag)の MEP を E-Line(EVPN-VPWS・XE1⇔XE3・VLAN 120)の両端の EFP に(XE1 mpid 41・XE3 mpid 43・レベル 5・CC 1 秒)"
  for p in "$E1:41" "$E3:43"; do
    S "${p%%:*}" 'configure terminal' 'ethernet cfm ieee' 'ethernet cfm global' 'ethernet evc E120' 'exit' \
      'ethernet cfm domain CUST level 5' 'no service E-LINE-120 evc E120' 'service E-LINE-120 evc E120 vlan 120' \
      'continuity-check' 'continuity-check interval 1s' 'exit' 'exit' \
      'interface GigabitEthernet2' 'service instance 120 ethernet E120' "cfm mep domain CUST mpid ${p##*:}" 'end' \
      'show running-config | section cfm|evc E120|service instance 120'
  done
  sleep 20
  S "$E1" 'show ethernet cfm maintenance-points local' 'show ethernet cfm maintenance-points remote' \
    'ping ethernet mpid 43 domain CUST service E-LINE-120' 'traceroute ethernet mpid 43 domain CUST service E-LINE-120'
  H "f-2: Y.1731 の遅延(IP SLA の ethernet y1731 delay DMM)"
  S "$E1" 'configure terminal' 'ip sla 10' 'ethernet y1731 delay DMM domain CUST evc E120 mpid 43 cos 0 source mpid 41' 'frequency 10' 'exit' \
    'ip sla schedule 10 start-time now life forever' 'end'
  sleep 25
  S "$E1" 'show ip sla summary' 'show ip sla statistics 10'
  H "f-3: 片側(XE3)の EFP を落とす → XE1 の remote MEP・エラー"
  S "$E3" 'configure terminal' 'interface GigabitEthernet2' 'service instance 120 ethernet E120' 'shutdown' 'end'
  sleep 15
  S "$E1" 'show ethernet cfm maintenance-points remote' 'show ethernet cfm errors' 'show ethernet cfm maintenance-points local detail | include RDI|Defect|defect'
  S "$E3" 'configure terminal' 'interface GigabitEthernet2' 'service instance 120 ethernet E120' 'no shutdown' 'end'
}

for p in "$@"; do "$p"; done
