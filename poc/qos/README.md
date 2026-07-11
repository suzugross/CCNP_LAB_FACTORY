# QoS 実効性 PoC (BL-022) — 結果 (2026-07-08)

「QoS の効果を数値で体感できるラボ問」(QOS-SERIES.design.md) の Phase 0。
IOL 上で shaping / policing / LLQ が**実際に効くか**を iperf3 + ping で測定。
**全項目成立 → 設計の判断基準どおり IOL 採用**（cat8000v / IOSv の比較測定は不要と判断）。

## 検証環境（poc-qos-iol-lab.yaml）

```
PC01(ubuntu, iperf3) — RT01(IOL) —[ボトルネック E0/1]— RT02(IOL) — PC02(ubuntu, iperf3 -s)
   10.99.1.2/30        .1 | .1 ← 10.99.12.0/30 → .2 | .1        10.99.2.2/30
MGMT: RT01=.14 RT02=.15 PC01=.16 PC02=.17 (mgmt_alloc 台帳リース)
```

- ubuntu は cloud-init `package_update: true` + `packages: [iperf3]` で自動導入
  （apt 完了まで起動から**約2〜3分**。マーカー: /var/tmp/poc_cloudinit_done）。
- 測定はすべて PC01 から: iperf3 TCP/UDP、`ping -Q 184`(=DSCP EF) / `ping`(BE)。

## 測定結果マトリクス（IOL iol-xe-17-15-01）

| # | 項目 | 結果 | 数値 |
|---|------|------|------|
| - | ベースライン (QoSなし) | - | TCP **168 Mbps** / 無負荷 RTT avg 3.4ms (max 21ms のジッタあり) |
| A | `shape average 2000000` | ✅実効 | TCP **1.82 Mbps** (CIRの91%) に張り付き。counters: total drops 増加 |
| B | `police cir 1000000` | ✅実効 | TCP **943 kbps** / UDP 3M供給→**990 kbps 通過・67% loss**。conform/exceed カウンタ正確 |
| C | LLQ (shape 2M 親 + EF priority 256k 子) | ✅劇的 | 下表参照 |
| D | Genie パース | ⚠️条件付き | 後述。直接クラス呼びで完全構造化可 / raw regex 代替も可 |
| E | ubuntu + iperf3 基盤 | ✅ | cloud-init のみで完結。2本目サーバは `-p 5202` で並行測定可 |

### C. LLQ の体感数値（UDP 5Mbps flood で輻輳させた状態での ping 25発）

| 状態 | EF ping (tos 184) | BE ping (tos 0) |
|------|-------------------|------------------|
| shaper のみ (LLQなし) | **RTT 327ms / 68% loss** | (同等に悲惨) |
| LLQ + class-default **fair-queue** | RTT 3.8ms / 0% loss | RTT 4.6ms / 0% loss ←★BEも救われる |
| LLQ + class-default **FIFO** | **RTT 0.97ms / 0% loss** | **RTT 334ms / 64% loss** |

- ★**作問上の最重要知見**: class-default に `fair-queue` を入れると WFQ が小フロー
  (ICMP) を保護してしまい **BE ping まで綺麗になる**（対比が消える）。
  「EF だけ助かる」対比を見せたい問題では **class-default は FIFO にする**こと。
  逆に「fair-queue で BE の小フローも改善する」現象自体を第2幕として出題可能。
- 輻輳時の RTT ≈ 330ms は理論値と整合 (queue 64pkt × 1200B × 8 / 2Mbps ≈ 310ms)。
- **priority 内蔵ポリサの罠も実証**: EF に 1Mbps 供給 (priority 256k・輻輳下)
  → **76.5% loss・`b/w exceed drops: 7166`**。「LLQ にしたのに音声が死ぬ」変種に使える。

## D. Genie パースの注意（実装時に効く）

- `dev.parse("show policy-map interface ...")` は **rv1 版パーサ
  (genie.libs.parser.iosxe.rv1) が選ばれ、IOL の `Ethernet0/1` にマッチしない**
  （rv1 の interface regex が `TenGigabitEthernet\d+/\d+/\d+` 固定という半端実装）
  → SchemaEmptyParserError で grade.py の genie_parse は None を返す。
- **回避1 (推奨)**: 旧版クラス
  `genie.libs.parser.iosxe.show_policy_map.ShowPolicyMapInterface` を直接呼ぶと
  shape/police/LLQ 階層とも**完全に構造化できた**（shape_cir_bps / police cir_bps /
  conformed/exceeded packets / total_drops / priority まで全部取れる）。
  → grade.py に「パーサクラス直指定」の小拡張を入れる（Phase 1 実装項目）。
- **回避2**: 既存の raw regex チェックで代替（`b/w exceed drops: [1-9]` 等）。
- `show policy-map control-plane`（CoPP実績あり）は従来どおり問題なし。

## 採点設計への反映（実測に基づく閾値）

- スループット系: **CIR×0.7 〜 CIR×1.1 の帯**判定が安全（TCP goodput は CIR の 91〜94% で安定）。
- RTT 系: 無負荷でも max 21ms のジッタ → **avg で判定し、比率で見る**
  （輻輳+LLQなし avg 327ms vs LLQあり avg <10ms は 30 倍差なので余裕）。
- カウンタ系が最も安定: `total drops > 0` / `exceeded packets > 0` /
  `b/w exceed drops` / EF クラス `total drops == 0`。**clear counters 後の増分**で判定。
- 輻輳の再現性: iperf3 UDP `-b 5M -l 1200` × shape 2M で毎回同じ惨状を再現できた。

## 再現手順（次フェーズでの実装用）

1. ラボ投入: `cml import poc/qos/poc-qos-iol-lab.yaml`（mgmt_alloc で .14-.17 リース済みが前提）
2. PC02: `iperf3 -s -D`（+必要なら `-p 5202` も）
3. 輻輳: PC01 `iperf3 -c 10.99.2.2 -u -b 5M -l 1200 -t 40`
4. 測定: PC01 `ping -Q 184 -c 25 -i 0.2 10.99.2.2` / `ping -c 25 -i 0.2 10.99.2.2`
5. QoS 切替 (RT01 E0/1 output): SHAPE2M → POLICE1M → WAN2M(CHILD-LLQ)
   ※検証に使った policy-map 定義は poc-qos-iol-lab.yaml の notes ではなく本 README 末尾参照

## 検証に使った MQC 定義（IOL で全て受容）

```
class-map match-all EF
 match dscp ef
policy-map CHILD-LLQ
 class EF
  priority 256
 class class-default        ! fair-queue は入れない(対比が消える)
policy-map WAN2M
 class class-default
  shape average 2000000
  service-policy CHILD-LLQ
policy-map SHAPE2M
 class class-default
  shape average 2000000
policy-map POLICE1M
 class class-default
  police cir 1000000 conform-action transmit exceed-action drop
```

## 運用メモ

- iperf3 の bg 起動は `setsid nohup iperf3 -s -p 5202 </dev/null >log 2>&1 &`
  （pgrep で存在確認してから起動する書き方は**自分の bash 行に self-match**して
  スキップされる罠あり）。
- ubuntu ノードの iperf3 導入は package_update 込みで起動後 2〜3 分。
  問題実装では provision 直後の採点プリフライトに「iperf3 存在確認」を入れること。
