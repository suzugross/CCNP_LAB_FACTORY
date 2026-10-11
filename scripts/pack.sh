#!/usr/bin/env bash
# ============================================================
# 問題パック（連続出題）のライフサイクル管理。BL-099 / BL-205。
# ★2026-09-20（BL-205・ユーザ指示）: **1回の new で 3 パック作る**のが既定。
#   1パックの中身 = 思考系5問 ＋ 瞬発力枠8問 ＋ 穴埋め枠5問（＝紙面18問）。
#   ラボ2〜3問は **1本目にだけ**付く（CML の予算は1日ぶんで共通のため増やせない）。
#   配分は**1日全体**で決める: 必須ジャンルを3パックへ配り分け（4/3/3＝全10ジャンルを1周）、
#   先行パックで出した shape/kind は後続パックの抽選から外す。
#   HTML の問題用紙は packs/<PACK-ID>/ に出る（2本目以降は -B / -C が自動で付く）。
#   本数   = --packs（既定3・1 にすれば従来どおり単発）
#   ★1パック7問(思考2+瞬発3+穴埋め2)×3 = 21問/日(2026-09-28 ユーザ指示。旧 5〜6+8+5)
#   思考系 = --paper（既定 auto=2・必須ジャンルは --require-shape auto で配り分け）
#   瞬発力 = --speed（既定3・shape=speed・別枠で上乗せ・0 で無効）
#   穴埋め = --cloze（既定2・shape=cloze=解説穴埋め形・別枠で上乗せ・0 で無効・2026-09-19）
#   紙面   = 3 枠とも単元ローテーション（BL-224）= units.yml の全単元を最終実施日の古い順に 1 問ずつ。
#            確認: python3 topologies/paper_rotation.py [--all]。--require-shape/--profile 明示で従来の抽選
#   ラボ   = 単元ローテーション 3 問（1本目のみ・BL-223）= 曜日表＋遅れ補正（topologies/lab_modes.yml）。
#            今日の選定表の確認: python3 topologies/lab_rotation.py [--date YYYY-MM-DD]
#            --lab-genres a,b,… を明示すると従来の固定ジャンル抽選（--lab 2 ＋ --lab-extra 1）
#   範囲   = --profile ccna|encor|enarsi|ccie|vendor|U-A3,U-H2 …（単元台帳 CURRICULUM.md の単元で絞る・BL-213）
#
#   作成:   scripts/pack.sh new [オプション]          # 夜間バッチ想定（時間はかかる）
#   下見:   scripts/pack.sh new --dry-run             # CML にも questions/ にも触らない
#   進捗:   scripts/pack.sh status [PACK-ID]
#   採点:   scripts/pack.sh grade  [PACK-ID]
#           scripts/pack.sh grade --today --no-lab   # 今日の3パックの紙面をまとめて採点
#           scripts/pack.sh grade --today --report-only  # 解説ページだけ組み直す(再記録なし)
#           scripts/pack.sh grade <PACK-ID> --no 3   # Q3 のラボだけ再採点(他のラボは前回の結果のまま)
#   英語版: scripts/pack.sh en     [PACK-ID] / en --today   # 紙面の英語版の状態(未訳・原文との食い違い)。全部 OK で rc=0
#           ★紙面も英文出題が基本(2026-10-08)。訳文は questions/en/<ID>.md(原文の隣の en/)に出題者が置き、
#             照合を通ったものだけが描画に使われる(通らない問は日本語のまま)。置いたら render で反映。
#           scripts/pack.sh render <PACK-ID> --paper-lang ja   # このパックの紙面を日本語に戻す(en で英語へ)
#   撤収:   scripts/pack.sh close  [PACK-ID] / close --today
#   配信:   scripts/pack.sh serve  [PORT]   # Windows のブラウザから開く用
#           ★このサーバ経由で開くと、ページ下部の解答欄がそのまま 解答.md に保存される
#           ★ラボのワークスペース(BL-234)も一緒に上がる: ラボの問番号を押すと、最初から
#             左=タスク/トポロジ・右=機器コンソール の 1 画面で開く(別ポート 8897・topologies/lab_console.py)。
#             ポートは PACK_CONSOLE_PORT で変更、PACK_CONSOLE_PORT=0 で起動しない
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

usage() { sed -n '2,38p' "${BASH_SOURCE[0]}"; exit 1; }

# ★本体は関数に入れて最後に 1 回呼ぶ。bash はスクリプトを読み進めながら実行するので、実行中
#   (new は 15〜25 分・grade は数分)にこのファイルを書き換えると、続きを別の位置から読んで壊れる
#   (2026-10-07 実発= grade の実行中に編集し、終了時に「-repo: command not found」で exit 127)。
#   関数にしておけば、呼ぶ前に全文を読み終えているので、あとからの編集に影響されない。
main() {
cmd="${1:-}"; shift || true
case "$cmd" in
  new)
    "$PY" "$GEN" new --repo "$REPO" "$@"
    ;;
  serve)
    # Windows 側のブラウザから開くための配信。
    # ★2026-09-21 ユーザ指示: LAN(10.1.10.6:<PORT>)から直接開けるように、既定で 0.0.0.0 に bind する
    #   (VSCode のポート転送越しの http://localhost:<PORT>/ も従来どおり使える)。
    #   127.0.0.1 だけに戻すなら: scripts/pack.sh serve 8899 127.0.0.1  (または PACK_BIND=127.0.0.1)
    port="${1:-8899}"
    bind="${2:-${PACK_BIND:-0.0.0.0}}"
    cport="${PACK_CONSOLE_PORT:-8897}"
    echo "Windows のブラウザから http://10.1.10.6:${port}/ (LAN) または http://localhost:${port}/ (VSCode 転送) で開けます"
    # ラボのワークスペース(コンソール中継)を同じ bind で一緒に上げる。配信サーバ(下の exec で
    # このシェルと同じ PID になる)が終われば --with-parent で自分も終わる。配信サーバが
    # ポート使用中などで即終了した時も居残らないよう、親の PID はここから渡す。
    # 起動に失敗しても(ポート使用中など)配信は続ける。VSCode 転送で開く時は ${cport} も転送する。
    if [ "$cport" != "0" ]; then
      "$PY" "$REPO/topologies/lab_console.py" --repo "$REPO" --port "$cport" --bind "$bind" \
            --pack-port "$port" --with-parent "$$" &
    fi
    exec "$PY" "$REPO/topologies/pack_server.py" --repo "$REPO" --port "$port" --bind "$bind" --console-port "$cport"
    ;;
  status|grade|close|render|replace|redeploy|en)
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
}
main "$@"; exit $?
