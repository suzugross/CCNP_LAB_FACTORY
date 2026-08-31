# RTCTL-DOJO — 純粋経路制御ラボ問（BL-141）設計メモ

- 起点: 2026-08-23 ユーザ発案。純粋IGP路線（BL-140 方針）と整合。
- 状態: ★★**完成・出題可（2026-08-23）**= `topologies/gen_route_ctrl.py`（GEN-RTCTL）。
  PoC=§9末尾/poc/rtctl・実装結果=§10。
- 確定日: 2026-08-23（確認質問6件への回答で方針確定→同日 PoC・実装・E2E まで完了）。

## 1. コンセプト

単一〜複数ルーティングドメインの基線盤面の上で、**解法制約付きの要件**を満たす
各種リスト（ACL / prefix-list / route-map / offset-list）の**作成と適用**、および
**redistribute 文の投入**だけを解答者が行い、各ルータの RIB を条件どおりに操作する。
道場系（型稽古）に近いが、要件同士が同じルータ・同じプロセス上で衝突する
「それなりに複雑」な構築問。

解答者の実施範囲:
- 各種リストの作成（ゼロから）
- リストの適用（distribute-list / offset-list / route-map 付き redistribute 等）
- **redistribute 文自体も解答者が書く**（基線には含めない）★確定

基線（day0）に含めるもの:
- 基本設定・IF への IP アドレス
- 各ドメイン内の基本ルーティング（隣接は全て up・ドメイン内経路は流通済み）
- redistribute は**未投入**

## 2. 確定事項（2026-08-23 Q&A）

| # | 論点 | 決定 |
|---|------|------|
| 1 | 出題形式 | **(c) 中間形**: 1盤面に Task1..N を段階提示。後の Task が前の Task で作ったリストへの追記・seq 挿入・順序見直しを強いる。採点は最終状態一括 |
| 2 | プロトコル | 主ドメイン= **EIGRP**（IF指定 distribute-list / gateway / offset-list / metric 操作とツールが最豊富）・第2ドメイン= **OSPF**（再配送先）。BGP は範囲外。RIP 第3枝は当面見送り（拡張候補として §8 に記載） |
| 3 | 経路別優先の実現手段 | **seed 抽選で「条件文で解法を縛る」回と「自由（結果のみ採点）」回を切り替える**。縛る回は offset-list 等を明示指定し指紋採点、自由回は RIB の結果一致のみ |
| 4 | redistribute 文 | **解答者が書く**（基線に含めない） |
| 5 | deny禁止/PL1行の意図 | 確認どおり= deny 禁止は**暗黙 deny を活かした permit 列挙**を強いる意図・PL 1行は **ge/le 圧縮**を強いる意図 |
| 6 | ID 体系 | ユーザ「どちらでもよい」→ **新生成器 `topologies/gen_route_ctrl.py`・ID= `GEN-RTCTL-<seed>`** で進める（構築系なので TS 系の GEN-RDFIELD とは分離。ID 秘匿が必要になったら BL-119② 方式へ後日合流可） |

## 3. トポロジ（固定5台 IOL・seed で変えない）

**固定中規模盤面+要件側だけ seed 抽選**（確定）。理由= 実機E2E 1サイクルで全 seed を
信頼できる（リスト道場の実証済み原則「盤面固定・ランダム化は要件側のみ」）／
条件の相互作用には同一プロセス上での衝突が必要／可変最小トポロジだと条件が孤立し
既存道場と変わらない。

```
        RT04 (経路源: Loopback群 = battery)
        /            \
     RT02            RT03      ← 同一 EIGRP AS の並列フィード
        \            /
         RT01 (主戦場・再配送境界 ASBR)
          |
        RT05 (OSPF ドメイン・Lo群あり)
```

- RT01–RT02 / RT01–RT03: 並列2フィード → IF指定 distribute-list・経路別優先
  （ルートAは RT02 経由・ルートBは RT03 経由）の舞台。RT02–RT03 直結リンクは
  **置かない**（定常性・決定性優先。デコイとして欲しくなったら PoC で再検討）。
- RT01–RT05: OSPF。RT01 が唯一の再配送点（redistribute 両方向は解答者が投入）。
- battery 設計方針（実装時に確定）: RT04 側 8〜12 prefix
  （classful 境界ちょうど / 連続ブロック= ge/le 1行圧縮の題材 / 飛び地= permit 列挙の題材）
  ＋ RT05 側 OSPF Lo群 4〜6 prefix（再配送方向フィルタの題材）。
  prefix の値は seed 抽選、**本数と性格（圧縮可能群・飛び地群）は固定**。

## 4. 出題形式(c)の具体化

- task.md に Task1..N を順に提示（例: N=5〜7）。各 Task は要件文＋解法制約
  （制約なし回もある）。
- **Task 間相互作用を必ず1箇所以上仕込む**: 例= Task2 で作った PL に Task5 が
  seq 挿入を強いる／Task1 の ACL に Task4 が行追加を強いる（deny 禁止制約下で
  順序を壊さず足せるか）／Task3 の redistribute route-map に Task6 が節追加。
- 採点は最終状態一括（lab.sh grade）。段階性は提示構造のみで、途中状態は採点しない。

## 5. 要件プール（seed 抽選の母集団・条件例）

ユーザ提示分（全て採用）:
1. distribute-list は **ACL を使ったもののみ可**
2. **RT01 のみ route-map** を使う（他ルータでは別手段を強制）
3. **拒否（deny）エントリ使用不可** → permit 列挙+暗黙 deny
4. **prefix-list 1行**で表現 → ge/le 圧縮
5. **distribute-list out 使用不可** → 受信側 in で同じ結果を作らせる
6. RT02/RT03 から同じルート群が届く時、**ルートAは RT02・ルートBは RT03 を優先**
   （メトリック柔軟操作。縛り回= offset-list in・IF指定／自由回= 結果のみ）
7. **IF 指定の distribute-list**（RT01 の対RT02 IF だけに掛ける 等）
8. **再配送のプロトコル指定**（例: EIGRP 側 `distribute-list <ACL> out ospf 1` で
   OSPF 由来分だけをフィルタ）

追加候補（実装時に取捨・PoC で挙動確認してから）:
- `distribute-list gateway <PL>`（広告元ゲートウェイでのフィルタ）
- prefix-list の seq 指定挿入（Task 間相互作用の道具）
- redistribute route-map の match ip address / set metric（prefix 毎 seed metric）
- `distance <AD> <src> <acl>` による prefix 限定 AD 操作（入れるなら定常性検証必須）

## 6. 解法強制と採点

- 機構は **gen_redist_mp_ts の実証済み監査ポリシーを流用**: 解法の指紋 regex ＋
  他解法禁止 not_regex（`--solution` 4モードで実機実証済み・誤解法混入 90 降格実績）。
- 形式チェック: deny 禁止= `show access-lists`/`show ip prefix-list` に deny 行の
  not_regex／PL 1行= エントリ数 regex／out 禁止= `show ip protocols` の
  distribute-list 表示で判定。
- 結果チェック: `show ip route`（via <IF名> は詳細ビュー・テーブルは via <IP> の
  既知の癖に注意）＋ netmodel 到達性。
- 生成時セルフチェック（道場方式）: 要件の真偽述語で battery を分類した集合と、
  模範解答を意味評価器（acl_model 流用）で適用した集合の一致を assert。
  `--selfcheck N` で seed 一括検品。

## 7. 未決事項 → 初版実装での扱い（2026-08-23）

1. **条件違反時の減点方式**: 既存流儀どおり**チェック配点式の降格**で実装
   （制約チェック 4〜6 点×Task。E2E で誤解法混入= 94 点降格を実証）。
   要件0点方式にしたくなったら効果チェックと制約チェックの抱き合わせに変える。
2. **規模感**: 難易度4・Task 6 本で確定（スケッチ提示時にユーザ「了解です」）。
3. 追加候補: gateway 形は PoC 済みで採用可・distance 系は未採用（v2 候補、§8）。

## 8. 拡張候補（初版に入れない）

- RIP 第3枝（RT05 の先 or RT04 の別枝）→ 3ドメイン化
- 名前/IF/台数の seed 抽選（BL-104 手法）による暗記対策強化
- GEN-RDFIELD への ID 合流（BL-119②）

## 9. 問題文スケッチ（2026-08-23・机上の空論=実機未検証。数値・挙動・一意性は PoC で変わり得る）

battery 仮置き:
- RT04(EIGRP AS100): Lo 172.16.0.0/24〜172.16.3.0/24(連続4本= ge/le 圧縮の題材)・
  10.10.1.0/24, 10.10.5.0/24, 10.10.9.0/24(飛び地3本= permit列挙の題材)・
  192.168.20.0/24, 192.168.40.0/24(除外対象の題材)
- RT05(OSPF 1 Area0): Lo 10.50.1.0/24〜10.50.3.0/24, 172.31.100.0/24

導入文(Cisco語調): 「あなたは○○社のネットワークエンジニアです。図のネットワークは
基本設定が完了しており、EIGRP AS 100 および OSPF プロセス 1 の隣接関係は確立されて
います。再配送はまだ設定されていません。以下のタスクを順番に完了してください。
各タスクには、使用できる手段に関する制約が含まれている場合があります。」

- Task1(deny禁止×permit列挙): RT01 が RT02 から学習する経路から 192.168.20.0/24 と
  192.168.40.0/24 を除外(RT03 側は無影響のこと)。制約= 番号付き標準ACL 10 の
  distribute-list・**deny エントリ禁止**→ 残り7経路の permit 列挙+暗黙denyを強いる。
- Task2(経路別優先): RT01 で 10.10.1.0/24 は RT02 経由・10.10.5.0/24 は RT03 経由。
  **「リンク障害時はもう一方へ切替わること」でフィルタ解を封殺**しメトリック操作を強制。
  縛り回= 「offset-list を該当IFの in に適用して実現」+指紋採点/自由回= 制約文なし・
  結果のみ採点。
- Task3(PL 1行×再配送): RT05 のRIBに 172.16.0.0/24〜172.16.3.0/24 の4経路だけが
  外部経路として現れる。制約= フィルタは **1行の prefix-list**
  (→ 172.16.0.0/22 ge 24 le 24)・route-map 使用は RT01 のみ可。redistribute は解答者が投入。
- Task4(プロトコル指定DL): OSPF 由来の 10.50.1.0/24 と 10.50.2.0/24 だけを EIGRP へ
  再配送(seed metric 指定)。制約= route-map 禁止・**EIGRP 側の
  `distribute-list <ACL> out ospf 1`(プロトコル指定)で実現**。
- Task5(Task間相互作用): 「追加要件が判明」の体で 10.50.3.0/24 も再配送対象に追加。
  制約= Task4 の ACL の**既存エントリを削除・再作成せずに**行を追加。
- Task6(検証・任意): 到達性確認(RT04→10.50.1.1 ping 等)を解答者の確認事項として提示。

★スケッチ時点の未検証リスク4点は **PoC 全通過(2026-08-23・[poc/rtctl/README.md](../../poc/rtctl/README.md))**。
実測の要点= ①`distribute-list <ACL> out ospf 1` は受理・完全動作(connected 随伴
10.0.15.0 も遮断)・表示形= `Redistributed ospf 1 filtered by 20` ②offset-list は
RD にも加算→ **offset ≤ (FD−RD) を生成器が保証**すれば FS 維持=1秒切替
③★Task1 に「トランジット網 permit 忘れ→ 10.0.24.0 が迂回」の隠し罠が実在
(要件文は「除外対象以外に影響を与えないこと」・採点は via 直行を regex)
④DL-in の反映は clear 不要だが約30〜90秒(offset 15秒・redist 側 ACL 追記 8秒)
⑤到達性採点は source 指定 ping 必須 ⑥`distribute-list gateway <PL> in` も
受理・動作確認済→要件プール入り可 ⑦17.15 subnets 暗黙化・ACL/PL/protocols の
採点用表示形は poc/rtctl/README.md の表を正とする。

## 11. v2: バリエーション拡張（BL-143・2026-08-23 ユーザ指摘起点）※§10 の後に読む

★★**v2 実装完了(2026-08-23・同日)**。下記方針のうち採用= ①手段抽選(除外3種/E→O 2種/
O→E 3種/T-pref 2変種×bind・free) ②骨格抽選(T-pref p=0.8・T-add p=0.75・順序シャッフル・
配点 settle) ③§11-6 の pl_shape 5種。**見送り(将来枠)**= gateway DL の T-excl 適用
(「選択的除外」を表現できず文面の再設計が要る)・PL seq 挿入・traceroute 検証形・
除外対象グループ抽選。E2E= 9201/9202(強制変種2本)とも broken 21→100・
selfcheck 500(canonical PL の意味評価一致)。実測表は poc/rtctl/README.md v2 節。

★初出題(PACK-20260823-B・3本連続)でのユーザ評価:「3問とも同じような内容で残念。
タスクの流れも全く一緒。もっとバリエーション豊かに」。初版の「固定6Task骨格+
値抽選のみ」は、**同一パックに複数本入れる出題形態で骨格の同一性が露呈**する。

改修方針（タスクプール化）:

1. **スロット×手段抽選**: 各機能スロットに複数の実現形を持たせ seed で抽選する。
   - 除外フィルタ: {番号ACL DL(deny禁止) / named ACL DL / **prefix-list DL** /
     **gateway DL**(PoC済・広告元で縛る文面)} × 除外対象= {C群 / B群1本+C群1本}
   - 経路別優先: 現行 bind/free ＋「グループ全体を片フィードへ寄せ、特定1本だけ逆」形
   - E→O: {1行PL×route-map(現行) / **OSPF 側 `distribute-list <ACL> out`**(要PoC) /
     route-map 直 match} ＋ metric-type E1 指定の追加要件回
   - O→E: {プロトコル指定 DL(現行・route-map禁止) / **route-map 指定(DL禁止)**=
     現 E2E の「誤解法」の鏡像(採点 regex/not_regex を反転するだけ) / 手段自由}
   - 追記系: {ACL 末尾追記(現行) / **PL の seq 指定挿入**(1行制約を課さない回)}
   - 検証: {source 指定 ping / traceroute の経由確認}
2. **骨格抽選**: プールから 4〜6 本を依存関係(再配送→検証 等)を守って抽選し、
   **順序も依存内でシャッフル**して Task 番号を振り直す。
3. 制約文言の粒度も抽選: {リスト番号まで指定 / 名前だけ指定 / 手段だけ指定 / 完全自由}。
4. ★新規要素(prefix-list DL / OSPF 側 DL out / PL seq 挿入)は**実機1サイクル検証必須**。
   既 PoC 済みの gateway DL・named ACL はそのまま使える。
5. パック側の補助案(任意): gen_pack の複数 pin 時に生成器へ骨格ヒントを渡す口
   (--variant 相当)。ただし生成器単体の抽選幅で実用上足りる見込みが立てばやらない。
6. ★**PL 集合形(pl_shape)の抽選**(2026-08-23 ユーザ追加要望「4連続を/22で指定、を
   覚えてしまう」): A 群の構造自体を抽選し、暗記解「/22 ge 24 le 24」を書くと
   落ちる形を混ぜる。全形で **/22 外の同 /16 デコイ /24 を常設**(過剰 permit 検出)。
   - `quad24`: 4×/24 整列(現行) → `x/22 ge 24 le 24`
   - `pair24`: 4連続 /24 のうち**先頭 2 本だけ**が対象(整列 /23) → `x/23 ge 24 le 24`。
     残り 2 本は同 /22 内の天然デコイ= /22 暗記解を書くと漏れて落ちる
   - `mixed_len`: /22 内に /24,/25,/26 混在・全部対象 → `x/22 ge 24 le 26`
   - `longer_only`: 同混在 battery で **/25・/26 だけ**対象 → `x/22 ge 25`(/24 は遮断)
   - `exact`: 対象は **/22 経路そのもの**(Lo を /22 マスクで広告)+隣接 /22 の
     デコイ /24×2 → `permit x/22`(ge/le なし)。暗記解は対象ゼロで即死
   ★要 PoC: /25・/26・/22 マスク Lo の EIGRP 広告と RT05 での表示形(variably
   subnetted 時は行に /len が付く)・T1 側 ACL の網羅範囲(モデル解は /22+デコイ)。

## 10. 実装順（着手時のプラン）

1. ✅ PoC 完了(2026-08-23・全項目成立・poc/rtctl/README.md)。ラボ撤収済
   (poc/rtctl/poc-rtctl-iol-lab.yaml から再現可)
2. ✅ `topologies/gen_route_ctrl.py` 完成(2026-08-23)。GEN-RTCTL-\<seed\>・
   conventions 準拠(幹線 /30=10.1.xy.0/30・Lo0=x.x.x.x/32 非広告・mgmt slot3)。
   `--mode auto|bind|free`(auto=seed 抽選・強制は乱数列を消費しない=同seed同値)
3. ✅ 監査= 制約指紋(regex/not_regex)+RT01 以外の無改変チェック。`--selfcheck 200` OK
   ★採点実装の教訓= **経路詳細ビューに `via <IP>` は現れない**(via <IF名> のみ。
   next-hop IP は素の contains で見る)。topology 表の `1 Successor` で素の ECMP を
   弾くと T2 が broken 状態で通らない
4. ✅ 実機 E2E(GEN-RTCTL-9102・bind)= **broken 21(事前計算と一致)→模範解答 100
   →誤解法(T4 を route-map 置換・効果同一)94→復元 100**。同盤面のまま
   `--mode free` の採点定義でも 100。検証 seed 掃除済
5. ✅ CATALOG 生成器一覧に1行追記・BL-141 完了アーカイブへ(2026-08-23)。出題時は新seed

## 12. v3 候補: 固定化の解消(BL-151・2026-08-27 ユーザ指摘起点)

契機= 出題4本目でのユーザ指摘2点: ①「deny は使わない」制約が毎回で、**permit 列挙が
反射化し deny を使う素直な設計を思いつかなくなる**(訓練としての害) ②プロセス番号が
毎回同じ(ospf 1 / eigrp 100)。生成器精査(2026-08-27)による固定化の全量は以下。

### A. 制約極性の抽選(本丸・優先=高)

現行: T-excl(3手段とも)と T-add は **deny 禁止(permit 列挙)固定**(生成器 L18
「deny禁止は共通」・L348/354/513 の not_regex deny)。

- 極性 `pol ∈ {permit_only(現行), deny_based}` を seed 抽選(50/50 か 60/40)。
- `deny_based` 回の要件文=「除外の対象を **deny** で指定し、それ以外は包括の permit で
  通過させること。**対象側を列挙する permit は、認められません**」。
  指紋= deny 行×対象(regex)+包括 permit(`permit any` / `permit 0.0.0.0/0 le 32`)
  +not_regex(対象の個別 permit)。
- 教育核心= permit 列挙(増えた正当経路を落とす=閉鎖型)と deny+包括 permit
  (増えた経路を通す=開放型)の**設計選択を要件文から読み取らせる**。解説にこの対比を明記。
- T-add(ACL 追記)にも極性適用: 「既存の deny の手前に挿入」型(seq 挿入の訓練)。
- E2E: 両極性で broken→100 を各1回。一意性= 極性ごとに指紋が排他なので相互の
  誤解法降格(deny_based 回に permit 列挙で解く→制約 FAIL)が自動で立つ。

### B. プロセス/AS 番号の抽選(優先=中・手軽)

- `ospf_pid = randint(1,99)`・`eigrp_as = randint(1,65535)` を v に追加し、
  day0(L302/306)・task 文・**全チェック regex**(「ospf 1」「eigrp 100」がリテラルで
  多数: L342/402/441/449/470/473 ほか)・プロトコル指定 DL `out ospf <pid>` に貫通させる。
- 副次効果= `distribute-list N out ospf <誤pid>` と書くと黙って無効になる実機挙動が、
  番号が毎回変わることで**自然な罠**として機能し始める(採点は正 pid のみ受理)。

### C. その他の固定化(精査の全量・優先=低〜中)

1. **トランジットリンク固定**(L57: 10.1.12.0/30・10.1.13.0/30、NH .2 固定)→
   サブネットを seed 抽選。T1 の「トランジット permit 忘れ→対向へ迂回」罠が
   毎回同じアドレス面なのを解消(中)。
2. **役割↔ホスト名の固定**(RT01=主戦場・RT04=源・RT05=OSPF が既知)→ role→hostname の
   割当を shuffle。「どのルータで作業すべきか」を盤面から読ませる(中。task 文・
   チェック node・監査対象は role 基準で生成しているため名前回転のみで成立するはず)。
3. リスト/route-map 名プールが各4語(L66-69)→ プール拡張か「接頭+用途+方向」合成で
   実質無限化(低)。
4. OFFSETS が 5 値固定(L73)→ FS_MARGIN(25600)未満の randint 化(低)。
5. T6(source 指定 ping)が常設 → 有無 or 対象の抽選を骨格軸に追加(低)。
6. 要件文の言い回しが固定 → 言い換えプール。BL-150(担い手括弧監査)と同時に触るのが
   効率的(低)。

### 実装順の推奨

A → B → C2 → C1 → 残り。A/B だけでも「反射で解ける」構造は大きく崩れる。
E2E は A の両極性×B の番号抽選を1盤面ずつ(計2サイクル)で足りる見込み。

### §12 実装記録(2026-08-27・A+B 完了)

- A(極性)+B(AS/pid 抽選)を実装。**新抽選は rand_values 末尾に追加**し既存 seed の
  先行乱数列を保存(--force に excl_pol/eigrp_as/ospf_pid 追加)。selfcheck 500 通過
  (極性 255/245・順序58パターン維持)。
- **T-add(T5)の極性は設計から除外**: deny_based の o2e ACL に対する T5「削除・再作成せず
  追記」は deny 行の削除を要し制約と衝突。代替= 「既存 deny の手前への seq 挿入」型として
  C 群と一緒に再設計する(残課題)。
- E2E(実機・2026-08-27):
  - seed 880002(deny_based/pl_dl・as=59916/pid=58): broken **21→模範100**。
    さらに permit 列挙(旧 permit_only 模範解)へ差し替え→**96 に降格**(効果は満点のまま
    極性制約のみ FAIL)=反射解の封殺を実証。
  - seed 880016(permit_only/acl_num・rm_pl/rm・as=35176/pid=73): broken **21→100**(回帰)。
  - 検証 seed は teardown・problems/ とも掃除済。
- ACL 表示の注意: 標準 ACL の deny 行は `deny   <net>, wildcard bits <wc>` 形で表示される
  ため deny 指紋は `deny +<net>` で照合(wildcard 部は照合しない)。
