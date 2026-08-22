#!/usr/bin/env bash
# BL-134 E2E 自己検品: GEN-IPSLATS 全13故障種を実機フルサイクルで回す。
#   各 seed(90001..90013)= 1故障種固定生成済み。
#   provision → grade(broken・max_attempts=2) → fix_generated → grade(→100点期待)
#   → 不感系4種のみ verify_ipsla_generated(破壊実証・fix 後=全段PASS期待) → teardown
# 使い方: poc/ipsla/e2e.sh [開始i] [終了i]   (既定 1 13)
# ★検証 seed は E2E 後に problems/ から掃除する(出題時新seed の規約)。
set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PY="$REPO/.venv/bin"
vault() { printf 'CCNP\n'; }
VERIFY_KINDS=" sla_wrong_source_lo sla_wrong_target route_track_missing pin_missing "

score_of() {  # 採点ログから最終スコアを抜く
  grep -oE '合計: [0-9]+ / [0-9]+' "$1" | tail -1 | grep -oE '^合計: [0-9]+' | grep -oE '[0-9]+'
}

for i in $(seq "${1:-1}" "${2:-13}"); do
  seed=$((90000 + i)); id="GEN-IPSLATS-$seed"
  fault=$("$PY/python3" -c "import json;print(json.load(open('$REPO/problems/$id/solution/fault.json'))['faults'][0])")
  echo "==== [$i/13] $id fault=$fault $(date +%H:%M:%S) ===="
  logdir=$(mktemp -d)
  if ! "$REPO/scripts/lab.sh" provision "$id" >"$logdir/prov.log" 2>&1; then
    echo "RESULT $id $fault PROVISION-FAIL (log: $logdir/prov.log)"
    "$REPO/scripts/lab.sh" teardown "$id" >/dev/null 2>&1
    continue
  fi
  "$PY/ansible-playbook" "$REPO/playbooks/grade.yml" -e problem="$id" \
    -e max_attempts=2 --vault-password-file <(vault) >"$logdir/broken.log" 2>&1
  broken=$(score_of "$logdir/broken.log"); broken=${broken:-ERR}
  "$PY/ansible-playbook" "$REPO/playbooks/fix_generated.yml" -e problem="$id" \
    --vault-password-file <(vault) >"$logdir/fix.log" 2>&1 || echo "  [!] fix 投入で失敗 (log: $logdir/fix.log)"
  "$PY/ansible-playbook" "$REPO/playbooks/grade.yml" -e problem="$id" \
    --vault-password-file <(vault) >"$logdir/fixed.log" 2>&1
  fixed=$(score_of "$logdir/fixed.log"); fixed=${fixed:-ERR}
  vres="-"
  if [[ "$VERIFY_KINDS" == *" $fault "* ]]; then
    if "$PY/ansible-playbook" "$REPO/playbooks/verify_ipsla_generated.yml" \
         -e problem="$id" --vault-password-file <(vault) >"$logdir/verify.log" 2>&1; then
      vres="PASS"
    else
      vres="FAIL(log: $logdir/verify.log)"
    fi
  fi
  "$REPO/scripts/lab.sh" teardown "$id" >"$logdir/teardown.log" 2>&1 \
    || echo "  [!] teardown 失敗 (log: $logdir/teardown.log)"
  keep="OK"
  { [ "$fixed" = "100" ] && [ "$broken" != "100" ] && [ "$broken" != "ERR" ]; } || keep="NG(logs: $logdir)"
  echo "RESULT $id $fault broken=$broken fixed=$fixed verify=$vres judge=$keep"
  [ "$keep" = "OK" ] && rm -rf "$logdir"
done
echo "==== E2E 完了 $(date +%H:%M:%S) ===="
