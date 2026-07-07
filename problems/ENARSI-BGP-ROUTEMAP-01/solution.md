# 模範解答 : ENARSI-BGP-ROUTEMAP-01

## RT01
```
ip prefix-list APP-PREFIX permit 10.10.0.0/16 ge 24
ip as-path access-list 1 permit _65003_
!
route-map RM-IN permit 10
 match ip address prefix-list APP-PREFIX
 set local-preference 200
!
route-map RM-IN deny 20
 match as-path 1
!
route-map RM-IN permit 30
!
router bgp 65001
 neighbor 10.1.12.2 route-map RM-IN in
!
end
clear ip bgp 10.1.12.2 soft in
```

## 確認
```
show ip bgp
show ip bgp 10.10.0.0/24    ! localpref 200
show ip bgp 10.20.0.0/24    ! localpref 100
show ip bgp 172.16.0.0/24   ! Network not in table
show route-map RM-IN
```

### ポイント（落とし穴の解説）
- **route-map の評価は順序がすべて**: seq 10 でマッチした経路は seq 20 を見ない。
  seq 10 を「prefix-list でマッチしたら set LP 200 して permit (=暗黙)」、
  seq 20 で「as-path で 65003 を見つけたら deny」、seq 30 で「残りを permit」と
  並べる。順番を入れ替えると意図が崩れる。
- **`permit 30` (空) を忘れない**: 末尾の暗黙 deny を無効化するため。書かないと
  seq 10 / 20 にマッチしなかった経路 (例: 10.20.0.0/24) も全部落ちる。本問の最大の
  落とし穴。
- **`route-map ... deny SEQ` + `match`**: deny で書くと「match した場合に経路を捨てる」。
  `match` を書かないと「すべて deny」になるので、必ず match を入れる。
- **prefix-list 名の `ip address` 指定**: route-map の prefix-list を呼ぶには
  `match ip address prefix-list NAME`。`match ip address NAME` だと標準 ACL を見にいく。
- **as-path access-list は番号 (1-500)**: `permit _65003_` で 65003 を含む path を識別。
  本問は match して deny する用途なので `permit` で書いて、route-map seq 20 で
  deny アクション。逆 (`deny _65003_` + route-map permit) でも実現可能だが思考は逆になる。
- **`set local-preference`**: ハイフン無しの `local-preference`。`local-pref` は無効。

> 採点: route-map inbound 適用 / BGP テーブルで 10.10/24 が LP=200、10.20/24 が
> 残存 (LP=100)、172.16/24 が不在を判定。
