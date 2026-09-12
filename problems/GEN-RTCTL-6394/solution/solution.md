# GEN-RTCTL-6394 模範解答（採点者用）

抽選結果: pl_shape=quad24 / excl=acl_num(deny_based) / t2=two_opposite/bind /
e2o=ospf_dl_out / o2e=free / t5=あり / 順序=['t2', 't1', 't3', 't4', 't5', 't6'] /
EIGRP AS 1735 / OSPF pid 9

投入は `solution/fix.json`（RT01 のみ）。全文:

```
access-list 27 deny 192.168.137.0 0.0.0.255
access-list 27 deny 192.168.148.0 0.0.0.255
access-list 27 permit any
access-list 29 permit 10.33.6.0 0.0.0.255
access-list 39 permit 10.33.1.0 0.0.0.255
access-list 36 permit 172.27.180.0
access-list 36 permit 172.27.181.0
access-list 36 permit 172.27.182.0
access-list 36 permit 172.27.183.0
access-list 93 permit 10.32.30.0 0.0.0.255
access-list 93 permit 10.32.24.0 0.0.0.255
router eigrp 1735
 distribute-list 27 in Ethernet0/1
 offset-list 29 in 1000 Ethernet0/0
 offset-list 39 in 1000 Ethernet0/1
 redistribute ospf 9 metric 1000000 1 255 1 1500
 distribute-list 93 out ospf 9
router ospf 9
 redistribute eigrp 1735 subnets
 distribute-list 36 out eigrp 1735
access-list 93 permit 10.32.34.0 0.0.0.255
```

## レビュー観点（実測は poc/rtctl/README.md）

- **T-excl の主罠**(pol=deny_based): permit_only 回=列挙にトランジット網
  (10.1.24.0/30・10.1.34.0/30)を含め忘れると 10.1.34.0/30 が対向へ迂回。
  deny_based 回=包括 permit を書き忘れると暗黙 deny で当該フィードの全ルートが落ちる。
  ★設計対比: permit 列挙=閉鎖型(新規の正当経路を落とす)/deny+包括 permit=開放型
  (新規経路を通す)。どちらを要求されているかは要件文で判別する。
- **T-pref**: 障害時切替の要件があるためフィルタでは満たせない。offset は RD にも
  加算されるため大きすぎると FS が消える(本seedの 1000 は FS 維持圏内)。
- **T-e2o の正準 1 行**: `172.27.180.0/22 ge 24 le 24`(pl_shape=quad24)。
  ★「4連続/24=/22 ge 24 le 24」の暗記解は pair24/longer_only/exact では不正解になる。
- **T-o2e**: プロトコル指定 DL と route-map は等価な効果を持つが、本問は制約で
  片方を指定する(free)。connected 随伴(10.1.15.0/30)も遮断される。
- **T6**: source 無指定の ping は失敗する(RT05 はトランジット網への経路を持たない)。
