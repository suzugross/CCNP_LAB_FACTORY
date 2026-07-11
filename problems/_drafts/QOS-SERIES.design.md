# QoS シリーズ — 「効果を数値で体感する」ラボ設計メモ

作成: 2026-07-08。番号は BACKLOG.md の BL-ID に対応 (BL-022〜BL-025)。

## コンセプト

QoS は「設定はできるが効果が見えない」まま終わりがちな分野。本シリーズは
**受験者自身が before/after を測定し、数値の変化（スループット・RTT・loss・
キューカウンタ）で効果を確認する**ことを一貫の核に置く。

- 設定だけの採点では終わらせない: **効果そのもの（counters / 実測値）を採点**する。
- task.md には「測定手順」を詳しめにガイドし（サーバラボ方針と同型）、
  **解法・設定値は従来どおり伏せる** [[ccnp-problem-hint-policy]]。
  before/after を書き込む記録表を task に含め、体感を強制する。

## 測定インフラ（シリーズ共通）

標準トポロジ（4〜5ノード・20ノード制限に余裕）:

```
PC01(ubuntu: iperf3 client) — RT01 —(ボトルネック回線)— RT02 — PC02(ubuntu: iperf3 server)
                               └ 測定用に RT01/RT02 から ping (tos指定) も併用
```

測定3点セット:
1. **iperf3**（TCP/UDP スループット・loss・jitter。`--json` で採点にも使える）
2. **ping 統計**（`ping ... tos 184` で EF 相当、repeat 大きめ → RTT min/avg/max, loss%）
3. **`show policy-map interface`**（class 毎 offered rate / drops / conform・exceed）

補助・代替:
- **IOS ping flood** (`ping x.x.x.x repeat 100000 size 1400 timeout 0`) = Linux ノード無しでも
  輻輳を作れる congestion 源。ルータのみ構成のフォールバックとして常に選択肢に置く。
- 導入済みイメージ **trex**（本格トラフィック生成）と **alpine-wanem**（遅延/損失エミュ）
  は当面使わない（overkill）。LLQ 問で「WAN らしさ」が欲しくなったら wanem を検討。
- ubuntu への iperf3 導入は cloud-init (apt)。DNS ラボで apt 実績あり。
  PC* 接頭辞・shell 採点型のインフラは Linux サーバラボで整備済み → 流用。

## BL-022 Phase 0: プラットフォーム PoC — ✅完了 (2026-07-08・実機測定済)

**結論: IOL で全項目成立 → IOL 採用**（判断基準どおり cat8000v/IOSv 比較は省略）。
詳細な数値・再現手順・MQC 定義は [poc/qos/README.md](../../poc/qos/README.md)。

- A shaping: TCP 168Mbps → **1.82Mbps** (CIR 2M の 91%) ✅
- B policing: TCP 943kbps / UDP 67% drop・conform/exceed カウンタ正確 ✅
- C LLQ: 輻輳中 EF ping **327ms/68%loss → 0.97ms/0%loss** ✅
- ★最重要知見: **class-default に fair-queue を入れると WFQ が BE の小フローまで
  救ってしまい対比が消える** → 体感問は class-default FIFO で作る。
  fair-queue の救済現象自体は第2幕の出題ネタになる。
- ★priority 内蔵ポリサ罠を実証: EF 1M 供給 vs priority 256k → 76.5% loss,
  `b/w exceed drops` カウント → BL-024 変種に採用。
- ★Genie 罠: dev.parse は rv1 パーサを選び IOL の Ethernet IF 名に不整合
  → **grade.py にパーサクラス直指定の小拡張が必要**（または raw regex 代替）。
- 閾値の実測根拠: スループットは CIR×0.7〜1.1 帯 / RTT は avg の比率(30倍差) /
  カウンタ増分判定が最安定。

<details><summary>PoC 前の検証計画（記録用に残す）</summary>

仮想機での QoS は「設定は入るが効果が出ない」リスクがある。
**IOL / IOSv / cat8000v の3者で QoS 実効性マトリクスを取ってから作問する。**

検証項目（各プラットフォームで）:
- **A. shaping 実効**: `shape average 2m` でボトルネック化 → iperf3 TCP が ≈2Mbps に張り付くか。
- **B. policing 実効**: `police cir 1m` → 超過 drop がカウンタと実測スループット両方に出るか。
- **C. LLQ 実効（体感の核心）**: 輻輳下（iperf UDP flood）で EF ping の RTT/loss が
  LLQ 適用前 → 後で劇的に改善するか。class-default との差が数値で出るか。
- **D. Genie 構造化**: `show policy-map interface` の Genie パーサが各 OS 出力を
  パースできるか（CoPP 問で `show policy-map control-plane` は実績あり）。
- **E. iperf3 導入**: ubuntu cloud-init での apt 導入と PC01→PC02 実測の疎通。

判断基準:
- IOL で A〜C が成立するなら **IOL 採用**（軽い・既定イメージ方針に合致）。
- IOL で効果が出ない/不安定なら **cat8000v へ切替**（QoS データパスの忠実度が高い。
  RAM は潤沢、小規模トポロジなので 20 ノード制限も問題なし）。node_image 切替は
  既存インフラ（image_family）で対応可 [[ccnp-image-policy]]。
- ★仮想環境はタイマ/CPU スケジューリングでレートが揺れる前提。効果採点の閾値は
  **絶対値でなく比率**で設計する（例: 実測 ≤ CIR×1.5、EF RTT < default RTT の 1/5、
  exceed drops > 0）。PoC で揺れ幅も記録すること。

</details>

## BL-023 ENCOR-QOS-CLASS-01 / ENCOR-QOS-POLICE-01（組み立て・難3）— ✅完了 (2026-07-09)

両問とも実機フルサイクル済（未解答10点/模範解答100点収束）。学習順序 CLASS→POLICE→LLQ。
- CLASS-01: RT02 に観測ポリシー MONITOR（match dscp のカウンタ専用・initial 焼込み）
  を置き「マーキングの WAN 越え伝搬」を数値で見せる方式が成立。マーキング実績は
  複数行 raw regex（Genie 非構造化のため）。
- POLICE-01: ★class-default 丸ごと police の誤答は **ICMP 巻き添えでは検出不可**
  （TCP が輻輳制御で自制→ping 無傷=90点通過を実機確認）→ 構造 `match.*: {ne: any}`
  ＋ UDP 素通り実測の2本柱に修正（誤答65点/正答100点を実機確認）。
- 詳細は conventions.md「QoS効果採点規約」。残: BL-025 生成器 / BL-026 入門ドリル(低)。

### CLASS-01: 分類とマーキング
- class-map（ACL / DSCP マッチ）→ `set dscp ef / af41` を LAN 入力に適用。信頼境界の考え方。
- 体感: tos 違いの ping / iperf3 `--dscp` を流し、`show policy-map interface` の
  class 毎カウンタが**意図したクラスだけ**増えることを確認。下流 RT02 で DSCP マッチの
  class が増える＝「マーキングが伝搬した」ことを数値で見る。
- 採点: ①ポリシー構造（Genie）②採点器がトラフィックを流した後のカウンタ増分。

### POLICE-01: ポリシングでレートが頭打ちになる体感
- 特定トラフィック（iperf / HTTP 相当 ACL）を `police cir 2m` 等で制限。
- 体感手順: before = iperf3 で無制限スループットを記録 → 適用後 = ≈CIR に張り付く。
  conform/exceed カウンタの伸びも観察。
- 採点: ①police 構造（cir / exceed drop）②効果 = exceed drops > 0、
  （可能なら）iperf3 --json のスループットが CIR×1.5 以下（exec:shell 採点）。

## BL-024 ENCOR-QOS-LLQ-01（旗艦・難4）— ✅完了 (2026-07-09・実機フルサイクル済)

未解答 0/100・模範解答 100/100（3回再現・2試行収束 約4分）。実装で確立したこと:
- grade.py に `parser: "class:<module>.<Class>"` 直指定拡張（rv1 回避・後方互換）。
- ★**EF保護の単独採点は偽陽性**（QoS 未設定→輻輳が起きず EF ping が綺麗
  =実機で20点素通り）→「同一輻輳ウィンドウで EF 無傷 AND BE 劣化」の統合チェックへ。
- カウンタ系は「採点器のトラフィックで加算→試行2で PASS」が正常動作。
- 採点規約は conventions.md「QoS効果採点規約」に集約。BL-023/025 はそれを流用する。
- Linux ノードのログインは SUZUKI/CCNP（パイプライン標準。PoC の suzuki とは異なる）。

<details><summary>実装前の設計（記録用）</summary>

シリーズの目玉。「輻輳で音声が死ぬ → LLQ で蘇る」を数値で体験する。

- ボトルネック WAN（parent `shape average 2m`）+ child ポリシー:
  EF に `priority`、業務クラスに `bandwidth remaining`、**class-default は FIFO**
  （PoC 知見: fair-queue を入れると WFQ が BE ping まで救い対比が消える）。
  第2幕として「class-default に fair-queue を足すと BE の小フローも改善する」
  発展要件を置ける（fair-queue の意義を数値で学ぶ）。
- 体感シナリオ（task.md の記録表に書き込ませる）:
  1. 平常時: EF ping RTT を記録（基準値）。
  2. iperf3 UDP flood で輻輳 → EF ping の RTT 悪化・loss を記録（惨状を見る）。
  3. LLQ を実装 → 同じ輻輳下で EF ping がほぼ平常時 RTT に戻り loss 0、
     bulk は shaper に張り付いたまま、class-default にキュー drop が出るのを記録。
- 採点: ①階層ポリシー構造（Genie）②効果 = 輻輳注入後に EF クラス drops=0 かつ
  class-default drops>0、EF の ping loss 0%。RTT は揺れるので副次チェック
  （比率閾値・配点小）に留める。
- 変種候補: `priority` の帯域上限（policer 内蔵）超過で EF 自身が落ちる罠 /
  bandwidth vs priority の使い分け。

</details>

## BL-025 gen_qos_ts.py（TS 生成器・難4）

BL-023/024 の健全構成に故障を注入し「効果が出ていない QoS を直す」問題。
**症状が数値で見える**（＝切り分けも数値で行う）のが既存 TS 群との差別化。

故障カタログ候補:
- `dir_wrong`: service-policy の input/output 逆 → カウンタが一切増えない
- `intf_wrong`: 適用インターフェイス違い
- `match_dscp_wrong`: class-map の DSCP 値ずれ → 全部 class-default 行き
- `priority_missing`: priority が bandwidth になっている → 輻輳時に EF RTT 悪化
- `police_cir_wrong`: 桁違いの CIR（2m→2000=2kbps 等）→ 全滅に近い drop
- `acl_mismatch`: 分類 ACL の対象ずれ
- `shaper_no_child`: parent だけで child が外れている
- 既存規約どおり decoy・変種軸（--faults N）も踏襲。

## 採点系の実装メモ

- 2層採点 = **構成（Genie）+ 効果（数値）**。効果採点には
  「採点器がトラフィックを流す」ステップが要る:
  - 案1: grading.yml に `pre_actions:`（clear counters → IOS ping flood N 秒）を足す
    grade.py 小拡張。
  - 案2: exec:shell（既存）で PC01 の iperf3 を叩き `--json` を regex/jq 判定。
  - どちらも既存リトライ機構と干渉しないよう「注入→計測」を1チェック内で完結させる。
- `show policy-map interface` の Genie 構造は深い（class→police/queueing→counters）。
  find パスは PoC 中に実出力で確定させる。
- カウンタは累積 → 判定は **clear 後の増分** か「>0」型に限定し、絶対レート判定は避ける。

## 実装順序

1. BL-022 PoC（プラットフォーム決定・揺れ幅測定・iperf3 基盤）
2. BL-024 LLQ-01 を先に手組み（旗艦で採点パターンを確立。CLASS/POLICE は部分集合になる）
3. BL-023 CLASS-01 / POLICE-01（LLQ で確立した効果採点を軽量流用）
4. BL-025 gen_qos_ts.py（3問の知見を故障カタログ化）
