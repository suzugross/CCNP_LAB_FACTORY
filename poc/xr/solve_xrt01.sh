#!/bin/bash
# XRT-01 の模範解をコンソールから流す(E2E 確認用)。引数= m0 | m1a(M1-1〜3) | m1b(M1-6)
cd "$(dirname "$0")/../.." && source poc/xr/env.sh
X() { .venv/bin/python poc/xr/xrcon.py XRT-01 XR01 "$@" 2>&1 | grep -E "^%|Invalid|Failed|^###.*commit|Rollback|M1-T" | cut -c1-150; }
case "$1" in
m0) X "configure terminal" "interface GigabitEthernet0/0/0/0" "no shutdown" "ipv6 address 2001:db8:12::1/64" "root" \
      "router ospf 1" "no area 1" "area 0" "interface GigabitEthernet0/0/0/0" "network point-to-point" "root" \
      "interface GigabitEthernet0/0/0/1" "vrf CUST-A" "root" \
      "router static" "vrf CUST-A" "address-family ipv4 unicast" "172.16.2.0/24 10.0.13.2" "root" \
      "router static" "address-family ipv4 unicast" "0.0.0.0/0 10.0.12.2" "root" "commit" "end" ;;
m1a) X "configure terminal" "interface GigabitEthernet0/0/0/0" "shutdown" "commit confirmed 30" "sleep 40" "do show configuration commit list 2" \
      "interface Loopback50" "ipv4 address 10.50.50.50 255.255.255.255" "commit confirmed 60 label M1-T1" "commit" "root" \
      "interface Loopback61" "ipv4 address 10.61.61.61 255.255.255.255" "commit label M1-T2A" "root" \
      "interface Loopback62" "ipv4 address 10.62.62.62 255.255.255.255" "commit label M1-T2B" "root" \
      "load rollback changes M1-T2A" "commit" \
      "interface Loopback70" "ipv4 address 10.70.70.70 255.255.255.255" "root" \
      "router bgp 65001" "bgp router-id 1.1.1.1" "address-family ipv4 unicast" "exit" "neighbor 10.0.12.2" "remote-as 65002" "address-family ipv4 unicast" "route-policy RP-IN in" "root" \
      "commit label M1-T3" "route-policy RP-IN" "pass" "end-policy" "commit label M1-T3" "end" ;;
m1b) X "configure terminal" "load rollback changes CHG1003" "commit label M1-T6" "end" ;;
m1c) X "configure terminal" "load rollback changes CHG2001" "commit label M1-T7" "end" ;;
esac
