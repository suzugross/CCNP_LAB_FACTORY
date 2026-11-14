#!/bin/bash
# BL-246 M13 PoC= 自動化とアシュアランス(SPCOR 5.7〜5.10)。盤面= problems/_POC-XRAUTO
#   XR01= XRv9000 26.1.1・XR02= XRd 26.1.1・RT01= IOL(試験のトラフィックの発信元)・SRV01= Ubuntu の収集役
# 記録= design §30。usage: source poc/xr/env.sh; poc/xr/auto_poc.sh <段…>   出力は標準出力(呼び出し側で poc/xr/expAUTO-<段>.log へ)
cd "$(dirname "$0")/../.."
PID=${PID:-_POC-XRAUTO}
M=topologies/_generated/$PID/mgmt_map.yml
ip() { awk -v n="$1:" '$1==n{print $2}' "$M"; }
X1=$(ip XR01) X2=$(ip XR02) R1=$(ip RT01) SV=$(ip SRV01)
S() { local h=$1; shift; .venv/bin/python poc/xr/xrsh.py "$h" "$@" 2>&1; }
L() { .venv/bin/python poc/xr/lxsh.py "$SV" "$@" 2>&1; }
H() { echo; echo "######## $(date +%T) $*"; }
XC() { local h=$1; shift; S "$h" configure "$@" commit 'show configuration failed' end; }   # XR: configure → 行 → commit
IC() { local h=$1; shift; S "$h" 'configure terminal' "$@" end; }                           # IOS: configure terminal → 行 → end
BOTH() { for h in "$X1" "$X2"; do echo "== $([ "$h" = "$X1" ] && echo XR01 || echo XR02)"; "$@" "$h"; done; }

a() {
  H "a: 版・土台(IS-IS)・到達性・SRV01 の道具"
  for h in "$X1" "$X2"; do S "$h" 'show version | include Version' 'show isis adjacency' 'show route ipv4 | include "^[ILC]"'; done
  S "$R1" 'show isis neighbors' 'ping 10.0.50.10 source Loopback100 repeat 5' 'ping 10.0.60.10 source Loopback100 repeat 5'
  L 'cat /var/tmp/ccnp-cloudinit-done' 'tail -5 /var/log/ccnp-init.log' 'gnmic version | head -3' 'telegraf --version' 'nfcapd -V' \
    'ping -c 2 10.255.0.1' 'ping -c 2 10.255.0.2' 'ip -br addr'
}

# ---- 5.9 NETCONF
nc_cfg() { XC "$1" 'ssh server v2' 'ssh server netconf vrf default' 'netconf-yang agent' 'ssh'; S "$1" 'show running-config netconf-yang agent' 'show running-config ssh'; }
nc() {
  H "nc: NETCONF の最小の設定 → SRV01 の ncclient で hello・get-config・edit(candidate → commit)"
  BOTH nc_cfg
  for t in 10.0.50.1 10.0.60.1; do
    echo "==== NETCONF to $t"
    L --put poc/xr/nc_probe.py:/tmp/nc_probe.py "python3 /tmp/nc_probe.py $t '$NODE_USER' '$NODE_PASS' caps getcfg edit oper"
  done
  for h in "$X1" "$X2"; do S "$h" 'show netconf-yang clients' 'show netconf-yang statistics' 'show configuration commit list 3' \
    'show configuration commit changes last 1' 'show running-config interface Loopback0'; done
}
nc_confirmed() {
  H "nc_confirmed: confirmed-commit を出して確定しない → 60 秒で戻るか・その間の CLI の表示"
  L "python3 /tmp/nc_probe.py 10.0.50.1 '$NODE_USER' '$NODE_PASS' confirmed"
  S "$X1" 'show configuration commit list 3' 'show running-config interface Loopback0' 'show configuration sessions'
  sleep 75
  S "$X1" 'show configuration commit list 4' 'show running-config interface Loopback0'
}

# ---- 5.7 gRPC/gNMI のダイヤルイン
GN() { local t=$1; shift; L "timeout 40 gnmic -a $t -u '$NODE_USER' -p '$NODE_PASS' -e json_ietf $*"; }
gi_cfg() { XC "$1" 'grpc' 'port 57400' 'no-tls' 'address-family ipv4'; S "$1" 'show running-config grpc' 'show grpc'; }
gi() {
  H "gi: gRPC を TLS なしで有効にし、SRV01 の gnmic で capabilities・get・subscribe(sample/once)"
  BOTH gi_cfg
  for t in 10.0.50.1:57400 10.0.60.1:57400; do
    echo "==== gNMI to $t"
    GN $t --insecure capabilities '| grep -E -A8 "version|encodings" | head -12'
    GN $t --insecure get --path '/interfaces/interface[name=Loopback0]/state' '| head -40'
    GN $t --insecure get --path 'Cisco-IOS-XR-shellutil-oper:system-time/uptime' '| head -20'
    GN $t --insecure subscribe --path '/interfaces/interface[name=Loopback0]/state/counters' --mode once '| head -30'
    L "timeout 25 gnmic -a $t -u '$NODE_USER' -p '$NODE_PASS' --insecure subscribe --path 'Cisco-IOS-XR-infra-statsd-oper:infra-statistics/interfaces/interface[interface-name=Loopback0]/latest/generic-counters' --stream-mode sample --sample-interval 10s --format event | grep -c timestamp"
  done
  for h in "$X1" "$X2"; do S "$h" 'show grpc statistics' 'show grpc trace ems last 20' 'show telemetry model-driven subscription'; done
}

# ---- 5.7 テレメトリのダイヤルアウト(受け手= telegraf の cisco_telemetry_mdt)
tg_start() {
  L "cat > /tmp/telegraf.conf <<'EOF'
[agent]
  interval = \"10s\"
  flush_interval = \"5s\"
  omit_hostname = true
[[inputs.cisco_telemetry_mdt]]
  transport = \"tcp\"
  service_address = \":57000\"
[[inputs.cisco_telemetry_mdt]]
  transport = \"grpc\"
  service_address = \":57500\"
[[outputs.file]]
  files = [\"/tmp/mdt.out\"]
  data_format = \"json\"
EOF" 'pkill -x telegraf; rm -f /tmp/mdt.out; setsid nohup telegraf --config /tmp/telegraf.conf > /tmp/telegraf.log 2>&1 < /dev/null & sleep 3; ss -ltnp | grep -E "57000|57500"'
}
go_cfg() {
  XC "$1" 'telemetry model-driven' \
    'destination-group DG-TCP' "address-family ipv4 $2 port 57000" 'encoding self-describing-gpb' 'protocol tcp' 'exit' 'exit' \
    'destination-group DG-GRPC' "address-family ipv4 $2 port 57500" 'encoding self-describing-gpb' 'protocol grpc no-tls' 'exit' 'exit' \
    'sensor-group SG-IF' 'sensor-path openconfig-interfaces:interfaces/interface/state/counters' 'sensor-path Cisco-IOS-XR-infra-statsd-oper:infra-statistics/interfaces/interface/latest/generic-counters' 'exit' \
    'subscription SUB-TCP' 'sensor-group-id SG-IF sample-interval 10000' 'destination-id DG-TCP' 'source-interface Loopback0' 'exit' \
    'subscription SUB-GRPC' 'sensor-group-id SG-IF sample-interval 10000' 'destination-id DG-GRPC' 'source-interface Loopback0'
}
go() {
  H "go: ダイヤルアウト(TCP と gRPC の TLS なし)→ telegraf で受ける"
  tg_start
  go_cfg "$X1" 10.0.50.10; go_cfg "$X2" 10.0.60.10
  sleep 40
  L 'wc -l /tmp/mdt.out' 'tail -5 /tmp/telegraf.log' "jq -r '[.tags.source, .tags.subscription, .name, .tags.name] | @tsv' /tmp/mdt.out | sort | uniq -c | head -30" 'head -c 900 /tmp/mdt.out'
  for h in "$X1" "$X2"; do S "$h" 'show telemetry model-driven subscription' 'show telemetry model-driven destination' 'show telemetry model-driven sensor-group'; done
}

# ---- 5.8 NetFlow/IPFIX(受け手= nfcapd)
nf_start() { L 'pkill nfcapd; sleep 2; rm -rf /tmp/nf; mkdir -p /tmp/nf; nfcapd -w /tmp/nf -p 2055 -t 60 -D; sleep 1; ss -lunp | grep 2055'; }
nf_cfg() {   # nf_cfg <host> <宛先> <版 v9|ipfix>
  XC "$1" 'flow exporter-map FEM' "version $3" 'options interface-table timeout 60' 'template data timeout 60' 'exit' 'transport udp 2055' 'source Loopback0' "destination $2" 'exit' \
    'flow monitor-map FMM' 'record ipv4' 'exporter FEM' 'cache timeout active 10' 'cache timeout inactive 5' 'exit' \
    'sampler-map SM' 'random 1 out-of 1' 'exit' \
    'interface GigabitEthernet0/0/0/0' 'flow ipv4 monitor FMM sampler SM ingress'
}
nf() {
  H "nf: NetFlow v9 を XR01・XR02 の RT01 側の入力に付け、RT01 から SRV01 へ流す → nfcapd で受ける"
  nf_start
  nf_cfg "$X1" 10.0.50.10 v9; nf_cfg "$X2" 10.0.60.10 v9
  S "$R1" 'ping 10.0.50.10 source Loopback100 repeat 200' 'ping 10.0.60.10 source Loopback100 repeat 200'
  sleep 20
  for h in "$X1" "$X2"; do S "$h" 'show flow monitor FMM cache location 0/0/CPU0' 'show flow exporter FEM location 0/0/CPU0' 'show flow platform producer statistics location 0/0/CPU0'; done
  sleep 60
  L 'ls -la /tmp/nf' 'nfdump -R /tmp/nf -o extended -c 20' 'nfdump -R /tmp/nf -s srcip/flows'
}

# ---- 5.10 SNMP
sn_cfg() {
  XC "$1" 'ipv4 access-list ACL-NMS' '10 permit ipv4 host 10.0.50.10 any' '20 permit ipv4 host 10.0.60.10 any' 'exit' \
    'snmp-server view VIEW-SYS 1.3.6.1.2.1.1 included' 'snmp-server view VIEW-ALL 1.3.6.1 included' \
    'snmp-server community PocRO RO IPv4 ACL-NMS' \
    'snmp-server group GRP-V3 v3 priv read VIEW-ALL' \
    'snmp-server user USR-V3 GRP-V3 v3 auth sha clear PocAuth123 priv aes 128 clear PocPriv123' \
    "snmp-server host $2 traps version 3 priv USR-V3" 'snmp-server traps snmp linkup' 'snmp-server traps snmp linkdown' 'snmp-server ifindex persist'
  S "$1" 'show running-config snmp-server' 'show snmp' 'show snmp user' 'show snmp group' 'show snmp engineid'
}
sn() {
  H "sn: SNMP v2c(ACL)と v3(authPriv)・トラップ"
  sn_cfg "$X1" 10.0.50.10; sn_cfg "$X2" 10.0.60.10
  for t in 10.0.50.1 10.0.60.1; do
    echo "==== SNMP to $t"
    L "snmpget -v2c -c PocRO $t 1.3.6.1.2.1.1.5.0 1.3.6.1.2.1.1.3.0" "snmpwalk -v2c -c PocRO $t 1.3.6.1.2.1.2.2.1.2 | head" \
      "snmpget -v3 -l authPriv -u USR-V3 -a SHA -A PocAuth123 -x AES -X PocPriv123 $t 1.3.6.1.2.1.1.5.0" \
      "snmpget -v3 -l authPriv -u USR-V3 -a SHA -A wrongpass1 -x AES -X PocPriv123 $t 1.3.6.1.2.1.1.5.0"
  done
}

"$@"
