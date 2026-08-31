# GEN-RTCTL-15723 模範解答（採点者用）

抽選結果: pl_shape=pair24 / excl=pl_dl(deny_based) / t2=group_exception/free /
e2o=rm_pl / o2e=free / t5=あり / 順序=['t3', 't1', 't2', 't4', 't5', 't6'] /
EIGRP AS 6884 / OSPF pid 53

投入は `solution/fix.json`（RT01 のみ）。全文:

```
ip prefix-list PL-EDGE-IN seq 5 deny 192.168.198.0/24
ip prefix-list PL-EDGE-IN seq 10 deny 192.168.209.0/24
ip prefix-list PL-EDGE-IN seq 15 permit 0.0.0.0/0 le 32
access-list 19 permit 10.30.77.0 0.0.0.255
access-list 19 permit 10.30.85.0 0.0.0.255
access-list 26 permit 10.30.73.0 0.0.0.255
ip prefix-list PL-BRANCH24 seq 5 permit 172.17.44.0/23 ge 24 le 24
access-list 51 permit 10.58.34.0 0.0.0.255
access-list 51 permit 10.58.37.0 0.0.0.255
route-map RM-REDIST-OUT permit 10
 match ip address prefix-list PL-BRANCH24
router eigrp 6884
 distribute-list prefix PL-EDGE-IN in Ethernet0/1
 offset-list 19 in 4000 Ethernet0/1
 offset-list 26 in 4000 Ethernet0/0
 redistribute ospf 53 metric 10000 1000 255 1 1500
 distribute-list 51 out ospf 53
router ospf 53
 redistribute eigrp 6884 subnets route-map RM-REDIST-OUT
access-list 51 permit 10.58.40.0 0.0.0.255
```

## レビュー観点（実測は poc/rtctl/README.md）

- **T-excl の主罠**(pol=deny_based): permit_only 回=列挙にトランジット網
  (10.1.24.0/30・10.1.34.0/30)を含め忘れると 10.1.34.0/30 が対向へ迂回。
  deny_based 回=包括 permit を書き忘れると暗黙 deny で当該フィードの全ルートが落ちる。
  ★設計対比: permit 列挙=閉鎖型(新規の正当経路を落とす)/deny+包括 permit=開放型
  (新規経路を通す)。どちらを要求されているかは要件文で判別する。
- **T-pref**: 障害時切替の要件があるためフィルタでは満たせない。offset は RD にも
  加算されるため大きすぎると FS が消える(本seedの 4000 は FS 維持圏内)。
- **T-e2o の正準 1 行**: `172.17.44.0/23 ge 24 le 24`(pl_shape=pair24)。
  ★「4連続/24=/22 ge 24 le 24」の暗記解は pair24/longer_only/exact では不正解になる。
- **T-o2e**: プロトコル指定 DL と route-map は等価な効果を持つが、本問は制約で
  片方を指定する(free)。connected 随伴(10.1.15.0/30)も遮断される。
- **T6**: source 無指定の ping は失敗する(RT05 はトランジット網への経路を持たない)。
