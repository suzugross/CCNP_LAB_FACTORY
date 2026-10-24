#!/bin/bash
# XRT-06 の模範解(learn.yml の solution と同じもの)を管理 IF の SSH で XR01 に入れる。PoC/E2E 用。
# usage: source poc/xr/env.sh; poc/xr/solve_xrt06.sh <XR01 の管理 IP> [m7t1 … m7t5](既定= 全部)
#   誤答の確かめ用: m7t1-pad(MTU を直さずハローのパディングを切る)・m7t1-pad-undo・
#                   m7t2-min(最低本数だけ)・m7t2-lacp(LACP の周期だけ)・m7t2-undo・
#                   m7t3-no(オーバーロードを外すだけ)・m7t3-60(on-startup 60)・
#                   m7t4-off(BFD を外す)・m7t5-noreset(GR を入れてセッションをやり直さない)・m7t5-off(NSF と GR を外す)
#   別解: m7t1-passive(XR を passive)・m7t4-default(BFD の間隔を既定のまま)・m7t5-cisco(nsf cisco)
cd "$(dirname "$0")/../.."
H=${1:?XR01 mgmt ip}; shift; steps=${*:-m7t1 m7t2 m7t3 m7t4 m7t5}
X() { .venv/bin/python poc/xr/xrsh.py "$H" "$@" 2>&1 | grep -iE "^%|fail|error|invalid" || true; }
G0=GigabitEthernet0/0/0/0 G1=GigabitEthernet0/0/0/1 G2=GigabitEthernet0/0/0/2
for s in $steps; do case $s in
m7t1)
  X configure "interface $G0" 'bundle id 1 mode active' root "interface $G1" 'bundle id 1 mode active' root \
    'interface Bundle-Ether1' 'no mtu' commit end ;;
m7t1-passive)
  X configure "interface $G0" 'bundle id 1 mode passive' root "interface $G1" 'bundle id 1 mode passive' root \
    'interface Bundle-Ether1' 'no mtu' commit end ;;
m7t1-pad)
  X configure "interface $G0" 'bundle id 1 mode active' root "interface $G1" 'bundle id 1 mode active' root \
    'router isis CORE' 'interface Bundle-Ether1' 'hello-padding disable' commit end ;;
m7t1-pad-undo)
  X configure 'router isis CORE' 'interface Bundle-Ether1' 'no hello-padding disable' root 'interface Bundle-Ether1' 'no mtu' commit end ;;
m7t2)
  X configure 'interface Bundle-Ether1' 'bundle minimum-active links 2' root \
    "interface $G0" 'lacp period short' root "interface $G1" 'lacp period short' commit end ;;
m7t2-min)
  X configure 'interface Bundle-Ether1' 'bundle minimum-active links 2' commit end ;;
m7t2-lacp)
  X configure "interface $G0" 'lacp period short' root "interface $G1" 'lacp period short' commit end ;;
m7t2-undo)
  X configure 'interface Bundle-Ether1' 'no bundle minimum-active links' root \
    "interface $G0" 'no lacp period' root "interface $G1" 'no lacp period' commit end ;;
m7t3)
  X configure 'router isis CORE' 'set-overload-bit on-startup wait-for-bgp' commit end ;;
m7t3-no)
  X configure 'router isis CORE' 'no set-overload-bit' commit end ;;
m7t3-60)
  X configure 'router isis CORE' 'set-overload-bit on-startup 60' commit end ;;
m7t4)
  X configure 'router isis CORE' "interface $G2" 'bfd minimum-interval 100' 'bfd multiplier 3' 'bfd fast-detect ipv4' commit end ;;
m7t4-default)
  X configure 'router isis CORE' "interface $G2" 'no bfd minimum-interval' 'no bfd multiplier' 'bfd fast-detect ipv4' commit end ;;
m7t4-off)
  X configure 'router isis CORE' "interface $G2" 'no bfd fast-detect ipv4' 'no bfd minimum-interval' 'no bfd multiplier' commit end ;;
m7t5)
  X configure 'router isis CORE' 'nsf ietf' root 'router bgp 65000' 'bgp graceful-restart' commit end
  X 'clear bgp 10.255.0.12' ;;
m7t5-noreset)
  X configure 'router isis CORE' 'nsf ietf' root 'router bgp 65000' 'bgp graceful-restart' commit end ;;
m7t5-cisco)
  X configure 'router isis CORE' 'nsf cisco' commit end ;;
m7t5-off)
  X configure 'router isis CORE' 'no nsf ietf' 'no nsf cisco' root 'router bgp 65000' 'no bgp graceful-restart' commit end ;;
*) echo "unknown step $s"; exit 2 ;;
esac; done
