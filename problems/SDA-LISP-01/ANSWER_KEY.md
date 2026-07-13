# SDA-LISP-01 模範解答（出題者用・受講者非公開）

★実機検証済み（PoC 2026-07-13 → poc/sda-lisp/README.md、本問フルサイクル検証は README.md）。
一括投入は `python3 topologies/sda_ops.py solve`。

## 第1部 LISP編

### MSMR（Phase 1）

```
router lisp
 site SITE-A
  authentication-key CCNP
  eid-prefix 172.16.1.0/24
 site SITE-B
  authentication-key CCNP
  eid-prefix 172.16.2.0/24
 ipv4 map-server
 ipv4 map-resolver
```

### XTR1（Phase 2。XTR2 は 172.16.2.0/24 / 10.255.0.3 に読み替え）

```
router lisp
 database-mapping 172.16.1.0/24 10.255.0.2 priority 1 weight 100
 ipv4 itr map-resolver 10.255.0.1
 ipv4 etr map-server 10.255.0.1 key CCNP
 ipv4 itr
 ipv4 etr
 ipv4 use-petr 10.255.0.4        ← Phase 4 で追加
```

### PXTR（Phase 4）

```
router lisp
 ipv4 proxy-etr
 ipv4 proxy-itr 10.255.0.4
 ipv4 itr map-resolver 10.255.0.1
 instance-id 0
  service ipv4
   eid-table default
   map-cache 172.16.0.0/16 map-request   ← ★これが無いと戻り方向 0%（本問の山場）
```

**Phase 4 の意図的な失敗と指紋**（proxy-itr/proxy-etr のみの状態）:
- `show ip lisp` → `ITR local RLOC (last resort): *** NOT FOUND ***`
- `show lisp instance-id 0 ipv4 map-cache` → `% Could not find EID table instance ID 0`
- 原因: PITR に「LISP な宛先空間」を教える設定が無く、EXT からの戻りパケットで
  Map-Request が発火しない。静的 map-cache エントリがトリガを作る。
- ★構文罠: `ipv4 map-cache 172.16.0.0/16 map-request` は **Invalid**。
  この設定だけ階層構文（instance-id 0 → service ipv4 → eid-table default）が必要
  （router lisp 直下の `map-cache 〜` でも受理される）。

## 第2部 VXLAN編

### LEAF1（Phase 6-8。LEAF2 は router-id 10.254.0.2 / neighbor 10.254.0.1 に読み替え）

```
feature bgp
feature interface-vlan
feature vn-segment-vlan-based
feature nv overlay
nv overlay evpn
!
vlan 100
  vn-segment 10100
!
router bgp 65100
  router-id 10.254.0.1
  neighbor 10.254.0.2
    remote-as 65100
    update-source loopback0
    address-family l2vpn evpn
      send-community
      send-community extended
!
evpn
  vni 10100 l2
    rd auto
    route-target import auto
    route-target export auto
!
interface nve1
  no shutdown
  host-reachability protocol bgp
  source-interface loopback0
  member vni 10100
    ingress-replication protocol bgp
!
interface Ethernet1/2
  switchport
  switchport access vlan 100
  no shutdown
```

## 期待される観察結果（実測値）

| 観察 | 期待 |
|---|---|
| 観察1（MSMR のみ設定後） | `show lisp site` に SITE-A/B が Up=**no** で並ぶ |
| 観察2-2 | 両サイト Up=yes・`show lisp session` established: 2 |
| 観察3-1 | 初回 ping `..!!!`（2/5 前後）→ 2回目 5/5 |
| 観察3-2 | `172.16.2.0/24 via map-reply, complete / Locator 10.255.0.3` |
| 観察4-1 | ping 0%＋map-cache に `192.0.0.0/2 forward-native`・`Encapsulating to proxy ETR` |
| 観察4-3 | XTR→EXT・EXT→EID とも成功（初回落ち後 100%） |
| 観察7 | BGP EVPN ピア Up・PfxRcd 0（NVE 未作成のため広告物が無い） |
| 観察8-1 | `show nve peers` 相手 Lo0 Up/CP・Type-3 交換 |
| 観察8-2 | H1→H2 初回 ARP 1落ち→以降 100% |
| 観察8-3 | H1 MAC=Local / H2 MAC=BGP (Next-Hop 10.254.0.2, Label 10100) |

## 考察の答え（伴走トーク用の要点）

- **考察0**: EID を IGP に入れない＝経路表サイズを RLOC 数（≒スイッチ台数）に抑え、
  端末移動時も IGP 再収束が起きない（電話帳の書き換えだけで済む）。
- **考察2**: ルーティング＝全員へ事前配布、LISP＝必要時にオンデマンド解決。
  経路表に無くても「解決手段がある」ことが到達性になる。
- **考察3-1/3-2**: 初回落ち＝Map-Request/Reply の往復時間。MSMR はデータ転送に
  非関与（CP/DP 分離）。DNS と Web サーバの関係と同じ。
- **考察4-2**: Border Node の本質＝「電話帳の世界」と「経路の世界」の変換点。
- **考察6**: VNI 24bit＝VLAN 4094 制限の突破＋テナント毎の名前空間分離。
- **考察8**: pull（LISP・未知宛先に強い・WAN/移動端末向き）vs push（EVPN・既知
  メンバーに速い・DC 向き）。落ちた発数の差（2発 vs 1発）がその設計差の実測。
- **最終考察**: 本ラボで手打ちした行数 ≒ ノード1台あたり 30〜60 行。DNAC は
  これを機器追加のたびに自動生成・整合性維持している。
