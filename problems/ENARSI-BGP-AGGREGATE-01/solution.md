# 模範解答 : ENARSI-BGP-AGGREGATE-01

設定するのは **RT01 (AS65001)** のみ。

```
router bgp 65001
 bgp log-neighbor-changes
 neighbor 10.1.12.2 remote-as 65002
 neighbor 10.1.13.2 remote-as 65003
 aggregate-address 172.16.0.0 255.255.252.0 summary-only as-set
```

## 確認
```
show ip bgp                          ! RT01 に /22(集約・local) と /24×4(s=suppressed) が見える
show ip bgp 172.16.0.0/22            ! aggregated, as-set で {65002} を含む path
! RT03 側
show ip route bgp                    ! 172.16.0.0/22 のみ
show ip bgp 172.16.1.0/24            ! % Network not in table (抑止されている)
```

## ポイント（落とし穴の解説）
- **集約が形成される条件**: BGP テーブルに集約対象の「構成経路 (component)」が
  最低 1 本必要。本問は RT02 から /24 を受信しているので条件を満たす。
  構成経路が無いと aggregate-address を書いても /22 は生成されない。
- **summary-only**: これを付けると構成経路 (/24) が下流広告から抑止される (s フラグ)。
  付けないと /22 と /24 の両方が下流に出てしまう。
- **as-set**: 集約はデフォルトで AS-path 情報を失い **atomic-aggregate** 属性が付く
  （元の AS が分からなくなる＝ループ防止情報の欠落）。`as-set` を付けると構成経路の
  AS を **AS_SET `{65002}`** として保持し、atomic-aggregate を回避できる。
  → 下流 RT03 から見た /22 の path に `65002` が残る。
- フィルタ (prefix-list/distribute-list) で /24 を下流向けに落とすのは「集約」ではない。
  集約は 1 本の新しい経路を生成する点が異なる。本問は集約機能で解くこと。
