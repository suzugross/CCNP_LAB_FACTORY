# GEN-RTCTL-60916 模範解答（採点者用）

抽選結果: pl_shape=quad24 / excl=pl_dl / t2=group_exception/free /
e2o=ospf_dl_out / o2e=free / t5=あり / 順序=['t1', 't3', 't2', 't4', 't5', 't6']

投入は `solution/fix.json`（RT01 のみ）。全文:

```
ip prefix-list PL-EDGE-IN seq 5 permit 10.0.0.0/8 le 32
ip prefix-list PL-EDGE-IN seq 10 permit 172.31.0.0/16 le 32
access-list 36 permit 10.42.42.0 0.0.0.255
access-list 36 permit 10.42.49.0 0.0.0.255
access-list 28 permit 10.42.47.0 0.0.0.255
access-list 9 permit 172.31.180.0
access-list 9 permit 172.31.181.0
access-list 9 permit 172.31.182.0
access-list 9 permit 172.31.183.0
access-list 85 permit 10.2.19.0 0.0.0.255
access-list 85 permit 10.2.27.0 0.0.0.255
router eigrp 100
 distribute-list prefix PL-EDGE-IN in Ethernet0/0
 offset-list 36 in 2000 Ethernet0/1
 offset-list 28 in 2000 Ethernet0/0
 redistribute ospf 1 metric 100000 100 255 1 1500
 distribute-list 85 out ospf 1
router ospf 1
 redistribute eigrp 100 subnets
 distribute-list 9 out eigrp 100
access-list 85 permit 10.2.23.0 0.0.0.255
```

## レビュー観点（実測は poc/rtctl/README.md）

- **T-excl の主罠**: permit 列挙にトランジット網(10.1.24.0/30・10.1.34.0/30)を含め
  忘れると、除外対象でない 10.1.24.0/30 が対向フィード経由へ迂回する。
- **T-pref**: 障害時切替の要件があるためフィルタでは満たせない。offset は RD にも
  加算されるため大きすぎると FS が消える(本seedの 2000 は FS 維持圏内)。
- **T-e2o の正準 1 行**: `172.31.180.0/22 ge 24 le 24`(pl_shape=quad24)。
  ★「4連続/24=/22 ge 24 le 24」の暗記解は pair24/longer_only/exact では不正解になる。
- **T-o2e**: プロトコル指定 DL と route-map は等価な効果を持つが、本問は制約で
  片方を指定する(free)。connected 随伴(10.1.15.0/30)も遮断される。
- **T6**: source 無指定の ping は失敗する(RT05 はトランジット網への経路を持たない)。
