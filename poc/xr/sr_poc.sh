#!/bin/bash
# BL-246 M10 セグメントルーティング(SPCOR 3.3)の PoC。盤面= problems/_POC-XRSR(XRT-09 の写し。XR01= XRv9000 26.1.1・XR02= XRd 26.1.1・他は IOL 17.15)。
# 記録= design §23。usage: source poc/xr/env.sh; poc/xr/sr_poc.sh <phase…>   出力は標準出力(呼び出し側で poc/xr/sr-<phase>.log へ)
#   前提= 構築後に `PID=_POC-XRSR poc/xr/solve_xrt09.sh` で M9 を解き終えた状態。phase は a から順に積む。
#   SID の約束(PoC)= SRGB 16000-23999・index は Lo0 の末尾(XR01=1・RT01=11・RT02=12・RT03=13・XR02=21)。
cd "$(dirname "$0")/../.."
PID=${PID:-_POC-XRSR}
M=topologies/_generated/$PID/mgmt_map.yml
ip() { awk -v n="$1:" '$1==n{print $2}' "$M"; }
XR=$(ip XR01) RR=$(ip XR02) R1=$(ip RT01) R2=$(ip RT02) R3=$(ip RT03)
A1=$(ip CEA1) A2=$(ip CEA2) B1=$(ip CEB1) B2=$(ip CEB2)
S() { local h=$1; shift; .venv/bin/python poc/xr/xrsh.py "$h" "$@" 2>&1; }
X() { S "$XR" "$@"; }
Q() { S "$RR" "$@"; }
H() { echo; echo "######## $(date +%T) $*"; }
SLA() { .venv/bin/python poc/xr/sla_loss.py "$PID" CEA1 10.101.2.1 10.101.1.1 "$@" 2>&1; }
G0=GigabitEthernet0/0/0/0 G1=GigabitEthernet0/0/0/1
VPN='ping 10.101.2.1 source 10.101.1.1 repeat 20'
XCEF() { X 'show cef 10.255.0.12/32 detail' 'show cef vrf CUST-A 10.101.2.0/24 detail' 'show mpls forwarding prefix 10.255.0.12/32'; }
ISDB() { X 'show isis database verbose | include "^[A-Z0-9]|Prefix-SID|Router Cap|SRGB|SRLB|Segment|Metric: [0-9]+ +IS-Extended|ADJ-SID|Adjacency SID"'; }

a() {
  H "a-1: 出発点(M9 を解き終えた形)。LDP の上で L3VPN が通っているか"
  X 'show version | include "Version|uptime"' 'show isis adjacency' 'show mpls ldp neighbor brief' 'show bgp vpnv4 unicast summary'
  XCEF
  S "$A1" "$VPN"
  H "a-2: IOL の版と SR のコマンドの有無(? で見る)"
  S "$R1" 'show version | include IOS|Version' 'show running-config | section segment' \
    'configure terminal' 'segment-routing ?' 'segment-routing mpls' '?' 'end'
  S "$R1" 'configure terminal' 'router isis CORE' 'segment-routing ?' 'fast-reroute ?' 'flex-algo ?' 'microloop ?' 'distribute ?' 'end'
}

b() {
  H "b-1: IOL(RT01〜RT03)に SR を入れる(connected-prefix-sid-map・IS-IS の segment-routing mpls)。LDP は残す"
  for n in 1 2 3; do
    h=$(ip RT0$n)
    S "$h" 'configure terminal' 'segment-routing mpls' 'connected-prefix-sid-map' 'address-family ipv4' \
      "10.255.0.1$n/32 index 1$n range 1" 'exit-address-family' 'exit' 'exit' 'router isis CORE' 'segment-routing mpls' 'end'
  done
  sleep 15
  S "$R1" 'show segment-routing mpls state' 'show segment-routing mpls gb' 'show segment-routing mpls connected-prefix-sid-map ipv4' \
    'show isis segment-routing prefix-sid-map' 'show mpls forwarding-table | include SR|Pfx|160' 'show isis database verbose RT02.00-00'
  S "$R2" 'show mpls forwarding-table 10.255.0.11 32 detail' 'show ip cef 10.255.0.11 detail'
  H "b-2: XR01 から見た IOL の SID(XR01 はまだ SR なし)"
  ISDB
  X 'show isis segment-routing label table' 'show mpls forwarding | include "160[0-9][0-9]"'
}

c() {
  H "c-1: XR01 の Lo0 に prefix-sid index 1 を書く(IS-IS の AF に segment-routing mpls はまだ無い)。コミットは通るか・広告されるか"
  X configure 'router isis CORE' 'interface Loopback0' 'address-family ipv4 unicast' 'prefix-sid index 1' 'show configuration' commit 'show configuration failed' end
  sleep 15
  X 'show isis database verbose XR01.00-00' 'show isis segment-routing label table' 'show mpls forwarding | include "160[0-9][0-9]"'
  S "$R1" 'show mpls forwarding-table 10.255.0.1 32'
  H "c-2: IS-IS の AF に segment-routing mpls を足す"
  X configure 'router isis CORE' 'address-family ipv4 unicast' 'segment-routing mpls' commit 'show configuration failed' end
  sleep 20
  X 'show isis database verbose XR01.00-00' 'show isis segment-routing label table' 'show mpls forwarding | include "160[0-9][0-9]|Local"'
  H "c-3: 既定ではどちらのラベルを積むか(XR01 は LDP と SR の両方を持つ)"
  XCEF
  S "$R2" 'show mpls forwarding-table 10.255.0.1 32 detail' 'show ip cef 10.255.0.1 detail' 'show ip cef vrf CUST-A 10.101.1.0 detail'
  S "$R1" 'show mpls forwarding-table 10.255.0.1 32' 'show mpls forwarding-table labels 16001' 'show mpls forwarding-table labels 16012'
  H "c-4: XR01 に sr-prefer"
  X configure 'router isis CORE' 'address-family ipv4 unicast' 'segment-routing mpls sr-prefer' commit 'show configuration failed' end
  sleep 10
  XCEF
  S "$A1" "$VPN"
  H "c-5: IOL に SR 優先(sr-label-preferred を試す)"
  for n in 1 2 3; do
    S "$(ip RT0$n)" 'configure terminal' 'segment-routing mpls' 'set-attributes' 'address-family ipv4' 'sr-label-preferred' 'exit-address-family' 'end' \
      'show running-config | section segment-routing'
  done
  sleep 10
  S "$R2" 'show ip cef 10.255.0.1 detail' 'show ip cef vrf CUST-A 10.101.1.0 detail' 'show mpls forwarding-table 10.255.0.1 32'
  S "$A1" "$VPN"
}

c6() {
  H "c-6: XR01 の LDP を止める(IS-IS の mpls ldp sync は残したまま)。相手の同期・メトリック・L3VPN"
  X configure 'no mpls ldp' commit 'show configuration failed' end
  sleep 30
  X 'show isis interface brief' 'show isis mpls ldp sync' 'show running-config router isis' 'show isis adjacency'
  ISDB
  S "$R1" 'show mpls ldp igp sync' 'show isis database verbose RT01.00-00 | include Metric|IS-Extended'
  S "$R3" 'show mpls ldp igp sync'
  XCEF
  S "$R2" 'show ip cef vrf CUST-A 10.101.1.0 detail' 'show ip route 10.255.0.1'
  S "$A1" "$VPN" 'traceroute 10.101.2.1 source 10.101.1.1 numeric timeout 1 probe 1'
  H "c-7: XR01 の IS-IS から mpls ldp sync を消す"
  X configure 'router isis CORE' "interface $G0" 'address-family ipv4 unicast' 'no mpls ldp sync' 'root' \
    'router isis CORE' "interface $G1" 'address-family ipv4 unicast' 'no mpls ldp sync' commit 'show configuration failed' end
  sleep 15
  ISDB
  S "$A1" "$VPN"
}

d() {
  H "d-1: SRGB の既定と表示"
  X 'show isis database verbose XR01.00-00 | include "SRGB|SRLB|Router Cap"' 'show mpls label table summary' 'show mpls lsd applications' \
    'show running-config segment-routing' 'show segment-routing local-block inconsistencies'
  H "d-2: XR01 の SRGB を狭める(16000-16009= 相手の index 11〜13 は範囲外)。コミット・反映・転送"
  X configure 'segment-routing' 'global-block 16000 16009' commit 'show configuration failed' end
  sleep 20
  X 'show logging last 30' 'show isis database verbose XR01.00-00 | include "SRGB|SRLB|Router Cap"' 'show isis segment-routing label table' \
    'show mpls forwarding | include "160[0-9][0-9]"'
  XCEF
  S "$R1" 'show mpls forwarding-table 10.255.0.1 32' 'show isis database verbose XR01.00-00 | include SRGB|Router CAP|Segment'
  S "$A1" "$VPN"
  H "d-3: SRGB を戻す(global-block を消す)"
  X configure 'segment-routing' 'no global-block' commit 'show configuration failed' end
  sleep 20
  X 'show logging last 15' 'show isis database verbose XR01.00-00 | include "SRGB|Router Cap"' 'show isis segment-routing label table'
  XCEF
  S "$A1" "$VPN"
}

d4() {
  H "d-4: SID の衝突(RT03 の Lo0 に RT02 と同じ index 12)"
  S "$R3" 'configure terminal' 'segment-routing mpls' 'connected-prefix-sid-map' 'address-family ipv4' 'no 10.255.0.13/32' \
    '10.255.0.13/32 index 12 range 1' 'end'
  sleep 20
  X 'show isis segment-routing label table' 'show mpls forwarding labels 16012' 'show cef 10.255.0.12/32 detail' 'show cef 10.255.0.13/32 detail' \
    'show logging last 20' 'show isis segment-routing prefix-sid-map active-policy'
  S "$R1" 'show mpls forwarding-table labels 16012 detail' 'show segment-routing mpls connected-prefix-sid-map ipv4'
  S "$A1" "$VPN"
  H "d-5: 戻す(RT03= index 13)"
  S "$R3" 'configure terminal' 'segment-routing mpls' 'connected-prefix-sid-map' 'address-family ipv4' 'no 10.255.0.13/32' \
    '10.255.0.13/32 index 13 range 1' 'end'
  H "d-6: XR01 の index を相手の SRGB の外(index 9000)に"
  X configure 'router isis CORE' 'interface Loopback0' 'address-family ipv4 unicast' 'prefix-sid index 9000' commit 'show configuration failed' end
  sleep 20
  X 'show isis segment-routing label table' 'show logging last 10'
  S "$R1" 'show mpls forwarding-table 10.255.0.1 32 detail' 'show logging | include SR|SID'
  S "$R2" 'show ip cef 10.255.0.1 detail'
  S "$A1" "$VPN"
  X configure 'router isis CORE' 'interface Loopback0' 'address-family ipv4 unicast' 'prefix-sid index 1' commit end
}

e() {
  H "e-0: BFD(XR01⇔RT01・XR01⇔RT03= 100 ms × 3)と CEA2 の SLA の応答役"
  X configure 'router isis CORE' "interface $G0" 'bfd fast-detect ipv4' 'bfd minimum-interval 100' 'bfd multiplier 3' 'root' \
    'router isis CORE' "interface $G1" 'bfd fast-detect ipv4' 'bfd minimum-interval 100' 'bfd multiplier 3' commit 'show configuration failed' end
  S "$R1" 'configure terminal' 'interface Ethernet0/0' 'bfd interval 100 min_rx 100 multiplier 3' 'isis bfd' 'end'
  S "$R3" 'configure terminal' 'interface Ethernet0/0' 'bfd interval 100 min_rx 100 multiplier 3' 'isis bfd' 'end'
  S "$A2" 'configure terminal' 'ip sla responder' 'end'
  sleep 20
  X 'show bfd session' 'show isis fast-reroute summary'
  H "e-1: 基準(故障なし)"
  SLA --packets 500
  H "e-2: TI-LFA なし・BFD あり。XR01–RT01 にリンク条件 loss 100"
  SLA --fail XR01:RT01 --at 3
  sleep 40
  X 'show isis adjacency' 'show bfd session'
}

e3() {
  H "e-3: XR01 に TI-LFA(両方のコアの IF)"
  X configure 'router isis CORE' "interface $G0" 'address-family ipv4 unicast' 'fast-reroute per-prefix' 'fast-reroute per-prefix ti-lfa' 'root' \
    'router isis CORE' "interface $G1" 'address-family ipv4 unicast' 'fast-reroute per-prefix' 'fast-reroute per-prefix ti-lfa' commit 'show configuration failed' end
  sleep 20
  X 'show isis fast-reroute summary' 'show isis fast-reroute 10.255.0.11/32 detail' 'show isis fast-reroute 10.255.0.12/32 detail' \
    'show isis fast-reroute 10.255.0.13/32 detail' 'show cef 10.255.0.11/32 detail' 'show cef 10.255.0.12/32 detail' \
    'show cef vrf CUST-A 10.101.2.0/24 detail' 'show mpls forwarding prefix 10.255.0.11/32 detail'
  H "e-4: TI-LFA あり(XR01 だけ)・BFD あり。同じ故障"
  SLA --fail XR01:RT01 --at 3
  sleep 40
  X 'show isis adjacency'
}

e5() {
  H "e-5: IOL(RT01)にも TI-LFA(帰りの向きの PLR)"
  S "$R1" 'configure terminal' 'router isis CORE' 'fast-reroute per-prefix level-2 all' 'fast-reroute ti-lfa level-2' 'end' \
    'show running-config | section router isis'
  sleep 20
  S "$R1" 'show isis fast-reroute summary' 'show isis fast-reroute ti-lfa tunnel' 'show ip cef 10.255.0.1 detail' 'show isis rib 10.255.0.1 255.255.255.255'
  H "e-6: 両方に TI-LFA・BFD あり。同じ故障"
  SLA --fail XR01:RT01 --at 3
  sleep 40
  H "e-7: メトリックを変えて adj-SID の要る修復(XR01–RT03 を両側 10・RT03–RT02 は 100 のまま)"
  X configure 'router isis CORE' "interface $G1" 'address-family ipv4 unicast' 'metric 10' commit end
  S "$R3" 'configure terminal' 'interface Ethernet0/0' 'isis metric 10' 'end'
  sleep 20
  X 'show isis fast-reroute 10.255.0.11/32 detail' 'show isis fast-reroute 10.255.0.12/32 detail' 'show cef 10.255.0.11/32 detail'
  S "$R3" 'show isis segment-routing adjacency-sid' 'show mpls forwarding-table | include Adj|SR'
  SLA --fail XR01:RT01 --at 3
  sleep 40
  H "e-8: メトリックを戻す"
  X configure 'router isis CORE' "interface $G1" 'address-family ipv4 unicast' 'metric 100' commit end
  S "$R3" 'configure terminal' 'interface Ethernet0/0' 'isis metric 100' 'end'
}

f() {
  H "f-1: microloop avoidance(XR01)"
  X configure 'router isis CORE' 'address-family ipv4 unicast' 'microloop avoidance segment-routing' 'microloop avoidance rib-update-delay 3000' \
    commit 'show configuration failed' end 'show running-config router isis CORE address-family ipv4 unicast' 'show isis protocol'
}

g() {
  H "g-1: SR-TE の明示経路ポリシー(RT03 経由・色 100)"
  X configure 'segment-routing' 'traffic-eng' 'segment-list VIA-RT03' 'index 10 mpls label 16013' 'index 20 mpls label 16012' 'exit' \
    'policy CUST-A-VIA-RT03' 'color 100 end-point ipv4 10.255.0.12' 'candidate-paths' 'preference 100' 'explicit segment-list VIA-RT03' \
    commit 'show configuration failed' end
  sleep 10
  X 'show segment-routing traffic-eng policy color 100' 'show segment-routing traffic-eng policy color 100 detail'
  H "g-2: VPNv4 の受け入れで CUST-A の経路に色 100(automated steering)"
  X configure 'extcommunity-set opaque COLOR-100' '100' 'end-set' 'extcommunity-set rt RT-CUST-A' '65000:101' 'end-set' \
    'route-policy COLOR-CUST-A' 'if extcommunity rt matches-any RT-CUST-A then' 'set extcommunity color COLOR-100' 'endif' 'pass' 'end-policy' \
    'router bgp 65000' 'neighbor 10.255.0.21' 'address-family vpnv4 unicast' 'route-policy COLOR-CUST-A in' commit 'show configuration failed' end
  sleep 20
  X 'show bgp vrf CUST-A 10.101.2.0/24' 'show cef vrf CUST-A 10.101.2.0/24 detail' 'show cef vrf CUST-B 10.102.2.0/24 detail' \
    'show bgp vrf CUST-B 10.102.2.0/24'
  S "$A1" "$VPN" 'traceroute 10.101.2.1 source 10.101.1.1 numeric timeout 1 probe 1'
  S "$B1" 'traceroute 10.102.2.1 source 10.102.1.1 numeric timeout 1 probe 1'
  H "g-3: 明示経路を消して ODN(色 100 が来たら自動で作る・自分の IF に色)"
  X configure 'segment-routing' 'traffic-eng' 'no policy CUST-A-VIA-RT03' 'affinity-map' 'name AVOID bit-position 0' 'exit' \
    "interface $G0" 'affinity' 'name AVOID' 'root' 'segment-routing' 'traffic-eng' 'on-demand color 100' 'dynamic' 'metric' 'type igp' 'exit' \
    'affinity' 'exclude-any' 'name AVOID' commit 'show configuration failed' end
  sleep 15
  X 'show segment-routing traffic-eng policy color 100 detail' 'show cef vrf CUST-A 10.101.2.0/24 detail' 'show logging last 15'
  H "g-4: IS-IS の distribute link-state を足して計算させる(要るか)"
  X configure 'router isis CORE' 'distribute link-state' commit 'show configuration failed' end
  sleep 15
  X 'show segment-routing traffic-eng policy color 100 detail' 'show segment-routing traffic-eng topology summary' 'show cef vrf CUST-A 10.101.2.0/24 detail'
  S "$A1" 'traceroute 10.101.2.1 source 10.101.1.1 numeric timeout 1 probe 1'
}

h() {
  H "h-1: XR02(XRd)を PCE に(IS-IS の LSDB を distribute link-state で渡す)・過負荷ビット"
  Q configure 'pce' 'address ipv4 10.255.0.21' 'root' 'router isis CORE' 'distribute link-state' 'set-overload-bit' commit 'show configuration failed' end
  H "h-2: XR01 を PCC に"
  X configure 'segment-routing' 'traffic-eng' 'pcc' 'source-address ipv4 10.255.0.1' 'pce address ipv4 10.255.0.21' commit 'show configuration failed' end
  sleep 20
  Q 'show pce ipv4 peer' 'show pce ipv4 topology summary' 'show pce ipv4 prefix'
  X 'show segment-routing traffic-eng pcc ipv4 peer'
  H "h-3: PCE に計算させるポリシー 2 本(色 201・202)をリンクで離す"
  X configure 'segment-routing' 'traffic-eng' \
    'policy DISJ-1' 'color 201 end-point ipv4 10.255.0.12' 'candidate-paths' 'preference 100' 'dynamic' 'pcep' 'exit' 'metric' 'type igp' 'exit' 'exit' \
    'constraints' 'disjoint-path group-id 1 type link' 'root' 'segment-routing' 'traffic-eng' \
    'policy DISJ-2' 'color 202 end-point ipv4 10.255.0.12' 'candidate-paths' 'preference 100' 'dynamic' 'pcep' 'exit' 'metric' 'type igp' 'exit' 'exit' \
    'constraints' 'disjoint-path group-id 1 type link' commit 'show configuration failed' end
  sleep 20
  X 'show segment-routing traffic-eng policy color 201 detail' 'show segment-routing traffic-eng policy color 202 detail' 'show running-config segment-routing'
  Q 'show pce lsp detail' 'show pce association'
}

i() {
  H "i-1: Flex-Algo(XR01 と IOL で設定が通るか)"
  X configure 'router isis CORE' 'flex-algo 128' 'metric-type delay' 'advertise-definition' 'root' \
    'router isis CORE' 'interface Loopback0' 'address-family ipv4 unicast' 'prefix-sid algorithm 128 index 101' commit 'show configuration failed' end
  sleep 10
  X 'show isis flex-algo 128' 'show isis database verbose XR01.00-00 | include "Flex|Algo|Prefix-SID"'
  S "$R1" 'configure terminal' 'router isis CORE' 'flex-algo 128' 'end' 'show running-config | section flex'
}

for p in "$@"; do "$p"; done
