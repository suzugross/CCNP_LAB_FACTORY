# 模範解答 : ENCOR-EIGRP-01

## RT01
```
router eigrp 100
 no auto-summary
 network 10.1.12.0 0.0.0.3
 network 10.1.13.0 0.0.0.3
 network 1.1.1.1 0.0.0.0
```

## RT02
```
router eigrp 100
 no auto-summary
 network 10.1.12.0 0.0.0.3
 network 2.2.2.2 0.0.0.0
```

## RT03
```
router eigrp 100
 no auto-summary
 network 10.1.13.0 0.0.0.3
 network 3.3.3.3 0.0.0.0
```

## 確認コマンド
```
show ip eigrp neighbors
show ip route eigrp
ping 2.2.2.2 source 1.1.1.1
```

> `network A.B.C.D 0.0.0.0`（ホストワイルドカード）で個々のインタフェースを正確に EIGRP へ
> 参加させている。`network 10.0.0.0` のようなクラスフル指定でも近隣は張れるが、
> 意図しないインタフェースを巻き込むため本問ではワイルドカードで限定している。
> 採点は最終状態（近隣確立 / D 経路の学習）で判定するため、参加方法の差異は問わない。

## 変種 "bfd"（-e variant=bfd）の追加解答
各リンク IF に BFD タイマを設定し、EIGRP（classic）と連動させる。

```
! 各ルータの全リンクIF（例 RT01 は Ethernet0/0, 0/1）
interface Ethernet0/0
 bfd interval 500 min_rx 500 multiplier 3
! EIGRP 連動（各ルータ）
router eigrp 100
 bfd all-interfaces
```

> 確認: `show bfd neighbors details`（State Up / Registered protocols: EIGRP）
