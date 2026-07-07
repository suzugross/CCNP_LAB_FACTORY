# 模範解答 : ENARSI-BGP-ASPATH-01

## RT01
```
ip as-path access-list 10 deny _65003_
ip as-path access-list 10 permit .*
!
router bgp 65001
 neighbor 10.1.12.2 filter-list 10 in
!
end
clear ip bgp 10.1.12.2 soft in
```

## 確認
```
show ip bgp
show ip bgp regexp _65003_      ! 何もマッチしないはず
show ip bgp 10.2.0.0/24         ! best path で残っている
show ip bgp 10.3.0.0/24         ! "Network not in table"
```

### ポイント（落とし穴の解説）
- **`_<asn>_` の意味**: アンダースコアは「単語境界」(空白 / 行頭 / 行末 / カンマ / 中括弧 / etc) を表す。
  `_65003_` は AS-path の途中・末尾・先頭のいずれにも 65003 が単体トークンとして
  あればマッチする。`65003` を含む文字列(例: 650030, 165003)は誤検知しない。
- **`permit .*` を忘れない**: AS-path access-list の最後は暗黙 deny。`permit .*`
  (= 任意の AS-path にマッチ) を入れないと、`_65003_` で deny されなかった経路も
  すべて落ちる。これが本問の落とし穴。
- **`filter-list` のスコープ**: `neighbor X filter-list NN in` で inbound のみに
  適用。outbound に効かせたいなら別 ACL を out で。
- **prefix-list / distribute-list との違い**: prefix-list は宛先プレフィックスを
  見る。AS-path access-list は経路属性 AS-path を見る。同じ「フィルタ」でも
  match 軸が違う。本問は **AS で見る** が要件。
- **soft clear**: 既存セッションに新ポリシーを反映させるため `clear ip bgp X soft in`。
  hard clear はセッション断するので避ける。

> 採点: AS-path access-list 10 と filter-list の構成 / RT01 の BGP テーブルで
> 10.2.0.0/24 は残存・10.3.0.0/24 は不在を判定。
