#!/bin/bash
# BL-257 PoC の追加の確かめ(2026-11-21)= bgpops_poc.sh の段で結論が出なかったもの。盤面と道具は bgpops_poc.sh と同じ。
cd "$(dirname "$0")/../.."
. <(sed -n '/^PID=/,/^look()/p' poc/xr/bgpops_poc.sh | grep -v '^look()')
st2() { S "$PE2" 'show bgp neighbor 172.16.2.1' | grep -E 'BGP state|Last reset|Last read '; S "$X1" 'show ip bgp neighbors 172.16.2.254' | grep -E 'BGP state|Last reset|Option Flags'; }
kc() {
  H "kc1: XR の keychain(暗号 $1)と IOS の password(同じ文字列)。両側から張り直す"
  XC "$PE2" 'key chain MD5-KC' 'key 1' 'key-string clear LAB-MD5' "cryptographic-algorithm $1" \
      'accept-lifetime 00:00:00 january 01 2026 infinite' 'send-lifetime 00:00:00 january 01 2026 infinite' 'exit' 'exit' \
      'router bgp 65000' 'neighbor 172.16.2.1' 'keychain MD5-KC' | grep -E '%|!!'
  IC "$X1" 'router bgp 65100' 'neighbor 172.16.2.254 password LAB-MD5' > /dev/null
  S "$PE2" 'clear bgp 172.16.2.1' > /dev/null; S "$X1" 'clear ip bgp 172.16.2.254' > /dev/null; sleep 45; st2
  S "$X1" 'show logging | include BADAUTH|TCP-6' | tail -3
  H "kc2: 片付け"
  XC "$PE2" 'router bgp 65000' 'neighbor 172.16.2.1' 'no keychain' 'exit' 'exit' 'no key chain MD5-KC' | grep -E '%|!!'
  IC "$X1" 'router bgp 65100' 'no neighbor 172.16.2.254 password' > /dev/null
  S "$PE2" 'clear bgp 172.16.2.1' > /dev/null; sleep 40; st2
}
ribx() {
  H "ribx: XR(PE2)で RIB に入らない BGP の経路(static 10.199.9.0/24 Null0 が勝つ)。X1 の Loopback9 と network は ribf で入れたまま"
  S "$X1" 'show ip bgp 10.199.9.0' | grep -E 'Paths|best'
  XC "$PE2" 'router static' 'address-family ipv4 unicast' '10.199.9.0/24 Null0' | grep -E '%|!!'; sleep 15
  S "$PE2" 'show route 10.199.9.0/24' 'show bgp 10.199.9.0/24' 'show bgp' 'show bgp neighbor 10.255.0.21 advertised-routes'
  S "$RR1" 'show bgp 10.199.9.0/24'
  XC "$PE2" 'router static' 'address-family ipv4 unicast' 'no 10.199.9.0/24 Null0' | grep -E '%|!!'
}
supi() {
  H "supi: IOS(X2)の bgp suppress-inactive を、static で RIB-failure にした経路で。soft out → hard reset の順に効くか見る"
  IC "$X2" 'ip route 10.199.9.0 255.255.255.0 Null0' 'router bgp 65100' 'bgp suppress-inactive' > /dev/null; sleep 10
  S "$X2" 'show running-config | section router bgp' 'show ip bgp rib-failure' 'show ip bgp neighbors 172.16.3.254 advertised-routes'
  S "$X2" 'clear ip bgp 172.16.3.254'; sleep 45
  echo "== hard reset の後"; S "$X2" 'show ip bgp neighbors 172.16.3.254 advertised-routes'; S "$PE3" 'show bgp neighbor 172.16.3.1 routes'
  IC "$X2" 'router bgp 65100' 'no bgp suppress-inactive' 'exit' 'no ip route 10.199.9.0 255.255.255.0 Null0' > /dev/null
  S "$X2" 'clear ip bgp 172.16.3.254 soft out' > /dev/null
}
dmp() {
  H "dmp: PE2 に bgp dampening(既定値)。X1 の network 10.199.9.0 を消す/入れるで 3 回揺らす(間 15 秒)"
  XC "$PE2" 'router bgp 65000' 'address-family ipv4 unicast' 'bgp dampening' | grep -E '%|!!'; sleep 5
  for i in 1 2 3; do
    IC "$X1" 'router bgp 65100' 'address-family ipv4' 'no network 10.199.9.0 mask 255.255.255.0' > /dev/null; sleep 15
    IC "$X1" 'router bgp 65100' 'address-family ipv4' 'network 10.199.9.0 mask 255.255.255.0' > /dev/null; sleep 15
    echo "== 揺らし $i 回目の後"; S "$PE2" 'show bgp flap-statistics' 'show bgp 10.199.9.0/24' | grep -vE '^\s*$|UTC$|Versions|Process|Speaker|RP/0'
  done
  S "$PE2" 'show bgp dampened-paths' 'show bgp' ; S "$RR1" 'show bgp 10.199.9.0/24' | grep -E 'Paths|from|valid'
  H "dmp2: clear bgp ipv4 unicast dampening → 片付け"
  S "$PE2" 'clear bgp ipv4 unicast dampening'; sleep 10; S "$PE2" 'show bgp dampened-paths' 'show bgp 10.199.9.0/24' | grep -vE '^\s*$|UTC$'
  XC "$PE2" 'router bgp 65000' 'address-family ipv4 unicast' 'no bgp dampening' | grep -E '%|!!'
}
for p in "$@"; do case $p in kcmd5) kc MD5;; kchmac) kc HMAC-MD5;; *) "$p";; esac; done
