# SD-Access 中核技術（LISP / VXLAN）再現可否 PoC — 結果 (2026-07-13)

SDA-LISP.design.md (BL-054) の先行 PoC。**結論: 両方とも再現可能・作問可**。

- **Tier1 = Classic LISP ファブリック**: iol-xe-17-15-01 で `router lisp` **完全動作**
  （MS/MR・xTR・PxTR・PETR/PITR・EID間疎通・非LISPドメイン相互到達まで全✅）。
- **Tier2A = EVPN-VXLAN**: nxosv9300-10-5-1-f ×2 で **day0 焼き込み一発成立**
  （iBGP EVPN・NVE CP学習・L2VNI 越しのホスト間疎通✅）。

## 検証環境（poc-sdalisp-lab.yaml・9台＝IOL×7 + NX-OS×2）

```
[LISP]   XTR1(EID 172.16.1.0/24)   XTR2(EID 172.16.2.0/24)
              └──── MSMR(MS/MR・OSPFハブ) ────┘
                      │
                    PXTR(PETR/PITR) ── EXT(非LISP 198.51.100.0/24)
         アンダーレイ: OSPF area0 で RLOC(Lo0 10.255.0.1-4/32) のみ広告。EID は広告しない。

[VXLAN]  H1(172.16.100.11) ─ LEAF1 ═(VNI 10100 / iBGP EVPN AS65100)═ LEAF2 ─ H2(.12)
         アンダーレイ: 10.0.99.0/30 + Lo0 10.254.0.1-2/32 (OSPF)。ホストは iol-xe 代用。
```

- 既存9ノードラボ(GEN-BGPCX-5291)と並行稼働で問題なし（unmanaged_switch/ext-conn は
  VM数に入らない＝20ノード上限はデバイス数で数えてよいことを running_vms で確認）。
- NX-OS は RAM 12GB/台・ブート約4.5分。IOL 7台は約1分で全起動。
- 検証後 stop/wipe/remove・リース(.37-.45)解放済み。本 yaml で再構築可。

## 結果マトリクス

| # | 項目 | 結果 |
|---|------|------|
| 1 | iol-xe 17.15 `router lisp` 構文受理 | ✅ **クラシック構文が全て素通り**（site/authentication-key/eid-prefix・database-mapping・ipv4 itr map-resolver・ipv4 etr map-server ... key・ipv4 itr/etr・ipv4 use-petr・ipv4 map-server/map-resolver・ipv4 proxy-etr/proxy-itr）。SSH ライブ投入で確認 |
| 2 | Map-Register 成立 | ✅ 投入直後に SITE-A/B 登録（reliable transport）。`show lisp session` established・`show lisp site` に Who Last Registered=各RLOC |
| 3 | map-cache オンデマンド学習 | ✅ EID間 初回 ping **2/5 ドロップ→map-reply 学習→100%**（LISP の本質が見える教育的指紋）。TTL 24h |
| 4 | EID間データプレーン | ✅ XTR1↔XTR2 100%。traceroute は「アンダーレイ1hop→宛先」（encap で中間が隠れる様子が見える） |
| 5 | PxTR（PETR/PITR）非LISP相互到達 | ✅ 双方向 100%。ただし★下記の罠1を踏んで是正 |
| 6 | 負の map-reply | ✅ 非LISP宛は `192.0.0.0/2 ... forward-native / Encapsulating to proxy ETR` が map-cache に入る（use-petr の指紋） |
| 7 | nxosv9300 day0 焼き込み | ✅ node定義の boot workaround ブロック保持＋追記方式で、feature 群〜EVPN〜NVE まで全量一発適用 |
| 8 | EVPN コントロールプレーン | ✅ iBGP l2vpn evpn UP・Type-2(MAC)/Type-3(IMET) 交換・`show nve peers` LearnType=CP・`show nve vni` 10100 Up |
| 9 | VXLAN データプレーン | ✅ H1↔H2 ping 成立（初回 ARP で1ドロップのみ）。`show l2route evpn mac all` にリモートMAC=BGP産・Label 10100 |

## ★実機で踏んだ罠（作問・伴走時の素材）

### 罠1: PxTR は proxy-itr/proxy-etr だけでは戻り方向が死ぬ

- 症状: xTR→EXT・EXT→EID とも 0%。制御面（負のmap-reply）は正常に見える。
- 指紋: PXTR の `show ip lisp` に **`ITR local RLOC (last resort): *** NOT FOUND ***`**、
  `show lisp instance-id 0 ipv4 map-cache` が **`% Could not find EID table instance ID 0`**。
- 原因: PITR が「どの宛先空間が LISP か」を知らず map-request を発火できない。
- 対処: **静的 map-cache エントリ** `map-cache 172.16.0.0/16 map-request` を投入
  （router-lisp 直下 or `instance-id 0`→`service ipv4`→`eid-table default` 配下）。
  ★クラシック形 `ipv4 map-cache ...` は **Invalid**（他の ipv4 系は通るのにこれだけ新構文）。
- 投入後: EXT→EID 初回 83%→100%、xTR→EXT も 100% に収束。

### 罠2（軽微）: show コマンドの deprecation 案内

- `show lisp site` / `show ip lisp map-cache` は動くが毎回 deprecation バナーが出る。
  正式は `show lisp instance-id 0 ipv4 server` / `show lisp instance-id 0 ipv4 map-cache`。
  採点で raw パースする場合はバナー混入に注意（Genie パーサ有無は未確認→採点実装時に確認）。

## 採点・観察に使える show（実測済み）

- MSMR: `show lisp site`（登録状態）・`show lisp session`（reliable transport established）
- xTR: `show lisp instance-id 0 ipv4 map-cache`（オンデマンド学習・negative entry・PETR encap）
- xTR: EID 間 ping は **必ず `source Loopback1`**（EID ソース。アンダーレイソースは LISP に乗らない）
- LEAF: `show bgp l2vpn evpn summary`（Type-2/3 カウント列あり）・`show nve peers`・
  `show nve vni`・`show l2route evpn mac all`

## 作問への示唆

- Tier1 LISP は **iol-xe 5台で軽量に成立**（cat8000v フォールバック不要と確定）。
  ガイド付き教育ラボ（design.md §2.5）の Phase 構成にそのまま使える。
  「初回 ping がドロップ→map-cache が埋まる」を観察チェックポイントの目玉に。
- 罠1 は上級ひねり（PxTR Phase）として最適: 制御面は正常・データ面だけ死ぬ、指紋も明確。
- Tier2A VXLAN は nxosv9300 2台+ホスト2台で最小成立。LISP(制御面の思想) と
  VXLAN(encapの実像) を別セクションで体感させる2部構成が現実的。
- cat9000v（真SDA・VXLAN-GPO）は未検証のまま（優先度低・Tier1/2A で教育目的は充足）。
