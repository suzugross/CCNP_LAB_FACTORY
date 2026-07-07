# 模範解答 : ENARSI-BGP-01 variant=mh-auth (Loopbackピア + multihop + 認証)

設定するのは **RT01 (AS65001)** のみ。

```
! ピア Loopback への到達性（直結IF経由のstatic）
ip route 2.2.2.2 255.255.255.255 10.1.12.2
ip route 3.3.3.3 255.255.255.255 10.1.13.2
!
router bgp 65001
 bgp log-neighbor-changes
 ! RT02 と Loopback ピア(eBGP multihop + 認証)
 neighbor 2.2.2.2 remote-as 65002
 neighbor 2.2.2.2 update-source Loopback0
 neighbor 2.2.2.2 ebgp-multihop 2
 neighbor 2.2.2.2 password CCNP-BGP
 ! RT03 と Loopback ピア(eBGP multihop + 認証)
 neighbor 3.3.3.3 remote-as 65003
 neighbor 3.3.3.3 update-source Loopback0
 neighbor 3.3.3.3 ebgp-multihop 2
 neighbor 3.3.3.3 password CCNP-BGP
 ! 自分の Loopback を広告
 network 1.1.1.1 mask 255.255.255.255
```

## 確認
```
show ip bgp summary                 ! 2.2.2.2 / 3.3.3.3 が Established
show ip bgp neighbors 2.2.2.2 | include password|state
show ip route bgp                   ! 4.4.4.4/32 を学習(next-hop=2.2.2.2 recursive)
```

### ポイント（落とし穴）
- **eBGP を Loopback で張ると直結でなくなる**ため、既定の TTL=1 では到達できず `ebgp-multihop`(>=2) が必須。
- `update-source Loopback0` を入れないと、相手から見た送信元が物理IFになり、相手の `neighbor <自分のLo>` 設定と一致せずセッションが上がらない。
- **相手の Loopback への IP 到達性**が無いと TCP セッションが張れない。IGP を使わない指定なので static で補う。
- `password` は両側一致が必須。値が違う/片側だけだと Established にならない（採点は Established=効果で実質検証 + 設定行の存在を raw 確認）。
- 採点は loopback ピアのネイバーアドレス(2.2.2.2 / 3.3.3.3)で Established を見るため、物理IPで張ると 0 点。
