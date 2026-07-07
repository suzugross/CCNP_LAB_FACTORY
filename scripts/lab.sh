#!/usr/bin/env bash
# ============================================================
# CCNP ラボのライフサイクル管理（出題=provision / 片付け=teardown）。
# Claude が一貫して回すための薄いラッパ。コピー〜削除までを1コマンドに集約。
#
#   出題:   scripts/lab.sh provision <PROBLEM_ID> [variant]
#   片付け: scripts/lab.sh teardown  <PROBLEM_ID> [--keep-workspace]
#   状態:   scripts/lab.sh status
#
# 設計方針:
#   - 容量を食うのは CML 側の VM。teardown は **CMLラボを absent** にして実体を解放する。
#   - 問題パック(problems/<ID>) は再利用するので **消さない**。
#   - 自動化ラボ(controller/ を持つ問題)は **リポジトリ内 lab/<ID>/** に作業コピー(=穴あき問題用紙
#     ＋問題.md)を置く。ユーザは VSCode で開いた CCNP01 ツリーの中で lab/<ID>/ を編集して解く
#     (別ウィンドウを開かず1つのディレクトリ参照で完結)。/lab は .gitignore 済。
#   - 作業コピーは **解くときだけの使い捨て**(本物の解答=機器の設定/模範解答=controller_solution)。
#     よって teardown は既定で **lab/<ID> も削除**する。残したいときだけ --keep-workspace。
# ============================================================
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAB_HOME="$REPO/lab"   # リポジトリ内に作業フォルダを置く（VSCodeで同じツリー内で解く・/lab は .gitignore 済）
PY="$REPO/.venv/bin"
vault() { printf 'CCNP\n'; }   # vault パスワード（プロジェクト規約）

usage() { sed -n '2,18p' "${BASH_SOURCE[0]}"; exit 1; }

cmd="${1:-}"; prob="${2:-}"

case "$cmd" in
  provision)
    [ -n "$prob" ] || usage
    [ -d "$REPO/problems/$prob" ] || { echo "問題が存在しません: $prob"; exit 1; }
    variant="${3:-base}"
    echo "== [1/3] build_topology ($prob, variant=$variant) =="
    "$PY/ansible-playbook" "$REPO/playbooks/build_topology.yml" \
      -e problem="$prob" -e variant="$variant" --vault-password-file <(vault)
    echo "== [2/3] lab_up (CML 起動) =="
    "$PY/ansible-playbook" "$REPO/playbooks/lab_up.yml" \
      -e problem="$prob" --vault-password-file <(vault)
    # [3/3] 作業フォルダ lab/<ID> を作る: 問題用紙(task.md)＋(あれば)穴あきworkspace
    mkdir -p "$LAB_HOME"          # 親 lab/ を必ず先に作る（cp -r の親不在エラー防止）
    dest="$LAB_HOME/$prob"
    rm -rf "${dest:?}"
    if [ -f "$REPO/problems/$prob/blanks.yml" ]; then
      # 穴ランダム化: blanks.yml があれば seed で穴の位置/数を変えて生成（採点は最終状態で不変）
      seed="${LAB_SEED:-$RANDOM}"
      "$PY/python3" "$REPO/topologies/gen_blanks.py" \
        --repo "$REPO" --problem "$prob" --seed "$seed" \
        --count "${LAB_COUNT:-0}" --out "$dest"
    elif [ -d "$REPO/problems/$prob/controller" ]; then
      cp -r "$REPO/problems/$prob/controller" "$dest"     # 固定の穴あき問題用紙(playbook等)
    else
      mkdir -p "$dest"
    fi
    # 問題文をコピー（params展開済みの _generated/<ID>/task.md を優先、無ければ静的 task.md）
    if   [ -f "$REPO/topologies/_generated/$prob/task.md" ]; then
      cp "$REPO/topologies/_generated/$prob/task.md" "$dest/問題.md"
    elif [ -f "$REPO/problems/$prob/task.md" ]; then
      cp "$REPO/problems/$prob/task.md" "$dest/問題.md"
    fi
    echo "== [3/3] 作業フォルダ作成: $dest =="
    echo "   $(ls "$dest" 2>/dev/null | tr '\n' ' ')"
    echo "完了。VSCodeで開いた CCNP01 ツリーの lab/$prob/ を編集（問題.md 同梱）。SSH: SUZUKI/CCNP・mgmt .11〜。"
    ;;

  teardown)
    [ -n "$prob" ] || usage
    keep=0; [ "${3:-}" = "--keep-workspace" ] && keep=1
    echo "== CMLラボを absent（VM実体を解放）: $prob =="
    "$PY/ansible-playbook" "$REPO/playbooks/lab_up.yml" \
      -e problem="$prob" -e lab_state=absent --vault-password-file <(vault) || true
    # lab_up(absent) が途中で失敗しても MGMT リースは必ず返す（冪等・保険）
    "$PY/python3" "$REPO/topologies/mgmt_alloc.py" release --repo "$REPO" --problem "$prob" || true
    echo "== 生成物を掃除: topologies/_generated/$prob =="
    rm -rf "${REPO:?}/topologies/_generated/$prob"
    if [ -d "$LAB_HOME/$prob" ]; then
      if [ "$keep" = "1" ]; then
        echo "== 作業コピーは保持(--keep-workspace): $LAB_HOME/$prob =="
      else
        echo "== 作業コピー(使い捨て)を削除: $LAB_HOME/$prob =="
        rm -rf "${LAB_HOME:?}/$prob"
      fi
    fi
    echo "片付け完了。問題パック problems/$prob は再利用のため保持。"
    ;;

  status)
    echo "== MGMT リース台帳（同時稼働ラボと空きIP） =="
    "$PY/python3" "$REPO/topologies/mgmt_alloc.py" status --repo "$REPO" || true
    echo "== 作業コピー (~/lab) =="; ls -1 "$LAB_HOME" 2>/dev/null || echo "(なし)"
    echo "== 生成物 (_generated) =="; ls -1 "$REPO/topologies/_generated" 2>/dev/null || echo "(なし)"
    ;;

  *) usage ;;
esac
