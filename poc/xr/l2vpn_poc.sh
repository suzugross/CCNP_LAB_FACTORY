#!/bin/bash
# BL-246 M11 L2VPN とキャリア イーサネット(SPCOR 4.1.a・4.2)の PoC。盤面= problems/_POC-XRL2VPN
#   XR01・XR02= XRv9000 26.1.1(PE)・XR03= XRd 26.1.1(PE・L2 を転送するかを見る)・RT01/RT03= P・RT02= IOL 17.15 の PE・CE1〜4= IOL・SW1= IOL-L2。
# 記録= design §24。usage: source poc/xr/env.sh; poc/xr/l2vpn_poc.sh <phase…>   出力は標準出力(呼び出し側で poc/xr/l2vpn-<phase>.log へ)
cd "$(dirname "$0")/../.."
PID=${PID:-_POC-XRL2VPN}
M=topologies/_generated/$PID/mgmt_map.yml
ip() { awk -v n="$1:" '$1==n{print $2}' "$M"; }
X1=$(ip XR01) X2=$(ip XR02) X3=$(ip XR03) R1=$(ip RT01) R2=$(ip RT02) R3=$(ip RT03)
C1=$(ip CE1) C2=$(ip CE2) C3=$(ip CE3) C4=$(ip CE4) SW=$(ip SW1)
S() { local h=$1; shift; .venv/bin/python poc/xr/xrsh.py "$h" "$@" 2>&1; }
H() { echo; echo "######## $(date +%T) $*"; }
# XR の IF(links[3]= Gi0/0/0/0 …)。XR01: G0 RT01・G1 RT03・G2 CE1・G3 SW1 / XR02: G0 RT03・G1 CE4・G2 SW1 / XR03: G0 RT01・G1 CE3
G0=GigabitEthernet0/0/0/0 G1=GigabitEthernet0/0/0/1 G2=GigabitEthernet0/0/0/2 G3=GigabitEthernet0/0/0/3

a() {
  H "a-1: 版・IS-IS・LDP(XR の 3 台と RT02)"
  for h in $X1 $X2 $X3; do
    S "$h" 'show version | include "Version|uptime"' 'show isis adjacency' 'show mpls ldp neighbor brief' 'show ipv4 interface brief'
  done
  S "$R2" 'show version | include IOS' 'show isis neighbors' 'show mpls ldp neighbor | include Peer|State' 'show ip route isis | include /32'
  H "a-2: CE の IF(サブインタフェースが up か)"
  for h in $C1 $C2 $C3 $C4; do S "$h" 'show ip interface brief | exclude unassigned'; done
}

p() {
  H "p-1: RT02(IOL 17.15)が受け付ける L2VPN の書き方(試して消す)"
  S "$R2" 'configure terminal' \
    'interface Ethernet0/2' 'service instance 999 ethernet' 'encapsulation dot1q 999' 'rewrite ingress tag pop 1 symmetric' 'exit' 'no service instance 999 ethernet' 'exit' \
    'bridge-domain 999' 'exit' 'no bridge-domain 999' \
    'l2vpn xconnect context PROBE' 'exit' 'no l2vpn xconnect context PROBE' \
    'interface pseudowire999' 'encapsulation mpls' 'neighbor 10.255.0.1 999' 'exit' 'no interface pseudowire999' \
    'l2vpn vfi context PROBE' 'vpn id 999' 'exit' 'no l2vpn vfi context PROBE' \
    'l2vpn evpn' 'exit' 'no l2vpn evpn' \
    'l2vpn evpn instance 999 point-to-point' 'exit' 'no l2vpn evpn instance 999 point-to-point' \
    'l2vpn evpn instance 998 vlan-based' 'exit' 'no l2vpn evpn instance 998 vlan-based' \
    'ethernet cfm ieee' 'no ethernet cfm ieee' 'ethernet cfm global' 'no ethernet cfm global' \
    'interface Ethernet0/2.999' 'encapsulation dot1Q 999' 'xconnect 10.255.0.1 999 encapsulation mpls' 'no xconnect' 'exit' 'no interface Ethernet0/2.999' \
    'end' 'show running-config | section l2vpn|bridge-domain|pseudowire|cfm|Ethernet0/2'
  H "p-2: CE1(IOL)で二重タグ(802.1Q-in-Q)のサブインタフェースを作れるか(試して消す)"
  S "$C1" 'configure terminal' 'interface Ethernet0/0.999' 'encapsulation dot1Q 400 second-dot1q 10' 'exit' 'no interface Ethernet0/0.999' 'end'
}

T() { .venv/bin/python poc/xr/tcpprobe.py "$@" 2>&1 | tail -2; }
XSH='show l2vpn xconnect'
R2SH='show l2vpn atom vc'

b() {
  H "b-1: XRd(XR03)に l2transport のサブインタフェースと LDP の疑似回線(相手 RT02・pw-id 103)を入れる"
  S "$X3" configure "interface $G1.103 l2transport" 'encapsulation dot1q 103' 'rewrite ingress tag pop 1 symmetric' 'root' \
    'l2vpn' 'xconnect group POC' 'p2p CE3-CE2' "interface $G1.103" 'neighbor ipv4 10.255.0.12 pw-id 103' 'root' \
    'show configuration' commit 'show configuration failed' end
  H "b-2: RT02 側= EVC(service instance)+ l2vpn xconnect context"
  S "$R2" 'configure terminal' 'interface Ethernet0/2' 'service instance 103 ethernet' 'encapsulation dot1q 103' 'rewrite ingress tag pop 1 symmetric' 'exit' 'exit' \
    'l2vpn xconnect context CE3-CE2' 'member Ethernet0/2 service-instance 103' 'member 10.255.0.31 103 encapsulation mpls' 'end'
  sleep 20
  S "$X3" "$XSH" "$XSH detail" 'show mpls ldp neighbor brief'
  S "$R2" "$R2SH" "$R2SH detail" 'show ethernet service instance'
  H "b-3: CE3 ⇔ CE2(VLAN 103)の ping・大きいパケット・TCP"
  S "$C3" 'ping 192.168.103.2 repeat 5' 'ping 192.168.103.2 size 1500 df-bit repeat 3' 'show arp | include 192.168.103'
  T "$C3" 192.168.103.2
  S "$X3" "show interfaces $G1.103 accounting" "show l2vpn forwarding interface $G1.103 detail location 0/RP0/CPU0"
}

c() {
  H "c-1: XRv9000(XR01)に E-Line(LDP の疑似回線・相手 RT02・pw-id 100)"
  S "$X1" configure "interface $G2.100 l2transport" 'encapsulation dot1q 100' 'rewrite ingress tag pop 1 symmetric' 'root' \
    'l2vpn' 'xconnect group POC' 'p2p CE1-CE2' "interface $G2.100" 'neighbor ipv4 10.255.0.12 pw-id 100' 'root' \
    'show configuration' commit 'show configuration failed' end
  S "$R2" 'configure terminal' 'interface Ethernet0/2' 'service instance 100 ethernet' 'encapsulation dot1q 100' 'rewrite ingress tag pop 1 symmetric' 'exit' 'exit' \
    'l2vpn xconnect context CE1-CE2' 'member Ethernet0/2 service-instance 100' 'member 10.255.0.1 100 encapsulation mpls' 'end'
  sleep 20
  S "$X1" "$XSH" "$XSH detail"
  S "$R2" "$R2SH" "$R2SH vcid 100 detail"
  H "c-2: CE1 ⇔ CE2(VLAN 100)の ping・大きいパケット・TCP"
  S "$C1" 'ping 192.168.100.2 repeat 5' 'ping 192.168.100.2 size 1500 df-bit repeat 3' 'ping 192.168.100.2 size 1501 df-bit repeat 2'
  T "$C1" 192.168.100.2
}

c3() {
  H "c3-1: いまのコアの MTU(XR01 の G0・RT01・RT02)と、疑似回線の上で通る大きさの上限を探る"
  S "$X1" "show interfaces $G0 | include MTU" "show im database interface $G0 | include mtu" 'show mpls forwarding labels 24009 detail | include MTU'
  S "$R1" 'show interfaces Ethernet0/0 | include MTU' 'show interfaces Ethernet0/1 | include MTU'
  S "$C1" 'ping 192.168.100.2 size 1478 df-bit repeat 2' 'ping 192.168.100.2 size 1479 df-bit repeat 2'
  H "c3-2: 主経路(XR01–RT01–RT02)の MTU を上げる(XR は L2 ヘッダ込み= 1614・IOS は L3 = 1600)"
  S "$X1" configure "interface $G0" 'mtu 1614' commit end "show interfaces $G0 | include MTU" 'show isis adjacency'
  S "$R1" 'configure terminal' 'interface Ethernet0/0' 'mtu 1600' 'interface Ethernet0/1' 'mtu 1600' 'end' 'show interfaces Ethernet0/0 | include MTU'
  S "$R2" 'configure terminal' 'interface Ethernet0/0' 'mtu 1600' 'end' 'show interfaces Ethernet0/0 | include MTU'
  sleep 25
  S "$X1" 'show isis adjacency' 'show mpls ldp neighbor brief'
  S "$C1" 'ping 192.168.100.2 size 1500 df-bit repeat 3'
  H "c3-3: AC の MTU を食い違わせる(XR01 の CE1 向き G2 を 9014 に= AC の MTU 9000)→ 疑似回線の状態"
  S "$X1" configure "interface $G2" 'mtu 9014' commit end
  sleep 15
  S "$X1" "$XSH" "$XSH detail | include \"state|MTU|mismatch\""
  S "$R2" "$R2SH" "$R2SH vcid 100 detail | include MTU|status|mismatch"
  S "$X1" 'show logging last 15 | include "L2VPN|PW|MTU"'
  H "c3-4: 戻す"
  S "$X1" configure "interface $G2" 'no mtu' commit end
  sleep 15
  S "$X1" "$XSH"
}

d() {
  H "d-1: BGP の l2vpn evpn= XR03(XRd)をルート リフレクタに・XR01/XR02/RT02 はクライアント"
  S "$X3" configure 'router bgp 65000' 'bgp router-id 10.255.0.31' 'address-family l2vpn evpn' 'exit' \
    'neighbor-group PE' 'remote-as 65000' 'update-source Loopback0' 'address-family l2vpn evpn' 'route-reflector-client' 'exit' 'exit' \
    'neighbor 10.255.0.1' 'use neighbor-group PE' 'exit' 'neighbor 10.255.0.21' 'use neighbor-group PE' 'exit' 'neighbor 10.255.0.12' 'use neighbor-group PE' \
    'root' commit 'show configuration failed' end
  for h in "$X1:10.255.0.1" "$X2:10.255.0.21"; do
    S "${h%%:*}" configure 'router bgp 65000' "bgp router-id ${h##*:}" 'address-family l2vpn evpn' 'exit' \
      'neighbor 10.255.0.31' 'remote-as 65000' 'update-source Loopback0' 'address-family l2vpn evpn' 'root' commit 'show configuration failed' end
  done
  S "$R2" 'configure terminal' 'router bgp 65000' 'bgp router-id 10.255.0.12' 'bgp log-neighbor-changes' 'no bgp default ipv4-unicast' \
    'neighbor 10.255.0.31 remote-as 65000' 'neighbor 10.255.0.31 update-source Loopback0' \
    'address-family l2vpn evpn' 'neighbor 10.255.0.31 activate' 'neighbor 10.255.0.31 send-community both' 'end'
  H "d-2: EVPN-VPWS XR01(source 1)⇔ XR02(source 4)・EVI 110・VLAN 110"
  S "$X1" configure "interface $G2.110 l2transport" 'encapsulation dot1q 110' 'rewrite ingress tag pop 1 symmetric' 'root' \
    'l2vpn' 'xconnect group POC' 'p2p CE1-CE4' "interface $G2.110" 'neighbor evpn evi 110 target 4 source 1' 'root' commit 'show configuration failed' end
  S "$X2" configure "interface $G1.110 l2transport" 'encapsulation dot1q 110' 'rewrite ingress tag pop 1 symmetric' 'root' \
    'l2vpn' 'xconnect group POC' 'p2p CE4-CE1' "interface $G1.110" 'neighbor evpn evi 110 target 1 source 4' 'root' commit 'show configuration failed' end
  sleep 30
  S "$X3" 'show bgp l2vpn evpn summary' 'show bgp l2vpn evpn'
  S "$X1" "$XSH" "$XSH detail" 'show evpn evi vpn-id 110 detail' 'show bgp l2vpn evpn rd 10.255.0.21:110'
  S "$C1" 'ping 192.168.110.4 repeat 5' 'ping 192.168.110.4 size 1478 df-bit repeat 2'
  T "$C1" 192.168.110.4
}

d2() {
  H "d2-1: IOL(RT02)を EVPN-VPWS の相手に(EVI 120・VLAN 120・XR01 source 1 ⇔ RT02 source 2)。CE1/CE2 に VLAN 120 を足す"
  S "$C1" 'configure terminal' 'interface Ethernet0/0.120' 'encapsulation dot1Q 120' 'ip address 192.168.120.1 255.255.255.0' 'end'
  S "$C2" 'configure terminal' 'interface Ethernet0/0.120' 'encapsulation dot1Q 120' 'ip address 192.168.120.2 255.255.255.0' 'end'
  S "$X1" configure "interface $G2.120 l2transport" 'encapsulation dot1q 120' 'rewrite ingress tag pop 1 symmetric' 'root' \
    'l2vpn' 'xconnect group POC' 'p2p CE1-CE2-EVPN' "interface $G2.120" 'neighbor evpn evi 120 target 2 source 1' 'root' commit 'show configuration failed' end
  S "$R2" 'configure terminal' 'interface Ethernet0/2' 'service instance 120 ethernet' 'encapsulation dot1q 120' 'rewrite ingress tag pop 1 symmetric' 'exit' 'exit' \
    'l2vpn evpn instance 120 point-to-point' 'vpws context CE2-CE1' 'service target 1 source 2' 'member Ethernet0/2 service-instance 120' 'end' \
    'show running-config | section l2vpn evpn' 'show bgp l2vpn evpn summary'
  sleep 30
  S "$R2" 'show l2vpn evpn vpws vc id 120 detail' 'show l2vpn evpn vpws vc' 'show bgp l2vpn evpn'
  S "$X1" "$XSH" "$XSH group POC xc-name CE1-CE2-EVPN detail"
  S "$C1" 'ping 192.168.120.2 repeat 5'
}

e() {
  H "e-1: EVPN の E-LAN= ブリッジ ドメイン BD200 に EVI 200(XR01: CE1 の VLAN 200・XR02: CE4 の VLAN 201)。どちらも pop 1 で、BD の中ではタグなし"
  S "$X1" configure "interface $G2.200 l2transport" 'encapsulation dot1q 200' 'rewrite ingress tag pop 1 symmetric' 'root' \
    'evpn' 'evi 200' 'advertise-mac' 'root' \
    'l2vpn' 'bridge group POC' 'bridge-domain BD200' "interface $G2.200" 'exit' 'evi 200' 'root' commit 'show configuration failed' end
  S "$X2" configure "interface $G1.201 l2transport" 'encapsulation dot1q 201' 'rewrite ingress tag pop 1 symmetric' 'root' \
    'evpn' 'evi 200' 'advertise-mac' 'root' \
    'l2vpn' 'bridge group POC' 'bridge-domain BD200' "interface $G1.201" 'exit' 'evi 200' 'root' commit 'show configuration failed' end
  sleep 30
  S "$C1" 'ping 192.168.200.4 repeat 5'
  S "$C4" 'ping 192.168.200.1 repeat 5'
  T "$C1" 192.168.200.4
  S "$X1" 'show l2vpn bridge-domain bd-name BD200' 'show l2vpn bridge-domain bd-name BD200 detail | include "state|MAC|EVPN|evi|ACs|PWs"' \
    'show evpn evi vpn-id 200 mac' 'show bgp l2vpn evpn rd 10.255.0.21:200' 'show l2vpn forwarding bridge-domain POC:BD200 mac-address location 0/RP0/CPU0'
  H "e-2: タグの付け替えを 1-to-1 の translate で(XR02 の CE4 向きを pop の代わりに translate 1-to-1 dot1q 200)→ BD の中にタグ 200 が残る形。相手 XR01 は pop のまま"
  S "$X2" configure "interface $G1.201 l2transport" 'rewrite ingress tag translate 1-to-1 dot1q 200 symmetric' commit 'show configuration failed' end
  sleep 10
  S "$C4" 'clear arp' 'ping 192.168.200.1 repeat 5'
  S "$X2" configure "interface $G1.201 l2transport" 'rewrite ingress tag pop 1 symmetric' commit end
}

e2() {
  H "e2-1: VPLS(LDP)= VLAN 210 で XR01・XR02・RT02 の 3 拠点(VFI・全部と疑似回線)。CE1/CE4/CE2 に VLAN 210 を足す"
  for h in "$C1:1" "$C4:4" "$C2:2"; do
    S "${h%%:*}" 'configure terminal' 'interface Ethernet0/0.210' 'encapsulation dot1Q 210' "ip address 192.168.210.${h##*:} 255.255.255.0" 'end'
  done
  S "$X1" configure "interface $G2.210 l2transport" 'encapsulation dot1q 210' 'rewrite ingress tag pop 1 symmetric' 'root' \
    'l2vpn' 'bridge group POC' 'bridge-domain BD210' "interface $G2.210" 'exit' 'vfi VPLS210' 'neighbor 10.255.0.21 pw-id 210' 'exit' 'neighbor 10.255.0.12 pw-id 210' \
    'root' commit 'show configuration failed' end
  S "$X2" configure "interface $G1.210 l2transport" 'encapsulation dot1q 210' 'rewrite ingress tag pop 1 symmetric' 'root' \
    'l2vpn' 'bridge group POC' 'bridge-domain BD210' "interface $G1.210" 'exit' 'vfi VPLS210' 'neighbor 10.255.0.1 pw-id 210' 'exit' 'neighbor 10.255.0.12 pw-id 210' \
    'root' commit 'show configuration failed' end
  S "$R2" 'configure terminal' 'l2vpn vfi context VPLS210' 'vpn id 210' 'member 10.255.0.1 encapsulation mpls' 'member 10.255.0.21 encapsulation mpls' 'exit' \
    'bridge-domain 210' 'member Ethernet0/2 service-instance 210' 'member vfi VPLS210' 'exit' \
    'interface Ethernet0/2' 'service instance 210 ethernet' 'encapsulation dot1q 210' 'rewrite ingress tag pop 1 symmetric' 'bridge-domain 210' 'end' \
    'show running-config | section vfi|bridge-domain'
  sleep 30
  S "$X1" 'show l2vpn bridge-domain bd-name BD210' 'show l2vpn bridge-domain bd-name BD210 detail | include "PW:|state is|PW type|MTU"'
  S "$R2" 'show l2vpn vfi' 'show l2vpn atom vc' 'show bridge-domain 210'
  S "$C1" 'ping 192.168.210.2 repeat 5' 'ping 192.168.210.4 repeat 5'
  S "$C2" 'ping 192.168.210.4 repeat 5'
  T "$C2" 192.168.210.1
  S "$X1" 'show l2vpn forwarding bridge-domain POC:BD210 mac-address location 0/RP0/CPU0'
  S "$R2" 'show bridge-domain 210 | include Et|pseudowire|MAC|mac'
}

f() {
  H "f-1: 両端で VLAN が違う E-Line(CE4 を VLAN 111 に替える)。XR01 は 110・XR02 は 111、どちらも pop 1(EVPN-VPWS CE1-CE4)"
  S "$C4" 'configure terminal' 'no interface Ethernet0/0.110' 'interface Ethernet0/0.111' 'encapsulation dot1Q 111' 'ip address 192.168.110.4 255.255.255.0' 'end'
  S "$X2" configure "no interface $G1.110" "interface $G1.111 l2transport" 'encapsulation dot1q 111' 'rewrite ingress tag pop 1 symmetric' 'root' \
    'l2vpn' 'xconnect group POC' 'p2p CE4-CE1' "no interface $G1.110" "interface $G1.111" 'root' commit 'show configuration failed' end
  sleep 15
  S "$X2" "$XSH"
  S "$C1" 'ping 192.168.110.4 repeat 5'
  H "f-2: 両端とも rewrite を外す(タグを付けたまま運ぶ)→ CE4 には 110 のまま届く"
  S "$X1" configure "interface $G2.110 l2transport" 'no rewrite ingress tag pop 1 symmetric' commit end
  S "$X2" configure "interface $G1.111 l2transport" 'no rewrite ingress tag pop 1 symmetric' commit end
  sleep 10
  S "$C1" 'clear arp' 'ping 192.168.110.4 repeat 5'
  S "$X2" "show l2vpn xconnect group POC xc-name CE4-CE1 detail | include \"Rewrite|packets|state is|drops\""
  H "f-3: XR02 で translate 1-to-1(CE4 の 111 ⇔ コアでは 110)"
  S "$X2" configure "interface $G1.111 l2transport" 'rewrite ingress tag translate 1-to-1 dot1q 110 symmetric' commit 'show configuration failed' end
  sleep 10
  S "$C1" 'clear arp' 'ping 192.168.110.4 repeat 5'
  S "$X2" "show l2vpn xconnect group POC xc-name CE4-CE1 detail | include \"Rewrite|packets|state is\""
  H "f-4: 片側だけ pop(XR01 は pop・XR02 は translate のまま)= 非対称の症状"
  S "$X1" configure "interface $G2.110 l2transport" 'rewrite ingress tag pop 1 symmetric' commit end
  sleep 10
  S "$C1" 'clear arp' 'ping 192.168.110.4 repeat 5'
  S "$X2" configure "interface $G1.111 l2transport" 'rewrite ingress tag pop 1 symmetric' commit end
  sleep 10
  S "$C1" 'clear arp' 'ping 192.168.110.4 repeat 3'
  H "f-5: Q-in-Q= CE1 が 400/10 の二重タグで出す → XR01 が 2 枚とも外す(pop 2)→ XR02 で CE4 の VLAN 140 へ"
  S "$C1" 'configure terminal' 'interface Ethernet0/0.1400' 'encapsulation dot1Q 400 second-dot1q 10' 'ip address 192.168.140.1 255.255.255.0' 'end'
  S "$C4" 'configure terminal' 'interface Ethernet0/0.140' 'encapsulation dot1Q 140' 'ip address 192.168.140.4 255.255.255.0' 'end'
  S "$X1" configure "interface $G2.400 l2transport" 'encapsulation dot1q 400 second-dot1q 10' 'rewrite ingress tag pop 2 symmetric' 'root' \
    'l2vpn' 'xconnect group POC' 'p2p QINQ' "interface $G2.400" 'neighbor evpn evi 140 target 40 source 14' 'root' commit 'show configuration failed' end
  S "$X2" configure "interface $G1.140 l2transport" 'encapsulation dot1q 140' 'rewrite ingress tag pop 1 symmetric' 'root' \
    'l2vpn' 'xconnect group POC' 'p2p QINQ' "interface $G1.140" 'neighbor evpn evi 140 target 14 source 40' 'root' commit 'show configuration failed' end
  sleep 30
  S "$X1" "$XSH"
  S "$C1" 'ping 192.168.140.4 repeat 5'
  H "f-6: 802.1ad(外側 0x88a8)の書き方が通るか・pop 1 で外側だけ外す形・push"
  S "$X1" configure "interface $G2.401 l2transport" 'encapsulation dot1ad 401 dot1q 10' 'rewrite ingress tag pop 1 symmetric' 'root' \
    "interface $G2.402 l2transport" 'encapsulation dot1q 402' 'rewrite ingress tag push dot1q 999 symmetric' 'root' \
    "interface $G2.403 l2transport" 'encapsulation dot1q 403' 'rewrite ingress tag translate 1-to-2 dot1ad 500 dot1q 403 symmetric' 'root' \
    'show configuration' commit 'show configuration failed' 'abort'
}

g() {
  H "g-1: CFM(802.1ag)の up MEP を E-Line CE1-CE4(EVPN-VPWS)の両端に(XR01 mep 1・XR02 mep 4・レベル 5・CC 1 秒)"
  for h in "$X1:$G2.110:1:4:CE1-CE4" "$X2:$G1.111:4:1:CE4-CE1"; do
    IFS=: read -r host ifn me peer xc <<<"$h"
    S "$host" configure 'ethernet cfm' 'domain CUST level 5 id null' "service E-LINE-110 xconnect group POC p2p $xc id number 110" \
      'continuity-check interval 1s' 'mep crosscheck' "mep-id $peer" 'root' \
      "interface $ifn l2transport" 'ethernet cfm' "mep domain CUST service E-LINE-110 mep-id $me" 'root' commit 'show configuration failed' end
  done
  sleep 20
  S "$X1" 'show ethernet cfm peer meps' 'show ethernet cfm local meps' 'show ethernet cfm services'
  S "$X1" "ping ethernet cfm domain CUST service E-LINE-110 mep-id 4 source interface $G2.110" \
    "traceroute ethernet cfm domain CUST service E-LINE-110 mep-id 4 source interface $G2.110"
  H "g-2: Y.1731 の遅延の測定(ethernet sla)"
  S "$X1" configure 'ethernet sla' 'profile DM type cfm-delay-measurement' 'probe' 'send packet every 1 seconds' 'exit' 'schedule' 'every 1 minutes for 30 seconds' 'exit' \
    'statistics' 'measure round-trip-delay' 'buckets size 1 probes' 'root' \
    "interface $G2.110 l2transport" 'ethernet cfm' 'mep domain CUST service E-LINE-110 mep-id 1' 'sla operation profile DM target mep-id 4' 'root' \
    commit 'show configuration failed' end
  H "g-3: 片側の MEP を消す(XR02)→ XR01 の peer の表示(CC の途絶・crosscheck)"
  S "$X2" configure "interface $G1.111 l2transport" 'no ethernet cfm' commit end
  sleep 15
  S "$X1" 'show ethernet cfm peer meps' 'show ethernet cfm local meps verbose | include "Defect|Errors|missing|RDI|Peer MEP"'
}

g2() {
  H "g2-0: XRd(XR03)は ethernet cfm を受け付けるか(XRv9000 26.1.1 は CFM のパッケージなし= コマンドが無い)"
  S "$X3" configure 'ethernet cfm' 'domain CUST level 5 id null' 'show configuration' 'abort'
  H "g2-1: お客さまの CE 同士(IOL)で CFM の down MEP(VLAN 100= XR01⇔RT02 の LDP の疑似回線を素通り)。CE1 mpid 1・CE2 mpid 2・レベル 5"
  for h in "$C1:1" "$C2:2"; do
    S "${h%%:*}" 'configure terminal' 'ethernet cfm ieee' 'ethernet cfm global' 'ethernet cfm domain CUST level 5' \
      'service E-LINE-100 vlan 100 direction down' 'continuity-check' 'continuity-check interval 1s' 'exit' 'exit' \
      'interface Ethernet0/0' "ethernet cfm mep domain CUST mpid ${h##*:} vlan 100" 'end'
  done
  sleep 20
  S "$C1" 'show ethernet cfm maintenance-points local' 'show ethernet cfm maintenance-points remote' \
    'ping ethernet mpid 2 domain CUST vlan 100' 'traceroute ethernet mpid 2 domain CUST vlan 100'
  H "g2-2: Y.1731 の遅延(IP SLA の ethernet y1731 delay DMM)"
  S "$C1" 'configure terminal' 'ip sla 10' 'ethernet y1731 delay DMM domain CUST vlan 100 mpid 2 cos 0 source mpid 1' 'frequency 10' 'exit' \
    'ip sla schedule 10 start-time now life forever' 'end'
  sleep 25
  S "$C1" 'show ip sla summary' 'show ip sla statistics 10'
  H "g2-3: 疑似回線を落とす(XR01 の AC を shutdown)→ CE1 の remote MEP の表示"
  S "$X1" configure "interface $G2.100 l2transport" 'shutdown' commit end
  sleep 12
  S "$C1" 'show ethernet cfm maintenance-points remote' 'show ethernet cfm errors' 'show ethernet cfm statistics | include CCM'
  S "$X1" configure "interface $G2.100 l2transport" 'no shutdown' commit end
}

h() {
  H "h-0: CE の CFM の残骸と XR01 の f-6 の残骸を片付ける"
  for c in $C1 $C2; do
    S "$c" 'configure terminal' 'interface Ethernet0/0' 'no service instance 100 ethernet E100' 'exit' 'no ethernet cfm domain CUST level 5' 'no ethernet evc E100' 'no ethernet cfm global' 'no ethernet cfm ieee' 'end'
  done
  S "$X1" configure "no interface $G2.401" "no interface $G2.402" "no interface $G2.403" commit end
  H "h-1: VC タイプの食い違い= XR01 だけ transport-mode vlan(タイプ 4)・RT02 は既定(タイプ 5)"
  S "$X1" configure 'l2vpn' 'pw-class T4' 'encapsulation mpls' 'transport-mode vlan' 'root' \
    'l2vpn' 'xconnect group POC' 'p2p CE1-CE2' 'neighbor ipv4 10.255.0.12 pw-id 100' 'pw-class T4' 'root' commit 'show configuration failed' end
  sleep 15
  S "$X1" "$XSH" "show l2vpn xconnect group POC xc-name CE1-CE2 detail | include \"state is|PW type|Error|mismatch\""
  S "$R2" "$R2SH vcid 100 detail | include status|type|error|Last"
  S "$C1" 'ping 192.168.100.2 repeat 3'
  H "h-2: control word の食い違い= XR01 だけ control-word(タイプは 5 に戻す)。RT02 は既定(autosense)"
  S "$X1" configure 'l2vpn' 'pw-class T4' 'encapsulation mpls' 'no transport-mode vlan' 'control-word' commit 'show configuration failed' end
  sleep 15
  S "$X1" "show l2vpn xconnect group POC xc-name CE1-CE2 detail | include \"state is|PW type|Control word|control word|Error\""
  S "$R2" "$R2SH vcid 100 detail | include status|Control|control"
  S "$C1" 'ping 192.168.100.2 repeat 3'
  H "h-3: 戻す(pw-class を外す)"
  S "$X1" configure 'l2vpn' 'xconnect group POC' 'p2p CE1-CE2' 'neighbor ipv4 10.255.0.12 pw-id 100' 'no pw-class T4' 'root' 'no l2vpn pw-class T4' commit end
  sleep 15
  S "$X1" "$XSH"
  H "h-4: EVPN-VPWS の source/target の食い違い= XR02 の target を 9 に(本当は 1)"
  S "$X2" configure 'l2vpn' 'xconnect group POC' 'p2p CE4-CE1' "interface $G1.111" 'no neighbor evpn evi 110 target 1 source 4' 'neighbor evpn evi 110 target 9 source 4' 'root' commit 'show configuration failed' end
  sleep 20
  S "$X2" "$XSH" "show l2vpn xconnect group POC xc-name CE4-CE1 detail | include \"state is|EVPN:|neighbor|Label\""
  S "$X1" "show l2vpn xconnect group POC xc-name CE1-CE4 detail | include \"state is|EVPN:|neighbor\"" 'show evpn evi vpn-id 110 inclusive-multicast' 'show bgp l2vpn evpn rd 10.255.0.21:110'
  S "$X2" configure 'l2vpn' 'xconnect group POC' 'p2p CE4-CE1' 'no neighbor evpn evi 110 target 9 source 4' 'neighbor evpn evi 110 target 1 source 4' 'root' commit end
  H "h-5: RT の食い違い= XR02 の EVI 110 の import/export を 65000:999 に"
  S "$X2" configure 'evpn' 'evi 110' 'bgp' 'route-target import 65000:999' 'route-target export 65000:999' 'root' commit 'show configuration failed' end
  sleep 20
  S "$X2" "$XSH" 'show evpn evi vpn-id 110 detail | include "RT|Route Target|65000"'
  S "$X1" "$XSH" 'show bgp l2vpn evpn rd 10.255.0.21:110'
  S "$C1" 'ping 192.168.110.4 repeat 3'
  S "$X2" configure 'no evpn evi 110' commit end
  sleep 20
  S "$X2" "$XSH"
  S "$C1" 'ping 192.168.110.4 repeat 3'
}

j() {
  H "j-1: LDP の疑似回線(XR01⇔RT02・VLAN 100)で XR01 の rewrite を付け忘れる → 状態・MTU・通信"
  S "$X1" configure "interface $G2.100 l2transport" 'no rewrite ingress tag pop 1 symmetric' commit end
  sleep 15
  S "$X1" "show l2vpn xconnect group POC xc-name CE1-CE2 detail | include \"state is|MTU|Error|PW type|Rewrite\""
  S "$R2" "$R2SH vcid 100 detail | include status|MTU|error|Last"
  S "$C1" 'clear arp' 'ping 192.168.100.2 repeat 3'
  H "j-2: 戻す"
  S "$X1" configure "interface $G2.100 l2transport" 'rewrite ingress tag pop 1 symmetric' commit end
  sleep 15
  S "$X1" "$XSH"
}

k() {
  H "k-1: Q-in-Q で内側の VLAN をまとめて運ぶ= AC は外側 410 だけを指定して pop 1(EVPN-VPWS XR01⇔XR02・EVI 410)。CE は 410/10 と 410/20"
  S "$C1" 'configure terminal' 'interface Ethernet0/0.4110' 'encapsulation dot1Q 410 second-dot1q 10' 'ip address 192.168.41.1 255.255.255.0' 'exit' \
    'interface Ethernet0/0.4120' 'encapsulation dot1Q 410 second-dot1q 20' 'ip address 192.168.42.1 255.255.255.0' 'end'
  S "$C4" 'configure terminal' 'interface Ethernet0/0.4110' 'encapsulation dot1Q 410 second-dot1q 10' 'ip address 192.168.41.4 255.255.255.0' 'exit' \
    'interface Ethernet0/0.4120' 'encapsulation dot1Q 410 second-dot1q 20' 'ip address 192.168.42.4 255.255.255.0' 'end'
  S "$X1" configure "interface $G2.410 l2transport" 'encapsulation dot1q 410' 'rewrite ingress tag pop 1 symmetric' 'root' \
    'l2vpn' 'xconnect group POC' 'p2p QINQ-ALL' "interface $G2.410" 'neighbor evpn evi 410 target 2 source 1' 'root' commit 'show configuration failed' end
  S "$X2" configure "interface $G1.410 l2transport" 'encapsulation dot1q 410' 'rewrite ingress tag pop 1 symmetric' 'root' \
    'l2vpn' 'xconnect group POC' 'p2p QINQ-ALL' "interface $G1.410" 'neighbor evpn evi 410 target 1 source 2' 'root' commit 'show configuration failed' end
  sleep 30
  S "$X1" "$XSH" "show l2vpn xconnect group POC xc-name QINQ-ALL detail | include \"state is|MTU|Rewrite|VLAN\""
  S "$C1" 'ping 192.168.41.4 repeat 3' 'ping 192.168.42.4 repeat 3'
  H "k-2: AC を exact にする(外側 410 だけの単一タグに限る)→ 二重タグは落ちる"
  for h in "$X1:$G2" "$X2:$G1"; do S "${h%%:*}" configure "interface ${h##*:}.410 l2transport" 'encapsulation dot1q 410 exact' commit 'show configuration failed' end; done
  sleep 10
  S "$C1" 'clear arp' 'ping 192.168.41.4 repeat 3'
  H "k-3: 内側を 10 だけに限る(second-dot1q 10)→ 10 は通り 20 は落ちる"
  for h in "$X1:$G2" "$X2:$G1"; do S "${h%%:*}" configure "interface ${h##*:}.410 l2transport" 'encapsulation dot1q 410 second-dot1q 10' commit 'show configuration failed' end; done
  sleep 10
  S "$C1" 'clear arp' 'ping 192.168.41.4 repeat 3' 'ping 192.168.42.4 repeat 3'
  H "k-4: second-dot1q any(外側 410 の二重タグだけ・内側は何でも)"
  for h in "$X1:$G2" "$X2:$G1"; do S "${h%%:*}" configure "interface ${h##*:}.410 l2transport" 'encapsulation dot1q 410 second-dot1q any' commit 'show configuration failed' end; done
  sleep 10
  S "$C1" 'clear arp' 'ping 192.168.41.4 repeat 3' 'ping 192.168.42.4 repeat 3'
}

for p in "$@"; do "$p"; done
