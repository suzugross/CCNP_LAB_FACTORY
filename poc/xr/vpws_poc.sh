#!/bin/bash
# BL-261 PoC= EVPN-VPWS は LDP の疑似回線より何が嬉しいか。盤面= problems/_POC-XRVPWS(design §26.11)
#   ①マルチホーム: SW1(拠点 4)を XE1・XE2 に束で二重に収容し、拠点 3(XE3・CE3)と E-Line でつなぐ(EVPN-VPWS= VLAN 150・LDP= VLAN 160)
#   ②道を SR にして LDP を外したとき、どちらが LDP を必要とするか ③相手の PE の住所を書くか
# usage: source poc/xr/env.sh; poc/xr/vpws_poc.sh <phase…>   出力は標準出力(呼び出し側で poc/xr/expVPWS-<phase>.log へ)
cd "$(dirname "$0")/../.."
PID=${PID:-_POC-XRVPWS}
M=topologies/_generated/$PID/mgmt_map.yml
ip() { awk -v n="$1:" '$1==n{print $2}' "$M"; }
E1=$(ip XE1) E2=$(ip XE2) E3=$(ip XE3) P1=$(ip P1) R1=$(ip RR1) W1=$(ip SW1) C3=$(ip CE3)
S() { local h=$1; shift; .venv/bin/python poc/xr/xrsh.py "$h" "$@" 2>&1; }
H() { echo; echo "######## $(date +%T) $*"; }
# 途切れの長さを測る: SW1 から timeout 1 秒の ping を流し続け、その間に壊す(落ちた数 ≒ 途切れた秒数)。
# 返りが速いと数千発が数秒で終わるので、発数は rate の段で測った速さから決める(既定 N=20000)。記録= poc/xr/expVPWS-ping-<名前>.txt
N=${N:-20000}
PINGBG() { S "$W1" "ping $1 repeat $N timeout 1" > "poc/xr/expVPWS-ping-$2.txt" & }
PINGRES() { wait; local f="poc/xr/expVPWS-ping-$1.txt"; grep -E "Success rate" "$f" | tail -1
  grep -E '^[!.U]+$' "$f" | tr -d '\n' | python3 -c "import sys,re; s=sys.stdin.read(); r=[len(m) for m in re.findall(r'[.U]+', s)]; print('sent', len(s), 'lost', sum(r), 'runs', r[:20], 'longest', max(r or [0]))"; }

rate() {
  H "rate: ping の速さ(1000 発に何秒か)"
  local t0=$SECONDS; S "$W1" 'ping 172.31.150.3 repeat 3000 timeout 1' | grep Success; echo "elapsed $((SECONDS - t0)) s (3000 発)"
}

a() {
  H "a: 版・IS-IS・LDP・RR1・SW1 の束(まだ PE 側の束は無い)"
  for h in $E1 $E2 $E3; do S "$h" 'show version | include Version' 'show isis neighbors' 'show mpls ldp neighbor | include Peer'; done
  S "$P1" 'show isis neighbors' 'show mpls forwarding-table' 'show ip bgp summary'
  S "$R1" 'show isis neighbors' 'show bgp l2vpn evpn summary'
  S "$W1" 'show etherchannel summary' 'show vlan brief'
}

bgp() {
  H "bgp: PE から RR1 への iBGP(l2vpn evpn)と EVPN の全体設定"
  for n in 1 2 3; do h=$(ip XE$n)
    S "$h" 'configure terminal' 'router bgp 65000' "bgp router-id 10.255.0.4$n" 'bgp log-neighbor-changes' 'no bgp default ipv4-unicast' \
      'neighbor 10.255.0.52 remote-as 65000' 'neighbor 10.255.0.52 update-source Loopback0' \
      'address-family l2vpn evpn' 'neighbor 10.255.0.52 activate' 'neighbor 10.255.0.52 send-community both' 'exit-address-family' 'exit' \
      'l2vpn evpn' 'replication-type ingress' 'router-id Loopback0' 'end'
  done
  sleep 40
  S "$R1" 'show bgp l2vpn evpn summary'
}

mh() {
  H "mh-1: XE1・XE2= SW1 への束(Po1)を ES 4(all-active)にし、EVPN-VPWS(EVI 150・端 4)に入れる"
  for h in $E1 $E2; do
    S "$h" 'configure terminal' 'l2vpn evpn ethernet-segment 4' 'identifier type 0 00.00.00.00.00.00.00.04.01' 'redundancy all-active' 'exit' \
      'interface Port-channel1' 'description to SW1 (site 4)' 'no ip address' 'lacp device-id 0000.0000.0004' 'evpn ethernet-segment 4' \
      'service instance 150 ethernet' 'encapsulation dot1q 150' 'rewrite ingress tag pop 1 symmetric' 'exit' 'exit' \
      'interface GigabitEthernet3' 'channel-group 1 mode active' 'exit' \
      'l2vpn evpn instance 150 point-to-point' 'vpws context SITE4-SITE3' 'service target 3 source 4' 'member Port-channel1 service-instance 150' 'end' \
      'show running-config | section ethernet-segment|interface Port-channel1|instance 150'
  done
  H "mh-2: XE3= 拠点 3(Gi2)を EVPN-VPWS(EVI 150・端 3)に入れる"
  S "$E3" 'configure terminal' 'interface GigabitEthernet2' 'service instance 150 ethernet' 'encapsulation dot1q 150' 'rewrite ingress tag pop 1 symmetric' 'exit' 'exit' \
    'l2vpn evpn instance 150 point-to-point' 'vpws context SITE3-SITE4' 'service target 4 source 3' 'member GigabitEthernet2 service-instance 150' 'end' \
    'show running-config | section instance 150'
  sleep 60
  H "mh-3: 確かめる(束・ES・種類 1 と 4 の経路・VC・ping)"
  S "$W1" 'show etherchannel summary' 'ping 172.31.150.3 repeat 10'
  for h in $E1 $E2; do S "$h" 'show l2vpn evpn ethernet-segment detail' 'show l2vpn evpn vpws vc id 150 detail' 'show bgp l2vpn evpn route-type 4'; done
  S "$E3" 'show l2vpn evpn vpws vc id 150 detail' 'show bgp l2vpn evpn route-type 1' 'show l2vpn evpn vpws vc preferred-path' \
    'show mpls forwarding-table | include evpn|EVPN|150' 'show l2vpn evpn evi 150 detail'
}

mhf() {
  H "mhf-1: 切り替え= SW1 から CE3 へ ping を流しながら、XE1 の SW1 向きの線(Gi3)を落とす→戻す"
  PINGBG 172.31.150.3 mh1; sleep 15
  S "$E1" 'configure terminal' 'interface GigabitEthernet3' 'shutdown' 'end'
  sleep 30
  S "$E3" 'show l2vpn evpn vpws vc id 150 detail' 'show bgp l2vpn evpn route-type 1'
  PINGRES mh1
  S "$W1" 'show etherchannel summary'
  PINGBG 172.31.150.3 mh2; sleep 15
  S "$E1" 'configure terminal' 'interface GigabitEthernet3' 'no shutdown' 'end'
  sleep 60
  PINGRES mh2
  S "$E3" 'show l2vpn evpn vpws vc id 150 detail'
  S "$W1" 'show etherchannel summary'
  H "mhf-2: XE2 側も同じ(どちらの PE が落ちても通るか)"
  PINGBG 172.31.150.3 mh3; sleep 15
  S "$E2" 'configure terminal' 'interface GigabitEthernet3' 'shutdown' 'end'
  sleep 30
  PINGRES mh3
  S "$E2" 'configure terminal' 'interface GigabitEthernet3' 'no shutdown' 'end'
  sleep 60
  S "$W1" 'show etherchannel summary' 'ping 172.31.150.3 repeat 10'
}

mhf3() {
  H "mhf-3: XE3 がいま使っている PE(次の行き先)の線を落とす= 遠くの PE の切り替えを測る"
  local nh=$(S "$E3" 'show l2vpn evpn vpws vc id 150 detail' | awk '/Next Hop Address/{print $4}'); echo "XE3 の次の行き先= $nh"
  local h=$E1; [ "$nh" = 10.255.0.42 ] && h=$E2
  PINGBG 172.31.150.3 mh4; sleep 15
  S "$h" 'configure terminal' 'interface GigabitEthernet3' 'shutdown' 'end'
  sleep 5; S "$E3" 'show l2vpn evpn vpws vc id 150 detail' 'show bgp l2vpn evpn route-type 1'
  PINGRES mh4
  S "$h" 'configure terminal' 'interface GigabitEthernet3' 'no shutdown' 'end'
  sleep 60
  S "$E3" 'show l2vpn evpn vpws vc id 150 detail'
  S "$W1" 'show etherchannel summary' 'ping 172.31.150.3 repeat 10'
}

ldp() {
  H "ldp-1: LDP の疑似回線で同じ形を作る(VLAN 160)。XE1= PW 161・XE2= PW 162 で XE3 へ。XE3 は XE1 を主・XE2 を予備"
  for p in "$E1:161" "$E2:162"; do h=${p%%:*} id=${p##*:}
    S "$h" 'configure terminal' 'interface Port-channel1' 'service instance 160 ethernet' 'encapsulation dot1q 160' 'rewrite ingress tag pop 1 symmetric' 'exit' 'exit' \
      'l2vpn xconnect context SITE4-SITE3-LDP' 'member Port-channel1 service-instance 160' "member 10.255.0.43 $id encapsulation mpls" 'end'
  done
  S "$E3" 'configure terminal' 'interface GigabitEthernet2' 'service instance 160 ethernet' 'encapsulation dot1q 160' 'rewrite ingress tag pop 1 symmetric' 'exit' 'exit' \
    'l2vpn xconnect context SITE3-SITE4-LDP' 'member GigabitEthernet2 service-instance 160' \
    'member 10.255.0.41 161 encapsulation mpls group SITE4 priority 1' 'member 10.255.0.42 162 encapsulation mpls group SITE4 priority 2' 'end' \
    'show running-config | section xconnect'
  sleep 40
  H "ldp-2: 確かめる(主と予備・ping)"
  S "$E3" 'show l2vpn atom vc' 'show xconnect all' 'show mpls ldp neighbor | include Peer|Targeted'
  for h in $E1 $E2; do S "$h" 'show l2vpn atom vc'; done
  S "$W1" 'ping 172.31.160.3 repeat 10' 'show etherchannel summary'
  S "$W1" 'show interfaces Ethernet0/0 | include packets output' 'show interfaces Ethernet0/1 | include packets output'
  S "$W1" 'ping 172.31.160.3 repeat 20'
  S "$W1" 'show interfaces Ethernet0/0 | include packets output' 'show interfaces Ethernet0/1 | include packets output'
}

ldpf() {
  H "ldpf-1: 切り替え= SW1 から ping を流しながら XE1 の Gi3 を落とす→戻す(主の PW が落ちて予備へ)"
  PINGBG 172.31.160.3 ld1; sleep 15
  S "$E1" 'configure terminal' 'interface GigabitEthernet3' 'shutdown' 'end'
  sleep 30
  S "$E3" 'show l2vpn atom vc' 'show xconnect all'
  PINGRES ld1
  S "$E1" 'configure terminal' 'interface GigabitEthernet3' 'no shutdown' 'end'
  sleep 60
  S "$E3" 'show l2vpn atom vc'
  S "$W1" 'ping 172.31.160.3 repeat 10'
}

sr() {
  H "sr-1: 道を SR に(IS-IS の SR・ループバックに SID)= P1・XE1〜3。まだ LDP も残す"
  for p in "$P1:51" "$E1:41" "$E2:42" "$E3:43"; do h=${p%%:*} n=${p##*:}
    S "$h" 'configure terminal' 'segment-routing mpls' 'connected-prefix-sid-map' 'address-family ipv4' "10.255.0.$n/32 index $n range 1" 'exit-address-family' 'exit' 'exit' \
      'router isis CORE' 'segment-routing mpls' 'end' 'show segment-routing mpls connected-prefix-sid-map ipv4'
  done
  sleep 30
  S "$E3" 'show isis segment-routing prefix-sid-map active-policy' 'show mpls forwarding-table labels 16000 23999' 'show mpls forwarding-table 10.255.0.41 32 detail'
  H "sr-2: コアのリンクから LDP を外す(P1 の全 IF・XE1〜3 の Gi1)"
  S "$P1" 'configure terminal' 'interface Ethernet0/0' 'no mpls ip' 'interface Ethernet0/1' 'no mpls ip' 'interface Ethernet0/2' 'no mpls ip' 'end'
  for h in $E1 $E2 $E3; do S "$h" 'configure terminal' 'interface GigabitEthernet1' 'no mpls ip' 'end'; done
  sleep 40
  H "sr-3: 確かめる= 道は SR のラベル。LDP は疑似回線のための targeted だけが残る。EVPN-VPWS は LDP なし"
  S "$P1" 'show mpls ldp neighbor' 'show mpls forwarding-table'
  S "$E3" 'show mpls ldp neighbor | include Peer|Targeted|Src' 'show mpls forwarding-table 10.255.0.41 32' 'show l2vpn atom vc' 'show l2vpn evpn vpws vc id 150 detail'
  S "$W1" 'ping 172.31.150.3 repeat 10' 'ping 172.31.160.3 repeat 10'
  H "sr-4: 疑似回線を消すと、XE3 の LDP は何も残らない(EVPN-VPWS はそのまま)"
  S "$E3" 'configure terminal' 'no l2vpn xconnect context SITE3-SITE4-LDP' 'end'
  sleep 20
  S "$E3" 'show mpls ldp neighbor' 'show l2vpn evpn vpws vc id 150 detail'
  S "$W1" 'ping 172.31.150.3 repeat 10'
}

cfg() {
  H "cfg: 設定例の元"
  for h in $E1 $E2 $E3; do S "$h" 'show running-config | section l2vpn|interface Port-channel1|interface GigabitEthernet2|interface GigabitEthernet3|router bgp|segment-routing'; done
  S "$P1" 'show running-config | section segment-routing|router isis'
}

for p in "$@"; do "$p"; done
