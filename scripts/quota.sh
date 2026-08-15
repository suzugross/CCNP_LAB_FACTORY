#!/usr/bin/env bash
# ============================================================
# 1日の学習ノルマ（紙面10問・ラボ3問/3ジャンル）の記録と確認。BL-114。
#
#   進捗:   scripts/quota.sh                       # 当日の進捗
#           scripts/quota.sh today --brief         # 1行（フック用）
#   記録:   scripts/quota.sh log paper 20260812-024 ok
#           scripts/quota.sh log lab GEN-DMVPN-48222 --score 100 --total 100
#   採点:   scripts/quota.sh grade-lab GEN-DMVPN-48222 [--variant base]
#           ↑ grade.yml を実走して得点を自動記録する（採点はこれで打つ）
#   集計:   scripts/quota.sh report --days 30 --out /tmp/quota.html
#   取込:   scripts/quota.sh backfill [--apply]    # _history.md から過去分
#
# 記録の実体は records/attempts.jsonl（追記専用）。PVT系は private/ 側へ分離。
# ノルマ値・日付境界は records/quota.yml、ジャンル定義は records/genres.yml。
# ============================================================
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "$REPO/.venv/bin/python3" "$REPO/topologies/quota.py" --repo "$REPO" \
     "${@:-today}"
