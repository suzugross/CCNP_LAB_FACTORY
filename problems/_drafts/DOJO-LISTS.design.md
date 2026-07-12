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

## 実装記録 — Phase 1 完了（BL-012・2026-07-12）

`topologies/gen_list_dojo.py` として実装。**実機フルサイクル済**
（seed=101 mix: 0点発射 0/100 → solve_generated → **100/100 一発収束**・
(前提)0点チェックで battery 36経路受信も PASS 確認）。検証 seed は掃除済み。

### 確定した構造（Phase 2/3 も流用する）

- battery 36経路 = 35 static Null0 + network 文 ＋ `default-originate`。
  リンクは 10.1.12.0/30（battery と衝突しない帯を厳守）。
- 課題テンプレ10種: EXACT / LE / GE / BAND / DEFAULT / ANY / HOSTBLOCK /
  FIX24 / EXCEPT（deny 先行の順序稽古）/ SEQ（挿入・形式チェック）。
  tier1=EXACT,LE,GE,DEFAULT,ANY / tier2=残り。`--tier {1,2,mix}` で選抜、
  必修テンプレ→残り抽選（テンプレ毎 cap）で多様性を担保。
- **生成時セルフチェック**が要: 各課題で「要件述語で battery を分類した集合」==
  「模範解答を prefix-list 意味評価器(first-match+暗黙deny+ge/le)で適用した集合」
  を assert。`--selfcheck 300`（=900生成）で三者矛盾ゼロを常時検品できる。
- 机上 regex 検証（モック show 出力）は「1経路欠け」「除外1経路混入」
  「permit any 誤答」「未定義」の4誤答パターンまで通すと実機一発が狙える。

### 実機知見（IOL iol-xe 17.15）

1. **classful 境界の /len 省略は実在**: `10.0.0.0`(/8)・`0.0.0.0`(/0)・
   `172.2x.0.0`(/16)・`192.168.10x.0`(/24) → 包含/除外 regex とも
   `(/8)?` 式の両対応が必須（設計時の懸念どおり）。
2. **Network 列 17桁超（18桁 /25 等）は折返し表示**
   （prefix 単独行→next-hop が次行）。regex の後方境界を `\s`（改行含む）に
   しておけば折返し/同一行の両方を吸収できる。17桁ちょうどは同一行。
3. **未定義リストへの `show ip bgp prefix-list PL-x` は無言の空出力**
   （%エラー文なし）。包含 regex が必ず不成立になるので 0点発射が自然成立。
4. `show ip prefix-list PL-x` は `ip prefix-list PL-x: N entries` +
   `   seq NN permit A/L` 形式（/len 常時明示）→ SEQ 課題の形式チェックは
   `N entries`＋各 seq 行 regex で「再採番・余計な行」まで拒否できる。
5. **solve_generated.yml の互換形式**: solution.json は**パック直下**・
   filters は `[{node, blocks: [{parents, lines}]}]`（blocks 必須。
   nodes:{} なら OSPF 投入プレイは自動スキップ＝道場はフィルタのみで可）。

### Phase 2 (BL-013) への申し送り

- feeder/リンク/採番/選抜/セルフチェックの骨格は gen_list_dojo.py に
  `--dojo aspath` を足す形で流用（意味評価器を AS_PATH regex 版に差し替え）。
- 先行PoC 必須のまま: `neighbor ... local-as X no-prepend replace-as` の
  IOL 挙動と `show ip bgp filter-list` の表示形式。

## 実装記録 — Phase 2 完了（BL-013・2026-07-12）

gen_list_dojo.py を2道場対応に再構成し `--dojo aspath` を追加。**実機フルサイクル済**
（seed=202 mix: 0点発射 0/100 → solve_generated → **100/100 収束**）。検証 seed 掃除済。

### AS_PATH 合成の確定構成（設計どおり成立）

- **並列 eBGP 4セッション**を RT01-RT02 間に張る: 直結（素の AS65099）＋
  loopback 間×3（RT02 側 `local-as 65010/65020/65030 no-prepend replace-as`・
  両側 `update-source LoX`＋`ebgp-multihop 2`・相互 /32 static）。
- **セッション別 outbound route-map**: 担当 battery のみ permit
  （match ip prefix-list）＋ `set as-path prepend <中間..起源>`。
  暗黙 deny が「他セッションの battery」と「RT01 経路の折返し」を同時に遮断する。
- battery 19経路（S0:5 / S1:5 / S2:4 / S3:5・path 先頭=セッションAS を生成器で assert）
  ＋ RT01 ローカル2経路（`^$` 用・network 文＋Null0 static）= 21経路固定。
- 課題9テンプレ: A_LOCAL(`^$`) / A_ORIGINDIRECT(`^X$`) / A_VIA(`_X_`) /
  A_FROMNBR(`^X_`) / A_ORIGIN(`_X$`) / A_EITHER(`_(X|Y)$`) /
  A_PREPEND(`^X(_X)+$`) / A_VIANOTORIGIN(deny `_X$`+permit `_X_`) /
  A_NOTFROM(deny `^X_`+permit `.*`)。ACL 番号=課題番号。
- 意味評価器: Cisco regex の `_` を `(?:^|$| )` に翻訳して空白区切りパス文字列に
  first-match 適用（battery は confed 無しなので ,{}() は不要）。

### 実機知見（IOL-XE 17.15・PoC 2026-07-12）

1. **`local-as X no-prepend replace-as` は完全動作**。受信パスは全19経路が
   設計値と一致（leftmost=セッションAS・実AS 65099 は完全隠蔽・prepend 合成も正確）。
2. **未定義 ACL への `show ip bgp filter-list N` は
   「% N is not a valid AS-path access-list number」エラー**（全表示にはならない）
   → 包含 regex が必ず不成立で 0点発射が自然成立。
   定義済みでマッチ0件は無言の空出力（prefix-list 道場と同じ）。
3. **class C 空間（198.18.x.0/24 等）の /24 も classful 省略表示**
   → disp_rx の dual regex（`(/24)?`）が battery 全域で必須。
4. **solve 直後の filter-list 採点は1〜2試行分の一過性 FAIL がありうる**
   （BGP filter-list cache 形成待ちとみられる。実測: 3試行目で全PASS収束
   = grade.yml の再試行設計の範囲内・出題運用に支障なし）。
5. 設計上の保険: aspath 道場は「全許可」課題を作らない
   （除外集合非空を assert）。仮に未定義 ACL が全表示になる版があっても
   誤 PASS しない。
6. セッション確立直後（〜1分）は PfxRcd=0 のことがある（広告は確立から
   数十秒遅れ）。(前提) 0点チェック= summary の4行 regex（AS と PfxRcd 拘束）が
   そのまま収束シグナルになる。

### Phase 3 (BL-014, ACL 道場) への申し送り

- 残りは acl_model.py（テストパケットベクタ意味評価器）＋ grade.py の新チェック種
  `acl_vectors:` ＋単体テスト（test_netmodel.py の流儀）。道場の選抜/セルフチェック/
  出力骨格は gen_list_dojo.py に `--dojo acl` を足す形で流用可。
- 採点は `show access-lists <name>` の正規化出力をパース（running-config 不使用）。
  TGEN ルータ（multi-loopback）は自己確認専用でカウンタ非依存。

## 実装記録 — Phase 3 完了・シリーズ完結（BL-014・2026-07-12）

**実機フルサイクル済**（seed=303 mix: 0点発射 0/100 → solve_generated →
**100/100 一発収束**）。検証 seed 掃除済。これで prefix / aspath / acl の
**フィルタ道場3部作が全て出題可**。

### 確定した構成

- 新規エンジン `topologies/acl_model.py`:
  - パーサ: `show access-lists` の正規化出力 → ACL モデル。
    標準（裸ホスト IP・「A, wildcard bits W」）/ 拡張（host/any・eq/neq/gt/lt/range・
    established・icmp タイプ名）・"(N matches)"/"log" 除去・**seq でソートして評価**
    （標準 ACL のハッシュ順表示対策）。
  - 評価器: ベクタ {proto, src, dst, sport, dport, established, icmp_type} を
    first-match＋暗黙deny で判定。ワイルドカードは XOR&~wild のビット演算＝
    **非連続ワイルドカード対応**。ポート名⇔番号テーブル（www/telnet/domain/
    bootps/tftp/syslog/ntp 等）・icmp タイプ名テーブル同梱。
  - 単体テスト `test_acl_model.py`（33 アサート・実機不要で全緑）。
- grade.py に新チェック種 **`acl_vectors:`**（{"acl": 名前, "vectors": [ベクタ+expect]}）。
  raw / match と AND 併用可（ODD 課題の形式チェック・APPLY 課題で使用）。
- 道場: `--dojo acl`。RT01(TARGET)+RT02(TGEN・テスト送信元 loopback×10)。
  **固定ベクタ battery 26本** × テンプレ11種:
  STD_NET / STD_HOSTDENY / NAMED_STD / EXT_HTTP / NAMED_EXT_BLOCK（tier1）、
  EST / ICMP / RANGE / **ODD（非連続 WC 奇数・偶数=名物。「1行」は
  `A, wildcard bits 0.0.254.255` の raw regex で形式拘束）** / NEQ /
  **APPLY（定義＋IF 適用。acl_vectors 5点＋ `show ip interface` raw 5点の
  2チェック分割）**（tier2）。
- ACL 識別子は課題番号から決定的に採番: 標準番号=10+k / 拡張番号=100+k /
  named=DOJO-k（種別稽古のため課題文で種別を明示指定）。
- セルフチェックは他道場と同型:「要件述語でベクタを分類」==「模範解答を
  acl_model.evaluate で分類」を assert（評価器自体の正しさは単体テストが担保）。
  机上検証は grade.py evaluate 経由で「未定義 / 先頭 action 反転 /
  permit any 手抜き」の誤答3種が全課題 FAIL になることまで確認してから実機へ。

### 実機知見（IOL-XE 17.15・2026-07-12）

1. `show access-lists` の表示は**設計想定どおり一発適合**:
   既知ポートは名前化（`eq www` / `neq domain` / `eq telnet`）、icmp タイプも
   名前化（`echo` / `echo-reply`）、標準はサブネット「A, wildcard bits W」・
   ホスト裸 IP、named/番号とも `10 permit ...` の seq 付き。パーサ修正ゼロ。
2. `ip access-group <named> in` を含む模範解答ブロック（named 定義→IF 適用の
   blocks 順序）は solve_generated.yml でそのまま投入できる。
3. 未定義 ACL への `show access-lists <id>` は**無言の空出力** →
   acl_vectors が「ACL が存在しない」で FAIL＝0点発射自然成立。

### シリーズ総括（今後の拡張余地）

- カタログ追加はテンプレ関数を1つ足すだけ（remark / resequence /
  time-range / IPv6 ACL 等が候補）。battery を変えたら実機1サイクル再検証。
- acl_model.py は道場専用でなく汎用（既存 ACL 問題の採点強化・TS 生成器の
  ACL 故障注入の期待値計算にも流用可）。
