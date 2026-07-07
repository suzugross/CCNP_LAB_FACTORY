# 模範解答 : ENARSI-REDIST-LOOP-01

## なぜ素の再配送だと壊れるか
境界の EIGRP 外部 AD は **95**（会社ポリシー）で、OSPF の **110** より小さい。
両境界が OSPF 発経路（例 1.1.1.1）を EIGRP へ再配送すると、相手境界はそれを
**EIGRP 外部(AD 95)** で学習し、自分の **OSPF ネイティブ(AD 110)** より優先してしまう。
結果、`RT03 → RT01` が直結 OSPF（1 ホップ）ではなく **`RT03 → RT02 → RT01`（2 ホップ）の遠回り**になる。

## 解（境界 RT02・RT03 の両方）
OSPF 発の経路に**タグを付けて識別**し、境界の **EIGRP 受信時にそのタグを遮断**する。
こうすると境界は「自ドメイン発が相手ドメインを一周して戻ってきた経路」を採用せず、
OSPF ネイティブを使う＝最短に戻る。AD は変更しない。

```
! OSPF 発経路に印（タグ110）を付けて EIGRP へ
route-map SET_TAG permit 10
 set tag 110
! タグ110（OSPF発）が EIGRP 経由で戻ってきたら受信拒否
route-map BLOCK_TAG deny 10
 match tag 110
route-map BLOCK_TAG permit 20
!
router ospf 1
 redistribute eigrp 100 subnets
!
router eigrp 100
 redistribute ospf 1 metric 100000 100 255 1 1500 route-map SET_TAG
 distribute-list route-map BLOCK_TAG in
```

## 確認
- `RT01: show ip route 1.1.1.1` 系は不要。境界で `show ip route 1.1.1.1` が
  **`Known via "ospf 1"`（EIGRP 外部でない）**になっていれば最短。
- RT04 は `show ip route eigrp` に `D EX 1.1.1.1`、RT01 は `show ip route ospf` に `O E2 4.4.4.4`。

## 別解（効果採点なので可）
- `distance` をルート単位で上書きして OSPF 発の EIGRP 外部経路だけ AD を上げる、
  prefix-list ベースの distribute-list で当該プレフィックスを境界 EIGRP inbound で遮断、等。
  会社ポリシー（`distance eigrp 90 95` 自体）を書き換える解は不可。

## 教育核心
- 2 点相互再配送＋AD 非対称（外部 < ネイティブ）は、**自ドメイン発経路の「相手ドメイン
  経由フィードバック」**を生む。標準 AD（EIGRP 外部 170 > OSPF 110）なら自然に防がれるが、
  AD を操作するとこの保護が崩れ、**経路タグによる明示的な制御**が必要になる。
- タグは「経路の出自」を運ぶメタ情報。再配送の境界で付与・判定することで、
  ループ/フィードバック/次善を方向性をもって制御できる（ENARSI の再配送制御の核心）。
