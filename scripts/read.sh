#!/usr/bin/env bash
# ============================================================
# 読み物（訳文を読むための HTML）のビルドと配信。BL-230。
# 問題ではない。技術書を段階的に訳しながら読み進めるための機能。
#
#   ビルド: scripts/read.sh build  <ソースディレクトリ>
#   配信:   ポータル(scripts/pack.sh serve → http://<ホスト>:8899/ の Study Materials)に一本化(2026-10-13・BL-247)。
#           build した読み物は book.yml の shelf: の棚に載る。`read.sh serve` はポータルを起動するだけの別名。
#   持ち出し: scripts/read.sh bundle <ソースディレクトリ> [--split]
#           → reading/<key>-offline.html （全ページを1枚に・外部参照ゼロ）
#             --split なら章ごとに1枚。Drive へ置いてスマホに落とせば通信なしで読める
#   同期:   scripts/read.sh sync <ソースディレクトリ> [--dry-run]
#           → 章ごとにビルドし、クラウドへ **作成・改訂・削除をまとめて反映**（rclone sync）。
#             宛先は book.yml の drive:（例 "gdrive:…/ja"）。初回だけ `rclone config` が要る。
#
# ソース(訳文 Markdown)の置き場と記法は topologies/gen_reading.py の docstring を参照。
# 出力 reading/ は .gitignore 済（ソースが非公開なら成果物も非公開）。
# ============================================================
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$REPO/.venv/bin/python3"

usage() { sed -n '2,15p' "${BASH_SOURCE[0]}"; exit 1; }

cmd="${1:-}"; shift || true
case "$cmd" in
  build)
    src="${1:-}"; [ -n "$src" ] || usage; shift
    "$PY" "$REPO/topologies/gen_reading.py" build --src "$src" "$@"
    ;;
  sync)
    src="${1:-}"; [ -n "$src" ] || usage; shift
    # 1) 章ごとに持ち出し用ディレクトリへビルド（消えた章はここからも消える）
    "$PY" "$REPO/topologies/gen_reading.py" bundle --src "$src" --stage
    key=$("$PY" -c "import sys,yaml;print((yaml.safe_load(open(sys.argv[1]+'/book.yml'))or{}).get('key',''))" "$src")
    dest=$("$PY" -c "import sys,yaml;print((yaml.safe_load(open(sys.argv[1]+'/book.yml'))or{}).get('drive',''))" "$src")
    [ -n "$dest" ] || { echo "book.yml に drive: が無い（同期先を書いてください）"; exit 2; }
    command -v rclone >/dev/null || { echo "rclone が無い。~/.local/bin/rclone を確認"; exit 2; }
    # 2) 作成・改訂・削除をそのまま反映（source に無い物は宛先から消える）
    echo "同期: reading/_offline/$key/ → $dest"
    exec rclone sync "$REPO/reading/_offline/$key" "$dest" --progress "$@"
    ;;
  bundle)
    src="${1:-}"; [ -n "$src" ] || usage; shift
    "$PY" "$REPO/topologies/gen_reading.py" bundle --src "$src" "$@"
    ;;
  serve)
    # 読み物だけの配信(旧 8898)は廃止。ポータル(8899)の Study Materials から読む。
    if (exec 3<>/dev/tcp/127.0.0.1/8899) 2>/dev/null; then
      echo "読み物はポータルで配信中です: http://10.1.10.6:8899/ (Study Materials)"
      exit 0
    fi
    echo "読み物の配信はポータルに一本化しました。ポータルを起動します(scripts/pack.sh serve)。"
    exec "$REPO/scripts/pack.sh" serve "$@"
    ;;
  *) usage ;;
esac
