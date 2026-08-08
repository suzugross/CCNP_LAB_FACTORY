
## sweep run (2026-08-07 23:41:40)


### E1a_area0_out_denyC

効果発現(clearなし): 4s で確認

R1 `show ipv6 route ospf`:
```
IPv6 Routing Table - default - 10 entries
Codes: C - Connected, L - Local, S - Static, U - Per-user Static route
       B - BGP, R - RIP, H - NHRP, HG - NHRP registered
       Hg - NHRP registration summary, HE - NHRP External, I1 - ISIS L1
       I2 - ISIS L2, IA - ISIS interarea, IS - ISIS summary, D - EIGRP
       EX - EIGRP external, ND - ND Default, NDp - ND Prefix, DCE - Destination
       NDr - Redirect, RL - RPL, O - OSPF Intra, OI - OSPF Inter
       OE1 - OSPF ext 1, OE2 - OSPF ext 2, ON1 - OSPF NSSA ext 1
       ON2 - OSPF NSSA ext 2, la - LISP alt, lr - LISP site-registrations
       ld - LISP dyn-eid, lA - LISP away, le - LISP extranet-policy
       lp - LISP publications, ls - LISP destinations-summary, a - Application
       m - OMP
OI  2001:DB8:0:A::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
OI  2001:DB8:3:3::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
OI  2001:DB8:9:9::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
OI  2001:DB8:A:A::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
OI  2001:DB8:B:B::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
```
R3 `show ipv6 route ospf`:
```
IPv6 Routing Table - default - 9 entries
Codes: C - Connected, L - Local, S - Static, U - Per-user Static route
       B - BGP, R - RIP, H - NHRP, HG - NHRP registered
       Hg - NHRP registration summary, HE - NHRP External, I1 - ISIS L1
       I2 - ISIS L2, IA - ISIS interarea, IS - ISIS summary, D - EIGRP
       EX - EIGRP external, ND - ND Default, NDp - ND Prefix, DCE - Destination
       NDr - Redirect, RL - RPL, O - OSPF Intra, OI - OSPF Inter
       OE1 - OSPF ext 1, OE2 - OSPF ext 2, ON1 - OSPF NSSA ext 1
       ON2 - OSPF NSSA ext 2, la - LISP alt, lr - LISP site-registrations
       ld - LISP dyn-eid, lA - LISP away, le - LISP extranet-policy
       lp - LISP publications, ls - LISP destinations-summary, a - Application
       m - OMP
OI  2001:DB8:0:A::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD20, Ethernet0/0
OI  2001:DB8:1:1::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD20, Ethernet0/0
OI  2001:DB8:2:2::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD20, Ethernet0/0
OI  2001:DB8:9:9::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD20, Ethernet0/0
OI  2001:DB8:A:A::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD20, Ethernet0/0
OI  2001:DB8:B:B::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD20, Ethernet0/0
```
R2 `show ipv6 route ospf`:
```
IPv6 Routing Table - default - 12 entries
Codes: C - Connected, L - Local, S - Static, U - Per-user Static route
       B - BGP, R - RIP, H - NHRP, HG - NHRP registered
       Hg - NHRP registration summary, HE - NHRP External, I1 - ISIS L1
       I2 - ISIS L2, IA - ISIS interarea, IS - ISIS summary, D - EIGRP
       EX - EIGRP external, ND - ND Default, NDp - ND Prefix, DCE - Destination
       NDr - Redirect, RL - RPL, O - OSPF Intra, OI - OSPF Inter
       OE1 - OSPF ext 1, OE2 - OSPF ext 2, ON1 - OSPF NSSA ext 1
       ON2 - OSPF NSSA ext 2, la - LISP alt, lr - LISP site-registrations
       ld - LISP dyn-eid, lA - LISP away, le - LISP extranet-policy
       lp - LISP publications, ls - LISP destinations-summary, a - Application
       m - OMP
O   2001:DB8:2:2::/64 [110/10]
     via Ethernet0/0, directly connected
O   2001:DB8:9:9::/64 [110/11]
     via FE80::A8BB:CCFF:FE01:E000, Ethernet0/1
O   2001:DB8:A:A::/64 [110/11]
     via FE80::A8BB:CCFF:FE01:E000, Ethernet0/1
O   2001:DB8:B:B::/64 [110/11]
     via FE80::A8BB:CCFF:FE01:E000, Ethernet0/1
O   2001:DB8:C:C::/64 [110/11]
     via FE80::A8BB:CCFF:FE01:E000, Ethernet0/1
```

### E1b_area10_in_denyC

効果発現(clearなし): 4s で確認

R1 `show ipv6 route ospf`:
```
IPv6 Routing Table - default - 10 entries
Codes: C - Connected, L - Local, S - Static, U - Per-user Static route
       B - BGP, R - RIP, H - NHRP, HG - NHRP registered
       Hg - NHRP registration summary, HE - NHRP External, I1 - ISIS L1
       I2 - ISIS L2, IA - ISIS interarea, IS - ISIS summary, D - EIGRP
       EX - EIGRP external, ND - ND Default, NDp - ND Prefix, DCE - Destination
       NDr - Redirect, RL - RPL, O - OSPF Intra, OI - OSPF Inter
       OE1 - OSPF ext 1, OE2 - OSPF ext 2, ON1 - OSPF NSSA ext 1
       ON2 - OSPF NSSA ext 2, la - LISP alt, lr - LISP site-registrations
       ld - LISP dyn-eid, lA - LISP away, le - LISP extranet-policy
       lp - LISP publications, ls - LISP destinations-summary, a - Application
       m - OMP
OI  2001:DB8:0:A::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
OI  2001:DB8:3:3::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
OI  2001:DB8:9:9::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
OI  2001:DB8:A:A::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
OI  2001:DB8:B:B::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
```
R3 `show ipv6 route ospf`:
```
IPv6 Routing Table - default - 10 entries
Codes: C - Connected, L - Local, S - Static, U - Per-user Static route
       B - BGP, R - RIP, H - NHRP, HG - NHRP registered
       Hg - NHRP registration summary, HE - NHRP External, I1 - ISIS L1
       I2 - ISIS L2, IA - ISIS interarea, IS - ISIS summary, D - EIGRP
       EX - EIGRP external, ND - ND Default, NDp - ND Prefix, DCE - Destination
       NDr - Redirect, RL - RPL, O - OSPF Intra, OI - OSPF Inter
       OE1 - OSPF ext 1, OE2 - OSPF ext 2, ON1 - OSPF NSSA ext 1
       ON2 - OSPF NSSA ext 2, la - LISP alt, lr - LISP site-registrations
       ld - LISP dyn-eid, lA - LISP away, le - LISP extranet-policy
       lp - LISP publications, ls - LISP destinations-summary, a - Application
       m - OMP
OI  2001:DB8:0:A::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD20, Ethernet0/0
OI  2001:DB8:1:1::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD20, Ethernet0/0
OI  2001:DB8:2:2::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD20, Ethernet0/0
OI  2001:DB8:9:9::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD20, Ethernet0/0
OI  2001:DB8:A:A::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD20, Ethernet0/0
OI  2001:DB8:B:B::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD20, Ethernet0/0
OI  2001:DB8:C:C::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD20, Ethernet0/0
```

### E4_area10_out_deny22

(固定待ち 20s)

R1 `show ipv6 route ospf`:
```
IPv6 Routing Table - default - 11 entries
Codes: C - Connected, L - Local, S - Static, U - Per-user Static route
       B - BGP, R - RIP, H - NHRP, HG - NHRP registered
       Hg - NHRP registration summary, HE - NHRP External, I1 - ISIS L1
       I2 - ISIS L2, IA - ISIS interarea, IS - ISIS summary, D - EIGRP
       EX - EIGRP external, ND - ND Default, NDp - ND Prefix, DCE - Destination
       NDr - Redirect, RL - RPL, O - OSPF Intra, OI - OSPF Inter
       OE1 - OSPF ext 1, OE2 - OSPF ext 2, ON1 - OSPF NSSA ext 1
       ON2 - OSPF NSSA ext 2, la - LISP alt, lr - LISP site-registrations
       ld - LISP dyn-eid, lA - LISP away, le - LISP extranet-policy
       lp - LISP publications, ls - LISP destinations-summary, a - Application
       m - OMP
OI  2001:DB8:0:A::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
OI  2001:DB8:3:3::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
OI  2001:DB8:9:9::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
OI  2001:DB8:A:A::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
OI  2001:DB8:B:B::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
OI  2001:DB8:C:C::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
```
Ra `show ipv6 route ospf`:
```
IPv6 Routing Table - default - 13 entries
Codes: C - Connected, L - Local, S - Static, U - Per-user Static route
       B - BGP, R - RIP, H - NHRP, HG - NHRP registered
       Hg - NHRP registration summary, HE - NHRP External, I1 - ISIS L1
       I2 - ISIS L2, IA - ISIS interarea, IS - ISIS summary, D - EIGRP
       EX - EIGRP external, ND - ND Default, NDp - ND Prefix, DCE - Destination
       NDr - Redirect, RL - RPL, O - OSPF Intra, OI - OSPF Inter
       OE1 - OSPF ext 1, OE2 - OSPF ext 2, ON1 - OSPF NSSA ext 1
       ON2 - OSPF NSSA ext 2, la - LISP alt, lr - LISP site-registrations
       ld - LISP dyn-eid, lA - LISP away, le - LISP extranet-policy
       lp - LISP publications, ls - LISP destinations-summary, a - Application
       m - OMP
OI  2001:DB8:1:1::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD10, Ethernet0/0
OI  2001:DB8:3:3::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD10, Ethernet0/0
```
R3 `show ipv6 route ospf`:
```
IPv6 Routing Table - default - 9 entries
Codes: C - Connected, L - Local, S - Static, U - Per-user Static route
       B - BGP, R - RIP, H - NHRP, HG - NHRP registered
       Hg - NHRP registration summary, HE - NHRP External, I1 - ISIS L1
       I2 - ISIS L2, IA - ISIS interarea, IS - ISIS summary, D - EIGRP
       EX - EIGRP external, ND - ND Default, NDp - ND Prefix, DCE - Destination
       NDr - Redirect, RL - RPL, O - OSPF Intra, OI - OSPF Inter
       OE1 - OSPF ext 1, OE2 - OSPF ext 2, ON1 - OSPF NSSA ext 1
       ON2 - OSPF NSSA ext 2, la - LISP alt, lr - LISP site-registrations
       ld - LISP dyn-eid, lA - LISP away, le - LISP extranet-policy
       lp - LISP publications, ls - LISP destinations-summary, a - Application
       m - OMP
OI  2001:DB8:0:A::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD20, Ethernet0/0
OI  2001:DB8:1:1::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD20, Ethernet0/0
OI  2001:DB8:9:9::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD20, Ethernet0/0
OI  2001:DB8:A:A::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD20, Ethernet0/0
OI  2001:DB8:B:B::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD20, Ethernet0/0
OI  2001:DB8:C:C::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD20, Ethernet0/0
```
R2 `show ipv6 route ospf`:
```
IPv6 Routing Table - default - 12 entries
Codes: C - Connected, L - Local, S - Static, U - Per-user Static route
       B - BGP, R - RIP, H - NHRP, HG - NHRP registered
       Hg - NHRP registration summary, HE - NHRP External, I1 - ISIS L1
       I2 - ISIS L2, IA - ISIS interarea, IS - ISIS summary, D - EIGRP
       EX - EIGRP external, ND - ND Default, NDp - ND Prefix, DCE - Destination
       NDr - Redirect, RL - RPL, O - OSPF Intra, OI - OSPF Inter
       OE1 - OSPF ext 1, OE2 - OSPF ext 2, ON1 - OSPF NSSA ext 1
       ON2 - OSPF NSSA ext 2, la - LISP alt, lr - LISP site-registrations
       ld - LISP dyn-eid, lA - LISP away, le - LISP extranet-policy
       lp - LISP publications, ls - LISP destinations-summary, a - Application
       m - OMP
O   2001:DB8:2:2::/64 [110/10]
     via Ethernet0/0, directly connected
O   2001:DB8:9:9::/64 [110/11]
     via FE80::A8BB:CCFF:FE01:E000, Ethernet0/1
O   2001:DB8:A:A::/64 [110/11]
     via FE80::A8BB:CCFF:FE01:E000, Ethernet0/1
O   2001:DB8:B:B::/64 [110/11]
     via FE80::A8BB:CCFF:FE01:E000, Ethernet0/1
O   2001:DB8:C:C::/64 [110/11]
     via FE80::A8BB:CCFF:FE01:E000, Ethernet0/1
```

### E2a_distlist_R1_in

効果発現(clearなし): 0s で確認

R1 `show ipv6 route ospf`:
```
IPv6 Routing Table - default - 10 entries
Codes: C - Connected, L - Local, S - Static, U - Per-user Static route
       B - BGP, R - RIP, H - NHRP, HG - NHRP registered
       Hg - NHRP registration summary, HE - NHRP External, I1 - ISIS L1
       I2 - ISIS L2, IA - ISIS interarea, IS - ISIS summary, D - EIGRP
       EX - EIGRP external, ND - ND Default, NDp - ND Prefix, DCE - Destination
       NDr - Redirect, RL - RPL, O - OSPF Intra, OI - OSPF Inter
       OE1 - OSPF ext 1, OE2 - OSPF ext 2, ON1 - OSPF NSSA ext 1
       ON2 - OSPF NSSA ext 2, la - LISP alt, lr - LISP site-registrations
       ld - LISP dyn-eid, lA - LISP away, le - LISP extranet-policy
       lp - LISP publications, ls - LISP destinations-summary, a - Application
       m - OMP
OI  2001:DB8:0:A::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
OI  2001:DB8:3:3::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
OI  2001:DB8:9:9::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
OI  2001:DB8:B:B::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
OI  2001:DB8:C:C::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
```
R1 `show ipv6 ospf database inter-area prefix`:
```
OSPFv3 Router with ID (1.1.1.1) (Process ID 10)

		Inter Area Prefix Link States (Area 10)

  LS age: 99
  LS Type: Inter Area Prefix Links
  Link State ID: 0
  Advertising Router: 2.2.2.2
  LS Seq Number: 80000001
  Checksum: 0x11E6
  Length: 36
  Metric: 10 
  Prefix Address: 2001:DB8:3:3::
  Prefix Length: 64, Options: None

  LS age: 99
  LS Type: Inter Area Prefix Links
  Link State ID: 1
  Advertising Router: 2.2.2.2
  LS Seq Number: 80000001
  Checksum: 0x559D
  Length: 36
  Metric: 10 
  Prefix Address: 2001:DB8:0:A::
  Prefix Length: 64, Options: None

  LS age: 50
  LS Type: Inter Area Prefix Links
  Link State ID: 3
  Advertising Router: 2.2.2.2
  LS Seq Number: 80000001
  Checksum: 0xAD9
  Length: 36
  Metric: 11 
  Prefix Address: 2001:DB8:B:B::
  Prefix Length: 64, Options: None

  LS age: 50
  LS Type: Inter Area Prefix Links
  Link State ID: 4
  Advertising Router: 2.2.2.2
  LS Seq Number: 80000001
  Checksum: 0xDD07
  Length: 36
  Metric: 11 
  Prefix Address: 2001:DB8:A:A::
  Prefix Length: 64, Options: None

  LS age: 50
  LS Type: Inter Area Prefix Links
  Link State ID: 5
  Advertising Router: 2.2.2.2
  LS Seq Number: 80000001
  Checksum: 0xB134
  Length: 36
  Metric: 11 
  Prefix Address: 2001:DB8:9:9::
  Prefix Length: 64, Options: None

  LS age: 30
  LS Type: Inter Area Prefix Links
  Link State ID: 7
  Advertising Router: 2.2.2.2
  LS Seq Number: 80000001
  Checksum: 0x4D9
  Length: 36
  Metric: 11 
  Prefix Address: 2001:DB8:C:C::
  Prefix Length: 64, Options: None
```
R1 `show running-config | section router ospfv3`:
```
router ospfv3 10
 router-id 1.1.1.1
 !
 address-family ipv6 unicast
  distribute-list prefix-list PL_E2 in
 exit-address-family
```

### E2b_distlist_R2_in

(固定待ち 30s)

R1 `show ipv6 route ospf`:
```
IPv6 Routing Table - default - 10 entries
Codes: C - Connected, L - Local, S - Static, U - Per-user Static route
       B - BGP, R - RIP, H - NHRP, HG - NHRP registered
       Hg - NHRP registration summary, HE - NHRP External, I1 - ISIS L1
       I2 - ISIS L2, IA - ISIS interarea, IS - ISIS summary, D - EIGRP
       EX - EIGRP external, ND - ND Default, NDp - ND Prefix, DCE - Destination
       NDr - Redirect, RL - RPL, O - OSPF Intra, OI - OSPF Inter
       OE1 - OSPF ext 1, OE2 - OSPF ext 2, ON1 - OSPF NSSA ext 1
       ON2 - OSPF NSSA ext 2, la - LISP alt, lr - LISP site-registrations
       ld - LISP dyn-eid, lA - LISP away, le - LISP extranet-policy
       lp - LISP publications, ls - LISP destinations-summary, a - Application
       m - OMP
OI  2001:DB8:0:A::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
OI  2001:DB8:3:3::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
OI  2001:DB8:A:A::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
OI  2001:DB8:B:B::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
OI  2001:DB8:C:C::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
```
R2 `show ipv6 route ospf`:
```
IPv6 Routing Table - default - 11 entries
Codes: C - Connected, L - Local, S - Static, U - Per-user Static route
       B - BGP, R - RIP, H - NHRP, HG - NHRP registered
       Hg - NHRP registration summary, HE - NHRP External, I1 - ISIS L1
       I2 - ISIS L2, IA - ISIS interarea, IS - ISIS summary, D - EIGRP
       EX - EIGRP external, ND - ND Default, NDp - ND Prefix, DCE - Destination
       NDr - Redirect, RL - RPL, O - OSPF Intra, OI - OSPF Inter
       OE1 - OSPF ext 1, OE2 - OSPF ext 2, ON1 - OSPF NSSA ext 1
       ON2 - OSPF NSSA ext 2, la - LISP alt, lr - LISP site-registrations
       ld - LISP dyn-eid, lA - LISP away, le - LISP extranet-policy
       lp - LISP publications, ls - LISP destinations-summary, a - Application
       m - OMP
O   2001:DB8:2:2::/64 [110/10]
     via Ethernet0/0, directly connected
O   2001:DB8:A:A::/64 [110/11]
     via FE80::A8BB:CCFF:FE01:E000, Ethernet0/1
O   2001:DB8:B:B::/64 [110/11]
     via FE80::A8BB:CCFF:FE01:E000, Ethernet0/1
O   2001:DB8:C:C::/64 [110/11]
     via FE80::A8BB:CCFF:FE01:E000, Ethernet0/1
```
R3 `show ipv6 route ospf`:
```
IPv6 Routing Table - default - 9 entries
Codes: C - Connected, L - Local, S - Static, U - Per-user Static route
       B - BGP, R - RIP, H - NHRP, HG - NHRP registered
       Hg - NHRP registration summary, HE - NHRP External, I1 - ISIS L1
       I2 - ISIS L2, IA - ISIS interarea, IS - ISIS summary, D - EIGRP
       EX - EIGRP external, ND - ND Default, NDp - ND Prefix, DCE - Destination
       NDr - Redirect, RL - RPL, O - OSPF Intra, OI - OSPF Inter
       OE1 - OSPF ext 1, OE2 - OSPF ext 2, ON1 - OSPF NSSA ext 1
       ON2 - OSPF NSSA ext 2, la - LISP alt, lr - LISP site-registrations
       ld - LISP dyn-eid, lA - LISP away, le - LISP extranet-policy
       lp - LISP publications, ls - LISP destinations-summary, a - Application
       m - OMP
OI  2001:DB8:0:A::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD20, Ethernet0/0
OI  2001:DB8:1:1::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD20, Ethernet0/0
OI  2001:DB8:2:2::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD20, Ethernet0/0
OI  2001:DB8:A:A::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD20, Ethernet0/0
OI  2001:DB8:B:B::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD20, Ethernet0/0
OI  2001:DB8:C:C::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD20, Ethernet0/0
```

### E3a_range_notadv

効果発現(clearなし): 0s で確認

R1 `show ipv6 route ospf`:
```
IPv6 Routing Table - default - 7 entries
Codes: C - Connected, L - Local, S - Static, U - Per-user Static route
       B - BGP, R - RIP, H - NHRP, HG - NHRP registered
       Hg - NHRP registration summary, HE - NHRP External, I1 - ISIS L1
       I2 - ISIS L2, IA - ISIS interarea, IS - ISIS summary, D - EIGRP
       EX - EIGRP external, ND - ND Default, NDp - ND Prefix, DCE - Destination
       NDr - Redirect, RL - RPL, O - OSPF Intra, OI - OSPF Inter
       OE1 - OSPF ext 1, OE2 - OSPF ext 2, ON1 - OSPF NSSA ext 1
       ON2 - OSPF NSSA ext 2, la - LISP alt, lr - LISP site-registrations
       ld - LISP dyn-eid, lA - LISP away, le - LISP extranet-policy
       lp - LISP publications, ls - LISP destinations-summary, a - Application
       m - OMP
OI  2001:DB8:0:A::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
OI  2001:DB8:3:3::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
```
R3 `show ipv6 route ospf`:
```
IPv6 Routing Table - default - 6 entries
Codes: C - Connected, L - Local, S - Static, U - Per-user Static route
       B - BGP, R - RIP, H - NHRP, HG - NHRP registered
       Hg - NHRP registration summary, HE - NHRP External, I1 - ISIS L1
       I2 - ISIS L2, IA - ISIS interarea, IS - ISIS summary, D - EIGRP
       EX - EIGRP external, ND - ND Default, NDp - ND Prefix, DCE - Destination
       NDr - Redirect, RL - RPL, O - OSPF Intra, OI - OSPF Inter
       OE1 - OSPF ext 1, OE2 - OSPF ext 2, ON1 - OSPF NSSA ext 1
       ON2 - OSPF NSSA ext 2, la - LISP alt, lr - LISP site-registrations
       ld - LISP dyn-eid, lA - LISP away, le - LISP extranet-policy
       lp - LISP publications, ls - LISP destinations-summary, a - Application
       m - OMP
OI  2001:DB8:0:A::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD20, Ethernet0/0
OI  2001:DB8:1:1::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD20, Ethernet0/0
OI  2001:DB8:2:2::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD20, Ethernet0/0
```

### E3b_range_adv

効果発現(clearなし): 0s で確認

R1 `show ipv6 route ospf`:
```
IPv6 Routing Table - default - 8 entries
Codes: C - Connected, L - Local, S - Static, U - Per-user Static route
       B - BGP, R - RIP, H - NHRP, HG - NHRP registered
       Hg - NHRP registration summary, HE - NHRP External, I1 - ISIS L1
       I2 - ISIS L2, IA - ISIS interarea, IS - ISIS summary, D - EIGRP
       EX - EIGRP external, ND - ND Default, NDp - ND Prefix, DCE - Destination
       NDr - Redirect, RL - RPL, O - OSPF Intra, OI - OSPF Inter
       OE1 - OSPF ext 1, OE2 - OSPF ext 2, ON1 - OSPF NSSA ext 1
       ON2 - OSPF NSSA ext 2, la - LISP alt, lr - LISP site-registrations
       ld - LISP dyn-eid, lA - LISP away, le - LISP extranet-policy
       lp - LISP publications, ls - LISP destinations-summary, a - Application
       m - OMP
OI  2001:DB8:0:A::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
OI  2001:DB8:3:3::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
OI  2001:DB8:8::/45 [110/21]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
```
R3 `show ipv6 route ospf`:
```
IPv6 Routing Table - default - 7 entries
Codes: C - Connected, L - Local, S - Static, U - Per-user Static route
       B - BGP, R - RIP, H - NHRP, HG - NHRP registered
       Hg - NHRP registration summary, HE - NHRP External, I1 - ISIS L1
       I2 - ISIS L2, IA - ISIS interarea, IS - ISIS summary, D - EIGRP
       EX - EIGRP external, ND - ND Default, NDp - ND Prefix, DCE - Destination
       NDr - Redirect, RL - RPL, O - OSPF Intra, OI - OSPF Inter
       OE1 - OSPF ext 1, OE2 - OSPF ext 2, ON1 - OSPF NSSA ext 1
       ON2 - OSPF NSSA ext 2, la - LISP alt, lr - LISP site-registrations
       ld - LISP dyn-eid, lA - LISP away, le - LISP extranet-policy
       lp - LISP publications, ls - LISP destinations-summary, a - Application
       m - OMP
OI  2001:DB8:0:A::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD20, Ethernet0/0
OI  2001:DB8:1:1::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD20, Ethernet0/0
OI  2001:DB8:2:2::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD20, Ethernet0/0
OI  2001:DB8:8::/45 [110/21]
     via FE80::A8BB:CCFF:FE01:DD20, Ethernet0/0
```
R2 `show ipv6 route ospf | include /45|Null`:
```
O   2001:DB8:8::/45 [110/11]
     via Null0, directly connected
```

### E7a_bit46_only

効果発現(clearなし): 0s で確認

R1 `show ipv6 route ospf`:
```
IPv6 Routing Table - default - 8 entries
Codes: C - Connected, L - Local, S - Static, U - Per-user Static route
       B - BGP, R - RIP, H - NHRP, HG - NHRP registered
       Hg - NHRP registration summary, HE - NHRP External, I1 - ISIS L1
       I2 - ISIS L2, IA - ISIS interarea, IS - ISIS summary, D - EIGRP
       EX - EIGRP external, ND - ND Default, NDp - ND Prefix, DCE - Destination
       NDr - Redirect, RL - RPL, O - OSPF Intra, OI - OSPF Inter
       OE1 - OSPF ext 1, OE2 - OSPF ext 2, ON1 - OSPF NSSA ext 1
       ON2 - OSPF NSSA ext 2, la - LISP alt, lr - LISP site-registrations
       ld - LISP dyn-eid, lA - LISP away, le - LISP extranet-policy
       lp - LISP publications, ls - LISP destinations-summary, a - Application
       m - OMP
OI  2001:DB8:9:9::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
OI  2001:DB8:A:A::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
OI  2001:DB8:B:B::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
```

### E7b_bit47_only

効果発現(clearなし): 0s で確認

R1 `show ipv6 route ospf`:
```
IPv6 Routing Table - default - 7 entries
Codes: C - Connected, L - Local, S - Static, U - Per-user Static route
       B - BGP, R - RIP, H - NHRP, HG - NHRP registered
       Hg - NHRP registration summary, HE - NHRP External, I1 - ISIS L1
       I2 - ISIS L2, IA - ISIS interarea, IS - ISIS summary, D - EIGRP
       EX - EIGRP external, ND - ND Default, NDp - ND Prefix, DCE - Destination
       NDr - Redirect, RL - RPL, O - OSPF Intra, OI - OSPF Inter
       OE1 - OSPF ext 1, OE2 - OSPF ext 2, ON1 - OSPF NSSA ext 1
       ON2 - OSPF NSSA ext 2, la - LISP alt, lr - LISP site-registrations
       ld - LISP dyn-eid, lA - LISP away, le - LISP extranet-policy
       lp - LISP publications, ls - LISP destinations-summary, a - Application
       m - OMP
OI  2001:DB8:A:A::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
OI  2001:DB8:B:B::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
```

### E7c_default_only

効果発現(clearなし): 75s 以内に発現せず

R1 `show ipv6 route ospf`:
```
IPv6 Routing Table - default - 5 entries
Codes: C - Connected, L - Local, S - Static, U - Per-user Static route
       B - BGP, R - RIP, H - NHRP, HG - NHRP registered
       Hg - NHRP registration summary, HE - NHRP External, I1 - ISIS L1
       I2 - ISIS L2, IA - ISIS interarea, IS - ISIS summary, D - EIGRP
       EX - EIGRP external, ND - ND Default, NDp - ND Prefix, DCE - Destination
       NDr - Redirect, RL - RPL, O - OSPF Intra, OI - OSPF Inter
       OE1 - OSPF ext 1, OE2 - OSPF ext 2, ON1 - OSPF NSSA ext 1
       ON2 - OSPF NSSA ext 2, la - LISP alt, lr - LISP site-registrations
       ld - LISP dyn-eid, lA - LISP away, le - LISP extranet-policy
       lp - LISP publications, ls - LISP destinations-summary, a - Application
       m - OMP
```

### E5_gele_syntax

    CLI応答: `% Invalid prefix range for 2001:DB8:8::/45, make sure: len < ge-value <= le-value`
    CLI応答: `% Invalid prefix range for 2001:DB8:8::/45, make sure: len < ge-value <= le-value`
    CLI応答: `% Invalid prefix range for 2001:DB8:8::/45, make sure: len < ge-value <= le-value`
    CLI応答: `% Invalid prefix range for 2001:DB8:8::/45, make sure: len < ge-value <= le-value`
(固定待ち 2s)

R1 `show ipv6 route ospf`:
```
IPv6 Routing Table - default - 11 entries
Codes: C - Connected, L - Local, S - Static, U - Per-user Static route
       B - BGP, R - RIP, H - NHRP, HG - NHRP registered
       Hg - NHRP registration summary, HE - NHRP External, I1 - ISIS L1
       I2 - ISIS L2, IA - ISIS interarea, IS - ISIS summary, D - EIGRP
       EX - EIGRP external, ND - ND Default, NDp - ND Prefix, DCE - Destination
       NDr - Redirect, RL - RPL, O - OSPF Intra, OI - OSPF Inter
       OE1 - OSPF ext 1, OE2 - OSPF ext 2, ON1 - OSPF NSSA ext 1
       ON2 - OSPF NSSA ext 2, la - LISP alt, lr - LISP site-registrations
       ld - LISP dyn-eid, lA - LISP away, le - LISP extranet-policy
       lp - LISP publications, ls - LISP destinations-summary, a - Application
       m - OMP
OI  2001:DB8:0:A::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
OI  2001:DB8:3:3::/64 [110/20]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
OI  2001:DB8:9:9::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
OI  2001:DB8:A:A::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
OI  2001:DB8:B:B::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
OI  2001:DB8:C:C::/64 [110/21]
     via FE80::A8BB:CCFF:FE01:DD00, Ethernet0/0
```
R2 `show ipv6 prefix-list`:
```
ipv6 prefix-list T5: 1 entries
   seq 5 permit 2001:DB8:8::/45 ge 46 le 64
ipv6 prefix-list T6: 1 entries
   seq 5 permit ::/0 le 128
ipv6 prefix-list T7: 1 entries
   seq 5 permit ::/0 ge 1
```

## 追測: le 境界の受理挙動 (2026-08-08・R2 で単発実測)

```
ipv6 prefix-list L1 permit 2001:DB8:8::/45 le 45
% Invalid prefix range for 2001:DB8:8::/45, make sure: len < ge-value <= le-value
```
L2 `le 46` / L3 `ge 64 le 64` / L4 `ge 46 le 46` / L5 `le 128` / L7 `le 63` → 受理。
L6 `::/0 le 0` → 受理されるが `show ipv6 prefix-list` の保存形は `permit ::/0`
(le 0 が正規化で消える=デフォルトのみマッチ)。

確定則: **len < ge ≤ le / len < le(le単独時)。ge・le とも len 同値は不可。ge=le は可**
(長さ完全一致マッチ)。

## P1 spotcheck run 1 (2026-08-08) 生ログ(初回ケースは起動直後の収束レースで偽不一致・基線待ち付き再検で解消)

lab start...
== dir_swap/hide_all (seed 226) ==
  R1 model=['2001:DB8:0:A::/64', '2001:DB8:3:3::/64', '2001:DB8:9:9::/64', '2001:DB8:A:A::/64', '2001:DB8:C:C::/64']
  R1 live =['2001:DB8:0:A::/64', '2001:DB8:3:3::/64']  ★不一致
  R3 model=['2001:DB8:0:A::/64', '2001:DB8:1:1::/64', '2001:DB8:2:2::/64', '2001:DB8:9:9::/64', '2001:DB8:A:A::/64', '2001:DB8:B:B::/64', '2001:DB8:C:C::/64']
  R3 live =['2001:DB8:0:A::/64', '2001:DB8:1:1::/64', '2001:DB8:2:2::/64']  ★不一致
== mask_off/summarize (seed 226) ==
  R1 model=['2001:DB8:0:A::/64', '2001:DB8:3:3::/64', '2001:DB8:8::/46', '2001:DB8:C:C::/64']
  R1 live =['2001:DB8:0:A::/64', '2001:DB8:3:3::/64', '2001:DB8:8::/46', '2001:DB8:C:C::/64']  OK
  R3 model=['2001:DB8:0:A::/64', '2001:DB8:1:1::/64', '2001:DB8:2:2::/64', '2001:DB8:8::/46', '2001:DB8:C:C::/64']
  R3 live =['2001:DB8:0:A::/64', '2001:DB8:1:1::/64', '2001:DB8:2:2::/64', '2001:DB8:8::/46', '2001:DB8:C:C::/64']  OK
== dl_abr/rib_only (seed 226) ==
  R1 model=['2001:DB8:0:A::/64', '2001:DB8:3:3::/64', '2001:DB8:9:9::/64', '2001:DB8:A:A::/64', '2001:DB8:C:C::/64']
  R1 live =['2001:DB8:0:A::/64', '2001:DB8:3:3::/64', '2001:DB8:9:9::/64', '2001:DB8:A:A::/64', '2001:DB8:C:C::/64']  OK
  R3 model=['2001:DB8:0:A::/64', '2001:DB8:1:1::/64', '2001:DB8:2:2::/64', '2001:DB8:9:9::/64', '2001:DB8:A:A::/64', '2001:DB8:C:C::/64']
  R3 live =['2001:DB8:0:A::/64', '2001:DB8:1:1::/64', '2001:DB8:2:2::/64', '2001:DB8:9:9::/64', '2001:DB8:A:A::/64', '2001:DB8:C:C::/64']  OK
== le_off/area10_only (seed 226) ==
  R1 model=[]
  R1 live =[]  OK
  R3 model=['2001:DB8:0:A::/64', '2001:DB8:1:1::/64', '2001:DB8:2:2::/64', '2001:DB8:9:9::/64', '2001:DB8:A:A::/64', '2001:DB8:B:B::/64', '2001:DB8:C:C::/64']
  R3 live =['2001:DB8:0:A::/64', '2001:DB8:1:1::/64', '2001:DB8:2:2::/64', '2001:DB8:9:9::/64', '2001:DB8:A:A::/64', '2001:DB8:B:B::/64', '2001:DB8:C:C::/64']  OK
== seq_shadow/rib_only (seed 226) ==
  R1 model=['2001:DB8:0:A::/64', '2001:DB8:3:3::/64', '2001:DB8:9:9::/64', '2001:DB8:A:A::/64', '2001:DB8:B:B::/64', '2001:DB8:C:C::/64']
  R1 live =['2001:DB8:0:A::/64', '2001:DB8:3:3::/64', '2001:DB8:9:9::/64', '2001:DB8:A:A::/64', '2001:DB8:B:B::/64', '2001:DB8:C:C::/64']  OK
  R3 model=['2001:DB8:0:A::/64', '2001:DB8:1:1::/64', '2001:DB8:2:2::/64', '2001:DB8:9:9::/64', '2001:DB8:A:A::/64', '2001:DB8:B:B::/64', '2001:DB8:C:C::/64']
  R3 live =['2001:DB8:0:A::/64', '2001:DB8:1:1::/64', '2001:DB8:2:2::/64', '2001:DB8:9:9::/64', '2001:DB8:A:A::/64', '2001:DB8:B:B::/64', '2001:DB8:C:C::/64']  OK
== extra: 未定義PL参照 filter-list ==
  R1 with undefined-ref filter: ['2001:DB8:0:A::/64', '2001:DB8:3:3::/64', '2001:DB8:9:9::/64', '2001:DB8:A:A::/64', '2001:DB8:B:B::/64', '2001:DB8:C:C::/64']
  R1 baseline restored: 6 OI routes
  R1 残存PL: なし
  R2 残存PL: なし
  R3 残存PL: なし
lab stopped. RESULT: MISMATCH あり

## P1 spotcheck run 2 (2026-08-08) — dir_swap 基線待ち付き再検

lab start...
baseline OK: 6 OI routes
== dir_swap/hide_all (seed 226) ==
  R1 model=['2001:DB8:0:A::/64', '2001:DB8:3:3::/64', '2001:DB8:9:9::/64', '2001:DB8:A:A::/64', '2001:DB8:C:C::/64']
  R1 live =['2001:DB8:0:A::/64', '2001:DB8:3:3::/64', '2001:DB8:9:9::/64', '2001:DB8:A:A::/64', '2001:DB8:C:C::/64']  OK
  R3 model=['2001:DB8:0:A::/64', '2001:DB8:1:1::/64', '2001:DB8:2:2::/64', '2001:DB8:9:9::/64', '2001:DB8:A:A::/64', '2001:DB8:B:B::/64', '2001:DB8:C:C::/64']
  R3 live =['2001:DB8:0:A::/64', '2001:DB8:1:1::/64', '2001:DB8:2:2::/64', '2001:DB8:9:9::/64', '2001:DB8:A:A::/64', '2001:DB8:B:B::/64', '2001:DB8:C:C::/64']  OK
== extra: 未定義PL参照 filter-list ==
  R1 with undefined-ref filter: ['2001:DB8:0:A::/64', '2001:DB8:3:3::/64', '2001:DB8:9:9::/64', '2001:DB8:A:A::/64', '2001:DB8:B:B::/64', '2001:DB8:C:C::/64']
  R1 baseline restored: 6 OI routes
  R1 残存PL: なし
  R2 残存PL: なし
  R3 残存PL: なし
lab stopped. RESULT: ALL OK
