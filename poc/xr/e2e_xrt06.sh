#!/bin/bash
# XRT-06 の E2E= 課題ごとの確認(grading.<課題>.yml)か最終(grading.yml)を grade.yml で 1 回だけ回す(ノルマに記録しない)。
# usage: poc/xr/e2e_xrt06.sh <m7t1 … m7t5 | final> …   出力= [課題] [PASS]/[FAIL] の行と未充足・合計
cd "$(dirname "$0")/../.."
for ck in "$@"; do
  if [ "$ck" = final ]; then args=(-e max_attempts=1); else args=(-e checkpoint="$ck" -e max_attempts=1); fi
  .venv/bin/ansible-playbook playbooks/grade.yml -e problem=XRT-06 "${args[@]}" --vault-password-file <(printf "CCNP\n") 2>&1 \
    | sed -n '/TASK \[最終結果\]/,$p' | grep -E "\[(PASS|FAIL)\]|未充足|合計" | sed "s/^/[$ck] /"
done
