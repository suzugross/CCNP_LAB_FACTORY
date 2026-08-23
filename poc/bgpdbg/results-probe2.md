

# probe2 run 2026-08-23 00:42 (b1 b2 b3)

## b1

b1 password_mismatch: RT01 `show ip bgp summary`:
```
undebug all
All possible debugging has been turned off
```

b1 password_mismatch: RT01 logging(debug 抜粋):
```
BGP router identifier 1.1.1.1, local AS number 65001
BGP table version is 1, main routing table version 1
```

b1 password_mismatch: RT02 `show ip bgp summary`:
```
undebug all
All possible debugging has been turned off
```

b1 password_mismatch: RT02 logging(debug 抜粋):
```
BGP router identifier 2.2.2.2, local AS number 65001
BGP table version is 1, main routing table version 1
```

b1b password_oneside: RT01 `show ip bgp summary`:
```
undebug all
All possible debugging has been turned off
```

b1b password_oneside: RT01 logging(debug 抜粋):
```
BGP router identifier 1.1.1.1, local AS number 65001
BGP table version is 1, main routing table version 1
```

b1b password_oneside: RT02 `show ip bgp summary`:
```
undebug all
All possible debugging has been turned off
```

b1b password_oneside: RT02 logging(debug 抜粋):
```
BGP router identifier 2.2.2.2, local AS number 65001
BGP table version is 1, main routing table version 1
```

## b2

b2 remote_as_wrong: RT01 `show ip bgp summary`:
```
BGP router identifier 1.1.1.1, local AS number 65001
BGP table version is 1, main routing table version 1

Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.0.12.2       4        65003       0       0        1    0    0 never    Idle
```

b2 remote_as_wrong: RT01 logging(debug 抜粋):
```
Enhanced Refresh cap received in open message
*Aug 23 00:45:12.079: BGP: 10.0.12.2 passive rcvd OPEN w/ optional parameter type 2 (Capability) len 6
*Aug 23 00:45:12.079: BGP: 10.0.12.2 passive OPEN has CAPABILITY code: 65, length 4
*Aug 23 00:45:12.079: BGP: 10.0.12.2 passive OPEN has 4-byte ASN CAP for: 65002
*Aug 23 00:45:12.079: BGP: 10.0.12.2 passive bad OPEN, remote AS is 65002, expected 65003  
*Aug 23 00:45:12.079: BGP: 10.0.12.2 passive went from Connect to Closing
*Aug 23 00:45:12.079: %BGP-3-NOTIFICATION: sent to neighbor 10.0.12.2 passive 2/2 (peer in wrong AS) 2 bytes FDEA
*Aug 23 00:45:12.079: BGP: ses global 10.0.12.2 (0x7161E6385D88:0) pas Send NOTIFICATION 2/2 (peer in wrong AS) 2 bytes FDEA
*Aug 23 00:45:12.079: %BGP-4-MSGDUMP: unsupported or mal-formatted message received from 10.0.12.2: 
*Aug 23 00:45:16.545: BGP: 10.0.12.2 passive local error close after sending NOTIFICATION
*Aug 23 00:45:16.545: %BGP-5-NBR_RESET: Neighbor 10.0.12.2 passive reset (BGP Notification sent)
*Aug 23 00:45:16.545: BGP: 10.0.12.2 passive(0x7161E6385D88) closing
*Aug 23 00:45:16.545: BGP: 10.0.12.2 passive went from Closing to Idle
*Aug 23 00:45:16.545: %BGP-5-ADJCHANGE: neighbor 10.0.12.2 passive Down BGP Notification sent
*Aug 23 00:45:16.545: BGP: nbr global 10.0.12.2 Active open failed - open timer running
*Aug 23 00:45:16.545: BGP: nbr global 10.0.12.2 Active open failed - open timer running
*Aug 23 00:45:19.249: BGP: 10.0.12.2 passive open to 10.0.12.1
*Aug 23 00:45:19.249: BGP: Fetched peer 10.0.12.2 from tcb
*Aug 23 00:45:19.249: BGP: 10.0.12.2 passive went from Idle to Connect
*Aug 23 00:45:19.249: BGP: ses global 10.0.12.2 (0x7161E6385D88:0) pas Setting open delay timer to 60 seconds.
*Aug 23 00:45:19.249: BGP: 10.0.12.2 passive rcv message type 1, length (excl. header) 38
*Aug 23 00:45:19.249: BGP: ses global 10.0.12.2 (0x7161E6385D88:0) pas Receive OPEN
*Aug 23 00:45:19.249: BGP: 10.0.12.2 passive rcv OPEN, version 4, holdtime 180 seconds
*Aug 23 00:45:19.249: BGP: 10.0.12.2 passive rcv OPEN w/ OPTION parameter len: 28
*Aug 23 00:45:19.249: BGP: 10.0.12.2 passive rcvd OPEN w/ optional parameter type 2 (Capability) len 6
*Aug 23 00:45:19.249: BGP: 10.0.12.2 passive OPEN has CAPABILITY code: 1, length 4
*Aug 23 00:45:19.249: BGP: 10.0.12.2 passive OPEN has MP_EXT CAP for afi/safi: 1/1
*Aug 23 00:45:19.249: BGP: 10.0.12.2 passive rcvd OPEN w/ optional parameter type 2 (Capability) len 2
*Aug 23 00:45:19.249: BGP: 10.0.12.2 passive OPEN has CAPABILITY code: 128, length 0
*Aug 23 00:45:19.249: BGP: 10.0.12.2 passive OPEN has ROUTE-REFRESH capability(old) for all address-families
*Aug 23 00:45:19.249: BGP: 10.0.12.2 passive rcvd OPEN w/ optional parameter type 2 (Capability) len 2
*Aug 23 00:45:19.249: BGP: 10.0.12.2 passive OPEN has CAPABILITY code: 2, length 0
*Aug 23 00:45:19.249: BGP: 10.0.12.2 passive OPEN has ROUTE-REFRESH capability(new) for all address-families
*Aug 23 00:45:19.249: BGP: 10.0.12.2 passive rcvd OPEN w/ optional parameter type 2 (Capability) len 2
*Aug 23 00:45:19.249: BGP: 10.0.12.2 passive OPEN has CAPABILITY code: 70, length 0
*Aug 23 00:45:19.249: BGP: ses global 10.0.12.2 (0x7161E6385D88:0) pas Enhanced Refresh cap received in open message
*Aug 23 00:45:19.249: BGP: 10.0.12.2 passive rcvd OPEN w/ optional parameter type 2 (Capability) len 6
*Aug 23 00:45:19.249: BGP: 10.0.12.2 passive OPEN has CAPABILITY code: 65, length 4
*Aug 23 00:45:19.249: BGP: 10.0.12.2 passive OPEN has 4-byte ASN CAP for: 65002
*Aug 23 00:45:19.249: BGP: 10.0.12.2 passive bad OPEN, remote AS is 65002, expected 65003  
*Aug 23 00:45:19.249: BGP: 10.0.12.2 passive went from Connect to Closing
*Aug 23 00:45:19.249: %BGP-3-NOTIFICATION: sent to neighbor 10.0.12.2 passive 2/2 (peer in wrong AS) 2 bytes FDEA
*Aug 23 00:45:19.249: BGP: ses global 10.0.12.2 (0x7161E6385D88:0) pas Send NOTIFICATION 2/2 (peer in wrong AS) 2 bytes FDEA
*Aug 23 00:45:19.249: %BGP-4-MSGDUMP: unsupported or mal-formatted message received from 10.0.12.2:
```

b2 remote_as_wrong: RT02 `show ip bgp summary`:
```
undebug all
All possible debugging has been turned off
```

b2 remote_as_wrong: RT02 logging(debug 抜粋):
```
BGP router identifier 2.2.2.2, local AS number 65002
BGP table version is 1, main routing table version 1
```

## b3

b3 nbr_shutdown: RT01 `show ip bgp summary`:
```
BGP router identifier 1.1.1.1, local AS number 65001
BGP table version is 1, main routing table version 1

Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
2.2.2.2         4        65001       0       0        1    0    0 never    Idle (Admin)
```

b3 nbr_shutdown: RT01 logging(debug 抜粋):
```

```

b3 nbr_shutdown: RT02 `show ip bgp summary`:
```
undebug all
All possible debugging has been turned off
```

b3 nbr_shutdown: RT02 logging(debug 抜粋):
```
BGP router identifier 2.2.2.2, local AS number 65001
BGP table version is 1, main routing table version 1
```


# probe2 run 2026-08-23 00:47 (b1 b2 b3)

## b1

b1 password_mismatch: RT01 `show ip bgp summary`:
```
BGP router identifier 1.1.1.1, local AS number 65001
BGP table version is 1, main routing table version 1

Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
2.2.2.2         4        65001       0       0        1    0    0 never    Idle
```

b1 password_mismatch: RT01 logging(debug 抜粋):
```
*Aug 23 00:47:37.911: BGP: 2.2.2.2 active went from Idle to Active
*Aug 23 00:47:37.911: BGP: 2.2.2.2 open active, local address 1.1.1.1
*Aug 23 00:47:38.130: %TCP-6-BADAUTH: Invalid MD5 digest from 2.2.2.2(54006) to 1.1.1.1(179) tableid - 0
*Aug 23 00:47:40.130: %TCP-6-BADAUTH: Invalid MD5 digest from 2.2.2.2(54006) to 1.1.1.1(179) tableid - 0
*Aug 23 00:47:44.130: %TCP-6-BADAUTH: Invalid MD5 digest from 2.2.2.2(54006) to 1.1.1.1(179) tableid - 0
*Aug 23 00:47:52.131: %TCP-6-BADAUTH: Invalid MD5 digest from 2.2.2.2(54006) to 1.1.1.1(179) tableid - 0
*Aug 23 00:48:07.911: BGP: 2.2.2.2 open failed: Connection timed out; remote host not responding
*Aug 23 00:48:07.911: BGP: 2.2.2.2 Active open failed - tcb is not available, open active delayed 8192ms (35000ms max, 60% jitter)
*Aug 23 00:48:07.911: BGP: ses global 2.2.2.2 (0x7161E623E350:0) act Reset (Active open failed).
*Aug 23 00:48:07.911: BGP: 2.2.2.2 active went from Active to Idle
*Aug 23 00:48:07.911: BGP: nbr global 2.2.2.2 Active open failed - open timer running
*Aug 23 00:48:07.911: BGP: nbr global 2.2.2.2 Active open failed - open timer running
```

b1 password_mismatch: RT02 `show ip bgp summary`:
```
BGP router identifier 2.2.2.2, local AS number 65001
BGP table version is 1, main routing table version 1

Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
1.1.1.1         4        65001       0       0        1    0    0 never    Idle
```

b1 password_mismatch: RT02 logging(debug 抜粋):
```
*Aug 23 00:47:37.912: %TCP-6-BADAUTH: Invalid MD5 digest from 1.1.1.1(39477) to 2.2.2.2(179) tableid - 0
*Aug 23 00:47:38.129: BGP: 1.1.1.1 active went from Idle to Active
*Aug 23 00:47:38.129: BGP: 1.1.1.1 open active, local address 2.2.2.2
*Aug 23 00:47:39.912: %TCP-6-BADAUTH: Invalid MD5 digest from 1.1.1.1(39477) to 2.2.2.2(179) tableid - 0
*Aug 23 00:47:43.912: %TCP-6-BADAUTH: Invalid MD5 digest from 1.1.1.1(39477) to 2.2.2.2(179) tableid - 0
*Aug 23 00:47:51.913: %TCP-6-BADAUTH: Invalid MD5 digest from 1.1.1.1(39477) to 2.2.2.2(179) tableid - 0
*Aug 23 00:48:08.129: BGP: 1.1.1.1 open failed: Connection timed out; remote host not responding
*Aug 23 00:48:08.129: BGP: 1.1.1.1 Active open failed - tcb is not available, open active delayed 10240ms (35000ms max, 60% jitter)
*Aug 23 00:48:08.129: BGP: ses global 1.1.1.1 (0x70F9F020C450:0) act Reset (Active open failed).
*Aug 23 00:48:08.129: BGP: 1.1.1.1 active went from Active to Idle
*Aug 23 00:48:08.129: BGP: nbr global 1.1.1.1 Active open failed - open timer running
*Aug 23 00:48:08.129: BGP: nbr global 1.1.1.1 Active open failed - open timer running
```

b1b password_oneside: RT01 `show ip bgp summary`:
```
BGP router identifier 1.1.1.1, local AS number 65001
BGP table version is 1, main routing table version 1

Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
2.2.2.2         4        65001       0       0        1    0    0 never    Idle
```

b1b password_oneside: RT01 logging(debug 抜粋):
```
*Aug 23 00:48:17.811: %TCP-6-BADAUTH: No MD5 digest from 2.2.2.2(179) to 1.1.1.1(50398) tableid - 0
*Aug 23 00:48:18.077: %TCP-6-BADAUTH: No MD5 digest from 2.2.2.2(21400) to 1.1.1.1(179) tableid - 0
*Aug 23 00:48:19.812: %TCP-6-BADAUTH: No MD5 digest from 2.2.2.2(179) to 1.1.1.1(50398) tableid - 0
*Aug 23 00:48:20.078: %TCP-6-BADAUTH: No MD5 digest from 2.2.2.2(21400) to 1.1.1.1(179) tableid - 0
*Aug 23 00:48:21.811: %TCP-6-BADAUTH: No MD5 digest from 2.2.2.2(179) to 1.1.1.1(50398) tableid - 0
*Aug 23 00:48:23.811: %TCP-6-BADAUTH: No MD5 digest from 2.2.2.2(179) to 1.1.1.1(50398) tableid - 0
*Aug 23 00:48:24.078: %TCP-6-BADAUTH: No MD5 digest from 2.2.2.2(21400) to 1.1.1.1(179) tableid - 0
*Aug 23 00:48:29.811: %TCP-6-BADAUTH: No MD5 digest from 2.2.2.2(179) to 1.1.1.1(50398) tableid - 0
*Aug 23 00:48:30.732: BGP: topo global:IPv4 Unicast:base Scanning routing tables
*Aug 23 00:48:30.732: BGP: topo global:IPv4 Multicast:base Scanning routing tables
*Aug 23 00:48:30.732: BGP: topo global:L2VPN E-VPN:base Scanning routing tables
*Aug 23 00:48:30.732: BGP: topo global:MVPNv4 Unicast:base Scanning routing tables
*Aug 23 00:48:31.811: %TCP-6-BADAUTH: No MD5 digest from 2.2.2.2(179) to 1.1.1.1(50398) tableid - 0
*Aug 23 00:48:32.078: %TCP-6-BADAUTH: No MD5 digest from 2.2.2.2(21400) to 1.1.1.1(179) tableid - 0
*Aug 23 00:48:45.811: BGP: ses global 2.2.2.2 (0x7161E623E350:0) act Reset (Active open failed).
*Aug 23 00:48:45.811: BGP: 2.2.2.2 active went from Active to Idle
*Aug 23 00:48:45.811: BGP: nbr global 2.2.2.2 Active open failed - open timer running
*Aug 23 00:48:45.811: BGP: nbr global 2.2.2.2 Active open failed - open timer running
```

b1b password_oneside: RT02 `show ip bgp summary`:
```
BGP router identifier 2.2.2.2, local AS number 65001
BGP table version is 1, main routing table version 1

Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
1.1.1.1         4        65001       0       0        1    0    0 never    Idle
```

b1b password_oneside: RT02 logging(debug 抜粋):
```
*Aug 23 00:48:31.977: BGP: topo global:IPv4 Unicast:base Scanning routing tables
*Aug 23 00:48:31.977: BGP: topo global:IPv4 Multicast:base Scanning routing tables
*Aug 23 00:48:31.977: BGP: topo global:L2VPN E-VPN:base Scanning routing tables
*Aug 23 00:48:31.977: BGP: topo global:MVPNv4 Unicast:base Scanning routing tables
*Aug 23 00:48:48.078: BGP: ses global 1.1.1.1 (0x70F9F020D070:0) act Reset (Active open failed).
*Aug 23 00:48:48.078: BGP: 1.1.1.1 active went from Active to Idle
*Aug 23 00:48:48.078: BGP: nbr global 1.1.1.1 Active open failed - open timer running
*Aug 23 00:48:48.078: BGP: nbr global 1.1.1.1 Active open failed - open timer running
```

## b2

b2 remote_as_wrong: RT01 `show ip bgp summary`:
```
BGP router identifier 1.1.1.1, local AS number 65001
BGP table version is 1, main routing table version 1

Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.0.12.2       4        65003       2       2        1    0    0 00:00:03 Closing
```

b2 remote_as_wrong: RT01 logging(debug 抜粋):
```
*Aug 23 00:49:41.283: BGP: 10.0.12.2 passive OPEN has CAPABILITY code: 128, length 0
*Aug 23 00:49:41.283: BGP: 10.0.12.2 passive OPEN has ROUTE-REFRESH capability(old) for all address-families
*Aug 23 00:49:41.283: BGP: 10.0.12.2 passive rcvd OPEN w/ optional parameter type 2 (Capability) len 2
*Aug 23 00:49:41.283: BGP: 10.0.12.2 passive OPEN has CAPABILITY code: 2, length 0
*Aug 23 00:49:41.283: BGP: 10.0.12.2 passive OPEN has ROUTE-REFRESH capability(new) for all address-families
*Aug 23 00:49:41.283: BGP: 10.0.12.2 passive rcvd OPEN w/ optional parameter type 2 (Capability) len 2
*Aug 23 00:49:41.283: BGP: 10.0.12.2 passive OPEN has CAPABILITY code: 70, length 0
*Aug 23 00:49:41.283: BGP: ses global 10.0.12.2 (0x7161E66482A8:0) pas Enhanced Refresh cap received in open message
*Aug 23 00:49:41.283: BGP: 10.0.12.2 passive rcvd OPEN w/ optional parameter type 2 (Capability) len 6
*Aug 23 00:49:41.283: BGP: 10.0.12.2 passive OPEN has CAPABILITY code: 65, length 4
*Aug 23 00:49:41.283: BGP: 10.0.12.2 passive OPEN has 4-byte ASN CAP for: 65002
*Aug 23 00:49:41.283: BGP: 10.0.12.2 passive bad OPEN, remote AS is 65002, expected 65003  
*Aug 23 00:49:41.283: BGP: 10.0.12.2 passive went from Connect to Closing
*Aug 23 00:49:41.283: %BGP-3-NOTIFICATION: sent to neighbor 10.0.12.2 passive 2/2 (peer in wrong AS) 2 bytes FDEA
*Aug 23 00:49:41.283: BGP: ses global 10.0.12.2 (0x7161E66482A8:0) pas Send NOTIFICATION 2/2 (peer in wrong AS) 2 bytes FDEA
*Aug 23 00:49:41.283: %BGP-4-MSGDUMP: unsupported or mal-formatted message received from 10.0.12.2: 
*Aug 23 00:49:41.321: BGP: 10.0.12.2 active went from Idle to Active
*Aug 23 00:49:41.321: BGP: 10.0.12.2 open active, local address 10.0.12.1
*Aug 23 00:49:41.322: BGP: ses global 10.0.12.2 (0x7161E6647C90:0) act Adding topology IPv4 Unicast:base
*Aug 23 00:49:41.322: BGP: ses global 10.0.12.2 (0x7161E6647C90:0) act Send OPEN
*Aug 23 00:49:41.322: BGP: ses global 10.0.12.2 (0x7161E6647C90:0) act Building Enhanced Refresh capability
*Aug 23 00:49:41.322: BGP: 10.0.12.2 active went from Active to OpenSent
*Aug 23 00:49:41.322: BGP: 10.0.12.2 active sending OPEN, version 4, my as: 65001, holdtime 180 seconds, ID 1010101
*Aug 23 00:49:41.323: BGP: 10.0.12.2 active rcv message type 1, length (excl. header) 38
*Aug 23 00:49:41.323: BGP: ses global 10.0.12.2 (0x7161E6647C90:0) act Receive OPEN
*Aug 23 00:49:41.323: BGP: 10.0.12.2 active rcv OPEN, version 4, holdtime 180 seconds
*Aug 23 00:49:41.323: BGP: 10.0.12.2 active rcv OPEN w/ OPTION parameter len: 28
*Aug 23 00:49:41.323: BGP: 10.0.12.2 active rcvd OPEN w/ optional parameter type 2 (Capability) len 6
*Aug 23 00:49:41.323: BGP: 10.0.12.2 active OPEN has CAPABILITY code: 1, length 4
*Aug 23 00:49:41.323: BGP: 10.0.12.2 active OPEN has MP_EXT CAP for afi/safi: 1/1
*Aug 23 00:49:41.323: BGP: 10.0.12.2 active rcvd OPEN w/ optional parameter type 2 (Capability) len 2
*Aug 23 00:49:41.323: BGP: 10.0.12.2 active OPEN has CAPABILITY code: 128, length 0
*Aug 23 00:49:41.323: BGP: 10.0.12.2 active OPEN has ROUTE-REFRESH capability(old) for all address-families
*Aug 23 00:49:41.323: BGP: 10.0.12.2 active rcvd OPEN w/ optional parameter type 2 (Capability) len 2
*Aug 23 00:49:41.323: BGP: 10.0.12.2 active OPEN has CAPABILITY code: 2, length 0
*Aug 23 00:49:41.323: BGP: 10.0.12.2 active OPEN has ROUTE-REFRESH capability(new) for all address-families
*Aug 23 00:49:41.323: BGP: 10.0.12.2 active rcvd OPEN w/ optional parameter type 2 (Capability) len 2
*Aug 23 00:49:41.323: BGP: 10.0.12.2 active OPEN has CAPABILITY code: 70, length 0
*Aug 23 00:49:41.323: BGP: ses global 10.0.12.2 (0x7161E6647C90:0) act Enhanced Refresh cap received in open message
*Aug 23 00:49:41.323: BGP: 10.0.12.2 active rcvd OPEN w/ optional parameter type 2 (Capability) len 6
*Aug 23 00:49:41.323: BGP: 10.0.12.2 active OPEN has CAPABILITY code: 65, length 4
*Aug 23 00:49:41.323: BGP: 10.0.12.2 active OPEN has 4-byte ASN CAP for: 65002
*Aug 23 00:49:41.323: BGP: 10.0.12.2 active bad OPEN, remote AS is 65002, expected 65003  
*Aug 23 00:49:41.323: BGP: 10.0.12.2 active went from OpenSent to Closing
*Aug 23 00:49:41.323: %BGP-3-NOTIFICATION: sent to neighbor 10.0.12.2 active 2/2 (peer in wrong AS) 2 bytes FDEA
*Aug 23 00:49:41.323: BGP: ses global 10.0.12.2 (0x7161E6647C90:0) act Send NOTIFICATION 2/2 (peer in wrong AS) 2 bytes FDEA
*Aug 23 00:49:41.323: %BGP-4-MSGDUMP: unsupported or mal-formatted message received from 10.0.12.2:
```

b2 remote_as_wrong: RT02 `show ip bgp summary`:
```
BGP router identifier 2.2.2.2, local AS number 65002
BGP table version is 1, main routing table version 1

Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.0.12.1       4        65001       0       0        1    0    0 never    Idle
```

b2 remote_as_wrong: RT02 logging(debug 抜粋):
```
g open delay timer to 60 seconds.
*Aug 23 00:49:41.323: BGP: 10.0.12.1 passive rcv message type 1, length (excl. header) 38
*Aug 23 00:49:41.323: BGP: ses global 10.0.12.1 (0x70F9F01CE648:0) pas Receive OPEN
*Aug 23 00:49:41.323: BGP: 10.0.12.1 passive rcv OPEN, version 4, holdtime 180 seconds
*Aug 23 00:49:41.323: BGP: 10.0.12.1 passive rcv OPEN w/ OPTION parameter len: 28
*Aug 23 00:49:41.323: BGP: 10.0.12.1 passive rcvd OPEN w/ optional parameter type 2 (Capability) len 6
*Aug 23 00:49:41.323: BGP: 10.0.12.1 passive OPEN has CAPABILITY code: 1, length 4
*Aug 23 00:49:41.323: BGP: 10.0.12.1 passive OPEN has MP_EXT CAP for afi/safi: 1/1
*Aug 23 00:49:41.323: BGP: 10.0.12.1 passive rcvd OPEN w/ optional parameter type 2 (Capability) len 2
*Aug 23 00:49:41.323: BGP: 10.0.12.1 passive OPEN has CAPABILITY code: 128, length 0
*Aug 23 00:49:41.323: BGP: 10.0.12.1 passive OPEN has ROUTE-REFRESH capability(old) for all address-families
*Aug 23 00:49:41.323: BGP: 10.0.12.1 passive rcvd OPEN w/ optional parameter type 2 (Capability) len 2
*Aug 23 00:49:41.323: BGP: 10.0.12.1 passive OPEN has CAPABILITY code: 2, length 0
*Aug 23 00:49:41.323: BGP: 10.0.12.1 passive OPEN has ROUTE-REFRESH capability(new) for all address-families
*Aug 23 00:49:41.323: BGP: 10.0.12.1 passive rcvd OPEN w/ optional parameter type 2 (Capability) len 2
*Aug 23 00:49:41.323: BGP: 10.0.12.1 passive OPEN has CAPABILITY code: 70, length 0
*Aug 23 00:49:41.323: BGP: ses global 10.0.12.1 (0x70F9F01CE648:0) pas Enhanced Refresh cap received in open message
*Aug 23 00:49:41.323: BGP: 10.0.12.1 passive rcvd OPEN w/ optional parameter type 2 (Capability) len 6
*Aug 23 00:49:41.323: BGP: 10.0.12.1 passive OPEN has CAPABILITY code: 65, length 4
*Aug 23 00:49:41.323: BGP: 10.0.12.1 passive OPEN has 4-byte ASN CAP for: 65001
*Aug 23 00:49:41.323: BGP: 10.0.12.1 passive rcvd OPEN w/ remote AS 65001, 4-byte remote AS 65001
*Aug 23 00:49:41.323: BGP: ses global 10.0.12.1 (0x70F9F01CE648:0) pas Adding topology IPv4 Unicast:base
*Aug 23 00:49:41.323: BGP: ses global 10.0.12.1 (0x70F9F01CE648:0) pas Send OPEN
*Aug 23 00:49:41.323: BGP: ses global 10.0.12.1 (0x70F9F01CE648:0) pas Building Enhanced Refresh capability
*Aug 23 00:49:41.323: BGP: 10.0.12.1 passive went from Connect to OpenSent
*Aug 23 00:49:41.323: BGP: 10.0.12.1 passive sending OPEN, version 4, my as: 65002, holdtime 180 seconds, ID 2020202
*Aug 23 00:49:41.323: BGP: 10.0.12.1 passive went from OpenSent to OpenConfirm
*Aug 23 00:49:41.323: BGP: 10.0.12.1 passive rcv message type 3, length (excl. header) 4
*Aug 23 00:49:41.323: %BGP-3-NOTIFICATION: received from neighbor 10.0.12.1 passive 2/2 (peer in wrong AS) 2 bytes FDEA
*Aug 23 00:49:41.323: BGP: ses global 10.0.12.1 (0x70F9F01CE648:0) pas Receive NOTIFICATION 2/2 (peer in wrong AS) 2 bytes FDEA
*Aug 23 00:49:41.323: %BGP-5-NBR_RESET: Neighbor 10.0.12.1 passive reset (BGP Notification received)
*Aug 23 00:49:41.323: BGP: ses global 10.0.12.1 (0x70F9F01CE648:0) pas Reset (BGP Notification received).
*Aug 23 00:49:41.324: BGP: 10.0.12.1 passive went from OpenConfirm to Closing
*Aug 23 00:49:41.324: BGP: nbr_topo global 10.0.12.1 IPv4 Unicast:base (0x70F9F01CE648:0) NSF delete stale NSF not active
*Aug 23 00:49:41.324: BGP: nbr_topo global 10.0.12.1 IPv4 Unicast:base (0x70F9F01CE648:0) NSF no stale paths state is NSF not active
*Aug 23 00:49:41.324: BGP: nbr_topo global 10.0.12.1 IPv4 Unicast:base (0x70F9F01CE648:0) Resetting ALL counters.
*Aug 23 00:49:41.324: BGP: 10.0.12.1 passive(0x70F9F01CE648) closing
*Aug 23 00:49:41.324: BGP: ses global 10.0.12.1 (0x70F9F01CE648:0) pas Session close and reset neighbor 10.0.12.1 topostate
*Aug 23 00:49:41.324: BGP: nbr_topo global 10.0.12.1 IPv4 Unicast:base (0x70F9F01CE648:0) Resetting ALL counters.
*Aug 23 00:49:41.324: BGP: 10.0.12.1 passive went from Closing to Idle
*Aug 23 00:49:41.324: %BGP-5-ADJCHANGE: neighbor 10.0.12.1 passive Down BGP Notification received
*Aug 23 00:49:41.324: %BGP_SESSION-5-ADJCHANGE: neighbor 10.0.12.1 IPv4 Unicast topology base removed from session  BGP Notification received
*Aug 23 00:49:41.324: BGP: ses global 10.0.12.1 (0x70F9F01CE648:0) pas Removed topology IPv4 Unicast:base
*Aug 23 00:49:41.324: BGP: ses global 10.0.12.1 (0x70F9F01CE648:0) pas Removed last topology
*Aug 23 00:49:41.324: BGP: nbr global 10.0.12.1 Active open failed - open timer running
*Aug 23 00:49:41.324: BGP: nbr global 10.0.12.1 Active open failed - open timer running
```

## b3

b3 nbr_shutdown: RT01 `show ip bgp summary`:
```
BGP router identifier 1.1.1.1, local AS number 65001
BGP table version is 1, main routing table version 1

Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
2.2.2.2         4        65001       0       0        1    0    0 never    Idle (Admin)
```

b3 nbr_shutdown: RT01 logging(debug 抜粋):
```

```

b3 nbr_shutdown: RT02 `show ip bgp summary`:
```
BGP router identifier 2.2.2.2, local AS number 65001
BGP table version is 1, main routing table version 1

Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
1.1.1.1         4        65001       0       0        1    0    0 never    Idle
```

b3 nbr_shutdown: RT02 logging(debug 抜粋):
```
*Aug 23 00:50:02.576: BGP: 1.1.1.1 active went from Idle to Active
*Aug 23 00:50:02.576: BGP: 1.1.1.1 open active, local address 2.2.2.2
*Aug 23 00:50:02.576: BGP: 1.1.1.1 open failed: Connection refused by remote host
*Aug 23 00:50:02.576: BGP: 1.1.1.1 Active open failed - tcb is not available, open active delayed 13312ms (35000ms max, 60% jitter)
*Aug 23 00:50:02.576: BGP: ses global 1.1.1.1 (0x70F9F017C1E0:0) act Reset (Active open failed).
*Aug 23 00:50:02.576: BGP: 1.1.1.1 active went from Active to Idle
*Aug 23 00:50:02.576: BGP: nbr global 1.1.1.1 Active open failed - open timer running
*Aug 23 00:50:02.576: BGP: nbr global 1.1.1.1 Active open failed - open timer running
*Aug 23 00:50:15.891: BGP: 1.1.1.1 active went from Idle to Active
*Aug 23 00:50:15.891: BGP: 1.1.1.1 open active, local address 2.2.2.2
*Aug 23 00:50:15.892: BGP: 1.1.1.1 open failed: Connection refused by remote host
*Aug 23 00:50:15.892: BGP: 1.1.1.1 Active open failed - tcb is not available, open active delayed 14336ms (35000ms max, 60% jitter)
*Aug 23 00:50:15.892: BGP: ses global 1.1.1.1 (0x70F9F01CF2A8:0) act Reset (Active open failed).
*Aug 23 00:50:15.892: BGP: 1.1.1.1 active went from Active to Idle
*Aug 23 00:50:15.892: BGP: nbr global 1.1.1.1 Active open failed - open timer running
*Aug 23 00:50:15.892: BGP: nbr global 1.1.1.1 Active open failed - open timer running
*Aug 23 00:50:30.232: BGP: 1.1.1.1 active went from Idle to Active
*Aug 23 00:50:30.232: BGP: 1.1.1.1 open active, local address 2.2.2.2
*Aug 23 00:50:30.232: BGP: 1.1.1.1 open failed: Connection refused by remote host
*Aug 23 00:50:30.233: BGP: 1.1.1.1 Active open failed - tcb is not available, open active delayed 7168ms (35000ms max, 60% jitter)
*Aug 23 00:50:30.233: BGP: ses global 1.1.1.1 (0x70F9F01CF2A8:0) act Reset (Active open failed).
*Aug 23 00:50:30.233: BGP: 1.1.1.1 active went from Active to Idle
*Aug 23 00:50:30.233: BGP: nbr global 1.1.1.1 Active open failed - open timer running
*Aug 23 00:50:30.233: BGP: nbr global 1.1.1.1 Active open failed - open timer running
```
