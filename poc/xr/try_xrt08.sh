#!/bin/bash
# XRT-08 の読み物「M8 — Unified MPLS」の「やってみる」を、解く側と同じ手順で測る(答え合わせの実測)。
# 前提= M8-7 まで解いた状態(poc/xr/solve_xrt08.sh <XR01> m8t6 m8t7)。usage: source poc/xr/env.sh; poc/xr/try_xrt08.sh [t1 t2 t3 t5]
cd "$(dirname "$0")/../.."
M=topologies/_generated/XRT-08/mgmt_map.yml
ip() { awk -v n="$1:" '$1==n{print $2}' "$M"; }
XR=$(ip XR01) R2=$(ip RT02) R4=$(ip RT04) R5=$(ip RT05)
X() { .venv/bin/python poc/xr/xrsh.py "$XR" "$@" 2>&1; }
R() { local h=$1; shift; .venv/bin/python poc/xr/xrsh.py "$h" "$@" 2>&1; }
H() { echo; echo "######## $(date +%T) $*"; }
t1() {
  H "T1(2.2): ACCESS から redistribute connected を外す"
  X configure 'router isis ACCESS' 'address-family ipv4 unicast' 'no redistribute connected' commit end
  for w in 20 40 60 90; do sleep $w; H "T1 +$w 秒のあと"
    X 'show mpls ldp neighbor brief' 'show bgp ipv4 labeled-unicast summary | include 10.255'
    R "$R4" 'show mpls ldp discovery detail' 'show ip route 10.255.0.1' 'show mpls ldp neighbor | include Peer|State'
    R "$R2" 'ping 10.50.0.1 source Loopback100 repeat 5'
  done
  H "T1 戻す"
  X configure 'router isis ACCESS' 'address-family ipv4 unicast' 'redistribute connected route-policy ABR-LOOPBACK' commit end
  sleep 45; X 'show mpls ldp neighbor brief' 'show bgp ipv4 labeled-unicast summary | include 10.255'
  sleep 90; R "$R2" 'show ip bgp summary | begin Neighbor' 'ping 10.50.0.1 source Loopback100 repeat 5'
}
t2() {
  H "T2(3.2): ibgp policy out enforce-modifications を外す"
  X configure 'router bgp 65000' 'no ibgp policy out enforce-modifications' commit end
  sleep 20; R "$R2" 'show ip bgp 10.255.0.15' 'show ip bgp summary | begin Neighbor' 'ping 10.50.0.1 source Loopback100 repeat 5'
  H "T2 戻す"
  X configure 'router bgp 65000' 'ibgp policy out enforce-modifications' commit end
  sleep 30; R "$R2" 'show ip bgp 10.255.0.15' 'show ip bgp summary | begin Neighbor' 'ping 10.50.0.1 source Loopback100 repeat 5'
}
t3() {
  H "T3(3.3): allocate-label を外す"
  X configure 'router bgp 65000' 'address-family ipv4 unicast' 'no allocate-label' commit end
  sleep 20; X 'show bgp ipv4 labeled-unicast 10.255.0.15/32'
  R "$R2" 'show ip bgp labels' 'ping 10.50.0.1 source Loopback100 repeat 5' 'show ip bgp summary | begin Neighbor'
  H "T3 戻す"
  X configure 'router bgp 65000' 'address-family ipv4 unicast' 'allocate-label all' commit end
  sleep 30; R "$R2" 'show ip bgp labels' 'ping 10.50.0.1 source Loopback100 repeat 5'
}
t5() {
  H "T5(5.1): RT05 から RT02 への LSP ping/traceroute"
  R "$R5" 'ping mpls ipv4 10.255.0.12/32 repeat 3' 'ping mpls ipv4 10.255.0.12/32 fec-type bgp repeat 3' \
    'ping mpls ipv4 10.255.0.12/32 fec-type bgp source 10.255.0.15 repeat 3' \
    'traceroute mpls ipv4 10.255.0.12/32 fec-type bgp source 10.255.0.15 timeout 1 ttl 6'
}
for t in ${*:-t1 t2 t3 t5}; do $t; done
