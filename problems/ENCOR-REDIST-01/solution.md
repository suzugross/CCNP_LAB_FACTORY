# 模範解答 : ENCOR-REDIST-01

設定するのは **RT02 のみ**。

## RT02
```
router ospf 1
 redistribute eigrp 100 subnets
!
router eigrp 100
 redistribute ospf 1 metric 100000 100 255 1 1500
```

### 補足
- OSPF への再配送は既定でクラスフル境界のみ＝サブネットが落ちるため **`subnets`** が必須
  （これが無いと 3.3.3.3/32 のようなホスト経路が再配送されない）。
- EIGRP への再配送は**シードメトリック**が必須。`metric <BW> <Delay> <Reliability> <Load> <MTU>`
  もしくは `default-metric 100000 100 255 1 1500` で代用可。これが無いと OSPF 経路が EIGRP に入らない。

## 確認
```
! RT01
show ip route ospf      → O E2  3.3.3.3/32 [110/20] via 10.1.12.2
! RT03
show ip route eigrp     → D EX  1.1.1.1/32 [170/...] via 10.1.23.1
```

> 採点は最終状態（外部経路コード O E2 / D EX を含む経路の学習）で判定する。
> `redistribute connected` を併用するなど別解でも、上記の到達状態に達していれば合格。
