#!/bin/bash
# XRT-04 の模範解(learn.yml の solution と同じもの)を管理 IF の SSH で XR01 に入れる。PoC/E2E 用。
# usage: source poc/xr/env.sh; poc/xr/solve_xrt04.sh <XR01 の管理 IP> [m4t1 … m4t4](既定= 全部)
cd "$(dirname "$0")/../.."
H=${1:?XR01 mgmt ip}; shift; steps=${*:-m4t1 m4t2 m4t3 m4t4}
X() { .venv/bin/python poc/xr/xrsh.py "$H" "$@" 2>&1 | grep -iE "^%|fail|error" || true; }
for s in $steps; do case $s in
m4t1)
  X configure 'router isis CORE' 'no net 49.0001.0000.0000.0001.00' 'net 49.0001.0102.5500.0001.00' \
    'interface Loopback0' 'address-family ipv4 unicast' exit 'address-family ipv6 unicast' root \
    'router isis CORE' 'interface GigabitEthernet0/0/0/0' 'circuit-type level-1' 'point-to-point' 'address-family ipv4 unicast' exit 'address-family ipv6 unicast' root \
    'router isis CORE' 'interface GigabitEthernet0/0/0/1' 'circuit-type level-2-only' 'point-to-point' 'address-family ipv4 unicast' exit 'address-family ipv6 unicast' root \
    'router isis CORE' 'interface GigabitEthernet0/0/0/2' 'circuit-type level-2-only' 'point-to-point' 'address-family ipv4 unicast' exit 'address-family ipv6 unicast' root \
    commit end ;;
m4t2)
  X configure 'router isis CORE' 'address-family ipv4 unicast' 'metric-style wide level 2' root \
    'router isis CORE' 'interface GigabitEthernet0/0/0/2' 'address-family ipv4 unicast' 'metric 1000' commit end ;;
m4t3)
  X configure 'router isis CORE' 'address-family ipv6 unicast' 'single-topology' root \
    'router isis CORE' 'interface GigabitEthernet0/0/0/2' 'address-family ipv6 unicast' 'metric 1000' commit end ;;
m4t4)
  X configure 'prefix-set LOOPBACKS' '10.255.0.0/24 eq 32,' '2001:db8:255::/64 eq 128' end-set \
    'route-policy LEAK-LOOPBACKS' 'if destination in LOOPBACKS then' 'pass' 'endif' end-policy \
    'router isis CORE' 'address-family ipv4 unicast' 'propagate level 2 into level 1 route-policy LEAK-LOOPBACKS' root \
    'router isis CORE' 'address-family ipv6 unicast' 'propagate level 2 into level 1 route-policy LEAK-LOOPBACKS' commit end ;;
*) echo "unknown step $s"; exit 2 ;;
esac; done
