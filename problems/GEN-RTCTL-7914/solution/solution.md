# GEN-RTCTL-7914 模範解答（採点者用）

抽選結果: pl_shape=longer_only / excl=acl_num / t2=two_opposite/free /
e2o=rm_pl / o2e=rm / t5=あり / 順序=['t3', 't1', 't2', 't4', 't5', 't6']

投入は `solution/fix.json`（RT01 のみ）。全文:

```
access-list 27 permit 172.22.0.0 0.0.255.255
access-list 27 permit 10.58.29.0 0.0.0.255
access-list 27 permit 10.58.37.0 0.0.0.255
access-list 27 permit 10.58.40.0 0.0.0.255
access-list 27 permit 10.1.24.0 0.0.0.3
access-list 27 permit 10.1.34.0 0.0.0.3
access-list 30 permit 10.58.29.0 0.0.0.255
access-list 46 permit 10.58.40.0 0.0.0.255
ip prefix-list PL-BRANCH24 seq 5 permit 172.22.40.0/22 ge 25
access-list 81 permit 10.36.48.0 0.0.0.255
access-list 81 permit 10.36.40.0 0.0.0.255
route-map RM-E2O permit 10
 match ip address prefix-list PL-BRANCH24
route-map RM-FROM-OSPF permit 10
 match ip address 81
router eigrp 100
 distribute-list 27 in Ethernet0/1
 offset-list 30 in 1000 Ethernet0/1
 offset-list 46 in 1000 Ethernet0/0
 redistribute ospf 1 metric 100000 100 255 1 1500 route-map RM-FROM-OSPF
router ospf 1
 redistribute eigrp 100 subnets route-map RM-E2O
access-list 81 permit 10.36.44.0 0.0.0.255
```

## レビュー観点（実測は poc/rtctl/README.md）

- **T-excl の主罠**: permit 列挙にトランジット網(10.1.24.0/30・10.1.34.0/30)を含め
  忘れると、除外対象でない 10.1.34.0/30 が対向フィード経由へ迂回する。
- **T-pref**: 障害時切替の要件があるためフィルタでは満たせない。offset は RD にも
  加算されるため大きすぎると FS が消える(本seedの 1000 は FS 維持圏内)。
- **T-e2o の正準 1 行**: `172.22.40.0/22 ge 25`(pl_shape=longer_only)。
  ★「4連続/24=/22 ge 24 le 24」の暗記解は pair24/longer_only/exact では不正解になる。
- **T-o2e**: プロトコル指定 DL と route-map は等価な効果を持つが、本問は制約で
  片方を指定する(rm)。connected 随伴(10.1.15.0/30)も遮断される。
- **T6**: source 無指定の ping は失敗する(RT05 はトランジット網への経路を持たない)。
