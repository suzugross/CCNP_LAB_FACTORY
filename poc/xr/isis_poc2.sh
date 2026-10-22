#!/bin/bash
# BL-246 M4 IS-IS の PoC の追加段(isis_poc.sh の続き・同じ盤面と引数)。usage: isis_poc2.sh <XR> <R1> <R2> h
cd "$(dirname "$0")/../.."
XR=$1 R1=$2 R2=$3; shift 3
X() { .venv/bin/python poc/xr/xrsh.py "$XR" "$@" 2>&1; }
R() { local h=$1; shift; .venv/bin/python poc/xr/xrsh.py "$h" "$@" 2>&1; }
H() { echo; echo "######## $*"; }

h() {
  H "h-1: XR だけ broadcast(既定)・IOL は p2p のときの症状"
  X configure 'router isis CORE' 'interface GigabitEthernet0/0/0/0' 'no point-to-point' commit end
  sleep 40
  X 'show isis adjacency' 'show isis interface GigabitEthernet0/0/0/0 | include "Media|Rejected|IIH|Adjacency Count|DIS"' 'show isis neighbors'
  R "$R1" 'show clns neighbors' 'show isis neighbors' 'show logging | include ISIS|CLNS|isis'
  X configure 'router isis CORE' 'interface GigabitEthernet0/0/0/0' 'point-to-point' commit end
  H "h-2: NET を 1 回のコミットで付け替える(システム ID を慣習どおりに)"
  X configure 'router isis CORE' 'no net 49.0001.0000.0000.0001.00' 'net 49.0001.0010.0100.1001.00' commit 'show configuration failed' end
  sleep 40
  X 'show isis adjacency' 'show isis hostname' 'show isis database' 'show running-config router isis CORE | include net'
  R "$R1" 'show clns neighbors' 'show isis database'
  H "h-3: RPL の prefix-set で eq(長さちょうど)が書けるか"
  X configure 'prefix-set LOOPS-EQ' '22.22.22.0/24 eq 32,' '2001:db8::/64 eq 128' end-set commit 'show configuration failed' abort
  X configure 'prefix-set LOOPS-GE' '22.22.22.0/24 ge 32,' '2001:db8::/64 ge 128' end-set commit 'show configuration failed' end
  X 'show rpl prefix-set LOOPS-GE'
  H "h-4: metric の範囲(wide のとき)"
  X configure 'router isis CORE' 'interface GigabitEthernet0/0/0/1' 'address-family ipv4 unicast' 'metric ?' abort
  H "h-5: 隣接変化のログ(log adjacency changes 後)"
  X configure 'router isis CORE' 'interface GigabitEthernet0/0/0/0' 'shutdown' commit end
  sleep 5
  X configure 'router isis CORE' 'interface GigabitEthernet0/0/0/0' 'no shutdown' commit end
  sleep 20
  X 'show logging | include ADJCHANGE | utility tail count 6'
  H "h-6: narrow のレベル(L1)に 1000 を書くと何が広告されるか"
  X configure 'router isis CORE' 'interface GigabitEthernet0/0/0/0' 'address-family ipv4 unicast' 'metric 1000 level 1' commit 'show configuration failed' end
  sleep 15
  X 'show isis database detail level 1 | include "Metric|LSPID|XR"' 'show isis interface GigabitEthernet0/0/0/0 | include Metric' 'show logging | utility tail count 8'
  R "$R1" 'show isis database detail' 'show ip route isis'
  X configure 'router isis CORE' 'interface GigabitEthernet0/0/0/0' 'address-family ipv4 unicast' 'no metric 1000 level 1' commit end
}


for p in "$@"; do "$p"; done
