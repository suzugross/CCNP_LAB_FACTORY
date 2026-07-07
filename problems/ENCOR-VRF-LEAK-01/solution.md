# 模範解答 ENCOR-VRF-LEAK-01 （RT01 のみ）

```
! --- VRF 定義 + ルートターゲット(hub-spoke リーク) ---
vrf definition RED
 rd 65000:1
 address-family ipv4
  route-target export 65000:1
  route-target import 65000:100
 exit-address-family
!
vrf definition BLUE
 rd 65000:2
 address-family ipv4
  route-target export 65000:2
  route-target import 65000:100
 exit-address-family
!
vrf definition SHARED
 rd 65000:100
 address-family ipv4
  route-target export 65000:100
  route-target import 65000:1
  route-target import 65000:2
 exit-address-family
!
! --- インタフェース割当 ---
interface Ethernet0/0
 vrf forwarding RED
 ip address 10.1.12.1 255.255.255.252
 no shutdown
interface Ethernet0/1
 vrf forwarding BLUE
 ip address 10.2.12.1 255.255.255.252
 no shutdown
interface Loopback100
 vrf forwarding SHARED
 ip address 100.64.0.1 255.255.255.255
!
! --- PE-CE 経路(顧客拠点を学習) ---
ip route vrf RED 172.16.1.0 255.255.255.0 10.1.12.2
ip route vrf BLUE 172.16.2.0 255.255.255.0 10.2.12.2
!
! --- BGP で VRF 間リーク(RT で制御) ---
router bgp 65000
 ! ★全IFがVRF収容でグローバルIPが無い → router-id を手動指定しないと
 !   「% BGP cannot run because the router-id is not configured」でBGPが起動せずリークが走らない
 bgp router-id 10.255.255.1
 address-family ipv4 vrf RED
  redistribute connected
  redistribute static
 exit-address-family
 address-family ipv4 vrf BLUE
  redistribute connected
  redistribute static
 exit-address-family
 address-family ipv4 vrf SHARED
  redistribute connected
 exit-address-family
```

## ポイント / 教育核心
- **ルートターゲットの hub-spoke 設計**がリーク制御の本質。
  - SHARED は `export 65000:100` / `import 65000:1, 65000:2` → 両顧客を取り込み、自分を両顧客へ配る。
  - RED は `export 65000:1` / `import 65000:100` → SHARED だけ取り込む（BLUE の `65000:2` は import しない）。
  - BLUE も同様に SHARED のみ。**RED と BLUE は互いの RT を import しない＝分離**。
- VRF 間のリークは BGP の VPN テーブルで RT に基づき行われる。**同一ルータ内なので MPLS 不要**
  （ローカル import、転送も同一筐体内 CEF で成立）。
- `redistribute connected`(SHARED Lo / transit) と `redistribute static`(PE-CE 経路) を BGP VRF AF に入れて
  リーク対象にする。これが無いと RT を付けても配るルートが BGP に乗らない。
- **★最大の落とし穴 = `bgp router-id`**：全インタフェースが VRF 内でグローバル table に IP が無いと、
  BGP は router-id を自動選定できず `% BGP cannot run because the router-id is not configured` で
  **プロセスが起動しない**（RT import の痕跡は VPNv4 テーブルに出るが RIB に落ちない）。`bgp router-id` を手動指定する。
- 同一筐体内なので **MPLS 不要**。RT import が VRF 間でローカルに成立し、`B 100.64.0.1 ... via Loopback100` のように
  他 VRF のインタフェースを次ホップに RIB へ載る。
- 確認:
  - `show ip route vrf RED` に `100.64.0.1/32`（B、SHARED 由来）/ BLUE 経路は無い
  - `show ip route vrf SHARED` に `172.16.1.0/24` と `172.16.2.0/24`
  - `ping vrf RED 100.64.0.1`（成功）/ `ping vrf RED 172.16.2.1`（失敗）
