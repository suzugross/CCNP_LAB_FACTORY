#!/bin/bash
# BL-115 GEN-BGPBEST 実機検証スイープ: 各故障 broken→fix→100 / build 0→100
# 使い方: lab_sweep.sh <fault|build> <seed>
set -u
REPO=/home/suzuki/ansible/CCNP01
cd "$REPO"
FAULT=$1
SEED=$2
ID="GEN-BGPBEST-$SEED"
VAULT=$(mktemp)
echo CCNP > "$VAULT"
LOG="poc/bgpbest/sweep-$FAULT.log"
: > "$LOG"

say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

grade() {
  .venv/bin/ansible-playbook playbooks/grade.yml -e problem="$ID" \
    --vault-password-file "$VAULT" >> "$LOG" 2>&1
  grep -E '合計|TOTAL|total' "$LOG" | tail -2
}

say "=== $FAULT (seed=$SEED) ==="
if [ "$FAULT" = "build" ]; then
  .venv/bin/python3 topologies/gen_bgpbest_ts.py --repo . --seed "$SEED" \
    --mode build >> "$LOG" 2>&1 || { say "gen 失敗"; exit 1; }
else
  .venv/bin/python3 topologies/gen_bgpbest_ts.py --repo . --seed "$SEED" \
    --mode ts --fault "$FAULT" >> "$LOG" 2>&1 || { say "gen 失敗"; exit 1; }
fi

say "provision..."
scripts/lab.sh provision "$ID" >> "$LOG" 2>&1 || { say "provision 失敗"; exit 1; }
say "収束待ち 120s"
sleep 120

say "grade(broken)"
grade
say "fix 投入"
.venv/bin/ansible-playbook playbooks/fix_generated.yml -e problem="$ID" \
  --vault-password-file "$VAULT" >> "$LOG" 2>&1 || say "fix 投入で警告(ログ確認)"
say "収束待ち 45s"
sleep 45
say "grade(fixed)"
grade
say "teardown"
scripts/lab.sh teardown "$ID" >> "$LOG" 2>&1
rm -f "$VAULT"
say "=== $FAULT 完了 ==="
