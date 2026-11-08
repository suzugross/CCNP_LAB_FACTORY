#!/bin/bash
# XRT-14 の誤答の判別・逐語の模範解・やり直しの確認(E2E)。usage: source poc/xr/env.sh; poc/xr/wrong_xrt14.sh   出力= 段ごとの合計と FAIL の行
cd "$(dirname "$0")/../.."
R() { echo "#### reset"; scripts/lab.sh reset XRT-14 2>&1 | tail -2; sleep 40; }
C() { timeout 900 poc/xr/e2e_xrt14.sh "$@" 2>&1 | grep -E "合計|FAIL"; }
V() { timeout 300 poc/xr/solve_xrt14.sh "$@"; }
X1=$(awk '$1=="XR01:"{print $2}' topologies/_generated/XRT-14/mgmt_map.yml)
R
echo "#### m12t1-allef(期待= CE2 の確認が落ちる)"; V m12t1-allef; sleep 30; C m12t1
R; echo "#### m12t1-noremark(期待= 両方落ちる)"; V m12t1-noremark; sleep 30; C m12t1
R; echo "#### m12t1-noexp(期待= P1 の確認が落ちる)"; V m12t1-noexp; sleep 30; C m12t1
R; echo "#### m12t2-qg(期待= コミットが拒まれる)"; V m12t1; .venv/bin/python poc/xr/xrsh.py "$X1" configure 'policy-map CE1-IN' 'class DATA' 'set qos-group 3' \
  'police rate 256 kbps peak-rate 512 kbps' 'conform-action transmit' 'exceed-action set dscp af22' 'violate-action drop' 'exit' 'exit' 'end-policy-map' commit 'show configuration failed' abort 2>&1 | grep -E "!!%|Failed"
echo "#### m12t2-1r2c(期待= 両方落ちる)"; V m12t2-1r2c; sleep 30; C m12t2
R; echo "#### m12t3-php(期待= CE1 の確認が落ちる)"; V m12t1 m12t2 m12t3-php; sleep 40; C m12t3
R; echo "#### m12t3-noshape(期待= 整形の確認が落ちる)"; V m12t1 m12t2 m12t3-noshape; sleep 40; C m12t3
R; echo "#### m12t4-loosecust(期待= CUST1 の確認が落ちる)"; V m12t4-loosecust; sleep 20; C m12t4
R; echo "#### m12t4-strictinet(期待= INET の送信元の確認が落ちる)"; V m12t4-strictinet; sleep 20; C m12t4
R; echo "#### m12t4-allowdef(期待= INET の送信元の確認が落ちる)"; V m12t4-allowdef; sleep 20; C m12t4
R; echo "#### m12t4-noacl(期待= インフラ ACL の確認が落ちる)"; V m12t4-noacl; sleep 20; C m12t4
R; echo "#### m12t5-noexport(期待= 攻撃元の確認と新しい攻撃元の確認が落ちる)"; V m12t4 m12t5-noexport; sleep 40; C m12t5
R; echo "#### m12t5-discard(期待= INET への漏れの確認が落ちる)"; V m12t4 m12t5-discard; sleep 40; C m12t5
R; echo "#### m12t5-static(期待= 新しい攻撃元の確認とインターネットへの漏れの確認が落ちる)"; V m12t4 m12t5-static; sleep 40; C m12t5
R; echo "#### 逐語の模範解(learn.yml の solution をそのまま)→ 最終"; .venv/bin/python poc/xr/verbatim.py XRT-14 "$X1"; sleep 60; C final
R; echo "#### 白紙(最後の reset 後)"; C final
