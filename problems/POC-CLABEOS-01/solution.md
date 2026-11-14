# POC-CLABEOS-01 模範解答(cEOS 4.37.0F で確認済み)

ログインすると `eos1>`(特権レベル 1)なので、まず `enable`。

```
enable
configure
ip routing
interface Ethernet1
   no switchport
   ip address 10.0.14.1/30
interface Loopback0
   ip address 192.168.0.4/32
router ospf 1
   router-id 192.168.0.4
   passive-interface Loopback0
   network 10.0.14.0/30 area 0.0.0.0
   network 192.168.0.4/32 area 0.0.0.0
end
write memory
```

確認(EOS1): `show ip ospf neighbor`(192.168.0.3 が FULL)・`show ip route 192.168.0.3/32`・
`ping 192.168.0.3 source 192.168.0.4 repeat 5`。
