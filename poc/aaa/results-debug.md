# BL-101 P0 追試2 — ルータ側 debug の出力

自動生成: poc/aaa/debug_probe.py。対象= _POC-AAA の RT02。
採取した debug= `debug radius authentication` / `debug aaa authentication` /
`debug aaa authorization`。

## D4 — port_mismatch: 待受ポート違い(RAD1 停止)  (180s)

```
Attempting authentication test to server-group RADGRP using radius
*Aug  8 11:11:44.061: AAA/AUTHOR: auth_need : user= 'SUZUKI' ruser= 'RT02'rem_addr= '10.1.10.6' priv= 1 list= '' AUTHOR-TYPE= 'commands'
*Aug  8 11:11:44.061: AAA/AUTHOR: auth_need : user= 'SUZUKI' ruser= 'RT02'rem_addr= '10.1.10.6' priv= 15 list= '' AUTHOR-TYPE= 'commands'
*Aug  8 11:11:44.061: AAA/SG/TEST:Invoked SPI services for PROXY_START and PROXY_STOP
*Aug  8 11:11:44.061: AAA: parse name=<no string> idb type=-1 tty=-1
*Aug  8 11:11:44.061: AAA/MEMORY: create_user (0x76050166D530) user='noc-taro' ruser='NULL' ds0=0 port='' rem_addr='NULL' authen_type=ASCII service=LOGIN priv=1 initial_task_id='0', vrf= (id=0)
*Aug  8 11:11:44.061: RADIUS: Pick NAS IP for u=0x76050166D530 tableid=0 cfg_addr=10.0.0.2
*Aug  8 11:11:44.061: vrfid: [65535]  ipv6 tableid : [0]
*Aug  8 11:11:44.061: idb is NULL
*Aug  8 11:11:44.061: RADIUS(00000000): Config NAS IPv6: ::
*Aug  8 11:11:44.061: RADIUS: ustruct sharecount=1
*Aug  8 11:11:44.061: Radius: radius_port_info() success=0 radius_nas_port=1
*Aug  8 11:11:44.061: RADIUS(00000000): Send Access-Request to 10.99.1.2:1812 id 1645/124, len 60
RADIUS:  authenticator B5 36 DD A8 C0 F3 C6 28 - C4 2F 57 9A EC 72 DD 86
*Aug  8 11:11:44.061: RADIUS:  NAS-IP-Address      [4]   6   10.0.0.2
*Aug  8 11:11:44.061: RADIUS:  NAS-Port-Type       [61]  6   Async                     [0]
*Aug  8 11:11:44.061: RADIUS:  User-Name           [1]   10  "noc-taro"
*Aug  8 11:11:44.061: RADIUS:  User-Password       [2]   18  *
*Aug  8 11:11:44.061: RADIUS(00000000): Sending a IPv4 Radius Packet
*Aug  8 11:11:44.061: RADIUS(00000000): Started 3 sec timeout
*Aug  8 11:11:47.092: RADIUS(00000000): Request timed out!
*Aug  8 11:11:47.092: RADIUS: Retransmit to (10.99.1.2:1812,1813) for id 1645/124
*Aug  8 11:11:47.092: RADIUS(00000000): Started 3 sec timeout
*Aug  8 11:11:50.133: RADIUS(00000000): Request timed out!
*Aug  8 11:11:50.133: RADIUS: Fail-over to (10.99.2.2:1812,1813) for id 1645/124
*Aug  8 11:11:50.148: RADIUS(00000000): Started 3 sec timeout
*Aug  8 11:11:53.162: RADIUS(00000000): Request timed out!
*Aug  8 11:11:53.162: RADIUS: Retransmit to (10.99.2.2:1812,1813) for id 1645/124
*Aug  8 11:11:53.163: RADIUS(00000000): Started 3 sec timeoutNo authoritative response from any server.
*Aug  8 11:11:56.189: RADIUS(00000000): Request timed out!
*Aug  8 11:11:56.189: RADIUS: No response from (10.99.2.2:1812,1813) for id 1645/124
*Aug  8 11:11:56.189: RADIUS: No response from server
*Aug  8 11:11:56.189: AAA/MEMORY: free_user (0x76050166D530) user='noc-taro' ruser='NULL' port='' rem_addr='NULL' authen_type=ASCII service=LOGIN priv=1 vrf= (id=0)
```

## D5 — 全断: サーバが両方落ちている  (60s)

```
Attempting authentication test to server-group RADGRP using radius
*Aug  8 11:12:43.233: %AMDP2_FE-6-EXCESSCOLL: Ethernet0/3 TDR=0, TRC=0
*Aug  8 11:12:44.426: AAA/AUTHOR: auth_need : user= 'SUZUKI' ruser= 'RT02'rem_addr= '10.1.10.6' priv= 1 list= '' AUTHOR-TYPE= 'commands'
*Aug  8 11:12:44.426: AAA/AUTHOR: auth_need : user= 'SUZUKI' ruser= 'RT02'rem_addr= '10.1.10.6' priv= 15 list= '' AUTHOR-TYPE= 'commands'
*Aug  8 11:12:44.426: AAA/SG/TEST:Invoked SPI services for PROXY_START and PROXY_STOP
*Aug  8 11:12:44.426: AAA: parse name=<no string> idb type=-1 tty=-1
*Aug  8 11:12:44.426: AAA/MEMORY: create_user (0x76050079CEF0) user='noc-taro' ruser='NULL' ds0=0 port='' rem_addr='NULL' authen_type=ASCII service=LOGIN priv=1 initial_task_id='0', vrf= (id=0)
*Aug  8 11:12:44.426: RADIUS: Pick NAS IP for u=0x76050079CEF0 tableid=0 cfg_addr=10.0.0.2
*Aug  8 11:12:44.426: vrfid: [65535]  ipv6 tableid : [0]
*Aug  8 11:12:44.426: idb is NULL
*Aug  8 11:12:44.426: RADIUS(00000000): Config NAS IPv6: ::
*Aug  8 11:12:44.426: RADIUS: ustruct sharecount=1
*Aug  8 11:12:44.426: Radius: radius_port_info() success=0 radius_nas_port=1
*Aug  8 11:12:44.426: RADIUS(00000000): Send Access-Request to 10.99.1.2:1812 id 1645/125, len 60
RADIUS:  authenticator 38 F0 DA A1 B5 5F 82 1B - FE 4C 9A 10 6B 05 86 B8
*Aug  8 11:12:44.426: RADIUS:  NAS-IP-Address      [4]   6   10.0.0.2
*Aug  8 11:12:44.426: RADIUS:  NAS-Port-Type       [61]  6   Async                     [0]
*Aug  8 11:12:44.426: RADIUS:  User-Name           [1]   10  "noc-taro"
*Aug  8 11:12:44.426: RADIUS:  User-Password       [2]   18  *
*Aug  8 11:12:44.426: RADIUS(00000000): Sending a IPv4 Radius Packet
*Aug  8 11:12:44.426: RADIUS(00000000): Started 3 sec timeout
*Aug  8 11:12:47.458: RADIUS(00000000): Request timed out!
*Aug  8 11:12:47.459: RADIUS: Retransmit to (10.99.1.2:1812,1813) for id 1645/125
*Aug  8 11:12:47.459: RADIUS(00000000): Started 3 sec timeout
*Aug  8 11:12:50.493: RADIUS(00000000): Request timed out!
*Aug  8 11:12:50.493: RADIUS: Fail-over to (10.99.2.2:1912,1913) for id 1645/125
*Aug  8 11:12:50.493: RADIUS(00000000): Started 3 sec timeout
*Aug  8 11:12:53.519: RADIUS(00000000): Request timed out!
*Aug  8 11:12:53.519: RADIUS: Retransmit to (10.99.2.2:1912,1913) for id 1645/125
*Aug  8 11:12:53.519: RADIUS(00000000): Started 3 sec timeoutNo authoritative response from any server.
*Aug  8 11:12:56.564: RADIUS(00000000): Request timed out!
*Aug  8 11:12:56.564: RADIUS: No response from (10.99.2.2:1912,1913) for id 1645/125
*Aug  8 11:12:56.564: RADIUS: No response from server
*Aug  8 11:12:56.564: AAA/MEMORY: free_user (0x76050079CEF0) user='noc-taro' ruser='NULL' port='' rem_addr='NULL' authen_type=ASCII service=LOGIN priv=1 vrf= (id=0)
```
