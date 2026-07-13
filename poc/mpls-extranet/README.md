# MPLS Extranet / 共有サービス VRF PoC (BL-051 先行) — 結果 (2026-07-12)

MPLS-SERIES.design.md BL-051 の先行 PoC。IOL (iol-xe-17-15-01) 上で
①vrf af `export map` の RT 付与セマンティクス（±additive）②素朴解の重複 prefix 衝突
③RT300 配布の基本配管 を実機測定。**全項目成立 → ENARSI-MPLS-L3VPN-06 は設計どおり実装可**。

## 検証環境（poc-mplsext-lab.yaml・最小2台）

- PE1 = 顧客側: VRF CUST_A (rd 65000:100) / CUST_B (rd 65000:200)。CE 経路は
  VRF Loopback + `redistribute connected` で模擬（A: 172.16.1.1/24 + 10.65.1.1/24,
  B: 172.16.1.9/24 + 10.66.1.1/24 — 172.16 は A/B 重複）。
- PE2 = 共有側: VRF SVCS (rd 65000:300, export 300 / import 301) + LAN 172.30.0.1/24。
  additive 検証用に VRF CUST_A も併設。コアは OSPF/LDP/VPNv4 直結。
- MGMT リースは mgmt_alloc.py（.20/.31）。検証後 stop/wipe/remove・リース解放済み。

## 結果マトリクス

| # | 項目 | 結果 |
|---|------|------|
| E1 | ベースライン | ✅ SVCS は import 301 に何もマッチせず自 LAN のみ。顧客 VRF 正常 |
| E2 | **export map（additive 無し）= 罠の指紋** | ✅ **既定 RT が置換されて消える**。マッチした 10.65.1.0/24 の Extended Community が `RT:65000:301` のみになり（RT:100 消失）、**対向 PE の CUST_A から経路消失**。非マッチの 172.16 は既定 RT 維持で無傷 = 部分故障。SVCS へは届く（301 で import） |
| E3 | `set extcommunity rt 65000:301 additive` | ✅ `RT:65000:100 RT:65000:301` 併記・CUST_A の経路即復活。**additive が正解形** |
| E5 | 素朴解: SVCS が RT100/200 を直 import | ✅ **重複 172.16.1.0/24 は片方だけが無言で勝つ**（今回 65000:200 版。`imported path from 65000:200:...` 表示・代替パスとしても残らない `Paths: (1 available)`）→「監視が A のつもりで B に届く」事故の実機再現。チケット要件「共有 VRF に重複 prefix を持ち込まない」の必然性の裏付け |
| E6 | RT300 配布 + 分離 | ✅ 顧客 VRF は `route-target import 65000:300` 追加のみで 172.30.0.0/24 を受信。A↔B 分離は構造維持。★export map の無い顧客の利用セグメントは SVCS に届かない = **全 PE への export map 展開が判別チェックとして機能** |

## ★採点・解説用の実機指紋

1. **additive 忘れ**（config 指紋・debug 不要）:
   `show bgp vpnv4 unicast all 10.65.1.0` →
   `Extended Community: RT:65000:301`（**RT:65000:100 が無い**）＋対向 PE の顧客 VRF から
   当該 /24 消失。正解形は `RT:65000:100 RT:65000:301` 併記。
2. **重複衝突**（素朴解）: SVCS の `show bgp vpnv4 unicast vrf SVCS 172.16.1.0/24` →
   `Local, imported path from 65000:200:172.16.1.0/24` = どちらの顧客の経路かが
   import 元 RD で読める。勝敗は非決定的（ベストパス次第）。
3. export map の permit/match に**掛からない経路は既定 RT のまま正常に export される**
   （export map はフィルタではなく RT 変更のみ・実機確認済）。

## 設計への反映（ENARSI-MPLS-L3VPN-06）

- 設計変更なしで実装可（MPLS-SERIES.design.md BL-051 節のまま）。
- 採点: additive 拘束は「利用セグメントのサイト間 E2E」＋（補助的に）
  `show bgp vpnv4` の Extended Community 併記 regex が使える。
- solution.md の解説素材: E5 の衝突出力（片顧客 silently 不達）を再現手順ごと記載する。

## 再現手順

```
python3 topologies/mgmt_alloc.py allocate --repo . --problem POC-MPLSEXT --nodes PE1,PE2
# poc-mplsext-lab.yaml を CML へ import して start
# プローブ: python3 poc/mpls-hubspoke/probe.py <mgmt-ip> "<cmd>" ...
# 撤収: stop/wipe/remove + mgmt_alloc.py release --problem POC-MPLSEXT
```
