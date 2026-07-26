# 模範解答 : ENARSI-REDIST-POLICY-01

境界 **RT02 / RT03 の両方**に、同一のポリシー付き相互再配送を設定する。
ポリシーは各 redistribute に適用する **route-map に集約**する（仕様6）。

```
! --- 選択用 prefix-list ---
ip prefix-list BR-LAB seq 5 permit 10.20.99.0/24     ! 拠点検証網（遮断対象）
ip prefix-list BR-SRV seq 5 permit 10.20.10.0/24     ! 拠点サーバ網（E1 対象）
ip prefix-list HQ-LAB seq 5 permit 172.16.99.0/24    ! 本社検証網（遮断対象）
ip prefix-list HQ-SRV seq 5 permit 172.16.10.0/24    ! 本社基幹サーバ網（優遇 metric 対象）
!
! --- EIGRP → OSPF 方向 ---
route-map EIGRP_TO_OSPF deny 10
 match tag 110                  ! 元々 OSPF 由来（他境界が入れた戻り）は OSPF へ戻さない
route-map EIGRP_TO_OSPF deny 15
 match ip address prefix-list BR-LAB    ! 仕様2: 検証網はドメイン間遮断
route-map EIGRP_TO_OSPF permit 20
 match ip address prefix-list BR-SRV
 set metric-type type-1         ! 仕様3: 拠点サーバ網は O E1
 set tag 90
route-map EIGRP_TO_OSPF permit 30
 set tag 90                     ! 仕様5: EIGRP 由来の印（既定は E2 のまま）
!
! --- OSPF → EIGRP 方向 ---
route-map OSPF_TO_EIGRP deny 10
 match tag 90                   ! 元々 EIGRP 由来は EIGRP へ戻さない
route-map OSPF_TO_EIGRP deny 15
 match ip address prefix-list HQ-LAB    ! 仕様2
route-map OSPF_TO_EIGRP permit 20
 match ip address prefix-list HQ-SRV
 set metric 10000 100 255 1 1500        ! 仕様4: 基幹サーバ網は優遇シード
 set tag 110
route-map OSPF_TO_EIGRP permit 30
 set metric 1000 100 255 1 1500         ! 仕様4: その他は既定シード
 set tag 110                            ! 仕様5: OSPF 由来の印
!
! --- 相互再配送 ---
router ospf 1
 redistribute eigrp 100 subnets route-map EIGRP_TO_OSPF
router eigrp 100
 redistribute ospf 1 route-map OSPF_TO_EIGRP
```

## 学習の核心

1. **route-map は上から first-match**。「戻り遮断（タグ）→ 個別遮断（検証網）→ 個別色付け
   （サーバ網）→ 包括 permit（既定色）」の**順序設計**がこの問題の本体。包括 permit を
   先に書くと個別条件が死ぬ。最後の permit（match なし）が無いと**残り全部が暗黙 deny**で
   落ちて到達性が壊れる。
2. **OSPF → EIGRP はシードメトリック必須**。`redistribute` の metric キーワードの代わりに
   route-map の `set metric` でも与えられ、**プレフィックス毎に別の値**を出し分けられる
   （metric キーワード＋permit 20 の set metric 上書きでも可）。set metric が無い permit
   経路はメトリック無限大で注入されない。
3. **E1/E2 の使い分け**（`set metric-type type-1`）。E1 は域内コストが加算されるため
   「境界からの距離」を反映した最寄り境界選択になる。E2（既定）はコスト固定。
4. **2点境界のループ防止は出自タグ**（deny match tag / permit set tag の対）。
   OSPF 外部 LSA・EIGRP external とも経路タグを運搬できるので、
   「来た方向へ戻さない」を宣言的に実装できる。
5. 確認コマンド:
   - RT01: `show ip route 10.20.10.0` → `Tag 90, type extern 1`
   - RT04: `show ip route 172.16.10.0` → `metric 307200`・`Route tag 110`
     （307200 = 256×(10^7/10000 + (1000+1000)/10)。既定シードは 2611200）
   - 境界: `show route-map` でシーケンス毎のマッチ数を確認
