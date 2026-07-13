# EVPN-VXLAN ファブリック 案A 再現可否 PoC — 結果 (2026-07-13)

EVPN-VXLAN.design.md (BL-055) の先行 PoC。**結論: 案A 成立・作問可**。

- **★最重要項目 = IOL を l2vpn evpn RR にする案A**: iol-xe-17-15-01 の
  `address-family l2vpn evpn` が day0 で素通りし、NX-OS leaf ×2 と **完全 interop**。
  Type-2/3/5 全てを反射し、RMAC 拡張コミュニティも透過。
  **`no bgp default route-target filter` 不要**（既定で全保持・全反射）。
- Symmetric IRB（L3VNI）・Distributed Anycast GW・Type-5 border まで **day0 一発成立**。
- NX-OS は leaf 2台 =24GB のみ。フル教材の leaf 3台でも 36GB で収まる見込み。

## 検証環境（poc-evpn-lab.yaml・9台＝IOL×5 + NX-OS×2 + MGMTSW/EXTC）

```
              SPINE (iol-xe・EVPN RR・VTEPなし・Lo0 10.254.0.254)
             /                        \
      10.0.1.0/30                 10.0.2.0/30        ← アンダーレイ OSPF area0
           /                            \
   LEAF1 (nxosv9300)              LEAF2 (nxosv9300・border)
   Lo0 10.254.0.1                 Lo0 10.254.0.2
     |                              |         \            \
   H1(VLAN100)                 H2(VLAN100)  H3(VLAN200)   EXT(iol-xe)
   172.16.100.11               .100.12      .200.13        192.168.100.0/30
                                                           Lo1 198.51.100.0/24
オーバーレイ: AS65100 iBGP EVPN via SPINE RR
  VLAN100/L2VNI10100=172.16.100.0/24・VLAN200/L2VNI10200=172.16.200.0/24
  L3VNI=VLAN500/VNI50000・vrf TENANT-A・anycast GW .1 / MAC 0000.2222.3333
MGMT: SPINE=.20 LEAF1=.31 LEAF2=.32 H1=.33 H2=.34 H3=.35 EXT=.36
```

- リースは mgmt_alloc.py に POC-EVPN で登録（.20, .31-.36）。検証後 release 済み。
- NX-OS day0 は「boot workaround ブロック保持＋追記」方式（SDA-LISP PoC と同じ）。
- ブート: IOL 約1分・NX-OS 約4.5分。build 全体約6分。

## 結果マトリクス

| # | 項目 | 結果 |
|---|------|------|
| 1 | IOL `address-family l2vpn evpn`（RR 構成）day0 受理 | ✅ 全行素通り。`show bgp l2vpn evpn summary` で両 leaf Established |
| 2 | ★IOL RR → NX-OS 反射 | ✅ LEAF1 が RR 経由で 7 経路受信（**Type-2×4 / Type-3×2 / Type-5×1**）。NX-OS 側 summary に Type 別カウント列があり観察に最適 |
| 3 | RMAC 拡張コミュニティ透過 | ✅ `show nve peers` に Router-Mac 表示・LearnType=CP |
| 4 | RT フィルタ | ✅ **`no bgp default route-target filter` 不要**（IOS-XE RR は既定で全保持） |
| 5 | L2VNI データプレーン（H1↔H2 同一サブネット・leaf 跨ぎ） | ✅ 初回 ping 4/5（ARP glean で1ドロップ→100%。教育的指紋） |
| 6 | Symmetric IRB（H1↔H3 サブネット間・L3VNI 50000） | ✅ 100%。`show ip route vrf TENANT-A` にリモート /32 が `segid: 50000 encap: VXLAN` で載る（Type-2 ホストルート） |
| 7 | Distributed Anycast GW | ✅ H1 の `show ip arp 172.16.100.1` = **0000.2222.3333**（設定した anycast MAC） |
| 8 | Type-5 外部経路（LEAF2 border・redistribute static route-map） | ✅ H1→198.51.100.1 100%。LEAF1 に 198.51.100.0/24 が Type-5 で着信 |
| 9 | `show l2route evpn mac all` | ✅ Local/BGP(SplRcv)/Rmac が一覧で見える（採点素材） |
| 10 | ARP suppression（ライブ投入） | ✅ **最終的に完全動作**（suppression-cache に Local + Remote(VTEP) 両エントリ・疎通も維持）。ただし★下記の罠= TCAM carving＋reload ダンスが必要 |

## ★実機で踏んだ罠（作問・伴走時の素材）

### 罠1: suppress-arp は TCAM carving なしでは投入できない（nxosv9300 も実機 N9K と同じ挙動）

- `suppress-arp` → `ERROR: Please configure TCAM region for Ingress ARP-Ether ACL before configuring ARP supression.`
- `hardware access-list tcam region arp-ether 256 double-wide` → `ERROR: Aggregate TCAM region configuration exceeded the available Ingress TCAM slices.`
  （既定は racl=1536 でスライス満杯）
- racl を縮めて空ける必要があるが、★**racl 1024 では不足**（QoS 系 256×3 が残るため）。
  **racl 512 まで縮めて初めて arp-ether 256 double-wide が受理**された（double-wide は実質1024消費）。
- ★さらに carve の検証は **running の pending 値でなくアクティブ値**に対して行われるため、
  racl 縮小を投入した直後に arp-ether carve を続けても同じエラーで弾かれる。
  → **確定手順（実証済み）**: ①`racl 512`→save→reload ②`arp-ether 256 double-wide`→save→reload
  ③`suppress-arp`（即受理・reload不要）。**最低2段 reload**（各4.5分）。
- 投入後の動作は完全: `show ip arp suppression-cache detail` に
  **L(Local)=172.16.100.11 と R(Remote)=172.16.100.12 via 10.254.0.2** の両エントリ、疎通も維持。
- 作問への示唆: day0 焼き込みは同じ順序制約を受ける可能性が高い（1st boot のアクティブ値=既定。
  racl 512 と arp-ether carve を両方 day0 に書けば2行目だけ弾かれ、2nd boot で成立する可能性はあるが未検証）。
  suppress-arp を教材に入れるなら「TCAM ダンス自体を上級ひねり」にするか、観察のみ・任意phaseに退避が現実的。

## 採点・観察に使える show（実測済み）

- LEAF: `show bgp l2vpn evpn summary`（★Type-2/3/4/5/12 のカウント列つき — 中間観察の目玉）
- LEAF: `show nve peers`（LearnType=CP・Router-Mac）・`show nve vni`（L2/L3 の別・UnicastBGP）
- LEAF: `show ip route vrf TENANT-A`（リモート /32 = Type-2 ホストルート・`segid: 50000 encap: VXLAN` が
  symmetric IRB の指紋・Type-5 の外部プレフィクスも同形式）
- LEAF: `show l2route evpn mac all`（Local / BGP SplRcv / Rmac）
- SPINE(IOL): `show bgp l2vpn evpn summary`・`show bgp l2vpn evpn`（RR 視点の全経路・RD 別）
- ホスト: `show ip arp <GW>` = anycast MAC 0000.2222.3333（distributed anycast GW の証拠）

## 作問への示唆

- **案A 確定**: SPINE=IOL RR で NX-OS を leaf 分だけに抑えられる（本 PoC 2台=24GB、教材 3台=36GB）。
- 初回 ping の ARP glean 1ドロップは LISP 編（map-request 2ドロップ）との対比でそのまま使える。
- 意図的失敗 Phase の本命「L3VNI の NVE 未登録」は本 PoC では未注入（構成要素は全て実証済みのため
  本実装の中間観察検証で実施予定）。
- suppress-arp は罠1のとおり2段 reload が必要 → 本編からは外し、終章の読み物 or 任意上級 phase に。
