# EVPN-VXLAN ファブリック教育ラボ — 設計ドラフト（BL-055）

作成: 2026-07-13（検討フェーズ）。SDA-LISP-01（BL-054）の続編・「正統合流」編。

**★PoC 結果（2026-07-13・[poc/evpn-vxlan/README.md](../../poc/evpn-vxlan/README.md)）: 案A 成立・確定。**
IOL RR は Type-2/3/5 全反射・RMAC 透過・`no bgp default route-target filter` 不要。
Symmetric IRB／Anycast GW／Type-5 まで day0 一発成立。
唯一の罠= suppress-arp は TCAM carving（racl 縮小→reload→arp-ether carve→reload）が必要
→ 本編から外し任意上級 phase or 読み物へ。

## 1. 位置づけ — なぜこれが SDA-LISP-01 の完結編になるか

SDA-LISP-01 は「LISP（pull型コントロールプレーン）」と「VXLAN（カプセル化の実像）」を
**別々に体感**し、終章で SD-Access の部品対応表として**頭の中で合流**させる設計だった
（実機合流は cat9k ASIC 前提で不可のため）。

本ラボはその裏面: **BGP EVPN（push型コントロールプレーン）＋ VXLAN** は
CML の nxosv9300 で**実機のまま合流できる**唯一の組み合わせ。
つまり「頭の中で合流」で終わった前作に対し、本作は
**CP と DP が一体で動くファブリックを最初から最後まで実機で組む**。

終章の対比が完成する:

| | SD-Access (前作) | DC/オープンファブリック (本作) |
|---|---|---|
| コントロールプレーン | LISP (pull・オンデマンド) | BGP EVPN (push・事前配布) |
| データプレーン | VXLAN | VXLAN（同一） |
| 初回パケット | map-request で数発ドロップ | 事前学習済みでドロップなし（★実機で対比観察できる目玉） |
| 標準化 | Cisco 独自色強 | RFC 8365・マルチベンダ標準 |

## 2. 前作 VXLAN 編との差分（新規学習項目）

前作 Tier2A は「leaf 2台 back-to-back・iBGP フルメッシュ・単一 L2VNI・Type-2/3」= EVPN の入口のみ。
本作で加わるもの:

1. **Spine-Leaf 構造＋ルートリフレクタ**（実ファブリックの形。leaf 同士は直接ピアしない）
2. **Symmetric IRB ＋ L3VNI**（サブネット間ルーティング）— 最大の新規概念
3. **Distributed Anycast Gateway**（全 leaf が同一 GW MAC/IP・端末は移動しても GW 不変）
4. **マルチテナント**（tenant VRF × VNI × RT の対応関係）
5. **Type-5 ルート**（外部経路の注入・border leaf）
6. **ARP suppression**（leaf が代理応答・BUM 削減の観察）

Route type の読解が 2/3 → 2/3/5 に広がり、`show bgp l2vpn evpn` の
NLRI 構造読解がそのまま採点・観察ポイントになる。

## 3. トポロジ案

```
                SPINE (EVPN RR・VTEPなし)  ← IOL で軽量化できるかが PoC 最重要項目
               /        |         \
          LEAF1       LEAF2      LEAF3(border)     ← nxosv9300 (12GB/台)
            |           |           |
           H1(T-A)   H2(T-A)+H3(T-B)  EXT(IOL・外部網)
        アンダーレイ: p2p /31 + Lo0/32 (OSPF or eBGP)・オーバーレイ: iBGP EVPN via RR
        テナントA: VLAN100/L2VNI10100・VLAN200/L2VNI10200・L3VNI50000
        テナントB: VLAN300/L2VNI10300・L3VNI50001（テナント分離の観察用）
```

- **案A（推奨・要PoC）**: SPINE=IOL（`address-family l2vpn evpn` の RR としてのみ動作・
  NVE/VTEP 機能は不要）。NX-OS は leaf 3台 = **36GB**。
- **案B（縮退）**: leaf 2台（border 機能を LEAF2 に同居）= **24GB**。IRB/anycast GW/
  マルチテナントは 2台でも全て成立。Type-5 も LEAF2 border 兼務で可。
- **案C（IOL RR 不成立時）**: SPINE も nxosv9300 → 3〜4台 = 36〜48GB。
  48GB は RAM 54.8GB に対し危険域なので、その場合は案B相当（NX-OS 3台上限）に落とす。

RAM 予算（案A・leaf3台）: NX-OS 36GB + IOL×2 + alpine×3 ≒ **38GB** / 54.8GB。
ただし他ラボ並行稼働はほぼ不可（SD-WAN 退避ラボ等と同時起動しないこと）。
20ノード上限は 8〜9台で余裕。ブート = NX-OS 約4.5分（並列）→ build 全体 7〜8分見込み。

## 4. PoC 項目（着手時に先行検証）

| # | 項目 | リスク | フォールバック |
|---|------|--------|----------------|
| 1 | **IOL (iol-xe-17-15) が l2vpn evpn AF の RR として NX-OS と interop するか**（RR での RT 保持挙動含む・`retain route-target all` 要否） | 中 | SPINE を NX-OS 化（案C→実質案B） |
| 2 | nxosv9300 で Symmetric IRB（L3VNI・VRF・`fabric forwarding anycast-gateway-mac`） | 低（本物9kの定番構成） | — |
| 3 | Type-5 注入（border leaf で外部 OSPF/static → EVPN 再配送） | 低 | — |
| 4 | ARP suppression の観察指紋（`show ip arp suppression-cache`） | 低 | 観察項目から外す |
| 5 | 採点収集: NX-OS SSH ＋ Genie パーサ（nxos は parser 充実）or raw | 低 | raw + regex |
| 6 | day0 焼き込みで feature〜NVE〜IRB 全量一発適用（前作は L2VNI まで実証済） | 低 | 段階投入 |

## 5. 出題形式（前作踏襲）

- ガイド付き教育ラボ（伴走・design.md §2.5 形式）＋採点フルサイクル（0/100→100/100）。
- 部構成案: 第1部=アンダーレイ＋EVPN CP 成立（RR 経由・PfxRcd 観察）／
  第2部=L2VNI ブリッジング（前作の復習を spine 経由で）／
  第3部=Symmetric IRB＋Anycast GW（サブネット間・本作の心臓）／
  第4部=マルチテナント or Type-5 外部接続／終章=LISP との実機対比考察。
- **意図的失敗 Phase 候補**（前作 Phase4 の系譜・指紋読解→是正）:
  - **L3VNI を NVE(interface nve1) に未登録** → 同一サブネットは通るのに
    サブネット間だけ 0%（`show nve vni` に L3VNI 不在・指紋明確・本命）
  - RT 不一致 → Type-2 は届くが import されない（`show bgp l2vpn evpn` にはあるのに
    `show l2route` に無い）
  - anycast-gateway-mac 片系未設定 → 端末移動で GW 死
- ヒント控えめ方針（ccnp-problem-hint-policy）適用。

## 6. 運用

- 前作 `topologies/sda_ops.py` の build/solve/grade/teardown 骨格を流用し
  `evpn_ops.py`（または sda_ops.py の汎用化）。静的 yaml リース焼込＋突合中止も踏襲。
- nxosv9300 day0 は「node 定義の boot workaround ブロック保持＋追記」方式（前作実証済）。

## 7. 未決事項

- ~~案A/B/C の確定~~ → **案A 確定（PoC で IOL RR interop 全✅）**
- テナント2つ入れるか（教材価値 vs 台数・RAM）— PoC はテナント1で実施。
  第4部をマルチテナントにするなら leaf の day0 に TENANT-B を足すだけ（PoC不要と判断）
- ~~アンダーレイ~~ → **OSPF 確定**（PoC も OSPF で実施・前作と統一）
- ARP suppression の扱い: PoC 罠1（TCAM 2段 reload）により本編から除外。
  終章の読み物 or 任意上級 phase（reload 待ち時間を許容できる人向け）に
