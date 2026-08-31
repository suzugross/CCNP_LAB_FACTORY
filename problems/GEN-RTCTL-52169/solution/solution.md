# GEN-RTCTL-52169 模範解答（採点者用）

抽選結果: pl_shape=mixed_len / excl=acl_named(deny_based) / t2=group_exception/free /
e2o=ospf_dl_out / o2e=proto_dl / t5=あり / 順序=['t2', 't1', 't3', 't4', 't5', 't6'] /
EIGRP AS 54194 / OSPF pid 84

投入は `solution/fix.json`（RT01 のみ）。全文:

```
access-list 47 permit 10.41.2.0 0.0.0.255
access-list 47 permit 10.41.7.0 0.0.0.255
access-list 25 permit 10.41.9.0 0.0.0.255
access-list 30 permit 172.19.128.0
access-list 30 permit 172.19.129.0
access-list 30 permit 172.19.130.0
access-list 30 permit 172.19.131.0
access-list 78 permit 10.25.71.0 0.0.0.255
access-list 78 permit 10.25.81.0 0.0.0.255
ip access-list standard CORP-IN-FILTER
 deny 192.168.234.0 0.0.0.255
 deny 192.168.59.0 0.0.0.255
 permit any
router eigrp 54194
 distribute-list CORP-IN-FILTER in Ethernet0/0
 offset-list 47 in 4000 Ethernet0/1
 offset-list 25 in 4000 Ethernet0/0
 redistribute ospf 84 metric 100000 100 255 1 1500
 distribute-list 78 out ospf 84
router ospf 84
 redistribute eigrp 54194 subnets
 distribute-list 30 out eigrp 54194
access-list 78 permit 10.25.73.0 0.0.0.255
```

## レビュー観点（実測は poc/rtctl/README.md）

- **T-excl の主罠**(pol=deny_based): permit_only 回=列挙にトランジット網
  (10.1.24.0/30・10.1.34.0/30)を含め忘れると 10.1.24.0/30 が対向へ迂回。
  deny_based 回=包括 permit を書き忘れると暗黙 deny で当該フィードの全ルートが落ちる。
  ★設計対比: permit 列挙=閉鎖型(新規の正当経路を落とす)/deny+包括 permit=開放型
  (新規経路を通す)。どちらを要求されているかは要件文で判別する。
- **T-pref**: 障害時切替の要件があるためフィルタでは満たせない。offset は RD にも
  加算されるため大きすぎると FS が消える(本seedの 4000 は FS 維持圏内)。
- **T-e2o の正準 1 行**: `172.19.128.0/22 ge 24 le 26`(pl_shape=mixed_len)。
  ★「4連続/24=/22 ge 24 le 24」の暗記解は pair24/longer_only/exact では不正解になる。
- **T-o2e**: プロトコル指定 DL と route-map は等価な効果を持つが、本問は制約で
  片方を指定する(proto_dl)。connected 随伴(10.1.15.0/30)も遮断される。
- **T6**: source 無指定の ping は失敗する(RT05 はトランジット網への経路を持たない)。
