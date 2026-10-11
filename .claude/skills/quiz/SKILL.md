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

環境の前提(既知として扱ってよい): CML 10.1.10.10 / vault パスワード `CCNP` / 機器ログイン SUZUKI/CCNP / **ユーザは CML コンソールで直接解く(SSH 不使用・IOSv も出題可)** / CML Personal Plus は同時起動 40 ノード上限(2026-09-27〜・MGMT プールも 40 リース)。

## 手順

### 1. 選定

- ユーザ指定(分野・難易度・ID)があればそれに従う。指定がなければ **履歴と重複しない難3〜4** から2〜3候補を挙げて提案(難易度は全体的に難しめ好み)。
- **出題言語**(2026-10-05・紙面は 2026-10-08 ユーザ指示): **ラボ問も紙面問も英文出題が既定**
  (ラボは「英語出題」節・紙面は「紙面の英語出題」節)。
  「日本語で」と指定された回だけ日本語で出す(途中からの切替も可)。
- **GEN 系は新 seed で新インスタンスを生成**してから出題(既存インスタンスは既出の可能性)。生成コマンドは CATALOG の生成器一覧。
- **「スーパーハード」指定**(BL-210/211): CATALOG の生成器行にある部品オプションを付けて生成する
  (`gen_dmvpn_wreck --hard all` / `gen_dhcp_ts --hard acl_wall` / `gen_redist_field --wall`)。難易度は +1〜2。
  提示は通常どおり task.md のみ(壁の欠陥・囮・偽メモの中身は solution/README.md にあり、採点後レビューまで出さない)。
- 台数を確認: 稼働中ラボと合計で 40 ノードを超えるなら、先に teardown を提案。
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
- **ラボは英文出題が既定**: 上記の task.md を `task.en.md` に置き換えて同じことをする(下の「英語出題」節)。
  日本語指定の回だけ task.md／`問題.md` をそのまま使う。

### 4. 採点(ユーザが「採点して」と言ったら)

```bash
scripts/lab.sh grade <ID> [variant]        # grade.yml を実走＋学習ノルマへ自動記録
```

- チェック数が多い問題は2分を超える → Bash の timeout を 600000 に上げて実行。
- **素の `ansible-playbook playbooks/grade.yml` は使わない**(ノルマ台帳に載らない)。
  どうしても直接叩いた場合は、後から `scripts/quota.sh log lab <ID> --score N --total M` を打つ。
- 特殊ラボは ops CLI の `grade` サブコマンド(記録は上の `quota.sh log lab` を手で打つ)。
- 満点でなければ得点と **落ちたチェック名だけ** 伝える(修正方法は聞かれるまで言わない)。再挑戦→再採点は何度でも。

### 5. 採点後レビュー(満点後、または降参時に毎回)

- **実機 config を収集して読み**、「解法レビュー＋補足」を付ける: 技術的な正否・最小解か汎用解か・別解・伸びしろ。
- DMVPN/GRE 系は毎回 `ip mtu` / `ip tcp adjust-mss` の補足を添える。
- 降参時は solution.md を基に解説(その場合も実機の最終状態と突き合わせる)。

### 6. 記録・撤収

- `_history.md` の行を更新(状態・得点・メモ)。**英語出題した回はメモに `en` を記録**(再出題判断・task.en.md キャッシュ有無の把握用)。
- **学習ノルマ台帳(BL-114)**: 紙面をチャットで採点した回は、正誤が確定した時点で必ず打つ:
  `scripts/quota.sh log paper <紙面ID> ok|ng`(ラボは `lab.sh grade`・パック採点が自動で記録するので不要)。
  出力に当日の残ノルマが出るので、そのままユーザに伝える。
- ユーザに確認のうえ撤収: `scripts/lab.sh teardown <ID>`(特殊ラボは ops の `teardown`/`stop`。**FGT は stop のみ・fgt1 wipe 禁止**)。
- 撤収したら `_history.md` を `撤収済` に更新。

## 問題パック(連続出題・BL-099)

「5問まとめて」「明日ぶんを用意して」等、**複数問を一度に**求められたらこちらを使う
(1問だけなら上の通常フローのまま)。想定運用は**夜間バッチ**: 就寝前に作成 → 翌朝から1日で解く。

```bash
scripts/pack.sh new [--packs 3] [--lab 2] [--budget 20]   # 作成(15〜25分・nohup 推奨)
#   ★既定は **1回で3パック**(BL-205・2026-09-20)。1パック= 思考系 2 ＋ 瞬発力 3(--speed)
#     ＋ 穴埋め 2(--cloze)= 紙面7問(2026-09-28・旧 18問)。**ラボ 3 は1本目にだけ**付く(CML 予算は1日ぶん共通)。ラボは**単元ローテーション**(BL-223・曜日表＋遅れ補正・`topologies/lab_modes.yml`)、紙面も**単元ローテーション**(BL-224・全単元を最終実施日の古い順・資格で絞らない)で選ぶ。
#     配分は1日全体で決める= 必須ジャンルを3本へ配り分け(--profile/--require-shape 明示時のみ・1本2ジャンル)・既出 kind は後続から除外。
#     単発に戻すなら `--packs 1`。
scripts/pack.sh serve                                     # 配信(Windows ブラウザから開く)。ラボのワークスペース(8897)も一緒に上がる
scripts/pack.sh status --today                            # 今日の3パックの進捗(個別は status <PACK-ID>)
scripts/pack.sh grade  --today --no-lab                   # ①今日の全パックの紙面を即採点
scripts/pack.sh grade  <PACK-ID>                          # ②ラボ込み採点(ラボがあるのは1本目)
scripts/pack.sh grade  <PACK-ID> --no 3                   # 再挑戦した 1 問(Q3)のラボだけ再採点
scripts/pack.sh replace <PACK-ID> --no 5                  # 1問だけ差し替え
scripts/pack.sh close  --today                            # 全ラボ撤収
```

- **提示は3本まとめて**: 3パックぶんの URL を並べて伝える(2本目以降のIDは `-B` / `-C`)。
  1日のノルマ(紙面10問)は1本目だけでほぼ満たせるので、**2・3本目は「まだ解ける余力がある時に」**と添える。
- 成果物は `packs/<PACK-ID>/`(gitignore)。**問題文は HTML**、解答はページ下部の解答欄に
  書くと `解答.md` に保存される(`serve` 経由のときのみ。`file://` では直接編集)。
- **画面の枠は英語・ナビ帯は下端**(BL-236・2026-10-07): 目次・ナビ・解答欄・ストップウォッチ・保存表示は英語で出る
  (`解答.md` の書式= `状態:`/`解答:`/`根拠:`/`メモ:` は日本語のまま。採点が読むので変えない)。
  目次・問番号のナビ帯は**画面の下端に固定**(上にあるとワークスペースのタブと押し間違える)。
- **ラボは最初からワークスペースで開く**(BL-234/236): 目次・ナビ帯のラボの問番号は、そのまま
  上= タスク/トポロジ(タブ)・下= 機器コンソール(機器ごとのタブ)の 1 画面を開く(既定は上下。画面下端の帯の右端で
  左右にも切替・境目はドラッグで可変。`topologies/lab_console.py`・
  `serve` が同時に起動・ポート 8897。VSCode 転送で開く時は 8897 も転送)。問番号を押すと画面ごとその問題へ切り替わる
  (前の問題のコンソール画面は閉じる。機器の状態はそのまま。別タブで並べたい時は Ctrl+クリック)。
  ワークスペースが上がっていない時は、単体の問題ページ(全文)に落ちる。
  コンソールは CML のコンソールと**共有**(同じ画面が映る)なので、採点はユーザの操作が止まってから走らせる。
  問題文の盤面の節(トポロジ／構成図)は、ワークスペースでは Task でなく **Topology タブ**(結線図の下)に出る。
  リンクが無い旧パックは `scripts/pack.sh render <PACK-ID>` で付く。
- **提示は index.html の URL を伝える**(`http://10.1.10.6:8899/<PACK-ID>/index.html`。VSCode の転送越しなら
  `http://localhost:8899/…` でも可。2026-09-21 から serve は LAN に bind)。
  task.md 全文貼りは不要(HTML が問題用紙そのもの)。
- **選定方針(ユーザ指示)**: 純粋な Cisco 問題のみ・**ラボは TS 中心**。
  他ベンダ機/Linux サーバ構築/自動化(Ansible・RESTCONF 等。**EEM は含めない**= 出題対象・2026-10-07)は既定で除外(`--allow-non-cisco` / `--allow-automation` /
  `--any-lab` で解除)。外部機器が単なる観測機(Zabbix 等)なら可。
  **学習目的のラボ**(手順に沿って効果を体感する演習。測定手順・記録表・考察つき= QoS 体感シリーズ等)も既定で除外
  (2026-10-11 ユーザ指示「学習目的のラボはパックに入れない」)。印は CATALOG のタグ `tutorial`。名指し(`--lab-id`)は通る・
  まとめて解除は `--allow-tutorial`。新しく体感型の問題を作った時は CATALOG の行にこのタグを付ける。
- **発掘枠(BL-233・2026-10-06)**: ラボ 3 本のうち 1 本は、単元ローテーションが引けない資産(登録外の生成器・静的問題)
  から**最後に出した日が古い順**に選ぶ(生成器と静的を日替わりで交互・同じ日の中だけ乱数)。静的問題は構築問が多いので、
  その日は単元側の構築スロットを使わない(構築は 1 日最大 1 本)。待ち行列と対象外の理由は
  `python3 topologies/lab_rotation.py [--all]`、保留の解除は `topologies/lab_modes.yml` の `discovery.hold`、
  無効化は `--discovery 0`。設計= LAB-ROTATION.design.md §8。
- 台数は **CML に問い合わせて実測**する(リース台帳では手組みラボを取りこぼす)。
- **答え合わせボタン(BL-212・2026-09-21)**: 紙面の各ページに「答え合わせ」がある。押すと**その時点の解答で確定**し、
  正誤だけを緑/赤で表示して入力をロックする(正解の記号・解説は出さない= 解説は採点後の report.html のまま)。
  確定した解答が `解答:` として残るので、採点・ノルマ集計はこれまでどおり(初回解答だけ集計)。serve 経由のときだけ動く。
- **採点は 2 段階**: ①`grade --no-lab` で紙面だけ先に採点する。これで
  **解説ページ `packs/<PACK-ID>/report.html`** が書かれ、`index.html` 最上部にリンクが入る。
  ★**紙面は誤答があっても初回採点で全問の正答と解説を出す**(2026-09-20 ユーザ指示で恒久変更。
  旧運用= 誤答があるうちは正解率と問番号だけ)。チャットには**正答率・誤答の問番号・気づいた傾向**を
  短く書き、詳細は解説ページへ誘導する(全文をチャットに貼り直さない)。
  ②同時に `grade <PACK-ID>` を `run_in_background` で実走(ラボ 1 本あたり数分・timeout 600000)し、完了通知後に
  ラボの点数・未充足チェック名・解法レビューを追って報告する。紙面の再採点は dedupe されるので 2 度走って問題ない。
  **ラボの正解 config は従来どおり求められてから**(解説ページにも載せない)。
- **パックのラボも英文で出す**(2026-10-05): `pack.sh new` の完了後、提示の前に、ラボ各問について「英語出題」節の
  手順 1〜4(翻訳 → `lab/<ID>/Task.md` → Lab Notes 差し替え)を行い、最後に `scripts/pack.sh render <PACK-ID>` で
  ページを作り直す(`Task.md` があるラボは英語版が描画される)。`replace`/`redeploy` で
  ラボを入れ替えた時も同じ。CML キャンバスの要約注釈はパックでは貼られない(`LAB_TASK_ANNOTATION=off`)。
- **パックの紙面も英文で出す**(2026-10-08): `pack.sh new` の完了後、提示の前に「紙面の英語出題」節の手順で
  全パックの紙面を訳し、`scripts/pack.sh en --today` が全問 OK になってから `scripts/pack.sh render --today` で
  ページを作り直す。**URL を伝えるのはその後**(訳す前のページは日本語で出ている)。
- ラボ採点・レビューは通常フローと同じ(`grade.yml` を実走し、実機 config を読んでレビュー)。
  **`_history.md` のメモ欄はパックが自動で埋めない**(空欄のときだけ定型文を入れる)。
  レビュー内容は従来どおり Claude が書く。
- 詳細設計: [QUIZ-PACK.design.md](../../../problems/_drafts/QUIZ-PACK.design.md)

## 英語出題(オンデマンド翻訳・ラボの既定)

**ラボ問は英文出題が既定**(2026-10-05〜)。**採点系・生成器・task.md 原文には一切手を入れず**、提示物だけを英語化する。

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
5. **採点〜レビュー**: 採点コマンドや落ちたチェック名の扱いは通常どおり。**採点後レビュー・降参時の解説は日本語**で書く
   (英文なのは問題文だけ。チャット出力は日本語という CLAUDE.md の規則が優先)。
   ユーザが「レビューも英語で」と明示した回だけ英語で書く(solution.md は日本語のままでよい。訳して見せる)。

### 翻訳規約

- **文体は Cisco 公式に寄せる**: Config Guide / ENARSI・ENCOR OCG / 試験シム問の言い回し。
  「〜を設定しなさい」→ "Configure ...", 「〜を確認」→ "Verify that ...", 「〜禁止」→ "Do not use ... / ... is not allowed"。
- **見出しはシム問体裁**: シナリオ→ "Scenario" / 要件→ "Requirements" / 制約・禁止事項→ "Restrictions" / 採点→ "Scoring" / 構成情報→ "Topology"。
  ★盤面の節(トポロジ／構成図)の見出しには必ず **Topology** を入れる("Topology" / "Topology (Physical)" 等)。
  ラボのワークスペースはこの見出しを鍵に、節を Task タブから Topology タブへ移す(BL-234。外れると Task 側に残るだけで欠落はしない)。
- **識別子は逐語保持**: ホスト名・IP・プレフィックス・VRF名・AS番号・コマンド・インターフェース名・ACL/route-map 名は
  原文のまま一字も変えない(採点 regex との食い違い防止)。
- **要件は1対1対応**: 数値・条件・禁止事項の欠落/追加/意訳での弱化を禁止。訳後に原文と要件数を突き合わせる。
- **用語は試験英語に統一**: 再配送=redistribution / 集約=summarization(BGPは aggregation) / 隣接=adjacency(EIGRPは neighbor) /
  経路=route / 疎通=reachability / 認証=authentication / 冗長化=redundancy / 本社=HQ / 拠点=branch site / 検証網=test segment。

## 紙面の英語出題(オンデマンド翻訳・紙面の既定)

**紙面問も英文出題が既定**(2026-10-08〜)。ラボと同じく**提示物だけ**を英語にする。生成器・原文
(`questions/<ID>.md`)・正解キー(`answers/`)・採点・`解答.md` の書式には一切手を入れない。
解説ページ(report.html)は、問題文の再掲だけが出した版(英語)になり、**解説は日本語のまま**。

### 手順

```bash
scripts/pack.sh en --today            # 紙面ごとの状態: 未訳 / 要修正(食い違いの中身つき) / OK。全部 OK で rc=0
scripts/pack.sh render --today        # 訳文を置いたらページを作り直す(英語版で出せた問数が出る)
scripts/pack.sh render <PACK-ID> --paper-lang ja   # 「日本語で」の回: そのパックの紙面を原文に戻す(en で英語へ)
```

1. **置き場**: 訳文は原文の隣の `en/` に同じ名前で置く(`questions/20261008-001.md` → `questions/en/20261008-001.md`。
   別置きプールの紙面も同じ規則= `<原文のディレクトリ>/en/`)。`pack.sh en` が行ごとに置き場を出す。
2. **訳す**: 下の規約に従い Claude が全文を訳す。★**読むのは原文だけ。`answers/` は開かない**(正解を知って訳すと、
   正解の肢だけ言い回しが精密になる)。show 出力・config が長い問題は、原文を `en/` へコピーしてから
   日本語の行だけを置き換える(コードブロックを打ち直さない)。
3. **照合**: `pack.sh en` が原文と機械照合する(`topologies/paper_en.py`)。**通らない訳文は描画に使われず、その問は
   日本語のまま出る**(解けない・誤採点になる訳文を出さない安全側の作り)。食い違いが出たら訳文を直す
   (原文は直さない)。照合が見るのは下の「変えてはいけないもの」だけで、訳の良し悪しは見ない。
4. **1 問だけ紙面を出す回**(パック外)も同じ: 訳文を `en/` に置き、`.venv/bin/python3 topologies/paper_en.py <原文>` が
   OK になってから、英語版をチャットに貼って出す。採点・`quota.sh log paper` は従来どおり。

### 変えてはいけないもの(照合が落とす)

- **解答欄の形を決める目印**は下の表の英語に固定する(描画と解答欄はこの語を鍵に読む)。

  | 原文 | 訳文 |
  |---|---|
  | `# 問題 <ID>` | `# Question <ID>` |
  | `> **本問は機器に接続せずに解答すること。…**` | `> **Answer this question without connecting to any device. No additional show commands may be run.**` |
  | `## 設問` ／ `## 選択肢` | `## Question` ／ `## Choices` |
  | `(1つを選択してください)` ／ `2 つ選択してください` | `(Choose one.)` ／ `(Choose two.)`(個数は必ず括弧つきで文末に) |
  | `すべて選んでください`(数非明示) | `(Choose all that apply.)` |
  | `### 対応させる項目`(組合せ形の表) | `### Items to Match` |
  | 空欄 `［①］` | そのまま写す(全角の角括弧＋丸数字。番号は同じ概念に付けたまま)。★半角の `[①]` にすると空欄として読めない |
  | 穴埋め形の指示文(定型) | `For each of the blanks ① through ⑥ in the following explanation (which includes a configuration example), select one term from choices A through J below. No term is used in two blanks. The choices include terms that do not fit any of the blanks.` |
  | 組合せ形の指示文(型) | `… match each of the commands ① through ④ on the left with one of A through D on the right.`(語群も見出しは `## Choices`) |

  それ以外の見出し: シナリオ= Scenario / トポロジ= Topology / 要件= Requirements / 現在の状態= Current State /
  設定抜粋= Configuration Excerpt / 出力= Output / 解答の表= Answer Table / ルータのアドレス= Router Addresses。
- **選択肢の記号と順序**は原文どおり(入れ替えない・統合しない)。正解キーも解説も記号で指している。
- **コードブロック**: 数と行数を変えない。日本語を含まない行(show 出力・config・図の配線)は一字一句そのまま。
  日本語を含む行(図のラベル・`(出力なし)`・説明の行)だけを訳し、その行の識別子は残す。
- **識別子は逐語保持**: ホスト名・アドレス・プレフィックス・IF 名・AS 番号・タイマ値・コマンド・インラインコード。
  **数は数字のまま**書く(`30 seconds`。thirty と綴らない)。1 桁の数だけは綴ってよい(two routers / the third octet)。
  コマンドのキーワードは地の文に溶かさない(「passive-interface に設定されている」→ `is configured as passive-interface`。
  a passive interface と書かない。数字を含まない語は照合で拾えないので、訳す側が守る)。
- **骨組み**: 見出しの階層・表の行と列・番号付きの要件の数・箇条書きの数を変えない(要件は 1 対 1)。
- **日本語を残さない**(全角の括弧・読点・中黒も半角へ。**例外は空欄の `［ ］` だけ**)。

### 変えてはいけないもの(照合では見えない= 訳す側が守る)

- **情報を足さない・削らない・強めない・弱めない**。原文が冗長でも要件が重複していても、そのまま訳す
  (紙面の読みにくさは仕様。整理して読みやすくしない)。原文が明示していない前提・主語・理由を補わない
  (未提示の前提から消去法で解かせる問題が、補った一語で割れる)。
- **二通りに読める英文を作らない**: 訳した結果、原文に無い読みが生まれていないかを肢ごとに確かめる
  (2026-10-08 実例: 「reload を伴って構成を置き換える」を `replaces the configuration with a reload` と訳すと、
  replace A with B の型で「構成を reload に置き換える」とも読める。`…, and the replacement involves a reload` のように書く)。
- **選択肢の粒度をそろえる**: 正解らしい肢だけ長く・具体的にしない。原文で同じ語は訳文でも同じ語にする
  (肢ごとに言い換えると、言い換えの差が手がかりになる)。
- **穴埋め形**: 空欄に語群のどの語を入れても**文法が通る**ように文を組む(品詞・語形で正解が割れないように)。
  語群は固有の表記を除き**小文字始まり**でそろえる(文頭用・表用の大文字で入る場所が割れる)。
  英語の語順で空欄の出現順が変わるのはよい(番号は概念に付けたまま)。

### 文体(CCIE ラボ対策書の文体をモチーフにする・2026-10-08 ユーザ指示)

手本は CCIE のラボ対策書(ワークブック)の**タスク文と解説の地の文**。言い回しの実例は、あれば
`private/PAPER-EN-STYLE.md`(出典つきの抜粋・非公開)を読む。要点:

| 問題の部分 | 書き方 |
|---|---|
| シナリオ・現在の状態 | 平叙の現在形で短く事実を並べる。障害の報告はチケットの型: `R1 is configured to …. However, …` / `R4 can't reach R1's Lo0.` / `… should …, but it does not.` |
| 要件・条件 | タスク文の型。命令形 `Configure …` / 目的は `Ensure that …` / 状態は `… should be …`・`… must …` / 禁止は `Do not …`・`You should not …` / 条件の列挙は `based on the following policy:` / 手段の制限は `… to accomplish this task.` / 対象をぼかす時は `the appropriate router/s such that …` |
| 設問 | Cisco の試験の型: `Which statement about … is true?` / `Which two statements … are true? (Choose two.)` / `Which route/s are installed … if … is configured?`。原文が 1 文に条件を畳み込んでいる時は `Given that …, that …, and that …, which …?` で 1 文のまま訳す |
| 選択肢 | 完結した平叙文(ピリオドで終える)。語句だけの肢は語句のまま |
| 穴埋めの説明文 | 解説の地の文の型。現在形で、出力や構成を指して言う: `Notice that …` / `This is because …` / `As a result, …` / `In this case, …` / `In other words, …` / `Recall that …` / `Keep in mind that …` / `If this configuration is performed successfully, … should …` |

- **機器と IF の指し方**: `the G0/1 interface of R2` / `R2's Lo0` / `the Loopback0 interfaces of these routers` /
  `network 10.1.1.0/24` / `the 7.7.7.7/32 prefix` / 並列は `…, respectively`。
- **用語は試験英語に統一**(ラボの翻訳規約と同じ表): redistribution / summarization(BGP は aggregation) /
  adjacency(EIGRP は neighbor) / route / reachability / next hop / administrative distance。
  装飾語(simply, just, easily)と推量(probably, seems)は足さない。

## 学習ノルマ(BL-114)

1日のノルマは **紙面10問・ラボ3問(3ジャンル以上に分散)**。1日の境界は **JST 04:00**
(深夜に解いた分は前日に計上)。ノルマ値は `records/quota.yml`、ジャンル定義は `records/genres.yml`。

```bash
scripts/quota.sh                       # 当日の進捗(残り問数・未消化ジャンル)
scripts/quota.sh report --days 30      # 期間集計(--out で HTML)
```

- 記録の正準は `records/attempts.jsonl`(追記専用・PVT系は `private/attempts.jsonl`)。
  **_history.md はノルマ計数に使わない**(叙述用・書き換えが起きるため)。
- **出題の選定にノルマを使う**: 未消化ジャンルが残っていれば、指定が無い限りそこから優先して選ぶ。
- ラボは**満点でノルマ1問**として数える(途中点は「挑戦中」表示)。紙面は正誤を問わず1問。
- **紙面の正答率は初回の解答だけで集計する**(2026-09-19 ユーザ指示・quota.py dedupe)。再挑戦→再採点で正解になっても正答には入れない(問数は 1 のまま)。ラボは最後の結果。

## 守ること

- 問題固有の注意(CATALOG 備考列)を provision 前に必ず読む(例: IOSvL2 は Vlan999 SVI の shut/no shut、EVPN⇔SDA 同時稼働不可)。
- 出題中にトポロジや採点基準の中身(grading.yml・initial/)をチャットに出さない(解法バレ)。
- 新しい問題を作った/検証した時は CATALOG.md に1行追記する。
