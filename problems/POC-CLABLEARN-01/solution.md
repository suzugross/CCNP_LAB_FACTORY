# POC-CLABLEARN-01 模範解答

```
configure
set interfaces et-0/0/0 unit 0 family inet address 10.0.14.1/30
set interfaces lo0 unit 0 family inet address 192.168.0.1/32
set routing-options router-id 192.168.0.1
set protocols ospf area 0.0.0.0 interface et-0/0/0.0
set protocols ospf area 0.0.0.0 interface lo0.0 passive
commit and-quit
```
