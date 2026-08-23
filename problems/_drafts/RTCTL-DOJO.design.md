# RTCTL-DOJO — 純粋経路制御ラボ問（BL-141）設計メモ

- 起点: 2026-08-23 ユーザ発案。純粋IGP路線（BL-140 方針）と整合。
- 状態: **方針確定・実装未着手**（ユーザ指示により着手保留。次回この文書から再開）。
- 確定日: 2026-08-23（確認質問6件への回答で下記を確定）。

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

## 7. 未決事項（次回ユーザに確認）

1. **条件違反時の減点方式**: 既存流儀の降格（90点前後）か、該当要件0点か。
   （前回 Q5 の後半のみ回答済み・この点は未回答）
2. **規模感**: 難易度4・Task 5〜7・所要 60〜90 分の想定で良いか。
3. offset-list / gateway / distance 等の追加候補（§5 後半）の採用範囲。

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

★スケッチ時点の未検証リスク(PoC 必須): `distribute-list out ospf 1` の実挙動と
show 表示形/offset-list IF指定 in の並列フィードでの効き/Task1 の列挙と Task2 の
offset の相互作用/各 Task の解の一意性。

## 10. 実装順（着手時のプラン）

1. PoC: §5 の各条件を IOL 5台の素組みで1つずつ実機確認
   （特に distribute-list out <protocol> の表示形・offset-list IF指定 in の効き方・
   ge/le と `show ip route` 表示の突合）
2. gen_route_ctrl.py 骨格（盤面固定部＋battery 抽選＋要件抽選＋task.md 生成）
3. 監査ポリシー（指紋+not_regex）と selfcheck
4. 実機 E2E（broken→模範解→100・誤解法混入→降格の実証）
5. CATALOG 追記・出題可化
