#!/bin/bash
# BL-246 M12 PoC= データプレーンの保護と QoS(SPCOR 1.7・4.5・1.4)。盤面= problems/_POC-XRQOS
#   XR01= XRv9000 26.1.1(PE 兼インターネットの出入り口)・P1= IOL(P)・PE2= IOL(PE)・RR1= XRd(RR 兼 RTBH の起点・道の外)
#   CE1/CE2= VRF A の CE・CUST1(XR01)/CUST2(PE2)= グローバルのお客さま・INET= インターネット役(AS 64500)
# 記録= design §27。usage: source poc/xr/env.sh; poc/xr/qos_poc.sh <phase…>   出力は標準出力(呼び出し側で poc/xr/expQOS-<phase>.log へ)
cd "$(dirname "$0")/../.."
PID=${PID:-_POC-XRQOS}
M=topologies/_generated/$PID/mgmt_map.yml
ip() { awk -v n="$1:" '$1==n{print $2}' "$M"; }
X1=$(ip XR01) P1=$(ip P1) E2=$(ip PE2) R1=$(ip RR1)
C1=$(ip CE1) C2=$(ip CE2) U1=$(ip CUST1) U2=$(ip CUST2) IN=$(ip INET)
S() { local h=$1; shift; .venv/bin/python poc/xr/xrsh.py "$h" "$@" 2>&1; }
H() { echo; echo "######## $(date +%T) $*"; }
CAP() { .venv/bin/python poc/xr/cml_cap.py "$PID" "$@" 2>&1 | tail -1; }
DEC() { echo "---- $1"; tcpdump -r "$1" -nn -v -e -c "${2:-6}" 2>/dev/null | cut -c1-300; }
XC() { local h=$1; shift; S "$h" configure "$@" commit 'show configuration failed' end; }   # XR: configure → 行 → commit
IC() { local h=$1; shift; S "$h" 'configure terminal' "$@" end; }                           # IOS: configure terminal → 行 → end

a() {
  H "a: 版・土台(IS-IS・LDP・BGP)・到達性"
  S "$X1" 'show version | include Version' 'show install active summary' 'show license platform summary' \
    'show isis adjacency' 'show mpls ldp neighbor brief' 'show bgp all all summary' 'show bgp vrf A summary'
  S "$R1" 'show version | include Version' 'show bgp all all summary'
  S "$E2" 'show bgp all summary' 'show ip route vrf A'
  S "$C1" 'show ip bgp' 'ping 10.100.2.1 source Loopback100 repeat 5'
  S "$U1" 'ping 198.51.100.130 source Loopback0 repeat 5' 'ping 203.0.113.1 source Loopback0 repeat 5' 'traceroute 198.51.100.130 source Loopback0 probe 1 timeout 2'
  S "$IN" 'show ip bgp' 'ping 198.51.100.130 source Loopback0 repeat 5' 'ping 198.51.100.1 source Loopback0 repeat 5'
}

mark() {
  H "mark: CE に「音声の宛て」「大量の宛て」を足し、CE の出口で宛てごとに DSCP を付ける(試験用のトラフィック)"
  #   CE<n>: Loopback46 10.46.0.<n>/32(EF の宛て)・Loopback10 10.10.0.<n>/32(AF11 の宛て)。相手の CE の Lo46/Lo10 宛ては EF/AF11 を付けて出す
  for n in 1 2; do h=$C1; [ $n = 2 ] && h=$C2; o=$((3-n))
    IC "$h" "interface Loopback46" "ip address 10.46.0.$n 255.255.255.255" "interface Loopback10" "ip address 10.10.0.$n 255.255.255.255" \
      "ip access-list extended TO-VOICE" "permit ip any host 10.46.0.$o" "ip access-list extended TO-BULK" "permit ip any host 10.10.0.$o" \
      "class-map match-any TO-VOICE" "match access-group name TO-VOICE" "class-map match-any TO-BULK" "match access-group name TO-BULK" \
      "policy-map MARK" "class TO-VOICE" "set dscp ef" "class TO-BULK" "set dscp af11" "exit" "exit" \
      "interface Ethernet0/0" "service-policy output MARK" \
      "router bgp 6500$n" "address-family ipv4" "network 10.46.0.$n mask 255.255.255.255" "network 10.10.0.$n mask 255.255.255.255"
  done
  sleep 20
  S "$C1" 'show ip bgp' 'ping 10.46.0.2 source Loopback46 repeat 5' 'ping 10.10.0.2 source Loopback10 repeat 5' 'show policy-map interface Ethernet0/0 output'
}

echo_n() { S "$1" 'show ip traffic' | awk '/Rcvd:/{r=1} r&&/echo/{print $1; exit}'; }   # その機器が受けた echo の数
xif() { S "$X1" "show interfaces $1" | grep -E "rate|packets input|packets output|drops" | sed "s|^|  $1: |"; }
thr() {
  H "thr: 方策なしで XR01 を通る量の上限(200 kbps の制限)を見る。CE1 → CE2 に間を空けずに 1000 発。CE2 が受けた数と所要時間"
  for sz in 1000 100; do
    a=$(echo_n "$C2"); t0=$(date +%s.%N)
    S "$C1" "ping 10.100.2.1 source Loopback100 repeat 1000 size $sz timeout 0" > /dev/null
    t1=$(date +%s.%N); sleep 3; b=$(echo_n "$C2")
    echo "size $sz: 送った 1000 → CE2 が受けた $((b-a))  所要 $(echo "$t1 - $t0" | bc) 秒(SSH 込み)"
  done
  xif GigabitEthernet0/0/0/1; xif GigabitEthernet0/0/0/0
  a=$(echo_n "$U2"); S "$U1" 'ping 198.51.100.130 source Loopback0 repeat 1000 size 1000 timeout 0' > /dev/null; sleep 3; b=$(echo_n "$U2")
  echo "グローバル size 1000: 送った 1000 → CUST2 が受けた $((b-a))"
}

# ---- 線の上の捕獲(MPLS の QoS のモデル)。4 本の線で同時に捕まえ、試験のトラフィックを流して止める
LINKS="XR01:P1 P1:PE2 PE2:CE2 XR01:CE1"
capall() {   # capall <名前> <流す関数>
  local tag=$1 fn=$2
  for l in $LINKS; do CAP "${l%%:*}" "${l##*:}" start >/dev/null; done
  sleep 3; $fn; sleep 3
  for l in $LINKS; do f=poc/xr/pcap/qos-$tag-${l%%:*}-${l##*:}.pcap; CAP "${l%%:*}" "${l##*:}" stop "$f"; done
  for l in $LINKS; do f=poc/xr/pcap/qos-$tag-${l%%:*}-${l##*:}.pcap
    echo "---- $f(ICMP・ラベル/TC の積み方は左が外側)"; .venv/bin/python poc/xr/pcap_qos.py "$f" 40
  done
}
traf_vpn() {   # CE1 → CE2 の 3 種(EF・AF11・印なし)を 3 発ずつ
  S "$C1" 'ping 10.46.0.2 source Loopback46 repeat 3' 'ping 10.10.0.2 source Loopback10 repeat 3' 'ping 10.100.2.1 source Loopback100 repeat 3' | grep -E "Success|!!!"
}
traf_rev() {   # CE2 → CE1(XR01 が出口 PE)
  S "$C2" 'ping 10.46.0.1 source Loopback46 repeat 3' 'ping 10.10.0.1 source Loopback10 repeat 3' 'ping 10.100.1.1 source Loopback100 repeat 3' | grep -E "Success|!!!"
}
traf_inet() {  # グローバル= CUST1 → CUST2(BGP の次ホップへ LDP のラベル 1 枚)
  S "$U1" 'ping 198.51.100.130 source Loopback0 repeat 3' | grep -E "Success|!!!"
}
traf_all() { traf_vpn; traf_rev; traf_inet; }

cap0() { H "cap0: 方策なしの既定= CE の DSCP は EXP に写るか・PHP の後・出口の DSCP"; mkdir -p poc/xr/pcap; capall def traf_all; }

xmark() {
  H "xmark: XR01 の CE1 側の入力で分類して EXP を付ける(DSCP は触らない= パイプ/ショート パイプの入口)。qos-group も付ける"
  XC "$X1" 'class-map match-any VOICE' 'match dscp ef' 'end-class-map' \
    'class-map match-any BULK' 'match dscp af11' 'end-class-map' \
    'policy-map CE-IN' 'class VOICE' 'set mpls experimental imposition 5' 'set qos-group 5' 'exit' \
    'class BULK' 'set mpls experimental imposition 2' 'set qos-group 2' 'exit' \
    'class class-default' 'set mpls experimental imposition 0' 'exit' 'end-policy-map' \
    'interface GigabitEthernet0/0/0/1' 'service-policy input CE-IN' 'root'
  S "$X1" 'show running-config policy-map CE-IN' 'show qos interface GigabitEthernet0/0/0/1 input'
  capall imp traf_vpn
  S "$X1" 'show policy-map interface GigabitEthernet0/0/0/1 input'
}

p1remark() {
  H "p1remark: P1(IOL)が XR01 から来た EXP 5 を 0 に付け替える(混雑時の付け替えの模擬)→ PHP の後に内側の EXP はどうなるか"
  IC "$P1" 'class-map match-any EXP5' 'match mpls experimental topmost 5' 'policy-map REMARK' 'class EXP5' 'set mpls experimental topmost 0' 'exit' 'exit' \
    'interface Ethernet0/0' 'service-policy input REMARK'
  capall rmk traf_vpn
  S "$P1" 'show policy-map interface Ethernet0/0 input'
}

enull() {
  H "enull: PE2 が explicit null を広告 → P1→PE2 の線にラベル 0(と EXP)が残るか"
  IC "$E2" 'mpls ldp explicit-null'
  sleep 10
  S "$P1" 'show mpls forwarding-table 10.255.0.2 32'
  capall enl traf_all
}

xegress() {
  H "xegress: XR01 を出口 PE に= コア側の入力で EXP → qos-group、CE1 側の出力で qos-group → DSCP(ユニフォーム)。P1 は PE2 から来た EXP 5 を 0 へ"
  IC "$P1" 'interface Ethernet0/1' 'service-policy input REMARK'
  XC "$X1" 'class-map match-any EXP0' 'match mpls experimental topmost 0' 'end-class-map' \
    'class-map match-any EXP5' 'match mpls experimental topmost 5' 'end-class-map' \
    'policy-map CORE-IN' 'class EXP5' 'set qos-group 5' 'exit' 'class EXP0' 'set qos-group 7' 'exit' 'end-policy-map' \
    'class-map match-any QG7' 'match qos-group 7' 'end-class-map' \
    'policy-map CE-OUT-UNIFORM' 'class QG7' 'set dscp default' 'exit' 'end-policy-map' \
    'interface GigabitEthernet0/0/0/0' 'service-policy input CORE-IN' 'root' \
    'interface GigabitEthernet0/0/0/1' 'service-policy output CE-OUT-UNIFORM' 'root'
  sleep 5; capall uni traf_rev
  S "$X1" 'show policy-map interface GigabitEthernet0/0/0/0 input' 'show policy-map interface GigabitEthernet0/0/0/1 output'
  H "xegress-2: XR01 が explicit null を広告 → P1 の付け替え(外側の EXP 0)が XR01 に届くか → qos-group 7 → DSCP 0"
  XC "$X1" 'mpls ldp' 'address-family ipv4' 'label' 'local' 'advertise' 'explicit-null' 'root'
  sleep 10; S "$P1" 'show mpls forwarding-table 10.255.0.1 32'
  S "$X1" 'clear qos counters interface GigabitEthernet0/0/0/0 input'
  capall uni2 traf_rev
  S "$X1" 'show policy-map interface GigabitEthernet0/0/0/0 input' 'show policy-map interface GigabitEthernet0/0/0/1 output'
}

mon() {  # CE2 の入力に DSCP ごとに数えるだけの方策(観測用)
  IC "$C2" 'class-map match-any D-EF' 'match dscp ef' 'class-map match-any D-AF11' 'match dscp af11' 'class-map match-any D-AF12' 'match dscp af12' \
    'class-map match-any D-BE' 'match dscp default' 'policy-map MONITOR' 'class D-EF' 'class D-AF11' 'class D-AF12' 'class D-BE' 'exit' 'exit' \
    'interface Ethernet0/0' 'service-policy input MONITOR'
}
monshow() { S "$C2" 'show policy-map interface Ethernet0/0 input' | awk '/Class-map:/{c=$2} /packets, .* bytes/ && c!=""{print "  CE2 受信 " c " " $1 " pkts"; c=""}'; }
police() {
  H "police: XR01 の CE1 側の入力で BULK(AF11)を 64 kbps に(1 速度 2 色)→ 2 速度 3 色(超過は AF12 に付け替え)。カウンタは 30 秒待って見る"
  mon
  XC "$X1" 'policy-map CE-IN' 'class BULK' 'police rate 64 kbps' 'conform-action transmit' 'exceed-action drop' 'exit' 'exit' 'end-policy-map'
  S "$X1" 'clear qos counters interface GigabitEthernet0/0/0/1 input' > /dev/null; S "$C2" 'clear counters' '' > /dev/null
  S "$C1" 'ping 10.10.0.2 source Loopback10 repeat 1000 size 500 timeout 0' > /dev/null
  sleep 30; S "$X1" 'show policy-map interface GigabitEthernet0/0/0/1 input' | sed -n '/Class BULK/,/Class class-default/p'; monshow
  H "police-2: 2 速度 3 色(CIR 64k・PIR 128k・超過は AF12)。★1 つの class の印は 2 種類まで→ BULK の qos-group を外す"
  XC "$X1" 'policy-map CE-IN' 'class BULK' 'no set qos-group 2' 'no police' 'police rate 64 kbps peak-rate 128 kbps' 'conform-action transmit' 'exceed-action set dscp af12' 'violate-action drop' 'exit' 'exit' 'end-policy-map'
  S "$X1" 'show running-config policy-map CE-IN' 'clear qos counters interface GigabitEthernet0/0/0/1 input' > /dev/null; S "$C2" 'clear counters' '' > /dev/null
  S "$C1" 'ping 10.10.0.2 source Loopback10 repeat 1000 size 500 timeout 0' > /dev/null
  sleep 30; S "$X1" 'show running-config policy-map CE-IN' 'show policy-map interface GigabitEthernet0/0/0/1 input' | sed -n '/Class BULK/,/Class class-default/p'; monshow
  H "police-3: ポリサの値の単位と最小値・バーストの既定(show qos interface)"
  S "$X1" 'show qos interface GigabitEthernet0/0/0/1 input' | sed -n '/Class: BULK/,/Class: class-default/p'
}

shape() {
  H "shape: XR01 の CE1 側の出力= 親で 100 kbps に整形・子で EF を優先(priority level 1+ポリサ)・残りは既定のキュー"
  XC "$X1" 'interface GigabitEthernet0/0/0/1' 'no service-policy output CE-OUT-UNIFORM' 'root' \
    'policy-map CE-OUT-CHILD' 'class VOICE' 'priority level 1' 'police rate 32 kbps' 'exit' 'exit' 'class class-default' 'queue-limit 20 packets' 'exit' 'end-policy-map' \
    'policy-map CE-OUT' 'class class-default' 'shape average 100 kbps' 'service-policy CE-OUT-CHILD' 'exit' 'end-policy-map' \
    'interface GigabitEthernet0/0/0/1' 'service-policy output CE-OUT' 'root'
  S "$X1" 'show qos interface GigabitEthernet0/0/0/1 output'
}

load_rev() {  # 輻輳の窓: CE2 → CE1 の AF11 を約 25 秒間あいだを空けずに流し、6 秒後から EF と印なしの ping の遅れと欠けを測る
  S "$C2" 'ping 10.10.0.1 source Loopback10 repeat 15000 size 1000 timeout 0' > /dev/null &
  sleep 6
  S "$C2" 'ping 10.46.0.1 source Loopback46 repeat 50 size 100 timeout 1' 'ping 10.100.1.1 source Loopback100 repeat 10 size 100 timeout 1' | grep -E "Success"
  wait; sleep 25
}
shapetest() {
  H "shapetest: 方策なし→整形+優先で、輻輳中の EF・印なしの遅れと欠け"
  XC "$X1" 'interface GigabitEthernet0/0/0/1' 'no service-policy output CE-OUT' 'root'; load_rev
  XC "$X1" 'interface GigabitEthernet0/0/0/1' 'service-policy output CE-OUT' 'root'
  S "$X1" 'clear qos counters interface GigabitEthernet0/0/0/1 output'; load_rev
  S "$X1" 'show policy-map interface GigabitEthernet0/0/0/1 output' | grep -E "^Class|Policy CE|Matched|Transmitted|Total Dropped|Taildropped|Policed"
}

wred() {
  H "wred: 子の class-default に WRED(既定・DSCP ごと)"
  XC "$X1" 'policy-map CE-OUT-CHILD' 'class class-default' 'random-detect default' 'exit' 'end-policy-map'
  XC "$X1" 'policy-map CE-OUT-CHILD' 'class class-default' 'no random-detect default' 'random-detect dscp af11 10 packets 20 packets' 'random-detect dscp default 5 packets 10 packets' 'exit' 'end-policy-map'
  S "$X1" 'show running-config policy-map CE-OUT-CHILD' 'clear qos counters interface GigabitEthernet0/0/0/1 output'; load_rev
  S "$X1" 'show policy-map interface GigabitEthernet0/0/0/1 output'
}

ttl() {
  H "ttl: traceroute にコアが見えるか(既定)→ XR01 で mpls ip-ttl-propagate disable"
  S "$U1" 'traceroute 198.51.100.130 source Loopback0 probe 1 timeout 2'
  S "$C1" 'traceroute 10.100.2.1 source Loopback100 probe 1 timeout 2'
  XC "$X1" 'mpls ip-ttl-propagate disable'
  S "$U1" 'traceroute 198.51.100.130 source Loopback0 probe 1 timeout 2'
  S "$C1" 'traceroute 10.100.2.1 source Loopback100 probe 1 timeout 2'
  XC "$X1" 'no mpls ip-ttl-propagate disable'
}

rcv() { S "$U2" 'show ip traffic | include Rcvd|echo' | grep -E "echo" | head -2; }   # CUST2 が受けた echo の数
spoof() {   # CUST1 から 3 つの送信元で CUST2 宛てに 10 発ずつ。CUST2 が受けた echo の数の増え方で、XR01 で落ちたかを見る
  for src in Loopback0 Loopback9 Loopback10; do
    a=$(S "$U2" 'show ip traffic' | awk '/Rcvd:/{r=1} r&&/echo/{print $1; exit}')
    S "$U1" "ping 198.51.100.130 source $src repeat 10 timeout 1" | grep -E "Success" | sed "s/^/$src: /"
    b=$(S "$U2" 'show ip traffic' | awk '/Rcvd:/{r=1} r&&/echo/{print $1; exit}')
    echo "   CUST2 が受けた echo: $a → $b"
  done
}
urpf() {
  H "urpf: XR01 の CUST1 側に厳格(rx)→ 緩い(any)→ 既定経路を足して緩い+allow-default。送信元= 割り当て内/インターネットの番号/経路なし"
  echo "== 方策なし"; spoof
  XC "$X1" 'interface GigabitEthernet0/0/0/2' 'ipv4 verify unicast source reachable-via rx' 'root'
  echo "== 厳格(rx)"; spoof
  S "$X1" 'show cef ipv4 interface GigabitEthernet0/0/0/2 detail' 'show cef ipv4 drops' 'show cef drops'
  XC "$X1" 'interface GigabitEthernet0/0/0/2' 'ipv4 verify unicast source reachable-via any' 'root'
  echo "== 緩い(any)"; spoof
  XC "$X1" 'router static' 'address-family ipv4 unicast' '0.0.0.0/0 10.0.100.100' 'root'
  echo "== 緩い(any)+既定経路あり"; spoof
  XC "$X1" 'interface GigabitEthernet0/0/0/2' 'ipv4 verify unicast source reachable-via any allow-default' 'root'
  echo "== 緩い(any)+allow-default"; spoof
  XC "$X1" 'interface GigabitEthernet0/0/0/2' 'no ipv4 verify unicast source reachable-via any allow-default' 'root' \
    'router static' 'address-family ipv4 unicast' 'no 0.0.0.0/0 10.0.100.100' 'root'
}

rtbh() {
  H "rtbh: 宛てで捨てる= RR1(XRd)で静的経路にタグ 666 → RPL で次ホップ 192.0.2.1 と印 → XR01・PE2 は 192.0.2.1 → Null0"
  XC "$R1" 'route-policy RTBH-TRIGGER' 'if tag eq 666 then' 'set next-hop 192.0.2.1' 'set community (no-export, 65000:666)' 'pass' 'else' 'drop' 'endif' 'end-policy' \
    'router static' 'address-family ipv4 unicast' '198.51.100.130/32 Null0 tag 666' 'root' \
    'router bgp 65000' 'address-family ipv4 unicast' 'redistribute static route-policy RTBH-TRIGGER' 'root'
  sleep 15
  S "$R1" 'show bgp ipv4 unicast 198.51.100.130/32'
  S "$X1" 'show bgp ipv4 unicast 198.51.100.130/32' 'show route 198.51.100.130/32' 'show cef 198.51.100.130/32'
  S "$E2" 'show ip bgp 198.51.100.130/32' 'show ip cef 198.51.100.130 255.255.255.255 detail'
  S "$IN" 'show ip bgp' 'ping 198.51.100.130 source Loopback0 repeat 5' 'ping 198.51.100.129 source Loopback0 repeat 5'
}
discard() {
  H "discard: XR01 の入力の RPL で、印 65000:666 の経路を set next-hop discard(起点は印だけ付け、次ホップは書き換えない)"
  XC "$R1" 'route-policy RTBH-TRIGGER' 'if tag eq 666 then' 'set community (no-export, 65000:666)' 'pass' 'else' 'drop' 'endif' 'end-policy'
  XC "$X1" 'community-set RTBH' '65000:666' 'end-set' \
    'route-policy FROM-RR' 'if community matches-any RTBH then' 'set next-hop discard' 'endif' 'pass' 'end-policy' \
    'router bgp 65000' 'neighbor 10.255.0.52' 'address-family ipv4 unicast' 'route-policy FROM-RR in' 'root'
  sleep 15
  S "$X1" 'show bgp ipv4 unicast 198.51.100.130/32' 'show route 198.51.100.130/32' 'show cef 198.51.100.130/32'
  S "$IN" 'ping 198.51.100.130 source Loopback0 repeat 5' 'ping 198.51.100.129 source Loopback0 repeat 5'
}
srtbh() {
  H "srtbh: 送信元で捨てる= 攻撃元 203.0.113.66 を同じ仕組みで捨て先へ向け、XR01 の INET 側に緩い uRPF"
  XC "$R1" 'router static' 'address-family ipv4 unicast' '203.0.113.66/32 Null0 tag 666' 'root'
  sleep 15
  S "$X1" 'show route 203.0.113.66/32' 'show cef 203.0.113.66/32'
  for s in Loopback0 Loopback66; do
    a=$(S "$U2" 'show ip traffic' | awk '/Rcvd:/{r=1} r&&/echo/{print $1; exit}')
    S "$IN" "ping 198.51.100.129 source $s repeat 10 timeout 1" | grep Success | sed "s/^/(uRPF なし) $s: /"
    b=$(S "$U2" 'show ip traffic' | awk '/Rcvd:/{r=1} r&&/echo/{print $1; exit}'); echo "   CUST2 が受けた echo: $a → $b"
  done
  XC "$X1" 'interface GigabitEthernet0/0/0/3' 'ipv4 verify unicast source reachable-via any' 'root'
  for s in Loopback0 Loopback66; do
    a=$(S "$U2" 'show ip traffic' | awk '/Rcvd:/{r=1} r&&/echo/{print $1; exit}')
    S "$IN" "ping 198.51.100.129 source $s repeat 10 timeout 1" | grep Success | sed "s/^/(緩い uRPF) $s: /"
    b=$(S "$U2" 'show ip traffic' | awk '/Rcvd:/{r=1} r&&/echo/{print $1; exit}'); echo "   CUST2 が受けた echo: $a → $b"
  done
  S "$X1" 'show cef ipv4 drops' | grep -E "RPF drops|Null0 drops"
  H "srtbh-2: 同じことを次ホップ 192.0.2.1(→ Null0 への再帰)の形で= XR01 の入力の discard を外し、起点で次ホップを書く"
  XC "$R1" 'route-policy RTBH-TRIGGER' 'if tag eq 666 then' 'set next-hop 192.0.2.1' 'set community (no-export, 65000:666)' 'pass' 'else' 'drop' 'endif' 'end-policy'
  XC "$X1" 'router bgp 65000' 'neighbor 10.255.0.52' 'address-family ipv4 unicast' 'no route-policy FROM-RR in' 'root'
  sleep 20
  S "$X1" 'show route 203.0.113.66/32' 'show cef 203.0.113.66/32' | grep -E "via|Null|null|Known"
  for s in Loopback0 Loopback66; do
    a=$(S "$U2" 'show ip traffic' | awk '/Rcvd:/{r=1} r&&/echo/{print $1; exit}')
    S "$IN" "ping 198.51.100.129 source $s repeat 10 timeout 1" | grep Success | sed "s/^/(緩い uRPF・192.0.2.1 の再帰) $s: /"
    b=$(S "$U2" 'show ip traffic' | awk '/Rcvd:/{r=1} r&&/echo/{print $1; exit}'); echo "   CUST2 が受けた echo: $a → $b"
  done
  sleep 15; S "$X1" 'show cef ipv4 drops' | grep -E "RPF drops|Null0 drops"
}

acl() {
  H "acl: インフラ ACL= INET から SP のアドレス(コア 10.0.0.0/16・ループバック 10.255.0.0/24)宛てを落とし、BGP と他は通す。★object-group は XRv9000 で不可(実測)→ 行で書く"
  IC "$IN" 'ip route 10.0.0.0 255.0.0.0 10.0.100.1'
  S "$IN" 'ping 10.255.0.1 repeat 5' 'ping 10.0.1.1 repeat 5' | grep Success
  XC "$X1" 'ipv4 access-list IACL' '10 permit tcp host 10.0.100.100 host 10.0.100.1 eq bgp' '20 permit tcp host 10.0.100.100 eq bgp host 10.0.100.1' \
    '30 deny ipv4 any 10.0.0.0/16' '40 deny ipv4 any 10.255.0.0/24' '50 permit ipv4 any any' 'exit' \
    'interface GigabitEthernet0/0/0/3' 'ipv4 access-group IACL ingress hardware-count' 'root'
  S "$IN" 'ping 10.255.0.1 repeat 5' 'ping 10.0.1.1 repeat 5' 'ping 198.51.100.129 source Loopback0 repeat 5' | grep Success
  S "$IN" 'show ip bgp summary | include 10.0.100.1'
  sleep 15
  S "$X1" 'show access-lists ipv4 IACL' 'show access-lists ipv4 IACL hardware ingress location 0/0/CPU0' 'show running-config interface GigabitEthernet0/0/0/3'
}
abf() {
  H "abf: ACL で次ホップを変える(攻撃される宛てを洗浄の役= CUST1 へ寄せる)の可否。★ACL の名前 ABF は予約語(実測)"
  XC "$X1" 'ipv4 access-list TO-SCRUB' '10 permit ipv4 any host 198.51.100.130 nexthop1 ipv4 172.20.1.1' '20 permit ipv4 any any' 'exit' \
    'interface GigabitEthernet0/0/0/3' 'no ipv4 access-group IACL ingress' 'ipv4 access-group TO-SCRUB ingress' 'root'
  a=$(echo_n "$U1"); c=$(echo_n "$U2")
  S "$IN" 'ping 198.51.100.130 source Loopback0 repeat 10 timeout 1' 'ping 198.51.100.129 source Loopback0 repeat 5' | grep Success
  b=$(echo_n "$U1"); d=$(echo_n "$U2"); echo "   CUST1(洗浄役)が受けた echo: $a → $b / CUST2: $c → $d"
  S "$X1" 'show access-lists ipv4 TO-SCRUB'
  XC "$X1" 'interface GigabitEthernet0/0/0/3' 'no ipv4 access-group TO-SCRUB ingress' 'root'
}
macsec() {
  H "macsec: MACsec の可否(パッケージ・構文)"
  S "$X1" 'show install active summary | include -i macsec|k9sec|sec' 'show running-config macsec-policy'
  XC "$X1" 'key chain MKA' 'macsec' 'key 01' 'key-string password 0123456789ABCDEF0123456789ABCDEF cryptographic-algorithm aes-128-cmac' 'lifetime 00:00:00 january 01 2020 infinite' 'root' \
    'macsec-policy MP' 'exit' 'interface GigabitEthernet0/0/0/1' 'macsec psk-keychain MKA policy MP' 'root'
}

cfg() {
  H "cfg: 設定例の元(running-config)"
  S "$X1" 'show running-config class-map' 'show running-config policy-map' 'show running-config interface' 'show running-config route-policy' 'show running-config router bgp' 'show running-config ipv4 access-list'
  S "$R1" 'show running-config route-policy' 'show running-config router static' 'show running-config router bgp'
  S "$P1" 'show running-config | section policy-map|class-map'
}

for p in "$@"; do "$p"; done
