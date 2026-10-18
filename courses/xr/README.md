# courses/xr — XR トラックの読み物(BL-246)

IOS XR を「読み物で学ぶ → ワークスペースで実践する」ための教材の原文。設計は `problems/_drafts/XR-TRACK.design.md`。

- 1 冊の 2 言語の本(`book.yml`)。`en/` が原文(英語)、`ja/` が日本語版で、ページの中のボタンで切り替わる(形の決まりは `courses/README.md`)。1 単元 = 1 ファイル。
- 翻訳ではなく、Cisco の公開文書(コンフィギュレーション ガイド・コマンド リファレンス)と実機(XRv9000 24.3.1)の
  実測をもとに書き下ろしたもの。端末出力はすべて実機から採った。
- 実践編の課題文は `problems/<ラボ ID>/task.en.md`(英語)と `task.md`(日本語)が正本。
  `scripts/course.sh` が単元ごとに切り出して読み物の「Practice」ページにする(ここには置かない= 二重管理を避ける)。
- 手元で読む= 配信サーバのポータル(`scripts/pack.sh serve` → `http://<ホスト>:8899/` の Study Materials)。
  棚は `book.yml` の `shelf:`、学習用ラボへのリンクは `labs:`。ビルドは `scripts/course.sh xr build`。
- 持ち出し= `scripts/course.sh xr sync`(言語ごと・単元ごとに 1 枚に束ねて Drive へ。宛先は `book.yml` の `drive:` の下の `en/`・`ja/`)。

| 単元 | 読み物 | 実践 |
|---|---|---|
| M0 Finding your way | `00-m0-finding-your-way.md` | XRT-01 の M0 |
| M1 Managing configuration | `10-m1-managing-configuration.md` | XRT-01 の M1 |
