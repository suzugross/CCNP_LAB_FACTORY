#!/bin/bash
# BL-257 PoC= M6 追補「BGP の運用機能」(SPCOR 2.4.g 追加パス・2.4.h PIC・1.5.b TTL セキュリティと認証・1.5.c プレフィックスの抑制)。盤面= problems/_POC-XRBGP
#   CE1(65001)─ PE1(XRd)─┐            ┌─ PE2(XRd)─ X1 ─┐
#                         ├─ P1(XRd) ─┤       (65100)    ├─ T 203.0.113.1(IP SLA の responder)
#   CE4(65004)─ PE4(XRv)─┘    │       └─ PE3(XRd)─ X2 ─┘  X1 ─ X2 直結
#                            RR1(XRd)
#   XR は Gi0/0/0/0= P1 へ・Gi0/0/0/1= CE か X へ。P1 は /0 PE1・/1 PE2・/2 PE3・/3 PE4・/4 RR1。IOL は Et0/0= PE 側。
#   Lo0= PE1 10.255.0.1・PE2 .2・PE3 .3・PE4 .4・P1 .11・RR1 .21。PE2 は X1 の経路に local-preference 200(PE3 は 100)。
# 記録= design §32。usage: source poc/xr/env.sh; poc/xr/bgpops_poc.sh <phase…>   出力は標準出力(呼び出し側で poc/xr/expBGPOPS-<phase>.log へ)
cd "$(dirname "$0")/../.."
PID=${PID:-_POC-XRBGP}
M=topologies/_generated/$PID/mgmt_map.yml
ip() { awk -v n="$1:" '$1==n{print $2}' "$M"; }
PE1=$(ip PE1) PE2=$(ip PE2) PE3=$(ip PE3) PE4=$(ip PE4) P1=$(ip P1) RR1=$(ip RR1) CE1=$(ip CE1) CE4=$(ip CE4) X1=$(ip X1) X2=$(ip X2) T=$(ip T)
S() { local h=$1; shift; .venv/bin/python poc/xr/xrsh.py "$h" "$@" 2>&1; }
H() { echo; echo "######## $(date +%T) $*"; }
XC() { local h=$1; shift; S "$h" configure "$@" commit 'show configuration failed' end; }   # XR: configure → 行 → commit
IC() { local h=$1; shift; S "$h" 'configure terminal' "$@" end; }                           # IOS: configure terminal → 行 → end
Q() { local h=$1; shift; local f; f=$(mktemp); printf '%s\n' "$@" > "$f"
      .venv/bin/python topologies/cli_drill.py session --host "$h" --script "$f" --out "$f.out" > /dev/null 2>&1; cat "$f.out"; rm -f "$f" "$f.out"; }
XRS="$PE1 $PE2 $PE3 $PE4 $P1 $RR1"
name() { case $1 in $PE1) echo PE1;; $PE2) echo PE2;; $PE3) echo PE3;; $PE4) echo PE4;; $P1) echo P1;; $RR1) echo RR1;; esac; }
PFX=203.0.113.0/24
# 切り替えの欠け(片道・10 ms 単位)。sla <送信元の CE> <故障 P1:PE2|PE2:X1>
# ★XRd は CML のリンクの停止をキャリア断として検知せず(IS-IS は hold time まで隣接を保つ)、BFD のセッションも作られない(2026-11-21 実測)
#  → 故障は「隣の XR の IF を shutdown」で起こす(P1:PE2= P1 の Gi0/0/0/1・PE2:X1= PE2 の Gi0/0/0/1)。検知は即時になり、測れるのは IGP の伝わりと入口の PE の反応。
shut_cmd() { local h=$1 ifn=$2 no=$3; echo ".venv/bin/python poc/xr/xrsh.py $h configure 'interface $ifn' '${no}shutdown' commit end"; }
sla() { local ce=$1 fail=$2 src h ifn; case $ce in CE1) src=192.168.1.1;; CE4) src=192.168.4.1;; esac
        echo "== SLA $ce($src)→ T 203.0.113.1・故障= ${fail:-なし}"
        case $fail in P1:PE2) h=$P1 ifn=GigabitEthernet0/0/0/1;; PE2:X1) h=$PE2 ifn=GigabitEthernet0/0/0/1;; esac
        if [ -n "$fail" ]; then .venv/bin/python poc/xr/sla_loss.py "$PID" "$ce" 203.0.113.1 "$src" --fail "$fail" --how cmd \
             --cmd "$(shut_cmd $h $ifn)" --undo "$(shut_cmd $h $ifn 'no ')" --at 3 --packets ${PKTS:-3000} --interval 10
        else .venv/bin/python poc/xr/sla_loss.py "$PID" "$ce" 203.0.113.1 "$src" --packets 300 --interval 10; fi; }
# 入口の PE で T 向けの経路を見る
look() { for h in "$@"; do echo "==== $(name $h)"
  S "$h" "show bgp $PFX" "show route $PFX detail" "show cef $PFX detail"; done; }
# リンクを戻した後、IS-IS・LDP・BGP が落ち着くのを待つ
settle() { sleep "${1:-60}"; S "$P1" 'show isis adjacency' 'show mpls ldp neighbor brief' | grep -E 'PE2|Up|10\.255' ; S "$RR1" 'show bgp summary' | grep -E '^10\.' ; }

a() {
  H "a: 版・IS-IS・LDP・BGP の確立・T への道(土台)"
  for h in $XRS; do echo "==== $(name $h)"; S "$h" 'show version | include Version' 'show isis adjacency' 'show mpls ldp neighbor brief' 'show bgp summary'; done
  for h in $X1 $X2 $CE1 $CE4; do S "$h" 'show ip bgp summary | begin Neighbor' 'show ip bgp'; done
  S "$CE1" 'ping 203.0.113.1 source 192.168.1.1 repeat 5' 'traceroute 203.0.113.1 source 192.168.1.1 probe 1 timeout 2'
  S "$CE4" 'ping 203.0.113.1 source 192.168.4.1 repeat 5' 'traceroute 203.0.113.1 source 192.168.4.1 probe 1 timeout 2'
  H "a2: 最初の状態の経路(PE3 の最良は PE2 経由の iBGP・RR1 と PE1 は道を 1 本しか知らない見込み)"
  for h in $PE3 $RR1; do echo "==== $(name $h)"; S "$h" "show bgp $PFX"; done
  look "$PE1" "$PE4"
}

defaults() {
  H "defaults: 何も設定していない時の既定(next-hop の追跡の遅延・fast-external-fallover・受ける経路数の上限・追加パスの能力)"
  for h in $PE1 $PE4; do echo "==== $(name $h)"
    S "$h" 'show bgp process detail' 'show bgp nexthops' 'show bgp neighbor 172.16.1.1' 'show bgp neighbor 10.255.0.21' 'show bgp neighbor 172.16.4.1'; done
  S "$PE2" 'show bgp neighbor 172.16.2.1'
}

help() {
  H "help: ? の一覧(追加パス・PIC・TTL セキュリティ・認証・上限・ダンプニング・集約)。PE1= XRd・PE4= XRv9000"
  for h in $PE1 $PE4; do echo "==== $(name $h)"
    Q "$h" 'show bgp ?' 'show bgp 203.0.113.0/24 ?' 'show cef 203.0.113.0/24 ?' \
      'configure' 'router bgp 65000' '?' 'bgp ?' 'address-family ipv4 unicast' '?' 'additional-paths ?' 'additional-paths selection ?' \
      'advertise ?' 'bgp ?' 'aggregate-address 192.168.0.0/16 ?' 'exit' \
      'neighbor 172.16.1.1' '?' 'ttl-security ?' 'password ?' 'keychain ?' 'ao ?' 'capability ?' 'ebgp-multihop ?' \
      'address-family ipv4 unicast' '?' 'maximum-prefix ?' 'maximum-prefix 10 ?' 'maximum-prefix 10 75 ?' 'capability ?' 'exit' 'exit' 'exit' \
      'route-policy QTEST' 'set path-selection ?' 'set path-selection backup ?' 'set path-selection backup 1 ?' 'set path-selection all ?' 'abort'
  done
}

pic0() {
  H "pic0: 何も足していない状態で、主の出口 PE2 を P1 から切る(P1─PE2 のリンクを止める)。入口= PE1(XRd)と PE4(XRv9000)"
  sla CE1; sla CE1 P1:PE2; settle 75
  sla CE4 P1:PE2; settle 75
}

be() {
  H "be: PE3 に advertise best-external → RR1 が PE3 の経路を知るか・PE1 にはまだ 1 本か"
  XC "$PE3" 'router bgp 65000' 'address-family ipv4 unicast' 'advertise best-external'
  sleep 15
  echo "==== PE3"; S "$PE3" "show bgp $PFX" "show bgp neighbor 10.255.0.21 advertised-routes"
  echo "==== RR1"; S "$RR1" "show bgp $PFX"
  look "$PE1"
}

pic0b() {
  H "pic0b: best-external だけの状態で PE2 を切る(RR1 は予備の道を持つが、反射は最良の 1 本だけ)"
  sla CE1 P1:PE2; settle 75
}

ap() {
  H "ap: 追加パス。RR1= send/receive と selection(backup 1 advertise)・PE1/PE4= receive。能力の交渉と、PE1 が 2 本を知るか(まだ install しない)"
  XC "$RR1" 'route-policy AP-RR' '  set path-selection backup 1 advertise' 'end-policy' \
            'router bgp 65000' 'address-family ipv4 unicast' 'additional-paths send' 'additional-paths receive' 'additional-paths selection route-policy AP-RR'
  for h in $PE1 $PE4; do XC "$h" 'router bgp 65000' 'address-family ipv4 unicast' 'additional-paths receive'; done
  # ★能力は OPEN で交渉する= 入れただけでは Additional-paths operation: None のまま(公式どおり)。張り直しは `clear bgp <近隣>`
  #  (XR の `clear bgp ipv4 unicast <近隣>` は soft しか続かず % Incomplete command.)
  for h in $PE1 $PE4; do S "$h" 'clear bgp 10.255.0.21' > /dev/null; done
  sleep 30
  echo "==== RR1"; S "$RR1" 'show bgp summary' "show bgp $PFX" 'show bgp neighbor 10.255.0.1' "show bgp neighbor 10.255.0.1 advertised-routes"
  for h in $PE1 $PE4; do echo "==== $(name $h)"; S "$h" 'show bgp summary' 'show bgp neighbor 10.255.0.21'; done
  look "$PE1" "$PE4"
}

pic1() {
  H "pic1: 追加パスで 2 本を知っているが install していない状態で PE2 を切る"
  sla CE1 P1:PE2; settle 75
  sla CE4 P1:PE2; settle 75
}

pic() {
  H "pic: PE1/PE4 に selection(backup 1 install)= PIC。予備の経路の表示"
  for h in $PE1 $PE4; do XC "$h" 'route-policy PIC' '  set path-selection backup 1 install' 'end-policy' \
      'router bgp 65000' 'address-family ipv4 unicast' 'additional-paths selection route-policy PIC'; done
  sleep 15
  look "$PE1" "$PE4"
}

pic2() {
  H "pic2: PIC(予備を install)の状態で PE2 を切る"
  sla CE1 P1:PE2; settle 75
  sla CE4 P1:PE2; settle 75
}

edge() {
  H "edge: 出口の PE2 と X1 の間のリンクを切る(PE2 は X1 を失う)。PE2 に予備が無い時"
  echo "==== PE2"; S "$PE2" "show bgp $PFX" "show cef $PFX detail"
  sla CE1 PE2:X1; settle 75
  H "edge2: PE2 にも追加パスの receive と PIC(backup 1 install)→ PE2 自身が PE3 経由の予備を持ち、ローカルに切り替えるか(ラベルなしなので PE3 が PE2 へ送り返すループになる見込み)"
  XC "$PE2" 'route-policy PIC' '  set path-selection backup 1 install' 'end-policy' \
      'router bgp 65000' 'address-family ipv4 unicast' 'additional-paths receive' 'additional-paths selection route-policy PIC'
  S "$PE2" 'clear bgp 10.255.0.21' > /dev/null
  sleep 30
  echo "==== PE2"; S "$PE2" "show bgp $PFX" "show route $PFX detail" "show cef $PFX detail"
  sla CE1 PE2:X1; settle 75
}

# ---- 1.5.b/1.5.c(PE2─X1 の eBGP と PE1─CE1 の eBGP で。セッションを張り直すので PIC の測定の後に流す)----
st() {  # 両端のセッションの状態
  S "$PE2" 'show bgp neighbor 172.16.2.1 | include BGP state|TTL|ttl|hop|Last reset|password|authentication|Connections'
  S "$X1" 'show ip bgp summary | include 172.16.2.254' 'show ip bgp neighbors 172.16.2.254 | include BGP state|hops|TTL|Last reset|password|Option'
}
ttl() {
  H "ttl1: XR(PE2)だけに ttl-security → clear → 状態(公式= OpenSent/OpenConfirm で止まる・RFC は片側を書いていない)。PE2─X1 のパケットを捕まえて TTL を見る"
  .venv/bin/python poc/xr/cml_cap.py "$PID" PE2 X1 start 'tcp port 179'
  XC "$PE2" 'router bgp 65000' 'neighbor 172.16.2.1' 'ttl-security'
  S "$PE2" 'clear bgp 172.16.2.1'; sleep 40; st
  H "ttl2: X1 にも neighbor ttl-security hops 1 → clear → 確立するか"
  IC "$X1" 'router bgp 65100' 'neighbor 172.16.2.254 ttl-security hops 1'
  S "$X1" 'clear ip bgp 172.16.2.254'; sleep 40; st
  .venv/bin/python poc/xr/cml_cap.py "$PID" PE2 X1 stop poc/xr/expBGPOPS-ttl.pcap
  .venv/bin/python poc/xr/pcap_ttl.py poc/xr/expBGPOPS-ttl.pcap
  H "ttl3: XR で ttl-security と ebgp-multihop を同居させる(公式= 許す・ttl-security が勝つ)/IOS で同居させる(公式= 排他でエラー)"
  XC "$PE2" 'router bgp 65000' 'neighbor 172.16.2.1' 'ebgp-multihop 2'
  S "$PE2" 'show running-config router bgp 65000 neighbor 172.16.2.1'
  IC "$X1" 'router bgp 65100' 'neighbor 172.16.2.254 ebgp-multihop 2'
  S "$X1" 'show running-config | section router bgp'
  H "ttl4: 片付け(両側から外す)"
  XC "$PE2" 'router bgp 65000' 'neighbor 172.16.2.1' 'no ebgp-multihop' 'no ttl-security'
  IC "$X1" 'router bgp 65100' 'no neighbor 172.16.2.254 ebgp-multihop' 'no neighbor 172.16.2.254 ttl-security hops 1'
  S "$X1" 'clear ip bgp 172.16.2.254'; sleep 40; st
}
maxp() {
  H "maxp0: CE1 が 4 本を広告(Loopback11〜13 を足す)。何も設定しない PE1 の表示"
  IC "$CE1" 'interface Loopback11' 'ip address 192.168.11.1 255.255.255.0' 'interface Loopback12' 'ip address 192.168.12.1 255.255.255.0' \
     'interface Loopback13' 'ip address 192.168.13.1 255.255.255.0' 'router bgp 65001' 'address-family ipv4' \
     'network 192.168.11.0' 'network 192.168.12.0' 'network 192.168.13.0'
  sleep 10; S "$PE1" 'show bgp summary' 'show bgp neighbor 172.16.1.1 | include accepted|Maximum|maximum|Threshold|limit'
  H "maxp1: maximum-prefix 3 75(上限 3・警告 75%)= 4 本で超える"
  XC "$PE1" 'router bgp 65000' 'neighbor 172.16.1.1' 'address-family ipv4 unicast' 'maximum-prefix 3 75'
  sleep 15; S "$PE1" 'show bgp summary' 'show bgp neighbor 172.16.1.1 | include BGP state|accepted|Maximum|maximum|Threshold|limit|Last reset|Cease' 'show logging last 20'
  S "$CE1" 'show ip bgp summary | begin Neighbor' 'show logging | include BGP|MAXPFX|NOTIFICATION'
  H "maxp2: warning-only に替えて clear"
  XC "$PE1" 'router bgp 65000' 'neighbor 172.16.1.1' 'address-family ipv4 unicast' 'maximum-prefix 3 75 warning-only'
  S "$PE1" 'clear bgp 172.16.1.1'; sleep 30
  S "$PE1" 'show bgp summary' 'show bgp neighbor 172.16.1.1 | include BGP state|accepted|Maximum|maximum|Threshold|limit' 'show logging last 10'
  H "maxp3: discard-extra-paths に替えて clear(超えた分を捨ててセッションは保つ)"
  XC "$PE1" 'router bgp 65000' 'neighbor 172.16.1.1' 'address-family ipv4 unicast' 'maximum-prefix 3 75 discard-extra-paths'
  S "$PE1" 'clear bgp 172.16.1.1'; sleep 30
  S "$PE1" 'show bgp summary' 'show bgp neighbor 172.16.1.1 | include BGP state|accepted|Maximum|maximum|Threshold|limit|discard' 'show bgp neighbor 172.16.1.1 routes'
  H "maxp4: restart 1(1 分後に張り直す)= 上限超えで切れたあと 1 分で戻るか"
  XC "$PE1" 'router bgp 65000' 'neighbor 172.16.1.1' 'address-family ipv4 unicast' 'maximum-prefix 3 75 restart 1'
  S "$PE1" 'clear bgp 172.16.1.1'; sleep 20
  S "$PE1" 'show bgp summary' 'show bgp neighbor 172.16.1.1 | include BGP state|Maximum|restart|Restart|Last reset'
  sleep 70; S "$PE1" 'show bgp summary' 'show bgp neighbor 172.16.1.1 | include BGP state|Maximum|restart|Restart|Last reset'
  H "maxp5: 片付け(上限を外し CE1 の 3 本も消す)"
  XC "$PE1" 'router bgp 65000' 'neighbor 172.16.1.1' 'address-family ipv4 unicast' 'no maximum-prefix'
  IC "$CE1" 'router bgp 65001' 'address-family ipv4' 'no network 192.168.11.0' 'no network 192.168.12.0' 'no network 192.168.13.0' \
     'no interface Loopback11' 'no interface Loopback12' 'no interface Loopback13'
  S "$PE1" 'clear bgp 172.16.1.1'; sleep 30; S "$PE1" 'show bgp summary'
}
damp() {
  H "damp1: PE2 に bgp dampening(既定値)。X1 の 10.199.9.0/24(Loopback9)を 3 回揺らす"
  IC "$X1" 'interface Loopback9' 'ip address 10.199.9.1 255.255.255.0' 'router bgp 65100' 'address-family ipv4' 'network 10.199.9.0 mask 255.255.255.0'
  XC "$PE2" 'router bgp 65000' 'address-family ipv4 unicast' 'bgp dampening'
  sleep 10; S "$PE2" 'show bgp 10.199.9.0/24' 'show bgp dampened-paths' 'show bgp flap-statistics'
  for i in 1 2 3; do IC "$X1" 'interface Loopback9' 'shutdown' > /dev/null; sleep 8; IC "$X1" 'interface Loopback9' 'no shutdown' > /dev/null; sleep 8
    echo "== 揺らし $i 回目の後"; S "$PE2" 'show bgp flap-statistics' 'show bgp 10.199.9.0/24' | grep -E 'Paths|flap|Flap|penalty|Penalty|suppress|Suppress|reuse|Reuse|dampen|Dampen|history|valid|^[*hd ]'; done
  S "$PE2" 'show bgp dampened-paths' 'show bgp 10.199.9.0/24' 'show bgp' ; S "$RR1" 'show bgp 10.199.9.0/24'
  H "damp2: clear bgp ipv4 unicast dampening で戻るか → 片付け"
  S "$PE2" 'clear bgp ipv4 unicast dampening'; sleep 5; S "$PE2" 'show bgp dampened-paths' 'show bgp 10.199.9.0/24'
  XC "$PE2" 'router bgp 65000' 'address-family ipv4 unicast' 'no bgp dampening'
}
agg() {
  H "agg1: PE2 で aggregate-address 192.168.0.0/16 summary-only(CE の 2 本を束ねて X1 へ)。PE2 の表示(s)・X1 と RR1 が受けるもの"
  XC "$PE2" 'router bgp 65000' 'address-family ipv4 unicast' 'aggregate-address 192.168.0.0/16 summary-only'
  sleep 15; S "$PE2" 'show bgp' 'show bgp 192.168.0.0/16' 'show bgp 192.168.1.0/24'; S "$X1" 'show ip bgp'; S "$RR1" 'show bgp'
  H "agg2: summary-only を外し route-policy で 192.168.1.0/24 だけ抑止(suppress-route)"
  XC "$PE2" 'route-policy AGG-SUP' '  if destination in (192.168.1.0/24) then' '    suppress-route' '  endif' 'end-policy' \
      'router bgp 65000' 'address-family ipv4 unicast' 'no aggregate-address 192.168.0.0/16 summary-only' 'aggregate-address 192.168.0.0/16 route-policy AGG-SUP'
  sleep 15; S "$PE2" 'show bgp' 'show running-config router bgp 65000 address-family ipv4 unicast'; S "$X1" 'show ip bgp'
  H "agg3: 片付け"
  XC "$PE2" 'router bgp 65000' 'address-family ipv4 unicast' 'no aggregate-address 192.168.0.0/16' 'no route-policy AGG-SUP'
}
ribf() {
  H "ribf1: RIB に入らない BGP の経路を XR は広告するか(IOS の bgp suppress-inactive の対照)。PE2 に 10.199.9.0/24 の static(Null0・AD 1)→ BGP の経路は RIB で負ける"
  IC "$X1" 'interface Loopback9' 'ip address 10.199.9.1 255.255.255.0' 'router bgp 65100' 'address-family ipv4' 'network 10.199.9.0 mask 255.255.255.0'
  sleep 10
  XC "$PE2" 'router static' 'address-family ipv4 unicast' '10.199.9.0/24 Null0'
  sleep 15; S "$PE2" 'show route 10.199.9.0/24' 'show bgp 10.199.9.0/24' 'show bgp' 'show bgp neighbor 10.255.0.21 advertised-routes'
  S "$RR1" 'show bgp 10.199.9.0/24'; S "$PE1" 'show bgp 10.199.9.0/24'
  H "ribf2: ? で suppress-inactive に当たるものがあるか(XR)"
  Q "$PE2" 'configure' 'router bgp 65000' 'bgp ?' 'address-family ipv4 unicast' 'bgp ?' 'abort'
  H "ribf3: 対照= IOS(X2)でも同じ形を作る(X2 に static 10.199.9.0/24 Null0 → X2 が PE3 へ広告するか)。続いて bgp suppress-inactive"
  IC "$X2" 'ip route 10.199.9.0 255.255.255.0 Null0'
  sleep 10; S "$X2" 'show ip bgp 10.199.9.0' 'show ip bgp rib-failure' 'show ip bgp neighbors 172.16.3.254 advertised-routes'
  IC "$X2" 'router bgp 65100' 'address-family ipv4' 'bgp suppress-inactive'
  sleep 15; S "$X2" 'show ip bgp 10.199.9.0' 'show ip bgp neighbors 172.16.3.254 advertised-routes'; S "$PE3" 'show bgp 10.199.9.0/24'
  H "ribf4: 片付け"
  IC "$X2" 'router bgp 65100' 'address-family ipv4' 'no bgp suppress-inactive' 'exit' 'exit' 'no ip route 10.199.9.0 255.255.255.0 Null0'
  XC "$PE2" 'router static' 'address-family ipv4 unicast' 'no 10.199.9.0/24 Null0'
}

auth() {
  H "auth1: XR(PE2)だけに password(MD5)→ clear → 状態・IOS のログ"
  XC "$PE2" 'router bgp 65000' 'neighbor 172.16.2.1' 'password clear LAB-MD5'
  S "$PE2" 'clear bgp 172.16.2.1' > /dev/null; sleep 30; st; S "$X1" 'show logging | include BADAUTH|MD5|TCP-6|AUTH'
  H "auth2: X1 にも neighbor password LAB-MD5 → 確立するか(XR と IOS の MD5)"
  IC "$X1" 'router bgp 65100' 'neighbor 172.16.2.254 password LAB-MD5'
  S "$X1" 'clear ip bgp 172.16.2.254'; sleep 40; st
  H "auth3: PE2 を password から keychain(暗号= MD5)へ。相手の IOS は password のまま(公式= keychain は draft-bonica の方式で password とつながらない)"
  XC "$PE2" 'key chain MD5-KC' 'key 1' 'key-string clear LAB-MD5' 'cryptographic-algorithm MD5' \
      'accept-lifetime 00:00:00 january 01 2026 infinite' 'send-lifetime 00:00:00 january 01 2026 infinite' 'exit' 'exit' \
      'router bgp 65000' 'neighbor 172.16.2.1' 'no password' 'keychain MD5-KC'
  S "$PE2" 'show running-config key chain MD5-KC' 'show running-config router bgp 65000 neighbor 172.16.2.1'
  S "$PE2" 'clear bgp 172.16.2.1' > /dev/null; sleep 40; st
  H "auth3b: password と keychain の同居(公式= 1 つの方式だけ・ほかはコミットで拒む)"
  XC "$PE2" 'router bgp 65000' 'neighbor 172.16.2.1' 'password clear LAB-MD5'
  H "auth4: TCP-AO(XR= key chain の AES-128-CMAC-96+tcp ao の SendID/ReceiveID+neighbor の ao/IOS= key chain … tcp+neighbor ao)"
  XC "$PE2" 'key chain AO-KC' 'key 1' 'key-string clear 0123456789ABCDEF0123456789ABCDEF' 'cryptographic-algorithm AES-128-CMAC-96' \
      'accept-lifetime 00:00:00 january 01 2026 infinite' 'send-lifetime 00:00:00 january 01 2026 infinite' 'exit' 'exit' \
      'tcp ao' 'keychain AO-KC' 'key 1 SendID 1 ReceiveID 1' 'exit' 'exit' \
      'router bgp 65000' 'neighbor 172.16.2.1' 'no keychain' 'ao AO-KC include-tcp-options enable'
  IC "$X1" 'key chain AO-KC tcp' 'key 1' 'send-id 1' 'recv-id 1' 'key-string 0123456789ABCDEF0123456789ABCDEF' 'cryptographic-algorithm aes-128-cmac' 'exit' 'exit' \
      'router bgp 65100' 'no neighbor 172.16.2.254 password' 'neighbor 172.16.2.254 ao AO-KC include-tcp-options'
  S "$X1" 'clear ip bgp 172.16.2.254'; sleep 45; st
  S "$PE2" 'show tcp authentication keychain AO-KC' 'show running-config tcp ao' 'show running-config router bgp 65000 neighbor 172.16.2.1'
  S "$X1" 'show tcp ao key-chain AO-KC' 'show ip bgp neighbors 172.16.2.254 | include TCP-AO|AO|ao|BGP state'
  H "auth5: 片付け(どちらも外す)"
  XC "$PE2" 'router bgp 65000' 'neighbor 172.16.2.1' 'no ao' 'exit' 'exit' 'no tcp ao' 'no key chain AO-KC' 'no key chain MD5-KC'
  IC "$X1" 'router bgp 65100' 'no neighbor 172.16.2.254 ao AO-KC' 'exit' 'no key chain AO-KC'
  S "$X1" 'clear ip bgp 172.16.2.254'; sleep 40; st
}

case_all() { for p in "$@"; do "$p"; done; }
case_all "$@"
