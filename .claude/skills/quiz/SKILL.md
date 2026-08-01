---
name: quiz
description: CCNP問題の出題フロー。ユーザが「問題を出して」「出題して」「◯◯の問題やりたい」等と出題を依頼したら必ずこのスキルに従う。選定→構築→提示→採点→レビュー→記録・撤収までの正準手順。
---

# CCNP 出題フロー

出題依頼が来たら、プロジェクト全体を探索せず **この3ファイルだけ**読んで開始する:

1. このスキル(手順とポリシー)
2. [problems/CATALOG.md](../../../problems/CATALOG.md) — 出題可問題の一覧・variant・固有注意・生成器
3. [problems/_history.md](../../../problems/_history.md) — 出題履歴(重複回避・出題中ラボの把握)

さらに `private/` ディレクトリが存在すれば `private/CATALOG.md` と `private/_history.md`
も読む(git管理外の非公開問題群=PVT系。選定候補に含め、出題記録は `private/_history.md` 側に付ける)。

環境の前提(既知として扱ってよい): CML 10.1.10.10 / vault パスワード `CCNP` / 機器ログイン SUZUKI/CCNP / **ユーザは CML コンソールで直接解く(SSH 不使用・IOSv も出題可)** / CML Personal は同時起動 20 ノード上限。

## 手順

### 1. 選定

- ユーザ指定(分野・難易度・ID)があればそれに従う。指定がなければ **履歴と重複しない難3〜4** から2〜3候補を挙げて提案(難易度は全体的に難しめ好み)。
- **出題言語**: 既定は日本語。「英語で」「in English」等の指定があれば英語出題(手順は「英語出題」節)。指定が曖昧なら日本語で進めてよい(途中からの英語切替も可)。
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
- **英語出題の場合**は上記の task.md を `task.en.md` に置き換えて同じことをする(下の「英語出題」節)。

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

- `_history.md` の行を更新(状態・得点・メモ)。**英語出題した回はメモに `en` を記録**(再出題判断・task.en.md キャッシュ有無の把握用)。
- ユーザに確認のうえ撤収: `scripts/lab.sh teardown <ID>`(特殊ラボは ops の `teardown`/`stop`。**FGT は stop のみ・fgt1 wipe 禁止**)。
- 撤収したら `_history.md` を `撤収済` に更新。

## 英語出題(オンデマンド翻訳)

英語指定の出題では、**採点系・生成器・task.md 原文には一切手を入れず**、提示物だけを英語化する。

### 手順

1. **翻訳元の特定**: `lab.sh provision` がコピーした task.md と同じソースを訳す
   (優先順: `topologies/_generated/<ID>/task.md` → `problems/<ID>/task.md`。GEN 系は生成された `problems/<GEN-ID>/task.md`)。
2. **キャッシュ確認**: 翻訳元と同じディレクトリに `task.en.md` が既にあり、かつ **task.md より新しければ再利用**。
   task.md の方が新しい(params 再生成・問題改修後)なら訳し直す。
3. **翻訳**: 下の翻訳規約に従い Claude が全文翻訳し、翻訳元と同じディレクトリに `task.en.md` として保存(キャッシュ)。
4. **提示**: `task.en.md` を `lab/<ID>/Task.md` にコピーし、**全文をチャットに貼る**＋プレビューリンクは `lab/<ID>/Task.md` を案内
   (日本語版 `問題.md` も lab.sh が置いたまま残る。混乱防止のため案内は英語版のみ)。
   さらに **CML の Lab Notes も英語版へ差し替える**(build が日本語 task.md を埋め込むため):
   `.venv/bin/python3 scripts/set_lab_notes.py <問題ID> <task.en.mdのパス>`(config 無変更・出題中でも安全)。
5. **採点〜レビュー**: 採点コマンドや落ちたチェック名の扱いは通常どおり。**採点後レビュー・降参時の解説も英語**で書く
   (solution.md は日本語のままでよい。訳して見せる)。ユーザが日本語で質問してきたら以後は日本語に切り替えてよい。

### 翻訳規約

- **文体は Cisco 公式に寄せる**: Config Guide / ENARSI・ENCOR OCG / 試験シム問の言い回し。
  「〜を設定しなさい」→ "Configure ...", 「〜を確認」→ "Verify that ...", 「〜禁止」→ "Do not use ... / ... is not allowed"。
- **見出しはシム問体裁**: シナリオ→ "Scenario" / 要件→ "Requirements" / 制約・禁止事項→ "Restrictions" / 採点→ "Scoring" / 構成情報→ "Topology"。
- **識別子は逐語保持**: ホスト名・IP・プレフィックス・VRF名・AS番号・コマンド・インターフェース名・ACL/route-map 名は
  原文のまま一字も変えない(採点 regex との食い違い防止)。
- **要件は1対1対応**: 数値・条件・禁止事項の欠落/追加/意訳での弱化を禁止。訳後に原文と要件数を突き合わせる。
- **用語は試験英語に統一**: 再配送=redistribution / 集約=summarization(BGPは aggregation) / 隣接=adjacency(EIGRPは neighbor) /
  経路=route / 疎通=reachability / 認証=authentication / 冗長化=redundancy / 本社=HQ / 拠点=branch site / 検証網=test segment。

## 守ること

- 問題固有の注意(CATALOG 備考列)を provision 前に必ず読む(例: IOSvL2 は Vlan999 SVI の shut/no shut、EVPN⇔SDA 同時稼働不可)。
- 出題中にトポロジや採点基準の中身(grading.yml・initial/)をチャットに出さない(解法バレ)。
- 新しい問題を作った/検証した時は CATALOG.md に1行追記する。
