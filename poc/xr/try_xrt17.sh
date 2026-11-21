#!/bin/bash
# XRT-17 の盤面で、読み物(M6 追補 65-m6-protect-session・67-m6-limit-damp-agg)の設定例の値のまま測る。上限= 3 80(課題 4 75)・ダンプニング= 既定値(課題 10)・集約= /16(課題 /22)。課題とは場所と値をずらしてある
# (課題= GTSM は PE2─X1・TCP-AO は PE3─X2 の 37/73)。読み物= GTSM は PE3─X2・MD5 は PE1─CE1・TCP-AO は PE2─X1 の 12/21。
# usage: source poc/xr/env.sh; poc/xr/try_xrt17.sh <gtsm|md5|ao|aofix|maxp|damp|agg|pic|undo>…   記録= poc/xr/expM6X-try-<段>.log(呼び出し側で)
# ★測り終えたら undo で外す(ラボは E2E の後に組み直して白紙で渡す)。
cd "$(dirname "$0")/../.."
PID=${PID:-XRT-17}
M=topologies/_generated/$PID/mgmt_map.yml
ip() { awk -v n="$1:" '$1==n{print $2}' "$M"; }
PE1=$(ip PE1) PE2=$(ip PE2) PE3=$(ip PE3) P1=$(ip P1) RR1=$(ip RR1) CE1=$(ip CE1) X1=$(ip X1) X2=$(ip X2) T=$(ip T)
S() { local h=$1; shift; .venv/bin/python poc/xr/xrsh.py "$h" "$@" 2>&1; }
H() { echo; echo "######## $(date +%T) $*"; }
XC() { local h=$1; shift; S "$h" configure "$@" commit 'show configuration failed' end; }
IC() { local h=$1; shift; S "$h" 'configure terminal' "$@" end; }

gtsm() {
  H "gtsm1: PE3 だけに ttl-security(X2 はまだ)→ clear → 両端の状態"
  XC "$PE3" 'router bgp 65000' 'neighbor 172.16.3.1' 'ttl-security'
  S "$PE3" 'clear bgp 172.16.3.1'; sleep 40
  S "$PE3" 'show bgp summary' 'show bgp neighbor 172.16.3.1'; S "$X2" 'show ip bgp summary' 'show ip bgp neighbors 172.16.3.254'
  H "gtsm2: X2 にも ttl-security hops 1 → 確立"
  IC "$X2" 'router bgp 65100' 'neighbor 172.16.3.254 ttl-security hops 1'
  S "$X2" 'clear ip bgp 172.16.3.254'; sleep 40
  S "$PE3" 'show bgp summary' 'show bgp neighbor 172.16.3.1'; S "$X2" 'show ip bgp summary' 'show ip bgp neighbors 172.16.3.254'
  H "gtsm3: XR で ebgp-multihop を足す(同居)/IOS で ebgp-multihop を足す(拒否)"
  XC "$PE3" 'router bgp 65000' 'neighbor 172.16.3.1' 'ebgp-multihop 2'
  S "$PE3" 'show running-config router bgp 65000 neighbor 172.16.3.1'
  IC "$X2" 'router bgp 65100' 'neighbor 172.16.3.254 ebgp-multihop 2'
  XC "$PE3" 'router bgp 65000' 'neighbor 172.16.3.1' 'no ebgp-multihop'
}
md5() {
  H "md5: PE1─CE1 に password(MD5)。PE1 だけ → 両方"
  XC "$PE1" 'router bgp 65000' 'neighbor 172.16.1.1' 'password clear CUST-65001'
  S "$PE1" 'clear bgp 172.16.1.1'; sleep 35
  S "$PE1" 'show bgp summary' 'show bgp neighbor 172.16.1.1'; S "$CE1" 'show ip bgp summary' 'show logging | include BADAUTH|TCP-6'
  IC "$CE1" 'router bgp 65001' 'neighbor 172.16.1.254 password CUST-65001'
  S "$CE1" 'clear ip bgp 172.16.1.254'; sleep 40
  S "$PE1" 'show bgp summary' 'show bgp neighbor 172.16.1.1' 'show running-config router bgp 65000 neighbor 172.16.1.1'
  S "$CE1" 'show ip bgp summary' 'show ip bgp neighbors 172.16.1.254' 'show running-config | include neighbor 172.16.1.254'
  H "md5b: password と keychain の同居を試す(拒否される見込み)"
  XC "$PE1" 'key chain CUST-KC' 'key 1' 'key-string clear CUST-65001' 'cryptographic-algorithm MD5' \
      'accept-lifetime 00:00:00 january 01 2026 infinite' 'send-lifetime 00:00:00 january 01 2026 infinite' 'exit' 'exit' \
      'router bgp 65000' 'neighbor 172.16.1.1' 'keychain CUST-KC'
}
ao() {
  H "ao: PE2─X1 に TCP-AO(UPLINK-AO・key 3・SendID 12/ReceiveID 21・X1 は 21/12・AES-128-CMAC-96)"
  XC "$PE2" 'key chain UPLINK-AO' 'key 3' 'key-string clear 0F1E2D3C4B5A69788796A5B4C3D2E1F0' 'cryptographic-algorithm AES-128-CMAC-96' \
      'accept-lifetime 00:00:00 january 01 2026 infinite' 'send-lifetime 00:00:00 january 01 2026 infinite' 'exit' 'exit' \
      'tcp ao' 'keychain UPLINK-AO' 'key 3 SendID 12 ReceiveID 21' 'exit' 'exit' \
      'router bgp 65000' 'neighbor 172.16.2.1' 'ao UPLINK-AO include-tcp-options enable'
  H "ao1: X1 の ID を交差させずに入れる(send-id 12・recv-id 21= PE2 と同じ)→ 失敗の見え方"
  IC "$X1" 'key chain UPLINK-AO tcp' 'key 3' 'send-id 12' 'recv-id 21' 'key-string 0F1E2D3C4B5A69788796A5B4C3D2E1F0' 'cryptographic-algorithm aes-128-cmac' 'exit' 'exit' \
      'router bgp 65100' 'neighbor 172.16.2.254 ao UPLINK-AO include-tcp-options'
  S "$X1" 'clear ip bgp 172.16.2.254'; sleep 45
  S "$PE2" 'show bgp summary' 'show tcp authentication keychain UPLINK-AO' 'show bgp neighbor 172.16.2.1'; S "$X1" 'show ip bgp summary' 'show logging | include AO|TCP-' 'show tcp ao key-chain UPLINK-AO'
  H "ao2: X1 の ID を交差させる(send-id 21・recv-id 12)→ 確立"
  IC "$X1" 'key chain UPLINK-AO tcp' 'key 3' 'send-id 21' 'recv-id 12'
  S "$X1" 'clear ip bgp 172.16.2.254'; sleep 45
  S "$PE2" 'show bgp summary' 'show tcp authentication keychain UPLINK-AO' 'show bgp neighbor 172.16.2.1' 'show running-config key chain UPLINK-AO' 'show running-config tcp ao'
  S "$X1" 'show ip bgp summary' 'show ip bgp neighbors 172.16.2.254' 'show tcp ao key-chain UPLINK-AO' 'show running-config | section key chain'
}
maxp() {
  H "maxp0: 読み物の値= PE1 ← CE1 に maximum-prefix 3 80(CE1 は 2 本)。表示"
  XC "$PE1" 'router bgp 65000' 'neighbor 172.16.1.1' 'address-family ipv4 unicast' 'maximum-prefix 3 80'
  sleep 5; S "$PE1" 'show bgp neighbor 172.16.1.1' 'show bgp summary'
  H "maxp1: CE1 に 2 本足す(4 本 > 3)→ 切れる・ログ"
  IC "$CE1" 'interface Loopback21' 'ip address 192.168.21.1 255.255.255.0' 'interface Loopback22' 'ip address 192.168.22.1 255.255.255.0' \
     'router bgp 65001' 'address-family ipv4' 'network 192.168.21.0' 'network 192.168.22.0'
  sleep 20; S "$PE1" 'show bgp summary' 'show logging | include MAXPFX|ADJCHANGE'; S "$CE1" 'show logging | include NOTIFICATION|ADJCHANGE'
  H "maxp2: warning-only → clear"
  XC "$PE1" 'router bgp 65000' 'neighbor 172.16.1.1' 'address-family ipv4 unicast' 'maximum-prefix 3 80 warning-only'
  S "$PE1" 'clear bgp 172.16.1.1'; sleep 35; S "$PE1" 'show bgp summary' 'show bgp neighbor 172.16.1.1 routes' 'show logging last 6'
  H "maxp3: discard-extra-paths → clear"
  XC "$PE1" 'router bgp 65000' 'neighbor 172.16.1.1' 'address-family ipv4 unicast' 'maximum-prefix 3 80 discard-extra-paths'
  S "$PE1" 'clear bgp 172.16.1.1'; sleep 35; S "$PE1" 'show bgp summary' 'show bgp neighbor 172.16.1.1 routes' 'show bgp neighbor 172.16.1.1'
  H "maxp4: 片付け(上限を外し CE1 の 2 本も消す)"
  XC "$PE1" 'router bgp 65000' 'neighbor 172.16.1.1' 'address-family ipv4 unicast' 'no maximum-prefix'
  IC "$CE1" 'router bgp 65001' 'address-family ipv4' 'no network 192.168.21.0' 'no network 192.168.22.0' 'exit' 'exit' 'no interface Loopback21' 'no interface Loopback22'
  S "$PE1" 'clear bgp 172.16.1.1'; sleep 35; S "$PE1" 'show bgp summary' | grep -E '^172'
}
damp() {
  H "damp: 読み物の値= PE2 に bgp dampening(既定値)。X1 の 198.51.100.0/24 を 3 回フラップ(bgpops_probe の --flap)"
  XC "$PE2" 'router bgp 65000' 'address-family ipv4 unicast' 'bgp dampening'
  S "$PE2" 'show bgp 198.51.100.0/24'
  LAB_USER=$NODE_USER LAB_PASS=$NODE_PASS .venv/bin/python topologies/bgpops_probe.py "$PID" run --flap 'X1:172.16.2.254:198.51.100.0/24:3:5' --wait 5 \
     --after 'PE2:show bgp flap-statistics' --after 'PE2:show bgp dampened-paths' --after 'PE2:show bgp 198.51.100.0/24' --after 'PE2:show bgp' --after 'RR1:show bgp 198.51.100.0/24'
  S "$PE2" 'clear bgp ipv4 unicast dampening'; sleep 8; S "$PE2" 'show bgp dampened-paths' 'show bgp 198.51.100.0/24'
  XC "$PE2" 'router bgp 65000' 'address-family ipv4 unicast' 'no bgp dampening'
}
agg() {
  H "agg1: 読み物の値= PE2 で aggregate-address 192.168.0.0/16 summary-only"
  XC "$PE2" 'router bgp 65000' 'address-family ipv4 unicast' 'aggregate-address 192.168.0.0/16 summary-only'
  sleep 15; S "$PE2" 'show bgp' 'show bgp 192.168.0.0/16' 'show bgp 192.168.1.0/24'; S "$X1" 'show ip bgp neighbors 172.16.2.254 routes' 'show ip bgp'; S "$RR1" 'show bgp'
  H "agg2: route-policy の suppress-route で 192.168.2.0/24 だけ抑制"
  XC "$PE2" 'route-policy AGG-SUPPRESS' '  if destination in (192.168.2.0/24) then' '    suppress-route' '  endif' 'end-policy' \
      'router bgp 65000' 'address-family ipv4 unicast' 'no aggregate-address 192.168.0.0/16 summary-only' 'aggregate-address 192.168.0.0/16 route-policy AGG-SUPPRESS'
  sleep 15; S "$PE2" 'show bgp' 'show running-config router bgp 65000 address-family ipv4 unicast'; S "$X1" 'show ip bgp neighbors 172.16.2.254 routes'
  H "agg3: 片付け"
  XC "$PE2" 'router bgp 65000' 'address-family ipv4 unicast' 'no aggregate-address 192.168.0.0/16' 'exit' 'exit' 'no route-policy AGG-SUPPRESS'
}

aofix() {
  H "aofix0: PE2─X1 に TCP-AO を入れ直す(ao の段は X1 の鍵が使用中で ID を直せず不成立= その記録は expM6X-try-ao.log)"
  XC "$PE2" 'key chain UPLINK-AO' 'key 3' 'key-string clear 0F1E2D3C4B5A69788796A5B4C3D2E1F0' 'cryptographic-algorithm AES-128-CMAC-96' \
      'accept-lifetime 00:00:00 january 01 2026 infinite' 'send-lifetime 00:00:00 january 01 2026 infinite' 'exit' 'exit' \
      'tcp ao' 'keychain UPLINK-AO' 'key 3 SendID 12 ReceiveID 21' 'exit' 'exit' \
      'router bgp 65000' 'neighbor 172.16.2.1' 'ao UPLINK-AO include-tcp-options enable'
  IC "$X1" 'key chain UPLINK-AO tcp' 'key 3' 'send-id 12' 'recv-id 21' 'key-string 0F1E2D3C4B5A69788796A5B4C3D2E1F0' 'cryptographic-algorithm aes-128-cmac' 'exit' 'exit' \
      'router bgp 65100' 'neighbor 172.16.2.254 ao UPLINK-AO include-tcp-options'
  H "aofix1: ID を交差させていない(X1 も send-id 12・recv-id 21)。PE2 から張り直す → 両端の状態"
  S "$PE2" 'clear bgp 172.16.2.1'; sleep 45
  S "$PE2" 'show bgp summary' 'show bgp neighbor 172.16.2.1' 'show tcp authentication keychain UPLINK-AO' 'show logging last 15'
  S "$X1" 'show ip bgp summary' 'show ip bgp neighbors 172.16.2.254' 'show tcp ao key-chain UPLINK-AO' 'show logging | include AO|TCP'
  H "aofix2: X1 の鍵を直すには、先にネイバーの ao を外す(使用中の鍵は直せない)→ send-id 21・recv-id 12 → ao を戻す → PE2 から張り直す"
  IC "$X1" 'router bgp 65100' 'no neighbor 172.16.2.254 ao UPLINK-AO include-tcp-options' 'exit' 'key chain UPLINK-AO tcp' 'key 3' 'send-id 21' 'recv-id 12' 'exit' 'exit' \
      'router bgp 65100' 'neighbor 172.16.2.254 ao UPLINK-AO include-tcp-options'
  S "$PE2" 'clear bgp 172.16.2.1'; sleep 45
  S "$PE2" 'show bgp summary' 'show bgp neighbor 172.16.2.1' 'show tcp authentication keychain UPLINK-AO' 'show running-config key chain UPLINK-AO' 'show running-config tcp ao' 'show running-config router bgp 65000 neighbor 172.16.2.1'
  S "$X1" 'show ip bgp summary' 'show ip bgp neighbors 172.16.2.254' 'show tcp ao key-chain UPLINK-AO' 'show running-config | section key chain' 'show running-config | include neighbor 172.16.2.254'
}
pic() {
  H "pic: XRT-17 の盤面(入口 PE1= XRv9000)で模範解の M6-5・M6-6 を当て、PE2 を切った時の途切れを測る(読み物の数値の裏づけ)"
  poc/xr/solve_xrt17.sh s5; sleep 35; poc/xr/solve_xrt17.sh s6; sleep 15
  S "$PE1" 'show route 203.0.113.0/24 detail' 'show cef 203.0.113.0/24 detail'
  for i in 1 2; do LAB_USER=$NODE_USER LAB_PASS=$NODE_PASS .venv/bin/python topologies/bgpops_probe.py "$PID" run --failover 'CE1:192.168.1.1:203.0.113.1:P1:GigabitEthernet0/0/0/1' --recover 60; done
  H "pic-b: PE3 の install を外す(入口だけの PIC)→ 1 回"
  XC "$PE3" 'route-policy ADDPATH-OUT' '  set path-selection backup 1 advertise' 'end-policy'; sleep 10
  LAB_USER=$NODE_USER LAB_PASS=$NODE_PASS .venv/bin/python topologies/bgpops_probe.py "$PID" run --failover 'CE1:192.168.1.1:203.0.113.1:P1:GigabitEthernet0/0/0/1' --recover 60
}

undo() {
  H "undo: 読み物の値で入れたものを外す"
  XC "$PE3" 'router bgp 65000' 'neighbor 172.16.3.1' 'no ttl-security' 'no ebgp-multihop'
  IC "$X2" 'router bgp 65100' 'no neighbor 172.16.3.254 ttl-security hops 1'
  XC "$PE1" 'router bgp 65000' 'neighbor 172.16.1.1' 'no password' 'no keychain' 'exit' 'exit' 'no key chain CUST-KC'
  IC "$CE1" 'router bgp 65001' 'no neighbor 172.16.1.254 password'
  XC "$PE2" 'router bgp 65000' 'neighbor 172.16.2.1' 'no ao' 'exit' 'exit' 'no tcp ao' 'no key chain UPLINK-AO'
  IC "$X1" 'router bgp 65100' 'no neighbor 172.16.2.254 ao UPLINK-AO include-tcp-options' 'exit' 'no key chain UPLINK-AO'
  S "$PE1" 'clear bgp 172.16.1.1'; S "$PE2" 'clear bgp 172.16.2.1'; S "$PE3" 'clear bgp 172.16.3.1'; sleep 45
  for h in $PE1 $PE2 $PE3; do S "$h" 'show bgp summary' | grep -E '^172'; done
}
for p in "$@"; do "$p"; done
