# GEN-RTCTL-61217 模範解答（採点者用）

抽選結果: pl_shape=exact / excl=pl_dl(permit_only) / t2=group_exception/bind /
e2o=ospf_dl_out / o2e=rm / t5=あり / 順序=['t2', 't1', 't4', 't5', 't3', 't6'] /
EIGRP AS 65301 / OSPF pid 12

投入は `solution/fix.json`（RT01 のみ）。全文:

```
ip prefix-list PL-CORE-IN seq 5 permit 10.0.0.0/8 le 32
ip prefix-list PL-CORE-IN seq 10 permit 172.28.0.0/16 le 32
access-list 6 permit 10.46.76.0 0.0.0.255
access-list 6 permit 10.46.82.0 0.0.0.255
access-list 14 permit 10.46.72.0 0.0.0.255
access-list 23 permit 172.28.96.0
access-list 67 permit 10.7.83.0 0.0.0.255
access-list 67 permit 10.7.78.0 0.0.0.255
route-map RM-FROM-OSPF permit 10
 match ip address 67
router eigrp 65301
 distribute-list prefix PL-CORE-IN in Ethernet0/0
 offset-list 6 in 4000 Ethernet0/0
 offset-list 14 in 4000 Ethernet0/1
 redistribute ospf 12 metric 1000000 1 255 1 1500 route-map RM-FROM-OSPF
router ospf 12
 redistribute eigrp 65301 subnets
 distribute-list 23 out eigrp 65301
access-list 67 permit 10.7.87.0 0.0.0.255
```

## レビュー観点（実測は poc/rtctl/README.md）

- **T-excl の主罠**(pol=permit_only): permit_only 回=列挙にトランジット網
  (10.1.24.0/30・10.1.34.0/30)を含め忘れると 10.1.24.0/30 が対向へ迂回。
  deny_based 回=包括 permit を書き忘れると暗黙 deny で当該フィードの全ルートが落ちる。
  ★設計対比: permit 列挙=閉鎖型(新規の正当経路を落とす)/deny+包括 permit=開放型
  (新規経路を通す)。どちらを要求されているかは要件文で判別する。
- **T-pref**: 障害時切替の要件があるためフィルタでは満たせない。offset は RD にも
  加算されるため大きすぎると FS が消える(本seedの 4000 は FS 維持圏内)。
- **T-e2o の正準 1 行**: `172.28.96.0/22`(pl_shape=exact)。
  ★「4連続/24=/22 ge 24 le 24」の暗記解は pair24/longer_only/exact では不正解になる。
- **T-o2e**: プロトコル指定 DL と route-map は等価な効果を持つが、本問は制約で
  片方を指定する(rm)。connected 随伴(10.1.15.0/30)も遮断される。
- **T6**: source 無指定の ping は失敗する(RT05 はトランジット網への経路を持たない)。
