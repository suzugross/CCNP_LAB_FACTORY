# GEN-RTCTL-39518 模範解答（採点者用）

抽選結果: pl_shape=quad24 / excl=acl_named / t2=なし /
e2o=rm_pl / o2e=rm / t5=あり / 順序=['t1', 't3', 't4', 't5', 't6']

投入は `solution/fix.json`（RT01 のみ）。全文:

```
ip prefix-list PL-BRANCH24 seq 5 permit 172.26.96.0/22 ge 24 le 24
access-list 76 permit 10.43.7.0 0.0.0.255
access-list 76 permit 10.43.15.0 0.0.0.255
ip access-list standard FILTER-CORE-IN
 permit 172.26.0.0 0.0.255.255
 permit 10.4.20.0 0.0.0.255
 permit 10.4.24.0 0.0.0.255
 permit 10.4.28.0 0.0.0.255
 permit 10.1.24.0 0.0.0.3
 permit 10.1.34.0 0.0.0.3
route-map RM-REDIST-OUT permit 10
 match ip address prefix-list PL-BRANCH24
route-map RM-OSPF-IMPORT permit 10
 match ip address 76
router eigrp 100
 distribute-list FILTER-CORE-IN in Ethernet0/0
 redistribute ospf 1 metric 50000 200 255 1 1500 route-map RM-OSPF-IMPORT
router ospf 1
 redistribute eigrp 100 subnets route-map RM-REDIST-OUT
access-list 76 permit 10.43.23.0 0.0.0.255
```

## レビュー観点（実測は poc/rtctl/README.md）

- **T-excl の主罠**: permit 列挙にトランジット網(10.1.24.0/30・10.1.34.0/30)を含め
  忘れると、除外対象でない 10.1.24.0/30 が対向フィード経由へ迂回する。
- **T-pref**: 障害時切替の要件があるためフィルタでは満たせない。offset は RD にも
  加算されるため大きすぎると FS が消える(本seedの 1000 は FS 維持圏内)。
- **T-e2o の正準 1 行**: `172.26.96.0/22 ge 24 le 24`(pl_shape=quad24)。
  ★「4連続/24=/22 ge 24 le 24」の暗記解は pair24/longer_only/exact では不正解になる。
- **T-o2e**: プロトコル指定 DL と route-map は等価な効果を持つが、本問は制約で
  片方を指定する(rm)。connected 随伴(10.1.15.0/30)も遮断される。
- **T6**: source 無指定の ping は失敗する(RT05 はトランジット網への経路を持たない)。
