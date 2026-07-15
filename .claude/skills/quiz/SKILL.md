---
name: quiz
description: CCNP問題の出題フロー。ユーザが「問題を出して」「出題して」「◯◯の問題やりたい」等と出題を依頼したら必ずこのスキルに従う。選定→構築→提示→採点→レビュー→記録・撤収までの正準手順。
---

# CCNP 出題フロー

出題依頼が来たら、プロジェクト全体を探索せず **この3ファイルだけ**読んで開始する:

1. このスキル(手順とポリシー)
2. [problems/CATALOG.md](../../../problems/CATALOG.md) — 出題可問題の一覧・variant・固有注意・生成器
3. [problems/_history.md](../../../problems/_history.md) — 出題履歴(重複回避・出題中ラボの把握)

環境の前提(既知として扱ってよい): CML 10.1.10.10 / vault パスワード `CCNP` / 機器ログイン SUZUKI/CCNP / **ユーザは CML コンソールで直接解く(SSH 不使用・IOSv も出題可)** / CML Personal は同時起動 20 ノード上限。

## 手順

### 1. 選定

- ユーザ指定(分野・難易度・ID)があればそれに従う。指定がなければ **履歴と重複しない難3〜4** から2〜3候補を挙げて提案(難易度は全体的に難しめ好み)。
- **GEN 系は新 seed で新インスタンスを生成**してから出題(既存インスタンスは既出の可能性)。生成コマンドは CATALOG の生成器一覧。
- 台数を確認: 稼働中ラボと合計で 20 ノードを超えるなら、先に teardown を提案。
- パラメータ化問題(params/ あり)の再出題は `gen_params.py --problem <ID> --seed <新N>` で値違いにできる。

### 2. 構築

```bash
scripts/lab.sh status                          # 稼働ラボ・リース確認
scripts/lab.sh provision <ID> [variant]        # 通常問題
```

- **特殊ラボ(CAMPUS/EVPN/SDA/UM2/FGT)は lab.sh ではなく専用 ops CLI**(CATALOG の特殊ラボ表)。build に6〜7分かかるものあり。
- provision 完了時に `_history.md` へ `出題中` で1行追記(GEN は seed、variant も記録)。

### 3. 提示

- **task.md 全文をチャットに貼る** ＋ VSCode プレビューリンク(`lab/<ID>/問題.md`)を添える。
- **ヒントは控えめに**: 落とし穴・使うコマンド・故障箇所のレイヤは先に明かさない。問題文にある情報だけで出題する。
- 接続方法(CML コンソール)と採点依頼の合図(「採点して」)だけ案内する。

### 4. 採点(ユーザが「採点して」と言ったら)

```bash
.venv/bin/ansible-playbook playbooks/grade.yml -e problem=<ID> \
  --vault-password-file <(printf 'CCNP\n')     # variant があれば -e variant=<名>
```

- チェック数が多い問題は2分を超える → Bash の timeout を 600000 に上げて実行。
- 特殊ラボは ops CLI の `grade` サブコマンド。
- 満点でなければ得点と **落ちたチェック名だけ** 伝える(修正方法は聞かれるまで言わない)。再挑戦→再採点は何度でも。

### 5. 採点後レビュー(満点後、または降参時に毎回)

- **実機 config を収集して読み**、「解法レビュー＋補足」を付ける: 技術的な正否・最小解か汎用解か・別解・伸びしろ。
- DMVPN/GRE 系は毎回 `ip mtu` / `ip tcp adjust-mss` の補足を添える。
- 降参時は solution.md を基に解説(その場合も実機の最終状態と突き合わせる)。

### 6. 記録・撤収

- `_history.md` の行を更新(状態・得点・メモ)。
- ユーザに確認のうえ撤収: `scripts/lab.sh teardown <ID>`(特殊ラボは ops の `teardown`/`stop`。**FGT は stop のみ・fgt1 wipe 禁止**)。
- 撤収したら `_history.md` を `撤収済` に更新。

## 守ること

- 問題固有の注意(CATALOG 備考列)を provision 前に必ず読む(例: IOSvL2 は Vlan999 SVI の shut/no shut、EVPN⇔SDA 同時稼働不可)。
- 出題中にトポロジや採点基準の中身(grading.yml・initial/)をチャットに出さない(解法バレ)。
- 新しい問題を作った/検証した時は CATALOG.md に1行追記する。
