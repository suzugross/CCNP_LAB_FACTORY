# GEN-RTCTL-9678 模範解答（採点者用）

抽選結果: pl_shape=quad24 / excl=pl_dl / t2=two_opposite/bind /
e2o=rm_pl / o2e=rm / t5=あり / 順序=['t2', 't1', 't3', 't4', 't5', 't6']

投入は `solution/fix.json`（RT01 のみ）。全文:

```
ip prefix-list PL-FEED-IN seq 5 permit 10.0.0.0/8 le 32
ip prefix-list PL-FEED-IN seq 10 permit 172.23.0.0/16 le 32
access-list 18 permit 10.44.2.0 0.0.0.255
access-list 47 permit 10.44.5.0 0.0.0.255
ip prefix-list PL-TOKYO-LAN seq 5 permit 172.23.172.0/22 ge 24 le 24
access-list 71 permit 10.45.68.0 0.0.0.255
access-list 71 permit 10.45.77.0 0.0.0.255
route-map RM-REDIST-OUT permit 10
 match ip address prefix-list PL-TOKYO-LAN
route-map RM-O2E permit 10
 match ip address 71
router eigrp 100
 distribute-list prefix PL-FEED-IN in Ethernet0/1
 offset-list 18 in 1000 Ethernet0/1
 offset-list 47 in 1000 Ethernet0/0
 redistribute ospf 1 metric 10000 1000 255 1 1500 route-map RM-O2E
router ospf 1
 redistribute eigrp 100 subnets route-map RM-REDIST-OUT
access-list 71 permit 10.45.74.0 0.0.0.255
```

## レビュー観点（実測は poc/rtctl/README.md）

- **T-excl の主罠**: permit 列挙にトランジット網(10.1.24.0/30・10.1.34.0/30)を含め
  忘れると、除外対象でない 10.1.34.0/30 が対向フィード経由へ迂回する。
- **T-pref**: 障害時切替の要件があるためフィルタでは満たせない。offset は RD にも
  加算されるため大きすぎると FS が消える(本seedの 1000 は FS 維持圏内)。
- **T-e2o の正準 1 行**: `172.23.172.0/22 ge 24 le 24`(pl_shape=quad24)。
  ★「4連続/24=/22 ge 24 le 24」の暗記解は pair24/longer_only/exact では不正解になる。
- **T-o2e**: プロトコル指定 DL と route-map は等価な効果を持つが、本問は制約で
  片方を指定する(rm)。connected 随伴(10.1.15.0/30)も遮断される。
- **T6**: source 無指定の ping は失敗する(RT05 はトランジット網への経路を持たない)。
