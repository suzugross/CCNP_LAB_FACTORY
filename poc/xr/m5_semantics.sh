#!/bin/bash
# BL-246 §15 PoC: M5 の前提になる RPL の挙動を XRT-03 の XR01 で確かめる。usage: source poc/xr/env.sh; poc/xr/m5_semantics.sh <XR01> <phase…>
cd "$(dirname "$0")/../.."
XR=$1; shift
X() { .venv/bin/python poc/xr/xrsh.py "$XR" "$@" 2>&1 | grep -vE "^\s*$|^Sun Oct|config[^#]*\)#\s*$"; }
for p in "$@"; do case $p in
init)
  echo "######## init: 出発点の見え方"
  X 'show bgp ipv4 unicast summary' 'show bgp neighbor 10.0.11.2 | include "olic|denied|No policy|By policy"' \
    'show bgp neighbor 10.0.12.2 | include "olic|denied|No policy|By policy"' ;;
setonly)
  echo "######## setonly: set だけ(pass なし)のポリシーを ISP-A の入力に"
  X configure 'route-policy T-SET' 'set local-preference 150' end-policy \
    'router bgp 65000' 'neighbor 10.0.11.2' 'address-family ipv4 unicast' 'route-policy T-SET in' commit end
  sleep 15; X 'show bgp ipv4 unicast neighbors 10.0.11.2 routes' 'show bgp neighbor 10.0.11.2 | include "denied|By policy"'
  echo "######## ifset: 条件つき set だけ(合わない経路は?)"
  X configure 'route-policy T-SET' 'if destination in (11.0.0.0/8) then' 'set local-preference 150' endif end-policy commit end
  sleep 15; X 'show bgp ipv4 unicast neighbors 10.0.11.2 routes' ;;
comm)
  echo "######## comm: 顧客の入力に as-path・community の判定と削除"
  X configure 'as-path-set CUST-AS' "ios-regex '^65201(_65201)*\$'" end-set \
    'route-policy T-CUST' 'if as-path in CUST-AS then' 'pass' 'endif' end-policy \
    'route-policy T-PASS' pass end-policy \
    'router bgp 65000' 'neighbor 10.0.13.2' 'address-family ipv4 unicast' 'route-policy T-CUST in' 'route-policy T-PASS out' commit end
  sleep 15; X 'show bgp ipv4 unicast neighbors 10.0.13.2 routes' 'show bgp ipv4 unicast 198.51.100.0/24' 'show bgp ipv4 unicast 198.51.101.0/24'
  echo "######## comm2: originates-from・community の条件・delete community in"
  X configure 'route-policy T-CUST' "if as-path originates-from '65201' then" 'pass' 'endif' end-policy commit end
  sleep 10; X 'show bgp ipv4 unicast neighbors 10.0.13.2 routes'
  X configure 'community-set SIG' '65000:*' end-set \
    'route-policy T-OUT' 'if community matches-any (65000:1002) then' 'drop' 'endif' 'delete community in SIG' 'pass' end-policy \
    'router bgp 65000' 'neighbor 10.0.12.2' 'address-family ipv4 unicast' 'route-policy T-OUT out' 'send-community-ebgp' \
    root 'router bgp 65000' 'neighbor 10.0.11.2' 'address-family ipv4 unicast' 'route-policy T-OUT out' 'send-community-ebgp' commit 'show configuration failed' end
  sleep 15; X 'show bgp ipv4 unicast neighbors 10.0.12.2 advertised-routes' 'show bgp ipv4 unicast neighbors 10.0.11.2 advertised-routes' ;;
esac; done
