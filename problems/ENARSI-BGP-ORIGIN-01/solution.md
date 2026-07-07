# 模範解答 : ENARSI-BGP-ORIGIN-01

設定するのは **RT01 (AS65001)** のみ。

```
route-map PREFER-ORIGIN permit 10
 set origin igp
!
router bgp 65001
 bgp log-neighbor-changes
 neighbor 10.1.12.2 remote-as 65002
 neighbor 10.1.13.2 remote-as 65003
 ! RT02 から受け取る経路の origin を IGP に書き換える
 neighbor 10.1.12.2 route-map PREFER-ORIGIN in
```

## 確認
```
show ip bgp 203.0.113.0/24    ! RT02(10.1.12.2)経由が "best"、Origin IGP
show ip route bgp             ! 203.0.113.0/24 が via 10.1.12.2
```

## ポイント（落とし穴の解説）
- 両経路は weight=0 / LP=100 / AS-path長=1 / MED=0 と同条件。BGP ベストパス選択で
  これらの後に来る比較が **origin コード (IGP < EGP < incomplete)**。
- RT02/RT03 はともに `redistribute static` で広告しているため origin は **incomplete (?)**。
  RT01 で RT02 経由の経路だけ `set origin igp` すると、IGP < incomplete のルールで RT02 が勝つ。
- origin より上位（weight/LP/locally-originated/AS-path長）を使うのは禁止。MED は origin より
  **下位**なので使っても origin の差で決着がつく前に効かない（そもそも禁止）。
- route-map は **inbound (in)** に適用する。受信した経路の属性を書き換えてから自分の RIB/ベスト選択に
  反映させるため。outbound では自分のベスト選択は変わらない。
