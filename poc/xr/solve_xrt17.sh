#!/bin/bash
# XRT-17 の模範解(E2E 用・M6-5〜M6-10)。usage: source poc/xr/env.sh; poc/xr/solve_xrt17.sh <s5|s6|s7|s8|s9|s10|all>…
# 値は課題文(problems/XRT-17/task.md)のとおり。読み物の設定例は値をずらしてある(poc/xr/try_xrt17.sh)。
cd "$(dirname "$0")/../.."
PID=${PID:-XRT-17}
M=topologies/_generated/$PID/mgmt_map.yml
ip() { awk -v n="$1:" '$1==n{print $2}' "$M"; }
PE1=$(ip PE1) PE2=$(ip PE2) PE3=$(ip PE3) P1=$(ip P1) RR1=$(ip RR1) CE1=$(ip CE1) X1=$(ip X1) X2=$(ip X2) T=$(ip T)
S() { local h=$1; shift; .venv/bin/python poc/xr/xrsh.py "$h" "$@" 2>&1; }
H() { echo; echo "######## $(date +%T) $*"; }
XC() { local h=$1; shift; S "$h" configure "$@" commit 'show configuration failed' end; }
IC() { local h=$1; shift; S "$h" 'configure terminal' "$@" end; }

s5() {
  H "s5: 追加パス(PE3= send と backup advertise・RR1= send/receive と backup advertise・PE1= receive)→ 張り直し"
  XC "$PE3" 'route-policy ADDPATH-OUT' '  set path-selection backup 1 advertise' 'end-policy' \
            'router bgp 65000' 'address-family ipv4 unicast' 'additional-paths send' 'additional-paths selection route-policy ADDPATH-OUT'
  XC "$RR1" 'route-policy RR-ADDPATH' '  set path-selection backup 1 advertise' 'end-policy' \
            'router bgp 65000' 'address-family ipv4 unicast' 'additional-paths send' 'additional-paths receive' 'additional-paths selection route-policy RR-ADDPATH'
  XC "$PE1" 'router bgp 65000' 'address-family ipv4 unicast' 'additional-paths receive'
  S "$PE3" 'clear bgp 10.255.0.21'; S "$PE1" 'clear bgp 10.255.0.21'
}
s6() {
  H "s6: PIC(PE1= backup 1 install・PE3= 予備の自分の eBGP も install)"
  XC "$PE1" 'route-policy PIC' '  set path-selection backup 1 install' 'end-policy' \
            'router bgp 65000' 'address-family ipv4 unicast' 'additional-paths selection route-policy PIC'
  XC "$PE3" 'route-policy ADDPATH-OUT' '  set path-selection backup 1 advertise install' 'end-policy'
}
s7() {
  H "s7: GTSM(PE2= ttl-security・X1= ttl-security hops 1)"
  XC "$PE2" 'router bgp 65000' 'neighbor 172.16.2.1' 'ttl-security'
  IC "$X1" 'router bgp 65100' 'neighbor 172.16.2.254 ttl-security hops 1'
  S "$PE2" 'clear bgp 172.16.2.1'
}
s8() {
  H "s8: TCP-AO(PE3 と X2)"
  XC "$PE3" 'key chain AS65100-AO' 'key 7' 'key-string clear 5A3C9E107B2D4F6681A0C3E5F7092B4D' 'cryptographic-algorithm AES-128-CMAC-96' \
            'accept-lifetime 00:00:00 january 01 2026 infinite' 'send-lifetime 00:00:00 january 01 2026 infinite' 'exit' 'exit' \
            'tcp ao' 'keychain AS65100-AO' 'key 7 SendID 37 ReceiveID 73' 'exit' 'exit' \
            'router bgp 65000' 'neighbor 172.16.3.1' 'ao AS65100-AO include-tcp-options enable'
  IC "$X2" 'key chain AS65100-AO tcp' 'key 7' 'send-id 73' 'recv-id 37' 'key-string 5A3C9E107B2D4F6681A0C3E5F7092B4D' 'cryptographic-algorithm aes-128-cmac' 'exit' 'exit' \
           'router bgp 65100' 'neighbor 172.16.3.254 ao AS65100-AO include-tcp-options'
  S "$PE3" 'clear bgp 172.16.3.1'
}
s9() {
  H "s9: maximum-prefix(PE1 ← CE1・4 本・75%・restart 2)"
  XC "$PE1" 'router bgp 65000' 'neighbor 172.16.1.1' 'address-family ipv4 unicast' 'maximum-prefix 4 75 restart 2'
}
s10() {
  H "s10: ダンプニング(PE2・半減期 10 分)・集約(PE2 と PE3・192.168.0.0/22 summary-only)"
  XC "$PE2" 'router bgp 65000' 'address-family ipv4 unicast' 'bgp dampening 10' 'aggregate-address 192.168.0.0/22 summary-only'
  XC "$PE3" 'router bgp 65000' 'address-family ipv4 unicast' 'aggregate-address 192.168.0.0/22 summary-only'
}
for p in "$@"; do case $p in all) s5; sleep 30; s6; s7; s8; s9; s10;; *) "$p";; esac; done
