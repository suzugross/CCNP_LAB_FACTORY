# EIGRP 集約×リーク 手段選択問題(紙面) — 設計メモ (BL-095)

作成: 2026-08-07 / 発端: ユーザ手組みラボ「EIGRP leak-map」(CML, 2×IOL, 温存・無改変)

## 出題意図(ユーザ要望の整理)

「1.1.1.0/30 で集約しつつ 1.1.1.3/32 だけは明細で届かせたい」を題材に、
**要件・制約ごとに最適な手段を選ばせる**問題ファミリを作る。

- 制約バリエーション: redistribute 禁止 / Loopback の network 文禁止 /
  集約は内部(AD90)であること / リーク明細も内部であること 等 → **制約が正解を反転させる**
  (gen_paper_pbr の被覆エンジン方式を踏襲)。
- **無駄な access-list / prefix-list を乱立**させ、生きている参照チェーンを読み解かせる。
- 形式: 紙面4択中心(構築選択 / 逆引き読解 / TS「どの1修正で要件回復か」)。

## 技術の核 — 3レバー分離

この問題ファミリの教育的核心。「集約とリークの両立」は独立な3操作の合成:

| レバー | 手段 | 備考 |
|---|---|---|
| ①投入 (明細を EIGRP へ) | network 文 / redistribute connected (+route-map) | redistribute は D EX (AD170) になる |
| ②集約 (明細の抑止) | `ip summary-address eigrp <AS> ...` (IF単位・内部・自身に AD5 Null0) / static Null0 + redistribute static (D EX・抑止なし) | 後者は「広告しない」ことで抑止を代替 |
| ③リーク (例外通過) | `leak-map <route-map>` **のみ**が summary-address の抑止を破れる | route-map → prefix-list/ACL |

ユーザがラボで確認した「network 1.1.1.1 を足してもリークされない」はこの分離の実例:
network は①(投入)であって③(リーク許可)ではない。リークには
「トポロジテーブルに存在する」**かつ**「leak-map の route-map が permit する」の両方が必要。
同様に redistribute connected も①の代替であって③にはならない(leak-map が無ければ抑止される)。

制約→正解の反転例:
- 「redistribute 禁止」→ network + summary-address + leak-map (正典解) 一択
- 「Lo を network で広告禁止」→ redistribute connected route-map + leak-map
- 「集約が D (内部) で受信されること」→ static Null0 + redistribute static 案が死ぬ
- 「リーク明細も AD90 であること」→ redistribute 投入案が死ぬ

## エッジ挙動 実機確定表(★2026-08-07 IOL iol-xe 17.15 で全件実測・poc/leakmap/)

盤面: RT01(Lo=1.1.1.1/1.1.1.2/1.1.1.3/10.10.10.10 全て network 投入)—RT02。
summary 1.1.1.0/30 leak-map。各行は clear ip eigrp neighbors 後の RT02 受信経路。

| # | 状況 | ★実測(確定) |
|---|---|---|
| S0 | leak-map なしの summary | /30 のみ(全明細抑止) |
| E1 | leak-map が参照する route-map が**未定義** | **リークなし**(/30のみ。「全リーク」ではない) |
| E2 | route-map は在るが参照 prefix-list **未定義** | **全リーク**(/30+.1+.2+.3 全部) |
| E3 | permit 節に match なし | **全リーク** |
| E4 | prefix-list は在るが成分に不一致(99.99.99.99/32) | リークなし(/30のみ) |
| E5 | 成分投入が redistribute connected(route-map絞り) | リーク成立・**明細は D EX [170]**・集約は D [90] のまま |
| E6 | route-map の match が標準 ACL (`match ip address 10`) | prefix-list と同様にリーク成立 |
| E7 | 集約成分が1個(=リーク対象と同一。ユーザラボ状態) | 集約 /30 と明細 /32 の**両方**届く |
| V1 | summary を使わず static Null0 + redistribute static + network は対象のみ | 集約 **D EX [170/281600]** + 明細 D [90](成立・手段c3) |
| V2 | 全Lo network + Null0 static 再配送・summary なし | **抑止なし**(D EX /30 + 全明細。「Null0静的=集約」では抑止されない) |
| V3 | 成分が全て redistribute connected(external)の summary+leak | 集約は **D [90] 内部のまま**・リーク明細は D EX [170] |
| V4 | ★エコ形(ユーザ発案): redistribute connected と leak-map が**同一 route-map を共用**(対象/32のみ投入) | 成立: D /30 [90] + 対象 D EX [170/409600] |
| V5 | 共用マップのリストを別 Lo へ「変更」 | 旧対象は**投入ごと消失**(明細もリークも無い・ただし集約経由で到達は可)・新 Lo が D EX で出現 |

### エコ形の採用(2026-08-07・BL-096③ 完了)

- redist_leak 候補の**表面バリアント**: seed で「2チェーン形(RM-CONN 投入+RM-NEW リーク)」
  ⇄「共用形(RM-SHARED 一本・対象のみ投入)」を描き分け(`d["eco"]`)。両者は
  works/complies プロファイルが同一のため、一意性機構は不変(同時提示はしない)。
- 新故障種 `shared_map_wrong_target`(V5 の写像): 共用マップの許可先が別 Lo →
  対象は投入ごと消え、別 Lo が D EX で漏れる(二重の要件違反)。cause 形では
  pl_wrong_prefix / not_injected の claim も同時に真になるため **CAUSE_EXCLUDE で排他**。
- 検証= 7故障×4世界×40seed=1120/1120・E2E 14問検分(shared 2問含む・正解一意)。

★最重要の非対称(E1 vs E2/E3): **route-map ごと無いと「何も漏れない」、route-map の
器だけ在って中身が空振り(未定義リスト/matchなし permit)だと「全部漏れる」**。
「絞るつもりが逆に全開」——紙面TSの症状素材として最上級。
補足: リーク明細のメトリックは集約と同値(409600)で届く(この盤面では)。

## デコイ(リスト乱立)仕様

- prefix-list / 標準ACL / 拡張ACL を計4〜7個生成。似た名前(PL01/PL-LEAK/10/ACL_LEAK 等)。
- 生きている参照チェーンは1本だけ。罠: 未参照リスト / route-map が別リストを参照 /
  deny 節が permit 節を先取りする sequence 影 / prefix-list の ge/le で空振り /
  拡張ACL を route-map match に使った時の source/dest 解釈。
- hard でデコイ数・sequence 影を増量。

## 出題形状

- S1 構築選択: 要件+制約 → 4設定案からどれが満たすか(正解は制約で反転)
- S2 逆引き読解: 乱立設定のエキシビット → 「RT02 の経路表はどれか」
- S3 紙面TS: 現状設定+症状(明細が届かない/全部漏れる) → どの1修正で要件回復か
- S4 複数選択(BL-082 連動・後回し可)

提示規約は gen_paper_mcq 踏襲: Cisco語文体 / --exam / 選択肢に因果を書かない / 図の可読性後処理。

## 実装計画(2026-08-07 完了)

- P0 ✅: エッジ挙動 E1〜E7 + V1〜V3 実機スイープ(自前2 IOL・poc/leakmap/)→ 上表確定
- P1 ✅: `topologies/gen_paper_leakmap.py` + gen_paper_mcq `--shape leakmap`(mixed 合流)。
  故障6種×要件世界4種・被覆エンジン(モデル一意性 960/960 検証)・デコイ乱立。
- P2 ✅: 出題形3種= fix(prose/CLI・★CLI は既存構成の削除込みの状態収束形)/
  cause(原因特定・claim は事実記述のみ)/ read(逆引き=経路表4択・実測書式)。
- P3 → **BL-096 へ分離**: GEN-EGVRF 実機TS移植(★named mode 再検証前提)＋
  BGP 姉妹問(aggregate-address summary-only × unsuppress-map)。

公開可否: leak-map は定番題材の自作問のため公開系(PVT不要)。
