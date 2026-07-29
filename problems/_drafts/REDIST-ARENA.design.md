# REDIST-ARENA — トポロジ抽選型・再配送ルーティングループ生成器 (BL-074)

- 起点: 2026-07-29 ユーザ要望「いろんなパターンのトポロジーの再配送ループ問題を出題したい。
  固定トポロジだと慣れると考える余地がなくなる」。
- 現状の課題: gen_redist_loop_ts / gen_redist_mp_ts / gen_redist_mutual_ts はいずれも
  **正準トポロジ固定**(値・故障・解法のみランダム)。ノード名(RA/RB/RC…)と図が毎回同じため、
  構造の特定という一番おいしい切り分けがスキップされてしまう。

## 1. 実現性の根拠(既存資産)

| 部品 | 状態 | 流用点 |
|------|------|--------|
| netmodel.py 大域不変条件採点 | 実機検証済 | 到達性/loop_free/optimal は「モデル+RIB」だけで判定=**トポロジ非依存**。grading.yml の model 節を生成器が吐けばよい |
| ループ成立の定石(実機検証済) | BL-056/058 等 | ①3ドメインリング(BGP→IGP→IGP・戻り経路のADが起点ADに勝つ) ②2点相互再配送×AD次善(EIGRP external 95<110 固定等) ③多点 seed metric ループ ★ランダム配線では定常ループは出ない(自己制限振動)→**モチーフ保存が必須** |
| gen_topology.py / gen_ospf_complex_ts | 実機検証済 | ランダム形状生成→自動解答(solution.json)→fix_generated.yml の型 |
| 解法強制監査 | gen_redist_mp_ts | --solution を seed 抽選し「指紋regex+他解法禁止not_regex」で強制 |
| 値ランダム化・decoy | 各生成器 | AS/PID/プレフィックス/名前の抽選機構 |

結論: **可能**。新規に書くのは「モチーフを保ったままトポロジを装飾する層」のみ。

## 2. アーキテクチャ(gen_redist_arena.py 想定)

```
モチーフ抽選 (M1リング/M2二点相互/M3多点seed) ← ループ成立の骨格。決定性は既検証の定石を踏襲
  ↓
装飾ランダム化
  - プロトコル割当シャッフル (OSPF/EIGRP/BGP/RIP から モチーフ要件を満たす組合せ)
  - 各ドメイン内部へノイズノード接ぎ木 (chain/tree 0〜3台・ループ機構に無関係=安全に乱せる)
  - 境界ルータの位置・台数・「変更可能ルータ」の指定もランダム
  - ★匿名化: ノード名は RT01..RTn を役割と無関係にシャッフル(役割が名前から透けない)
  - 被害プレフィックス/アドレッシング/decoy設定の抽選
  - 症状クラス抽選: 定常ループ / ブラックホール / 次善経路(毎回ループとは限らない)
  ↓
出力: initial(day0) + task.md(図は実形状から生成) + grading.yml(netmodel model節+監査) + solution.json
```

- 台数上限: 6〜8台(IOL・mgmt リースと 20 ノード上限に収める)
- 難易度: モチーフ+ノイズ量+症状クラス+解法強制の組合せで 4〜6
- 採点: netmodel(reachability/loop_free/optimal) + 方向別 raw 指紋 + 監査(regex/not_regex)。
  すべて既存 grade.py 機構で無改修

## 3.5 Phase1 実装結果(2026-07-29 完了・出題可)
- **topologies/gen_redist_arena.py** 完成(GEN-RDARENA-<seed>・難5・5〜8台)。
  骨格=リングモチーフ(gen_redist_loop_ts と同一機構)・装飾=①名前匿名化(RT01..RTn シャッフル・
  task の図/表は実形状からエッジリスト生成・役割記述は排し「参加プロトコル+Lo」の事実のみ)
  ②OSPF側ノイズ接ぎ木(RB配下 leaf→chain/fork・RA配下 leaf・最低1台強制)
  ③抽選=リング向き2×解法2×被害prefix/AS/PID/Lo/セグ。値は全て焼き込み(params 不使用)。
  fix は solution/fix.json(fix_generated 形式・clear exec 込み)。
- 検証: オフライン30seed 構造検証 30/30(ノード数分布 5:15/6:6/7:6/8:3)＋実機フルサイクル
  **seed112**(inject_ospf×filter・6台)15→100 / **seed127**(inject_eigrp×distance・8台)20→100。
  ★新規に実機実証= **EIGRP 側の distribute-list prefix in による戻り遮断**(従来未検証の組合せ)。
- ★設計判断(Phase2への申し送り): **EIGRP側ノイズは見送り** — EIGRP leaf の Lo は
  eigrp→bgp 再配送なしに起点へ届かず、eigrp→bgp は ad_eigrp 型の distance 解を壊す
  実機知見(weight 32768 がBGPベスト奪取)と衝突。解決案=①inject_eigrp 限定で接ぎ木
  ②leaf Lo を到達性モデルから除外(タスクの到達目標文言も要調整) のどちらかを Phase2 で。

## 3.6 Phase2A 実装結果(2026-07-29 完了・出題可) — 方針転換込み
- **ユーザ評価(8351 初出題)**: 「トポロジが変わっても全然違わなくない?」= 正当。
  ①提示がモチーフ/診断手順をバラしていた(タイトル・チケットのループ描写・手順ヒント)
  ②単一モチーフでは解が 1:1 転用できる(実際 4977 の解がそのまま通った)。
- **対処①= アリーナ提示改修**: タイトル「経路到達性障害チケット」に汎用化・チケットは
  申告事実のみ(症状の型=ループか否かの特定を受験者の仕事に)・手順ヒント撤去。
- **対処②= gen_redist_field.py 新設(ドメイングラフ抽選型)**: 「ループ限定」を捨て
  **再配送起因トラブル全般**に拡張したことで、モチーフ制約が消えトポロジを自由に抽選できる:
  ドメイン数 K=2-3 の数珠つなぎ(木)・各ドメイン OSPF/EIGRP(同種異インスタンス隣接あり)・
  内部 0-2 台の木配線・名前匿名化。**木構造ゆえループが構造的に不成立**なので、
  故障カタログ(missing / wrong_id / no_seed / filter)がどんな抽選形でも決定的に成立する。
  採点= netmodel(reachability 40+loop_free 10)＋仕様書突き合わせ監査(BR毎 redistribute 行
  regex+フィルタ不在)＋対岸学習指紋。難4(missing/filter)〜5(wrong_id/no_seed/複合)。
- 検証: オフライン 40seed 40/40(3〜8台分布・全故障型出現)＋実機
  **seed226**(K=3・7台・no_seed)40→fix→100 / **seed217**(K=3・6台・missing+filter 複合)30→fix→100。
- ★実機知見: **監査 regex は「表示形」で生成する** — iol-xe 17.15 は into-OSPF の
  `subnets` を暗黙化して running-config に表示しない(BL-058 知見が採点側に波及。
  config には書く・regex からは外す、で解決)。
- 使い分け: **アリーナ=ループ特化**(リング構造が必要) / **フィールド=それ以外全部**。
  出題時は field を既定にし、ループを混ぜたい時だけ arena も抽選対象に(両者とも
  タイトル・チケット形式を揃えたので、**どちらが来たか自体が受験者には非自明**)。
- ★追補(2026-07-29 4471 出題後のユーザ指摘→実機確認→修正済): OSPF⇄OSPF 境界 BR の
  Lo 二重 network は片方が死に文(1 IF=1 OSPF プロセス・所有は config 順先勝ち)。
  生成器は Lo network を先頭ドメインのみに出すよう修正。非所有側へは
  **redistribute の connected-subnets 随伴仕様**(source IGP が動く connected も再配送される)
  で E2 として届く=field が redistribute connected 無しで全到達する理由。
## 3.7 Phase2B 実装結果(2026-07-29 完了・BL-074 全完了)
- **統一生成器化**: gen_redist_field.py に shape 抽選を実装(chain 50% / twoborder 25% /
  ring 25%・`--shape` 指定可)。**全て GEN-RDFIELD-<seed> の ID で出るため、受験者は
  「木構造トラブルか・2点相互か・ループか」を ID からも問題文からも判別できない**。
- **twoborder(M2)**: gen_redist_mutual_ts の定石(OSPF⇄EIGRP 境界2台・EIGRP外部AD=95固定・
  健全形=双方向+seed metric+タグ衛生 SET_TAG/BLOCK_TAG・故障は両境界対称)を、
  匿名化+leaf/chain 装飾(4〜8台)+値抽選(tag 含む)付きで移植。
  故障= no_tag(難5・次善) / missing_o2e / missing_e2o(難4) / missing_seed_metric(難5)。
- **ring**: arena を generate(prob_id=...) に関数化し field から委譲(ID差し替え)。
- 検証: shape分布 30seed(19/6/5)・twoborder構造 10/10・実機フルサイクル3本=
  **504 no_tag 60→100(到達○・最短だけFAIL=正しい次善症状) / 503 seed_metric 20→100 /
  640 ring経由 25→100**。検証seed掃除済。
- 残り種(小粒・必要時に新IDで): RIPドメイン / chain の EIGRP側ノイズ / M3多点seed metric。

## 3. 実装ステップ(推奨)

1. **Phase 1**: M1(リング)のトポロジ装飾版。既存 gen_redist_loop_ts の骨格を移植し、
   ノイズ接ぎ木+匿名化+図生成を実装。seed 数本を実機フルサイクル(broken→fix→100)
2. **Phase 2**: M2(2点相互)を統合。症状クラス抽選(ループ/次善)を追加
3. **Phase 3**: M3(多点 seed metric)+解法強制統合。オフライン 50seed スイープで
   「全 seed でループ成立(または意図した症状)」を機械検証(gen_ospf_complex_ts の前例)
- 各 Phase 完了ごとに出題可(段階リリース)。全体規模は BL-058 級(1〜2セッション)

## 4. 注意(過去の教訓の適用)

- ★ランダム配線で「壊れているのに到達できてしまう」偽完成を防ぐ: 生成後に impact
  検証(failing_pairs 非空)を必須化(gen_ospf_complex_ts Phase B.1 の教訓)
- ★ループ検証は「RIB乗っ取り≠ループ」(chain TS 教訓)。転送グラフで閉路判定(netmodel)
- ★distance 系解法は clear 要否がプロトコルで違う(bgp=clear必須/ospf external=不要)
- 内部ノイズノードの RIB も netmodel に食わせると採点が重くなる → RIB 収集は
  境界+代表内部ノードに限定するオプションを検討
