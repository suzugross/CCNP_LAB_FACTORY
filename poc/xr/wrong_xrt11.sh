#!/bin/bash
# XRT-11 の誤答の判別とやり直しの確認(E2E)。usage: source poc/xr/env.sh; poc/xr/wrong_xrt11.sh   出力= 段ごとの合計と FAIL の行
cd "$(dirname "$0")/../.."
S() { .venv/bin/python poc/xr/xrsh.py "$@" 2>&1; }
R() { echo "#### reset"; scripts/lab.sh reset XRT-11 2>&1 | tail -2; sleep 20; }
C() { timeout 300 poc/xr/e2e_xrt11.sh "$@" 2>&1 | grep -E "合計|FAIL"; }
V() { timeout 300 poc/xr/solve_xrt11.sh "$@"; }
R; echo "#### 白紙(reset 後)"; C final
echo "#### m11t1-ldpcore(期待= LDP の確認だけ落ちる)"; V m11t1-ldpcore; sleep 30; C m11t1
R; echo "#### m11t1-ldponly(別解= 100)・m11t2-mtuonly(期待= 300 が落ちる)"; V m11t1-ldponly; sleep 30; C m11t1; V m11t2-mtuonly; sleep 30; C m11t2
R; echo "#### m11t3-direct(期待= RR だけの確認が落ちる)"; V m11t1 m11t2 m11t3-direct; sleep 90; C m11t3
R; echo "#### m11t3-swap(期待= E-Line と到達が落ちる)"; V m11t1 m11t2 m11t3-swap; sleep 90; C m11t3
R; echo "#### m11t4-410only(期待= 420 が落ちる)"; V m11t1 m11t2 m11t3 m11t4-410only; sleep 90; C m11t4
echo "#### m11t5-plain(期待= 単一タグの確認が落ちる)"; V m11t5-plain; sleep 40; C m11t5
echo "#### m11t5 を列挙(10,20)に(期待= VLAN 30 の確認が落ちる)"
for h in 10.1.10.11:GigabitEthernet0/0/0/3 10.1.10.13:GigabitEthernet0/0/0/1; do S ${h%%:*} configure "interface ${h##*:}.500 l2transport" 'encapsulation dot1q 500 second-dot1q 10,20' commit end >/dev/null; done; sleep 25; C m11t5
R; echo "#### 白紙(最後の reset 後)"; C final
