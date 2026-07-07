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
