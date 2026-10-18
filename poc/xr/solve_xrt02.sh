#!/bin/bash
# XRT-02 の模範解(learn.yml の solution と同じもの)を管理 IF の SSH で XR01 に入れる。PoC/E2E 用。
# usage: source poc/xr/env.sh; poc/xr/solve_xrt02.sh <XR01 の管理 IP>
cd "$(dirname "$0")/../.."
H=${1:?XR01 mgmt ip}
X() { .venv/bin/python poc/xr/xrsh.py "$H" "$@" 2>&1 | grep -iE "%|fail" || true; sleep 5; }  # MPP のコミット直後は約 1 秒 SSH が拒否される(実測)
X configure 'taskgroup NOC-TG' 'task read rib' 'task read ospf' 'task read interface' 'task execute interface' \
  'task read basic-services' 'task write basic-services' 'task execute basic-services' \
  'usergroup NOC' 'taskgroup NOC-TG' 'username noc1' 'group NOC' 'secret Noc1-Pass' 'commit' 'end'
X configure control-plane management-plane out-of-band 'vrf MGMT' 'interface MgmtEth0/RP0/CPU0/0' 'allow SSH' exit exit \
  inband 'interface GigabitEthernet0/0/0/0' 'allow Telnet peer' 'address ipv4 2.2.2.2' root commit end
X configure 'tacacs-server host 10.0.50.10 port 49' 'key XRT02-Tac-Key' exit 'tacacs source-interface Loopback0 vrf default' \
  'aaa group server tacacs+ TAC' 'server 10.0.50.10' exit 'aaa authentication login default group TAC local' \
  'aaa authentication login CONSOLE local' 'line console' 'login authentication CONSOLE' commit end
X configure 'lpts pifib hardware police' 'flow icmp local rate 50' commit end
X configure 'ipv4 access-list GUEST-IN' '10 deny ipv4 198.51.100.0 0.0.0.255 any' '20 permit ipv4 any any' exit \
  'interface GigabitEthernet0/0/0/0' 'ipv4 access-group GUEST-IN ingress' commit end

# M3
X configure 'router ospf 1' 'area 0' 'interface GigabitEthernet0/0/0/2' 'passive disable' root \
  'router ospf 1' 'area 1' 'stub no-summary' 'range 172.16.0.0/22' root \
  'router ospfv3 1' 'router-id 1.1.1.1' 'area 0' 'interface Loopback0' exit 'interface GigabitEthernet0/0/0/0' 'network point-to-point' commit end
echo "solve done"
