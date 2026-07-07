# 模範解答 : ENARSI-BGP-COMM-01

community を扱うには 3 点セット (set / send-community / match) が必要。

## RT01 (送出側)
```
route-map TAG-COMM permit 10
 set community 65002:100
!
router bgp 65001
 neighbor 10.1.12.2 send-community
 neighbor 10.1.12.2 route-map TAG-COMM out
!
end
clear ip bgp * soft out
```

## RT02 (受信側)
```
ip community-list 10 permit 65002:100
!
route-map RM-IN permit 10
 match community 10
 set local-preference 200
!
route-map RM-IN permit 20
 ! それ以外の経路は通常通り
!
router bgp 65002
 neighbor 10.1.12.1 route-map RM-IN in
!
end
clear ip bgp * soft in
```

## 確認（RT02 側）
```
show ip bgp 10.100.0.0/24
```
期待される出力:
```
  Origin IGP, metric 0, localpref 200, valid, external, best
  Community: 65002:100
```

### ポイント（落とし穴の解説）
- **`send-community` を忘れない**: route-map で `set community` を書いても、
  デフォルトでは update に community 属性は載らない。`neighbor X send-community` を
  明示しないと相手に届かない。これが本問の最大の落とし穴。
- **route-map "permit 20" 空ステートメントの必要性**: route-map は最後の暗黙 deny で
  「マッチしないものは全部 deny」。community がマッチしない他の経路まで弾かれる
  と業務影響が出る。最後に "permit 20"（match 無し）で残りを通す。
- **community-list の番号体系**: 標準 community-list は 1-99 / 100-500 が拡張。
  本問は標準 community (`asn:value`) なので `community-list 10` のような標準を使う。
- **`set community additive` の有無**: 上書きしたいなら省略、既存に追加したいなら
  `additive` を付ける。本問は新規付与なので省略で可。
- **soft clear**: 既存の advertise / receive を新ポリシーで再評価させるため
  `clear ip bgp * soft out` (送出側) / `... soft in` (受信側) を打つ。

> 採点: eBGP Established / RT02 の BGP テーブルで 10.100.0.0/24 の path に
> `Community: 65002:100` が乗り、`localpref 200` が反映されていることを判定。
