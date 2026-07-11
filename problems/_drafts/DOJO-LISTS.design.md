# DOJO-LISTS design — ACL / ip prefix-list / as-path access-list 道場シリーズ

## コンセプト

TS・構築問と毛色を変えた**ドリル(型稽古)問題**。

- 1回の出題で K 個(既定10)の小課題。各課題は「指定の名前/番号のリストを1本書く」だけ。
- 採点は**模範解答との意味的突き合わせ**：書き方(seq番号・同義表現)の自由は認め、
  「何を通し何を落とすか」の一致で得点。1課題 = 100/K 点。
- トポロジは最小(1〜2台・IOL)。provision が軽く、seed でパラメタが変わるので
  **繰り返し稽古**が前提（体で覚える）。
- 学習者がその場で自己確認できる**素振り環境**を同梱する（下記、道場ごとの
  read-only 確認コマンド）。ヒント控えめ方針は維持：確認コマンドは教えるが答えの構文は書かない。

## 共通フレームワーク

- 生成器: `topologies/gen_list_dojo.py --repo . --dojo {prefix,aspath,acl} --seed N [--count K] [--tier {1,2,mix}]`
- 出力: `problems/GEN-DOJO-<DOJO>-<seed>/`（problem.yml / initial/*.cfg.j2 / task.md /
  grading.yml / solution/{solution.md, catalog.json}）— gen_mpls_ts.py と同じ流儀。
- **課題カタログ**: 道場ごとにテンプレ(要件文の雛形＋パラメタ空間＋模範解答生成関数＋
  期待マッチ集合の算出関数)を定義。seed で「どのテンプレを何問・どのパラメタで」を決める。
- **battery(被験対象)は道場ごとに固定**（試験プレフィクス群 / AS_PATH群 / テストパケット群）。
  ランダム化は要件側のみ。→ day0 と実機挙動が不変になり、実機検証1サイクルで
  以後の全seedを信頼できる（期待集合は決定的に計算できるため）。
- 採点: 1課題=grading.yml の1チェック(all-or-nothing)。
  「この構文を使え」系の課題のみ raw regex の形式チェックを併設。
- 完成条件: solve_generated.yml で模範解答投入 → 実機100点（既存規約どおり）。

## Phase 1: GEN-DOJO-PREFIX（ip prefix-list 道場）

**最初に作る**。オンボックス採点で新規評価器が不要＝道場フォーマットの確立に最適。

- トポロジ: `TARGET(RT01, AS65001) --eBGP-- FEEDER(RT02, AS65099)` の2台。
- FEEDER day0: `ip route ... Null0` ＋ network 文で battery 約36 prefix を広告。
  長さ帯 /8〜/32 の代表と **ge/le 境界を刺す**プレフィクスを網羅
  （例: 10.0.0.0/8, 10.10.0.0/16, 10.10.0.0/24, 10.10.1.128/25, …, x/32, 0.0.0.0/0 は別課題用に既定経路も）。
  ※ classful 境界ちょうどの prefix は `show ip bgp` 表示で /len が省略され regex が
  曖昧になるため、battery からは外すか regex を両対応にする。
- 学習者: RT01 上で `PL-01`〜`PL-K` を**定義するだけ**（ネイバー適用は不要）。
- 自己確認 = 採点コマンド: **`show ip bgp prefix-list PL-x`**（read-only でリストを
  BGPテーブルに適用表示。clear 不要・セッション不変）。
- 採点: 各課題 = `show ip bgp prefix-list PL-x` の一致集合 vs 期待集合
  （期待に入る prefix は `regex:`、入らない prefix は `not_contains:` を battery 全件分生成）。
- 課題テンプレ例:
  - 完全一致 permit（`/8ちょうど` ≠ 配下全部、の理解）
  - `le` のみ / `ge` のみ / `ge+le` 帯域指定（例: 10.0.0.0/8 ge 24 le 26）
  - default route のみ（`0.0.0.0/0`）/ 全経路（`0.0.0.0/0 le 32`）の対比
  - /32 全拒否＋他は全許可（deny+permit の順序）
  - `ge 24 le 24`（＝配下の/24固定）
  - seq 番号を指定して既存リストの間に挿入
  - 罠tier2: le < prefix長 がエラーになる境界、permit のみで暗黙deny を踏む構成

## Phase 2: GEN-DOJO-ASPATH（as-path access-list 道場）

Phase 1 の FEEDER 枠組みを流用。

- AS_PATH の合成（FEEDER 1台で多彩なパスを作る）:
  - **中間/先頭AS**: per-prefix outbound route-map の `set as-path prepend` （受信側では
    prepend 列が左端に来る）。
  - **origin AS の可変**: FEEDER のループバック別に複数 eBGP セッションを張り、
    `neighbor ... local-as <X> no-prepend replace-as` でセッションごとに送信元ASを差し替え。
  - `^$` 用に RT01 自身のローカル経路（network 文）も battery に混ぜる。
- 学習者: RT01 で `ip as-path access-list <n>` を定義するだけ。
- 自己確認 = 採点コマンド: **`show ip bgp filter-list <n>`**（read-only）。
  素振り用に `show ip bgp regexp <re>` も task.md で紹介。
- 課題テンプレ例: `^$` / `^X$` / `_X_` / `^X_` / `_X$` / 選択 `_(X|Y)$` /
  prepend 検出 `^X(_X)+` / permit+deny 組合せ（「Xを経由するが Y 発ではない」）/
  `.*`と暗黙denyの理解。`_` のマッチ範囲（行頭行末・空白）を体感させる課題を必ず入れる。
- **先行PoC（リスク項目）**: `local-as no-prepend replace-as` の IOL 挙動と
  `show ip bgp filter-list` の表示形式を実機で先に確認してからカタログ本実装。

## Phase 3: GEN-DOJO-ACL（ACL 道場）

唯一 IOS にオンボックスのテスト手段がないため、**Python 意味評価器**を新設して採点。

- トポロジ: `TARGET(RT01)` ＋ `TGEN(RT02)`（multi-loopback）。TGEN は学習者の
  自己確認用（IFに仮適用→ping→`show access-lists` のヒットカウンタで体感）。
  採点はカウンタ非依存（フレーク回避）。
- 学習者: RT01 上で指定名/番号の ACL を定義。一部課題のみ「指定IFに in 適用」まで要求。
- 採点:
  - `show access-lists <name>` を収集（running-config でなく正規化出力を使う）。
  - 新設 `topologies/acl_model.py`: パース＋テストパケットベクタ
    `{proto, src, dst, sport, dport, tcp_flags, icmp_type}` を first-match＋暗黙deny で評価。
    ワイルドカード（**非連続含む**）・host/any・eq/range/gt/lt/neq・established・
    ポート名⇔番号テーブル（www/telnet/domain/bootps 等）を実装。
  - `grade.py` に新チェック種 `acl_vectors:`（模範と全ベクタ一致で得点）を追加。
  - 単体テスト `test_acl_model.py`（test_netmodel.py の流儀）。
- 課題テンプレ例: 標準番号(1-99) / 拡張番号(100-199) / named standard / named extended /
  host・any の使い分け / ポート演算子各種 / established / icmp type 指定 /
  **非連続ワイルドカードで偶数(奇数)サブネットのみ**（tier2 名物）/
  remark＋seq 挿入 / `ip access-list resequence` / IF 適用＋方向。

## 採点後レビュー（共通UX）

- チェック名を「課題番号: 要件の一言」で生成し、既存の採点レポートだけで
  課題別○×が読める粒度にする。
- 採点後解説（既存方針どおり実機configを読んで）: 不一致だった課題は
  「学習者のリストが通した/落とした差分」を battery 単位で提示し、なぜズレたかを講評。

## 工程・順序

| 順 | 内容 | 主作業 | 完了条件 |
|----|------|--------|----------|
| 1 | GEN-DOJO-PREFIX | gen_list_dojo.py 骨格＋prefixカタログ＋battery設計 | 実機1サイクル100点 |
| 2 | GEN-DOJO-ASPATH | local-as/filter-list PoC → aspathカタログ | 同上 |
| 3 | GEN-DOJO-ACL | acl_model.py＋単体テスト → aclカタログ | 単体テスト全緑＋実機100点 |

リスク: (a) local-as replace-as の IOL 挙動 (b) `show ip bgp` の classful 表示省略
(c) `show access-lists` のポート名正規化 — いずれも各Phase冒頭のPoCで潰す。
