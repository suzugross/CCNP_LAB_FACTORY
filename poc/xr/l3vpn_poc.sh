#!/bin/bash
# BL-246 M9 L3VPN(SPCOR 4.3)の PoC。盤面= problems/_POC-XRL3VPN(XR01= PE・XR02= VPNv4 の RR 候補・どちらも XRd 26.1.1・他は IOL 17.15)。
# 記録= design §22。usage: source poc/xr/env.sh; poc/xr/l3vpn_poc.sh <phase…>   出力は標準出力(呼び出し側で poc/xr/l3vpn-<phase>.log へ)
#   phase は a から順に積む前提。管理 IP は topologies/_generated/$PID/mgmt_map.yml から引く。
cd "$(dirname "$0")/../.."
PID=${PID:-_POC-XRL3VPN}
M=topologies/_generated/$PID/mgmt_map.yml
ip() { awk -v n="$1:" '$1==n{print $2}' "$M"; }
XR=$(ip XR01) RR=$(ip XR02) R1=$(ip RT01) R2=$(ip RT02) R3=$(ip RT03)
A1=$(ip CEA1) A2=$(ip CEA2) B1=$(ip CEB1) B2=$(ip CEB2) SV=$(ip SVC) IN=$(ip INET)
S() { local h=$1; shift; .venv/bin/python poc/xr/xrsh.py "$h" "$@" 2>&1; }
X() { S "$XR" "$@"; }
Q() { S "$RR" "$@"; }
T() { .venv/bin/python poc/xr/tcpprobe.py "$@" 2>&1 | tail -3; }
H() { echo; echo "######## $(date +%T) $*"; }
G2=GigabitEthernet0/0/0/2 G3=GigabitEthernet0/0/0/3 G4=GigabitEthernet0/0/0/4 G5=GigabitEthernet0/0/0/5
CKS='show ip traffic | include checksum|format errors'

a() {
  H "a-1: 初期状態。XR01(M8 を解き終えた形)・XR02 が IS-IS に入っているか・RT02 の RR 向けセッション"
  X 'show version | include "Version|uptime"' 'show isis adjacency' 'show mpls ldp neighbor brief' 'show route 10.255.0.21/32' \
    'show bgp ipv4 unicast summary' "show running-config interface $G2" 'show vrf all'
  Q 'show isis adjacency' 'show route isis' 'show running-config router bgp'
  S "$R2" 'show ip bgp all summary' 'show ip route vrf CUST-A' 'show ip route 10.255.0.21'
  S "$A1" 'show ip bgp summary | begin Neighbor'
}

b() {
  H "b-1: VRF CUST-A を定義し、アドレスの付いた IF に vrf を足す(アドレスは残るか・コミットは通るか)"
  X configure 'vrf CUST-A' 'address-family ipv4 unicast' 'import route-target' '65000:101' '65000:900' 'exit' \
    'export route-target' '65000:101' 'root' "interface $G2" 'vrf CUST-A' 'show configuration' commit 'show configuration failed' end
  X "show running-config interface $G2" "show ipv4 vrf all interface brief" 'show route vrf CUST-A connected' 'ping vrf CUST-A 172.16.11.2 count 3'
  H "b-2: 付け直し(アドレスを消して付け直す=同じコミット)"
  X configure "interface $G2" 'no ipv4 address' 'ipv4 address 172.16.11.1 255.255.255.0' commit 'show configuration failed' end
  X "show running-config interface $G2" 'show route vrf CUST-A connected' 'ping vrf CUST-A 172.16.11.2 count 3'
  H "b-3: VPNv4 の近隣を、BGP 全体の address-family vpnv4 unicast なしで足す(コミットで止まるか)"
  X configure 'router bgp 65000' 'neighbor 10.255.0.21' 'remote-as 65000' 'update-source Loopback0' 'address-family vpnv4 unicast' \
    commit 'show configuration failed' abort
  H "b-4: BGP の VRF を RD なしで作り、CE と eBGP(RPL なし)"
  X configure 'router bgp 65000' 'vrf CUST-A' 'address-family ipv4 unicast' 'exit' \
    'neighbor 172.16.11.2' 'remote-as 65101' 'address-family ipv4 unicast' 'root' 'show configuration' commit 'show configuration failed' end
  sleep 30
  X 'show running-config router bgp' 'show bgp vrf CUST-A summary' 'show bgp vrf CUST-A' \
    'show bgp vrf CUST-A neighbors 172.16.11.2 | include "policy|accepted|Prefix|denied"'
  S "$A1" 'show ip bgp summary | begin Neighbor' 'show ip bgp'
}

c() {
  H "c-1: (確認) RD の無い BGP の VRF に AF を作る → コミットで拒否される(全体の vpnv4 AF も同じコミットなら一緒に戻る)"
  X configure 'router bgp 65000' 'address-family vpnv4 unicast' 'root' 'router bgp 65000' 'vrf CUST-T' 'address-family ipv4 unicast' \
    commit 'show configuration failed' abort
  H "c-2: 全体の vpnv4 AF + VRF(RD は付いている)の AF + CE と eBGP(RPL なし)"
  X configure 'router bgp 65000' 'address-family vpnv4 unicast' 'root' 'router bgp 65000' 'vrf CUST-A' 'rd 10.255.0.1:101' 'address-family ipv4 unicast' 'exit' \
    'neighbor 172.16.11.2' 'remote-as 65101' 'address-family ipv4 unicast' 'root' 'show configuration' commit 'show configuration failed' end
  sleep 30
  X 'show running-config router bgp' 'show bgp vrf CUST-A summary' 'show bgp vrf CUST-A' \
    'show bgp vrf CUST-A neighbors 172.16.11.2 | include "policy|accepted|Prefix|denied|Policy"'
  S "$A1" 'show ip bgp summary | begin Neighbor'
  H "c-3: RPL を付ける(PASS in/out)"
  X configure 'route-policy PASS' 'pass' 'end-policy' 'router bgp 65000' 'vrf CUST-A' 'neighbor 172.16.11.2' 'address-family ipv4 unicast' \
    'route-policy PASS in' 'route-policy PASS out' commit 'show configuration failed' end
  sleep 20
  X 'show bgp vrf CUST-A summary' 'show bgp vrf CUST-A' 'show route vrf CUST-A'
  H "c-4: VPNv4 の近隣(RR 候補 XR02・RR の設定はまだ無い)"
  X configure 'router bgp 65000' 'neighbor 10.255.0.21' 'remote-as 65000' 'update-source Loopback0' \
    'address-family vpnv4 unicast' commit 'show configuration failed' end
  Q configure 'router bgp 65000' 'bgp router-id 10.255.0.21' 'address-family vpnv4 unicast' 'exit' \
    'neighbor 10.255.0.1' 'remote-as 65000' 'update-source Loopback0' 'address-family vpnv4 unicast' 'root' \
    'router bgp 65000' 'neighbor 10.255.0.12' 'remote-as 65000' 'update-source Loopback0' 'address-family vpnv4 unicast' \
    commit 'show configuration failed' end
  sleep 40
  X 'show bgp vpnv4 unicast summary' 'show bgp vpnv4 unicast' 'show bgp vpnv4 unicast neighbors 10.255.0.21 advertised-count'
}

d() {
  H "d-1: XR02 は RR の設定なし(素の iBGP)。VRF を持たない XR が VPNv4 を受けた時に何が残るか"
  Q 'show bgp vpnv4 unicast summary' 'show bgp vpnv4 unicast' \
    'show bgp vpnv4 unicast neighbors 10.255.0.1 | include "accepted|Prefix|denied|Route refresh|retain"' \
    'show bgp vpnv4 unicast neighbors 10.255.0.12 | include "accepted|Prefix|denied"'
  S "$R2" 'show ip bgp vpnv4 all summary | begin Neighbor' 'show ip bgp vpnv4 all'
  H "d-2: XR02 に retain route-target all(RR クライアントなし)"
  Q configure 'router bgp 65000' 'address-family vpnv4 unicast' 'retain route-target all' commit 'show configuration failed' end
  sleep 20
  Q 'show bgp vpnv4 unicast' 'show bgp vpnv4 unicast summary'
  S "$R2" 'show ip bgp vpnv4 all'
  H "d-3: retain を外して、両 PE を route-reflector-client に(vpnv4 の AF の下)"
  Q configure 'router bgp 65000' 'address-family vpnv4 unicast' 'no retain route-target all' 'root' \
    'router bgp 65000' 'neighbor 10.255.0.1' 'address-family vpnv4 unicast' 'route-reflector-client' 'root' \
    'router bgp 65000' 'neighbor 10.255.0.12' 'address-family vpnv4 unicast' 'route-reflector-client' commit 'show configuration failed' end
  sleep 30
  Q 'show bgp vpnv4 unicast' 'show bgp vpnv4 unicast summary'
  S "$R2" 'show ip bgp vpnv4 all' 'show ip route vrf CUST-A bgp'
  X 'show bgp vpnv4 unicast' 'show bgp vrf CUST-A' 'show bgp vpnv4 unicast rd 10.255.0.12:102'
  H "d-4: as-override なし。CEA2(AS 65101)の経路を XR01 は CEA1(AS 65101)へ送るか"
  X 'show bgp vrf CUST-A neighbors 172.16.11.2 advertised-routes' 'show bgp vrf CUST-A 10.101.2.0/24'
  S "$A1" 'show ip bgp' 'show ip bgp neighbors 172.16.11.1 | include denied|loop|Prefixes'
  S "$A2" 'show ip bgp'
  H "d-5: XR01 に as-override"
  X configure 'router bgp 65000' 'vrf CUST-A' 'neighbor 172.16.11.2' 'address-family ipv4 unicast' 'as-override' commit 'show configuration failed' end
  sleep 20
  X 'show bgp vrf CUST-A neighbors 172.16.11.2 advertised-routes'
  S "$A1" 'show ip bgp' 'ping 10.101.2.1 source Loopback10 repeat 5'
  S "$A2" 'show ip bgp' 'ping 10.101.1.1 source Loopback10 repeat 5'
}

e() {
  H "e-1: XRd の PE を通る TCP/UDP。CEA2→CEA1(XR01 でラベルを外して CE へ)と CEA1→CEA2(XR01 でラベルを付ける)"
  S "$A1" "$CKS"; S "$A2" "$CKS"
  T "$A2" 10.101.1.1 Loopback10
  T "$A1" 10.101.2.1 Loopback10
  S "$A2" 'traceroute 10.101.1.1 source Loopback10 numeric timeout 1 probe 1 ttl 1 8'
  S "$A1" 'traceroute 10.101.2.1 source Loopback10 numeric timeout 1 probe 1 ttl 1 8'
  S "$A1" "$CKS"; S "$A2" "$CKS"
  H "e-2: XR01 自身の VRF の TCP(XR01 から CEA1 へ telnet 22 は無いので、CEA1→XR01 の VRF アドレスへ)"
  T "$A1" 172.16.11.1
}

f() {
  H "f-1: ラベルの割り当て方。既定(プレフィックスごと?)"
  X 'show bgp vrf CUST-A labels' 'show bgp vpnv4 unicast labels' 'show mpls forwarding'
  H "f-2: label mode per-vrf"
  X configure 'router bgp 65000' 'vrf CUST-A' 'address-family ipv4 unicast' 'label mode per-vrf' commit 'show configuration failed' end
  sleep 15
  X 'show bgp vrf CUST-A labels' 'show mpls forwarding'
  S "$R2" 'show ip bgp vpnv4 vrf CUST-A labels'
  S "$A2" 'ping 10.101.1.1 source Loopback10 repeat 5'
  H "f-3: 既定に戻す"
  X configure 'router bgp 65000' 'vrf CUST-A' 'address-family ipv4 unicast' 'no label mode' commit 'show configuration failed' end
  sleep 15
  X 'show bgp vrf CUST-A labels'
}

g() {
  H "g-1: お客さま B を XR01 に(VRF を後から足す= RT の取り込み先ができた時に RR から取り直すか)"
  X 'show bgp vpnv4 unicast rd 10.255.0.12:102'
  X configure 'vrf CUST-B' 'address-family ipv4 unicast' 'import route-target' '65000:102' '65000:900' 'exit' \
    'export route-target' '65000:102' 'root' "interface $G3" 'vrf CUST-B' 'ipv4 address 172.16.21.1 255.255.255.0' 'root' \
    'router bgp 65000' 'vrf CUST-B' 'rd 10.255.0.1:102' 'address-family ipv4 unicast' 'exit' 'neighbor 172.16.21.2' 'remote-as 65201' \
    'address-family ipv4 unicast' 'route-policy PASS in' 'route-policy PASS out' commit 'show configuration failed' end
  sleep 5
  X 'show bgp vpnv4 unicast rd 10.255.0.12:102' 'show bgp vpnv4 unicast neighbors 10.255.0.21 | include "refresh|Refresh"'
  sleep 30
  X 'show bgp vrf CUST-B' 'show route vrf CUST-B'
  S "$B1" 'show ip bgp' 'ping 10.102.2.1 source Loopback10 repeat 5' 'ping 10.101.1.1 source Loopback10 repeat 2'
}

h() {
  H "h-1: 共有サービス VRF SVC(PE-CE は静的)。10.99.1.0/24 だけ RT 65000:900 を足して配る(additive)"
  X configure "interface $G4" 'vrf SVC' 'ipv4 address 172.16.91.1 255.255.255.0' 'root' \
    'route-policy SVC-EXPORT' 'if destination in (10.99.1.0/24) then' 'set extcommunity rt (65000:900) additive' 'endif' 'pass' 'end-policy' \
    'vrf SVC' 'address-family ipv4 unicast' 'import route-target' '65000:101' '65000:102' 'exit' 'export route-target' '65000:999' 'exit' \
    'export route-policy SVC-EXPORT' 'root' \
    'router static' 'vrf SVC' 'address-family ipv4 unicast' '10.99.1.0/24 172.16.91.2' '10.99.2.0/24 172.16.91.2' 'root' \
    'router bgp 65000' 'vrf SVC' 'rd 10.255.0.1:900' 'address-family ipv4 unicast' 'redistribute static' \
    'show configuration' commit 'show configuration failed' end
  sleep 30
  X 'show bgp vrf SVC' 'show bgp vrf SVC 10.99.1.0/24' 'show bgp vrf SVC 10.99.2.0/24' 'show bgp vrf CUST-A' 'show bgp vrf CUST-B'
  S "$R2" 'show ip route vrf CUST-A bgp' 'show ip route vrf CUST-B bgp'
  S "$A1" 'show ip route bgp' 'ping 10.99.1.1 source Loopback10 repeat 5' 'ping 10.99.2.1 source Loopback10 repeat 2'
  S "$A2" 'ping 10.99.1.1 source Loopback10 repeat 5'
  S "$B2" 'ping 10.99.1.1 source Loopback10 repeat 5' 'ping 10.101.2.1 source Loopback10 repeat 2'
  H "h-2: additive なし(置き換え)にすると 10.99.1.0/24 の RT はどうなるか"
  X configure 'route-policy SVC-EXPORT' 'if destination in (10.99.1.0/24) then' 'set extcommunity rt (65000:900)' 'endif' 'pass' 'end-policy' \
    commit 'show configuration failed' end
  sleep 20
  X 'show bgp vrf SVC 10.99.1.0/24' 'show bgp vpnv4 unicast rd 10.255.0.1:900 10.99.1.0/24'
  H "h-3: 方針で落とした経路(pass しない)は輸出されないか= 10.99.2.0/24 を drop"
  X configure 'route-policy SVC-EXPORT' 'if destination in (10.99.1.0/24) then' 'set extcommunity rt (65000:900) additive' 'pass' 'endif' 'end-policy' \
    commit 'show configuration failed' end
  sleep 20
  X 'show bgp vrf SVC' 'show bgp vpnv4 unicast rd 10.255.0.1:900'
  S "$R2" 'show ip bgp vpnv4 all | include 10.99'
  H "h-4: 元に戻す(additive・pass)"
  X configure 'route-policy SVC-EXPORT' 'if destination in (10.99.1.0/24) then' 'set extcommunity rt (65000:900) additive' 'endif' 'pass' 'end-policy' \
    commit end
  H "h-5: 同じ PE の VRF どうし(CEA1 ⇔ SVC)を通る TCP(XR01 でラベルなしの通り抜け)"
  T "$A1" 10.99.1.1 Loopback10
  S "$SV" "$CKS"
}

i() {
  H "i-1: インターネット役とグローバルで eBGP"
  X configure "interface $G5" 'ipv4 address 192.0.2.1 255.255.255.0' 'root' \
    'route-policy INET-OUT' 'if destination in (198.51.100.0/24) then' 'pass' 'endif' 'end-policy' \
    'router bgp 65000' 'neighbor 192.0.2.2' 'remote-as 64500' 'address-family ipv4 unicast' 'route-policy PASS in' 'route-policy INET-OUT out' \
    commit 'show configuration failed' end
  sleep 30
  X 'show bgp ipv4 unicast summary' 'show route 0.0.0.0/0'
  H "i-2: CUST-A にグローバルの既定経路を取り込み(import from default-vrf)・198.51.100.0/24 をグローバルへ(export to default-vrf)"
  X configure 'route-policy FROM-GLOBAL' 'if destination in (0.0.0.0/0) then' 'pass' 'endif' 'end-policy' \
    'route-policy TO-GLOBAL' 'if destination in (198.51.100.0/24) then' 'pass' 'endif' 'end-policy' \
    'vrf CUST-A' 'address-family ipv4 unicast' 'import from default-vrf route-policy FROM-GLOBAL' \
    'export to default-vrf route-policy TO-GLOBAL' 'show configuration' commit 'show configuration failed' end
  sleep 30
  X 'show bgp vrf CUST-A 0.0.0.0/0' 'show route vrf CUST-A 0.0.0.0/0' 'show bgp ipv4 unicast 198.51.100.0/24' 'show route 198.51.100.0/24' \
    'show bgp ipv4 unicast neighbors 192.0.2.2 advertised-routes'
  S "$IN" 'show ip bgp'
  S "$A1" 'show ip route 0.0.0.0' 'ping 203.0.113.10 source Loopback11 repeat 5' 'ping 203.0.113.10 source Loopback10 repeat 2'
  S "$A2" 'show ip route 0.0.0.0'
  H "i-3: advertise-as-vpn(取り込んだ既定経路を VPNv4 でも配る)= CEA2 にも既定経路"
  X configure 'vrf CUST-A' 'address-family ipv4 unicast' 'import from default-vrf route-policy FROM-GLOBAL advertise-as-vpn' \
    commit 'show configuration failed' end
  sleep 30
  X 'show bgp vpnv4 unicast rd 10.255.0.1:101 0.0.0.0/0'
  S "$R2" 'show ip route vrf CUST-A 0.0.0.0'
  S "$A2" 'show ip route 0.0.0.0'
  H "i-4: インターネットへの TCP(XR01 でラベルなしの通り抜け・VRF→グローバル)"
  T "$A1" 203.0.113.10 Loopback11
  S "$IN" "$CKS"
}

j() {
  H "j-1: 静的経路での漏らし(CUST-B の既定経路の次ホップをグローバルに)。書き方が通るか"
  X configure 'router static' 'vrf CUST-B' 'address-family ipv4 unicast' '0.0.0.0/0 vrf default 192.0.2.2' \
    'show configuration' commit 'show configuration failed' end
  X 'show route vrf CUST-B 0.0.0.0/0' 'show running-config router static'
  X configure 'router static' 'vrf CUST-B' 'address-family ipv4 unicast' 'no 0.0.0.0/0' commit end
}

k() {
  H "k-1: 全体の VRF モードに rd があるか(新しい文書は vrf X / rd と書く)"
  X configure 'vrf CUST-A' 'rd ?' abort
  H "k-2: リモートの PE から来た経路(10.101.2.0/24)をグローバルへ出せるか= allow-imported-vpn の要否"
  X configure 'route-policy TO-GLOBAL' 'if destination in (198.51.100.0/24, 10.101.2.0/24) then' 'pass' 'endif' 'end-policy' commit end
  sleep 20
  X 'show bgp ipv4 unicast 10.101.2.0/24' 'show route 10.101.2.0/24'
  X configure 'vrf CUST-A' 'address-family ipv4 unicast' 'export to default-vrf route-policy TO-GLOBAL allow-imported-vpn' commit 'show configuration failed' end
  sleep 20
  X 'show bgp ipv4 unicast 10.101.2.0/24' 'show route 10.101.2.0/24'
  H "k-3: 元に戻す"
  X configure 'route-policy TO-GLOBAL' 'if destination in (198.51.100.0/24) then' 'pass' 'endif' 'end-policy' \
    'vrf CUST-A' 'address-family ipv4 unicast' 'export to default-vrf route-policy TO-GLOBAL' commit end
  H "k-4: 既存の VRF(CUST-B)に取り込み RT(65000:101)を足す= RR に取り直しを頼むか(送った回数の前後)"
  X 'show bgp vpnv4 unicast neighbors 10.255.0.21 | include "Route refresh request"'
  X configure 'vrf CUST-B' 'address-family ipv4 unicast' 'import route-target' '65000:101' commit end
  sleep 10
  X 'show bgp vpnv4 unicast neighbors 10.255.0.21 | include "Route refresh request"' 'show bgp vrf CUST-B | include "10.101"'
  X configure 'vrf CUST-B' 'address-family ipv4 unicast' 'import route-target' 'no 65000:101' commit end
  sleep 10
  X 'show bgp vrf CUST-B | include "10.101"'
  H "k-5: PE が取り込み先の無い RT の経路を捨てた数は見えるか(XR02 に CUST-T 用の経路= RT 65000:777 を流す代わりに、RT02 の CUST-B の RT を一時的に 65000:777 に)"
  S "$R2" 'configure terminal' 'vrf definition CUST-B' 'address-family ipv4' 'route-target export 65000:777' 'no route-target export 65000:102' 'end'
  sleep 20
  X 'show bgp vpnv4 unicast rd 10.255.0.12:102' 'show bgp vpnv4 unicast neighbors 10.255.0.21 | include "denied|Failed RT|accepted"'
  S "$R2" 'configure terminal' 'vrf definition CUST-B' 'address-family ipv4' 'route-target export 65000:102' 'no route-target export 65000:777' 'end'
  sleep 20
  X 'show bgp vrf CUST-B | include "10.102"'
}

l() {
  H "l-1: A の拠点 2 にも公開セグメント(198.51.100.128/25)。リモートの経路をインターネットへ出す= allow-imported-vpn・戻りは XR01 でラベルを付けて RT02 へ"
  S "$A2" 'configure terminal' 'interface Loopback11' 'description PUBLIC (Internet-facing)' 'ip address 198.51.100.129 255.255.255.128' 'exit' \
    'router bgp 65101' 'address-family ipv4' 'network 198.51.100.128 mask 255.255.255.128' 'end'
  X configure 'route-policy TO-GLOBAL' 'if destination in (198.51.100.0/24, 198.51.100.128/25) then' 'pass' 'endif' 'end-policy' \
    'route-policy INET-OUT' 'if destination in (198.51.100.0/24, 198.51.100.128/25) then' 'pass' 'endif' 'end-policy' \
    'vrf CUST-A' 'address-family ipv4 unicast' 'export to default-vrf route-policy TO-GLOBAL allow-imported-vpn' commit 'show configuration failed' end
  sleep 30
  X 'show bgp ipv4 unicast 198.51.100.128/25' 'show route 198.51.100.128/25' 'show cef 198.51.100.128/25 | include "via|label|Label"'
  S "$IN" 'show ip bgp' 'ping 198.51.100.129 source Loopback10 repeat 5'
  S "$A2" 'ping 203.0.113.10 source Loopback11 repeat 5' 'traceroute 203.0.113.10 source Loopback11 numeric timeout 1 probe 1 ttl 1 8'
  H "l-2: TCP(INET→CEA2= XR01 でラベルを付ける・CEA2→INET= XR01 でラベルを外してグローバルへ)"
  S "$A2" "$CKS"; S "$IN" "$CKS"
  T "$IN" 198.51.100.129 Loopback10
  T "$A2" 203.0.113.10 Loopback11
  S "$A2" "$CKS"; S "$IN" "$CKS"
}

for p in "$@"; do "$p"; done
