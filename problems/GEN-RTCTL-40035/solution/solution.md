# GEN-RTCTL-40035 模範解答（採点者用）

投入は `solution/fix.json`（RT01 のみ・Task 順）。全文:

```
access-list 21 permit 172.16.192.0 0.0.3.255
access-list 21 permit 10.56.18.0 0.0.0.255
access-list 21 permit 10.56.22.0 0.0.0.255
access-list 21 permit 10.56.24.0 0.0.0.255
access-list 21 permit 10.1.24.0 0.0.0.3
access-list 21 permit 10.1.34.0 0.0.0.3
access-list 8 permit 10.56.24.0 0.0.0.255
access-list 26 permit 10.56.18.0 0.0.0.255
access-list 70 permit 10.40.87.0 0.0.0.255
access-list 70 permit 10.40.79.0 0.0.0.255
ip prefix-list PL-CORE-NETS seq 5 permit 172.16.192.0/22 ge 24 le 24
route-map RM-E2O permit 10
 match ip address prefix-list PL-CORE-NETS
router eigrp 100
 distribute-list 21 in Ethernet0/1
 offset-list 8 in 5000 Ethernet0/0
 offset-list 26 in 5000 Ethernet0/1
 redistribute ospf 1 metric 1000000 1 255 1 1500
 distribute-list 70 out ospf 1
router ospf 1
 redistribute eigrp 100 subnets route-map RM-E2O
access-list 70 permit 10.40.89.0 0.0.0.255
```

## レビュー観点（実測は poc/rtctl/README.md）

- **T1 の主罠**: permit 列挙にトランジット網(10.1.24.0/30・10.1.34.0/30)を含め
  忘れると、除外対象でない 10.1.34.0/30 が対向フィード経由へ**迂回**する
  (経路は失われないため気づきにくい)。「除外対象以外に影響を与えない」の採点は
  ここを見ている。
- **T2**: 障害時切替の要件があるため、フィルタ(distribute-list)では要件を満たせ
  ない(topology table から代替経路ごと消える)。メトリック操作(offset-list 等)が
  必要。offset は非優先側の in に掛ける。RD にも加算されるため、offset が大きすぎ
  ると FS が消えて切替がクエリ経由になる(本seedの 5000 は FS 維持圏内)。
- **T3**: 1 行 prefix-list の正準解は `permit 172.16.192.0/22 ge 24 le 24`
  (連続 4 本の /24 は /22 に整列している)。`ge 24` のみ等でも盤面上は同効果。
- **T4**: `distribute-list 70 out ospf 1` は**再配送方向のフィルタ**。
  `redistribute ospf 1` は OSPF 走行 IF の connected(10.1.15.0/30)も随伴させるが、
  permit 列挙がこれも遮断する。
- **T6**: source 無指定の ping は失敗する(RT05 はトランジット網 10.1.24.0/30 への
  経路を持たない。T3 のフィルタが正しく効いている証拠でもある)。
