#!/bin/bash
# XRT-10 の模範解(learn.yml の solution と同じもの)を管理 IF の SSH で XR01/XR02 に入れる。PoC/E2E 用。
# usage: source poc/xr/env.sh; poc/xr/solve_xrt10.sh [m10t1 m10t2 m10t3 m10t4 m10t5 …](既定= 全部)。管理 IP は _generated の mgmt_map から引く
#   誤答の確かめ用: m10t1-keepsrgb(SRGB を直さない)・m10t1-noprefer(sr-prefer なし)・m10t2-sync(LDP だけ止めて同期を残す)・
#                   m10t3-lfa(TI-LFA なし= 素の LFA だけ)・m10t3-noml(microloop avoidance なし)・
#                   m10t4-nols(distribute link-state なし)・m10t4-explicit(固定の経路= 明示の segment-list)・
#                   m10t5-nols(XR02 に distribute link-state なし)・m10t5-nodisj(離す条件なし)
#   別解: m10t1-abs(SRGB を 16000-23999 と書く)・m10t4-vrfimport(色を VRF の import で付ける= 公式は match だけ・26.1.1 は効く §23.6-2)
cd "$(dirname "$0")/../.."
M=topologies/_generated/${PID:-XRT-10}/mgmt_map.yml
ipof() { awk -v n="$1:" '$1==n{print $2}' "$M"; }
XR=$(ipof XR01) RR=$(ipof XR02)
steps=${*:-m10t1 m10t2 m10t3 m10t4 m10t5}
run() { local h=$1; shift; .venv/bin/python poc/xr/xrsh.py "$h" "$@" 2>&1 | grep -iE "^%|fail|error|invalid|!!%" || true; }
X() { run "$XR" "$@"; }
Q() { run "$RR" "$@"; }
G0=GigabitEthernet0/0/0/0 G1=GigabitEthernet0/0/0/1
SR_BASE=('router isis CORE' 'address-family ipv4 unicast' 'segment-routing mpls sr-prefer' 'root'
  'router isis CORE' 'interface Loopback0' 'address-family ipv4 unicast' 'prefix-sid index 1' 'root')
TILFA=('router isis CORE' "interface $G0" 'address-family ipv4 unicast' 'fast-reroute per-prefix' 'fast-reroute per-prefix ti-lfa' 'root'
  'router isis CORE' "interface $G1" 'address-family ipv4 unicast' 'fast-reroute per-prefix' 'fast-reroute per-prefix ti-lfa' 'root')
COLOR=('extcommunity-set opaque COLOR-100' '100' 'end-set' 'extcommunity-set rt CUST-A-RT' '65000:101' 'end-set'
  'route-policy FROM-RR' 'if extcommunity rt matches-any CUST-A-RT then' 'set extcommunity color COLOR-100' 'endif' 'pass' 'end-policy')
ODN=('segment-routing' 'traffic-eng' 'affinity-map' 'name RT01-MAINT bit-position 0' 'exit'
  "interface $G0" 'affinity' 'name RT01-MAINT' 'root'
  'segment-routing' 'traffic-eng' 'on-demand color 100' 'dynamic' 'metric' 'type igp' 'exit' 'affinity' 'exclude-any' 'name RT01-MAINT' 'root')
PCC=('segment-routing' 'traffic-eng' 'pcc' 'source-address ipv4 10.255.0.1' 'pce address ipv4 10.255.0.21' 'root')
disj() {  # $1= 名前 $2= 色 $3= 離す条件を付けるか(yes/no)
  local c=('segment-routing' 'traffic-eng' "policy $1" "color $2 end-point ipv4 10.255.0.12" 'candidate-paths' 'preference 100'
    'dynamic' 'pcep' 'exit' 'metric' 'type igp' 'exit' 'exit')
  [ "$3" = yes ] && c+=('constraints' 'disjoint-path group-id 1 type link')
  c+=('root'); printf '%s\n' "${c[@]}"
}
for s in $steps; do case $s in
m10t1)        X configure 'segment-routing' 'no global-block' 'root' "${SR_BASE[@]}" commit end ;;
m10t1-abs)    X configure 'segment-routing' 'global-block 16000 23999' 'root' "${SR_BASE[@]}" commit end ;;
m10t1-keepsrgb) X configure "${SR_BASE[@]}" commit end ;;
m10t1-noprefer) X configure 'segment-routing' 'no global-block' 'root' \
                  'router isis CORE' 'address-family ipv4 unicast' 'segment-routing mpls' 'root' \
                  'router isis CORE' 'interface Loopback0' 'address-family ipv4 unicast' 'prefix-sid index 1' 'root' commit end ;;
m10t2)        X configure 'no mpls ldp' 'router isis CORE' "interface $G0" 'address-family ipv4 unicast' 'no mpls ldp sync' 'root' \
                'router isis CORE' "interface $G1" 'address-family ipv4 unicast' 'no mpls ldp sync' 'root' commit end ;;
m10t2-sync)   X configure 'no mpls ldp' commit end ;;
m10t3)        X configure "${TILFA[@]}" 'router isis CORE' 'address-family ipv4 unicast' 'microloop avoidance segment-routing' 'root' commit end ;;
m10t3-lfa)    X configure 'router isis CORE' "interface $G0" 'address-family ipv4 unicast' 'fast-reroute per-prefix' 'root' \
                'router isis CORE' "interface $G1" 'address-family ipv4 unicast' 'fast-reroute per-prefix' 'root' \
                'router isis CORE' 'address-family ipv4 unicast' 'microloop avoidance segment-routing' 'root' commit end ;;
m10t3-noml)   X configure "${TILFA[@]}" commit end ;;
m10t4)        X configure "${COLOR[@]}" 'router bgp 65000' 'neighbor 10.255.0.21' 'address-family vpnv4 unicast' 'route-policy FROM-RR in' 'root' \
                'router isis CORE' 'distribute link-state' 'root' "${ODN[@]}" commit end ;;
m10t4-nols)   X configure "${COLOR[@]}" 'router bgp 65000' 'neighbor 10.255.0.21' 'address-family vpnv4 unicast' 'route-policy FROM-RR in' 'root' \
                "${ODN[@]}" commit end ;;
m10t4-explicit) X configure "${COLOR[@]}" 'router bgp 65000' 'neighbor 10.255.0.21' 'address-family vpnv4 unicast' 'route-policy FROM-RR in' 'root' \
                'segment-routing' 'traffic-eng' 'segment-list VIA-RT03' 'index 10 mpls label 16013' 'index 20 mpls label 16012' 'exit' \
                'policy CUST-A-VIA-RT03' 'color 100 end-point ipv4 10.255.0.12' 'candidate-paths' 'preference 100' 'explicit segment-list VIA-RT03' 'root' commit end ;;
m10t4-vrfimport) X configure 'extcommunity-set opaque COLOR-100' '100' 'end-set' \
                'route-policy COLOR-A' 'set extcommunity color COLOR-100' 'pass' 'end-policy' \
                'vrf CUST-A' 'address-family ipv4 unicast' 'import route-policy COLOR-A' 'root' \
                'router isis CORE' 'distribute link-state' 'root' "${ODN[@]}" commit end ;;
m10t5)        Q configure 'pce' 'address ipv4 10.255.0.21' 'root' 'router isis CORE' 'distribute link-state' 'root' commit end
              mapfile -t A < <(disj DISJ-1 201 yes); mapfile -t B < <(disj DISJ-2 202 yes)
              X configure "${PCC[@]}" "${A[@]}" "${B[@]}" commit end ;;
m10t5-nols)   Q configure 'pce' 'address ipv4 10.255.0.21' 'root' commit end
              mapfile -t A < <(disj DISJ-1 201 yes); mapfile -t B < <(disj DISJ-2 202 yes)
              X configure "${PCC[@]}" "${A[@]}" "${B[@]}" commit end ;;
m10t5-nodisj) Q configure 'pce' 'address ipv4 10.255.0.21' 'root' 'router isis CORE' 'distribute link-state' 'root' commit end
              mapfile -t A < <(disj DISJ-1 201 no); mapfile -t B < <(disj DISJ-2 202 no)
              X configure "${PCC[@]}" "${A[@]}" "${B[@]}" commit end ;;
*) echo "unknown step: $s"; exit 2 ;;
esac; done
