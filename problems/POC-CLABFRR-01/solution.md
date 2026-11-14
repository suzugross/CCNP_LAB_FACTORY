# POC-CLABFRR-01 模範解答

```
configure
set interfaces et-0/0/0 unit 0 family inet address 10.0.13.1/30
set interfaces lo0 unit 0 family inet address 192.168.0.1/32
set routing-options router-id 192.168.0.1
set protocols ospf area 0.0.0.0 interface et-0/0/0.0
set protocols ospf area 0.0.0.0 interface lo0.0 passive
commit and-quit
```

確認(JUN01): `show ospf neighbor`(10.0.13.2 が Full)・`show route 192.168.0.3/32 exact`・
`ping 192.168.0.3 source 192.168.0.1 count 5 rapid`。FRR1 側: `show ip ospf neighbor`・`show ip route 192.168.0.1/32`。
