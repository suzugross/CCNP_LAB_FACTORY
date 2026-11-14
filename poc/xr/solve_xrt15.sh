#!/bin/bash
# XRT-15 の模範解(learn.yml の solution と同じもの)を管理 IF の SSH で XR01・PE2・SRV01 に入れる。PoC/E2E 用。
# usage: source poc/xr/env.sh; poc/xr/solve_xrt15.sh [m13t1 … m13t6](既定= 全部)。管理 IP は _generated の mgmt_map から引く
#   誤答の確かめ用: m13t1-cli(Loopback100 を CLI で入れる= コミット履歴が CLI)/
#                   m13t2-priv1(nms-api を権限 1 で作る= 403)・m13t2-http(平文の ip http server も開ける)/
#                   m13t3-tls(tls-mutual なし= 証明書なしでも通る)・m13t3-nocert(tls-mutual だけで CA を差し替えない)/
#                   m13t4-path(センサー パスだけ直す)・m13t4-noca(パスと名前を直し CA を置かない)/
#                   m13t5-v9(NetFlow v9 で 2055 へ)/m13t6-acl(ACL だけ直す)・m13t6-notify(グループに notify のビューだけ足す)
cd "$(dirname "$0")/../.."
M=topologies/_generated/${PID:-XRT-15}/mgmt_map.yml
ipof() { awk -v n="$1:" '$1==n{print $2}' "$M"; }
X1=$(ipof XR01) P2=$(ipof PE2) SV=$(ipof SRV01)
SP=$(dirname "$0")
steps=${*:-m13t1 m13t2 m13t3 m13t4 m13t5 m13t6}
run() { local h=$1; shift; .venv/bin/python poc/xr/xrsh.py "$h" "$@" 2>&1 | grep -iE "^%|fail|error|invalid|!!%" | grep -v "No such configuration" || true; }
XC() { local h=$1; shift; run "$h" configure "$@" commit 'show configuration failed' end; }
IC() { local h=$1; shift; run "$h" 'configure terminal' "$@" end; }
L() { .venv/bin/python poc/xr/lxsh.py "$SV" "$@" 2>&1 | sed "s/$NODE_PASS/***/g"; }
http_up() { L 'ss -ltn | grep -q ":8080 " || (cd ~/pki && setsid nohup python3 -m http.server 8080 > /tmp/http.log 2>&1 < /dev/null &); sleep 1; ss -ltn | grep -c 8080'; }
ca_to() { .venv/bin/python poc/xr/xrsh.py "$X1" 'copy http://10.0.50.10:8080/ca.pem harddisk:/nms-ca.pem' '' "run cp /harddisk:/nms-ca.pem $1" 2>&1 | grep -E "Copy operation|rror" ; }

m13t1() {
  XC "$X1" 'ssh server netconf vrf default' 'netconf-yang agent' 'ssh'
  sleep 5
  if [ "$1" = cli ]; then XC "$X1" 'interface Loopback100' 'description NMS-MANAGED' 'ipv4 address 10.255.100.1 255.255.255.255'; return; fi
  L --put "$SP/nc_fill_xrt15.py:/tmp/nc_fill.py" "python3 /tmp/nc_fill.py ~/m13/nc_edit.py '$NODE_USER' '$NODE_PASS' > /tmp/nc_solved.py && python3 /tmp/nc_solved.py edit | grep -c '<ok/>'"
}
m13t2() {
  local pv=15; [ "$1" = priv1 ] && pv=1
  IC "$P2" "username nms-api privilege $pv secret Api-Pass-15" 'ip http secure-server' 'restconf'
  [ "$1" = http ] && IC "$P2" 'ip http server'
  sleep 75
  L 'python3 ~/m13/rc_customer_lo.py'
}
m13t3() {
  case $1 in
    tls) XC "$X1" 'grpc' 'port 57400' 'address-family ipv4'; return ;;
    nocert) XC "$X1" 'grpc' 'port 57400' 'address-family ipv4' 'tls-mutual'; return ;;
  esac
  XC "$X1" 'grpc' 'port 57400' 'address-family ipv4' 'tls-mutual'
  http_up; ca_to /misc/config/grpc/ca.cert
  run "$X1" 'process restart emsd'; sleep 15
}
m13t4() {
  [ "$1" != path ] && [ "$1" != noca ] && { http_up; ca_to /misc/config/grpc/dialout/dialout.pem; }
  local dg=('destination-group NMS' 'address-family ipv4 10.0.50.10 port 57500' 'protocol grpc tls-hostname collector.nms.lab' 'exit' 'exit')
  [ "$1" = path ] && dg=()
  XC "$X1" 'telemetry model-driven' "${dg[@]}" 'sensor-group IF-COUNTERS' \
    'no sensor-path Cisco-IOS-XR-infra-statsd-oper:infra-statistics/interfaces/interface/latest/generic-counters' \
    'sensor-path openconfig-interfaces:interfaces/interface/state/counters'
}
m13t5() {
  local ver=('transport udp 4739' 'export-protocol ipfix')
  [ "$1" = v9 ] && ver=('transport udp 2055' 'export-protocol netflow-v9')
  IC "$P2" 'flow record FR-CUST' 'match ipv4 source address' 'match ipv4 destination address' 'match ipv4 protocol' \
    'match transport source-port' 'match transport destination-port' 'match interface input' 'collect counter bytes long' \
    'collect counter packets long' 'collect timestamp absolute first' 'collect timestamp absolute last' 'exit' \
    'flow exporter FE-NMS' 'destination 10.0.50.10' 'source Loopback0' "${ver[@]}" 'exit' \
    'flow monitor FM-CUST' 'exporter FE-NMS' 'record FR-CUST' 'cache timeout active 60' 'exit' \
    'interface GigabitEthernet2' 'ip flow monitor FM-CUST input'
}
m13t6() {
  local acl=('ipv4 access-list NMS-ONLY' 'no 10' '10 permit ipv4 host 10.0.50.10 any' 'exit')
  local trp=('snmp-server group NMS-V3 v3 priv read NMS-VIEW notify NMS-VIEW')
  [ "$1" = acl ] && trp=()
  [ "$1" = notify ] && acl=()
  XC "$X1" "${acl[@]}" "${trp[@]}"
}

for s in $steps; do
  base=${s%%-*}; var=${s#*-}; [ "$var" = "$s" ] && var=
  echo "== $s"; $base "$var"
done
