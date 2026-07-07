# 模範解答 ENCOR-VRF-NAT-01 （RT01 のみ）

```
! --- VRF 定義 ---
vrf definition RED
 rd 65000:1
 address-family ipv4
 exit-address-family
vrf definition BLUE
 rd 65000:2
 address-family ipv4
 exit-address-family
!
! --- インタフェース(inside=顧客 / outside=ISP global) ---
interface Ethernet0/0
 vrf forwarding RED
 ip address 10.1.13.1 255.255.255.252
 ip nat inside
 no shutdown
interface Ethernet0/1
 vrf forwarding BLUE
 ip address 10.2.14.1 255.255.255.252
 ip nat inside
 no shutdown
interface Ethernet0/2
 ip address 100.64.0.1 255.255.255.252
 ip nat outside
 no shutdown
!
! --- NAT 対象 ACL(顧客サブネット) ---
ip access-list standard NAT-RED
 permit 10.0.0.0 0.0.0.255
ip access-list standard NAT-BLUE
 permit 10.0.0.0 0.0.0.255
!
! --- VRF対応 PAT(vrf 修飾で重複アドレスを区別) ---
ip nat inside source list NAT-RED interface Ethernet0/2 vrf RED overload
ip nat inside source list NAT-BLUE interface Ethernet0/2 vrf BLUE overload
!
! --- 顧客サブネット到達 ---
ip route vrf RED 10.0.0.0 255.255.255.0 10.1.13.2
ip route vrf BLUE 10.0.0.0 255.255.255.0 10.2.14.2
!
! --- ★VRF から global(ISP)へ抜ける default(global キーワード) ---
ip route vrf RED 0.0.0.0 0.0.0.0 100.64.0.2 global
ip route vrf BLUE 0.0.0.0 0.0.0.0 100.64.0.2 global
```

## ポイント / 教育核心
- **VRF対応 NAT の肝 = `ip nat inside source list ... vrf <名> overload`**。`vrf` 修飾子で
  「どの VRF の inside か」を区別する。これにより **両顧客の重複アドレス `10.0.0.1` が
  別エントリとして PAT** され、同じ outside IP(100.64.0.1) でもポートで分離される。
- **inside / outside の向き**：顧客IF=`ip nat inside`、ISP IF=`ip nat outside`。
- **★VRF→global の橋渡し = `ip route vrf RED 0.0.0.0 0.0.0.0 <ISP> global`**。
  inside は VRF、outside(ISP) は global table。`global` キーワードでネクストホップを
  global で解決させ、VRF のインターネット行きを global の ISP へ抜く。これが無いと
  VRF 内に出口が無く NAT 以前に転送されない。
- 戻りは ISP→100.64.0.1(connected) で届き、NAT が outside→inside に逆変換して該当 VRF へ戻す。
- 確認:
  - `show ip nat translations vrf RED` / `... vrf BLUE` に各 `10.0.0.1 → 8.8.8.8` エントリ
  - RT03 / RT04 から `ping 8.8.8.8 source Lo0` が成功
```
