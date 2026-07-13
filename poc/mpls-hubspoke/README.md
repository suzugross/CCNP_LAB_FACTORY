# MPLS L3VPN ハブ&スポーク折返し PoC (BL-016 Phase 1) — 結果 (2026-07-12)

MPLS-SERIES.design.md BL-016 の先行 PoC。IOL (iol-xe-17-15-01) 上で
①非対称 RT の H&S 基本動作 ②hub CE 折返し（spoke↔spoke を hub 経由で通す）の
成立方式を実機測定。**結論: 案1(単一セッション折返し)は IOS の送信側抑止で不成立、
案3改め本命の「dot1q subif 2セッション + 2VRF half-duplex + allowas-in」で完全成立**。
→ 手組み ENARSI-MPLS-L3VPN-05 は via-hub 形で実装可。

## 検証環境（poc-mplshs-lab.yaml・6台）

```
              CEH (AS65201, hub LAN 172.16.1.0/24)
               │ 192.168.1.0/30 (→subif .10/.20 に分割)
              PE1 (hub PE)
     10.0.12/30 ┌┴┐ 10.0.13/30     コア: OSPF area0 + LDP + VPNv4 フルメッシュ
              PE2   PE3
               │     │
             CES1   CES2 (spoke LAN 172.16.2/3.0/24, AS65202/65203)
```

- sdwan-poc(9ノード) と共存のため 12台でなく最小6台（9+6=15 ≦ 20上限・RAM free 48GB）。
- RT 設計（day0 焼き込み）: hub PE = export 65000:210 / import 65000:220、
  spoke PE = export 220 / import 210。RD は PE 毎に別値 (65000:201/202/203)。
- MGMT リースは mgmt_alloc.py（.20, .31-.35）。検証後 stop/wipe/remove・リース解放済み。

## 結果マトリクス

| # | 項目 | 結果 |
|---|------|------|
| 0 | 非対称 RT の H&S 基本動作 | ✅ spoke↔hub 100% / spoke↔spoke 0%（spoke PE の VRF に対向 spoke LAN が**経路ごと無い**）。制御面・データ面とも設計どおり |
| 1 | 単一セッション折返し（CEH が学習元セッションへ再広告するか） | ❌ **不成立**。CEH は spoke 経路を BGP table に持つのに、学習元ピア 192.168.1.1 への advertised-routes は自 LAN 1本のみ。**IOS の送信側ループ抑止は「学習元ピアへ送り返さない」= ピア(セッション)単位**。PE 側 allowas-in では救えない（送信側で止まるため） |
| 2 | 別セッションへの再広告（送信抑止が AS 単位か） | ✅ **AS 単位ではない**。同じ AS65000 の別ピア(192.168.1.5)へは AS_PATH に 65000 を含む spoke 経路も広告する → 2セッション折返しの成立条件クリア |
| 3 | PE 受信側ループ検知と allowas-in | ✅ allowas-in 無し: DENIED（下記指紋）。`allowas-in 1` 投入で受理（path 内の自ASは1回なので 1 で十分） |
| 4 | E2E / データ面折返し | ✅ spoke1↔spoke2 双方向 100%・hub↔spoke 100%。subif 2本なので同一物理 IF のヘアピンだが in/out は別サブ IF・問題なし |
| 5 | IOL の dot1q subif ライブ追加 | ✅ wipe 不要。`no vrf forwarding`→subif 化をライブ投入で成立（IOSv の物理 IF 追加とは違い再起動不要） |

## ★実機指紋（採点・解説用素材）

1. **PE1 のループ検知 DENIED（allowas-in 欠落時）** — ★PE の VRF セッションでは
   `debug ip bgp updates in` でなく **`debug bgp all updates in`** でないと出ない:
   ```
   BGP(0): 192.168.1.6 rcv UPDATE w/ attr: ... merged path 65201 65000 65202, ...
   BGP(0): 192.168.1.6 rcv UPDATE about 172.16.2.0/24 -- DENIED due to: AS-PATH contains our own AS;
   ```
2. **DENIED 経路は soft-reconfiguration inbound でも received-routes に現れない**
   （ループ検知は adj-RIB-in 格納前に破棄）。「CEH の advertised-routes には在るのに
   PE の received-routes にすら無い」— 04 の PE/CE 突き合わせのさらに一段深い版。
3. **spoke CE から見た対向 spoke の AS_PATH = `65000 65201 65000 65203`**
   （hub AS 挟み込み・65000 が2回）。raw regex で折返し経由を制御面から拘束可能。
4. **traceroute の折返しホップ**（CES1→CES2, 採点で raw 拘束可能）:
   ```
   1 192.168.2.1  2 192.168.1.5 [MPLS: Label]  3 192.168.1.6  4 192.168.1.1  5 192.168.3.1 [MPLS: Label]  6 192.168.3.2
   ```
   hop2→3 が PE1(UP subif)→CEH、hop3→4 が CEH→PE1(DOWN subif) の折返し。
5. **hub PE の 2VRF 完成形**（正解 config の核・詳細は下記）。

## 完成形 config（PE1 / CEH の要点）

```
! PE1 (hub)
vrf definition CUST_B          ! DOWN: spoke経路を受けて CE へ降ろす
 rd 65000:201
 address-family ipv4
  route-target import 65000:220   ! export 無し
vrf definition CUST_B_UP       ! UP: CE から折返しを受けて spoke へ配る
 rd 65000:2011
 address-family ipv4
  route-target export 65000:210   ! import 無し
interface Ethernet0/2.10
 encapsulation dot1Q 10
 vrf forwarding CUST_B
 ip address 192.168.1.1 255.255.255.252
interface Ethernet0/2.20
 encapsulation dot1Q 20
 vrf forwarding CUST_B_UP
 ip address 192.168.1.5 255.255.255.252
router bgp 65000
 address-family ipv4 vrf CUST_B
  neighbor 192.168.1.2 remote-as 65201 / activate
 address-family ipv4 vrf CUST_B_UP
  neighbor 192.168.1.6 remote-as 65201 / activate
  neighbor 192.168.1.6 allowas-in 1        ! ★これが無いと DENIED（指紋1）

! CEH (hub CE) — 2セッション張るだけ。フル BGP table を両セッションに広告
interface Ethernet0/0.10 / .20 (192.168.1.2 / 192.168.1.6)
router bgp 65201
 network 172.16.1.0 mask 255.255.255.0
 neighbor 192.168.1.1 remote-as 65000
 neighbor 192.168.1.5 remote-as 65000
```

経路フロー: spoke PE --(RT220)--> PE1:CUST_B --(eBGP .10)--> CEH --(eBGP .20)-->
PE1:CUST_B_UP --(RT210)--> spoke PE。hub LAN も UP 経由で spoke へ届く
（DOWN は export 無しなので二重広告なし）。

## 設計への反映（ENARSI-MPLS-L3VPN-05）

- **via-hub 折返し形で実装可**（フォールバック案2は不要）。
- 受験者作業の核: ①CUST_B の RT 非対称化（監査是正） ②hub PE の 2VRF + subif 分割
  ③allowas-in（DENIED 指紋から到達させる隠しひねり）。
- subif 分割はライブ投入可なので、初期状態は「単一リンク・全対称 RT」で焼き、
  是正チケットで subif 化まで受験者にやらせる構成が可能（wipe 不要 = IOL で成立）。
- 採点素材: 指紋 3(AS_PATH)・4(traceroute hop 列)・spoke PE VRF の
  「hub 経路**在** AND 対向 spoke 経路**無**」複合チェック（PoC-0 で確認済みの状態）。
- 注意: task/ヒントで allowas-in・2VRF を先に明かさない（hint policy）。
  ただし CE 側 2セッション（CEH の subif/neighbor）は「顧客が用意済み」として
  day0 に焼く方が良い — CE は顧客管理・変更禁止の建付け（04 と整合）のため。
  ★その場合 PE 側 subif 分割は受験者作業として残る。

## 再現手順

```
# 起動 (mgmt_alloc.py で 6 リース確保後、YAML の IP を合わせる)
python3 topologies/mgmt_alloc.py allocate --repo . --problem POC-MPLSHS --nodes PE1,PE2,PE3,CEH,CES1,CES2
# CML へ import して start (poc-mplshs-lab.yaml)
# プローブ: python3 poc/mpls-hubspoke/probe.py <mgmt-ip> "<cmd>" ...
# 撤収: lab.stop() → wipe → remove、mgmt_alloc.py release --problem POC-MPLSHS
```
