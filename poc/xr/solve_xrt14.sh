#!/bin/bash
# XRT-14 の模範解(learn.yml の solution と同じもの)を管理 IF の SSH で XR01/RR1 に入れる。PoC/E2E 用。
# usage: source poc/xr/env.sh; poc/xr/solve_xrt14.sh [m12t1 m12t2 m12t3 m12t4 m12t5 …](既定= 全部)。管理 IP は _generated の mgmt_map から引く
#   誤答の確かめ用: m12t1-allef(EF を宛てを問わず DSCP 0 に)・m12t1-noremark(契約外の EF を戻さない)・m12t1-noexp(業務の EXP を付けない= 既定の写しで 2)/
#                   m12t2-1r2c(1 速度 2 色= 超過は捨てる)・m12t2-qg(業務に qos-group も付ける= 印が 3 種類でコミット拒否)/
#                   m12t3-php(explicit null を広告しない)・m12t3-noshape(整形なし= 出口の印だけ)/
#                   m12t4-loosecust(CUST1 側も緩い)・m12t4-strictinet(INET 側も厳格)・m12t4-allowdef(INET 側に allow-default)・m12t4-noacl(ACL なし)/
#                   m12t5-noexport(no-export だけ直す)・m12t5-discard(discard だけ・no-export なし)・m12t5-static(XR01 に攻撃元の静的経路を書く)
cd "$(dirname "$0")/../.."
M=topologies/_generated/${PID:-XRT-14}/mgmt_map.yml
ipof() { awk -v n="$1:" '$1==n{print $2}' "$M"; }
X1=$(ipof XR01) R1=$(ipof RR1)
steps=${*:-m12t1 m12t2 m12t3 m12t4 m12t5}
run() { local h=$1; shift; .venv/bin/python poc/xr/xrsh.py "$h" "$@" 2>&1 | grep -iE "^%|fail|error|invalid|!!%" | grep -v "No such configuration" || true; }
XC() { local h=$1; shift; run "$h" configure "$@" commit 'show configuration failed' end; }
CE=GigabitEthernet0/0/0/1 CORE=GigabitEthernet0/0/0/0 CU=GigabitEthernet0/0/0/2 IN=GigabitEthernet0/0/0/3

m12t1() {  # $1= 変種
  local nv=('class NOT-VOICE-EF' 'set dscp default' 'set mpls experimental imposition 0' 'exit')
  local vc=('class VOICE' 'set mpls experimental imposition 5' 'exit')
  local dc=('class DATA' 'set mpls experimental imposition 3' 'exit')
  case $1 in
    allef)    vc=('class VOICE' 'set dscp default' 'set mpls experimental imposition 5' 'exit') ;;
    noremark) nv=('class NOT-VOICE-EF' 'set mpls experimental imposition 0' 'exit') ;;
    noexp)    dc=() ;;
  esac
  XC "$X1" 'ipv4 access-list VOICE-NET' '10 permit ipv4 any 10.46.0.0/16' 'exit' \
    'class-map match-all VOICE' 'match dscp ef' 'match access-group ipv4 VOICE-NET' 'end-class-map' \
    'class-map match-any NOT-VOICE-EF' 'match dscp ef' 'end-class-map' \
    'class-map match-any DATA' 'match dscp af21' 'end-class-map' \
    'policy-map CE1-IN' "${vc[@]}" "${nv[@]}" "${dc[@]}" 'class class-default' 'set mpls experimental imposition 0' 'exit' 'end-policy-map' \
    "interface $CE" 'service-policy input CE1-IN' 'root'
}
m12t2() {
  local p=('police rate 256 kbps peak-rate 512 kbps' 'conform-action transmit' 'exceed-action set dscp af22' 'violate-action drop' 'exit')
  [ "$1" = 1r2c ] && p=('police rate 256 kbps' 'conform-action transmit' 'exceed-action drop' 'exit')
  [ "$1" = qg ] && p=('set qos-group 3' "${p[@]}")
  XC "$X1" 'policy-map CE1-IN' 'class DATA' "${p[@]}" 'exit' 'end-policy-map'
}
m12t3() {
  [ "$1" != php ] && XC "$X1" 'mpls ldp' 'address-family ipv4' 'label' 'local' 'advertise' 'explicit-null' 'root'
  local child=('policy-map CE1-OUT-CHILD' 'class QG5' 'priority level 1' 'police rate 512 kbps' 'exit' 'set dscp ef' 'exit'
    'class QG3' 'set dscp af21' 'exit' 'class QG1' 'set dscp af11' 'exit' 'class QG9' 'set dscp default' 'exit' 'end-policy-map')
  local out=('policy-map CE1-OUT' 'class class-default' 'shape average 2 mbps' 'service-policy CE1-OUT-CHILD' 'exit' 'end-policy-map')
  local att=CE1-OUT
  if [ "$1" = noshape ]; then
    child=('policy-map CE1-OUT-CHILD' 'class QG5' 'set dscp ef' 'exit' 'class QG3' 'set dscp af21' 'exit' 'class QG1' 'set dscp af11' 'exit'
      'class QG9' 'set dscp default' 'exit' 'end-policy-map'); out=(); att=CE1-OUT-CHILD
  fi
  XC "$X1" 'class-map match-any CORE-EXP5' 'match mpls experimental topmost 5' 'end-class-map' \
    'class-map match-any CORE-EXP3' 'match mpls experimental topmost 3' 'end-class-map' \
    'class-map match-any CORE-EXP1' 'match mpls experimental topmost 1' 'end-class-map' \
    'class-map match-any CORE-EXP0' 'match mpls experimental topmost 0' 'end-class-map' \
    'policy-map CORE-IN' 'class CORE-EXP5' 'set qos-group 5' 'exit' 'class CORE-EXP3' 'set qos-group 3' 'exit' \
    'class CORE-EXP1' 'set qos-group 1' 'exit' 'class CORE-EXP0' 'set qos-group 9' 'exit' 'end-policy-map' \
    'class-map match-any QG5' 'match qos-group 5' 'end-class-map' 'class-map match-any QG3' 'match qos-group 3' 'end-class-map' \
    'class-map match-any QG1' 'match qos-group 1' 'end-class-map' 'class-map match-any QG9' 'match qos-group 9' 'end-class-map' \
    "${child[@]}" "${out[@]}" \
    "interface $CORE" 'service-policy input CORE-IN' 'root' "interface $CE" "service-policy output $att" 'root'
}
m12t4() {
  local cu=rx inet=any acl=yes
  case $1 in loosecust) cu=any ;; strictinet) inet=rx ;; allowdef) inet='any allow-default' ;; noacl) acl=no ;; esac
  XC "$X1" "interface $CU" "ipv4 verify unicast source reachable-via $cu" 'root' "interface $IN" "ipv4 verify unicast source reachable-via $inet" 'root'
  [ $acl = yes ] && XC "$X1" 'ipv4 access-list FROM-INTERNET' '10 permit tcp host 10.0.100.100 host 10.0.100.1 eq bgp' \
    '20 permit tcp host 10.0.100.100 eq bgp host 10.0.100.1' '30 deny ipv4 any 10.0.0.0/16' '40 deny ipv4 any 10.255.0.0/24' \
    '50 permit ipv4 any any' 'exit' "interface $IN" 'ipv4 access-group FROM-INTERNET ingress hardware-count' 'root'
}
m12t5() {
  local rr=yes xr=yes
  case $1 in noexport) xr=no ;; discard) rr=no ;; static) xr=static ;; esac
  [ $rr = yes ] && XC "$R1" 'route-policy RTBH-TRIGGER' 'if tag eq 666 then' 'set next-hop 192.0.2.1' 'set community (65000:666, no-export)' \
    'pass' 'else' 'drop' 'endif' 'end-policy'
  [ $xr = yes ] && XC "$X1" 'community-set RTBH' '65000:666' 'end-set' \
    'route-policy FROM-RR' 'if community matches-any RTBH then' 'set next-hop discard' 'endif' 'pass' 'end-policy' \
    'router bgp 65000' 'neighbor 10.255.0.52' 'address-family ipv4 unicast' 'route-policy FROM-RR in' 'root'
  [ $xr = static ] && XC "$X1" 'router static' 'address-family ipv4 unicast' '203.0.113.66/32 Null0' 'root'
}

for s in $steps; do
  f=${s%%-*}; v=; [ "$s" != "$f" ] && v=${s#*-}
  $f "$v"
done
