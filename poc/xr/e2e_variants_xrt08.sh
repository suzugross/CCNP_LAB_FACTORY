#!/bin/bash
# XRT-08 の誤答・別解・やり直しの確かめ(design §21.8)。各ケースの前に lab.sh reset で構築直後へ戻す。
# usage: source poc/xr/env.sh; poc/xr/e2e_variants_xrt08.sh [ケース…](既定= 全部)   出力= poc/xr/expM8b-variants.log へ
cd "$(dirname "$0")/../.."
XR=$(awk '$1=="XR01:"{print $2}' topologies/_generated/XRT-08/mgmt_map.yml)
S() { poc/xr/solve_xrt08.sh "$XR" "$@"; }
G() { poc/xr/e2e_xrt08.sh "$@" | grep -E "合計|FAIL"; }
rst() { echo "== reset"; scripts/lab.sh reset XRT-08 2>&1 | grep -E "rollback|after rollback|ERROR|WARNING"; sleep 20; }
case_A() { echo "### A: reset 直後の白紙(期待 0/0)"; rst; G m8t6 m8t7; }
case_B() { echo "### B: 別解 Lo0 を 2 つのインスタンスに(期待 m8t6 100)"; rst; S m8t6-two; sleep 50; G m8t6; }
case_C() { echo "### C: Lo0 を載せない(期待 m8t6 20)"; rst; S m8t6-nolo; sleep 50; G m8t6; }
case_D() { echo "### D: コアの経路をアクセスへ再配送(期待 m8t6 80)"; rst; S m8t6-leak; sleep 50; G m8t6; }
case_E() { echo "### E: allocate-label だけ(期待 m8t7 0)"; rst; S m8t6; sleep 40; S m8t7-alloc; sleep 60; G m8t7; }
case_F() { echo "### F: enforce だけ(期待 m8t7 0)"; rst; S m8t6; sleep 40; S m8t7-enforce; sleep 60; G m8t7; }
case_G() { echo "### G: 送る経路だけ絞る(期待 m8t8 70)"; rst; S m8t6; sleep 40; S m8t7; sleep 60; S m8t8-out; sleep 40; G m8t8; }
case_H() { echo "### H: learn.yml の模範解を逐語で(期待 final 100)"; rst; .venv/bin/python poc/xr/verbatim.py XRT-08 "$XR"; sleep 90; G final; }
case_I() { echo "### I: reset して白紙で残す(期待 final 0)"; rst; G final; }
for c in ${*:-A B C D E F G H I}; do echo; echo "######## $(date +%T)"; case_$c; done
