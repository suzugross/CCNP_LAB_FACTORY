
## sweep run (2026-08-10 21:50:13) — checks: P1_undef, P2_dl_ext, P3_dl_std, P4_out_self, P5_named_seq, P6_numbered, P7_timerange, P8_copp_deny, P9_log, P10_mask, P11_display, P12_empty


基線 RT01 `show ip route eigrp`:
```
Codes: L - local, C - connected, S - static, R - RIP, M - mobile, B - BGP
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area 
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2, m - OMP
       n - NAT, Ni - NAT inside, No - NAT outside, Nd - NAT DIA
       i - IS-IS, su - IS-IS summary, L1 - IS-IS level-1, L2 - IS-IS level-2
       ia - IS-IS inter area, * - candidate default, U - per-user static route
       H - NHRP, G - NHRP registered, g - NHRP registration summary
       o - ODR, P - periodic downloaded static route, l - LISP
       a - application route
       + - replicated route, % - next hop override, p - overrides from PfR
       & - replicated local route overrides by connected

Gateway of last resort is not set

      2.0.0.0/32 is subnetted, 1 subnets
D        2.2.2.2 [90/409600] via 10.0.12.2, 00:00:03, Ethernet0/1
      3.0.0.0/32 is subnetted, 1 subnets
D        3.3.3.3 [90/409600] via 10.0.13.3, 00:00:01, Ethernet0/0
      172.30.0.0/16 is variably subnetted, 5 subnets, 4 masks
D        172.30.16.0/24 [90/409600] via 10.0.12.2, 00:00:03, Ethernet0/1
D        172.30.16.0/28 [90/409600] via 10.0.13.3, 00:00:01, Ethernet0/0
D        172.30.17.0/26 [90/409600] via 10.0.12.2, 00:00:03, Ethernet0/1
D        172.30.18.0/30 [90/409600] via 10.0.12.2, 00:00:03, Ethernet0/1
D        172.30.32.0/24 [90/409600] via 10.0.12.2, 00:00:03, Ethernet0/1
```

### P1_undef


#### P1a interface `ip access-group <未定義> in`
- RT03→RT02 通過率(名前・未定義): **60%**

RT01 `show ip interface Ethernet0/0 | include access list`:
```
Outgoing Common access list is not set 
  Outgoing access list is not set
  Inbound Common access list is not set 
  Inbound  access list is NOEXIST-A
```
- RT03→RT02 通過率(番号 177・未定義): **100%**

#### P1b `distribute-list <未定義> in`(EIGRP)
- 残った学習経路: **7/7** ['2.2.2.2/32', '172.30.16.0/24', '172.30.17.0/26', '172.30.18.0/30', '172.30.32.0/24', '3.3.3.3/32', '172.30.16.0/28']

RT01 `show ip route eigrp`:
```
Codes: L - local, C - connected, S - static, R - RIP, M - mobile, B - BGP
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area 
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2, m - OMP
       n - NAT, Ni - NAT inside, No - NAT outside, Nd - NAT DIA
       i - IS-IS, su - IS-IS summary, L1 - IS-IS level-1, L2 - IS-IS level-2
       ia - IS-IS inter area, * - candidate default, U - per-user static route
       H - NHRP, G - NHRP registered, g - NHRP registration summary
       o - ODR, P - periodic downloaded static route, l - LISP
       a - application route
       + - replicated route, % - next hop override, p - overrides from PfR
       & - replicated local route overrides by connected

Gateway of last resort is not set

      2.0.0.0/32 is subnetted, 1 subnets
D        2.2.2.2 [90/409600] via 10.0.12.2, 00:00:23, Ethernet0/1
      3.0.0.0/32 is subnetted, 1 subnets
D        3.3.3.3 [90/409600] via 10.0.13.3, 00:00:21, Ethernet0/0
      172.30.0.0/16 is variably subnetted, 5 subnets, 4 masks
D        172.30.16.0/24 [90/409600] via 10.0.12.2, 00:00:23, Ethernet0/1
D        172.30.16.0/28 [90/409600] via 10.0.13.3, 00:00:21, Ethernet0/0
D        172.30.17.0/26 [90/409600] via 10.0.12.2, 00:00:23, Ethernet0/1
D        172.30.18.0/30 [90/409600] via 10.0.12.2, 00:00:23, Ethernet0/1
D        172.30.32.0/24 [90/409600] via 10.0.12.2, 00:00:23, Ethernet0/1
```

#### P1c CoPP `match access-group name <未定義>`

RT01 `show policy-map control-plane input`:
```
Control Plane 

  Service-policy input: PM-UNDEF

    Class-map: CM-UNDEF (match-all)  
      Match: access-group name NOEXIST-C
      police:
          cir 8000 bps, bc 1500 bytes
        conformed 0 packets, 0 bytes; actions:
          transmit 
        exceeded 0 packets, 0 bytes; actions:
          transmit 
        conformed 0000 bps, exceeded 0000 bps

    Class-map: class-default (match-any)  
      Match: any
```

#### P1d uRPF `ip verify unicast source reachable-via rx <未定義>`

偽装前 `show ip interface Ethernet0/0`(抜粋):
```
IP verify source reachable-via RX, ACL 178
   0 verification drops
   0 suppressed verification drops
   0 verification drop-rate
```

偽装後(203.0.113.5 発を5発):
```
IP verify source reachable-via RX, ACL 178
   0 verification drops
   5 suppressed verification drops
   0 verification drop-rate
```

#### P1e NAT `ip nat inside source list <未定義>`

RT01 `show ip nat translations`:
```

```

### P2_dl_ext


#### P2a 拡張 ACL で「/26 だけ」を通す (`permit ip host 172.30.17.0 host 255.255.255.192`)
- CLI応答: `% The ACL cannot be created or an ACL with the same name but incompatible type already exists.`
- 残った学習経路: **['2.2.2.2/32', '172.30.16.0/24', '172.30.17.0/26', '172.30.18.0/30', '172.30.32.0/24', '3.3.3.3/32', '172.30.16.0/28']**

RT01 `show ip route eigrp`:
```
Codes: L - local, C - connected, S - static, R - RIP, M - mobile, B - BGP
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area 
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2, m - OMP
       n - NAT, Ni - NAT inside, No - NAT outside, Nd - NAT DIA
       i - IS-IS, su - IS-IS summary, L1 - IS-IS level-1, L2 - IS-IS level-2
       ia - IS-IS inter area, * - candidate default, U - per-user static route
       H - NHRP, G - NHRP registered, g - NHRP registration summary
       o - ODR, P - periodic downloaded static route, l - LISP
       a - application route
       + - replicated route, % - next hop override, p - overrides from PfR
       & - replicated local route overrides by connected

Gateway of last resort is not set

      2.0.0.0/32 is subnetted, 1 subnets
D        2.2.2.2 [90/409600] via 10.0.12.2, 00:00:49, Ethernet0/1
      3.0.0.0/32 is subnetted, 1 subnets
D        3.3.3.3 [90/409600] via 10.0.13.3, 00:00:49, Ethernet0/0
      172.30.0.0/16 is variably subnetted, 5 subnets, 4 masks
D        172.30.16.0/24 [90/409600] via 10.0.12.2, 00:00:49, Ethernet0/1
D        172.30.16.0/28 [90/409600] via 10.0.13.3, 00:00:49, Ethernet0/0
D        172.30.17.0/26 [90/409600] via 10.0.12.2, 00:00:49, Ethernet0/1
D        172.30.18.0/30 [90/409600] via 10.0.12.2, 00:00:49, Ethernet0/1
D        172.30.32.0/24 [90/409600] via 10.0.12.2, 00:00:49, Ethernet0/1
```

RT01 `show ip access-lists DL-EXT`:
```
Extended IP access list DL-EXT
    10 permit ip host 172.30.17.0 host 255.255.255.192
```

#### P2b 送信元をワイルドカード・宛先を any (`permit ip 172.30.16.0 0.0.15.255 any`)
- 残った学習経路: **['2.2.2.2/32', '172.30.16.0/24', '172.30.17.0/26', '172.30.18.0/30', '172.30.32.0/24', '3.3.3.3/32', '172.30.16.0/28']**

RT01 `show ip route eigrp`:
```
Codes: L - local, C - connected, S - static, R - RIP, M - mobile, B - BGP
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area 
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2, m - OMP
       n - NAT, Ni - NAT inside, No - NAT outside, Nd - NAT DIA
       i - IS-IS, su - IS-IS summary, L1 - IS-IS level-1, L2 - IS-IS level-2
       ia - IS-IS inter area, * - candidate default, U - per-user static route
       H - NHRP, G - NHRP registered, g - NHRP registration summary
       o - ODR, P - periodic downloaded static route, l - LISP
       a - application route
       + - replicated route, % - next hop override, p - overrides from PfR
       & - replicated local route overrides by connected

Gateway of last resort is not set

      2.0.0.0/32 is subnetted, 1 subnets
D        2.2.2.2 [90/409600] via 10.0.12.2, 00:01:06, Ethernet0/1
      3.0.0.0/32 is subnetted, 1 subnets
D        3.3.3.3 [90/409600] via 10.0.13.3, 00:01:06, Ethernet0/0
      172.30.0.0/16 is variably subnetted, 5 subnets, 4 masks
D        172.30.16.0/24 [90/409600] via 10.0.12.2, 00:01:06, Ethernet0/1
D        172.30.16.0/28 [90/409600] via 10.0.13.3, 00:01:06, Ethernet0/0
D        172.30.17.0/26 [90/409600] via 10.0.12.2, 00:01:06, Ethernet0/1
D        172.30.18.0/30 [90/409600] via 10.0.12.2, 00:01:06, Ethernet0/1
D        172.30.32.0/24 [90/409600] via 10.0.12.2, 00:01:06, Ethernet0/1
```

### P3_dl_std


#### P3 標準 ACL `deny 172.30.16.0` + `permit any`
- 172.30.16.0/24 残存: **False** / 172.30.16.0/28 残存: **False**

RT01 `show ip route eigrp`:
```
Codes: L - local, C - connected, S - static, R - RIP, M - mobile, B - BGP
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area 
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2, m - OMP
       n - NAT, Ni - NAT inside, No - NAT outside, Nd - NAT DIA
       i - IS-IS, su - IS-IS summary, L1 - IS-IS level-1, L2 - IS-IS level-2
       ia - IS-IS inter area, * - candidate default, U - per-user static route
       H - NHRP, G - NHRP registered, g - NHRP registration summary
       o - ODR, P - periodic downloaded static route, l - LISP
       a - application route
       + - replicated route, % - next hop override, p - overrides from PfR
       & - replicated local route overrides by connected

Gateway of last resort is not set

      2.0.0.0/32 is subnetted, 1 subnets
D        2.2.2.2 [90/409600] via 10.0.12.2, 00:01:35, Ethernet0/1
      3.0.0.0/32 is subnetted, 1 subnets
D        3.3.3.3 [90/409600] via 10.0.13.3, 00:01:35, Ethernet0/0
      172.30.0.0/16 is variably subnetted, 3 subnets, 3 masks
D        172.30.17.0/26 [90/409600] via 10.0.12.2, 00:01:35, Ethernet0/1
D        172.30.18.0/30 [90/409600] via 10.0.12.2, 00:01:35, Ethernet0/1
D        172.30.32.0/24 [90/409600] via 10.0.12.2, 00:01:35, Ethernet0/1
```

RT01 `show ip access-lists 20`:
```
Standard IP access list 20
    10 deny   172.30.16.0 (6 matches)
    20 permit any (5 matches)
```

### P4_out_self


#### P4 `ip access-group BLOCK-ALL out` を RT01 e0/1 に適用
- **RT01 自身 → RT02: 0%**(自機生成)
- **RT03 → RT02(RT01 を通過): 0%**(転送)

RT01 `show ip access-lists BLOCK-ALL`:
```
Extended IP access list BLOCK-ALL
    10 deny icmp any any (10 matches)
    20 permit ip any any (6 matches)
```

### P5_named_seq


#### P5 named ACL の seq 挿入・resequence・カウンタ

① 初期状態(5発通した後):
```
Extended IP access list SEQT
    10 permit icmp host 10.0.13.3 any (5 matches)
    20 permit ip host 3.3.3.3 any
    30 permit ip any any (1 match)
```

② `15 deny udp any any eq 9999` を挿入した直後(★他行のカウンタが残るか):
```
Extended IP access list SEQT
    10 permit icmp host 10.0.13.3 any (5 matches)
    15 deny udp any any eq 9999
    20 permit ip host 3.3.3.3 any
    30 permit ip any any (1 match)
```

③ `ip access-list resequence SEQT 100 100` 後(★カウンタが残るか):
```
Extended IP access list SEQT
    100 permit icmp host 10.0.13.3 any (5 matches)
    200 deny udp any any eq 9999
    300 permit ip host 3.3.3.3 any
    400 permit ip any any (1 match)
```

④ `no ip access-list` → 作り直した後(★カウンタは消えるか):
```
Extended IP access list SEQT
    10 permit icmp host 10.0.13.3 any
    20 permit ip any any
```

### P6_numbered


#### P6 番号付き ACL の編集規則

① 2行を順に追加:
```
Extended IP access list 150
    10 permit ip host 10.0.13.3 any
    20 permit ip host 3.3.3.3 any
```

② さらに1行追加(★末尾に付くか・置換されないか):
```
Extended IP access list 150
    10 permit ip host 10.0.13.3 any
    20 permit ip host 3.3.3.3 any
    30 deny ip host 172.30.16.1 any
```

③ ★`ip access-list extended 150` に入って `15 permit ...` (番号付きでも seq 挿入できるか):
```
Extended IP access list 150
    10 permit ip host 10.0.13.3 any
    15 permit tcp any any eq 22
    20 permit ip host 3.3.3.3 any
    30 deny ip host 172.30.16.1 any
```
- ③ の CLI エラー: なし(受理)

④ `no access-list 150` 後:
```

```

### P7_timerange


#### P7 time-range periodic

- **平日 10:00(範囲内)** → RT03→RT02 の ICMP 通過率: **0%**

  `show time-range WORKHOURS`:
```
time-range entry: WORKHOURS (active)
   periodic weekdays 9:00 to 17:00
   used in: IP ACL entry
```

  `show ip access-lists TRT`(★非アクティブ時の表示):
```
Extended IP access list TRT
    10 deny icmp any any time-range WORKHOURS (active) (3 matches)
    20 permit ip any any (2 matches)
```

- **平日 18:30(範囲外)** → RT03→RT02 の ICMP 通過率: **100%**

  `show time-range WORKHOURS`:
```
time-range entry: WORKHOURS (inactive)
   periodic weekdays 9:00 to 17:00
   used in: IP ACL entry
```

  `show ip access-lists TRT`(★非アクティブ時の表示):
```
Extended IP access list TRT
    10 deny icmp any any time-range WORKHOURS (inactive) (3 matches)
    20 permit ip any any (6 matches)
```

- **土曜 10:00(曜日外)** → RT03→RT02 の ICMP 通過率: **100%**

  `show time-range WORKHOURS`:
```
time-range entry: WORKHOURS (inactive)
   periodic weekdays 9:00 to 17:00
   used in: IP ACL entry
```

  `show ip access-lists TRT`(★非アクティブ時の表示):
```
Extended IP access list TRT
    10 deny icmp any any time-range WORKHOURS (inactive) (3 matches)
    20 permit ip any any (10 matches)
```

### P8_copp_deny


#### P8 CoPP の deny ACE は class-default 行き

RT01 `show policy-map control-plane input`(★10.0.13.3 発の 10発がどちらのクラスに計上されるか):
```
Control Plane 

  Service-policy input: PM-COPP

    Class-map: CM-ICMP (match-all)  
      Match: access-group name CP-ICMP
      police:
          cir 8000 bps, bc 1500 bytes
        conformed 10 packets, 1140 bytes; actions:
          transmit 
        exceeded 0 packets, 0 bytes; actions:
          transmit 
        conformed 0000 bps, exceeded 0000 bps

    Class-map: class-default (match-any)  
      Match: any 
      police:
          cir 8000 bps, bc 1500 bytes
        conformed 12 packets, 1288 bytes; actions:
          transmit 
        exceeded 0 packets, 0 bytes; actions:
          transmit 
        conformed 0000 bps, exceeded 0000 bps
```

RT01 `show ip access-lists CP-ICMP`:
```
Extended IP access list CP-ICMP
    10 deny icmp host 10.0.13.3 any (10 matches)
    20 permit icmp any any (10 matches)
```

### P9_log


#### P9 ACL ログの書式

**測定失敗**: `SubCommandFailure: ('Command execution failed', SubCommandFailure('sub_command failure, patterns matched in the output:', ['% Invalid input detected at'], 'service result', "telnet 10.0.12.2 22 /source-interface Loopback0 /timeout 3\r\ntelnet 10.0.12.2 22 /source-interface Loopback0 /timeout 3\r\n                                                 ^\r\n% Invalid input detected at '^' marker.\r\n\r\nRT03#"))`


### P10_mask


#### P10 ワイルドカード ⇄ サブネットマスク取り違え
- CLI エラー: なし(3本とも受理)

RT01 `show ip access-lists 90`(255.0.0.0 と書いた場合):
```
Standard IP access list 90
    10 permit 0.0.0.0, wildcard bits 255.0.0.0
```

RT01 `show ip access-lists 91`(255.255.255.0 と書いた場合):
```
Standard IP access list 91
    10 permit 0.0.0.0, wildcard bits 255.255.255.0
```

RT01 `show ip access-lists 92`(正しく 0.255.255.255):
```
Standard IP access list 92
    10 permit 10.0.0.0, wildcard bits 0.255.255.255
```

RT01 `show running-config | include access-list 9`:
```

```

### P11_display


#### P11 表示書式(紙面の read 形の忠実性のため)

RT01 `show ip access-lists DISPT`:
```
Extended IP access list DISPT
    10 permit tcp 10.0.13.0 0.0.0.255 any eq 22
    20 permit tcp any host 172.30.16.1 eq www log
    30 permit udp any any range 16384 32767
    40 permit icmp any any echo-reply
    50 deny tcp any any established
    60 permit ip 10.0.0.0 0.0.1.255 any
```

RT01 `show running-config | section ip access-list extended DISPT`:
```
ip access-list extended DISPT
 10 remark === display test ===
 10 permit tcp 10.0.13.0 0.0.0.255 any eq 22
 20 permit tcp any host 172.30.16.1 eq www log
 30 permit udp any any range 16384 32767
 40 permit icmp any any echo-reply
 50 deny tcp any any established
 60 permit ip 10.0.0.0 0.0.1.255 any
```

### P12_empty


#### P12 空の named ACL を適用
- RT03→RT02 通過率: **100%**

RT01 `show ip access-lists EMPTYT`:
```
Extended IP access list EMPTYT
```

## sweep run (2026-08-10 21:57:59) — checks: P1F_ctrl, P2N_dl_num, P4B_selfgen, P9B_log, P13_empty_vs_undef


基線 RT01 `show ip route eigrp`:
```
Codes: L - local, C - connected, S - static, R - RIP, M - mobile, B - BGP
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area 
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2, m - OMP
       n - NAT, Ni - NAT inside, No - NAT outside, Nd - NAT DIA
       i - IS-IS, su - IS-IS summary, L1 - IS-IS level-1, L2 - IS-IS level-2
       ia - IS-IS inter area, * - candidate default, U - per-user static route
       H - NHRP, G - NHRP registered, g - NHRP registration summary
       o - ODR, P - periodic downloaded static route, l - LISP
       a - application route
       + - replicated route, % - next hop override, p - overrides from PfR
       & - replicated local route overrides by connected

Gateway of last resort is not set

      2.0.0.0/32 is subnetted, 1 subnets
D        2.2.2.2 [90/409600] via 10.0.12.2, 00:05:49, Ethernet0/1
      3.0.0.0/32 is subnetted, 1 subnets
D        3.3.3.3 [90/409600] via 10.0.13.3, 00:05:49, Ethernet0/0
      172.30.0.0/16 is variably subnetted, 5 subnets, 4 masks
D        172.30.16.0/24 [90/409600] via 10.0.12.2, 00:05:39, Ethernet0/1
D        172.30.16.0/28 [90/409600] via 10.0.13.3, 00:05:39, Ethernet0/0
D        172.30.17.0/26 [90/409600] via 10.0.12.2, 00:05:49, Ethernet0/1
D        172.30.18.0/30 [90/409600] via 10.0.12.2, 00:05:49, Ethernet0/1
D        172.30.32.0/24 [90/409600] via 10.0.12.2, 00:05:49, Ethernet0/1
```

### P1F_ctrl


#### P1F-a 未定義 ACL の interface 適用(ARP を温めてから再測)
- ACL 適用前(基準): **100%**
- 未定義の**名前付き**を in に適用: **100%**

  `show ip access-lists`(未定義参照で ACL が作られるか):
```

```

#### P1F-b CoPP: 定義済み ACL なら計上されるか(観測方法の対照)

定義済み ACL の場合:
```
Control Plane 

  Service-policy input: PM-CTRL

    Class-map: CM-CTRL (match-all)  
      Match: access-group name CTRL-A
      police:
          cir 8000 bps, bc 1500 bytes
        conformed 10 packets, 1140 bytes; actions:
          transmit 
        exceeded 0 packets, 0 bytes; actions:
          transmit 
        conformed 1000 bps, exceeded 0000 bps

    Class-map: class-default (match-any)  
      Match: any 
      police:
          cir 8000 bps, bc 1500 bytes
        conformed 3 packets, 547 bytes; actions:
          transmit 
        exceeded 0 packets, 0 bytes; actions:
          transmit 
        conformed 0000 bps, exceeded 0000 bps
```

#### P1F-c CoPP: 未定義 ACL(class-default にも police を置いて行き先を見る)

未定義 ACL の場合(★どちらのクラスに 10発が入るか):
```
Control Plane 

  Service-policy input: PM-UND2

    Class-map: CM-UND2 (match-all)  
      Match: access-group name NOEXIST-C
      police:
          cir 8000 bps, bc 1500 bytes
        conformed 0 packets, 0 bytes; actions:
          transmit 
        exceeded 0 packets, 0 bytes; actions:
          transmit 
        conformed 0000 bps, exceeded 0000 bps

    Class-map: class-default (match-any)  
      Match: any 
      police:
          cir 8000 bps, bc 1500 bytes
        conformed 12 packets, 1288 bytes; actions:
          transmit 
        exceeded 0 packets, 0 bytes; actions:
          transmit 
        conformed 1000 bps, exceeded 0000 bps
```

#### P1F-d NAT: 定義済み ACL との対照

定義済み ACL 60(3.3.3.3 を許可):
```
Pro Inside global      Inside local       Outside local      Outside global
icmp 10.0.12.1:1024    3.3.3.3:17         2.2.2.2:17         2.2.2.2:1024
```
- CLI応答: `%Dynamic mapping in use, cannot remove`

未定義 ACL の場合:
```

```

### P2N_dl_num


#### P2N-0 まず「名前付き拡張 ACL を distribute-list に使う」の可否を1行ずつ
- `ip access-list extended DL-EXT2` → 受理
- `permit ip host 172.30.17.0 host 255.255.255.192` → **% Invalid input detected at '^' marker.**
- `exit` → 受理
- `router eigrp 100` → 受理
- `distribute-list DL-EXT2 in` → **% Invalid input detected at '^' marker.**
- `exit` → 受理
- 残った学習経路: **['172.30.16.0/24', '172.30.16.0/28', '172.30.17.0/26', '172.30.18.0/30', '172.30.32.0/24', '2.2.2.2/32', '3.3.3.3/32']**

#### P2N-a 番号付き拡張 ACL 130 で「/26 だけ」を通す
- `access-list 130 permit ip host 172.30.17.0 host 255.255.255.192` → 受理
- `router eigrp 100` → 受理
- `distribute-list 130 in` → **% Invalid input detected at '^' marker.**
- `exit` → 受理
- 残った学習経路: **['172.30.16.0/24', '172.30.16.0/28', '172.30.17.0/26', '172.30.18.0/30', '172.30.32.0/24', '2.2.2.2/32', '3.3.3.3/32']**

RT01 `show ip route eigrp`:
```
Codes: L - local, C - connected, S - static, R - RIP, M - mobile, B - BGP
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area 
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2, m - OMP
       n - NAT, Ni - NAT inside, No - NAT outside, Nd - NAT DIA
       i - IS-IS, su - IS-IS summary, L1 - IS-IS level-1, L2 - IS-IS level-2
       ia - IS-IS inter area, * - candidate default, U - per-user static route
       H - NHRP, G - NHRP registered, g - NHRP registration summary
       o - ODR, P - periodic downloaded static route, l - LISP
       a - application route
       + - replicated route, % - next hop override, p - overrides from PfR
       & - replicated local route overrides by connected

Gateway of last resort is not set

      2.0.0.0/32 is subnetted, 1 subnets
D        2.2.2.2 [90/409600] via 10.0.12.2, 00:07:12, Ethernet0/1
      3.0.0.0/32 is subnetted, 1 subnets
D        3.3.3.3 [90/409600] via 10.0.13.3, 00:07:12, Ethernet0/0
      172.30.0.0/16 is variably subnetted, 5 subnets, 4 masks
D        172.30.16.0/24 [90/409600] via 10.0.12.2, 00:07:02, Ethernet0/1
D        172.30.16.0/28 [90/409600] via 10.0.13.3, 00:07:02, Ethernet0/0
D        172.30.17.0/26 [90/409600] via 10.0.12.2, 00:07:12, Ethernet0/1
D        172.30.18.0/30 [90/409600] via 10.0.12.2, 00:07:12, Ethernet0/1
D        172.30.32.0/24 [90/409600] via 10.0.12.2, 00:07:12, Ethernet0/1
```

RT01 `show ip access-lists 130`:
```
Extended IP access list 130
    10 permit ip host 172.30.17.0 host 255.255.255.192
```

#### P2N-b 送信元にワイルドカード・宛先(=マスク)を any にする
- 残った学習経路: **['172.30.16.0/24', '172.30.16.0/28', '172.30.17.0/26', '172.30.18.0/30', '172.30.32.0/24', '2.2.2.2/32', '3.3.3.3/32']**

#### P2N-c 宛先(=マスク)だけを /24 に固定 (`permit ip any host 255.255.255.0`)
- 残った学習経路: **['172.30.16.0/24', '172.30.16.0/28', '172.30.17.0/26', '172.30.18.0/30', '172.30.32.0/24', '2.2.2.2/32', '3.3.3.3/32']**

RT01 `show ip route eigrp`:
```
Codes: L - local, C - connected, S - static, R - RIP, M - mobile, B - BGP
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area 
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2, m - OMP
       n - NAT, Ni - NAT inside, No - NAT outside, Nd - NAT DIA
       i - IS-IS, su - IS-IS summary, L1 - IS-IS level-1, L2 - IS-IS level-2
       ia - IS-IS inter area, * - candidate default, U - per-user static route
       H - NHRP, G - NHRP registered, g - NHRP registration summary
       o - ODR, P - periodic downloaded static route, l - LISP
       a - application route
       + - replicated route, % - next hop override, p - overrides from PfR
       & - replicated local route overrides by connected

Gateway of last resort is not set

      2.0.0.0/32 is subnetted, 1 subnets
D        2.2.2.2 [90/409600] via 10.0.12.2, 00:07:45, Ethernet0/1
      3.0.0.0/32 is subnetted, 1 subnets
D        3.3.3.3 [90/409600] via 10.0.13.3, 00:07:45, Ethernet0/0
      172.30.0.0/16 is variably subnetted, 5 subnets, 4 masks
D        172.30.16.0/24 [90/409600] via 10.0.12.2, 00:07:35, Ethernet0/1
D        172.30.16.0/28 [90/409600] via 10.0.13.3, 00:07:35, Ethernet0/0
D        172.30.17.0/26 [90/409600] via 10.0.12.2, 00:07:45, Ethernet0/1
D        172.30.18.0/30 [90/409600] via 10.0.12.2, 00:07:45, Ethernet0/1
D        172.30.32.0/24 [90/409600] via 10.0.12.2, 00:07:45, Ethernet0/1
```

### P4B_selfgen


#### P4B outbound ACL は自機生成トラフィックに効くか(帰属つき再測)

適用直後(カウンタ基点):
```
Extended IP access list OUTT
    10 deny icmp any any
    20 permit ip any any (1 match)
```

- **RT01 自身 → 10.0.12.2(直結・既定送信元): 0%**

  直後のカウンタ:
```
Extended IP access list OUTT
    10 deny icmp any any (5 matches)
    20 permit ip any any (5 matches)
```

- **RT01 自身 → 2.2.2.2(Lo0 発・1ホップ先): 0%**

  直後のカウンタ:
```
Extended IP access list OUTT
    10 deny icmp any any (10 matches)
    20 permit ip any any (8 matches)
```

- **RT03 → 10.0.12.2(RT01 を通過): 0%**

  直後のカウンタ:
```
Extended IP access list OUTT
    10 deny icmp any any (15 matches)
    20 permit ip any any (9 matches)
```

### P9B_log


#### P9B ACL ログの書式(ICMP と TCP の両方)
- CLI応答: `% Duplicate sequence number`
- CLI応答: `% Duplicate sequence number`
- CLI応答: `% Failed to add ace to access-list`

RT01 `show logging | include SEC-6`:
```
Aug 15 10:07:42.465: %SEC-6-IPACCESSLOGP: list LOGT denied tcp 10.0.13.3(19314) -> 10.0.12.2(22), 1 packet
```

RT01 `show ip access-lists LOGT`:
```
Extended IP access list LOGT
    10 deny tcp any any eq 22 log (2 matches)
    20 deny icmp any any (3 matches)
    30 permit ip any any (5 matches)
```

#### P9B-b ★log の無い行で落ちた場合は記録が出ないか
- log 無しの deny で落とした後の SEC-6 行数: **0**

RT01 `show logging | include SEC-6`:
```

```

RT01 `show ip access-lists LOGT2`(カウンタは進む):
```
Extended IP access list LOGT2
    10 deny icmp any any echo (3 matches)
    20 permit ip any any (3 matches)
```

### P13_empty_vs_undef


#### P13 空の named ACL を distribute-list に使う
- 残った学習経路: **['172.30.16.0/24', '172.30.16.0/28', '172.30.17.0/26', '172.30.18.0/30', '172.30.32.0/24', '2.2.2.2/32', '3.3.3.3/32']**

RT01 `show ip route eigrp`:
```
Codes: L - local, C - connected, S - static, R - RIP, M - mobile, B - BGP
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area 
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2, m - OMP
       n - NAT, Ni - NAT inside, No - NAT outside, Nd - NAT DIA
       i - IS-IS, su - IS-IS summary, L1 - IS-IS level-1, L2 - IS-IS level-2
       ia - IS-IS inter area, * - candidate default, U - per-user static route
       H - NHRP, G - NHRP registered, g - NHRP registration summary
       o - ODR, P - periodic downloaded static route, l - LISP
       a - application route
       + - replicated route, % - next hop override, p - overrides from PfR
       & - replicated local route overrides by connected

Gateway of last resort is not set

      2.0.0.0/32 is subnetted, 1 subnets
D        2.2.2.2 [90/409600] via 10.0.12.2, 00:09:22, Ethernet0/1
      3.0.0.0/32 is subnetted, 1 subnets
D        3.3.3.3 [90/409600] via 10.0.13.3, 00:09:22, Ethernet0/0
      172.30.0.0/16 is variably subnetted, 5 subnets, 4 masks
D        172.30.16.0/24 [90/409600] via 10.0.12.2, 00:09:12, Ethernet0/1
D        172.30.16.0/28 [90/409600] via 10.0.13.3, 00:09:12, Ethernet0/0
D        172.30.17.0/26 [90/409600] via 10.0.12.2, 00:09:22, Ethernet0/1
D        172.30.18.0/30 [90/409600] via 10.0.12.2, 00:09:22, Ethernet0/1
D        172.30.32.0/24 [90/409600] via 10.0.12.2, 00:09:22, Ethernet0/1
```

## sweep run (2026-08-10 22:06:46) — checks: P2C_dl_ext, P9C_icmp_log, P14_cleanup


基線 RT01 `show ip route eigrp`:
```
Codes: L - local, C - connected, S - static, R - RIP, M - mobile, B - BGP
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area 
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2, m - OMP
       n - NAT, Ni - NAT inside, No - NAT outside, Nd - NAT DIA
       i - IS-IS, su - IS-IS summary, L1 - IS-IS level-1, L2 - IS-IS level-2
       ia - IS-IS inter area, * - candidate default, U - per-user static route
       H - NHRP, G - NHRP registered, g - NHRP registration summary
       o - ODR, P - periodic downloaded static route, l - LISP
       a - application route
       + - replicated route, % - next hop override, p - overrides from PfR
       & - replicated local route overrides by connected

Gateway of last resort is not set

      2.0.0.0/32 is subnetted, 1 subnets
D        2.2.2.2 [90/409600] via 10.0.12.2, 00:05:14, Ethernet0/1
      3.0.0.0/32 is subnetted, 1 subnets
D        3.3.3.3 [90/409600] via 10.0.13.3, 00:05:14, Ethernet0/0
      172.30.0.0/16 is variably subnetted, 5 subnets, 4 masks
D        172.30.16.0/24 [90/409600] via 10.0.12.2, 00:05:14, Ethernet0/1
D        172.30.16.0/28 [90/409600] via 10.0.13.3, 00:05:14, Ethernet0/0
D        172.30.17.0/26 [90/409600] via 10.0.12.2, 00:05:14, Ethernet0/1
D        172.30.18.0/30 [90/409600] via 10.0.12.2, 00:05:14, Ethernet0/1
D        172.30.32.0/24 [90/409600] via 10.0.12.2, 00:05:14, Ethernet0/1
```

### P2C_dl_ext


#### P2C-a 名前付き拡張 ACL
- `ip access-list extended DLX` → 受理
- `permit ip host 172.30.17.0 host 255.255.255.192` → 受理
- `exit` → 受理
- `router eigrp 100` → 受理
- `distribute-list DLX in` → **% The ACL cannot be created or an ACL with the same name but incompatible type already exists.**
- `exit` → 受理
- 残った学習経路: **['172.30.16.0/24', '172.30.16.0/28', '172.30.17.0/26', '172.30.18.0/30', '172.30.32.0/24', '2.2.2.2/32', '3.3.3.3/32']**

  `show ip protocols`(適用の確認):
```
Outgoing update filter list for all interfaces is not set
  Incoming update filter list for all interfaces is not set
  Outgoing update filter list for all interfaces is not set
  Incoming update filter list for all interfaces is not set
```

#### P2C-b 番号付き拡張 ACL 130(/26 のマスクをちょうど指定)
- `access-list 130 permit ip host 172.30.17.0 host 255.255.255.192` → 受理
- `router eigrp 100` → 受理
- `distribute-list 130 in` → 受理
- `exit` → 受理
- 残った学習経路: **[]**

  `show ip protocols`(適用の確認):
```
Outgoing update filter list for all interfaces is not set
  Incoming update filter list for all interfaces is not set
  Outgoing update filter list for all interfaces is not set
  Incoming update filter list for all interfaces is 130
```

#### P2C-c 番号付き拡張 130(送信元=網をWC・宛先=マスクは any)
- `access-list 130 permit ip 172.30.16.0 0.0.15.255 any` → 受理
- `router eigrp 100` → 受理
- `distribute-list 130 in` → 受理
- `exit` → 受理
- 残った学習経路: **[]**

  `show ip protocols`(適用の確認):
```
Outgoing update filter list for all interfaces is not set
  Incoming update filter list for all interfaces is not set
  Outgoing update filter list for all interfaces is not set
  Incoming update filter list for all interfaces is 130
```

#### P2C-d 番号付き拡張 130(★宛先=マスクだけ /24 に固定)
- `access-list 130 permit ip any host 255.255.255.0` → 受理
- `router eigrp 100` → 受理
- `distribute-list 130 in` → 受理
- `exit` → 受理
- 残った学習経路: **[]**

  `show ip protocols`(適用の確認):
```
Outgoing update filter list for all interfaces is not set
  Incoming update filter list for all interfaces is not set
  Outgoing update filter list for all interfaces is not set
  Incoming update filter list for all interfaces is 130
```

### P9C_icmp_log


#### P9C ICMP の ACL ログ書式
- RT03→RT02 通過率: **0%**

RT01 `show logging | include SEC-6`:
```
Aug 15 10:15:45.764: %SEC-6-IPACCESSLOGDP: list LOG3 denied icmp 10.0.13.3 -> 10.0.12.2 (8/0), 1 packet
```

RT01 `show ip access-lists LOG3`:
```
Extended IP access list LOG3
    10 deny icmp any any echo log (3 matches)
    20 permit ip any any (4 matches)
```

### P14_cleanup


#### P14 後片付け

RT01 `show ip access-lists`(残骸が無いこと):
```

```

RT01 `show running-config | include access-group|distribute-list|service-policy|ip nat|verify unicast`:
```
ip nat inside source list 60 interface Ethernet0/1 overload
```

## sweep run (2026-08-10 22:11:14) — checks: P2E_dl_semantics, P14_cleanup


基線 RT01 `show ip route eigrp`:
```
Codes: L - local, C - connected, S - static, R - RIP, M - mobile, B - BGP
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area 
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2, m - OMP
       n - NAT, Ni - NAT inside, No - NAT outside, Nd - NAT DIA
       i - IS-IS, su - IS-IS summary, L1 - IS-IS level-1, L2 - IS-IS level-2
       ia - IS-IS inter area, * - candidate default, U - per-user static route
       H - NHRP, G - NHRP registered, g - NHRP registration summary
       o - ODR, P - periodic downloaded static route, l - LISP
       a - application route
       + - replicated route, % - next hop override, p - overrides from PfR
       & - replicated local route overrides by connected

Gateway of last resort is not set

      2.0.0.0/32 is subnetted, 1 subnets
D        2.2.2.2 [90/409600] via 10.0.12.2, 00:02:30, Ethernet0/1
      3.0.0.0/32 is subnetted, 1 subnets
D        3.3.3.3 [90/409600] via 10.0.13.3, 00:02:30, Ethernet0/0
      172.30.0.0/16 is variably subnetted, 5 subnets, 4 masks
D        172.30.16.0/24 [90/409600] via 10.0.12.2, 00:02:30, Ethernet0/1
D        172.30.16.0/28 [90/409600] via 10.0.13.3, 00:02:30, Ethernet0/0
D        172.30.17.0/26 [90/409600] via 10.0.12.2, 00:02:30, Ethernet0/1
D        172.30.18.0/30 [90/409600] via 10.0.12.2, 00:02:30, Ethernet0/1
D        172.30.32.0/24 [90/409600] via 10.0.12.2, 00:02:30, Ethernet0/1
```

### P2E_dl_semantics


#### P2E-E1 `permit ip any any`(健全性確認=評価されているなら全部残る)
- `no access-list 131` → 受理
- `access-list 131 permit ip any any` → 受理
- `router eigrp 100` → 受理
- `distribute-list 131 in` → 受理
- `exit` → 受理
- 残った学習経路 **7/7**: ['172.30.16.0/24', '172.30.16.0/28', '172.30.17.0/26', '172.30.18.0/30', '172.30.32.0/24', '2.2.2.2/32', '3.3.3.3/32']

  `show ip access-lists 131`(★どの行が何回当たったか):
```
Extended IP access list 131
    10 permit ip any any (7 matches)
```

#### P2E-E2 `permit ip host 172.30.17.0 any`(src=ネットワークだけ・dst 無指定)
- `no access-list 131` → 受理
- `access-list 131 permit ip host 172.30.17.0 any` → 受理
- `router eigrp 100` → 受理
- `distribute-list 131 in` → 受理
- `exit` → 受理
- 残った学習経路 **0/7**: []

  `show ip access-lists 131`(★どの行が何回当たったか):
```
Extended IP access list 131
    10 permit ip host 172.30.17.0 any
```

#### P2E-E3 `permit ip host 10.0.12.2 any`(★src=広告元ルータ説の検証)
- `no access-list 131` → 受理
- `access-list 131 permit ip host 10.0.12.2 any` → 受理
- `router eigrp 100` → 受理
- `distribute-list 131 in` → 受理
- `exit` → 受理
- 残った学習経路 **5/7**: ['172.30.16.0/24', '172.30.17.0/26', '172.30.18.0/30', '172.30.32.0/24', '2.2.2.2/32']

  `show ip access-lists 131`(★どの行が何回当たったか):
```
Extended IP access list 131
    10 permit ip host 10.0.12.2 any (7 matches)
```

#### P2E-E4 `permit ip host 172.30.17.0 host 255.255.255.192`(定説どおりの書式)
- `no access-list 131` → 受理
- `access-list 131 permit ip host 172.30.17.0 host 255.255.255.192` → 受理
- `router eigrp 100` → 受理
- `distribute-list 131 in` → 受理
- `exit` → 受理
- 残った学習経路 **0/7**: []

  `show ip access-lists 131`(★どの行が何回当たったか):
```
Extended IP access list 131
    10 permit ip host 172.30.17.0 host 255.255.255.192
```

#### P2E-E5 `permit ip 172.30.0.0 0.0.255.255 any`(src=網をWCで広く)
- `no access-list 131` → 受理
- `access-list 131 permit ip 172.30.0.0 0.0.255.255 any` → 受理
- `router eigrp 100` → 受理
- `distribute-list 131 in` → 受理
- `exit` → 受理
- 残った学習経路 **0/7**: []

  `show ip access-lists 131`(★どの行が何回当たったか):
```
Extended IP access list 131
    10 permit ip 172.30.0.0 0.0.255.255 any
```

### P14_cleanup


#### P14 後片付け

RT01 `show ip access-lists`(残骸が無いこと):
```

```

RT01 `show running-config | include access-group|distribute-list|service-policy|ip nat|verify unicast`:
```
ip nat inside source list 60 interface Ethernet0/1 overload
```

## sweep run (2026-08-10 22:15:29) — checks: P2F_dst_field, P14_cleanup


基線 RT01 `show ip route eigrp`:
```
Codes: L - local, C - connected, S - static, R - RIP, M - mobile, B - BGP
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area 
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2, m - OMP
       n - NAT, Ni - NAT inside, No - NAT outside, Nd - NAT DIA
       i - IS-IS, su - IS-IS summary, L1 - IS-IS level-1, L2 - IS-IS level-2
       ia - IS-IS inter area, * - candidate default, U - per-user static route
       H - NHRP, G - NHRP registered, g - NHRP registration summary
       o - ODR, P - periodic downloaded static route, l - LISP
       a - application route
       + - replicated route, % - next hop override, p - overrides from PfR
       & - replicated local route overrides by connected

Gateway of last resort is not set

      2.0.0.0/32 is subnetted, 1 subnets
D        2.2.2.2 [90/409600] via 10.0.12.2, 00:01:58, Ethernet0/1
      3.0.0.0/32 is subnetted, 1 subnets
D        3.3.3.3 [90/409600] via 10.0.13.3, 00:01:58, Ethernet0/0
      172.30.0.0/16 is variably subnetted, 5 subnets, 4 masks
D        172.30.16.0/24 [90/409600] via 10.0.12.2, 00:01:58, Ethernet0/1
D        172.30.16.0/28 [90/409600] via 10.0.13.3, 00:01:58, Ethernet0/0
D        172.30.17.0/26 [90/409600] via 10.0.12.2, 00:01:58, Ethernet0/1
D        172.30.18.0/30 [90/409600] via 10.0.12.2, 00:01:58, Ethernet0/1
D        172.30.32.0/24 [90/409600] via 10.0.12.2, 00:01:58, Ethernet0/1
```

### P2F_dst_field


#### P2F-F1 `permit ip any host 172.30.17.0`(dst=広告された網 説)
- `no access-list 132` → 受理
- `access-list 132 permit ip any host 172.30.17.0` → 受理
- `router eigrp 100` → 受理
- `distribute-list 132 in` → 受理
- `exit` → 受理
- 残った学習経路 **1/7**: ['172.30.17.0/26']

  `show ip access-lists 132`:
```
Extended IP access list 132
    10 permit ip any host 172.30.17.0 (1 match)
```

#### P2F-F2 `permit ip host 10.0.12.2 host 172.30.17.0`(src と dst の両掛け)
- `no access-list 132` → 受理
- `access-list 132 permit ip host 10.0.12.2 host 172.30.17.0` → 受理
- `router eigrp 100` → 受理
- `distribute-list 132 in` → 受理
- `exit` → 受理
- 残った学習経路 **1/7**: ['172.30.17.0/26']

  `show ip access-lists 132`:
```
Extended IP access list 132
    10 permit ip host 10.0.12.2 host 172.30.17.0 (1 match)
```

#### P2F-F3 `permit ip any 172.30.16.0 0.0.15.255`(dst をWCで 16〜31 に)
- `no access-list 132` → 受理
- `access-list 132 permit ip any 172.30.16.0 0.0.15.255` → 受理
- `router eigrp 100` → 受理
- `distribute-list 132 in` → 受理
- `exit` → 受理
- 残った学習経路 **4/7**: ['172.30.16.0/24', '172.30.16.0/28', '172.30.17.0/26', '172.30.18.0/30']

  `show ip access-lists 132`:
```
Extended IP access list 132
    10 permit ip any 172.30.16.0 0.0.15.255 (4 matches)
```

#### P2F-F4 ★`permit ip any host 172.30.16.0`(同一網アドレスの /24 と /28 を区別できるか)
- `no access-list 132` → 受理
- `access-list 132 permit ip any host 172.30.16.0` → 受理
- `router eigrp 100` → 受理
- `distribute-list 132 in` → 受理
- `exit` → 受理
- 残った学習経路 **2/7**: ['172.30.16.0/24', '172.30.16.0/28']

  `show ip access-lists 132`:
```
Extended IP access list 132
    10 permit ip any host 172.30.16.0 (2 matches)
```

### P14_cleanup


#### P14 後片付け

RT01 `show ip access-lists`(残骸が無いこと):
```

```

RT01 `show running-config | include access-group|distribute-list|service-policy|ip nat|verify unicast`:
```
ip nat inside source list 60 interface Ethernet0/1 overload
```

## sweep run (2026-08-10 23:07:38) — checks: P15_undef_vs_empty


基線 RT01 `show ip route eigrp`:
```
Codes: L - local, C - connected, S - static, R - RIP, M - mobile, B - BGP
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area 
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2, m - OMP
       n - NAT, Ni - NAT inside, No - NAT outside, Nd - NAT DIA
       i - IS-IS, su - IS-IS summary, L1 - IS-IS level-1, L2 - IS-IS level-2
       ia - IS-IS inter area, * - candidate default, U - per-user static route
       H - NHRP, G - NHRP registered, g - NHRP registration summary
       o - ODR, P - periodic downloaded static route, l - LISP
       a - application route
       + - replicated route, % - next hop override, p - overrides from PfR
       & - replicated local route overrides by connected

Gateway of last resort is not set

      2.0.0.0/32 is subnetted, 1 subnets
D        2.2.2.2 [90/409600] via 10.0.12.2, 00:50:18, Ethernet0/1
      3.0.0.0/32 is subnetted, 1 subnets
D        3.3.3.3 [90/409600] via 10.0.13.3, 00:50:18, Ethernet0/0
      172.30.0.0/16 is variably subnetted, 5 subnets, 4 masks
D        172.30.16.0/24 [90/409600] via 10.0.12.2, 00:50:28, Ethernet0/1
D        172.30.16.0/28 [90/409600] via 10.0.13.3, 00:50:28, Ethernet0/0
D        172.30.17.0/26 [90/409600] via 10.0.12.2, 00:50:18, Ethernet0/1
D        172.30.18.0/30 [90/409600] via 10.0.12.2, 00:50:18, Ethernet0/1
D        172.30.32.0/24 [90/409600] via 10.0.12.2, 00:50:18, Ethernet0/1
```

### P15_undef_vs_empty


#### P15-a 未定義の**名前**を distribute-list が参照する
- `router eigrp 100` → 受理
- `distribute-list NOSUCHLIST in` → 受理
- `exit` → 受理

  未定義(名前) `show ip access-lists`:
```
(空)
```

  未定義(名前) `show running-config | include distribute-list`:
```
distribute-list NOSUCHLIST in
```

  未定義(名前) `show ip protocols | include Incoming`:
```
Incoming update filter list for all interfaces is not set
  Incoming update filter list for all interfaces is NOSUCHLIST
```
- 残った学習経路: **7/7**

#### P15-b 未定義の**番号**を distribute-list が参照する
- `router eigrp 100` → 受理
- `distribute-list 77 in` → 受理
- `exit` → 受理

  未定義(番号) `show ip access-lists`:
```
(空)
```

  未定義(番号) `show running-config | include distribute-list`:
```
distribute-list 77 in
```

  未定義(番号) `show ip protocols | include Incoming`:
```
Incoming update filter list for all interfaces is not set
  Incoming update filter list for all interfaces is 77
```

#### P15-c **空**の名前付き標準 ACL を参照する
- `ip access-list standard EMPTYLIST` → 受理
- `exit` → 受理
- `router eigrp 100` → 受理
- `distribute-list EMPTYLIST in` → 受理
- `exit` → 受理

  空 `show ip access-lists`:
```
Standard IP access list EMPTYLIST
```

  空 `show running-config | include distribute-list`:
```
distribute-list EMPTYLIST in
```

  空 `show ip protocols | include Incoming`:
```
Incoming update filter list for all interfaces is not set
  Incoming update filter list for all interfaces is EMPTYLIST
```

#### P15-d **名前付き拡張**を参照する(拒否されるはず)
- `ip access-list extended EXTLIST` → 受理
- `permit ip host 10.0.12.2 any` → 受理
- `exit` → 受理
- `router eigrp 100` → 受理
- `distribute-list EXTLIST in` → **% The ACL cannot be created or an ACL with the same name but incompatible type already exists.**
- `exit` → 受理

  名前付き拡張 `show ip access-lists`:
```
Extended IP access list EXTLIST
    10 permit ip host 10.0.12.2 any
```

  名前付き拡張 `show running-config | include distribute-list`:
```
(空)
```

  名前付き拡張 `show ip protocols | include Incoming`:
```
Incoming update filter list for all interfaces is not set
  Incoming update filter list for all interfaces is not set
```

## sweep run (2026-08-10 23:16:36) — checks: V1_ipv6_basics, V2_implicit_nd, V3_undef_empty, V4_seq, V5_cleanup


基線 RT01 `show ip route eigrp`:
```
Codes: L - local, C - connected, S - static, R - RIP, M - mobile, B - BGP
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area 
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2, m - OMP
       n - NAT, Ni - NAT inside, No - NAT outside, Nd - NAT DIA
       i - IS-IS, su - IS-IS summary, L1 - IS-IS level-1, L2 - IS-IS level-2
       ia - IS-IS inter area, * - candidate default, U - per-user static route
       H - NHRP, G - NHRP registered, g - NHRP registration summary
       o - ODR, P - periodic downloaded static route, l - LISP
       a - application route
       + - replicated route, % - next hop override, p - overrides from PfR
       & - replicated local route overrides by connected

Gateway of last resort is not set

      2.0.0.0/32 is subnetted, 1 subnets
D        2.2.2.2 [90/409600] via 10.0.12.2, 00:08:26, Ethernet0/1
      3.0.0.0/32 is subnetted, 1 subnets
D        3.3.3.3 [90/409600] via 10.0.13.3, 00:08:26, Ethernet0/0
      172.30.0.0/16 is variably subnetted, 5 subnets, 4 masks
D        172.30.16.0/24 [90/409600] via 10.0.12.2, 00:08:26, Ethernet0/1
D        172.30.16.0/28 [90/409600] via 10.0.13.3, 00:08:26, Ethernet0/0
D        172.30.17.0/26 [90/409600] via 10.0.12.2, 00:08:26, Ethernet0/1
D        172.30.18.0/30 [90/409600] via 10.0.12.2, 00:08:26, Ethernet0/1
D        172.30.32.0/24 [90/409600] via 10.0.12.2, 00:08:26, Ethernet0/1
```

### V1_ipv6_basics


#### V1 IPv6 ACL の基本(書式・表記・暗黙のエントリ)
- 基線(RT03→RT02 の v6 疎通): **100%**
- `ipv6 access-list V6T` → 受理
- `permit tcp 2001:DB8:13::/64 any eq 22` → 受理
- `permit ipv6 host 2001:DB8:3::3 host 2001:DB8:2::2` → 受理
- `exit` → 受理

RT01 `show ipv6 access-list V6T`(★書式と暗黙エントリ):
```
IPv6 access list V6T
    permit tcp 2001:DB8:13::/64 any eq 22 sequence 10
    permit ipv6 host 2001:DB8:3::3 host 2001:DB8:2::2 sequence 20
```

RT01 `show running-config | section ipv6 access-list`:
```
ipv6 access-list V6T
 sequence 10 permit tcp 2001:DB8:13::/64 any eq 22
 sequence 20 permit ipv6 host 2001:DB8:3::3 host 2001:DB8:2::2
```
- CLI応答: `% Invalid input detected at '^' marker.`
- ワイルドカード表記の可否: **拒否**

### V2_implicit_nd


#### V2 ★暗黙 deny と明示 deny で ND の生死が変わるか

**(a) 暗黙の deny のみ**(明示の deny 行を書かない)

- **暗黙 deny のみ**: RT01→RT03 直結 ping **100%** / RT03→RT02 通過 **0%**

  `show ipv6 neighbors 2001:DB8:13::3`:
```
IPv6 Address                              Age Link-layer Addr State Interface
2001:DB8:13::3                              0 aabb.cc02.4f00  REACH Et0/0
```

  `show ipv6 access-list V6ND`:
```
IPv6 access list V6ND
    permit ipv6 2001:DB8:13::/64 any (6 matches) sequence 10
```

**(b) 末尾に明示の `deny ipv6 any any` を追加**

- **明示 deny あり**: RT01→RT03 直結 ping **100%** / RT03→RT02 通過 **0%**

  `show ipv6 neighbors 2001:DB8:13::3`:
```
IPv6 Address                              Age Link-layer Addr State Interface
2001:DB8:13::3                              0 aabb.cc02.4f00  REACH Et0/0
```

  `show ipv6 access-list V6ND`:
```
IPv6 access list V6ND
    permit ipv6 2001:DB8:13::/64 any (12 matches) sequence 10
    deny ipv6 any any (5 matches) sequence 20
```

**(c) 明示 deny の手前に ND を明示許可**(`permit icmp any any nd-ns` / `nd-na`)
- `ipv6 access-list V6ND` → 受理
- `no deny ipv6 any any` → 受理
- `permit icmp any any nd-ns` → 受理
- `permit icmp any any nd-na` → 受理
- `deny ipv6 any any` → 受理
- `exit` → 受理

- **ND 明示許可あり**: RT01→RT03 直結 ping **100%** / RT03→RT02 通過 **0%**

  `show ipv6 neighbors 2001:DB8:13::3`:
```
IPv6 Address                              Age Link-layer Addr State Interface
2001:DB8:13::3                              0 aabb.cc02.4f00  REACH Et0/0
```

  `show ipv6 access-list V6ND`:
```
IPv6 access list V6ND
    permit ipv6 2001:DB8:13::/64 any (18 matches) sequence 10
    permit icmp any any nd-ns sequence 20
    permit icmp any any nd-na sequence 30
    deny ipv6 any any (5 matches) sequence 40
```

### V3_undef_empty


#### V3 未定義・空の IPv6 ACL
- `interface Ethernet0/0` → 受理
- `ipv6 traffic-filter NOSUCH6 in` → 受理
- `exit` → 受理
- **未定義**: RT03→RT02 通過 **100%**

  `show ipv6 access-list`(未定義):
```
IPv6 access list V6T
    permit tcp 2001:DB8:13::/64 any eq 22 sequence 10
    permit ipv6 host 2001:DB8:3::3 host 2001:DB8:2::2 sequence 20
```

  `show ipv6 interface Ethernet0/0 | include filter|list`:
```
Inbound access list NOSUCH6
```
- `ipv6 access-list EMPTY6` → 受理
- `exit` → 受理
- `interface Ethernet0/0` → 受理
- `ipv6 traffic-filter EMPTY6 in` → 受理
- `exit` → 受理
- **空**: RT03→RT02 通過 **100%**

  `show ipv6 access-list`(空):
```
IPv6 access list V6T
    permit tcp 2001:DB8:13::/64 any eq 22 sequence 10
    permit ipv6 host 2001:DB8:3::3 host 2001:DB8:2::2 sequence 20
```

  `show ipv6 interface Ethernet0/0 | include filter|list`:
```
Inbound access list EMPTY6
```

### V4_seq


#### V4 sequence の扱いとカウンタ
- `ipv6 access-list V6SEQ` → 受理
- `sequence 10 permit ipv6 2001:DB8:13::/64 any` → 受理
- `sequence 30 deny ipv6 any any` → 受理
- `exit` → 受理
- `interface Ethernet0/0` → 受理
- `ipv6 traffic-filter V6SEQ in` → 受理
- `exit` → 受理

① 通した後:
```
IPv6 access list V6SEQ
    permit ipv6 2001:DB8:13::/64 any sequence 10
    deny ipv6 any any (3 matches) sequence 30
```
- `ipv6 access-list V6SEQ` → 受理
- `sequence 20 deny tcp any any eq 23` → 受理
- `exit` → 受理

② `sequence 20` を挿入(★他行のカウンタが残るか):
```
IPv6 access list V6SEQ
    permit ipv6 2001:DB8:13::/64 any sequence 10
    deny tcp any any eq telnet sequence 20
    deny ipv6 any any (3 matches) sequence 30
```
- CLI応答: `% Invalid input detected at '^' marker.`
- resequence の可否: **不可**

③ resequence 後:
```
IPv6 access list V6SEQ
    permit ipv6 2001:DB8:13::/64 any sequence 10
    deny tcp any any eq telnet sequence 20
    deny ipv6 any any (3 matches) sequence 30
```

### V5_cleanup


#### V5 後片付け(IPv6)

RT01 `show ipv6 access-list`(残骸が無いこと):
```
IPv6 access list V6T
    permit tcp 2001:DB8:13::/64 any eq 22 sequence 10
    permit ipv6 host 2001:DB8:3::3 host 2001:DB8:2::2 sequence 20
```

RT01 `show running-config | include traffic-filter`:
```
(空)
```

## sweep run (2026-08-10 23:20:22) — checks: V6_empty_persist, V5_cleanup


基線 RT01 `show ip route eigrp`:
```
Codes: L - local, C - connected, S - static, R - RIP, M - mobile, B - BGP
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area 
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2, m - OMP
       n - NAT, Ni - NAT inside, No - NAT outside, Nd - NAT DIA
       i - IS-IS, su - IS-IS summary, L1 - IS-IS level-1, L2 - IS-IS level-2
       ia - IS-IS inter area, * - candidate default, U - per-user static route
       H - NHRP, G - NHRP registered, g - NHRP registration summary
       o - ODR, P - periodic downloaded static route, l - LISP
       a - application route
       + - replicated route, % - next hop override, p - overrides from PfR
       & - replicated local route overrides by connected

Gateway of last resort is not set

      2.0.0.0/32 is subnetted, 1 subnets
D        2.2.2.2 [90/409600] via 10.0.12.2, 00:12:12, Ethernet0/1
      3.0.0.0/32 is subnetted, 1 subnets
D        3.3.3.3 [90/409600] via 10.0.13.3, 00:12:12, Ethernet0/0
      172.30.0.0/16 is variably subnetted, 5 subnets, 4 masks
D        172.30.16.0/24 [90/409600] via 10.0.12.2, 00:12:12, Ethernet0/1
D        172.30.16.0/28 [90/409600] via 10.0.13.3, 00:12:12, Ethernet0/0
D        172.30.17.0/26 [90/409600] via 10.0.12.2, 00:12:12, Ethernet0/1
D        172.30.18.0/30 [90/409600] via 10.0.12.2, 00:12:12, Ethernet0/1
D        172.30.32.0/24 [90/409600] via 10.0.12.2, 00:12:12, Ethernet0/1
```

### V6_empty_persist


#### V6 空の IPv6 ACL は保持されるか
- `ipv6 access-list EMPTY6B` → 受理
- `exit` → 受理

  `show ipv6 access-list`(引数なし):
```
IPv6 access list V6T
    permit tcp 2001:DB8:13::/64 any eq 22 sequence 10
    permit ipv6 host 2001:DB8:3::3 host 2001:DB8:2::2 sequence 20
```

  `show running-config | section ipv6 access-list`:
```
ipv6 access-list V6T
 sequence 10 permit tcp 2001:DB8:13::/64 any eq 22
 sequence 20 permit ipv6 host 2001:DB8:3::3 host 2001:DB8:2::2
```

  `show ipv6 access-list EMPTY6B`(名指し):
```
(空)
```

  片付け後 `show ipv6 access-list`:
```
(空)
```

### V5_cleanup


#### V5 後片付け(IPv6)

RT01 `show ipv6 access-list`(残骸が無いこと):
```
(空)
```

RT01 `show running-config | include traffic-filter`:
```
(空)
```

## sweep run (2026-08-10 23:34:12) — checks: V7_nd_retest


基線 RT01 `show ip route eigrp`:
```
Codes: L - local, C - connected, S - static, R - RIP, M - mobile, B - BGP
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area 
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2, m - OMP
       n - NAT, Ni - NAT inside, No - NAT outside, Nd - NAT DIA
       i - IS-IS, su - IS-IS summary, L1 - IS-IS level-1, L2 - IS-IS level-2
       ia - IS-IS inter area, * - candidate default, U - per-user static route
       H - NHRP, G - NHRP registered, g - NHRP registration summary
       o - ODR, P - periodic downloaded static route, l - LISP
       a - application route
       + - replicated route, % - next hop override, p - overrides from PfR
       & - replicated local route overrides by connected

Gateway of last resort is not set

      2.0.0.0/32 is subnetted, 1 subnets
D        2.2.2.2 [90/409600] via 10.0.12.2, 00:26:02, Ethernet0/1
      3.0.0.0/32 is subnetted, 1 subnets
D        3.3.3.3 [90/409600] via 10.0.13.3, 00:26:02, Ethernet0/0
      172.30.0.0/16 is variably subnetted, 5 subnets, 4 masks
D        172.30.16.0/24 [90/409600] via 10.0.12.2, 00:26:02, Ethernet0/1
D        172.30.16.0/28 [90/409600] via 10.0.13.3, 00:26:02, Ethernet0/0
D        172.30.17.0/26 [90/409600] via 10.0.12.2, 00:26:02, Ethernet0/1
D        172.30.18.0/30 [90/409600] via 10.0.12.2, 00:26:02, Ethernet0/1
D        172.30.32.0/24 [90/409600] via 10.0.12.2, 00:26:02, Ethernet0/1
```

### V7_nd_retest


#### V7 ★近隣探索の再測(V2 の測定は無効だった)

RT03 のリンクローカル(参考):
```
IPv6 is enabled, link-local address is FE80::A8BB:CCFF:FE02:4F00 
  No Virtual link-local address(es):
```

- **(a) 暗黙の拒否のみ**: RT01→RT03(オンリンクのグローバル) ping **0%**

  `show ipv6 neighbors 2001:DB8:13::3`:
```
IPv6 Address                              Age Link-layer Addr State Interface
2001:DB8:13::3                              0 aabb.cc02.4f00  REACH Et0/0
```

  `show ipv6 access-list V6ND2`:
```
IPv6 access list V6ND2
    permit ipv6 host 2001:DB8:3::3 any sequence 10
```

- **(b) 末尾に明示の deny ipv6 any any**: RT01→RT03(オンリンクのグローバル) ping **0%**

  `show ipv6 neighbors 2001:DB8:13::3`:
```
IPv6 Address                              Age Link-layer Addr State Interface
2001:DB8:13::3                              0 -               INCMP Et0/0
```

  `show ipv6 access-list V6ND2`:
```
IPv6 access list V6ND2
    permit ipv6 host 2001:DB8:3::3 any sequence 10
    deny ipv6 any any (15 matches) sequence 20
```

- **(c) ND を明示許可した上で明示の deny**: RT01→RT03(オンリンクのグローバル) ping **0%**

  `show ipv6 neighbors 2001:DB8:13::3`:
```
IPv6 Address                              Age Link-layer Addr State Interface
2001:DB8:13::3                              0 aabb.cc02.4f00  REACH Et0/0
```

  `show ipv6 access-list V6ND2`:
```
IPv6 access list V6ND2
    permit ipv6 host 2001:DB8:3::3 any sequence 10
    permit icmp any any nd-ns (1 match) sequence 20
    permit icmp any any nd-na (1 match) sequence 30
    deny ipv6 any any (5 matches) sequence 40
```

## sweep run (2026-08-10 23:48:54) — checks: A1_outbound_selfgen, A2_bgp_update_source


基線 RT01 `show ip route eigrp`:
```
Codes: L - local, C - connected, S - static, R - RIP, M - mobile, B - BGP
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area 
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2, m - OMP
       n - NAT, Ni - NAT inside, No - NAT outside, Nd - NAT DIA
       i - IS-IS, su - IS-IS summary, L1 - IS-IS level-1, L2 - IS-IS level-2
       ia - IS-IS inter area, * - candidate default, U - per-user static route
       H - NHRP, G - NHRP registered, g - NHRP registration summary
       o - ODR, P - periodic downloaded static route, l - LISP
       a - application route
       + - replicated route, % - next hop override, p - overrides from PfR
       & - replicated local route overrides by connected

Gateway of last resort is not set

      2.0.0.0/32 is subnetted, 1 subnets
D        2.2.2.2 [90/409600] via 10.0.12.2, 00:40:44, Ethernet0/1
      3.0.0.0/32 is subnetted, 1 subnets
D        3.3.3.3 [90/409600] via 10.0.13.3, 00:40:44, Ethernet0/0
      172.30.0.0/16 is variably subnetted, 5 subnets, 4 masks
D        172.30.16.0/24 [90/409600] via 10.0.12.2, 00:40:44, Ethernet0/1
D        172.30.16.0/28 [90/409600] via 10.0.13.3, 00:40:44, Ethernet0/0
D        172.30.17.0/26 [90/409600] via 10.0.12.2, 00:40:44, Ethernet0/1
D        172.30.18.0/30 [90/409600] via 10.0.12.2, 00:40:44, Ethernet0/1
D        172.30.32.0/24 [90/409600] via 10.0.12.2, 00:40:44, Ethernet0/1
```

### A1_outbound_selfgen


#### A1 outbound ACL と自機生成トラフィック(対照つき再検証)

適用直後(基点):
```
Extended IP access list SELFT
    10 deny icmp any host 2.2.2.2
    20 permit ip any any (1 match)
```

- (i) **自機生成×deny に一致**(RT01→2.2.2.2): **0%**

  カウンタ:
```
Extended IP access list SELFT
    10 deny icmp any host 2.2.2.2 (5 matches)
    20 permit ip any any (4 matches)
```

- (ii) 対照= 自機生成×deny に不一致(RT01→10.0.12.2): **100%**

  カウンタ:
```
Extended IP access list SELFT
    10 deny icmp any host 2.2.2.2 (5 matches)
    20 permit ip any any (9 matches)
```

- (iii) 対照= 転送×deny に一致(RT03→2.2.2.2): **0%**

  カウンタ:
```
Extended IP access list SELFT
    10 deny icmp any host 2.2.2.2 (10 matches)
    20 permit ip any any (11 matches)
```

### A2_bgp_update_source


#### A2 片側だけ update-source 欠け(iBGP・Lo ピア)

- **(a) 両側に update-source あり(基線)**

  RT01 `show ip bgp summary`:
```
Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
2.2.2.2         4        65000       4       4        1    0    0 00:01:01        0
```

  RT02 `show ip bgp summary`:
```
Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
1.1.1.1         4        65000       4       4        1    0    0 00:01:08        0
```

- **(b) ★RT02 側だけ update-source を外す**

  RT01 `show ip bgp summary`:
```
Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
2.2.2.2         4        65000       4       4        1    0    0 00:00:58        0
```

  RT02 `show ip bgp summary`:
```
Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
1.1.1.1         4        65000       4       4        1    0    0 00:01:05        0
```

- **(c) 対照= 両側とも update-source なし**

  RT01 `show ip bgp summary`:
```
Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
2.2.2.2         4        65000       0       0        1    0    0 00:01:10 Idle
```

  RT02 `show ip bgp summary`:
```
Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
1.1.1.1         4        65000       0       0        1    0    0 00:01:16 Idle
```

## sweep run (2026-08-11 00:05:47) — checks: C1_routemap_semantics, C3_named_workaround, C2_out_direction


基線 RT01 `show ip route eigrp`:
```
Codes: L - local, C - connected, S - static, R - RIP, M - mobile, B - BGP
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area 
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2, m - OMP
       n - NAT, Ni - NAT inside, No - NAT outside, Nd - NAT DIA
       i - IS-IS, su - IS-IS summary, L1 - IS-IS level-1, L2 - IS-IS level-2
       ia - IS-IS inter area, * - candidate default, U - per-user static route
       H - NHRP, G - NHRP registered, g - NHRP registration summary
       o - ODR, P - periodic downloaded static route, l - LISP
       a - application route
       + - replicated route, % - next hop override, p - overrides from PfR
       & - replicated local route overrides by connected

Gateway of last resort is not set

      2.0.0.0/32 is subnetted, 1 subnets
D        2.2.2.2 [90/409600] via 10.0.12.2, 00:12:34, Ethernet0/1
      3.0.0.0/32 is subnetted, 1 subnets
D        3.3.3.3 [90/409600] via 10.0.13.3, 00:12:34, Ethernet0/0
      172.30.0.0/16 is variably subnetted, 5 subnets, 4 masks
D        172.30.16.0/24 [90/409600] via 10.0.12.2, 00:12:34, Ethernet0/1
D        172.30.16.0/28 [90/409600] via 10.0.13.3, 00:12:34, Ethernet0/0
D        172.30.17.0/26 [90/409600] via 10.0.12.2, 00:12:34, Ethernet0/1
D        172.30.18.0/30 [90/409600] via 10.0.12.2, 00:12:34, Ethernet0/1
D        172.30.32.0/24 [90/409600] via 10.0.12.2, 00:12:34, Ethernet0/1
```

### C1_routemap_semantics


#### C1 route-map 経由の拡張 ACL の意味論

##### C1a 対照 `permit ip any any`(機構が動くか)
- `no access-list 150` → 受理
- `access-list 150 permit ip any any` → 受理
- `no route-map RM-IN` → **% Could not find route-map RM-IN**
- `route-map RM-IN permit 10` → 受理
- ` match ip address 150` → 受理
- `exit` → 受理
- `router eigrp 100` → 受理
- `distribute-list route-map RM-IN in` → 受理
- `exit` → 受理
- 残った学習経路 **7/7**: ['172.30.16.0/24', '172.30.16.0/28', '172.30.17.0/26', '172.30.18.0/30', '172.30.32.0/24', '2.2.2.2/32', '3.3.3.3/32']

  `show ip access-lists 150`:
```
Extended IP access list 150
    10 permit ip any any (7 matches)
```

##### C1b ★教科書形 `permit ip host 172.30.17.0 host 255.255.255.192`(網+マスク)
- `no access-list 150` → 受理
- `access-list 150 permit ip host 172.30.17.0 host 255.255.255.192` → 受理
- `no route-map RM-IN` → 受理
- `route-map RM-IN permit 10` → 受理
- ` match ip address 150` → 受理
- `exit` → 受理
- `router eigrp 100` → 受理
- `distribute-list route-map RM-IN in` → 受理
- `exit` → 受理
- 残った学習経路 **1/7**: ['172.30.17.0/26']

  `show ip access-lists 150`:
```
Extended IP access list 150
    10 permit ip host 172.30.17.0 host 255.255.255.192 (1 match)
```

##### C1c `permit ip host 10.0.12.2 any`(src=広告元 の読み)
- `no access-list 150` → 受理
- `access-list 150 permit ip host 10.0.12.2 any` → 受理
- `no route-map RM-IN` → 受理
- `route-map RM-IN permit 10` → 受理
- ` match ip address 150` → 受理
- `exit` → 受理
- `router eigrp 100` → 受理
- `distribute-list route-map RM-IN in` → 受理
- `exit` → 受理
- 残った学習経路 **0/7**: []

  `show ip access-lists 150`:
```
Extended IP access list 150
    10 permit ip host 10.0.12.2 any
```

##### C1d ★★`permit ip any host 255.255.255.0`(dst=マスク=/24 だけ通す)
- `no access-list 150` → 受理
- `access-list 150 permit ip any host 255.255.255.0` → 受理
- `no route-map RM-IN` → 受理
- `route-map RM-IN permit 10` → 受理
- ` match ip address 150` → 受理
- `exit` → 受理
- `router eigrp 100` → 受理
- `distribute-list route-map RM-IN in` → 受理
- `exit` → 受理
- 残った学習経路 **2/7**: ['172.30.16.0/24', '172.30.32.0/24']

  `show ip access-lists 150`:
```
Extended IP access list 150
    10 permit ip any host 255.255.255.0 (2 matches)
```

##### C1e `permit ip any host 172.30.17.0`(dst=網 の読み)
- `no access-list 150` → 受理
- `access-list 150 permit ip any host 172.30.17.0` → 受理
- `no route-map RM-IN` → 受理
- `route-map RM-IN permit 10` → 受理
- ` match ip address 150` → 受理
- `exit` → 受理
- `router eigrp 100` → 受理
- `distribute-list route-map RM-IN in` → 受理
- `exit` → 受理
- 残った学習経路 **0/7**: []

  `show ip access-lists 150`:
```
Extended IP access list 150
    10 permit ip any host 172.30.17.0
```

### C3_named_workaround


#### C3 名前付き拡張 ACL の回避策(先に参照→後から定義)

**(a) 先に distribute-list で参照する(ACL 未定義の状態)**
- `router eigrp 100` → 受理
- `distribute-list NAMEDEXT in` → 受理
- `exit` → 受理

**(b) 後から名前付き拡張 ACL として定義する**
- `ip access-list extended NAMEDEXT` → 受理
- `permit ip host 10.0.12.2 any` → 受理
- `exit` → 受理
- 残った学習経路 **5/7**: ['172.30.16.0/24', '172.30.17.0/26', '172.30.18.0/30', '172.30.32.0/24', '2.2.2.2/32']

  `show ip protocols | include Incoming`:
```
Incoming update filter list for all interfaces is not set
  Incoming update filter list for all interfaces is NAMEDEXT
```

  `show ip access-lists NAMEDEXT`:
```
Extended IP access list NAMEDEXT
    10 permit ip host 10.0.12.2 any (7 matches)
```

### C2_out_direction


#### C2 out 方向の拡張 ACL
RT01 が RT02 へ広告する経路(3.3.3.3/32・172.30.16.0/28)を、RT02 側で観測する。

基線(RT02 の学習):
```

```

##### C2a `deny ip host 10.0.13.3 any` + permit any(src=広告元 の読み)
- `no access-list 160` → 受理
- `access-list 160 deny ip host 10.0.13.3 any` → 受理
- `access-list 160 permit ip any any` → 受理
- `router eigrp 100` → 受理
- `distribute-list 160 out` → 受理
- `exit` → 受理

  RT02 の学習:
```
D        3.3.3.3 [90/435200] via 10.0.12.1, 00:00:11, Ethernet0/0
D        172.30.16.0/28 [90/435200] via 10.0.12.1, 00:00:11, Ethernet0/0
```

##### C2b `deny ip host 3.3.3.3 any` + permit any(src=網 の読み)
- `no access-list 160` → 受理
- `access-list 160 deny ip host 3.3.3.3 any` → 受理
- `access-list 160 permit ip any any` → 受理
- `router eigrp 100` → 受理
- `distribute-list 160 out` → 受理
- `exit` → 受理

  RT02 の学習:
```
D        3.3.3.3 [90/435200] via 10.0.12.1, 00:00:48, Ethernet0/0
D        172.30.16.0/28 [90/435200] via 10.0.12.1, 00:00:48, Ethernet0/0
```

復旧後の RT02 の学習:
```
D        3.3.3.3 [90/435200] via 10.0.12.1, 00:01:05, Ethernet0/0
D        172.30.16.0/28 [90/435200] via 10.0.12.1, 00:01:05, Ethernet0/0
```
