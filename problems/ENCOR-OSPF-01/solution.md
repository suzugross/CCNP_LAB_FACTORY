# 模範解答 : ENCOR-OSPF-01

## RT01
```
router ospf 1
 network 10.1.12.0 0.0.0.3 area 0
 network 10.1.13.0 0.0.0.3 area 0
 network 1.1.1.1 0.0.0.0 area 0
```

## RT02
```
router ospf 1
 network 10.1.12.0 0.0.0.3 area 0
 network 2.2.2.2 0.0.0.0 area 0
```

## RT03
```
router ospf 1
 network 10.1.13.0 0.0.0.3 area 0
 network 3.3.3.3 0.0.0.0 area 0
```

## 確認コマンド
```
show ip ospf neighbor
show ip route ospf
ping 2.2.2.2 source 1.1.1.1
```

> `network ... area 0` の代わりに各インタフェースで `ip ospf 1 area 0` を使う解法も可。
> 採点は最終状態（ネイバー FULL / 経路学習）で判定するため、どちらでも合格となる。

## 変種 "bfd"（-e variant=bfd）の追加解答
全ルータ間リンクの IF に BFD タイマを設定し、OSPF と連動させる。

```
! RT01（両リンク。RT02/RT03 は自リンク側 IF のみ）
interface Ethernet0/0
 bfd interval 500 min_rx 500 multiplier 3
 ip ospf bfd
interface Ethernet0/1
 bfd interval 500 min_rx 500 multiplier 3
 ip ospf bfd
```

> IF ごとの `ip ospf bfd` の代わりに `router ospf 1` 配下 `bfd all-interfaces` でも可
> （採点は効果ベース: セッション Up＋OSPF クライアント登録＋乗数）。

### 確認コマンド
```
show bfd neighbors details   ← State Up / Registered protocols: OSPF
```
