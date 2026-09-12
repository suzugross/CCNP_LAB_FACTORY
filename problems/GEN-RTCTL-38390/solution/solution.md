# GEN-RTCTL-38390 模範解答（採点者用）

抽選結果: pl_shape=mixed_len / excl=pl_dl(permit_only) / t2=two_opposite/bind /
e2o=rm_pl / o2e=rm / t5=あり / 順序=['t1', 't2', 't4', 't5', 't3', 't6'] /
EIGRP AS 25332 / OSPF pid 79

投入は `solution/fix.json`（RT01 のみ）。全文:

```
ip prefix-list PL-EDGE-IN seq 5 permit 10.0.0.0/8 le 32
ip prefix-list PL-EDGE-IN seq 10 permit 172.27.0.0/16 le 32
access-list 40 permit 10.43.26.0 0.0.0.255
access-list 49 permit 10.43.19.0 0.0.0.255
ip prefix-list PL-CORE-NETS seq 5 permit 172.27.140.0/22 ge 24 le 26
access-list 73 permit 10.3.13.0 0.0.0.255
access-list 73 permit 10.3.9.0 0.0.0.255
route-map RM-REDIST-OUT permit 10
 match ip address prefix-list PL-CORE-NETS
route-map RM-OSPF-IMPORT permit 10
 match ip address 73
router eigrp 25332
 distribute-list prefix PL-EDGE-IN in Ethernet0/1
 offset-list 40 in 4000 Ethernet0/1
 offset-list 49 in 4000 Ethernet0/0
 redistribute ospf 79 metric 100000 100 255 1 1500 route-map RM-OSPF-IMPORT
router ospf 79
 redistribute eigrp 25332 subnets route-map RM-REDIST-OUT
access-list 73 permit 10.3.17.0 0.0.0.255
```

## レビュー観点（実測は poc/rtctl/README.md）

- **T-excl の主罠**(pol=permit_only): permit_only 回=列挙にトランジット網
  (10.1.24.0/30・10.1.34.0/30)を含め忘れると 10.1.34.0/30 が対向へ迂回。
  deny_based 回=包括 permit を書き忘れると暗黙 deny で当該フィードの全ルートが落ちる。
  ★設計対比: permit 列挙=閉鎖型(新規の正当経路を落とす)/deny+包括 permit=開放型
  (新規経路を通す)。どちらを要求されているかは要件文で判別する。
- **T-pref**: 障害時切替の要件があるためフィルタでは満たせない。offset は RD にも
  加算されるため大きすぎると FS が消える(本seedの 4000 は FS 維持圏内)。
- **T-e2o の正準 1 行**: `172.27.140.0/22 ge 24 le 26`(pl_shape=mixed_len)。
  ★「4連続/24=/22 ge 24 le 24」の暗記解は pair24/longer_only/exact では不正解になる。
- **T-o2e**: プロトコル指定 DL と route-map は等価な効果を持つが、本問は制約で
  片方を指定する(rm)。connected 随伴(10.1.15.0/30)も遮断される。
- **T6**: source 無指定の ping は失敗する(RT05 はトランジット網への経路を持たない)。
