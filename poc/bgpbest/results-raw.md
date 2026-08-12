
---
# probe 実行 2026-08-12 11:42 (checks=['b1'])

## B1/B2: 基線(5経路)の表・detail 書式

RT01 show ip bgp:
```
BGP table version is 1, local router ID is 1.1.1.1
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 *    198.51.100.0     10.0.14.4                0             0 65300 i
```

RT01 show ip bgp 198.51.100.0:
```
BGP routing table entry for 198.51.100.0/24, version 0
Paths: (1 available, no best path)
  Not advertised to any peer
  Refresh Epoch 1
  65300
    10.0.14.4 (inaccessible) from 10.0.14.4 (4.4.4.4)
      Origin IGP, metric 0, localpref 100, valid, external
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 11:42:00 UTC
```

RT01 show ip bgp summary:
```
BGP router identifier 1.1.1.1, local AS number 65100
BGP table version is 1, main routing table version 1
1 network entries using 248 bytes of memory
1 path entries using 136 bytes of memory
1/0 BGP path/bestpath attribute entries using 296 bytes of memory
1 BGP AS-PATH entries using 24 bytes of memory
0 BGP route-map cache entries using 0 bytes of memory
0 BGP filter-list cache entries using 0 bytes of memory
BGP using 704 total bytes of memory
BGP activity 1/0 prefixes, 1/0 paths, scan interval 60 secs
1 networks peaked at 11:42:00 Aug 12 2026 UTC (00:00:03.878 ago)

Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
5.5.5.5         4        65100       2       2        1    0    0 00:00:12        0
6.6.6.6         4        65100       2       2        1    0    0 00:00:11        0
10.0.12.2       4        65200       3       3        1    0    0 00:01:03        0
10.0.13.3       4        65200       3       3        1    0    0 00:01:02        0
10.0.14.4       4        65300       5       3        1    0    0 00:00:59        1
```

RT01 show ip bgp 198.51.100.0 bestpath(有無の確認):
```
BGP routing table entry for 198.51.100.0/24, version 0
Paths: (2 available, no best path)
  Not advertised to any peer
```

---
# probe 実行 2026-08-12 11:44 (checks=['b1', 'b3', 'b4', 'b5', 'b16', 'b7', 'b8', 'b10', 'b13', 'b11', 'b12', 'b15', 'restore'])

## B1/B2: 基線(5経路)の表・detail 書式

RT01 show ip bgp:
```
BGP table version is 2, local router ID is 1.1.1.1
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 * i  198.51.100.0     5.5.5.5                  0    100      0 65200 i
 * i                   6.6.6.6                  0    100      0 65200 i
 *                     10.0.13.3                0             0 65200 i
 *>                    10.0.12.2                0             0 65200 i
 *                     10.0.14.4                0             0 65300 i
```

RT01 show ip bgp 198.51.100.0:
```
BGP routing table entry for 198.51.100.0/24, version 2
Paths: (5 available, best #4, table default)
  Advertised to update-groups:
     1          2         
  Refresh Epoch 1
  65200
    5.5.5.5 (metric 11) from 5.5.5.5 (5.5.5.5)
      Origin IGP, metric 0, localpref 100, valid, internal
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 11:42:11 UTC
  Refresh Epoch 1
  65200
    6.6.6.6 (metric 101) from 6.6.6.6 (6.6.6.6)
      Origin IGP, metric 0, localpref 100, valid, internal
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 11:42:11 UTC
  Refresh Epoch 1
  65200
    10.0.13.3 from 10.0.13.3 (3.3.3.3)
      Origin IGP, metric 0, localpref 100, valid, external
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 11:42:10 UTC
  Refresh Epoch 1
  65200
    10.0.12.2 from 10.0.12.2 (2.2.2.2)
      Origin IGP, metric 0, localpref 100, valid, external, best
      rx pathid: 0, tx pathid: 0x0
      Updated on Aug 12 2026 11:42:03 UTC
  Refresh Epoch 1
  65300
    10.0.14.4 from 10.0.14.4 (4.4.4.4)
      Origin IGP, metric 0, localpref 100, valid, external
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 11:42:00 UTC
```

RT01 show ip bgp summary:
```
BGP router identifier 1.1.1.1, local AS number 65100
BGP table version is 2, main routing table version 2
1 network entries using 248 bytes of memory
5 path entries using 680 bytes of memory
3/1 BGP path/bestpath attribute entries using 888 bytes of memory
2 BGP AS-PATH entries using 48 bytes of memory
0 BGP route-map cache entries using 0 bytes of memory
0 BGP filter-list cache entries using 0 bytes of memory
BGP using 1864 total bytes of memory
BGP activity 1/0 prefixes, 5/0 paths, scan interval 60 secs
1 networks peaked at 11:42:00 Aug 12 2026 UTC (00:03:00.804 ago)

Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
5.5.5.5         4        65100       8       7        2    0    0 00:03:09        1
6.6.6.6         4        65100       8       8        2    0    0 00:03:08        1
10.0.12.2       4        65200       8       8        2    0    0 00:04:00        1
10.0.13.3       4        65200       8       8        2    0    0 00:03:59        1
10.0.14.4       4        65300       8       8        2    0    0 00:03:56        1
```

RT01 show ip bgp 198.51.100.0 bestpath(有無の確認):
```
BGP routing table entry for 198.51.100.0/24, version 2
Paths: (5 available, best #4, table default)
  Advertised to update-groups:
     1          2         
  Refresh Epoch 1
  65200
    10.0.12.2 from 10.0.12.2 (2.2.2.2)
      Origin IGP, metric 0, localpref 100, valid, external, best
      rx pathid: 0, tx pathid: 0x0
      Updated on Aug 12 2026 11:42:03 UTC
```

## B3: neighbor weight 40000(RT03 向け)が最優先
- best from = `None` (期待= 10.0.13.3)

RT01 show ip bgp (Weight 40000 行あり):
```
BGP table version is 3, local router ID is 1.1.1.1
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 * i  198.51.100.0     5.5.5.5                  0    100      0 65200 i
 * i                   6.6.6.6                  0    100      0 65200 i
 *>                    10.0.13.3                0         40000 65200 i
 *                     10.0.12.2                0             0 65200 i
 *                     10.0.14.4                0             0 65300 i
```

RT01 show ip bgp 198.51.100.0:
```
BGP routing table entry for 198.51.100.0/24, version 3
Paths: (5 available, best #3, table default)
  Advertised to update-groups:
     1          2         
  Refresh Epoch 1
  65200
    5.5.5.5 (metric 11) from 5.5.5.5 (5.5.5.5)
      Origin IGP, metric 0, localpref 100, valid, internal
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 11:42:11 UTC
  Refresh Epoch 1
  65200
    6.6.6.6 (metric 101) from 6.6.6.6 (6.6.6.6)
      Origin IGP, metric 0, localpref 100, valid, internal
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 11:42:11 UTC
  Refresh Epoch 2
  65200
    10.0.13.3 from 10.0.13.3 (3.3.3.3)
      Origin IGP, metric 0, localpref 100, weight 40000, valid, external, best
      rx pathid: 0, tx pathid: 0x0
      Updated on Aug 12 2026 11:45:03 UTC
  Refresh Epoch 1
  65200
    10.0.12.2 from 10.0.12.2 (2.2.2.2)
      Origin IGP, metric 0, localpref 100, valid, external
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 11:42:03 UTC
  Refresh Epoch 1
  65300
    10.0.14.4 from 10.0.14.4 (4.4.4.4)
      Origin IGP, metric 0, localpref 100, valid, external
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 11:42:00 UTC
```

## B4: LOCAL_PREF 200 > AS-PATH 長(+iBGP 伝播)
- best from = `None` (期待= 10.0.14.4・path 最長なのに LP で勝つ)

RT01 show ip bgp (LocPrf 200 行あり):
```
BGP table version is 5, local router ID is 1.1.1.1
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 * i  198.51.100.0     5.5.5.5                  0    100      0 65200 i
 * i                   6.6.6.6                  0    100      0 65200 i
 *                     10.0.13.3                0             0 65200 i
 *                     10.0.12.2                0             0 65200 i
 *>                    10.0.14.4                0    200      0 65300 65300 65300 i
```

RT01 show ip bgp 198.51.100.0:
```
BGP routing table entry for 198.51.100.0/24, version 5
Paths: (5 available, best #5, table default)
  Advertised to update-groups:
     1          2         
  Refresh Epoch 1
  65200
    5.5.5.5 (metric 11) from 5.5.5.5 (5.5.5.5)
      Origin IGP, metric 0, localpref 100, valid, internal
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 11:42:11 UTC
  Refresh Epoch 1
  65200
    6.6.6.6 (metric 101) from 6.6.6.6 (6.6.6.6)
      Origin IGP, metric 0, localpref 100, valid, internal
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 11:42:11 UTC
  Refresh Epoch 3
  65200
    10.0.13.3 from 10.0.13.3 (3.3.3.3)
      Origin IGP, metric 0, localpref 100, valid, external
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 11:46:08 UTC
  Refresh Epoch 1
  65200
    10.0.12.2 from 10.0.12.2 (2.2.2.2)
      Origin IGP, metric 0, localpref 100, valid, external
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 11:42:03 UTC
  Refresh Epoch 2
  65300 65300 65300
    10.0.14.4 from 10.0.14.4 (4.4.4.4)
      Origin IGP, metric 0, localpref 200, valid, external, best
      rx pathid: 0, tx pathid: 0x0
      Updated on Aug 12 2026 11:46:44 UTC
```

RT05 show ip bgp 198.51.100.0 (RT01 経由の LP 伝播):
```
BGP routing table entry for 198.51.100.0/24, version 2
Paths: (2 available, best #2, table default)
  Advertised to update-groups:
     2         
  Refresh Epoch 1
  65300 65300 65300
    10.0.14.4 (inaccessible) from 1.1.1.1 (1.1.1.1)
      Origin IGP, metric 0, localpref 200, valid, internal
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 11:46:44 UTC
  Refresh Epoch 1
  65200
    10.0.25.2 from 10.0.25.2 (2.2.2.2)
      Origin IGP, metric 0, localpref 100, valid, external, best
      rx pathid: 0, tx pathid: 0x0
      Updated on Aug 12 2026 11:42:03 UTC
```

## B5: 自機起源 = weight 32768 行の表示

RT01 show ip bgp (203.0.113.0/24 = 自機起源):
```
BGP table version is 7, local router ID is 1.1.1.1
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 * i  198.51.100.0     5.5.5.5                  0    100      0 65200 i
 * i                   6.6.6.6                  0    100      0 65200 i
 *                     10.0.13.3                0             0 65200 i
 *                     10.0.12.2                0             0 65200 i
 *>                    10.0.14.4                0             0 65300 i
 *>   203.0.113.0      0.0.0.0                  0         32768 i
```

RT01 show ip bgp 203.0.113.0:
```
BGP routing table entry for 203.0.113.0/24, version 7
Paths: (1 available, best #1, table default)
  Flag: 0x8100
  Advertised to update-groups: (Pending Update Generation)
     2         
  Refresh Epoch 1
  Local
    0.0.0.0 from 0.0.0.0 (1.1.1.1)
      Origin IGP, metric 0, localpref 100, weight 32768, valid, sourced, local, best
      rx pathid: 0, tx pathid: 0x0
      Updated on Aug 12 2026 11:47:27 UTC
```

## B16: LP を eBGP ピア向け out に set(送られるか?)

RT01 show ip bgp 198.51.100.0 (RT02 経路の localpref 表示に注目):
```
BGP routing table entry for 198.51.100.0/24, version 6
Paths: (5 available, best #5, table default)
  Advertised to update-groups:
     1          2         
  Refresh Epoch 1
  65200
    5.5.5.5 (metric 11) from 5.5.5.5 (5.5.5.5)
      Origin IGP, metric 0, localpref 100, valid, internal
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 11:42:11 UTC
  Refresh Epoch 1
  65200
    6.6.6.6 (metric 101) from 6.6.6.6 (6.6.6.6)
      Origin IGP, metric 0, localpref 100, valid, internal
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 11:42:11 UTC
  Refresh Epoch 3
  65200
    10.0.13.3 from 10.0.13.3 (3.3.3.3)
      Origin IGP, metric 0, localpref 100, valid, external
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 11:46:08 UTC
  Refresh Epoch 1
  65200
    10.0.12.2 from 10.0.12.2 (2.2.2.2)
      Origin IGP, metric 0, localpref 100, valid, external
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 11:47:32 UTC
  Refresh Epoch 2
  65300
    10.0.14.4 from 10.0.14.4 (4.4.4.4)
      Origin IGP, metric 0, localpref 100, valid, external, best
      rx pathid: 0, tx pathid: 0x0
      Updated on Aug 12 2026 11:47:22 UTC
```
- ↑ RT02(10.0.12.2) からの経路の localpref が 100(既定)のままなら「eBGP には送られない」が確定

## B7: origin IGP vs incomplete の決着
- 隣接を ['RT02', 'RT03'] に限定(収束 0s・経路2本)
- best from = `None` (期待= 10.0.12.2・origin i が ? に勝つ)

RT01 show ip bgp 198.51.100.0 (i vs ?):
```
BGP routing table entry for 198.51.100.0/24, version 9
Paths: (1 available, best #1, table default)
  Advertised to update-groups:
     1         
  Refresh Epoch 3
  65200
    10.0.12.2 from 10.0.12.2 (2.2.2.2)
      Origin IGP, metric 0, localpref 100, valid, external, best
      rx pathid: 0, tx pathid: 0x0
      Updated on Aug 12 2026 11:47:44 UTC
```

RT01 show ip bgp (Path 列の i/? 表示):
```
BGP table version is 9, local router ID is 1.1.1.1
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 *>   198.51.100.0     10.0.12.2                0             0 65200 i
```

## B8: MED(同一隣接AS)= 小さい方が勝つ・入替で反転
- 隣接を ['RT02', 'RT03'] に限定(収束 0s・経路2本)
- MED 50(RT02) vs 200(RT03): best from = `None` (期待= 10.0.12.2)

RT01 show ip bgp (Metric 列 50/200):
```
BGP table version is 11, local router ID is 1.1.1.1
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 *    198.51.100.0     10.0.13.3              200             0 65200 i
 *>                    10.0.12.2               50             0 65200 i
```

RT01 show ip bgp 198.51.100.0:
```
BGP routing table entry for 198.51.100.0/24, version 11
Paths: (2 available, best #2, table default)
  Advertised to update-groups:
     1         
  Refresh Epoch 5
  65200
    10.0.13.3 from 10.0.13.3 (3.3.3.3)
      Origin IGP, metric 200, localpref 100, valid, external
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 11:49:18 UTC
  Refresh Epoch 3
  65200
    10.0.12.2 from 10.0.12.2 (2.2.2.2)
      Origin IGP, metric 50, localpref 100, valid, external, best
      rx pathid: 0, tx pathid: 0x0
      Updated on Aug 12 2026 11:49:17 UTC
```
- RT02 の MED を 300 へ → best が RT03 に反転(所要 -1s)

RT01 show ip bgp 198.51.100.0 (反転後):
```
BGP routing table entry for 198.51.100.0/24, version 12
Paths: (2 available, best #1, table default)
  Advertised to update-groups:
     1         
  Refresh Epoch 5
  65200
    10.0.13.3 from 10.0.13.3 (3.3.3.3)
      Origin IGP, metric 200, localpref 100, valid, external, best
      rx pathid: 0, tx pathid: 0x0
      Updated on Aug 12 2026 11:49:18 UTC
  Refresh Epoch 4
  65200
    10.0.12.2 from 10.0.12.2 (2.2.2.2)
      Origin IGP, metric 300, localpref 100, valid, external
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 11:50:23 UTC
```

## B10: MED 欠落の既定値(=0)と missing-as-worst
- MED 欠落(RT02) vs 200(RT03): best from = `None` (期待= 10.0.12.2・欠落は 0 扱い)

RT01 show ip bgp (RT02 行の Metric 列が空欄か 0 か):
```
BGP table version is 13, local router ID is 1.1.1.1
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 *    198.51.100.0     10.0.13.3              200             0 65200 i
 *>                    10.0.12.2                0             0 65200 i
```

RT01 show ip bgp 198.51.100.0 (欠落側 detail の metric 表示):
```
BGP routing table entry for 198.51.100.0/24, version 13
Paths: (2 available, best #2, table default)
  Advertised to update-groups:
     1         
  Refresh Epoch 5
  65200
    10.0.13.3 from 10.0.13.3 (3.3.3.3)
      Origin IGP, metric 200, localpref 100, valid, external
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 11:49:18 UTC
  Refresh Epoch 6
  65200
    10.0.12.2 from 10.0.12.2 (2.2.2.2)
      Origin IGP, metric 0, localpref 100, valid, external, best
      rx pathid: 0, tx pathid: 0x0
      Updated on Aug 12 2026 11:51:56 UTC
```
- `bgp bestpath med missing-as-worst` 投入 → best が RT03 へ(clear 無しで反転するか: 所要 -1s)

RT01 show ip bgp 198.51.100.0 (worst 扱い後):
```
BGP routing table entry for 198.51.100.0/24, version 14
BGP Bestpath: med
Paths: (2 available, best #2, table default)
  Advertised to update-groups:
     1         
  Refresh Epoch 5
  65200
    10.0.13.3 from 10.0.13.3 (3.3.3.3)
      Origin IGP, metric 200, localpref 100, valid, external
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 11:49:18 UTC
  Refresh Epoch 6
  65200
    10.0.12.2 from 10.0.12.2 (2.2.2.2)
      Origin IGP, metric 0, localpref 100, valid, external, best
      rx pathid: 0, tx pathid: 0x0
      Updated on Aug 12 2026 11:51:56 UTC
```

## B13: oldest 勝ち → bgp bestpath compare-routerid
- 隣接を ['RT02', 'RT03'] に限定(収束 0s・経路2本)
- 素の 2経路(全属性タイ)の best from = `None`

RT01 show ip bgp 198.51.100.0 (タイ状態):
```
BGP routing table entry for 198.51.100.0/24, version 15
Paths: (2 available, best #2, table default)
  Advertised to update-groups:
     1         
  Refresh Epoch 7
  65200
    10.0.13.3 from 10.0.13.3 (3.3.3.3)
      Origin IGP, metric 0, localpref 100, valid, external
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 11:55:03 UTC
  Refresh Epoch 6
  65200
    10.0.12.2 from 10.0.12.2 (2.2.2.2)
      Origin IGP, metric 0, localpref 100, valid, external, best
      rx pathid: 0, tx pathid: 0x0
      Updated on Aug 12 2026 11:51:56 UTC
```
- RT03 を flap → 再確立後の best from = `None` (期待= `10.0.12.2` のまま = oldest 勝ちの実証)

RT01 show ip bgp 198.51.100.0 (flap 後):
```
BGP routing table entry for 198.51.100.0/24, version 15
Paths: (2 available, best #2, table default)
  Advertised to update-groups:
     1         
  Refresh Epoch 2
  65200
    10.0.13.3 from 10.0.13.3 (3.3.3.3)
      Origin IGP, metric 0, localpref 100, valid, external
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 11:56:22 UTC
  Refresh Epoch 6
  65200
    10.0.12.2 from 10.0.12.2 (2.2.2.2)
      Origin IGP, metric 0, localpref 100, valid, external, best
      rx pathid: 0, tx pathid: 0x0
      Updated on Aug 12 2026 11:51:56 UTC
```
- `bgp bestpath compare-routerid` 投入 → best from = `None` (期待= 10.0.12.2=RID 2.2.2.2 < 3.3.3.3。clear 無し所要 -1s)

RT01 show ip bgp 198.51.100.0 (compare-routerid 後):
```
BGP routing table entry for 198.51.100.0/24, version 16
BGP Bestpath: compare-routerid
Paths: (2 available, best #2, table default)
  Advertised to update-groups:
     1         
  Refresh Epoch 2
  65200
    10.0.13.3 from 10.0.13.3 (3.3.3.3)
      Origin IGP, metric 0, localpref 100, valid, external
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 11:56:22 UTC
  Refresh Epoch 6
  65200
    10.0.12.2 from 10.0.12.2 (2.2.2.2)
      Origin IGP, metric 0, localpref 100, valid, external, best
      rx pathid: 0, tx pathid: 0x0
      Updated on Aug 12 2026 11:51:56 UTC
```

## B11: eBGP > iBGP
- 隣接を ['RT04', 'RT05'] に限定(収束 0s・経路2本)
- best from = `None` (期待= 10.0.14.4・eBGP が iBGP に勝つ)

RT01 show ip bgp (iBGP 行の i マーカーと LocPrf 100):
```
BGP table version is 21, local router ID is 1.1.1.1
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 *>   198.51.100.0     10.0.14.4                0             0 65300 i
 * i                   5.5.5.5                  0    100      0 65200 i
```

RT01 show ip bgp 198.51.100.0:
```
BGP routing table entry for 198.51.100.0/24, version 21
Paths: (2 available, best #1, table default)
  Advertised to update-groups:
     3         
  Refresh Epoch 1
  65300
    10.0.14.4 from 10.0.14.4 (4.4.4.4)
      Origin IGP, metric 0, localpref 100, valid, external, best
      rx pathid: 0, tx pathid: 0x0
      Updated on Aug 12 2026 11:58:09 UTC
  Refresh Epoch 1
  65200
    5.5.5.5 (metric 11) from 5.5.5.5 (5.5.5.5)
      Origin IGP, metric 0, localpref 100, valid, internal
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 11:58:09 UTC
```

RT01 show ip bgp 198.51.100.0 (eBGP 断後= iBGP best):
```
BGP routing table entry for 198.51.100.0/24, version 22
Paths: (1 available, best #1, table default)
  Not advertised to any peer
  Refresh Epoch 1
  65200
    5.5.5.5 (metric 11) from 5.5.5.5 (5.5.5.5)
      Origin IGP, metric 0, localpref 100, valid, internal, best
      rx pathid: 0, tx pathid: 0x0
      Updated on Aug 12 2026 11:58:09 UTC
```

## B12: IGP metric to next-hop(detail の `(metric N)`)
- 隣接を ['RT05', 'RT06'] に限定(収束 0s・経路2本)
- cost 10(→RT05) vs 100(→RT06): best from = `None` (期待= 5.5.5.5)

RT01 show ip bgp 198.51.100.0 (`(metric N)` 表示):
```
BGP routing table entry for 198.51.100.0/24, version 24
Paths: (2 available, best #2, table default)
  Not advertised to any peer
  Refresh Epoch 1
  65200
    6.6.6.6 (metric 101) from 6.6.6.6 (6.6.6.6)
      Origin IGP, metric 0, localpref 100, valid, internal
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 12:00:28 UTC
  Refresh Epoch 1
  65200
    5.5.5.5 (metric 11) from 5.5.5.5 (5.5.5.5)
      Origin IGP, metric 0, localpref 100, valid, internal, best
      rx pathid: 0, tx pathid: 0x0
      Updated on Aug 12 2026 11:58:09 UTC
```
- コスト入替 → best が RT06 へ反転(所要 -1s・clear 無し=NHT/scanner の反応時間)

RT01 show ip bgp 198.51.100.0 (反転後):
```
BGP routing table entry for 198.51.100.0/24, version 25
Paths: (2 available, best #1, table default)
  Not advertised to any peer
  Refresh Epoch 1
  65200
    6.6.6.6 (metric 11) from 6.6.6.6 (6.6.6.6)
      Origin IGP, metric 0, localpref 100, valid, internal, best
      rx pathid: 0, tx pathid: 0x0
      Updated on Aug 12 2026 12:00:28 UTC
  Refresh Epoch 1
  65200
    5.5.5.5 (metric 101) from 5.5.5.5 (5.5.5.5)
      Origin IGP, metric 0, localpref 100, valid, internal
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 11:58:09 UTC
```

## B15: next-hop 解決不能(inaccessible)の実表示
- 隣接を ['RT04', 'RT05'] に限定(収束 0s・経路2本)

RT01 show ip bgp (無効経路の行マーカー):
```
BGP table version is 27, local router ID is 1.1.1.1
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 *>   198.51.100.0     10.0.14.4                0             0 65300 i
 * i                   10.0.25.2                0    100      0 65200 i
```

RT01 show ip bgp 198.51.100.0 (inaccessible 表示):
```
BGP routing table entry for 198.51.100.0/24, version 27
Paths: (2 available, best #1, table default)
  Flag: 0x8100
  Advertised to update-groups: (Pending Update Generation)
     3          6         
  Refresh Epoch 1
  65300
    10.0.14.4 from 10.0.14.4 (4.4.4.4)
      Origin IGP, metric 0, localpref 100, valid, external, best
      rx pathid: 0, tx pathid: 0x0
      Updated on Aug 12 2026 12:05:16 UTC
  Refresh Epoch 1
  65200
    10.0.25.2 (inaccessible) from 5.5.5.5 (5.5.5.5)
      Origin IGP, metric 0, localpref 100, valid, internal
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 12:05:23 UTC
```
- ↑ 属性がどれだけ良くても候補から外れることの実表示

## 復元: 全隣接 no shutdown(収束 6s)

RT01 show ip bgp (最終基線):
```
BGP table version is 27, local router ID is 1.1.1.1
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 * i  198.51.100.0     6.6.6.6                  0    100      0 65200 i
 *                     10.0.12.2                0             0 65200 i
 *                     10.0.13.3                0             0 65200 i
 *>                    10.0.14.4                0             0 65300 i
 * i                   5.5.5.5                  0    100      0 65200 i
```

---
# probe2 実行 2026-08-12 12:13

## B7b: origin i vs ?(redistribute connected でやり直し)
- 隣接を ['RT02', 'RT03'] に限定(収束 0s・経路2本)
- best from = `10.0.12.2` (期待= 10.0.12.2・i が ? に勝つ)

RT01 show ip bgp 198.51.100.0 (i vs ?):
```
BGP routing table entry for 198.51.100.0/24, version 28
Paths: (2 available, best #2, table default)
  Advertised to update-groups:
     6         
  Refresh Epoch 3
  65200
    10.0.13.3 from 10.0.13.3 (3.3.3.3)
      Origin incomplete, metric 0, localpref 100, valid, external
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 12:13:55 UTC
  Refresh Epoch 2
  65200
    10.0.12.2 from 10.0.12.2 (2.2.2.2)
      Origin IGP, metric 0, localpref 100, valid, external, best
      rx pathid: 0, tx pathid: 0x0
      Updated on Aug 12 2026 12:05:30 UTC
```

RT01 show ip bgp (Path 列の ? 表示):
```
BGP table version is 31, local router ID is 1.1.1.1
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 *>   3.3.3.3/32       10.0.13.3                0             0 65200 ?
 r>   10.0.13.0/24     10.0.13.3                0             0 65200 ?
 *>   10.0.36.0/24     10.0.13.3                0             0 65200 ?
 *    198.51.100.0     10.0.13.3                0             0 65200 ?
 *>                    10.0.12.2                0             0 65200 i
```

## B13b: ★best 側を flap → oldest の持続を判別
- 隣接を ['RT02', 'RT03'] に限定(収束 0s・経路2本)

タイ状態(best from = 10.0.12.2):
```
BGP routing table entry for 198.51.100.0/24, version 28
Paths: (2 available, best #2, table default)
  Advertised to update-groups:
     6         
  Refresh Epoch 4
  65200
    10.0.13.3 from 10.0.13.3 (3.3.3.3)
      Origin IGP, metric 0, localpref 100, valid, external
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 12:15:29 UTC
  Refresh Epoch 2
  65200
    10.0.12.2 from 10.0.12.2 (2.2.2.2)
      Origin IGP, metric 0, localpref 100, valid, external, best
      rx pathid: 0, tx pathid: 0x0
      Updated on Aug 12 2026 12:05:30 UTC
```
- ★best 側(RT02)を flap する
- 再確立後の best from = `10.0.13.3` (期待= `10.0.13.3` の維持=oldest 勝ち。戻った側は新しいので奪還できない)

flap 後:
```
BGP routing table entry for 198.51.100.0/24, version 35
Paths: (2 available, best #2, table default)
  Advertised to update-groups:
     6         
  Refresh Epoch 2
  65200
    10.0.12.2 from 10.0.12.2 (2.2.2.2)
      Origin IGP, metric 0, localpref 100, valid, external
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 12:15:43 UTC
  Refresh Epoch 4
  65200
    10.0.13.3 from 10.0.13.3 (3.3.3.3)
      Origin IGP, metric 0, localpref 100, valid, external, best
      rx pathid: 0, tx pathid: 0x0
      Updated on Aug 12 2026 12:15:29 UTC
```

## B13c: ★compare-routerid は oldest に勝つか
- crid 投入前の best from = `10.0.13.3` (期待= 10.0.13.3=older)
- `bgp bestpath compare-routerid` → best from = `10.0.12.2` (期待= 10.0.12.2=RID 2.2.2.2。oldest より優先・clear 無し所要 11s)

compare-routerid 後(detail 冒頭の BGP Bestpath: 行にも注目):
```
BGP routing table entry for 198.51.100.0/24, version 36
BGP Bestpath: compare-routerid
Paths: (2 available, best #1, table default)
  Advertised to update-groups:
     6         
  Refresh Epoch 2
  65200
    10.0.12.2 from 10.0.12.2 (2.2.2.2)
      Origin IGP, metric 0, localpref 100, valid, external, best
      rx pathid: 0, tx pathid: 0x0
      Updated on Aug 12 2026 12:15:43 UTC
  Refresh Epoch 4
  65200
    10.0.13.3 from 10.0.13.3 (3.3.3.3)
      Origin IGP, metric 0, localpref 100, valid, external
      rx pathid: 0, tx pathid: 0
      Updated on Aug 12 2026 12:15:29 UTC
```

## B17: ★真の MED 欠落(2 AS ホップ)の表示
- 隣接を ['RT02', 'RT03'] に限定(収束 0s・経路2本)

RT01 show ip bgp (172.20.77.0 行の Metric 列= 欠落の表示):
```
BGP table version is 38, local router ID is 1.1.1.1
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 *>   172.20.77.0/24   10.0.13.3                              0 65200 65400 i
 *>   198.51.100.0     10.0.12.2                0             0 65200 i
 *                     10.0.13.3                0             0 65200 i
```

RT01 show ip bgp 172.20.77.0 (detail の metric 表示):
```
BGP routing table entry for 172.20.77.0/24, version 38
Paths: (1 available, best #1, table default)
  Advertised to update-groups:
     6         
  Refresh Epoch 4
  65200 65400
    10.0.13.3 from 10.0.13.3 (3.3.3.3)
      Origin IGP, localpref 100, valid, external, best
      rx pathid: 0, tx pathid: 0x0
      Updated on Aug 12 2026 12:17:22 UTC
```

RT03 show ip bgp 172.20.77.0 (RT03 では MED 受信済のはず):
```
BGP routing table entry for 172.20.77.0/24, version 17
Paths: (1 available, best #1, table default)
  Advertised to update-groups:
     1         
  Refresh Epoch 1
  65400
    10.0.36.6 from 10.0.36.6 (6.6.6.6)
      Origin IGP, metric 0, localpref 100, valid, external, best
      rx pathid: 0, tx pathid: 0x0
      Updated on Aug 12 2026 12:17:22 UTC
```

## cfgref: 紙面 cfg 抜粋の忠実性参照

RT01 show running-config | section router bgp:
```
router bgp 65100
 bgp router-id 1.1.1.1
 bgp log-neighbor-changes
 neighbor 5.5.5.5 remote-as 65100
 neighbor 5.5.5.5 shutdown
 neighbor 5.5.5.5 update-source Loopback0
 neighbor 6.6.6.6 remote-as 65100
 neighbor 6.6.6.6 shutdown
 neighbor 6.6.6.6 update-source Loopback0
 neighbor 10.0.12.2 remote-as 65200
 neighbor 10.0.13.3 remote-as 65200
 neighbor 10.0.14.4 remote-as 65300
 neighbor 10.0.14.4 shutdown
 !
 address-family ipv4
  neighbor 5.5.5.5 activate
  neighbor 6.6.6.6 activate
  neighbor 10.0.12.2 activate
  neighbor 10.0.13.3 activate
  neighbor 10.0.14.4 activate
 exit-address-family
```

RT05 show running-config | section router bgp:
```
router bgp 65100
 bgp router-id 5.5.5.5
 bgp log-neighbor-changes
 neighbor 1.1.1.1 remote-as 65100
 neighbor 1.1.1.1 update-source Loopback0
 neighbor 10.0.25.2 remote-as 65200
 !
 address-family ipv4
  neighbor 1.1.1.1 activate
  neighbor 1.1.1.1 next-hop-self
  neighbor 10.0.25.2 activate
 exit-address-family
```

## 復元: 全隣接 no shutdown(収束 0s)
