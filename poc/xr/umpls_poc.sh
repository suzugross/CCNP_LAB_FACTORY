#!/bin/bash
# BL-246 M8 追補(Unified MPLS・SPCOR 3.1.d)の PoC。盤面= problems/_POC-XRUMPLS(XR01= XRd 26.1.1・RT01〜RT05= IOL 17.15)。記録= design §21。
# usage: source poc/xr/env.sh; poc/xr/umpls_poc.sh <phase…>   出力は標準出力(呼び出し側で poc/xr/umpls-<phase>.log へ)
#   管理 IP は topologies/_generated/$PID/mgmt_map.yml から引く。phase は a から順に積む前提。
cd "$(dirname "$0")/../.."
PID=${PID:-_POC-XRUMPLS}
M=topologies/_generated/$PID/mgmt_map.yml
ip() { awk -v n="$1:" '$1==n{print $2}' "$M"; }
XR=$(ip XR01) R1=$(ip RT01) R2=$(ip RT02) R3=$(ip RT03) R4=$(ip RT04) R5=$(ip RT05)
X() { .venv/bin/python poc/xr/xrsh.py "$XR" "$@" 2>&1; }
R() { local h=$1; shift; .venv/bin/python poc/xr/xrsh.py "$h" "$@" 2>&1; }
H() { echo; echo "######## $(date +%T) $*"; }
G0=GigabitEthernet0/0/0/0 G1=GigabitEthernet0/0/0/1 G2=GigabitEthernet0/0/0/2

a() {
  H "a-1: XR01 の初期状態(M8 を解き終えた形)。コアの隣接・LDP・BGP・お客さま A の疎通"
  X 'show version | include "Version|uptime"' 'show isis adjacency' 'show mpls ldp neighbor brief' 'show mpls ldp igp sync' \
    'show bgp ipv4 unicast summary' 'show bgp ipv4 unicast' 'ping 10.20.0.1 source Loopback100 count 5'
  H "a-2: アクセス側(XR01 はまだ参加していない)"
  R "$R4" 'show isis neighbors' 'show ip route' 'show mpls ldp neighbor | include Peer|State'
  R "$R5" 'show ip route' 'show mpls forwarding-table'
  R "$R2" 'show ip route 10.255.0.15' 'show ip bgp'
}

b() {
  H "b-1: XR01 にアクセスの IGP を 2 つめの IS-IS インスタンスで。Lo0 を CORE と ACCESS の両方に載せられるか"
  X configure 'router isis ACCESS' 'is-type level-2-only' 'net 49.0002.0100.0000.0001.00' 'log adjacency changes' \
    'address-family ipv4 unicast' 'metric-style wide' 'exit' \
    'interface Loopback0' 'passive' 'address-family ipv4 unicast' 'root' \
    'router isis ACCESS' "interface $G2" 'point-to-point' 'address-family ipv4 unicast' 'root' \
    'show configuration' commit 'show configuration failed' end
  sleep 30
  X 'show running-config router isis ACCESS' 'show isis instance ACCESS adjacency' 'show isis adjacency' \
    'show isis instance CORE interface Loopback0 | include "Loopback0|Enabled|Disabled|Adjacency"' \
    'show isis instance ACCESS interface Loopback0 | include "Loopback0|Enabled|Disabled|Adjacency"' \
    'show route isis' 'show route 10.255.0.15/32'
  R "$R4" 'show isis neighbors' 'show ip route 10.255.0.1' 'show ip route 10.255.0.12'
  R "$R5" 'show ip route 10.255.0.1'
  R "$R1" 'show ip route 10.255.0.15'
}

c() {
  H "c-1: XR01 のアクセス側の IF で LDP。RT04 とのセッション・束縛(XR01 は host-routes だけ割り当てる)"
  X configure 'mpls ldp' "interface $G2" commit 'show configuration failed' end
  sleep 40
  X 'show mpls ldp neighbor brief' 'show mpls ldp bindings 10.255.0.15/32' 'show mpls forwarding' 'show mpls ldp igp sync'
  R "$R4" 'show mpls ldp neighbor | include Peer|State' 'show mpls ldp bindings 10.255.0.1 32' 'show mpls forwarding-table'
  R "$R5" 'show mpls forwarding-table' 'ping 10.255.0.1 source Loopback0 repeat 3' 'ping mpls ipv4 10.255.0.1/32 repeat 3'
}

BGPX='show bgp ipv4 labeled-unicast summary|show bgp ipv4 labeled-unicast|show bgp ipv4 labeled-unicast labels'
xbgp() { IFS='|' read -ra c <<< "$BGPX"; X "${c[@]}" "$@"; }

d1() {
  H "d-1: RT05 → XR01 に BGP ラベル付きユニキャスト(RT05 は Lo0 と お客さま B を network・send-label)。XR01 は LU の AF だけ(RR/NHS なし)"
  R "$R5" 'configure terminal' 'router bgp 65000' 'bgp router-id 10.255.0.15' 'bgp log-neighbor-changes' \
    'neighbor 10.255.0.1 remote-as 65000' 'neighbor 10.255.0.1 update-source Loopback0' 'address-family ipv4' \
    'network 10.255.0.15 mask 255.255.255.255' 'network 10.50.0.0 mask 255.255.0.0' \
    'neighbor 10.255.0.1 activate' 'neighbor 10.255.0.1 send-label' 'end'
  X configure 'router bgp 65000' 'neighbor 10.255.0.15' 'remote-as 65000' 'update-source Loopback0' \
    'address-family ipv4 labeled-unicast' commit 'show configuration failed' end
  sleep 45
  xbgp 'show bgp ipv4 unicast' 'show bgp ipv4 labeled-unicast 10.255.0.15/32' 'show bgp ipv4 unicast 10.50.0.0/16' \
    'show bgp neighbor 10.255.0.15 | include "family|abel|State|Prefix"' 'show route 10.50.0.0/16' 'show mpls forwarding'
  R "$R5" 'show ip bgp summary' 'show ip bgp' 'show ip bgp labels' \
    'show ip bgp neighbors 10.255.0.1 | include family|abel|BGP state|Prefixes'
}

d2() {
  H "d-2: RT02 にも send-label(XR01 との既存の ipv4 のセッション)。XR01 は 10.255.0.12 に LU の AF を足す(unicast の AF は残す)"
  R "$R2" 'configure terminal' 'router bgp 65000' 'address-family ipv4' 'network 10.255.0.12 mask 255.255.255.255' \
    'neighbor 10.255.0.1 send-label' 'end'
  X configure 'router bgp 65000' 'neighbor 10.255.0.12' 'address-family ipv4 labeled-unicast' commit 'show configuration failed' end
  sleep 50
  xbgp 'show bgp ipv4 unicast summary' 'show bgp ipv4 unicast' \
    'show bgp neighbor 10.255.0.12 | include "family|abel|State|Prefix|Last reset|reset"' 'show logging last 20'
  R "$R2" 'show ip bgp summary' 'show ip bgp' 'show ip bgp labels' \
    'show ip bgp neighbors 10.255.0.1 | include family|abel|BGP state|Prefixes|reset' 'ping 10.30.0.1 source Loopback100 repeat 5'
}

d3() {
  H "d-3: XR01 を両方の RR に。LU の AF に route-reflector-client と next-hop-self(enforce-modifications はまだ無し)"
  X configure 'router bgp 65000' 'neighbor 10.255.0.15' 'address-family ipv4 labeled-unicast' 'route-reflector-client' 'next-hop-self' \
    'root' 'router bgp 65000' 'neighbor 10.255.0.12' 'address-family ipv4 labeled-unicast' 'route-reflector-client' 'next-hop-self' \
    commit 'show configuration failed' end
  sleep 45
  xbgp 'show bgp ipv4 labeled-unicast 10.255.0.15/32' 'show bgp ipv4 labeled-unicast 10.255.0.12/32' \
    'show bgp ipv4 labeled-unicast neighbors 10.255.0.12 advertised-routes' 'show mpls forwarding'
  R "$R2" 'show ip bgp' 'show ip bgp labels' 'show ip bgp 10.255.0.15' 'show ip route 10.255.0.15' 'show ip cef 10.255.0.15 detail' \
    'show mpls forwarding-table'
  R "$R5" 'show ip bgp' 'show ip bgp labels' 'show ip route 10.255.0.12' 'show ip cef 10.255.0.12 detail'
}

d3b() {
  H "d-3b: ibgp policy out enforce-modifications を足す(反映する経路に next-hop-self を効かせる)"
  X configure 'router bgp 65000' 'ibgp policy out enforce-modifications' commit 'show configuration failed' end
  sleep 30
  xbgp 'show bgp ipv4 labeled-unicast neighbors 10.255.0.12 advertised-routes' 'show bgp ipv4 labeled-unicast 10.255.0.15/32' \
    'show mpls forwarding' 'show logging last 6'
  R "$R2" 'show ip bgp' 'show ip bgp labels' 'show ip route 10.255.0.15' 'show ip cef 10.255.0.15 detail' 'show mpls forwarding-table'
  R "$R5" 'show ip bgp' 'show ip bgp labels' 'show ip cef 10.255.0.12 detail'
}

d3c() {
  H "d-3c: address-family ipv4 unicast に allocate-label all(受け取った LU 経路・自分の network にローカル ラベルを割り当てる)"
  X configure 'router bgp 65000' 'address-family ipv4 unicast' 'allocate-label all' commit 'show configuration failed' end
  sleep 30
  xbgp 'show bgp ipv4 labeled-unicast neighbors 10.255.0.12 advertised-routes' 'show bgp ipv4 labeled-unicast neighbors 10.255.0.15 advertised-routes' \
    'show bgp ipv4 unicast neighbors 10.255.0.12 advertised-routes' 'show bgp ipv4 labeled-unicast 10.255.0.15/32' 'show mpls forwarding'
  R "$R2" 'show ip bgp' 'show ip bgp labels' 'show ip route 10.255.0.15' 'show ip cef 10.255.0.15 detail' 'show ip cef 10.50.0.0 detail'
  R "$R5" 'show ip bgp' 'show ip bgp labels' 'show ip cef 10.255.0.12 detail'
}

d4() {
  H "d-4: 転送。RT02 ⇔ RT05 のループバック間・お客さま同士(お客さま B は LU で XR01 経由)・traceroute のラベル・LSP ping"
  R "$R2" 'ping 10.255.0.15 source Loopback0 repeat 5' 'ping 10.50.0.1 source Loopback100 repeat 5' \
    'traceroute 10.255.0.15 source Loopback0 timeout 1 probe 1' 'traceroute 10.50.0.1 source Loopback100 timeout 1 probe 1' \
    'ping mpls ipv4 10.255.0.15/32 repeat 3' 'traceroute mpls ipv4 10.255.0.15/32 timeout 1'
  R "$R5" 'ping 10.255.0.12 source Loopback0 repeat 5' 'ping 10.20.0.1 source Loopback100 repeat 5' \
    'traceroute 10.20.0.1 source Loopback100 timeout 1 probe 1' 'ping mpls ipv4 10.255.0.12/32 repeat 3'
  X 'show mpls forwarding' 'show cef 10.255.0.15/32' 'show cef 10.50.0.0/16' \
    'ping mpls ipv4 10.255.0.15/32 fec-type bgp repeat 3' 'ping mpls ipv4 10.255.0.15/32 repeat 3'
  R "$R1" 'show ip route 10.255.0.15' 'show mpls forwarding-table'
  R "$R4" 'show ip route 10.255.0.12' 'show mpls forwarding-table'
}

e1() {
  H "e-1: LSP ping/traceroute の FEC の種類(BGP ラベル付きの経路は LDP の FEC ではない)"
  R "$R2" 'ping mpls ipv4 10.255.0.15/32 fec-type bgp repeat 3' 'ping mpls ipv4 10.255.0.15/32 fec-type generic repeat 3' \
    'traceroute mpls ipv4 10.255.0.15/32 fec-type bgp timeout 1' 'traceroute mpls ipv4 10.255.0.15/32 fec-type generic timeout 1' \
    'ping mpls ipv4 10.255.0.15/32 fec-type ?'
  R "$R5" 'ping mpls ipv4 10.255.0.12/32 fec-type bgp repeat 3' 'traceroute mpls ipv4 10.255.0.12/32 fec-type bgp timeout 1'
  X 'ping mpls ipv4 10.255.0.12/32 fec-type bgp repeat 3' 'ping mpls ipv4 10.255.0.12/32 fec-type generic repeat 3' \
    'ping mpls ipv4 10.255.0.12/32 fec-type ?'
}

e2() {
  H "e-2: PE 同士の直接の iBGP(お客さまの経路= ipv4 unicast・ラベルなし)。TCP が XR01 をラベル付きで通り抜ける"
  R "$R2" 'configure terminal' 'router bgp 65000' 'neighbor 10.255.0.15 remote-as 65000' 'neighbor 10.255.0.15 update-source Loopback0' \
    'address-family ipv4' 'neighbor 10.255.0.15 activate' 'end'
  R "$R5" 'configure terminal' 'router bgp 65000' 'neighbor 10.255.0.12 remote-as 65000' 'neighbor 10.255.0.12 update-source Loopback0' \
    'address-family ipv4' 'neighbor 10.255.0.12 activate' 'end'
  sleep 60
  R "$R2" 'show ip bgp summary' 'show ip bgp 10.50.0.0' 'show ip bgp labels' 'show ip cef 10.50.0.0 detail' \
    'show ip bgp neighbors 10.255.0.15 | include BGP state|family|abel|unique' 'show ip bgp neighbors 10.255.0.1 | include unique|Unique' \
    'ping 10.50.0.1 source Loopback100 repeat 5'
  R "$R5" 'show ip bgp summary' 'show ip bgp 10.20.0.0' 'show tcp brief'
}

e2b() {
  H "e-2b: 直接のセッションではお客さまの経路だけ送る(ループバックを送ると next hop の再帰がループする)"
  R "$R2" 'configure terminal' 'ip prefix-list SVC-OUT seq 5 permit 10.20.0.0/16' 'router bgp 65000' 'address-family ipv4' \
    'neighbor 10.255.0.15 prefix-list SVC-OUT out' 'end' 'clear ip bgp 10.255.0.15 soft out'
  R "$R5" 'configure terminal' 'ip prefix-list SVC-OUT seq 5 permit 10.50.0.0/16' 'router bgp 65000' 'address-family ipv4' \
    'neighbor 10.255.0.12 prefix-list SVC-OUT out' 'end' 'clear ip bgp 10.255.0.12 soft out'
  sleep 30
  R "$R2" 'show ip bgp' 'show ip bgp 10.50.0.0' 'show ip cef 10.50.0.0 detail' 'ping 10.50.0.1 source Loopback100 repeat 5'
  R "$R5" 'show ip bgp' 'ping 10.20.0.1 source Loopback100 repeat 5'
}

e3() {
  H "e-3: XR01 はループバック(10.255.0.0/24 の /32)にだけラベルを割り当てる(allocate-label route-policy)"
  X configure 'route-policy LU-LOOPBACKS' 'if destination in (10.255.0.0/24 eq 32) then' 'pass' 'endif' 'end-policy' \
    'router bgp 65000' 'address-family ipv4 unicast' 'allocate-label route-policy LU-LOOPBACKS' commit 'show configuration failed' end
  sleep 40
  X 'show bgp ipv4 labeled-unicast labels' 'show bgp ipv4 labeled-unicast neighbors 10.255.0.12 advertised-routes' \
    'show bgp ipv4 labeled-unicast neighbors 10.255.0.15 advertised-routes' 'show bgp ipv4 unicast neighbors 10.255.0.12 advertised-routes' \
    'show mpls forwarding'
  R "$R2" 'show ip bgp' 'show ip bgp labels' 'show ip cef 10.50.0.0 detail' 'ping 10.50.0.1 source Loopback100 repeat 5' \
    'traceroute 10.50.0.1 source Loopback100 timeout 1 probe 1' 'ping 10.30.0.1 source Loopback100 repeat 3'
  R "$R5" 'show ip bgp' 'show ip bgp labels' 'ping 10.20.0.1 source Loopback100 repeat 5'
}

SYM2="show ip bgp 10.255.0.15|show ip bgp 10.50.0.0|show ip bgp summary|ping 10.50.0.1 source Loopback100 repeat 5"
sym() { IFS='|' read -ra c <<< "$SYM2"; R "$R2" "${c[@]}"; }
f1() {
  H "f-1: 正常な形から enforce-modifications だけ外す → RT02 の 10.255.0.15 と、PE 同士のセッション・お客さまの通信"
  X configure 'router bgp 65000' 'no ibgp policy out enforce-modifications' commit end
  sleep 20; sym
  X 'show bgp ipv4 labeled-unicast neighbors 10.255.0.12 advertised-routes' 'show bgp ipv4 labeled-unicast labels'
  X configure 'router bgp 65000' 'ibgp policy out enforce-modifications' commit end
  sleep 30; R "$R2" 'show ip bgp 10.255.0.15 | include from|label' 'show ip bgp summary | include 10.255' 'ping 10.50.0.1 source Loopback100 repeat 5'
}
f2() {
  H "f-2: allocate-label だけ外す"
  X configure 'router bgp 65000' 'address-family ipv4 unicast' 'no allocate-label' commit end
  sleep 20; sym
  X 'show bgp ipv4 labeled-unicast neighbors 10.255.0.12 advertised-routes' 'show bgp ipv4 labeled-unicast 10.255.0.15/32'
  X configure 'router bgp 65000' 'address-family ipv4 unicast' 'allocate-label route-policy LU-LOOPBACKS' commit end
  sleep 30; R "$R2" 'show ip bgp 10.255.0.15 | include from|label' 'ping 10.50.0.1 source Loopback100 repeat 5'
}
f3() {
  H "f-3: next-hop-self だけ外す(RT02 向けの LU の AF から)"
  X configure 'router bgp 65000' 'neighbor 10.255.0.12' 'address-family ipv4 labeled-unicast' 'no next-hop-self' commit end
  sleep 20; sym
  X 'show bgp ipv4 labeled-unicast neighbors 10.255.0.12 advertised-routes' 'show bgp ipv4 labeled-unicast labels'
  X configure 'router bgp 65000' 'neighbor 10.255.0.12' 'address-family ipv4 labeled-unicast' 'next-hop-self' commit end
  sleep 30; R "$R2" 'show ip bgp 10.255.0.15 | include from|label' 'ping 10.50.0.1 source Loopback100 repeat 5'
}
f4() {
  H "f-4: route-reflector-client だけ外す(RT05 向け)"
  X configure 'router bgp 65000' 'neighbor 10.255.0.15' 'address-family ipv4 labeled-unicast' 'no route-reflector-client' commit end
  sleep 20; sym
  X 'show bgp ipv4 labeled-unicast neighbors 10.255.0.12 advertised-routes'
  X configure 'router bgp 65000' 'neighbor 10.255.0.15' 'address-family ipv4 labeled-unicast' 'route-reflector-client' commit end
  sleep 30; R "$R2" 'show ip bgp 10.255.0.15 | include from|label' 'ping 10.50.0.1 source Loopback100 repeat 5'
}

g1() {
  H "g-1: Lo0 を ACCESS のインスタンスから外し、接続経路の再配送(Lo0 だけ)でアクセスへ載せる(公式文書 119191 の形)"
  X configure 'route-policy ABR-LO0' 'if destination in (10.255.0.1/32) then' 'pass' 'endif' 'end-policy' \
    'router isis ACCESS' 'no interface Loopback0' 'address-family ipv4 unicast' 'redistribute connected route-policy ABR-LO0' \
    commit 'show configuration failed' end
  sleep 30
  X 'show isis instance ACCESS database verbose XR01.00-00' 'show mpls ldp neighbor brief' 'show bgp ipv4 labeled-unicast summary'
  R "$R4" 'show ip route 10.255.0.1' 'show ip route | include ^i'
  R "$R5" 'show ip route 10.255.0.1' 'ping 10.20.0.1 source Loopback100 repeat 5'
}
g1undo() {
  H "g-1 戻し: Lo0 を ACCESS のインスタンスに戻す"
  X configure 'router isis ACCESS' 'address-family ipv4 unicast' 'no redistribute connected' 'root' \
    'router isis ACCESS' 'interface Loopback0' 'passive' 'address-family ipv4 unicast' 'root' 'no route-policy ABR-LO0' commit end
  sleep 20; R "$R4" 'show ip route 10.255.0.1'
}

mtu() {
  H "mtu: ラベル 2 枚(コア)と 1 枚(アクセス)で DF 付きの大きさの上限"
  R "$R2" 'ping 10.50.0.1 source Loopback100 size 1500 df-bit repeat 2' 'ping 10.50.0.1 source Loopback100 size 1496 df-bit repeat 2' \
    'ping 10.50.0.1 source Loopback100 size 1492 df-bit repeat 2'
  R "$R5" 'ping 10.20.0.1 source Loopback100 size 1500 df-bit repeat 2' 'ping 10.20.0.1 source Loopback100 size 1496 df-bit repeat 2' \
    'ping 10.20.0.1 source Loopback100 size 1492 df-bit repeat 2'
}

"$@"
