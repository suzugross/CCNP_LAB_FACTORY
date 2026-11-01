#!/bin/bash
# XRT-12 の誤答の判別とやり直しの確認(E2E)。usage: source poc/xr/env.sh; poc/xr/wrong_xrt12.sh [段…](既定= 全部)
# 模範解= learn.yml の solution を逐語で(poc/xr/verbatim.py)。誤答は模範解から 1 か所だけ崩す。出力= 段ごとの合計と FAIL の行。
cd "$(dirname "$0")/../.."
M=topologies/_generated/XRT-12/mgmt_map.yml
ip() { awk -v n="$1:" '$1==n{print $2}' "$M"; }
E1=$(ip XE1) E2=$(ip XE2) E3=$(ip XE3)
S() { .venv/bin/python poc/xr/xrsh.py "$@" 2>&1 | grep -E "^%|Invalid" || true; }
R() { echo "#### reset"; scripts/lab.sh reset XRT-12 2>&1 | grep -E "configure replace|ERROR|after" ; sleep 30; }
C() { timeout 900 poc/xr/e2e_xrt12.sh "$@" 2>&1 | grep -E "合計|FAIL"; }
V() { .venv/bin/python poc/xr/verbatim.py XRT-12 "$E1" "$@"; }
w6() {
  R; echo "#### m11t6: rewrite だけ直す(期待= 35)"
  S "$E3" 'configure terminal' 'interface GigabitEthernet2' 'service instance 210 ethernet' 'rewrite ingress tag pop 1 symmetric' 'end'; sleep 20; C m11t6
  # ★8000V 17.15 の VFI の member には no-split-horizon が無い(Invalid input・2026-11-01 実測)→ 「XE2 で外す」誤答は成り立たない
  R; echo "#### m11t6: メッシュだけ直す(rewrite の付け忘れが残る・期待= 30)"
  S "$E1" 'configure terminal' 'l2vpn vfi context VPLS210' 'member 10.255.0.43 encapsulation mpls' 'end'
  S "$E3" 'configure terminal' 'l2vpn vfi context VPLS210' 'member 10.255.0.41 encapsulation mpls' 'end'
  sleep 30; C m11t6
}
w7() {
  R; V m11t6; echo "#### m11t7: XE3 を dot1q 200 に(期待= 到達が落ちる 55)"
  V m11t7; S "$E3" 'configure terminal' 'interface GigabitEthernet2' 'no service instance 200 ethernet' 'service instance 200 ethernet' 'encapsulation dot1q 200' 'rewrite ingress tag pop 1 symmetric' 'exit' 'exit' 'bridge-domain 200' 'member GigabitEthernet2 service-instance 200' 'end'
  sleep 40; C m11t7
  echo "#### m11t7: replication-type なし(期待= MAC と到達が落ちる 30)"
  V m11t7; for h in $E1 $E2 $E3; do S "$h" 'configure terminal' 'l2vpn evpn' 'no replication-type ingress' 'end'; done; sleep 40; C m11t7
  # ★全 PE から replication-type を外して戻すと 40 秒では E-LAN が戻らなかった(2026-11-01・未追跡)→ 次の段は reset から
  R; V m11t6 m11t7; sleep 60; echo "#### m11t7: PE どうしの直接のセッションも張る(期待= セッションの確認が落ちる 85)"
  S "$E1" 'configure terminal' 'router bgp 65000' 'neighbor 10.255.0.42 remote-as 65000' 'neighbor 10.255.0.42 update-source Loopback0' 'address-family l2vpn evpn' 'neighbor 10.255.0.42 activate' 'end'
  S "$E2" 'configure terminal' 'router bgp 65000' 'neighbor 10.255.0.41 remote-as 65000' 'neighbor 10.255.0.41 update-source Loopback0' 'address-family l2vpn evpn' 'neighbor 10.255.0.41 activate' 'end'
  sleep 40; C m11t7
}
w8() {
  R; V m11t6 m11t7; sleep 40; echo "#### m11t8: lacp device-id を XE1 だけに(期待= 束・ES・エイリアシングが落ちる)"
  V m11t8; S "$E2" 'configure terminal' 'interface Port-channel1' 'no lacp device-id' 'end'; sleep 60; C m11t8
  echo "#### m11t8: XE2 だけ ESI を種類 3 に(期待= ES の確認が落ちる)"
  V m11t8; S "$E2" 'configure terminal' 'interface Port-channel1' 'no evpn ethernet-segment 4' 'exit' 'no l2vpn evpn ethernet-segment 4' \
    'l2vpn evpn ethernet-segment 4' 'identifier type 3 system-mac 0000.0000.0004' 'redundancy all-active' 'exit' 'interface Port-channel1' 'evpn ethernet-segment 4' 'end'
  sleep 60; C m11t8
}
w9() {
  R; V m11t6 m11t7 m11t8; sleep 60; echo "#### m11t9: CC の間隔が既定(期待= 黙った故障の 2 項目が落ちる 60)"
  V m11t9; for h in $E1 $E3; do S "$h" 'configure terminal' 'ethernet cfm domain PROV level 4' 'service E130 evc E130' 'no continuity-check interval 1s' 'end'; done
  sleep 30; C m11t9
  echo "#### m11t9: ethernet cfm global なし(期待= IP SLA 以外も全部落ちる)"
  V m11t9; for h in $E1 $E3; do S "$h" 'configure terminal' 'no ethernet cfm global' 'end'; done; sleep 30; C m11t9
}
fin() { R; echo "#### 白紙(最後の reset 後)"; C final; }
for p in ${*:-w6 w7 w8 w9 fin}; do $p; done
