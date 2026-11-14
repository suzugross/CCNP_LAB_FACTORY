# JNT-01 模範解答(J0)

```
On JUN01:
configure
set interfaces et-0/0/0 unit 0 family inet address 10.0.12.1/30
set interfaces lo0 unit 0 family inet address 192.168.0.1/32
set protocols ospf area 0.0.0.0 interface et-0/0/0.0
set protocols ospf area 0.0.0.0 interface lo0.0 passive
commit and-quit

On JUN02:
configure
set interfaces et-0/0/0 unit 0 family inet address 10.0.12.2/30
set interfaces et-0/0/1 unit 0 family inet address 10.0.23.1/30
set interfaces lo0 unit 0 family inet address 192.168.0.2/32
set protocols ospf area 0.0.0.0 interface et-0/0/0.0
set protocols ospf area 0.0.0.0 interface et-0/0/1.0
set protocols ospf area 0.0.0.0 interface lo0.0 passive
commit and-quit

J0-3(JUN02): MTU 9000 を commit confirmed で入れ、OSPF が ExStart/Exchange に留まるのを見て、確定せずに巻き戻るのを待つ。
configure
set interfaces et-0/0/1 mtu 9000
commit confirmed 3 comment "MTU 9000 toward FRR1"
(待つ → "Commit was not confirmed; automatic rollback complete.")
exit

J0-4(JUN02):
configure
set routing-options static route 198.51.100.0/24 next-hop 192.168.0.3
set routing-options static route 198.51.100.0/24 resolve
set routing-options static route 198.51.100.0/24 preference 160
commit and-quit
```
