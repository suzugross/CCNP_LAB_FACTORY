#!/bin/bash
# XRT-08 の模範解(learn.yml の solution と同じもの)を管理 IF の SSH で XR01 に入れる。PoC/E2E 用。
# usage: source poc/xr/env.sh; poc/xr/solve_xrt08.sh <XR01 の管理 IP> [m8t6 m8t7 m8t8](既定= 全部)
#   誤答の確かめ用: m8t6-nolo(Lo0 をアクセスに載せない)・m8t6-leak(模範解+コアの経路をアクセスへ再配送)・
#                   m8t7-enforce(enforce だけ)・m8t7-alloc(allocate-label だけ)・m8t8-out(allocate-label all のまま送る経路だけ絞る)・
#                   undo-<課題>(その課題の設定を外す)
#   別解: m8t6-two(Lo0 を CORE と ACCESS の両方のインスタンスに載せる)。M8-7 の模範解は allocate-label all、M8-8 で route-policy に替える
cd "$(dirname "$0")/../.."
H=${1:?XR01 mgmt ip}; shift; steps=${*:-m8t6 m8t7 m8t8}
X() { .venv/bin/python poc/xr/xrsh.py "$H" "$@" 2>&1 | grep -iE "^%|fail|error|invalid" || true; }
G2=GigabitEthernet0/0/0/2
ISIS_ACCESS=('router isis ACCESS' 'is-type level-2-only' 'net 49.0002.0100.0000.0001.00' 'log adjacency changes'
  'address-family ipv4 unicast' 'metric-style wide' 'exit'
  "interface $G2" 'point-to-point' 'address-family ipv4 unicast' 'metric 10' 'root')
for s in $steps; do case $s in
m8t6)
  X configure 'route-policy ABR-LOOPBACK' 'if destination in (10.255.0.1/32) then' 'pass' 'endif' 'end-policy' \
    "${ISIS_ACCESS[@]}" 'router isis ACCESS' 'address-family ipv4 unicast' 'redistribute connected route-policy ABR-LOOPBACK' 'root' \
    'mpls ldp' "interface $G2" commit end ;;
m8t6-two)
  X configure "${ISIS_ACCESS[@]}" 'router isis ACCESS' 'interface Loopback0' 'passive' 'address-family ipv4 unicast' 'root' \
    'mpls ldp' "interface $G2" commit end ;;
m8t6-nolo)
  X configure "${ISIS_ACCESS[@]}" 'mpls ldp' "interface $G2" commit end ;;
m8t6-leak)
  X configure 'route-policy ABR-LOOPBACK' 'if destination in (10.255.0.1/32) then' 'pass' 'endif' 'end-policy' \
    "${ISIS_ACCESS[@]}" 'router isis ACCESS' 'address-family ipv4 unicast' 'redistribute connected route-policy ABR-LOOPBACK' \
    'redistribute isis CORE level-2' 'root' 'mpls ldp' "interface $G2" commit end ;;
undo-m8t6)
  X configure 'no router isis ACCESS' 'no route-policy ABR-LOOPBACK' 'mpls ldp' "no interface $G2" commit end ;;
m8t7)
  X configure 'router bgp 65000' 'ibgp policy out enforce-modifications' 'address-family ipv4 unicast' 'allocate-label all' commit end ;;
m8t7-enforce)
  X configure 'router bgp 65000' 'ibgp policy out enforce-modifications' commit end ;;
m8t7-alloc)
  X configure 'router bgp 65000' 'address-family ipv4 unicast' 'allocate-label all' commit end ;;
undo-m8t7)
  X configure 'router bgp 65000' 'no ibgp policy out enforce-modifications' 'address-family ipv4 unicast' 'no allocate-label' commit end ;;
m8t8)
  X configure 'route-policy LU-LOOPBACKS' 'if destination in (10.255.0.0/24 eq 32) then' 'pass' 'endif' 'end-policy' \
    'router bgp 65000' 'address-family ipv4 unicast' 'allocate-label route-policy LU-LOOPBACKS' commit end ;;
m8t8-out)
  X configure 'route-policy LU-OUT' 'if destination in (10.255.0.0/24 eq 32) then' 'pass' 'endif' 'end-policy' \
    'router bgp 65000' 'neighbor 10.255.0.12' 'address-family ipv4 labeled-unicast' 'route-policy LU-OUT out' 'root' \
    'router bgp 65000' 'neighbor 10.255.0.15' 'address-family ipv4 labeled-unicast' 'route-policy LU-OUT out' commit end ;;
undo-m8t8)
  X configure 'router bgp 65000' 'address-family ipv4 unicast' 'allocate-label all' 'root' \
    'router bgp 65000' 'neighbor 10.255.0.12' 'address-family ipv4 labeled-unicast' 'no route-policy LU-OUT out' 'root' \
    'router bgp 65000' 'neighbor 10.255.0.15' 'address-family ipv4 labeled-unicast' 'no route-policy LU-OUT out' 'root' \
    'no route-policy LU-OUT' commit end ;;
*) echo "unknown step $s"; exit 2 ;;
esac; done
