# 模範解答 : ENARSI-BGP-MED-01

ピアごとに outbound 方向の route-map で `set metric` (= MED) を指定する。

## RT01
```
route-map MED-PRIMARY permit 10
 set metric 10
!
route-map MED-BACKUP permit 10
 set metric 200
!
router bgp 65001
 neighbor 10.1.12.2 route-map MED-PRIMARY out
 neighbor 10.1.122.2 route-map MED-BACKUP out
!
end
clear ip bgp * soft out
```

(soft out は新ポリシーを即時送出するため。`clear ip bgp *` でも可だが乱暴。)

## 確認（RT02 から）
```
show ip bgp 10.100.0.0/24
show ip route bgp
```

`show ip bgp 10.100.0.0/24` の表示:
```
  65001
    10.1.12.1 from 10.1.12.1 (1.1.1.1)
      Origin IGP, metric 10, localpref 100, valid, external, best
  65001
    10.1.122.1 from 10.1.122.1 (1.1.1.1)
      Origin IGP, metric 200, localpref 100, valid, external
```

### ポイント（落とし穴の解説）
- **MED は隣接 AS への "ヒント"**: 受信側 AS の管理者が無視することもある（`bgp bestpath
  med always-compare-med` の有無や、AS 境界での処理ポリシー）。本問は両パスとも同じ
  隣接 AS (65001) からなのでデフォルトで比較対象になる。
- **best-path 順序での位置**: weight, local-pref, locally-originated, AS-path length,
  origin の後に MED が来る。本問はそれより前の属性が全部同一なので MED で勝負がつく。
- **set metric は outbound 側でやる**: 送信側ルータが MED 値をパッケージして
  update に詰める。受信側で `set metric` をやっても自分の BGP テーブルにしか
  影響しない（あまり意味がない）。
- **soft out / clear**: 既存のセッションでルートマップを変えても、すでに送ったルートに
  対する効果は次の advertisement まで反映されない。`clear ip bgp * soft out` で
  即時再送 (graceful)。

> 採点: 両 eBGP セッション Established / RT02 の BGP テーブルで 10.100.0.0/24 の
> best path の metric=10 / RIB の nexthop=10.1.12.1 を判定。
