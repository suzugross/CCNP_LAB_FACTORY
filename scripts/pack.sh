#!/usr/bin/env bash
# ============================================================
# 問題パック（連続出題）のライフサイクル管理。BL-099。
# 紙面3問＋ラボ2問を1パックにまとめ、HTML の問題用紙を packs/<PACK-ID>/ に出す。
#
#   作成:   scripts/pack.sh new [オプション]          # 夜間バッチ想定（時間はかかる）
#   下見:   scripts/pack.sh new --dry-run             # CML にも questions/ にも触らない
#   進捗:   scripts/pack.sh status [PACK-ID]
#   採点:   scripts/pack.sh grade  [PACK-ID]
#   撤収:   scripts/pack.sh close  [PACK-ID]
#   配信:   scripts/pack.sh serve  [PORT]   # Windows のブラウザから開く用
#           ★このサーバ経由で開くと、ページ下部の解答欄がそのまま 解答.md に保存される
#
# 設計方針:
#   - 「寝る前に作らせ、翌朝から1日で解く」運用。所要時間は最適化せず、
#     **朝、確実に解ける状態になっていること**（各フェーズの完成判定）に全振りする。
#   - 出力 packs/ は .gitignore 済の使い捨て。正解キー(answers/)は絶対に置かない。
#   - 夜間に流す時は nohup 推奨:
#       nohup scripts/pack.sh new > /dev/null 2>&1 &
#     進捗は topologies/_state/pack-<PACK-ID>.log に追記される
#     （故障種が出るのでユーザフォルダには置かない）。
# ============================================================
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$REPO/.venv/bin/python3"
GEN="$REPO/topologies/gen_pack.py"

usage() { sed -n '2,21p' "${BASH_SOURCE[0]}"; exit 1; }

cmd="${1:-}"; shift || true
case "$cmd" in
  new)
    "$PY" "$GEN" new --repo "$REPO" "$@"
    ;;
  serve)
    # Windows 側のブラウザから開くための配信。VSCode Remote-SSH ならポートが
    # 自動転送されるので、Windows で http://localhost:<PORT>/ を開けばよい。
    port="${1:-8899}"
    echo "VSCode のポート転送が効いていれば Windows のブラウザからそのまま開けます"
    exec "$PY" "$REPO/topologies/pack_server.py" --repo "$REPO" --port "$port"
    ;;
  status|grade|close|render|replace|redeploy)
    # 第1引数が PACK-* ならそれを --pack-id として渡す（打ちやすさ優先）
    first="${1:-}"
    if [ -n "$first" ] && [ "$first" != "${first#PACK-}" ]; then
      pid="$1"; shift
      "$PY" "$GEN" "$cmd" --repo "$REPO" --pack-id "$pid" "$@"
    else
      "$PY" "$GEN" "$cmd" --repo "$REPO" "$@"
    fi
    ;;
  *) usage ;;
esac
