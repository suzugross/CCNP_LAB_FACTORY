#!/bin/bash
# BL-261 PoC= 同じ盤面・同じ CE の組の上で 4 つのサービスを並べて組み、ラベルの積み方と設定の骨組みを比べる。盤面= problems/_POC-XRSVC
#   P1= IOL(P だけ・BGP なし)・RR1= IOL(RR だけ・P1 の脇・LDP なし)・XE1/XE2/XE3= Cat8000v の PE・XR01= XRv9000 の PE・CE1〜4= IOL(据付)
#   2026-11-04 に P1 兼 RR から RR1 を分けて取り直した(旧い出力は捨てた)
#   VLAN 100= L3VPN(CE1・CE2・CE4)/130= VPWS LDP(CE1⇔CE4)/140= VPWS EVPN(CE2⇔CE3)/200= EVPN E-LAN(CE1〜3)/210= VPLS(CE1〜3)
# 記録= design §26。usage: source poc/xr/env.sh; poc/xr/svc_poc.sh <phase…>   出力は標準出力(呼び出し側で poc/xr/expSVC-<phase>.log へ)
cd "$(dirname "$0")/../.."
PID=${PID:-_POC-XRSVC}
M=topologies/_generated/$PID/mgmt_map.yml
ip() { awk -v n="$1:" '$1==n{print $2}' "$M"; }
E1=$(ip XE1) E2=$(ip XE2) E3=$(ip XE3) P1=$(ip P1) X1=$(ip XR01) R1=$(ip RR1)
C1=$(ip CE1) C2=$(ip CE2) C3=$(ip CE3) C4=$(ip CE4)
S() { local h=$1; shift; .venv/bin/python poc/xr/xrsh.py "$h" "$@" 2>&1; }
H() { echo; echo "######## $(date +%T) $*"; }
CAP() { .venv/bin/python poc/xr/cml_cap.py "$PID" "$@" 2>&1 | tail -1; }
DEC() { echo "---- $1"; tcpdump -r "$1" -nn -e -c "${2:-6}" 2>/dev/null | cut -c1-400; }
XEG() { echo "$E1:1 $E2:2 $E3:3"; }   # 管理 IP:拠点の番号

a() {
  H "a: 版・ライセンスの段階・IS-IS・LDP・RR"
  for h in $E1 $E2 $E3; do
    S "$h" 'show version | include Version' 'show license summary | include network|dna' 'show isis neighbors' 'show mpls ldp neighbor | include Peer|State'
  done
  S "$X1" 'show version | include Version' 'show isis adjacency' 'show mpls ldp neighbor brief'
  S "$P1" 'show isis neighbors' 'show mpls forwarding-table' 'show bgp all summary'
  S "$R1" 'show isis neighbors' 'show bgp all summary'
}

bgp() {
  H "bgp: 段 1 の共通部分= PE から RR1 への iBGP。XE1〜3= vpnv4 と l2vpn evpn・XR01= vpnv4"
  for p in $(XEG); do h=${p%%:*} n=${p##*:}
    S "$h" 'configure terminal' 'router bgp 65000' "bgp router-id 10.255.0.4$n" 'bgp log-neighbor-changes' 'no bgp default ipv4-unicast' \
      'neighbor 10.255.0.52 remote-as 65000' 'neighbor 10.255.0.52 update-source Loopback0' \
      'address-family vpnv4' 'neighbor 10.255.0.52 activate' 'neighbor 10.255.0.52 send-community both' 'exit-address-family' \
      'address-family l2vpn evpn' 'neighbor 10.255.0.52 activate' 'neighbor 10.255.0.52 send-community both' 'end'
  done
  S "$X1" configure 'router bgp 65000' 'bgp router-id 10.255.0.1' 'address-family vpnv4 unicast' 'exit' \
    'neighbor 10.255.0.52' 'remote-as 65000' 'update-source Loopback0' 'address-family vpnv4 unicast' 'root' commit 'show configuration failed' end
  sleep 40
  S "$R1" 'show bgp all summary'
}

l3() {
  H "l3-1: L3VPN(VRF A・VLAN 100)を XE1・XE2 に。入れ物= VRF・収容= Gi2.100 を VRF に入れて eBGP"
  for p in "$E1:1" "$E2:2"; do h=${p%%:*} n=${p##*:}
    S "$h" 'configure terminal' 'vrf definition A' "rd 10.255.0.4$n:100" 'address-family ipv4' 'route-target export 65000:100' 'route-target import 65000:100' 'exit-address-family' 'exit' \
      'interface GigabitEthernet2.100' 'encapsulation dot1Q 100' 'vrf forwarding A' "ip address 172.16.$n.254 255.255.255.0" 'exit' \
      'router bgp 65000' 'address-family ipv4 vrf A' "neighbor 172.16.$n.1 remote-as 6500$n" "neighbor 172.16.$n.1 activate" 'end' \
      'show running-config | section vrf definition A|interface GigabitEthernet2|router bgp'
  done
  H "l3-2: XR01 に(VRF A・Gi0/0/0/1.100・eBGP は RPL が要る)"
  S "$X1" configure 'vrf A' 'address-family ipv4 unicast' 'import route-target' '65000:100' 'exit' 'export route-target' '65000:100' 'root' \
    'interface GigabitEthernet0/0/0/1.100' 'encapsulation dot1q 100' 'vrf A' 'ipv4 address 172.16.4.254 255.255.255.0' 'root' \
    'route-policy PASS' 'pass' 'end-policy' \
    'router bgp 65000' 'vrf A' 'rd 10.255.0.1:100' 'address-family ipv4 unicast' 'exit' 'neighbor 172.16.4.1' 'remote-as 65004' \
    'address-family ipv4 unicast' 'route-policy PASS in' 'route-policy PASS out' 'root' commit 'show configuration failed' end
  sleep 45
  H "l3-3: 確かめる(CE の LAN 同士)"
  S "$C1" 'show ip bgp' 'ping 10.100.2.1 source Loopback100 repeat 5' 'ping 10.100.4.1 source Loopback100 repeat 5' 'traceroute 10.100.4.1 source Loopback100 probe 1 timeout 2' 'traceroute 10.100.2.1 source Loopback100 probe 1 timeout 2'
  H "l3-4: PE が覚えたもの・ラベル"
  S "$E1" 'show ip route vrf A' 'show bgp vpnv4 unicast all labels' 'show ip cef vrf A 10.100.2.0 255.255.255.0 detail' 'show ip cef vrf A 10.100.4.0 255.255.255.0 detail' 'show mpls forwarding-table vrf A'
  S "$X1" 'show route vrf A' 'show bgp vpnv4 unicast labels' 'show cef vrf A 10.100.1.0/24 detail' 'show mpls forwarding'
}

pw() {
  H "pw-1: VPWS(LDP の疑似回線・VLAN 130・pw-id 130)= XE1 ⇔ XR01。入れ物= xconnect・収容= service instance / l2transport"
  S "$E1" 'configure terminal' 'interface GigabitEthernet2' 'service instance 130 ethernet' 'encapsulation dot1q 130' 'rewrite ingress tag pop 1 symmetric' 'exit' 'exit' \
    'l2vpn xconnect context CE1-CE4' 'member GigabitEthernet2 service-instance 130' 'member 10.255.0.1 130 encapsulation mpls' 'end' \
    'show running-config | section interface GigabitEthernet2|xconnect'
  S "$X1" configure 'interface GigabitEthernet0/0/0/1.130 l2transport' 'encapsulation dot1q 130' 'rewrite ingress tag pop 1 symmetric' 'root' \
    'l2vpn' 'xconnect group SVC' 'p2p CE4-CE1' 'interface GigabitEthernet0/0/0/1.130' 'neighbor ipv4 10.255.0.41 pw-id 130' 'root' commit 'show configuration failed' end
  sleep 30
  S "$C1" 'ping 192.168.130.4 repeat 5'
  H "pw-2: PE が覚えたもの・ラベル"
  S "$E1" 'show l2vpn atom vc' 'show l2vpn atom vc vcid 130 detail' 'show mpls ldp neighbor 10.255.0.1' 'show mpls forwarding-table | include l2ckt|130'
  S "$X1" 'show l2vpn xconnect' 'show l2vpn xconnect detail' 'show mpls ldp neighbor 10.255.0.41 brief' 'show mpls forwarding | include PW|130'
  S "$C1" 'show ip bgp summary | include 172'   # VPWS は L3VPN の eBGP と同じ線(Gi の別 VLAN)で動く
}

ev() {
  H "ev-1: VPWS(EVPN・VLAN 140・EVI 140)= XE2 ⇔ XE3。入れ物= l2vpn evpn instance … point-to-point"
  for p in "$E2:2:3" "$E3:3:2"; do IFS=: read -r h s t <<<"$p"
    S "$h" 'configure terminal' 'l2vpn evpn' 'replication-type ingress' 'router-id Loopback0' 'exit' \
      'interface GigabitEthernet2' 'service instance 140 ethernet' 'encapsulation dot1q 140' 'rewrite ingress tag pop 1 symmetric' 'exit' 'exit' \
      'l2vpn evpn instance 140 point-to-point' "vpws context CE$s-CE$t" "service target $t source $s" 'member GigabitEthernet2 service-instance 140' 'end' \
      'show running-config | section l2vpn evpn'
  done
  sleep 40
  S "$C2" 'ping 192.168.140.3 repeat 5'
  H "ev-2: PE が覚えたもの・ラベル"
  S "$E2" 'show l2vpn evpn vpws vc id 140 detail' 'show bgp l2vpn evpn route-type 1' 'show mpls forwarding-table | include evpn|EVPN|140'
}

vp() {
  H "vp-1: VPLS(VLAN 210・VFI VPLS210・LDP の疑似回線を全 PE と)= XE1〜3。入れ物= VFI+ブリッジ ドメイン"
  for p in "$E1:10.255.0.42:10.255.0.43" "$E2:10.255.0.41:10.255.0.43" "$E3:10.255.0.41:10.255.0.42"; do IFS=: read -r h n1 n2 <<<"$p"
    S "$h" 'configure terminal' 'l2vpn vfi context VPLS210' 'vpn id 210' "member $n1 encapsulation mpls" "member $n2 encapsulation mpls" 'exit' \
      'interface GigabitEthernet2' 'service instance 210 ethernet' 'encapsulation dot1q 210' 'rewrite ingress tag pop 1 symmetric' 'exit' 'exit' \
      'bridge-domain 210' 'member GigabitEthernet2 service-instance 210' 'member vfi VPLS210' 'end'
  done
  sleep 30
  S "$C1" 'ping 192.168.210.2 repeat 5' 'ping 192.168.210.3 repeat 5'
  H "vp-2: PE が覚えたもの・ラベル"
  S "$E1" 'show l2vpn vfi' 'show l2vpn atom vc' 'show bridge-domain 210' 'show mpls forwarding-table | include l2ckt'
}

el() {
  H "el-1: EVPN の E-LAN(VLAN 200・EVI 200・vlan-based)= XE1〜3。入れ物= EVI+ブリッジ ドメイン"
  for p in $(XEG); do h=${p%%:*}
    S "$h" 'configure terminal' 'l2vpn evpn' 'replication-type ingress' 'router-id Loopback0' 'exit' \
      'l2vpn evpn instance 200 vlan-based' 'exit' \
      'interface GigabitEthernet2' 'service instance 200 ethernet' 'encapsulation dot1q 200' 'rewrite ingress tag pop 1 symmetric' 'exit' 'exit' \
      'bridge-domain 200' 'member GigabitEthernet2 service-instance 200' 'member evpn-instance 200' 'end'
  done
  sleep 40
  S "$C1" 'ping 192.168.200.2 repeat 5' 'ping 192.168.200.3 repeat 5'
  H "el-2: PE が覚えたもの・ラベル"
  S "$E1" 'show l2vpn evpn evi 200 detail' 'show bgp l2vpn evpn route-type 2' 'show bgp l2vpn evpn route-type 3' 'show l2vpn evpn mac' 'show bridge-domain 200' \
    'show mpls forwarding-table | include evpn|EVPN|200'
}

lbl() {
  H "lbl: 全体のラベル表(P1= 運ぶ層だけ・PE= サービスのラベルも)"
  S "$P1" 'show mpls forwarding-table'
  for h in $E1 $E2 $E3; do S "$h" 'show mpls forwarding-table'; done
  S "$X1" 'show mpls forwarding'
}

cap() {
  H "cap: 線の上のラベル(XE1→P1 の線= 2 枚・P1→XE2 の線= PHP で 1 枚)。サービスごとに 1 つずつ流す"
  local d=poc/xr/pcap; mkdir -p $d
  for svc in l3 vpls elan; do
    CAP XE1 P1 start mpls; CAP P1 XE2 start mpls; sleep 3
    case $svc in
      l3)   S "$C1" 'ping 10.100.2.1 source Loopback100 repeat 3' ;;
      vpls) S "$C1" 'ping 192.168.210.2 repeat 3' ;;
      elan) S "$C1" 'ping 192.168.200.2 repeat 3' ;;
    esac
    sleep 3; CAP XE1 P1 stop $d/$svc-xe1p1.pcap; CAP P1 XE2 stop $d/$svc-p1xe2.pcap
    DEC $d/$svc-xe1p1.pcap; DEC $d/$svc-p1xe2.pcap
  done
  CAP XE1 P1 start mpls; CAP P1 XR01 start mpls; sleep 3
  S "$C1" 'ping 192.168.130.4 repeat 3'
  sleep 3; CAP XE1 P1 stop $d/vpws-xe1p1.pcap; CAP P1 XR01 stop $d/vpws-p1xr01.pcap
  DEC $d/vpws-xe1p1.pcap; DEC $d/vpws-p1xr01.pcap
  CAP XE2 P1 start mpls; CAP P1 XE3 start mpls; sleep 3
  S "$C2" 'ping 192.168.140.3 repeat 3'
  sleep 3; CAP XE2 P1 stop $d/evpws-xe2p1.pcap; CAP P1 XE3 stop $d/evpws-p1xe3.pcap
  DEC $d/evpws-xe2p1.pcap; DEC $d/evpws-p1xe3.pcap
}

cfg() {
  H "cfg: 設定例の元(各 PE のサービスの部分)"
  for h in $E1 $E2 $E3; do
    S "$h" 'show running-config | section vrf definition|interface GigabitEthernet2|router bgp|l2vpn|bridge-domain'
  done
  S "$X1" 'show running-config vrf' 'show running-config interface GigabitEthernet0/0/0/1*' 'show running-config router bgp' 'show running-config l2vpn' 'show running-config route-policy'
}

ce() {
  H "ce: お客さまから見た網(CE1 の ARP と BGP)"
  S "$C1" 'show ip arp' 'show ip bgp | begin Network' 'show ip route bgp | begin Gateway'
  S "$E1" 'ping mpls ipv4 10.255.0.42/32 repeat 2' 'traceroute mpls ipv4 10.255.0.42/32' 'show mpls forwarding-table 10.255.0.42 32' \
    'show mpls ldp neighbor | include Peer|TCP|Targeted|Src' 'show bgp vpnv4 unicast all summary | begin Neighbor' 'show bgp l2vpn evpn summary | begin Neighbor'
}

rr() {
  H "rr: P1 は BGP を持たない・RR1 は経路を配るだけ(転送の道の外)"
  S "$P1" 'show running-config | include ^router' 'show ip bgp summary' 'show bgp vpnv4 unicast all summary' 'show mpls forwarding-table' 'show ip route summary'
  S "$R1" 'show running-config | include ^router|^mpls' 'show running-config | section router bgp' 'show bgp vpnv4 unicast all summary | begin Neighbor' 'show bgp l2vpn evpn summary | begin Neighbor' \
    'show bgp vpnv4 unicast all' 'show bgp vpnv4 unicast all 10.100.2.0/24' 'show mpls interfaces' 'show mpls ldp neighbor' 'show ip vrf'
  S "$E1" 'show bgp vpnv4 unicast all 10.100.2.0/24' 'show ip cef vrf A 10.100.2.0 255.255.255.0 detail' 'show mpls forwarding-table 10.255.0.52 32' 'traceroute 10.255.0.42 source Loopback0 probe 1 timeout 2'
}

fail() {
  H "f1: XE2 の VRF A の輸入 RT を 65000:101 に(輸出は 65000:100 のまま)"
  S "$E2" 'configure terminal' 'vrf definition A' 'address-family ipv4' 'no route-target import 65000:100' 'route-target import 65000:101' 'end' \
    'show ip route vrf A | begin Gateway' 'show bgp vpnv4 unicast all | begin Network' 'ping 10.100.1.1 source Loopback100 repeat 3'
  S "$C2" 'show ip bgp | begin Network' 'ping 10.100.1.1 source Loopback100 repeat 3'
  S "$E1" 'show ip route vrf A | begin Gateway'
  S "$E2" 'configure terminal' 'vrf definition A' 'address-family ipv4' 'no route-target import 65000:101' 'route-target import 65000:100' 'end'
  sleep 30
  S "$C2" 'ping 10.100.1.1 source Loopback100 repeat 3'
  H "f2: P1 の XR01 向きの IF から mpls ip を外す(XR01 への道にラベルが無くなる)"
  S "$P1" 'configure terminal' 'interface Ethernet1/0' 'no mpls ip' 'end'
  sleep 20
  S "$E1" 'show mpls forwarding-table 10.255.0.1 32' 'show ip cef vrf A 10.100.4.0 255.255.255.0 detail' 'show l2vpn atom vc' \
    'show l2vpn atom vc vcid 130 detail | include state|Status|status|label|Label'
  S "$C1" 'show ip bgp | begin Network' 'ping 10.100.4.1 source Loopback100 repeat 3' 'ping 192.168.130.4 repeat 3'
  S "$X1" 'show mpls forwarding prefix 10.255.0.41/32' 'show l2vpn xconnect' 'show route vrf A 10.100.1.0/24'
  S "$P1" 'configure terminal' 'interface Ethernet1/0' 'mpls ip' 'end'
  sleep 40
  S "$C1" 'ping 10.100.4.1 source Loopback100 repeat 3' 'ping 192.168.130.4 repeat 3'
}

for p in "$@"; do "$p"; done
