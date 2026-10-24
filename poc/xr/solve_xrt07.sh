#!/bin/bash
# XRT-07 の模範解(learn.yml の solution と同じもの)を管理 IF の SSH で XR01 に入れる。PoC/E2E 用。
# usage: source poc/xr/env.sh; poc/xr/solve_xrt07.sh <XR01 の管理 IP> [m8t1 … m8t5](既定= 全部)
#   誤答の確かめ用: m8t1-if(IF だけ足して転送アドレスはそのまま)・m8t2-global(全体の既定パスワード= RT01 も落ちる)・m8t2-global-undo・
#                   m8t3-nodelay(遅延なし)・m8t3-one(PRIMARY だけ同期)・m8t4-all(全員に保護・最長 10 分)・m8t4-default(ACL も時間もなし)・
#                   m8t5-oam(mpls oam だけ)・m8t5-null(explicit-null だけ)・undo-<課題>(その課題の設定を外す)
#   別解: m8t1-auto(IS-IS の auto-config)・m8t1-explicit(router-id と転送アドレスを Lo0 に明示)
cd "$(dirname "$0")/../.."
H=${1:?XR01 mgmt ip}; shift; steps=${*:-m8t1 m8t2 m8t3 m8t4 m8t5}
X() { .venv/bin/python poc/xr/xrsh.py "$H" "$@" 2>&1 | grep -iE "^%|fail|error|invalid" || true; }
G0=GigabitEthernet0/0/0/0 G1=GigabitEthernet0/0/0/1
for s in $steps; do case $s in
m8t1)
  X configure 'mpls ldp' "interface $G0" root 'mpls ldp' "interface $G1" root \
    'mpls ldp' 'address-family ipv4' 'no discovery transport-address' commit end ;;
m8t1-if)
  X configure 'mpls ldp' "interface $G0" root 'mpls ldp' "interface $G1" commit end ;;
m8t1-auto)
  X configure 'router isis CORE' 'address-family ipv4 unicast' 'mpls ldp auto-config' root \
    'mpls ldp' 'address-family ipv4' 'no discovery transport-address' commit end ;;
m8t1-explicit)
  X configure 'mpls ldp' 'router-id 10.255.0.1' "interface $G0" root 'mpls ldp' "interface $G1" root \
    'mpls ldp' 'address-family ipv4' 'discovery transport-address 10.255.0.1' commit end ;;
undo-m8t1)
  X configure 'mpls ldp' "no interface $G0" "no interface $G1" 'address-family ipv4' 'discovery transport-address 10.255.255.1' commit end ;;
m8t2)
  X configure 'mpls ldp' 'neighbor 10.255.0.13:0 password clear CoreLdp-2026' root \
    'mpls ldp' 'address-family ipv4' 'label' 'local' 'allocate for host-routes' commit end ;;
m8t2-global)
  X configure 'mpls ldp' 'neighbor password clear CoreLdp-2026' root \
    'mpls ldp' 'address-family ipv4' 'label' 'local' 'allocate for host-routes' commit end ;;
m8t2-global-undo)
  X configure 'mpls ldp' 'no neighbor password' commit end ;;
undo-m8t2)
  X configure 'mpls ldp' 'no neighbor 10.255.0.13:0 password' 'no neighbor password' 'address-family ipv4' 'label' 'local' 'no allocate' commit end ;;
m8t3)
  X configure 'router isis CORE' "interface $G0" 'address-family ipv4 unicast' 'mpls ldp sync' root \
    'router isis CORE' "interface $G1" 'address-family ipv4 unicast' 'mpls ldp sync' root \
    'mpls ldp' 'igp sync delay on-session-up 10' commit end ;;
m8t3-nodelay)
  X configure 'router isis CORE' "interface $G0" 'address-family ipv4 unicast' 'mpls ldp sync' root \
    'router isis CORE' "interface $G1" 'address-family ipv4 unicast' 'mpls ldp sync' commit end ;;
m8t3-one)
  X configure 'router isis CORE' "interface $G0" 'address-family ipv4 unicast' 'mpls ldp sync' root \
    'mpls ldp' 'igp sync delay on-session-up 10' commit end ;;
undo-m8t3)
  X configure 'router isis CORE' "interface $G0" 'address-family ipv4 unicast' 'no mpls ldp sync' root \
    'router isis CORE' "interface $G1" 'address-family ipv4 unicast' 'no mpls ldp sync' root \
    'mpls ldp' 'no igp sync delay on-session-up' commit end ;;
m8t4)
  X configure 'ipv4 access-list LDP-SP' '10 permit ipv4 host 10.255.0.11 any' root \
    'mpls ldp' 'session protection for LDP-SP duration 600' commit end ;;
m8t4-all)
  X configure 'mpls ldp' 'session protection duration 600' commit end ;;
m8t4-default)
  X configure 'mpls ldp' 'session protection' commit end ;;
undo-m8t4)
  X configure 'mpls ldp' 'no session protection' root 'no ipv4 access-list LDP-SP' commit end ;;
m8t5)
  X configure 'mpls oam' root 'mpls ldp' 'address-family ipv4' 'label' 'local' 'advertise' 'explicit-null' commit end ;;
m8t5-oam)
  X configure 'mpls oam' commit end ;;
m8t5-null)
  X configure 'mpls ldp' 'address-family ipv4' 'label' 'local' 'advertise' 'explicit-null' commit end ;;
undo-m8t5)
  X configure 'no mpls oam' root 'mpls ldp' 'address-family ipv4' 'label' 'local' 'advertise' 'no explicit-null' commit end ;;
*) echo "unknown step $s"; exit 2 ;;
esac; done
