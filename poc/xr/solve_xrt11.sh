#!/bin/bash
# XRT-11 の模範解(learn.yml の solution と同じもの)を管理 IF の SSH で XR01/XR02/XR03 に入れる。PoC/E2E 用。
# usage: source poc/xr/env.sh; poc/xr/solve_xrt11.sh [m11t1 m11t2 m11t3 m11t4 m11t5 …](既定= 全部)。管理 IP は _generated の mgmt_map から引く
#   誤答の確かめ用: m11t1-ldpcore(コアのリンクでも LDP を動かす)・m11t1-ldponly(mpls ldp だけ= 別解・通る)・m11t1-norewrite(AC に rewrite なし= MTU 1504)・
#                   m11t2-mtuonly(300 の rewrite を足さない)・m11t3-direct(XR01⇔XR03 の直接の l2vpn evpn・RR を使わない)・
#                   m11t3-swap(source/target を入れ違える)・m11t4-410only(420 を直さない)・m11t5-plain(外側 500 だけ= 単一タグも運ぶ)
#   別解: m11t5-norewrite(両端とも rewrite なしで 2 枚とも運ぶ)・m11t2-submtu(ポートはジャンボのまま、サブインタフェースの MTU を 1514 に)
cd "$(dirname "$0")/../.."
M=topologies/_generated/${PID:-XRT-11}/mgmt_map.yml
ipof() { awk -v n="$1:" '$1==n{print $2}' "$M"; }
X1=$(ipof XR01) X2=$(ipof XR02) X3=$(ipof XR03)
steps=${*:-m11t1 m11t2 m11t3 m11t4 m11t5}
run() { local h=$1; shift; .venv/bin/python poc/xr/xrsh.py "$h" "$@" 2>&1 | grep -iE "^%|fail|error|invalid|!!%" || true; }
A=GigabitEthernet0/0/0/2 B=GigabitEthernet0/0/0/3 B3=GigabitEthernet0/0/0/1
eline_a() {  # $1= rewrite する(yes/no)
  local c=("interface $A.100 l2transport" 'encapsulation dot1q 100')
  [ "$1" = yes ] && c+=('rewrite ingress tag pop 1 symmetric')
  c+=('root' 'l2vpn' 'xconnect group CUST-A' 'p2p A-100' "interface $A.100" 'neighbor ipv4 10.255.0.12 pw-id 100' 'root')
  printf '%s\n' "${c[@]}"
}
BGP_PE=('router bgp 65000' 'address-family l2vpn evpn' 'exit' 'neighbor 10.255.0.21' 'address-family l2vpn evpn' 'root')
BGP_X3=('router bgp 65000' 'bgp router-id 10.255.0.3' 'address-family l2vpn evpn' 'exit'
  'neighbor 10.255.0.21' 'remote-as 65000' 'update-source Loopback0' 'address-family l2vpn evpn' 'root')
BGP_RR=('router bgp 65000' 'address-family l2vpn evpn' 'exit'
  'neighbor 10.255.0.1' 'address-family l2vpn evpn' 'route-reflector-client' 'exit' 'exit'
  'neighbor 10.255.0.3' 'remote-as 65000' 'description PE XR03' 'update-source Loopback0' 'address-family l2vpn evpn' 'route-reflector-client' 'root')
vpws() {  # $1= IF $2= VLAN $3= p2p の名前 $4= EVI $5= target $6= source
  printf '%s\n' "interface $1.$2 l2transport" "encapsulation dot1q $2" 'rewrite ingress tag pop 1 symmetric' 'root' \
    'l2vpn' 'xconnect group CUST-B' "p2p $3" "interface $1.$2" "neighbor evpn evi $4 target $5 source $6" 'root'
}
qinq() {  # $1= IF $2= target $3= source $4= encapsulation の書き方 $5= rewrite する(yes/no)
  local c=("interface $1.500 l2transport" "$4")
  [ "$5" = yes ] && c+=('rewrite ingress tag pop 1 symmetric')
  c+=('root' 'l2vpn' 'xconnect group CUST-B' 'p2p B-500' "interface $1.500" "neighbor evpn evi 500 target $2 source $3" 'root')
  printf '%s\n' "${c[@]}"
}
for s in $steps; do case $s in
m11t1)          mapfile -t C < <(eline_a yes); run "$X1" configure "${C[@]}" commit end ;;
m11t1-norewrite) mapfile -t C < <(eline_a no); run "$X1" configure "${C[@]}" commit end ;;
m11t1-ldpcore)  mapfile -t C < <(eline_a yes)
                run "$X1" configure "${C[@]}" 'mpls ldp' 'interface GigabitEthernet0/0/0/0' 'exit' 'interface GigabitEthernet0/0/0/1' 'root' commit end ;;
m11t1-ldponly)  mapfile -t C < <(eline_a yes); run "$X1" configure "${C[@]}" 'mpls ldp' 'root' commit end ;;
m11t2)          run "$X1" configure "interface $B.300 l2transport" 'rewrite ingress tag pop 1 symmetric' 'root' "interface $B" 'no mtu' 'root' commit end ;;
m11t2-mtuonly)  run "$X1" configure "interface $B" 'no mtu' 'root' commit end ;;
m11t2-submtu)   run "$X1" configure "interface $B.300 l2transport" 'rewrite ingress tag pop 1 symmetric' 'mtu 1514' 'root' "interface $B.310 l2transport" 'mtu 1514' 'root' commit end ;;
m11t3)          run "$X2" configure "${BGP_RR[@]}" commit end
                mapfile -t C < <(vpws $B 400 B-400 400 3 1); run "$X1" configure "${BGP_PE[@]}" "${C[@]}" commit end
                mapfile -t C < <(vpws $B3 40 B-400 400 1 3); run "$X3" configure "${BGP_X3[@]}" "${C[@]}" commit end ;;
m11t3-swap)     run "$X2" configure "${BGP_RR[@]}" commit end
                mapfile -t C < <(vpws $B 400 B-400 400 1 3); run "$X1" configure "${BGP_PE[@]}" "${C[@]}" commit end
                mapfile -t C < <(vpws $B3 40 B-400 400 3 1); run "$X3" configure "${BGP_X3[@]}" "${C[@]}" commit end ;;
m11t3-direct)   mapfile -t C < <(vpws $B 400 B-400 400 3 1)
                run "$X1" configure 'router bgp 65000' 'address-family l2vpn evpn' 'exit' 'neighbor 10.255.0.3' 'remote-as 65000' 'update-source Loopback0' \
                  'address-family l2vpn evpn' 'root' "${C[@]}" commit end
                mapfile -t C < <(vpws $B3 40 B-400 400 1 3)
                run "$X3" configure 'router bgp 65000' 'bgp router-id 10.255.0.3' 'address-family l2vpn evpn' 'exit' 'neighbor 10.255.0.1' 'remote-as 65000' \
                  'update-source Loopback0' 'address-family l2vpn evpn' 'root' "${C[@]}" commit end ;;
m11t4)          run "$X3" configure 'l2vpn' 'xconnect group CUST-B' 'p2p B-410' 'no neighbor evpn evi 410 target 2 source 3' 'neighbor evpn evi 410 target 1 source 3' 'root' \
                  "interface $B3.42 l2transport" 'rewrite ingress tag pop 1 symmetric' 'root' commit end ;;
m11t4-410only)  run "$X3" configure 'l2vpn' 'xconnect group CUST-B' 'p2p B-410' 'no neighbor evpn evi 410 target 2 source 3' 'neighbor evpn evi 410 target 1 source 3' 'root' commit end ;;
m11t5)          mapfile -t C < <(qinq $B 3 1 'encapsulation dot1q 500 second-dot1q any' yes); run "$X1" configure "${C[@]}" commit end
                mapfile -t C < <(qinq $B3 1 3 'encapsulation dot1q 500 second-dot1q any' yes); run "$X3" configure "${C[@]}" commit end ;;
m11t5-norewrite) mapfile -t C < <(qinq $B 3 1 'encapsulation dot1q 500 second-dot1q any' no); run "$X1" configure "${C[@]}" commit end
                mapfile -t C < <(qinq $B3 1 3 'encapsulation dot1q 500 second-dot1q any' no); run "$X3" configure "${C[@]}" commit end ;;
m11t5-plain)    mapfile -t C < <(qinq $B 3 1 'encapsulation dot1q 500' yes); run "$X1" configure "${C[@]}" commit end
                mapfile -t C < <(qinq $B3 1 3 'encapsulation dot1q 500' yes); run "$X3" configure "${C[@]}" commit end ;;
*) echo "unknown step: $s"; exit 2 ;;
esac; done
