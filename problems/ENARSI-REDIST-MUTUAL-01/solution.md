# 模範解答 : ENARSI-REDIST-MUTUAL-01

境界 **RT02 / RT03 の両方**に、同一の双方向再配送を設定する。

```
! --- ループ防止タグ（2点境界のフィードバック再注入を遮断）---
route-map EIGRP_TO_OSPF deny 10
 match tag 110                 ! 元々 OSPF 由来(後述 set tag 110)は OSPF へ戻さない
route-map EIGRP_TO_OSPF permit 20
 set tag 90                    ! EIGRP 由来として印を付けて OSPF へ
!
route-map OSPF_TO_EIGRP deny 10
 match tag 90                  ! 元々 EIGRP 由来は EIGRP へ戻さない
route-map OSPF_TO_EIGRP permit 20
 set tag 110                   ! OSPF 由来として印を付けて EIGRP へ
!
! --- 相互再配送 ---
router ospf 1
 redistribute eigrp 100 subnets route-map EIGRP_TO_OSPF
!
router eigrp 100
 redistribute ospf 1 metric 1000000 100 255 1 1500 route-map OSPF_TO_EIGRP
```

## 学習の核心
1. **OSPF → EIGRP は seed metric 必須**。`metric`（または `default-metric`）が無いと
   再配送経路はメトリック無限大で **EIGRP に注入されない** → RT04 が OSPF 系プレフィックスを学習せず到達不能。
2. **EIGRP → OSPF は `subnets`** を付ける（クラスフル以外＝/30・/32 を運ぶため）。
   ※ 近年の IOS-XE は subnets が既定で効くため省略でも入ることがあるが、明示が安全・移植性が高い。
3. **2 点境界のフィードバック防止**：再配送点が 2 つあると、一方が相手ドメインへ入れた経路を
   他方が元ドメインへ再注入し得る（AD 次第でループ/次善）。**route-map tag で「来た方向へ戻さない」**のが定石。
4. 効果の確認：RT01 で `show ip route ospf` に `O E2 4.4.4.4`、RT04 で `show ip route eigrp` に `D EX 1.1.1.1`。
   外部経路には set tag（90/110）が乗る（`show ip route 4.4.4.4` の "Tag" 行で確認可）。
