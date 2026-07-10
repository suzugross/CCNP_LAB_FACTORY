# 解答 ENARSI-MPLS-L3VPN-03 — バックドア + sham-link

## 診断
- RT04 で `show ip route 172.16.2.0` → **`type intra area`・次ホップ 172.16.9.2（バックドア）**。
  MPLS 経由は `O IA`（inter-area）で提供されるため、OSPF は**経路種別優先で intra を無条件に選ぶ**
  （バックドアが cost 500 でも勝つ）。しかも area 0 がバックドアで連結されるため、PE の VRF RIB でも
  OSPF(AD110) が BGP(AD200) に勝ち、MPLS コアが使われない。
- 是正は **sham-link** で MPLS 経路を **O intra に昇格**させ、cost をバックドア(500)未満にする。

## 手順（RT01=PE1 / RT03=PE2 の両方に対称に投入）

### 1. sham-link 端点（VRF CUST_A の /32 ループバック）を作る
```
! RT01
interface Loopback110
 vrf forwarding CUST_A
 ip address 1.1.110.1 255.255.255.255
! RT03
interface Loopback110
 vrf forwarding CUST_A
 ip address 3.3.110.1 255.255.255.255
```

### 2. 端点を MP-BGP(VPNv4) のみで広告
```
! RT01
router bgp 65000
 address-family ipv4 vrf CUST_A
  network 1.1.110.1 mask 255.255.255.255
! RT03
router bgp 65000
 address-family ipv4 vrf CUST_A
  network 3.3.110.1 mask 255.255.255.255
```

### 3. ★端点を BGP→OSPF 再配布から除外（これを忘れると sham-link が張れない）
既存の `redistribute bgp 65000`（route-map なし）が端点 /32 を OSPF に漏らすと、端点が
sham-link 自身の経由で解決され recursion で UP しない。端点を除外する route-map を噛ませる。
```
! RT01/RT03 共通
ip prefix-list PL_SLEP seq 5 permit 1.1.110.1/32
ip prefix-list PL_SLEP seq 10 permit 3.3.110.1/32
route-map RM_B2O deny 10
 match ip address prefix-list PL_SLEP
route-map RM_B2O permit 20
!
router ospf 10 vrf CUST_A
 redistribute bgp 65000 route-map RM_B2O
```

### 4. sham-link を area 0 に張る（cost は 500 未満）
```
! RT01
router ospf 10 vrf CUST_A
 area 0 sham-link 1.1.110.1 3.3.110.1 cost 40
! RT03
router ospf 10 vrf CUST_A
 area 0 sham-link 3.3.110.1 1.1.110.1 cost 40
```

## 確認
- `show ip ospf 10 sham-links` → `... is up` / `State POINT_TO_POINT`。
- RT04 `show ip route 172.16.2.0` → 次ホップ **192.168.1.2（PE1）**・`intra area`（バックドアでない）。
- RT04 `show ip ospf neighbor` → 1.1.1.1（PE）と **5.5.5.5（バックドア）両方 FULL**＝予備生存。
- フォールバック確認: コア/ sham-link を落とすと 172.16.2.0/24 が 172.16.9.2（バックドア）へ切替。

## 落とし穴
- 端点除外 route-map を忘れる → sham-link が UP しない（本問最大の罠。実機PoC確認済）。
- sham-link cost を 500 以上にする → 依然バックドアが勝つ（形成≠優先）。
- `capability vrf-lite` を入れる → DN ビット防護が無効化しループ防止違反（本問は不要・禁止）。
- `no area 0 sham-link A B cost 40` は cost だけ剥がれ本体が残る。削除は `no area 0 sham-link A B`。
