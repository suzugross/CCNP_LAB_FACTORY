#!/bin/bash
# BL-246 M8(MPLS LDP)の PoC。盤面= problems/_POC-XRLDP(XR01= XRv9000 26.1.1・XR02= XRd 26.1.1・IOL 17.15)。記録= design §20。
# usage: source poc/xr/env.sh; poc/xr/ldp_poc.sh <phase…>   出力は標準出力(呼び出し側で poc/xr/ldp-<phase>.log へ)
#   管理 IP は topologies/_generated/_POC-XRLDP/mgmt_map.yml から引く。phase は a から順に積む前提。
cd "$(dirname "$0")/../.."
PID=${PID:-_POC-XRLDP}
M=topologies/_generated/$PID/mgmt_map.yml
ip() { awk -v n="$1:" '$1==n{print $2}' "$M"; }
XR=$(ip XR01) XD=$(ip XR02) R1=$(ip RT01) R2=$(ip RT02) R3=$(ip RT03) R4=$(ip RT04) R5=$(ip RT05)
X() { .venv/bin/python poc/xr/xrsh.py "$XR" "$@" 2>&1; }
D() { .venv/bin/python poc/xr/xrsh.py "$XD" "$@" 2>&1; }
R() { local h=$1; shift; .venv/bin/python poc/xr/xrsh.py "$h" "$@" 2>&1; }
H() { echo; echo "######## $(date +%T) $*"; }
LINK() { .venv/bin/python poc/xr/cml_link.py $PID "$@" 2>&1; }
G0=GigabitEthernet0/0/0/0 G1=GigabitEthernet0/0/0/1
CUST='ping 10.20.0.1 source Loopback100 count 5'

a() {
  H "a-1: XRv9000 26.1.1 の素の状態と BGP(LDP なし)"
  X 'show version | include "Version|uptime"' 'show memory summary' 'show isis adjacency' 'show bgp ipv4 unicast' \
    'show route 10.20.0.0/16' "$CUST"
  H "a-2: IOL 側(RT01 は BGP なし= 10.20/16 を知らない)"
  R "$R1" 'show ip route 10.20.0.0' 'show mpls ldp neighbor' 'show mpls ldp discovery' 'show mpls forwarding-table'
  R "$R2" 'show ip bgp' 'ping 10.30.0.1 source Loopback100 repeat 5' 'show mpls ldp neighbor | include Peer|State|Up time'
}

b() {
  H "b-1: XR01 で LDP を有効に(router-id は指定しない)。Lo1 10.255.255.1 は IS-IS に無い"
  X configure 'mpls ldp' "interface $G0" root 'mpls ldp' "interface $G1" commit 'show configuration failed' end \
    'show running-config mpls ldp' 'show running-config router-id'
  sleep 40
  X 'show mpls ldp summary' 'show mpls ldp discovery' 'show mpls ldp neighbor brief' 'show mpls ldp neighbor' \
    'show mpls ldp parameters' 'show logging last 30'
  R "$R1" 'show mpls ldp discovery detail' 'show mpls ldp neighbor' 'show logging | include LDP|TAGCON' 'show ip route 10.255.255.1'
  R "$R3" 'show mpls ldp discovery' 'show mpls ldp neighbor | include Peer|State'
}
b2() {
  H "b-2: LDP の ID を Lo0 のアドレスに(mpls ldp router-id)。その場で効くか"
  X configure 'mpls ldp' 'router-id 10.255.0.1' commit 'show configuration failed' end
  sleep 30
  X 'show mpls ldp neighbor brief' 'show mpls ldp discovery' 'show logging last 15'
  sleep 30
  X 'show mpls ldp neighbor brief' 'show mpls ldp discovery | include "LDP Id|Transport|Session"' \
    'show mpls forwarding' 'show mpls forwarding prefix 10.255.0.12/32' 'show cef 10.20.0.0/16' "$CUST" \
    'traceroute 10.20.0.1 source Loopback100 timeout 1'
  R "$R1" 'show mpls ldp neighbor | include Peer|State|Up time' 'show mpls forwarding-table'
  R "$R2" 'ping 10.30.0.1 source Loopback100 repeat 5' 'traceroute 10.30.0.1 source Loopback100 timeout 1 probe 1'
}

c() {
  H "c-1: RT03 に XR01 向けのパスワード(XR01 はまだ無し)→ セッションを張り直させる"
  R "$R3" 'configure terminal' 'mpls ldp neighbor 10.255.0.1 password LDP-CORE-7' 'end' 'clear mpls ldp neighbor 10.255.0.1'
  sleep 40
  R "$R3" 'show mpls ldp neighbor | include Peer|State' 'show mpls ldp discovery' 'show logging | include TCP|LDP|MD5|AUTH'
  X 'show mpls ldp neighbor brief' 'show mpls ldp discovery' 'show logging last 15'
  H "c-2: RT03 に password required(パスワードなしのセッションを一切受けない)"
  R "$R3" 'configure terminal' 'mpls ldp password required' 'end' 'show mpls ldp neighbor | include Peer|State'
  H "c-3: XR01 に RT03 向けのパスワード"
  X configure 'mpls ldp' 'neighbor 10.255.0.13:0 password clear LDP-CORE-7' commit 'show configuration failed' end \
    'show running-config mpls ldp'
  sleep 40
  X 'show mpls ldp neighbor brief' 'show mpls ldp neighbor 10.255.0.13:0 detail'
  R "$R3" 'show mpls ldp neighbor detail | include Peer|State|MD5|Password|password'
  H "c-4: XR01 の全体の既定パスワード(RT01 はパスワードなし)→ RT01 とのセッションはどうなるか(試したら外す)"
  X configure 'mpls ldp' 'neighbor password clear LDP-CORE-7' commit 'show configuration failed' end
  sleep 5
  X 'clear mpls ldp neighbor 10.255.0.11'
  sleep 40
  X 'show mpls ldp neighbor brief' 'show logging last 15'
  R "$R1" 'show mpls ldp neighbor | include Peer|State' 'show logging | include TCP|LDP|MD5'
  X configure 'mpls ldp' 'no neighbor password' commit 'show configuration failed' end 'clear mpls ldp neighbor 10.255.0.11'
  sleep 40
  X 'show mpls ldp neighbor brief'
}

d() {
  H "d-1: ラベルの割り当てを /32 だけに(前後で束縛を比べる)"
  X 'show mpls ldp bindings brief' 'show mpls ldp bindings local'
  R "$R1" 'show mpls ldp bindings neighbor 10.255.0.1'
  X configure 'mpls ldp' 'address-family ipv4' 'label' 'local' 'allocate for host-routes' commit 'show configuration failed' end \
    'show running-config mpls ldp'
  sleep 10
  X 'show mpls ldp bindings brief' 'show mpls ldp bindings local' 'show mpls forwarding' "$CUST"
  R "$R1" 'show mpls ldp bindings neighbor 10.255.0.1' 'show mpls forwarding-table'
}

e() {
  H "e-1: 同期なし。RT01 の XR01 側で LDP だけ止める(IS-IS は上がったまま)"
  R "$R1" 'configure terminal' 'interface Ethernet0/0' 'no mpls ip' 'end'
  sleep 25
  X 'show mpls ldp neighbor brief' 'show mpls ldp discovery brief' 'show isis adjacency' 'show route 10.255.0.12/32' \
    'show mpls forwarding prefix 10.255.0.12/32' 'show cef 10.20.0.0/16' "$CUST"
  H "e-2: XR01 に同期(IS-IS の IF の AF の下)"
  X configure 'router isis CORE' "interface $G0" 'address-family ipv4 unicast' 'mpls ldp sync' root \
    'router isis CORE' "interface $G1" 'address-family ipv4 unicast' 'mpls ldp sync' commit 'show configuration failed' end
  sleep 10
  X 'show mpls ldp igp sync' 'show isis interface '"$G0" 'show isis database verbose XR01.00-00' 'show route 10.255.0.12/32' \
    'show mpls forwarding prefix 10.255.0.12/32' "$CUST" 'traceroute 10.20.0.1 source Loopback100 timeout 1'
  R "$R1" 'show isis database verbose XR01.00-00' 'show ip route 10.255.0.12'
  R "$R2" 'ping 10.30.0.1 source Loopback100 repeat 5'
  H "e-3: RT01 の LDP を戻す → 同期がそろって通常のメトリックへ戻るまで"
  R "$R1" 'configure terminal' 'interface Ethernet0/0' 'mpls ip' 'end'
  for i in 1 2 3 4; do sleep 5; X 'show mpls ldp igp sync | include "Sync status|Peers|GigabitEthernet"' 'show isis database verbose XR01.00-00 | include Metric'; done
  X 'show route 10.255.0.12/32' 'show logging last 20'
}

f() {
  H "f-1: XR01 にセッション保護(RT01 は targeted ハローを受け入れる設定なし)"
  X configure 'mpls ldp' 'session protection' commit 'show configuration failed' end
  sleep 30
  X 'show mpls ldp neighbor 10.255.0.11:0 detail' 'show mpls ldp discovery' 'show mpls ldp neighbor brief'
  R "$R1" 'show mpls ldp discovery' 'show logging | include LDP|TAGCON'
  H "f-2: RT01 に targeted ハローの受け入れ"
  R "$R1" 'configure terminal' 'mpls ldp discovery targeted-hello accept' 'end'
  sleep 30
  X 'show mpls ldp neighbor 10.255.0.11:0 detail' 'show mpls ldp discovery'
  R "$R1" 'show mpls ldp discovery' 'show mpls ldp neighbor 10.255.0.1 detail | include Up time|Addresses|Targeted|Src'
}

f3() {
  H "f-3: XR01-RT01 を CML のリンク条件で黙って落とす(loss 100)→ 保護の間のセッションと束縛"
  X 'show mpls ldp neighbor 10.255.0.11:0 | include "Up time|Protection|State"'
  LINK XR01 RT01 loss 100
  for t in 20 25; do sleep $t; X 'show mpls ldp neighbor 10.255.0.11:0 detail' 'show mpls ldp bindings 10.255.0.12/32' 'show isis adjacency' \
    'show mpls ldp igp sync' 'show route 10.255.0.12/32' "$CUST"; done
  H "f-3b: リンクを戻す → 稼働時間・同期・主経路への戻り"
  LINK XR01 RT01 clear
  for i in 1 2 3 4 5 6; do sleep 5; X 'show mpls ldp neighbor 10.255.0.11:0 | include "Up time|Protection|State"' \
    'show mpls ldp igp sync | include "Sync status|GigabitEthernet0/0/0/0"' 'show route 10.255.0.12/32 | include via'; done
  X 'show logging last 30'
}

g() {
  H "g-1: OAM。XR01 に mpls oam なしで、RT02 から LSP ping/traceroute・XR01 から LSP ping"
  R "$R2" 'ping mpls ipv4 10.255.0.1/32 repeat 3' 'traceroute mpls ipv4 10.255.0.1/32 timeout 1'
  X 'ping mpls ipv4 10.255.0.12/32 repeat 3' 'traceroute mpls ipv4 10.255.0.12/32'
  H "g-2: XR01 に mpls oam"
  X configure 'mpls oam' commit 'show configuration failed' end
  sleep 5
  R "$R2" 'ping mpls ipv4 10.255.0.1/32 repeat 3' 'traceroute mpls ipv4 10.255.0.1/32 timeout 1'
  X 'ping mpls ipv4 10.255.0.12/32 repeat 3' 'traceroute mpls ipv4 10.255.0.12/32' 'traceroute mpls multipath ipv4 10.255.0.12/32'
}

h() {
  H "h-1: 脇の系統。XRd(XR02)に LDP → RT04 ⇔ RT05 のお客さまの通信がラベルで XR02 を通るか"
  R "$R4" 'show ip bgp' 'ping 10.50.0.1 source Loopback100 repeat 5'
  D configure 'mpls ldp' 'router-id 10.255.1.2' 'interface GigabitEthernet0/0/0/0' root 'mpls ldp' 'interface GigabitEthernet0/0/0/1' \
    commit 'show configuration failed' end
  sleep 40
  D 'show mpls ldp neighbor brief' 'show mpls forwarding' 'show mpls interfaces'
  R "$R4" 'show mpls ldp neighbor | include Peer|State' 'show mpls forwarding-table' 'ping 10.50.0.1 source Loopback100 repeat 5' \
    'traceroute 10.50.0.1 source Loopback100 timeout 1 probe 1' 'ping mpls ipv4 10.255.1.5/32 repeat 3'
}
bt() {
  H "bt: 仕込みの候補= 転送アドレスだけ IS-IS に無い Lo1 へ(LDP ID は Lo0 のまま)→ 戻す"
  X 'show router-id' configure 'mpls ldp address-family ipv4 discovery transport-address 10.255.255.1' commit 'show configuration failed' end
  sleep 45
  X 'show mpls ldp neighbor brief' 'show mpls ldp discovery' 'show mpls ldp parameters | include "Router ID|IPv4:"' 'show logging last 8'
  R "$R1" 'show mpls ldp discovery detail' 'show logging | include LDP'
  X configure 'no mpls ldp address-family ipv4 discovery transport-address' commit end
  sleep 40
  X 'show mpls ldp neighbor brief'
}

f4() {
  H "f4: 保護+同期あり。RT01 Et0/0 で no mpls ip(IS-IS は上がったまま・セッションは targeted で残る)→ 戻す"
  R "$R1" 'configure terminal' 'interface Ethernet0/0' 'no mpls ip' 'end'
  sleep 25
  X 'show mpls ldp neighbor 10.255.0.11:0 detail | include "Up time|state|Targeted|Gigabit"' 'show mpls ldp igp sync' \
    'show isis database verbose XR01.00-00 | include Metric' 'show route 10.255.0.12/32 | include via' "$CUST"
  R "$R2" 'ping 10.30.0.1 source Loopback100 repeat 5'
  R "$R1" 'configure terminal' 'interface Ethernet0/0' 'mpls ip' 'end'
  sleep 15
  X 'show mpls ldp igp sync | include "Sync status"' 'show mpls ldp neighbor 10.255.0.11:0 | include "Up time"' \
    'configure' 'mpls ldp' 'igp sync delay ?' 'igp sync delay on-session-up ?' 'abort'
}

mtu() {
  H "mtu: ラベル 1 枚ぶんで 1500 バイトの DF が通るか"
  X 'show interfaces GigabitEthernet0/0/0/0 | include MTU' 'ping 10.20.0.1 source Loopback100 size 1500 df-bit count 3' \
    'ping 10.20.0.1 source Loopback100 size 1496 df-bit count 3' 'ping mpls ipv4 10.255.0.12/32 sweep 1490 1510 4 repeat 1'
  R "$R2" 'ping 10.30.0.1 source Loopback100 size 1500 df-bit repeat 3' 'ping 10.30.0.1 source Loopback100 size 1496 df-bit repeat 3'
}
"$@"
