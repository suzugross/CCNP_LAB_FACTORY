
## P0 基線(IKEv1 Phase3)  (2026-09-21 07:00)

- P0 基線: 健全復帰 16s

**P0 hub — RT01# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Hub, NHRP Peers:3, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 198.51.100.2         172.16.0.2    UP 00:00:16     D
     1 198.51.100.6         172.16.0.3    UP 00:00:15     D
     1 198.51.100.10        172.16.0.4    UP 00:00:15     D
```

**P0 hub — RT01# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.6    QM_IDLE           1005 ACTIVE
203.0.113.2     198.51.100.6    MM_NO_STATE       1002 ACTIVE (deleted)
203.0.113.2     198.51.100.2    QM_IDLE           1004 ACTIVE
203.0.113.2     198.51.100.2    MM_NO_STATE       1001 ACTIVE (deleted)
203.0.113.2     198.51.100.10   QM_IDLE           1006 ACTIVE
203.0.113.2     198.51.100.10   MM_NO_STATE       1003 ACTIVE (deleted)

IPv6 Crypto ISAKMP SA
```

**P0 hub — RT01# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```
   current_peer 198.51.100.10 port 500
    #pkts encaps: 16, #pkts encrypt: 16, #pkts digest: 16
    #pkts decaps: 12, #pkts decrypt: 12, #pkts verify: 12
        in use settings ={Transport, }
        in use settings ={Transport, }
   current_peer 198.51.100.6 port 500
    #pkts encaps: 17, #pkts encrypt: 17, #pkts digest: 17
    #pkts decaps: 16, #pkts decrypt: 16, #pkts verify: 16
        in use settings ={Transport, }
        in use settings ={Transport, }
   current_peer 198.51.100.2 port 500
    #pkts encaps: 18, #pkts encrypt: 18, #pkts digest: 18
    #pkts decaps: 17, #pkts decrypt: 17, #pkts verify: 17
        in use settings ={Transport, }
        in use settings ={Transport, }
```

**P0 hub — RT01# show ip eigrp neighbors**

```
EIGRP-IPv4 Neighbors for AS(100)
H   Address                 Interface              Hold Uptime   SRTT   RTO  Q  Seq
                                                   (sec)         (ms)       Cnt Num
2   172.16.0.4              Tu0                      14 00:00:14    6  1512  0  6
1   172.16.0.2              Tu0                      10 00:00:15   11  1512  0  10
0   172.16.0.3              Tu0                      10 00:00:15   15  1512  0  9
```

**P0 spoke→spoke — RT02# ping 10.0.3.1 repeat 5 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 10.0.3.1, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/3 ms
```

**P0 RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:2, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     2 198.51.100.6         172.16.0.3    UP 00:00:05   DT2
                            172.16.0.3    UP 00:00:05   DT1
     1 203.0.113.2          172.16.0.1    UP 00:00:23     S
```

**P0 RT02 — RT02# show ip nhrp nhs detail**

```
Legend:	E=Expecting replies, R=Responding, W=Waiting, D=Dynamic
Tunnel0:
172.16.0.1  RE  NBMA Address: 203.0.113.2 priority = 0 cluster = 0  req-sent 1  req-failed 0  repl-recv 1 (00:00:22 ago)
```

**P0 RT02 — RT02# show ip route next-hop-override | begin Gateway**

```
Gateway of last resort is 198.51.100.1 to network 0.0.0.0

S*    0.0.0.0/0 [1/0] via 198.51.100.1
      10.0.0.0/8 is variably subnetted, 5 subnets, 2 masks
D        10.0.0.0/24 [90/27008000] via 172.16.0.1, 00:00:22, Tunnel0
C        10.0.2.0/24 is directly connected, Loopback1
L        10.0.2.1/32 is directly connected, Loopback1
D   %    10.0.3.0/24 [90/28288000] via 172.16.0.1, 00:00:21, Tunnel0
                     [NHO][90/255] via 172.16.0.3, 00:00:06, Tunnel0
D        10.0.4.0/24 [90/28288000] via 172.16.0.1, 00:00:21, Tunnel0
      172.16.0.0/16 is variably subnetted, 3 subnets, 2 masks
C        172.16.0.0/24 is directly connected, Tunnel0
L        172.16.0.2/32 is directly connected, Tunnel0
H        172.16.0.3/32 is directly connected, 00:00:06, Tunnel0
      198.51.100.0/24 is variably subnetted, 2 subnets, 2 masks
C        198.51.100.0/30 is directly connected, Ethernet0/0
L        198.51.100.2/32 is directly connected, Ethernet0/0
```

## P5x protection 変更と自動 shutdown  (2026-09-21 07:03)

- == P5x: protection 追加で自動 shutdown するか

**P5x 削除**

```
interface Tunnel0
no tunnel protection ipsec profile DMVPN-PROF
---
(応答なし)
```

**P5x 削除直後 — RT01# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.1      YES TFTP   up                    up
```

**P5x 再追加**

```
interface Tunnel0
tunnel protection ipsec profile DMVPN-PROF
---
(応答なし)
```

**P5x 再追加直後 — RT01# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.1      YES TFTP   up                    up
```

**P5x hub log — RT01 show logging**

```
*Sep 21 07:02:15.210: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is DOWN
*Sep 21 07:02:15.210: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is DOWN
*Sep 21 07:02:15.210: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is DOWN
*Sep 21 07:02:15.216: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:02:15.310: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:02:16.018: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:02:16.039: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is UP
*Sep 21 07:02:16.039: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is UP
*Sep 21 07:02:16.043: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is UP
*Sep 21 07:02:16.118: %SYS-5-CONFIG_I: Configured from console by console
```

**P5x 60s 後 — RT01# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Hub, NHRP Peers:3, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 198.51.100.2         172.16.0.2    UP 00:03:10     D
     1 198.51.100.6         172.16.0.3    UP 00:03:10     D
     1 198.51.100.10        172.16.0.4    UP 00:03:09     D
```

- P5x 後: 健全復帰 16s

## W1 hub の tunnel protection なし(profile は定義済み)  (2026-09-21 07:05)

- == W1: hub の tunnel protection なし(profile は定義済み)

**W1 注入 RT01**

```
interface Tunnel0
no tunnel protection ipsec profile DMVPN-PROF
---
(応答なし)
```

**W1 hub — RT01# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================
```

**W1 hub — RT01# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status

IPv6 Crypto ISAKMP SA
```

**W1 hub — RT01# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```

```

**W1 hub — RT01# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.1      YES TFTP   up                    up
```

**W1 hub log — RT01 show logging**

```
*Sep 21 07:03:50.269: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is DOWN
*Sep 21 07:03:50.269: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is DOWN
*Sep 21 07:03:50.269: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is DOWN
*Sep 21 07:03:50.275: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:03:50.369: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:03:50.998: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.2 NBMA: 198.51.100.2 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:03:50.998: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:03:50.998: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:03:50.999: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.4 (Tunnel0) is down: interface down
*Sep 21 07:03:50.999: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.3 (Tunnel0) is down: interface down
*Sep 21 07:03:50.999: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.2 (Tunnel0) is down: interface down
*Sep 21 07:03:51.199: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:03:52.999: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:03:52.999: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:03:57.856: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:03:59.655: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:03:59.655: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
```

**W1 RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:1, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 203.0.113.2          172.16.0.1   IKE 00:01:10     S
```

**W1 RT02 — RT02# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.2    MM_NO_STATE          0 ACTIVE
203.0.113.2     198.51.100.2    MM_NO_STATE          0 ACTIVE (deleted)

IPv6 Crypto ISAKMP SA
```

**W1 RT02 — RT02# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```
   current_peer 203.0.113.2 port 500
    #pkts encaps: 0, #pkts encrypt: 0, #pkts digest: 0
    #pkts decaps: 0, #pkts decrypt: 0, #pkts verify: 0
```

**W1 RT02 — RT02# show ip nhrp nhs detail**

```
Legend:	E=Expecting replies, R=Responding, W=Waiting, D=Dynamic
Tunnel0:
172.16.0.1   E  NBMA Address: 203.0.113.2 priority = 0 cluster = 0  req-sent 6  req-failed 0  repl-recv 0 (00:01:45 ago)


Pending Registration Requests:
Registration Request: Reqid 15, Ret 64  NHS 172.16.0.1 expired (Tu0)
```

**W1 RT02 — RT02# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.2      YES TFTP   up                    up
```

**W1 RT02 log — RT02 show logging**

```
*Sep 21 07:03:50.270: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is DOWN
*Sep 21 07:03:50.270: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:03:51.907: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.1 (Tunnel0) is down: interface down
*Sep 21 07:03:51.907: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:03:52.107: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:03:53.907: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:03:53.907: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:03:58.494: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:03:58.593: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:04:00.494: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:04:00.494: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
*Sep 21 07:04:05.792: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: NHRP Registration Failure(NHRP: no error)
```

**W1 是正 RT01**

```
interface Tunnel0
tunnel protection ipsec profile DMVPN-PROF
---
(応答なし)
```

- W1 是正後: 健全復帰 16s

## W2 hub の ipsec profile も protection も無い(profile 未定義)  (2026-09-21 07:07)

- == W2: hub の ipsec profile も protection も無い(profile 未定義)

**W2 注入 RT01**

```
interface Tunnel0
no tunnel protection ipsec profile DMVPN-PROF
exit
no crypto ipsec profile DMVPN-PROF
---
(応答なし)
```

**W2 hub — RT01# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================
```

**W2 hub — RT01# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status

IPv6 Crypto ISAKMP SA
```

**W2 hub — RT01# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```

```

**W2 hub — RT01# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.1      YES TFTP   up                    up
```

**W2 hub log — RT01 show logging**

```
*Sep 21 07:05:46.719: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is DOWN
*Sep 21 07:05:46.719: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is DOWN
*Sep 21 07:05:46.719: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is DOWN
*Sep 21 07:05:46.726: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:05:47.218: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:05:47.923: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.2 NBMA: 198.51.100.2 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:05:47.923: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:05:47.923: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:05:47.924: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.4 (Tunnel0) is down: interface down
*Sep 21 07:05:47.924: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.3 (Tunnel0) is down: interface down
*Sep 21 07:05:47.924: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.2 (Tunnel0) is down: interface down
*Sep 21 07:05:48.124: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:05:49.924: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:05:49.924: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:05:54.569: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:05:56.470: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:05:56.470: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
```

**W2 RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:1, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 203.0.113.2          172.16.0.1   IKE 00:01:11     S
```

**W2 RT02 — RT02# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.2    MM_NO_STATE          0 ACTIVE
203.0.113.2     198.51.100.2    MM_NO_STATE          0 ACTIVE (deleted)

IPv6 Crypto ISAKMP SA
```

**W2 RT02 — RT02# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```
   current_peer 203.0.113.2 port 500
    #pkts encaps: 0, #pkts encrypt: 0, #pkts digest: 0
    #pkts decaps: 0, #pkts decrypt: 0, #pkts verify: 0
```

**W2 RT02 — RT02# show ip nhrp nhs detail**

```
Legend:	E=Expecting replies, R=Responding, W=Waiting, D=Dynamic
Tunnel0:
172.16.0.1   E  NBMA Address: 203.0.113.2 priority = 0 cluster = 0  req-sent 6  req-failed 0  repl-recv 0 (00:01:45 ago)


Pending Registration Requests:
Registration Request: Reqid 21, Ret 64  NHS 172.16.0.1 expired (Tu0)
```

**W2 RT02 — RT02# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.2      YES TFTP   up                    up
```

**W2 RT02 log — RT02 show logging**

```
*Sep 21 07:05:46.721: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is DOWN
*Sep 21 07:05:46.721: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:05:48.571: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.1 (Tunnel0) is down: interface down
*Sep 21 07:05:48.572: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:05:48.671: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:05:50.571: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:05:50.571: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:05:55.019: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:05:55.119: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:05:57.018: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:05:57.018: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
*Sep 21 07:06:02.161: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: NHRP Registration Failure(NHRP: no error)
```

**W2 是正 RT01**

```
crypto ipsec profile DMVPN-PROF
set transform-set TS
exit
interface Tunnel0
tunnel protection ipsec profile DMVPN-PROF
---
(応答なし)
```

- W2 是正後: 健全復帰 16s

## W3 hub の ip nhrp network-id なし  (2026-09-21 07:09)

- == W3: hub の ip nhrp network-id なし

**W3 注入 RT01**

```
interface Tunnel0
no ip nhrp network-id 100
---
(応答なし)
```

**W3 hub — RT01# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================
```

**W3 hub — RT01# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.6    QM_IDLE           1023 ACTIVE
203.0.113.2     198.51.100.2    QM_IDLE           1022 ACTIVE
203.0.113.2     198.51.100.10   QM_IDLE           1024 ACTIVE

IPv6 Crypto ISAKMP SA
```

**W3 hub — RT01# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```
   current_peer 198.51.100.10 port 500
    #pkts encaps: 0, #pkts encrypt: 0, #pkts digest: 0
    #pkts decaps: 25, #pkts decrypt: 25, #pkts verify: 25
        in use settings ={Transport, }
        in use settings ={Transport, }
   current_peer 198.51.100.6 port 500
    #pkts encaps: 0, #pkts encrypt: 0, #pkts digest: 0
    #pkts decaps: 26, #pkts decrypt: 26, #pkts verify: 26
        in use settings ={Transport, }
        in use settings ={Transport, }
   current_peer 198.51.100.2 port 500
    #pkts encaps: 0, #pkts encrypt: 0, #pkts digest: 0
    #pkts decaps: 26, #pkts decrypt: 26, #pkts verify: 26
        in use settings ={Transport, }
        in use settings ={Transport, }
```

**W3 hub — RT01# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.1      YES TFTP   up                    up
```

**W3 hub log — RT01 show logging**

```
*Sep 21 07:07:43.912: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.2 NBMA: 198.51.100.2 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: administratively prohibited(NHRP: no error)
*Sep 21 07:07:43.912: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is DOWN
*Sep 21 07:07:43.912: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: administratively prohibited(NHRP: no error)
*Sep 21 07:07:43.912: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is DOWN
*Sep 21 07:07:43.912: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: administratively prohibited(NHRP: no error)
*Sep 21 07:07:43.912: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is DOWN
*Sep 21 07:07:43.912: %DMVPN-5-NHRP_NETID_UNCONFIGURED:  Tunnel0: NETID : 100 Unconfigured (Tunnel: 172.16.0.1 NBMA:  203.0.113.2)
*Sep 21 07:07:44.012: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:07:44.366: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is UP
*Sep 21 07:07:44.618: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is DOWN
*Sep 21 07:07:44.619: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.4 (Tunnel0) is down: interface down
*Sep 21 07:07:44.619: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.2 (Tunnel0) is down: interface down
*Sep 21 07:07:44.619: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.3 (Tunnel0) is down: interface down
*Sep 21 07:07:44.620: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:07:44.719: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:07:46.618: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:07:46.618: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:07:50.872: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:07:50.972: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:07:51.479: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is UP
*Sep 21 07:07:51.964: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is UP
*Sep 21 07:07:52.594: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is UP
*Sep 21 07:07:52.872: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:07:52.872: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
*Sep 21 07:07:54.301: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.2 (Tunnel0) is up: new adjacency
*Sep 21 07:07:54.695: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.3 (Tunnel0) is up: new adjacency
*Sep 21 07:07:55.776: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.4 (Tunnel0) is up: new adjacency
```

**W3 RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:1, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 203.0.113.2          172.16.0.1  NHRP 00:01:10     S
```

**W3 RT02 — RT02# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.2    QM_IDLE           1011 ACTIVE

IPv6 Crypto ISAKMP SA
```

**W3 RT02 — RT02# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```
   current_peer 203.0.113.2 port 500
    #pkts encaps: 26, #pkts encrypt: 26, #pkts digest: 26
    #pkts decaps: 0, #pkts decrypt: 0, #pkts verify: 0
        in use settings ={Transport, }
        in use settings ={Transport, }
```

**W3 RT02 — RT02# show ip nhrp nhs detail**

```
Legend:	E=Expecting replies, R=Responding, W=Waiting, D=Dynamic
Tunnel0:
172.16.0.1   E  NBMA Address: 203.0.113.2 priority = 0 cluster = 0  req-sent 6  req-failed 0  repl-recv 0 (00:01:43 ago)


Pending Registration Requests:
Registration Request: Reqid 29, Ret 64  NHS 172.16.0.1 expired (Tu0)
```

**W3 RT02 — RT02# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.2      YES TFTP   up                    up
```

**W3 RT02 log — RT02 show logging**

```
*Sep 21 07:07:43.914: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is DOWN
*Sep 21 07:07:43.914: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:07:44.365: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is UP
*Sep 21 07:07:44.621: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is DOWN
*Sep 21 07:07:45.216: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.1 (Tunnel0) is down: interface down
*Sep 21 07:07:45.217: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:07:45.316: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:07:47.217: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:07:47.217: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:07:51.467: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:07:51.478: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is UP
*Sep 21 07:07:51.567: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:07:53.466: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:07:53.467: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
*Sep 21 07:07:58.460: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: NHRP Registration Failure(NHRP: no error)
```

**W3 是正 RT01**

```
interface Tunnel0
ip nhrp network-id 100
---
(応答なし)
```

- W3 是正後: 健全復帰 16s

## W4 hub の tunnel key なし(spoke は key あり)  (2026-09-21 07:11)

- == W4: hub の tunnel key なし(spoke は key あり)

**W4 注入 RT01**

```
interface Tunnel0
no tunnel key 100
---
(応答なし)
```

**W4 hub — RT01# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================
```

**W4 hub — RT01# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.6    QM_IDLE           1029 ACTIVE
203.0.113.2     198.51.100.2    QM_IDLE           1028 ACTIVE
203.0.113.2     198.51.100.10   QM_IDLE           1030 ACTIVE

IPv6 Crypto ISAKMP SA
```

**W4 hub — RT01# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```
   current_peer 198.51.100.10 port 500
    #pkts encaps: 0, #pkts encrypt: 0, #pkts digest: 0
    #pkts decaps: 25, #pkts decrypt: 25, #pkts verify: 25
        in use settings ={Transport, }
        in use settings ={Transport, }
   current_peer 198.51.100.6 port 500
    #pkts encaps: 0, #pkts encrypt: 0, #pkts digest: 0
    #pkts decaps: 26, #pkts decrypt: 26, #pkts verify: 26
        in use settings ={Transport, }
        in use settings ={Transport, }
   current_peer 198.51.100.2 port 500
    #pkts encaps: 0, #pkts encrypt: 0, #pkts digest: 0
    #pkts decaps: 25, #pkts decrypt: 25, #pkts verify: 25
        in use settings ={Transport, }
        in use settings ={Transport, }
```

**W4 hub — RT01# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.1      YES TFTP   up                    up
```

**W4 hub log — RT01 show logging**

```
*Sep 21 07:09:38.459: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:09:38.861: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.2 NBMA: 198.51.100.2 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:09:38.861: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is DOWN
*Sep 21 07:09:38.861: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:09:38.861: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is DOWN
*Sep 21 07:09:38.861: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:09:38.862: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is DOWN
*Sep 21 07:09:38.862: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.4 (Tunnel0) is down: interface down
*Sep 21 07:09:38.863: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.3 (Tunnel0) is down: interface down
*Sep 21 07:09:38.863: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.2 (Tunnel0) is down: interface down
*Sep 21 07:09:38.870: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:09:38.963: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:09:40.862: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:09:40.862: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:09:45.218: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:09:45.317: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:09:45.766: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is UP
*Sep 21 07:09:46.339: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is UP
*Sep 21 07:09:47.053: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is UP
*Sep 21 07:09:47.218: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:09:47.218: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
```

**W4 RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:1, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 203.0.113.2          172.16.0.1  NHRP 00:01:11     S
```

**W4 RT02 — RT02# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.2    QM_IDLE           1013 ACTIVE

IPv6 Crypto ISAKMP SA
```

**W4 RT02 — RT02# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```
   current_peer 203.0.113.2 port 500
    #pkts encaps: 26, #pkts encrypt: 26, #pkts digest: 26
    #pkts decaps: 0, #pkts decrypt: 0, #pkts verify: 0
        in use settings ={Transport, }
        in use settings ={Transport, }
```

**W4 RT02 — RT02# show ip nhrp nhs detail**

```
Legend:	E=Expecting replies, R=Responding, W=Waiting, D=Dynamic
Tunnel0:
172.16.0.1   E  NBMA Address: 203.0.113.2 priority = 0 cluster = 0  req-sent 6  req-failed 0  repl-recv 0 (00:01:44 ago)


Pending Registration Requests:
Registration Request: Reqid 36, Ret 64  NHS 172.16.0.1 expired (Tu0)
```

**W4 RT02 — RT02# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.2      YES TFTP   up                    up
```

**W4 RT02 log — RT02 show logging**

```
*Sep 21 07:09:38.864: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is DOWN
*Sep 21 07:09:38.864: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:09:39.505: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.1 (Tunnel0) is down: interface down
*Sep 21 07:09:39.506: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:09:39.605: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:09:41.505: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:09:41.505: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:09:45.754: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:09:45.766: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is UP
*Sep 21 07:09:45.853: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:09:47.754: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:09:47.754: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
*Sep 21 07:09:52.931: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: NHRP Registration Failure(NHRP: no error)
```

**W4 是正 RT01**

```
interface Tunnel0
tunnel key 100
---
(応答なし)
```

- W4 是正後: 健全復帰 16s

## W5 hub が p2p GRE(tunnel mode gre ip + tunnel destination)  (2026-09-21 07:13)

- == W5: hub が p2p GRE(tunnel mode gre ip + tunnel destination)

**W5 注入 RT01**

```
interface Tunnel0
tunnel mode gre ip
tunnel destination 198.51.100.2
---
%WARNING: The tunnel mode has been modified while the tunnel protection is already active. It is recommended to run "shutdown" and "no shutdown" on Tunnel0 interface to refresh the config.
```

**W5 hub — RT01# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Hub, NHRP Peers:1, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 198.51.100.2         172.16.0.2    UP    never     D
```

**W5 hub — RT01# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
198.51.100.2    203.0.113.2     QM_IDLE           1038 ACTIVE
203.0.113.2     198.51.100.6    QM_IDLE           1036 ACTIVE
203.0.113.2     198.51.100.2    QM_IDLE           1035 ACTIVE
203.0.113.2     198.51.100.10   QM_IDLE           1037 ACTIVE

IPv6 Crypto ISAKMP SA
```

**W5 hub — RT01# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```
   current_peer 198.51.100.2 port 500
    #pkts encaps: 27, #pkts encrypt: 27, #pkts digest: 27
    #pkts decaps: 25, #pkts decrypt: 25, #pkts verify: 25
        in use settings ={Transport, }
        in use settings ={Transport, }
        in use settings ={Transport, }
        in use settings ={Transport, }
```

**W5 hub — RT01# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.1      YES TFTP   up                    up
```

**W5 hub log — RT01 show logging**

```
*Sep 21 07:11:33.621: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.2 NBMA: 198.51.100.2 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:11:33.621: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is DOWN
*Sep 21 07:11:33.621: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:11:33.621: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is DOWN
*Sep 21 07:11:33.621: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:11:33.621: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is DOWN
*Sep 21 07:11:33.621: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:11:33.622: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.3 (Tunnel0) is down: interface down
*Sep 21 07:11:33.622: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.4 (Tunnel0) is down: interface down
*Sep 21 07:11:33.622: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.2 (Tunnel0) is down: interface down
*Sep 21 07:11:33.738: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is UP
*Sep 21 07:11:33.738: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:11:33.741: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 07:11:33.821: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:11:34.224: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is DOWN
*Sep 21 07:11:34.225: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:11:34.324: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:11:36.224: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:11:36.224: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:11:40.368: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:11:40.468: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:11:41.122: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is UP
*Sep 21 07:11:41.122: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:11:42.013: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 07:11:44.448: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.2 (Tunnel0) is up: new adjacency
```

**W5 RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:1, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 203.0.113.2          172.16.0.1    UP 00:01:17     S
```

**W5 RT02 — RT02# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.2    QM_IDLE           1016 ACTIVE
198.51.100.2    203.0.113.2     QM_IDLE           1017 ACTIVE

IPv6 Crypto ISAKMP SA
```

**W5 RT02 — RT02# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```
   current_peer 203.0.113.2 port 500
    #pkts encaps: 25, #pkts encrypt: 25, #pkts digest: 25
    #pkts decaps: 28, #pkts decrypt: 28, #pkts verify: 28
        in use settings ={Transport, }
        in use settings ={Transport, }
        in use settings ={Transport, }
        in use settings ={Transport, }
```

**W5 RT02 — RT02# show ip nhrp nhs detail**

```
Legend:	E=Expecting replies, R=Responding, W=Waiting, D=Dynamic
Tunnel0:
172.16.0.1  RE  NBMA Address: 203.0.113.2 priority = 0 cluster = 0  req-sent 1  req-failed 0  repl-recv 1 (00:01:17 ago)
```

**W5 RT02 — RT02# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.2      YES TFTP   up                    up
```

**W5 RT02 log — RT02 show logging**

```
*Sep 21 07:11:33.624: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is DOWN
*Sep 21 07:11:33.624: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:11:33.739: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is UP
*Sep 21 07:11:33.742: %DMVPN-5-NHRP_NHS_UP: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is  UP
*Sep 21 07:11:34.226: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is DOWN
*Sep 21 07:11:34.226: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:11:34.966: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.1 (Tunnel0) is down: interface down
*Sep 21 07:11:34.966: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:11:35.166: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:11:36.965: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:11:36.965: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:11:41.109: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:11:41.121: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is UP
*Sep 21 07:11:41.310: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:11:42.014: %DMVPN-5-NHRP_NHS_UP: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is  UP
*Sep 21 07:11:43.109: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:11:43.109: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
*Sep 21 07:11:44.451: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.1 (Tunnel0) is up: new adjacency
```

**W5 是正 RT01**

```
interface Tunnel0
no tunnel destination
tunnel mode gre multipoint
---
%WARNING: The tunnel mode has been modified while the tunnel protection is already active. It is recommended to run "shutdown" and "no shutdown" on Tunnel0 interface to refresh the config.
```

- W5 是正後: 健全復帰 16s

## W6 hub の ip nhrp map multicast dynamic なし  (2026-09-21 07:15)

- == W6: hub の ip nhrp map multicast dynamic なし

**W6 注入 RT01**

```
interface Tunnel0
no ip nhrp map multicast dynamic
---
(応答なし)
```

**W6 hub — RT01# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Hub, NHRP Peers:3, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 198.51.100.2         172.16.0.2    UP 00:01:16     D
     1 198.51.100.6         172.16.0.3    UP 00:01:15     D
     1 198.51.100.10        172.16.0.4    UP 00:01:14     D
```

**W6 hub — RT01# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.6    QM_IDLE           1043 ACTIVE
203.0.113.2     198.51.100.2    QM_IDLE           1042 ACTIVE
203.0.113.2     198.51.100.10   QM_IDLE           1044 ACTIVE

IPv6 Crypto ISAKMP SA
```

**W6 hub — RT01# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```
   current_peer 198.51.100.10 port 500
    #pkts encaps: 19, #pkts encrypt: 19, #pkts digest: 19
    #pkts decaps: 19, #pkts decrypt: 19, #pkts verify: 19
        in use settings ={Transport, }
        in use settings ={Transport, }
   current_peer 198.51.100.6 port 500
    #pkts encaps: 19, #pkts encrypt: 19, #pkts digest: 19
    #pkts decaps: 20, #pkts decrypt: 20, #pkts verify: 20
        in use settings ={Transport, }
        in use settings ={Transport, }
   current_peer 198.51.100.2 port 500
    #pkts encaps: 20, #pkts encrypt: 20, #pkts digest: 20
    #pkts decaps: 20, #pkts decrypt: 20, #pkts verify: 20
        in use settings ={Transport, }
        in use settings ={Transport, }
```

**W6 hub — RT01# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.1      YES TFTP   up                    up
```

**W6 hub log — RT01 show logging**

```
*Sep 21 07:13:28.347: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:13:28.751: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.2 NBMA: 198.51.100.2 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:13:28.751: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is DOWN
*Sep 21 07:13:28.751: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:13:28.751: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is DOWN
*Sep 21 07:13:28.751: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:13:28.751: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is DOWN
*Sep 21 07:13:28.752: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.3 (Tunnel0) is down: interface down
*Sep 21 07:13:28.752: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.4 (Tunnel0) is down: interface down
*Sep 21 07:13:28.752: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.2 (Tunnel0) is down: interface down
*Sep 21 07:13:28.759: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:13:28.852: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:13:30.751: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:13:30.751: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:13:35.520: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:13:35.620: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:13:36.269: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is UP
*Sep 21 07:13:37.070: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 07:13:37.097: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is UP
*Sep 21 07:13:37.520: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:13:37.520: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
*Sep 21 07:13:37.903: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is UP
*Sep 21 07:13:38.021: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 07:13:38.667: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 07:13:38.789: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.2 (Tunnel0) is up: new adjacency
*Sep 21 07:13:39.381: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.3 (Tunnel0) is up: new adjacency
*Sep 21 07:13:40.202: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.4 (Tunnel0) is up: new adjacency
```

**W6 RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:1, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 203.0.113.2          172.16.0.1    UP 00:01:17     S
```

**W6 RT02 — RT02# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.2    QM_IDLE           1019 ACTIVE

IPv6 Crypto ISAKMP SA
```

**W6 RT02 — RT02# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```
   current_peer 203.0.113.2 port 500
    #pkts encaps: 20, #pkts encrypt: 20, #pkts digest: 20
    #pkts decaps: 20, #pkts decrypt: 20, #pkts verify: 20
        in use settings ={Transport, }
        in use settings ={Transport, }
```

**W6 RT02 — RT02# show ip nhrp nhs detail**

```
Legend:	E=Expecting replies, R=Responding, W=Waiting, D=Dynamic
Tunnel0:
172.16.0.1  RE  NBMA Address: 203.0.113.2 priority = 0 cluster = 0  req-sent 1  req-failed 0  repl-recv 1 (00:01:17 ago)
```

**W6 RT02 — RT02# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.2      YES TFTP   up                    up
```

**W6 RT02 log — RT02 show logging**

```
*Sep 21 07:13:28.754: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is DOWN
*Sep 21 07:13:28.754: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:13:29.500: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.1 (Tunnel0) is down: interface down
*Sep 21 07:13:29.501: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:13:29.701: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:13:31.499: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:13:31.499: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:13:36.257: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:13:36.269: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is UP
*Sep 21 07:13:36.457: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:13:37.071: %DMVPN-5-NHRP_NHS_UP: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is  UP
*Sep 21 07:13:38.256: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:13:38.257: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
```

**W6 是正 RT01**

```
interface Tunnel0
ip nhrp map multicast dynamic
---
(応答なし)
```

- W6 是正後: 健全復帰 16s

## W7 RT02 の crypto isakmp key なし  (2026-09-21 07:17)

- == W7: RT02 の crypto isakmp key なし

**W7 注入 RT02**

```
no crypto isakmp key CCNPKEY1 address 0.0.0.0
---
(応答なし)
```

**W7 hub — RT01# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Hub, NHRP Peers:2, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 198.51.100.6         172.16.0.3    UP 00:01:15     D
     1 198.51.100.10        172.16.0.4    UP 00:01:14     D
```

**W7 hub — RT01# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.6    QM_IDLE           1048 ACTIVE
203.0.113.2     198.51.100.10   QM_IDLE           1049 ACTIVE

IPv6 Crypto ISAKMP SA
```

**W7 hub — RT01# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```
   current_peer 198.51.100.10 port 500
    #pkts encaps: 28, #pkts encrypt: 28, #pkts digest: 28
    #pkts decaps: 27, #pkts decrypt: 27, #pkts verify: 27
        in use settings ={Transport, }
        in use settings ={Transport, }
   current_peer 198.51.100.6 port 500
    #pkts encaps: 28, #pkts encrypt: 28, #pkts digest: 28
    #pkts decaps: 28, #pkts decrypt: 28, #pkts verify: 28
        in use settings ={Transport, }
        in use settings ={Transport, }
```

**W7 hub — RT01# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.1      YES TFTP   up                    up
```

**W7 hub log — RT01 show logging**

```
*Sep 21 07:15:23.837: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.2 NBMA: 198.51.100.2 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:15:23.837: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is DOWN
*Sep 21 07:15:23.837: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:15:23.837: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is DOWN
*Sep 21 07:15:23.837: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:15:23.837: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is DOWN
*Sep 21 07:15:23.838: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.3 (Tunnel0) is down: interface down
*Sep 21 07:15:23.838: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.4 (Tunnel0) is down: interface down
*Sep 21 07:15:23.838: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.2 (Tunnel0) is down: interface down
*Sep 21 07:15:23.845: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:15:23.938: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:15:25.837: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:15:25.837: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:15:29.483: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:15:29.582: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:15:30.924: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is UP
*Sep 21 07:15:31.482: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:15:31.483: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
*Sep 21 07:15:31.629: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is UP
*Sep 21 07:15:31.831: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 07:15:32.444: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 07:15:33.035: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.3 (Tunnel0) is up: new adjacency
*Sep 21 07:15:34.481: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.4 (Tunnel0) is up: new adjacency
```

**W7 RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:1, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 203.0.113.2          172.16.0.1   IKE 00:01:11     S
```

**W7 RT02 — RT02# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status

IPv6 Crypto ISAKMP SA
```

**W7 RT02 — RT02# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```
   current_peer 203.0.113.2 port 500
    #pkts encaps: 0, #pkts encrypt: 0, #pkts digest: 0
    #pkts decaps: 0, #pkts decrypt: 0, #pkts verify: 0
```

**W7 RT02 — RT02# show ip nhrp nhs detail**

```
Legend:	E=Expecting replies, R=Responding, W=Waiting, D=Dynamic
Tunnel0:
172.16.0.1   E  NBMA Address: 203.0.113.2 priority = 0 cluster = 0  req-sent 6  req-failed 0  repl-recv 0 (00:01:43 ago)


Pending Registration Requests:
Registration Request: Reqid 60, Ret 64  NHS 172.16.0.1 expired (Tu0)
```

**W7 RT02 — RT02# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.2      YES TFTP   up                    up
```

**W7 RT02 log — RT02 show logging**

```
*Sep 21 07:15:23.460: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:15:23.846: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is DOWN
*Sep 21 07:15:23.846: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:15:24.366: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.1 (Tunnel0) is down: interface down
*Sep 21 07:15:24.367: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:15:24.466: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:15:26.367: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:15:26.367: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:15:30.123: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:15:30.324: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:15:32.122: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:15:32.122: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
*Sep 21 07:15:37.253: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: NHRP Registration Failure(NHRP: no error)
```

**W7 是正 RT02**

```
crypto isakmp key CCNPKEY1 address 0.0.0.0
---
(応答なし)
```

- W7 是正後: 健全復帰 16s

## W8 RT02 の tunnel protection なし(hub はあり)  (2026-09-21 07:19)

- == W8: RT02 の tunnel protection なし(hub はあり)

**W8 注入 RT02**

```
interface Tunnel0
no tunnel protection ipsec profile DMVPN-PROF
---
(応答なし)
```

**W8 hub — RT01# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Hub, NHRP Peers:2, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 198.51.100.6         172.16.0.3    UP 00:01:14     D
     1 198.51.100.10        172.16.0.4    UP 00:01:14     D
```

**W8 hub — RT01# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.6    QM_IDLE           1053 ACTIVE
203.0.113.2     198.51.100.10   QM_IDLE           1054 ACTIVE

IPv6 Crypto ISAKMP SA
```

**W8 hub — RT01# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```
   current_peer 198.51.100.10 port 500
    #pkts encaps: 29, #pkts encrypt: 29, #pkts digest: 29
    #pkts decaps: 27, #pkts decrypt: 27, #pkts verify: 27
        in use settings ={Transport, }
        in use settings ={Transport, }
   current_peer 198.51.100.6 port 500
    #pkts encaps: 27, #pkts encrypt: 27, #pkts digest: 27
    #pkts decaps: 27, #pkts decrypt: 27, #pkts verify: 27
        in use settings ={Transport, }
        in use settings ={Transport, }
```

**W8 hub — RT01# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.1      YES TFTP   up                    up
```

**W8 hub log — RT01 show logging**

```
*Sep 21 07:17:17.701: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is DOWN
*Sep 21 07:17:17.707: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.2 NBMA: 198.51.100.2 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:17:18.037: %CRYPTO-4-RECVD_PKT_NOT_IPSEC: Rec'd packet not an IPSEC packet. (ip) vrf/dest_addr= /203.0.113.2, src_addr= 198.51.100.2, prot= 47
*Sep 21 07:17:18.263: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:17:18.263: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is DOWN
*Sep 21 07:17:18.263: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:17:18.264: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is DOWN
*Sep 21 07:17:18.265: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.4 (Tunnel0) is down: interface down
*Sep 21 07:17:18.265: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.3 (Tunnel0) is down: interface down
*Sep 21 07:17:18.265: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.2 (Tunnel0) is down: interface down
*Sep 21 07:17:18.266: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:17:18.364: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:17:20.264: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:17:20.264: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:17:24.524: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:17:24.615: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:17:25.700: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is UP
*Sep 21 07:17:26.175: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is UP
*Sep 21 07:17:26.515: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:17:26.515: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
*Sep 21 07:17:26.532: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 07:17:27.135: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 07:17:27.807: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.3 (Tunnel0) is up: new adjacency
*Sep 21 07:17:28.922: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.4 (Tunnel0) is up: new adjacency
*Sep 21 07:18:19.217: %CRYPTO-4-RECVD_PKT_NOT_IPSEC: Rec'd packet not an IPSEC packet. (ip) vrf/dest_addr= /203.0.113.2, src_addr= 198.51.100.2, prot= 47
```

**W8 RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:1, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 203.0.113.2          172.16.0.1  NHRP 00:01:10     S
```

**W8 RT02 — RT02# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status

IPv6 Crypto ISAKMP SA
```

**W8 RT02 — RT02# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```

```

**W8 RT02 — RT02# show ip nhrp nhs detail**

```
Legend:	E=Expecting replies, R=Responding, W=Waiting, D=Dynamic
Tunnel0:
172.16.0.1   E  NBMA Address: 203.0.113.2 priority = 0 cluster = 0  req-sent 6  req-failed 0  repl-recv 0 (00:01:44 ago)


Pending Registration Requests:
Registration Request: Reqid 65, Ret 64  NHS 172.16.0.1 expired (Tu0)
```

**W8 RT02 — RT02# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.2      YES TFTP   up                    up
```

**W8 RT02 log — RT02 show logging**

```
*Sep 21 07:17:17.700: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is DOWN
*Sep 21 07:17:17.700: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:17:17.799: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:17:18.908: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:17:18.909: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.1 (Tunnel0) is down: interface down
*Sep 21 07:17:19.008: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:17:20.909: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:17:20.909: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:17:25.253: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:17:27.153: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:17:27.153: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
*Sep 21 07:17:32.438: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: NHRP Registration Failure(NHRP: no error)
```

**W8 是正 RT02**

```
interface Tunnel0
tunnel protection ipsec profile DMVPN-PROF
---
(応答なし)
```

- W8 是正後: 健全復帰 16s

## W9 RT02 の ip nhrp network-id なし  (2026-09-21 07:21)

- == W9: RT02 の ip nhrp network-id なし

**W9 注入 RT02**

```
interface Tunnel0
no ip nhrp network-id 100
---
(応答なし)
```

**W9 hub — RT01# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Hub, NHRP Peers:2, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 198.51.100.6         172.16.0.3    UP 00:01:15     D
     1 198.51.100.10        172.16.0.4    UP 00:01:14     D
```

**W9 hub — RT01# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.6    QM_IDLE           1059 ACTIVE
203.0.113.2     198.51.100.10   QM_IDLE           1060 ACTIVE

IPv6 Crypto ISAKMP SA
```

**W9 hub — RT01# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```
   current_peer 198.51.100.10 port 500
    #pkts encaps: 28, #pkts encrypt: 28, #pkts digest: 28
    #pkts decaps: 26, #pkts decrypt: 26, #pkts verify: 26
        in use settings ={Transport, }
        in use settings ={Transport, }
   current_peer 198.51.100.6 port 500
    #pkts encaps: 29, #pkts encrypt: 29, #pkts digest: 29
    #pkts decaps: 27, #pkts decrypt: 27, #pkts verify: 27
        in use settings ={Transport, }
        in use settings ={Transport, }
```

**W9 hub — RT01# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.1      YES TFTP   up                    up
```

**W9 hub log — RT01 show logging**

```
*Sep 21 07:19:13.189: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is DOWN
*Sep 21 07:19:13.195: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.2 NBMA: 198.51.100.2 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:19:13.692: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:19:13.692: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is DOWN
*Sep 21 07:19:13.692: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:19:13.692: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is DOWN
*Sep 21 07:19:13.693: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.4 (Tunnel0) is down: interface down
*Sep 21 07:19:13.693: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.2 (Tunnel0) is down: interface down
*Sep 21 07:19:13.693: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.3 (Tunnel0) is down: interface down
*Sep 21 07:19:13.694: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:19:13.894: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:19:15.692: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:19:15.693: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:19:20.143: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:19:20.244: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:19:21.381: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is UP
*Sep 21 07:19:22.081: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is UP
*Sep 21 07:19:22.143: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:19:22.143: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
*Sep 21 07:19:22.370: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 07:19:22.865: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 07:19:24.291: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.3 (Tunnel0) is up: new adjacency
*Sep 21 07:19:24.295: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.4 (Tunnel0) is up: new adjacency
```

**W9 RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================
```

**W9 RT02 — RT02# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status

IPv6 Crypto ISAKMP SA
```

**W9 RT02 — RT02# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```

```

**W9 RT02 — RT02# show ip nhrp nhs detail**

```

```

**W9 RT02 — RT02# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.2      YES TFTP   up                    up
```

**W9 RT02 log — RT02 show logging**

```
*Sep 21 07:19:13.186: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: administratively prohibited(NHRP: no error)
*Sep 21 07:19:13.187: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is DOWN
*Sep 21 07:19:13.187: %DMVPN-5-NHRP_NETID_UNCONFIGURED:  Tunnel0: NETID : 100 Unconfigured (Tunnel: 172.16.0.2 NBMA:  198.51.100.2)
*Sep 21 07:19:13.286: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:19:14.295: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:19:14.295: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.1 (Tunnel0) is down: interface down
*Sep 21 07:19:14.396: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:19:16.294: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:19:16.294: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:19:20.647: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:19:20.747: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:19:22.646: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:19:22.646: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
```

**W9 是正 RT02**

```
interface Tunnel0
ip nhrp network-id 100
---
(応答なし)
```

- W9 是正後: 健全復帰 16s

## W10 RT02 の tunnel key なし(hub はあり)  (2026-09-21 07:23)

- == W10: RT02 の tunnel key なし(hub はあり)

**W10 注入 RT02**

```
interface Tunnel0
no tunnel key 100
---
(応答なし)
```

**W10 hub — RT01# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Hub, NHRP Peers:2, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 198.51.100.6         172.16.0.3    UP 00:01:15     D
     1 198.51.100.10        172.16.0.4    UP 00:01:14     D
```

**W10 hub — RT01# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.6    QM_IDLE           1066 ACTIVE
203.0.113.2     198.51.100.2    QM_IDLE           1065 ACTIVE
203.0.113.2     198.51.100.10   QM_IDLE           1067 ACTIVE

IPv6 Crypto ISAKMP SA
```

**W10 hub — RT01# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```
   current_peer 198.51.100.10 port 500
    #pkts encaps: 28, #pkts encrypt: 28, #pkts digest: 28
    #pkts decaps: 26, #pkts decrypt: 26, #pkts verify: 26
        in use settings ={Transport, }
        in use settings ={Transport, }
   current_peer 198.51.100.6 port 500
    #pkts encaps: 29, #pkts encrypt: 29, #pkts digest: 29
    #pkts decaps: 26, #pkts decrypt: 26, #pkts verify: 26
        in use settings ={Transport, }
        in use settings ={Transport, }
   current_peer 198.51.100.2 port 500
    #pkts encaps: 0, #pkts encrypt: 0, #pkts digest: 0
    #pkts decaps: 25, #pkts decrypt: 25, #pkts verify: 25
        in use settings ={Transport, }
        in use settings ={Transport, }
```

**W10 hub — RT01# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.1      YES TFTP   up                    up
```

**W10 hub log — RT01 show logging**

```
*Sep 21 07:21:09.155: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.2 NBMA: 198.51.100.2 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:21:09.155: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is DOWN
*Sep 21 07:21:09.155: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:21:09.155: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is DOWN
*Sep 21 07:21:09.155: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:21:09.156: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is DOWN
*Sep 21 07:21:09.156: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.2 (Tunnel0) is down: interface down
*Sep 21 07:21:09.156: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.4 (Tunnel0) is down: interface down
*Sep 21 07:21:09.157: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.3 (Tunnel0) is down: interface down
*Sep 21 07:21:09.163: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:21:09.255: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:21:11.156: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:21:11.156: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:21:15.506: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:21:15.706: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:21:16.163: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is UP
*Sep 21 07:21:16.850: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is UP
*Sep 21 07:21:17.505: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:21:17.506: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
*Sep 21 07:21:17.557: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is UP
*Sep 21 07:21:17.690: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 07:21:18.373: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 07:21:19.321: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.3 (Tunnel0) is up: new adjacency
*Sep 21 07:21:20.300: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.4 (Tunnel0) is up: new adjacency
```

**W10 RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:1, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 203.0.113.2          172.16.0.1  NHRP 00:01:10     S
```

**W10 RT02 — RT02# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.2    QM_IDLE           1026 ACTIVE

IPv6 Crypto ISAKMP SA
```

**W10 RT02 — RT02# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```
   current_peer 203.0.113.2 port 500
    #pkts encaps: 26, #pkts encrypt: 26, #pkts digest: 26
    #pkts decaps: 0, #pkts decrypt: 0, #pkts verify: 0
        in use settings ={Transport, }
        in use settings ={Transport, }
```

**W10 RT02 — RT02# show ip nhrp nhs detail**

```
Legend:	E=Expecting replies, R=Responding, W=Waiting, D=Dynamic
Tunnel0:
172.16.0.1   E  NBMA Address: 203.0.113.2 priority = 0 cluster = 0  req-sent 6  req-failed 0  repl-recv 0 (00:01:44 ago)


Pending Registration Requests:
Registration Request: Reqid 80, Ret 64  NHS 172.16.0.1 expired (Tu0)
```

**W10 RT02 — RT02# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.2      YES TFTP   up                    up
```

**W10 RT02 log — RT02 show logging**

```
*Sep 21 07:21:08.489: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:21:09.158: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is DOWN
*Sep 21 07:21:09.158: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:21:09.697: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.1 (Tunnel0) is down: interface down
*Sep 21 07:21:09.697: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:21:09.796: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:21:11.696: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:21:11.696: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:21:16.151: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:21:16.163: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is UP
*Sep 21 07:21:16.251: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:21:18.151: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:21:18.151: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
*Sep 21 07:21:23.687: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: NHRP Registration Failure(NHRP: no error)
```

**W10 是正 RT02**

```
interface Tunnel0
tunnel key 100
---
(応答なし)
```

- W10 是正後: 健全復帰 16s

## F1 RT02 の transform-set 不一致(esp-3des esp-sha-hmac)  (2026-09-21 07:25)

- == F1: RT02 の transform-set 不一致(esp-3des esp-sha-hmac)

**F1 注入 RT02**

```
crypto ipsec transform-set TS esp-3des esp-sha-hmac
mode transport
exit
---
% Invalid input detected at '^' marker.
% Invalid input detected at '^' marker.
```

**F1 hub — RT01# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Hub, NHRP Peers:3, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 198.51.100.2         172.16.0.2    UP 00:01:16     D
     1 198.51.100.6         172.16.0.3    UP 00:01:15     D
     1 198.51.100.10        172.16.0.4    UP 00:01:14     D
```

**F1 hub — RT01# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.6    QM_IDLE           1072 ACTIVE
203.0.113.2     198.51.100.2    QM_IDLE           1071 ACTIVE
203.0.113.2     198.51.100.10   QM_IDLE           1073 ACTIVE

IPv6 Crypto ISAKMP SA
```

**F1 hub — RT01# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```
   current_peer 198.51.100.10 port 500
    #pkts encaps: 30, #pkts encrypt: 30, #pkts digest: 30
    #pkts decaps: 27, #pkts decrypt: 27, #pkts verify: 27
        in use settings ={Transport, }
        in use settings ={Transport, }
   current_peer 198.51.100.6 port 500
    #pkts encaps: 30, #pkts encrypt: 30, #pkts digest: 30
    #pkts decaps: 27, #pkts decrypt: 27, #pkts verify: 27
        in use settings ={Transport, }
        in use settings ={Transport, }
   current_peer 198.51.100.2 port 500
    #pkts encaps: 32, #pkts encrypt: 32, #pkts digest: 32
    #pkts decaps: 29, #pkts decrypt: 29, #pkts verify: 29
        in use settings ={Transport, }
        in use settings ={Transport, }
```

**F1 hub — RT01# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.1      YES TFTP   up                    up
```

**F1 hub log — RT01 show logging**

```
*Sep 21 07:23:07.576: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.2 NBMA: 198.51.100.2 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:23:07.576: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is DOWN
*Sep 21 07:23:07.576: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:23:07.576: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is DOWN
*Sep 21 07:23:07.576: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:23:07.576: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is DOWN
*Sep 21 07:23:07.577: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.4 (Tunnel0) is down: interface down
*Sep 21 07:23:07.577: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.3 (Tunnel0) is down: interface down
*Sep 21 07:23:07.577: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.2 (Tunnel0) is down: interface down
*Sep 21 07:23:07.585: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:23:07.665: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:23:09.576: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:23:09.576: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:23:14.336: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:23:14.435: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:23:15.084: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is UP
*Sep 21 07:23:15.851: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 07:23:15.899: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is UP
*Sep 21 07:23:16.335: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:23:16.335: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
*Sep 21 07:23:16.577: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is UP
*Sep 21 07:23:16.750: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 07:23:17.383: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 07:23:18.184: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.2 (Tunnel0) is up: new adjacency
*Sep 21 07:23:18.189: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.3 (Tunnel0) is up: new adjacency
*Sep 21 07:23:19.192: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.4 (Tunnel0) is up: new adjacency
```

**F1 RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:1, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 203.0.113.2          172.16.0.1    UP 00:01:17     S
```

**F1 RT02 — RT02# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.2    QM_IDLE           1028 ACTIVE

IPv6 Crypto ISAKMP SA
```

**F1 RT02 — RT02# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```
   current_peer 203.0.113.2 port 500
    #pkts encaps: 29, #pkts encrypt: 29, #pkts digest: 29
    #pkts decaps: 33, #pkts decrypt: 33, #pkts verify: 33
        in use settings ={Transport, }
        in use settings ={Transport, }
```

**F1 RT02 — RT02# show ip nhrp nhs detail**

```
Legend:	E=Expecting replies, R=Responding, W=Waiting, D=Dynamic
Tunnel0:
172.16.0.1  RE  NBMA Address: 203.0.113.2 priority = 0 cluster = 0  req-sent 1  req-failed 0  repl-recv 1 (00:01:17 ago)
```

**F1 RT02 — RT02# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.2      YES TFTP   up                    up
```

**F1 RT02 log — RT02 show logging**

```
*Sep 21 07:23:04.089: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:23:07.579: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is DOWN
*Sep 21 07:23:07.579: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:23:08.324: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.1 (Tunnel0) is down: interface down
*Sep 21 07:23:08.324: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:23:08.524: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:23:10.323: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:23:10.323: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:23:15.072: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:23:15.084: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is UP
*Sep 21 07:23:15.272: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:23:15.851: %DMVPN-5-NHRP_NHS_UP: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is  UP
*Sep 21 07:23:17.071: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:23:17.072: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
*Sep 21 07:23:18.187: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.1 (Tunnel0) is up: new adjacency
```

**F1 是正 RT02**

```
crypto ipsec transform-set TS esp-aes 256 esp-sha256-hmac
mode transport
exit
---
(応答なし)
```

- F1 是正後: 健全復帰 16s

## F2 hub の外側 IF で ESP だけ遮断(UDP 500 は許可)  (2026-09-21 07:26)

- == F2: hub の外側 IF で ESP だけ遮断(UDP 500 は許可)

**F2 注入 RT01**

```
ip access-list extended OUTSIDE-IN
deny esp any any
permit ip any any
exit
interface Ethernet0/0
ip access-group OUTSIDE-IN in
---
(応答なし)
```

**F2 hub — RT01# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================
```

**F2 hub — RT01# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.6    QM_IDLE           1078 ACTIVE
203.0.113.2     198.51.100.2    QM_IDLE           1077 ACTIVE
203.0.113.2     198.51.100.10   QM_IDLE           1079 ACTIVE

IPv6 Crypto ISAKMP SA
```

**F2 hub — RT01# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```
   current_peer 198.51.100.10 port 500
    #pkts encaps: 0, #pkts encrypt: 0, #pkts digest: 0
    #pkts decaps: 0, #pkts decrypt: 0, #pkts verify: 0
        in use settings ={Transport, }
        in use settings ={Transport, }
   current_peer 198.51.100.6 port 500
    #pkts encaps: 0, #pkts encrypt: 0, #pkts digest: 0
    #pkts decaps: 0, #pkts decrypt: 0, #pkts verify: 0
        in use settings ={Transport, }
        in use settings ={Transport, }
   current_peer 198.51.100.2 port 500
    #pkts encaps: 0, #pkts encrypt: 0, #pkts digest: 0
    #pkts decaps: 0, #pkts decrypt: 0, #pkts verify: 0
        in use settings ={Transport, }
        in use settings ={Transport, }
```

**F2 hub — RT01# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.1      YES TFTP   up                    up
```

**F2 hub log — RT01 show logging**

```
*Sep 21 07:25:04.655: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:25:05.057: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.2 NBMA: 198.51.100.2 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:25:05.058: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is DOWN
*Sep 21 07:25:05.058: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:25:05.058: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is DOWN
*Sep 21 07:25:05.058: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:25:05.058: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is DOWN
*Sep 21 07:25:05.059: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.4 (Tunnel0) is down: interface down
*Sep 21 07:25:05.059: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.3 (Tunnel0) is down: interface down
*Sep 21 07:25:05.059: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.2 (Tunnel0) is down: interface down
*Sep 21 07:25:05.066: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:25:05.158: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:25:07.058: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:25:07.058: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:25:11.521: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:25:11.620: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:25:12.209: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is UP
*Sep 21 07:25:12.915: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is UP
*Sep 21 07:25:13.521: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:25:13.521: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
*Sep 21 07:25:13.544: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is UP
```

**F2 RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:1, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 203.0.113.2          172.16.0.1  NHRP 00:01:10     S
```

**F2 RT02 — RT02# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.2    QM_IDLE           1030 ACTIVE

IPv6 Crypto ISAKMP SA
```

**F2 RT02 — RT02# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```
   current_peer 203.0.113.2 port 500
    #pkts encaps: 26, #pkts encrypt: 26, #pkts digest: 26
    #pkts decaps: 0, #pkts decrypt: 0, #pkts verify: 0
        in use settings ={Transport, }
        in use settings ={Transport, }
```

**F2 RT02 — RT02# show ip nhrp nhs detail**

```
Legend:	E=Expecting replies, R=Responding, W=Waiting, D=Dynamic
Tunnel0:
172.16.0.1   E  NBMA Address: 203.0.113.2 priority = 0 cluster = 0  req-sent 6  req-failed 0  repl-recv 0 (00:01:45 ago)


Pending Registration Requests:
Registration Request: Reqid 95, Ret 64  NHS 172.16.0.1 expired (Tu0)
```

**F2 RT02 — RT02# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.2      YES TFTP   up                    up
```

**F2 RT02 log — RT02 show logging**

```
*Sep 21 07:25:05.061: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is DOWN
*Sep 21 07:25:05.061: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:25:05.731: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.1 (Tunnel0) is down: interface down
*Sep 21 07:25:05.731: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:25:05.931: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:25:07.730: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:25:07.730: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:25:12.196: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:25:12.208: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is UP
*Sep 21 07:25:12.397: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:25:14.196: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:25:14.196: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
*Sep 21 07:25:19.497: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: NHRP Registration Failure(NHRP: no error)
```

**F2 是正 RT01**

```
interface Ethernet0/0
no ip access-group OUTSIDE-IN in
exit
no ip access-list extended OUTSIDE-IN
---
(応答なし)
```

- F2 是正後: 健全復帰 16s

## F3 RT02 の NHRP 認証不一致  (2026-09-21 07:28)

- == F3: RT02 の NHRP 認証不一致

**F3 注入 RT02**

```
interface Tunnel0
ip nhrp authentication NHRPKEX
---
(応答なし)
```

**F3 hub — RT01# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Hub, NHRP Peers:3, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 UNKNOWN              172.16.0.2   IKE    never    IX
     1 198.51.100.6         172.16.0.3    UP 00:01:14     D
     1 198.51.100.10        172.16.0.4    UP 00:01:14     D
```

**F3 hub — RT01# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.6    QM_IDLE           1084 ACTIVE
203.0.113.2     198.51.100.2    QM_IDLE           1083 ACTIVE
203.0.113.2     198.51.100.10   QM_IDLE           1085 ACTIVE

IPv6 Crypto ISAKMP SA
```

**F3 hub — RT01# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```
   current_peer 198.51.100.10 port 500
    #pkts encaps: 28, #pkts encrypt: 28, #pkts digest: 28
    #pkts decaps: 28, #pkts decrypt: 28, #pkts verify: 28
        in use settings ={Transport, }
        in use settings ={Transport, }
   current_peer 198.51.100.6 port 500
    #pkts encaps: 28, #pkts encrypt: 28, #pkts digest: 28
    #pkts decaps: 28, #pkts decrypt: 28, #pkts verify: 28
        in use settings ={Transport, }
        in use settings ={Transport, }
   current_peer 198.51.100.2 port 500
    #pkts encaps: 0, #pkts encrypt: 0, #pkts digest: 0
    #pkts decaps: 25, #pkts decrypt: 25, #pkts verify: 25
        in use settings ={Transport, }
        in use settings ={Transport, }
```

**F3 hub — RT01# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.1      YES TFTP   up                    up
```

**F3 hub log — RT01 show logging**

```
*Sep 21 07:27:01.649: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.2 NBMA: 198.51.100.2 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:27:01.649: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is DOWN
*Sep 21 07:27:01.649: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:27:01.649: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is DOWN
*Sep 21 07:27:01.650: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:27:01.650: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is DOWN
*Sep 21 07:27:01.651: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.4 (Tunnel0) is down: interface down
*Sep 21 07:27:01.651: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.3 (Tunnel0) is down: interface down
*Sep 21 07:27:01.651: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.2 (Tunnel0) is down: interface down
*Sep 21 07:27:01.658: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:27:01.852: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:27:03.650: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:27:03.650: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:27:07.904: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:27:08.104: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:27:08.612: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is UP
*Sep 21 07:27:09.111: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is UP
*Sep 21 07:27:09.587: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is UP
*Sep 21 07:27:09.904: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:27:09.904: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
*Sep 21 07:27:09.920: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 07:27:10.353: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 07:27:10.471: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: Recieved wrong authentication string for  Registration Request , Reason:  authentication failure (11) on (Tunnel: 172.16.0.2 NBMA: 203.0.113.2)
*Sep 21 07:27:10.600: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: Recieved wrong authentication string for  Registration Request , Reason:  authentication failure (11) on (Tunnel: 172.16.0.2 NBMA: 203.0.113.2)
*Sep 21 07:27:11.660: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.2 (Tunnel0) is up: new adjacency
*Sep 21 07:27:11.664: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.4 (Tunnel0) is up: new adjacency
*Sep 21 07:27:11.664: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.3 (Tunnel0) is up: new adjacency
*Sep 21 07:27:11.672: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Resolution Request , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
*Sep 21 07:27:12.399: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: Recieved wrong authentication string for  Registration Request , Reason:  authentication failure (11) on (Tunnel: 172.16.0.2 NBMA: 203.0.113.2)
*Sep 21 07:27:13.284: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Resolution Request , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
*Sep 21 07:27:15.446: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: Recieved wrong authentication string for  Registration Request , Reason:  authentication failure (11) on (Tunnel: 172.16.0.2 NBMA: 203.0.113.2)
*Sep 21 07:27:17.144: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Resolution Request , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
*Sep 21 07:27:22.126: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: Recieved wrong authentication string for  Registration Request , Reason:  authentication failure (11) on (Tunnel: 172.16.0.2 NBMA: 203.0.113.2)
*Sep 21 07:27:23.805: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Resolution Request , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
*Sep 21 07:27:35.226: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: Recieved wrong authentication string for  Registration Request , Reason:  authentication failure (11) on (Tunnel: 172.16.0.2 NBMA: 203.0.113.2)
*Sep 21 07:27:37.374: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Resolution Request , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
*Sep 21 07:28:04.094: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: Recieved wrong authentication string for  Registration Request , Reason:  authentication failure (11) on (Tunnel: 172.16.0.2 NBMA: 203.0.113.2)
*Sep 21 07:28:04.532: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Resolution Request , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
```

**F3 RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:1, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 203.0.113.2          172.16.0.1  NHRP 00:01:11     S
```

**F3 RT02 — RT02# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.2    QM_IDLE           1032 ACTIVE

IPv6 Crypto ISAKMP SA
```

**F3 RT02 — RT02# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```
   current_peer 203.0.113.2 port 500
    #pkts encaps: 26, #pkts encrypt: 26, #pkts digest: 26
    #pkts decaps: 0, #pkts decrypt: 0, #pkts verify: 0
        in use settings ={Transport, }
        in use settings ={Transport, }
```

**F3 RT02 — RT02# show ip nhrp nhs detail**

```
Legend:	E=Expecting replies, R=Responding, W=Waiting, D=Dynamic
Tunnel0:
172.16.0.1   E  NBMA Address: 203.0.113.2 priority = 0 cluster = 0  req-sent 6  req-failed 0  repl-recv 0 (00:01:44 ago)


Pending Registration Requests:
Registration Request: Reqid 102, Ret 64  NHS 172.16.0.1 expired (Tu0)
```

**F3 RT02 — RT02# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.2      YES TFTP   up                    up
```

**F3 RT02 log — RT02 show logging**

```
*Sep 21 07:27:01.030: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:27:01.652: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is DOWN
*Sep 21 07:27:01.652: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:27:02.348: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.1 (Tunnel0) is down: interface down
*Sep 21 07:27:02.348: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:27:02.447: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:27:04.347: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:27:04.348: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:27:08.599: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:27:08.611: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is UP
*Sep 21 07:27:08.699: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:27:10.599: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:27:10.599: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
*Sep 21 07:27:15.445: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: NHRP Registration Failure(NHRP: no error)
```

**F3 是正 RT02**

```
interface Tunnel0
ip nhrp authentication NHRPKEY
---
(応答なし)
```

- F3 是正後: 健全復帰 16s

## F4 RT02 の NHS トンネル IP 誤り(172.16.0.254)  (2026-09-21 07:30)

- == F4: RT02 の NHS トンネル IP 誤り(172.16.0.254)

**F4 注入 RT02**

```
interface Tunnel0
no ip nhrp nhs 172.16.0.1 nbma 203.0.113.2 multicast
ip nhrp nhs 172.16.0.254 nbma 203.0.113.2 multicast
---
(応答なし)
```

**F4 hub — RT01# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Hub, NHRP Peers:3, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 UNKNOWN              172.16.0.2   IKE    never    IX
     1 198.51.100.6         172.16.0.3    UP 00:01:14     D
     1 198.51.100.10        172.16.0.4    UP 00:01:14     D
```

**F4 hub — RT01# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.6    QM_IDLE           1091 ACTIVE
203.0.113.2     198.51.100.2    QM_IDLE           1090 ACTIVE
203.0.113.2     198.51.100.10   QM_IDLE           1092 ACTIVE

IPv6 Crypto ISAKMP SA
```

**F4 hub — RT01# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```
   current_peer 198.51.100.10 port 500
    #pkts encaps: 28, #pkts encrypt: 28, #pkts digest: 28
    #pkts decaps: 26, #pkts decrypt: 26, #pkts verify: 26
        in use settings ={Transport, }
        in use settings ={Transport, }
   current_peer 198.51.100.6 port 500
    #pkts encaps: 30, #pkts encrypt: 30, #pkts digest: 30
    #pkts decaps: 27, #pkts decrypt: 27, #pkts verify: 27
        in use settings ={Transport, }
        in use settings ={Transport, }
   current_peer 198.51.100.2 port 500
    #pkts encaps: 0, #pkts encrypt: 0, #pkts digest: 0
    #pkts decaps: 25, #pkts decrypt: 25, #pkts verify: 25
        in use settings ={Transport, }
        in use settings ={Transport, }
```

**F4 hub — RT01# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.1      YES TFTP   up                    up
```

**F4 hub log — RT01 show logging**

```
*Sep 21 07:28:55.814: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is DOWN
*Sep 21 07:28:55.820: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.2 NBMA: 198.51.100.2 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:28:55.925: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is UP
*Sep 21 07:28:55.926: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Registration Request , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
*Sep 21 07:28:55.926: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Error Indication , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
*Sep 21 07:28:56.424: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:28:56.424: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is DOWN
*Sep 21 07:28:56.424: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:28:56.424: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is DOWN
*Sep 21 07:28:56.425: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is DOWN
*Sep 21 07:28:56.425: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.4 (Tunnel0) is down: interface down
*Sep 21 07:28:56.425: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.2 (Tunnel0) is down: interface down
*Sep 21 07:28:56.425: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.3 (Tunnel0) is down: interface down
*Sep 21 07:28:56.427: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:28:56.621: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:28:58.425: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:28:58.425: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:29:02.878: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:29:03.073: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:29:03.691: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is UP
*Sep 21 07:29:04.278: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is UP
*Sep 21 07:29:04.792: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is UP
*Sep 21 07:29:04.872: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:29:04.872: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
*Sep 21 07:29:05.124: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 07:29:05.447: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Registration Request , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
*Sep 21 07:29:05.447: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Error Indication , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
*Sep 21 07:29:05.680: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Registration Request , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
*Sep 21 07:29:05.680: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Error Indication , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
*Sep 21 07:29:05.774: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 07:29:06.199: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.2 (Tunnel0) is up: new adjacency
*Sep 21 07:29:06.211: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Resolution Request , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
*Sep 21 07:29:06.795: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.3 (Tunnel0) is up: new adjacency
*Sep 21 07:29:06.799: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.4 (Tunnel0) is up: new adjacency
*Sep 21 07:29:07.189: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Registration Request , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
*Sep 21 07:29:07.189: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Error Indication , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
*Sep 21 07:29:08.089: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Resolution Request , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
*Sep 21 07:29:10.604: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Registration Request , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
*Sep 21 07:29:10.604: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Error Indication , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
*Sep 21 07:29:11.946: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Resolution Request , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
*Sep 21 07:29:16.760: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Registration Request , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
*Sep 21 07:29:16.760: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Error Indication , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
*Sep 21 07:29:19.833: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Resolution Request , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
*Sep 21 07:29:29.449: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Registration Request , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
*Sep 21 07:29:29.449: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Error Indication , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
*Sep 21 07:29:33.095: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Resolution Request , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
*Sep 21 07:29:58.440: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Resolution Request , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
*Sep 21 07:30:01.097: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Registration Request , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
*Sep 21 07:30:01.097: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Error Indication , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
```

**F4 RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:1, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 203.0.113.2        172.16.0.254  NHRP 00:01:11     S
```

**F4 RT02 — RT02# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.2    QM_IDLE           1035 ACTIVE

IPv6 Crypto ISAKMP SA
```

**F4 RT02 — RT02# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```
   current_peer 203.0.113.2 port 500
    #pkts encaps: 26, #pkts encrypt: 26, #pkts digest: 26
    #pkts decaps: 0, #pkts decrypt: 0, #pkts verify: 0
        in use settings ={Transport, }
        in use settings ={Transport, }
```

**F4 RT02 — RT02# show ip nhrp nhs detail**

```
Legend:	E=Expecting replies, R=Responding, W=Waiting, D=Dynamic
Tunnel0:
172.16.0.254   E  NBMA Address: 203.0.113.2 priority = 0 cluster = 0  req-sent 6  req-failed 0  repl-recv 0 


Pending Registration Requests:
Registration Request: Reqid 109, Ret 64  NHS 172.16.0.254 expired (Tu0)
```

**F4 RT02 — RT02# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.2      YES TFTP   up                    up
```

**F4 RT02 log — RT02 show logging**

```
*Sep 21 07:28:55.812: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: administratively prohibited(NHRP: no error)
*Sep 21 07:28:55.812: %DMVPN-5-NHRP_NHP_UP: Tunnel0: Next Hop NHP : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is UP
*Sep 21 07:28:55.812: %DMVPN-5-NHRP_NHP_DOWN: Tunnel0: Next Hop Peer : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: administratively prohibited(NHRP: no error)
*Sep 21 07:28:55.812: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is DOWN
*Sep 21 07:28:55.913: %DMVPN-5-NHRP_NHP_UP: Tunnel0: Next Hop NHP : (Tunnel: 172.16.0.254 NBMA: 203.0.113.2) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is UP
*Sep 21 07:28:55.913: %DMVPN-5-NHRP_NHP_DOWN: Tunnel0: Next Hop Peer : (Tunnel: 172.16.0.254 NBMA: 203.0.113.2) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: administratively prohibited(NHRP: no error)
*Sep 21 07:28:55.924: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is UP
*Sep 21 07:28:56.013: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:28:56.436: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is DOWN
*Sep 21 07:28:56.436: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.254 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:28:57.123: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.1 (Tunnel0) is down: interface down
*Sep 21 07:28:57.124: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:28:57.222: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:28:59.124: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:28:59.124: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:29:03.679: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:29:03.691: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is UP
*Sep 21 07:29:03.879: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:29:05.678: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:29:05.679: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
*Sep 21 07:29:10.603: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.254 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: NHRP Registration Failure(NHRP: no error)
```

**F4 是正 RT02**

```
interface Tunnel0
no ip nhrp nhs 172.16.0.254 nbma 203.0.113.2 multicast
ip nhrp nhs 172.16.0.1 nbma 203.0.113.2 multicast
---
(応答なし)
```

- F4 是正後: 健全復帰 16s

## F5 RT02 が nhs を持たず static map だけ(spoke に hub が static で見える)  (2026-09-21 07:32)

- == F5: RT02 が nhs を持たず static map だけ(spoke に hub が static で見える)

**F5 注入 RT02**

```
interface Tunnel0
no ip nhrp nhs 172.16.0.1 nbma 203.0.113.2 multicast
ip nhrp map 172.16.0.1 203.0.113.2
ip nhrp map multicast 203.0.113.2
---
(応答なし)
```

**F5 hub — RT01# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Hub, NHRP Peers:3, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 UNKNOWN              172.16.0.2   IKE    never    IX
     1 198.51.100.6         172.16.0.3    UP 00:01:15     D
     1 198.51.100.10        172.16.0.4    UP 00:01:14     D
```

**F5 hub — RT01# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.6    QM_IDLE           1099 ACTIVE
203.0.113.2     198.51.100.2    QM_IDLE           1098 ACTIVE
203.0.113.2     198.51.100.10   QM_IDLE           1100 ACTIVE

IPv6 Crypto ISAKMP SA
```

**F5 hub — RT01# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```
   current_peer 198.51.100.10 port 500
    #pkts encaps: 28, #pkts encrypt: 28, #pkts digest: 28
    #pkts decaps: 26, #pkts decrypt: 26, #pkts verify: 26
        in use settings ={Transport, }
        in use settings ={Transport, }
   current_peer 198.51.100.6 port 500
    #pkts encaps: 30, #pkts encrypt: 30, #pkts digest: 30
    #pkts decaps: 28, #pkts decrypt: 28, #pkts verify: 28
        in use settings ={Transport, }
        in use settings ={Transport, }
   current_peer 198.51.100.2 port 500
    #pkts encaps: 0, #pkts encrypt: 0, #pkts digest: 0
    #pkts decaps: 16, #pkts decrypt: 16, #pkts verify: 16
        in use settings ={Transport, }
        in use settings ={Transport, }
```

**F5 hub — RT01# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.1      YES TFTP   up                    up
```

**F5 hub log — RT01 show logging**

```
*Sep 21 07:30:50.286: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is DOWN
*Sep 21 07:30:50.292: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.2 NBMA: 198.51.100.2 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:30:50.396: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is UP
*Sep 21 07:30:51.166: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:30:51.167: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is DOWN
*Sep 21 07:30:51.167: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:30:51.167: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is DOWN
*Sep 21 07:30:51.167: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is DOWN
*Sep 21 07:30:51.168: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.4 (Tunnel0) is down: interface down
*Sep 21 07:30:51.168: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.3 (Tunnel0) is down: interface down
*Sep 21 07:30:51.168: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.2 (Tunnel0) is down: interface down
*Sep 21 07:30:51.169: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:30:51.267: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:30:53.168: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:30:53.168: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:30:57.643: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:30:57.743: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:30:58.361: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is UP
*Sep 21 07:30:59.066: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is UP
*Sep 21 07:30:59.588: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is UP
*Sep 21 07:30:59.643: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:30:59.643: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
*Sep 21 07:30:59.933: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 07:31:00.443: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 07:31:00.658: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.2 (Tunnel0) is up: new adjacency
*Sep 21 07:31:00.671: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Resolution Request , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
*Sep 21 07:31:01.800: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.3 (Tunnel0) is up: new adjacency
*Sep 21 07:31:01.804: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.4 (Tunnel0) is up: new adjacency
*Sep 21 07:31:02.345: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Resolution Request , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
*Sep 21 07:31:05.924: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Resolution Request , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
*Sep 21 07:31:13.671: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Resolution Request , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
*Sep 21 07:31:28.468: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Resolution Request , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
*Sep 21 07:31:54.291: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Resolution Request , Reason:  protocol generic error (7) on (Tunnel: 172.16.0.1 NBMA: 203.0.113.2)
```

**F5 RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:1, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 203.0.113.2          172.16.0.1  NHRP    never     S
```

**F5 RT02 — RT02# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.2    QM_IDLE           1039 ACTIVE

IPv6 Crypto ISAKMP SA
```

**F5 RT02 — RT02# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```
   current_peer 203.0.113.2 port 500
    #pkts encaps: 17, #pkts encrypt: 17, #pkts digest: 17
    #pkts decaps: 0, #pkts decrypt: 0, #pkts verify: 0
        in use settings ={Transport, }
        in use settings ={Transport, }
```

**F5 RT02 — RT02# show ip nhrp nhs detail**

```

```

**F5 RT02 — RT02# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.2      YES TFTP   up                    up
```

**F5 RT02 log — RT02 show logging**

```
*Sep 21 07:30:50.284: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: administratively prohibited(NHRP: no error)
*Sep 21 07:30:50.284: %DMVPN-5-NHRP_NHP_UP: Tunnel0: Next Hop NHP : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is UP
*Sep 21 07:30:50.284: %DMVPN-5-NHRP_NHP_DOWN: Tunnel0: Next Hop Peer : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: administratively prohibited(NHRP: no error)
*Sep 21 07:30:50.284: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is DOWN
*Sep 21 07:30:50.384: %DMVPN-5-NHRP_NHP_UP: Tunnel0: Next Hop NHP : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is UP
*Sep 21 07:30:50.395: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is UP
*Sep 21 07:30:50.585: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:30:51.179: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is DOWN
*Sep 21 07:30:51.897: %DMVPN-5-NHRP_NHP_DOWN: Tunnel0: Next Hop Peer : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:30:51.898: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.1 (Tunnel0) is down: interface down
*Sep 21 07:30:51.899: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:30:51.998: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:30:53.898: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:30:53.898: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:30:58.348: %DMVPN-5-NHRP_NHP_UP: Tunnel0: Next Hop NHP : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is UP
*Sep 21 07:30:58.348: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:30:58.360: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is UP
*Sep 21 07:30:58.448: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:31:00.348: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:31:00.348: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
```

**F5 是正 RT02**

```
interface Tunnel0
no ip nhrp map 172.16.0.1 203.0.113.2
no ip nhrp map multicast 203.0.113.2
ip nhrp nhs 172.16.0.1 nbma 203.0.113.2 multicast
---
(応答なし)
```

- F5 是正後: 健全復帰 16s

## F6 hub の PFS 片側要求(set pfs group14)  (2026-09-21 07:34)

- == F6: hub の PFS 片側要求(set pfs group14)

**F6 注入 RT01**

```
crypto ipsec profile DMVPN-PROF
set pfs group14
exit
---
(応答なし)
```

**F6 hub — RT01# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================
```

**F6 hub — RT01# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.6    QM_IDLE           1006 ACTIVE
203.0.113.2     198.51.100.2    QM_IDLE           1005 ACTIVE
203.0.113.2     198.51.100.10   QM_IDLE           1007 ACTIVE

IPv6 Crypto ISAKMP SA
```

**F6 hub — RT01# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```

```

**F6 hub — RT01# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.1      YES TFTP   up                    up
```

**F6 hub log — RT01 show logging**

```
*Sep 21 07:32:47.108: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:32:47.815: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.2 NBMA: 198.51.100.2 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:32:47.815: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is DOWN
*Sep 21 07:32:47.815: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:32:47.815: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is DOWN
*Sep 21 07:32:47.815: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:32:47.816: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is DOWN
*Sep 21 07:32:47.816: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.4 (Tunnel0) is down: interface down
*Sep 21 07:32:47.816: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.3 (Tunnel0) is down: interface down
*Sep 21 07:32:47.817: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.2 (Tunnel0) is down: interface down
*Sep 21 07:32:47.824: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:32:48.016: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:32:49.817: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:32:49.817: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:32:54.071: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:32:54.272: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:32:56.072: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:32:56.072: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
```

**F6 RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:1, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 203.0.113.2          172.16.0.1 IPSEC 00:01:10     S
```

**F6 RT02 — RT02# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.2    QM_IDLE           1042 ACTIVE

IPv6 Crypto ISAKMP SA
```

**F6 RT02 — RT02# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```
   current_peer 203.0.113.2 port 500
    #pkts encaps: 0, #pkts encrypt: 0, #pkts digest: 0
    #pkts decaps: 0, #pkts decrypt: 0, #pkts verify: 0
```

**F6 RT02 — RT02# show ip nhrp nhs detail**

```
Legend:	E=Expecting replies, R=Responding, W=Waiting, D=Dynamic
Tunnel0:
172.16.0.1   E  NBMA Address: 203.0.113.2 priority = 0 cluster = 0  req-sent 6  req-failed 0  repl-recv 0 (00:01:44 ago)


Pending Registration Requests:
Registration Request: Reqid 122, Ret 64  NHS 172.16.0.1 expired (Tu0)
```

**F6 RT02 — RT02# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.2      YES TFTP   up                    up
```

**F6 RT02 log — RT02 show logging**

```
*Sep 21 07:32:47.818: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is DOWN
*Sep 21 07:32:47.818: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:32:48.507: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.1 (Tunnel0) is down: interface down
*Sep 21 07:32:48.507: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:32:48.607: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:32:50.507: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:32:50.507: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:32:54.759: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:32:54.859: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:32:56.758: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:32:56.759: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
*Sep 21 07:33:02.041: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: NHRP Registration Failure(NHRP: no error)
```

**F6 是正 RT01**

```
crypto ipsec profile DMVPN-PROF
no set pfs
exit
---
(応答なし)
```

- F6 是正後: 健全復帰 16s

## F7 hub の mode gre ip(tunnel destination なし)  (2026-09-21 07:36)

- == F7: hub の mode gre ip(tunnel destination なし)

**F7 注入 RT01**

```
interface Tunnel0
tunnel mode gre ip
---
%WARNING: The tunnel mode has been modified while the tunnel protection is already active. It is recommended to run "shutdown" and "no shutdown" on Tunnel0 interface to refresh the config.
```

**F7 hub — RT01# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================
```

**F7 hub — RT01# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status

IPv6 Crypto ISAKMP SA
```

**F7 hub — RT01# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```

```

**F7 hub — RT01# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.1      YES TFTP   up                    down
```

**F7 hub log — RT01 show logging**

```
*Sep 21 07:34:42.651: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.2 NBMA: 198.51.100.2 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:34:42.651: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is DOWN
*Sep 21 07:34:42.651: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:34:42.651: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is DOWN
*Sep 21 07:34:42.651: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:34:42.651: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is DOWN
*Sep 21 07:34:42.651: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:34:42.652: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.4 (Tunnel0) is down: interface down
*Sep 21 07:34:42.652: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.3 (Tunnel0) is down: interface down
*Sep 21 07:34:42.653: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.2 (Tunnel0) is down: interface down
*Sep 21 07:34:42.819: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:34:43.223: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:34:43.324: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:34:45.224: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:34:49.372: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:34:51.272: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
```

**F7 RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:1, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 203.0.113.2          172.16.0.1   IKE 00:01:10     S
```

**F7 RT02 — RT02# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.2    MM_NO_STATE          0 ACTIVE
203.0.113.2     198.51.100.2    MM_NO_STATE          0 ACTIVE (deleted)

IPv6 Crypto ISAKMP SA
```

**F7 RT02 — RT02# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```
   current_peer 203.0.113.2 port 500
    #pkts encaps: 0, #pkts encrypt: 0, #pkts digest: 0
    #pkts decaps: 0, #pkts decrypt: 0, #pkts verify: 0
```

**F7 RT02 — RT02# show ip nhrp nhs detail**

```
Legend:	E=Expecting replies, R=Responding, W=Waiting, D=Dynamic
Tunnel0:
172.16.0.1   E  NBMA Address: 203.0.113.2 priority = 0 cluster = 0  req-sent 6  req-failed 0  repl-recv 0 (00:01:44 ago)


Pending Registration Requests:
Registration Request: Reqid 128, Ret 64  NHS 172.16.0.1 expired (Tu0)
```

**F7 RT02 — RT02# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.2      YES TFTP   up                    up
```

**F7 RT02 log — RT02 show logging**

```
*Sep 21 07:34:42.654: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is DOWN
*Sep 21 07:34:42.654: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:34:43.746: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.1 (Tunnel0) is down: interface down
*Sep 21 07:34:43.746: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:34:43.845: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:34:45.745: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:34:45.745: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:34:49.790: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:34:49.890: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:34:51.790: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:34:51.790: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
*Sep 21 07:34:57.427: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: NHRP Registration Failure(NHRP: no error)
```

**F7 是正 RT01**

```
interface Tunnel0
tunnel mode gre multipoint
---
%WARNING: The tunnel mode has been modified while the tunnel protection is already active. It is recommended to run "shutdown" and "no shutdown" on Tunnel0 interface to refresh the config.
```

- F7 是正後: 健全復帰 16s

## F8 hub の transform-set が mode tunnel(spoke は transport)  (2026-09-21 07:38)

- == F8: hub の transform-set が mode tunnel(spoke は transport)

**F8 注入 RT01**

```
crypto ipsec transform-set TS esp-aes 256 esp-sha256-hmac
mode tunnel
exit
---
(応答なし)
```

**F8 hub — RT01# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================
```

**F8 hub — RT01# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.6    QM_IDLE           1017 ACTIVE
203.0.113.2     198.51.100.2    QM_IDLE           1016 ACTIVE
203.0.113.2     198.51.100.10   QM_IDLE           1018 ACTIVE

IPv6 Crypto ISAKMP SA
```

**F8 hub — RT01# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```

```

**F8 hub — RT01# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.1      YES TFTP   up                    up
```

**F8 hub log — RT01 show logging**

```
*Sep 21 07:36:38.548: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:36:38.951: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.2 NBMA: 198.51.100.2 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:36:38.951: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is DOWN
*Sep 21 07:36:38.951: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:36:38.951: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is DOWN
*Sep 21 07:36:38.951: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:36:38.951: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is DOWN
*Sep 21 07:36:38.952: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.3 (Tunnel0) is down: interface down
*Sep 21 07:36:38.952: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.4 (Tunnel0) is down: interface down
*Sep 21 07:36:38.952: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.2 (Tunnel0) is down: interface down
*Sep 21 07:36:38.959: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:36:39.052: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:36:40.952: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:36:40.952: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:36:44.898: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:36:45.098: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:36:46.898: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:36:46.898: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
```

**F8 RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:1, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 203.0.113.2          172.16.0.1 IPSEC 00:01:11     S
```

**F8 RT02 — RT02# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.2    QM_IDLE           1045 ACTIVE

IPv6 Crypto ISAKMP SA
```

**F8 RT02 — RT02# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```
   current_peer 203.0.113.2 port 500
    #pkts encaps: 0, #pkts encrypt: 0, #pkts digest: 0
    #pkts decaps: 0, #pkts decrypt: 0, #pkts verify: 0
```

**F8 RT02 — RT02# show ip nhrp nhs detail**

```
Legend:	E=Expecting replies, R=Responding, W=Waiting, D=Dynamic
Tunnel0:
172.16.0.1   E  NBMA Address: 203.0.113.2 priority = 0 cluster = 0  req-sent 6  req-failed 0  repl-recv 0 (00:01:45 ago)


Pending Registration Requests:
Registration Request: Reqid 134, Ret 64  NHS 172.16.0.1 expired (Tu0)
```

**F8 RT02 — RT02# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.2      YES TFTP   up                    up
```

**F8 RT02 log — RT02 show logging**

```
*Sep 21 07:36:38.954: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is DOWN
*Sep 21 07:36:38.954: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:36:39.442: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.1 (Tunnel0) is down: interface down
*Sep 21 07:36:39.443: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:36:39.541: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:36:41.442: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:36:41.442: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:36:45.803: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:36:46.003: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:36:47.803: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:36:47.803: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
*Sep 21 07:36:53.215: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: NHRP Registration Failure(NHRP: no error)
```

**F8 是正 RT01**

```
crypto ipsec transform-set TS esp-aes 256 esp-sha256-hmac
mode transport
exit
---
(応答なし)
```

- F8 是正後: 健全復帰 16s

## F1b RT02 の transform-set 不一致(esp-aes 128 esp-sha-hmac)  (2026-09-21 07:42)

- == F1b: RT02 の transform-set 不一致(esp-aes 128 esp-sha-hmac)

**F1b 注入 RT02**

```
crypto ipsec transform-set TS esp-aes esp-sha-hmac
mode transport
exit
---
(応答なし)
```

**F1b hub — RT01# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Hub, NHRP Peers:2, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 198.51.100.6         172.16.0.3    UP 00:01:14     D
     1 198.51.100.10        172.16.0.4    UP 00:01:14     D
```

**F1b hub — RT01# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.6    QM_IDLE           1023 ACTIVE
203.0.113.2     198.51.100.2    QM_IDLE           1022 ACTIVE
203.0.113.2     198.51.100.10   QM_IDLE           1024 ACTIVE

IPv6 Crypto ISAKMP SA
```

**F1b hub — RT01# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```
   current_peer 198.51.100.10 port 500
    #pkts encaps: 28, #pkts encrypt: 28, #pkts digest: 28
    #pkts decaps: 26, #pkts decrypt: 26, #pkts verify: 26
        in use settings ={Transport, }
        in use settings ={Transport, }
   current_peer 198.51.100.6 port 500
    #pkts encaps: 29, #pkts encrypt: 29, #pkts digest: 29
    #pkts decaps: 27, #pkts decrypt: 27, #pkts verify: 27
        in use settings ={Transport, }
        in use settings ={Transport, }
```

**F1b hub — RT01# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.1      YES TFTP   up                    up
```

**F1b hub log — RT01 show logging**

```
*Sep 21 07:41:00.209: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.2 NBMA: 198.51.100.2 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:41:00.209: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is DOWN
*Sep 21 07:41:00.209: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:41:00.209: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is DOWN
*Sep 21 07:41:00.209: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:41:00.209: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is DOWN
*Sep 21 07:41:00.210: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.3 (Tunnel0) is down: interface down
*Sep 21 07:41:00.210: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.4 (Tunnel0) is down: interface down
*Sep 21 07:41:00.210: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.2 (Tunnel0) is down: interface down
*Sep 21 07:41:00.217: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:41:00.309: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:41:02.209: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:41:02.209: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:41:06.156: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:41:06.256: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:41:07.220: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is UP
*Sep 21 07:41:07.713: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is UP
*Sep 21 07:41:08.155: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:41:08.156: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
*Sep 21 07:41:08.205: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 07:41:08.677: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 07:41:11.160: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.3 (Tunnel0) is up: new adjacency
*Sep 21 07:41:11.164: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.4 (Tunnel0) is up: new adjacency
```

**F1b RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:1, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 203.0.113.2          172.16.0.1 IPSEC 00:01:10     S
```

**F1b RT02 — RT02# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.2    QM_IDLE           1047 ACTIVE

IPv6 Crypto ISAKMP SA
```

**F1b RT02 — RT02# show crypto ipsec sa | include peer|encaps|decaps|in use settings**

```
   current_peer 203.0.113.2 port 500
    #pkts encaps: 0, #pkts encrypt: 0, #pkts digest: 0
    #pkts decaps: 0, #pkts decrypt: 0, #pkts verify: 0
```

**F1b RT02 — RT02# show ip nhrp nhs detail**

```
Legend:	E=Expecting replies, R=Responding, W=Waiting, D=Dynamic
Tunnel0:
172.16.0.1   E  NBMA Address: 203.0.113.2 priority = 0 cluster = 0  req-sent 6  req-failed 0  repl-recv 0 (00:04:08 ago)


Pending Registration Requests:
Registration Request: Reqid 140, Ret 64  NHS 172.16.0.1 expired (Tu0)
```

**F1b RT02 — RT02# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.2      YES TFTP   up                    up
```

**F1b RT02 log — RT02 show logging**

```
*Sep 21 07:40:59.733: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:41:00.212: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is DOWN
*Sep 21 07:41:00.212: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:41:00.955: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.1 (Tunnel0) is down: interface down
*Sep 21 07:41:00.956: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:41:01.156: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:41:02.954: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:41:02.954: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:41:06.695: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:41:06.794: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:41:08.695: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:41:08.695: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
*Sep 21 07:41:14.142: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: NHRP Registration Failure(NHRP: no error)
```

**F1b 是正 RT02**

```
crypto ipsec transform-set TS esp-aes 256 esp-sha256-hmac
mode transport
exit
---
(応答なし)
```

- F1b 是正後: 健全復帰 16s

## P2 壊滅スタート→是正  (2026-09-21 07:44)

- == P2: 壊滅スタート → 是正(clear/bounce なし)

**P2 注入 RT01**

```
interface Tunnel0
no tunnel protection ipsec profile DMVPN-PROF
exit
no crypto ipsec profile DMVPN-PROF
interface Tunnel0
no ip nhrp network-id 100
no tunnel key 100
no ip nhrp map multicast dynamic
tunnel mode gre ip
tunnel destination 198.51.100.2
---
(応答なし)
```

**P2 注入 RT02**

```
no crypto isakmp key CCNPKEY1 address 0.0.0.0
---
(応答なし)
```

**P2 注入 RT03**

```
interface Tunnel0
no tunnel protection ipsec profile DMVPN-PROF
exit
no crypto ipsec profile DMVPN-PROF
---
(応答なし)
```

**P2 注入 RT04**

```
interface Tunnel0
no tunnel key 100
---
(応答なし)
```

**P2 壊滅 hub — RT01# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================
```

**P2 壊滅 RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:1, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 203.0.113.2          172.16.0.1   IKE 00:00:54     S
```

**P2 壊滅 RT03 — RT03# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:1, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 203.0.113.2          172.16.0.1  NHRP 00:00:54     S
```

**P2 壊滅 RT04 — RT04# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:1, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 203.0.113.2          172.16.0.1   IKE 00:00:54     S
```

**P2 是正 RT01**

```
crypto ipsec profile DMVPN-PROF
set transform-set TS
exit
interface Tunnel0
no tunnel destination
tunnel mode gre multipoint
tunnel key 100
ip nhrp network-id 100
ip nhrp map multicast dynamic
tunnel protection ipsec profile DMVPN-PROF
---
(応答なし)
```

**P2 是正 RT02**

```
crypto isakmp key CCNPKEY1 address 0.0.0.0
---
(応答なし)
```

**P2 是正 RT03**

```
crypto ipsec profile DMVPN-PROF
set transform-set TS
exit
interface Tunnel0
tunnel protection ipsec profile DMVPN-PROF
---
(応答なし)
```

**P2 是正 RT04**

```
interface Tunnel0
tunnel key 100
---
(応答なし)
```

**P2 是正直後 RT01 — RT01# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.1      YES TFTP   up                    up
```

**P2 是正直後 RT02 — RT02# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.2      YES TFTP   up                    up
```

**P2 是正直後 RT03 — RT03# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.3      YES TFTP   up                    up
```

**P2 是正直後 RT04 — RT04# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.4      YES TFTP   up                    up
```

- P2: 是正のみ(no shut なし)で 3 spoke UP まで 41s

**P2 是正後 hub show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Hub, NHRP Peers:3, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 198.51.100.2         172.16.0.2    UP 00:00:16     D
     1 198.51.100.6         172.16.0.3    UP 00:00:43     D
     1 198.51.100.10        172.16.0.4    UP 00:00:38     D
```

## P3a フルトンネル(素朴)  (2026-09-21 07:45)

- == P3a: 素朴な構成(spoke の static default を消し hub から EIGRP で default を受ける・NBMA は host route)

**P3a hub**

```
ip access-list standard NAT-SRC
permit 10.0.0.0 0.0.255.255
exit
ip nat inside source list NAT-SRC interface Ethernet0/0 overload
interface Ethernet0/0
ip nat outside
exit
interface Tunnel0
ip nat inside
exit
interface Loopback1
ip nat inside
exit
ip route 0.0.0.0 0.0.0.0 203.0.113.1
router eigrp 100
redistribute static metric 10000 100 255 1 1400
exit
---
(応答なし)
```

**P3a RT02**

```
no ip route 0.0.0.0 0.0.0.0 198.51.100.1
ip route 203.0.113.2 255.255.255.255 198.51.100.1
---
(応答なし)
```

**P3a RT03**

```
no ip route 0.0.0.0 0.0.0.0 198.51.100.5
ip route 203.0.113.2 255.255.255.255 198.51.100.5
---
(応答なし)
```

**P3a RT04**

```
no ip route 0.0.0.0 0.0.0.0 198.51.100.9
ip route 203.0.113.2 255.255.255.255 198.51.100.9
---
(応答なし)
```

**P3a RT02 — RT02# show ip route 0.0.0.0**

```
Routing entry for 0.0.0.0/0, supernet
  Known via "eigrp 100", distance 170, metric 26905600, candidate default path, precedence routine (0), type external
  Redistributing via eigrp 100
  Last update from 172.16.0.1 on Tunnel0, 00:00:42 ago
  Routing Descriptor Blocks:
  * 172.16.0.1, from 172.16.0.1, 00:00:42 ago, via Tunnel0
      Route metric is 26905600, traffic share count is 1
      Total delay is 51000 microseconds, minimum bandwidth is 100 Kbit
      Reliability 255/255, minimum MTU 1400 bytes
      Loading 1/255, Hops 1
```

**P3a RT02 LAN→internet — RT02# ping 8.8.8.8 repeat 5 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 8.8.8.8, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/2 ms
```

**P3a RT02→hub LAN — RT02# ping 10.0.0.1 repeat 5 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 10.0.0.1, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/2 ms
```

**P3a RT02→RT03 LAN(shortcut) — RT02# ping 10.0.3.1 repeat 5 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 10.0.3.1, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 2/2/2 ms
```

**P3a RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:1, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 203.0.113.2          172.16.0.1    UP 00:01:13     S
```

**P3a hub — RT01# show ip nat translations**

```
Pro Inside global         Inside local          Outside local         Outside global
icmp 203.0.113.2:1024     10.0.2.1:1            8.8.8.8:1             8.8.8.8:1024
```

**P3a hub — RT01# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Hub, NHRP Peers:3, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 198.51.100.2         172.16.0.2    UP 00:01:14     D
     1 198.51.100.6         172.16.0.3    UP 00:01:41     D
     1 198.51.100.10        172.16.0.4    UP 00:01:37     D
```

**P3a RT02 log — RT02 show logging**

```
*Sep 21 07:40:59.733: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:41:00.212: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is DOWN
*Sep 21 07:41:00.212: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:41:00.955: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.1 (Tunnel0) is down: interface down
*Sep 21 07:41:00.956: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:41:01.156: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:41:02.954: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:41:02.954: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:41:06.695: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:41:06.794: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:41:08.695: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:41:08.695: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
*Sep 21 07:41:14.142: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: NHRP Registration Failure(NHRP: no error)
*Sep 21 07:42:26.765: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:42:27.875: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:42:27.974: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:42:29.875: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:42:29.875: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:42:33.718: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:42:33.729: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is UP
*Sep 21 07:42:33.817: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:42:34.681: %DMVPN-5-NHRP_NHS_UP: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is  UP
*Sep 21 07:42:35.717: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:42:35.718: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
*Sep 21 07:42:36.867: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.1 (Tunnel0) is up: new adjacency
*Sep 21 07:42:50.931: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is DOWN
*Sep 21 07:42:50.931: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 07:42:52.266: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:42:54.387: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.1 (Tunnel0) is down: interface down
*Sep 21 07:42:54.387: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 07:42:54.486: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:42:56.387: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to down
*Sep 21 07:42:56.387: %LINK-5-CHANGED: Interface Tunnel0, changed state to administratively down
*Sep 21 07:43:00.141: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 07:43:00.241: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:43:02.141: %LINEPROTO-5-UPDOWN: Line protocol on Interface Tunnel0, changed state to up
*Sep 21 07:43:02.141: %LINK-5-UPDOWN: Interface Tunnel0, changed state to up
*Sep 21 07:43:07.435: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2 ) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is DOWN, Reason: NHRP Registration Failure(NHRP: no error)
*Sep 21 07:44:05.692: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 07:44:33.899: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 203.0.113.2 socket is UP
*Sep 21 07:44:33.902: %DMVPN-5-NHRP_NHS_UP: Tunnel0: Next Hop Server : (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is  UP
*Sep 21 07:44:35.853: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 172.16.0.1 (Tunnel0) is up: new adjacency
*Sep 21 07:44:54.237: %ADJ-5-PARENT: Midchain parent maintenance for IP midchain out of Tunnel0, addr 172.16.0.1 - looped chain attempting to stack
*Sep 21 07:44:54.639: %SYS-5-CONFIG_I: Configured from console by console
```

## P3b フルトンネル(NBMA 静的経路)  (2026-09-21 07:46)

- == P3b: spoke 間 NBMA を underlay の静的経路で補う

**P3b RT02**

```
ip route 198.51.100.0 255.255.255.0 198.51.100.1
---
(応答なし)
```

**P3b RT03**

```
ip route 198.51.100.0 255.255.255.0 198.51.100.5
---
(応答なし)
```

**P3b RT04**

```
ip route 198.51.100.0 255.255.255.0 198.51.100.9
---
(応答なし)
```

- P3b: 健全復帰 16s

**P3b RT02→RT03 LAN(shortcut) — RT02# ping 10.0.3.1 repeat 5 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 10.0.3.1, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/3 ms
```

**P3b RT02→RT03 LAN 2回目 — RT02# ping 10.0.3.1 repeat 5 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 10.0.3.1, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/2/3 ms
```

**P3b RT02 LAN→internet — RT02# ping 8.8.8.8 repeat 5 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 8.8.8.8, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/2 ms
```

**P3b RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:1, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 203.0.113.2          172.16.0.1    UP 00:00:27     S
```

## P3r 後片付け  (2026-09-21 07:46)

- P3r: 健全復帰 16s

## P3c フルトンネル時の shortcut 切り分け  (2026-09-21 07:49)

- P3c-0 基線: 健全復帰 16s

**P3c-0 基線(フルトンネル無し) RT02→RT03 LAN 1回目 — RT02# ping 10.0.3.1 repeat 10 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 10, 100-byte ICMP Echos to 10.0.3.1, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!!!!!!
Success rate is 100 percent (10/10), round-trip min/avg/max = 1/1/3 ms
```

**P3c-0 基線(フルトンネル無し) RT02→RT03 LAN 2回目 — RT02# ping 10.0.3.1 repeat 10 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 10, 100-byte ICMP Echos to 10.0.3.1, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!!!!!!
Success rate is 100 percent (10/10), round-trip min/avg/max = 1/1/3 ms
```

**P3c-0 基線(フルトンネル無し) RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:1, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 203.0.113.2          172.16.0.1    UP 00:00:22     S
```

**P3c-0 基線(フルトンネル無し) RT02 — RT02# show ip route 10.0.3.0**

```
Routing entry for 10.0.3.0/24
  Known via "eigrp 100", distance 90, metric 28288000, precedence routine (0), type internal
  Redistributing via eigrp 100
  Last update from 172.16.0.1 on Tunnel0, 00:00:19 ago
  Routing Descriptor Blocks:
  * 172.16.0.1, from 172.16.0.1, 00:00:19 ago, via Tunnel0
      Route metric is 28288000, traffic share count is 1
      Total delay is 105000 microseconds, minimum bandwidth is 100 Kbit
      Reliability 255/255, minimum MTU 1400 bytes
      Loading 2/255, Hops 2
```

**P3c-0 基線(フルトンネル無し) RT02 — RT02# show ip cef 10.0.3.1**

```
10.0.3.0/24
  nexthop 172.16.0.1 Tunnel0
```

**P3c-0 基線(フルトンネル無し) hub — RT01# show ip nhrp traffic**

```
Tunnel0: Max-send limit:10000Pkts/10Sec, Usage:0%
   Sent: Total 0
         0 Resolution Request  0 Resolution Reply  0 Registration Request  
         0 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress  
   Rcvd: Total 0
         0 Resolution Request  0 Resolution Reply  0 Registration Request  
         0 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress
```

**P3c-0 基線(フルトンネル無し) RT02 — RT02# show ip nhrp traffic**

```
Tunnel0: Max-send limit:10000Pkts/10Sec, Usage:0%
   Sent: Total 137
         0 Resolution Request  0 Resolution Reply  134 Registration Request  
         0 Registration Reply  3 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress  
   Rcvd: Total 48
         0 Resolution Request  0 Resolution Reply  0 Registration Request  
         48 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress
```

- P3c-0 基線(フルトンネル無し): RT02 に直接トンネル(DT) ★なし

**P3c-1 hub NAT inside on Tunnel0**

```
ip access-list standard NAT-SRC
permit 10.0.0.0 0.0.255.255
exit
ip nat inside source list NAT-SRC interface Ethernet0/0 overload
interface Ethernet0/0
ip nat outside
exit
interface Tunnel0
ip nat inside
exit
---
(応答なし)
```

**P3c-1 NAT inside on Tunnel0 のみ RT02→RT03 LAN 1回目 — RT02# ping 10.0.3.1 repeat 10 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 10, 100-byte ICMP Echos to 10.0.3.1, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!!!!!!
Success rate is 100 percent (10/10), round-trip min/avg/max = 1/1/2 ms
```

**P3c-1 NAT inside on Tunnel0 のみ RT02→RT03 LAN 2回目 — RT02# ping 10.0.3.1 repeat 10 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 10, 100-byte ICMP Echos to 10.0.3.1, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!!!!!!
Success rate is 100 percent (10/10), round-trip min/avg/max = 1/1/3 ms
```

**P3c-1 NAT inside on Tunnel0 のみ RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:1, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 203.0.113.2          172.16.0.1    UP 00:00:32     S
```

**P3c-1 NAT inside on Tunnel0 のみ RT02 — RT02# show ip route 10.0.3.0**

```
Routing entry for 10.0.3.0/24
  Known via "eigrp 100", distance 90, metric 28288000, precedence routine (0), type internal
  Redistributing via eigrp 100
  Last update from 172.16.0.1 on Tunnel0, 00:00:29 ago
  Routing Descriptor Blocks:
  * 172.16.0.1, from 172.16.0.1, 00:00:29 ago, via Tunnel0
      Route metric is 28288000, traffic share count is 1
      Total delay is 105000 microseconds, minimum bandwidth is 100 Kbit
      Reliability 255/255, minimum MTU 1400 bytes
      Loading 2/255, Hops 2
```

**P3c-1 NAT inside on Tunnel0 のみ RT02 — RT02# show ip cef 10.0.3.1**

```
10.0.3.0/24
  nexthop 172.16.0.1 Tunnel0
```

**P3c-1 NAT inside on Tunnel0 のみ hub — RT01# show ip nhrp traffic**

```
Tunnel0: Max-send limit:10000Pkts/10Sec, Usage:0%
   Sent: Total 0
         0 Resolution Request  0 Resolution Reply  0 Registration Request  
         0 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress  
   Rcvd: Total 0
         0 Resolution Request  0 Resolution Reply  0 Registration Request  
         0 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress
```

**P3c-1 NAT inside on Tunnel0 のみ RT02 — RT02# show ip nhrp traffic**

```
Tunnel0: Max-send limit:10000Pkts/10Sec, Usage:0%
   Sent: Total 137
         0 Resolution Request  0 Resolution Reply  134 Registration Request  
         0 Registration Reply  3 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress  
   Rcvd: Total 48
         0 Resolution Request  0 Resolution Reply  0 Registration Request  
         48 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress
```

- P3c-1 NAT inside on Tunnel0 のみ: RT02 に直接トンネル(DT) ★なし

**P3c-2 hub default を EIGRP へ**

```
interface Tunnel0
no ip nat inside
exit
interface Ethernet0/0
no ip nat outside
exit
no ip nat inside source list NAT-SRC interface Ethernet0/0 overload
ip route 0.0.0.0 0.0.0.0 203.0.113.1
router eigrp 100
redistribute static metric 10000 100 255 1 1400
exit
---
(応答なし)
```

**P3c-2 RT02**

```
no ip route 0.0.0.0 0.0.0.0 198.51.100.1
ip route 203.0.113.2 255.255.255.255 198.51.100.1
ip route 198.51.100.0 255.255.255.0 198.51.100.1
---
(応答なし)
```

**P3c-2 RT03**

```
no ip route 0.0.0.0 0.0.0.0 198.51.100.5
ip route 203.0.113.2 255.255.255.255 198.51.100.5
ip route 198.51.100.0 255.255.255.0 198.51.100.5
---
(応答なし)
```

**P3c-2 RT04**

```
no ip route 0.0.0.0 0.0.0.0 198.51.100.9
ip route 203.0.113.2 255.255.255.255 198.51.100.9
ip route 198.51.100.0 255.255.255.0 198.51.100.9
---
(応答なし)
```

**P3c-2 default via tunnel のみ(NAT なし) RT02→RT03 LAN 1回目 — RT02# ping 10.0.3.1 repeat 10 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 10, 100-byte ICMP Echos to 10.0.3.1, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!!!!!!
Success rate is 100 percent (10/10), round-trip min/avg/max = 1/1/3 ms
```

**P3c-2 default via tunnel のみ(NAT なし) RT02→RT03 LAN 2回目 — RT02# ping 10.0.3.1 repeat 10 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 10, 100-byte ICMP Echos to 10.0.3.1, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!!!!!!
Success rate is 100 percent (10/10), round-trip min/avg/max = 1/1/3 ms
```

**P3c-2 default via tunnel のみ(NAT なし) RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:1, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 203.0.113.2          172.16.0.1    UP 00:01:13     S
```

**P3c-2 default via tunnel のみ(NAT なし) RT02 — RT02# show ip route 10.0.3.0**

```
Routing entry for 10.0.3.0/24
  Known via "eigrp 100", distance 90, metric 28288000, precedence routine (0), type internal
  Redistributing via eigrp 100
  Last update from 172.16.0.1 on Tunnel0, 00:01:11 ago
  Routing Descriptor Blocks:
  * 172.16.0.1, from 172.16.0.1, 00:01:11 ago, via Tunnel0
      Route metric is 28288000, traffic share count is 1
      Total delay is 105000 microseconds, minimum bandwidth is 100 Kbit
      Reliability 255/255, minimum MTU 1400 bytes
      Loading 2/255, Hops 2
```

**P3c-2 default via tunnel のみ(NAT なし) RT02 — RT02# show ip cef 10.0.3.1**

```
10.0.3.0/24
  nexthop 172.16.0.1 Tunnel0
```

**P3c-2 default via tunnel のみ(NAT なし) hub — RT01# show ip nhrp traffic**

```
Tunnel0: Max-send limit:10000Pkts/10Sec, Usage:0%
   Sent: Total 0
         0 Resolution Request  0 Resolution Reply  0 Registration Request  
         0 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress  
   Rcvd: Total 0
         0 Resolution Request  0 Resolution Reply  0 Registration Request  
         0 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress
```

**P3c-2 default via tunnel のみ(NAT なし) RT02 — RT02# show ip nhrp traffic**

```
Tunnel0: Max-send limit:10000Pkts/10Sec, Usage:0%
   Sent: Total 137
         0 Resolution Request  0 Resolution Reply  134 Registration Request  
         0 Registration Reply  3 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress  
   Rcvd: Total 48
         0 Resolution Request  0 Resolution Reply  0 Registration Request  
         48 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress
```

- P3c-2 default via tunnel のみ(NAT なし): RT02 に直接トンネル(DT) ★なし

**P3c-3 NAT 戻し**

```
interface Tunnel0
ip nat inside
exit
interface Ethernet0/0
ip nat outside
exit
ip nat inside source list NAT-SRC interface Ethernet0/0 overload
---
(応答なし)
```

**P3c-3 両方 RT02→RT03 LAN 1回目 — RT02# ping 10.0.3.1 repeat 10 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 10, 100-byte ICMP Echos to 10.0.3.1, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!!!!!!
Success rate is 100 percent (10/10), round-trip min/avg/max = 1/2/3 ms
```

**P3c-3 両方 RT02→RT03 LAN 2回目 — RT02# ping 10.0.3.1 repeat 10 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 10, 100-byte ICMP Echos to 10.0.3.1, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!!!!!!
Success rate is 100 percent (10/10), round-trip min/avg/max = 1/1/3 ms
```

**P3c-3 両方 RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:1, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 203.0.113.2          172.16.0.1    UP 00:01:22     S
```

**P3c-3 両方 RT02 — RT02# show ip route 10.0.3.0**

```
Routing entry for 10.0.3.0/24
  Known via "eigrp 100", distance 90, metric 28288000, precedence routine (0), type internal
  Redistributing via eigrp 100
  Last update from 172.16.0.1 on Tunnel0, 00:01:19 ago
  Routing Descriptor Blocks:
  * 172.16.0.1, from 172.16.0.1, 00:01:19 ago, via Tunnel0
      Route metric is 28288000, traffic share count is 1
      Total delay is 105000 microseconds, minimum bandwidth is 100 Kbit
      Reliability 255/255, minimum MTU 1400 bytes
      Loading 2/255, Hops 2
```

**P3c-3 両方 RT02 — RT02# show ip cef 10.0.3.1**

```
10.0.3.0/24
  nexthop 172.16.0.1 Tunnel0
```

**P3c-3 両方 hub — RT01# show ip nhrp traffic**

```
Tunnel0: Max-send limit:10000Pkts/10Sec, Usage:0%
   Sent: Total 0
         0 Resolution Request  0 Resolution Reply  0 Registration Request  
         0 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress  
   Rcvd: Total 0
         0 Resolution Request  0 Resolution Reply  0 Registration Request  
         0 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress
```

**P3c-3 両方 RT02 — RT02# show ip nhrp traffic**

```
Tunnel0: Max-send limit:10000Pkts/10Sec, Usage:0%
   Sent: Total 137
         0 Resolution Request  0 Resolution Reply  134 Registration Request  
         0 Registration Reply  3 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress  
   Rcvd: Total 48
         0 Resolution Request  0 Resolution Reply  0 Registration Request  
         48 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress
```

- P3c-3 両方: RT02 に直接トンネル(DT) ★なし

**P3c-3 RT02→internet — RT02# ping 8.8.8.8 repeat 5 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 8.8.8.8, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/3 ms
```

## P3r 後片付け  (2026-09-21 07:49)

- P3r: 健全復帰 16s

## P3c フルトンネル時の shortcut 切り分け  (2026-09-21 08:03)

- P3c-0 基線: 健全復帰 16s

**P3c-0 基線(フルトンネル無し) RT02→RT03 LAN 1回目 — RT02# ping 10.0.3.1 repeat 10 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 10, 100-byte ICMP Echos to 10.0.3.1, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!!!!!!
Success rate is 100 percent (10/10), round-trip min/avg/max = 1/3/11 ms
```

**P3c-0 基線(フルトンネル無し) RT02→RT03 LAN 2回目 — RT02# ping 10.0.3.1 repeat 10 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 10, 100-byte ICMP Echos to 10.0.3.1, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!!!!!!
Success rate is 100 percent (10/10), round-trip min/avg/max = 1/1/2 ms
```

**P3c-0 基線(フルトンネル無し) RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:2, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     2 198.51.100.6         172.16.0.3    UP 00:00:05   DT2
                            172.16.0.3    UP 00:00:05   DT1
     1 203.0.113.2          172.16.0.1    UP 00:00:22     S
```

**P3c-0 基線(フルトンネル無し) RT02 — RT02# show ip route 10.0.3.0**

```
Routing entry for 10.0.3.0/24
  Known via "eigrp 100", distance 90, metric 28288000, precedence routine (0), type internal
  Redistributing via eigrp 100
  Last update from 172.16.0.1 on Tunnel0, 00:00:19 ago
  Routing Descriptor Blocks:
  * 172.16.0.1, from 172.16.0.1, 00:00:19 ago, via Tunnel0
      Route metric is 28288000, traffic share count is 1
      Total delay is 105000 microseconds, minimum bandwidth is 100 Kbit
      Reliability 255/255, minimum MTU 1400 bytes
      Loading 2/255, Hops 2
```

**P3c-0 基線(フルトンネル無し) RT02 — RT02# show ip cef 10.0.3.1**

```
10.0.3.0/24
  nexthop 172.16.0.3 Tunnel0
```

**P3c-0 基線(フルトンネル無し) hub — RT01# show ip nhrp traffic**

```
Tunnel0: Max-send limit:10000Pkts/10Sec, Usage:0%
   Sent: Total 4
         2 Resolution Request  0 Resolution Reply  0 Registration Request  
         0 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  2 Traffic Indication  0 Redirect Suppress  
   Rcvd: Total 2
         2 Resolution Request  0 Resolution Reply  0 Registration Request  
         0 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress
```

**P3c-0 基線(フルトンネル無し) RT02 — RT02# show ip nhrp traffic**

```
Tunnel0: Max-send limit:10000Pkts/10Sec, Usage:0%
   Sent: Total 19
         5 Resolution Request  5 Resolution Reply  9 Registration Request  
         0 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress  
   Rcvd: Total 22
         5 Resolution Request  5 Resolution Reply  0 Registration Request  
         7 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  5 Traffic Indication  0 Redirect Suppress
```

- P3c-0 基線(フルトンネル無し): RT02 に直接トンネル(DT) あり

**P3c-1 hub NAT inside on Tunnel0**

```
ip access-list standard NAT-SRC
permit 10.0.0.0 0.0.255.255
exit
ip nat inside source list NAT-SRC interface Ethernet0/0 overload
interface Ethernet0/0
ip nat outside
exit
interface Tunnel0
ip nat inside
exit
---
(応答なし)
```

**P3c-1 NAT inside on Tunnel0 のみ RT02→RT03 LAN 1回目 — RT02# ping 10.0.3.1 repeat 10 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 10, 100-byte ICMP Echos to 10.0.3.1, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!!!!!!
Success rate is 100 percent (10/10), round-trip min/avg/max = 2/3/5 ms
```

**P3c-1 NAT inside on Tunnel0 のみ RT02→RT03 LAN 2回目 — RT02# ping 10.0.3.1 repeat 10 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 10, 100-byte ICMP Echos to 10.0.3.1, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!!!!!!
Success rate is 100 percent (10/10), round-trip min/avg/max = 1/1/2 ms
```

**P3c-1 NAT inside on Tunnel0 のみ RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:2, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     2 198.51.100.6         172.16.0.3    UP 00:00:05   DT2
                            172.16.0.3    UP 00:00:05   DT1
     1 203.0.113.2          172.16.0.1    UP 00:00:33     S
```

**P3c-1 NAT inside on Tunnel0 のみ RT02 — RT02# show ip route 10.0.3.0**

```
Routing entry for 10.0.3.0/24
  Known via "eigrp 100", distance 90, metric 28288000, precedence routine (0), type internal
  Redistributing via eigrp 100
  Last update from 172.16.0.1 on Tunnel0, 00:00:30 ago
  Routing Descriptor Blocks:
  * 172.16.0.1, from 172.16.0.1, 00:00:30 ago, via Tunnel0
      Route metric is 28288000, traffic share count is 1
      Total delay is 105000 microseconds, minimum bandwidth is 100 Kbit
      Reliability 255/255, minimum MTU 1400 bytes
      Loading 2/255, Hops 2
```

**P3c-1 NAT inside on Tunnel0 のみ RT02 — RT02# show ip cef 10.0.3.1**

```
10.0.3.0/24
  nexthop 172.16.0.3 Tunnel0
```

**P3c-1 NAT inside on Tunnel0 のみ hub — RT01# show ip nhrp traffic**

```
Tunnel0: Max-send limit:10000Pkts/10Sec, Usage:0%
   Sent: Total 4
         2 Resolution Request  0 Resolution Reply  0 Registration Request  
         0 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  2 Traffic Indication  0 Redirect Suppress  
   Rcvd: Total 2
         2 Resolution Request  0 Resolution Reply  0 Registration Request  
         0 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress
```

**P3c-1 NAT inside on Tunnel0 のみ RT02 — RT02# show ip nhrp traffic**

```
Tunnel0: Max-send limit:10000Pkts/10Sec, Usage:0%
   Sent: Total 21
         6 Resolution Request  6 Resolution Reply  9 Registration Request  
         0 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress  
   Rcvd: Total 25
         6 Resolution Request  6 Resolution Reply  0 Registration Request  
         7 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  6 Traffic Indication  0 Redirect Suppress
```

- P3c-1 NAT inside on Tunnel0 のみ: RT02 に直接トンネル(DT) あり

**P3c-2 hub default を EIGRP へ**

```
interface Tunnel0
no ip nat inside
exit
interface Ethernet0/0
no ip nat outside
exit
no ip nat inside source list NAT-SRC interface Ethernet0/0 overload
ip route 0.0.0.0 0.0.0.0 203.0.113.1
router eigrp 100
redistribute static metric 10000 100 255 1 1400
exit
---
(応答なし)
```

**P3c-2 RT02**

```
no ip route 0.0.0.0 0.0.0.0 198.51.100.1
ip route 203.0.113.2 255.255.255.255 198.51.100.1
ip route 198.51.100.0 255.255.255.0 198.51.100.1
---
(応答なし)
```

**P3c-2 RT03**

```
no ip route 0.0.0.0 0.0.0.0 198.51.100.5
ip route 203.0.113.2 255.255.255.255 198.51.100.5
ip route 198.51.100.0 255.255.255.0 198.51.100.5
---
(応答なし)
```

**P3c-2 RT04**

```
no ip route 0.0.0.0 0.0.0.0 198.51.100.9
ip route 203.0.113.2 255.255.255.255 198.51.100.9
ip route 198.51.100.0 255.255.255.0 198.51.100.9
---
(応答なし)
```

**P3c-2 default via tunnel のみ(NAT なし) RT02→RT03 LAN 1回目 — RT02# ping 10.0.3.1 repeat 10 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 10, 100-byte ICMP Echos to 10.0.3.1, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!!!!!!
Success rate is 100 percent (10/10), round-trip min/avg/max = 1/2/7 ms
```

**P3c-2 default via tunnel のみ(NAT なし) RT02→RT03 LAN 2回目 — RT02# ping 10.0.3.1 repeat 10 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 10, 100-byte ICMP Echos to 10.0.3.1, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!!!!!!
Success rate is 100 percent (10/10), round-trip min/avg/max = 1/1/2 ms
```

**P3c-2 default via tunnel のみ(NAT なし) RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:2, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     2 198.51.100.6         172.16.0.3    UP 00:00:05   DT2
                            172.16.0.3    UP 00:00:05   DT1
     1 203.0.113.2          172.16.0.1    UP 00:01:16     S
```

**P3c-2 default via tunnel のみ(NAT なし) RT02 — RT02# show ip route 10.0.3.0**

```
Routing entry for 10.0.3.0/24
  Known via "eigrp 100", distance 90, metric 28288000, precedence routine (0), type internal
  Redistributing via eigrp 100
  Last update from 172.16.0.1 on Tunnel0, 00:01:13 ago
  Routing Descriptor Blocks:
  * 172.16.0.1, from 172.16.0.1, 00:01:13 ago, via Tunnel0
      Route metric is 28288000, traffic share count is 1
      Total delay is 105000 microseconds, minimum bandwidth is 100 Kbit
      Reliability 255/255, minimum MTU 1400 bytes
      Loading 2/255, Hops 2
```

**P3c-2 default via tunnel のみ(NAT なし) RT02 — RT02# show ip cef 10.0.3.1**

```
10.0.3.0/24
  nexthop 172.16.0.3 Tunnel0
```

**P3c-2 default via tunnel のみ(NAT なし) hub — RT01# show ip nhrp traffic**

```
Tunnel0: Max-send limit:10000Pkts/10Sec, Usage:0%
   Sent: Total 4
         2 Resolution Request  0 Resolution Reply  0 Registration Request  
         0 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  2 Traffic Indication  0 Redirect Suppress  
   Rcvd: Total 2
         2 Resolution Request  0 Resolution Reply  0 Registration Request  
         0 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress
```

**P3c-2 default via tunnel のみ(NAT なし) RT02 — RT02# show ip nhrp traffic**

```
Tunnel0: Max-send limit:10000Pkts/10Sec, Usage:0%
   Sent: Total 23
         7 Resolution Request  7 Resolution Reply  9 Registration Request  
         0 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress  
   Rcvd: Total 28
         7 Resolution Request  7 Resolution Reply  0 Registration Request  
         7 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  7 Traffic Indication  0 Redirect Suppress
```

- P3c-2 default via tunnel のみ(NAT なし): RT02 に直接トンネル(DT) あり

**P3c-3 NAT 戻し**

```
interface Tunnel0
ip nat inside
exit
interface Ethernet0/0
ip nat outside
exit
ip nat inside source list NAT-SRC interface Ethernet0/0 overload
---
(応答なし)
```

**P3c-3 両方 RT02→RT03 LAN 1回目 — RT02# ping 10.0.3.1 repeat 10 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 10, 100-byte ICMP Echos to 10.0.3.1, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!!!!!!
Success rate is 100 percent (10/10), round-trip min/avg/max = 1/2/10 ms
```

**P3c-3 両方 RT02→RT03 LAN 2回目 — RT02# ping 10.0.3.1 repeat 10 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 10, 100-byte ICMP Echos to 10.0.3.1, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!!!!!!
Success rate is 100 percent (10/10), round-trip min/avg/max = 1/1/1 ms
```

**P3c-3 両方 RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:2, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     2 198.51.100.6         172.16.0.3    UP 00:00:05   DT2
                            172.16.0.3    UP 00:00:05   DT1
     1 203.0.113.2          172.16.0.1    UP 00:01:26     S
```

**P3c-3 両方 RT02 — RT02# show ip route 10.0.3.0**

```
Routing entry for 10.0.3.0/24
  Known via "eigrp 100", distance 90, metric 28288000, precedence routine (0), type internal
  Redistributing via eigrp 100
  Last update from 172.16.0.1 on Tunnel0, 00:01:22 ago
  Routing Descriptor Blocks:
  * 172.16.0.1, from 172.16.0.1, 00:01:22 ago, via Tunnel0
      Route metric is 28288000, traffic share count is 1
      Total delay is 105000 microseconds, minimum bandwidth is 100 Kbit
      Reliability 255/255, minimum MTU 1400 bytes
      Loading 2/255, Hops 2
```

**P3c-3 両方 RT02 — RT02# show ip cef 10.0.3.1**

```
10.0.3.0/24
  nexthop 172.16.0.3 Tunnel0
```

**P3c-3 両方 hub — RT01# show ip nhrp traffic**

```
Tunnel0: Max-send limit:10000Pkts/10Sec, Usage:0%
   Sent: Total 4
         2 Resolution Request  0 Resolution Reply  0 Registration Request  
         0 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  2 Traffic Indication  0 Redirect Suppress  
   Rcvd: Total 2
         2 Resolution Request  0 Resolution Reply  0 Registration Request  
         0 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress
```

**P3c-3 両方 RT02 — RT02# show ip nhrp traffic**

```
Tunnel0: Max-send limit:10000Pkts/10Sec, Usage:0%
   Sent: Total 25
         8 Resolution Request  8 Resolution Reply  9 Registration Request  
         0 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress  
   Rcvd: Total 31
         8 Resolution Request  8 Resolution Reply  0 Registration Request  
         7 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  8 Traffic Indication  0 Redirect Suppress
```

- P3c-3 両方: RT02 に直接トンネル(DT) あり

**P3c-3 RT02→internet — RT02# ping 8.8.8.8 repeat 5 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 8.8.8.8, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/2 ms
```

## P3r 後片付け  (2026-09-21 08:04)

- P3r: 健全復帰 16s

## P3d 素朴なフルトンネル(他 spoke の NBMA が既定経路=トンネルへ再帰)  (2026-09-21 08:08)

- P3d-0: 健全復帰 16s

**P3d hub**

```
ip access-list standard NAT-SRC
permit 10.0.0.0 0.0.255.255
exit
ip nat inside source list NAT-SRC interface Ethernet0/0 overload
interface Ethernet0/0
ip nat outside
exit
interface Tunnel0
ip nat inside
exit
ip route 0.0.0.0 0.0.0.0 203.0.113.1
router eigrp 100
redistribute static metric 10000 100 255 1 1400
exit
---
(応答なし)
```

**P3d RT02**

```
no ip route 0.0.0.0 0.0.0.0 198.51.100.1
ip route 203.0.113.2 255.255.255.255 198.51.100.1
---
(応答なし)
```

**P3d RT03**

```
no ip route 0.0.0.0 0.0.0.0 198.51.100.5
ip route 203.0.113.2 255.255.255.255 198.51.100.5
---
(応答なし)
```

**P3d RT04**

```
no ip route 0.0.0.0 0.0.0.0 198.51.100.9
ip route 203.0.113.2 255.255.255.255 198.51.100.9
---
(応答なし)
```

**P3d RT02→internet — RT02# ping 8.8.8.8 repeat 5 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 8.8.8.8, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/2 ms
```

**P3d 素朴 RT02→RT03 LAN 1回目 — RT02# ping 10.0.3.1 repeat 10 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 10, 100-byte ICMP Echos to 10.0.3.1, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!!!!!!
Success rate is 100 percent (10/10), round-trip min/avg/max = 1/2/3 ms
```

**P3d 素朴 RT02→RT03 LAN 2回目 — RT02# ping 10.0.3.1 repeat 10 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 10, 100-byte ICMP Echos to 10.0.3.1, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!!!!!!
Success rate is 100 percent (10/10), round-trip min/avg/max = 1/1/2 ms
```

**P3d 素朴 RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:2, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     2 198.51.100.6         172.16.0.3    UP 00:00:05   DT2
                            172.16.0.3    UP 00:00:05   DT1
     1 203.0.113.2          172.16.0.1    UP 00:01:00     S
```

**P3d 素朴 RT02 — RT02# show ip route 10.0.3.0**

```
Routing entry for 10.0.3.0/24
  Known via "eigrp 100", distance 90, metric 28288000, precedence routine (0), type internal
  Redistributing via eigrp 100
  Last update from 172.16.0.1 on Tunnel0, 00:00:56 ago
  Routing Descriptor Blocks:
  * 172.16.0.1, from 172.16.0.1, 00:00:56 ago, via Tunnel0
      Route metric is 28288000, traffic share count is 1
      Total delay is 105000 microseconds, minimum bandwidth is 100 Kbit
      Reliability 255/255, minimum MTU 1400 bytes
      Loading 2/255, Hops 2
```

**P3d 素朴 RT02 — RT02# show ip cef 10.0.3.1**

```
10.0.3.0/24
  nexthop 172.16.0.3 Tunnel0
```

**P3d 素朴 hub — RT01# show ip nhrp traffic**

```
Tunnel0: Max-send limit:10000Pkts/10Sec, Usage:0%
   Sent: Total 4
         2 Resolution Request  0 Resolution Reply  0 Registration Request  
         0 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  2 Traffic Indication  0 Redirect Suppress  
   Rcvd: Total 2
         2 Resolution Request  0 Resolution Reply  0 Registration Request  
         0 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress
```

**P3d 素朴 RT02 — RT02# show ip nhrp traffic**

```
Tunnel0: Max-send limit:10000Pkts/10Sec, Usage:0%
   Sent: Total 33
         9 Resolution Request  9 Resolution Reply  15 Registration Request  
         0 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress  
   Rcvd: Total 40
         9 Resolution Request  9 Resolution Reply  0 Registration Request  
         13 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  9 Traffic Indication  0 Redirect Suppress
```

- P3d 素朴: RT02 に直接トンネル(DT) あり

**P3d 60 秒後 RT02→RT03 LAN — RT02# ping 10.0.3.1 repeat 20 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 20, 100-byte ICMP Echos to 10.0.3.1, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!!!!!!!!!!!!!!!!
Success rate is 100 percent (20/20), round-trip min/avg/max = 1/1/3 ms
```

**P3d 60 秒後 RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:2, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     2 198.51.100.6         172.16.0.3    UP 00:01:07   DT2
                            172.16.0.3    UP 00:01:07   DT1
     1 203.0.113.2          172.16.0.1    UP 00:02:02     S
```

**P3d RT02 — RT02# show ip route 198.51.100.6**

```
% Subnet not in table
```

**P3d RT02 — RT02# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.2    QM_IDLE           1093 ACTIVE
198.51.100.6    198.51.100.2    QM_IDLE           1095 ACTIVE
198.51.100.2    198.51.100.6    QM_IDLE           1094 ACTIVE

IPv6 Crypto ISAKMP SA
```

**P3d RT02 log — RT02 show logging**

```
*Sep 21 08:06:50.305: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 198.51.100.6 socket is UP
*Sep 21 08:06:50.306: %DMVPN-5-NHRP_NHP_UP: Tunnel0: Next Hop NHP : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is UP
*Sep 21 08:06:50.306: %DMVPN-7-NHRP_RES:  Tunnel0: Host with (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) Received Resolution Req from  (Tunnel: 172.16.0.3 NBMA: 198.51.100.6)
```

**P3d RT03 log — RT03 show logging**

```
*Sep 21 08:06:50.304: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.6 remote address : 198.51.100.2 socket is UP
*Sep 21 08:06:50.305: %DMVPN-5-NHRP_NHP_UP: Tunnel0: Next Hop NHP : (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) for (Tunnel: 172.16.0.3 NBMA: 198.51.100.6) is UP
*Sep 21 08:06:50.305: %DMVPN-7-NHRP_RES:  Tunnel0: Host with (Tunnel: 172.16.0.3 NBMA: 198.51.100.6) Received Resolution Req from  (Tunnel: 172.16.0.2 NBMA: 198.51.100.2)
```

**P3d 最後 RT02→internet — RT02# ping 8.8.8.8 repeat 5 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 8.8.8.8, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/2 ms
```

## P3r 後片付け  (2026-09-21 08:08)

- P3r: 健全復帰 15s

## P3d 素朴なフルトンネル(他 spoke の NBMA が既定経路=トンネルへ再帰)  (2026-09-21 08:12)

- P3d-0: 健全復帰 16s

**P3d hub**

```
ip access-list standard NAT-SRC
permit 10.0.0.0 0.0.255.255
exit
ip nat inside source list NAT-SRC interface Ethernet0/0 overload
interface Ethernet0/0
ip nat outside
exit
interface Tunnel0
ip nat inside
exit
ip route 0.0.0.0 0.0.0.0 203.0.113.1
router eigrp 100
redistribute static metric 10000 100 255 1 1400
exit
---
(応答なし)
```

**P3d RT02**

```
no ip route 0.0.0.0 0.0.0.0 198.51.100.1
ip route 203.0.113.2 255.255.255.255 198.51.100.1
---
(応答なし)
```

**P3d RT03**

```
no ip route 0.0.0.0 0.0.0.0 198.51.100.5
ip route 203.0.113.2 255.255.255.255 198.51.100.5
---
(応答なし)
```

**P3d RT04**

```
no ip route 0.0.0.0 0.0.0.0 198.51.100.9
ip route 203.0.113.2 255.255.255.255 198.51.100.9
---
(応答なし)
```

**P3d RT02→internet — RT02# ping 8.8.8.8 repeat 5 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 8.8.8.8, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/3 ms
```

**P3d 素朴 RT02→RT03 LAN 1回目 — RT02# ping 10.0.3.1 repeat 10 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 10, 100-byte ICMP Echos to 10.0.3.1, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!!!!!!
Success rate is 100 percent (10/10), round-trip min/avg/max = 2/3/7 ms
```

**P3d 素朴 RT02→RT03 LAN 2回目 — RT02# ping 10.0.3.1 repeat 10 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 10, 100-byte ICMP Echos to 10.0.3.1, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!!!!!!
Success rate is 100 percent (10/10), round-trip min/avg/max = 1/2/3 ms
```

**P3d 素朴 RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:2, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     2 198.51.100.6         172.16.0.3    UP 00:00:05   DT2
                            172.16.0.3    UP 00:00:05   DT1
     1 203.0.113.2          172.16.0.1    UP 00:00:58     S
```

**P3d 素朴 RT02 — RT02# show ip route 10.0.3.0**

```
Routing entry for 10.0.3.0/24
  Known via "eigrp 100", distance 90, metric 28288000, precedence routine (0), type internal
  Redistributing via eigrp 100
  Last update from 172.16.0.1 on Tunnel0, 00:00:56 ago
  Routing Descriptor Blocks:
  * 172.16.0.1, from 172.16.0.1, 00:00:56 ago, via Tunnel0
      Route metric is 28288000, traffic share count is 1
      Total delay is 105000 microseconds, minimum bandwidth is 100 Kbit
      Reliability 255/255, minimum MTU 1400 bytes
      Loading 2/255, Hops 2
```

**P3d 素朴 RT02 — RT02# show ip cef 10.0.3.1**

```
10.0.3.0/24
  nexthop 172.16.0.3 Tunnel0
```

**P3d 素朴 hub — RT01# show ip nhrp traffic**

```
Tunnel0: Max-send limit:10000Pkts/10Sec, Usage:0%
   Sent: Total 4
         2 Resolution Request  0 Resolution Reply  0 Registration Request  
         0 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  2 Traffic Indication  0 Redirect Suppress  
   Rcvd: Total 2
         2 Resolution Request  0 Resolution Reply  0 Registration Request  
         0 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress
```

**P3d 素朴 RT02 — RT02# show ip nhrp traffic**

```
Tunnel0: Max-send limit:10000Pkts/10Sec, Usage:0%
   Sent: Total 41
         10 Resolution Request  10 Resolution Reply  21 Registration Request  
         0 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress  
   Rcvd: Total 49
         10 Resolution Request  10 Resolution Reply  0 Registration Request  
         19 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  10 Traffic Indication  0 Redirect Suppress
```

- P3d 素朴: RT02 に直接トンネル(DT) あり

**P3d 60 秒後 RT02→RT03 LAN — RT02# ping 10.0.3.1 repeat 20 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 20, 100-byte ICMP Echos to 10.0.3.1, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!!!!!!!!!!!!!!!!
Success rate is 100 percent (20/20), round-trip min/avg/max = 1/3/32 ms
```

**P3d 60 秒後 RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:2, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     2 198.51.100.6         172.16.0.3    UP 00:01:07   DT2
                            172.16.0.3    UP 00:01:07   DT1
     1 203.0.113.2          172.16.0.1    UP 00:02:00     S
```

**P3d RT02 — RT02# show ip route 198.51.100.6**

```
% Subnet not in table
```

**P3d RT02 — RT02# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.2    QM_IDLE           1097 ACTIVE
198.51.100.6    198.51.100.2    QM_IDLE           1099 ACTIVE
198.51.100.2    198.51.100.6    QM_IDLE           1098 ACTIVE

IPv6 Crypto ISAKMP SA
```

**P3d RT02 log — RT02 show logging**

```
*Sep 21 08:11:31.188: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.2 remote address : 198.51.100.6 socket is UP
*Sep 21 08:11:31.189: %DMVPN-5-NHRP_NHP_UP: Tunnel0: Next Hop NHP : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6) for (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) is UP
*Sep 21 08:11:31.189: %DMVPN-7-NHRP_RES:  Tunnel0: Host with (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) Received Resolution Req from  (Tunnel: 172.16.0.3 NBMA: 198.51.100.6)
```

**P3d RT03 log — RT03 show logging**

```
*Sep 21 08:11:31.187: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 198.51.100.6 remote address : 198.51.100.2 socket is UP
*Sep 21 08:11:31.188: %DMVPN-5-NHRP_NHP_UP: Tunnel0: Next Hop NHP : (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) for (Tunnel: 172.16.0.3 NBMA: 198.51.100.6) is UP
*Sep 21 08:11:31.188: %DMVPN-7-NHRP_RES:  Tunnel0: Host with (Tunnel: 172.16.0.3 NBMA: 198.51.100.6) Received Resolution Req from  (Tunnel: 172.16.0.2 NBMA: 198.51.100.2)
```

**P3d 最後 RT02→internet — RT02# ping 8.8.8.8 repeat 5 source Loopback1 → 100%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 8.8.8.8, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/2 ms
```

## P3e 素朴フルトンネルの spoke 間外側経路と MTU  (2026-09-21 08:12)

**P3e RT02 — RT02# show ip cef 198.51.100.6**

```
198.51.100.6/32
  nexthop 172.16.0.1 Tunnel0
```

**P3e RT02 — RT02# show ip cef 198.51.100.6 detail**

```
198.51.100.6/32, epoch 0, flags [default route]
  QOS: Precedence routine (0)
  1 RR source [active source]
    Dependent covered prefix type rr, cover 0.0.0.0/0
  recursive via 0.0.0.0/0
    nexthop 172.16.0.1 Tunnel0
```

**P3e RT02 — RT02# show crypto ipsec sa peer 198.51.100.6 | include encaps|decaps|local crypto|remote crypto|path mtu**

```
    #pkts encaps: 31, #pkts encrypt: 31, #pkts digest: 31
    #pkts decaps: 31, #pkts decrypt: 31, #pkts verify: 31
     local crypto endpt.: 198.51.100.2, remote crypto endpt.: 198.51.100.6
     plaintext mtu 1458, path mtu 1500, ip mtu 1500, ip mtu idb Ethernet0/0
```

**P3e hub 前 — RT01# show interfaces Tunnel0 | include packets**

```
    Checksumming of packets disabled
  5 minute input rate 1000 bits/sec, 1 packets/sec
  5 minute output rate 0 bits/sec, 0 packets/sec
     4798 packets input, 516427 bytes, 0 no buffer
     5849 packets output, 627320 bytes, 0 underruns
```

**P3e RT02→RT03 size 100 df — RT02# ping 10.0.3.1 source Loopback1 repeat 5 size 100 df-bit**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 10.0.3.1, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
Packet sent with the DF bit set
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/3 ms
```

**P3e RT02→internet size 100 df — RT02# ping 8.8.8.8 source Loopback1 repeat 5 size 100 df-bit**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 8.8.8.8, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
Packet sent with the DF bit set
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/2 ms
```

**P3e RT02→RT03 size 1300 df — RT02# ping 10.0.3.1 source Loopback1 repeat 5 size 1300 df-bit**

```
Type escape sequence to abort.
Sending 5, 1300-byte ICMP Echos to 10.0.3.1, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
Packet sent with the DF bit set
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/2/3 ms
```

**P3e RT02→internet size 1300 df — RT02# ping 8.8.8.8 source Loopback1 repeat 5 size 1300 df-bit**

```
Type escape sequence to abort.
Sending 5, 1300-byte ICMP Echos to 8.8.8.8, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
Packet sent with the DF bit set
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/2 ms
```

**P3e RT02→RT03 size 1372 df — RT02# ping 10.0.3.1 source Loopback1 repeat 5 size 1372 df-bit**

```
Type escape sequence to abort.
Sending 5, 1372-byte ICMP Echos to 10.0.3.1, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
Packet sent with the DF bit set
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 2/2/3 ms
```

**P3e RT02→internet size 1372 df — RT02# ping 8.8.8.8 source Loopback1 repeat 5 size 1372 df-bit**

```
Type escape sequence to abort.
Sending 5, 1372-byte ICMP Echos to 8.8.8.8, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
Packet sent with the DF bit set
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/2 ms
```

**P3e RT02→RT03 size 1400 df — RT02# ping 10.0.3.1 source Loopback1 repeat 5 size 1400 df-bit**

```
Type escape sequence to abort.
Sending 5, 1400-byte ICMP Echos to 10.0.3.1, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
Packet sent with the DF bit set
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 2/2/4 ms
```

**P3e RT02→internet size 1400 df — RT02# ping 8.8.8.8 source Loopback1 repeat 5 size 1400 df-bit**

```
Type escape sequence to abort.
Sending 5, 1400-byte ICMP Echos to 8.8.8.8, timeout is 2 seconds:
Packet sent with a source address of 10.0.2.1 
Packet sent with the DF bit set
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/2 ms
```

**P3e hub 後 — RT01# show interfaces Tunnel0 | include packets**

```
    Checksumming of packets disabled
  5 minute input rate 3000 bits/sec, 2 packets/sec
  5 minute output rate 1000 bits/sec, 1 packets/sec
     4881 packets input, 584991 bytes, 0 no buffer
     5859 packets output, 635040 bytes, 0 underruns
```

**P3e hub — RT01# show ip nat translations**

```
Pro Inside global         Inside local          Outside local         Outside global
icmp 203.0.113.2:1024     10.0.2.1:64           8.8.8.8:64            8.8.8.8:1024
icmp 203.0.113.2:1025     10.0.2.1:66           8.8.8.8:66            8.8.8.8:1025
icmp 203.0.113.2:1026     10.0.2.1:68           8.8.8.8:68            8.8.8.8:1026
icmp 203.0.113.2:1027     10.0.2.1:70           8.8.8.8:70            8.8.8.8:1027
```

## P3r 後片付け  (2026-09-21 08:13)

- P3r: 健全復帰 16s

## Q1 out 方向 ACL と DMVPN  (2026-09-21 09:48)

- Q1-0: 健全復帰 16s

- == Q1: EDGE-OUT(out 方向)に IKE/ESP/ICMP だけ permit → DMVPN が生きるか・どの行に hit するか

**Q1 EDGE-OUT 適用**

```
ip access-list extended EDGE-OUT
10 permit udp host 203.0.113.2 any eq isakmp
20 permit udp host 203.0.113.2 any eq non500-isakmp
30 permit esp host 203.0.113.2 any
40 permit icmp any any
90 deny ip any any log
exit
interface Ethernet0/0
ip access-group EDGE-OUT out
---
(応答なし)
```

**Q1 hub(out ACL: gre 無し) — RT01# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Hub, NHRP Peers:3, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 198.51.100.2         172.16.0.2    UP 00:01:00     D
     1 198.51.100.6         172.16.0.3    UP 00:01:00     D
     1 198.51.100.10        172.16.0.4    UP 00:00:59     D
```

**Q1 hit — RT01# show ip access-lists EDGE-OUT**

```
Extended IP access list EDGE-OUT
    10 permit udp host 203.0.113.2 any eq isakmp (18 matches)
    20 permit udp host 203.0.113.2 any eq non500-isakmp
    30 permit esp host 203.0.113.2 any (87 matches)
    40 permit icmp any any (2 matches)
    90 deny ip any any log (8 matches)
```

**Q1 hub log — RT01 show logging**

```
*Sep 21 09:42:27.428: %CRYPTO-5-SELF_TEST_START: Crypto algorithms release (Rel5a), Entropy release (3.4.1)
*Sep 21 09:42:27.428: %CRYPTO-0-SELF_TEST_FAILURE: Crypto self-test - (Crypto Module Integrity Test Bypassed)
*Sep 21 09:42:27.517: %CRYPTO-5-SELF_TEST_END: Crypto Algorithm self-test completed successfully
*Sep 21 09:42:29.445: %CRYPTO_ENGINE-5-CSDL_COMPLIANCE_ENFORCED: Cisco PSB security compliance is being enforced
*Sep 21 09:42:48.629: %CRYPTO-5-SELF_TEST_START: Crypto algorithms release (Rel5a), Entropy release (3.4.1)
*Sep 21 09:42:48.630: %CRYPTO-5-SELF_TEST_END: Crypto Algorithm self-test completed successfully
*Sep 21 09:42:48.639: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 09:43:02.039: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is UP
*Sep 21 09:43:02.040: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 09:43:05.419: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is UP
*Sep 21 09:43:05.420: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 09:43:08.759: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is UP
*Sep 21 09:43:08.760: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 09:45:14.336: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.2 NBMA: 198.51.100.2 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 09:45:14.336: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is DOWN
*Sep 21 09:45:14.336: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 09:45:14.336: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is DOWN
*Sep 21 09:45:14.336: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 09:45:14.336: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is DOWN
*Sep 21 09:45:14.345: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 09:45:21.789: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 09:45:22.608: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is UP
*Sep 21 09:45:23.509: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 09:45:23.516: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is UP
*Sep 21 09:45:24.296: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 09:45:24.436: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is UP
*Sep 21 09:45:25.192: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 09:45:43.320: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.2 NBMA: 198.51.100.2 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 09:45:43.320: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is DOWN
*Sep 21 09:45:43.320: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 09:45:43.320: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is DOWN
*Sep 21 09:45:43.320: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10 ) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is DOWN, Reason: External(NHRP: no error)
*Sep 21 09:45:43.320: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is DOWN
*Sep 21 09:45:43.328: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 21 09:45:47.525: %SEC-6-IPACCESSLOGS: list EDGE-OUT denied 0.0.0.0 1 packet 
*Sep 21 09:45:50.392: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 21 09:45:51.314: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.2 socket is UP
*Sep 21 09:45:52.067: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.2 NBMA: 198.51.100.2) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 09:45:52.120: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.6 socket is UP
*Sep 21 09:45:52.687: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 203.0.113.2 remote address : 198.51.100.10 socket is UP
*Sep 21 09:45:52.923: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.3 NBMA: 198.51.100.6) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 09:45:53.560: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 172.16.0.4 NBMA: 198.51.100.10) for (Tunnel: 172.16.0.1 NBMA: 203.0.113.2) is UP
*Sep 21 09:46:32.774: %SEC-6-IPACCESSLOGNP: list EDGE-OUT denied 84 0.5.1.3 -> 67.105.115.99, 1 packet
```

**Q1 gre 追加**

```
ip access-list extended EDGE-OUT
35 permit gre host 203.0.113.2 any
---
(応答なし)
```

**Q1 hub(out ACL: gre あり) — RT01# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Hub, NHRP Peers:3, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 198.51.100.2         172.16.0.2    UP 00:01:00     D
     1 198.51.100.6         172.16.0.3    UP 00:01:00     D
     1 198.51.100.10        172.16.0.4    UP 00:00:59     D
```

**Q1 hit(gre あり) — RT01# show ip access-lists EDGE-OUT**

```
Extended IP access list EDGE-OUT
    10 permit udp host 203.0.113.2 any eq isakmp (36 matches)
    20 permit udp host 203.0.113.2 any eq non500-isakmp
    30 permit esp host 203.0.113.2 any (173 matches)
    35 permit gre host 203.0.113.2 any
    40 permit icmp any any (4 matches)
    90 deny ip any any log (16 matches)
```

- Q1 後: 健全復帰 16s

## Q2 resequence と 4500  (2026-09-21 09:56)

- == Q2: 詰まった seq への挿入(resequence)・4500 無し

**Q2 詰まった wall(esp 無し・remark 込み)を in に適用**

```
ip access-list extended Q2WALL
10 deny ip 10.0.0.0 0.255.255.255 any
11 deny ip 192.168.0.0 0.0.255.255 any
12 remark === VPN (SEC-TEAM) ===
13 permit udp any host 203.0.113.2 eq isakmp
14 permit udp any host 203.0.113.2 eq non500-isakmp
15 permit icmp any host 203.0.113.2 echo
16 deny ip any host 203.0.113.2 log
17 deny ip any any log
exit
interface Ethernet0/0
ip access-group Q2WALL in
---
(応答なし)
```

**Q2 run(remark の seq) — RT01# show running-config | section access-list extended Q2WALL**

```
ip access-list extended Q2WALL
 10 deny ip 10.0.0.0 0.255.255.255 any
 11 deny ip 192.168.0.0 0.0.255.255 any
 12 remark === VPN (SEC-TEAM) ===
 13 permit udp any host 203.0.113.2 eq isakmp
 14 permit udp any host 203.0.113.2 eq non500-isakmp
 15 permit icmp any host 203.0.113.2 echo
 16 deny ip any host 203.0.113.2 log
 17 deny ip any any log
```

**Q2 esp 無し hub — RT01# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================
```

**Q2 esp 無し hub — RT01# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.2    QM_IDLE           1016 ACTIVE
203.0.113.2     198.51.100.10   QM_IDLE           1018 ACTIVE
203.0.113.2     198.51.100.6    QM_IDLE           1017 ACTIVE

IPv6 Crypto ISAKMP SA
```

**Q2 esp 無し hit — RT01# show ip access-lists Q2WALL**

```
Extended IP access list Q2WALL
    10 deny ip 10.0.0.0 0.255.255.255 any
    11 deny ip 192.168.0.0 0.0.255.255 any
    13 permit udp any host 203.0.113.2 eq isakmp (42 matches)
    14 permit udp any host 203.0.113.2 eq non500-isakmp
    15 permit icmp any host 203.0.113.2 echo
    16 deny ip any host 203.0.113.2 log (79 matches)
    17 deny ip any any log
```

**Q2 hub log — RT01 show logging**

```
*Sep 21 09:45:47.525: %SEC-6-IPACCESSLOGS: list EDGE-OUT denied 0.0.0.0 1 packet 
*Sep 21 09:46:32.774: %SEC-6-IPACCESSLOGNP: list EDGE-OUT denied 84 0.5.1.3 -> 67.105.115.99, 1 packet 
*Sep 21 09:46:54.373: %SEC-6-IPACCESSLOGS: list EDGE-OUT denied 0.0.0.0 6 packets 
*Sep 21 09:48:05.652: %SEC-6-IPACCESSLOGS: list EDGE-OUT denied 0.0.0.0 7 packets 
*Sep 21 09:48:05.652: %SEC-6-IPACCESSLOGNP: list EDGE-OUT denied 84 0.5.1.3 -> 67.105.115.99, 1 packet 
*Sep 21 09:48:32.129: %SEC-6-IPACCESSLOGNP: list Q2WALL denied 50 198.51.100.2 -> 203.0.113.2, 1 packet 
*Sep 21 09:48:41.878: %SEC-6-IPACCESSLOGNP: list Q2WALL denied 50 198.51.100.10 -> 203.0.113.2, 1 packet
```

**Q2 埋まっている seq 15 に挿入(拒否されるはず)**

```
ip access-list extended Q2WALL
15 permit esp any host 203.0.113.2
---
% Duplicate sequence number
% Failed to add ace to access-list
```

**Q2 seq 15 挿入の結果 — RT01# show ip access-lists Q2WALL**

```
Extended IP access list Q2WALL
    10 deny ip 10.0.0.0 0.255.255.255 any
    11 deny ip 192.168.0.0 0.0.255.255 any
    13 permit udp any host 203.0.113.2 eq isakmp (42 matches)
    14 permit udp any host 203.0.113.2 eq non500-isakmp
    15 permit icmp any host 203.0.113.2 echo
    16 deny ip any host 203.0.113.2 log (80 matches)
    17 deny ip any any log
```

**Q2 resequence**

```
ip access-list resequence Q2WALL 10 10
---
(応答なし)
```

**Q2 resequence 後(カウンタ保持?) — RT01# show ip access-lists Q2WALL**

```
Extended IP access list Q2WALL
    10 deny ip 10.0.0.0 0.255.255.255 any
    20 deny ip 192.168.0.0 0.0.255.255 any
    30 permit udp any host 203.0.113.2 eq isakmp (42 matches)
    40 permit udp any host 203.0.113.2 eq non500-isakmp
    50 permit icmp any host 203.0.113.2 echo
    60 deny ip any host 203.0.113.2 log (80 matches)
    70 deny ip any any log
```

**Q2 resequence 後 run(remark も renumber?) — RT01# show running-config | section access-list extended Q2WALL**

```
ip access-list extended Q2WALL
 10 deny ip 10.0.0.0 0.255.255.255 any
 20 deny ip 192.168.0.0 0.0.255.255 any
 30 permit udp any host 203.0.113.2 eq isakmp
 40 permit udp any host 203.0.113.2 eq non500-isakmp
 50 permit icmp any host 203.0.113.2 echo
 60 deny ip any host 203.0.113.2 log
 70 deny ip any any log
```

**Q2 65 に esp 挿入(deny 70 の直前)**

```
ip access-list extended Q2WALL
65 permit esp any host 203.0.113.2
---
(応答なし)
```

- Q2: esp 挿入(resequence 後・bounce なし)で 3 spoke UP まで ★180s 未達

**Q2 挿入後 hit — RT01# show ip access-lists Q2WALL**

```
Extended IP access list Q2WALL
    10 deny ip 10.0.0.0 0.255.255.255 any
    20 deny ip 192.168.0.0 0.0.255.255 any
    30 permit udp any host 203.0.113.2 eq isakmp (42 matches)
    40 permit udp any host 203.0.113.2 eq non500-isakmp
    50 permit icmp any host 203.0.113.2 echo
    60 deny ip any host 203.0.113.2 log (213 matches)
    65 permit esp any host 203.0.113.2
    70 deny ip any any log
```

**Q2 4500 permit(seq 50)を外す**

```
ip access-list extended Q2WALL
no 50
---
(応答なし)
```

- Q2: udp 4500 permit 無しで 3 spoke UP まで ★180s 未達= 4500 は必要

**Q2 4500 無し hit — RT01# show ip access-lists Q2WALL**

```
Extended IP access list Q2WALL
    10 deny ip 10.0.0.0 0.255.255.255 any
    20 deny ip 192.168.0.0 0.0.255.255 any
    30 permit udp any host 203.0.113.2 eq isakmp (84 matches)
    40 permit udp any host 203.0.113.2 eq non500-isakmp
    60 deny ip any host 203.0.113.2 log (365 matches)
    65 permit esp any host 203.0.113.2
    70 deny ip any any log
```

- Q2 後: 健全復帰 16s

## Q2b resequence 後の挿入位置と 4500  (2026-09-21 10:04)

- == Q2b: resequence 後の正しい位置(55)へ esp 挿入・4500 無し

**Q2b wall 適用**

```
ip access-list extended Q2WALL
10 deny ip 10.0.0.0 0.255.255.255 any
11 deny ip 192.168.0.0 0.0.255.255 any
12 remark === VPN (SEC-TEAM) ===
13 permit udp any host 203.0.113.2 eq isakmp
14 permit udp any host 203.0.113.2 eq non500-isakmp
15 permit icmp any host 203.0.113.2 echo
16 deny ip any host 203.0.113.2 log
17 deny ip any any log
exit
interface Ethernet0/0
ip access-group Q2WALL in
---
(応答なし)
```

**Q2b esp 無し hub — RT01# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================
```

**Q2b resequence**

```
ip access-list resequence Q2WALL 10 10
---
(応答なし)
```

**Q2b 55 に esp 挿入**

```
ip access-list extended Q2WALL
55 permit esp any host 203.0.113.2
---
(応答なし)
```

- Q2b: esp 挿入(resequence 後・正しい位置・bounce なし)で 3 spoke UP まで 62s

**Q2b 挿入後 hit — RT01# show ip access-lists Q2WALL**

```
Extended IP access list Q2WALL
    10 deny ip 10.0.0.0 0.255.255.255 any
    20 deny ip 192.168.0.0 0.0.255.255 any
    30 permit udp any host 203.0.113.2 eq isakmp (40 matches)
    40 permit udp any host 203.0.113.2 eq non500-isakmp
    50 permit icmp any host 203.0.113.2 echo
    55 permit esp any host 203.0.113.2 (61 matches)
    60 deny ip any host 203.0.113.2 log (69 matches)
    70 deny ip any any log
```

**Q2b 4500 permit(seq 40)を外す**

```
ip access-list extended Q2WALL
no 40
---
(応答なし)
```

- Q2b: udp 4500 permit 無し(reset あり)で 3 spoke UP まで 16s

**Q2b 4500 無し hit — RT01# show ip access-lists Q2WALL**

```
Extended IP access list Q2WALL
    10 deny ip 10.0.0.0 0.255.255.255 any
    20 deny ip 192.168.0.0 0.0.255.255 any
    30 permit udp any host 203.0.113.2 eq isakmp (80 matches)
    50 permit icmp any host 203.0.113.2 echo
    55 permit esp any host 203.0.113.2 (103 matches)
    60 deny ip any host 203.0.113.2 log (69 matches)
    70 deny ip any any log
```

- Q2b 後: 健全復帰 16s

## Q3 打ちづらい名前と大小違い参照  (2026-09-21 10:44)

- == Q3: 打ちづらい名前の受理 / 大小違い参照

**Q3 打ちづらい名前(受理されるか)**

```
crypto isakmp key pR3sh4red-K3y#7 address 10.99.99.99
no crypto isakmp key pR3sh4red-K3y#7 address 10.99.99.99
crypto ipsec transform-set Ts-aEs256_Sha2.v1 esp-aes 256 esp-sha256-hmac
mode transport
exit
crypto ipsec profile IPsec.Prof_DmVPN-1
set transform-set Ts-aEs256_Sha2.v1
exit
ip access-list extended Sec_Edge-IN.v2
10 permit ip any any
exit
interface Tunnel0
ip nhrp authentication nH0rP-k1
ip nhrp authentication NHRPKEY
---
(応答なし)
```

**Q3 run — RT01# show run | include Ts-aEs|IPsec.Prof|Sec_Edge|nhrp auth**

```
crypto ipsec transform-set Ts-aEs256_Sha2.v1 esp-aes 256 esp-sha256-hmac 
crypto ipsec profile IPsec.Prof_DmVPN-1
 set transform-set Ts-aEs256_Sha2.v1 
 ip nhrp authentication NHRPKEY
ip access-list extended Sec_Edge-IN.v2
```

**Q3 大小違い参照(存在しない名前)**

```
interface Tunnel0
tunnel protection ipsec profile DMVPN-Prof
---
(応答なし)
```

**Q3 参照後 run — RT01# show run | section interface Tunnel0|crypto ipsec profile**

```
crypto ipsec profile DMVPN-PROF
 set transform-set TS 
crypto ipsec profile IPsec.Prof_DmVPN-1
 set transform-set Ts-aEs256_Sha2.v1 
interface Tunnel0
 ip address 172.16.0.1 255.255.255.0
 no ip redirects
 ip mtu 1400
 no ip split-horizon eigrp 100
 ip nhrp authentication NHRPKEY
 ip nhrp network-id 100
 ip nhrp redirect
 ip tcp adjust-mss 1360
 tunnel source Ethernet0/0
 tunnel mode gre multipoint
 tunnel key 100
 tunnel protection ipsec profile DMVPN-PROF
```

**Q3 profile 一覧 — RT01# show crypto ipsec profile**

```
IPSEC profile DMVPN-PROF
	Security association lifetime: 4608000 kilobytes/3600 seconds
	Dualstack (Y/N): N

	Responder-Only (Y/N): N
	PFS (Y/N): N
	Mixed-mode : Disabled
	Transform sets={ 
		TS:  { esp-256-aes esp-sha256-hmac  } , 
	}

IPSEC profile IPsec.Prof_DmVPN-1
	Security association lifetime: 4608000 kilobytes/3600 seconds
	Dualstack (Y/N): N

	Responder-Only (Y/N): N
	PFS (Y/N): N
	Mixed-mode : Disabled
	Transform sets={ 
		Ts-aEs256_Sha2.v1:  { esp-256-aes esp-sha256-hmac  } , 
	}

IPSEC profile default
	Security association lifetime: 4608000 kilobytes/3600 seconds
	Dualstack (Y/N): N

	Responder-Only (Y/N): N
	PFS (Y/N): N
	Mixed-mode : Disabled
	Transform sets={ 
		default:  { esp-aes esp-sha-hmac  } , 
	}
```

**Q3 Tunnel 状態 — RT01# show ip interface brief | include Tunnel**

```
Tunnel0                172.16.0.1      YES TFTP   up                    up
```

**Q3 log — RT01 show logging**

```
*Sep 21 10:43:03.048: %SYS-5-CONFIG_I: Configured from console by console
*Sep 21 10:43:04.459: %SYS-5-CONFIG_I: Configured from console by console
```

**Q3 大小違い参照 hub — RT01# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Hub, NHRP Peers:3, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 198.51.100.2         172.16.0.2    UP 00:01:00     D
     1 198.51.100.6         172.16.0.3    UP 00:00:59     D
     1 198.51.100.10        172.16.0.4    UP 00:00:59     D
```

**Q3 hub — RT01# show crypto isakmp sa**

```
IPv4 Crypto ISAKMP SA
dst             src             state          conn-id status
203.0.113.2     198.51.100.6    QM_IDLE           1005 ACTIVE
203.0.113.2     198.51.100.10   QM_IDLE           1006 ACTIVE
203.0.113.2     198.51.100.2    QM_IDLE           1004 ACTIVE

IPv6 Crypto ISAKMP SA
```

**Q3 hub — RT01# show crypto ipsec sa | include peer|encaps|decaps|in use**

```
   current_peer 198.51.100.10 port 500
    #pkts encaps: 24, #pkts encrypt: 24, #pkts digest: 24
    #pkts decaps: 25, #pkts decrypt: 25, #pkts verify: 25
        in use settings ={Transport, }
        in use settings ={Transport, }
   current_peer 198.51.100.6 port 500
    #pkts encaps: 25, #pkts encrypt: 25, #pkts digest: 25
    #pkts decaps: 26, #pkts decrypt: 26, #pkts verify: 26
        in use settings ={Transport, }
        in use settings ={Transport, }
   current_peer 198.51.100.2 port 500
    #pkts encaps: 24, #pkts encrypt: 24, #pkts digest: 24
    #pkts decaps: 25, #pkts decrypt: 25, #pkts verify: 25
        in use settings ={Transport, }
        in use settings ={Transport, }
```

**Q3 RT02 — RT02# show dmvpn**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface: Tunnel0, IPv4 NHRP Details 
Type:Spoke, NHRP Peers:1, 

 # Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb
 ----- --------------- --------------- ----- -------- -----
     1 203.0.113.2          172.16.0.1    UP 00:01:01     S
```

**Q3 是正**

```
interface Tunnel0
tunnel protection ipsec profile DMVPN-PROF
---
(応答なし)
```

**Q3 是正後 profile(空の Prof が残る?) — RT01# show run | section crypto ipsec profile**

```
crypto ipsec profile DMVPN-PROF
 set transform-set TS 
crypto ipsec profile IPsec.Prof_DmVPN-1
 set transform-set Ts-aEs256_Sha2.v1
```

**Q3 掃除**

```
no crypto ipsec profile DMVPN-Prof
no crypto ipsec profile IPsec.Prof_DmVPN-1
no crypto ipsec transform-set Ts-aEs256_Sha2.v1
no ip access-list extended Sec_Edge-IN.v2
---
(応答なし)
```

- Q3 後: 健全復帰 16s
