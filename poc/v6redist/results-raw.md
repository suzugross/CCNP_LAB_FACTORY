
## sweep run (base, e16, e1, e2, e3, e4, e5, e6, e7, e8, e9, e10, e11, e12, e13, e14, e15)

### B0 — 基線(ユーザラボ複製) — 双方向とも route-map でトランジットのみ通過

| 観測点 | 値 |
|---|---|
| RT-C redist | `redistribute ospf 544 match internal metric 10000 100 255 1 1500 route-map OMAP01 include-connected ; redistribute eigrp 5400 route-map EMAP01 include-connected` |
| C1 | `2001:DB8:1A:A::/64=— / 2001:DB8:A:A::/64=OE2 [110/20] / ::/0=—` |
| RA | `2001:DB8:1A:A::/64=— / 2001:DB8:A:A::/64=OE2 [110/20] / ::/0=—` |
| RB | `2001:DB8:2:1::/64=— / 2001:DB8:1:1::/64=EX [170/1536000] / ::/0=—` |
| C2 | `2001:DB8:2:1::/64=— / 2001:DB8:1:1::/64=EX [170/2048000] / ::/0=—` |
| ping C1->C2 | `NOROUTE` |
| ping C2->C1 | `NOROUTE` |

補足:
```
✅ ユーザラボ実測と完全一致

EIGRP-IPv6 VR(NAMED) Topology Table for AS(5400)/ID(1.1.1.1)
Codes: P - Passive, A - Active, U - Update, Q - Query, R - Reply,
       r - reply Status, s - sia Status 

P 2001:DB8:1:1::/64, 1 successors, FD is 131072000
        via Redistributed (131072000/0)
P 2001:DB8:A:A::/64, 1 successors, FD is 131072000
        via Connected, Ethernet0/1
P 2001:DB8:1A:A::/64, 1 successors, FD is 196608000
        via FE80::A8BB:CCFF:FE01:EA00 (196608000/131072000), Ethernet0/1

		Type-5 AS External Link States

ADV Router       Age         Seq#        Prefix
 2.2.2.2         26          0x80000001  2001:DB8:A:A::/64
```

### E16 — ★route-map 節を書かずに redistribute を再発行(no を前置しない) — 外れるか

適用 delta:
```
router eigrp NAMED
 address-family ipv6 unicast autonomous-system 5400
  topology base
   redistribute ospf 544 match internal metric 10000 100 255 1 1500 include-connected
  exit-af-topology
 exit-address-family
exit
router ospfv3 544
 address-family ipv6 unicast
  redistribute eigrp 5400 include-connected
 exit-address-family
exit
```

| 観測点 | 値 |
|---|---|
| RT-C redist | `redistribute ospf 544 match internal metric 10000 100 255 1 1500 route-map OMAP01 include-connected ; redistribute eigrp 5400 route-map EMAP01 include-connected` |
| C1 | `2001:DB8:1A:A::/64=— / 2001:DB8:A:A::/64=OE2 [110/20] / ::/0=—` |
| RA | `2001:DB8:1A:A::/64=— / 2001:DB8:A:A::/64=OE2 [110/20] / ::/0=—` |
| RB | `2001:DB8:2:1::/64=— / 2001:DB8:1:1::/64=EX [170/1536000] / ::/0=—` |
| C2 | `2001:DB8:2:1::/64=— / 2001:DB8:1:1::/64=EX [170/2048000] / ::/0=—` |
| ping C1->C2 | `NOROUTE` |
| ping C2->C1 | `NOROUTE` |
| (参考) delta 適用前の redist 行 | `redistribute ospf 544 match internal metric 10000 100 255 1 1500 route-map OMAP01 include-connected ; redistribute eigrp 5400 route-map EMAP01 include-connected` |

### E1 — route-map を両方向とも外す(metric 維持・★no を前置)

適用 delta:
```
router eigrp NAMED
 address-family ipv6 unicast autonomous-system 5400
  topology base
   no redistribute ospf 544
   redistribute ospf 544 match internal metric 10000 100 255 1 1500 include-connected
  exit-af-topology
 exit-address-family
exit
router ospfv3 544
 address-family ipv6 unicast
  no redistribute eigrp 5400
  redistribute eigrp 5400 include-connected
 exit-address-family
exit
```

| 観測点 | 値 |
|---|---|
| RT-C redist | `redistribute ospf 544 match internal metric 10000 100 255 1 1500 include-connected ; redistribute eigrp 5400 include-connected` |
| C1 | `2001:DB8:1A:A::/64=OE2 [110/20] / 2001:DB8:A:A::/64=OE2 [110/20] / ::/0=—` |
| RA | `2001:DB8:1A:A::/64=OE2 [110/20] / 2001:DB8:A:A::/64=OE2 [110/20] / ::/0=—` |
| RB | `2001:DB8:2:1::/64=EX [170/1536000] / 2001:DB8:1:1::/64=EX [170/1536000] / ::/0=—` |
| C2 | `2001:DB8:2:1::/64=EX [170/2048000] / 2001:DB8:1:1::/64=EX [170/2048000] / ::/0=—` |
| ping C1->C2 | `100%` |
| ping C2->C1 | `100%` |

### E2 — prefix-list に客先 LAN を追記(トランジットも残る)

適用 delta:
```
ipv6 prefix-list O544 seq 10 permit 2001:DB8:2:1::/64
ipv6 prefix-list E5400 seq 10 permit 2001:DB8:1A:A::/64
```

| 観測点 | 値 |
|---|---|
| RT-C redist | `redistribute ospf 544 match internal metric 10000 100 255 1 1500 route-map OMAP01 include-connected ; redistribute eigrp 5400 route-map EMAP01 include-connected` |
| C1 | `2001:DB8:1A:A::/64=OE2 [110/20] / 2001:DB8:A:A::/64=OE2 [110/20] / ::/0=—` |
| RA | `2001:DB8:1A:A::/64=OE2 [110/20] / 2001:DB8:A:A::/64=OE2 [110/20] / ::/0=—` |
| RB | `2001:DB8:2:1::/64=EX [170/1536000] / 2001:DB8:1:1::/64=EX [170/1536000] / ::/0=—` |
| C2 | `2001:DB8:2:1::/64=EX [170/2048000] / 2001:DB8:1:1::/64=EX [170/2048000] / ::/0=—` |
| ping C1->C2 | `100%` |
| ping C2->C1 | `100%` |

### E3 — ★prefix-list を客先LANのみに置換 — include-connected は route-map に従うか

適用 delta:
```
no ipv6 prefix-list O544
no ipv6 prefix-list E5400
ipv6 prefix-list O544 seq 5 permit 2001:DB8:2:1::/64
ipv6 prefix-list E5400 seq 5 permit 2001:DB8:1A:A::/64
```

| 観測点 | 値 |
|---|---|
| RT-C redist | `redistribute ospf 544 match internal metric 10000 100 255 1 1500 route-map OMAP01 include-connected ; redistribute eigrp 5400 route-map EMAP01 include-connected` |
| C1 | `2001:DB8:1A:A::/64=OE2 [110/20] / 2001:DB8:A:A::/64=— / ::/0=—` |
| RA | `2001:DB8:1A:A::/64=OE2 [110/20] / 2001:DB8:A:A::/64=— / ::/0=—` |
| RB | `2001:DB8:2:1::/64=EX [170/1536000] / 2001:DB8:1:1::/64=— / ::/0=—` |
| C2 | `2001:DB8:2:1::/64=EX [170/2048000] / 2001:DB8:1:1::/64=— / ::/0=—` |
| ping C1->C2 | `100%` |
| ping C2->C1 | `100%` |

### E4 — include-connected を外す(prefix-list は基線のまま)

適用 delta:
```
router eigrp NAMED
 address-family ipv6 unicast autonomous-system 5400
  topology base
   no redistribute ospf 544
   redistribute ospf 544 match internal metric 10000 100 255 1 1500 route-map OMAP01
  exit-af-topology
 exit-address-family
exit
router ospfv3 544
 address-family ipv6 unicast
  no redistribute eigrp 5400
  redistribute eigrp 5400 route-map EMAP01
 exit-address-family
exit
```

| 観測点 | 値 |
|---|---|
| RT-C redist | `redistribute ospf 544 match internal metric 10000 100 255 1 1500 route-map OMAP01 ; redistribute eigrp 5400 route-map EMAP01` |
| C1 | `2001:DB8:1A:A::/64=— / 2001:DB8:A:A::/64=— / ::/0=—` |
| RA | `2001:DB8:1A:A::/64=— / 2001:DB8:A:A::/64=— / ::/0=—` |
| RB | `2001:DB8:2:1::/64=— / 2001:DB8:1:1::/64=— / ::/0=—` |
| C2 | `2001:DB8:2:1::/64=— / 2001:DB8:1:1::/64=— / ::/0=—` |
| ping C1->C2 | `NOROUTE` |
| ping C2->C1 | `NOROUTE` |

### E5 — ★EIGRP 側 redistribute の metric 省略(route-map なし)

適用 delta:
```
router eigrp NAMED
 address-family ipv6 unicast autonomous-system 5400
  topology base
   no redistribute ospf 544
   redistribute ospf 544 include-connected
  exit-af-topology
 exit-address-family
exit
router ospfv3 544
 address-family ipv6 unicast
  redistribute eigrp 5400 include-connected
 exit-address-family
exit
```

| 観測点 | 値 |
|---|---|
| RT-C redist | `redistribute ospf 544 include-connected ; redistribute eigrp 5400 route-map EMAP01 include-connected` |
| C1 | `2001:DB8:1A:A::/64=— / 2001:DB8:A:A::/64=OE2 [110/20] / ::/0=—` |
| RA | `2001:DB8:1A:A::/64=— / 2001:DB8:A:A::/64=OE2 [110/20] / ::/0=—` |
| RB | `2001:DB8:2:1::/64=— / 2001:DB8:1:1::/64=— / ::/0=—` |
| C2 | `2001:DB8:2:1::/64=— / 2001:DB8:1:1::/64=— / ::/0=—` |
| ping C1->C2 | `NOROUTE` |
| ping C2->C1 | `NOROUTE` |

補足:
```
IPv6 Routing Protocol is "eigrp 5400"
    Redistributing protocol eigrp 5400 route-map EMAP01 include-connected
```

### E6 — metric 省略 + default-metric で補う

適用 delta:
```
router eigrp NAMED
 address-family ipv6 unicast autonomous-system 5400
  topology base
   no redistribute ospf 544
   default-metric 10000 100 255 1 1500
   redistribute ospf 544 include-connected
  exit-af-topology
 exit-address-family
exit
router ospfv3 544
 address-family ipv6 unicast
  redistribute eigrp 5400 include-connected
 exit-address-family
exit
```

| 観測点 | 値 |
|---|---|
| RT-C redist | `default-metric 10000 100 255 1 1500 ; redistribute ospf 544 include-connected ; redistribute eigrp 5400 route-map EMAP01 include-connected` |
| C1 | `2001:DB8:1A:A::/64=— / 2001:DB8:A:A::/64=OE2 [110/20] / ::/0=—` |
| RA | `2001:DB8:1A:A::/64=— / 2001:DB8:A:A::/64=OE2 [110/20] / ::/0=—` |
| RB | `2001:DB8:2:1::/64=EX [170/1536000] / 2001:DB8:1:1::/64=EX [170/1536000] / ::/0=—` |
| C2 | `2001:DB8:2:1::/64=EX [170/2048000] / 2001:DB8:1:1::/64=EX [170/2048000] / ::/0=—` |
| ping C1->C2 | `NOROUTE` |
| ping C2->C1 | `0%` |

### E7 — ★参照 prefix-list を未定義に(route-map は在る) — 全許可か全拒否か

適用 delta:
```
no ipv6 prefix-list O544
no ipv6 prefix-list E5400
```

| 観測点 | 値 |
|---|---|
| RT-C redist | `redistribute ospf 544 match internal metric 10000 100 255 1 1500 route-map OMAP01 include-connected ; redistribute eigrp 5400 route-map EMAP01 include-connected` |
| C1 | `2001:DB8:1A:A::/64=OE2 [110/20] / 2001:DB8:A:A::/64=OE2 [110/20] / ::/0=—` |
| RA | `2001:DB8:1A:A::/64=OE2 [110/20] / 2001:DB8:A:A::/64=OE2 [110/20] / ::/0=—` |
| RB | `2001:DB8:2:1::/64=EX [170/1536000] / 2001:DB8:1:1::/64=EX [170/1536000] / ::/0=—` |
| C2 | `2001:DB8:2:1::/64=EX [170/2048000] / 2001:DB8:1:1::/64=EX [170/2048000] / ::/0=—` |
| ping C1->C2 | `100%` |
| ping C2->C1 | `100%` |

### E8 — ★未定義 route-map を参照 — 全拒否か全許可か

適用 delta:
```
router eigrp NAMED
 address-family ipv6 unicast autonomous-system 5400
  topology base
   no redistribute ospf 544
   redistribute ospf 544 match internal metric 10000 100 255 1 1500 route-map GHOST include-connected
  exit-af-topology
 exit-address-family
exit
router ospfv3 544
 address-family ipv6 unicast
  no redistribute eigrp 5400
  redistribute eigrp 5400 route-map GHOST include-connected
 exit-address-family
exit
```

| 観測点 | 値 |
|---|---|
| RT-C redist | `redistribute ospf 544 match internal metric 10000 100 255 1 1500 route-map GHOST include-connected ; redistribute eigrp 5400 route-map GHOST include-connected` |
| C1 | `2001:DB8:1A:A::/64=— / 2001:DB8:A:A::/64=— / ::/0=—` |
| RA | `2001:DB8:1A:A::/64=— / 2001:DB8:A:A::/64=— / ::/0=—` |
| RB | `2001:DB8:2:1::/64=— / 2001:DB8:1:1::/64=— / ::/0=—` |
| C2 | `2001:DB8:2:1::/64=— / 2001:DB8:1:1::/64=— / ::/0=—` |
| ping C1->C2 | `NOROUTE` |
| ping C2->C1 | `NOROUTE` |

### E9 — EIGRP af-interface E0/0 の shutdown 解除 — 1:1::/64 は D(内部)になるか

適用 delta:
```
router eigrp NAMED
 address-family ipv6 unicast autonomous-system 5400
  af-interface Ethernet0/0
   no shutdown
  exit-af-interface
 exit-address-family
exit
```

| 観測点 | 値 |
|---|---|
| RT-C redist | `redistribute ospf 544 match internal metric 10000 100 255 1 1500 route-map OMAP01 include-connected ; redistribute eigrp 5400 route-map EMAP01 include-connected` |
| C1 | `2001:DB8:1A:A::/64=— / 2001:DB8:A:A::/64=OE2 [110/20] / ::/0=—` |
| RA | `2001:DB8:1A:A::/64=— / 2001:DB8:A:A::/64=OE2 [110/20] / ::/0=—` |
| RB | `2001:DB8:2:1::/64=— / 2001:DB8:1:1::/64=D [90/1536000] / ::/0=—` |
| C2 | `2001:DB8:2:1::/64=— / 2001:DB8:1:1::/64=D [90/2048000] / ::/0=—` |
| ping C1->C2 | `NOROUTE` |
| ping C2->C1 | `NOROUTE` |

### E10 — ★match internal は OSPF 外部(OE2)を落とすか

適用 delta:
```
ipv6 route 2001:DB8:9:9::/64 Null0
router ospfv3 544
 address-family ipv6 unicast
  redistribute static
 exit-address-family
exit
ipv6 prefix-list O544 seq 20 permit 2001:DB8:9:9::/64
router eigrp NAMED
 address-family ipv6 unicast autonomous-system 5400
  topology base
   no redistribute ospf 544
   redistribute ospf 544 match internal external metric 10000 100 255 1 1500 route-map OMAP01 include-connected
  exit-af-topology
 exit-address-family
exit
```

| 観測点 | 値 |
|---|---|
| RT-C 9:9::/64 | `2001:DB8:9:9::/64=OE2 [110/20]` |
| RB 9:9::/64 | `2001:DB8:9:9::/64=—` |
| → match internal external 後 RB 9:9::/64 | `2001:DB8:9:9::/64=EX [170/1536000]` |

### E11 — ★OSPFv3 default-information originate の always 要否

適用 delta:
```
router ospfv3 544
 address-family ipv6 unicast
  default-information originate
 exit-address-family
exit
router ospfv3 544
 address-family ipv6 unicast
  default-information originate always
 exit-address-family
exit
```

| 観測点 | 値 |
|---|---|
| C1 ::/0 (always なし) | `::/0=—` |
| C1 ::/0 (always あり) | `::/0=OE2 [110/1]` |
| RA ::/0 | `::/0=OE2 [110/1]` |
| ping C1->C2 | `0%` |

### E12 — ★EIGRP af-interface summary-address ::/0 でデフォルト配布(+OSPF 側 default originate always)

適用 delta:
```
router ospfv3 544
 address-family ipv6 unicast
  default-information originate always
 exit-address-family
exit
router eigrp NAMED
 address-family ipv6 unicast autonomous-system 5400
  af-interface Ethernet0/1
   summary-address ::/0
  exit-af-interface
 exit-address-family
exit
```

| 観測点 | 値 |
|---|---|
| RT-C redist | `redistribute ospf 544 match internal metric 10000 100 255 1 1500 route-map OMAP01 include-connected ; redistribute eigrp 5400 route-map EMAP01 include-connected` |
| C1 | `2001:DB8:1A:A::/64=— / 2001:DB8:A:A::/64=OE2 [110/20] / ::/0=OE2 [110/1]` |
| RA | `2001:DB8:1A:A::/64=— / 2001:DB8:A:A::/64=OE2 [110/20] / ::/0=OE2 [110/1]` |
| RB | `2001:DB8:2:1::/64=— / 2001:DB8:1:1::/64=— / ::/0=D [90/1536000]` |
| C2 | `2001:DB8:2:1::/64=— / 2001:DB8:1:1::/64=— / ::/0=D [90/2048000]` |
| ping C1->C2 | `100%` |
| ping C2->C1 | `100%` |
| RT-C ::/0 | `::/0=D [5/1024000]` |
| RT-C C1LAN | `2001:DB8:2:1::/64=O [110/20]` |

### E13 — ★RA/RB に静的のみ(再配送なし) — 中継は知るがクライアントは知らない

適用 delta:
```
ipv6 route 2001:DB8:1A:A::/64 2001:DB8:1:1::1
ipv6 route 2001:DB8:2:1::/64 2001:DB8:A:A::1
```

| 観測点 | 値 |
|---|---|
| RT-C redist | `redistribute ospf 544 match internal metric 10000 100 255 1 1500 route-map OMAP01 include-connected ; redistribute eigrp 5400 route-map EMAP01 include-connected` |
| C1 | `2001:DB8:1A:A::/64=— / 2001:DB8:A:A::/64=OE2 [110/20] / ::/0=—` |
| RA | `2001:DB8:1A:A::/64=S [1/0] / 2001:DB8:A:A::/64=OE2 [110/20] / ::/0=—` |
| RB | `2001:DB8:2:1::/64=S [1/0] / 2001:DB8:1:1::/64=EX [170/1536000] / ::/0=—` |
| C2 | `2001:DB8:2:1::/64=— / 2001:DB8:1:1::/64=EX [170/2048000] / ::/0=—` |
| ping C1->C2 | `NOROUTE` |
| ping C2->C1 | `NOROUTE` |
| RA C2LAN | `2001:DB8:1A:A::/64=S [1/0]` |
| RB C1LAN | `2001:DB8:2:1::/64=S [1/0]` |

### E14 — RA/RB 静的 + C1/C2 デフォルト(フィルタ無改変の静的解)

適用 delta:
```
ipv6 route ::/0 2001:DB8:2:1::1
ipv6 route ::/0 2001:DB8:1A:A::1
```

| 観測点 | 値 |
|---|---|
| RT-C redist | `redistribute ospf 544 match internal metric 10000 100 255 1 1500 route-map OMAP01 include-connected ; redistribute eigrp 5400 route-map EMAP01 include-connected` |
| C1 | `2001:DB8:1A:A::/64=— / 2001:DB8:A:A::/64=OE2 [110/20] / ::/0=S [1/0]` |
| RA | `2001:DB8:1A:A::/64=S [1/0] / 2001:DB8:A:A::/64=OE2 [110/20] / ::/0=—` |
| RB | `2001:DB8:2:1::/64=S [1/0] / 2001:DB8:1:1::/64=EX [170/1536000] / ::/0=—` |
| C2 | `2001:DB8:2:1::/64=— / 2001:DB8:1:1::/64=EX [170/2048000] / ::/0=S [1/0]` |
| ping C1->C2 | `100%` |
| ping C2->C1 | `100%` |

### E15 — OSPF 側 metric-type 1 + metric 500

適用 delta:
```
ipv6 prefix-list E5400 seq 10 permit 2001:DB8:1A:A::/64
router ospfv3 544
 address-family ipv6 unicast
  no redistribute eigrp 5400
  redistribute eigrp 5400 metric 500 metric-type 1 route-map EMAP01 include-connected
 exit-address-family
exit
```

| 観測点 | 値 |
|---|---|
| C1 | `2001:DB8:1A:A::/64=OE1 [110/520] / 2001:DB8:A:A::/64=OE1 [110/520]` |
| RA | `2001:DB8:1A:A::/64=OE1 [110/510] / 2001:DB8:A:A::/64=OE1 [110/510]` |


## sweep run (base)

### B0 — 基線(ユーザラボ複製) — 双方向とも route-map でトランジットのみ通過

| 観測点 | 値 |
|---|---|
| RT-C redist | `redistribute ospf 544 match internal metric 10000 100 255 1 1500 route-map OMAP01 include-connected ; redistribute eigrp 5400 route-map EMAP01 include-connected` |
| C1 | `2001:DB8:1A:A::/64=— / 2001:DB8:A:A::/64=OE2 [110/20] / ::/0=—` |
| RA | `2001:DB8:1A:A::/64=— / 2001:DB8:A:A::/64=OE2 [110/20] / ::/0=—` |
| RB | `2001:DB8:2:1::/64=— / 2001:DB8:1:1::/64=EX [170/1536000] / ::/0=—` |
| C2 | `2001:DB8:2:1::/64=— / 2001:DB8:1:1::/64=EX [170/2048000] / ::/0=—` |
| ping C1->C2 | `NOROUTE` |
| ping C2->C1 | `NOROUTE` |

補足:
```
✅ ユーザラボ実測と完全一致

EIGRP-IPv6 VR(NAMED) Topology Table for AS(5400)/ID(1.1.1.1)
Codes: P - Passive, A - Active, U - Update, Q - Query, R - Reply,
       r - reply Status, s - sia Status 

P 2001:DB8:1:1::/64, 1 successors, FD is 131072000
        via Redistributed (131072000/0)
P 2001:DB8:A:A::/64, 1 successors, FD is 131072000
        via Connected, Ethernet0/1
P 2001:DB8:1A:A::/64, 1 successors, FD is 196608000
        via FE80::A8BB:CCFF:FE01:EA00 (196608000/131072000), Ethernet0/1

		Type-5 AS External Link States

ADV Router       Age         Seq#        Prefix
 2.2.2.2         26          0x80000001  2001:DB8:A:A::/64
```

