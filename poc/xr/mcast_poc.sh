#!/bin/bash
# BL-257 PoC= マルチキャスト(SPCOR 4.4= PIM-SM・PIM-SSM・PIM-BIDIR・PIMv6・IGMP v1/v2/v3・MLD)を IOS XR で。盤面= problems/_POC-XRMCAST
#   SRC1 ─ PE1(XRv9000)── PE2(XRv9000)─ RCV2 / PE1 ─ P1(XRd・RP の候補)─ PE2 / P1 ─ P2(XRd)─ SW1 の LAN ─ R5(IOL)・RCV3 / PE2 ─ R5
#   PE1: Gi0/0/0/0 PE2・/1 P1・/2 SRC1     PE2: /0 PE1・/1 P1・/2 R5・/3 RCV2     P1: /0 PE1・/1 PE2・/2 P2     P2: /0 P1・/1 LAN
#   R5: Et0/0 PE2・Et0/1 LAN    送信元 SRC1 192.168.1.1・受信者 RCV2 192.168.2.1・RCV3 192.168.3.1(LAN: P2 .252・R5 .253)
# 記録= design §31。usage: source poc/xr/env.sh; poc/xr/mcast_poc.sh <phase…>   出力は標準出力(呼び出し側で poc/xr/expMCAST-<phase>.log へ)
cd "$(dirname "$0")/../.."
PID=${PID:-_POC-XRMCAST}
M=topologies/_generated/$PID/mgmt_map.yml
ip() { awk -v n="$1:" '$1==n{print $2}' "$M"; }
PE1=$(ip PE1) PE2=$(ip PE2) P1=$(ip P1) P2=$(ip P2) R5=$(ip R5) SRC=$(ip SRC1) RV2=$(ip RCV2) RV3=$(ip RCV3)
S() { local h=$1; shift; .venv/bin/python poc/xr/xrsh.py "$h" "$@" 2>&1; }
H() { echo; echo "######## $(date +%T) $*"; }
XC() { local h=$1; shift; S "$h" configure "$@" commit 'show configuration failed' end; }   # XR: configure → 行 → commit
IC() { local h=$1; shift; S "$h" 'configure terminal' "$@" end; }                           # IOS: configure terminal → 行 → end
# `?` の一覧を採る(行末が ? の行は改行なしで送り、Ctrl-U で消す)。引数= 機器 台本の行 …
Q() { local h=$1; shift; local f; f=$(mktemp); printf '%s\n' "$@" > "$f"
      .venv/bin/python topologies/cli_drill.py session --host "$h" --script "$f" --out "$f.out" > /dev/null 2>&1; cat "$f.out"; rm -f "$f" "$f.out"; }
XRS="$PE1 $PE2 $P1 $P2"
name() { case $1 in $PE1) echo PE1;; $PE2) echo PE2;; $P1) echo P1;; $P2) echo P2;; $R5) echo R5;; esac; }

# 受信者の「届いた数」= IOS のホスト役が受けた echo の数(ip igmp join-group のホストは echo に答える)
echo_n() { S "$1" 'show ip traffic' | awk '/Rcvd:/{r=1} r&&/echo/{print $1; exit}'; }
send() {  # send <宛先グループ> <回数> … SRC1 から送り、RCV2・RCV3 が受けた数を数える
  local g=$1 n=${2:-20} a2 a3 b2 b3
  a2=$(echo_n "$RV2"); a3=$(echo_n "$RV3")
  S "$SRC" "ping $g repeat $n timeout 1" | grep -E "Reply|Success|^\.+$|!" | head -8
  sleep 2; b2=$(echo_n "$RV2"); b3=$(echo_n "$RV3")
  echo "== $g を $n 発: RCV2 が受けた $((b2-a2))・RCV3 が受けた $((b3-a3))"
}

a() {
  H "a: 版・IS-IS・ユニキャストの到達(IPv4/IPv6)"
  for h in $XRS; do echo "==== $(name $h)"; S "$h" 'show version | include Version' 'show isis adjacency' 'show isis ipv6 topology | include ^[0-9A-Za-z]'; done
  S "$R5" 'show version | include Version' 'show isis neighbors' 'show ip route isis | include ^i'
  S "$SRC" 'ping 192.168.2.1 repeat 3' 'ping 192.168.3.1 repeat 3' 'ping 2001:db8:100:2::1 repeat 3' 'ping 2001:db8:100:3::1 repeat 3' \
    'traceroute 192.168.2.1 probe 1 timeout 2' 'traceroute 192.168.3.1 probe 1 timeout 2'
}

base() {
  H "base: マルチキャストを何も設定していない時の XR の状態(既定で何が動くか)"
  for h in $PE1 $P1; do echo "==== $(name $h)"
    S "$h" 'show running-config multicast-routing' 'show running-config router pim' 'show running-config router igmp' \
      'show pim interface' 'show pim neighbor' 'show igmp interface' 'show mld interface' 'show mrib route' 'show pim summary'
  done
}

help() {
  H "help: XRd(P1)と XRv9000(PE1)の ? の一覧(マルチキャストの設定と show)"
  for h in $P1 $PE1; do echo "==== $(name $h)"
    Q "$h" 'show pim ?' 'show igmp ?' 'show mld ?' 'show mrib ?' 'show mfib ?' 'show pim ipv6 ?' \
      'configure' 'multicast-routing' '?' 'address-family ipv4' '?' 'interface all ?' 'exit' 'exit' \
      'router pim' 'address-family ipv4' '?' 'rp-address 10.255.0.11 ?' 'bsr ?' 'auto-rp ?' 'spt-threshold ?' 'interface GigabitEthernet0/0/0/0' '?' 'exit' 'exit' 'exit' \
      'router igmp' '?' 'interface GigabitEthernet0/0/0/0' '?' 'version ?' 'exit' 'exit' \
      'router mld' '?' 'exit' 'abort'
  done
}

en() {
  H "en1: router pim(静的 RP だけ)を P1・P2 に入れる。multicast-routing なしで PIM が IF に乗るか"
  for h in $P1 $P2; do echo "==== $(name $h)"; XC "$h" 'router pim' 'address-family ipv4' 'rp-address 10.255.0.11'
    S "$h" 'show pim interface' 'show pim neighbor' 'show igmp interface'; done
  H "en2: 全 XR に multicast-routing の address-family ipv4 で interface all enable(PE1・PE2 には router pim なし)。R5= ip multicast-routing と ip pim sparse-mode"
  for h in $XRS; do XC "$h" 'multicast-routing' 'address-family ipv4' 'interface all enable'; done
  IC "$R5" 'ip multicast-routing' 'interface Loopback0' 'ip pim sparse-mode' 'interface Ethernet0/0' 'ip pim sparse-mode' 'interface Ethernet0/1' 'ip pim sparse-mode'
  sleep 45
  for h in $XRS; do echo "==== $(name $h)"; S "$h" 'show running-config multicast-routing' 'show running-config router pim' 'show running-config router igmp' \
    'show pim interface' 'show pim neighbor' 'show igmp interface' 'show pim summary'; done
  S "$R5" 'show ip pim interface' 'show ip pim neighbor' 'show ip igmp interface Ethernet0/1'
}

sm() {
  H "sm1: 静的 RP= P1 の Lo0(10.255.0.11)を PE1・PE2・R5 にも。RCV2・RCV3 が 239.1.1.1 に参加(IOS のホストの既定= IGMPv2)"
  for h in $PE1 $PE2; do XC "$h" 'router pim' 'address-family ipv4' 'rp-address 10.255.0.11'; done
  IC "$R5" 'ip pim rp-address 10.255.0.11'
  IC "$RV2" 'interface Ethernet0/0' 'ip igmp join-group 239.1.1.1'
  IC "$RV3" 'interface Ethernet0/0' 'ip igmp join-group 239.1.1.1'
  sleep 15
  S "$PE2" 'show igmp groups' 'show igmp interface GigabitEthernet0/0/0/3' 'show pim group-map' 'show pim rpf' 'show pim topology 239.1.1.1' 'show mrib route 239.1.1.1'
  S "$P1" 'show pim topology 239.1.1.1' 'show mrib route 239.1.1.1'
  S "$P2" 'show igmp groups' 'show igmp interface GigabitEthernet0/0/0/1' 'show pim interface GigabitEthernet0/0/0/1 detail' 'show pim topology 239.1.1.1'
  S "$R5" 'show ip igmp groups' 'show ip igmp interface Ethernet0/1' 'show ip pim interface Ethernet0/1 detail' 'show ip mroute 239.1.1.1'
  H "sm2: SRC1 から 239.1.1.1 へ 20 発 → 届いた数・各ルータの状態"
  send 239.1.1.1 20
  for h in $PE1 $P1 $PE2 $P2; do echo "==== $(name $h)"; S "$h" 'show pim topology 239.1.1.1' 'show mrib route 239.1.1.1' 'show mfib route 239.1.1.1 detail'; done
  S "$R5" 'show ip mroute 239.1.1.1' 'show ip mroute 239.1.1.1 count'
}

spt() {
  H "spt1: PE2 に spt-threshold infinity → PE2 が共有木(P1 経由)に留まるか。★R5(IOS)が既定で (S,G) の Join を PE2 へ送ると PE2 に (S,G) ができるので R5 にも ip pim spt-threshold infinity"
  XC "$PE2" 'router pim' 'address-family ipv4' 'spt-threshold infinity'
  IC "$R5" 'ip pim spt-threshold infinity'
  S "$R5" 'clear ip mroute 239.1.1.1'; S "$PE2" 'clear pim topology 239.1.1.1'; sleep 70   # RP(P1)の状態は消さない・Join の間隔(60 秒)を待つ
  send 239.1.1.1 20
  for h in $PE1 $P1 $PE2; do echo "==== $(name $h)"; S "$h" 'show pim topology 239.1.1.1' 'show mrib route 239.1.1.1'; done
  S "$R5" 'show ip mroute 239.1.1.1'
  H "spt2: 戻す(PE2 と R5 の spt-threshold infinity を外す)"
  XC "$PE2" 'router pim' 'address-family ipv4' 'no spt-threshold infinity'
  IC "$R5" 'no ip pim spt-threshold infinity'
  S "$R5" 'clear ip mroute 239.1.1.1'; S "$PE2" 'clear pim topology 239.1.1.1'; sleep 70; send 239.1.1.1 10
  S "$PE2" 'show pim topology 239.1.1.1'
}

dr() {
  H "dr1: SW1 の LAN の DR と querier(P2 .252= XRd・R5 .253= IOS)"
  S "$P2" 'show pim interface GigabitEthernet0/0/0/1 detail' 'show pim neighbor GigabitEthernet0/0/0/1' 'show igmp interface GigabitEthernet0/0/0/1' 'show igmp groups GigabitEthernet0/0/0/1'
  S "$R5" 'show ip pim interface Ethernet0/1 detail' 'show ip igmp interface Ethernet0/1' 'show ip igmp groups'
  H "dr2: P2 の LAN 側に dr-priority 10 → P2 が DR に。RCV3 へは P1 → P2(XRd)で届くか"
  XC "$P2" 'router pim' 'address-family ipv4' 'interface GigabitEthernet0/0/0/1' 'dr-priority 10'
  sleep 10
  S "$P2" 'show pim interface GigabitEthernet0/0/0/1 detail' 'show pim topology 239.1.1.1'
  S "$R5" 'show ip pim interface Ethernet0/1 detail' 'show ip mroute 239.1.1.1'
  send 239.1.1.1 20
  S "$P2" 'show pim topology 239.1.1.1' 'show mrib route 239.1.1.1' 'show mfib route 239.1.1.1 detail'
  S "$P1" 'show pim topology 239.1.1.1' 'show mfib route 239.1.1.1 detail'
  S "$R5" 'show ip mroute 239.1.1.1'
}

igmp() {
  H "igmp1: XR の IGMP の既定(版・間隔・querier)と、v2 のホスト(RCV2)の参加の見え方"
  S "$PE2" 'show igmp interface GigabitEthernet0/0/0/3' 'show igmp groups 239.1.1.1 detail'
  H "igmp2: PE2 の RCV2 側を version 2 に"
  XC "$PE2" 'router igmp' 'interface GigabitEthernet0/0/0/3' 'version 2'
  sleep 5; S "$PE2" 'show igmp interface GigabitEthernet0/0/0/3' 'show igmp groups 239.1.1.1 detail'
  H "igmp3: version 1"
  XC "$PE2" 'router igmp' 'interface GigabitEthernet0/0/0/3' 'version 1'
  sleep 5; S "$PE2" 'show igmp interface GigabitEthernet0/0/0/3'; S "$RV2" 'show ip igmp interface Ethernet0/0'
  XC "$PE2" 'router igmp' 'interface GigabitEthernet0/0/0/3' 'no version'
  H "igmp4: XR 自身を受信者に(P2 に join-group 239.9.9.9)→ SRC1 の ping に答えるか / PE2 に static-group 239.8.8.8 → ホストなしで RCV2 の LAN へ流すか"
  XC "$P2" 'router igmp' 'interface GigabitEthernet0/0/0/1' 'join-group 239.9.9.9'
  XC "$PE2" 'router igmp' 'interface GigabitEthernet0/0/0/3' 'static-group 239.8.8.8'
  sleep 5
  S "$P2" 'show igmp groups 239.9.9.9 detail' 'show pim topology 239.9.9.9'
  S "$PE2" 'show igmp groups 239.8.8.8 detail' 'show pim topology 239.8.8.8' 'show mrib route 239.8.8.8'
  S "$SRC" 'ping 239.9.9.9 repeat 5 timeout 1' 'ping 239.8.8.8 repeat 5 timeout 1'
  S "$PE2" 'show mfib route 239.8.8.8 detail'
}

ssm() {
  H "ssm1: XR の既定の SSM の範囲(group-map)"
  S "$PE2" 'show pim group-map' 'show running-config router pim'
  H "ssm2: RCV2 を IGMPv3 にして (192.168.1.1, 232.1.1.1) に参加(PE2 は既定の版)"
  IC "$RV2" 'interface Ethernet0/0' 'ip igmp version 3' 'ip igmp join-group 232.1.1.1 source 192.168.1.1'
  sleep 10
  S "$PE2" 'show igmp groups 232.1.1.1 detail' 'show pim topology 232.1.1.1' 'show mrib route 232.1.1.1'
  send 232.1.1.1 20
  S "$PE1" 'show pim topology 232.1.1.1'; S "$P1" 'show pim topology 232.1.1.1'
  H "ssm3: RCV3(LAN・DR= P2 か R5)も v3 で同じ (S,G) に参加"
  IC "$RV3" 'interface Ethernet0/0' 'ip igmp version 3' 'ip igmp join-group 232.1.1.1 source 192.168.1.1'
  sleep 10
  S "$P2" 'show igmp groups 232.1.1.1 detail' 'show pim topology 232.1.1.1'
  S "$R5" 'show ip igmp groups 232.1.1.1 detail' 'show ip mroute 232.1.1.1'
  send 232.1.1.1 20
  H "ssm4: v2 のホストが 232/8 に参加(RCV2 を v2 に戻して 232.2.2.2)"
  IC "$RV2" 'interface Ethernet0/0' 'ip igmp version 2' 'ip igmp join-group 232.2.2.2'
  sleep 10
  S "$PE2" 'show igmp groups 232.2.2.2 detail' 'show pim topology 232.2.2.2' 'show igmp ssm map' 
  S "$RV2" 'show ip igmp groups'
}

bidir() {
  H "bidir1: 239.2.0.0/16 を BIDIR に。RP= P1 の Loopback1 10.255.1.11(BIDIR 用の RP アドレス・IS-IS に載せる)"
  XC "$P1" 'interface Loopback1' 'ipv4 address 10.255.1.11 255.255.255.255' 'router isis CORE' 'interface Loopback1' 'passive' 'address-family ipv4 unicast'
  for h in $XRS; do XC "$h" 'ipv4 access-list BIDIR-G' '10 permit ipv4 239.2.0.0 0.0.255.255 any' 'router pim' 'address-family ipv4' 'rp-address 10.255.1.11 BIDIR-G bidir'; done
  IC "$R5" 'access-list 20 permit 239.2.0.0 0.0.255.255' 'ip pim bidir-enable' 'ip pim rp-address 10.255.1.11 20 bidir'
  IC "$RV2" 'interface Ethernet0/0' 'ip igmp join-group 239.2.2.2'
  IC "$RV3" 'interface Ethernet0/0' 'ip igmp join-group 239.2.2.2'
  sleep 20
  for h in $XRS; do echo "==== $(name $h)"; S "$h" 'show pim group-map' 'show pim df winner' 'show pim topology 239.2.2.2' 'show mrib route 239.2.2.2'; done
  S "$R5" 'show ip pim rp mapping' 'show ip pim interface df' 'show ip mroute 239.2.2.2'
  H "bidir2: SRC1 から 239.2.2.2 へ(送信元側に (S,G) ができないこと・届くこと)"
  send 239.2.2.2 20
  for h in $PE1 $P1 $PE2; do echo "==== $(name $h)"; S "$h" 'show pim topology 239.2.2.2' 'show mfib route 239.2.2.2 detail'; done
  H "bidir3: RCV3 からも 239.2.2.2 へ(どこからでも送れる・RCV2 が受ける)"
  a2=$(echo_n "$RV2"); S "$RV3" 'ping 239.2.2.2 repeat 10 timeout 1' | grep -E 'Reply|Success' | head -4; sleep 2; b2=$(echo_n "$RV2")
  echo "== RCV3 から 10 発: RCV2 が受けた $((b2-a2))"
}

bsr() {
  H "bsr1: 静的 RP(10.255.0.11)を全ルータから外す。P1 を候補 RP(priority を指定しない= 既定を見る)・PE1 を候補 BSR に"
  for h in $XRS; do XC "$h" 'router pim' 'address-family ipv4' 'no rp-address 10.255.0.11'; done
  IC "$R5" 'no ip pim rp-address 10.255.0.11'
  XC "$P1" 'router pim' 'address-family ipv4' 'bsr candidate-rp 10.255.0.11 interval 30'
  XC "$PE1" 'router pim' 'address-family ipv4' 'bsr candidate-bsr 10.255.0.1 hash-mask-len 30'
  sleep 70
  for h in $XRS; do echo "==== $(name $h)"; S "$h" 'show pim bsr election' 'show pim rp mapping'; done
  S "$P1" 'show pim bsr candidate-rp'
  S "$R5" 'show ip pim bsr-router' 'show ip pim rp mapping'
  send 239.1.1.1 10
  H "bsr2: PE2 も候補 RP(priority 50)→ どちらが選ばれるか(小さい方が勝つか)"
  XC "$PE2" 'router pim' 'address-family ipv4' 'bsr candidate-rp 10.255.0.2 priority 50 interval 30'
  sleep 70
  for h in $PE1 $P2; do echo "==== $(name $h)"; S "$h" 'show pim rp mapping' 'show pim rp mapping 239.1.1.1'; done
  S "$R5" 'show ip pim rp mapping' 'show ip pim rp-hash 239.1.1.1'
}

autorp() {
  H "autorp1: BSR を外す。P1 を Auto-RP の候補 RP・PE1 を mapping agent に。R5 は sparse-mode のまま(listener なし)"
  XC "$P1" 'router pim' 'address-family ipv4' 'no bsr candidate-rp 10.255.0.11' 'auto-rp candidate-rp Loopback0 scope 16 interval 30'
  XC "$PE2" 'router pim' 'address-family ipv4' 'no bsr candidate-rp 10.255.0.2'
  XC "$PE1" 'router pim' 'address-family ipv4' 'no bsr candidate-bsr 10.255.0.1' 'auto-rp mapping-agent Loopback0 scope 16 interval 30'
  sleep 80
  for h in $XRS; do echo "==== $(name $h)"; S "$h" 'show pim rp mapping' 'show pim topology 224.0.1.39' 'show pim topology 224.0.1.40'; done
  S "$PE1" 'show pim auto-rp mapping-agent' 'show pim auto-rp candidate-rp'
  S "$R5" 'show ip pim rp mapping' 'show ip pim autorp' 'show ip mroute 224.0.1.40'
  H "autorp2: R5 に ip pim autorp listener"
  IC "$R5" 'ip pim autorp listener'
  sleep 70
  S "$R5" 'show ip pim rp mapping' 'show ip mroute 224.0.1.40'
  send 239.1.1.1 10
}

v6() {
  H "v6-1: XR 4 台に multicast-routing の address-family ipv6 interface all enable・router pim の address-family ipv6 rp-address 2001:db8:255::11。R5= ipv6 multicast-routing・ipv6 pim rp-address"
  for h in $XRS; do XC "$h" 'multicast-routing' 'address-family ipv6' 'interface all enable' 'router pim' 'address-family ipv6' 'rp-address 2001:db8:255::11'; done
  IC "$R5" 'ipv6 multicast-routing' 'ipv6 pim rp-address 2001:db8:255::11'
  sleep 40
  for h in $XRS; do echo "==== $(name $h)"; S "$h" 'show pim ipv6 neighbor' 'show mld interface'; done
  S "$R5" 'show ipv6 pim neighbor' 'show ipv6 mld interface Ethernet0/1'
  H "v6-2: RCV2・RCV3 が FF0E::1:1 に参加(ipv6 mld join-group)"
  IC "$RV2" 'interface Ethernet0/0' 'ipv6 mld join-group FF0E::1:1'
  IC "$RV3" 'interface Ethernet0/0' 'ipv6 mld join-group FF0E::1:1'
  sleep 10
  S "$PE2" 'show mld groups' 'show mld groups ff0e::1:1 detail' 'show pim ipv6 topology' 'show pim ipv6 group-map'
  S "$P2" 'show mld groups' 'show pim ipv6 topology'
  S "$R5" 'show ipv6 mld groups' 'show ipv6 mroute'
  H "v6-3: SRC1 から FF0E::1:1 へ ping"
  S "$SRC" 'ping FF0E::1:1 repeat 10 timeout 1'
  for h in $PE1 $P1 $PE2 $P2; do echo "==== $(name $h)"; S "$h" 'show pim ipv6 topology' 'show mrib ipv6 route ff0e::1:1'; done
  S "$R5" 'show ipv6 mroute'
}

prec() {
  H "prec1: Auto-RP(P1 10.255.0.11・224/4)が動いている所に、PE2 だけ静的 RP 10.255.0.12(P2)を足す(override なし)→ どちらを使うか"
  XC "$PE2" 'router pim' 'address-family ipv4' 'rp-address 10.255.0.12'
  sleep 5; S "$PE2" 'show pim group-map' 'show pim topology 239.1.1.1'
  H "prec2: override を付ける"
  XC "$PE2" 'router pim' 'address-family ipv4' 'rp-address 10.255.0.12 override'
  sleep 5; S "$PE2" 'show pim group-map'
  H "prec3: 片付け(PE2 の静的を外す)"
  XC "$PE2" 'router pim' 'address-family ipv4' 'no rp-address 10.255.0.12'
  sleep 5; S "$PE2" 'show pim group-map'
}

restore() {
  H "restore: Auto-RP を外し全ルータを静的 RP 10.255.0.11 に戻す・P2 の dr-priority を外す(LAN の DR= R5)・RCV2 を v3 に・RCV3 は v3 の (S,G) 232.1.1.1 のまま"
  XC "$P1" 'router pim' 'address-family ipv4' 'no auto-rp candidate-rp Loopback0 scope 16 interval 30'
  XC "$PE1" 'router pim' 'address-family ipv4' 'no auto-rp mapping-agent Loopback0 scope 16 interval 30'
  for h in $XRS; do XC "$h" 'router pim' 'address-family ipv4' 'rp-address 10.255.0.11'; done
  IC "$R5" 'ip pim rp-address 10.255.0.11' 'no ip pim autorp listener'
  XC "$P2" 'router pim' 'address-family ipv4' 'interface GigabitEthernet0/0/0/1' 'no dr-priority'
  IC "$RV2" 'interface Ethernet0/0' 'no ip igmp join-group 232.2.2.2' 'ip igmp version 3'
  sleep 70
  for h in $XRS; do echo "==== $(name $h)"; S "$h" 'show running-config router pim' 'show pim group-map'; done
  S "$R5" 'show ip pim rp mapping' 'show ip pim interface Ethernet0/1 detail | include DR'
  send 239.1.1.1 10
  H "f7(SSM の範囲の不一致): LAN の DR= R5(IOS・ip pim ssm default なし)。RCV3 の v3 の (192.168.1.1, 232.1.1.1) の参加 → R5 は ASM の (*,G) として RP へ"
  S "$R5" 'show ip igmp groups 232.1.1.1 detail' 'show ip mroute 232.1.1.1'
  send 232.1.1.1 10
  S "$P1" 'show pim topology 232.1.1.1'
  H "f7 直す: R5 に ip pim ssm default"
  IC "$R5" 'ip pim ssm default'
  sleep 70
  S "$R5" 'show ip mroute 232.1.1.1'
  send 232.1.1.1 10
}

f1() {
  H "f1(RP へ向く IF の PIM を止める): PE2 の Gi0/0/0/1(P1 へ・RP への RPF)で router pim の interface … disable"
  XC "$PE2" 'router pim' 'address-family ipv4' 'interface GigabitEthernet0/0/0/1' 'disable'
  S "$PE2" 'clear pim topology 239.1.1.1'; sleep 20
  S "$PE2" 'show pim interface' 'show pim neighbor GigabitEthernet0/0/0/1' 'show pim rpf' 'show pim topology 239.1.1.1' 'show mrib route 239.1.1.1'
  send 239.1.1.1 10
  S "$P1" 'show pim topology 239.1.1.1'
  H "f1 戻す"
  XC "$PE2" 'router pim' 'address-family ipv4' 'interface GigabitEthernet0/0/0/1' 'no disable'
  sleep 70; send 239.1.1.1 10
}

f2() {
  H "f2(受信者の LAN でマルチキャストを止める): PE2 の Gi0/0/0/3 で multicast-routing の interface … disable"
  XC "$PE2" 'multicast-routing' 'address-family ipv4' 'interface GigabitEthernet0/0/0/3' 'disable'
  sleep 10
  S "$PE2" 'show igmp interface GigabitEthernet0/0/0/3' 'show igmp groups GigabitEthernet0/0/0/3' 'show pim interface' 'show pim topology 239.1.1.1'
  send 239.1.1.1 10
  H "f2 戻す"
  XC "$PE2" 'multicast-routing' 'address-family ipv4' 'no interface GigabitEthernet0/0/0/3'
  sleep 70; send 239.1.1.1 10
}

f3() {
  H "f3(RP の取り違え): PE2 だけ RP を 10.255.0.12(P2)に"
  XC "$PE2" 'router pim' 'address-family ipv4' 'no rp-address 10.255.0.11' 'rp-address 10.255.0.12'
  S "$PE2" 'clear pim topology 239.1.1.1'; sleep 70
  S "$PE2" 'show pim group-map' 'show pim topology 239.1.1.1'
  S "$P1" 'show pim topology 239.1.1.1'; S "$P2" 'show pim topology 239.1.1.1'
  send 239.1.1.1 10
  S "$PE2" 'show pim topology 239.1.1.1'
  H "f3 戻す"
  XC "$PE2" 'router pim' 'address-family ipv4' 'no rp-address 10.255.0.12' 'rp-address 10.255.0.11'
  S "$PE2" 'clear pim topology 239.1.1.1'; sleep 70; send 239.1.1.1 10
}

f4() {
  H "f4(PIM を止める ACL): PE2 の Gi0/0/0/1 の入力に deny pim → P1 との PIM の隣接が切れるまで(holdtime 105 秒)待つ"
  XC "$PE2" 'ipv4 access-list NO-PIM' '10 deny pim any any' '20 permit ipv4 any any' 'interface GigabitEthernet0/0/0/1' 'ipv4 access-group NO-PIM ingress'
  sleep 120
  S "$PE2" 'show pim neighbor GigabitEthernet0/0/0/1' 'show pim interface' 'show access-lists ipv4 NO-PIM hardware ingress interface GigabitEthernet0/0/0/1 location 0/0/CPU0' 'show access-lists ipv4 NO-PIM'
  S "$PE2" 'clear pim topology 239.1.1.1'; sleep 20; send 239.1.1.1 10
  H "f4 戻す"
  XC "$PE2" 'interface GigabitEthernet0/0/0/1' 'no ipv4 access-group NO-PIM ingress' 'no ipv4 access-list NO-PIM'
  sleep 70; send 239.1.1.1 10
}

f5() {
  H "f5(IGMP を止める ACL): PE2 の Gi0/0/0/3 の入力に deny igmp。PE2 の IGMP の表を消し、RCV2 が参加し直す"
  XC "$PE2" 'ipv4 access-list NO-IGMP' '10 deny igmp any any' '20 permit ipv4 any any' 'interface GigabitEthernet0/0/0/3' 'ipv4 access-group NO-IGMP ingress'
  S "$PE2" 'clear igmp groups GigabitEthernet0/0/0/3'
  IC "$RV2" 'interface Ethernet0/0' 'no ip igmp join-group 239.1.1.1' 'ip igmp join-group 239.1.1.1'
  sleep 15
  S "$PE2" 'show igmp groups GigabitEthernet0/0/0/3' 'show access-lists ipv4 NO-IGMP' 'show pim topology 239.1.1.1'
  send 239.1.1.1 10
  H "f5 戻す"
  XC "$PE2" 'interface GigabitEthernet0/0/0/3' 'no ipv4 access-group NO-IGMP ingress' 'no ipv4 access-list NO-IGMP'
  IC "$RV2" 'interface Ethernet0/0' 'no ip igmp join-group 239.1.1.1' 'ip igmp join-group 239.1.1.1'
  sleep 15; S "$PE2" 'show igmp groups GigabitEthernet0/0/0/3'; send 239.1.1.1 10
}

f6() {
  H "f6(RP の accept-register で送信元を拒む): 新しいグループ 239.1.1.5 に RCV2 が参加。P1 で 192.168.1.1 からの Register を拒む"
  IC "$RV2" 'interface Ethernet0/0' 'ip igmp join-group 239.1.1.5'
  XC "$P1" 'ipv4 access-list REG-OK' '10 deny ipv4 host 192.168.1.1 any' '20 permit ipv4 any any' 'router pim' 'address-family ipv4' 'accept-register REG-OK'
  sleep 10
  send 239.1.1.5 10
  S "$PE1" 'show pim topology 239.1.1.5'; S "$P1" 'show pim topology 239.1.1.5' 'show access-lists ipv4 REG-OK'; S "$PE2" 'show pim topology 239.1.1.5'
  H "f6 戻す"
  XC "$P1" 'router pim' 'address-family ipv4' 'no accept-register REG-OK' 'root' 'no ipv4 access-list REG-OK'
  sleep 70; send 239.1.1.5 10
}

f8() {
  H "f8(IGMP の版の不一致で SSM が届かない): PE2 の Gi0/0/0/3 を version 2 に。RCV2(v3)の (192.168.1.1, 232.1.1.1) の参加"
  IC "$RV2" 'interface Ethernet0/0' 'ip igmp join-group 232.1.1.1 source 192.168.1.1'
  sleep 10; send 232.1.1.1 5
  XC "$PE2" 'router igmp' 'interface GigabitEthernet0/0/0/3' 'version 2'
  S "$PE2" 'clear igmp groups GigabitEthernet0/0/0/3'; sleep 70
  S "$PE2" 'show igmp interface GigabitEthernet0/0/0/3' 'show igmp groups GigabitEthernet0/0/0/3' 'show pim topology 232.1.1.1'
  S "$RV2" 'show ip igmp interface Ethernet0/0' 'show ip igmp groups'
  send 232.1.1.1 10
  H "f8 戻す"
  XC "$PE2" 'router igmp' 'interface GigabitEthernet0/0/0/3' 'no version'
  sleep 70; S "$PE2" 'show igmp groups 232.1.1.1 detail'; send 232.1.1.1 10
}

f7b() {
  H "f7b: R5 の LAN 側(Et0/1)が IGMPv2(IOS の既定)だと RCV3 の v3 の (S,G) の報告を表に載せない → ip igmp version 3 に。ssm default あり"
  IC "$R5" 'interface Ethernet0/1' 'ip igmp version 3'
  IC "$RV3" 'interface Ethernet0/0' 'no ip igmp join-group 232.1.1.1 source 192.168.1.1' 'ip igmp join-group 232.1.1.1 source 192.168.1.1'
  sleep 15
  S "$R5" 'show ip igmp interface Ethernet0/1' 'show ip igmp groups 232.1.1.1 detail' 'show ip mroute 232.1.1.1'
  send 232.1.1.1 10
  H "f7c(SSM の範囲の不一致そのもの): R5 の ip pim ssm default を外す(R5 の IGMP は v3 のまま)"
  IC "$R5" 'no ip pim ssm default'
  S "$R5" 'clear ip mroute 232.1.1.1'
  IC "$RV3" 'interface Ethernet0/0' 'no ip igmp join-group 232.1.1.1 source 192.168.1.1' 'ip igmp join-group 232.1.1.1 source 192.168.1.1'
  sleep 15
  S "$R5" 'show ip igmp groups 232.1.1.1 detail' 'show ip mroute 232.1.1.1'
  send 232.1.1.1 10
  S "$P1" 'show pim topology 232.1.1.1'; S "$PE2" 'show pim topology 232.1.1.1'
  H "f7c 戻す: ip pim ssm default"
  IC "$R5" 'ip pim ssm default'
  S "$R5" 'clear ip mroute 232.1.1.1'
  IC "$RV3" 'interface Ethernet0/0' 'no ip igmp join-group 232.1.1.1 source 192.168.1.1' 'ip igmp join-group 232.1.1.1 source 192.168.1.1'
  sleep 15; S "$R5" 'show ip mroute 232.1.1.1'; send 232.1.1.1 10
}

f7d() {
  H "f7d(SSM の範囲の不一致・名残を待つ): R5 の ip pim ssm default を外し、PE2 に残る (S,G) の Join(R5 から・210 秒)が切れるまで待つ"
  IC "$R5" 'no ip pim ssm default'
  S "$R5" 'clear ip mroute 232.1.1.1'
  IC "$RV3" 'interface Ethernet0/0' 'no ip igmp join-group 232.1.1.1 source 192.168.1.1' 'ip igmp join-group 232.1.1.1 source 192.168.1.1'
  S "$PE2" 'show pim topology 232.1.1.1'
  sleep 230
  S "$R5" 'show ip mroute 232.1.1.1'
  S "$PE2" 'show pim topology 232.1.1.1' 'show pim topology 232.1.1.1 detail' 'show pim traffic | include Join'
  send 232.1.1.1 10
  S "$P1" 'show pim topology 232.1.1.1'
  H "f7d 戻す: ip pim ssm default"
  IC "$R5" 'ip pim ssm default'
  S "$R5" 'clear ip mroute 232.1.1.1'
  IC "$RV3" 'interface Ethernet0/0' 'no ip igmp join-group 232.1.1.1 source 192.168.1.1' 'ip igmp join-group 232.1.1.1 source 192.168.1.1'
  sleep 15; S "$R5" 'show ip mroute 232.1.1.1'; send 232.1.1.1 10
}

# ---- 測り直し(2026-11-18): 故障を先に入れてから、RCV2 だけが参加する新しいグループで測る(前の Join の名残・R5 の (S,G) にまぎれないように)
r1() {
  H "r1(= f1 の測り直し): PE2 の Gi0/0/0/1(RP への RPF)の PIM を止めてから、RCV2 が 239.1.1.6 に参加"
  XC "$PE2" 'router pim' 'address-family ipv4' 'interface GigabitEthernet0/0/0/1' 'disable'
  IC "$RV2" 'interface Ethernet0/0' 'ip igmp join-group 239.1.1.6'
  sleep 20
  S "$PE2" 'show pim topology 239.1.1.6' 'show pim rpf 10.255.0.11'
  S "$P1" 'show pim topology 239.1.1.6'
  send 239.1.1.6 10
  H "r1 戻す"
  XC "$PE2" 'router pim' 'address-family ipv4' 'interface GigabitEthernet0/0/0/1' 'no disable'
  sleep 40; S "$PE2" 'show pim topology 239.1.1.6'; send 239.1.1.6 10
}
r3() {
  H "r3(= f3 の測り直し): PE2 だけ RP を 10.255.0.12(P2)にしてから、RCV2 が 239.1.1.7 に参加"
  XC "$PE2" 'router pim' 'address-family ipv4' 'no rp-address 10.255.0.11' 'rp-address 10.255.0.12'
  IC "$RV2" 'interface Ethernet0/0' 'ip igmp join-group 239.1.1.7'
  sleep 20
  S "$PE2" 'show pim topology 239.1.1.7'; S "$P1" 'show pim topology 239.1.1.7'; S "$P2" 'show pim topology 239.1.1.7'
  send 239.1.1.7 10
  S "$PE1" 'show pim topology 239.1.1.7'; S "$P1" 'show pim topology 239.1.1.7'
  H "r3 戻す"
  XC "$PE2" 'router pim' 'address-family ipv4' 'no rp-address 10.255.0.12' 'rp-address 10.255.0.11'
  sleep 70; S "$PE2" 'show pim topology 239.1.1.7'; send 239.1.1.7 10
}
r4() {
  H "r4(= f4 の測り直し): PE2 の Gi0/0/0/1 の入力に deny pim → 隣接が切れるまで待ってから、RCV2 が 239.1.1.8 に参加"
  XC "$PE2" 'ipv4 access-list NO-PIM' '10 deny pim any any' '20 permit ipv4 any any' 'interface GigabitEthernet0/0/0/1' 'ipv4 access-group NO-PIM ingress'
  sleep 120
  IC "$RV2" 'interface Ethernet0/0' 'ip igmp join-group 239.1.1.8'
  sleep 20
  S "$PE2" 'show pim neighbor GigabitEthernet0/0/0/1' 'show pim topology 239.1.1.8'
  S "$P1" 'show pim neighbor GigabitEthernet0/0/0/1' 'show pim topology 239.1.1.8'
  send 239.1.1.8 10
  S "$PE2" 'show pim topology 239.1.1.8'
  H "r4 戻す"
  XC "$PE2" 'interface GigabitEthernet0/0/0/1' 'no ipv4 access-group NO-PIM ingress' 'root' 'no ipv4 access-list NO-PIM'
  sleep 40; send 239.1.1.8 10
}
r5() {
  H "r5(= f5 の測り直し): PE2 の Gi0/0/0/3 の入力に deny igmp を入れてから、RCV2 が 239.1.1.9 に参加"
  XC "$PE2" 'ipv4 access-list NO-IGMP' '10 deny igmp any any' '20 permit ipv4 any any' 'interface GigabitEthernet0/0/0/3' 'ipv4 access-group NO-IGMP ingress'
  IC "$RV2" 'interface Ethernet0/0' 'ip igmp join-group 239.1.1.9'
  sleep 20
  S "$PE2" 'show igmp groups 239.1.1.9 detail' 'show pim topology 239.1.1.9' 'show igmp traffic'
  send 239.1.1.9 10
  H "r5 戻す(次の問い合わせまで待つ)"
  XC "$PE2" 'interface GigabitEthernet0/0/0/3' 'no ipv4 access-group NO-IGMP ingress' 'root' 'no ipv4 access-list NO-IGMP'
  sleep 70; S "$PE2" 'show igmp groups 239.1.1.9 detail'; send 239.1.1.9 10
}
r8() {
  H "r8(= f8 の続き): PE2 の Gi0/0/0/3 を version 2 → RCV2 のホストが v2 互換に → PE2 を v3 に戻してから RCV2 が v3 に戻るまでの時間と、SSM が届き直すまで"
  XC "$PE2" 'router igmp' 'interface GigabitEthernet0/0/0/3' 'version 2'
  sleep 70
  S "$RV2" 'show ip igmp interface Ethernet0/0' | grep -E 'version|querying'
  XC "$PE2" 'router igmp' 'interface GigabitEthernet0/0/0/3' 'no version'
  t0=$(date +%s)
  for i in $(seq 1 20); do
    v=$(S "$RV2" 'show ip igmp interface Ethernet0/0' | awk '/host version/{print $NF}')
    g=$(S "$PE2" 'show igmp groups 232.1.1.1 detail' | grep -cE 'Source Address|192.168.1.1')
    echo "$(( $(date +%s) - t0 )) 秒: RCV2 の host version= $v・PE2 の (S,G) の行= $g"
    [ "$v" = 3 ] && [ "$g" -ge 1 ] && break
    sleep 30
  done
  send 232.1.1.1 10
}

ssmr() {
  H "ssmr1: SSM の範囲を変える置き場。PE2 の router pim の address-family ipv4 に ssm range SSM-ALT(232/8 と 239.100.0.0/16)"
  XC "$PE2" 'ipv4 access-list SSM-ALT' '10 permit ipv4 232.0.0.0 0.255.255.255 any' '20 permit ipv4 239.100.0.0 0.0.255.255 any' 'router pim' 'address-family ipv4' 'ssm range SSM-ALT'
  sleep 5; S "$PE2" 'show running-config router pim' 'show pim group-map'
  XC "$PE2" 'router pim' 'address-family ipv4' 'no ssm range SSM-ALT'
  H "ssmr2: 同じことを multicast-routing の address-family ipv4 の下で(文書の置き場・26.1.1 の ? では cisco-support)"
  XC "$PE2" 'multicast-routing' 'address-family ipv4' 'ssm range SSM-ALT'
  sleep 5; S "$PE2" 'show running-config multicast-routing' 'show pim group-map'
  XC "$PE2" 'multicast-routing' 'address-family ipv4' 'no ssm range SSM-ALT' 'root' 'no ipv4 access-list SSM-ALT'
  sleep 5; S "$PE2" 'show pim group-map'
}

for p in "$@"; do "$p"; done
