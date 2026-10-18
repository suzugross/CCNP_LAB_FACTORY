#!/bin/bash
# 中間チェック(または最終採点)を 1 回回して結果の行だけ出す。引数= チェック名 … / final
cd "$(dirname "$0")/../.."
for c in "$@"; do
  if [ "$c" = final ]; then extra=""; else extra="-e checkpoint=$c"; fi
  .venv/bin/ansible-playbook playbooks/grade.yml -e problem=${PROB:-XRT-01} $extra -e max_attempts=${ATT:-1} --vault-password-file <(printf 'CCNP\n') 2>&1 \
    | sed -n '/TASK \[最終結果\]/,$p' | grep -E "\[(PASS|FAIL)\]|未充足|合計" | sed "s/^ *- *//; s/^/[$c] /" | cut -c1-170
done
