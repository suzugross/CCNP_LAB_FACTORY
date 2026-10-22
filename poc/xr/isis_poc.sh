#!/bin/bash
# BL-246 M4 IS-IS の PoC(XRv9000 26.1.1 と XRd 26.1.1 を同じ手順で)。盤面= problems/_POC-XRCMP。記録= design §17。
# usage: source poc/xr/env.sh; poc/xr/isis_poc.sh <XR の管理IP> <R1(L1・area 49.0001)の管理IP> <R2(L2・area 49.0002)の管理IP> <phase…>
#   phase= a b c d e f g(順に流す前提。各 phase は前の状態の上に積む)。出力は標準出力(呼び出し側で poc/xr/isis-<機種>-<phase>.log へ)
#   盤面: R1 Et0/0 10.0.1.2 ── Gi0/0/0/0 XR 10.0.1.1 / Gi0/0/0/1 10.0.2.1 ── Et0/0 10.0.2.2 R2
cd "$(dirname "$0")/../.."
XR=$1 R1=$2 R2=$3; shift 3
X() { .venv/bin/python poc/xr/xrsh.py "$XR" "$@" 2>&1; }
R() { local h=$1; shift; .venv/bin/python poc/xr/xrsh.py "$h" "$@" 2>&1; }
H() { echo; echo "######## $*"; }
XS() { X 'show isis adjacency' 'show isis interface brief' 'show route isis' "$@"; }

a() {
  H "a-0: IOL の IS-IS(IPv4 だけ)。R1= L1 だけ・area 49.0001 / R2= L2 だけ・area 49.0002。どちらも p2p"
  R "$R1" 'configure terminal' 'router isis' 'net 49.0001.0000.0000.0011.00' 'is-type level-1' 'log-adjacency-changes' \
    'interface Loopback0' 'ip router isis' 'interface Ethernet0/0' 'ip router isis' 'isis network point-to-point' end \
    'show running-config | section isis' 'show isis protocol' 'show clns protocol'
  R "$R2" 'configure terminal' 'router isis' 'net 49.0002.0000.0000.0022.00' 'is-type level-2-only' 'log-adjacency-changes' \
    'interface Loopback0' 'ip router isis' 'interface Ethernet0/0' 'ip router isis' 'isis network point-to-point' end \
    'show running-config | section isis'
  H "a-1: XR に IS-IS を IOS の感覚で書く(IF を並べるだけ・アドレスファミリなし)"
  X configure 'router isis CORE' 'net 49.0001.0000.0000.0001.00' 'interface Loopback0' exit \
    'interface GigabitEthernet0/0/0/0' 'point-to-point' exit 'interface GigabitEthernet0/0/0/1' 'point-to-point' commit end
  sleep 30
  XS 'show isis interface GigabitEthernet0/0/0/0' 'show isis' 'show running-config router isis'
  R "$R1" 'show clns neighbors' 'show isis neighbors'
}

b() {
  H "b-1: IF の下にだけ address-family ipv4 unicast を足す(プロセスには無い)"
  X configure 'router isis CORE' 'interface Loopback0' 'address-family ipv4 unicast' root \
    'router isis CORE' 'interface GigabitEthernet0/0/0/0' 'address-family ipv4 unicast' root \
    'router isis CORE' 'interface GigabitEthernet0/0/0/1' 'address-family ipv4 unicast' commit 'show configuration failed' end
  sleep 30
  XS 'show isis interface GigabitEthernet0/0/0/0'
}

c() {
  H "c-1: プロセスにも address-family ipv4 unicast"
  X configure 'router isis CORE' 'address-family ipv4 unicast' commit end
  sleep 40
  XS 'show isis interface GigabitEthernet0/0/0/0' 'show isis interface GigabitEthernet0/0/0/1' 'show isis interface Loopback0'
  H "c-2: 状態の表示一式"
  X 'show isis' 'show isis protocol' 'show isis neighbors' 'show isis adjacency detail' 'show isis hostname' \
    'show isis database' 'show isis database detail' 'show isis topology' 'show isis route' 'show route ipv4' \
    'show running-config router isis CORE' 'show running-config router isis CORE inheritance detail' \
    'show logging | include ISIS'
  H "c-3: IOL 側"
  R "$R1" 'show clns neighbors detail' 'show isis database detail' 'show ip route isis' 'show ip route 0.0.0.0' 'ping 22.22.22.22 source 11.11.11.11'
  R "$R2" 'show clns neighbors detail' 'show isis database detail' 'show ip route isis'
}

d() {
  H "d-1: narrow のまま IF に 1000 を書く"
  X configure 'router isis CORE' 'interface GigabitEthernet0/0/0/1' 'address-family ipv4 unicast' 'metric 1000' commit 'show configuration failed' abort
  X configure 'router isis CORE' 'interface GigabitEthernet0/0/0/1' 'address-family ipv4 unicast' 'metric 63' commit end
  sleep 15
  R "$R2" 'show isis database detail' 'show ip route isis'
  X configure 'router isis CORE' 'interface GigabitEthernet0/0/0/1' 'address-family ipv4 unicast' 'no metric 63' commit end
  H "d-2: R2(L2 の相手)だけ wide にする= バックボーンが wide へ移行した状態"
  R "$R2" 'configure terminal' 'router isis' 'metric-style wide' end
  sleep 40
  XS 'show isis database detail' 'show isis topology level 2' 'show isis route' 'show isis'
  R "$R2" 'show isis database detail' 'show ip route isis' 'show isis topology' 'show clns neighbors'
  R "$R1" 'show ip route isis' 'show isis database detail'
  H "d-3: XR を level 2 だけ wide"
  X configure 'router isis CORE' 'address-family ipv4 unicast' 'metric-style wide level 2' commit end
  sleep 40
  XS 'show isis database detail' 'show isis'
  R "$R2" 'show ip route isis'
  R "$R1" 'show ip route isis' 'ping 22.22.22.22 source 11.11.11.11'
  H "d-4: L2 だけ wide になったので 1000 を level 2 に書けるか"
  X configure 'router isis CORE' 'interface GigabitEthernet0/0/0/1' 'address-family ipv4 unicast' 'metric 1000 level 2' commit 'show configuration failed' end
  sleep 20
  X 'show isis interface GigabitEthernet0/0/0/1' 'show isis database detail XR*'
  X configure 'router isis CORE' 'interface GigabitEthernet0/0/0/1' 'address-family ipv4 unicast' 'metric 1000' commit 'show configuration failed' abort
  H "d-5: 両レベル wide にすると L1(narrow の R1)はどうなるか"
  X configure 'router isis CORE' 'address-family ipv4 unicast' 'no metric-style wide level 2' 'metric-style wide' commit end
  sleep 40
  R "$R1" 'show ip route isis' 'show isis database detail'
  X 'show route isis'
  X configure 'router isis CORE' 'address-family ipv4 unicast' 'no metric-style wide' 'metric-style wide level 2' commit end
  sleep 30
  R "$R1" 'show ip route isis'
}

e() {
  H "e-0: IOL に IPv6(単一トポロジ= IOS の既定)を足す。XR はまだ IPv6 なし= 隣接はどうなるか"
  R "$R1" 'configure terminal' 'ipv6 unicast-routing' 'interface Loopback0' 'ipv6 address 2001:db8::11/128' 'ipv6 router isis' \
    'interface Ethernet0/0' 'ipv6 router isis' end
  R "$R2" 'configure terminal' 'ipv6 unicast-routing' 'interface Loopback0' 'ipv6 address 2001:db8::22/128' 'ipv6 router isis' \
    'interface Ethernet0/0' 'ipv6 router isis' end
  sleep 40
  X 'show isis adjacency'
  R "$R1" 'show clns neighbors' 'show isis protocol' 'show logging | include ISIS|CLNS'
  R "$R2" 'show clns neighbors' 'show logging | include ISIS|CLNS'
  H "e-1: XR に IPv6 を足す(既定のまま)"
  X configure 'router isis CORE' 'address-family ipv6 unicast' root \
    'router isis CORE' 'interface Loopback0' 'address-family ipv6 unicast' root \
    'router isis CORE' 'interface GigabitEthernet0/0/0/0' 'address-family ipv6 unicast' root \
    'router isis CORE' 'interface GigabitEthernet0/0/0/1' 'address-family ipv6 unicast' commit 'show configuration failed' end
  sleep 40
  X 'show isis adjacency' 'show isis adjacency detail' 'show isis' 'show route ipv6 isis' 'show isis ipv6 topology' \
    'show isis database detail' 'show running-config router isis CORE'
  R "$R1" 'show clns neighbors' 'show ipv6 route isis' 'show isis database detail'
  R "$R2" 'show clns neighbors' 'show ipv6 route isis'
  H "e-2: XR を single-topology に"
  X configure 'router isis CORE' 'address-family ipv6 unicast' 'single-topology' commit 'show configuration failed' end
  sleep 40
  X 'show isis adjacency' 'show isis' 'show route ipv6 isis' 'show isis database detail' 'show running-config router isis CORE'
  R "$R1" 'show clns neighbors' 'show ipv6 route isis' 'ping 2001:db8::22 source 2001:db8::11'
  R "$R2" 'show ipv6 route isis'
}

f() {
  H "f-0: 書式の確認(ヘルプ)"
  X configure 'router isis CORE' 'address-family ipv4 unicast' 'propagate level 2 into level 1 ?' abort
  X configure 'router isis CORE' 'address-family ipv4 unicast' '?' abort
  X configure 'router isis CORE' 'interface GigabitEthernet0/0/0/0' '?' abort
  X configure 'router isis CORE' '?' abort
  H "f-1: L2 → L1 の漏らし(R2 のループバック /32 だけ)。IPv4"
  X configure 'prefix-set LOOPS' '22.22.22.22/32' end-set 'route-policy L2-TO-L1' 'if destination in LOOPS then' pass endif end-policy \
    'router isis CORE' 'address-family ipv4 unicast' 'propagate level 2 into level 1 route-policy L2-TO-L1' commit 'show configuration failed' end
  sleep 30
  R "$R1" 'show ip route isis' 'show isis database detail' 'show ip route 22.22.22.22'
  X 'show isis database detail XR*' 'show rpl route-policy L2-TO-L1 attachpoints'
  H "f-2: ポリシーなしの propagate は書けるか(全部漏れるか)"
  X configure 'router isis CORE' 'address-family ipv4 unicast' 'no propagate level 2 into level 1 route-policy L2-TO-L1' 'propagate level 2 into level 1' commit 'show configuration failed' abort
  H "f-3: IPv6 の漏らし(single-topology のまま)"
  X configure 'prefix-set LOOPS6' '2001:db8::22/128' end-set 'route-policy L2-TO-L1-V6' 'if destination in LOOPS6 then' pass endif end-policy \
    'router isis CORE' 'address-family ipv6 unicast' 'propagate level 2 into level 1 route-policy L2-TO-L1-V6' commit 'show configuration failed' end
  sleep 30
  R "$R1" 'show ipv6 route isis'
  H "f-4: L1 の既定経路(ATT ビット)は漏らしの後も残るか"
  R "$R1" 'show ip route 0.0.0.0' 'show isis database' 'show ipv6 route ::/0'
}

g() {
  H "g-1: その他の既定(ハローのパディング・ログ・passive)"
  X 'show isis interface GigabitEthernet0/0/0/0 | include "adding|Pad|pad"' 'show logging | include "ISIS|isis" | utility tail count 20'
  X configure 'router isis CORE' 'log adjacency changes' 'interface Loopback0' 'passive' commit end
  X 'show isis interface Loopback0' 'show isis interface brief'
  H "g-2: advertise passive-only(リンクのサブネットを広告しない)"
  X configure 'router isis CORE' 'address-family ipv4 unicast' 'advertise passive-only' commit 'show configuration failed' end
  sleep 30
  R "$R1" 'show ip route isis'
  R "$R2" 'show ip route isis'
  X configure 'router isis CORE' 'address-family ipv4 unicast' 'no advertise passive-only' commit end
  H "g-3: circuit-type と is-type"
  X configure 'router isis CORE' 'interface GigabitEthernet0/0/0/0' 'circuit-type level-1' root \
    'router isis CORE' 'interface GigabitEthernet0/0/0/1' 'circuit-type level-2-only' commit end
  sleep 20
  X 'show isis interface GigabitEthernet0/0/0/0' 'show isis interface GigabitEthernet0/0/0/1' 'show isis adjacency'
  H "g-4: 隣接の詳細・DB の読み方"
  X 'show isis database verbose' 'show isis spf-log' 'show isis statistics'
}

for p in "$@"; do "$p"; done
