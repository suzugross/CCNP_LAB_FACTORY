#!/bin/bash
# BL-246 §14: XRv9000 と XRd の比較 PoC(M5 RPL・M6 BGP と基本)。盤面= problems/_POC-XRCMP。
# usage: source poc/xr/env.sh; poc/xr/cmp_m5m6.sh <XR の管理IP> <eBGP 相手 IOL の管理IP> <iBGP 相手 IOL の管理IP> <phase…>
#   phase= base rpl bgp all。出力は標準出力(呼び出し側で poc/xr/cmp-<機種>-<phase>.log へ)
cd "$(dirname "$0")/../.."
XR=$1 E=$2 I=$3; shift 3
X() { .venv/bin/python poc/xr/xrsh.py "$XR" "$@" 2>&1; }
R() { local h=$1; shift; .venv/bin/python poc/xr/xrsh.py "$h" "$@" 2>&1; }
H() { echo; echo "######## $*"; }

base() {
  H "base: 版・パッケージ・資源"
  X 'show version' 'show install active summary' 'show platform' 'show memory summary' 'show processes cpu | utility head count 4'
  H "base: IF"
  X 'show ipv4 interface brief' 'show interfaces summary'
  H "base: exec 最上位のヘルプ"
  X 'show ?'
  H "base: 設定モード最上位のヘルプ"
  X configure '?' 'abort'
  H "base: XR 自身からの ping(直結)"
  X 'ping 10.0.1.2' 'ping 10.0.2.2'
}

rpl() {
  H "rpl-1: ポリシーなしの eBGP"
  X configure 'router bgp 65000' 'bgp router-id 1.1.1.1' 'address-family ipv4 unicast' exit \
    'neighbor 10.0.1.2' 'remote-as 65001' 'address-family ipv4 unicast' 'send-community-ebgp' root \
    'router bgp 65000' 'neighbor 10.0.2.2' 'remote-as 65000' 'address-family ipv4 unicast' commit end
  sleep 40
  X 'show bgp ipv4 unicast summary' 'show bgp ipv4 unicast' 'show bgp neighbor 10.0.1.2 | include "olic|Policy|accepted|denied"'
  H "rpl-2: prefix-set・community-set・as-path-set・引数つき・apply・末尾まで pass なし"
  X configure 'prefix-set PS-24' '172.16.0.0/16 ge 24 le 24' end-set \
    'community-set CS-TAG' '65000:100' end-set \
    "as-path-set AS-ORIGIN" "ios-regex '^65001\$'" end-set \
    'route-policy SET-LP($lp)' 'set local-preference $lp' end-policy \
    'route-policy RP-IN' 'if destination in PS-24 then' 'set community CS-TAG' 'apply SET-LP(200)' \
    'elseif destination in (172.16.2.0/25) and as-path in AS-ORIGIN then' 'pass' 'endif' end-policy \
    'route-policy PASS' 'pass' end-policy \
    'router bgp 65000' 'neighbor 10.0.1.2' 'address-family ipv4 unicast' 'route-policy RP-IN in' 'route-policy PASS out' commit end
  sleep 20
  X 'show bgp ipv4 unicast' 'show bgp ipv4 unicast 172.16.0.0/24' 'show bgp ipv4 unicast community 65000:100'
  H "rpl-3: 表示・確認系"
  X 'show rpl route-policy RP-IN' 'show rpl route-policy RP-IN detail' 'show rpl route-policy RP-IN attachpoints' \
    'show rpl active route-policy' 'show rpl inactive route-policy' 'show rpl prefix-set PS-24 attachpoints' \
    'show bgp neighbor 10.0.1.2 | include "olic"' 'show bgp ipv4 unicast policy | utility head count 30' \
    'show bgp ipv4 unicast neighbors 10.0.1.2 routes' 'show bgp ipv4 unicast neighbors 10.0.1.2 received routes'
  H "rpl-4: 使用中の set を書き換える(clear なしで反映されるか)"
  X configure 'prefix-set PS-24' '172.16.0.0/16 ge 24 le 24,' '11.11.11.11/32' end-set commit end
  sleep 15
  X 'show bgp ipv4 unicast' 'show bgp ipv4 unicast 11.11.11.11/32'
  H "rpl-5: 未定義のポリシー・使用中の削除・適用点にそぐわない動作"
  X configure 'router bgp 65000' 'neighbor 10.0.2.2' 'address-family ipv4 unicast' 'route-policy NOPE out' commit 'show configuration failed' abort
  X configure 'no route-policy PASS' commit 'show configuration failed' abort
  X configure 'router ospf 1' 'area 0' 'interface Loopback0' root 'router ospf 1' 'redistribute bgp 65000 route-policy RP-IN' commit 'show configuration failed' abort
  X configure 'route-policy RP-OSPF' 'set metric-type type-1' pass end-policy 'router ospf 1' 'area 0' 'interface Loopback0' root \
    'router ospf 1' 'redistribute bgp 65000 route-policy RP-OSPF' commit 'show configuration failed' end
  X 'show rpl route-policy RP-OSPF attachpoints'
  H "rpl-6: soft reconfiguration の要否(受信前の経路が見えるか)"
  X 'clear bgp ipv4 unicast 10.0.1.2 soft in' 'show bgp ipv4 unicast neighbors 10.0.1.2 received routes'
  X configure 'router bgp 65000' 'neighbor 10.0.1.2' 'address-family ipv4 unicast' 'soft-reconfiguration inbound always' commit end
  sleep 10
  X 'show bgp ipv4 unicast neighbors 10.0.1.2 received routes'
}

bgp() {
  H "bgp-1: RR・next-hop-self・相手側の受信"
  X configure 'router bgp 65000' 'neighbor 10.0.2.2' 'address-family ipv4 unicast' 'route-reflector-client' 'next-hop-self' commit end
  sleep 20
  R "$I" 'show ip bgp' 'show ip bgp 11.11.11.11'
  R "$E" 'show ip bgp'
  H "bgp-2: XR を通り抜ける転送(RT01 Lo0 → RT02 Lo0)"
  R "$E" 'ping 22.22.22.22 source Loopback0 repeat 20' 'traceroute 22.22.22.22 source Loopback0 numeric timeout 1 ttl 1 3'
  X 'show cef 22.22.22.22' 'show route 22.22.22.22' 'show interfaces GigabitEthernet0/0/0/1 | include "packets|rate"'
  H "bgp-3: パス選択の表示・属性"
  X 'show bgp ipv4 unicast 11.11.11.11/32 bestpath-compare' 'show bgp ipv4 unicast neighbors 10.0.2.2 advertised-routes' \
    'show bgp ipv4 unicast summary' 'show bgp neighbor 10.0.2.2 | utility head count 40'
  H "bgp-4: IPv6 AF(XR 側だけ・相手なしで設定が通るか)と BFD"
  X configure 'router bgp 65000' 'address-family ipv6 unicast' exit 'neighbor 2001:db8:1::2' 'remote-as 65001' \
    'address-family ipv6 unicast' 'route-policy PASS in' 'route-policy PASS out' root \
    'router bgp 65000' 'neighbor 10.0.1.2' 'bfd fast-detect' 'bfd minimum-interval 300' commit 'show configuration failed' end
  X 'show bfd session' 'show bgp ipv6 unicast summary'
}

for p in "$@"; do
  case $p in base) base ;; rpl) rpl ;; bgp) bgp ;; all) base; rpl; bgp ;; esac
done
