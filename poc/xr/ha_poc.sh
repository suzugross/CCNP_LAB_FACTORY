#!/bin/bash
# BL-246 M7(高可用性)の PoC。盤面= problems/_POC-XRHA(XR01= XRv9000 26.1.1・IOL 17.15)。記録= design §19。
# usage: source poc/xr/env.sh; poc/xr/ha_poc.sh <phase…>   出力は標準出力(呼び出し側で poc/xr/ha-<phase>.log へ)
#   管理 IP は topologies/_generated/_POC-XRHA/mgmt_map.yml から引く。phase は a から順に積む前提。
cd "$(dirname "$0")/../.."
M=topologies/_generated/_POC-XRHA/mgmt_map.yml
ip() { awk -v n="$1:" '$1==n{print $2}' "$M"; }
XR=$(ip XR01) R1=$(ip RT01) R2=$(ip RT02)
X() { .venv/bin/python poc/xr/xrsh.py "$XR" "$@" 2>&1; }
R() { local h=$1; shift; .venv/bin/python poc/xr/xrsh.py "$h" "$@" 2>&1; }
H() { echo; echo "######## $(date +%T) $*"; }
LINK() { .venv/bin/python poc/xr/cml_link.py _POC-XRHA "$@" 2>&1; }
# 主経路(RT01 → XR01 → SW01 → RT02)を測る ping。欠落の数 ≒ 止まった秒数
PING() { .venv/bin/python poc/xr/pingloss.py "$R1" 10.20.0.1 Loopback1 "${1:-20000}" 2>&1; }
G0=GigabitEthernet0/0/0/0 G1=GigabitEthernet0/0/0/1 G2=GigabitEthernet0/0/0/2

a() {
  H "a-1: XRv9000 26.1.1 の素の状態(資源・IF)"
  X 'show version' 'show platform' 'show memory summary' 'show processes cpu | include "CPU utilization"' \
    'show ipv4 interface brief' 'show interfaces summary' 'show running-config'
  H "a-2: IOL 側(束は相手待ち・IS-IS は RT01-RT02 の予備経路だけ)"
  R "$R1" 'show etherchannel summary' 'show lacp neighbor' 'show clns neighbors' 'show ip route isis' \
    'show interfaces Port-channel1 | include MTU|line protocol' 'show isis protocol' 'show running-config | section router isis'
  R "$R2" 'show clns neighbors' 'show ip route isis' 'show isis protocol'
}

b() {
  H "b-1: 束を LACP active で作る(最低本数は既定のまま)"
  X configure 'interface Bundle-Ether1' 'description BUNDLE to RT01' 'ipv4 address 10.0.1.1 255.255.255.0' root \
    "interface $G0" 'bundle id 1 mode active' root "interface $G1" 'bundle id 1 mode active' commit 'show configuration failed' end
  sleep 40
  X 'show bundle Bundle-Ether1' 'show lacp Bundle-Ether1' 'show interfaces Bundle-Ether1 | include "MTU|line protocol|BW"' \
    "show interfaces $G0 | include \"MTU|line protocol\"" 'ping 10.0.1.11 count 5'
  R "$R1" 'show etherchannel summary' 'show lacp neighbor' 'show interfaces Port-channel1 | include MTU|line protocol|BW'

  H "b-2: 最低本数 2 → RT01 で 1 本止める(束はダウンするか)→ 戻す"
  X configure 'interface Bundle-Ether1' 'bundle minimum-active links 2' commit 'show configuration failed' end
  R "$R1" 'configure terminal' 'interface GigabitEthernet2' 'shutdown' 'end'
  sleep 15
  X 'show bundle Bundle-Ether1' 'show interfaces Bundle-Ether1 | include "line protocol"' 'show logging last 20'
  R "$R1" 'show etherchannel summary'
  R "$R1" 'configure terminal' 'interface GigabitEthernet2' 'no shutdown' 'end'
  sleep 40
  X 'show bundle Bundle-Ether1 | include "Status|Local links|Gi"'

  H "b-3: モードの食い違い= XR を mode on(静的)・RT01 は LACP active"
  X configure "interface $G0" 'no bundle id' 'bundle id 1 mode on' root "interface $G1" 'no bundle id' 'bundle id 1 mode on' \
    commit 'show configuration failed' end
  sleep 60
  X 'show bundle Bundle-Ether1' 'show interfaces Bundle-Ether1 | include "line protocol"' 'ping 10.0.1.11 count 5' 'show logging last 20'
  R "$R1" 'show etherchannel summary' 'show lacp neighbor' 'show logging | include LINK|LACP|EC|PORT'

  H "b-4: XR を passive(RT01 は active)→ 上がるはず"
  X configure "interface $G0" 'no bundle id' 'bundle id 1 mode passive' root "interface $G1" 'no bundle id' 'bundle id 1 mode passive' \
    commit 'show configuration failed' end
  sleep 45
  X 'show bundle Bundle-Ether1 | include "Status|Local links|Gi"' 'ping 10.0.1.11 count 5'
  R "$R1" 'show etherchannel summary'

  H "b-5: 両方 passive(RT01 も passive)→ 上がらないはず"
  R "$R1" 'configure terminal' 'interface range GigabitEthernet1 - 2' 'channel-group 1 mode passive' 'end'
  sleep 45
  X 'show bundle Bundle-Ether1 | include "Status|Local links|Gi"'
  R "$R1" 'show etherchannel summary'

  H "b-6: 元へ(両方 active)"
  R "$R1" 'configure terminal' 'interface range GigabitEthernet1 - 2' 'channel-group 1 mode active' 'end'
  X configure "interface $G0" 'no bundle id' 'bundle id 1 mode active' root "interface $G1" 'no bundle id' 'bundle id 1 mode active' \
    commit 'show configuration failed' end
  sleep 45
  X 'show bundle Bundle-Ether1 | include "Status|Local links|Gi"' 'ping 10.0.1.11 count 5'
  R "$R1" 'show etherchannel summary'
}

# 束のメンバ(Gi0/0/0/1 ⇔ RT01 Gi2)が抜けるまでの秒数を測る
WAITOUT() {
  local t0=$(date +%s) i
  for i in $(seq 1 30); do
    sleep 5
    if ! X 'show bundle Bundle-Ether1 | include "Gi0/0/0/1"' | grep -q ' Active '; then
      echo "== Gi0/0/0/1 left the bundle after $(( $(date +%s) - t0 )) s"; return; fi
  done
  echo "== still Active after $(( $(date +%s) - t0 )) s"
}

b2() {
  H "b2-1: LACP 周期 slow(既定)。RT01 Gi2 を shutdown → XR が抜くまで(CML では XR 側のキャリアは落ちない)"
  X 'show lacp Bundle-Ether1 | include "Gi0/0/0/1|Period|Slow|Fast"'
  R "$R1" 'configure terminal' 'interface GigabitEthernet2' 'shutdown' 'end'; date +%T
  WAITOUT
  X 'show bundle Bundle-Ether1 | include "Status|Local links|Gi"' 'show logging last 6'
  R "$R1" 'configure terminal' 'interface GigabitEthernet2' 'no shutdown' 'end'
  sleep 40; X 'show bundle Bundle-Ether1 | include "Status|Gi"'

  H "b2-2: XR のメンバに lacp period short(相手に速い送信を求める)→ 同じ操作"
  X configure "interface $G0" 'lacp period short' root "interface $G1" 'lacp period short' commit 'show configuration failed' end
  sleep 15
  X 'show lacp Bundle-Ether1' 
  R "$R1" 'show lacp internal' 'show lacp neighbor'
  R "$R1" 'configure terminal' 'interface GigabitEthernet2' 'shutdown' 'end'; date +%T
  WAITOUT
  X 'show bundle Bundle-Ether1 | include "Status|Local links|Gi"' 'show logging last 6'
  R "$R1" 'configure terminal' 'interface GigabitEthernet2' 'no shutdown' 'end'
  sleep 40; X 'show bundle Bundle-Ether1 | include "Status|Gi"'

  H "b2-3: RT01 側にも lacp rate fast(受け付けるか)"
  R "$R1" 'configure terminal' 'interface range GigabitEthernet1 - 2' 'lacp rate fast' 'end' 'show lacp internal'
  sleep 10; X 'show lacp Bundle-Ether1 | include "Gi0/0/0|Fast|Slow"'

  H "b2-4: 周期を元へ・両方 passive で 150 秒待つ"
  X configure "interface $G0" 'no lacp period' root "interface $G1" 'no lacp period' commit end
  R "$R1" 'configure terminal' 'interface range GigabitEthernet1 - 2' 'no lacp rate' 'channel-group 1 mode passive' 'end'
  X configure "interface $G0" 'no bundle id' 'bundle id 1 mode passive' root "interface $G1" 'no bundle id' 'bundle id 1 mode passive' \
    commit end; date +%T
  for i in 1 2 3 4 5; do sleep 30; date +%T; X 'show bundle Bundle-Ether1 | include "Status|Gi0"'; done
  R "$R1" 'show etherchannel summary | include Po1'

  H "b2-5: 元へ(両方 active)"
  R "$R1" 'configure terminal' 'interface range GigabitEthernet1 - 2' 'channel-group 1 mode active' 'end'
  X configure "interface $G0" 'no bundle id' 'bundle id 1 mode active' root "interface $G1" 'no bundle id' 'bundle id 1 mode active' \
    commit end
  sleep 45; X 'show bundle Bundle-Ether1 | include "Status|Gi"' 'ping 10.0.1.11 count 5'
}

# RT01 の束のモードを替える(Cat8000v はその場で替えられない= 外してから付け直す)
R1MODE() { R "$R1" 'configure terminal' 'interface range GigabitEthernet1 - 2' 'no channel-group 1' "channel-group 1 mode $1" 'end' \
  'show running-config interface GigabitEthernet1 | include channel'; }

b3() {
  H "b3-1: 両方 passive(付け直して最初から)"
  X configure "interface $G0" 'no bundle id' 'bundle id 1 mode passive' root "interface $G1" 'no bundle id' 'bundle id 1 mode passive' commit end
  R1MODE passive; date +%T
  for i in 1 2 3; do sleep 30; date +%T; X 'show bundle Bundle-Ether1 | include "Status|Gi0"'; done
  R "$R1" 'show etherchannel summary | include Po1'
  H "b3-2: RT01 を mode on(静的)・XR は passive"
  R1MODE on
  sleep 60; X 'show bundle Bundle-Ether1 | include "Status|Gi0"' 'ping 10.0.1.11 count 5'
  R "$R1" 'show etherchannel summary | include Po1'
  H "b3-3: 元へ(両方 active)"
  R1MODE active
  X configure "interface $G0" 'no bundle id' 'bundle id 1 mode active' root "interface $G1" 'no bundle id' 'bundle id 1 mode active' commit end
  sleep 45; X 'show bundle Bundle-Ether1 | include "Status|Gi0"' 'ping 10.0.1.11 count 5'
  R "$R1" 'show etherchannel summary | include Po1'
}

c() {
  H "c-1: IS-IS(L2 だけ・wide)を束と主経路に。Lo0 は passive"
  X configure 'router isis CORE' 'is-type level-2-only' 'net 49.0001.0100.0000.0001.00' 'log adjacency changes' \
    'address-family ipv4 unicast' 'metric-style wide' 'exit' \
    'interface Loopback0' 'passive' 'address-family ipv4 unicast' 'exit' 'exit' \
    'interface Bundle-Ether1' 'point-to-point' 'address-family ipv4 unicast' 'exit' 'exit' \
    "interface $G2" 'point-to-point' 'address-family ipv4 unicast' commit 'show configuration failed' end
  sleep 45
  X 'show isis adjacency' 'show isis interface Bundle-Ether1' 'show route ipv4 isis' 'show isis protocol' \
    'show running-config router isis'
  R "$R1" 'show clns neighbors' 'show ip route isis' 'traceroute 10.20.0.1 source Loopback1 numeric timeout 1 probe 1'
  R "$R2" 'show clns neighbors' 'show ip route isis'

  H "c-2: XR の束に mtu 1500(= L3 で 1486)。RT01 は既定 1500 → パディングしたハローが合わない?"
  X configure 'interface Bundle-Ether1' 'mtu 1500' commit 'show configuration failed' end
  X 'show interfaces Bundle-Ether1 | include MTU' 'show ipv4 interface Bundle-Ether1 | include MTU' 'clear isis process' 
  sleep 60
  X 'show isis adjacency' 'show isis interface Bundle-Ether1' 'show isis statistics Bundle-Ether1' 'show logging last 15'
  R "$R1" 'show clns neighbors detail' 'show clns interface Port-channel1' 'show logging | include ISIS|CLNS'

  H "c-3: 逆向き= XR の束に mtu 9000(RT01 は 1500)"
  X configure 'interface Bundle-Ether1' 'mtu 9000' commit 'show configuration failed' end
  X 'clear isis process'
  sleep 60
  X 'show isis adjacency' 'show isis interface Bundle-Ether1 | include "MTU|Adjacenc|LSP|pad"' 'show logging last 15'
  R "$R1" 'show clns neighbors detail' 'show logging | include ISIS|CLNS'

  H "c-4: 元へ(mtu を外す)"
  X configure 'interface Bundle-Ether1' 'no mtu' commit end
  sleep 45
  X 'show isis adjacency'
  R "$R1" 'show clns neighbors'
}

d() {
  H "d-0: 相手役の SPF/LSP 生成の既定(IOS XE は routing-default-optimize で 50/200/5000 ms のはず)→ 明示で詰める"
  for h in "$R1" "$R2"; do
    R "$h" 'show running-config all | include spf-interval|prc-interval|lsp-gen-interval|routing-default-optimize'
  done
  for h in "$R1" "$R2"; do
    R "$h" 'configure terminal' 'router isis CORE' 'spf-interval 1 50 200' 'prc-interval 1 50 200' 'lsp-gen-interval 1 50 200' 'end' \
      'show isis protocol'
  done
  X 'show isis protocol' 'show running-config router isis'

  H "d-1: BFD なし。SW01-RT02 のリンクで全パケットを捨てる(両端のポートは up のまま)"
  LINK RT02 SW01 show
  PING 20000 > /tmp/xrha-ping-d1.txt & P=$!
  sleep 5; LINK RT02 SW01 loss 100; date +%T
  sleep 20; X "show interfaces $G2 | include \"line protocol\"" 'show isis adjacency'
  R "$R2" 'show interfaces Ethernet0/0 | include line protocol' 'show clns neighbors'
  wait $P; cat /tmp/xrha-ping-d1.txt
  X 'show isis adjacency' 'show route ipv4 10.20.0.0/16' 'show logging last 10'
  LINK RT02 SW01 clear; sleep 45; X 'show isis adjacency'

  H "d-2: BFD を主経路に(XR= IS-IS の IF に・RT02= IF の BFD+isis bfd)。100 ms × 3"
  X configure 'router isis CORE' "interface $G2" 'bfd minimum-interval 100' 'bfd multiplier 3' 'bfd fast-detect ipv4' \
    commit 'show configuration failed' end
  R "$R2" 'configure terminal' 'interface Ethernet0/0' 'bfd interval 100 min_rx 100 multiplier 3' 'isis bfd' 'end'
  sleep 30
  X 'show bfd session' 'show bfd session detail' 'show isis interface '"$G2"' | include BFD'
  R "$R2" 'show bfd neighbors details'

  H "d-3: BFD あり。同じ黙った故障"
  PING 20000 > /tmp/xrha-ping-d3.txt & P=$!
  sleep 5; LINK RT02 SW01 loss 100; date +%T
  sleep 10; X 'show bfd session' 'show isis adjacency'
  wait $P; cat /tmp/xrha-ping-d3.txt
  X 'show logging last 15'
  LINK RT02 SW01 clear; sleep 45; X 'show isis adjacency' 'show bfd session'

  H "d-4: 下限を探る(50/15/3 ms)"
  for ms in 50 15 3; do
    X configure 'router isis CORE' "interface $G2" "bfd minimum-interval $ms" commit 'show configuration failed' end
  done
  sleep 10; X 'show bfd session detail | include "interval|Async|State|Local|Remote"'
  X configure 'router isis CORE' "interface $G2" 'bfd minimum-interval 100' commit end

  H "d-5: 束の上の BFD(IS-IS の束 IF に fast-detect= BLB)"
  X configure 'router isis CORE' 'interface Bundle-Ether1' 'bfd minimum-interval 100' 'bfd multiplier 3' 'bfd fast-detect ipv4' \
    commit 'show configuration failed' end
  R "$R1" 'configure terminal' 'interface Port-channel1' 'bfd interval 100 min_rx 100 multiplier 3' 'isis bfd' 'end'
  sleep 30
  X 'show bfd session' 'show bfd session detail | include "Bundle|State|Type|BLB|BoB"' 'show running-config bfd' 'show logging last 10'
  R "$R1" 'show bfd neighbors details'
  H "d-6: BLB に bfd multipath include location が要るか(ASR9K/NCS の文書では無いとセッションを作らない)"
  X configure 'bfd' 'multipath include location 0/0/CPU0' commit 'show configuration failed' end
  sleep 30
  X 'show bfd session' 'show bfd session detail | include "Bundle|State|Type|BLB|BoB"'
  R "$R1" 'show bfd neighbors details'
  H "d-7: BoB(メンバーごと)を XR だけに入れてみる(相手は対応しない見込み= 受け付けと状態だけ)"
  X configure 'interface Bundle-Ether1' 'bfd address-family ipv4 fast-detect' 'bfd address-family ipv4 destination 10.0.1.11' \
    'bfd address-family ipv4 minimum-interval 150' commit 'show configuration failed' end
  sleep 30
  X 'show bfd session' 'show bundle Bundle-Ether1 | include "Status|Gi|BFD"' 'show logging last 10'
  X configure 'interface Bundle-Ether1' 'no bfd' commit end
  sleep 20; X 'show bundle Bundle-Ether1 | include "Status|Gi"'
}

d2() {
  H "d2-1: 束の上の IS-IS が Init のまま(BFD 列も Init)。RT01 の isis bfd を外すと?"
  X 'show isis adjacency' 'show isis adjacency detail | include "RT01|State|BFD|Topology"'
  R "$R1" 'show running-config interface Port-channel1' 'configure terminal' 'interface Port-channel1' 'no isis bfd' 'end'
  sleep 30
  X 'show isis adjacency' 'show bfd session'
  H "d2-2: XR 側の束の BFD も外す(片付け)"
  X configure 'router isis CORE' 'interface Bundle-Ether1' 'no bfd fast-detect ipv4' 'no bfd minimum-interval' 'no bfd multiplier' \
    commit 'show configuration failed' end
  sleep 20; X 'show isis adjacency' 'show bfd session'

  H "d2-3: 主経路で切り分け= RT02 から isis bfd だけ外す(IF の bfd interval は残す)"
  R "$R2" 'configure terminal' 'interface Ethernet0/0' 'no isis bfd' 'end'
  sleep 30; X 'show isis adjacency' 'show bfd session'
  X configure 'router isis CORE' "interface $G2" 'shutdown' commit end; sleep 5
  X configure 'router isis CORE' "interface $G2" 'no shutdown' commit end; sleep 40
  X 'show isis adjacency' 'show bfd session' 'show isis adjacency detail | include "RT02|State|BFD"'
  H "d2-4: RT02 に isis bfd を戻し、IF の bfd interval を外す(TLV は出すが BFD を張れない)"
  R "$R2" 'configure terminal' 'interface Ethernet0/0' 'isis bfd' 'no bfd interval 100 min_rx 100 multiplier 3' 'end' \
    'show running-config interface Ethernet0/0'
  sleep 30; X 'show isis adjacency' 'show bfd session'
  X configure 'router isis CORE' "interface $G2" 'shutdown' commit end; sleep 5
  X configure 'router isis CORE' "interface $G2" 'no shutdown' commit end; sleep 40
  X 'show isis adjacency' 'show bfd session' 'show logging last 8'
  R "$R2" 'show clns neighbors' 'show bfd neighbors'
  H "d2-5: 元へ(RT02 に bfd interval)"
  R "$R2" 'configure terminal' 'interface Ethernet0/0' 'bfd interval 100 min_rx 100 multiplier 3' 'end'
  sleep 40; X 'show isis adjacency' 'show bfd session'
}

e() {
  H "e-0: XR01-RT02 の iBGP(ループバック間)"
  X configure 'router bgp 65000' 'bgp router-id 10.255.0.1' 'address-family ipv4 unicast' 'exit' \
    'neighbor 10.255.0.12' 'remote-as 65000' 'update-source Loopback0' 'address-family ipv4 unicast' commit 'show configuration failed' end
  sleep 40
  X 'show bgp ipv4 unicast summary' 'show bgp ipv4 unicast neighbors 10.255.0.12 | include "state|Graceful|restart"'
  R "$R2" 'show ip bgp summary' 'show ip bgp neighbors 10.255.0.1 | include state|Graceful|restart'

  H "e-1: NSF なしで process restart isis(RT01 の隣接と ping)"
  R "$R1" 'show clns neighbors' 'show isis nsf'
  PING 20000 > /tmp/xrha-ping-e1.txt & P=$!
  sleep 5; X 'process restart isis' ; date +%T
  sleep 30; X 'show processes isis | include "PID|Respawn|Process state|Last started"' 'show isis adjacency' \
    'show isis protocol | include -i "startup|nsf"'
  wait $P; cat /tmp/xrha-ping-e1.txt
  R "$R1" 'show clns neighbors' 'show logging | include ISIS|CLNS'

  H "e-2: nsf ietf(XR)。IOL は既定のまま(ヘルパー)"
  X configure 'router isis CORE' 'nsf ietf' commit 'show configuration failed' end
  sleep 15
  X 'show isis protocol | include -i nsf' 
  PING 20000 > /tmp/xrha-ping-e2.txt & P=$!
  sleep 5; X 'process restart isis' ; date +%T
  sleep 40; X 'show isis adjacency' 'show isis protocol | include -i "startup|nsf|restart"' 'show logging last 20'
  wait $P; cat /tmp/xrha-ping-e2.txt
  R "$R1" 'show clns neighbors' 'show isis nsf' 'show logging | include ISIS|CLNS|NSF'
  R "$R2" 'show clns neighbors'

  H "e-3: BGP。XR に bgp graceful-restart・RT02 は未設定 → 能力の交換は?"
  X configure 'router bgp 65000' 'bgp graceful-restart' commit 'show configuration failed' end
  sleep 5; X 'clear bgp ipv4 unicast 10.255.0.12'
  sleep 40
  X 'show bgp ipv4 unicast neighbors 10.255.0.12 | include "Graceful|restart|state"'
  R "$R2" 'show ip bgp neighbors 10.255.0.1 | include Graceful|restart|state'

  H "e-4: RT02 にも bgp graceful-restart → process restart bgp(RT02 で経路が stale で残るか)"
  R "$R2" 'configure terminal' 'router bgp 65000' 'bgp graceful-restart' 'end' 'clear ip bgp 10.255.0.1'
  sleep 40
  R "$R2" 'show ip bgp neighbors 10.255.0.1 | include Graceful|restart|state'
  X 'process restart bgp'; date +%T
  sleep 3; R "$R2" 'show ip bgp' 'show ip bgp summary' 'show logging | include BGP'
  sleep 40; R "$R2" 'show ip bgp summary' 'show logging | include BGP'

  H "e-5: NSR(RP 1 枚)の設定と表示。設定前の BGP NSR の既定(公式どうしで食い違い)"
  X 'show bgp process | include -i "non-stop|nsr"'
  X configure 'router isis CORE' 'nsr' root 'router bgp 65000' 'nsr' commit 'show configuration failed' end
  sleep 10
  X 'show isis nsr status' 'show bgp nsr' 'show redundancy summary' 'show isis protocol | include -i "nsr|nsf|startup"' \
    'show bgp process | include -i "non-stop|nsr"'
  PING 20000 > /tmp/xrha-ping-e5.txt & P=$!
  sleep 5; X 'process restart isis' ; date +%T
  sleep 40; X 'show isis adjacency' 'show logging last 20'
  wait $P; cat /tmp/xrha-ping-e5.txt
  R "$R1" 'show clns neighbors' 'show logging | include ISIS|CLNS|NSF'
}

e2() {
  H "e2-0: XR から BGP で広告する経路(Loopback10・IS-IS には載せない)。RT02 の GR 既定値も見る"
  X configure 'interface Loopback10' 'ipv4 address 10.30.0.1 255.255.0.0' root 'router bgp 65000' 'address-family ipv4 unicast' \
    'network 10.30.0.0/16' commit 'show configuration failed' end
  sleep 20
  R "$R2" 'show ip bgp' 'show running-config all | include graceful' 'show ip bgp neighbors 10.255.0.1 | include Graceful|restart|stale'
  X 'show bgp ipv4 unicast neighbors 10.255.0.12 | include "Graceful|restart|stale|preserved"'
  H "e2-1: GR あり(両側)で process restart bgp → RT02 で S(Stale)が付いて残るか・XR の RIB/FIB は"
  X 'process restart bgp'; date +%T
  for i in 1 2 3 4; do sleep 3; date +%T; R "$R2" 'show ip bgp | begin Network' 'show ip route 10.30.0.0'; done
  X 'show route ipv4 10.20.0.0/16' 'show cef ipv4 10.20.0.0/16 | include "via|path"'
  sleep 40; R "$R2" 'show ip bgp summary | begin Neighbor' 'show logging | include BGP' 
  X 'show bgp ipv4 unicast neighbors 10.255.0.12 | include "Graceful|restart|preserved|state"'
  H "e2-2: RT02 の GR を外す → 同じ再起動(経路はすぐ消えるはず)"
  R "$R2" 'configure terminal' 'router bgp 65000' 'no bgp graceful-restart' 'end' 'clear ip bgp 10.255.0.1'
  sleep 40; R "$R2" 'show ip bgp neighbors 10.255.0.1 | include Graceful|state'
  X 'process restart bgp'; date +%T
  for i in 1 2 3; do sleep 3; date +%T; R "$R2" 'show ip bgp | begin Network' 'show ip route 10.30.0.0'; done
  sleep 40; R "$R2" 'show ip bgp summary | begin Neighbor'
  H "e2-3: RT02 に GR を戻す"
  R "$R2" 'configure terminal' 'router bgp 65000' 'bgp graceful-restart' 'end' 'clear ip bgp 10.255.0.1'
  sleep 40; R "$R2" 'show ip bgp neighbors 10.255.0.1 | include Graceful|state'
}

f() {
  H "f-1: オーバーロード ビット(手動)→ RT01 から RT02 への経路は予備へ・XR01 宛ては残る"
  X configure 'router isis CORE' 'set-overload-bit' commit 'show configuration failed' end
  sleep 10
  X 'show isis database'
  R "$R1" 'show isis database' 'show ip route 10.20.0.0' 'show ip route 10.255.0.1' \
    'traceroute 10.20.0.1 source Loopback1 numeric timeout 1 probe 1' 'ping 10.255.0.1 source Loopback1'
  X configure 'router isis CORE' 'no set-overload-bit' commit end

  H "f-2: on-startup wait-for-bgp → process restart isis(NSF ietf あり= 公式は NSF の再起動では使わないと書く)"
  X configure 'router isis CORE' 'set-overload-bit on-startup wait-for-bgp' commit 'show configuration failed' end
  X 'show running-config router isis' 'process restart isis'; date +%T
  for i in 1 2 3; do sleep 10; date +%T; X 'show isis database XR01.00-00' 'show isis protocol | include "startup|verload"'; done

  H "f-2b: NSF と NSR を外して process restart isis(冷えた起動で OL が立つか)"
  X configure 'router isis CORE' 'no nsf' 'no nsr' commit 'show configuration failed' end
  X 'process restart isis'; date +%T
  for i in 1 2 3 4 5 6; do sleep 10; date +%T; X 'show isis database XR01.00-00' 'show isis protocol | include "startup|verload"'; done
  R "$R1" 'show isis database'

  H "f-2c: clear isis process でも立つか"
  X 'clear isis process'; date +%T
  for i in 1 2 3; do sleep 10; date +%T; X 'show isis database XR01.00-00'; done

  H "f-3: on-startup 60(秒)→ process restart isis"
  X configure 'router isis CORE' 'set-overload-bit on-startup 60' commit 'show configuration failed' end
  X 'process restart isis'; date +%T
  for i in 1 2 3 4 5 6 7 8; do sleep 10; date +%T; X 'show isis database XR01.00-00'; done
  X configure 'router isis CORE' 'no set-overload-bit' commit end
}

# 再起動から n 秒ごとに XR01 の LSP の ATT/P/OL と起動の種類を見る
OLW() { local step=$1 n=$2 t0=$(date +%s) i
  for i in $(seq 1 "$n"); do sleep "$step"
    echo "+$(( $(date +%s) - t0 ))s $(X 'show isis database XR01.00-00' | grep -E '^XR01\.00-00') | $(X 'show isis protocol' | grep -E 'startup mode|Overload Bit' | tr -s ' ' | tr '\n' ' ')"
  done; }

f2() {
  H "f2-1: 設定なし(set-overload-bit なし)・nsf ietf あり → process restart isis。再起動の間に OL が立つか"
  X configure 'router isis CORE' 'no set-overload-bit' commit end 'show running-config router isis | include "nsf|nsr|overload"'
  X 'process restart isis'; date +%T; OLW 3 10
  H "f2-2: 設定なし・NSF なし(冷えた起動)"
  X configure 'router isis CORE' 'no nsf ietf' commit 'show configuration failed' end 'show running-config router isis | include "nsf|nsr|overload"'
  X 'process restart isis'; date +%T; OLW 3 10
  H "f2-3: NSF なし+on-startup 60 → process restart isis(60 秒立つか)"
  X configure 'router isis CORE' 'set-overload-bit on-startup 60' commit end 'show running-config router isis | include "nsf|nsr|overload"'
  X 'process restart isis'; date +%T; OLW 10 10
  H "f2-4: NSF なし+on-startup wait-for-bgp"
  X configure 'router isis CORE' 'set-overload-bit on-startup wait-for-bgp' commit end
  X 'process restart isis'; date +%T; OLW 5 12
  X 'show bgp ipv4 unicast summary | include "10.255|BGP is|converge"'
  H "f2-5: NSF なし+on-startup 60 → clear isis process(確認に yes)"
  X configure 'router isis CORE' 'set-overload-bit on-startup 60' commit end
  X 'clear isis process' 'yes'; date +%T; OLW 10 8
  H "f2-6: NSF あり+on-startup 60 → process restart isis(公式= NSF の再起動では使わない)"
  X configure 'router isis CORE' 'nsf ietf' commit end
  X 'process restart isis'; date +%T; OLW 10 8
  H "f2-7: 片付け(overload を外す・nsf ietf は残す)"
  X configure 'router isis CORE' 'no set-overload-bit' commit end 'show running-config router isis'
}

g() {
  H "g-1: TS 候補= メンバを bundle id 1(モード省略)+束に mtu 1500 → 症状"
  X configure "interface $G0" 'no bundle id' 'bundle id 1' root "interface $G1" 'no bundle id' 'bundle id 1' root \
    'interface Bundle-Ether1' 'mtu 1500' commit 'show configuration failed' end "show running-config interface $G0"
  sleep 60
  X 'show bundle Bundle-Ether1 | include "Status|LACP|Gi0"' 'show isis adjacency' 'ping 10.0.1.11 count 5'
  R "$R1" 'show etherchannel summary | include Po1' 'show clns neighbors'
  H "g-2: モードだけ直す(active)→ 次の症状(MTU)が見えるか"
  X configure "interface $G0" 'no bundle id' 'bundle id 1 mode active' root "interface $G1" 'no bundle id' 'bundle id 1 mode active' commit end
  sleep 60
  X 'show bundle Bundle-Ether1 | include "Status|LACP|Gi0"' 'show isis adjacency' 'ping 10.0.1.11 count 5' \
    'show isis interface Bundle-Ether1 | include "MTU|Rejected"'
  R "$R1" 'show clns neighbors'
  H "g-3: MTU を直す"
  X configure 'interface Bundle-Ether1' 'no mtu' commit end
  sleep 45; X 'show isis adjacency'; R "$R1" 'show clns neighbors'
}

for p in "$@"; do "$p"; done
