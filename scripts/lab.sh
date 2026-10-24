#!/usr/bin/env bash
# ============================================================
# CCNP ラボのライフサイクル管理（出題=provision / 片付け=teardown）。
# Claude が一貫して回すための薄いラッパ。コピー〜削除までを1コマンドに集約。
#
#   出題:   scripts/lab.sh provision <PROBLEM_ID> [variant]
#   採点:   scripts/lab.sh grade     <PROBLEM_ID> [variant]
#   中間:   scripts/lab.sh checkpoint <PROBLEM_ID> <名前>   # grading.<名前>.yml で途中の状態を確認(ノルマ記録なし)
#   片付け: scripts/lab.sh teardown  <PROBLEM_ID> [--keep-workspace]
#   やり直し: scripts/lab.sh reset   <PROBLEM_ID>          # IOS XR を構築直後のコミットへ戻す＋学習モードの記録を初期化(BL-254)
#   学習:   scripts/lab.sh learn     <PROBLEM_ID> [PORT]   # 学習モードのワークスペース(Steps タブ= 確認・ヒント)。既定 8896
#   状態:   scripts/lab.sh status
#   交換:   scripts/lab.sh rma <PROBLEM_ID> <NODE>     # 機器交換(保存済みの設定で新しい MAC の機体に入れ替える・BL-249)
#
#   LAB_XR_PLATFORM=xrd を付けて provision すると、XR のノードを XRv9000 ではなく XRd(コンテナ)で組む(BL-250)。
#   LAB_TASK_ANNOTATION=off を付けて provision すると、CML キャンバスに問題の要約注釈を貼らない
#   (全文は Lab Notes に残る)。パック(gen_pack)経由の構築は常に off。
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

usage() { sed -n '2,20p' "${BASH_SOURCE[0]}"; exit 1; }

cmd="${1:-}"; prob="${2:-}"

case "$cmd" in
  provision)
    [ -n "$prob" ] || usage
    [ -d "$REPO/problems/$prob" ] || { echo "問題が存在しません: $prob"; exit 1; }
    variant="${3:-base}"
    echo "== [1/3] build_topology ($prob, variant=$variant) =="
    "$PY/ansible-playbook" "$REPO/playbooks/build_topology.yml" \
      -e problem="$prob" -e variant="$variant" \
      -e task_annotation="${LAB_TASK_ANNOTATION:-on}" \
      -e xr_platform="$( [ "${LAB_XR_PLATFORM:-}" = xrd ] && echo iosxrd || echo iosxr )" \
      --vault-password-file <(vault)
    echo "== [2/3] lab_up (CML 起動) =="
    "$PY/ansible-playbook" "$REPO/playbooks/lab_up.yml" \
      -e problem="$prob" --vault-password-file <(vault)
    # 複合ラボ(BL-061): problem.yml に clab_topology があれば containerlab 側も deploy
    # (未定義の問題は clab_ops.py が即スキップするので常時呼んで無害)
    "$PY/python3" "$REPO/topologies/clab_ops.py" deploy --repo "$REPO" --problem "$prob"
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
    # 英語版の原文を持つ問題(problems/<ID>/task.en.md)は Task.md として並べる(ワークスペースが 問題.md と対で切り替える)
    if [ -f "$REPO/problems/$prob/task.en.md" ]; then
      cp "$REPO/problems/$prob/task.en.md" "$dest/Task.md"
    fi
    echo "== [3/3] 作業フォルダ作成: $dest =="
    echo "   $(ls "$dest" 2>/dev/null | tr '\n' ' ')"
    echo "完了。VSCodeで開いた CCNP01 ツリーの lab/$prob/ を編集（問題.md 同梱）。SSH: SUZUKI/CCNP・mgmt .11〜。"
    ;;

  grade)
    # grade.yml をそのまま流しつつ、得点を学習ノルマ台帳に自動記録する（BL-114）。
    # 出力・落ちたチェック名の見え方は素の ansible-playbook と同じ。
    [ -n "$prob" ] || usage
    variant="${3:-}"
    exec "$PY/python3" "$REPO/topologies/quota.py" --repo "$REPO" \
      grade-lab "$prob" ${variant:+--variant "$variant"}
    ;;

  reset)
    # 学習用ラボのやり直し(BL-254)。IOS XR の機器を構築直後のコミットへ戻す(作り直さない・数秒)。
    # 相手役の IOS・サーバは戻さない(課題で変えない約束)。学習モードの記録は退避して初期化する。
    [ -n "$prob" ] || usage
    "$PY/ansible-playbook" "$REPO/playbooks/xr_reset.yml" -e problem="$prob" --vault-password-file <(vault)
    log="$REPO/records/learn/$prob.jsonl"
    if [ -f "$log" ]; then mv "$log" "$REPO/records/learn/$prob.$(date +%Y%m%d-%H%M%S).jsonl.bak"; echo "学習モードの記録を退避: records/learn/$prob.*.jsonl.bak"; fi
    ;;

  checkpoint)
    # 途中の状態を確認する中間チェック(BL-231)。点数は参考・ノルマには記録しない。
    [ -n "$prob" ] || usage
    cp="${3:-}"; [ -n "$cp" ] || { echo "中間チェック名を指定: 例 scripts/lab.sh checkpoint $prob t13"; exit 2; }
    [ -f "$REPO/problems/$prob/grading.$cp.yml" ] || { echo "problems/$prob/grading.$cp.yml が無い"; exit 2; }
    echo "== 中間チェック $cp（参考点・ノルマ記録なし）: $prob =="
    # 中間チェックは「いまの状態」を見るだけなので、本採点(10 回)ほど粘らない。未充足が残ると
    # 全項目を取り直すため、10 回だと 10 分を超える(2026-10-06 実測)。収束待ちぶんだけ 3 回にする。
    exec "$PY/ansible-playbook" "$REPO/playbooks/grade.yml" \
      -e problem="$prob" -e checkpoint="$cp" -e max_attempts="${LAB_CP_ATTEMPTS:-3}" \
      --vault-password-file <(vault)
    ;;

  rma)
    # 機器交換(BL-249): 保存済みの startup-config を退避 → 停止・初期化 → MAC 差し替え → 保存済みの設定で起動。
    # 保存していない設定は戻らない(本物の交換と同じ)。初期化で VLAN データベースも消える。
    [ -n "$prob" ] || usage
    node="${3:-}"; [ -n "$node" ] || { echo "交換するノード名を指定: 例 scripts/lab.sh rma $prob SW5"; exit 2; }
    echo "== 機器交換: $prob の $node (保存済みの設定だけが新しい機体に戻ります) =="
    exec "$PY/ansible-playbook" "$REPO/playbooks/lab_rma.yml" \
      -e repo="$REPO" -e problem="$prob" -e node="$node" --vault-password-file <(vault)
    ;;
  learn)
    # 学習モードのワークスペース(BL-246)。problems/<ID>/learn.yml を持つ問題だけ。provision 済みが前提。
    [ -n "$prob" ] || usage
    [ -f "$REPO/problems/$prob/learn.yml" ] || { echo "problems/$prob/learn.yml が無い(学習モードの対象外)"; exit 2; }
    exec "$PY/python3" "$REPO/topologies/lab_console.py" --repo "$REPO" --learn "$prob" --port "${3:-8896}"
    ;;

  teardown)
    [ -n "$prob" ] || usage
    keep=0; [ "${3:-}" = "--keep-workspace" ] && keep=1
    echo "== CMLラボを absent（VM実体を解放）: $prob =="
    if ! "$PY/ansible-playbook" "$REPO/playbooks/lab_up.yml" \
      -e problem="$prob" -e lab_state=absent --vault-password-file <(vault); then
      # ★撤去に失敗したとき、CML にラボがまだ残っていれば止める(2026-10-24 XRT-05: 残ったラボの IP を台帳だけ返して
      #   しまい、生成物も消えて teardown をやり直せなくなった)。リースと生成物を残しておけば、やり直せて IP の二重割り当ても起きない。
      #   ラボが CML に無い(手で消した等)ときだけ、従来どおり先へ進んでリースを返す。
      rc=0; "$PY/python3" "$REPO/topologies/cml_lab_exists.py" --repo "$REPO" --problem "$prob" || rc=$?
      if [ "$rc" -eq 3 ]; then
        echo "!! 生成物が無くラボの名前が分かりません。CML の画面でラボが残っていないか確かめてください(先へ進みます)。"
      elif [ "$rc" -ne 1 ]; then
        echo "!! CML のラボがまだ残っているか、確かめられませんでした。MGMT リースと生成物は残しました。"
        echo "!! 少し待ってから scripts/lab.sh teardown $prob をやり直してください。"
        exit 1
      fi
      if [ "$rc" -eq 1 ]; then echo "== CML にラボは残っていません(先へ進みます) =="; fi
    fi
    # ラボが CML から消えたら MGMT リースを返す（冪等）
    "$PY/python3" "$REPO/topologies/mgmt_alloc.py" release --repo "$REPO" --problem "$prob" || true
    # 複合ラボ(BL-061): clab 側も destroy(clab_topology 未定義なら即スキップ)
    "$PY/python3" "$REPO/topologies/clab_ops.py" destroy --repo "$REPO" --problem "$prob" || true
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
