# BL-022/023 — OSPF PE-CE バックドア＋sham-link / DNビット 設計メモ

作成 2026-07-09。**IOL-XE 17.15 実機PoC済（下記「PoC結果」）＝設計確定・実装可**。

> **【完了】BL-022 = 問題 `ENARSI-MPLS-L3VPN-03` として実装・実機フルサイクル済（2026-07-09）。**
> 未解答=40点／模範解答=100点収束（全16チェック）。判別チェック(sham-link UP×2・
> 経路がMPLS(PE)経由 RT04/RT05/RT01/RT03=52点)は未解答で全FAIL、環境保存チェック(E2E・
> バックドア隣接生存・制約=40点)はバックドア経由で成立しPASS。トポロジ=下記どおり
> RT04(e0/1)-RT05(e0/1) バックドア1本追加。採点は traceroute を廃し **経路の次ホップ**
> (192.168.1.2=PE1 / 192.168.2.2=PE2 / 遠端PE 3.3.3.3・1.1.1.1)で判定(traceroute は
> 収束リトライ中に遅く採点タイムアウトの原因になった)。実機確認: 初期=RT04 が
> `via 172.16.9.2(backdoor) metric 501 intra`、解答後=`via 192.168.1.2(PE) metric 61 intra`。
> BL-023(capability vrf-lite 裏返し)は未着手のまま。

土台は稼働中の **ENARSI-MPLS-L3VPN-02 完成形**（OSPF PE-CE / MP-BGP VPNv4 / VRF CUST_A・B）。

## 狙い（ENARSI 35%枠 直撃）

| 教えどころ | ENARSI目標 |
|---|---|
| バックドア(O intra)が MPLS(O IA)を無条件で負かす | 1.10.c/d OSPF網種別・path preference |
| DNビット/ドメインタグのループ防止 | 1.3 loop prevention |
| BGP⇄OSPF 相互再配布の挙動 | 1.4 redistribution |
| sham-link / domain-id で経路タイプ操作 | 2.2 describe MPLS L3VPN |
| （BL-023）capability vrf-lite の DNビット・ブラックホール | 1.7 VRF-Lite + 1.3 |

## 核心メカニズム（3段）

1. **経路タイプ優先はコストに勝つ**：CUST_A の site1(RT04)↔site2(RT05) に直結バックドア(area0,低速)を敷くと、
   対向LANはバックドア経由=**O intra**、MPLS経由=**O IA**。intra>inter なので**低速でもバックドアが必ず勝つ**。
   "コストを下げれば直る"では直らない、が体感の核心。
2. **sham-link で MPLS を intra 昇格**：`area 0 sham-link` で MPLS越しの対向LANも **O intra** 化。
   ここで初めて `sham-link cost` / IFコストで**意図どおりMPLS優先**にできる。sham-linkダウンで自動フォールバック。
3. **DNビット防護は維持**：PEの MP-BGP→OSPF 再配布はDNビットを立て、対向PEがBGPへ戻さない＝ループ防止。触らせない。

## トポロジ（7台流用＋リンク1本追加）

```
 CUST_A site1                                  CUST_A site2
   RT04(CE) ─ e0/0 ─┐                ┌─ e0/0 ─ RT05(CE)
      │ e0/1       RT01 ═ RT02 ═ RT03        e0/1 │
      └──────── バックドア(area0,低速) ────────────┘   ← 172.16.9.0/30 等・追加
   RT06 ─ CUST_B site1     CUST_B site2 ─ RT07             ← 対照群(バックドア無)
```
- 追加は **RT04(e0/1)—RT05(e0/1) 直結1本**のみ（IOLスロット内）。CUST_B は対照。

## 正解の骨子

1. 両PEの VRF CUST_A に **/32 ループバック（sham-link端点）**を作り **MP-BGPで広告（OSPFには載せない）**。
2. `router ospf 10 vrf CUST_A` に `area 0 sham-link <local> <remote> cost <n>`。
3. sham-link cost / バックドアIFコストで **MPLS経路 < バックドア経路** に。
4. DNビット既存挙動を維持（余計な `capability vrf-lite` を入れない）。

## 隠しひねり（task非開示）

- ★**sham-link端点/32を BGP→OSPF 再配布が拾うと recursion で張れない**（端点はBGP-onlyで到達必須）。
  L3VPN-02 は `redistribute bgp 65000`（route-mapなし）なので**端点がOSPFに漏れる**→端点除外route-map必須。
  **PoCで実証済**（下記）。
- sham-link を張っても **cost調整を忘れると優劣が変わらない**（形成≠優先）。
- **バックドアのコストだけ上げても、sham-link無しでは経路タイプ差で無効**（本丸の気づき）。
- domain-id を弄ると O E2 化して別の罠（E2はコスト非累積）。
- `capability vrf-lite` を安易に入れると DNビット防護無効＝ループ防止違反で減点。

## 採点設計

| 観点 | コマンド | 判定 |
|---|---|---|
| 経路タイプ昇格 | RT04 `show ip route 172.16.2.0` | `type intra area`（旧`inter area`から反転） |
| 実パス | RT04 `traceroute` | 第1ホップ=PE側（バックドアIFでない）raw照合 |
| sham-link確立 | RT01 `show ip ospf 10 sham-links` | `is up` / `State POINT_TO_POINT` / cost=設定値 raw |
| ループ防止健在 | RT01/RT03 `show bgp vpnv4 ...` | 対向site経路の再注入・振動なし |
| フォールバック | sham-link/コア片系ダウン→再確認 | バックドアIF経由へ切替 |

- パス優先・sham-link状態は **raw照合**（VPNv4はGenie不可の既知知見）。
- フォールバックは netmodel.py（軸1）で状態別検証の手もあり。

## PoC結果（2026-07-09・稼働中 L3VPN-02 上・RT01/RT03=PE, RT04=CE）

**全項目成功。ロールバックで100点状態に復元済。**

- ベースライン：RT04 の 172.16.2.0/24 = **`O IA`(inter area, metric21)**。domain-id 両PE一致(`0.0.0.10`)。
  VRF方式=`vrf definition`、PE-CE=`ip ospf 10 area 0`。
- sham-link投入（端点 1.1.110.1/3.3.110.1 を VRF Lo + BGP network、端点除外route-map、`area 0 sham-link ... cost 40`）：
  - `Sham Link OSPF_SL0 to 3.3.110.1 is up` / `State POINT_TO_POINT` / `Cost 40` / demand-circuit・DoNotAge ✅
  - 端点 `3.3.110.1/32 Known via "bgp 65000" ... MPLS label 21`＝**OSPFに漏れず（route-map有効）recursion回避** ✅
  - RT01: 172.16.2.0/24 が `bgp internal` → **`ospf 10 intra area`（MPLS越しintra）** ✅
  - **RT04: `inter area`(O IA) → `intra area`(O) 反転** ✅（本丸）
- IOS癖メモ：`no area 0 sham-link A B cost 40` は**costオプションだけ剥がれ本体が残る**（redistribute route-map と同じ）。
  削除は `no area 0 sham-link A B`（cost無し）。

## BL-023（裏返し変種）★完成＝問題 ENARSI-VRFLITE-DNBIT-01（2026-07-10 実機フルサイクル済）

多段VRF-lite（MPLS無）で上流がDNビット付きLSAを出し、下流VRFルータが防護で破棄→**ブラックホール**。
修正=`capability vrf-lite`。純IOS・IOL確実・1.7＋1.3直球。BL-022とセットでDNビットの表裏を教える。

**実装・実機検証（2026-07-10・IOL-XE 17.15・3ノード）**：
- 構成: RT01(Site A 172.20.20.0/24 を eBGP で起点) → RT02(eBGP受信を `router ospf 10 vrf RED / redistribute bgp` で
  VRF内OSPFへ相互再配布) → RT03(Site B 172.30.30.0/24 収容・`router ospf 10 vrf RED` の被害者)。全リンク VRF RED。
- ★**MPLS無し・純VRF-Lite でも DNビットが立つ**ことを実機確認：RT02 が redistribute bgp→ospf(vrf) で生成する
  Type-5 外部LSAに **`Options: (... Downward)`（DNビット）＋ドメインタグ(例3489725928)** が付く。
- RT03(VRF内OSPF)はそれをループ防止で破棄 → `show ip route vrf RED 172.20.20.0` = **`% Network not in table`**
  （`show ip ospf N database external` にはLSAが在る＝「DBにあるがRIBに無い」シグネチャ）→ ping 0%。
- 修正 = RT03 の `router ospf 10 vrf RED` に **`capability vrf-lite`** 一発 → RIB搭載(`Known via "ospf" type extern 2`)・ping 100%。
- 採点: 未解答48点/模範解答100点（判別52点=RIB搭載18+E2E22+capability12）。RT03のみ操作・static禁止でOSPF解に強制。
- 表裏の教育: **同じDNビットが、VRF-Lite では過剰防護→`capability vrf-lite`で解除／MPLS-VPN(BL-022) では必須防護→維持(禁止)**。

## 実装順

1. build_topology に RT04-RT05 バックドアリンク追加した派生トポロジを用意（L3VPN-02 initial 流用＋1リンク＋CEにバックドアIF/area0）。
2. initial に「バックドア開通済み・MPLS未優先」状態を焼く。
3. grading.yml：上表の checks を実装（sham-link raw / route-type / traceroute / フォールバック）。
4. 実機1サイクル（注入→採点0点付近→正解投入→100点）。
5. 完了後 BL-022 を完了アーカイブへ。
