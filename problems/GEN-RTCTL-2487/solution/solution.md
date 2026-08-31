# GEN-RTCTL-2487 模範解答（採点者用）

抽選結果: pl_shape=mixed_len / excl=acl_num / t2=group_exception/free /
e2o=rm_pl / o2e=proto_dl / t5=あり / 順序=['t4', 't5', 't1', 't3', 't2', 't6']

投入は `solution/fix.json`（RT01 のみ）。全文:

```
access-list 23 permit 172.31.0.0 0.0.255.255
access-list 23 permit 10.3.61.0 0.0.0.255
access-list 23 permit 10.3.69.0 0.0.0.255
access-list 23 permit 10.3.76.0 0.0.0.255
access-list 23 permit 10.1.24.0 0.0.0.3
access-list 23 permit 10.1.34.0 0.0.0.3
access-list 17 permit 10.3.69.0 0.0.0.255
access-list 17 permit 10.3.76.0 0.0.0.255
access-list 28 permit 10.3.61.0 0.0.0.255
ip prefix-list PL-DC-BLOCK seq 5 permit 172.31.212.0/22 ge 24 le 26
access-list 63 permit 10.41.22.0 0.0.0.255
access-list 63 permit 10.41.27.0 0.0.0.255
route-map RM-TO-OSPF permit 10
 match ip address prefix-list PL-DC-BLOCK
router eigrp 100
 distribute-list 23 in Ethernet0/1
 offset-list 17 in 1000 Ethernet0/1
 offset-list 28 in 1000 Ethernet0/0
 redistribute ospf 1 metric 10000 1000 255 1 1500
 distribute-list 63 out ospf 1
router ospf 1
 redistribute eigrp 100 subnets route-map RM-TO-OSPF
access-list 63 permit 10.41.33.0 0.0.0.255
```

## レビュー観点（実測は poc/rtctl/README.md）

- **T-excl の主罠**: permit 列挙にトランジット網(10.1.24.0/30・10.1.34.0/30)を含め
  忘れると、除外対象でない 10.1.34.0/30 が対向フィード経由へ迂回する。
- **T-pref**: 障害時切替の要件があるためフィルタでは満たせない。offset は RD にも
  加算されるため大きすぎると FS が消える(本seedの 1000 は FS 維持圏内)。
- **T-e2o の正準 1 行**: `172.31.212.0/22 ge 24 le 26`(pl_shape=mixed_len)。
  ★「4連続/24=/22 ge 24 le 24」の暗記解は pair24/longer_only/exact では不正解になる。
- **T-o2e**: プロトコル指定 DL と route-map は等価な効果を持つが、本問は制約で
  片方を指定する(proto_dl)。connected 随伴(10.1.15.0/30)も遮断される。
- **T6**: source 無指定の ping は失敗する(RT05 はトランジット網への経路を持たない)。
