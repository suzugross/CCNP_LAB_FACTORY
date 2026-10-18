# courses/ — 書き下ろしの教材

訳文ではなく、公開文書と実機の実測をもとに自分たちで書く教材の原文を置く。読み物ビルダー(`topologies/gen_reading.py`)の入力。
規約は CLAUDE.md「読み物」§6。

## 標準の形(2026-10-13・BL-248)

- **1 コース = 1 冊**。`courses/<名前>/book.yml` に `lang: en`・`alt_lang: ja` を書き、ページを `en/` と `ja/` に
  同じファイル名で置く。ポータルには 1 行で載り、ページの中のボタンで日本語⇔英語が切り替わる。
- 英語が原文。日本語版は見出しの並びと段落の数を原文にそろえる。
- `title`・`subtitle`・`chapters` は `{en: …, ja: …}` で書く。棚は `shelf:`、学習用ラボは `labs: [問題 ID]`。
- 実践ページ(課題文)は `practice.yml` の対応表に従って `scripts/course.sh` が課題文から切り出す(ここには置かない)。

## コマンド

| 目的 | コマンド |
|---|---|
| ビルド(ポータルに載る) | `scripts/course.sh <名前> build` |
| Drive へ持ち出す(言語ごとに別の 1 枚) | `scripts/course.sh <名前> sync` |

読むのはポータル(`scripts/pack.sh serve` → `http://<ホスト>:8899/` の Study Materials)。
