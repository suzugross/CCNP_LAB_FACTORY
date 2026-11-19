#!/bin/bash
# XRT-16 の誤答の E2E= 模範解が全部入った状態から、課題ごとに 1 か所だけ崩して(solve_xrt16.sh w<n>)その課題の確認を回し、戻す(r<n>)。
# usage: source poc/xr/env.sh; poc/xr/e2e_wrong_xrt16.sh 1 2 3 4 5 6
cd "$(dirname "$0")/../.."
for n in "$@"; do
  poc/xr/solve_xrt16.sh "w$n" > /dev/null 2>&1; sleep 5
  echo "#### w$n"; poc/xr/e2e_xrt16.sh "m14t$n"
  poc/xr/solve_xrt16.sh "r$n" > /dev/null 2>&1
done
