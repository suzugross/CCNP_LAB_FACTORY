#!/bin/bash
# XRT-03 の模範解(learn.yml の solution と同じもの)を管理 IF の SSH で XR01 に入れる。PoC/E2E 用。
# usage: source poc/xr/env.sh; poc/xr/solve_xrt03.sh <XR01 の管理 IP> [m5t1 … m5t4 m6t1 … m6t4](既定= 全部)
cd "$(dirname "$0")/../.."
H=${1:?XR01 mgmt ip}; shift; steps=${*:-m5t1 m5t2 m5t3 m5t4 m6t1 m6t2 m6t3 m6t4}
X() { .venv/bin/python poc/xr/xrsh.py "$H" "$@" 2>&1 | grep -iE "^%|fail|error" || true; }
for s in $steps; do case $s in
m5t1)
  X configure 'prefix-set OWN' '203.0.113.0/24' end-set \
    'route-policy ISP-FILTER' 'if destination in PRIVATE then' 'drop' 'endif' 'pass' end-policy \
    'route-policy ISP-OUT' 'if destination in OWN then' 'pass' 'endif' end-policy \
    'router bgp 65000' 'neighbor 10.0.11.2' 'address-family ipv4 unicast' 'route-policy ISP-FILTER in' 'route-policy ISP-OUT out' root \
    'router bgp 65000' 'neighbor 10.0.12.2' 'address-family ipv4 unicast' 'route-policy ISP-FILTER in' 'route-policy ISP-OUT out' root \
    'no route-policy ISPB-IN' commit end ;;
m5t2)
  X configure 'route-policy ISP-FILTER' 'if destination in PRIVATE or destination in (0.0.0.0/0, 0.0.0.0/0 ge 25) then' 'drop' 'endif' 'pass' end-policy commit end ;;
m5t3)
  X configure 'route-policy ISP-IN($lp, $tag)' 'apply ISP-FILTER' 'set local-preference $lp' 'set community (65000:$tag) additive' end-policy \
    'router bgp 65000' 'neighbor 10.0.11.2' 'address-family ipv4 unicast' 'route-policy ISP-IN(200, 101) in' root \
    'router bgp 65000' 'neighbor 10.0.12.2' 'address-family ipv4 unicast' 'route-policy ISP-IN(100, 102) in' commit end ;;
m5t4)
  X configure 'prefix-set CUST-PFX' '198.51.100.0/23 le 24' end-set \
    "as-path-set CUST-AS" "ios-regex '^65201(_65201)*\$'" end-set \
    'community-set OURS' '65000:*' end-set \
    'route-policy CUST-IN' 'if destination in CUST-PFX and as-path in CUST-AS then' 'pass' 'endif' end-policy \
    'route-policy CUST-OUT' 'pass' end-policy \
    'route-policy ISP-OUT($nosend)' 'if destination in OWN then' 'pass' \
    'elseif destination in CUST-PFX and not community matches-any (65000:$nosend) then' 'delete community in OURS' 'pass' 'endif' end-policy \
    'router bgp 65000' 'neighbor 10.0.11.2' 'address-family ipv4 unicast' 'route-policy ISP-OUT(1001) out' 'send-community-ebgp' root \
    'router bgp 65000' 'neighbor 10.0.12.2' 'address-family ipv4 unicast' 'route-policy ISP-OUT(1002) out' 'send-community-ebgp' root \
    'router bgp 65000' 'neighbor 10.0.13.2' 'address-family ipv4 unicast' 'route-policy CUST-IN in' 'route-policy CUST-OUT out' 'send-community-ebgp' commit end ;;
m6t1)
  X configure 'router bgp 65000' 'neighbor 4.4.4.4' 'update-source Loopback0' 'address-family ipv4 unicast' 'next-hop-self' commit end ;;
m6t2)
  X configure 'route-policy OSPF-TO-BGP' 'if destination in (203.0.113.0/24 ge 25) then' 'pass' 'endif' end-policy \
    'router bgp 65000' 'address-family ipv4 unicast' 'redistribute ospf 1 route-policy OSPF-TO-BGP' commit end ;;
m6t3)
  X configure 'route-policy ISP-OUT($nosend, $prepend)' 'if destination in OWN then' 'prepend as-path own-as $prepend' 'pass' \
    'elseif destination in CUST-PFX and not community matches-any (65000:$nosend) then' 'delete community in OURS' 'prepend as-path own-as $prepend' 'pass' 'endif' end-policy \
    'router bgp 65000' 'neighbor 10.0.11.2' 'address-family ipv4 unicast' 'route-policy ISP-OUT(1001, 0) out' root \
    'router bgp 65000' 'neighbor 10.0.12.2' 'address-family ipv4 unicast' 'route-policy ISP-OUT(1002, 3) out' commit end ;;
m6t4)
  X configure 'router bgp 65000' 'af-group ISP-AF address-family ipv4 unicast' 'send-community-ebgp' 'maximum-prefix 1000 80' exit \
    'neighbor-group ISP' 'address-family ipv4 unicast' 'use af-group ISP-AF' root \
    'router bgp 65000' 'neighbor 10.0.11.2' 'use neighbor-group ISP' 'address-family ipv4 unicast' 'no send-community-ebgp' root \
    'router bgp 65000' 'neighbor 10.0.12.2' 'use neighbor-group ISP' 'address-family ipv4 unicast' 'no send-community-ebgp' commit end ;;
esac; echo "[$s] done"; done
