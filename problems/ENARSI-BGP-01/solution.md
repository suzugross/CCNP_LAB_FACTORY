# 模範解答 : ENARSI-BGP-01

設定するのは **RT01 (AS65001)** のみ。

```
route-map PREFER-RT02 permit 10
 set local-preference 200
!
route-map PREPEND-RT03 permit 10
 set as-path prepend 65001 65001
!
router bgp 65001
 bgp log-neighbor-changes
 neighbor 10.1.12.2 remote-as 65002
 neighbor 10.1.13.2 remote-as 65003
 network 1.1.1.1 mask 255.255.255.255
 ! 行き: RT02 から来る経路の local-preference を上げて RT02 経由を優先
 neighbor 10.1.12.2 route-map PREFER-RT02 in
 ! 帰り: RT03 へ出す広告に自分のASを prepend し、RT04 から見て RT03 経由を不利に
 neighbor 10.1.13.2 route-map PREPEND-RT03 out
```

## 確認
```
show ip bgp summary                 ! 両ネイバーが Established
show ip bgp 4.4.4.4/32              ! best path が RT02(10.1.12.2)・local-pref 200
show ip route bgp                   ! 4.4.4.4/32 が via 10.1.12.2
! RT04 側: show ip route bgp        ! 1.1.1.1/32 が via 10.1.24.1 (RT02経由)
```

### ポイント（落とし穴の解説）
- **行き(inbound)の経路選択**は **local-preference** で制御する。LP は AS 内で共有される強い属性で、
  best-path 評価で weight の次・AS-path より先に効く。RT02 から入る経路に高い LP を付ければ RT02 が選ばれる。
  weight でも RT01 単体なら同じ結果になるが、ENARSI 的には LP が定石。
- **帰り(outbound)の誘導**は自分では決められない（決めるのは RT04）。そこで **AS-path prepend** で
  RT03 向けの広告に自AS を水増しし、RT04 から見た RT03 経由の AS-path を長くして不利にする
  （＝相対的に RT02 経由を選ばせる）。prepend は「相手の経路選択を間接的に誘導する」手筋。
- route-map の **in/out の向き**を間違えない。LP は in（受信時に付与）、prepend は out（送信する広告を加工）。

> 採点はベストパスの最終結果で判定する（RT01 のルートテーブルで 4.4.4.4 が RT02 経由、
> RT04 のルートテーブルで 1.1.1.1 が RT02 経由）。属性の付け方(LP値やprepend回数)は任意。
