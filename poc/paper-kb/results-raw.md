
## P0 基線  (2026-09-18 12:53)

- RT01: admin-down IF あり(CVAC 罠)→ no shutdown を投入

**P0 基線 — RT01 show ip interface brief**

```
Interface              IP-Address      OK? Method Status                Protocol
Ethernet0/0            10.0.12.1       YES TFTP   up                    up      
Ethernet0/1            unassigned      YES unset  up                    up      
Ethernet0/2            unassigned      YES unset  up                    up      
Ethernet0/3            unassigned      YES unset  up                    up      
Ethernet1/0            unassigned      YES unset  up                    up      
Ethernet1/1            unassigned      YES unset  up                    up      
Ethernet1/2            unassigned      YES unset  up                    up      
Ethernet1/3            unassigned      YES unset  up                    up      
Ethernet2/0            unassigned      YES unset  up                    up      
Ethernet2/1            unassigned      YES unset  up                    up      
Ethernet2/2            unassigned      YES unset  up                    up      
Ethernet2/3            unassigned      YES unset  up                    up      
Ethernet3/0            unassigned      YES unset  up                    up      
Ethernet3/1            unassigned      YES unset  up                    up      
Ethernet3/2            unassigned      YES unset  up                    up      
Ethernet3/3            unassigned      YES unset  up                    up      
Ethernet4/0            unassigned      YES unset  up                    up      
Ethernet4/1            unassigned      YES unset  up                    up      
Ethernet4/2            unassigned      YES unset  up                    up      
Ethernet4/3            unassigned      YES unset  up                    up      
Ethernet5/0            unassigned      YES unset  up                    up      
Ethernet5/1            unassigned      YES unset  up                    up      
Ethernet5/2            unassigned      YES unset  up                    up      
Ethernet5/3            unassigned      YES unset  up                    up      
Ethernet6/0            unassigned      YES unset  up                    up      
Ethernet6/1            unassigned      YES unset  up                    up      
Ethernet6/2            unassigned      YES unset  up                    up      
Ethernet6/3            unassigned      YES unset  up                    up      
Ethernet7/0            unassigned      YES unset  up                    up      
Ethernet7/1            unassigned      YES unset  up                    up      
Ethernet7/2            unassigned      YES unset  up                    up      
Ethernet7/3            unassigned      YES unset  up                    up      
Loopback0              1.1.1.1         YES TFTP   up                    up
```

**P0 — RT01 show version | include Software|uptime**

```
Cisco IOS Software [IOSXE], Linux Software (X86_64BI_LINUX-ADVENTERPRISEK9-M), Version 17.15.1, RELEASE SOFTWARE (fc4)
RT01 uptime is 1 minute
```

- RT02: admin-down IF あり(CVAC 罠)→ no shutdown を投入

**P0 基線 — RT02 show ip interface brief**

```
Interface              IP-Address      OK? Method Status                Protocol
Ethernet0/0            10.0.12.2       YES TFTP   up                    up      
Ethernet0/1            10.0.23.2       YES TFTP   up                    up      
Ethernet0/2            unassigned      YES unset  up                    up      
Ethernet0/3            unassigned      YES unset  up                    up      
Ethernet1/0            unassigned      YES unset  up                    up      
Ethernet1/1            unassigned      YES unset  up                    up      
Ethernet1/2            unassigned      YES unset  up                    up      
Ethernet1/3            unassigned      YES unset  up                    up      
Ethernet2/0            unassigned      YES unset  up                    up      
Ethernet2/1            unassigned      YES unset  up                    up      
Ethernet2/2            unassigned      YES unset  up                    up      
Ethernet2/3            unassigned      YES unset  up                    up      
Ethernet3/0            unassigned      YES unset  up                    up      
Ethernet3/1            unassigned      YES unset  up                    up      
Ethernet3/2            unassigned      YES unset  up                    up      
Ethernet3/3            unassigned      YES unset  up                    up      
Ethernet4/0            unassigned      YES unset  up                    up      
Ethernet4/1            unassigned      YES unset  up                    up      
Ethernet4/2            unassigned      YES unset  up                    up      
Ethernet4/3            unassigned      YES unset  up                    up      
Ethernet5/0            unassigned      YES unset  up                    up      
Ethernet5/1            unassigned      YES unset  up                    up      
Ethernet5/2            unassigned      YES unset  up                    up      
Ethernet5/3            unassigned      YES unset  up                    up      
Ethernet6/0            unassigned      YES unset  up                    up      
Ethernet6/1            unassigned      YES unset  up                    up      
Ethernet6/2            unassigned      YES unset  up                    up      
Ethernet6/3            unassigned      YES unset  up                    up      
Ethernet7/0            unassigned      YES unset  up                    up      
Ethernet7/1            unassigned      YES unset  up                    up      
Ethernet7/2            unassigned      YES unset  up                    up      
Ethernet7/3            unassigned      YES unset  up                    up      
Loopback0              2.2.2.2         YES TFTP   up                    up
```

**P0 — RT02 show version | include Software|uptime**

```
Cisco IOS Software [IOSXE], Linux Software (X86_64BI_LINUX-ADVENTERPRISEK9-M), Version 17.15.1, RELEASE SOFTWARE (fc4)
RT02 uptime is 1 minute
```

- RT03: admin-down IF あり(CVAC 罠)→ no shutdown を投入

**P0 基線 — RT03 show ip interface brief**

```
Interface              IP-Address      OK? Method Status                Protocol
Ethernet0/0            10.0.34.3       YES TFTP   up                    up      
Ethernet0/1            10.0.23.3       YES TFTP   up                    up      
Ethernet0/2            unassigned      YES unset  up                    up      
Ethernet0/3            unassigned      YES unset  up                    up      
Ethernet1/0            unassigned      YES unset  up                    up      
Ethernet1/1            unassigned      YES unset  up                    up      
Ethernet1/2            unassigned      YES unset  up                    up      
Ethernet1/3            unassigned      YES unset  up                    up      
Ethernet2/0            unassigned      YES unset  up                    up      
Ethernet2/1            unassigned      YES unset  up                    up      
Ethernet2/2            unassigned      YES unset  up                    up      
Ethernet2/3            unassigned      YES unset  up                    up      
Ethernet3/0            unassigned      YES unset  up                    up      
Ethernet3/1            unassigned      YES unset  up                    up      
Ethernet3/2            unassigned      YES unset  up                    up      
Ethernet3/3            unassigned      YES unset  up                    up      
Ethernet4/0            unassigned      YES unset  up                    up      
Ethernet4/1            unassigned      YES unset  up                    up      
Ethernet4/2            unassigned      YES unset  up                    up      
Ethernet4/3            unassigned      YES unset  up                    up      
Ethernet5/0            unassigned      YES unset  up                    up      
Ethernet5/1            unassigned      YES unset  up                    up      
Ethernet5/2            unassigned      YES unset  up                    up      
Ethernet5/3            unassigned      YES unset  up                    up      
Ethernet6/0            unassigned      YES unset  up                    up      
Ethernet6/1            unassigned      YES unset  up                    up      
Ethernet6/2            unassigned      YES unset  up                    up      
Ethernet6/3            unassigned      YES unset  up                    up      
Ethernet7/0            unassigned      YES unset  up                    up      
Ethernet7/1            unassigned      YES unset  up                    up      
Ethernet7/2            unassigned      YES unset  up                    up      
Ethernet7/3            unassigned      YES unset  up                    up      
Loopback0              3.3.3.3         YES TFTP   up                    up
```

**P0 — RT03 show version | include Software|uptime**

```
Cisco IOS Software [IOSXE], Linux Software (X86_64BI_LINUX-ADVENTERPRISEK9-M), Version 17.15.1, RELEASE SOFTWARE (fc4)
RT03 uptime is 1 minute
```

- RT04: admin-down IF あり(CVAC 罠)→ no shutdown を投入

**P0 基線 — RT04 show ip interface brief**

```
Interface              IP-Address      OK? Method Status                Protocol
Ethernet0/0            10.0.34.4       YES TFTP   up                    up      
Ethernet0/1            unassigned      YES unset  up                    up      
Ethernet0/2            unassigned      YES unset  up                    up      
Ethernet0/3            unassigned      YES unset  up                    up      
Ethernet1/0            unassigned      YES unset  up                    up      
Ethernet1/1            unassigned      YES unset  up                    up      
Ethernet1/2            unassigned      YES unset  up                    up      
Ethernet1/3            unassigned      YES unset  up                    up      
Ethernet2/0            unassigned      YES unset  up                    up      
Ethernet2/1            unassigned      YES unset  up                    up      
Ethernet2/2            unassigned      YES unset  up                    up      
Ethernet2/3            unassigned      YES unset  up                    up      
Ethernet3/0            unassigned      YES unset  up                    up      
Ethernet3/1            unassigned      YES unset  up                    up      
Ethernet3/2            unassigned      YES unset  up                    up      
Ethernet3/3            unassigned      YES unset  up                    up      
Ethernet4/0            unassigned      YES unset  up                    up      
Ethernet4/1            unassigned      YES unset  up                    up      
Ethernet4/2            unassigned      YES unset  up                    up      
Ethernet4/3            unassigned      YES unset  up                    up      
Ethernet5/0            unassigned      YES unset  up                    up      
Ethernet5/1            unassigned      YES unset  up                    up      
Ethernet5/2            unassigned      YES unset  up                    up      
Ethernet5/3            unassigned      YES unset  up                    up      
Ethernet6/0            unassigned      YES unset  up                    up      
Ethernet6/1            unassigned      YES unset  up                    up      
Ethernet6/2            unassigned      YES unset  up                    up      
Ethernet6/3            unassigned      YES unset  up                    up      
Ethernet7/0            unassigned      YES unset  up                    up      
Ethernet7/1            unassigned      YES unset  up                    up      
Ethernet7/2            unassigned      YES unset  up                    up      
Ethernet7/3            unassigned      YES unset  up                    up      
Loopback0              4.4.4.4         YES TFTP   up                    up
```

**P0 — RT04 show version | include Software|uptime**

```
Cisco IOS Software [IOSXE], Linux Software (X86_64BI_LINUX-ADVENTERPRISEK9-M), Version 17.15.1, RELEASE SOFTWARE (fc4)
RT04 uptime is 2 minutes
```

**P0 疎通 RT01→RT04(static 連鎖) — RT01# ping 10.0.34.4 repeat 3 → 100%**

```
Type escape sequence to abort.
Sending 3, 100-byte ICMP Echos to 10.0.34.4, timeout is 2 seconds:
!!!
Success rate is 100 percent (3/3), round-trip min/avg/max = 1/1/2 ms
```

**P0 疎通 RT04→RT01 — RT04# ping 10.0.12.1 repeat 3 → 100%**

```
Type escape sequence to abort.
Sending 3, 100-byte ICMP Echos to 10.0.12.1, timeout is 2 seconds:
!!!
Success rate is 100 percent (3/3), round-trip min/avg/max = 1/2/3 ms
```

## P1 (失敗)  (2026-09-18 12:53)

**P1 eigrp named: (config-router) — RT01: router eigrp NAMED : ?**

```
?
Router configuration commands:
  address-family  Enter Address Family command mode
  default         Set a command to its defaults
  exit            Exit from routing protocol configuration mode
  no              Negate a command or set its defaults
  service-family  Enter Service Family command mode
  shutdown        Shutdown this instance of EIGRP

RT01(config-router)#
```

**P1 eigrp named: (config-router-af) — RT01: router eigrp NAMED / address-family ipv4 unicast autonomous-system 100 : ?**

```
?
Address Family configuration commands:
  af-interface         Enter Address Family interface configuration
  default              Set a command to its defaults
  eigrp                EIGRP Address Family specific commands
  exit-address-family  Exit Address Family configuration mode
  help                 Description of the interactive help system
  maximum-prefix       Maximum number of prefixes acceptable in aggregate
  metric               Modify metrics and parameters for address advertisement
  neighbor             Specify an IPv4 neighbor router
  network              Enable routing on an IP network
  no                   Negate a command or set its defaults
  remote-neighbors     Specify IPv4 service remote neighbors
  shutdown             Shutdown address family
  soft-sia             Enable graceful restart for stuck-in-active neighbors
  timers               Adjust peering based timers
  topology             Topology configuration mode

RT01(config-router-af)#
```

**P1 eigrp named: (config-router-af-interface) — RT01: router eigrp NAMED / address-family ipv4 unicast autonomous-system 100 / af-interface default : ?**

```
?
Address Family Interfaces configuration commands:
  add-paths           Advertise add paths
  authentication      authentication subcommands
  bandwidth-percent   Set percentage of bandwidth percentage limit
  bfd                 Enable Bidirectional Forwarding Detection
  dampening-change    Percent interface metric must change to cause update
  dampening-interval  Time in seconds to check interface metrics
  default             Set a command to its defaults
  exit-af-interface   Exit from Address Family Interface configuration mode
  hello-interval      Configures hello interval
  hold-time           Configures hold time
  next-hop-self       Configures EIGRP next-hop-self
  no                  Negate a command or set its defaults
  passive-interface   Suppress address updates on an interface
  shutdown            Disable Address-Family on interface
  split-horizon       Perform split horizon

RT01(config-router-af-interface)#
```

**P1 eigrp named: (config-router-af-topology) — RT01: router eigrp NAMED / address-family ipv4 unicast autonomous-system 100 / topology base : ?**

```
?
Address Family Topology configuration commands:
  auto-summary             Enable automatic network number summarization
  cts                      EIGRP Trustsec Configuration
  default                  Set a command to its defaults
  default-information      Control distribution of default information
  default-metric           Set metric of redistributed routes
  distance                 Define an administrative distance
  distribute-list          Filter entries in eigrp updates
  eigrp                    EIGRP specific commands
  exit-af-topology         Exit from Address Family Topology configuration mode
  fast-reroute             Configure Fast-Reroute
  maximum-paths            Forward packets over multiple paths
  maximum-secondary-paths  Maximum secondary paths
  metric                   Modify metrics and parameters for advertisement
  no                       Negate a command or set its defaults
  offset-list              Add or subtract offset from EIGRP metrics
  redistribute             Redistribute IPv4 routes from another routing protocol
  snmp                     Modify snmp parameters
  summary-metric           Specify summary to apply metric/filtering
  table-map                Map external entry attributes into routing table
  timers                   Adjust topology specific timers
  topo-interface           Enter Topology interface configuration
  traffic-share            How to compute traffic share over alternate paths
  variance                 Control load balancing variance

RT01(config-router-af-topology)#
```

**P1 EXCEPTION**

```
Traceback (most recent call last):
  File "/home/suzuki/ansible/CCNP01/poc/paper-kb/sweep.py", line 740, in main
    STEPS[s](devs)
  File "/home/suzuki/ansible/CCNP01/poc/paper-kb/sweep.py", line 313, in P1
    help_capture(d, ["router eigrp NAMED", "address-family ipv4 unicast autonomous-system 100"], "eigrp ",
  File "/home/suzuki/ansible/CCNP01/poc/paper-kb/sweep.py", line 267, in help_capture
    out = xp(r"\)#" + re.escape(query) + r"\s*$")
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/suzuki/ansible/CCNP01/poc/paper-kb/sweep.py", line 258, in xp
    sp.expect([pat], timeout=t)
  File "src/unicon/eal/backend/spawn.py", line 364, in unicon.eal.backend.spawn.RawSpawn.expect
unicon.core.errors.TimeoutError: Timeout occurred
```

## P2 debug ip packet  (2026-09-18 12:54)

- P2a forus(自ルータ宛を受信): ping RT01→10.0.12.2 = -1%

**P2a forus(自ルータ宛を受信) — RT02 show logging**

```

```

- P2b transit(中継 forward): ping RT01→10.0.23.3 = -1%

**P2b transit(中継 forward) — RT02 show logging**

```

```

- P2c local 発(自ルータ発): ping RT02→10.0.12.1 = 100%

**P2c local 発(自ルータ発) — RT02 show logging**

```
*Sep 18 12:54:06.158: IP: tableid=0, s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0) nexthop=10.0.12.1, routed via FIB
*Sep 18 12:54:06.158: IP: s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0), len 100, sending
*Sep 18 12:54:06.158: IP: s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0), len 100, sending full packet
*Sep 18 12:54:06.159: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.12.2 (nil), len 100, input feature, MCI Check(110), rtype 0, forus FALSE, sendself FALSE, mtu 0, fwdchk FALSE
*Sep 18 12:54:06.160: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.12.2 (nil), len 100, rcvd 2
*Sep 18 12:54:06.160: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.12.2 (nil), len 100, stop process pak for forus packet
*Sep 18 12:54:06.160: IP: tableid=0, s=10.0.12.1 (Ethernet0/0), d=10.0.12.2 (Ethernet0/0) nexthop=10.0.12.2, routed via RIB
*Sep 18 12:54:06.160: IP: tableid=0, s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0) nexthop=10.0.12.1, routed via FIB
*Sep 18 12:54:06.160: IP: s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0), len 100, sending
*Sep 18 12:54:06.160: IP: s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0), len 100, sending full packet
*Sep 18 12:54:06.164: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.12.2 (nil), len 100, input feature, MCI Check(110), rtype 0, forus FALSE, sendself FALSE, mtu 0, fwdchk FALSE
*Sep 18 12:54:06.164: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.12.2 (nil), len 100, rcvd 2
*Sep 18 12:54:06.164: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.12.2 (nil), len 100, stop process pak for forus packet
*Sep 18 12:54:06.164: IP: tableid=0, s=10.0.12.1 (Ethernet0/0), d=10.0.12.2 (Ethernet0/0) nexthop=10.0.12.2, routed via RIB
```

- P2d unroutable(経路なし): ping RT01→172.31.99.1 = -1%

**P2d unroutable(経路なし) — RT02 show logging**

```

```

- P2e access denied(inbound ACL で拒否): ping RT01→10.0.23.3 = -1%

**P2e access denied(inbound ACL で拒否) — RT02 show logging**

```

```

- P2f encapsulation failed(next-hop が ARP 応答しない): ping RT01→172.31.100.1 = -1%

**P2f encapsulation failed(next-hop が ARP 応答しない) — RT02 show logging**

```

```

- P2g detail(forus・ICMP type/code): ping RT01→10.0.12.2 = -1%

**P2g detail(forus・ICMP type/code) — RT02 show logging**

```

```

- P2h detail(transit): ping RT01→10.0.23.3 = -1%

**P2h detail(transit) — RT02 show logging**

```

```

## P1 `?` ヘルプ採取  (2026-09-18 12:57)

**P1 eigrp named: (config-router) — RT01: router eigrp NAMED : ?**

```
?
Router configuration commands:
  address-family  Enter Address Family command mode
  default         Set a command to its defaults
  exit            Exit from routing protocol configuration mode
  no              Negate a command or set its defaults
  service-family  Enter Service Family command mode
  shutdown        Shutdown this instance of EIGRP

RT01(config-router)#
```

**P1 eigrp named: (config-router-af) — RT01: router eigrp NAMED / address-family ipv4 unicast autonomous-system 100 : ?**

```
?
Address Family configuration commands:
  af-interface         Enter Address Family interface configuration
  default              Set a command to its defaults
  eigrp                EIGRP Address Family specific commands
  exit-address-family  Exit Address Family configuration mode
  help                 Description of the interactive help system
  maximum-prefix       Maximum number of prefixes acceptable in aggregate
  metric               Modify metrics and parameters for address advertisement
  neighbor             Specify an IPv4 neighbor router
  network              Enable routing on an IP network
  no                   Negate a command or set its defaults
  remote-neighbors     Specify IPv4 service remote neighbors
  shutdown             Shutdown address family
  soft-sia             Enable graceful restart for stuck-in-active neighbors
  timers               Adjust peering based timers
  topology             Topology configuration mode

RT01(config-router-af)#
```

**P1 eigrp named: (config-router-af-interface) — RT01: router eigrp NAMED / address-family ipv4 unicast autonomous-system 100 / af-interface default : ?**

```
?
Address Family Interfaces configuration commands:
  add-paths           Advertise add paths
  authentication      authentication subcommands
  bandwidth-percent   Set percentage of bandwidth percentage limit
  bfd                 Enable Bidirectional Forwarding Detection
  dampening-change    Percent interface metric must change to cause update
  dampening-interval  Time in seconds to check interface metrics
  default             Set a command to its defaults
  exit-af-interface   Exit from Address Family Interface configuration mode
  hello-interval      Configures hello interval
  hold-time           Configures hold time
  next-hop-self       Configures EIGRP next-hop-self
  no                  Negate a command or set its defaults
  passive-interface   Suppress address updates on an interface
  shutdown            Disable Address-Family on interface
  split-horizon       Perform split horizon

RT01(config-router-af-interface)#
```

**P1 eigrp named: (config-router-af-topology) — RT01: router eigrp NAMED / address-family ipv4 unicast autonomous-system 100 / topology base : ?**

```
?
Address Family Topology configuration commands:
  auto-summary             Enable automatic network number summarization
  cts                      EIGRP Trustsec Configuration
  default                  Set a command to its defaults
  default-information      Control distribution of default information
  default-metric           Set metric of redistributed routes
  distance                 Define an administrative distance
  distribute-list          Filter entries in eigrp updates
  eigrp                    EIGRP specific commands
  exit-af-topology         Exit from Address Family Topology configuration mode
  fast-reroute             Configure Fast-Reroute
  maximum-paths            Forward packets over multiple paths
  maximum-secondary-paths  Maximum secondary paths
  metric                   Modify metrics and parameters for advertisement
  no                       Negate a command or set its defaults
  offset-list              Add or subtract offset from EIGRP metrics
  redistribute             Redistribute IPv4 routes from another routing protocol
  snmp                     Modify snmp parameters
  summary-metric           Specify summary to apply metric/filtering
  table-map                Map external entry attributes into routing table
  timers                   Adjust topology specific timers
  topo-interface           Enter Topology interface configuration
  traffic-share            How to compute traffic share over alternate paths
  variance                 Control load balancing variance

RT01(config-router-af-topology)#
```

**P1 eigrp named af: eigrp ? — RT01: router eigrp NAMED / address-family ipv4 unicast autonomous-system 100 : eigrp ?**

```
eigrp ?
  default-route-tag      Default Route Tag for the Internal Routes
  graceful-restart       Peer resync without adjancency reset
  kill-everyone          Kill all adjacencies on SIA
  log-neighbor-changes   Enable/Disable EIGRP neighbor logging
  log-neighbor-warnings  Enable/Disable EIGRP neighbor warnings
  router-id              router id for this EIGRP process
  stub                   Set address-family in stubbed mode
  stub-site              Set address-family in stub-site mode

RT01(config-router-af)#eigrp
```

**P1 eigrp named af-interface: authentication ? — RT01: router eigrp NAMED / address-family ipv4 unicast autonomous-system 100 / af-interface default : authentication ?**

```
authentication ?
  key-chain  key-chain
  mode       authentication mode

RT01(config-router-af-interface)#authentication
```

**P1 eigrp named af-topology: redistribute ? — RT01: router eigrp NAMED / address-family ipv4 unicast autonomous-system 100 / topology base : redistribute ?**

```
redistribute ?
  application     Application
  bgp             Border Gateway Protocol (BGP)
  connected       Connected
  eigrp           Enhanced Interior Gateway Routing Protocol (EIGRP)
  isis            ISO IS-IS
  lisp            Locator ID Separation Protocol (LISP)
  maximum-prefix  Maximum number of prefixes redistributed to protocol
  mobile          Mobile routes
  nat-route       Network Address Translation (NAT) Route
  nhrp            Next Hop Resolution Protocol (NHRP)
  odr             On Demand stub Routes
  omp             Overlay Management Protocol
  ospf            Open Shortest Path First (OSPF)
  ospfv3          OSPFv3
  rip             Routing Information Protocol (RIP)
  static          Static routes
  vrf             Specify a source virtual routing/forwarding instance

RT01(config-router-af-topology)#redistribute
```

**P1 eigrp classic: (config-router) — RT01: router eigrp 100 : ?**

```
?
Configure commands:
  aaa                         Authentication, Authorization and Accounting.
  access-list                 Add an access list entry
  accounting                  Policy accounting feature
  alias                       Create command alias
  alps                        Configure Airline Protocol Support
  ancp                        Configure ANCP
  apollo                      Apollo global configuration commands
  appletalk                   Appletalk global configuration commands
  arap                        Appletalk Remote Access Protocol
  archive                     Archive the configuration
  arp                         Set a static ARP entry
  async-bootp                 Modify system bootp parameters
  auto                        Configure Automation
  auto-ip-ring                Auto-IP-Ring global configuration commands
  avc                         Application visibility and control
  banner                      Define a login banner
  bba-group                   Configure BBA Group
  beep                        Configure BEEP (Blocks Extensible Exchange Protocol)
  bfd                         BFD configuration commands
  bfd-template                BFD template configuration
  boot                        Modify system boot parameters
  boot-end-marker             boot-end-marker
  boot-start-marker           boot-start-marker
  bridge                      Bridge Group.
  bridge-domain               Bridge-domain global configuration commands
  bstun                       BSTUN global configuration commands
  buffers                     Adjust system buffer pool parameters
  bulkstat                    Bulkstat Application
  busy-message                Display message when connection to host fails
  call                        Configure Call parameters
  cdp                         Global CDP configuration subcommands
  cef                         Cisco Express Forwarding
  cfg-mode                    Enter configuration mode
  chat-script                 Define a modem chat script
  class-map                   Configure CPL Class Map
  classmap-template           create a parameterized class from base class
  clns                        Global CLNS configuration subcommands
  clock                       Configure time-of-day clock
  cns                         CNS agents
  config-register             Define the configuration register
  configuration               Configuration access
  connect                     cross-connect two interfaces
  control-plane               Configure control plane services
  cops                        Common Open Policy Service (COPS)
  crypto                      Encryption module
  cts                         Cisco Trusted Security commands
  dapr                        Dynamic Application Policy Routing (DAPR) configuration
  decnet                      Global DECnet configuration subcommands
  default                     Set a command to its defaults
  default-value               Default character-bits values
  define                      interface range macro definition
  device-tracking             Device tracking configuration commands
  dialer                      Dialer commands
  dialer-list                 Create a dialer list entry
  dlsw                        Data Link Switching global configuration commands
  dnsix-dmdp                  Provide DMDP service for DNSIX
  dnsix-nat                   Provide DNSIX service for audit trails
  do-exec                     To run exec commands in config mode
  downward-compatible-config  Generate a configuration compatible with older software
  dspu                        DownStream Physical Unit Command
  eap                         EAP Global Configuration Commands
  enable                      Modify enable password parameters
  end                         Exit from configure mode
  esmc                        Ethernet Synchronization Messaging Channel
  ethernet                    Ethernet configuration
  event                       Event related configuration commands
  exception                   Exception handling
  exception-slave             exception-slave
  exit                        Exit from configure mode
  fhrp                        Configure First Hop Redundancy Protocols
  file                        Adjust file system parameters
  flow                        Global Flow configuration subcommands
  flow-sampler-map            Flow sampler configuration
  flowspec                    FlowSpec configuration
  format                      Format the output
  fqdn                        fqdn config commands
  frame-relay                 global frame relay configuration commands
  global-address-family       Enter address-family base routing topology mode
  graceful-reload             graceful reload configuration
  group-policy                Group-policy configuration
  gtp                         Enable GTP Gn'
  help                        Description of the interactive help system
  hostname                    Set system's network name
  hw-module                   Control of individual components in the system
  id-manager                  ID Pool Manager
  interface                   Select an interface to configure
  ip                          Global IP configuration subcommands
  ipc                         Configure IPC system
  ipv6                        Global IPv6 configuration commands
  ipx                         Novell/IPX global configuration commands
  isis                        Global ISIS configuration subcommands
  kerberos                    Configure Kerberos
  key                         Key management
  keymap                      Define a new keymap
  kron                        Kron interval Facility
  l2                          Layer 2 configuration
  l2tp                        Layer 2 Tunneling Protocol (L2TP) parameters
  l2tp-class                  l2tp-class configuration
  l2vpn                       Layer2 VPN commands
  l3vpn                       l3vpn encapsulation ip commands
  lacp                        LACP configuration
  lat                         DEC Local Area Transport (LAT) transmission protocol
  li-view                     LI View
  line                        Configure a terminal line
  lldp                        Global LLDP configuration subcommands
  lnm                         IBM Lan Manager
  load                        Load Protocol
  locaddr-priority-list       Establish queueing priorities based on LU address
  location                    Global location configuration commands
  logging                     Modify message logging facilities
  login                       Enable secure login checking
  login-string                Define a host-specific login string
  maintenance-template        maintenance-template configuration
  map-class                   Configure static map class
  map-list                    Configure static map list
  map3270keys                 map3270keys
  mcsa                        Configure mcsa
  mdns-sd                     mDNS Service Discovery Gateway Configuration
  media                       Media Commands
  memory                      Configure memory management
  menu                        Define a user-interface menu
  metadata                    Metadata Application
  mka                         MACsec Key Agreement (MKA) configuration
  mode                        Firewall mode
  modemcap                    Modem Capabilities database
  monitor                     Monitoring different system events
  mop                         Configure the DEC MOP Server
  mpls                        Configure MPLS parameters
  multilink                   PPP multilink global configuration
  named-ordering-route-map    named ordering route-map enable
  nat46                       NAT46 configuration commands
  nat64                       NAT64 configuration commands
  nat66                       NAT66 configuration commands
  ncia                        Native Client Interface Architecture
  netbios                     NETBIOS access control filtering
  netconf                     Configure NETCONF
  network-clock               Network clock configuration commands
  nhrp                        NHRP global commands
  no                          Negate a command or set its defaults
  novell                      Novell/IPX global configuration commands
  ntp                         Configure NTP
  object-group                Configure Object Group
  onep                        ONEP functionality
  otv                         Configure OTV information
  overlay                     Global Overlay Tunnel Configurations
  parser                      Configure parser
  password                    Configure encryption password (key)
  pdm                         Policy Definition manager configurations
  pdm                         Policy Definition manager configurations
  performance                 Global Performance monitor configuration
  performance-measurement     Performance Measurement configuration
  pnp                         Configure PNP
  policy-manager              Policy Manager configuration commands
  policy-map                  Configure Policy Map
  policy-peer                 External Policy Delegation(EPD) peer parameters
  ppp                         PPP global configuration
  pppoe                       PPPoE global configuration
  privilege                   Command privilege parameters
  process                     Configure process
  process-max-time            Maximum time for process to run before voluntarily relinquishing processor
  prompt                      Set system's prompt
  pseudowire-class            Pseudowire-class configuration
  pseudowire-static-oam       Static PW OAM configuration
  pseudowire-tlv              Global PW TLV configuration
  ptp                         Precision Time Protocol
  qos                         Global QoS configuration subcommands
  rbe                         Commands for Routing RFC 1483 Ethernet encapsulated packets
  rcmd                        Remote command configuration commands
  rcp-enable                  Enable server side of RCP
  redirect                    Configure L4 redirect parameters
  redundancy                  Enter redundancy mode
  regexp                      regexp commands
  resource                    Configure Embedded Resource Manager (ERM)
  resource-group              Configure Resource Group settings
  resume-string               Define a host-specific resume string
  rif                         Source-route RIF cache
  rlogin                      Rlogin configuration commands
  route-map                   Create route-map or enter route-map command mode
  route-tag                   Route Tag
  router                      Enable a routing process
  routing-default-optimize    Enable routing default optimization
  rsh-disable-command         rsh-disable-command
  rsh-enable                  Enable server side of RSH
  rsrb                        RSRB LSAP/DSAP filtering
  rwatch                      Enter RIB_RWATCH test configuration submode
  sampler                     Define a Sampler
  sap-priority-list           Establish queueing priorities based on SAP and/or MAC address(es)
  sasl                        Configure SASL
  sbfd                        SBFD configuration commands
  scheduler                   Scheduler parameters
  scheduler-interval          scheduler-interval
  scripting                   Configure options for scripting languages
  segment-routing             Enter Segment Routing Mode
  service                     Modify use of network based services
  service-export              Configure a Central controller
  service-family              Configure external service-family clients
  service-group               service-group global command
  service-instance            Configure a Static Service
  service-list                Enter the service list
  service-routing             Configure service-routing 
  sgbp                        SGBP Stack Group Bidding Protocol configuration
  sgi                         Configure SGI
  shell                       Configure shell command
  site-manager                Site-manager Configuration Commands
  smrp                        Simple Multicast Routing Protocol configuration commands
  sna                         Network Management Physical Unit Command
  snapshot-template           snapshot-template configuration
  snmp                        Modify non engine SNMP parameters
  snmp-server                 Modify SNMP engine parameters
  sntp                        Configure SNTP
  source                      Get config from another source
  source-bridge               Source-route bridging ring groups
  spanning-tree               Spanning Tree Subsystem
  spd                         Selective Packet Discard parameters
  stacks                      Configure stacks
  standby                     Global HSRP configuration commands
  state-machine               Define a TCP dispatch state machine
  stun                        STUN global configuration commands
  subscriber                  Subscriber configuration
  subscriber-policy           Subscriber policy
  system                      System configuration
  tacacs-server               Modify TACACS query parameters
  tag-switching               Dynamic Tag Switching commands
  tarp                        Global TARP configuration subcommands
  template                    Select a template to configure
  terminal-queue              Terminal queue commands
  tftp-server                 Provide TFTP service for netload requests
  time-range                  Define time range entries
  timezone                    timezone
  tn3270                      tn3270 configuration command
  tod-clock                   Time-of-Day clock
  track                       Object tracking configuration commands
  translate                   Translate global configuration commands
  ttycap                      Define a new termcap
  user-name                   Establish User Name Authentication
  username                    Establish User Name Authentication
  version                     version
  vines                       VINES global configuration commands
  virtual-profile             Virtual Profile configuration
  virtual-template            Virtual Template configuration
  vlan                        VLAN configuration commands
  vlan-autoconfig             Configure dynamic VLAN interface
  vpdn                        Virtual Private Dialup Network
  vpdn-group                  VPDN group configuration
  vpdn-template               vpdn-template configuration
  vrf                         VRF commands
  vrrs                        vrrs global command
  vty-async                   Enable virtual async line configuration
  vxlan                       Configure VxLAN information
  wsma                        Configure Web Services Management Agents
  x25                         X.25 Level 3
  xconnect                    Xconnect config commands
  xns                         XNS global configuration commands
  xot                         Global XOT commands

RT01(config)#
```

**P1 classic IF: ip hello-interval ? — RT01: interface Ethernet0/0 : ip hello-interval ?**

```
ip hello-interval ?
  eigrp  Enhanced Interior Gateway Routing Protocol (EIGRP)

RT01(config-if)#ip hello-interval
```

**P1 classic IF: ip authentication ? — RT01: interface Ethernet0/0 : ip authentication ?**

```
ip authentication ?
  key-chain  key-chain
  mode       mode

RT01(config-if)#ip authentication
```

**P1 nhrp/tunnel — RT01: interface Tunnel0 : ip nhrp ?**

```
ip nhrp ?
  attribute                NHRP attribute set
  authentication           Authentication string
  bfd                      BFD Parameters
  block-next-hop-override  Disable installation of NHRP next-hop-overrides
  cache                    NHRP Cache related commands.
  connect                  NHRP resolution request connect
  holdtime                 Advertised holdtime
  interest                 Specify an access list
  map                      Map dest IP addresses to NBMA addresses
  max-send                 Rate limit NHRP traffic
  multicast                Multicast Parameters
  network-id               NBMA network identifier
  nhs                      Specify a next hop server
  path                     NHRP path specific configuration
  process-delay            Process delayed event
  record                   Allow NHRP record option
  redirect                 Enable NHRP redirect traffic indication
  registration             Settings for registration packets.
  reject                   NHRP resolution reject request
  resolution               Settings for resolution messages
  responder                Responder interface
  send-routed              Send NHRP packets via the routed path first.
  server-only              Disable NHRP requests
  shortcut                 Enable shortcut switching
  summary-map               Summary IP address 
  trigger-svc              Create NHRP cut-through based on traffic load
  use                      Specify usage count for sending requests

RT01(config-if)#ip nhrp
```

**P1 nhrp/tunnel — RT01: interface Tunnel0 : ip nhrp registration ?**

```
ip nhrp registration ?
  differential  Differential registration - updated networks only
  no-unique     Do not set the 'Unique' flag in registration requests.
  req-def-map   Request default map(s) in registration requests
  timeout       Time between periodic Registration messages

RT01(config-if)#ip nhrp registration
```

**P1 nhrp/tunnel — RT01: interface Tunnel0 : ip nhrp map ?**

```
ip nhrp map ?
  A.B.C.D    IP address of destination
  multicast  Use this NBMA mapping for broadcasts/multicasts

RT01(config-if)#ip nhrp map
```

**P1 nhrp/tunnel — RT01: interface Tunnel0 : ip nhrp map multicast ?**

```
ip nhrp map multicast ?
  A.B.C.D     IP NBMA address
  X:X:X:X::X  IPv6 NBMA address
  dynamic     Dynamically learn destinations from client registrations on hub

RT01(config-if)#ip nhrp map multicast
```

**P1 nhrp/tunnel — RT01: interface Tunnel0 : ip nhrp nhs ?**

```
ip nhrp nhs ?
  A.B.C.D   Protocol IP address of NHS
  cluster   NHS Redundancy cluster configurations
  dynamic   NHS protocol address dynamically learnt
  fallback  NHS Redundancy Fallback time

RT01(config-if)#ip nhrp nhs
```

**P1 nhrp/tunnel — RT01: interface Tunnel0 : ip nhrp nhs 10.0.0.1 ?**

```
ip nhrp nhs 10.0.0.1 ?
  cluster   NHS cluster, don't specify for default cluster
  nbma      NBMA of NHS
  priority  NHS priority, don't specify for default priority
  <cr>      <cr>

RT01(config-if)#ip nhrp nhs 10.0.0.1
```

**P1 nhrp/tunnel — RT01: interface Tunnel0 : ip nhrp nhs 10.0.0.1 nbma 192.0.2.1 ?**

```
ip nhrp nhs 10.0.0.1 nbma 192.0.2.1 ?
  cluster    NHS cluster, don't specify for default cluster
  multicast  Use this NBMA mapping for broadcasts/multicasts
  priority   NHS priority, don't specify for default priority
  <cr>       <cr>

RT01(config-if)#ip nhrp nhs 10.0.0.1 nbma 192.0.2.1
```

**P1 nhrp/tunnel — RT01: interface Tunnel0 : ip nhrp holdtime ?**

```
ip nhrp holdtime ?
  <1-65535>  Number of seconds

RT01(config-if)#ip nhrp holdtime
```

**P1 nhrp/tunnel — RT01: interface Tunnel0 : ip nhrp authentication ?**

```
ip nhrp authentication ?
  WORD  authentication string

RT01(config-if)#ip nhrp authentication
```

**P1 nhrp/tunnel — RT01: interface Tunnel0 : ip nhrp shortcut ?**

```
ip nhrp shortcut ?
  virtual-template  Virtual template interface number
  <cr>              <cr>

RT01(config-if)#ip nhrp shortcut
```

**P1 nhrp/tunnel — RT01: interface Tunnel0 : ip nhrp redirect ?**

```
ip nhrp redirect ?
  interest  Specify an access list
  timeout   Specify interval over which to throttle
  <cr>      <cr>

RT01(config-if)#ip nhrp redirect
```

**P1 nhrp/tunnel — RT01: interface Tunnel0 : ip nhrp network-id ?**

```
ip nhrp network-id ?
  <1-4294967295>  Network identifier

RT01(config-if)#ip nhrp network-id
```

**P1 nhrp/tunnel — RT01: interface Tunnel0 : tunnel mode ?**

```
tunnel mode ?
  aurp           AURP TunnelTalk AppleTalk encapsulation
  cayman         Cayman TunnelTalk AppleTalk encapsulation
  dvmrp          DVMRP multicast tunnel
  eon            EON compatible CLNS tunnel
  ethernet       Ethernet over gre
  gre            generic route encapsulation protocol
  ipip           IP over IP encapsulation
  ipsec          IPSec tunnel encapsulation
  iptalk         Apple IPTalk encapsulation
  ipv6           Generic packet tunneling in IPv6
  ipv6ip         IPv6 over IP encapsulation
  mpls           MPLS encapsulations
  nos            IP over IP encapsulation (KA9Q/NOS compatible)
  rbscp          RBSCP in IP tunnel
  sdwan          SDWAN Overlay
  tag-switching  IP over Tag Switching encapsulation
  udp            UDP encapsulation protocol
  vxlan          VXLAN encapsulation
  vxlan-gpe      VXLAN GPE encapsulation

RT01(config-if)#tunnel mode
```

**P1 nhrp/tunnel — RT01: interface Tunnel0 : tunnel mode gre ?**

```
tunnel mode gre ?
  ip          over IP
  ipv6        over IPv6
  multipoint  over IPv4 (multipoint)

RT01(config-if)#tunnel mode gre
```

**P1 nhrp/tunnel — RT01: interface Tunnel0 : tunnel key ?**

```
tunnel key ?
  <0-4294967295>  key

RT01(config-if)#tunnel key
```

**P1 nhrp/tunnel — RT01: interface Tunnel0 : tunnel protection ?**

```
tunnel protection ?
  ipsec  Use ipsec to protect this tunnel interface
  psk    Use preshared key value for default tunnel protection

RT01(config-if)#tunnel protection
```

**P1 nhrp/tunnel — RT01: interface Tunnel0 : tunnel protection ipsec profile PROF ?**

```
tunnel protection ipsec profile PROF ?
  ikev2-profile   Specify ikev2 profile for the crypto connection.
  isakmp-profile  Specify isakmp profile for the crypto connection.
  shared          Use a shared socket for the crypto connection.
  <cr>            <cr>

RT01(config-if)#tunnel protection ipsec profile PROF
```

**P1 crypto 有無 — RT01: (config) : crypto ?**

```
crypto ?
  RSA-key-pair  RSA key pair
  call          Configure Crypto Call Admission Control
  dynamic-map   Specify a dynamic crypto map template
  engine        Enter a crypto engine configurable menu
  gdoi          Configure GKM (Group Key Management, GDOI or G-IKEv2) Policy
  gkm           Configure GKM (Group Key Management, GDOI or G-IKEv2) Policy
  identity      Enter a crypto identity list
  ikev2         Configure IKEv2 Options
  ipsec         Configure IPSEC policy
  isakmp        Configure ISAKMP policy
  key           Long term key operations
  keyring       Key ring commands
  logging       logging messages
  map           Enter a crypto map
  mib           Configure Crypto-related MIB Parameters
  pki           Public Key components
  provisioning  Secure Device Provisioning
  skip-client   Configure SKIP-Client
  ssl           Configure Crypto SSL Options
  tls-tunnel    Configure Crypto TLS-Tunnel Options
  vpn           Configure crypto vpn commands
  wui           Crypto HTTP configuration interfaces
  xauth         X-Auth parameters

RT01(config)#crypto
```

**P1 crypto 有無 — RT01: (config) : crypto ipsec ?**

```
crypto ipsec ?
  df-bit                Handling of encapsulated DF bit.
  exclude               LI exclude list
  fragmentation         Handling of fragmentation of near-MTU sized packets
  ike                   Common global config for ISAKMP and IKEv2
  ipv4-deny             Configure global ipv4 deny policy.
  nat-transparency      IPsec NAT transparency model
  optional              Enable optional encryption for IPSec
  profile               Configure an ipsec policy profile
  security-association  Security association parameters
  session-key           security association parameters
  transform-set         Define transform and settings

RT01(config)#crypto ipsec
```

**P1 crypto 有無 — RT01: (config) : crypto isakmp ?**

```
crypto isakmp ?
  aggressive-mode           Disable ISAKMP aggressive mode 
  client                    Set client configuration policy
  default                   ISAKMP default policy
  diagnose                  Diagnostic configuration
  disconnect-revoked-peers  Disconnect Crypto Session with Revoked Peer
  enable                    Enable ISAKMP
  fragmentation             IKE Fragmentation enabled if required
  identity                  Set the identity which ISAKMP will use
  invalid-spi-recovery      Initiate IKE and send Invalid SPI Notify
  keepalive                 Set a keepalive interval for use with IOS peers
  key                       Set pre-shared key for remote peer
  nat                       Set a nat  keepalive interval for use with IOS peers
  peer                      Set Peer Policy
  performance               Enable performance statistics collection
  policy                    Set policy for an ISAKMP protection suite
  profile                   Define ISAKMP Profiles
  xauth                     Set Extended Authentication values

RT01(config)#crypto isakmp
```

**P1 route-map set — RT01: route-map RM-POC permit 10 : set ip precedence ?**

```
set ip precedence ?
  <0-7>           Precedence value
  critical        Set critical precedence (5)
  flash           Set flash precedence (3)
  flash-override  Set flash override precedence (4)
  immediate       Set immediate precedence (2)
  internet        Set internetwork control precedence (6)
  network         Set network control precedence (7)
  priority        Set priority precedence (1)
  routine         Set routine precedence (0)

RT01(config-route-map)#set ip precedence
```

**P1 route-map set — RT01: route-map RM-POC permit 10 : set ip dscp ?**

```
set ip dscp ?
% Unrecognized command
RT01(config-route-map)#set ip dscp
```

**P1 route-map set — RT01: route-map RM-POC permit 10 : set ip tos ?**

```
set ip tos ?
  <0-15>             Type of service value
  max-reliability    Set max reliable TOS (2)
  max-throughput     Set max throughput TOS (4)
  min-delay          Set min delay TOS (8)
  min-monetary-cost  Set min monetary cost TOS (1)
  normal             Set normal TOS (0)

RT01(config-route-map)#set ip tos
```

**P1 route-map set — RT01: route-map RM-POC permit 10 : set ?**

```
set ?
  aigp-metric       accumulated metric value
  as-path           Modify BGP AS-path attribute
  attribute-set     Set attribute
  automatic-tag     Automatically compute TAG value
  clns              OSI summary address
  comm-list         set BGP community list (for deletion)
  community         BGP community attribute
  dampening         Set BGP route flap dampening parameters
  default           Set default information
  evpn              BGP EVPN policies
  extcomm-list      Set BGP/VPN extended community list (for deletion)
  extcommunity      BGP extended community attribute
  global            Set to global routing table
  interface         Output interface
  ip                IP specific information
  ipv6              IPv6 specific information
  large-community   BGP large community attribute
  largecomm-list    set BGP large community list (for deletion)
  level             Where to import route
  lisp              Locator ID Separation Protocol specific information
  local-preference  BGP local preference path attribute
  metric            Metric value for destination routing protocol
  metric-type       Type of metric for destination routing protocol
  mpls-label        Set MPLS label for prefix
  nlri              BGP NLRI type
  omp-tag           OMP Tag value for destination routing protocol
  origin            BGP origin code
  overlay-summary   Set overlay summary
  tag               Tag value for destination routing protocol
  traffic-index     BGP traffic classification number for accounting
  vrf               Define VRF name
  weight            BGP weight for routing table

RT01(config-route-map)#set
```

**P1 route-map set — RT01: route-map RM-POC permit 10 : set precedence ?**

```
set precedence ?
% Unrecognized command
RT01(config-route-map)#set precedence
```

**P1 route-map set — RT01: route-map RM-POC permit 10 : set dscp ?**

```
set dscp ?
% Unrecognized command
RT01(config-route-map)#set dscp
```

**P1 show route-map(precedence/dscp の表示形)**

```
route-map RM-POC, permit, sequence 10
  Match clauses:
  Set clauses:
    ip precedence priority
  Policy routing matches: 0 packets, 0 bytes
```

**P1 bfd — RT01: bfd-template single-hop T-POC : interval ?**

```
interval ?
  both          Minimum transmit and receive interval capability
  microseconds  Specify BFD timers in microseconds
  min-tx        Minimum transmit interval capability

RT01(config-bfd)#interval
```

**P1 bfd — RT01: bfd-template single-hop T-POC : interval min-tx 100 ?**

```
interval min-tx 100 ?
  min-rx  Minimum receive interval capability

RT01(config-bfd)#interval min-tx 100
```

**P1 bfd — RT01: bfd-template single-hop T-POC : interval min-tx 100 min-rx 100 ?**

```
interval min-tx 100 min-rx 100 ?
  multiplier  Multiplier value used to compute holddown
  <cr>        <cr>

RT01(config-bfd)#interval min-tx 100 min-rx 100
```

**P1 bfd — RT01: interface Ethernet0/0 : bfd ?**

```
bfd ?
  enable         bfd enable(by default enable)
  interval       Transmit interval between BFD packets
  jitter         Enable BFD interval transmit jittering
  local-address  bfd local address 
  template       BFD template

RT01(config-if)#bfd
```

**P1 bfd — RT01: interface Ethernet0/0 : bfd interval 100 ?**

```
bfd interval 100 ?
  min_rx  Minimum receive interval capability

RT01(config-if)#bfd interval 100
```

**P1 bfd — RT01: interface Ethernet0/0 : bfd interval 100 min_rx 100 ?**

```
bfd interval 100 min_rx 100 ?
  multiplier  Multiplier value used to compute holddown

RT01(config-if)#bfd interval 100 min_rx 100
```

**P1 bfd — RT01: interface Ethernet0/0 : ip ospf bfd ?**

```
ip ospf bfd ?
  disable      Disable BFD on this interface
  strict-mode  Enable BFD in strict mode
  <cr>         <cr>

RT01(config-if)#ip ospf bfd
```

**P1 bfd — RT01: router ospf 99 : bfd ?**

```
bfd ?
  all-interfaces  Enable BFD on all interfaces

RT01(config-router)#bfd
```

## P2 debug ip packet  (2026-09-18 12:58)

- P2a forus(自ルータ宛を受信): ping RT01→10.0.12.2 = 100%

**P2a forus(自ルータ宛を受信) — RT02 show logging**

```
*Sep 18 12:57:13.482: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.12.2 (nil), len 100, input feature, MCI Check(110), rtype 0, forus FALSE, sendself FALSE, mtu 0, fwdchk FALSE
*Sep 18 12:57:13.482: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.12.2 (nil), len 100, rcvd 2
*Sep 18 12:57:13.482: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.12.2 (nil), len 100, stop process pak for forus packet
*Sep 18 12:57:13.482: IP: tableid=0, s=10.0.12.1 (Ethernet0/0), d=10.0.12.2 (Ethernet0/0) nexthop=10.0.12.2, routed via RIB
*Sep 18 12:57:13.482: IP: tableid=0, s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0) nexthop=10.0.12.1, routed via FIB
*Sep 18 12:57:13.482: IP: s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0), len 100, sending
*Sep 18 12:57:13.482: IP: s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0), len 100, sending full packet
*Sep 18 12:57:13.483: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.12.2 (nil), len 100, input feature, MCI Check(110), rtype 0, forus FALSE, sendself FALSE, mtu 0, fwdchk FALSE
*Sep 18 12:57:13.483: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.12.2 (nil), len 100, rcvd 2
*Sep 18 12:57:13.483: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.12.2 (nil), len 100, stop process pak for forus packet
*Sep 18 12:57:13.483: IP: tableid=0, s=10.0.12.1 (Ethernet0/0), d=10.0.12.2 (Ethernet0/0) nexthop=10.0.12.2, routed via RIB
*Sep 18 12:57:13.483: IP: tableid=0, s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0) nexthop=10.0.12.1, routed via FIB
*Sep 18 12:57:13.483: IP: s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0), len 100, sending
*Sep 18 12:57:13.483: IP: s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0), len 100, sending full packet
```

- P2b transit(中継 forward): ping RT01→10.0.23.3 = 100%

**P2b transit(中継 forward) — RT02 show logging**

```

```

- P2c local 発(自ルータ発): ping RT02→10.0.12.1 = 100%

**P2c local 発(自ルータ発) — RT02 show logging**

```
*Sep 18 12:57:22.943: IP: tableid=0, s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0) nexthop=10.0.12.1, routed via FIB
*Sep 18 12:57:22.943: IP: s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0), len 100, sending
*Sep 18 12:57:22.943: IP: s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0), len 100, sending full packet
*Sep 18 12:57:22.944: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.12.2 (nil), len 100, input feature, MCI Check(110), rtype 0, forus FALSE, sendself FALSE, mtu 0, fwdchk FALSE
*Sep 18 12:57:22.944: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.12.2 (nil), len 100, rcvd 2
*Sep 18 12:57:22.944: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.12.2 (nil), len 100, stop process pak for forus packet
*Sep 18 12:57:22.944: IP: tableid=0, s=10.0.12.1 (Ethernet0/0), d=10.0.12.2 (Ethernet0/0) nexthop=10.0.12.2, routed via RIB
*Sep 18 12:57:22.944: IP: tableid=0, s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0) nexthop=10.0.12.1, routed via FIB
*Sep 18 12:57:22.944: IP: s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0), len 100, sending
*Sep 18 12:57:22.944: IP: s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0), len 100, sending full packet
*Sep 18 12:57:22.944: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.12.2 (nil), len 100, input feature, MCI Check(110), rtype 0, forus FALSE, sendself FALSE, mtu 0, fwdchk FALSE
*Sep 18 12:57:22.944: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.12.2 (nil), len 100, rcvd 2
*Sep 18 12:57:22.944: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.12.2 (nil), len 100, stop process pak for forus packet
*Sep 18 12:57:22.944: IP: tableid=0, s=10.0.12.1 (Ethernet0/0), d=10.0.12.2 (Ethernet0/0) nexthop=10.0.12.2, routed via RIB
```

- P2d unroutable(経路なし): ping RT01→172.31.99.1 = 0%

**P2d unroutable(経路なし) — RT02 show logging**

```
*Sep 18 12:57:27.548: IP: s=10.0.12.1 (Ethernet0/0), d=172.31.99.1 (nil), len 100, input feature, MCI Check(110), rtype 0, forus FALSE, sendself FALSE, mtu 0, fwdchk FALSE
*Sep 18 12:57:27.548: IP: s=10.0.12.1 (Ethernet0/0), d=172.31.99.1 (nil), len 100, unroutable
*Sep 18 12:57:27.548: IP: tableid=0, s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0) nexthop=10.0.12.1, routed via FIB
*Sep 18 12:57:27.548: IP: s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0), len 56, sending
*Sep 18 12:57:27.548: IP: s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0), len 56, sending full packet
```

- P2e access denied(inbound ACL で拒否): ping RT01→10.0.23.3 = 0%

**P2e access denied(inbound ACL で拒否) — RT02 show logging**

```
*Sep 18 12:57:35.204: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.23.3 (nil), len 100, access denied
*Sep 18 12:57:35.204: IP: tableid=0, s=10.0.12.1 (Ethernet0/0), d=10.0.23.3 (Ethernet0/1) nexthop=10.0.23.3, routed via FIB
*Sep 18 12:57:35.204: IP: tableid=0, s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0) nexthop=10.0.12.1, routed via FIB
*Sep 18 12:57:35.204: IP: s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0), len 56, sending
*Sep 18 12:57:35.204: IP: s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0), len 56, sending full packet
*Sep 18 12:57:35.204: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.23.3 (nil), len 100, input feature, packet consumed, Access List(48), rtype 0, forus FALSE, sendself FALSE, mtu 0, fwdchk FALSE
```

- P2f encapsulation failed(next-hop が ARP 応答しない): ping RT01→172.31.100.1 = 0%

**P2f encapsulation failed(next-hop が ARP 応答しない) — RT02 show logging**

```

```

- P2g detail(forus・ICMP type/code): ping RT01→10.0.12.2 = 100%

**P2g detail(forus・ICMP type/code) — RT02 show logging**

```
*Sep 18 12:57:53.267: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.12.2 (nil), len 100, input feature
*Sep 18 12:57:53.267:     ICMP type=8, code=0, MCI Check(110), rtype 0, forus FALSE, sendself FALSE, mtu 0, fwdchk FALSE
*Sep 18 12:57:53.267: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.12.2 (nil), len 100, rcvd 2
*Sep 18 12:57:53.267:     ICMP type=8, code=0
*Sep 18 12:57:53.267: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.12.2 (nil), len 100, stop process pak for forus packet
*Sep 18 12:57:53.267:     ICMP type=8, code=0
*Sep 18 12:57:53.267: IP: tableid=0, s=10.0.12.1 (Ethernet0/0), d=10.0.12.2 (Ethernet0/0) nexthop=10.0.12.2, routed via RIB
*Sep 18 12:57:53.267: IP: tableid=0, s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0) nexthop=10.0.12.1, routed via FIB
*Sep 18 12:57:53.267: IP: s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0), len 100, sending
*Sep 18 12:57:53.267:     ICMP type=0, code=0
*Sep 18 12:57:53.267: IP: s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0), len 100, sending full packet
*Sep 18 12:57:53.267:     ICMP type=0, code=0
*Sep 18 12:57:53.268: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.12.2 (nil), len 100, input feature
*Sep 18 12:57:53.268:     ICMP type=8, code=0, MCI Check(110), rtype 0, forus FALSE, sendself FALSE, mtu 0, fwdchk FALSE
*Sep 18 12:57:53.268: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.12.2 (nil), len 100, rcvd 2
*Sep 18 12:57:53.268:     ICMP type=8, code=0
*Sep 18 12:57:53.268: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.12.2 (nil), len 100, stop process pak for forus packet
*Sep 18 12:57:53.268:     ICMP type=8, code=0
*Sep 18 12:57:53.268: IP: tableid=0, s=10.0.12.1 (Ethernet0/0), d=10.0.12.2 (Ethernet0/0) nexthop=10.0.12.2, routed via RIB
*Sep 18 12:57:53.268: IP: tableid=0, s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0) nexthop=10.0.12.1, routed via FIB
*Sep 18 12:57:53.268: IP: s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0), len 100, sending
*Sep 18 12:57:53.268:     ICMP type=0, code=0
*Sep 18 12:57:53.268: IP: s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0), len 100, sending full packet
*Sep 18 12:57:53.268:     ICMP type=0, code=0
```

- P2h detail(transit): ping RT01→10.0.23.3 = 100%

**P2h detail(transit) — RT02 show logging**

```

```

## P1b classic/named 追加採取  (2026-09-18 12:59)

**P1b eigrp classic: (config-router) — RT01: router eigrp 200 : ?**

```
?
Router configuration commands:
  address-family           Enter Address Family command mode
  auto-summary             Enable automatic network number summarization
  bfd                      BFD configuration commands
  default                  Set a command to its defaults
  default-information      Control distribution of default information
  default-metric           Set metric of redistributed routes
  distance                 Define an administrative distance
  distribute-list          Filter entries in eigrp updates
  eigrp                    EIGRP specific commands
  event-log-size           Set EIGRP maximum event log entries
  event-logging            Log EIGRP routing events
  exit                     Exit from routing protocol configuration mode
  kill-everyone            Kill all adjacencies on SIA
  log-event-type           Set event types logged
  log-neighbor-changes     Enable/Disable EIGRP neighbor logging
  log-neighbor-warnings    Enable/Disable EIGRP neighbor warnings
  maximum-paths            Forward packets over multiple paths
  maximum-secondary-paths  Maximum secondary paths
  metric                   Modify metrics and parameters for advertisement
  neighbor                 Specify a neighbor router
  network                  Enable routing on an IP network
  no                       Negate a command or set its defaults
  offset-list              Add or subtract offset from EIGRP metrics
  passive-interface        Suppress routing updates on an interface
  redistribute             Redistribute IPv4 routes from another routing protocol
  router-id                router id for this EIGRP process
  shutdown                 Shutdown this instance of EIGRP 
  stub                     Set address-family in stubbed mode
  summary-metric           Specify summary to apply metric/filtering
  timers                   Adjust routing timers
  traffic-share            How to compute traffic share over alternate paths
  variance                 Control load balancing variance

RT01(config-router)#
```

**P1b eigrp classic: passive-interface ? — RT01: router eigrp 200 : passive-interface ?**

```
passive-interface ?
  ACR                Virtual ACR interface
  ATM-ACR            ATM interface with ACR
  Analysis-Module    Cisco network analysis service module
  AppNav-Compress    Service-Context Virtual Interface Compress
  AppNav-UnCompress  Service-Context Virtual interface UnCompress
  Async              Async interface
  Auto-Template      Auto-Template interface
  BD-VIF             Bridge-Domain Virtual IP interface
  BDI                Bridge-Domain interface
  BVI                Bridge-Group Virtual Interface
  Bluetooth          Bluetooth interface
  CDMA-Ix            CDMA Ix interface
  CEM-ACR            Circuit Emulation interface with ACR
  CEM-PG             Circuit Emulation interface with Protection group
  CEOBC              Cluster EOBC Interface
  CTunnel            CTunnel interface
  Container          Container interface
  Dialer             Dialer interface
  EsconPhy           ESCON interface
  Ethernet           IEEE 802.3
  Ethernet-Internal  Ethernet-Internal interface
  Fcpa               Fiber Channel
  Filter             Filter interface
  Filtergroup        Filter Group interface
  GMPLS              MPLS interface
  Group-Async        Async Group interface
  IMA-ACR            IMA interface with ACR
  L2LISP             L2 Locator/ID Separation Protocol Virtual Interface
  LISP               Locator/ID Separation Protocol Virtual Interface
  LongReachEthernet  Long-Reach Ethernet interface
  Loopback           Loopback interface
  Lspvif             LSP virtual interface
  MFR                Multilink Frame Relay bundle interface
  Multilink          Multilink-group interface
  NVI                NAT virtual interface
  Overlay            Overlay interface
  PROTECTION_GROUP   Protection-group controller
  Port-channel       Ethernet Channel of interfaces
  Portgroup          Portgroup interface
  Pos-channel        POS Channel of interfaces
  SBC                Session Border Controller
  SDH_ACR            Virtual SDH-ACR controller
  SERIAL-ACR         Serial interface with ACR
  SONET_ACR          Virtual SONET-ACR controller
  SR                 SR virtual interface
  SSLVPN-VIF         SSLVPN Virtual Interface
  SYSCLOCK           Telecom-Bus Clock Controller
  Serial-PG          Serial interface with Protection Group
  Service-Engine     Cisco service engine module
  TLS-VIF            TLS Virtual Interface
  Tunnel             Tunnel interface
  Tunnel-tp          MPLS Transport Profile interface
  VPN                VPN interface
  Vif                PGM Multicast Host interface
  Vir-cem-ACR        Circuit Emulation Virtual interface with ACR
  Virtual-Ethernet   Virtual Ethernet interface
  Virtual-PPP        Virtual PPP interface
  Virtual-Template   Virtual Template interface
  Virtual-TokenRing  Virtual TokenRing
  Vlan               Catalyst Vlans
  default            Suppress routing updates on all interfaces
  multiservice       Multiservice interface
  nve                Network virtualization endpoint interface
  ucse               Cisco ucse server
  vasileft           VasiLeft interface
  vasiright          VasiRight interface
  vmi                Virtual Multipoint Interface
  voaBypassIn        VOA-Bypass-In interface
  voaBypassOut       VOA-Bypass-Out interface
  voaFilterIn        VOA-Filter-In interface
  voaFilterOut       VOA-Filter-Out interface
  voaIn              VOA-In interface
  voaOut             VOA-Out interface

RT01(config-router)#passive-interface
```

**P1b classic IF: ip summary-address ? — RT01: interface Ethernet0/0 : ip summary-address ?**

```
ip summary-address ?
  eigrp  Enhanced Interior Gateway Routing Protocol (EIGRP)
  rip    Routing Information Protocol (RIP)

RT01(config-if)#ip summary-address
```

**P1b classic IF: ip hello-interval eigrp 200 ? — RT01: interface Ethernet0/0 : ip hello-interval eigrp 200 ?**

```
ip hello-interval eigrp 200 ?
  <1-65535>  Seconds between hello transmissions

RT01(config-if)#ip hello-interval eigrp 200
```

**P1b named af-interface: summary-address ? — RT01: router eigrp NAMED / address-family ipv4 unicast autonomous-system 300 / af-interface Ethernet0/0 : summary-address ?**

```
summary-address ?
  A.B.C.D     Summary network address
  A.B.C.D/nn  Summary <network>/<length>, e.g. 192.168.0.0/16

RT01(config-router-af-interface)#summary-address
```

**P1b named af-topology: distance ? — RT01: router eigrp NAMED / address-family ipv4 unicast autonomous-system 300 / topology base : distance ?**

```
distance ?
  <1-255>  Set route administrative distance
  eigrp    Set distance for internal and external routes

RT01(config-router-af-topology)#distance
```

**P1b named af: network ? — RT01: router eigrp NAMED / address-family ipv4 unicast autonomous-system 300 : network ?**

```
network ?
  A.B.C.D  Network number

RT01(config-router-af)#network
```

## P2x debug ip packet(プロセススイッチ)  (2026-09-18 13:00)

- P2x: RT02 の Et0/0・Et0/1 で no ip route-cache(プロセススイッチ化)

- P2x-b transit forward(no ip route-cache): ping RT01→10.0.23.3 = 100%

**P2x-b transit forward(no ip route-cache) — RT02 show logging**

```
*Sep 18 12:59:42.243: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.23.3 (nil), len 100, input feature, MCI Check(110), rtype 0, forus FALSE, sendself FALSE, mtu 0, fwdchk FALSE
*Sep 18 12:59:42.243: IP: tableid=0, s=10.0.12.1 (Ethernet0/0), d=10.0.23.3 (Ethernet0/1) nexthop=10.0.23.3, routed via FIB
*Sep 18 12:59:42.243: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.23.3 (Ethernet0/1), g=10.0.23.3, len 100, forward
*Sep 18 12:59:42.243: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.23.3 (Ethernet0/1), len 100, sending full packet
*Sep 18 12:59:42.244: IP: s=10.0.23.3 (Ethernet0/1), d=10.0.12.1 (nil), len 100, input feature, MCI Check(110), rtype 0, forus FALSE, sendself FALSE, mtu 0, fwdchk FALSE
*Sep 18 12:59:42.244: IP: tableid=0, s=10.0.23.3 (Ethernet0/1), d=10.0.12.1 (Ethernet0/0) nexthop=10.0.12.1, routed via FIB
*Sep 18 12:59:42.244: IP: s=10.0.23.3 (Ethernet0/1), d=10.0.12.1 (Ethernet0/0), g=10.0.12.1, len 100, forward
*Sep 18 12:59:42.244: IP: s=10.0.23.3 (Ethernet0/1), d=10.0.12.1 (Ethernet0/0), len 100, sending full packet
*Sep 18 12:59:42.244: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.23.3 (nil), len 100, input feature, MCI Check(110), rtype 0, forus FALSE, sendself FALSE, mtu 0, fwdchk FALSE
*Sep 18 12:59:42.244: IP: tableid=0, s=10.0.12.1 (Ethernet0/0), d=10.0.23.3 (Ethernet0/1) nexthop=10.0.23.3, routed via FIB
*Sep 18 12:59:42.244: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.23.3 (Ethernet0/1), g=10.0.23.3, len 100, forward
*Sep 18 12:59:42.244: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.23.3 (Ethernet0/1), len 100, sending full packet
*Sep 18 12:59:42.245: IP: s=10.0.23.3 (Ethernet0/1), d=10.0.12.1 (nil), len 100, input feature, MCI Check(110), rtype 0, forus FALSE, sendself FALSE, mtu 0, fwdchk FALSE
*Sep 18 12:59:42.245: IP: tableid=0, s=10.0.23.3 (Ethernet0/1), d=10.0.12.1 (Ethernet0/0) nexthop=10.0.12.1, routed via FIB
*Sep 18 12:59:42.245: IP: s=10.0.23.3 (Ethernet0/1), d=10.0.12.1 (Ethernet0/0), g=10.0.12.1, len 100, forward
*Sep 18 12:59:42.245: IP: s=10.0.23.3 (Ethernet0/1), d=10.0.12.1 (Ethernet0/0), len 100, sending full packet
```

- P2x-f encapsulation failed(no ip route-cache・next-hop が ARP 応答しない): ping RT01→172.31.100.1 = 0%

**P2x-f encapsulation failed(no ip route-cache・next-hop が ARP 応答しない) — RT02 show logging**

```
*Sep 18 12:59:47.440: IP: s=10.0.12.1 (Ethernet0/0), d=172.31.100.1 (nil), len 100, input feature, MCI Check(110), rtype 0, forus FALSE, sendself FALSE, mtu 0, fwdchk FALSE
*Sep 18 12:59:47.440: IP: tableid=0, s=10.0.12.1 (Ethernet0/0), d=172.31.100.1 (Ethernet0/1) nexthop=10.0.23.99, routed via FIB
*Sep 18 12:59:47.440: IP: s=10.0.12.1 (Ethernet0/0), d=172.31.100.1 (Ethernet0/1), g=10.0.23.99, len 100, forward
*Sep 18 12:59:47.440: IP: s=10.0.12.1 (Ethernet0/0), d=172.31.100.1 (Ethernet0/1), len 100, encapsulation failed
*Sep 18 12:59:49.445: IP: s=10.0.12.1 (Ethernet0/0), d=172.31.100.1 (nil), len 100, input feature, MCI Check(110), rtype 0, forus FALSE, sendself FALSE, mtu 0, fwdchk FALSE
*Sep 18 12:59:49.445: IP: tableid=0, s=10.0.12.1 (Ethernet0/0), d=172.31.100.1 (Ethernet0/1) nexthop=10.0.23.99, routed via FIB
*Sep 18 12:59:49.445: IP: s=10.0.12.1 (Ethernet0/0), d=172.31.100.1 (Ethernet0/1), g=10.0.23.99, len 100, forward
*Sep 18 12:59:49.445: IP: s=10.0.12.1 (Ethernet0/0), d=172.31.100.1 (Ethernet0/1), len 100, encapsulation failed
```

- P2x-h detail transit(no ip route-cache): ping RT01→10.0.23.3 = 100%

**P2x-h detail transit(no ip route-cache) — RT02 show logging**

```
*Sep 18 12:59:56.979: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.23.3 (nil), len 100, input feature
*Sep 18 12:59:56.979:     ICMP type=8, code=0, MCI Check(110), rtype 0, forus FALSE, sendself FALSE, mtu 0, fwdchk FALSE
*Sep 18 12:59:56.979: IP: tableid=0, s=10.0.12.1 (Ethernet0/0), d=10.0.23.3 (Ethernet0/1) nexthop=10.0.23.3, routed via FIB
*Sep 18 12:59:56.979: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.23.3 (Ethernet0/1), g=10.0.23.3, len 100, forward
*Sep 18 12:59:56.979:     ICMP type=8, code=0
*Sep 18 12:59:56.980: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.23.3 (Ethernet0/1), len 100, sending full packet
*Sep 18 12:59:56.980:     ICMP type=8, code=0
*Sep 18 12:59:56.980: IP: s=10.0.23.3 (Ethernet0/1), d=10.0.12.1 (nil), len 100, input feature
*Sep 18 12:59:56.980:     ICMP type=0, code=0, MCI Check(110), rtype 0, forus FALSE, sendself FALSE, mtu 0, fwdchk FALSE
*Sep 18 12:59:56.980: IP: tableid=0, s=10.0.23.3 (Ethernet0/1), d=10.0.12.1 (Ethernet0/0) nexthop=10.0.12.1, routed via FIB
*Sep 18 12:59:56.980: IP: s=10.0.23.3 (Ethernet0/1), d=10.0.12.1 (Ethernet0/0), g=10.0.12.1, len 100, forward
*Sep 18 12:59:56.980:     ICMP type=0, code=0
*Sep 18 12:59:56.980: IP: s=10.0.23.3 (Ethernet0/1), d=10.0.12.1 (Ethernet0/0), len 100, sending full packet
*Sep 18 12:59:56.980:     ICMP type=0, code=0
*Sep 18 12:59:56.981: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.23.3 (nil), len 100, input feature
*Sep 18 12:59:56.981:     ICMP type=8, code=0, MCI Check(110), rtype 0, forus FALSE, sendself FALSE, mtu 0, fwdchk FALSE
*Sep 18 12:59:56.981: IP: tableid=0, s=10.0.12.1 (Ethernet0/0), d=10.0.23.3 (Ethernet0/1) nexthop=10.0.23.3, routed via FIB
*Sep 18 12:59:56.981: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.23.3 (Ethernet0/1), g=10.0.23.3, len 100, forward
*Sep 18 12:59:56.981:     ICMP type=8, code=0
*Sep 18 12:59:56.981: IP: s=10.0.12.1 (Ethernet0/0), d=10.0.23.3 (Ethernet0/1), len 100, sending full packet
*Sep 18 12:59:56.981:     ICMP type=8, code=0
*Sep 18 12:59:56.982: IP: s=10.0.23.3 (Ethernet0/1), d=10.0.12.1 (nil), len 100, input feature
*Sep 18 12:59:56.982:     ICMP type=0, code=0, MCI Check(110), rtype 0, forus FALSE, sendself FALSE, mtu 0, fwdchk FALSE
*Sep 18 12:59:56.982: IP: tableid=0, s=10.0.23.3 (Ethernet0/1), d=10.0.12.1 (Ethernet0/0) nexthop=10.0.12.1, routed via FIB
*Sep 18 12:59:56.982: IP: s=10.0.23.3 (Ethernet0/1), d=10.0.12.1 (Ethernet0/0), g=10.0.12.1, len 100, forward
*Sep 18 12:59:56.982:     ICMP type=0, code=0
*Sep 18 12:59:56.982: IP: s=10.0.23.3 (Ethernet0/1), d=10.0.12.1 (Ethernet0/0), len 100, sending full packet
*Sep 18 12:59:56.982:     ICMP type=0, code=0
```

- P2x-d unroutable(no ip route-cache): ping RT01→172.31.99.1 = 0%

**P2x-d unroutable(no ip route-cache) — RT02 show logging**

```
*Sep 18 13:00:01.729: IP: s=10.0.12.1 (Ethernet0/0), d=172.31.99.1 (nil), len 100, input feature, MCI Check(110), rtype 0, forus FALSE, sendself FALSE, mtu 0, fwdchk FALSE
*Sep 18 13:00:01.729: IP: s=10.0.12.1 (Ethernet0/0), d=172.31.99.1 (nil), len 100, unroutable
*Sep 18 13:00:01.729: IP: tableid=0, s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0) nexthop=10.0.12.1, routed via FIB
*Sep 18 13:00:01.729: IP: s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0), len 56, sending
*Sep 18 13:00:01.729: IP: s=10.0.12.2 (local), d=10.0.12.1 (Ethernet0/0), len 56, sending full packet
*Sep 18 13:00:01.730: IP: s=10.0.12.1 (Ethernet0/0), d=172.31.99.1 (nil), len 100, input feature, MCI Check(110), rtype 0, forus FALSE, sendself FALSE, mtu 0, fwdchk FALSE
*Sep 18 13:00:01.730: IP: s=10.0.12.1 (Ethernet0/0), d=172.31.99.1 (nil), len 100, unroutable
```

## P3 OSPF 隣接 debug 指紋  (2026-09-18 13:19)

**P3 基線 OSPF FULL**

```
43.048295736312866s

Neighbor ID     Pri   State           Dead Time   Address         Interface
2.2.2.2           1   FULL/DR         00:00:39    10.0.12.2       Ethernet0/0

Neighbor ID     Pri   State           Dead Time   Address         Interface
1.1.1.1           1   FULL/BDR        00:00:39    10.0.12.1       Ethernet0/0
```

- --- P3a mtu(RT02 ip mtu 1400 = 小さい側) ---

**P3a mtu(RT02 ip mtu 1400 = 小さい側) — RT01 show ip ospf neighbor**

```

Neighbor ID     Pri   State           Dead Time   Address         Interface
2.2.2.2           1   DOWN/DROTHER       -        10.0.12.2       Ethernet0/0
```

**P3a mtu(RT02 ip mtu 1400 = 小さい側) — RT02 show ip ospf neighbor**

```

Neighbor ID     Pri   State           Dead Time   Address         Interface
1.1.1.1           1   INIT/DROTHER    00:00:38    10.0.12.1       Ethernet0/0
```

**P3a mtu(RT02 ip mtu 1400 = 小さい側) [RT01] — RT01 show logging**

```
*Sep 18 13:00:56.428: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:00:57.251: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:00:57.251: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:00:57.251: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:00:57.251: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:00:57.251: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:00:57.251: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:00:57.251: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:00:57.251: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:00:57.251: OSPF-1 ADJ   Et0/0:    BDR: 1.1.1.1 (Id)
*Sep 18 13:00:57.251: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 1 AllRTR 0 AllDR 1
*Sep 18 13:00:57.251: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:00:57.251: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:00:57.251: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:00:57.251: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:00:57.251: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:00:57.251: OSPF-1 ADJ   Et0/0:    BDR: 1.1.1.1 (Id)
*Sep 18 13:00:57.639: OSPF-1 ADJ   Et0/0: Interface going Down
*Sep 18 13:00:57.639: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 10.0.12.2 is dead, state DOWN
*Sep 18 13:00:57.639: %OSPF-5-ADJCHG: Process 1, Nbr 2.2.2.2 on Ethernet0/0 from FULL to DOWN, Neighbor Down: Interface down or detached
*Sep 18 13:00:57.639: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Clean-up dbase exchange
*Sep 18 13:00:57.639: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:00:57.639: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:00:57.639: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:00:57.639: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:00:57.639: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:00:57.639: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:00:57.639: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:00:57.639: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:00:57.639: OSPF-1 ADJ   Et0/0: Remember old DR 2.2.2.2 (id)
*Sep 18 13:00:57.639: OSPF-1 ADJ   Et0/0: 1.1.1.1 address 10.0.12.1 is dead, state DOWN
*Sep 18 13:00:57.639: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:00:57.639: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:00:57.639: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:00:57.639: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:00:57.639: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:00:57.639: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:00:57.639: OSPF-1 ADJ   Et0/0: DR: none 
*Sep 18 13:00:57.639: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:00:57.639: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 0 AllRTR 0 AllDR 1
*Sep 18 13:00:57.639: OSPF-1 ADJ   Et0/0: Flush network LSA immediately
*Sep 18 13:00:57.639: OSPF-1 ADJ   Et0/0: Remember old DR 1.1.1.1 (id)
*Sep 18 13:00:57.639: OSPF-1 ADJ   Et0/0: Interface going Up
*Sep 18 13:00:57.639: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:00:57.640: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: 2 Way Communication to 2.2.2.2, state 2WAY
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: Backup seen event before WAIT timer
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0:    BDR: 1.1.1.1 (Id)
*Sep 18 13:00:57.640: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 1 AllRTR 0 AllDR 1
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Prepare dbase exchange
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0xB5D opt 0x52 flag 0x7 len 32
*Sep 18 13:00:57.640: OSPF-1 HELLO Et0/0: Send immediate hello to nbr 2.2.2.2, src address 10.0.12.2
*Sep 18 13:00:57.640: OSPF-1 HELLO Et0/0: Send hello to 10.0.12.2 area 0 from 10.0.12.1
*Sep 18 13:00:57.641: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1DA8 opt 0x52 flag 0x7 len 32  mtu 1400 state EXSTART
*Sep 18 13:00:57.641: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2 has smaller interface MTU
*Sep 18 13:00:57.641: OSPF-1 ADJ   Et0/0: NBR Negotiation Done. We are the SLAVE
*Sep 18 13:00:57.641: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Summary list built, size 0
*Sep 18 13:00:57.641: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1DA8 opt 0x52 flag 0x0 len 32
*Sep 18 13:00:58.044: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:00:58.044: OSPF-1 ADJ   Et0/0: Cannot see ourself in hello from 2.2.2.2, state INIT
*Sep 18 13:00:58.044: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Clean-up dbase exchange
*Sep 18 13:00:58.044: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:00:58.044: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:00:58.044: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:00:58.044: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:00:58.044: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:00:58.044: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:00:58.044: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:00:58.044: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:00:58.044: OSPF-1 ADJ   Et0/0: Remember old DR 2.2.2.2 (id)
*Sep 18 13:00:58.044: OSPF-1 HELLO Et0/0: Send immediate hello to nbr 2.2.2.2, src address 10.0.12.2
*Sep 18 13:00:58.044: OSPF-1 HELLO Et0/0: Send hello to 10.0.12.2 area 0 from 10.0.12.1
*Sep 18 13:00:58.045: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: 2 Way Communication to 2.2.2.2, state 2WAY
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0:    BDR: 2.2.2.2 (Id)
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Prepare dbase exchange
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1DA9 opt 0x52 flag 0x7 len 32
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0:    BDR: 2.2.2.2 (Id)
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0:    BDR: 2.2.2.2 (Id)
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x7 len 32  mtu 1400 state EXSTART
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2 has smaller interface MTU
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: NBR Negotiation Done. We are the SLAVE
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Summary list built, size 1
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x2 len 52
*Sep 18 13:01:02.738: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:01:02.738: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2 has smaller interface MTU
*Sep 18 13:01:02.738: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x2 len 52
*Sep 18 13:01:07.198: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:01:07.470: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:01:07.470: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2 has smaller interface MTU
*Sep 18 13:01:07.470: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x2 len 52
*Sep 18 13:01:07.836: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:01:12.454: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:01:12.454: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2 has smaller interface MTU
*Sep 18 13:01:12.454: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x2 len 52
*Sep 18 13:01:16.825: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:01:17.116: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:01:17.116: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2 has smaller interface MTU
*Sep 18 13:01:17.116: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x2 len 52
*Sep 18 13:01:17.182: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:01:21.643: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:01:21.643: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2 has smaller interface MTU
*Sep 18 13:01:21.643: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x2 len 52
*Sep 18 13:01:26.078: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:01:26.192: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:01:26.515: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:01:26.515: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2 has smaller interface MTU
*Sep 18 13:01:26.515: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x2 len 52
*Sep 18 13:01:31.309: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:01:31.309: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2 has smaller interface MTU
*Sep 18 13:01:31.309: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x2 len 52
*Sep 18 13:01:35.267: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:01:35.410: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:01:35.950: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:01:35.950: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2 has smaller interface MTU
*Sep 18 13:01:35.950: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x2 len 52
*Sep 18 13:01:40.653: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:01:40.653: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2 has smaller interface MTU
*Sep 18 13:01:40.653: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x2 len 52
*Sep 18 13:01:44.260: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:01:44.560: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:01:45.221: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:01:45.221: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2 has smaller interface MTU
*Sep 18 13:01:45.221: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x2 len 52
*Sep 18 13:01:50.209: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:01:50.209: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2 has smaller interface MTU
*Sep 18 13:01:50.209: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x2 len 52
*Sep 18 13:01:53.523: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:01:54.391: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:01:54.754: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:01:54.754: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2 has smaller interface MTU
*Sep 18 13:01:54.754: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x2 len 52
*Sep 18 13:01:59.343: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:01:59.343: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2 has smaller interface MTU
*Sep 18 13:01:59.343: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x2 len 52
*Sep 18 13:02:03.395: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:02:03.509: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:02:04.310: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:02:04.310: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2 has smaller interface MTU
*Sep 18 13:02:04.310: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x2 len 52
*Sep 18 13:02:09.006: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:02:09.006: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2 has smaller interface MTU
*Sep 18 13:02:09.006: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x2 len 52
*Sep 18 13:02:12.811: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:02:13.001: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:02:13.875: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:02:13.875: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2 has smaller interface MTU
*Sep 18 13:02:13.875: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x2 len 52
*Sep 18 13:02:18.441: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:02:18.441: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2 has smaller interface MTU
*Sep 18 13:02:18.441: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x2 len 52
*Sep 18 13:02:22.136: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:02:22.242: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:02:23.260: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:02:23.260: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2 has smaller interface MTU
*Sep 18 13:02:23.260: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x2 len 52
*Sep 18 13:02:28.146: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:02:28.146: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2 has smaller interface MTU
*Sep 18 13:02:28.146: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x2 len 52
*Sep 18 13:02:31.387: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:02:31.861: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:02:32.978: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:02:32.978: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2 has smaller interface MTU
*Sep 18 13:02:32.978: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x2 len 52
*Sep 18 13:02:37.522: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:02:37.522: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2 has smaller interface MTU
*Sep 18 13:02:37.522: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x2 len 52
*Sep 18 13:02:40.489: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:02:41.733: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:02:42.408: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:02:42.408: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2 has smaller interface MTU
*Sep 18 13:02:42.408: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x2 len 52
*Sep 18 13:02:47.301: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:02:47.301: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2 has smaller interface MTU
*Sep 18 13:02:47.301: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x2 len 52
*Sep 18 13:02:49.844: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:02:51.266: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:02:52.088: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:02:52.088: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2 has smaller interface MTU
*Sep 18 13:02:52.088: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x2 len 52
*Sep 18 13:02:56.727: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:02:56.727: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2 has smaller interface MTU
*Sep 18 13:02:56.727: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1C4 opt 0x52 flag 0x2 len 52
*Sep 18 13:02:57.298: OSPF-1 ADJ   Et0/0: Killing nbr 2.2.2.2 due to excessive (25) retransmissions
*Sep 18 13:02:57.298: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 10.0.12.2 is dead, state DOWN
*Sep 18 13:02:57.298: %OSPF-5-ADJCHG: Process 1, Nbr 2.2.2.2 on Ethernet0/0 from EXCHANGE to DOWN, Neighbor Down: Too many retransmissions
*Sep 18 13:02:57.298: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Clean-up dbase exchange
*Sep 18 13:02:57.298: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:02:57.298: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:02:57.298: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:02:57.298: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:02:57.298: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:02:57.298: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:02:59.274: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:02:59.274: OSPF-1 HELLO Et0/0: Nbr 2.2.2.2 10.0.12.2 is currently ignored
*Sep 18 13:03:00.365: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:03:00.376: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:03:00.376: OSPF-1 HELLO Et0/0: Nbr 2.2.2.2 10.0.12.2 is currently ignored
*Sep 18 13:03:09.169: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:03:09.169: OSPF-1 HELLO Et0/0: Nbr 2.2.2.2 10.0.12.2 is currently ignored
*Sep 18 13:03:09.630: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:03:09.631: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:03:09.631: OSPF-1 HELLO Et0/0: Nbr 2.2.2.2 10.0.12.2 is currently ignored
*Sep 18 13:03:18.622: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:03:18.622: OSPF-1 HELLO Et0/0: Nbr 2.2.2.2 10.0.12.2 is currently ignored
*Sep 18 13:03:18.869: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:03:27.949: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:03:28.135: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:03:28.135: OSPF-1 HELLO Et0/0: Nbr 2.2.2.2 10.0.12.2 is currently ignored
*Sep 18 13:03:37.600: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:03:37.848: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:03:37.848: OSPF-1 HELLO Et0/0: Nbr 2.2.2.2 10.0.12.2 is currently ignored
*Sep 18 13:03:47.173: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:03:47.173: OSPF-1 HELLO Et0/0: Nbr 2.2.2.2 10.0.12.2 is currently ignored
*Sep 18 13:03:47.339: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
```

**P3a mtu(RT02 ip mtu 1400 = 小さい側) [RT02] — RT02 show logging**

```
*Sep 18 13:00:56.428: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:00:56.428: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:00:56.428: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:00:56.428: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:00:56.428: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:00:56.428: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:00:56.428: OSPF-1 ADJ   Et0/0:    BDR: 1.1.1.1 (Id)
*Sep 18 13:00:56.428: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:00:56.428: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:00:56.428: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:00:56.428: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:00:56.428: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:00:56.428: OSPF-1 ADJ   Et0/0:    BDR: 1.1.1.1 (Id)
*Sep 18 13:00:57.037: OSPF EVENT Et0/0: ip mtu changed
*Sep 18 13:00:57.251: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:00:57.640: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: Cannot see ourself in hello from 1.1.1.1, state INIT
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Clean-up dbase exchange
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:00:57.640: OSPF-1 HELLO Et0/0: Send immediate hello to nbr 1.1.1.1, src address 10.0.12.1
*Sep 18 13:00:57.640: OSPF-1 HELLO Et0/0: Send hello to 10.0.12.1 area 0 from 10.0.12.2
*Sep 18 13:00:57.640: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: 2 Way Communication to 1.1.1.1, state 2WAY
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0:    BDR: 1.1.1.1 (Id)
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Prepare dbase exchange
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1DA8 opt 0x52 flag 0x7 len 32
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0:    BDR: 1.1.1.1 (Id)
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0:    BDR: 1.1.1.1 (Id)
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0xB5D opt 0x52 flag 0x7 len 32  mtu 1500 state EXSTART
*Sep 18 13:00:57.640: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:00:57.641: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1DA8 opt 0x52 flag 0x0 len 32  mtu 1500 state EXSTART
*Sep 18 13:00:57.641: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:00:58.043: OSPF-1 ADJ   Et0/0: Interface going Down
*Sep 18 13:00:58.043: OSPF-1 ADJ   Et0/0: 1.1.1.1 address 10.0.12.1 is dead, state DOWN
*Sep 18 13:00:58.043: %OSPF-5-ADJCHG: Process 1, Nbr 1.1.1.1 on Ethernet0/0 from EXSTART to DOWN, Neighbor Down: Interface down or detached
*Sep 18 13:00:58.043: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Clean-up dbase exchange
*Sep 18 13:00:58.043: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:00:58.043: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:00:58.043: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:00:58.043: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:00:58.043: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:00:58.043: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:00:58.043: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 10.0.12.2 is dead, state DOWN
*Sep 18 13:00:58.043: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:00:58.043: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:00:58.043: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:00:58.043: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:00:58.043: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:00:58.043: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:00:58.043: OSPF-1 ADJ   Et0/0: DR: none 
*Sep 18 13:00:58.043: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:00:58.043: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 0 AllRTR 0 AllDR 1
*Sep 18 13:00:58.043: OSPF-1 ADJ   Et0/0: Flush network LSA immediately
*Sep 18 13:00:58.043: OSPF-1 ADJ   Et0/0: Remember old DR 2.2.2.2 (id)
*Sep 18 13:00:58.044: OSPF-1 ADJ   Et0/0: Interface going Up
*Sep 18 13:00:58.044: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:00:58.045: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: 2 Way Communication to 1.1.1.1, state 2WAY
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: Backup seen event before WAIT timer
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0:    BDR: 2.2.2.2 (Id)
*Sep 18 13:00:58.045: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 1 AllRTR 0 AllDR 1
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Prepare dbase exchange
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x7 len 32
*Sep 18 13:00:58.045: OSPF-1 HELLO Et0/0: Send immediate hello to nbr 1.1.1.1, src address 10.0.12.1
*Sep 18 13:00:58.045: OSPF-1 HELLO Et0/0: Send hello to 10.0.12.1 area 0 from 10.0.12.2
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1DA9 opt 0x52 flag 0x7 len 32  mtu 1500 state EXSTART
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:00:58.045: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:01:02.737: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x7 len 32
*Sep 18 13:01:02.737: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [1]
*Sep 18 13:01:02.738: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:01:02.738: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:01:07.199: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:01:07.199: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:01:07.199: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:01:07.199: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:01:07.199: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:01:07.199: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:01:07.199: OSPF-1 ADJ   Et0/0:    BDR: 2.2.2.2 (Id)
*Sep 18 13:01:07.470: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x7 len 32
*Sep 18 13:01:07.470: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [2]
*Sep 18 13:01:07.489: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:01:07.489: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:01:07.835: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:01:12.454: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x7 len 32
*Sep 18 13:01:12.454: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [3]
*Sep 18 13:01:12.454: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:01:12.454: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:01:16.825: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:01:17.116: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x7 len 32
*Sep 18 13:01:17.116: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [4]
*Sep 18 13:01:17.116: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:01:17.116: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:01:17.181: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:01:21.642: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x7 len 32
*Sep 18 13:01:21.642: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [5]
*Sep 18 13:01:21.643: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:01:21.643: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:01:26.078: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:01:26.191: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:01:26.515: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x7 len 32
*Sep 18 13:01:26.515: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [6]
*Sep 18 13:01:26.516: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:01:26.516: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:01:31.308: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x7 len 32
*Sep 18 13:01:31.308: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [7]
*Sep 18 13:01:31.309: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:01:31.309: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:01:35.254: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:01:35.410: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:01:35.949: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x7 len 32
*Sep 18 13:01:35.949: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [8]
*Sep 18 13:01:35.958: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:01:35.958: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:01:40.653: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x7 len 32
*Sep 18 13:01:40.653: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [9]
*Sep 18 13:01:40.654: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:01:40.654: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:01:44.259: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:01:44.561: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:01:45.220: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x7 len 32
*Sep 18 13:01:45.220: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [10]
*Sep 18 13:01:45.222: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:01:45.222: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:01:50.209: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x7 len 32
*Sep 18 13:01:50.209: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [11]
*Sep 18 13:01:50.210: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:01:50.210: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:01:53.522: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:01:54.392: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:01:54.753: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x7 len 32
*Sep 18 13:01:54.753: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [12]
*Sep 18 13:01:54.754: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:01:54.754: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:01:59.342: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x7 len 32
*Sep 18 13:01:59.342: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [13]
*Sep 18 13:01:59.344: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:01:59.344: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:02:03.396: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:02:03.508: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:02:04.310: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x7 len 32
*Sep 18 13:02:04.310: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [14]
*Sep 18 13:02:04.311: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:02:04.311: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:02:08.992: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x7 len 32
*Sep 18 13:02:08.992: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [15]
*Sep 18 13:02:09.006: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:02:09.006: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:02:12.811: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:02:13.000: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:02:13.874: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x7 len 32
*Sep 18 13:02:13.874: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [16]
*Sep 18 13:02:13.875: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:02:13.875: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:02:18.441: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x7 len 32
*Sep 18 13:02:18.441: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [17]
*Sep 18 13:02:18.442: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:02:18.442: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:02:22.136: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:02:22.240: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:02:23.260: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x7 len 32
*Sep 18 13:02:23.260: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [18]
*Sep 18 13:02:23.261: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:02:23.261: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:02:28.133: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x7 len 32
*Sep 18 13:02:28.133: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [19]
*Sep 18 13:02:28.147: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:02:28.147: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:02:31.387: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:02:31.862: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:02:32.977: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x7 len 32
*Sep 18 13:02:32.978: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [20]
*Sep 18 13:02:32.979: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:02:32.979: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:02:37.522: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x7 len 32
*Sep 18 13:02:37.522: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [21]
*Sep 18 13:02:37.522: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:02:37.522: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:02:40.488: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:02:41.733: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:02:42.408: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x7 len 32
*Sep 18 13:02:42.408: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [22]
*Sep 18 13:02:42.408: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:02:42.408: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:02:47.296: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x7 len 32
*Sep 18 13:02:47.296: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [23]
*Sep 18 13:02:47.301: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:02:47.301: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:02:49.843: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:02:51.267: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:02:52.088: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x7 len 32
*Sep 18 13:02:52.088: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [24]
*Sep 18 13:02:52.088: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:02:52.088: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:02:56.727: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x7 len 32
*Sep 18 13:02:56.727: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [25]
*Sep 18 13:02:56.728: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1C4 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:02:56.728: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:02:59.274: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:03:00.365: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:03:00.365: OSPF-1 ADJ   Et0/0: Cannot see ourself in hello from 1.1.1.1, state INIT
*Sep 18 13:03:00.365: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Clean-up dbase exchange
*Sep 18 13:03:00.365: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:03:00.365: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:03:00.365: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:03:00.365: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:03:00.365: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:03:00.365: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:03:00.365: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:03:00.365: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:03:00.365: OSPF-1 ADJ   Et0/0: Remember old DR 1.1.1.1 (id)
*Sep 18 13:03:00.365: OSPF-1 HELLO Et0/0: Send immediate hello to nbr 1.1.1.1, src address 10.0.12.1
*Sep 18 13:03:00.365: OSPF-1 HELLO Et0/0: Send hello to 10.0.12.1 area 0 from 10.0.12.2
*Sep 18 13:03:09.168: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:03:09.630: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:03:09.630: OSPF-1 HELLO Et0/0: Send immediate hello to nbr 1.1.1.1, src address 10.0.12.1
*Sep 18 13:03:09.630: OSPF-1 HELLO Et0/0: Send hello to 10.0.12.1 area 0 from 10.0.12.2
*Sep 18 13:03:18.621: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:03:18.870: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:03:18.870: OSPF-1 HELLO Et0/0: No more immediate hello for nbr 1.1.1.1, which has been sent on this intf 2 times
*Sep 18 13:03:27.972: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:03:27.972: OSPF-1 HELLO Et0/0: No more immediate hello for nbr 1.1.1.1, which has been sent on this intf 2 times
*Sep 18 13:03:28.135: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:03:37.601: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:03:37.601: OSPF-1 HELLO Et0/0: No more immediate hello for nbr 1.1.1.1, which has been sent on this intf 2 times
*Sep 18 13:03:37.847: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:03:47.172: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:03:47.339: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:03:47.339: OSPF-1 HELLO Et0/0: No more immediate hello for nbr 1.1.1.1, which has been sent on this intf 2 times
```

- P3a mtu(RT02 ip mtu 1400 = 小さい側): 復旧 FULL = 43.32452464103699s

- --- P3a2 mtu + mtu-ignore を RT02(小さい側)だけ ---

**P3a2 mtu + mtu-ignore を RT02(小さい側)だけ — RT01 show ip ospf neighbor**

```

Neighbor ID     Pri   State           Dead Time   Address         Interface
2.2.2.2           1   FULL/BDR        00:00:36    10.0.12.2       Ethernet0/0
```

**P3a2 mtu + mtu-ignore を RT02(小さい側)だけ — RT02 show ip ospf neighbor**

```

Neighbor ID     Pri   State           Dead Time   Address         Interface
1.1.1.1           1   FULL/DR         00:00:35    10.0.12.1       Ethernet0/0
```

**P3a2 mtu + mtu-ignore を RT02(小さい側)だけ [RT01] — RT01 show logging**

```
*Sep 18 13:04:38.984: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:04:39.071: OSPF-1 ADJ   Et0/0: Interface going Down
*Sep 18 13:04:39.071: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 10.0.12.2 is dead, state DOWN
*Sep 18 13:04:39.071: %OSPF-5-ADJCHG: Process 1, Nbr 2.2.2.2 on Ethernet0/0 from FULL to DOWN, Neighbor Down: Interface down or detached
*Sep 18 13:04:39.071: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Clean-up dbase exchange
*Sep 18 13:04:39.071: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:04:39.071: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:04:39.071: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:04:39.071: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:04:39.071: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:04:39.071: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:04:39.071: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:04:39.071: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:04:39.071: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 1 AllRTR 0 AllDR 1
*Sep 18 13:04:39.071: OSPF-1 ADJ   Et0/0: Remember old DR 2.2.2.2 (id)
*Sep 18 13:04:39.071: OSPF-1 ADJ   Et0/0: 1.1.1.1 address 10.0.12.1 is dead, state DOWN
*Sep 18 13:04:39.071: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:04:39.071: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:04:39.071: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:04:39.071: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:04:39.071: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:04:39.071: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:04:39.071: OSPF-1 ADJ   Et0/0: DR: none 
*Sep 18 13:04:39.071: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:04:39.071: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 0 AllRTR 0 AllDR 1
*Sep 18 13:04:39.071: OSPF-1 ADJ   Et0/0: Flush network LSA immediately
*Sep 18 13:04:39.071: OSPF-1 ADJ   Et0/0: Remember old DR 1.1.1.1 (id)
*Sep 18 13:04:39.071: OSPF-1 ADJ   Et0/0: Interface going Up
*Sep 18 13:04:39.071: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:04:39.073: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: 2 Way Communication to 2.2.2.2, state 2WAY
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: Backup seen event before WAIT timer
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0:    BDR: 1.1.1.1 (Id)
*Sep 18 13:04:39.073: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 1 AllRTR 0 AllDR 1
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Prepare dbase exchange
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x185D opt 0x52 flag 0x7 len 32
*Sep 18 13:04:39.073: OSPF-1 HELLO Et0/0: Send immediate hello to nbr 2.2.2.2, src address 10.0.12.2
*Sep 18 13:04:39.073: OSPF-1 HELLO Et0/0: Send hello to 10.0.12.2 area 0 from 10.0.12.1
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1E36 opt 0x52 flag 0x7 len 32  mtu 1400 state EXSTART
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2 has smaller interface MTU
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: NBR Negotiation Done. We are the SLAVE
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Summary list built, size 1
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1E36 opt 0x52 flag 0x2 len 52
*Sep 18 13:04:39.074: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1E37 opt 0x52 flag 0x1 len 72  mtu 1400 state EXCHANGE
*Sep 18 13:04:39.074: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2 has smaller interface MTU
*Sep 18 13:04:39.074: OSPF-1 ADJ   Et0/0: Exchange Done with 2.2.2.2
*Sep 18 13:04:39.074: OSPF-1 ADJ   Et0/0: Send LS REQ to 2.2.2.2 length 48
*Sep 18 13:04:39.074: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1E37 opt 0x52 flag 0x0 len 32
*Sep 18 13:04:39.074: OSPF-1 ADJ   Et0/0: Rcv LS UPD from Nbr ID 2.2.2.2 length 96 LSA count 2
*Sep 18 13:04:39.074: OSPF-1 ADJ   Et0/0: Synchronized with 2.2.2.2, state FULL
*Sep 18 13:04:39.074: %OSPF-5-ADJCHG: Process 1, Nbr 2.2.2.2 on Ethernet0/0 from LOADING to FULL, Loading Done
*Sep 18 13:04:39.074: OSPF-1 ADJ   Et0/0: Rcv LS REQ from 2.2.2.2 length 36 LSA count 1
*Sep 18 13:04:39.098: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:04:39.098: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:04:39.098: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:04:39.098: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:04:39.098: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:04:39.098: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:04:39.098: OSPF-1 ADJ   Et0/0:    BDR: 1.1.1.1 (Id)
*Sep 18 13:04:39.442: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:04:39.442: OSPF-1 ADJ   Et0/0: Cannot see ourself in hello from 2.2.2.2, state INIT
*Sep 18 13:04:39.442: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Clean-up dbase exchange
*Sep 18 13:04:39.442: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:04:39.442: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:04:39.442: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:04:39.442: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:04:39.442: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:04:39.442: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:04:39.442: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:04:39.442: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:04:39.442: OSPF-1 ADJ   Et0/0: Remember old DR 2.2.2.2 (id)
*Sep 18 13:04:39.442: OSPF-1 HELLO Et0/0: Send immediate hello to nbr 2.2.2.2, src address 10.0.12.2
*Sep 18 13:04:39.442: OSPF-1 HELLO Et0/0: Send hello to 10.0.12.2 area 0 from 10.0.12.1
*Sep 18 13:04:39.443: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: 2 Way Communication to 2.2.2.2, state 2WAY
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0:    BDR: 2.2.2.2 (Id)
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Prepare dbase exchange
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1E38 opt 0x52 flag 0x7 len 32
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0:    BDR: 2.2.2.2 (Id)
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0:    BDR: 2.2.2.2 (Id)
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x19FE opt 0x52 flag 0x7 len 32  mtu 1400 state EXSTART
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2 has smaller interface MTU
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: NBR Negotiation Done. We are the SLAVE
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Summary list built, size 1
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x19FE opt 0x52 flag 0x2 len 52
*Sep 18 13:04:39.444: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x19FF opt 0x52 flag 0x1 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:04:39.444: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2 has smaller interface MTU
*Sep 18 13:04:39.444: OSPF-1 ADJ   Et0/0: Exchange Done with 2.2.2.2
*Sep 18 13:04:39.444: OSPF-1 ADJ   Et0/0: Synchronized with 2.2.2.2, state FULL
*Sep 18 13:04:39.444: %OSPF-5-ADJCHG: Process 1, Nbr 2.2.2.2 on Ethernet0/0 from LOADING to FULL, Loading Done
*Sep 18 13:04:39.444: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x19FF opt 0x52 flag 0x0 len 32
*Sep 18 13:04:39.445: OSPF-1 ADJ   Et0/0: Rcv LS REQ from 2.2.2.2 length 36 LSA count 1
*Sep 18 13:04:48.680: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:04:48.980: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:04:57.707: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:04:58.221: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:05:07.010: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:05:07.875: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:05:16.109: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:05:17.155: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:05:19.444: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Clean-up dbase exchange
*Sep 18 13:05:25.828: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:05:26.584: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:05:35.279: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:05:35.760: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
```

**P3a2 mtu + mtu-ignore を RT02(小さい側)だけ [RT02] — RT02 show logging**

```
*Sep 18 13:04:38.435: OSPF EVENT Et0/0: ip mtu changed
*Sep 18 13:04:38.985: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:04:38.985: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:04:38.985: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:04:38.985: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:04:38.985: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:04:38.985: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:04:38.985: OSPF-1 ADJ   Et0/0:    BDR: 1.1.1.1 (Id)
*Sep 18 13:04:38.985: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:04:38.985: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:04:38.985: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:04:38.985: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:04:38.985: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:04:38.985: OSPF-1 ADJ   Et0/0:    BDR: 1.1.1.1 (Id)
*Sep 18 13:04:39.072: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:04:39.072: OSPF-1 ADJ   Et0/0: Cannot see ourself in hello from 1.1.1.1, state INIT
*Sep 18 13:04:39.072: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Clean-up dbase exchange
*Sep 18 13:04:39.072: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:04:39.072: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:04:39.072: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:04:39.072: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:04:39.072: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:04:39.072: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:04:39.072: OSPF-1 HELLO Et0/0: Send immediate hello to nbr 1.1.1.1, src address 10.0.12.1
*Sep 18 13:04:39.072: OSPF-1 HELLO Et0/0: Send hello to 10.0.12.1 area 0 from 10.0.12.2
*Sep 18 13:04:39.073: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: 2 Way Communication to 1.1.1.1, state 2WAY
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0:    BDR: 1.1.1.1 (Id)
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Prepare dbase exchange
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1E36 opt 0x52 flag 0x7 len 32
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0:    BDR: 1.1.1.1 (Id)
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0:    BDR: 1.1.1.1 (Id)
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x185D opt 0x52 flag 0x7 len 32  mtu 1500 state EXSTART
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: First DBD and we are not SLAVE
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1E36 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: NBR Negotiation Done. We are the MASTER
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Summary list built, size 2
*Sep 18 13:04:39.073: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1E37 opt 0x52 flag 0x1 len 72
*Sep 18 13:04:39.074: OSPF-1 ADJ   Et0/0: Rcv LS REQ from 1.1.1.1 length 48 LSA count 2
*Sep 18 13:04:39.074: OSPF-1 ADJ   Et0/0: Send LS UPD to 10.0.12.1 length 96 LSA count 2
*Sep 18 13:04:39.074: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1E37 opt 0x52 flag 0x0 len 32  mtu 1500 state EXCHANGE
*Sep 18 13:04:39.074: OSPF-1 ADJ   Et0/0: Exchange Done with 1.1.1.1
*Sep 18 13:04:39.074: OSPF-1 ADJ   Et0/0: Send LS REQ to 1.1.1.1 length 36
*Sep 18 13:04:39.075: OSPF-1 ADJ   Et0/0: Rcv LS UPD from Nbr ID 1.1.1.1 length 64 LSA count 1
*Sep 18 13:04:39.098: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:04:39.124: OSPF-1 ADJ   Et0/0: Rcv LS UPD from Nbr ID 1.1.1.1 length 64 LSA count 1
*Sep 18 13:04:39.442: OSPF-1 ADJ   Et0/0: Interface going Down
*Sep 18 13:04:39.442: OSPF-1 ADJ   Et0/0: 1.1.1.1 address 10.0.12.1 is dead, state DOWN
*Sep 18 13:04:39.442: %OSPF-5-ADJCHG: Process 1, Nbr 1.1.1.1 on Ethernet0/0 from LOADING to DOWN, Neighbor Down: Interface down or detached
*Sep 18 13:04:39.442: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Clean-up dbase exchange
*Sep 18 13:04:39.442: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:04:39.442: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:04:39.442: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:04:39.442: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:04:39.442: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:04:39.442: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:04:39.442: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 10.0.12.2 is dead, state DOWN
*Sep 18 13:04:39.442: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:04:39.442: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:04:39.442: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:04:39.442: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:04:39.442: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:04:39.442: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:04:39.442: OSPF-1 ADJ   Et0/0: DR: none 
*Sep 18 13:04:39.442: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:04:39.442: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 0 AllRTR 0 AllDR 1
*Sep 18 13:04:39.442: OSPF-1 ADJ   Et0/0: Flush network LSA immediately
*Sep 18 13:04:39.442: OSPF-1 ADJ   Et0/0: Remember old DR 2.2.2.2 (id)
*Sep 18 13:04:39.442: OSPF-1 ADJ   Et0/0: Interface going Up
*Sep 18 13:04:39.442: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:04:39.443: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: 2 Way Communication to 1.1.1.1, state 2WAY
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: Backup seen event before WAIT timer
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0:    BDR: 2.2.2.2 (Id)
*Sep 18 13:04:39.443: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 1 AllRTR 0 AllDR 1
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Prepare dbase exchange
*Sep 18 13:04:39.443: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x19FE opt 0x52 flag 0x7 len 32
*Sep 18 13:04:39.443: OSPF-1 HELLO Et0/0: Send immediate hello to nbr 1.1.1.1, src address 10.0.12.1
*Sep 18 13:04:39.443: OSPF-1 HELLO Et0/0: Send hello to 10.0.12.1 area 0 from 10.0.12.2
*Sep 18 13:04:39.444: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1E38 opt 0x52 flag 0x7 len 32  mtu 1500 state EXSTART
*Sep 18 13:04:39.444: OSPF-1 ADJ   Et0/0: First DBD and we are not SLAVE
*Sep 18 13:04:39.444: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x19FE opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:04:39.444: OSPF-1 ADJ   Et0/0: NBR Negotiation Done. We are the MASTER
*Sep 18 13:04:39.444: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Summary list built, size 0
*Sep 18 13:04:39.444: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x19FF opt 0x52 flag 0x1 len 32
*Sep 18 13:04:39.444: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x19FF opt 0x52 flag 0x0 len 32  mtu 1500 state EXCHANGE
*Sep 18 13:04:39.444: OSPF-1 ADJ   Et0/0: Exchange Done with 1.1.1.1
*Sep 18 13:04:39.444: OSPF-1 ADJ   Et0/0: Send LS REQ to 1.1.1.1 length 36
*Sep 18 13:04:39.445: OSPF-1 ADJ   Et0/0: Rcv LS UPD from Nbr ID 1.1.1.1 length 64 LSA count 1
*Sep 18 13:04:39.445: OSPF-1 ADJ   Et0/0: Synchronized with 1.1.1.1, state FULL
*Sep 18 13:04:39.445: %OSPF-5-ADJCHG: Process 1, Nbr 1.1.1.1 on Ethernet0/0 from LOADING to FULL, Loading Done
*Sep 18 13:04:48.681: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:04:48.681: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:04:48.681: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:04:48.681: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:04:48.681: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:04:48.681: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:04:48.681: OSPF-1 ADJ   Et0/0:    BDR: 2.2.2.2 (Id)
*Sep 18 13:04:48.979: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:04:57.707: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:04:58.216: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:05:07.010: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:05:07.874: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:05:16.109: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:05:17.154: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:05:19.444: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Clean-up dbase exchange
*Sep 18 13:05:25.836: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:05:26.584: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:05:35.280: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:05:35.760: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
```

- P3a2 mtu + mtu-ignore を RT02(小さい側)だけ: 復旧 FULL = 0.6034331321716309s

- --- P3a3 mtu + mtu-ignore を RT01(大きい側)だけ ---

**P3a3 mtu + mtu-ignore を RT01(大きい側)だけ — RT01 show ip ospf neighbor**

```

Neighbor ID     Pri   State           Dead Time   Address         Interface
2.2.2.2           1   EXCHANGE/BDR    00:00:38    10.0.12.2       Ethernet0/0
```

**P3a3 mtu + mtu-ignore を RT01(大きい側)だけ — RT02 show ip ospf neighbor**

```

Neighbor ID     Pri   State           Dead Time   Address         Interface
1.1.1.1           1   EXSTART/DR      00:00:37    10.0.12.1       Ethernet0/0
```

**P3a3 mtu + mtu-ignore を RT01(大きい側)だけ [RT01] — RT01 show logging**

```
*Sep 18 13:05:48.943: OSPF-1 ADJ   Et0/0: Interface going Down
*Sep 18 13:05:48.943: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 10.0.12.2 is dead, state DOWN
*Sep 18 13:05:48.943: %OSPF-5-ADJCHG: Process 1, Nbr 2.2.2.2 on Ethernet0/0 from FULL to DOWN, Neighbor Down: Interface down or detached
*Sep 18 13:05:48.943: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Clean-up dbase exchange
*Sep 18 13:05:48.943: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:05:48.943: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:05:48.943: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:05:48.943: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:05:48.943: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:05:48.943: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:05:48.943: OSPF-1 ADJ   Et0/0: 1.1.1.1 address 10.0.12.1 is dead, state DOWN
*Sep 18 13:05:48.943: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:05:48.943: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:05:48.943: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:05:48.943: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:05:48.943: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:05:48.943: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:05:48.943: OSPF-1 ADJ   Et0/0: DR: none 
*Sep 18 13:05:48.943: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:05:48.943: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 0 AllRTR 0 AllDR 1
*Sep 18 13:05:48.943: OSPF-1 ADJ   Et0/0: Flush network LSA immediately
*Sep 18 13:05:48.943: OSPF-1 ADJ   Et0/0: Remember old DR 1.1.1.1 (id)
*Sep 18 13:05:48.943: OSPF-1 ADJ   Et0/0: Interface going Up
*Sep 18 13:05:48.943: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:05:48.944: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: 2 Way Communication to 2.2.2.2, state 2WAY
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: Backup seen event before WAIT timer
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0:    BDR: 1.1.1.1 (Id)
*Sep 18 13:05:48.944: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 1 AllRTR 0 AllDR 1
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Prepare dbase exchange
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x82 opt 0x52 flag 0x7 len 32
*Sep 18 13:05:48.944: OSPF-1 HELLO Et0/0: Send immediate hello to nbr 2.2.2.2, src address 10.0.12.2
*Sep 18 13:05:48.944: OSPF-1 HELLO Et0/0: Send hello to 10.0.12.2 area 0 from 10.0.12.1
*Sep 18 13:05:48.945: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1C21 opt 0x52 flag 0x7 len 32  mtu 1400 state EXSTART
*Sep 18 13:05:48.945: OSPF-1 ADJ   Et0/0: NBR Negotiation Done. We are the SLAVE
*Sep 18 13:05:48.945: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Summary list built, size 0
*Sep 18 13:05:48.945: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1C21 opt 0x52 flag 0x0 len 32
*Sep 18 13:05:49.365: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: Cannot see ourself in hello from 2.2.2.2, state INIT
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Clean-up dbase exchange
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: Remember old DR 2.2.2.2 (id)
*Sep 18 13:05:49.365: OSPF-1 HELLO Et0/0: Send immediate hello to nbr 2.2.2.2, src address 10.0.12.2
*Sep 18 13:05:49.365: OSPF-1 HELLO Et0/0: Send hello to 10.0.12.2 area 0 from 10.0.12.1
*Sep 18 13:05:49.366: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:05:49.366: OSPF-1 ADJ   Et0/0: 2 Way Communication to 2.2.2.2, state 2WAY
*Sep 18 13:05:49.366: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:05:49.366: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:05:49.366: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:05:49.366: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:05:49.366: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:05:49.366: OSPF-1 ADJ   Et0/0:    BDR: 2.2.2.2 (Id)
*Sep 18 13:05:49.366: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Prepare dbase exchange
*Sep 18 13:05:49.366: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1C22 opt 0x52 flag 0x7 len 32
*Sep 18 13:05:49.366: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:05:49.366: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:05:49.366: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:05:49.366: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:05:49.366: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:05:49.366: OSPF-1 ADJ   Et0/0:    BDR: 2.2.2.2 (Id)
*Sep 18 13:05:49.366: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:05:49.366: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:05:49.366: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:05:49.366: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:05:49.366: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:05:49.366: OSPF-1 ADJ   Et0/0:    BDR: 2.2.2.2 (Id)
*Sep 18 13:05:49.366: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x786 opt 0x52 flag 0x7 len 32  mtu 1400 state EXSTART
*Sep 18 13:05:49.366: OSPF-1 ADJ   Et0/0: NBR Negotiation Done. We are the SLAVE
*Sep 18 13:05:49.366: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Summary list built, size 1
*Sep 18 13:05:49.366: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x786 opt 0x52 flag 0x2 len 52
*Sep 18 13:05:54.018: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x786 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:05:54.018: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x786 opt 0x52 flag 0x2 len 52
*Sep 18 13:05:58.537: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:05:58.807: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x786 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:05:58.807: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x786 opt 0x52 flag 0x2 len 52
*Sep 18 13:05:59.313: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:06:03.557: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x786 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:06:03.557: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x786 opt 0x52 flag 0x2 len 52
*Sep 18 13:06:08.197: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x786 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:06:08.197: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x786 opt 0x52 flag 0x2 len 52
*Sep 18 13:06:08.517: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:06:08.792: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:06:12.920: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x786 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:06:12.920: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x786 opt 0x52 flag 0x2 len 52
*Sep 18 13:06:17.593: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x786 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:06:17.593: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x786 opt 0x52 flag 0x2 len 52
*Sep 18 13:06:17.819: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:06:18.776: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:06:22.348: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x786 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:06:22.348: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x786 opt 0x52 flag 0x2 len 52
*Sep 18 13:06:27.226: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:06:27.302: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x786 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:06:27.302: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x786 opt 0x52 flag 0x2 len 52
*Sep 18 13:06:28.659: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:06:31.981: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x786 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:06:31.981: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x786 opt 0x52 flag 0x2 len 52
*Sep 18 13:06:36.280: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:06:36.905: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x786 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:06:36.905: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x786 opt 0x52 flag 0x2 len 52
*Sep 18 13:06:38.039: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:06:41.678: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x786 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:06:41.678: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x786 opt 0x52 flag 0x2 len 52
*Sep 18 13:06:46.154: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:06:46.366: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x786 opt 0x52 flag 0x7 len 32  mtu 1400 state EXCHANGE
*Sep 18 13:06:46.366: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x786 opt 0x52 flag 0x2 len 52
*Sep 18 13:06:47.710: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
```

**P3a3 mtu + mtu-ignore を RT01(大きい側)だけ [RT02] — RT02 show logging**

```
*Sep 18 13:05:47.550: OSPF EVENT Et0/0: ip mtu changed
*Sep 18 13:05:48.944: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: Cannot see ourself in hello from 1.1.1.1, state INIT
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Clean-up dbase exchange
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: Remember old DR 1.1.1.1 (id)
*Sep 18 13:05:48.944: OSPF-1 HELLO Et0/0: Send immediate hello to nbr 1.1.1.1, src address 10.0.12.1
*Sep 18 13:05:48.944: OSPF-1 HELLO Et0/0: Send hello to 10.0.12.1 area 0 from 10.0.12.2
*Sep 18 13:05:48.944: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: 2 Way Communication to 1.1.1.1, state 2WAY
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0:    BDR: 1.1.1.1 (Id)
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Prepare dbase exchange
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1C21 opt 0x52 flag 0x7 len 32
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0:    BDR: 1.1.1.1 (Id)
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:05:48.944: OSPF-1 ADJ   Et0/0:    BDR: 1.1.1.1 (Id)
*Sep 18 13:05:48.945: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x82 opt 0x52 flag 0x7 len 32  mtu 1500 state EXSTART
*Sep 18 13:05:48.945: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:05:48.945: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1C21 opt 0x52 flag 0x0 len 32  mtu 1500 state EXSTART
*Sep 18 13:05:48.945: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:05:49.364: OSPF-1 ADJ   Et0/0: Interface going Down
*Sep 18 13:05:49.364: OSPF-1 ADJ   Et0/0: 1.1.1.1 address 10.0.12.1 is dead, state DOWN
*Sep 18 13:05:49.364: %OSPF-5-ADJCHG: Process 1, Nbr 1.1.1.1 on Ethernet0/0 from EXSTART to DOWN, Neighbor Down: Interface down or detached
*Sep 18 13:05:49.364: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Clean-up dbase exchange
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 10.0.12.2 is dead, state DOWN
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: DR: none 
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:05:49.365: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 0 AllRTR 0 AllDR 1
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: Flush network LSA immediately
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: Remember old DR 2.2.2.2 (id)
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: Interface going Up
*Sep 18 13:05:49.365: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:05:49.365: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: 2 Way Communication to 1.1.1.1, state 2WAY
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: Backup seen event before WAIT timer
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0:    BDR: 2.2.2.2 (Id)
*Sep 18 13:05:49.365: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 1 AllRTR 0 AllDR 1
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Prepare dbase exchange
*Sep 18 13:05:49.365: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x786 opt 0x52 flag 0x7 len 32
*Sep 18 13:05:49.365: OSPF-1 HELLO Et0/0: Send immediate hello to nbr 1.1.1.1, src address 10.0.12.1
*Sep 18 13:05:49.366: OSPF-1 HELLO Et0/0: Send hello to 10.0.12.1 area 0 from 10.0.12.2
*Sep 18 13:05:49.366: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1C22 opt 0x52 flag 0x7 len 32  mtu 1500 state EXSTART
*Sep 18 13:05:49.366: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:05:49.366: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x786 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:05:49.366: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:05:54.017: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x786 opt 0x52 flag 0x7 len 32
*Sep 18 13:05:54.017: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [1]
*Sep 18 13:05:54.018: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x786 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:05:54.018: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:05:58.537: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:05:58.537: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:05:58.537: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:05:58.537: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:05:58.537: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:05:58.537: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:05:58.537: OSPF-1 ADJ   Et0/0:    BDR: 2.2.2.2 (Id)
*Sep 18 13:05:58.806: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x786 opt 0x52 flag 0x7 len 32
*Sep 18 13:05:58.806: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [2]
*Sep 18 13:05:58.807: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x786 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:05:58.807: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:05:59.313: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:06:03.556: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x786 opt 0x52 flag 0x7 len 32
*Sep 18 13:06:03.556: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [3]
*Sep 18 13:06:03.557: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x786 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:06:03.557: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:06:08.196: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x786 opt 0x52 flag 0x7 len 32
*Sep 18 13:06:08.196: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [4]
*Sep 18 13:06:08.197: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x786 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:06:08.197: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:06:08.518: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:06:08.791: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:06:12.919: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x786 opt 0x52 flag 0x7 len 32
*Sep 18 13:06:12.919: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [5]
*Sep 18 13:06:12.920: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x786 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:06:12.920: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:06:17.592: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x786 opt 0x52 flag 0x7 len 32
*Sep 18 13:06:17.592: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [6]
*Sep 18 13:06:17.593: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x786 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:06:17.593: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:06:17.819: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:06:18.774: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:06:22.347: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x786 opt 0x52 flag 0x7 len 32
*Sep 18 13:06:22.347: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [7]
*Sep 18 13:06:22.349: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x786 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:06:22.349: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:06:27.227: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:06:27.301: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x786 opt 0x52 flag 0x7 len 32
*Sep 18 13:06:27.301: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [8]
*Sep 18 13:06:27.302: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x786 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:06:27.302: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:06:28.658: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:06:31.981: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x786 opt 0x52 flag 0x7 len 32
*Sep 18 13:06:31.981: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [9]
*Sep 18 13:06:31.982: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x786 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:06:31.982: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:06:36.281: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:06:36.904: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x786 opt 0x52 flag 0x7 len 32
*Sep 18 13:06:36.904: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [10]
*Sep 18 13:06:36.905: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x786 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:06:36.905: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:06:38.039: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:06:41.677: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x786 opt 0x52 flag 0x7 len 32
*Sep 18 13:06:41.677: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [11]
*Sep 18 13:06:41.678: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x786 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:06:41.678: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:06:46.154: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:06:46.366: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x786 opt 0x52 flag 0x7 len 32
*Sep 18 13:06:46.366: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [12]
*Sep 18 13:06:46.367: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x786 opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:06:46.367: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1 has larger interface MTU
*Sep 18 13:06:47.710: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
```

- P3a3 mtu + mtu-ignore を RT01(大きい側)だけ: 復旧 FULL = 0.6778554916381836s

- --- P3b hello(RT02 hello-interval 5) ---

**P3b hello(RT02 hello-interval 5) — RT01 show ip ospf neighbor**

```

```

**P3b hello(RT02 hello-interval 5) — RT02 show ip ospf neighbor**

```

```

**P3b hello(RT02 hello-interval 5) [RT01] — RT01 show logging**

```
*Sep 18 13:06:53.787: %OSPF-5-ADJCHG: Process 1, Nbr 2.2.2.2 on Ethernet0/0 from LOADING to FULL, Loading Done
*Sep 18 13:07:02.396: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:07:02.396: OSPF-1 HELLO Et0/0: Mismatched hello parameters from 10.0.12.2
*Sep 18 13:07:02.396: OSPF-1 HELLO Et0/0: Dead R 20 C 40, Hello R 5 C 10 Mask R 255.255.255.0 C 255.255.255.0
*Sep 18 13:07:02.641: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:07:07.172: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:07:07.172: OSPF-1 HELLO Et0/0: Mismatched hello parameters from 10.0.12.2
*Sep 18 13:07:07.172: OSPF-1 HELLO Et0/0: Dead R 20 C 40, Hello R 5 C 10 Mask R 255.255.255.0 C 255.255.255.0
*Sep 18 13:07:11.757: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:07:11.757: OSPF-1 HELLO Et0/0: Mismatched hello parameters from 10.0.12.2
*Sep 18 13:07:11.757: OSPF-1 HELLO Et0/0: Dead R 20 C 40, Hello R 5 C 10 Mask R 255.255.255.0 C 255.255.255.0
*Sep 18 13:07:12.541: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:07:16.668: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:07:16.668: OSPF-1 HELLO Et0/0: Mismatched hello parameters from 10.0.12.2
*Sep 18 13:07:16.668: OSPF-1 HELLO Et0/0: Dead R 20 C 40, Hello R 5 C 10 Mask R 255.255.255.0 C 255.255.255.0
*Sep 18 13:07:21.352: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:07:21.352: OSPF-1 HELLO Et0/0: Mismatched hello parameters from 10.0.12.2
*Sep 18 13:07:21.352: OSPF-1 HELLO Et0/0: Dead R 20 C 40, Hello R 5 C 10 Mask R 255.255.255.0 C 255.255.255.0
*Sep 18 13:07:21.771: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:07:25.874: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:07:25.874: OSPF-1 HELLO Et0/0: Mismatched hello parameters from 10.0.12.2
*Sep 18 13:07:25.874: OSPF-1 HELLO Et0/0: Dead R 20 C 40, Hello R 5 C 10 Mask R 255.255.255.0 C 255.255.255.0
*Sep 18 13:07:30.670: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:07:30.670: OSPF-1 HELLO Et0/0: Mismatched hello parameters from 10.0.12.2
*Sep 18 13:07:30.670: OSPF-1 HELLO Et0/0: Dead R 20 C 40, Hello R 5 C 10 Mask R 255.255.255.0 C 255.255.255.0
*Sep 18 13:07:31.579: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:07:33.787: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Clean-up dbase exchange
*Sep 18 13:07:35.455: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:07:35.455: OSPF-1 HELLO Et0/0: Mismatched hello parameters from 10.0.12.2
*Sep 18 13:07:35.455: OSPF-1 HELLO Et0/0: Dead R 20 C 40, Hello R 5 C 10 Mask R 255.255.255.0 C 255.255.255.0
*Sep 18 13:07:38.427: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 10.0.12.2 is dead
*Sep 18 13:07:38.427: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 10.0.12.2 is dead, state DOWN
*Sep 18 13:07:38.427: %OSPF-5-ADJCHG: Process 1, Nbr 2.2.2.2 on Ethernet0/0 from FULL to DOWN, Neighbor Down: Dead timer expired
*Sep 18 13:07:38.427: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:07:38.427: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:07:38.427: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:07:38.427: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:07:38.427: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:07:38.427: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:07:40.291: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:07:40.291: OSPF-1 HELLO Et0/0: Mismatched hello parameters from 10.0.12.2
*Sep 18 13:07:40.291: OSPF-1 HELLO Et0/0: Dead R 20 C 40, Hello R 5 C 10 Mask R 255.255.255.0 C 255.255.255.0
*Sep 18 13:07:41.478: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:07:45.083: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:07:45.083: OSPF-1 HELLO Et0/0: Mismatched hello parameters from 10.0.12.2
*Sep 18 13:07:45.083: OSPF-1 HELLO Et0/0: Dead R 20 C 40, Hello R 5 C 10 Mask R 255.255.255.0 C 255.255.255.0
```

**P3b hello(RT02 hello-interval 5) [RT02] — RT02 show logging**

```
*Sep 18 13:07:02.396: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:07:02.642: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:07:02.642: OSPF-1 HELLO Et0/0: Mismatched hello parameters from 10.0.12.1
*Sep 18 13:07:02.642: OSPF-1 HELLO Et0/0: Dead R 40 C 20, Hello R 10 C 5 Mask R 255.255.255.0 C 255.255.255.0
*Sep 18 13:07:07.172: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:07:11.757: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:07:12.545: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:07:12.545: OSPF-1 HELLO Et0/0: Mismatched hello parameters from 10.0.12.1
*Sep 18 13:07:12.545: OSPF-1 HELLO Et0/0: Dead R 40 C 20, Hello R 10 C 5 Mask R 255.255.255.0 C 255.255.255.0
*Sep 18 13:07:16.667: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:07:20.883: OSPF-1 ADJ   Et0/0: 1.1.1.1 address 10.0.12.1 is dead
*Sep 18 13:07:20.883: OSPF-1 ADJ   Et0/0: 1.1.1.1 address 10.0.12.1 is dead, state DOWN
*Sep 18 13:07:20.883: %OSPF-5-ADJCHG: Process 1, Nbr 1.1.1.1 on Ethernet0/0 from FULL to DOWN, Neighbor Down: Dead timer expired
*Sep 18 13:07:20.883: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Clean-up dbase exchange
*Sep 18 13:07:20.883: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:07:20.883: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:07:20.883: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:07:20.883: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:07:20.883: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:07:20.883: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:07:20.883: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:07:20.883: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:07:20.883: OSPF-1 ADJ   Et0/0: Remember old DR 1.1.1.1 (id)
*Sep 18 13:07:21.352: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:07:21.771: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:07:21.771: OSPF-1 HELLO Et0/0: Mismatched hello parameters from 10.0.12.1
*Sep 18 13:07:21.771: OSPF-1 HELLO Et0/0: Dead R 40 C 20, Hello R 10 C 5 Mask R 255.255.255.0 C 255.255.255.0
*Sep 18 13:07:25.871: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:07:30.669: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:07:31.586: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:07:31.586: OSPF-1 HELLO Et0/0: Mismatched hello parameters from 10.0.12.1
*Sep 18 13:07:31.586: OSPF-1 HELLO Et0/0: Dead R 40 C 20, Hello R 10 C 5 Mask R 255.255.255.0 C 255.255.255.0
*Sep 18 13:07:35.454: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:07:40.291: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:07:41.478: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:07:41.479: OSPF-1 HELLO Et0/0: Mismatched hello parameters from 10.0.12.1
*Sep 18 13:07:41.479: OSPF-1 HELLO Et0/0: Dead R 40 C 20, Hello R 10 C 5 Mask R 255.255.255.0 C 255.255.255.0
*Sep 18 13:07:45.082: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
```

- P3b hello(RT02 hello-interval 5): 復旧 FULL = 11.28831171989441s

- --- P3c area(RT02 を area 1) ---

**P3c area(RT02 を area 1) — RT01 show ip ospf neighbor**

```

```

**P3c area(RT02 を area 1) — RT02 show ip ospf neighbor**

```

```

**P3c area(RT02 を area 1) [RT01] — RT01 show logging**

```
*Sep 18 13:08:06.724: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.2, area 0.0.0.0, mismatched area 0.0.0.1 in the header
*Sep 18 13:08:10.492: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:08:16.029: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.2, area 0.0.0.0, mismatched area 0.0.0.1 in the header
*Sep 18 13:08:20.002: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:08:25.753: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.2, area 0.0.0.0, mismatched area 0.0.0.1 in the header
*Sep 18 13:08:29.513: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:08:32.068: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Clean-up dbase exchange
*Sep 18 13:08:35.497: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.2, area 0.0.0.0, mismatched area 0.0.0.1 in the header
*Sep 18 13:08:39.324: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:08:41.748: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 10.0.12.2 is dead
*Sep 18 13:08:41.748: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 10.0.12.2 is dead, state DOWN
*Sep 18 13:08:41.748: %OSPF-5-ADJCHG: Process 1, Nbr 2.2.2.2 on Ethernet0/0 from FULL to DOWN, Neighbor Down: Dead timer expired
*Sep 18 13:08:41.748: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:08:41.748: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:08:41.748: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:08:41.748: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:08:41.748: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:08:41.748: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:08:44.796: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.2, area 0.0.0.0, mismatched area 0.0.0.1 in the header
*Sep 18 13:08:48.403: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:08:54.319: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.2, area 0.0.0.0, mismatched area 0.0.0.1 in the header
```

**P3c area(RT02 を area 1) [RT02] — RT02 show logging**

```
*Sep 18 13:08:06.630: OSPF-1 EVENT: Config: no network 10.0.12.0 255.255.255.0 area 0
*Sep 18 13:08:06.630: OSPF-1 ADJ   Et0/0: Interface going Down
*Sep 18 13:08:06.630: OSPF-1 ADJ   Et0/0: 1.1.1.1 address 10.0.12.1 is dead, state DOWN
*Sep 18 13:08:06.630: %OSPF-5-ADJCHG: Process 1, Nbr 1.1.1.1 on Ethernet0/0 from FULL to DOWN, Neighbor Down: Interface down or detached
*Sep 18 13:08:06.630: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Clean-up dbase exchange
*Sep 18 13:08:06.630: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:08:06.630: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:08:06.630: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:08:06.630: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:08:06.630: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:08:06.630: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:08:06.630: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:08:06.630: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:08:06.630: OSPF-1 ADJ   Et0/0: Remember old DR 1.1.1.1 (id)
*Sep 18 13:08:06.630: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 10.0.12.2 is dead, state DOWN
*Sep 18 13:08:06.630: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:08:06.630: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:08:06.630: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:08:06.630: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:08:06.630: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:08:06.630: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:08:06.630: OSPF-1 ADJ   Et0/0: DR: none 
*Sep 18 13:08:06.630: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:08:06.630: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 0 AllRTR 0 AllDR 1
*Sep 18 13:08:06.630: OSPF-1 ADJ   Et0/0: Flush network LSA immediately
*Sep 18 13:08:06.630: OSPF-1 ADJ   Et0/0: Remember old DR 2.2.2.2 (id)
*Sep 18 13:08:06.630: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 0 AllRTR 1 AllDR 1
*Sep 18 13:08:06.723: OSPF-1 EVENT: Config: network 10.0.12.0 255.255.255.0 area 1
*Sep 18 13:08:06.723: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 1 AllRTR 1 AllDR 0
*Sep 18 13:08:06.723: OSPF-1 ADJ   Et0/0: Interface going Up
*Sep 18 13:08:06.723: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 10.0.12.2
*Sep 18 13:08:10.493: %OSPF-4-ERRRCV: Received invalid packet: mismatched area ID from backbone area from 10.0.12.1, Ethernet0/0
*Sep 18 13:08:16.028: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 10.0.12.2
*Sep 18 13:08:20.003: %OSPF-4-ERRRCV: Received invalid packet: mismatched area ID from backbone area from 10.0.12.1, Ethernet0/0
*Sep 18 13:08:25.752: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 10.0.12.2
*Sep 18 13:08:29.518: %OSPF-4-ERRRCV: Received invalid packet: mismatched area ID from backbone area from 10.0.12.1, Ethernet0/0
*Sep 18 13:08:35.492: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 10.0.12.2
*Sep 18 13:08:39.325: %OSPF-4-ERRRCV: Received invalid packet: mismatched area ID from backbone area from 10.0.12.1, Ethernet0/0
*Sep 18 13:08:44.795: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 10.0.12.2
*Sep 18 13:08:46.723: OSPF-1 ADJ   Et0/0: end of Wait on interface
*Sep 18 13:08:46.723: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:08:46.723: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:08:46.723: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:08:46.723: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:08:46.723: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:08:46.723: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:08:46.723: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:08:46.723: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 1 AllRTR 0 AllDR 1
*Sep 18 13:08:48.403: %OSPF-4-ERRRCV: Received invalid packet: mismatched area ID from backbone area from 10.0.12.1, Ethernet0/0
*Sep 18 13:08:54.319: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 10.0.12.2
*Sep 18 13:08:57.690: %OSPF-4-ERRRCV: Received invalid packet: mismatched area ID from backbone area from 10.0.12.1, Ethernet0/0
```

- P3c area(RT02 を area 1): 復旧 FULL = 11.21224331855774s

- --- P3d auth_type(RT02 のみ message-digest) ---

**P3d auth_type(RT02 のみ message-digest) — RT01 show ip ospf neighbor**

```

```

**P3d auth_type(RT02 のみ message-digest) — RT02 show ip ospf neighbor**

```

```

**P3d auth_type(RT02 のみ message-digest) [RT01] — RT01 show logging**

```
*Sep 18 13:09:18.651: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:09:19.447: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.2 : Mismatched Authentication type. Input packet specified type 2, we use type 0
*Sep 18 13:09:28.099: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:09:28.495: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.2 : Mismatched Authentication type. Input packet specified type 2, we use type 0
*Sep 18 13:09:37.934: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:09:38.010: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.2 : Mismatched Authentication type. Input packet specified type 2, we use type 0
*Sep 18 13:09:40.670: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Clean-up dbase exchange
*Sep 18 13:09:47.294: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.2 : Mismatched Authentication type. Input packet specified type 2, we use type 0
*Sep 18 13:09:47.920: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:09:49.677: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 10.0.12.2 is dead
*Sep 18 13:09:49.677: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 10.0.12.2 is dead, state DOWN
*Sep 18 13:09:49.677: %OSPF-5-ADJCHG: Process 1, Nbr 2.2.2.2 on Ethernet0/0 from FULL to DOWN, Neighbor Down: Dead timer expired
*Sep 18 13:09:49.677: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:09:49.677: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:09:49.677: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:09:49.677: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:09:49.677: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:09:49.677: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:09:57.172: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.2 : Mismatched Authentication type. Input packet specified type 2, we use type 0
*Sep 18 13:09:57.602: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
```

**P3d auth_type(RT02 のみ message-digest) [RT02] — RT02 show logging**

```
*Sep 18 13:09:18.652: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.1 : Mismatched Authentication type. Input packet specified type 0, we use type 2
*Sep 18 13:09:19.447: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:09:19.447: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:09:28.100: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.1 : Mismatched Authentication type. Input packet specified type 0, we use type 2
*Sep 18 13:09:28.494: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:09:28.494: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:09:37.935: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.1 : Mismatched Authentication type. Input packet specified type 0, we use type 2
*Sep 18 13:09:38.010: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:09:38.010: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:09:40.670: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Clean-up dbase exchange
*Sep 18 13:09:47.289: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:09:47.289: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:09:47.920: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.1 : Mismatched Authentication type. Input packet specified type 0, we use type 2
*Sep 18 13:09:51.783: OSPF-1 ADJ   Et0/0: 1.1.1.1 address 10.0.12.1 is dead
*Sep 18 13:09:51.783: OSPF-1 ADJ   Et0/0: 1.1.1.1 address 10.0.12.1 is dead, state DOWN
*Sep 18 13:09:51.783: %OSPF-5-ADJCHG: Process 1, Nbr 1.1.1.1 on Ethernet0/0 from FULL to DOWN, Neighbor Down: Dead timer expired
*Sep 18 13:09:51.783: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:09:51.783: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:09:51.783: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:09:51.783: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:09:51.783: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:09:51.783: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:09:51.783: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:09:51.783: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:09:51.783: OSPF-1 ADJ   Et0/0: Remember old DR 1.1.1.1 (id)
*Sep 18 13:09:57.171: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:09:57.171: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:09:57.603: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.1 : Mismatched Authentication type. Input packet specified type 0, we use type 2
```

- P3d auth_type(RT02 のみ message-digest): 復旧 FULL = 0.6003730297088623s

- --- P3e auth_key(両側 MD5・鍵文字列違い) ---

**P3e auth_key(両側 MD5・鍵文字列違い) — RT01 show ip ospf neighbor**

```

```

**P3e auth_key(両側 MD5・鍵文字列違い) — RT02 show ip ospf neighbor**

```

```

**P3e auth_key(両側 MD5・鍵文字列違い) [RT01] — RT01 show logging**

```
*Sep 18 13:10:13.995: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:10:14.023: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.2 : Mismatched Authentication key - ID 1
*Sep 18 13:10:18.010: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:10:18.010: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:10:18.187: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.2 : Mismatched Authentication key - ID 1
*Sep 18 13:10:18.564: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.2 : Mismatched Authentication key - ID 1
*Sep 18 13:10:18.744: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:10:23.153: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.2 : Mismatched Authentication key - ID 1
*Sep 18 13:10:23.257: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:10:27.563: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.2 : Mismatched Authentication key - ID 1
*Sep 18 13:10:27.657: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:10:27.657: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:10:27.855: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:10:28.087: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.2 : Mismatched Authentication key - ID 1
*Sep 18 13:10:32.657: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.2 : Mismatched Authentication key - ID 1
*Sep 18 13:10:32.832: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:10:37.019: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:10:37.019: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:10:37.103: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.2 : Mismatched Authentication key - ID 1
*Sep 18 13:10:37.523: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.2 : Mismatched Authentication key - ID 1
*Sep 18 13:10:37.541: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:10:42.079: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:10:42.402: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.2 : Mismatched Authentication key - ID 1
*Sep 18 13:10:46.126: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.2 : Mismatched Authentication key - ID 1
*Sep 18 13:10:46.684: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:10:46.684: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:10:47.025: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:10:47.080: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.2 : Mismatched Authentication key - ID 1
*Sep 18 13:10:49.061: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Clean-up dbase exchange
*Sep 18 13:10:51.069: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 10.0.12.2 is dead
*Sep 18 13:10:51.069: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 10.0.12.2 is dead, state DOWN
*Sep 18 13:10:51.069: %OSPF-5-ADJCHG: Process 1, Nbr 2.2.2.2 on Ethernet0/0 from FULL to DOWN, Neighbor Down: Dead timer expired
*Sep 18 13:10:51.069: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:10:51.069: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:10:51.069: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:10:51.069: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:10:51.069: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:10:51.069: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:10:55.758: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.2 : Mismatched Authentication key - ID 1
*Sep 18 13:10:56.475: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:10:56.475: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
```

**P3e auth_key(両側 MD5・鍵文字列違い) [RT02] — RT02 show logging**

```
*Sep 18 13:10:13.995: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.1 : Mismatched Authentication key - ID 1
*Sep 18 13:10:14.022: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:10:18.011: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.1 : Mismatched Authentication key - ID 1
*Sep 18 13:10:18.185: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:10:18.185: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:10:18.563: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:10:18.744: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.1 : Mismatched Authentication key - ID 1
*Sep 18 13:10:23.129: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:10:23.258: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.1 : Mismatched Authentication key - ID 1
*Sep 18 13:10:27.561: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:10:27.561: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:10:27.658: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.1 : Mismatched Authentication key - ID 1
*Sep 18 13:10:27.856: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.1 : Mismatched Authentication key - ID 1
*Sep 18 13:10:28.083: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:10:32.657: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:10:32.833: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.1 : Mismatched Authentication key - ID 1
*Sep 18 13:10:37.020: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.1 : Mismatched Authentication key - ID 1
*Sep 18 13:10:37.102: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:10:37.102: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:10:37.522: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:10:37.542: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.1 : Mismatched Authentication key - ID 1
*Sep 18 13:10:42.080: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.1 : Mismatched Authentication key - ID 1
*Sep 18 13:10:42.401: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:10:46.126: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:10:46.126: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:10:46.684: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.1 : Mismatched Authentication key - ID 1
*Sep 18 13:10:47.026: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.1 : Mismatched Authentication key - ID 1
*Sep 18 13:10:47.079: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:10:49.062: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Clean-up dbase exchange
*Sep 18 13:10:51.067: OSPF-1 ADJ   Et0/0: 1.1.1.1 address 10.0.12.1 is dead
*Sep 18 13:10:51.067: OSPF-1 ADJ   Et0/0: 1.1.1.1 address 10.0.12.1 is dead, state DOWN
*Sep 18 13:10:51.067: %OSPF-5-ADJCHG: Process 1, Nbr 1.1.1.1 on Ethernet0/0 from FULL to DOWN, Neighbor Down: Dead timer expired
*Sep 18 13:10:51.067: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:10:51.067: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:10:51.067: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:10:51.067: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:10:51.067: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:10:51.067: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:10:51.067: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:10:51.067: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:10:51.067: OSPF-1 ADJ   Et0/0: Remember old DR 1.1.1.1 (id)
*Sep 18 13:10:55.757: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:10:55.757: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:10:56.476: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.1 : Mismatched Authentication key - ID 1
```

- P3e auth_key(両側 MD5・鍵文字列違い): 復旧 FULL = 11.222607374191284s

- --- P3e2 auth_keyid(両側 MD5・鍵ID違い 1 vs 2) ---

**P3e2 auth_keyid(両側 MD5・鍵ID違い 1 vs 2) — RT01 show ip ospf neighbor**

```

```

**P3e2 auth_keyid(両側 MD5・鍵ID違い 1 vs 2) — RT02 show ip ospf neighbor**

```

```

**P3e2 auth_keyid(両側 MD5・鍵ID違い 1 vs 2) [RT01] — RT01 show logging**

```
*Sep 18 13:11:26.382: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:11:26.382: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:11:26.772: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.2 : Mismatched Authentication Key - Invalid cryptographic authentication Key ID 2 on interface
*Sep 18 13:11:36.295: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:11:36.295: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:11:36.735: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.2 : Mismatched Authentication Key - Invalid cryptographic authentication Key ID 2 on interface
*Sep 18 13:11:45.930: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:11:45.930: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:11:46.584: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.2 : Mismatched Authentication Key - Invalid cryptographic authentication Key ID 2 on interface
*Sep 18 13:11:48.175: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Clean-up dbase exchange
*Sep 18 13:11:55.570: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:11:55.570: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:11:55.896: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.2 : Mismatched Authentication Key - Invalid cryptographic authentication Key ID 2 on interface
*Sep 18 13:11:57.479: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 10.0.12.2 is dead
*Sep 18 13:11:57.479: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 10.0.12.2 is dead, state DOWN
*Sep 18 13:11:57.479: %OSPF-5-ADJCHG: Process 1, Nbr 2.2.2.2 on Ethernet0/0 from FULL to DOWN, Neighbor Down: Dead timer expired
*Sep 18 13:11:57.479: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:11:57.479: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:11:57.479: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:11:57.479: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:11:57.479: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:11:57.479: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:12:05.053: OSPF-1 ADJ   Et0/0: Send with youngest Key 1
*Sep 18 13:12:05.053: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:12:05.696: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.2 : Mismatched Authentication Key - Invalid cryptographic authentication Key ID 2 on interface
```

**P3e2 auth_keyid(両側 MD5・鍵ID違い 1 vs 2) [RT02] — RT02 show logging**

```
*Sep 18 13:11:26.394: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.1 : Mismatched Authentication Key - Invalid cryptographic authentication Key ID 1 on interface
*Sep 18 13:11:26.771: OSPF-1 ADJ   Et0/0: Send with youngest Key 2
*Sep 18 13:11:26.771: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:11:36.295: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.1 : Mismatched Authentication Key - Invalid cryptographic authentication Key ID 1 on interface
*Sep 18 13:11:36.734: OSPF-1 ADJ   Et0/0: Send with youngest Key 2
*Sep 18 13:11:36.734: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:11:45.930: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.1 : Mismatched Authentication Key - Invalid cryptographic authentication Key ID 1 on interface
*Sep 18 13:11:46.584: OSPF-1 ADJ   Et0/0: Send with youngest Key 2
*Sep 18 13:11:46.584: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:11:48.175: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Clean-up dbase exchange
*Sep 18 13:11:55.571: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.1 : Mismatched Authentication Key - Invalid cryptographic authentication Key ID 1 on interface
*Sep 18 13:11:55.895: OSPF-1 ADJ   Et0/0: Send with youngest Key 2
*Sep 18 13:11:55.895: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:11:59.447: OSPF-1 ADJ   Et0/0: 1.1.1.1 address 10.0.12.1 is dead
*Sep 18 13:11:59.447: OSPF-1 ADJ   Et0/0: 1.1.1.1 address 10.0.12.1 is dead, state DOWN
*Sep 18 13:11:59.447: %OSPF-5-ADJCHG: Process 1, Nbr 1.1.1.1 on Ethernet0/0 from FULL to DOWN, Neighbor Down: Dead timer expired
*Sep 18 13:11:59.447: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:11:59.447: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:11:59.447: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:11:59.447: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:11:59.447: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:11:59.447: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:11:59.447: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:11:59.447: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:11:59.447: OSPF-1 ADJ   Et0/0: Remember old DR 1.1.1.1 (id)
*Sep 18 13:12:05.054: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.1 : Mismatched Authentication Key - Invalid cryptographic authentication Key ID 1 on interface
*Sep 18 13:12:05.695: OSPF-1 ADJ   Et0/0: Send with youngest Key 2
*Sep 18 13:12:05.695: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
```

- P3e2 auth_keyid(両側 MD5・鍵ID違い 1 vs 2): 復旧 FULL = 0.6047096252441406s

- --- P3f nettype(RT02 point-to-point・RT01 broadcast) ---

**P3f nettype(RT02 point-to-point・RT01 broadcast) — RT01 show ip ospf neighbor**

```

Neighbor ID     Pri   State           Dead Time   Address         Interface
2.2.2.2           1   FULL/DR         00:00:36    10.0.12.2       Ethernet0/0
```

**P3f nettype(RT02 point-to-point・RT01 broadcast) — RT02 show ip ospf neighbor**

```

Neighbor ID     Pri   State           Dead Time   Address         Interface
1.1.1.1           0   FULL/  -        00:00:35    10.0.12.1       Ethernet0/0
```

**P3f nettype(RT02 point-to-point・RT01 broadcast) — RT01# show ip route ospf**

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

Gateway of last resort is 10.0.12.2 to network 0.0.0.0
```

**P3f nettype(RT02 point-to-point・RT01 broadcast) — RT02# show ip route ospf**

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
```

**P3f nettype(RT02 point-to-point・RT01 broadcast) — RT01# show ip ospf interface Ethernet0/0 | include Network Type|Neighbor|State**

```
  Attached via Network Statement
  Process ID 1, Router ID 1.1.1.1, Network Type BROADCAST, Cost: 10
  Transmit Delay is 1 sec, State DROTHER, Priority 1
  Neighbor Count is 1, Adjacent neighbor count is 1
```

**P3f nettype(RT02 point-to-point・RT01 broadcast) — RT02# show ip ospf interface Ethernet0/0 | include Network Type|Neighbor|State**

```
  Attached via Network Statement
  Process ID 1, Router ID 2.2.2.2, Network Type POINT_TO_POINT, Cost: 10
  Transmit Delay is 1 sec, State POINT_TO_POINT
  Neighbor Count is 1, Adjacent neighbor count is 1
```

**P3f nettype(RT02 point-to-point・RT01 broadcast) [RT01] — RT01 show logging**

```
*Sep 18 13:12:21.171: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:12:21.171: OSPF-1 ADJ   Et0/0: Cannot see ourself in hello from 2.2.2.2, state INIT
*Sep 18 13:12:21.171: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Clean-up dbase exchange
*Sep 18 13:12:21.171: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:12:21.171: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:12:21.171: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:12:21.171: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:12:21.171: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:12:21.171: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:12:21.171: OSPF-1 HELLO Et0/0: Send immediate hello to nbr 2.2.2.2, src address 10.0.12.2
*Sep 18 13:12:21.171: OSPF-1 HELLO Et0/0: Send hello to 10.0.12.2 area 0 from 10.0.12.1
*Sep 18 13:12:21.172: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:12:21.172: OSPF-1 ADJ   Et0/0: 2 Way Communication to 2.2.2.2, state 2WAY
*Sep 18 13:12:21.172: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:12:21.172: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:12:21.172: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:12:21.172: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:12:21.172: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:12:21.172: OSPF-1 ADJ   Et0/0:    BDR: 2.2.2.2 (Id)
*Sep 18 13:12:21.172: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Prepare dbase exchange
*Sep 18 13:12:21.172: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1703 opt 0x52 flag 0x7 len 32
*Sep 18 13:12:21.172: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x2288 opt 0x52 flag 0x7 len 32  mtu 1500 state EXSTART
*Sep 18 13:12:21.172: OSPF-1 ADJ   Et0/0: NBR Negotiation Done. We are the SLAVE
*Sep 18 13:12:21.172: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Summary list built, size 2
*Sep 18 13:12:21.172: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x2288 opt 0x52 flag 0x2 len 72
*Sep 18 13:12:21.173: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x2289 opt 0x52 flag 0x1 len 72  mtu 1500 state EXCHANGE
*Sep 18 13:12:21.173: OSPF-1 ADJ   Et0/0: Exchange Done with 2.2.2.2
*Sep 18 13:12:21.173: OSPF-1 ADJ   Et0/0: Send LS REQ to 2.2.2.2 length 36
*Sep 18 13:12:21.173: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x2289 opt 0x52 flag 0x0 len 32
*Sep 18 13:12:21.173: OSPF-1 ADJ   Et0/0: Rcv LS UPD from Nbr ID 2.2.2.2 length 64 LSA count 1
*Sep 18 13:12:21.173: OSPF-1 ADJ   Et0/0: Synchronized with 2.2.2.2, state FULL
*Sep 18 13:12:21.173: %OSPF-5-ADJCHG: Process 1, Nbr 2.2.2.2 on Ethernet0/0 from LOADING to FULL, Loading Done
*Sep 18 13:12:21.694: OSPF-1 ADJ   Et0/0: Interface going Down
*Sep 18 13:12:21.694: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 10.0.12.2 is dead, state DOWN
*Sep 18 13:12:21.694: %OSPF-5-ADJCHG: Process 1, Nbr 2.2.2.2 on Ethernet0/0 from FULL to DOWN, Neighbor Down: Interface down or detached
*Sep 18 13:12:21.694: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Clean-up dbase exchange
*Sep 18 13:12:21.694: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:12:21.694: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:12:21.694: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:12:21.694: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:12:21.694: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:12:21.694: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:12:21.694: OSPF-1 ADJ   Et0/0: 1.1.1.1 address 10.0.12.1 is dead, state DOWN
*Sep 18 13:12:21.694: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:12:21.694: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:12:21.694: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:12:21.694: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:12:21.694: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:12:21.694: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:12:21.694: OSPF-1 ADJ   Et0/0: DR: none 
*Sep 18 13:12:21.694: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:12:21.694: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 0 AllRTR 0 AllDR 1
*Sep 18 13:12:21.694: OSPF-1 ADJ   Et0/0: Flush network LSA immediately
*Sep 18 13:12:21.694: OSPF-1 ADJ   Et0/0: Remember old DR 1.1.1.1 (id)
*Sep 18 13:12:21.694: OSPF-1 ADJ   Et0/0: Interface going Up
*Sep 18 13:12:21.694: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:12:21.695: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:12:21.695: OSPF-1 ADJ   Et0/0: 2 Way Communication to 2.2.2.2, state 2WAY
*Sep 18 13:12:21.695: OSPF-1 HELLO Et0/0: Send immediate hello to nbr 2.2.2.2, src address 10.0.12.2
*Sep 18 13:12:21.695: OSPF-1 HELLO Et0/0: Send hello to 10.0.12.2 area 0 from 10.0.12.1
*Sep 18 13:12:21.696: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x228B opt 0x52 flag 0x7 len 32  mtu 1500 state 2WAY
*Sep 18 13:12:21.696: OSPF-1 ADJ   Et0/0: Nbr state is 2WAY
*Sep 18 13:12:22.077: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:12:22.077: OSPF-1 ADJ   Et0/0: Cannot see ourself in hello from 2.2.2.2, state INIT
*Sep 18 13:12:22.077: OSPF-1 HELLO Et0/0: Send immediate hello to nbr 2.2.2.2, src address 10.0.12.2
*Sep 18 13:12:22.077: OSPF-1 HELLO Et0/0: Send hello to 10.0.12.2 area 0 from 10.0.12.1
*Sep 18 13:12:22.081: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:12:22.081: OSPF-1 ADJ   Et0/0: 2 Way Communication to 2.2.2.2, state 2WAY
*Sep 18 13:12:22.081: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1DAB opt 0x52 flag 0x7 len 32  mtu 1500 state 2WAY
*Sep 18 13:12:22.081: OSPF-1 ADJ   Et0/0: Nbr state is 2WAY
*Sep 18 13:12:26.675: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1DAB opt 0x52 flag 0x7 len 32  mtu 1500 state 2WAY
*Sep 18 13:12:26.675: OSPF-1 ADJ   Et0/0: Nbr state is 2WAY
*Sep 18 13:12:31.193: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1DAB opt 0x52 flag 0x7 len 32  mtu 1500 state 2WAY
*Sep 18 13:12:31.193: OSPF-1 ADJ   Et0/0: Nbr state is 2WAY
*Sep 18 13:12:31.377: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:12:31.748: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:12:35.744: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1DAB opt 0x52 flag 0x7 len 32  mtu 1500 state 2WAY
*Sep 18 13:12:35.744: OSPF-1 ADJ   Et0/0: Nbr state is 2WAY
*Sep 18 13:12:40.452: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1DAB opt 0x52 flag 0x7 len 32  mtu 1500 state 2WAY
*Sep 18 13:12:40.452: OSPF-1 ADJ   Et0/0: Nbr state is 2WAY
*Sep 18 13:12:40.864: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:12:40.932: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:12:45.441: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1DAB opt 0x52 flag 0x7 len 32  mtu 1500 state 2WAY
*Sep 18 13:12:45.441: OSPF-1 ADJ   Et0/0: Nbr state is 2WAY
*Sep 18 13:12:49.872: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:12:50.066: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1DAB opt 0x52 flag 0x7 len 32  mtu 1500 state 2WAY
*Sep 18 13:12:50.066: OSPF-1 ADJ   Et0/0: Nbr state is 2WAY
*Sep 18 13:12:50.562: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:12:54.820: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1DAB opt 0x52 flag 0x7 len 32  mtu 1500 state 2WAY
*Sep 18 13:12:54.820: OSPF-1 ADJ   Et0/0: Nbr state is 2WAY
*Sep 18 13:12:59.266: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:12:59.503: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1DAB opt 0x52 flag 0x7 len 32  mtu 1500 state 2WAY
*Sep 18 13:12:59.503: OSPF-1 ADJ   Et0/0: Nbr state is 2WAY
*Sep 18 13:13:00.108: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:13:01.694: OSPF-1 ADJ   Et0/0: end of Wait on interface
*Sep 18 13:13:01.694: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:13:01.694: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:13:01.694: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:13:01.694: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:13:01.694: OSPF-1 ADJ   Et0/0:    BDR: 2.2.2.2 (Id)
*Sep 18 13:13:01.694: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Prepare dbase exchange
*Sep 18 13:13:01.694: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x125E opt 0x52 flag 0x7 len 32
*Sep 18 13:13:04.233: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1DAB opt 0x52 flag 0x7 len 32  mtu 1500 state EXSTART
*Sep 18 13:13:04.233: OSPF-1 ADJ   Et0/0: NBR Negotiation Done. We are the SLAVE
*Sep 18 13:13:04.233: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Summary list built, size 1
*Sep 18 13:13:04.233: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1DAB opt 0x52 flag 0x2 len 52
*Sep 18 13:13:04.234: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x1DAC opt 0x52 flag 0x1 len 52  mtu 1500 state EXCHANGE
*Sep 18 13:13:04.234: OSPF-1 ADJ   Et0/0: Exchange Done with 2.2.2.2
*Sep 18 13:13:04.234: OSPF-1 ADJ   Et0/0: Send LS REQ to 2.2.2.2 length 36
*Sep 18 13:13:04.234: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x1DAC opt 0x52 flag 0x0 len 32
*Sep 18 13:13:04.234: OSPF-1 ADJ   Et0/0: Rcv LS UPD from Nbr ID 2.2.2.2 length 64 LSA count 1
*Sep 18 13:13:04.235: OSPF-1 ADJ   Et0/0: Synchronized with 2.2.2.2, state FULL
*Sep 18 13:13:04.235: %OSPF-5-ADJCHG: Process 1, Nbr 2.2.2.2 on Ethernet0/0 from LOADING to FULL, Loading Done
*Sep 18 13:13:04.235: OSPF-1 ADJ   Et0/0: Rcv LS REQ from 2.2.2.2 length 36 LSA count 1
*Sep 18 13:13:08.601: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:13:09.467: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:13:17.819: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:13:18.658: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
```

**P3f nettype(RT02 point-to-point・RT01 broadcast) [RT02] — RT02 show logging**

```
*Sep 18 13:12:21.170: OSPF-1 ADJ   Et0/0: Interface going Down
*Sep 18 13:12:21.170: OSPF-1 ADJ   Et0/0: 1.1.1.1 address 10.0.12.1 is dead, state DOWN
*Sep 18 13:12:21.170: %OSPF-5-ADJCHG: Process 1, Nbr 1.1.1.1 on Ethernet0/0 from FULL to DOWN, Neighbor Down: Interface down or detached
*Sep 18 13:12:21.170: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Clean-up dbase exchange
*Sep 18 13:12:21.170: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:12:21.170: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:12:21.170: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:12:21.170: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:12:21.170: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:12:21.170: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:12:21.170: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:12:21.170: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:12:21.170: OSPF-1 ADJ   Et0/0: Remember old DR 1.1.1.1 (id)
*Sep 18 13:12:21.170: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 10.0.12.2 is dead, state DOWN
*Sep 18 13:12:21.170: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:12:21.170: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:12:21.170: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:12:21.170: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:12:21.170: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:12:21.170: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:12:21.170: OSPF-1 ADJ   Et0/0: DR: none 
*Sep 18 13:12:21.170: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:12:21.170: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 0 AllRTR 0 AllDR 1
*Sep 18 13:12:21.171: OSPF-1 ADJ   Et0/0: Flush network LSA immediately
*Sep 18 13:12:21.171: OSPF-1 ADJ   Et0/0: Remember old DR 2.2.2.2 (id)
*Sep 18 13:12:21.171: OSPF-1 ADJ   Et0/0: Interface going Up
*Sep 18 13:12:21.171: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:12:21.171: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:12:21.172: OSPF-1 ADJ   Et0/0: 2 Way Communication to 1.1.1.1, state 2WAY
*Sep 18 13:12:21.172: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Prepare dbase exchange
*Sep 18 13:12:21.172: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x2288 opt 0x52 flag 0x7 len 32
*Sep 18 13:12:21.172: %OSPF-4-NET_TYPE_MISMATCH: Received Hello from 1.1.1.1 on Ethernet0/0 indicating a  potential 
*Sep 18 13:12:21.172: OSPF-1 HELLO Et0/0: Send immediate hello to nbr 1.1.1.1, src address 10.0.12.1
*Sep 18 13:12:21.172: OSPF-1 HELLO Et0/0: Send hello to 10.0.12.1 area 0 from 10.0.12.2
*Sep 18 13:12:21.172: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1703 opt 0x52 flag 0x7 len 32  mtu 1500 state EXSTART
*Sep 18 13:12:21.172: OSPF-1 ADJ   Et0/0: First DBD and we are not SLAVE
*Sep 18 13:12:21.172: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x2288 opt 0x52 flag 0x2 len 72  mtu 1500 state EXSTART
*Sep 18 13:12:21.172: OSPF-1 ADJ   Et0/0: NBR Negotiation Done. We are the MASTER
*Sep 18 13:12:21.172: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Summary list built, size 3
*Sep 18 13:12:21.172: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x2289 opt 0x52 flag 0x1 len 72
*Sep 18 13:12:21.173: OSPF-1 ADJ   Et0/0: Rcv LS REQ from 1.1.1.1 length 36 LSA count 1
*Sep 18 13:12:21.173: OSPF-1 ADJ   Et0/0: Send LS UPD to 10.0.12.1 length 64 LSA count 1
*Sep 18 13:12:21.173: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x2289 opt 0x52 flag 0x0 len 32  mtu 1500 state EXCHANGE
*Sep 18 13:12:21.173: OSPF-1 ADJ   Et0/0: Exchange Done with 1.1.1.1
*Sep 18 13:12:21.173: OSPF-1 ADJ   Et0/0: Synchronized with 1.1.1.1, state FULL
*Sep 18 13:12:21.173: %OSPF-5-ADJCHG: Process 1, Nbr 1.1.1.1 on Ethernet0/0 from LOADING to FULL, Loading Done
*Sep 18 13:12:21.694: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:12:21.694: OSPF-1 ADJ   Et0/0: Cannot see ourself in hello from 1.1.1.1, state INIT
*Sep 18 13:12:21.694: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Clean-up dbase exchange
*Sep 18 13:12:21.694: OSPF-1 HELLO Et0/0: Send immediate hello to nbr 1.1.1.1, src address 10.0.12.1
*Sep 18 13:12:21.694: OSPF-1 HELLO Et0/0: Send hello to 10.0.12.1 area 0 from 10.0.12.2
*Sep 18 13:12:21.696: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:12:21.696: OSPF-1 ADJ   Et0/0: 2 Way Communication to 1.1.1.1, state 2WAY
*Sep 18 13:12:21.696: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Prepare dbase exchange
*Sep 18 13:12:21.696: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x228B opt 0x52 flag 0x7 len 32
*Sep 18 13:12:22.076: OSPF-1 ADJ   Et0/0: Interface going Down
*Sep 18 13:12:22.076: OSPF-1 ADJ   Et0/0: 1.1.1.1 address 10.0.12.1 is dead, state DOWN
*Sep 18 13:12:22.076: %OSPF-5-ADJCHG: Process 1, Nbr 1.1.1.1 on Ethernet0/0 from EXSTART to DOWN, Neighbor Down: Interface down or detached
*Sep 18 13:12:22.076: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Clean-up dbase exchange
*Sep 18 13:12:22.076: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 10.0.12.2 is dead, state DOWN
*Sep 18 13:12:22.076: OSPF-1 ADJ   Et0/0: Interface going Up
*Sep 18 13:12:22.076: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:12:22.078: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:12:22.078: OSPF-1 ADJ   Et0/0: 2 Way Communication to 1.1.1.1, state 2WAY
*Sep 18 13:12:22.078: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Prepare dbase exchange
*Sep 18 13:12:22.078: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1DAB opt 0x52 flag 0x7 len 32
*Sep 18 13:12:22.078: OSPF-1 HELLO Et0/0: Send immediate hello to nbr 1.1.1.1, src address 10.0.12.1
*Sep 18 13:12:22.078: OSPF-1 HELLO Et0/0: Send hello to 10.0.12.1 area 0 from 10.0.12.2
*Sep 18 13:12:26.673: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1DAB opt 0x52 flag 0x7 len 32
*Sep 18 13:12:26.673: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [1]
*Sep 18 13:12:31.192: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1DAB opt 0x52 flag 0x7 len 32
*Sep 18 13:12:31.192: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [2]
*Sep 18 13:12:31.378: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:12:31.748: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:12:35.743: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1DAB opt 0x52 flag 0x7 len 32
*Sep 18 13:12:35.743: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [3]
*Sep 18 13:12:40.452: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1DAB opt 0x52 flag 0x7 len 32
*Sep 18 13:12:40.452: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [4]
*Sep 18 13:12:40.864: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:12:40.931: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:12:45.440: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1DAB opt 0x52 flag 0x7 len 32
*Sep 18 13:12:45.440: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [5]
*Sep 18 13:12:49.873: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:12:50.063: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1DAB opt 0x52 flag 0x7 len 32
*Sep 18 13:12:50.063: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [6]
*Sep 18 13:12:50.562: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:12:54.820: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1DAB opt 0x52 flag 0x7 len 32
*Sep 18 13:12:54.820: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [7]
*Sep 18 13:12:59.266: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:12:59.503: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1DAB opt 0x52 flag 0x7 len 32
*Sep 18 13:12:59.503: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [8]
*Sep 18 13:13:00.107: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:13:01.695: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x125E opt 0x52 flag 0x7 len 32  mtu 1500 state EXSTART
*Sep 18 13:13:01.695: OSPF-1 ADJ   Et0/0: First DBD and we are not SLAVE
*Sep 18 13:13:04.228: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1DAB opt 0x52 flag 0x7 len 32
*Sep 18 13:13:04.228: OSPF-1 ADJ   Et0/0: Retransmitting DBD to 1.1.1.1 [9]
*Sep 18 13:13:04.233: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1DAB opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:13:04.233: OSPF-1 ADJ   Et0/0: NBR Negotiation Done. We are the MASTER
*Sep 18 13:13:04.233: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Summary list built, size 1
*Sep 18 13:13:04.234: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x1DAC opt 0x52 flag 0x1 len 52
*Sep 18 13:13:04.234: OSPF-1 ADJ   Et0/0: Rcv LS REQ from 1.1.1.1 length 36 LSA count 1
*Sep 18 13:13:04.234: OSPF-1 ADJ   Et0/0: Send LS UPD to 10.0.12.1 length 64 LSA count 1
*Sep 18 13:13:04.234: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x1DAC opt 0x52 flag 0x0 len 32  mtu 1500 state EXCHANGE
*Sep 18 13:13:04.234: OSPF-1 ADJ   Et0/0: Exchange Done with 1.1.1.1
*Sep 18 13:13:04.234: OSPF-1 ADJ   Et0/0: Send LS REQ to 1.1.1.1 length 36
*Sep 18 13:13:04.235: OSPF-1 ADJ   Et0/0: Rcv LS UPD from Nbr ID 1.1.1.1 length 64 LSA count 1
*Sep 18 13:13:04.235: OSPF-1 ADJ   Et0/0: Synchronized with 1.1.1.1, state FULL
*Sep 18 13:13:04.235: %OSPF-5-ADJCHG: Process 1, Nbr 1.1.1.1 on Ethernet0/0 from LOADING to FULL, Loading Done
*Sep 18 13:13:08.602: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:13:09.467: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:13:17.819: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:13:18.657: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
```

- P3f nettype(RT02 point-to-point・RT01 broadcast): 復旧 FULL = 0.6027977466583252s

- --- P3g prio0(両側 priority 0) ---

**P3g prio0(両側 priority 0) — RT01 show ip ospf neighbor**

```

Neighbor ID     Pri   State           Dead Time   Address         Interface
2.2.2.2           0   2WAY/DROTHER    00:00:37    10.0.12.2       Ethernet0/0
```

**P3g prio0(両側 priority 0) — RT02 show ip ospf neighbor**

```

Neighbor ID     Pri   State           Dead Time   Address         Interface
1.1.1.1           0   2WAY/DROTHER    00:00:36    10.0.12.1       Ethernet0/0
```

**P3g prio0(両側 priority 0) [RT01] — RT01 show logging**

```
*Sep 18 13:13:30.544: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:13:30.544: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:13:30.544: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:13:30.544: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:13:30.544: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:13:30.544: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:13:30.544: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:13:30.544: OSPF-1 ADJ   Et0/0:    BDR: 2.2.2.2 (Id)
*Sep 18 13:13:30.544: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 0 AllRTR 0 AllDR 1
*Sep 18 13:13:30.544: OSPF-1 ADJ   Et0/0: Set flush timer
*Sep 18 13:13:30.544: OSPF-1 ADJ   Et0/0: Remember old DR 1.1.1.1 (id)
*Sep 18 13:13:31.551: OSPF-1 ADJ   Et0/0: Interface going Down
*Sep 18 13:13:31.551: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 10.0.12.2 is dead, state DOWN
*Sep 18 13:13:31.551: %OSPF-5-ADJCHG: Process 1, Nbr 2.2.2.2 on Ethernet0/0 from FULL to DOWN, Neighbor Down: Interface down or detached
*Sep 18 13:13:31.551: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Clean-up dbase exchange
*Sep 18 13:13:31.551: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:13:31.551: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:13:31.551: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:13:31.551: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:13:31.551: OSPF-1 ADJ   Et0/0: DR: none 
*Sep 18 13:13:31.551: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:13:31.551: OSPF-1 ADJ   Et0/0: Remember old DR 2.2.2.2 (id)
*Sep 18 13:13:31.551: OSPF-1 ADJ   Et0/0: 1.1.1.1 address 10.0.12.1 is dead, state DOWN
*Sep 18 13:13:31.551: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:13:31.551: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:13:31.551: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:13:31.551: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:13:31.551: OSPF-1 ADJ   Et0/0: DR: none 
*Sep 18 13:13:31.551: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:13:31.551: OSPF-1 ADJ   Et0/0: Interface going Up
*Sep 18 13:13:31.551: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:13:31.980: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:13:40.995: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:13:41.385: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:13:41.385: OSPF-1 ADJ   Et0/0: 2 Way Communication to 2.2.2.2, state 2WAY
*Sep 18 13:13:50.714: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:13:50.892: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:13:59.782: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:14:00.171: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:14:09.511: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:14:10.098: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:14:11.551: OSPF-1 ADJ   Et0/0: end of Wait on interface
*Sep 18 13:14:11.551: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:14:11.551: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:14:11.551: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:14:11.551: OSPF-1 ADJ   Et0/0: DR: none 
*Sep 18 13:14:11.551: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:14:19.224: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:14:19.536: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:14:29.047: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:14:29.387: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
```

**P3g prio0(両側 priority 0) [RT02] — RT02 show logging**

```
*Sep 18 13:13:31.073: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:13:31.073: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:13:31.073: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:13:31.073: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:13:31.073: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:13:31.073: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:13:31.073: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:13:31.073: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:13:31.073: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 0 AllRTR 0 AllDR 1
*Sep 18 13:13:31.551: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:13:31.551: OSPF-1 ADJ   Et0/0: Cannot see ourself in hello from 1.1.1.1, state INIT
*Sep 18 13:13:31.551: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Clean-up dbase exchange
*Sep 18 13:13:31.551: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:13:31.551: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:13:31.551: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:13:31.551: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:13:31.551: OSPF-1 ADJ   Et0/0: DR: none 
*Sep 18 13:13:31.551: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:13:31.551: OSPF-1 ADJ   Et0/0: Remember old DR 1.1.1.1 (id)
*Sep 18 13:13:31.979: OSPF-1 ADJ   Et0/0: Interface going Down
*Sep 18 13:13:31.979: OSPF-1 ADJ   Et0/0: 1.1.1.1 address 10.0.12.1 is dead, state DOWN
*Sep 18 13:13:31.979: %OSPF-5-ADJCHG: Process 1, Nbr 1.1.1.1 on Ethernet0/0 from INIT to DOWN, Neighbor Down: Interface down or detached
*Sep 18 13:13:31.979: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:13:31.979: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:13:31.979: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:13:31.979: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:13:31.979: OSPF-1 ADJ   Et0/0: DR: none 
*Sep 18 13:13:31.979: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:13:31.979: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 10.0.12.2 is dead, state DOWN
*Sep 18 13:13:31.979: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:13:31.979: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:13:31.979: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:13:31.979: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:13:31.979: OSPF-1 ADJ   Et0/0: DR: none 
*Sep 18 13:13:31.979: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:13:31.979: OSPF-1 ADJ   Et0/0: Interface going Up
*Sep 18 13:13:31.979: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:13:40.995: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:13:40.996: OSPF-1 ADJ   Et0/0: 2 Way Communication to 1.1.1.1, state 2WAY
*Sep 18 13:13:41.384: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:13:50.716: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:13:50.892: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:13:59.786: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:14:00.162: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:14:09.512: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:14:10.098: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:14:11.980: OSPF-1 ADJ   Et0/0: end of Wait on interface
*Sep 18 13:14:11.980: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:14:11.980: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:14:11.980: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:14:11.980: OSPF-1 ADJ   Et0/0: DR: none 
*Sep 18 13:14:11.980: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:14:19.231: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:14:19.534: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:14:29.047: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 0 10.0.12.1
*Sep 18 13:14:29.387: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
```

- P3g prio0(両側 priority 0): 復旧 FULL = 0.715749979019165s

- --- P3h stub(両側 area 1・RT02 だけ area 1 stub) ---

**P3h stub(両側 area 1・RT02 だけ area 1 stub) — RT01 show ip ospf neighbor**

```

Neighbor ID     Pri   State           Dead Time   Address         Interface
2.2.2.2           1   FULL/DR         00:00:31    10.0.12.2       Ethernet0/0
```

**P3h stub(両側 area 1・RT02 だけ area 1 stub) — RT02 show ip ospf neighbor**

```

Neighbor ID     Pri   State           Dead Time   Address         Interface
1.1.1.1           1   FULL/BDR        00:00:31    10.0.12.1       Ethernet0/0
```

**P3h stub(両側 area 1・RT02 だけ area 1 stub) [RT01] — RT01 show logging**

```
*Sep 18 13:14:40.650: OSPF-1 EVENT: Config: no network 10.0.12.0 255.255.255.0 area 0
*Sep 18 13:14:40.650: OSPF-1 ADJ   Et0/0: Interface going Down
*Sep 18 13:14:40.650: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 10.0.12.2 is dead, state DOWN
*Sep 18 13:14:40.650: %OSPF-5-ADJCHG: Process 1, Nbr 2.2.2.2 on Ethernet0/0 from FULL to DOWN, Neighbor Down: Interface down or detached
*Sep 18 13:14:40.650: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Clean-up dbase exchange
*Sep 18 13:14:40.650: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:14:40.650: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:14:40.650: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:14:40.650: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:14:40.650: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:14:40.650: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:14:40.650: OSPF-1 ADJ   Et0/0: 1.1.1.1 address 10.0.12.1 is dead, state DOWN
*Sep 18 13:14:40.650: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:14:40.650: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:14:40.650: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:14:40.650: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:14:40.650: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:14:40.650: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:14:40.650: OSPF-1 ADJ   Et0/0: DR: none 
*Sep 18 13:14:40.650: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:14:40.650: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 0 AllRTR 0 AllDR 1
*Sep 18 13:14:40.650: OSPF-1 ADJ   Et0/0: Flush network LSA immediately
*Sep 18 13:14:40.650: OSPF-1 ADJ   Et0/0: Remember old DR 1.1.1.1 (id)
*Sep 18 13:14:40.650: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 0 AllRTR 1 AllDR 1
*Sep 18 13:14:40.750: OSPF-1 EVENT: Config: network 10.0.12.0 255.255.255.0 area 1
*Sep 18 13:14:40.750: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 1 AllRTR 1 AllDR 0
*Sep 18 13:14:40.750: OSPF-1 ADJ   Et0/0: Interface going Up
*Sep 18 13:14:40.750: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 10.0.12.1
*Sep 18 13:14:41.235: %OSPF-4-ERRRCV: Received invalid packet: mismatched area ID from backbone area from 10.0.12.2, Ethernet0/0
*Sep 18 13:14:41.616: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 1 10.0.12.2
*Sep 18 13:14:41.617: OSPF-1 HELLO Et0/0: Send immediate hello to nbr 2.2.2.2, src address 10.0.12.2
*Sep 18 13:14:41.617: OSPF-1 HELLO Et0/0: Send hello to 10.0.12.2 area 1 from 10.0.12.1
*Sep 18 13:14:41.617: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 1 10.0.12.2
*Sep 18 13:14:41.617: OSPF-1 ADJ   Et0/0: 2 Way Communication to 2.2.2.2, state 2WAY
*Sep 18 13:14:50.027: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 10.0.12.1
*Sep 18 13:14:50.756: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 1 10.0.12.2
*Sep 18 13:14:50.756: OSPF-1 HELLO Et0/0: Hello from 10.0.12.2 with mismatched Stub/Transit area option bit
*Sep 18 13:14:59.441: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 10.0.12.1
*Sep 18 13:15:00.231: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 1 10.0.12.2
*Sep 18 13:15:00.231: OSPF-1 HELLO Et0/0: Hello from 10.0.12.2 with mismatched Stub/Transit area option bit
*Sep 18 13:15:09.320: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 10.0.12.1
*Sep 18 13:15:09.487: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 1 10.0.12.2
*Sep 18 13:15:09.487: OSPF-1 HELLO Et0/0: Hello from 10.0.12.2 with mismatched Stub/Transit area option bit
*Sep 18 13:15:18.519: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 1 10.0.12.2
*Sep 18 13:15:18.519: OSPF-1 HELLO Et0/0: Hello from 10.0.12.2 with mismatched Stub/Transit area option bit
*Sep 18 13:15:19.320: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 10.0.12.1
*Sep 18 13:15:20.751: OSPF-1 ADJ   Et0/0: end of Wait on interface
*Sep 18 13:15:20.751: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:15:20.751: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:15:20.751: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:15:20.751: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:15:20.751: OSPF-1 ADJ   Et0/0:    BDR: 2.2.2.2 (Id)
*Sep 18 13:15:20.751: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Prepare dbase exchange
*Sep 18 13:15:20.751: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x919 opt 0x52 flag 0x7 len 32
*Sep 18 13:15:21.606: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x257B opt 0x50 flag 0x7 len 32  mtu 1500 state EXSTART
*Sep 18 13:15:21.606: OSPF-1 ADJ   Et0/0: NBR Negotiation Done. We are the SLAVE
*Sep 18 13:15:21.606: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Summary list built, size 1
*Sep 18 13:15:21.606: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x257B opt 0x52 flag 0x2 len 52
*Sep 18 13:15:21.607: OSPF-1 ADJ   Et0/0: Rcv DBD from 2.2.2.2 seq 0x257C opt 0x50 flag 0x1 len 52  mtu 1500 state EXCHANGE
*Sep 18 13:15:21.607: OSPF-1 ADJ   Et0/0: Exchange Done with 2.2.2.2
*Sep 18 13:15:21.607: OSPF-1 ADJ   Et0/0: Send LS REQ to 2.2.2.2 length 36
*Sep 18 13:15:21.607: OSPF-1 ADJ   Et0/0: Send DBD to 2.2.2.2 seq 0x257C opt 0x52 flag 0x0 len 32
*Sep 18 13:15:21.607: OSPF-1 ADJ   Et0/0: Rcv LS UPD from Nbr ID 2.2.2.2 length 64 LSA count 1
*Sep 18 13:15:21.607: OSPF-1 ADJ   Et0/0: Synchronized with 2.2.2.2, state FULL
*Sep 18 13:15:21.607: %OSPF-5-ADJCHG: Process 1, Nbr 2.2.2.2 on Ethernet0/0 from LOADING to FULL, Loading Done
*Sep 18 13:15:21.607: OSPF-1 ADJ   Et0/0: Rcv LS REQ from 2.2.2.2 length 36 LSA count 1
*Sep 18 13:15:28.177: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 1 10.0.12.2
*Sep 18 13:15:28.177: OSPF-1 HELLO Et0/0: Hello from 10.0.12.2 with mismatched Stub/Transit area option bit
*Sep 18 13:15:28.452: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 10.0.12.1
```

**P3h stub(両側 area 1・RT02 だけ area 1 stub) [RT02] — RT02 show logging**

```
*Sep 18 13:14:40.751: OSPF-1 ADJ   Et0/0: Rcv pkt from 10.0.12.1, area 0.0.0.0, mismatched area 0.0.0.1 in the header
*Sep 18 13:14:41.504: OSPF-1 EVENT: Config: no network 10.0.12.0 255.255.255.0 area 0
*Sep 18 13:14:41.504: OSPF-1 ADJ   Et0/0: Interface going Down
*Sep 18 13:14:41.504: OSPF-1 ADJ   Et0/0: 1.1.1.1 address 10.0.12.1 is dead, state DOWN
*Sep 18 13:14:41.504: %OSPF-5-ADJCHG: Process 1, Nbr 1.1.1.1 on Ethernet0/0 from FULL to DOWN, Neighbor Down: Interface down or detached
*Sep 18 13:14:41.504: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Clean-up dbase exchange
*Sep 18 13:14:41.504: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:14:41.504: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:14:41.504: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:14:41.504: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:14:41.504: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:14:41.504: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:14:41.504: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:14:41.504: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:14:41.504: OSPF-1 ADJ   Et0/0: Remember old DR 1.1.1.1 (id)
*Sep 18 13:14:41.504: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 10.0.12.2 is dead, state DOWN
*Sep 18 13:14:41.504: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:14:41.504: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:14:41.504: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:14:41.504: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:14:41.504: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:14:41.504: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:14:41.504: OSPF-1 ADJ   Et0/0: DR: none 
*Sep 18 13:14:41.504: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:14:41.504: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 0 AllRTR 0 AllDR 1
*Sep 18 13:14:41.504: OSPF-1 ADJ   Et0/0: Flush network LSA immediately
*Sep 18 13:14:41.504: OSPF-1 ADJ   Et0/0: Remember old DR 2.2.2.2 (id)
*Sep 18 13:14:41.504: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 0 AllRTR 1 AllDR 1
*Sep 18 13:14:41.605: OSPF-1 EVENT: Config: network 10.0.12.0 255.255.255.0 area 1
*Sep 18 13:14:41.605: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 1 AllRTR 1 AllDR 0
*Sep 18 13:14:41.605: OSPF-1 ADJ   Et0/0: Interface going Up
*Sep 18 13:14:41.605: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 10.0.12.2
*Sep 18 13:14:41.617: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 1 10.0.12.1
*Sep 18 13:14:41.617: OSPF-1 ADJ   Et0/0: 2 Way Communication to 1.1.1.1, state 2WAY
*Sep 18 13:14:41.617: OSPF-1 HELLO Et0/0: Send immediate hello to nbr 1.1.1.1, src address 10.0.12.1
*Sep 18 13:14:41.617: OSPF-1 HELLO Et0/0: Send hello to 10.0.12.1 area 1 from 10.0.12.2
*Sep 18 13:14:41.706: OSPF-1 EVENT: Area config: 'area 1 stub'
*Sep 18 13:14:50.027: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 1 10.0.12.1
*Sep 18 13:14:50.027: OSPF-1 HELLO Et0/0: Hello from 10.0.12.1 with mismatched Stub/Transit area option bit
*Sep 18 13:14:50.755: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 10.0.12.2
*Sep 18 13:14:59.441: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 1 10.0.12.1
*Sep 18 13:14:59.441: OSPF-1 HELLO Et0/0: Hello from 10.0.12.1 with mismatched Stub/Transit area option bit
*Sep 18 13:15:00.230: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 10.0.12.2
*Sep 18 13:15:09.320: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 1 10.0.12.1
*Sep 18 13:15:09.320: OSPF-1 HELLO Et0/0: Hello from 10.0.12.1 with mismatched Stub/Transit area option bit
*Sep 18 13:15:09.471: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 10.0.12.2
*Sep 18 13:15:18.504: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 10.0.12.2
*Sep 18 13:15:19.321: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 1 10.0.12.1
*Sep 18 13:15:19.321: OSPF-1 HELLO Et0/0: Hello from 10.0.12.1 with mismatched Stub/Transit area option bit
*Sep 18 13:15:20.752: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x919 opt 0x52 flag 0x7 len 32  mtu 1500 state 2WAY
*Sep 18 13:15:20.752: OSPF-1 ADJ   Et0/0: Nbr state is 2WAY
*Sep 18 13:15:21.605: OSPF-1 ADJ   Et0/0: end of Wait on interface
*Sep 18 13:15:21.605: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:15:21.605: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:15:21.605: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:15:21.605: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:15:21.605: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:15:21.605: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:15:21.605: OSPF-1 ADJ   Et0/0:    BDR: 1.1.1.1 (Id)
*Sep 18 13:15:21.605: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 1 AllRTR 0 AllDR 1
*Sep 18 13:15:21.605: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Prepare dbase exchange
*Sep 18 13:15:21.605: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x257B opt 0x50 flag 0x7 len 32
*Sep 18 13:15:21.606: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x257B opt 0x52 flag 0x2 len 52  mtu 1500 state EXSTART
*Sep 18 13:15:21.606: OSPF-1 ADJ   Et0/0: NBR Negotiation Done. We are the MASTER
*Sep 18 13:15:21.606: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Summary list built, size 1
*Sep 18 13:15:21.606: OSPF-1 ADJ   Et0/0: Send DBD to 1.1.1.1 seq 0x257C opt 0x50 flag 0x1 len 52
*Sep 18 13:15:21.607: OSPF-1 ADJ   Et0/0: Rcv LS REQ from 1.1.1.1 length 36 LSA count 1
*Sep 18 13:15:21.607: OSPF-1 ADJ   Et0/0: Send LS UPD to 10.0.12.1 length 64 LSA count 1
*Sep 18 13:15:21.607: OSPF-1 ADJ   Et0/0: Rcv DBD from 1.1.1.1 seq 0x257C opt 0x52 flag 0x0 len 32  mtu 1500 state EXCHANGE
*Sep 18 13:15:21.607: OSPF-1 ADJ   Et0/0: Exchange Done with 1.1.1.1
*Sep 18 13:15:21.607: OSPF-1 ADJ   Et0/0: Send LS REQ to 1.1.1.1 length 36
*Sep 18 13:15:21.607: OSPF-1 ADJ   Et0/0: Rcv LS UPD from Nbr ID 1.1.1.1 length 64 LSA count 1
*Sep 18 13:15:21.607: OSPF-1 ADJ   Et0/0: Synchronized with 1.1.1.1, state FULL
*Sep 18 13:15:21.607: %OSPF-5-ADJCHG: Process 1, Nbr 1.1.1.1 on Ethernet0/0 from LOADING to FULL, Loading Done
*Sep 18 13:15:28.176: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 10.0.12.2
*Sep 18 13:15:28.453: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 1 10.0.12.1
*Sep 18 13:15:28.453: OSPF-1 HELLO Et0/0: Hello from 10.0.12.1 with mismatched Stub/Transit area option bit
```

- P3h stub(両側 area 1・RT02 だけ area 1 stub): 復旧 FULL = 43.591980934143066s

- --- P3i passive(RT02 passive-interface Ethernet0/0) ---

**P3i passive(RT02 passive-interface Ethernet0/0) — RT01 show ip ospf neighbor**

```

```

**P3i passive(RT02 passive-interface Ethernet0/0) — RT02 show ip ospf neighbor**

```

```

**P3i passive(RT02 passive-interface Ethernet0/0) [RT01] — RT01 show logging**

```
*Sep 18 13:16:24.294: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:16:34.020: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:16:43.749: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:16:53.348: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:16:56.841: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Clean-up dbase exchange
*Sep 18 13:16:59.350: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 10.0.12.2 is dead
*Sep 18 13:16:59.350: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 10.0.12.2 is dead, state DOWN
*Sep 18 13:16:59.350: %OSPF-5-ADJCHG: Process 1, Nbr 2.2.2.2 on Ethernet0/0 from FULL to DOWN, Neighbor Down: Dead timer expired
*Sep 18 13:16:59.350: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:16:59.350: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:16:59.350: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:16:59.350: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:16:59.350: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:16:59.350: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:16:59.350: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:16:59.350: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:16:59.350: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 1 AllRTR 0 AllDR 1
*Sep 18 13:16:59.350: OSPF-1 ADJ   Et0/0: Remember old DR 2.2.2.2 (id)
*Sep 18 13:17:02.461: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:17:11.997: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:17:21.687: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
```

**P3i passive(RT02 passive-interface Ethernet0/0) [RT02] — RT02 show logging**

```
*Sep 18 13:16:24.294: OSPF-1 ADJ   Et0/0: Interface going Down
*Sep 18 13:16:24.294: OSPF-1 ADJ   Et0/0: 1.1.1.1 address 10.0.12.1 is dead, state DOWN
*Sep 18 13:16:24.294: %OSPF-5-ADJCHG: Process 1, Nbr 1.1.1.1 on Ethernet0/0 from FULL to DOWN, Neighbor Down: Interface down or detached
*Sep 18 13:16:24.294: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Clean-up dbase exchange
*Sep 18 13:16:24.294: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:16:24.294: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:16:24.294: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:16:24.294: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:16:24.294: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:16:24.294: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:16:24.294: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 10.0.12.2 is dead, state DOWN
*Sep 18 13:16:24.294: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:16:24.294: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:16:24.294: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:16:24.294: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:16:24.294: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:16:24.294: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:16:24.294: OSPF-1 ADJ   Et0/0: DR: none 
*Sep 18 13:16:24.294: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:16:24.294: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 0 AllRTR 0 AllDR 1
*Sep 18 13:16:24.294: OSPF-1 ADJ   Et0/0: Flush network LSA immediately
*Sep 18 13:16:24.295: OSPF-1 ADJ   Et0/0: Remember old DR 2.2.2.2 (id)
*Sep 18 13:16:24.295: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 0 AllRTR 1 AllDR 1
*Sep 18 13:16:24.295: OSPF-1 EVENT: Config: network 10.0.12.0 255.255.255.0 area 0 range idb Ethernet0/0
*Sep 18 13:16:24.295: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 1 AllRTR 1 AllDR 0
*Sep 18 13:16:24.295: OSPF-1 ADJ   Et0/0: Interface going Up
*Sep 18 13:17:04.295: OSPF-1 ADJ   Et0/0: end of Wait on interface
*Sep 18 13:17:04.295: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:17:04.295: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:17:04.295: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:17:04.295: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:17:04.295: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:17:04.295: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:17:04.295: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:17:04.295: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 1 AllRTR 0 AllDR 1
```

- P3i passive(RT02 passive-interface Ethernet0/0): 復旧 FULL = 0.593930721282959s

- --- P3j dup_rid(RT02 router-id 1.1.1.1) ---

**P3j dup_rid(RT02 router-id 1.1.1.1) — RT01 show ip ospf neighbor**

```

```

**P3j dup_rid(RT02 router-id 1.1.1.1) — RT02 show ip ospf neighbor**

```

```

**P3j dup_rid(RT02 router-id 1.1.1.1) [RT01] — RT01 show logging**

```
*Sep 18 13:17:27.981: %OSPF-5-ADJCHG: Process 1, Nbr 2.2.2.2 on Ethernet0/0 from LOADING to FULL, Loading Done
*Sep 18 13:17:31.802: %OSPF-4-DUP_RTRID_NBR: OSPF detected duplicate router-id 1.1.1.1 from 10.0.12.2 on interface Ethernet0/0
*Sep 18 13:17:32.265: OSPF-1 ADJ   Et0/0: Interface going Down
*Sep 18 13:17:32.265: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 10.0.12.2 is dead, state DOWN
*Sep 18 13:17:32.265: %OSPF-5-ADJCHG: Process 1, Nbr 2.2.2.2 on Ethernet0/0 from FULL to DOWN, Neighbor Down: Interface down or detached
*Sep 18 13:17:32.265: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Clean-up dbase exchange
*Sep 18 13:17:32.265: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:17:32.265: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:17:32.265: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:17:32.265: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:17:32.265: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:17:32.265: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:17:32.265: OSPF-1 ADJ   Et0/0: 1.1.1.1 address 10.0.12.1 is dead, state DOWN
*Sep 18 13:17:32.265: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:17:32.265: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:17:32.265: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:17:32.265: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:17:32.265: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:17:32.265: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:17:32.265: OSPF-1 ADJ   Et0/0: DR: none 
*Sep 18 13:17:32.265: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:17:32.265: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 0 AllRTR 0 AllDR 1
*Sep 18 13:17:32.265: OSPF-1 ADJ   Et0/0: Flush network LSA immediately
*Sep 18 13:17:32.265: OSPF-1 ADJ   Et0/0: Remember old DR 1.1.1.1 (id)
*Sep 18 13:17:32.265: OSPF-1 ADJ   Et0/0: Interface going Up
*Sep 18 13:17:32.265: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:17:41.986: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:17:51.323: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:18:01.303: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:18:11.208: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:18:12.266: OSPF-1 ADJ   Et0/0: end of Wait on interface
*Sep 18 13:18:12.266: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:18:12.266: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:18:12.266: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:18:12.266: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:18:12.266: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:18:12.266: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:18:12.266: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:18:12.266: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 1 AllRTR 0 AllDR 1
*Sep 18 13:18:20.565: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:18:29.906: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
```

**P3j dup_rid(RT02 router-id 1.1.1.1) [RT02] — RT02 show logging**

```
*Sep 18 13:17:31.701: OSPF-1 EVENT: Config: router-id 1.1.1.1
*Sep 18 13:17:31.701: %OSPF-6-NEW_RTRID: New router-id will take effect immediately. If OSPF adjacencies are UP for OSPF-1 they will be reset.
*Sep 18 13:17:31.801: OSPF-1 ADJ   Et0/0: Interface going Down
*Sep 18 13:17:31.801: OSPF-1 ADJ   Et0/0: 1.1.1.1 address 10.0.12.1 is dead, state DOWN
*Sep 18 13:17:31.801: %OSPF-5-ADJCHG: Process 1, Nbr 1.1.1.1 on Ethernet0/0 from FULL to DOWN, Neighbor Down: Interface down or detached
*Sep 18 13:17:31.801: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Clean-up dbase exchange
*Sep 18 13:17:31.801: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:17:31.801: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:17:31.801: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:17:31.801: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:17:31.801: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:17:31.801: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:17:31.801: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:17:31.801: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:17:31.801: OSPF-1 ADJ   Et0/0: Remember old DR 1.1.1.1 (id)
*Sep 18 13:17:31.801: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 10.0.12.2 is dead, state DOWN
*Sep 18 13:17:31.801: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:17:31.801: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:17:31.801: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:17:31.801: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:17:31.801: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:17:31.801: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:17:31.801: OSPF-1 ADJ   Et0/0: DR: none 
*Sep 18 13:17:31.801: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:17:31.801: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 0 AllRTR 0 AllDR 1
*Sep 18 13:17:31.801: OSPF-1 ADJ   Et0/0: Flush network LSA immediately
*Sep 18 13:17:31.801: OSPF-1 ADJ   Et0/0: Remember old DR 2.2.2.2 (id)
*Sep 18 13:17:31.801: OSPF-1 ADJ   Et0/0: Interface going Up
*Sep 18 13:17:31.801: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:17:32.233: %OSPF-4-DUP_RTRID_NBR: OSPF detected duplicate router-id 1.1.1.1 from 10.0.12.1 on interface Ethernet0/0
*Sep 18 13:17:32.807: OSPF-1 ADJ   Et0/0: Interface going Down
*Sep 18 13:17:32.807: OSPF-1 ADJ   Et0/0: 1.1.1.1 address 10.0.12.2 is dead, state DOWN
*Sep 18 13:17:32.807: OSPF-1 ADJ   Et0/0: Interface going Up
*Sep 18 13:17:32.807: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:17:42.173: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:17:51.509: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:18:01.090: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:18:11.007: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:18:12.808: OSPF-1 ADJ   Et0/0: end of Wait on interface
*Sep 18 13:18:12.808: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:18:12.808: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:18:12.808: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:18:12.808: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:18:12.808: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:18:12.808: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:18:12.808: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:18:12.808: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 1 AllRTR 0 AllDR 1
*Sep 18 13:18:20.322: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:18:29.604: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
```

- P3j dup_rid(RT02 router-id 1.1.1.1): 復旧 FULL = 0.7039632797241211s

- --- P3k unidir(RT02 inbound ACL で OSPF(89) を拒否) ---

**P3k unidir(RT02 inbound ACL で OSPF(89) を拒否) — RT01 show ip ospf neighbor**

```

Neighbor ID     Pri   State           Dead Time   Address         Interface
2.2.2.2           1   INIT/DROTHER    00:00:37    10.0.12.2       Ethernet0/0
```

**P3k unidir(RT02 inbound ACL で OSPF(89) を拒否) — RT02 show ip ospf neighbor**

```

```

**P3k unidir(RT02 inbound ACL で OSPF(89) を拒否) [RT01] — RT01 show logging**

```
*Sep 18 13:18:41.417: OSPF-1 ADJ   Et0/0: Interface going Down
*Sep 18 13:18:41.417: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 10.0.12.2 is dead, state DOWN
*Sep 18 13:18:41.417: %OSPF-5-ADJCHG: Process 1, Nbr 2.2.2.2 on Ethernet0/0 from FULL to DOWN, Neighbor Down: Interface down or detached
*Sep 18 13:18:41.417: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Clean-up dbase exchange
*Sep 18 13:18:41.417: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:18:41.417: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:18:41.417: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:18:41.417: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:18:41.417: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:18:41.417: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:18:41.417: OSPF-1 ADJ   Et0/0: 1.1.1.1 address 10.0.12.1 is dead, state DOWN
*Sep 18 13:18:41.417: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:18:41.417: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:18:41.417: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:18:41.417: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:18:41.417: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:18:41.417: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:18:41.417: OSPF-1 ADJ   Et0/0: DR: none 
*Sep 18 13:18:41.417: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:18:41.417: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 0 AllRTR 0 AllDR 1
*Sep 18 13:18:41.417: OSPF-1 ADJ   Et0/0: Flush network LSA immediately
*Sep 18 13:18:41.417: OSPF-1 ADJ   Et0/0: Remember old DR 1.1.1.1 (id)
*Sep 18 13:18:41.417: OSPF-1 ADJ   Et0/0: Interface going Up
*Sep 18 13:18:41.417: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:18:41.844: OSPF-1 ADJ   Et0/0: Rcv pkt  src 10.0.12.2 dst 224.0.0.5 id 2.2.2.2 type 4 if_state 2 : ignored due to unknown neighbor
*Sep 18 13:18:41.874: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:18:41.875: OSPF-1 HELLO Et0/0: Send immediate hello to nbr 2.2.2.2, src address 10.0.12.2
*Sep 18 13:18:41.875: OSPF-1 HELLO Et0/0: Send hello to 10.0.12.2 area 0 from 10.0.12.1
*Sep 18 13:18:50.576: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:18:51.872: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:18:51.872: OSPF-1 HELLO Et0/0: Send immediate hello to nbr 2.2.2.2, src address 10.0.12.2
*Sep 18 13:18:51.872: OSPF-1 HELLO Et0/0: Send hello to 10.0.12.2 area 0 from 10.0.12.1
*Sep 18 13:19:00.480: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:19:01.280: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:19:01.280: OSPF-1 HELLO Et0/0: No more immediate hello for nbr 2.2.2.2, which has been sent on this intf 2 times
*Sep 18 13:19:10.190: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:19:10.718: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:19:10.718: OSPF-1 HELLO Et0/0: No more immediate hello for nbr 2.2.2.2, which has been sent on this intf 2 times
*Sep 18 13:19:19.904: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:19:19.904: OSPF-1 HELLO Et0/0: No more immediate hello for nbr 2.2.2.2, which has been sent on this intf 2 times
*Sep 18 13:19:20.051: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:19:21.417: OSPF-1 ADJ   Et0/0: end of Wait on interface
*Sep 18 13:19:21.417: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:19:21.417: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 13:19:21.417: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:19:21.417: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:19:21.417: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 13:19:21.417: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 13:19:21.417: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:19:21.417: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 1 AllRTR 0 AllDR 1
*Sep 18 13:19:29.536: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:19:29.536: OSPF-1 HELLO Et0/0: No more immediate hello for nbr 2.2.2.2, which has been sent on this intf 2 times
*Sep 18 13:19:29.602: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
*Sep 18 13:19:39.129: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 0 10.0.12.2
*Sep 18 13:19:39.129: OSPF-1 HELLO Et0/0: No more immediate hello for nbr 2.2.2.2, which has been sent on this intf 2 times
*Sep 18 13:19:39.566: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.1
```

**P3k unidir(RT02 inbound ACL で OSPF(89) を拒否) [RT02] — RT02 show logging**

```
*Sep 18 13:18:41.874: OSPF-1 ADJ   Et0/0: Interface going Down
*Sep 18 13:18:41.874: OSPF-1 ADJ   Et0/0: 1.1.1.1 address 10.0.12.1 is dead, state DOWN
*Sep 18 13:18:41.874: %OSPF-5-ADJCHG: Process 1, Nbr 1.1.1.1 on Ethernet0/0 from FULL to DOWN, Neighbor Down: Interface down or detached
*Sep 18 13:18:41.874: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Clean-up dbase exchange
*Sep 18 13:18:41.874: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:18:41.874: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:18:41.874: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:18:41.874: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:18:41.874: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:18:41.874: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:18:41.874: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:18:41.874: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:18:41.874: OSPF-1 ADJ   Et0/0: Remember old DR 1.1.1.1 (id)
*Sep 18 13:18:41.874: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 10.0.12.2 is dead, state DOWN
*Sep 18 13:18:41.874: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 13:18:41.874: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:18:41.874: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:18:41.874: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:18:41.874: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:18:41.874: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 13:18:41.874: OSPF-1 ADJ   Et0/0: DR: none 
*Sep 18 13:18:41.874: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:18:41.874: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 0 AllRTR 0 AllDR 1
*Sep 18 13:18:41.874: OSPF-1 ADJ   Et0/0: Flush network LSA immediately
*Sep 18 13:18:41.874: OSPF-1 ADJ   Et0/0: Remember old DR 2.2.2.2 (id)
*Sep 18 13:18:41.874: OSPF-1 ADJ   Et0/0: Interface going Up
*Sep 18 13:18:41.874: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:18:51.872: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:19:01.280: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:19:10.717: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:19:19.894: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:19:21.875: OSPF-1 ADJ   Et0/0: end of Wait on interface
*Sep 18 13:19:21.875: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 13:19:21.875: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 13:19:21.875: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:19:21.875: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 13:19:21.875: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 13:19:21.875: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 13:19:21.875: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 13:19:21.875: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 1 AllRTR 0 AllDR 1
*Sep 18 13:19:29.536: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
*Sep 18 13:19:39.128: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 0 from 10.0.12.2
```

- P3k unidir(RT02 inbound ACL で OSPF(89) を拒否): 復旧 FULL = 0.6045544147491455s

## P4 BFD ネゴ  (2026-09-18 13:21)

**P4a BFD 非対称(RT03 tx100/rx100/m3・RT04 tx300/rx200/m5) Up=41.507550954818726s**

```

IPv4 Sessions
NeighAddr                              LD/RD         RH/RS     State     Int
10.0.34.4                               1/1          Up        Up        Et0/0
```

**P4a — RT03 show bfd neighbors details**

```

IPv4 Sessions
NeighAddr                              LD/RD         RH/RS     State     Int
10.0.34.4                               1/1          Up        Up        Et0/0
Session state is UP and using echo function with 200 ms interval.
Session Host: Software
OurAddr: 10.0.34.3      
Handle: 1
Local Diag: 0, Demand mode: 0, Poll bit: 0
MinTxInt: 1000000, MinRxInt: 1000000, Multiplier: 3
Received MinRxInt: 1000000, Received Multiplier: 5
Holddown (hits): 0(0), Hello (hits): 1000(2)
Rx Count: 4, Rx Interval (ms) min/max/avg: 1/805/310 last: 627 ms ago
Tx Count: 4, Tx Interval (ms) min/max/avg: 1/787/263 last: 771 ms ago
Echo Rx Count: 8, Echo Rx Interval (ms) min/max/avg: 154/210/169 last: 188 ms ago
Echo Tx Count: 8, Echo Tx Interval (ms) min/max/avg: 156/198/169 last: 190 ms ago
Elapsed time watermarks: 0 0 (last: 0)
Registered protocols: OSPF CEF 
Uptime: 00:00:01
Last packet: Version: 1                  - Diagnostic: 0
             State bit: Up               - Demand bit: 0
             Poll bit: 0                 - Final bit: 0
             C bit: 0                                   
             Multiplier: 5               - Length: 24
             My Discr.: 1                - Your Discr.: 1
             Min tx interval: 1000000    - Min rx interval: 1000000
             Min Echo interval: 200000
```

**P4a — RT04 show bfd neighbors details**

```

IPv4 Sessions
NeighAddr                              LD/RD         RH/RS     State     Int
10.0.34.3                               1/1          Up        Up        Et0/0
Session state is UP and using echo function with 300 ms interval.
Session Host: Software
OurAddr: 10.0.34.4      
Handle: 1
Local Diag: 0, Demand mode: 0, Poll bit: 0
MinTxInt: 1000000, MinRxInt: 1000000, Multiplier: 5
Received MinRxInt: 1000000, Received Multiplier: 3
Holddown (hits): 0(0), Hello (hits): 1000(3)
Rx Count: 5, Rx Interval (ms) min/max/avg: 1/932/430 last: 277 ms ago
Tx Count: 5, Tx Interval (ms) min/max/avg: 1/807/431 last: 271 ms ago
Echo Rx Count: 7, Echo Rx Interval (ms) min/max/avg: 243/300/269 last: 90 ms ago
Echo Tx Count: 7, Echo Tx Interval (ms) min/max/avg: 244/300/269 last: 90 ms ago
Elapsed time watermarks: 0 0 (last: 0)
Registered protocols: OSPF CEF 
Uptime: 00:00:01
Last packet: Version: 1                  - Diagnostic: 0
             State bit: Up               - Demand bit: 0
             Poll bit: 0                 - Final bit: 0
             C bit: 0                                   
             Multiplier: 3               - Length: 24
             My Discr.: 1                - Your Discr.: 1
             Min tx interval: 1000000    - Min rx interval: 1000000
             Min Echo interval: 100000
```

**P4a — RT03 show ip ospf interface Ethernet0/0 | include BFD|Hello**

```
  Transmit Delay is 1 sec, State DROTHER, Priority 1, BFD enabled
  Timer intervals configured, Hello 10, Dead 40, Wait 40, Retransmit 5
    Hello due in 00:00:03
```

**P4b template(RT03 min-tx50/min-rx50/m4 template・RT04 据置) — RT03 details**

```

IPv4 Sessions
NeighAddr                              LD/RD         RH/RS     State     Int
10.0.34.4                               1/1          Up        Up        Et0/0
Session state is UP and not using echo function.
Session Host: Software
OurAddr: 10.0.34.3      
Handle: 1
Local Diag: 0, Demand mode: 0, Poll bit: 0
MinTxInt: 50000, MinRxInt: 50000, Multiplier: 4
Received MinRxInt: 200000, Received Multiplier: 5
Holddown (hits): 1320(0), Hello (hits): 200(146)
Rx Count: 99, Rx Interval (ms) min/max/avg: 1/342/256 last: 180 ms ago
Tx Count: 145, Tx Interval (ms) min/max/avg: 1/203/175 last: 70 ms ago
Elapsed time watermarks: 0 0 (last: 0)
Registered protocols: OSPF CEF 
Template: T-POC
Uptime: 00:00:25
Last packet: Version: 1                  - Diagnostic: 0
             State bit: Up               - Demand bit: 0
             Poll bit: 0                 - Final bit: 0
             C bit: 0                                   
             Multiplier: 5               - Length: 24
             My Discr.: 1                - Your Discr.: 1
             Min tx interval: 300000     - Min rx interval: 200000
             Min Echo interval: 200000
```

**P4b — RT04 details**

```

IPv4 Sessions
NeighAddr                              LD/RD         RH/RS     State     Int
10.0.34.3                               1/1          Up        Up        Et0/0
Session state is UP and not using echo function.
Session Host: Software
OurAddr: 10.0.34.4      
Handle: 1
Local Diag: 0, Demand mode: 0, Poll bit: 0
MinTxInt: 300000, MinRxInt: 200000, Multiplier: 5
Received MinRxInt: 50000, Received Multiplier: 4
Holddown (hits): 730(0), Hello (hits): 300(101)
Rx Count: 146, Rx Interval (ms) min/max/avg: 1/205/176 last: 70 ms ago
Tx Count: 100, Tx Interval (ms) min/max/avg: 1/304/258 last: 38 ms ago
Elapsed time watermarks: 0 0 (last: 0)
Registered protocols: OSPF CEF 
Uptime: 00:00:25
Last packet: Version: 1                  - Diagnostic: 0
             State bit: Up               - Demand bit: 0
             Poll bit: 0                 - Final bit: 0
             C bit: 0                                   
             Multiplier: 4               - Length: 24
             My Discr.: 1                - Your Discr.: 1
             Min tx interval: 50000      - Min rx interval: 50000
             Min Echo interval: 0
```

**P4b — RT03 show bfd summary**

```

                    Session          Up          Down

Total                     1           1             0
```

**P4c no bfd echo(RT03) — RT03 details**

```

IPv4 Sessions
NeighAddr                              LD/RD         RH/RS     State     Int
10.0.34.4                               1/1          Up        Up        Et0/0
Session state is UP and not using echo function.
Session Host: Software
OurAddr: 10.0.34.3      
Handle: 1
Local Diag: 0, Demand mode: 0, Poll bit: 0
MinTxInt: 50000, MinRxInt: 50000, Multiplier: 4
Received MinRxInt: 200000, Received Multiplier: 5
Holddown (hits): 1457(0), Hello (hits): 200(267)
Rx Count: 182, Rx Interval (ms) min/max/avg: 1/342/259 last: 43 ms ago
Tx Count: 266, Tx Interval (ms) min/max/avg: 1/203/177 last: 133 ms ago
Elapsed time watermarks: 0 0 (last: 0)
Registered protocols: OSPF CEF 
Template: T-POC
Uptime: 00:00:47
Last packet: Version: 1                  - Diagnostic: 0
             State bit: Up               - Demand bit: 0
             Poll bit: 0                 - Final bit: 0
             C bit: 0                                   
             Multiplier: 5               - Length: 24
             My Discr.: 1                - Your Discr.: 1
             Min tx interval: 300000     - Min rx interval: 200000
             Min Echo interval: 200000
```

## P5 DHCPv6  (2026-09-18 13:25)

**P5a stateless(O flag + autoconfig) — RT04 show ipv6 interface brief**

```
Ethernet0/0            [up/up]
    FE80::A8BB:CCFF:FE01:5A00
    2001:DB8:34:0:A8BB:CCFF:FE01:5A00
Ethernet0/1            [up/up]
    unassigned
Ethernet0/2            [up/up]
    unassigned
Ethernet0/3            [up/up]
    unassigned
Ethernet1/0            [up/up]
    unassigned
Ethernet1/1            [up/up]
    unassigned
Ethernet1/2            [up/up]
    unassigned
Ethernet1/3            [up/up]
    unassigned
Ethernet2/0            [up/up]
    unassigned
Ethernet2/1            [up/up]
    unassigned
Ethernet2/2            [up/up]
    unassigned
Ethernet2/3            [up/up]
    unassigned
Ethernet3/0            [up/up]
    unassigned
Ethernet3/1            [up/up]
    unassigned
Ethernet3/2            [up/up]
    unassigned
Ethernet3/3            [up/up]
    unassigned
Ethernet4/0            [up/up]
    unassigned
Ethernet4/1            [up/up]
    unassigned
Ethernet4/2            [up/up]
    unassigned
Ethernet4/3            [up/up]
    unassigned
Ethernet5/0            [up/up]
    unassigned
Ethernet5/1            [up/up]
    unassigned
Ethernet5/2            [up/up]
    unassigned
Ethernet5/3            [up/up]
    unassigned
Ethernet6/0            [up/up]
    unassigned
Ethernet6/1            [up/up]
    unassigned
Ethernet6/2            [up/up]
    unassigned
Ethernet6/3            [up/up]
    unassigned
Ethernet7/0            [up/up]
    unassigned
Ethernet7/1            [up/up]
    unassigned
Ethernet7/2            [up/up]
    unassigned
Ethernet7/3            [up/up]
    unassigned
Loopback0              [up/up]
    unassigned
```

**P5a stateless(O flag + autoconfig) — RT04 show ipv6 dhcp interface Ethernet0/0**

```
Ethernet0/0 is in client mode
  Prefix State is INFORMATION-REQUEST (5)
  Information refresh timer expires in 00:00:02
  Address State is IDLE
  Prefix Rapid-Commit: disabled
  Address Rapid-Commit: disabled
```

**P5a stateless(O flag + autoconfig) — RT04 show ipv6 routers**

```
Router FE80::A8BB:CCFF:FE01:5800 on Ethernet0/0, last update 0 min
  Hops 64, Lifetime 1800 sec, AddrFlag=0, OtherFlag=1, MTU=1500
  HomeAgentFlag=0, Preference=Medium
  Reachable time 0 (unspecified), Retransmit time 0 (unspecified)
  Prefix 2001:DB8:34::/64 onlink autoconfig
    Valid lifetime 2592000, preferred lifetime 604800
```

**P5a stateless(O flag + autoconfig) — RT04 show hosts | include Default|Name**

```
Default domain is not set
Name servers are 255.255.255.255
```

**P5a stateless(O flag + autoconfig) — RT03 show ipv6 dhcp binding**

```

```

**P5a stateless(O flag + autoconfig) — RT03 show ipv6 interface Ethernet0/0 | include Hosts|ND|advert|flag|unicast**

```
  Global unicast address(es):
  ND DAD is enabled, number of DAD attempts: 1
  ND reachable time is 30000 milliseconds (using 30000)
  ND advertised reachable time is 0 (unspecified)
  ND advertised retransmit interval is 0 (unspecified)
  ND router advertisements are sent every 200 seconds
  ND router advertisements live for 1800 seconds
  ND advertised default router preference is Medium
  Hosts use stateless autoconfig for addresses.
  Hosts use DHCP to obtain other configuration.
```

**P5c4 O flag だが ipv6 dhcp server 未attach — RT04 show ipv6 interface brief**

```
Ethernet0/0            [up/up]
    FE80::A8BB:CCFF:FE01:5A00
    2001:DB8:34:0:A8BB:CCFF:FE01:5A00
Ethernet0/1            [up/up]
    unassigned
Ethernet0/2            [up/up]
    unassigned
Ethernet0/3            [up/up]
    unassigned
Ethernet1/0            [up/up]
    unassigned
Ethernet1/1            [up/up]
    unassigned
Ethernet1/2            [up/up]
    unassigned
Ethernet1/3            [up/up]
    unassigned
Ethernet2/0            [up/up]
    unassigned
Ethernet2/1            [up/up]
    unassigned
Ethernet2/2            [up/up]
    unassigned
Ethernet2/3            [up/up]
    unassigned
Ethernet3/0            [up/up]
    unassigned
Ethernet3/1            [up/up]
    unassigned
Ethernet3/2            [up/up]
    unassigned
Ethernet3/3            [up/up]
    unassigned
Ethernet4/0            [up/up]
    unassigned
Ethernet4/1            [up/up]
    unassigned
Ethernet4/2            [up/up]
    unassigned
Ethernet4/3            [up/up]
    unassigned
Ethernet5/0            [up/up]
    unassigned
Ethernet5/1            [up/up]
    unassigned
Ethernet5/2            [up/up]
    unassigned
Ethernet5/3            [up/up]
    unassigned
Ethernet6/0            [up/up]
    unassigned
Ethernet6/1            [up/up]
    unassigned
Ethernet6/2            [up/up]
    unassigned
Ethernet6/3            [up/up]
    unassigned
Ethernet7/0            [up/up]
    unassigned
Ethernet7/1            [up/up]
    unassigned
Ethernet7/2            [up/up]
    unassigned
Ethernet7/3            [up/up]
    unassigned
Loopback0              [up/up]
    unassigned
```

**P5c4 O flag だが ipv6 dhcp server 未attach — RT04 show ipv6 dhcp interface Ethernet0/0**

```
Ethernet0/0 is in client mode
  Prefix State is INFORMATION-REQUEST (5)
  Information refresh timer expires in 00:00:10
  Address State is IDLE
  Prefix Rapid-Commit: disabled
  Address Rapid-Commit: disabled
```

**P5c4 O flag だが ipv6 dhcp server 未attach — RT04 show ipv6 routers**

```
Router FE80::A8BB:CCFF:FE01:5800 on Ethernet0/0, last update 0 min
  Hops 64, Lifetime 1800 sec, AddrFlag=0, OtherFlag=1, MTU=1500
  HomeAgentFlag=0, Preference=Medium
  Reachable time 0 (unspecified), Retransmit time 0 (unspecified)
  Prefix 2001:DB8:34::/64 onlink autoconfig
    Valid lifetime 2592000, preferred lifetime 604800
```

**P5c4 O flag だが ipv6 dhcp server 未attach — RT04 show hosts | include Default|Name**

```
Default domain is not set
Name servers are 255.255.255.255
```

**P5c4 O flag だが ipv6 dhcp server 未attach — RT03 show ipv6 dhcp binding**

```

```

**P5c4 O flag だが ipv6 dhcp server 未attach — RT03 show ipv6 interface Ethernet0/0 | include Hosts|ND|advert|flag|unicast**

```
  Global unicast address(es):
  ND DAD is enabled, number of DAD attempts: 1
  ND reachable time is 30000 milliseconds (using 30000)
  ND advertised reachable time is 0 (unspecified)
  ND advertised retransmit interval is 0 (unspecified)
  ND router advertisements are sent every 200 seconds
  ND router advertisements live for 1800 seconds
  ND advertised default router preference is Medium
  Hosts use stateless autoconfig for addresses.
  Hosts use DHCP to obtain other configuration.
```

**P5c1 no ipv6 unicast-routing(RA 送出側) — RT04 show ipv6 interface brief**

```
Ethernet0/0            [up/up]
    FE80::A8BB:CCFF:FE01:5A00
Ethernet0/1            [up/up]
    unassigned
Ethernet0/2            [up/up]
    unassigned
Ethernet0/3            [up/up]
    unassigned
Ethernet1/0            [up/up]
    unassigned
Ethernet1/1            [up/up]
    unassigned
Ethernet1/2            [up/up]
    unassigned
Ethernet1/3            [up/up]
    unassigned
Ethernet2/0            [up/up]
    unassigned
Ethernet2/1            [up/up]
    unassigned
Ethernet2/2            [up/up]
    unassigned
Ethernet2/3            [up/up]
    unassigned
Ethernet3/0            [up/up]
    unassigned
Ethernet3/1            [up/up]
    unassigned
Ethernet3/2            [up/up]
    unassigned
Ethernet3/3            [up/up]
    unassigned
Ethernet4/0            [up/up]
    unassigned
Ethernet4/1            [up/up]
    unassigned
Ethernet4/2            [up/up]
    unassigned
Ethernet4/3            [up/up]
    unassigned
Ethernet5/0            [up/up]
    unassigned
Ethernet5/1            [up/up]
    unassigned
Ethernet5/2            [up/up]
    unassigned
Ethernet5/3            [up/up]
    unassigned
Ethernet6/0            [up/up]
    unassigned
Ethernet6/1            [up/up]
    unassigned
Ethernet6/2            [up/up]
    unassigned
Ethernet6/3            [up/up]
    unassigned
Ethernet7/0            [up/up]
    unassigned
Ethernet7/1            [up/up]
    unassigned
Ethernet7/2            [up/up]
    unassigned
Ethernet7/3            [up/up]
    unassigned
Loopback0              [up/up]
    unassigned
```

**P5c1 no ipv6 unicast-routing(RA 送出側) — RT04 show ipv6 dhcp interface Ethernet0/0**

```
Ethernet0/0 is in client mode
  Prefix State is IDLE (0)
  Information refresh timer expires in 23:59:42
  Address State is IDLE
  List of known servers:
    Reachable via address: FE80::A8BB:CCFF:FE01:5800
    DUID: 00030001AABBCC015800
    Preference: 0
    Configuration parameters:
      DNS server: 2001:4860:4860::8888
      Domain name: example.net
      Information refresh time: 0
  Prefix Rapid-Commit: disabled
  Address Rapid-Commit: disabled
```

**P5c1 no ipv6 unicast-routing(RA 送出側) — RT04 show ipv6 routers**

```

```

**P5c1 no ipv6 unicast-routing(RA 送出側) — RT04 show hosts | include Default|Name**

```
Default domain is not set
Name servers are 2001:4860:4860::8888
```

**P5c1 no ipv6 unicast-routing(RA 送出側) — RT03 show ipv6 dhcp binding**

```

```

**P5c1 no ipv6 unicast-routing(RA 送出側) — RT03 show ipv6 interface Ethernet0/0 | include Hosts|ND|advert|flag|unicast**

```
  Global unicast address(es):
  ND DAD is enabled, number of DAD attempts: 1
  ND reachable time is 30000 milliseconds (using 30000)
  ND NS retransmit interval is 1000 milliseconds
```

**P5c2 ipv6 nd ra suppress all — RT04 show ipv6 interface brief**

```
Ethernet0/0            [up/up]
    FE80::A8BB:CCFF:FE01:5A00
Ethernet0/1            [up/up]
    unassigned
Ethernet0/2            [up/up]
    unassigned
Ethernet0/3            [up/up]
    unassigned
Ethernet1/0            [up/up]
    unassigned
Ethernet1/1            [up/up]
    unassigned
Ethernet1/2            [up/up]
    unassigned
Ethernet1/3            [up/up]
    unassigned
Ethernet2/0            [up/up]
    unassigned
Ethernet2/1            [up/up]
    unassigned
Ethernet2/2            [up/up]
    unassigned
Ethernet2/3            [up/up]
    unassigned
Ethernet3/0            [up/up]
    unassigned
Ethernet3/1            [up/up]
    unassigned
Ethernet3/2            [up/up]
    unassigned
Ethernet3/3            [up/up]
    unassigned
Ethernet4/0            [up/up]
    unassigned
Ethernet4/1            [up/up]
    unassigned
Ethernet4/2            [up/up]
    unassigned
Ethernet4/3            [up/up]
    unassigned
Ethernet5/0            [up/up]
    unassigned
Ethernet5/1            [up/up]
    unassigned
Ethernet5/2            [up/up]
    unassigned
Ethernet5/3            [up/up]
    unassigned
Ethernet6/0            [up/up]
    unassigned
Ethernet6/1            [up/up]
    unassigned
Ethernet6/2            [up/up]
    unassigned
Ethernet6/3            [up/up]
    unassigned
Ethernet7/0            [up/up]
    unassigned
Ethernet7/1            [up/up]
    unassigned
Ethernet7/2            [up/up]
    unassigned
Ethernet7/3            [up/up]
    unassigned
Loopback0              [up/up]
    unassigned
```

**P5c2 ipv6 nd ra suppress all — RT04 show ipv6 dhcp interface Ethernet0/0**

```
Ethernet0/0 is in client mode
  Prefix State is IDLE (0)
  Information refresh timer expires in 23:59:42
  Address State is IDLE
  List of known servers:
    Reachable via address: FE80::A8BB:CCFF:FE01:5800
    DUID: 00030001AABBCC015800
    Preference: 0
    Configuration parameters:
      DNS server: 2001:4860:4860::8888
      Domain name: example.net
      Information refresh time: 0
  Prefix Rapid-Commit: disabled
  Address Rapid-Commit: disabled
```

**P5c2 ipv6 nd ra suppress all — RT04 show ipv6 routers**

```

```

**P5c2 ipv6 nd ra suppress all — RT04 show hosts | include Default|Name**

```
Default domain is not set
Name servers are 2001:4860:4860::8888
```

**P5c2 ipv6 nd ra suppress all — RT03 show ipv6 dhcp binding**

```

```

**P5c2 ipv6 nd ra suppress all — RT03 show ipv6 interface Ethernet0/0 | include Hosts|ND|advert|flag|unicast**

```
  Global unicast address(es):
  ND DAD is enabled, number of DAD attempts: 1
  ND reachable time is 30000 milliseconds (using 30000)
  ND RAs are suppressed (all)
  Hosts use stateless autoconfig for addresses.
  Hosts use DHCP to obtain other configuration.
```

**P5c5 IPv6 ACL(GUA host のみ許可)が LL 送信元の RA を落とす — RT04 show ipv6 interface brief**

```
Ethernet0/0            [up/up]
    FE80::A8BB:CCFF:FE01:5A00
Ethernet0/1            [up/up]
    unassigned
Ethernet0/2            [up/up]
    unassigned
Ethernet0/3            [up/up]
    unassigned
Ethernet1/0            [up/up]
    unassigned
Ethernet1/1            [up/up]
    unassigned
Ethernet1/2            [up/up]
    unassigned
Ethernet1/3            [up/up]
    unassigned
Ethernet2/0            [up/up]
    unassigned
Ethernet2/1            [up/up]
    unassigned
Ethernet2/2            [up/up]
    unassigned
Ethernet2/3            [up/up]
    unassigned
Ethernet3/0            [up/up]
    unassigned
Ethernet3/1            [up/up]
    unassigned
Ethernet3/2            [up/up]
    unassigned
Ethernet3/3            [up/up]
    unassigned
Ethernet4/0            [up/up]
    unassigned
Ethernet4/1            [up/up]
    unassigned
Ethernet4/2            [up/up]
    unassigned
Ethernet4/3            [up/up]
    unassigned
Ethernet5/0            [up/up]
    unassigned
Ethernet5/1            [up/up]
    unassigned
Ethernet5/2            [up/up]
    unassigned
Ethernet5/3            [up/up]
    unassigned
Ethernet6/0            [up/up]
    unassigned
Ethernet6/1            [up/up]
    unassigned
Ethernet6/2            [up/up]
    unassigned
Ethernet6/3            [up/up]
    unassigned
Ethernet7/0            [up/up]
    unassigned
Ethernet7/1            [up/up]
    unassigned
Ethernet7/2            [up/up]
    unassigned
Ethernet7/3            [up/up]
    unassigned
Loopback0              [up/up]
    unassigned
```

**P5c5 IPv6 ACL(GUA host のみ許可)が LL 送信元の RA を落とす — RT04 show ipv6 dhcp interface Ethernet0/0**

```
Ethernet0/0 is in client mode
  Prefix State is IDLE
  Address State is IDLE
  Prefix Rapid-Commit: disabled
  Address Rapid-Commit: disabled
```

**P5c5 IPv6 ACL(GUA host のみ許可)が LL 送信元の RA を落とす — RT04 show ipv6 routers**

```

```

**P5c5 IPv6 ACL(GUA host のみ許可)が LL 送信元の RA を落とす — RT04 show hosts | include Default|Name**

```
Default domain is not set
Name servers are 255.255.255.255
```

**P5c5 IPv6 ACL(GUA host のみ許可)が LL 送信元の RA を落とす — RT03 show ipv6 dhcp binding**

```

```

**P5c5 IPv6 ACL(GUA host のみ許可)が LL 送信元の RA を落とす — RT03 show ipv6 interface Ethernet0/0 | include Hosts|ND|advert|flag|unicast**

```
  Global unicast address(es):
  ND DAD is enabled, number of DAD attempts: 1
  ND reachable time is 30000 milliseconds (using 30000)
  ND advertised reachable time is 0 (unspecified)
  ND advertised retransmit interval is 0 (unspecified)
  ND router advertisements are sent every 200 seconds
  ND router advertisements live for 1800 seconds
  ND advertised default router preference is Medium
  Hosts use stateless autoconfig for addresses.
  Hosts use DHCP to obtain other configuration.
```

**P5c5 — RT04 show ipv6 access-list**

```
IPv6 access list ACL-POC
    permit ipv6 host 2001:DB8:34::3 any sequence 10
```

**P5b stateful(M flag + address prefix + no-autoconfig / client ipv6 address dhcp) — RT04 show ipv6 interface brief**

```
Ethernet0/0            [up/up]
    FE80::A8BB:CCFF:FE01:5A00
    2001:DB8:34:0:1C:580:9531:D6A3
Ethernet0/1            [up/up]
    unassigned
Ethernet0/2            [up/up]
    unassigned
Ethernet0/3            [up/up]
    unassigned
Ethernet1/0            [up/up]
    unassigned
Ethernet1/1            [up/up]
    unassigned
Ethernet1/2            [up/up]
    unassigned
Ethernet1/3            [up/up]
    unassigned
Ethernet2/0            [up/up]
    unassigned
Ethernet2/1            [up/up]
    unassigned
Ethernet2/2            [up/up]
    unassigned
Ethernet2/3            [up/up]
    unassigned
Ethernet3/0            [up/up]
    unassigned
Ethernet3/1            [up/up]
    unassigned
Ethernet3/2            [up/up]
    unassigned
Ethernet3/3            [up/up]
    unassigned
Ethernet4/0            [up/up]
    unassigned
Ethernet4/1            [up/up]
    unassigned
Ethernet4/2            [up/up]
    unassigned
Ethernet4/3            [up/up]
    unassigned
Ethernet5/0            [up/up]
    unassigned
Ethernet5/1            [up/up]
    unassigned
Ethernet5/2            [up/up]
    unassigned
Ethernet5/3            [up/up]
    unassigned
Ethernet6/0            [up/up]
    unassigned
Ethernet6/1            [up/up]
    unassigned
Ethernet6/2            [up/up]
    unassigned
Ethernet6/3            [up/up]
    unassigned
Ethernet7/0            [up/up]
    unassigned
Ethernet7/1            [up/up]
    unassigned
Ethernet7/2            [up/up]
    unassigned
Ethernet7/3            [up/up]
    unassigned
Loopback0              [up/up]
    unassigned
```

**P5b stateful(M flag + address prefix + no-autoconfig / client ipv6 address dhcp) — RT04 show ipv6 dhcp interface Ethernet0/0**

```
Ethernet0/0 is in client mode
  Prefix State is IDLE
  Address State is OPEN
  Renew for address will be sent in 11:59:40
  List of known servers:
    Reachable via address: FE80::A8BB:CCFF:FE01:5800
    DUID: 00030001AABBCC015800
    Preference: 0
    Configuration parameters:
      IA NA: IA ID 0x00020001, T1 43200, T2 69120
        Address: 2001:DB8:34:0:1C:580:9531:D6A3/128
                preferred lifetime INFINITY, valid lifetime INFINITY
      DNS server: 2001:4860:4860::8888
      Domain name: example.net
      Information refresh time: 0
  Prefix Rapid-Commit: disabled
  Address Rapid-Commit: disabled
```

**P5b stateful(M flag + address prefix + no-autoconfig / client ipv6 address dhcp) — RT04 show ipv6 routers**

```
Router FE80::A8BB:CCFF:FE01:5800 on Ethernet0/0, last update 0 min
  Hops 64, Lifetime 1800 sec, AddrFlag=1, OtherFlag=1, MTU=1500
  HomeAgentFlag=0, Preference=Medium
  Reachable time 0 (unspecified), Retransmit time 0 (unspecified)
  Prefix 2001:DB8:34::/64 onlink
    Valid lifetime 2592000, preferred lifetime 604800
```

**P5b stateful(M flag + address prefix + no-autoconfig / client ipv6 address dhcp) — RT04 show hosts | include Default|Name**

```
Default domain is not set
Name servers are 2001:4860:4860::8888
```

**P5b stateful(M flag + address prefix + no-autoconfig / client ipv6 address dhcp) — RT03 show ipv6 dhcp binding**

```
Client: FE80::A8BB:CCFF:FE01:5A00 
  DUID: 00030001AABBCC015A00
  Username : unassigned
  VRF : default
  IA NA: IA ID 0x00020001, T1 43200, T2 69120
    Address: 2001:DB8:34:0:1C:580:9531:D6A3
            preferred lifetime INFINITY, , valid lifetime INFINITY,
```

**P5b stateful(M flag + address prefix + no-autoconfig / client ipv6 address dhcp) — RT03 show ipv6 interface Ethernet0/0 | include Hosts|ND|advert|flag|unicast**

```
  Global unicast address(es):
  ND DAD is enabled, number of DAD attempts: 1
  ND reachable time is 30000 milliseconds (using 30000)
  ND advertised reachable time is 0 (unspecified)
  ND advertised retransmit interval is 0 (unspecified)
  ND router advertisements are sent every 200 seconds
  ND router advertisements live for 1800 seconds
  ND advertised default router preference is Medium
  Hosts use DHCP to obtain routable addresses.
  Hosts use DHCP to obtain other configuration.
```

**P5c3 M flag だが pool に address prefix 無し — RT04 show ipv6 interface brief**

```
Ethernet0/0            [up/up]
    FE80::A8BB:CCFF:FE01:5A00
Ethernet0/1            [up/up]
    unassigned
Ethernet0/2            [up/up]
    unassigned
Ethernet0/3            [up/up]
    unassigned
Ethernet1/0            [up/up]
    unassigned
Ethernet1/1            [up/up]
    unassigned
Ethernet1/2            [up/up]
    unassigned
Ethernet1/3            [up/up]
    unassigned
Ethernet2/0            [up/up]
    unassigned
Ethernet2/1            [up/up]
    unassigned
Ethernet2/2            [up/up]
    unassigned
Ethernet2/3            [up/up]
    unassigned
Ethernet3/0            [up/up]
    unassigned
Ethernet3/1            [up/up]
    unassigned
Ethernet3/2            [up/up]
    unassigned
Ethernet3/3            [up/up]
    unassigned
Ethernet4/0            [up/up]
    unassigned
Ethernet4/1            [up/up]
    unassigned
Ethernet4/2            [up/up]
    unassigned
Ethernet4/3            [up/up]
    unassigned
Ethernet5/0            [up/up]
    unassigned
Ethernet5/1            [up/up]
    unassigned
Ethernet5/2            [up/up]
    unassigned
Ethernet5/3            [up/up]
    unassigned
Ethernet6/0            [up/up]
    unassigned
Ethernet6/1            [up/up]
    unassigned
Ethernet6/2            [up/up]
    unassigned
Ethernet6/3            [up/up]
    unassigned
Ethernet7/0            [up/up]
    unassigned
Ethernet7/1            [up/up]
    unassigned
Ethernet7/2            [up/up]
    unassigned
Ethernet7/3            [up/up]
    unassigned
Loopback0              [up/up]
    unassigned
```

**P5c3 M flag だが pool に address prefix 無し — RT04 show ipv6 dhcp interface Ethernet0/0**

```
Ethernet0/0 is in client mode
  Prefix State is IDLE
  Address State is SOLICIT (5)
  Retransmission timer expires in 00:00:10
  Prefix Rapid-Commit: disabled
  Address Rapid-Commit: disabled
```

**P5c3 M flag だが pool に address prefix 無し — RT04 show ipv6 routers**

```
Router FE80::A8BB:CCFF:FE01:5800 on Ethernet0/0, last update 0 min
  Hops 64, Lifetime 1800 sec, AddrFlag=1, OtherFlag=1, MTU=1500
  HomeAgentFlag=0, Preference=Medium
  Reachable time 0 (unspecified), Retransmit time 0 (unspecified)
  Prefix 2001:DB8:34::/64 onlink
    Valid lifetime 2592000, preferred lifetime 604800
```

**P5c3 M flag だが pool に address prefix 無し — RT04 show hosts | include Default|Name**

```
Default domain is not set
Name servers are 255.255.255.255
```

**P5c3 M flag だが pool に address prefix 無し — RT03 show ipv6 dhcp binding**

```

```

**P5c3 M flag だが pool に address prefix 無し — RT03 show ipv6 interface Ethernet0/0 | include Hosts|ND|advert|flag|unicast**

```
  Global unicast address(es):
  ND DAD is enabled, number of DAD attempts: 1
  ND reachable time is 30000 milliseconds (using 30000)
  ND advertised reachable time is 0 (unspecified)
  ND advertised retransmit interval is 0 (unspecified)
  ND router advertisements are sent every 200 seconds
  ND router advertisements live for 1800 seconds
  ND advertised default router preference is Medium
  Hosts use DHCP to obtain routable addresses.
  Hosts use DHCP to obtain other configuration.
```

**P5c6 ipv6 address dhcp のみ(ipv6 enable 無し) — RT04 show ipv6 interface brief**

```
Ethernet0/0            [up/up]
    unassigned
Ethernet0/1            [up/up]
    unassigned
Ethernet0/2            [up/up]
    unassigned
Ethernet0/3            [up/up]
    unassigned
Ethernet1/0            [up/up]
    unassigned
Ethernet1/1            [up/up]
    unassigned
Ethernet1/2            [up/up]
    unassigned
Ethernet1/3            [up/up]
    unassigned
Ethernet2/0            [up/up]
    unassigned
Ethernet2/1            [up/up]
    unassigned
Ethernet2/2            [up/up]
    unassigned
Ethernet2/3            [up/up]
    unassigned
Ethernet3/0            [up/up]
    unassigned
Ethernet3/1            [up/up]
    unassigned
Ethernet3/2            [up/up]
    unassigned
Ethernet3/3            [up/up]
    unassigned
Ethernet4/0            [up/up]
    unassigned
Ethernet4/1            [up/up]
    unassigned
Ethernet4/2            [up/up]
    unassigned
Ethernet4/3            [up/up]
    unassigned
Ethernet5/0            [up/up]
    unassigned
Ethernet5/1            [up/up]
    unassigned
Ethernet5/2            [up/up]
    unassigned
Ethernet5/3            [up/up]
    unassigned
Ethernet6/0            [up/up]
    unassigned
Ethernet6/1            [up/up]
    unassigned
Ethernet6/2            [up/up]
    unassigned
Ethernet6/3            [up/up]
    unassigned
Ethernet7/0            [up/up]
    unassigned
Ethernet7/1            [up/up]
    unassigned
Ethernet7/2            [up/up]
    unassigned
Ethernet7/3            [up/up]
    unassigned
Loopback0              [up/up]
    unassigned
```

**P5c6 ipv6 address dhcp のみ(ipv6 enable 無し) — RT04 show ipv6 dhcp interface Ethernet0/0**

```
Ethernet0/0 is in client mode
  Prefix State is IDLE
  Address State is IDLE
  Prefix Rapid-Commit: disabled
  Address Rapid-Commit: disabled
```

**P5c6 ipv6 address dhcp のみ(ipv6 enable 無し) — RT04 show ipv6 routers**

```

```

**P5c6 ipv6 address dhcp のみ(ipv6 enable 無し) — RT04 show hosts | include Default|Name**

```
Default domain is not set
Name servers are 255.255.255.255
```

**P5c6 ipv6 address dhcp のみ(ipv6 enable 無し) — RT03 show ipv6 dhcp binding**

```

```

**P5c6 ipv6 address dhcp のみ(ipv6 enable 無し) — RT03 show ipv6 interface Ethernet0/0 | include Hosts|ND|advert|flag|unicast**

```
  Global unicast address(es):
  ND DAD is enabled, number of DAD attempts: 1
  ND reachable time is 30000 milliseconds (using 30000)
  ND advertised reachable time is 0 (unspecified)
  ND advertised retransmit interval is 0 (unspecified)
  ND router advertisements are sent every 200 seconds
  ND router advertisements live for 1800 seconds
  ND advertised default router preference is Medium
  Hosts use DHCP to obtain routable addresses.
  Hosts use DHCP to obtain other configuration.
```

## P6 EIGRP auto-summary 境界  (2026-09-18 13:28)

**P6 show run | section router eigrp (RT02)**

```
router eigrp 1
 network 172.16.0.0
 network 172.17.0.0
 auto-summary
```

**P6a 全台 auto-summary(壊れた基線) — RT01 show ip route eigrp**

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

D     172.17.0.0/16 [90/307200] via 172.16.12.2, 00:00:28, Ethernet0/0
```

**P6a 全台 auto-summary(壊れた基線) — RT02 show ip route eigrp**

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

      172.16.0.0/16 is variably subnetted, 4 subnets, 3 masks
D        172.16.0.0/16 is a summary, 00:00:26, Null0
D        172.16.11.0/24 [90/409600] via 172.16.12.1, 00:00:29, Ethernet0/0
      172.17.0.0/16 is variably subnetted, 3 subnets, 3 masks
D        172.17.0.0/16 is a summary, 00:00:34, Null0
```

**P6a 全台 auto-summary(壊れた基線) — RT03 show ip route eigrp**

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

      172.16.0.0/16 is variably subnetted, 4 subnets, 3 masks
D        172.16.0.0/16 is a summary, 00:00:29, Null0
D        172.16.41.0/24 [90/409600] via 172.16.34.4, 00:00:32, Ethernet0/0
      172.17.0.0/16 is variably subnetted, 3 subnets, 3 masks
D        172.17.0.0/16 is a summary, 00:00:33, Null0
```

**P6a 全台 auto-summary(壊れた基線) — RT04 show ip route eigrp**

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

D     172.17.0.0/16 [90/307200] via 172.16.34.3, 00:00:32, Ethernet0/0
```

**P6a 全台 auto-summary(壊れた基線) — RT01 show ip route 172.16.41.4**

```
% Subnet not in table
```

**P6a 全台 auto-summary(壊れた基線) ping RT01(172.16.11.1)→172.16.41.4 — RT01# ping 172.16.41.4 repeat 3 source 172.16.11.1 → 0%**

```
Type escape sequence to abort.
Sending 3, 100-byte ICMP Echos to 172.16.41.4, timeout is 2 seconds:
Packet sent with a source address of 172.16.11.1 
...
Success rate is 0 percent (0/3)
```

**P6a 全台 auto-summary(壊れた基線) ping RT04(172.16.41.4)→172.16.11.1 — RT04# ping 172.16.11.1 repeat 3 source 172.16.41.4 → 0%**

```
Type escape sequence to abort.
Sending 3, 100-byte ICMP Echos to 172.16.11.1, timeout is 2 seconds:
Packet sent with a source address of 172.16.41.4 
...
Success rate is 0 percent (0/3)
```

**P6b 非境界 RT01 だけ no auto-summary(効かないはず) — RT01 show ip route eigrp**

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

D     172.17.0.0/16 [90/307200] via 172.16.12.2, 00:01:03, Ethernet0/0
```

**P6b 非境界 RT01 だけ no auto-summary(効かないはず) — RT02 show ip route eigrp**

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

      172.16.0.0/16 is variably subnetted, 4 subnets, 3 masks
D        172.16.0.0/16 is a summary, 00:01:01, Null0
D        172.16.11.0/24 [90/409600] via 172.16.12.1, 00:01:04, Ethernet0/0
      172.17.0.0/16 is variably subnetted, 3 subnets, 3 masks
D        172.17.0.0/16 is a summary, 00:01:09, Null0
```

**P6b 非境界 RT01 だけ no auto-summary(効かないはず) — RT03 show ip route eigrp**

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

      172.16.0.0/16 is variably subnetted, 4 subnets, 3 masks
D        172.16.0.0/16 is a summary, 00:01:04, Null0
D        172.16.41.0/24 [90/409600] via 172.16.34.4, 00:01:07, Ethernet0/0
      172.17.0.0/16 is variably subnetted, 3 subnets, 3 masks
D        172.17.0.0/16 is a summary, 00:01:08, Null0
```

**P6b 非境界 RT01 だけ no auto-summary(効かないはず) — RT04 show ip route eigrp**

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

D     172.17.0.0/16 [90/307200] via 172.16.34.3, 00:01:07, Ethernet0/0
```

**P6b 非境界 RT01 だけ no auto-summary(効かないはず) — RT01 show ip route 172.16.41.4**

```
% Subnet not in table
```

**P6b 非境界 RT01 だけ no auto-summary(効かないはず) ping RT01(172.16.11.1)→172.16.41.4 — RT01# ping 172.16.41.4 repeat 3 source 172.16.11.1 → 0%**

```
Type escape sequence to abort.
Sending 3, 100-byte ICMP Echos to 172.16.41.4, timeout is 2 seconds:
Packet sent with a source address of 172.16.11.1 
...
Success rate is 0 percent (0/3)
```

**P6b 非境界 RT01 だけ no auto-summary(効かないはず) ping RT04(172.16.41.4)→172.16.11.1 — RT04# ping 172.16.11.1 repeat 3 source 172.16.41.4 → 0%**

```
Type escape sequence to abort.
Sending 3, 100-byte ICMP Echos to 172.16.11.1, timeout is 2 seconds:
Packet sent with a source address of 172.16.41.4 
...
Success rate is 0 percent (0/3)
```

**P6c 境界 RT02 だけ no auto-summary(片側) — RT01 show ip route eigrp**

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

      172.16.0.0/16 is variably subnetted, 5 subnets, 3 masks
D        172.16.0.0/16 [90/332800] via 172.16.12.2, 00:00:21, Ethernet0/0
      172.17.0.0/24 is subnetted, 1 subnets
D        172.17.23.0 [90/307200] via 172.16.12.2, 00:00:21, Ethernet0/0
```

**P6c 境界 RT02 だけ no auto-summary(片側) — RT02 show ip route eigrp**

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

      172.16.0.0/16 is variably subnetted, 4 subnets, 3 masks
D        172.16.0.0/16 [90/307200] via 172.17.23.3, 00:00:21, Ethernet0/1
D        172.16.11.0/24 [90/409600] via 172.16.12.1, 00:01:40, Ethernet0/0
```

**P6c 境界 RT02 だけ no auto-summary(片側) — RT03 show ip route eigrp**

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

      172.16.0.0/16 is variably subnetted, 6 subnets, 3 masks
D        172.16.0.0/16 is a summary, 00:01:40, Null0
D        172.16.11.0/24 [90/435200] via 172.17.23.2, 00:00:21, Ethernet0/1
D        172.16.12.0/24 [90/307200] via 172.17.23.2, 00:00:21, Ethernet0/1
D        172.16.41.0/24 [90/409600] via 172.16.34.4, 00:01:43, Ethernet0/0
      172.17.0.0/16 is variably subnetted, 3 subnets, 3 masks
D        172.17.0.0/16 is a summary, 00:01:44, Null0
```

**P6c 境界 RT02 だけ no auto-summary(片側) — RT04 show ip route eigrp**

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

      172.16.0.0/16 is variably subnetted, 6 subnets, 2 masks
D        172.16.11.0/24 [90/460800] via 172.16.34.3, 00:00:21, Ethernet0/0
D        172.16.12.0/24 [90/332800] via 172.16.34.3, 00:00:21, Ethernet0/0
D     172.17.0.0/16 [90/307200] via 172.16.34.3, 00:01:43, Ethernet0/0
```

**P6c 境界 RT02 だけ no auto-summary(片側) — RT01 show ip route 172.16.41.4**

```
Routing entry for 172.16.0.0/16
  Known via "eigrp 1", distance 90, metric 332800, precedence routine (0), type internal
  Redistributing via eigrp 1
  Last update from 172.16.12.2 on Ethernet0/0, 00:00:22 ago
  Routing Descriptor Blocks:
  * 172.16.12.2, from 172.16.12.2, 00:00:22 ago, via Ethernet0/0
      Route metric is 332800, traffic share count is 1
      Total delay is 3000 microseconds, minimum bandwidth is 10000 Kbit
      Reliability 255/255, minimum MTU 1500 bytes
      Loading 1/255, Hops 2
```

**P6c 境界 RT02 だけ no auto-summary(片側) ping RT01(172.16.11.1)→172.16.41.4 — RT01# ping 172.16.41.4 repeat 3 source 172.16.11.1 → 100%**

```
Type escape sequence to abort.
Sending 3, 100-byte ICMP Echos to 172.16.41.4, timeout is 2 seconds:
Packet sent with a source address of 172.16.11.1 
!!!
Success rate is 100 percent (3/3), round-trip min/avg/max = 1/5/13 ms
```

**P6c 境界 RT02 だけ no auto-summary(片側) ping RT04(172.16.41.4)→172.16.11.1 — RT04# ping 172.16.11.1 repeat 3 source 172.16.41.4 → 100%**

```
Type escape sequence to abort.
Sending 3, 100-byte ICMP Echos to 172.16.11.1, timeout is 2 seconds:
Packet sent with a source address of 172.16.41.4 
!!!
Success rate is 100 percent (3/3), round-trip min/avg/max = 1/1/2 ms
```

**P6d 境界 RT02+RT03 no auto-summary(両側) — RT01 show ip route eigrp**

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

      172.16.0.0/16 is variably subnetted, 6 subnets, 2 masks
D        172.16.34.0/24 [90/332800] via 172.16.12.2, 00:00:21, Ethernet0/0
D        172.16.41.0/24 [90/460800] via 172.16.12.2, 00:00:21, Ethernet0/0
      172.17.0.0/24 is subnetted, 1 subnets
D        172.17.23.0 [90/307200] via 172.16.12.2, 00:00:44, Ethernet0/0
```

**P6d 境界 RT02+RT03 no auto-summary(両側) — RT02 show ip route eigrp**

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

      172.16.0.0/16 is variably subnetted, 5 subnets, 2 masks
D        172.16.11.0/24 [90/409600] via 172.16.12.1, 00:02:03, Ethernet0/0
D        172.16.34.0/24 [90/307200] via 172.17.23.3, 00:00:21, Ethernet0/1
D        172.16.41.0/24 [90/435200] via 172.17.23.3, 00:00:21, Ethernet0/1
```

**P6d 境界 RT02+RT03 no auto-summary(両側) — RT03 show ip route eigrp**

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

      172.16.0.0/16 is variably subnetted, 5 subnets, 2 masks
D        172.16.11.0/24 [90/435200] via 172.17.23.2, 00:00:44, Ethernet0/1
D        172.16.12.0/24 [90/307200] via 172.17.23.2, 00:00:44, Ethernet0/1
D        172.16.41.0/24 [90/409600] via 172.16.34.4, 00:02:06, Ethernet0/0
```

**P6d 境界 RT02+RT03 no auto-summary(両側) — RT04 show ip route eigrp**

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

      172.16.0.0/16 is variably subnetted, 6 subnets, 2 masks
D        172.16.11.0/24 [90/460800] via 172.16.34.3, 00:00:44, Ethernet0/0
D        172.16.12.0/24 [90/332800] via 172.16.34.3, 00:00:44, Ethernet0/0
      172.17.0.0/24 is subnetted, 1 subnets
D        172.17.23.0 [90/307200] via 172.16.34.3, 00:00:21, Ethernet0/0
```

**P6d 境界 RT02+RT03 no auto-summary(両側) — RT01 show ip route 172.16.41.4**

```
Routing entry for 172.16.41.0/24
  Known via "eigrp 1", distance 90, metric 460800, precedence routine (0), type internal
  Redistributing via eigrp 1
  Last update from 172.16.12.2 on Ethernet0/0, 00:00:22 ago
  Routing Descriptor Blocks:
  * 172.16.12.2, from 172.16.12.2, 00:00:22 ago, via Ethernet0/0
      Route metric is 460800, traffic share count is 1
      Total delay is 8000 microseconds, minimum bandwidth is 10000 Kbit
      Reliability 255/255, minimum MTU 1500 bytes
      Loading 1/255, Hops 3
```

**P6d 境界 RT02+RT03 no auto-summary(両側) ping RT01(172.16.11.1)→172.16.41.4 — RT01# ping 172.16.41.4 repeat 3 source 172.16.11.1 → 100%**

```
Type escape sequence to abort.
Sending 3, 100-byte ICMP Echos to 172.16.41.4, timeout is 2 seconds:
Packet sent with a source address of 172.16.11.1 
!!!
Success rate is 100 percent (3/3), round-trip min/avg/max = 1/4/9 ms
```

**P6d 境界 RT02+RT03 no auto-summary(両側) ping RT04(172.16.41.4)→172.16.11.1 — RT04# ping 172.16.11.1 repeat 3 source 172.16.41.4 → 100%**

```
Type escape sequence to abort.
Sending 3, 100-byte ICMP Echos to 172.16.11.1, timeout is 2 seconds:
Packet sent with a source address of 172.16.41.4 
!!!
Success rate is 100 percent (3/3), round-trip min/avg/max = 1/1/2 ms
```

## P3h2 stub 再測  (2026-09-18 14:06)

**P3h2 基線 OSPF FULL**

```
Nones
```

**P3h2 stub 不一致(clear 後) — RT01 show ip ospf neighbor**

```

```

**P3h2 stub 不一致(clear 後) — RT02 show ip ospf neighbor**

```

```

**P3h2 [RT01] — RT01 show logging**

```
*Sep 18 14:03:21.959: OSPF-1 EVENT: Config: no network 10.0.12.0 255.255.255.0 area 0
*Sep 18 14:03:22.060: OSPF-1 EVENT: Config: network 10.0.12.0 255.255.255.0 area 1
```

**P3h2 [RT02] — RT02 show logging**

```
*Sep 18 14:03:22.801: OSPF-1 EVENT: Config: no network 10.0.12.0 255.255.255.0 area 0
*Sep 18 14:03:22.876: OSPF-1 EVENT: Config: network 10.0.12.0 255.255.255.0 area 1
*Sep 18 14:03:23.076: OSPF-1 EVENT: Area config: 'area 1 stub'
```

- P3h2 復旧 FULL = Nones

## P1c MQC/named 追加採取  (2026-09-18 14:07)

**P1c MQC: set dscp ? — RT01: policy-map PM-POC / class class-default : set dscp ?**

```
set dscp ?
  <0-63>   Differentiated services codepoint value
  af11     Match packets with AF11 dscp (001010)
  af12     Match packets with AF12 dscp (001100)
  af13     Match packets with AF13 dscp (001110)
  af21     Match packets with AF21 dscp (010010)
  af22     Match packets with AF22 dscp (010100)
  af23     Match packets with AF23 dscp (010110)
  af31     Match packets with AF31 dscp (011010)
  af32     Match packets with AF32 dscp (011100)
  af33     Match packets with AF33 dscp (011110)
  af41     Match packets with AF41 dscp (100010)
  af42     Match packets with AF42 dscp (100100)
  af43     Match packets with AF43 dscp (100110)
  cs1      Match packets with CS1(precedence 1) dscp (001000)
  cs2      Match packets with CS2(precedence 2) dscp (010000)
  cs3      Match packets with CS3(precedence 3) dscp (011000)
  cs4      Match packets with CS4(precedence 4) dscp (100000)
  cs5      Match packets with CS5(precedence 5) dscp (101000)
  cs6      Match packets with CS6(precedence 6) dscp (110000)
  cs7      Match packets with CS7(precedence 7) dscp (111000)
  default  Match packets with default dscp (000000)
  ef       Match packets with EF dscp (101110)
  tunnel   set tunnel packet dscp

RT01(config-pmap-c)#set dscp
```

**P1c MQC: set precedence ? — RT01: policy-map PM-POC / class class-default : set precedence ?**

```
set precedence ?
  <0-7>           Precedence value
  critical        Match packets with critical precedence (5)
  flash           Match packets with flash precedence (3)
  flash-override  Match packets with flash override precedence (4)
  immediate       Match packets with immediate precedence (2)
  internet        Match packets with internetwork control precedence (6)
  network         Match Packets with network control precedence (7)
  priority        Match packets with priority precedence (1)
  routine         Match packets with routine precedence (0)
  tunnel          Set tunnel packet precedence

RT01(config-pmap-c)#set precedence
```

**P1c MQC: set ip dscp ? — RT01: policy-map PM-POC / class class-default : set ip dscp ?**

```
set ip dscp ?
  <0-63>   Differentiated services codepoint value
  af11     Match packets with AF11 dscp (001010)
  af12     Match packets with AF12 dscp (001100)
  af13     Match packets with AF13 dscp (001110)
  af21     Match packets with AF21 dscp (010010)
  af22     Match packets with AF22 dscp (010100)
  af23     Match packets with AF23 dscp (010110)
  af31     Match packets with AF31 dscp (011010)
  af32     Match packets with AF32 dscp (011100)
  af33     Match packets with AF33 dscp (011110)
  af41     Match packets with AF41 dscp (100010)
  af42     Match packets with AF42 dscp (100100)
  af43     Match packets with AF43 dscp (100110)
  cs1      Match packets with CS1(precedence 1) dscp (001000)
  cs2      Match packets with CS2(precedence 2) dscp (010000)
  cs3      Match packets with CS3(precedence 3) dscp (011000)
  cs4      Match packets with CS4(precedence 4) dscp (100000)
  cs5      Match packets with CS5(precedence 5) dscp (101000)
  cs6      Match packets with CS6(precedence 6) dscp (110000)
  cs7      Match packets with CS7(precedence 7) dscp (111000)
  default  Match packets with default dscp (000000)
  ef       Match packets with EF dscp (101110)
  tunnel   set tunnel packet dscp

RT01(config-pmap-c)#set ip dscp
```

**P1c show policy-map PM-POC(dscp の表示形)**

```
  Policy Map PM-POC
    Class class-default
      set dscp af31
```

**P1c show route-map RM-POC2(数値指定の表示形)**

```
route-map RM-POC2, permit, sequence 10
  Match clauses:
  Set clauses:
    ip precedence priority
    ip tos min-delay
  Policy routing matches: 0 packets, 0 bytes
```

**P1c show run | section route-map RM-POC2**

```
route-map RM-POC2 permit 10 
 set ip precedence priority
 set ip tos min-delay
```

**P1c named af: metric ? — RT01: router eigrp NAMED / address-family ipv4 unicast autonomous-system 300 : metric ?**

```
metric ?
  rib-scale  set scaling value for rib installation
  version    set version for metric calculation
  weights    Modify address-family metric coefficients

RT01(config-router-af)#metric
```

**P1c named af-topology: metric ? — RT01: router eigrp NAMED / address-family ipv4 unicast autonomous-system 300 / topology base : metric ?**

```
metric ?
  maximum-hops  Advertise greater than <hops> as unreachable

RT01(config-router-af-topology)#metric
```

**P1c named af: timers ? — RT01: router eigrp NAMED / address-family ipv4 unicast autonomous-system 300 : timers ?**

```
timers ?
  graceful-restart  EIGRP Graceful Restart timer
  nsf               EIGRP NSF timer

RT01(config-router-af)#timers
```

**P1c named af-topology: timers ? — RT01: router eigrp NAMED / address-family ipv4 unicast autonomous-system 300 / topology base : timers ?**

```
timers ?
  active-time  time limit for active state

RT01(config-router-af-topology)#timers
```

**P1c named af: eigrp stub ? — RT01: router eigrp NAMED / address-family ipv4 unicast autonomous-system 300 : eigrp stub ?**

```
eigrp stub ?
  connected      Do advertise connected routes
  leak-map       Allow dynamic prefixes based on the leak-map
  receive-only   Set receive only neighbor
  redistributed  Do advertise redistributed routes
  static         Do advertise static routes
  summary        Do advertise summary routes
  <cr>           <cr>

RT01(config-router-af)#eigrp stub
```

**P1c named af-interface Ethernet0/0: ? — RT01: router eigrp NAMED / address-family ipv4 unicast autonomous-system 300 / af-interface Ethernet0/0 : ?**

```
?
Address Family Interfaces configuration commands:
  add-paths           Advertise add paths
  authentication      authentication subcommands
  bandwidth-percent   Set percentage of bandwidth percentage limit
  bfd                 Enable Bidirectional Forwarding Detection
  dampening-change    Percent interface metric must change to cause update
  dampening-interval  Time in seconds to check interface metrics
  default             Set a command to its defaults
  exit-af-interface   Exit from Address Family Interface configuration mode
  hello-interval      Configures hello interval
  hold-time           Configures hold time
  next-hop-self       Configures EIGRP next-hop-self
  no                  Negate a command or set its defaults
  passive-interface   Suppress address updates on an interface
  shutdown            Disable Address-Family on interface
  split-horizon       Perform split horizon
  stub-site           Stub-Site
  summary-address     Perform address summarization

RT01(config-router-af-interface)#
```

**P1c named af-interface: authentication mode ? — RT01: router eigrp NAMED / address-family ipv4 unicast autonomous-system 300 / af-interface Ethernet0/0 : authentication mode ?**

```
authentication mode ?
  hmac-sha-256  HMAC-SHA-256 Authentication
  md5           Keyed message digest

RT01(config-router-af-interface)#authentication mode
```

**P1c named af-topology: variance ? — RT01: router eigrp NAMED / address-family ipv4 unicast autonomous-system 300 / topology base : variance ?**

```
variance ?
  <1-128>  Metric variance multiplier

RT01(config-router-af-topology)#variance
```

## P3h3 stub 再測(正しいアドレス)  (2026-09-18 14:12)

**P3h3 基線 OSPF FULL(area 1・両側 non-stub)**

```
43.065884590148926s

Neighbor ID     Pri   State           Dead Time   Address         Interface
2.2.2.2           1   FULL/DR         00:00:39    172.16.12.2     Ethernet0/0

Neighbor ID     Pri   State           Dead Time   Address         Interface
1.1.1.1           1   FULL/BDR        00:00:39    172.16.12.1     Ethernet0/0
```

**P3h3 stub 不一致(RT02 だけ area 1 stub・clear 後 75s) — RT01 show ip ospf neighbor**

```

```

**P3h3 stub 不一致 — RT02 show ip ospf neighbor**

```

```

**P3h3 [RT01] — RT01 show logging**

```
*Sep 18 14:11:27.651: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 1 172.16.12.2
*Sep 18 14:11:27.651: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 14:11:27.651: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 14:11:27.651: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 14:11:27.651: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 14:11:27.651: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 14:11:27.651: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 14:11:27.651: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 14:11:27.651: OSPF-1 ADJ   Et0/0:    BDR: 1.1.1.1 (Id)
*Sep 18 14:11:27.651: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 1 AllRTR 0 AllDR 1
*Sep 18 14:11:27.651: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 14:11:27.651: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 14:11:27.651: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 14:11:27.651: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 14:11:27.651: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 14:11:27.651: OSPF-1 ADJ   Et0/0:    BDR: 1.1.1.1 (Id)
*Sep 18 14:11:28.252: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 172.16.12.1
*Sep 18 14:11:28.281: OSPF-1 ADJ   Et0/0: Interface going Down
*Sep 18 14:11:28.281: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 172.16.12.2 is dead, state DOWN
*Sep 18 14:11:28.281: %OSPF-5-ADJCHG: Process 1, Nbr 2.2.2.2 on Ethernet0/0 from FULL to DOWN, Neighbor Down: Interface down or detached
*Sep 18 14:11:28.281: OSPF-1 ADJ   Et0/0: Nbr 2.2.2.2: Clean-up dbase exchange
*Sep 18 14:11:28.281: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 14:11:28.281: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 14:11:28.281: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 14:11:28.281: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 14:11:28.281: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 14:11:28.281: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 14:11:28.281: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 14:11:28.281: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 14:11:28.281: OSPF-1 ADJ   Et0/0: Remember old DR 2.2.2.2 (id)
*Sep 18 14:11:28.281: OSPF-1 ADJ   Et0/0: 1.1.1.1 address 172.16.12.1 is dead, state DOWN
*Sep 18 14:11:28.281: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 14:11:28.281: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 14:11:28.281: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 14:11:28.281: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 14:11:28.281: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 14:11:28.281: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 14:11:28.281: OSPF-1 ADJ   Et0/0: DR: none 
*Sep 18 14:11:28.281: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 14:11:28.281: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 0 AllRTR 0 AllDR 1
*Sep 18 14:11:28.281: OSPF-1 ADJ   Et0/0: Flush network LSA immediately
*Sep 18 14:11:28.281: OSPF-1 ADJ   Et0/0: Remember old DR 1.1.1.1 (id)
*Sep 18 14:11:28.281: OSPF-1 ADJ   Et0/0: Interface going Up
*Sep 18 14:11:28.281: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 172.16.12.1
*Sep 18 14:11:28.632: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 1 172.16.12.2
*Sep 18 14:11:28.632: OSPF-1 HELLO Et0/0: Hello from 172.16.12.2 with mismatched Stub/Transit area option bit
*Sep 18 14:11:37.706: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 1 172.16.12.2
*Sep 18 14:11:37.706: OSPF-1 HELLO Et0/0: Hello from 172.16.12.2 with mismatched Stub/Transit area option bit
*Sep 18 14:11:37.749: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 172.16.12.1
*Sep 18 14:11:46.923: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 1 172.16.12.2
*Sep 18 14:11:46.923: OSPF-1 HELLO Et0/0: Hello from 172.16.12.2 with mismatched Stub/Transit area option bit
*Sep 18 14:11:46.949: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 172.16.12.1
*Sep 18 14:11:56.862: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 172.16.12.1
*Sep 18 14:11:56.885: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 1 172.16.12.2
*Sep 18 14:11:56.885: OSPF-1 HELLO Et0/0: Hello from 172.16.12.2 with mismatched Stub/Transit area option bit
*Sep 18 14:12:06.129: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 172.16.12.1
*Sep 18 14:12:06.591: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 1 172.16.12.2
*Sep 18 14:12:06.591: OSPF-1 HELLO Et0/0: Hello from 172.16.12.2 with mismatched Stub/Transit area option bit
*Sep 18 14:12:08.281: OSPF-1 ADJ   Et0/0: end of Wait on interface
*Sep 18 14:12:08.281: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 14:12:08.281: OSPF-1 ADJ   Et0/0: Elect BDR 1.1.1.1
*Sep 18 14:12:08.281: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 14:12:08.281: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 14:12:08.281: OSPF-1 ADJ   Et0/0: Elect DR 1.1.1.1
*Sep 18 14:12:08.281: OSPF-1 ADJ   Et0/0: DR: 1.1.1.1 (Id)
*Sep 18 14:12:08.281: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 14:12:08.281: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 1 AllRTR 0 AllDR 1
*Sep 18 14:12:15.333: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 172.16.12.1
*Sep 18 14:12:16.093: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 1 172.16.12.2
*Sep 18 14:12:16.093: OSPF-1 HELLO Et0/0: Hello from 172.16.12.2 with mismatched Stub/Transit area option bit
*Sep 18 14:12:24.951: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 172.16.12.1
*Sep 18 14:12:25.539: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 1 172.16.12.2
*Sep 18 14:12:25.539: OSPF-1 HELLO Et0/0: Hello from 172.16.12.2 with mismatched Stub/Transit area option bit
*Sep 18 14:12:34.519: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 172.16.12.1
*Sep 18 14:12:35.289: OSPF-1 HELLO Et0/0: Rcv hello from 2.2.2.2 area 1 172.16.12.2
*Sep 18 14:12:35.289: OSPF-1 HELLO Et0/0: Hello from 172.16.12.2 with mismatched Stub/Transit area option bit
*Sep 18 14:12:43.909: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 172.16.12.1
```

**P3h3 [RT02] — RT02 show logging**

```
*Sep 18 14:11:27.651: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 172.16.12.2
*Sep 18 14:11:27.759: OSPF-1 EVENT: Area config: 'area 1 stub'
*Sep 18 14:11:27.759: OSPF-1 ADJ   Et0/0: 1.1.1.1 address 172.16.12.1 is dead, state DOWN
*Sep 18 14:11:27.759: %OSPF-5-ADJCHG: Process 1, Nbr 1.1.1.1 on Ethernet0/0 from FULL to DOWN, Neighbor Down: Adjacency forced to reset
*Sep 18 14:11:27.759: OSPF-1 ADJ   Et0/0: Nbr 1.1.1.1: Clean-up dbase exchange
*Sep 18 14:11:27.759: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 14:11:27.759: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 14:11:27.759: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 14:11:27.759: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 14:11:27.759: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 14:11:27.759: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 14:11:28.252: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 1 172.16.12.1
*Sep 18 14:11:28.252: OSPF-1 HELLO Et0/0: Hello from 172.16.12.1 with mismatched Stub/Transit area option bit
*Sep 18 14:11:28.281: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 1 172.16.12.1
*Sep 18 14:11:28.281: OSPF-1 HELLO Et0/0: Hello from 172.16.12.1 with mismatched Stub/Transit area option bit
*Sep 18 14:11:28.632: OSPF-1 ADJ   Et0/0: Interface going Down
*Sep 18 14:11:28.632: OSPF-1 ADJ   Et0/0: 1.1.1.1 address 172.16.12.1 is dead, state DOWN
*Sep 18 14:11:28.632: %OSPF-5-ADJCHG: Process 1, Nbr 1.1.1.1 on Ethernet0/0 from DOWN to DOWN, Neighbor Down: Interface down or detached
*Sep 18 14:11:28.632: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 14:11:28.632: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 14:11:28.632: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 14:11:28.632: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 14:11:28.632: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 14:11:28.632: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 14:11:28.632: OSPF-1 ADJ   Et0/0: 2.2.2.2 address 172.16.12.2 is dead, state DOWN
*Sep 18 14:11:28.632: OSPF-1 ADJ   Et0/0: Neighbor change event
*Sep 18 14:11:28.632: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 14:11:28.632: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 14:11:28.632: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 14:11:28.632: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 14:11:28.632: OSPF-1 ADJ   Et0/0: Elect DR 0.0.0.0
*Sep 18 14:11:28.632: OSPF-1 ADJ   Et0/0: DR: none 
*Sep 18 14:11:28.632: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 14:11:28.632: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 0 AllRTR 0 AllDR 1
*Sep 18 14:11:28.632: OSPF-1 ADJ   Et0/0: Flush network LSA immediately
*Sep 18 14:11:28.632: OSPF-1 ADJ   Et0/0: Remember old DR 2.2.2.2 (id)
*Sep 18 14:11:28.632: OSPF-1 ADJ   Et0/0: Interface going Up
*Sep 18 14:11:28.632: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 172.16.12.2
*Sep 18 14:11:37.706: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 172.16.12.2
*Sep 18 14:11:37.750: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 1 172.16.12.1
*Sep 18 14:11:37.750: OSPF-1 HELLO Et0/0: Hello from 172.16.12.1 with mismatched Stub/Transit area option bit
*Sep 18 14:11:46.923: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 172.16.12.2
*Sep 18 14:11:46.949: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 1 172.16.12.1
*Sep 18 14:11:46.949: OSPF-1 HELLO Et0/0: Hello from 172.16.12.1 with mismatched Stub/Transit area option bit
*Sep 18 14:11:56.862: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 1 172.16.12.1
*Sep 18 14:11:56.862: OSPF-1 HELLO Et0/0: Hello from 172.16.12.1 with mismatched Stub/Transit area option bit
*Sep 18 14:11:56.885: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 172.16.12.2
*Sep 18 14:12:06.130: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 1 172.16.12.1
*Sep 18 14:12:06.130: OSPF-1 HELLO Et0/0: Hello from 172.16.12.1 with mismatched Stub/Transit area option bit
*Sep 18 14:12:06.591: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 172.16.12.2
*Sep 18 14:12:08.634: OSPF-1 ADJ   Et0/0: end of Wait on interface
*Sep 18 14:12:08.634: OSPF-1 ADJ   Et0/0: DR/BDR election
*Sep 18 14:12:08.634: OSPF-1 ADJ   Et0/0: Elect BDR 2.2.2.2
*Sep 18 14:12:08.634: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 14:12:08.634: OSPF-1 ADJ   Et0/0: Elect BDR 0.0.0.0
*Sep 18 14:12:08.634: OSPF-1 ADJ   Et0/0: Elect DR 2.2.2.2
*Sep 18 14:12:08.634: OSPF-1 ADJ   Et0/0: DR: 2.2.2.2 (Id)
*Sep 18 14:12:08.634: OSPF-1 ADJ   Et0/0:    BDR: none 
*Sep 18 14:12:08.634: OSPF-1 EVENT Et0/0: Queueing to Multicast WorkQ, Enable 1 AllRTR 0 AllDR 1
*Sep 18 14:12:15.335: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 1 172.16.12.1
*Sep 18 14:12:15.335: OSPF-1 HELLO Et0/0: Hello from 172.16.12.1 with mismatched Stub/Transit area option bit
*Sep 18 14:12:16.093: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 172.16.12.2
*Sep 18 14:12:24.952: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 1 172.16.12.1
*Sep 18 14:12:24.952: OSPF-1 HELLO Et0/0: Hello from 172.16.12.1 with mismatched Stub/Transit area option bit
*Sep 18 14:12:25.538: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 172.16.12.2
*Sep 18 14:12:34.532: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 1 172.16.12.1
*Sep 18 14:12:34.532: OSPF-1 HELLO Et0/0: Hello from 172.16.12.1 with mismatched Stub/Transit area option bit
*Sep 18 14:12:35.289: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 172.16.12.2
*Sep 18 14:12:43.910: OSPF-1 HELLO Et0/0: Rcv hello from 1.1.1.1 area 1 172.16.12.1
*Sep 18 14:12:43.910: OSPF-1 HELLO Et0/0: Hello from 172.16.12.1 with mismatched Stub/Transit area option bit
*Sep 18 14:12:44.533: OSPF-1 HELLO Et0/0: Send hello to 224.0.0.5 area 1 from 172.16.12.2
```

**P3h3 対照: 両側 area 1 stub → FULL = 0.6042068004608154s**

```

Neighbor ID     Pri   State           Dead Time   Address         Interface
2.2.2.2           1   FULL/BDR        00:00:39    172.16.12.2     Ethernet0/0

Neighbor ID     Pri   State           Dead Time   Address         Interface
1.1.1.1           1   FULL/DR         00:00:39    172.16.12.1     Ethernet0/0
```

## P3a4 mtu-ignore の側(R2a 再確認)  (2026-09-18 14:59)

**P3a4 基線 FULL**

```
43.2197847366333s

Neighbor ID     Pri   State           Dead Time   Address         Interface
2.2.2.2           1   FULL/DR         00:00:39    10.0.12.2       Ethernet0/0

Neighbor ID     Pri   State           Dead Time   Address         Interface
1.1.1.1           1   FULL/BDR        00:00:39    10.0.12.1       Ethernet0/0
```

**P3a4-1 小=RT02・ignore 小側だけ → FULL=True**

```

Neighbor ID     Pri   State           Dead Time   Address         Interface
2.2.2.2           1   FULL/BDR        00:00:36    10.0.12.2       Ethernet0/0

Neighbor ID     Pri   State           Dead Time   Address         Interface
1.1.1.1           1   FULL/DR         00:00:36    10.0.12.1       Ethernet0/0
```

**P3a4-2 小=RT02・ignore 大側だけ → FULL=False**

```

Neighbor ID     Pri   State           Dead Time   Address         Interface
2.2.2.2           1   EXCHANGE/BDR    00:00:36    10.0.12.2       Ethernet0/0

Neighbor ID     Pri   State           Dead Time   Address         Interface
1.1.1.1           1   EXSTART/DR      00:00:36    10.0.12.1       Ethernet0/0
```

**P3a4-3 小=RT01・ignore 小側だけ → FULL=True**

```

Neighbor ID     Pri   State           Dead Time   Address         Interface
2.2.2.2           1   FULL/BDR        00:00:35    10.0.12.2       Ethernet0/0

Neighbor ID     Pri   State           Dead Time   Address         Interface
1.1.1.1           1   FULL/DR         00:00:34    10.0.12.1       Ethernet0/0
```

**P3a4-4 小=RT01・ignore 大側だけ → FULL=False**

```

Neighbor ID     Pri   State           Dead Time   Address         Interface
2.2.2.2           1   EXSTART/BDR     00:00:36    10.0.12.2       Ethernet0/0

Neighbor ID     Pri   State           Dead Time   Address         Interface
1.1.1.1           1   EXSTART/DR      00:00:35    10.0.12.1       Ethernet0/0
```

**P3a4-5 小=RT02・ignore 両側 → FULL=True**

```

Neighbor ID     Pri   State           Dead Time   Address         Interface
2.2.2.2           1   FULL/BDR        00:00:36    10.0.12.2       Ethernet0/0

Neighbor ID     Pri   State           Dead Time   Address         Interface
1.1.1.1           1   FULL/DR         00:00:34    10.0.12.1       Ethernet0/0
```

- P3a4 まとめ: small=RT02 ignore=RT02(小): FULL / small=RT02 ignore=RT01(大): NOT FULL / small=RT01 ignore=RT01(小): FULL / small=RT01 ignore=RT02(大): NOT FULL / small=RT02 ignore=両側: FULL

## P7 DMVPN show 指紋(IOL crypto)  (2026-09-18 15:54)

**P7-0 underlay RT01 Lo0→hub Lo0 — RT01# ping 2.2.2.2 repeat 3 source 1.1.1.1 → 100%**

```
Type escape sequence to abort.
Sending 3, 100-byte ICMP Echos to 2.2.2.2, timeout is 2 seconds:
Packet sent with a source address of 1.1.1.1 
!!!
Success rate is 100 percent (3/3), round-trip min/avg/max = 1/1/1 ms
```

**P7-0 underlay RT03 Lo0→hub Lo0 — RT03# ping 2.2.2.2 repeat 3 source 3.3.3.3 → 100%**

```
Type escape sequence to abort.
Sending 3, 100-byte ICMP Echos to 2.2.2.2, timeout is 2 seconds:
Packet sent with a source address of 3.3.3.3 
!!!
Success rate is 100 percent (3/3), round-trip min/avg/max = 1/1/1 ms
```

**P7-0 underlay RT04 Lo0→hub Lo0 — RT04# ping 2.2.2.2 repeat 3 source 4.4.4.4 → 100%**

```
Type escape sequence to abort.
Sending 3, 100-byte ICMP Echos to 2.2.2.2, timeout is 2 seconds:
Packet sent with a source address of 4.4.4.4 
!!!
Success rate is 100 percent (3/3), round-trip min/avg/max = 1/1/1 ms
```

**P7-0 underlay RT01 Lo0→RT04 Lo0 — RT01# ping 4.4.4.4 repeat 3 source 1.1.1.1 → 100%**

```
Type escape sequence to abort.
Sending 3, 100-byte ICMP Echos to 4.4.4.4, timeout is 2 seconds:
Packet sent with a source address of 1.1.1.1 
!!!
Success rate is 100 percent (3/3), round-trip min/avg/max = 1/1/1 ms
```

**P7-0 crypto RT01**

```
crypto ikev2 proposal PROP-POC
encryption aes-cbc-256
integrity sha256
group 14
exit
crypto ikev2 policy POL-POC
proposal PROP-POC
exit
crypto ikev2 keyring KR-POC
peer ANY
address 0.0.0.0 0.0.0.0
pre-shared-key Ss2026#Poc
exit
exit
crypto ikev2 profile IKEV2-POC
match identity remote address 0.0.0.0
authentication remote pre-share
authentication local pre-share
keyring local KR-POC
exit
crypto ipsec transform-set TS-POC esp-aes 256 esp-sha256-hmac
mode transport
exit
crypto ipsec profile IPSEC-POC
set transform-set TS-POC
set ikev2-profile IKEV2-POC
exit
---
(応答なし)
```

**P7-0 crypto RT02**

```
crypto ikev2 proposal PROP-POC
encryption aes-cbc-256
integrity sha256
group 14
exit
crypto ikev2 policy POL-POC
proposal PROP-POC
exit
crypto ikev2 keyring KR-POC
peer ANY
address 0.0.0.0 0.0.0.0
pre-shared-key Ss2026#Poc
exit
exit
crypto ikev2 profile IKEV2-POC
match identity remote address 0.0.0.0
authentication remote pre-share
authentication local pre-share
keyring local KR-POC
exit
crypto ipsec transform-set TS-POC esp-aes 256 esp-sha256-hmac
mode transport
exit
crypto ipsec profile IPSEC-POC
set transform-set TS-POC
set ikev2-profile IKEV2-POC
exit
---
(応答なし)
```

**P7-0 crypto RT03**

```
crypto ikev2 proposal PROP-POC
encryption aes-cbc-256
integrity sha256
group 14
exit
crypto ikev2 policy POL-POC
proposal PROP-POC
exit
crypto ikev2 keyring KR-POC
peer ANY
address 0.0.0.0 0.0.0.0
pre-shared-key Ss2026#Poc
exit
exit
crypto ikev2 profile IKEV2-POC
match identity remote address 0.0.0.0
authentication remote pre-share
authentication local pre-share
keyring local KR-POC
exit
crypto ipsec transform-set TS-POC esp-aes 256 esp-sha256-hmac
mode transport
exit
crypto ipsec profile IPSEC-POC
set transform-set TS-POC
set ikev2-profile IKEV2-POC
exit
---
(応答なし)
```

**P7-0 crypto RT04**

```
crypto ikev2 proposal PROP-POC
encryption aes-cbc-256
integrity sha256
group 14
exit
crypto ikev2 policy POL-POC
proposal PROP-POC
exit
crypto ikev2 keyring KR-POC
peer ANY
address 0.0.0.0 0.0.0.0
pre-shared-key Ss2026#Poc
exit
exit
crypto ikev2 profile IKEV2-POC
match identity remote address 0.0.0.0
authentication remote pre-share
authentication local pre-share
keyring local KR-POC
exit
crypto ipsec transform-set TS-POC esp-aes 256 esp-sha256-hmac
mode transport
exit
crypto ipsec profile IPSEC-POC
set transform-set TS-POC
set ikev2-profile IKEV2-POC
exit
---
(応答なし)
```

**P7-0 hub(RT02) Tunnel0**

```
interface Tunnel0
ip address 10.255.0.2 255.255.255.0
no ip redirects
ip mtu 1400
ip tcp adjust-mss 1360
ip nhrp authentication DMVPNKEY
ip nhrp map multicast dynamic
ip nhrp network-id 1
ip nhrp redirect
no ip split-horizon eigrp 100
tunnel source Loopback0
tunnel mode gre multipoint
tunnel key 100
tunnel protection ipsec profile IPSEC-POC
exit
---
(応答なし)
```

**P7-0 spoke RT01 Tunnel0**

```
interface Tunnel0
ip address 10.255.0.1 255.255.255.0
no ip redirects
ip mtu 1400
ip tcp adjust-mss 1360
ip nhrp authentication DMVPNKEY
ip nhrp network-id 1
ip nhrp nhs 10.255.0.2 nbma 2.2.2.2 multicast
ip nhrp shortcut
tunnel source Loopback0
tunnel mode gre multipoint
tunnel key 100
tunnel protection ipsec profile IPSEC-POC
exit
---
(応答なし)
```

**P7-0 spoke RT03 Tunnel0**

```
interface Tunnel0
ip address 10.255.0.3 255.255.255.0
no ip redirects
ip mtu 1400
ip tcp adjust-mss 1360
ip nhrp authentication DMVPNKEY
ip nhrp network-id 1
ip nhrp nhs 10.255.0.2 nbma 2.2.2.2 multicast
ip nhrp shortcut
tunnel source Loopback0
tunnel mode gre multipoint
tunnel key 100
tunnel protection ipsec profile IPSEC-POC
exit
---
(応答なし)
```

**P7-0 spoke RT04 Tunnel0**

```
interface Tunnel0
ip address 10.255.0.4 255.255.255.0
no ip redirects
ip mtu 1400
ip tcp adjust-mss 1360
ip nhrp authentication DMVPNKEY
ip nhrp network-id 1
ip nhrp nhs 10.255.0.2 nbma 2.2.2.2 multicast
ip nhrp shortcut
tunnel source Loopback0
tunnel mode gre multipoint
tunnel key 100
tunnel protection ipsec profile IPSEC-POC
exit
---
(応答なし)
```

**P7a 基線 hub show dmvpn (3 UP after 0.27591419219970703s)**

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
     1 1.1.1.1              10.255.0.1    UP 00:00:08     D
     1 3.3.3.3              10.255.0.3    UP 00:00:06     D
     1 4.4.4.4              10.255.0.4    UP 00:00:03     D
```

**P7a 基線 hub**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface Tunnel0 is up/up, Addr. is 10.255.0.2, VRF "global" 
   Tunnel Src./Dest. addr: 2.2.2.2/Multipoint, Tunnel VRF "global"
   Protocol/Transport: "multi-GRE/IP", Protect "IPSEC-POC" 
   Interface State Control: Disabled
   nhrp event-publisher : Disabled
Type:Hub, Total NBMA Peers (v4/v6): 3

# Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb    Target Network
----- --------------- --------------- ----- -------- ----- -----------------
    1 1.1.1.1              10.255.0.1    UP 00:00:09     D      10.255.0.1/32
    1 3.3.3.3              10.255.0.3    UP 00:00:06     D      10.255.0.3/32
    1 4.4.4.4              10.255.0.4    UP 00:00:04     D      10.255.0.4/32


Crypto Session Details: 
--------------------------------------------------------------------------------

Interface: Tunnel0
Session: [0x76E3FA131218]
  Session ID: 1  
  IKEv2 SA: local 2.2.2.2/500 remote 1.1.1.1/500 Active 
          Capabilities:U connid:1 lifetime:23:59:51
  Crypto Session Status: UP-ACTIVE     
  fvrf: (none),	Phase1_id: 1.1.1.1
  IPSEC FLOW: permit 47   host 2.2.2.2 host 1.1.1.1 
        Active SAs: 2, origin: crypto map
        Inbound:  #pkts dec'ed 12 drop 0 life (KB/Sec) 4260376/3590
        Outbound: #pkts enc'ed 12 drop 0 life (KB/Sec) 4260376/3590
   Outbound SPI : 0xA83C94F5, transform : esp-256-aes esp-sha256-hmac 
    Socket State: Open

Interface: Tunnel0
Session: [0x76E3FA131098]
  Session ID: 2  
  IKEv2 SA: local 2.2.2.2/500 remote 3.3.3.3/500 Active 
          Capabilities:U connid:2 lifetime:23:59:54
  Crypto Session Status: UP-ACTIVE     
  fvrf: (none),	Phase1_id: 3.3.3.3
  IPSEC FLOW: permit 47   host 2.2.2.2 host 3.3.3.3 
        Active SAs: 2, origin: crypto map
        Inbound:  #pkts dec'ed 11 drop 0 life (KB/Sec) 4361698/3593
        Outbound: #pkts enc'ed 15 drop 0 life (KB/Sec) 4361697/3593
   Outbound SPI : 0xF4D3D7F6, transform : esp-256-aes esp-sha256-hmac 
    Socket State: Open

Interface: Tunnel0
Session: [0x76E3FA130F18]
  Session ID: 3  
  IKEv2 SA: local 2.2.2.2/500 remote 4.4.4.4/500 Active 
          Capabilities:U connid:3 lifetime:23:59:56
  Crypto Session Status: UP-ACTIVE     
  fvrf: (none),	Phase1_id: 4.4.4.4
  IPSEC FLOW: permit 47   host 2.2.2.2 host 4.4.4.4 
        Active SAs: 2, origin: crypto map
        Inbound:  #pkts dec'ed 4 drop 0 life (KB/Sec) 4262598/3595
        Outbound: #pkts enc'ed 10 drop 0 life (KB/Sec) 4262597/3595
   Outbound SPI : 0xF5F3E24B, transform : esp-256-aes esp-sha256-hmac 
    Socket State: Open

Pending DMVPN Sessions:
```

**P7a 基線 hub**

```
10.255.0.1/32 via 10.255.0.1
   Tunnel0 created 00:00:09, expire 00:09:50
   Type: dynamic, Flags: registered used nhop 
   NBMA address: 1.1.1.1
10.255.0.3/32 via 10.255.0.3
   Tunnel0 created 00:00:06, expire 00:09:53
   Type: dynamic, Flags: registered used nhop 
   NBMA address: 3.3.3.3
10.255.0.4/32 via 10.255.0.4
   Tunnel0 created 00:00:04, expire 00:09:55
   Type: dynamic, Flags: registered used nhop 
   NBMA address: 4.4.4.4
```

**P7a 基線 hub**

```
****************************************************************************
    NOTE: Link-Local, No-socket and Incomplete entries are not displayed
****************************************************************************
Legend: Type --> S - Static, D - Dynamic
        Flags --> u - unique, r - registered, e - temporary, c - claimed
        a - authoritative, t - route
============================================================================

Intf     NextHop Address                                    NBMA Address
         Target Network                              T/Flag
-------- ------------------------------------------- ------ ----------------
Tu0      10.255.0.1                                         1.1.1.1
         10.255.0.1/32                               D/r   
Tu0      10.255.0.3                                         3.3.3.3
         10.255.0.3/32                               D/r   
Tu0      10.255.0.4                                         4.4.4.4
         10.255.0.4/32                               D/r
```

**P7a 基線 hub**

```
10.255.0.1/32 via 10.255.0.1
   Tunnel0 created 00:00:10, expire 00:09:49
   Type: dynamic, Flags: registered used nhop 
   NBMA address: 1.1.1.1
   Preference: 255
10.255.0.3/32 via 10.255.0.3
   Tunnel0 created 00:00:07, expire 00:09:52
   Type: dynamic, Flags: registered used nhop 
   NBMA address: 3.3.3.3
   Preference: 255
10.255.0.4/32 via 10.255.0.4
   Tunnel0 created 00:00:04, expire 00:09:55
   Type: dynamic, Flags: registered used nhop 
   NBMA address: 4.4.4.4
   Preference: 255
```

**P7a 基線 hub**

```
  I/F     NBMA address  
Tunnel0    1.1.1.1         Flags: dynamic          (Enabled)
Tunnel0    3.3.3.3         Flags: dynamic          (Enabled)
Tunnel0    4.4.4.4         Flags: dynamic          (Enabled)
```

**P7a 基線 hub**

```

```

**P7a 基線 hub**

```
 IPv4 Crypto IKEv2  SA 

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
2         2.2.2.2/500           3.3.3.3/500           none/none            READY  
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/8 sec
      CE id: 1002, Session-id: 2
      Local spi: 60217463C8AD5A30       Remote spi: C5B97922AEAFB9CB

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
3         2.2.2.2/500           4.4.4.4/500           none/none            READY  
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/6 sec
      CE id: 1003, Session-id: 3
      Local spi: 6333B08CB811BE14       Remote spi: E53B70F9F9C7C789

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
1         2.2.2.2/500           1.1.1.1/500           none/none            READY  
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/11 sec
      CE id: 1001, Session-id: 1
      Local spi: 8DDBB406712409D8       Remote spi: DB35EEB4FB5DF11F

 IPv6 Crypto IKEv2  SA
```

**P7a 基線 hub**

```
   current_peer 4.4.4.4 port 500
    #pkts encaps: 16, #pkts encrypt: 16, #pkts digest: 16
    #pkts decaps: 11, #pkts decrypt: 11, #pkts verify: 11
        in use settings ={Transport, }
        in use settings ={Transport, }
   current_peer 3.3.3.3 port 500
    #pkts encaps: 17, #pkts encrypt: 17, #pkts digest: 17
    #pkts decaps: 13, #pkts decrypt: 13, #pkts verify: 13
        in use settings ={Transport, }
        in use settings ={Transport, }
   current_peer 1.1.1.1 port 500
    #pkts encaps: 14, #pkts encrypt: 14, #pkts digest: 14
    #pkts decaps: 14, #pkts decrypt: 14, #pkts verify: 14
        in use settings ={Transport, }
        in use settings ={Transport, }
```

**P7a 基線 hub**

```

Number of Crypto Socket connections 3

   Tu0 Peers (local/remote): 2.2.2.2/1.1.1.1 
       Local Ident  (addr/mask/port/prot): (2.2.2.2/255.255.255.255/0/47)
       Remote Ident (addr/mask/port/prot): (1.1.1.1/255.255.255.255/0/47)
       IPSec Profile: "IPSEC-POC"
       Socket State: Open
       Client: "TUNNEL SEC" (Client State: Active)
   Tu0 Peers (local/remote): 2.2.2.2/3.3.3.3 
       Local Ident  (addr/mask/port/prot): (2.2.2.2/255.255.255.255/0/47)
       Remote Ident (addr/mask/port/prot): (3.3.3.3/255.255.255.255/0/47)
       IPSec Profile: "IPSEC-POC"
       Socket State: Open
       Client: "TUNNEL SEC" (Client State: Active)
   Tu0 Peers (local/remote): 2.2.2.2/4.4.4.4 
       Local Ident  (addr/mask/port/prot): (2.2.2.2/255.255.255.255/0/47)
       Remote Ident (addr/mask/port/prot): (4.4.4.4/255.255.255.255/0/47)
       IPSec Profile: "IPSEC-POC"
       Socket State: Open
       Client: "TUNNEL SEC" (Client State: Active)
Crypto Sockets in Listen state:
Client: "TUNNEL SEC" Profile: "IPSEC-POC" Map-name: "Tunnel0-head-0"
```

**P7a 基線 hub**

```
Building configuration...

Current configuration : 332 bytes
!
interface Tunnel0
 ip address 10.255.0.2 255.255.255.0
 no ip redirects
 ip mtu 1400
 no ip split-horizon eigrp 100
 ip nhrp authentication DMVPNKEY
 ip nhrp network-id 1
 ip nhrp redirect
 ip tcp adjust-mss 1360
 tunnel source Loopback0
 tunnel mode gre multipoint
 tunnel key 100
 tunnel protection ipsec profile IPSEC-POC
end
```

**P7a 基線 hub**

```
EIGRP-IPv4 Neighbors for AS(100)
H   Address                 Interface              Hold Uptime   SRTT   RTO  Q  Seq
                                                   (sec)         (ms)       Cnt Num
2   10.255.0.4              Tu0                      13 00:00:03   20  1440  0  4
1   10.255.0.3              Tu0                      13 00:00:04    1  1440  0  6
0   10.255.0.1              Tu0                      13 00:00:05   14  1440  0  4
```

**P7a 基線 hub**

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

D     192.168.1.0/24 [90/27008000] via 10.255.0.1, 00:00:05, Tunnel0
D     192.168.3.0/24 [90/27008000] via 10.255.0.3, 00:00:05, Tunnel0
D     192.168.4.0/24 [90/27008000] via 10.255.0.4, 00:00:03, Tunnel0
```

**P7a 基線 hub**

```
Loopback0              2.2.2.2         YES TFTP   up                    up      
Loopback1              192.168.2.1     YES manual up                    up      
Tunnel0                10.255.0.2      YES manual up                    up
```

**P7a 基線 RT01 show ip route eigrp (192.168.4.0 after 0.30312633514404297s)**

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

Gateway of last resort is 10.0.12.2 to network 0.0.0.0

D     192.168.2.0/24 [90/27008000] via 10.255.0.2, 00:00:06, Tunnel0
D     192.168.3.0/24 [90/28288000] via 10.255.0.2, 00:00:05, Tunnel0
D     192.168.4.0/24 [90/28288000] via 10.255.0.2, 00:00:03, Tunnel0
```

**P7a 基線 RT01(shortcut 前)**

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
     1 2.2.2.2              10.255.0.2    UP 00:00:13     S
```

**P7a 基線 RT01(shortcut 前)**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface Tunnel0 is up/up, Addr. is 10.255.0.1, VRF "global" 
   Tunnel Src./Dest. addr: 1.1.1.1/Multipoint, Tunnel VRF "global"
   Protocol/Transport: "multi-GRE/IP", Protect "IPSEC-POC" 
   Interface State Control: Disabled
   nhrp event-publisher : Disabled

IPv4 NHS:
10.255.0.2  RE  NBMA Address: 2.2.2.2 priority = 0 cluster = 0
Type:Spoke, Total NBMA Peers (v4/v6): 1

# Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb    Target Network
----- --------------- --------------- ----- -------- ----- -----------------
    1 2.2.2.2              10.255.0.2    UP 00:00:13     S      10.255.0.2/32


Crypto Session Details: 
--------------------------------------------------------------------------------

Interface: Tunnel0
Session: [0x749F050C4D30]
  Session ID: 1  
  IKEv2 SA: local 1.1.1.1/500 remote 2.2.2.2/500 Active 
          Capabilities:U connid:1 lifetime:23:59:47
  Crypto Session Status: UP-ACTIVE     
  fvrf: (none),	Phase1_id: 2.2.2.2
  IPSEC FLOW: permit 47   host 1.1.1.1 host 2.2.2.2 
        Active SAs: 2, origin: crypto map
        Inbound:  #pkts dec'ed 14 drop 0 life (KB/Sec) 4258933/3586
        Outbound: #pkts enc'ed 14 drop 0 life (KB/Sec) 4258934/3586
   Outbound SPI : 0x 181C8DC, transform : esp-256-aes esp-sha256-hmac 
    Socket State: Open

Pending DMVPN Sessions:
```

**P7a 基線 RT01(shortcut 前)**

```
10.255.0.2/32 via 10.255.0.2
   Tunnel0 created 00:00:14, never expire 
   Type: static, Flags: used 
   NBMA address: 2.2.2.2
```

**P7a 基線 RT01(shortcut 前)**

```
Legend:	E=Expecting replies, R=Responding, W=Waiting, D=Dynamic
Tunnel0:
10.255.0.2  RE  NBMA Address: 2.2.2.2 priority = 0 cluster = 0  req-sent 2  req-failed 1  repl-recv 1 (00:00:14 ago)
```

**P7a 基線 RT01(shortcut 前)**

```
Legend:	E=Expecting replies, R=Responding, W=Waiting, D=Dynamic
Tunnel0:
10.255.0.2  RE  NBMA Address: 2.2.2.2 priority = 0 cluster = 0
```

**P7a 基線 RT01(shortcut 前)**

```
Building configuration...

Current configuration : 330 bytes
!
interface Tunnel0
 ip address 10.255.0.1 255.255.255.0
 no ip redirects
 ip mtu 1400
 ip nhrp authentication DMVPNKEY
 ip nhrp network-id 1
 ip nhrp nhs 10.255.0.2 nbma 2.2.2.2 multicast
 ip tcp adjust-mss 1360
 tunnel source Loopback0
 tunnel mode gre multipoint
 tunnel key 100
 tunnel protection ipsec profile IPSEC-POC
end
```

**P7a 基線 RT01(shortcut 前)**

```
EIGRP-IPv4 Neighbors for AS(100)
H   Address                 Interface              Hold Uptime   SRTT   RTO  Q  Seq
                                                   (sec)         (ms)       Cnt Num
0   10.255.0.2              Tu0                      10 00:00:08    3  1398  0  10
```

**P7a 基線 RT01(shortcut 前)**

```
Routing entry for 192.168.4.0/24
  Known via "eigrp 100", distance 90, metric 28288000, precedence routine (0), type internal
  Redistributing via eigrp 100
  Last update from 10.255.0.2 on Tunnel0, 00:00:05 ago
  Routing Descriptor Blocks:
  * 10.255.0.2, from 10.255.0.2, 00:00:05 ago, via Tunnel0
      Route metric is 28288000, traffic share count is 1
      Total delay is 105000 microseconds, minimum bandwidth is 100 Kbit
      Reliability 255/255, minimum MTU 1400 bytes
      Loading 2/255, Hops 2
```

**P7a 基線 RT01(shortcut 前)**

```

```

**P7a 基線 RT01(shortcut 前)**

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

Gateway of last resort is 10.0.12.2 to network 0.0.0.0

S*    0.0.0.0/0 [1/0] via 10.0.12.2
      1.0.0.0/32 is subnetted, 1 subnets
C        1.1.1.1 is directly connected, Loopback0
      10.0.0.0/8 is variably subnetted, 4 subnets, 2 masks
C        10.0.12.0/24 is directly connected, Ethernet0/0
L        10.0.12.1/32 is directly connected, Ethernet0/0
C        10.255.0.0/24 is directly connected, Tunnel0
L        10.255.0.1/32 is directly connected, Tunnel0
      192.168.1.0/24 is variably subnetted, 2 subnets, 2 masks
C        192.168.1.0/24 is directly connected, Loopback1
L        192.168.1.1/32 is directly connected, Loopback1
D     192.168.2.0/24 [90/27008000] via 10.255.0.2, 00:00:09, Tunnel0
D     192.168.3.0/24 [90/28288000] via 10.255.0.2, 00:00:08, Tunnel0
D     192.168.4.0/24 [90/28288000] via 10.255.0.2, 00:00:06, Tunnel0
```

**P7a 基線 RT01(shortcut 前)**

```
 IPv4 Crypto IKEv2  SA 

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
1         1.1.1.1/500           2.2.2.2/500           none/none            READY  
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/16 sec
      CE id: 1001, Session-id: 1
      Local spi: DB35EEB4FB5DF11F       Remote spi: 8DDBB406712409D8

 IPv6 Crypto IKEv2  SA
```

**P7a 基線 RT01 traceroute 192.168.4.1 (shortcut 前)**

```
Type escape sequence to abort.
Tracing the route to 192.168.4.1
VRF info: (vrf in name/id, vrf out name/id)
  1 10.255.0.2 1 msec
  2 10.255.0.4 2 msec
```

**P7a RT01 LAN→RT04 LAN (Phase3 トリガ) — RT01# ping 192.168.4.1 repeat 5 source 192.168.1.1 → 100%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 192.168.4.1, timeout is 2 seconds:
Packet sent with a source address of 192.168.1.1 
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/2 ms
```

**P7a RT01 LAN→RT04 LAN (2 回目) — RT01# ping 192.168.4.1 repeat 5 source 192.168.1.1 → 100%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 192.168.4.1, timeout is 2 seconds:
Packet sent with a source address of 192.168.1.1 
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/3 ms
```

**P7a RT01 traceroute 192.168.4.1 (shortcut 後)**

```
Type escape sequence to abort.
Tracing the route to 192.168.4.1
VRF info: (vrf in name/id, vrf out name/id)
  1 10.255.0.4 2 msec
```

**P7a RT01(shortcut 後)**

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
     1 2.2.2.2              10.255.0.2    UP 00:00:26     S
     2 4.4.4.4              10.255.0.4    UP 00:00:09   DT1
                            10.255.0.4    UP 00:00:09   DT2
```

**P7a RT01(shortcut 後)**

```
Legend: Attrb --> S - Static, D - Dynamic, I - Incomplete
	N - NATed, L - Local, X - No Socket
	T1 - Route Installed, T2 - Nexthop-override, B - BGP
	C - CTS Capable, I2 - Temporary
	# Ent --> Number of NHRP entries with same NBMA peer
	NHS Status: E --> Expecting Replies, R --> Responding, W --> Waiting
	UpDn Time --> Up or Down Time for a Tunnel
==========================================================================

Interface Tunnel0 is up/up, Addr. is 10.255.0.1, VRF "global" 
   Tunnel Src./Dest. addr: 1.1.1.1/Multipoint, Tunnel VRF "global"
   Protocol/Transport: "multi-GRE/IP", Protect "IPSEC-POC" 
   Interface State Control: Disabled
   nhrp event-publisher : Disabled

IPv4 NHS:
10.255.0.2  RE  NBMA Address: 2.2.2.2 priority = 0 cluster = 0
Type:Spoke, Total NBMA Peers (v4/v6): 3

# Ent  Peer NBMA Addr Peer Tunnel Add State  UpDn Tm Attrb    Target Network
----- --------------- --------------- ----- -------- ----- -----------------
    1 2.2.2.2              10.255.0.2    UP 00:00:26     S      10.255.0.2/32
    2 4.4.4.4              10.255.0.4    UP 00:00:09   DT1      10.255.0.4/32
      4.4.4.4              10.255.0.4    UP 00:00:09   DT2     192.168.4.0/24
    1 1.1.1.1              10.255.0.1   IKE 00:00:09   DLX     192.168.1.0/24


Crypto Session Details: 
--------------------------------------------------------------------------------

Interface: Tunnel0
Session: [0x749F050C4D30]
  Session ID: 1  
  IKEv2 SA: local 1.1.1.1/500 remote 2.2.2.2/500 Active 
          Capabilities:U connid:1 lifetime:23:59:34
  Crypto Session Status: UP-ACTIVE     
  fvrf: (none),	Phase1_id: 2.2.2.2
  IPSEC FLOW: permit 47   host 1.1.1.1 host 2.2.2.2 
        Active SAs: 2, origin: crypto map
        Inbound:  #pkts dec'ed 21 drop 0 life (KB/Sec) 4258932/3573
        Outbound: #pkts enc'ed 20 drop 0 life (KB/Sec) 4258933/3573
   Outbound SPI : 0x 181C8DC, transform : esp-256-aes esp-sha256-hmac 
    Socket State: Open

Interface: Tunnel0
Session: [0x749F050C4BB0]
  Session ID: 3  
  IKEv2 SA: local 1.1.1.1/500 remote 4.4.4.4/500 Active 
          Capabilities:U connid:3 lifetime:23:59:50
  Crypto Session Status: UP-ACTIVE     
  fvrf: (none),	Phase1_id: 4.4.4.4
  IPSEC FLOW: permit 47   host 1.1.1.1 host 4.4.4.4 
        Active SAs: 2, origin: crypto map
        Inbound:  #pkts dec'ed 12 drop 0 life (KB/Sec) 4292845/3590
        Outbound: #pkts enc'ed 12 drop 0 life (KB/Sec) 4292845/3590
   Outbound SPI : 0x4E04F46F, transform : esp-256-aes esp-sha256-hmac 
    Socket State: Open

Pending DMVPN Sessions:
```

**P7a RT01(shortcut 後)**

```
10.255.0.2/32 via 10.255.0.2
   Tunnel0 created 00:00:27, never expire 
   Type: static, Flags: used 
   NBMA address: 2.2.2.2
10.255.0.4/32 via 10.255.0.4
   Tunnel0 created 00:00:09, expire 00:09:50
   Type: dynamic, Flags: router nhop rib 
   NBMA address: 4.4.4.4
192.168.4.0/24 via 10.255.0.4
   Tunnel0 created 00:00:09, expire 00:09:50
   Type: dynamic, Flags: router used rib nho 
   NBMA address: 4.4.4.4
192.168.1.0/24 via 10.255.0.1
   Tunnel0 created 00:00:09, expire 00:09:50
   Type: dynamic, Flags: router unique local 
   NBMA address: 1.1.1.1
    (no-socket)
```

**P7a RT01(shortcut 後)**

```
10.255.0.2/32 via 10.255.0.2
   Tunnel0 created 00:00:27, never expire 
   Type: static, Flags: used 
   NBMA address: 2.2.2.2
   Preference: 255
10.255.0.4/32 via 10.255.0.4
   Tunnel0 created 00:00:10, expire 00:09:49
   Type: dynamic, Flags: router nhop rib 
   NBMA address: 4.4.4.4
   Preference: 255
192.168.4.0/24 via 10.255.0.4
   Tunnel0 created 00:00:10, expire 00:09:49
   Type: dynamic, Flags: router used rib nho 
   NBMA address: 4.4.4.4
   Preference: 255
192.168.1.0/24 via 10.255.0.1
   Tunnel0 created 00:00:10, expire 00:09:49
   Type: dynamic, Flags: router unique local 
   NBMA address: 1.1.1.1
   Preference: 255
    (no-socket) 
  Requester: 10.255.0.4 Request ID: 2
```

**P7a RT01(shortcut 後)**

```
10.255.0.4/32 via 10.255.0.4
   Tunnel0 created 00:00:10, expire 00:09:49
   Type: dynamic, Flags: router nhop rib 
   NBMA address: 4.4.4.4
192.168.4.0/24 via 10.255.0.4
   Tunnel0 created 00:00:10, expire 00:09:49
   Type: dynamic, Flags: router used rib nho 
   NBMA address: 4.4.4.4
```

**P7a RT01(shortcut 後)**

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

Gateway of last resort is 10.0.12.2 to network 0.0.0.0

S*    0.0.0.0/0 [1/0] via 10.0.12.2
      1.0.0.0/32 is subnetted, 1 subnets
C        1.1.1.1 is directly connected, Loopback0
      10.0.0.0/8 is variably subnetted, 5 subnets, 2 masks
C        10.0.12.0/24 is directly connected, Ethernet0/0
L        10.0.12.1/32 is directly connected, Ethernet0/0
C        10.255.0.0/24 is directly connected, Tunnel0
L        10.255.0.1/32 is directly connected, Tunnel0
H        10.255.0.4/32 is directly connected, 00:00:11, Tunnel0
      192.168.1.0/24 is variably subnetted, 2 subnets, 2 masks
C        192.168.1.0/24 is directly connected, Loopback1
L        192.168.1.1/32 is directly connected, Loopback1
D     192.168.2.0/24 [90/27008000] via 10.255.0.2, 00:00:21, Tunnel0
D     192.168.3.0/24 [90/28288000] via 10.255.0.2, 00:00:20, Tunnel0
D   % 192.168.4.0/24 [90/28288000] via 10.255.0.2, 00:00:18, Tunnel0
                     [NHO][90/255] via 10.255.0.4, 00:00:11, Tunnel0
```

**P7a RT01(shortcut 後)**

```
Routing entry for 192.168.4.0/24
  Known via "eigrp 100", distance 90, metric 28288000, precedence routine (0), type internal
  Redistributing via eigrp 100
  Last update from 10.255.0.2 on Tunnel0, 00:00:18 ago
  Routing Descriptor Blocks:
  * 10.255.0.2, from 10.255.0.2, 00:00:18 ago, via Tunnel0
      Route metric is 28288000, traffic share count is 1
      Total delay is 105000 microseconds, minimum bandwidth is 100 Kbit
      Reliability 255/255, minimum MTU 1400 bytes
      Loading 2/255, Hops 2
```

**P7a RT01(shortcut 後)**

```
192.168.4.0/24
  nexthop 10.255.0.4 Tunnel0
```

**P7a RT01(shortcut 後)**

```
 IPv4 Crypto IKEv2  SA 

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
3         1.1.1.1/500           4.4.4.4/500           none/none            READY  
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/12 sec
      CE id: 1002, Session-id: 2
      Local spi: 7F9B031B3E80C448       Remote spi: C3773529A56A6E7A

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
1         1.1.1.1/500           2.2.2.2/500           none/none            READY  
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/28 sec
      CE id: 1001, Session-id: 1
      Local spi: DB35EEB4FB5DF11F       Remote spi: 8DDBB406712409D8

 IPv6 Crypto IKEv2  SA
```

**P7a RT01(shortcut 後)**

```
   current_peer 4.4.4.4 port 500
    #pkts encaps: 12, #pkts encrypt: 12, #pkts digest: 12
    #pkts decaps: 12, #pkts decrypt: 12, #pkts verify: 12
        in use settings ={Transport, }
        in use settings ={Transport, }
   current_peer 2.2.2.2 port 500
    #pkts encaps: 20, #pkts encrypt: 20, #pkts digest: 20
    #pkts decaps: 21, #pkts decrypt: 21, #pkts verify: 21
        in use settings ={Transport, }
        in use settings ={Transport, }
```

**P7a RT01(shortcut 後)**

```
Tunnel0: Max-send limit:10000Pkts/10Sec, Usage:0%
   Sent: Total 4
         1 Resolution Request  1 Resolution Reply  2 Registration Request  
         0 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress  
   Rcvd: Total 4
         1 Resolution Request  1 Resolution Reply  0 Registration Request  
         1 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  1 Traffic Indication  0 Redirect Suppress
```

**P7a RT04(shortcut 後)**

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
     2 1.1.1.1              10.255.0.1    UP 00:00:12   DT1
                            10.255.0.1    UP 00:00:12   DT2
     1 2.2.2.2              10.255.0.2    UP 00:00:24     S
```

**P7a RT04(shortcut 後)**

```
10.255.0.1/32 via 10.255.0.1
   Tunnel0 created 00:00:13, expire 00:09:46
   Type: dynamic, Flags: router nhop rib 
   NBMA address: 1.1.1.1
10.255.0.2/32 via 10.255.0.2
   Tunnel0 created 00:00:24, never expire 
   Type: static, Flags: used 
   NBMA address: 2.2.2.2
192.168.1.0/24 via 10.255.0.1
   Tunnel0 created 00:00:13, expire 00:09:46
   Type: dynamic, Flags: router used rib nho 
   NBMA address: 1.1.1.1
192.168.4.0/24 via 10.255.0.4
   Tunnel0 created 00:00:13, expire 00:09:46
   Type: dynamic, Flags: router unique local 
   NBMA address: 4.4.4.4
    (no-socket)
```

**P7a RT04(shortcut 後)**

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

Gateway of last resort is 10.0.34.3 to network 0.0.0.0

S*    0.0.0.0/0 [1/0] via 10.0.34.3
      4.0.0.0/32 is subnetted, 1 subnets
C        4.4.4.4 is directly connected, Loopback0
      10.0.0.0/8 is variably subnetted, 5 subnets, 2 masks
C        10.0.34.0/24 is directly connected, Ethernet0/0
L        10.0.34.4/32 is directly connected, Ethernet0/0
C        10.255.0.0/24 is directly connected, Tunnel0
H        10.255.0.1/32 is directly connected, 00:00:14, Tunnel0
L        10.255.0.4/32 is directly connected, Tunnel0
D   % 192.168.1.0/24 [90/28288000] via 10.255.0.2, 00:00:20, Tunnel0
                     [NHO][90/255] via 10.255.0.1, 00:00:14, Tunnel0
D     192.168.2.0/24 [90/27008000] via 10.255.0.2, 00:00:20, Tunnel0
D     192.168.3.0/24 [90/28288000] via 10.255.0.2, 00:00:20, Tunnel0
      192.168.4.0/24 is variably subnetted, 2 subnets, 2 masks
C        192.168.4.0/24 is directly connected, Loopback1
L        192.168.4.1/32 is directly connected, Loopback1
```

**P7a hub(shortcut 後)**

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
     1 1.1.1.1              10.255.0.1    UP 00:00:30     D
     1 3.3.3.3              10.255.0.3    UP 00:00:27     D
     1 4.4.4.4              10.255.0.4    UP 00:00:25     D
```

**P7a hub(shortcut 後)**

```
10.255.0.1/32 via 10.255.0.1
   Tunnel0 created 00:00:30, expire 00:09:29
   Type: dynamic, Flags: registered used nhop 
   NBMA address: 1.1.1.1
10.255.0.3/32 via 10.255.0.3
   Tunnel0 created 00:00:28, expire 00:09:31
   Type: dynamic, Flags: registered used nhop 
   NBMA address: 3.3.3.3
10.255.0.4/32 via 10.255.0.4
   Tunnel0 created 00:00:25, expire 00:09:34
   Type: dynamic, Flags: registered used nhop 
   NBMA address: 4.4.4.4
```

**P7a hub(shortcut 後)**

```
Tunnel0: Max-send limit:10000Pkts/10Sec, Usage:0%
   Sent: Total 7
         2 Resolution Request  0 Resolution Reply  0 Registration Request  
         3 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  2 Traffic Indication  0 Redirect Suppress  
   Rcvd: Total 5
         2 Resolution Request  0 Resolution Reply  3 Registration Request  
         0 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress
```

**P7b network-id 不一致(RT03=99・他=1) 注入(RT03)**

```
interface Tunnel0
ip nhrp network-id 99
exit
---
(応答なし)
```

**P7b network-id 不一致(RT03=99・他=1) — hub**

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
     1 1.1.1.1              10.255.0.1    UP 00:01:39     D
     1 3.3.3.3              10.255.0.3    UP 00:00:59     D
     1 4.4.4.4              10.255.0.4    UP 00:01:34     D
```

**P7b network-id 不一致(RT03=99・他=1) — hub**

```
10.255.0.1/32 via 10.255.0.1
   Tunnel0 created 00:01:40, expire 00:08:19
   Type: dynamic, Flags: registered used nhop 
   NBMA address: 1.1.1.1
10.255.0.3/32 via 10.255.0.3
   Tunnel0 created 00:00:59, expire 00:09:01
   Type: dynamic, Flags: registered used nhop 
   NBMA address: 3.3.3.3
10.255.0.4/32 via 10.255.0.4
   Tunnel0 created 00:01:34, expire 00:08:25
   Type: dynamic, Flags: registered used nhop 
   NBMA address: 4.4.4.4
```

**P7b network-id 不一致(RT03=99・他=1) — hub**

```
 IPv4 Crypto IKEv2  SA 

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
3         2.2.2.2/500           4.4.4.4/500           none/none            READY  
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/95 sec
      CE id: 1003, Session-id: 3
      Local spi: 6333B08CB811BE14       Remote spi: E53B70F9F9C7C789

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
2         2.2.2.2/500           3.3.3.3/500           none/none            READY  
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/61 sec
      CE id: 1004, Session-id: 4
      Local spi: 664DF2EE125EF36C       Remote spi: 07DE378D7BD8F220

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
1         2.2.2.2/500           1.1.1.1/500           none/none            READY  
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/100 sec
      CE id: 1001, Session-id: 1
      Local spi: 8DDBB406712409D8       Remote spi: DB35EEB4FB5DF11F

 IPv6 Crypto IKEv2  SA
```

**P7b network-id 不一致(RT03=99・他=1) — hub**

```
EIGRP-IPv4 Neighbors for AS(100)
H   Address                 Interface              Hold Uptime   SRTT   RTO  Q  Seq
                                                   (sec)         (ms)       Cnt Num
1   10.255.0.3              Tu0                      14 00:00:52   61  1440  0  9
2   10.255.0.4              Tu0                      13 00:01:32   12  1440  0  6
0   10.255.0.1              Tu0                      14 00:01:33    8  1440  0  6
```

**P7b network-id 不一致(RT03=99・他=1) — RT03**

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
     1 2.2.2.2              10.255.0.2    UP 00:01:00     S
```

**P7b network-id 不一致(RT03=99・他=1) — RT03**

```
10.255.0.2/32 via 10.255.0.2
   Tunnel0 created 00:01:02, never expire 
   Type: static, Flags: used 
   NBMA address: 2.2.2.2
```

**P7b network-id 不一致(RT03=99・他=1) — RT03**

```
Legend:	E=Expecting replies, R=Responding, W=Waiting, D=Dynamic
Tunnel0:
10.255.0.2  RE  NBMA Address: 2.2.2.2 priority = 0 cluster = 0  req-sent 1  req-failed 0  repl-recv 1 (00:01:00 ago)
```

**P7b network-id 不一致(RT03=99・他=1) — RT03**

```
 IPv4 Crypto IKEv2  SA 

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
2         3.3.3.3/500           2.2.2.2/500           none/none            READY  
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/63 sec
      CE id: 1002, Session-id: 1
      Local spi: 07DE378D7BD8F220       Remote spi: 664DF2EE125EF36C

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
1         3.3.3.3/500           2.2.2.2/500           none/none            DELETE 
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/99 sec
      CE id: 1001, Session-id: 1
      Local spi: C5B97922AEAFB9CB       Remote spi: 60217463C8AD5A30

 IPv6 Crypto IKEv2  SA
```

**P7b network-id 不一致(RT03=99・他=1) — RT03**

```
   current_peer 2.2.2.2 port 500
    #pkts encaps: 23, #pkts encrypt: 23, #pkts digest: 23
    #pkts decaps: 22, #pkts decrypt: 22, #pkts verify: 22
```

**P7b network-id 不一致(RT03=99・他=1) — RT03**

```
EIGRP-IPv4 Neighbors for AS(100)
H   Address                 Interface              Hold Uptime   SRTT   RTO  Q  Seq
                                                   (sec)         (ms)       Cnt Num
0   10.255.0.2              Tu0                      11 00:00:58   11  1398  0  14
```

**P7b network-id 不一致(RT03=99・他=1) — RT03**

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

D     192.168.1.0/24 [90/28288000] via 10.255.0.2, 00:00:54, Tunnel0
D     192.168.2.0/24 [90/27008000] via 10.255.0.2, 00:00:54, Tunnel0
D     192.168.4.0/24 [90/28288000] via 10.255.0.2, 00:00:54, Tunnel0
```

**P7b network-id 不一致(RT03=99・他=1) — RT03**

```
Tunnel0: Max-send limit:10000Pkts/10Sec, Usage:0%
   Sent: Total 6
         0 Resolution Request  0 Resolution Reply  6 Registration Request  
         0 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress  
   Rcvd: Total 5
         0 Resolution Request  0 Resolution Reply  0 Registration Request  
         5 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress
```

**P7b network-id 不一致(RT03=99・他=1) — RT03**

```
Tunnel0 is up, line protocol is up 
  Hardware is Tunnel
  Tunnel linestate evaluation up
  Tunnel source 3.3.3.3 (Loopback0)
   Tunnel Subblocks:
         Tunnel0 source tracking subblock associated with Loopback0
  Tunnel protocol/transport multi-GRE/IP
    Checksumming of packets disabled
  Tunnel TTL 255, Fast tunneling enabled
  Tunnel transport MTU 1472 bytes
  Tunnel transmit bandwidth 8000 (kbps)
  Tunnel receive bandwidth 8000 (kbps)
  Tunnel protection via IPSec (profile "IPSEC-POC")
  Tunnel state info: 
  5 minute input rate 0 bits/sec, 0 packets/sec
  5 minute output rate 0 bits/sec, 0 packets/sec
     45 packets input, 4652 bytes, 0 no buffer
     70 packets output, 6172 bytes, 0 underruns
```

**P7b network-id 不一致(RT03=99・他=1) — RT03**

```
   Tunnel0 created 00:01:04, never expire
```

**P7b network-id 不一致(RT03=99・他=1) — RT03**

```
Building configuration...

Current configuration : 331 bytes
!
interface Tunnel0
 ip address 10.255.0.3 255.255.255.0
 no ip redirects
 ip mtu 1400
 ip nhrp authentication DMVPNKEY
 ip nhrp network-id 99
 ip nhrp nhs 10.255.0.2 nbma 2.2.2.2 multicast
 ip tcp adjust-mss 1360
 tunnel source Loopback0
 tunnel mode gre multipoint
 tunnel key 100
 tunnel protection ipsec profile IPSEC-POC
end
```

**P7b network-id 不一致(RT03=99・他=1) ping RT03 LAN→hub LAN — RT03# ping 192.168.2.1 repeat 3 source 192.168.3.1 → 100%**

```
Type escape sequence to abort.
Sending 3, 100-byte ICMP Echos to 192.168.2.1, timeout is 2 seconds:
Packet sent with a source address of 192.168.3.1 
!!!
Success rate is 100 percent (3/3), round-trip min/avg/max = 1/1/2 ms
```

**P7b network-id 不一致(RT03=99・他=1) ping RT03 LAN→RT01 LAN(spoke間) — RT03# ping 192.168.1.1 repeat 5 source 192.168.3.1 → 100%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 192.168.1.1, timeout is 2 seconds:
Packet sent with a source address of 192.168.3.1 
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/2 ms
```

**P7b network-id 不一致(RT03=99・他=1) — RT03 show dmvpn (spoke間 ping 後)**

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
     2 1.1.1.1              10.255.0.1    UP 00:00:00   DT1
                            10.255.0.1    UP 00:00:00   DT2
     1 2.2.2.2              10.255.0.2    UP 00:01:04     S
```

**P7b network-id 不一致(RT03=99・他=1) hub — RT02 show logging**

```
*Sep 18 15:38:36.810: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 3.3.3.3 socket is DOWN
*Sep 18 15:38:36.811: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 10.255.0.3 NBMA: 3.3.3.3 ) for (Tunnel: 10.255.0.2 NBMA: 2.2.2.2) is DOWN, Reason: External(NHRP: no error)
*Sep 18 15:38:40.447: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 3.3.3.3 socket is UP
*Sep 18 15:38:41.412: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 10.255.0.3 NBMA: 3.3.3.3) for (Tunnel: 10.255.0.2 NBMA: 2.2.2.2) is UP
*Sep 18 15:38:44.805: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.255.0.3 (Tunnel0) is down: peer restarted
*Sep 18 15:38:49.717: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.255.0.3 (Tunnel0) is up: new adjacency
```

**P7b network-id 不一致(RT03=99・他=1) RT03 — RT03 show logging**

```
*Sep 18 15:38:36.801: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 10.255.0.2 NBMA: 2.2.2.2 ) for (Tunnel: 10.255.0.3 NBMA: 3.3.3.3) is DOWN, Reason: External(NHRP: no error)
*Sep 18 15:38:36.802: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 3.3.3.3 remote address : 2.2.2.2 socket is DOWN
*Sep 18 15:38:36.802: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.255.0.2 (Tunnel0) is down: interface down
*Sep 18 15:38:36.810: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 18 15:38:40.438: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 18 15:38:40.447: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 3.3.3.3 remote address : 2.2.2.2 socket is UP
*Sep 18 15:38:41.411: NHRP-RATE: Sent one-time Registration Request for 10.255.0.2, reqid 5
*Sep 18 15:38:41.412: %DMVPN-5-NHRP_NHS_UP: Tunnel0: Next Hop Server : (Tunnel: 10.255.0.2 NBMA: 2.2.2.2) for (Tunnel: 10.255.0.3 NBMA: 3.3.3.3) is  UP
*Sep 18 15:38:44.802: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.255.0.2 (Tunnel0) is up: new adjacency
*Sep 18 15:39:45.804: NHRP-RATE: Sending initial Resolution Request for 192.168.1.1, reqid 2
*Sep 18 15:39:45.815: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 3.3.3.3 remote address : 1.1.1.1 socket is UP
*Sep 18 15:39:45.816: %DMVPN-5-NHRP_NHP_UP: Tunnel0: Next Hop NHP : (Tunnel: 10.255.0.1 NBMA: 1.1.1.1) for (Tunnel: 10.255.0.3 NBMA: 3.3.3.3) is UP
```

**P7b network-id 不一致(RT03=99・他=1) 復旧(RT03)**

```
interface Tunnel0
ip nhrp network-id 1
exit
---
(応答なし)
```

- P7b network-id 不一致(RT03=99・他=1) 復旧後 RT03 UP= 15.702147960662842s

**P7c NHRP authentication 不一致(RT03=WRONGKY1) 注入(RT03)**

```
interface Tunnel0
ip nhrp authentication WRONGKY1
exit
---
(応答なし)
```

**P7c NHRP authentication 不一致(RT03=WRONGKY1) — hub**

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
     1 1.1.1.1              10.255.0.1    UP 00:03:13     D
     1 4.4.4.4              10.255.0.4    UP 00:03:08     D
```

**P7c NHRP authentication 不一致(RT03=WRONGKY1) — hub**

```
10.255.0.1/32 via 10.255.0.1
   Tunnel0 created 00:03:13, expire 00:06:46
   Type: dynamic, Flags: registered used nhop 
   NBMA address: 1.1.1.1
10.255.0.4/32 via 10.255.0.4
   Tunnel0 created 00:03:08, expire 00:06:51
   Type: dynamic, Flags: registered used nhop 
   NBMA address: 4.4.4.4
```

**P7c NHRP authentication 不一致(RT03=WRONGKY1) — hub**

```
 IPv4 Crypto IKEv2  SA 

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
3         2.2.2.2/500           4.4.4.4/500           none/none            READY  
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/189 sec
      CE id: 1003, Session-id: 3
      Local spi: 6333B08CB811BE14       Remote spi: E53B70F9F9C7C789

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
1         2.2.2.2/500           1.1.1.1/500           none/none            READY  
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/194 sec
      CE id: 1001, Session-id: 1
      Local spi: 8DDBB406712409D8       Remote spi: DB35EEB4FB5DF11F

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
2         2.2.2.2/500           3.3.3.3/500           none/none            READY  
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/61 sec
      CE id: 1006, Session-id: 6
      Local spi: F319BF25DA9056CD       Remote spi: DEC88DB135C9519B

 IPv6 Crypto IKEv2  SA
```

**P7c NHRP authentication 不一致(RT03=WRONGKY1) — hub**

```
EIGRP-IPv4 Neighbors for AS(100)
H   Address                 Interface              Hold Uptime   SRTT   RTO  Q  Seq
                                                   (sec)         (ms)       Cnt Num
1   10.255.0.3              Tu0                      13 00:01:12  448  2688  0  12
2   10.255.0.4              Tu0                      12 00:03:06    7  1440  0  8
0   10.255.0.1              Tu0                      11 00:03:07    4  1440  0  8
```

**P7c NHRP authentication 不一致(RT03=WRONGKY1) — RT03**

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
     1 2.2.2.2              10.255.0.2  NHRP 00:00:53     S
```

**P7c NHRP authentication 不一致(RT03=WRONGKY1) — RT03**

```
10.255.0.2/32 via 10.255.0.2
   Tunnel0 created 00:01:01, never expire 
   Type: static, Flags: 
   NBMA address: 2.2.2.2
```

**P7c NHRP authentication 不一致(RT03=WRONGKY1) — RT03**

```
Legend:	E=Expecting replies, R=Responding, W=Waiting, D=Dynamic
Tunnel0:
10.255.0.2   E  NBMA Address: 2.2.2.2 priority = 0 cluster = 0  req-sent 6  req-failed 0  repl-recv 0 (00:01:22 ago)


Pending Registration Requests:
Registration Request: Reqid 14, Ret 64  NHS 10.255.0.2 expired (Tu0)
```

**P7c NHRP authentication 不一致(RT03=WRONGKY1) — RT03**

```
 IPv4 Crypto IKEv2  SA 

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
2         3.3.3.3/500           2.2.2.2/500           none/none            DELETE 
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/156 sec
      CE id: 1002, Session-id: 1
      Local spi: 07DE378D7BD8F220       Remote spi: 664DF2EE125EF36C

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
3         3.3.3.3/500           2.2.2.2/500           none/none            DELETE 
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/84 sec
      CE id: 1005, Session-id: 1
      Local spi: 47DA2338F78A8ED7       Remote spi: 097525F15A75E659

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
5         3.3.3.3/500           2.2.2.2/500           none/none            READY  
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/62 sec
      CE id: 1006, Session-id: 1
      Local spi: DEC88DB135C9519B       Remote spi: F319BF25DA9056CD

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
4         3.3.3.3/500           1.1.1.1/500           none/none            DELETE 
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/91 sec
      CE id: 1003, Session-id: 2
      Local spi: F1DE73071F7F0630       Remote spi: 4B10DD1988110575

 IPv6 Crypto IKEv2  SA
```

**P7c NHRP authentication 不一致(RT03=WRONGKY1) — RT03**

```
   current_peer 2.2.2.2 port 500
    #pkts encaps: 22, #pkts encrypt: 22, #pkts digest: 22
    #pkts decaps: 0, #pkts decrypt: 0, #pkts verify: 0
```

**P7c NHRP authentication 不一致(RT03=WRONGKY1) — RT03**

```
EIGRP-IPv4 Neighbors for AS(100)
```

**P7c NHRP authentication 不一致(RT03=WRONGKY1) — RT03**

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
```

**P7c NHRP authentication 不一致(RT03=WRONGKY1) — RT03**

```
Tunnel0: Max-send limit:10000Pkts/10Sec, Usage:0%
   Sent: Total 22
         1 Resolution Request  2 Resolution Reply  19 Registration Request  
         0 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress  
   Rcvd: Total 13
         2 Resolution Request  1 Resolution Reply  0 Registration Request  
         9 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  1 Traffic Indication  0 Redirect Suppress
```

**P7c NHRP authentication 不一致(RT03=WRONGKY1) — RT03**

```
Tunnel0 is up, line protocol is up 
  Hardware is Tunnel
  Tunnel linestate evaluation up
  Tunnel source 3.3.3.3 (Loopback0)
   Tunnel Subblocks:
         Tunnel0 source tracking subblock associated with Loopback0
  Tunnel protocol/transport multi-GRE/IP
    Checksumming of packets disabled
  Tunnel TTL 255, Fast tunneling enabled
  Tunnel transport MTU 1472 bytes
  Tunnel transmit bandwidth 8000 (kbps)
  Tunnel receive bandwidth 8000 (kbps)
  Tunnel protection via IPSec (profile "IPSEC-POC")
  Tunnel state info: 
  5 minute input rate 0 bits/sec, 0 packets/sec
  5 minute output rate 0 bits/sec, 0 packets/sec
     71 packets input, 7908 bytes, 0 no buffer
     141 packets output, 13268 bytes, 0 underruns
```

**P7c NHRP authentication 不一致(RT03=WRONGKY1) ping RT03 LAN→hub LAN — RT03# ping 192.168.2.1 repeat 3 source 192.168.3.1 → 0%**

```
Type escape sequence to abort.
Sending 3, 100-byte ICMP Echos to 192.168.2.1, timeout is 2 seconds:
Packet sent with a source address of 192.168.3.1 
...
Success rate is 0 percent (0/3)
```

**P7c NHRP authentication 不一致(RT03=WRONGKY1) ping RT03 LAN→RT01 LAN(spoke間) — RT03# ping 192.168.1.1 repeat 5 source 192.168.3.1 → 0%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 192.168.1.1, timeout is 2 seconds:
Packet sent with a source address of 192.168.3.1 
.....
Success rate is 0 percent (0/5)
```

**P7c NHRP authentication 不一致(RT03=WRONGKY1) — RT03 show dmvpn (spoke間 ping 後)**

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
     1 2.2.2.2              10.255.0.2  NHRP 00:01:13     S
```

**P7c NHRP authentication 不一致(RT03=WRONGKY1) hub — RT02 show logging**

```
*Sep 18 15:40:10.475: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 3.3.3.3 socket is DOWN
*Sep 18 15:40:10.481: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 10.255.0.3 NBMA: 3.3.3.3 ) for (Tunnel: 10.255.0.2 NBMA: 2.2.2.2) is DOWN, Reason: External(NHRP: no error)
*Sep 18 15:40:14.112: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 3.3.3.3 socket is UP
*Sep 18 15:40:15.014: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: Recieved wrong authentication string for  Registration Request , Reason:  authentication failure (11) on (Tunnel: 10.255.0.3 NBMA: 2.2.2.2)
*Sep 18 15:40:15.103: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: Recieved wrong authentication string for  Registration Request , Reason:  authentication failure (11) on (Tunnel: 10.255.0.3 NBMA: 2.2.2.2)
*Sep 18 15:40:15.924: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: Recieved wrong authentication string for  Registration Request , Reason:  authentication failure (11) on (Tunnel: 10.255.0.3 NBMA: 2.2.2.2)
*Sep 18 15:40:16.104: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: Recieved wrong authentication string for  Registration Request , Reason:  authentication failure (11) on (Tunnel: 10.255.0.3 NBMA: 2.2.2.2)
*Sep 18 15:40:18.017: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: Recieved wrong authentication string for  Registration Request , Reason:  authentication failure (11) on (Tunnel: 10.255.0.3 NBMA: 2.2.2.2)
*Sep 18 15:40:21.751: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: Recieved wrong authentication string for  Registration Request , Reason:  authentication failure (11) on (Tunnel: 10.255.0.3 NBMA: 2.2.2.2)
*Sep 18 15:40:28.262: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: Recieved wrong authentication string for  Registration Request , Reason:  authentication failure (11) on (Tunnel: 10.255.0.3 NBMA: 2.2.2.2)
*Sep 18 15:40:41.927: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: Recieved wrong authentication string for  Registration Request , Reason:  authentication failure (11) on (Tunnel: 10.255.0.3 NBMA: 2.2.2.2)
*Sep 18 15:41:06.078: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: Recieved wrong authentication string for  Registration Request , Reason:  authentication failure (11) on (Tunnel: 10.255.0.3 NBMA: 2.2.2.2)
```

**P7c NHRP authentication 不一致(RT03=WRONGKY1) RT03 — RT03 show logging**

```
*Sep 18 15:40:10.472: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 10.255.0.2 NBMA: 2.2.2.2 ) for (Tunnel: 10.255.0.3 NBMA: 3.3.3.3) is DOWN, Reason: External(NHRP: no error)
*Sep 18 15:40:10.472: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 3.3.3.3 remote address : 2.2.2.2 socket is DOWN
*Sep 18 15:40:10.473: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.255.0.2 (Tunnel0) is down: interface down
*Sep 18 15:40:10.474: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 18 15:40:14.103: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 18 15:40:14.113: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 3.3.3.3 remote address : 2.2.2.2 socket is UP
*Sep 18 15:40:15.014: NHRP-RATE: Sent one-time Registration Request for 10.255.0.2, reqid 12
*Sep 18 15:40:15.923: NHRP-RATE: Sending initial Registration Request for 10.255.0.2, reqid 13
*Sep 18 15:40:18.016: NHRP-RATE: Retransmitting Registration Request for 10.255.0.2, reqid 14, (retrans ivl 4 sec)
*Sep 18 15:40:21.751: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 10.255.0.2 NBMA: 2.2.2.2 ) for (Tunnel: 10.255.0.3 NBMA: 3.3.3.3) is DOWN, Reason: NHRP Registration Failure(NHRP: no error)
*Sep 18 15:40:21.751: NHRP-RATE: Retransmitting Registration Request for 10.255.0.2, reqid 14, (retrans ivl 8 sec)
*Sep 18 15:40:28.262: NHRP-RATE: Retransmitting Registration Request for 10.255.0.2, reqid 14, (retrans ivl 16 sec)
*Sep 18 15:40:41.927: NHRP-RATE: Retransmitting Registration Request for 10.255.0.2, reqid 14, (retrans ivl 32 sec)
*Sep 18 15:41:06.078: NHRP-RATE: Retransmitting Registration Request for 10.255.0.2, reqid 14, (retrans ivl 64 sec)
```

**P7c NHRP authentication 不一致(RT03=WRONGKY1) 復旧(RT03)**

```
interface Tunnel0
ip nhrp authentication DMVPNKEY
exit
---
(応答なし)
```

- P7c NHRP authentication 不一致(RT03=WRONGKY1) 復旧後 RT03 UP= 15.62475299835205s

**P7d tunnel key 不一致(RT03=101・他=100) 注入(RT03)**

```
interface Tunnel0
tunnel key 101
exit
---
(応答なし)
```

**P7d tunnel key 不一致(RT03=101・他=100) — hub**

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
     1 1.1.1.1              10.255.0.1    UP 00:05:03     D
     1 4.4.4.4              10.255.0.4    UP 00:04:57     D
```

**P7d tunnel key 不一致(RT03=101・他=100) — hub**

```
10.255.0.1/32 via 10.255.0.1
   Tunnel0 created 00:05:03, expire 00:08:16
   Type: dynamic, Flags: registered used nhop 
   NBMA address: 1.1.1.1
10.255.0.4/32 via 10.255.0.4
   Tunnel0 created 00:04:58, expire 00:08:21
   Type: dynamic, Flags: registered used nhop 
   NBMA address: 4.4.4.4
```

**P7d tunnel key 不一致(RT03=101・他=100) — hub**

```
 IPv4 Crypto IKEv2  SA 

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
2         2.2.2.2/500           3.3.3.3/500           none/none            READY  
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/61 sec
      CE id: 1008, Session-id: 8
      Local spi: 223628F214934DB1       Remote spi: 72472388D0504EF4

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
3         2.2.2.2/500           4.4.4.4/500           none/none            READY  
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/298 sec
      CE id: 1003, Session-id: 3
      Local spi: 6333B08CB811BE14       Remote spi: E53B70F9F9C7C789

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
1         2.2.2.2/500           1.1.1.1/500           none/none            READY  
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/303 sec
      CE id: 1001, Session-id: 1
      Local spi: 8DDBB406712409D8       Remote spi: DB35EEB4FB5DF11F

 IPv6 Crypto IKEv2  SA
```

**P7d tunnel key 不一致(RT03=101・他=100) — hub**

```
EIGRP-IPv4 Neighbors for AS(100)
H   Address                 Interface              Hold Uptime   SRTT   RTO  Q  Seq
                                                   (sec)         (ms)       Cnt Num
2   10.255.0.4              Tu0                      12 00:04:55    3  1398  0  11
0   10.255.0.1              Tu0                      12 00:04:57    1  1398  0  11
```

**P7d tunnel key 不一致(RT03=101・他=100) — RT03**

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
     1 2.2.2.2              10.255.0.2  NHRP 00:00:54     S
```

**P7d tunnel key 不一致(RT03=101・他=100) — RT03**

```
10.255.0.2/32 via 10.255.0.2
   Tunnel0 created 00:01:01, never expire 
   Type: static, Flags: 
   NBMA address: 2.2.2.2
```

**P7d tunnel key 不一致(RT03=101・他=100) — RT03**

```
Legend:	E=Expecting replies, R=Responding, W=Waiting, D=Dynamic
Tunnel0:
10.255.0.2   E  NBMA Address: 2.2.2.2 priority = 0 cluster = 0  req-sent 6  req-failed 0  repl-recv 0 (00:01:22 ago)


Pending Registration Requests:
Registration Request: Reqid 20, Ret 64  NHS 10.255.0.2 expired (Tu0)
```

**P7d tunnel key 不一致(RT03=101・他=100) — RT03**

```
 IPv4 Crypto IKEv2  SA 

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
2         3.3.3.3/500           2.2.2.2/500           none/none            READY  
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/63 sec
      CE id: 1008, Session-id: 1
      Local spi: 72472388D0504EF4       Remote spi: 223628F214934DB1

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
1         3.3.3.3/500           2.2.2.2/500           none/none            DELETE 
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/85 sec
      CE id: 1007, Session-id: 1
      Local spi: 9045536347387B69       Remote spi: 572A58193873072E

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
5         3.3.3.3/500           2.2.2.2/500           none/none            DELETE 
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/172 sec
      CE id: 1006, Session-id: 1
      Local spi: DEC88DB135C9519B       Remote spi: F319BF25DA9056CD

 IPv6 Crypto IKEv2  SA
```

**P7d tunnel key 不一致(RT03=101・他=100) — RT03**

```
   current_peer 2.2.2.2 port 500
    #pkts encaps: 22, #pkts encrypt: 22, #pkts digest: 22
    #pkts decaps: 0, #pkts decrypt: 0, #pkts verify: 0
```

**P7d tunnel key 不一致(RT03=101・他=100) — RT03**

```
EIGRP-IPv4 Neighbors for AS(100)
```

**P7d tunnel key 不一致(RT03=101・他=100) — RT03**

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
```

**P7d tunnel key 不一致(RT03=101・他=100) — RT03**

```
Tunnel0: Max-send limit:10000Pkts/10Sec, Usage:0%
   Sent: Total 34
         1 Resolution Request  2 Resolution Reply  31 Registration Request  
         0 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress  
   Rcvd: Total 16
         2 Resolution Request  1 Resolution Reply  0 Registration Request  
         12 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  1 Traffic Indication  0 Redirect Suppress
```

**P7d tunnel key 不一致(RT03=101・他=100) — RT03**

```
Tunnel0 is up, line protocol is up 
  Hardware is Tunnel
  Tunnel linestate evaluation up
  Tunnel source 3.3.3.3 (Loopback0)
   Tunnel Subblocks:
         Tunnel0 source tracking subblock associated with Loopback0
  Tunnel protocol/transport multi-GRE/IP
    Checksumming of packets disabled
  Tunnel TTL 255, Fast tunneling enabled
  Tunnel transport MTU 1472 bytes
  Tunnel transmit bandwidth 8000 (kbps)
  Tunnel receive bandwidth 8000 (kbps)
  Tunnel protection via IPSec (profile "IPSEC-POC")
  Tunnel state info: 
  5 minute input rate 0 bits/sec, 0 packets/sec
  5 minute output rate 0 bits/sec, 0 packets/sec
     83 packets input, 9332 bytes, 0 no buffer
     206 packets output, 19204 bytes, 0 underruns
```

**P7d tunnel key 不一致(RT03=101・他=100) ping RT03 LAN→hub LAN — RT03# ping 192.168.2.1 repeat 3 source 192.168.3.1 → 0%**

```
Type escape sequence to abort.
Sending 3, 100-byte ICMP Echos to 192.168.2.1, timeout is 2 seconds:
Packet sent with a source address of 192.168.3.1 
...
Success rate is 0 percent (0/3)
```

**P7d tunnel key 不一致(RT03=101・他=100) ping RT03 LAN→RT01 LAN(spoke間) — RT03# ping 192.168.1.1 repeat 5 source 192.168.3.1 → 0%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 192.168.1.1, timeout is 2 seconds:
Packet sent with a source address of 192.168.3.1 
.....
Success rate is 0 percent (0/5)
```

**P7d tunnel key 不一致(RT03=101・他=100) — RT03 show dmvpn (spoke間 ping 後)**

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
     1 2.2.2.2              10.255.0.2  NHRP 00:01:13     S
```

**P7d tunnel key 不一致(RT03=101・他=100) hub — RT02 show logging**

```
*Sep 18 15:42:00.211: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 3.3.3.3 socket is DOWN
*Sep 18 15:42:00.217: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 10.255.0.3 NBMA: 3.3.3.3 ) for (Tunnel: 10.255.0.2 NBMA: 2.2.2.2) is DOWN, Reason: External(NHRP: no error)
*Sep 18 15:42:03.837: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 3.3.3.3 socket is UP
*Sep 18 15:42:11.419: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.255.0.3 (Tunnel0) is down: holding time expired
```

**P7d tunnel key 不一致(RT03=101・他=100) RT03 — RT03 show logging**

```
*Sep 18 15:42:00.203: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 10.255.0.2 NBMA: 2.2.2.2 ) for (Tunnel: 10.255.0.3 NBMA: 3.3.3.3) is DOWN, Reason: External(NHRP: no error)
*Sep 18 15:42:00.203: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 3.3.3.3 remote address : 2.2.2.2 socket is DOWN
*Sep 18 15:42:00.204: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.255.0.2 (Tunnel0) is down: interface down
*Sep 18 15:42:00.211: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 18 15:42:03.828: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 18 15:42:03.837: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 3.3.3.3 remote address : 2.2.2.2 socket is UP
*Sep 18 15:42:04.761: NHRP-RATE: Sent one-time Registration Request for 10.255.0.2, reqid 18
*Sep 18 15:42:05.778: NHRP-RATE: Sending initial Registration Request for 10.255.0.2, reqid 19
*Sep 18 15:42:07.566: NHRP-RATE: Retransmitting Registration Request for 10.255.0.2, reqid 20, (retrans ivl 4 sec)
*Sep 18 15:42:11.099: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 10.255.0.2 NBMA: 2.2.2.2 ) for (Tunnel: 10.255.0.3 NBMA: 3.3.3.3) is DOWN, Reason: NHRP Registration Failure(NHRP: no error)
*Sep 18 15:42:11.099: NHRP-RATE: Retransmitting Registration Request for 10.255.0.2, reqid 20, (retrans ivl 8 sec)
*Sep 18 15:42:19.087: NHRP-RATE: Retransmitting Registration Request for 10.255.0.2, reqid 20, (retrans ivl 16 sec)
*Sep 18 15:42:34.007: NHRP-RATE: Retransmitting Registration Request for 10.255.0.2, reqid 20, (retrans ivl 32 sec)
*Sep 18 15:43:05.633: NHRP-RATE: Retransmitting Registration Request for 10.255.0.2, reqid 20, (retrans ivl 64 sec)
```

**P7d tunnel key 不一致(RT03=101・他=100) 復旧(RT03)**

```
interface Tunnel0
tunnel key 100
exit
---
(応答なし)
```

- P7d tunnel key 不一致(RT03=101・他=100) 復旧後 RT03 UP= 15.593587636947632s

**P7e NHS トンネル IP 誤り(RT03 nhs 10.255.0.22・NBMA 正) 注入(RT03)**

```
interface Tunnel0
no ip nhrp nhs 10.255.0.2 nbma 2.2.2.2 multicast
ip nhrp nhs 10.255.0.22 nbma 2.2.2.2 multicast
exit
---
(応答なし)
```

**P7e NHS トンネル IP 誤り(RT03 nhs 10.255.0.22・NBMA 正) — hub**

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
     2 1.1.1.1              10.255.0.1    UP 00:06:51     D
     0 UNKNOWN              10.255.0.3  NHRP    never    IX
     1 4.4.4.4              10.255.0.4    UP 00:06:46     D
```

**P7e NHS トンネル IP 誤り(RT03 nhs 10.255.0.22・NBMA 正) — hub**

```
10.255.0.1/32 via 10.255.0.1
   Tunnel0 created 00:06:51, expire 00:09:47
   Type: dynamic, Flags: registered nhop 
   NBMA address: 1.1.1.1
10.255.0.3/32
   Tunnel0 created 00:00:54, expire 00:02:10
   Type: incomplete, Flags: negative 
   Cache hits: 1
10.255.0.4/32 via 10.255.0.4
   Tunnel0 created 00:06:46, expire 00:09:53
   Type: dynamic, Flags: registered nhop 
   NBMA address: 4.4.4.4
```

**P7e NHS トンネル IP 誤り(RT03 nhs 10.255.0.22・NBMA 正) — hub**

```
 IPv4 Crypto IKEv2  SA 

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
2         2.2.2.2/500           3.3.3.3/500           none/none            READY  
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/61 sec
      CE id: 1012, Session-id: 11
      Local spi: 29FF37652158C057       Remote spi: 4519AC4B26269779

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
3         2.2.2.2/500           4.4.4.4/500           none/none            READY  
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/407 sec
      CE id: 1003, Session-id: 3
      Local spi: 6333B08CB811BE14       Remote spi: E53B70F9F9C7C789

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
1         2.2.2.2/500           1.1.1.1/500           none/none            READY  
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/412 sec
      CE id: 1001, Session-id: 1
      Local spi: 8DDBB406712409D8       Remote spi: DB35EEB4FB5DF11F

 IPv6 Crypto IKEv2  SA
```

**P7e NHS トンネル IP 誤り(RT03 nhs 10.255.0.22・NBMA 正) — hub**

```
EIGRP-IPv4 Neighbors for AS(100)
H   Address                 Interface              Hold Uptime   SRTT   RTO  Q  Seq
                                                   (sec)         (ms)       Cnt Num
1   10.255.0.3              Tu0                      14 00:00:55    1  5000  1  0
2   10.255.0.4              Tu0                      12 00:06:44    1  1398  0  13
0   10.255.0.1              Tu0                      13 00:06:45    1  1398  0  13
```

**P7e NHS トンネル IP 誤り(RT03 nhs 10.255.0.22・NBMA 正) — RT03**

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
     1 2.2.2.2             10.255.0.22  NHRP 00:00:54     S
```

**P7e NHS トンネル IP 誤り(RT03 nhs 10.255.0.22・NBMA 正) — RT03**

```
10.255.0.22/32 via 10.255.0.22
   Tunnel0 created 00:01:02, never expire 
   Type: static, Flags: 
   NBMA address: 2.2.2.2
```

**P7e NHS トンネル IP 誤り(RT03 nhs 10.255.0.22・NBMA 正) — RT03**

```
Legend:	E=Expecting replies, R=Responding, W=Waiting, D=Dynamic
Tunnel0:
10.255.0.22   E  NBMA Address: 2.2.2.2 priority = 0 cluster = 0  req-sent 6  req-failed 0  repl-recv 0 


Pending Registration Requests:
Registration Request: Reqid 27, Ret 64  NHS 10.255.0.22 expired (Tu0)
```

**P7e NHS トンネル IP 誤り(RT03 nhs 10.255.0.22・NBMA 正) — RT03**

```
 IPv4 Crypto IKEv2  SA 

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
4         3.3.3.3/500           2.2.2.2/500           none/none            READY  
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/63 sec
      CE id: 1012, Session-id: 1
      Local spi: 4519AC4B26269779       Remote spi: 29FF37652158C057

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
2         3.3.3.3/500           2.2.2.2/500           none/none            DELETE 
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/172 sec
      CE id: 1008, Session-id: 1
      Local spi: 72472388D0504EF4       Remote spi: 223628F214934DB1

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
3         3.3.3.3/500           2.2.2.2/500           none/none            DELETE 
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/68 sec
      CE id: 1011, Session-id: 1
      Local spi: F426A919364FDD21       Remote spi: 1A5604F23F2743F5

 IPv6 Crypto IKEv2  SA
```

**P7e NHS トンネル IP 誤り(RT03 nhs 10.255.0.22・NBMA 正) — RT03**

```
   current_peer 2.2.2.2 port 500
    #pkts encaps: 22, #pkts encrypt: 22, #pkts digest: 22
    #pkts decaps: 0, #pkts decrypt: 0, #pkts verify: 0
```

**P7e NHS トンネル IP 誤り(RT03 nhs 10.255.0.22・NBMA 正) — RT03**

```
EIGRP-IPv4 Neighbors for AS(100)
```

**P7e NHS トンネル IP 誤り(RT03 nhs 10.255.0.22・NBMA 正) — RT03**

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
```

**P7e NHS トンネル IP 誤り(RT03 nhs 10.255.0.22・NBMA 正) — RT03**

```
Tunnel0: Max-send limit:10000Pkts/10Sec, Usage:0%
   Sent: Total 48
         1 Resolution Request  2 Resolution Reply  44 Registration Request  
         0 Registration Reply  1 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress  
   Rcvd: Total 19
         2 Resolution Request  1 Resolution Reply  0 Registration Request  
         15 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  1 Traffic Indication  0 Redirect Suppress
```

**P7e NHS トンネル IP 誤り(RT03 nhs 10.255.0.22・NBMA 正) — RT03**

```
Tunnel0 is up, line protocol is up 
  Hardware is Tunnel
  Tunnel linestate evaluation up
  Tunnel source 3.3.3.3 (Loopback0)
   Tunnel Subblocks:
         Tunnel0 source tracking subblock associated with Loopback0
  Tunnel protocol/transport multi-GRE/IP
    Checksumming of packets disabled
  Tunnel TTL 255, Fast tunneling enabled
  Tunnel transport MTU 1472 bytes
  Tunnel transmit bandwidth 8000 (kbps)
  Tunnel receive bandwidth 8000 (kbps)
  Tunnel protection via IPSec (profile "IPSEC-POC")
  Tunnel state info: 
  5 minute input rate 0 bits/sec, 0 packets/sec
  5 minute output rate 0 bits/sec, 0 packets/sec
     94 packets input, 10654 bytes, 0 no buffer
     270 packets output, 25166 bytes, 0 underruns
```

**P7e NHS トンネル IP 誤り(RT03 nhs 10.255.0.22・NBMA 正) — RT03**

```
Legend:	E=Expecting replies, R=Responding, W=Waiting, D=Dynamic
Tunnel0:
10.255.0.22   E  NBMA Address: 2.2.2.2 priority = 0 cluster = 0
```

**P7e NHS トンネル IP 誤り(RT03 nhs 10.255.0.22・NBMA 正) ping RT03 LAN→hub LAN — RT03# ping 192.168.2.1 repeat 3 source 192.168.3.1 → 0%**

```
Type escape sequence to abort.
Sending 3, 100-byte ICMP Echos to 192.168.2.1, timeout is 2 seconds:
Packet sent with a source address of 192.168.3.1 
...
Success rate is 0 percent (0/3)
```

**P7e NHS トンネル IP 誤り(RT03 nhs 10.255.0.22・NBMA 正) ping RT03 LAN→RT01 LAN(spoke間) — RT03# ping 192.168.1.1 repeat 5 source 192.168.3.1 → 0%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 192.168.1.1, timeout is 2 seconds:
Packet sent with a source address of 192.168.3.1 
.....
Success rate is 0 percent (0/5)
```

**P7e NHS トンネル IP 誤り(RT03 nhs 10.255.0.22・NBMA 正) — RT03 show dmvpn (spoke間 ping 後)**

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
     1 2.2.2.2             10.255.0.22  NHRP 00:01:15     S
```

**P7e NHS トンネル IP 誤り(RT03 nhs 10.255.0.22・NBMA 正) hub — RT02 show logging**

```
*Sep 18 15:43:47.779: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 3.3.3.3 socket is DOWN
*Sep 18 15:43:47.780: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 10.255.0.3 NBMA: 3.3.3.3 ) for (Tunnel: 10.255.0.2 NBMA: 2.2.2.2) is DOWN, Reason: External(NHRP: no error)
*Sep 18 15:43:47.987: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 3.3.3.3 socket is UP
*Sep 18 15:43:47.990: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Registration Request , Reason:  protocol generic error (7) on (Tunnel: 10.255.0.2 NBMA: 2.2.2.2)
*Sep 18 15:43:47.990: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Error Indication , Reason:  protocol generic error (7) on (Tunnel: 10.255.0.2 NBMA: 2.2.2.2)
*Sep 18 15:43:48.891: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 3.3.3.3 socket is DOWN
*Sep 18 15:43:52.415: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 3.3.3.3 socket is UP
*Sep 18 15:43:53.363: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Registration Request , Reason:  protocol generic error (7) on (Tunnel: 10.255.0.2 NBMA: 2.2.2.2)
*Sep 18 15:43:53.363: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Error Indication , Reason:  protocol generic error (7) on (Tunnel: 10.255.0.2 NBMA: 2.2.2.2)
*Sep 18 15:43:53.406: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Registration Request , Reason:  protocol generic error (7) on (Tunnel: 10.255.0.2 NBMA: 2.2.2.2)
*Sep 18 15:43:53.406: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Error Indication , Reason:  protocol generic error (7) on (Tunnel: 10.255.0.2 NBMA: 2.2.2.2)
*Sep 18 15:43:54.319: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Registration Request , Reason:  protocol generic error (7) on (Tunnel: 10.255.0.2 NBMA: 2.2.2.2)
*Sep 18 15:43:54.319: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Error Indication , Reason:  protocol generic error (7) on (Tunnel: 10.255.0.2 NBMA: 2.2.2.2)
*Sep 18 15:43:54.406: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Registration Request , Reason:  protocol generic error (7) on (Tunnel: 10.255.0.2 NBMA: 2.2.2.2)
*Sep 18 15:43:54.406: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Error Indication , Reason:  protocol generic error (7) on (Tunnel: 10.255.0.2 NBMA: 2.2.2.2)
*Sep 18 15:43:55.927: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Registration Request , Reason:  protocol generic error (7) on (Tunnel: 10.255.0.2 NBMA: 2.2.2.2)
*Sep 18 15:43:55.927: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Error Indication , Reason:  protocol generic error (7) on (Tunnel: 10.255.0.2 NBMA: 2.2.2.2)
*Sep 18 15:43:58.085: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.255.0.3 (Tunnel0) is down: holding time expired
*Sep 18 15:43:58.103: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.255.0.3 (Tunnel0) is up: new adjacency
*Sep 18 15:43:58.160: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Resolution Request , Reason:  protocol generic error (7) on (Tunnel: 10.255.0.2 NBMA: 2.2.2.2)
*Sep 18 15:43:59.670: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Registration Request , Reason:  protocol generic error (7) on (Tunnel: 10.255.0.2 NBMA: 2.2.2.2)
*Sep 18 15:43:59.670: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Error Indication , Reason:  protocol generic error (7) on (Tunnel: 10.255.0.2 NBMA: 2.2.2.2)
*Sep 18 15:43:59.976: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Resolution Request , Reason:  protocol generic error (7) on (Tunnel: 10.255.0.2 NBMA: 2.2.2.2)
*Sep 18 15:44:03.776: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Resolution Request , Reason:  protocol generic error (7) on (Tunnel: 10.255.0.2 NBMA: 2.2.2.2)
*Sep 18 15:44:05.919: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Registration Request , Reason:  protocol generic error (7) on (Tunnel: 10.255.0.2 NBMA: 2.2.2.2)
*Sep 18 15:44:05.919: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Error Indication , Reason:  protocol generic error (7) on (Tunnel: 10.255.0.2 NBMA: 2.2.2.2)
*Sep 18 15:44:11.214: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Resolution Request , Reason:  protocol generic error (7) on (Tunnel: 10.255.0.2 NBMA: 2.2.2.2)
*Sep 18 15:44:20.537: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Registration Request , Reason:  protocol generic error (7) on (Tunnel: 10.255.0.2 NBMA: 2.2.2.2)
*Sep 18 15:44:20.537: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Error Indication , Reason:  protocol generic error (7) on (Tunnel: 10.255.0.2 NBMA: 2.2.2.2)
*Sep 18 15:44:26.079: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Resolution Request , Reason:  protocol generic error (7) on (Tunnel: 10.255.0.2 NBMA: 2.2.2.2)
*Sep 18 15:44:47.475: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Registration Request , Reason:  protocol generic error (7) on (Tunnel: 10.255.0.2 NBMA: 2.2.2.2)
*Sep 18 15:44:47.475: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Error Indication , Reason:  protocol generic error (7) on (Tunnel: 10.255.0.2 NBMA: 2.2.2.2)
*Sep 18 15:44:57.663: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Resolution Request , Reason:  protocol generic error (7) on (Tunnel: 10.255.0.2 NBMA: 2.2.2.2)
```

**P7e NHS トンネル IP 誤り(RT03 nhs 10.255.0.22・NBMA 正) RT03 — RT03 show logging**

```
*Sep 18 15:43:47.777: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 10.255.0.2 NBMA: 2.2.2.2 ) for (Tunnel: 10.255.0.3 NBMA: 3.3.3.3) is DOWN, Reason: administratively prohibited(NHRP: no error)
*Sep 18 15:43:47.777: %DMVPN-5-NHRP_NHP_UP: Tunnel0: Next Hop NHP : (Tunnel: 10.255.0.2 NBMA: 2.2.2.2) for (Tunnel: 10.255.0.3 NBMA: 3.3.3.3) is UP
*Sep 18 15:43:47.777: %DMVPN-5-NHRP_NHP_DOWN: Tunnel0: Next Hop Peer : (Tunnel: 10.255.0.2 NBMA: 2.2.2.2) for (Tunnel: 10.255.0.3 NBMA: 3.3.3.3) is DOWN, Reason: administratively prohibited(NHRP: no error)
*Sep 18 15:43:47.778: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 3.3.3.3 remote address : 2.2.2.2 socket is DOWN
*Sep 18 15:43:47.978: %DMVPN-5-NHRP_NHP_UP: Tunnel0: Next Hop NHP : (Tunnel: 10.255.0.22 NBMA: 2.2.2.2) for (Tunnel: 10.255.0.3 NBMA: 3.3.3.3) is UP
*Sep 18 15:43:47.978: %DMVPN-5-NHRP_NHP_DOWN: Tunnel0: Next Hop Peer : (Tunnel: 10.255.0.22 NBMA: 2.2.2.2) for (Tunnel: 10.255.0.3 NBMA: 3.3.3.3) is DOWN, Reason: administratively prohibited(NHRP: no error)
*Sep 18 15:43:47.988: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 3.3.3.3 remote address : 2.2.2.2 socket is UP
*Sep 18 15:43:47.989: NHRP-RATE: Sending initial Registration Request for 10.255.0.22, reqid 24
*Sep 18 15:43:48.883: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 3.3.3.3 remote address : 2.2.2.2 socket is DOWN
*Sep 18 15:43:48.883: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.255.0.2 (Tunnel0) is down: interface down
*Sep 18 15:43:48.890: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 18 15:43:52.406: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 18 15:43:52.416: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 3.3.3.3 remote address : 2.2.2.2 socket is UP
*Sep 18 15:43:53.362: NHRP-RATE: Sent one-time Registration Request for 10.255.0.22, reqid 25
*Sep 18 15:43:54.319: NHRP-RATE: Sending initial Registration Request for 10.255.0.22, reqid 26
*Sep 18 15:43:55.927: NHRP-RATE: Retransmitting Registration Request for 10.255.0.22, reqid 27, (retrans ivl 4 sec)
*Sep 18 15:43:59.669: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 10.255.0.22 NBMA: 2.2.2.2 ) for (Tunnel: 10.255.0.3 NBMA: 3.3.3.3) is DOWN, Reason: NHRP Registration Failure(NHRP: no error)
*Sep 18 15:43:59.669: NHRP-RATE: Retransmitting Registration Request for 10.255.0.22, reqid 27, (retrans ivl 8 sec)
*Sep 18 15:44:05.919: NHRP-RATE: Retransmitting Registration Request for 10.255.0.22, reqid 27, (retrans ivl 16 sec)
*Sep 18 15:44:20.536: NHRP-RATE: Retransmitting Registration Request for 10.255.0.22, reqid 27, (retrans ivl 32 sec)
*Sep 18 15:44:47.475: NHRP-RATE: Retransmitting Registration Request for 10.255.0.22, reqid 27, (retrans ivl 64 sec)
```

**P7e NHS トンネル IP 誤り(RT03 nhs 10.255.0.22・NBMA 正) 復旧(RT03)**

```
interface Tunnel0
no ip nhrp nhs 10.255.0.22 nbma 2.2.2.2 multicast
ip nhrp nhs 10.255.0.2 nbma 2.2.2.2 multicast
exit
---
(応答なし)
```

- P7e NHS トンネル IP 誤り(RT03 nhs 10.255.0.22・NBMA 正) 復旧後 RT03 UP= 15.706159830093384s

**P7e2 NHS NBMA 誤り(RT03 nbma=hub 物理 10.0.23.2・tunnel source は Lo0) 注入(RT03)**

```
interface Tunnel0
no ip nhrp nhs 10.255.0.2 nbma 2.2.2.2 multicast
ip nhrp nhs 10.255.0.2 nbma 10.0.23.2 multicast
exit
---
(応答なし)
```

**P7e2 NHS NBMA 誤り(RT03 nbma=hub 物理 10.0.23.2・tunnel source は Lo0) — hub**

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
     1 1.1.1.1              10.255.0.1    UP 00:08:42     D
     1 4.4.4.4              10.255.0.4    UP 00:08:37     D
```

**P7e2 NHS NBMA 誤り(RT03 nbma=hub 物理 10.0.23.2・tunnel source は Lo0) — hub**

```
10.255.0.1/32 via 10.255.0.1
   Tunnel0 created 00:08:43, expire 00:07:56
   Type: dynamic, Flags: registered used nhop 
   NBMA address: 1.1.1.1
10.255.0.4/32 via 10.255.0.4
   Tunnel0 created 00:08:37, expire 00:08:01
   Type: dynamic, Flags: registered used nhop 
   NBMA address: 4.4.4.4
```

**P7e2 NHS NBMA 誤り(RT03 nbma=hub 物理 10.0.23.2・tunnel source は Lo0) — hub**

```
 IPv4 Crypto IKEv2  SA 

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
3         2.2.2.2/500           4.4.4.4/500           none/none            READY  
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/518 sec
      CE id: 1003, Session-id: 3
      Local spi: 6333B08CB811BE14       Remote spi: E53B70F9F9C7C789

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
1         2.2.2.2/500           1.1.1.1/500           none/none            READY  
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/523 sec
      CE id: 1001, Session-id: 1
      Local spi: 8DDBB406712409D8       Remote spi: DB35EEB4FB5DF11F

 IPv6 Crypto IKEv2  SA
```

**P7e2 NHS NBMA 誤り(RT03 nbma=hub 物理 10.0.23.2・tunnel source は Lo0) — hub**

```
EIGRP-IPv4 Neighbors for AS(100)
H   Address                 Interface              Hold Uptime   SRTT   RTO  Q  Seq
                                                   (sec)         (ms)       Cnt Num
2   10.255.0.4              Tu0                      10 00:08:35    1  1398  0  15
0   10.255.0.1              Tu0                      14 00:08:37    1  1398  0  15
```

**P7e2 NHS NBMA 誤り(RT03 nbma=hub 物理 10.0.23.2・tunnel source は Lo0) — RT03**

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
     1 10.0.23.2            10.255.0.2   IKE 00:00:54     S
```

**P7e2 NHS NBMA 誤り(RT03 nbma=hub 物理 10.0.23.2・tunnel source は Lo0) — RT03**

```
10.255.0.2/32 via 10.255.0.2
   Tunnel0 created 00:01:01, never expire 
   Type: static, Flags: 
   NBMA address: 10.0.23.2
```

**P7e2 NHS NBMA 誤り(RT03 nbma=hub 物理 10.0.23.2・tunnel source は Lo0) — RT03**

```
Legend:	E=Expecting replies, R=Responding, W=Waiting, D=Dynamic
Tunnel0:
10.255.0.2   E  NBMA Address: 10.0.23.2 priority = 0 cluster = 0  req-sent 6  req-failed 0  repl-recv 0 


Pending Registration Requests:
Registration Request: Reqid 33, Ret 64  NHS 10.255.0.2 expired (Tu0)
```

**P7e2 NHS NBMA 誤り(RT03 nbma=hub 物理 10.0.23.2・tunnel source は Lo0) — RT03**

```
 IPv4 Crypto IKEv2  SA 

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
1         3.3.3.3/500           2.2.2.2/500           none/none            DELETE 
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/90 sec
      CE id: 1013, Session-id: 1
      Local spi: 3EE0C9E3360C6AE1       Remote spi: B30BD476E508E228

 IPv6 Crypto IKEv2  SA
```

**P7e2 NHS NBMA 誤り(RT03 nbma=hub 物理 10.0.23.2・tunnel source は Lo0) — RT03**

```
   current_peer 10.0.23.2 port 500
    #pkts encaps: 0, #pkts encrypt: 0, #pkts digest: 0
    #pkts decaps: 0, #pkts decrypt: 0, #pkts verify: 0
```

**P7e2 NHS NBMA 誤り(RT03 nbma=hub 物理 10.0.23.2・tunnel source は Lo0) — RT03**

```
EIGRP-IPv4 Neighbors for AS(100)
```

**P7e2 NHS NBMA 誤り(RT03 nbma=hub 物理 10.0.23.2・tunnel source は Lo0) — RT03**

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
```

**P7e2 NHS NBMA 誤り(RT03 nbma=hub 物理 10.0.23.2・tunnel source は Lo0) — RT03**

```
Tunnel0: Max-send limit:10000Pkts/10Sec, Usage:0%
   Sent: Total 63
         1 Resolution Request  2 Resolution Reply  57 Registration Request  
         0 Registration Reply  3 Purge Request  0 Purge Reply  
         0 Error Indication  0 Traffic Indication  0 Redirect Suppress  
   Rcvd: Total 23
         2 Resolution Request  1 Resolution Reply  0 Registration Request  
         19 Registration Reply  0 Purge Request  0 Purge Reply  
         0 Error Indication  1 Traffic Indication  0 Redirect Suppress
```

**P7e2 NHS NBMA 誤り(RT03 nbma=hub 物理 10.0.23.2・tunnel source は Lo0) — RT03**

```
Tunnel0 is up, line protocol is up 
  Hardware is Tunnel
  Tunnel linestate evaluation up
  Tunnel source 3.3.3.3 (Loopback0)
   Tunnel Subblocks:
         Tunnel0 source tracking subblock associated with Loopback0
  Tunnel protocol/transport multi-GRE/IP
    Checksumming of packets disabled
  Tunnel TTL 255, Fast tunneling enabled
  Tunnel transport MTU 1472 bytes
  Tunnel transmit bandwidth 8000 (kbps)
  Tunnel receive bandwidth 8000 (kbps)
  Tunnel protection via IPSec (profile "IPSEC-POC")
  Tunnel state info: 
  5 minute input rate 0 bits/sec, 0 packets/sec
  5 minute output rate 0 bits/sec, 0 packets/sec
     107 packets input, 12229 bytes, 0 no buffer
     336 packets output, 31306 bytes, 0 underruns
```

**P7e2 NHS NBMA 誤り(RT03 nbma=hub 物理 10.0.23.2・tunnel source は Lo0) — RT03**

```
Legend:	E=Expecting replies, R=Responding, W=Waiting, D=Dynamic
Tunnel0:
10.255.0.2   E  NBMA Address: 10.0.23.2 priority = 0 cluster = 0
```

**P7e2 NHS NBMA 誤り(RT03 nbma=hub 物理 10.0.23.2・tunnel source は Lo0) ping RT03 LAN→hub LAN — RT03# ping 192.168.2.1 repeat 3 source 192.168.3.1 → 0%**

```
Type escape sequence to abort.
Sending 3, 100-byte ICMP Echos to 192.168.2.1, timeout is 2 seconds:
Packet sent with a source address of 192.168.3.1 
...
Success rate is 0 percent (0/3)
```

**P7e2 NHS NBMA 誤り(RT03 nbma=hub 物理 10.0.23.2・tunnel source は Lo0) ping RT03 LAN→RT01 LAN(spoke間) — RT03# ping 192.168.1.1 repeat 5 source 192.168.3.1 → 0%**

```
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 192.168.1.1, timeout is 2 seconds:
Packet sent with a source address of 192.168.3.1 
.....
Success rate is 0 percent (0/5)
```

**P7e2 NHS NBMA 誤り(RT03 nbma=hub 物理 10.0.23.2・tunnel source は Lo0) — RT03 show dmvpn (spoke間 ping 後)**

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
     1 10.0.23.2            10.255.0.2   IKE 00:01:14     S
```

**P7e2 NHS NBMA 誤り(RT03 nbma=hub 物理 10.0.23.2・tunnel source は Lo0) hub — RT02 show logging**

```
*Sep 18 15:45:39.195: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 3.3.3.3 socket is DOWN
*Sep 18 15:45:39.201: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 10.255.0.3 NBMA: 3.3.3.3 ) for (Tunnel: 10.255.0.2 NBMA: 2.2.2.2) is DOWN, Reason: External(NHRP: no error)
*Sep 18 15:45:51.682: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.255.0.3 (Tunnel0) is down: holding time expired
```

**P7e2 NHS NBMA 誤り(RT03 nbma=hub 物理 10.0.23.2・tunnel source は Lo0) RT03 — RT03 show logging**

```
*Sep 18 15:45:39.187: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 10.255.0.2 NBMA: 2.2.2.2 ) for (Tunnel: 10.255.0.3 NBMA: 3.3.3.3) is DOWN, Reason: administratively prohibited(NHRP: no error)
*Sep 18 15:45:39.187: %DMVPN-5-NHRP_NHP_UP: Tunnel0: Next Hop NHP : (Tunnel: 10.255.0.2 NBMA: 2.2.2.2) for (Tunnel: 10.255.0.3 NBMA: 3.3.3.3) is UP
*Sep 18 15:45:39.187: %DMVPN-5-NHRP_NHP_DOWN: Tunnel0: Next Hop Peer : (Tunnel: 10.255.0.2 NBMA: 2.2.2.2) for (Tunnel: 10.255.0.3 NBMA: 3.3.3.3) is DOWN, Reason: administratively prohibited(NHRP: no error)
*Sep 18 15:45:39.187: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 3.3.3.3 remote address : 2.2.2.2 socket is DOWN
*Sep 18 15:45:39.287: %DMVPN-5-NHRP_NHP_UP: Tunnel0: Next Hop NHP : (Tunnel: 10.255.0.2 NBMA: 10.0.23.2) for (Tunnel: 10.255.0.3 NBMA: 3.3.3.3) is UP
*Sep 18 15:45:39.287: %DMVPN-5-NHRP_NHP_DOWN: Tunnel0: Next Hop Peer : (Tunnel: 10.255.0.2 NBMA: 10.0.23.2) for (Tunnel: 10.255.0.3 NBMA: 3.3.3.3) is DOWN, Reason: administratively prohibited(NHRP: no error)
*Sep 18 15:45:40.190: NHRP-RATE: Sending initial Registration Request for 10.255.0.2, reqid 8
*Sep 18 15:45:40.193: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.255.0.2 (Tunnel0) is down: interface down
*Sep 18 15:45:40.194: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 18 15:45:43.715: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 18 15:45:45.609: NHRP-RATE: Sending initial Registration Request for 10.255.0.2, reqid 32
*Sep 18 15:45:47.566: NHRP-RATE: Retransmitting Registration Request for 10.255.0.2, reqid 33, (retrans ivl 4 sec)
*Sep 18 15:45:50.940: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 10.255.0.2 NBMA: 10.0.23.2 ) for (Tunnel: 10.255.0.3 NBMA: 3.3.3.3) is DOWN, Reason: NHRP Registration Failure(NHRP: no error)
*Sep 18 15:45:50.940: NHRP-RATE: Retransmitting Registration Request for 10.255.0.2, reqid 33, (retrans ivl 8 sec)
*Sep 18 15:45:57.281: NHRP-RATE: Retransmitting Registration Request for 10.255.0.2, reqid 33, (retrans ivl 16 sec)
*Sep 18 15:46:09.573: NHRP-RATE: Retransmitting Registration Request for 10.255.0.2, reqid 33, (retrans ivl 32 sec)
*Sep 18 15:46:34.246: NHRP-RATE: Retransmitting Registration Request for 10.255.0.2, reqid 33, (retrans ivl 64 sec)
```

**P7e2 NHS NBMA 誤り(RT03 nbma=hub 物理 10.0.23.2・tunnel source は Lo0) 復旧(RT03)**

```
interface Tunnel0
no ip nhrp nhs 10.255.0.2 nbma 10.0.23.2 multicast
ip nhrp nhs 10.255.0.2 nbma 2.2.2.2 multicast
exit
---
(応答なし)
```

- P7e2 NHS NBMA 誤り(RT03 nbma=hub 物理 10.0.23.2・tunnel source は Lo0) 復旧後 RT03 UP= 15.513233423233032s

**P7f-1 hub Tunnel1 同一 source・同一 profile・shared 無し**

```
interface Tunnel1
ip address 10.254.0.2 255.255.255.0
tunnel source Loopback0
tunnel mode gre multipoint
tunnel key 200
tunnel protection ipsec profile IPSEC-POC
exit
---
(応答なし)
```

**P7f-1 hub**

```
Tunnel0                10.255.0.2      YES manual up                    up      
Tunnel1                10.254.0.2      YES manual up                    up
```

**P7f-1 hub**

```

Number of Crypto Socket connections 3

   Tu0 Peers (local/remote): 2.2.2.2/1.1.1.1 
       Local Ident  (addr/mask/port/prot): (2.2.2.2/255.255.255.255/0/47)
       Remote Ident (addr/mask/port/prot): (1.1.1.1/255.255.255.255/0/47)
       IPSec Profile: "IPSEC-POC"
       Socket State: Open
       Client: "TUNNEL SEC" (Client State: Active)
   Tu0 Peers (local/remote): 2.2.2.2/4.4.4.4 
       Local Ident  (addr/mask/port/prot): (2.2.2.2/255.255.255.255/0/47)
       Remote Ident (addr/mask/port/prot): (4.4.4.4/255.255.255.255/0/47)
       IPSec Profile: "IPSEC-POC"
       Socket State: Open
       Client: "TUNNEL SEC" (Client State: Active)
   Tu0 Peers (local/remote): 2.2.2.2/3.3.3.3 
       Local Ident  (addr/mask/port/prot): (2.2.2.2/255.255.255.255/0/47)
       Remote Ident (addr/mask/port/prot): (3.3.3.3/255.255.255.255/0/47)
       IPSec Profile: "IPSEC-POC"
       Socket State: Open
       Client: "TUNNEL SEC" (Client State: Active)
Crypto Sockets in Listen state:
Client: "TUNNEL SEC" Profile: "IPSEC-POC" Map-name: "Tunnel0-head-0"
```

**P7f-1 hub**

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
     1 1.1.1.1              10.255.0.1    UP 00:09:48     D
     1 3.3.3.3              10.255.0.3    UP 00:00:37     D
     1 4.4.4.4              10.255.0.4    UP 00:09:43     D
```

**P7f-1 hub**

```
IPSEC profile IPSEC-POC
	IKEv2 Profile: IKEV2-POC
	Security association lifetime: 4608000 kilobytes/3600 seconds
	Dualstack (Y/N): N

	Responder-Only (Y/N): N
	PFS (Y/N): N
	Mixed-mode : Disabled
	Transform sets={ 
		TS-POC:  { esp-256-aes esp-sha256-hmac  } , 
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

**P7f-1 hub**

```
Building configuration...

Current configuration : 148 bytes
!
interface Tunnel1
 ip address 10.254.0.2 255.255.255.0
 no ip redirects
 tunnel source Loopback0
 tunnel mode gre multipoint
 tunnel key 200
end
```

**P7f-1 hub**

```
Building configuration...

Current configuration : 332 bytes
!
interface Tunnel0
 ip address 10.255.0.2 255.255.255.0
 no ip redirects
 ip mtu 1400
 no ip split-horizon eigrp 100
 ip nhrp authentication DMVPNKEY
 ip nhrp network-id 1
 ip nhrp redirect
 ip tcp adjust-mss 1360
 tunnel source Loopback0
 tunnel mode gre multipoint
 tunnel key 100
 tunnel protection ipsec profile IPSEC-POC
end
```

**P7f-1 ping RT01 LAN→hub LAN(Tunnel0 生存?) — RT01# ping 192.168.2.1 repeat 3 source 192.168.1.1 → 100%**

```
Type escape sequence to abort.
Sending 3, 100-byte ICMP Echos to 192.168.2.1, timeout is 2 seconds:
Packet sent with a source address of 192.168.1.1 
!!!
Success rate is 100 percent (3/3), round-trip min/avg/max = 1/1/1 ms
```

**P7f-1 hub — RT02 show logging**

```

```

**P7f-2 hub Tunnel1 に shared**

```
interface Tunnel1
tunnel protection ipsec profile IPSEC-POC shared
exit
---
(応答なし)
```

**P7f-2 hub**

```
Tunnel0                10.255.0.2      YES manual up                    up      
Tunnel1                10.254.0.2      YES manual up                    up
```

**P7f-2 hub**

```

Number of Crypto Socket connections 3

   Tu0 Peers (local/remote): 2.2.2.2/1.1.1.1 
       Local Ident  (addr/mask/port/prot): (2.2.2.2/255.255.255.255/0/47)
       Remote Ident (addr/mask/port/prot): (1.1.1.1/255.255.255.255/0/47)
       IPSec Profile: "IPSEC-POC"
       Socket State: Open
       Client: "TUNNEL SEC" (Client State: Active)
   Tu0 Peers (local/remote): 2.2.2.2/4.4.4.4 
       Local Ident  (addr/mask/port/prot): (2.2.2.2/255.255.255.255/0/47)
       Remote Ident (addr/mask/port/prot): (4.4.4.4/255.255.255.255/0/47)
       IPSec Profile: "IPSEC-POC"
       Socket State: Open
       Client: "TUNNEL SEC" (Client State: Active)
   Tu0 Peers (local/remote): 2.2.2.2/3.3.3.3 
       Local Ident  (addr/mask/port/prot): (2.2.2.2/255.255.255.255/0/47)
       Remote Ident (addr/mask/port/prot): (3.3.3.3/255.255.255.255/0/47)
       IPSec Profile: "IPSEC-POC"
       Socket State: Open
       Client: "TUNNEL SEC" (Client State: Active)
Crypto Sockets in Listen state:
Client: "TUNNEL SEC" Profile: "IPSEC-POC" Map-name: "Tunnel0-head-0"
```

**P7f-2 hub**

```
Building configuration...

Current configuration : 148 bytes
!
interface Tunnel1
 ip address 10.254.0.2 255.255.255.0
 no ip redirects
 tunnel source Loopback0
 tunnel mode gre multipoint
 tunnel key 200
end
```

**P7f-2 hub — RT02 show logging**

```

```

**P7f-3 hub Tunnel0 にも shared**

```
interface Tunnel0
tunnel protection ipsec profile IPSEC-POC shared
exit
---
%Shutting down Tunnel0 interface due to IPsec tunnel protection modification.
%Please run "no shutdown" after config change to bring up the interface.
```

**P7f-3 hub**

```
Tunnel0                10.255.0.2      YES manual administratively down down    
Tunnel1                10.254.0.2      YES manual up                    up
```

**P7f-3 hub**

```

```

**P7f-3 hub**

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

**P7f-3 hub**

```
 IPv4 Crypto IKEv2  SA 

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
3         2.2.2.2/500           4.4.4.4/500           none/none            DELETE 
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/634 sec
      CE id: 1003, Session-id: 3
      Local spi: 6333B08CB811BE14       Remote spi: E53B70F9F9C7C789

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
1         2.2.2.2/500           1.1.1.1/500           none/none            DELETE 
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/639 sec
      CE id: 1001, Session-id: 1
      Local spi: 8DDBB406712409D8       Remote spi: DB35EEB4FB5DF11F

Tunnel-id Local                 Remote                fvrf/ivrf            Status 
2         2.2.2.2/500           3.3.3.3/500           none/none            DELETE 
      Encr: AES-CBC, keysize: 256, PRF: SHA256, Hash: SHA256, DH Grp:14, Auth sign: PSK, Auth verify: PSK
      Life/Active Time: 86400/90 sec
      CE id: 1020, Session-id: 19
      Local spi: 9D8BC94C6EBC8ABC       Remote spi: 7043AA089E5C0CA3

 IPv6 Crypto IKEv2  SA
```

**P7f-3 hub**

```
Building configuration...

Current configuration : 349 bytes
!
interface Tunnel0
 ip address 10.255.0.2 255.255.255.0
 no ip redirects
 ip mtu 1400
 no ip split-horizon eigrp 100
 ip nhrp authentication DMVPNKEY
 ip nhrp network-id 1
 ip nhrp redirect
 ip tcp adjust-mss 1360
 shutdown
 tunnel source Loopback0
 tunnel mode gre multipoint
 tunnel key 100
 tunnel protection ipsec profile IPSEC-POC shared
end
```

**P7f-3 ping RT01 LAN→hub LAN — RT01# ping 192.168.2.1 repeat 3 source 192.168.1.1 → 0%**

```
Type escape sequence to abort.
Sending 3, 100-byte ICMP Echos to 192.168.2.1, timeout is 2 seconds:
Packet sent with a source address of 192.168.1.1 
...
Success rate is 0 percent (0/3)
```

**P7f-3 hub — RT02 show logging**

```
*Sep 18 15:48:09.144: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 1.1.1.1 socket is DOWN
*Sep 18 15:48:09.144: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 4.4.4.4 socket is DOWN
*Sep 18 15:48:09.144: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 3.3.3.3 socket is DOWN
*Sep 18 15:48:09.146: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 18 15:48:11.145: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 10.255.0.1 NBMA: 1.1.1.1 ) for (Tunnel: 10.255.0.2 NBMA: 2.2.2.2) is DOWN, Reason: External(NHRP: no error)
*Sep 18 15:48:11.145: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 10.255.0.3 NBMA: 3.3.3.3 ) for (Tunnel: 10.255.0.2 NBMA: 2.2.2.2) is DOWN, Reason: External(NHRP: no error)
*Sep 18 15:48:11.145: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 10.255.0.4 NBMA: 4.4.4.4 ) for (Tunnel: 10.255.0.2 NBMA: 2.2.2.2) is DOWN, Reason: External(NHRP: no error)
*Sep 18 15:48:11.146: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.255.0.3 (Tunnel0) is down: interface down
*Sep 18 15:48:11.146: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.255.0.4 (Tunnel0) is down: interface down
*Sep 18 15:48:11.146: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.255.0.1 (Tunnel0) is down: interface down
```

**P7f-4 hub Tunnel1 削除・Tunnel0 の shared 解除**

```
no interface Tunnel1
interface Tunnel0
tunnel protection ipsec profile IPSEC-POC
exit
---
(応答なし)
```

**P7f-4 hub show dmvpn (3 UP after Nones)**

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

**P7g-0 hub show run int Tunnel0 | include nhrp**

```
 ip nhrp authentication DMVPNKEY
 ip nhrp network-id 1
 ip nhrp redirect
```

**P7g-0 RT01 show run int Tunnel0 | include nhrp**

```
 ip nhrp authentication DMVPNKEY
 ip nhrp network-id 1
 ip nhrp nhs 10.255.0.2 nbma 2.2.2.2 multicast
```

**P7g-1 hub no ip nhrp map multicast dynamic**

```
interface Tunnel0
no ip nhrp map multicast dynamic
exit
---
(応答なし)
```

**P7g-1 hub**

```
 ip nhrp authentication DMVPNKEY
 no ip nhrp map multicast dynamic
 ip nhrp network-id 1
 ip nhrp redirect
```

**P7g-1 hub**

```
  I/F     NBMA address
```

**P7g-1 hub**

```
EIGRP-IPv4 Neighbors for AS(100)
```

**P7g-1 hub**

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

**P7g-1 RT01**

```
EIGRP-IPv4 Neighbors for AS(100)
```

**P7g-1 RT01**

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

Gateway of last resort is 10.0.12.2 to network 0.0.0.0
```

**P7g-1 RT01**

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
     1 2.2.2.2              10.255.0.2   IKE 00:00:54     S
```

**P7g-1 RT01 — RT01 show logging**

```
*Sep 18 15:36:38.762: %CRYPTO-5-SELF_TEST_START: Crypto algorithms release (Rel5a), Entropy release (3.4.1)
*Sep 18 15:36:38.762: %CRYPTO-0-SELF_TEST_FAILURE: Crypto self-test - (Crypto Module Integrity Test Bypassed)
*Sep 18 15:36:38.862: %CRYPTO-5-SELF_TEST_END: Crypto Algorithm self-test completed successfully
*Sep 18 15:36:40.902: %CRYPTO_ENGINE-5-CSDL_COMPLIANCE_ENFORCED: Cisco PSB security compliance is being enforced
*Sep 18 15:37:00.090: %CRYPTO-5-SELF_TEST_START: Crypto algorithms release (Rel5a), Entropy release (3.4.1)
*Sep 18 15:37:00.091: %CRYPTO-5-SELF_TEST_END: Crypto Algorithm self-test completed successfully
*Sep 18 15:38:00.558: %DMVPN-5-NHRP_NHP_UP: Tunnel0: Next Hop NHP : (Tunnel: 10.255.0.2 NBMA: 2.2.2.2) for (Tunnel: 10.255.0.1 NBMA: UNKNOWN) is UP
*Sep 18 15:38:00.558: %DMVPN-5-NHRP_NHP_DOWN: Tunnel0: Next Hop Peer : (Tunnel: 10.255.0.2 NBMA: 2.2.2.2) for (Tunnel: 10.255.0.1 NBMA: UNKNOWN) is DOWN, Reason: administratively prohibited(NHRP: no error)
*Sep 18 15:38:00.859: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 10.255.0.2 NBMA: 2.2.2.2 ) for (Tunnel: 10.255.0.1 NBMA: 1.1.1.1) is DOWN, Reason: External(NHRP: no error)
*Sep 18 15:38:00.859: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Registration Request , Reason:  protocol generic error (7) on (Tunnel: 10.255.0.1 NBMA: 1.1.1.1)
*Sep 18 15:38:01.064: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 18 15:38:01.076: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 1.1.1.1 remote address : 2.2.2.2 socket is UP
*Sep 18 15:38:01.078: %DMVPN-5-NHRP_NHS_UP: Tunnel0: Next Hop Server : (Tunnel: 10.255.0.2 NBMA: 2.2.2.2) for (Tunnel: 10.255.0.1 NBMA: 1.1.1.1) is  UP
*Sep 18 15:38:07.942: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.255.0.2 (Tunnel0) is up: new adjacency
*Sep 18 15:38:17.927: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 1.1.1.1 remote address : 4.4.4.4 socket is UP
*Sep 18 15:38:17.929: %DMVPN-5-NHRP_NHP_UP: Tunnel0: Next Hop NHP : (Tunnel: 10.255.0.4 NBMA: 4.4.4.4) for (Tunnel: 10.255.0.1 NBMA: 1.1.1.1) is UP
*Sep 18 15:38:17.929: %DMVPN-7-NHRP_RES:  Tunnel0: Host with (Tunnel: 10.255.0.1 NBMA: 1.1.1.1) Received Resolution Req from  (Tunnel: 10.255.0.4 NBMA: 4.4.4.4)
*Sep 18 15:39:45.814: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 1.1.1.1 remote address : 3.3.3.3 socket is UP
*Sep 18 15:39:45.815: %DMVPN-5-NHRP_NHP_UP: Tunnel0: Next Hop NHP : (Tunnel: 10.255.0.3 NBMA: 3.3.3.3) for (Tunnel: 10.255.0.1 NBMA: 1.1.1.1) is UP
*Sep 18 15:39:45.815: %DMVPN-7-NHRP_RES:  Tunnel0: Host with (Tunnel: 10.255.0.1 NBMA: 1.1.1.1) Received Resolution Req from  (Tunnel: 10.255.0.3 NBMA: 3.3.3.3)
*Sep 18 15:39:45.818: %CRYPTO-4-RECVD_PKT_INV_SPI: decaps: rec'd IPSEC packet has invalid spi for destaddr=1.1.1.1, prot=50, spi=0xCBE96130(3421069616), srcaddr=3.3.3.3, input interface=Ethernet0/0
*Sep 18 15:39:48.516: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 1.1.1.1 remote address : 3.3.3.3 socket is DOWN
*Sep 18 15:39:48.519: %DMVPN-5-NHRP_NHP_DOWN: Tunnel0: Next Hop Peer : (Tunnel: 10.255.0.3 NBMA: 3.3.3.3) for (Tunnel: 10.255.0.1 NBMA: 1.1.1.1) is DOWN, Reason: External(NHRP: no error)
*Sep 18 15:48:09.146: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 1.1.1.1 remote address : 2.2.2.2 socket is DOWN
*Sep 18 15:48:09.146: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 10.255.0.2 NBMA: 2.2.2.2 ) for (Tunnel: 10.255.0.1 NBMA: 1.1.1.1) is DOWN, Reason: External(NHRP: no error)
*Sep 18 15:48:17.930: %DMVPN-5-NHRP_NHP_DOWN: Tunnel0: Next Hop Peer : (Tunnel: 10.255.0.4 NBMA: 4.4.4.4) for (Tunnel: 10.255.0.1 NBMA: 1.1.1.1) is DOWN, Reason: Expiry(NHRP: no error)
*Sep 18 15:48:17.931: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 1.1.1.1 remote address : 4.4.4.4 socket is DOWN
*Sep 18 15:48:22.723: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.255.0.2 (Tunnel0) is down: holding time expired
*Sep 18 15:49:46.605: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Purge Request , Reason:  protocol generic error (7) on (Tunnel: 10.255.0.1 NBMA: 1.1.1.1)
*Sep 18 15:49:46.765: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Purge Request , Reason:  protocol generic error (7) on (Tunnel: 10.255.0.1 NBMA: 1.1.1.1)
*Sep 18 15:52:24.693: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is OFF
*Sep 18 15:52:28.222: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON
*Sep 18 15:52:35.839: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 10.255.0.2 NBMA: 2.2.2.2 ) for (Tunnel: 10.255.0.1 NBMA: 1.1.1.1) is DOWN, Reason: NHRP Registration Failure(NHRP: no error)
```

**P7g-2 hub 復旧**

```
interface Tunnel0
ip nhrp map multicast dynamic
exit
---
(応答なし)
```

**P7g-2 hub show ip nhrp multicast**

```
  I/F     NBMA address
```

**P7g-2 hub show ip eigrp neighbors**

```
EIGRP-IPv4 Neighbors for AS(100)
```

## P7x shared 再測＋P7g 再測  (2026-09-18 16:00)

**P7x-0 hub 復旧 show dmvpn (3 UP after 30.933059692382812s)**

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
     1 1.1.1.1              10.255.0.1    UP 00:00:10     D
     1 3.3.3.3              10.255.0.3    UP 00:00:03     D
     1 4.4.4.4              10.255.0.4    UP 00:00:00     D
```

**P7x-f1 hub Tunnel1(同一 source・同一 profile・shared 無し) — console 全文**

```
interface Tunnel1
ip address 10.254.0.2 255.255.255.0
tunnel source Loopback0
tunnel mode gre multipoint
tunnel key 200
tunnel protection ipsec profile IPSEC-POC
exit
---
interface Tunnel1
ip address 10.254.0.2 255.255.255.0
tunnel source Loopback0
tunnel mode gre multipoint
tunnel key 200
tunnel protection ipsec profile IPSEC-POC
Error: All Tunnel interfaces having the same Tunnel Source [, same Tunnel Destination for p2p] and the same IPsec profile must be configured with the 'shared' keyword
Conflict between Tunnel1 and Tunnel0

exit
```

**P7x-f1 hub show run int Tunnel1**

```
Building configuration...

Current configuration : 148 bytes
!
interface Tunnel1
 ip address 10.254.0.2 255.255.255.0
 no ip redirects
 tunnel source Loopback0
 tunnel mode gre multipoint
 tunnel key 200
end
```

**P7x-f2 hub Tunnel1 に shared(Tunnel0 は shared 無し) — console 全文**

```
interface Tunnel1
tunnel protection ipsec profile IPSEC-POC shared
exit
---
interface Tunnel1
tunnel protection ipsec profile IPSEC-POC shared
Error: All Tunnel interfaces having the same Tunnel Source [, same Tunnel Destination for p2p] and the same IPsec profile must be configured with the 'shared' keyword
Conflict between Tunnel1 and Tunnel0

exit
```

**P7x-f2 hub show run int Tunnel1**

```
Building configuration...

Current configuration : 148 bytes
!
interface Tunnel1
 ip address 10.254.0.2 255.255.255.0
 no ip redirects
 tunnel source Loopback0
 tunnel mode gre multipoint
 tunnel key 200
end
```

**P7x-f3 hub Tunnel0 に shared — console 全文(自動 shutdown の警告)**

```
interface Tunnel0
tunnel protection ipsec profile IPSEC-POC shared
exit
---
interface Tunnel0
tunnel protection ipsec profile IPSEC-POC shared
%Shutting down Tunnel0 interface due to IPsec tunnel protection modification.
%Please run "no shutdown" after config change to bring up the interface.
exit
```

**P7x-f3 hub show dmvpn (Tunnel0 shared・3 UP after 0.2683229446411133s)**

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
     1 1.1.1.1              10.255.0.1    UP 00:00:14     D
     1 3.3.3.3              10.255.0.3    UP 00:00:07     D
     1 4.4.4.4              10.255.0.4    UP 00:00:04     D
```

**P7x-f3 hub show crypto socket**

```

Number of Crypto Socket connections 3

   Shd Peers (local/remote): 2.2.2.2/1.1.1.1 
       Local Ident  (addr/mask/port/prot): (2.2.2.2/255.255.255.255/0/47)
       Remote Ident (addr/mask/port/prot): (1.1.1.1/255.255.255.255/0/47)
       Flags: shared
       IPSec Profile: "IPSEC-POC"
       Socket State: Open
       Client: "TUNNEL SEC" (Client State: Active)
   Shd Peers (local/remote): 2.2.2.2/3.3.3.3 
       Local Ident  (addr/mask/port/prot): (2.2.2.2/255.255.255.255/0/47)
       Remote Ident (addr/mask/port/prot): (3.3.3.3/255.255.255.255/0/47)
       Flags: shared
       IPSec Profile: "IPSEC-POC"
       Socket State: Open
       Client: "TUNNEL SEC" (Client State: Active)
   Shd Peers (local/remote): 2.2.2.2/4.4.4.4 
       Local Ident  (addr/mask/port/prot): (2.2.2.2/255.255.255.255/0/47)
       Remote Ident (addr/mask/port/prot): (4.4.4.4/255.255.255.255/0/47)
       Flags: shared
       IPSec Profile: "IPSEC-POC"
       Socket State: Open
       Client: "TUNNEL SEC" (Client State: Active)
Crypto Sockets in Listen state:
Client: "TUNNEL SEC" Profile: "IPSEC-POC" Map-name: "IPSEC-POC-head-1-IPv4"
```

**P7x-f3 hub show run int Tunnel1**

```
Building configuration...

Current configuration : 148 bytes
!
interface Tunnel1
 ip address 10.254.0.2 255.255.255.0
 no ip redirects
 tunnel source Loopback0
 tunnel mode gre multipoint
 tunnel key 200
end
```

**P7x-f4 hub Tunnel1 に shared(Tunnel0 も shared) — console 全文**

```
interface Tunnel1
tunnel protection ipsec profile IPSEC-POC shared
exit
---
interface Tunnel1
tunnel protection ipsec profile IPSEC-POC shared
exit
```

**P7x-f4 hub show run int Tunnel1**

```
Building configuration...

Current configuration : 198 bytes
!
interface Tunnel1
 ip address 10.254.0.2 255.255.255.0
 no ip redirects
 tunnel source Loopback0
 tunnel mode gre multipoint
 tunnel key 200
 tunnel protection ipsec profile IPSEC-POC shared
end
```

**P7x-f4 hub show crypto socket**

```

Number of Crypto Socket connections 3

   Shd Peers (local/remote): 2.2.2.2/1.1.1.1 
       Local Ident  (addr/mask/port/prot): (2.2.2.2/255.255.255.255/0/47)
       Remote Ident (addr/mask/port/prot): (1.1.1.1/255.255.255.255/0/47)
       Flags: shared
       IPSec Profile: "IPSEC-POC"
       Socket State: Open
       Client: "TUNNEL SEC" (Client State: Active)
   Shd Peers (local/remote): 2.2.2.2/3.3.3.3 
       Local Ident  (addr/mask/port/prot): (2.2.2.2/255.255.255.255/0/47)
       Remote Ident (addr/mask/port/prot): (3.3.3.3/255.255.255.255/0/47)
       Flags: shared
       IPSec Profile: "IPSEC-POC"
       Socket State: Open
       Client: "TUNNEL SEC" (Client State: Active)
   Shd Peers (local/remote): 2.2.2.2/4.4.4.4 
       Local Ident  (addr/mask/port/prot): (2.2.2.2/255.255.255.255/0/47)
       Remote Ident (addr/mask/port/prot): (4.4.4.4/255.255.255.255/0/47)
       Flags: shared
       IPSec Profile: "IPSEC-POC"
       Socket State: Open
       Client: "TUNNEL SEC" (Client State: Active)
Crypto Sockets in Listen state:
Client: "TUNNEL SEC" Profile: "IPSEC-POC" Map-name: "IPSEC-POC-head-1-IPv4"
```

**P7x-f4 hub show ip interface brief | include Tunnel**

```
Tunnel0                10.255.0.2      YES manual up                    up      
Tunnel1                10.254.0.2      YES manual up                    up
```

**P7x-f4 ping RT01 LAN→hub LAN(両 Tunnel shared) — RT01# ping 192.168.2.1 repeat 3 source 192.168.1.1 → 100%**

```
Type escape sequence to abort.
Sending 3, 100-byte ICMP Echos to 192.168.2.1, timeout is 2 seconds:
Packet sent with a source address of 192.168.1.1 
!!!
Success rate is 100 percent (3/3), round-trip min/avg/max = 1/1/1 ms
```

**P7x-f5 hub Tunnel1 を shared 無しに戻す(Tunnel0 は shared) — console 全文**

```
interface Tunnel1
tunnel protection ipsec profile IPSEC-POC
exit
---
interface Tunnel1
tunnel protection ipsec profile IPSEC-POC
%Shutting down Tunnel1 interface due to IPsec tunnel protection modification.
%Please run "no shutdown" after config change to bring up the interface.Error: All Tunnel interfaces having the same Tunnel Source [, same Tunnel Destination for p2p] and the same IPsec profile must be configured with the 'shared' keyword
Conflict between Tunnel1 and Tunnel0

exit
```

**P7x-f5 hub show run int Tunnel1**

```
Building configuration...

Current configuration : 208 bytes
!
interface Tunnel1
 ip address 10.254.0.2 255.255.255.0
 no ip redirects
 shutdown
 tunnel source Loopback0
 tunnel mode gre multipoint
 tunnel key 200
 tunnel protection ipsec profile IPSEC-POC shared
end
```

**P7x-f6 hub Tunnel1 に別 profile IPSEC-POC2(shared 無し) — console 全文**

```
interface Tunnel1
tunnel protection ipsec profile IPSEC-POC2
exit
---
interface Tunnel1
tunnel protection ipsec profile IPSEC-POC2
exit
```

**P7x-f6 hub show run int Tunnel1**

```
Building configuration...

Current configuration : 202 bytes
!
interface Tunnel1
 ip address 10.254.0.2 255.255.255.0
 no ip redirects
 shutdown
 tunnel source Loopback0
 tunnel mode gre multipoint
 tunnel key 200
 tunnel protection ipsec profile IPSEC-POC2
end
```

**P7x-f6 hub show crypto socket**

```

Number of Crypto Socket connections 3

   Shd Peers (local/remote): 2.2.2.2/1.1.1.1 
       Local Ident  (addr/mask/port/prot): (2.2.2.2/255.255.255.255/0/47)
       Remote Ident (addr/mask/port/prot): (1.1.1.1/255.255.255.255/0/47)
       Flags: shared
       IPSec Profile: "IPSEC-POC"
       Socket State: Open
       Client: "TUNNEL SEC" (Client State: Active)
   Shd Peers (local/remote): 2.2.2.2/3.3.3.3 
       Local Ident  (addr/mask/port/prot): (2.2.2.2/255.255.255.255/0/47)
       Remote Ident (addr/mask/port/prot): (3.3.3.3/255.255.255.255/0/47)
       Flags: shared
       IPSec Profile: "IPSEC-POC"
       Socket State: Open
       Client: "TUNNEL SEC" (Client State: Active)
   Shd Peers (local/remote): 2.2.2.2/4.4.4.4 
       Local Ident  (addr/mask/port/prot): (2.2.2.2/255.255.255.255/0/47)
       Remote Ident (addr/mask/port/prot): (4.4.4.4/255.255.255.255/0/47)
       Flags: shared
       IPSec Profile: "IPSEC-POC"
       Socket State: Open
       Client: "TUNNEL SEC" (Client State: Active)
Crypto Sockets in Listen state:
Client: "TUNNEL SEC" Profile: "IPSEC-POC" Map-name: "IPSEC-POC-head-1-IPv4"
```

**P7x-f7 hub 後片付け(Tunnel1 削除・Tunnel0 shared 解除) — console 全文**

```
no interface Tunnel1
interface Tunnel0
tunnel protection ipsec profile IPSEC-POC
no shutdown
exit
no crypto ipsec profile IPSEC-POC2
---
no interface Tunnel1
interface Tunnel0
tunnel protection ipsec profile IPSEC-POC
%Shutting down Tunnel0 interface due to IPsec tunnel protection modification.
%Please run "no shutdown" after config change to bring up the interface.
no shutdown
exit
no crypto ipsec profile IPSEC-POC2
```

**P7x-f7 hub show dmvpn (3 UP after 0.27366065979003906s)**

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
     1 1.1.1.1              10.255.0.1    UP 00:00:36     D
     1 3.3.3.3              10.255.0.3    UP 00:00:29     D
     1 4.4.4.4              10.255.0.4    UP 00:00:26     D
```

**P7x-g1 hub no ip nhrp map multicast dynamic**

```
interface Tunnel0
no ip nhrp map multicast dynamic
exit
---
(応答なし)
```

**P7x-g1 hub show running-config interface Tunnel0 | include nhrp**

```
 ip nhrp authentication DMVPNKEY
 no ip nhrp map multicast dynamic
 ip nhrp network-id 1
 ip nhrp redirect
```

**P7x-g1 hub show ip nhrp multicast**

```
  I/F     NBMA address
```

**P7x-g1 hub show ip eigrp neighbors**

```
EIGRP-IPv4 Neighbors for AS(100)
H   Address                 Interface              Hold Uptime   SRTT   RTO  Q  Seq
                                                   (sec)         (ms)       Cnt Num
2   10.255.0.3              Tu0                      13 00:01:02    1  5000  1  0
1   10.255.0.4              Tu0                      13 00:01:02    1  5000  1  0
0   10.255.0.1              Tu0                      14 00:01:57   12  5000  1  23
```

**P7x-g1 hub show dmvpn**

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
     1 1.1.1.1              10.255.0.1    UP 00:01:15     D
     1 3.3.3.3              10.255.0.3    UP 00:01:50     D
     1 4.4.4.4              10.255.0.4    UP 00:01:48     D
```

**P7x-g1 RT01 show ip eigrp neighbors**

```
EIGRP-IPv4 Neighbors for AS(100)
```

**P7x-g1 RT01 show ip route eigrp | include D **

```
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area
```

**P7x-g1 RT01 show dmvpn**

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
     1 2.2.2.2              10.255.0.2    UP 00:01:16     S
```

**P7x-g1 ping RT01 LAN→hub LAN — RT01# ping 192.168.2.1 repeat 3 source 192.168.1.1 → 100%**

```
Type escape sequence to abort.
Sending 3, 100-byte ICMP Echos to 192.168.2.1, timeout is 2 seconds:
Packet sent with a source address of 192.168.1.1 
!!!
Success rate is 100 percent (3/3), round-trip min/avg/max = 1/1/1 ms
```

**P7x-g1 RT01 — RT01 show logging**

```
*Sep 18 15:38:00.558: %DMVPN-5-NHRP_NHP_UP: Tunnel0: Next Hop NHP : (Tunnel: 10.255.0.2 NBMA: 2.2.2.2) for (Tunnel: 10.255.0.1 NBMA: UNKNOWN) is UP
*Sep 18 15:38:00.558: %DMVPN-5-NHRP_NHP_DOWN: Tunnel0: Next Hop Peer : (Tunnel: 10.255.0.2 NBMA: 2.2.2.2) for (Tunnel: 10.255.0.1 NBMA: UNKNOWN) is DOWN, Reason: administratively prohibited(NHRP: no error)
*Sep 18 15:38:00.859: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 10.255.0.2 NBMA: 2.2.2.2 ) for (Tunnel: 10.255.0.1 NBMA: 1.1.1.1) is DOWN, Reason: External(NHRP: no error)
*Sep 18 15:38:00.859: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Registration Request , Reason:  protocol generic error (7) on (Tunnel: 10.255.0.1 NBMA: 1.1.1.1)
*Sep 18 15:38:01.076: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 1.1.1.1 remote address : 2.2.2.2 socket is UP
*Sep 18 15:38:01.078: %DMVPN-5-NHRP_NHS_UP: Tunnel0: Next Hop Server : (Tunnel: 10.255.0.2 NBMA: 2.2.2.2) for (Tunnel: 10.255.0.1 NBMA: 1.1.1.1) is  UP
*Sep 18 15:38:07.942: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.255.0.2 (Tunnel0) is up: new adjacency
*Sep 18 15:38:17.927: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 1.1.1.1 remote address : 4.4.4.4 socket is UP
*Sep 18 15:38:17.929: %DMVPN-5-NHRP_NHP_UP: Tunnel0: Next Hop NHP : (Tunnel: 10.255.0.4 NBMA: 4.4.4.4) for (Tunnel: 10.255.0.1 NBMA: 1.1.1.1) is UP
*Sep 18 15:38:17.929: %DMVPN-7-NHRP_RES:  Tunnel0: Host with (Tunnel: 10.255.0.1 NBMA: 1.1.1.1) Received Resolution Req from  (Tunnel: 10.255.0.4 NBMA: 4.4.4.4)
*Sep 18 15:39:45.814: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 1.1.1.1 remote address : 3.3.3.3 socket is UP
*Sep 18 15:39:45.815: %DMVPN-5-NHRP_NHP_UP: Tunnel0: Next Hop NHP : (Tunnel: 10.255.0.3 NBMA: 3.3.3.3) for (Tunnel: 10.255.0.1 NBMA: 1.1.1.1) is UP
*Sep 18 15:39:45.815: %DMVPN-7-NHRP_RES:  Tunnel0: Host with (Tunnel: 10.255.0.1 NBMA: 1.1.1.1) Received Resolution Req from  (Tunnel: 10.255.0.3 NBMA: 3.3.3.3)
*Sep 18 15:39:48.516: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 1.1.1.1 remote address : 3.3.3.3 socket is DOWN
*Sep 18 15:39:48.519: %DMVPN-5-NHRP_NHP_DOWN: Tunnel0: Next Hop Peer : (Tunnel: 10.255.0.3 NBMA: 3.3.3.3) for (Tunnel: 10.255.0.1 NBMA: 1.1.1.1) is DOWN, Reason: External(NHRP: no error)
*Sep 18 15:48:09.146: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 1.1.1.1 remote address : 2.2.2.2 socket is DOWN
*Sep 18 15:48:09.146: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 10.255.0.2 NBMA: 2.2.2.2 ) for (Tunnel: 10.255.0.1 NBMA: 1.1.1.1) is DOWN, Reason: External(NHRP: no error)
*Sep 18 15:48:17.930: %DMVPN-5-NHRP_NHP_DOWN: Tunnel0: Next Hop Peer : (Tunnel: 10.255.0.4 NBMA: 4.4.4.4) for (Tunnel: 10.255.0.1 NBMA: 1.1.1.1) is DOWN, Reason: Expiry(NHRP: no error)
*Sep 18 15:48:17.931: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 1.1.1.1 remote address : 4.4.4.4 socket is DOWN
*Sep 18 15:48:22.723: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.255.0.2 (Tunnel0) is down: holding time expired
*Sep 18 15:49:46.605: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Purge Request , Reason:  protocol generic error (7) on (Tunnel: 10.255.0.1 NBMA: 1.1.1.1)
*Sep 18 15:49:46.765: %DMVPN-3-DMVPN_NHRP_ERROR:  Tunnel0: NHRP Encap Error for  Purge Request , Reason:  protocol generic error (7) on (Tunnel: 10.255.0.1 NBMA: 1.1.1.1)
*Sep 18 15:52:35.839: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 10.255.0.2 NBMA: 2.2.2.2 ) for (Tunnel: 10.255.0.1 NBMA: 1.1.1.1) is DOWN, Reason: NHRP Registration Failure(NHRP: no error)
*Sep 18 15:53:43.903: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 10.255.0.2 NBMA: 2.2.2.2 ) for (Tunnel: 10.255.0.1 NBMA: 1.1.1.1) is DOWN, Reason: NHRP Registration Failure(NHRP: no error)
*Sep 18 15:57:36.584: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 1.1.1.1 remote address : 2.2.2.2 socket is UP
*Sep 18 15:57:36.587: %DMVPN-5-NHRP_NHS_UP: Tunnel0: Next Hop Server : (Tunnel: 10.255.0.2 NBMA: 2.2.2.2) for (Tunnel: 10.255.0.1 NBMA: 1.1.1.1) is  UP
*Sep 18 15:57:37.020: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.255.0.2 (Tunnel0) is up: new adjacency
*Sep 18 15:57:49.950: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 1.1.1.1 remote address : 2.2.2.2 socket is DOWN
*Sep 18 15:57:49.950: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 10.255.0.2 NBMA: 2.2.2.2 ) for (Tunnel: 10.255.0.1 NBMA: 1.1.1.1) is DOWN, Reason: External(NHRP: no error)
*Sep 18 15:57:50.557: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 1.1.1.1 remote address : 2.2.2.2 socket is UP
*Sep 18 15:57:51.314: %DMVPN-5-NHRP_NHS_UP: Tunnel0: Next Hop Server : (Tunnel: 10.255.0.2 NBMA: 2.2.2.2) for (Tunnel: 10.255.0.1 NBMA: 1.1.1.1) is  UP
*Sep 18 15:58:06.970: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 1.1.1.1 remote address : 2.2.2.2 socket is DOWN
*Sep 18 15:58:06.970: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 10.255.0.2 NBMA: 2.2.2.2 ) for (Tunnel: 10.255.0.1 NBMA: 1.1.1.1) is DOWN, Reason: External(NHRP: no error)
*Sep 18 15:58:07.071: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 1.1.1.1 remote address : 2.2.2.2 socket is UP
*Sep 18 15:58:07.881: %DMVPN-5-NHRP_NHS_UP: Tunnel0: Next Hop Server : (Tunnel: 10.255.0.2 NBMA: 2.2.2.2) for (Tunnel: 10.255.0.1 NBMA: 1.1.1.1) is  UP
*Sep 18 15:58:14.656: %DMVPN-5-NHRP_NHS_DOWN: Tunnel0: Next Hop Server : (Tunnel: 10.255.0.2 NBMA: 2.2.2.2 ) for (Tunnel: 10.255.0.1 NBMA: 1.1.1.1) is DOWN, Reason: External(NHRP: no error)
*Sep 18 15:58:14.656: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 1.1.1.1 remote address : 2.2.2.2 socket is DOWN
*Sep 18 15:58:14.657: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.255.0.2 (Tunnel0) is down: interface down
*Sep 18 15:58:18.295: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 1.1.1.1 remote address : 2.2.2.2 socket is UP
*Sep 18 15:58:19.256: %DMVPN-5-NHRP_NHS_UP: Tunnel0: Next Hop Server : (Tunnel: 10.255.0.2 NBMA: 2.2.2.2) for (Tunnel: 10.255.0.1 NBMA: 1.1.1.1) is  UP
```

**P7x-g1 hub — RT02 show logging**

```
*Sep 18 15:48:09.144: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 1.1.1.1 socket is DOWN
*Sep 18 15:48:09.144: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 4.4.4.4 socket is DOWN
*Sep 18 15:48:09.144: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 3.3.3.3 socket is DOWN
*Sep 18 15:48:11.145: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 10.255.0.1 NBMA: 1.1.1.1 ) for (Tunnel: 10.255.0.2 NBMA: 2.2.2.2) is DOWN, Reason: External(NHRP: no error)
*Sep 18 15:48:11.145: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 10.255.0.3 NBMA: 3.3.3.3 ) for (Tunnel: 10.255.0.2 NBMA: 2.2.2.2) is DOWN, Reason: External(NHRP: no error)
*Sep 18 15:48:11.145: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 10.255.0.4 NBMA: 4.4.4.4 ) for (Tunnel: 10.255.0.2 NBMA: 2.2.2.2) is DOWN, Reason: External(NHRP: no error)
*Sep 18 15:48:11.146: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.255.0.3 (Tunnel0) is down: interface down
*Sep 18 15:48:11.146: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.255.0.4 (Tunnel0) is down: interface down
*Sep 18 15:48:11.146: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.255.0.1 (Tunnel0) is down: interface down
*Sep 18 15:57:36.583: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 1.1.1.1 socket is UP
*Sep 18 15:57:36.586: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 10.255.0.1 NBMA: 1.1.1.1) for (Tunnel: 10.255.0.2 NBMA: 2.2.2.2) is UP
*Sep 18 15:57:37.022: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.255.0.1 (Tunnel0) is up: new adjacency
*Sep 18 15:57:43.829: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 3.3.3.3 socket is UP
*Sep 18 15:57:43.831: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 10.255.0.3 NBMA: 3.3.3.3) for (Tunnel: 10.255.0.2 NBMA: 2.2.2.2) is UP
*Sep 18 15:57:46.233: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 4.4.4.4 socket is UP
*Sep 18 15:57:46.236: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 10.255.0.4 NBMA: 4.4.4.4) for (Tunnel: 10.255.0.2 NBMA: 2.2.2.2) is UP
*Sep 18 15:57:47.612: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.255.0.4 (Tunnel0) is up: new adjacency
*Sep 18 15:57:47.615: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.255.0.3 (Tunnel0) is up: new adjacency
*Sep 18 15:57:49.943: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 1.1.1.1 socket is DOWN
*Sep 18 15:57:49.943: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 3.3.3.3 socket is DOWN
*Sep 18 15:57:49.943: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 4.4.4.4 socket is DOWN
*Sep 18 15:57:50.564: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 1.1.1.1 socket is UP
*Sep 18 15:57:50.564: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 3.3.3.3 socket is UP
*Sep 18 15:57:50.565: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 4.4.4.4 socket is UP
*Sep 18 15:58:06.962: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 1.1.1.1 socket is DOWN
*Sep 18 15:58:06.962: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 3.3.3.3 socket is DOWN
*Sep 18 15:58:06.962: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 4.4.4.4 socket is DOWN
*Sep 18 15:58:07.078: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 1.1.1.1 socket is UP
*Sep 18 15:58:07.078: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 3.3.3.3 socket is UP
*Sep 18 15:58:07.079: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 4.4.4.4 socket is UP
*Sep 18 15:58:14.665: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 1.1.1.1 socket is DOWN
*Sep 18 15:58:14.672: %DMVPN-5-NHRP_NHC_DOWN: Tunnel0: Next Hop Client : (Tunnel: 10.255.0.1 NBMA: 1.1.1.1 ) for (Tunnel: 10.255.0.2 NBMA: 2.2.2.2) is DOWN, Reason: External(NHRP: no error)
*Sep 18 15:58:18.295: %DMVPN-5-CRYPTO_SS:  Tunnel0: local address : 2.2.2.2 remote address : 1.1.1.1 socket is UP
*Sep 18 15:58:19.255: %DMVPN-5-NHRP_NHC_UP: Tunnel0: Next Hop Client : (Tunnel: 10.255.0.1 NBMA: 1.1.1.1) for (Tunnel: 10.255.0.2 NBMA: 2.2.2.2) is UP
*Sep 18 15:58:27.461: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.255.0.4 (Tunnel0) is down: Interface PEER-TERMINATION received
*Sep 18 15:58:27.461: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.255.0.3 (Tunnel0) is down: Interface PEER-TERMINATION received
*Sep 18 15:58:31.756: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.255.0.4 (Tunnel0) is up: new adjacency
*Sep 18 15:58:32.131: %DUAL-5-NBRCHANGE: EIGRP-IPv4 100: Neighbor 10.255.0.3 (Tunnel0) is up: new adjacency
```

**P7x-g2 hub 復旧**

```
interface Tunnel0
ip nhrp map multicast dynamic
exit
---
(応答なし)
```

**P7x-g2 hub show ip nhrp multicast**

```
  I/F     NBMA address  
Tunnel0    1.1.1.1         Flags: dynamic          (Enabled)
Tunnel0    3.3.3.3         Flags: dynamic          (Enabled)
```

**P7x-g2 hub show ip eigrp neighbors**

```
EIGRP-IPv4 Neighbors for AS(100)
H   Address                 Interface              Hold Uptime   SRTT   RTO  Q  Seq
                                                   (sec)         (ms)       Cnt Num
2   10.255.0.4              Tu0                      13 00:00:47    1  5000  1  0
1   10.255.0.3              Tu0                      13 00:00:51    2  1362  0  31
0   10.255.0.1              Tu0                      12 00:00:55    4  1362  0  26
```

**P7x-g2 RT01 show ip eigrp neighbors**

```
EIGRP-IPv4 Neighbors for AS(100)
H   Address                 Interface              Hold Uptime   SRTT   RTO  Q  Seq
                                                   (sec)         (ms)       Cnt Num
0   10.255.0.2              Tu0                      13 00:00:56   13  1398  0  54
```

## P9 LDP DU 表示・AD 同値  (2026-09-18 16:03)

**P9a LDP 有効化 RT01**

```
mpls label protocol ldp
mpls ldp router-id Loopback0 force
interface Ethernet0/0
mpls ip
exit
---
(応答なし)
```

**P9a LDP 有効化 RT02**

```
mpls label protocol ldp
mpls ldp router-id Loopback0 force
interface Ethernet0/0
mpls ip
exit
---
(応答なし)
```

**P9a RT01 show mpls ldp neighbor (Oper after 0.37764954566955566s)**

```
    Peer LDP Ident: 2.2.2.2:0; Local LDP Ident 1.1.1.1:0
	TCP connection: 2.2.2.2.43444 - 1.1.1.1.646
	State: Oper; Msgs sent/rcvd: 10/14; Downstream
	Up time: 00:00:00
	LDP discovery sources:
	  Ethernet0/0, Src IP addr: 10.0.12.2
        Addresses bound to peer LDP Ident:
          10.0.12.2       10.0.23.2       2.2.2.2         192.168.2.1     
          10.255.0.2
```

**P9a RT01**

```
    Peer LDP Ident: 2.2.2.2:0; Local LDP Ident 1.1.1.1:0
	TCP connection: 2.2.2.2.43444 - 1.1.1.1.646
	Password: not required, none, in use
	State: Oper; Msgs sent/rcvd: 10/14; Downstream; Last TIB rev sent 14
	Up time: 00:00:00; UID: 1; Peer Id 0
	LDP discovery sources:
	  Ethernet0/0; Src IP addr: 10.0.12.2 
	    holdtime: 15000 ms, hello interval: 5000 ms
        Addresses bound to peer LDP Ident:
          10.0.12.2       10.0.23.2       2.2.2.2         192.168.2.1     
          10.255.0.2      
	Peer holdtime: 180000 ms; KA interval: 60000 ms; Peer state: estab
	NSR: Not Ready
	Capabilities Sent:
	  [ICCP (type 0x0405) MajVer 1 MinVer 0]
	  [Dynamic Announcement (0x0506)]
	  [mLDP Point-to-Multipoint (0x0508)]
	  [mLDP Multipoint-to-Multipoint (0x0509)]
	  [Typed Wildcard (0x050B)]
	Capabilities Received:
	  [ICCP (type 0x0405) MajVer 1 MinVer 0]
	  [Dynamic Announcement (0x0506)]
	  [mLDP Point-to-Multipoint (0x0508)]
	  [mLDP Multipoint-to-Multipoint (0x0509)]
	  [Typed Wildcard (0x050B)]
```

**P9a RT01**

```
LDP Feature Set Manager: State Initialized
  LDP features:
    Auto-Configuration
    Basic
    ICPM
    IP-over-MPLS
    IGP-Sync
    LLAF
    TCP-MD5-Rollover
    TDP
    NSR
Protocol version: 1
Session hold time: 180 sec; keep alive interval: 60 sec
Discovery hello: holdtime: 15 sec; interval: 5 sec
Discovery targeted hello: holdtime: 90 sec; interval: 10 sec
Downstream on Demand max hop count: 255
LDP for targeted sessions
LDP initial/maximum backoff: 15/120 sec
LDP loop detection: off
LDP NSR: Disabled
```

**P9a RT01**

```
 Local LDP Identifier:
    1.1.1.1:0
    Discovery Sources:
    Interfaces:
	Ethernet0/0 (ldp): xmit/recv
	    Enabled: Interface config
	    Hello interval: 5000 ms; Transport IP addr: 1.1.1.1
	    LDP Id: 2.2.2.2:0; no host route to transport addr
	      Src IP addr: 10.0.12.2; Transport IP addr: 2.2.2.2
	      Hold time: 15 sec; Proposed local/peer: 15/15 sec
	      Reachable via 0.0.0.0/0
	      Password: not required, none, in use
            Clients: IPv4, mLDP
```

**P9a RT01**

```
Interface Ethernet0/0:
	Type Unknown
	IP labeling enabled (ldp) :
	  Interface config
	LSP Tunnel labeling not enabled
	IP FRR labeling not enabled
	BGP labeling not enabled
	MPLS operational
	MTU = 1500
```

**P9a RT01**

```
  lib entry: 0.0.0.0/0, rev 2
	local binding:  label: imp-null
  lib entry: 1.1.1.1/32, rev 4
	local binding:  label: imp-null
	remote binding: lsr: 2.2.2.2:0, label: 16
  lib entry: 2.2.2.2/32, rev 15
	no local binding
	remote binding: lsr: 2.2.2.2:0, label: imp-null
  lib entry: 3.3.3.3/32, rev 16
	no local binding
	remote binding: lsr: 2.2.2.2:0, label: 17
  lib entry: 4.4.4.4/32, rev 17
	no local binding
	remote binding: lsr: 2.2.2.2:0, label: 18
  lib entry: 10.0.12.0/24, rev 6
	local binding:  label: imp-null
	remote binding: lsr: 2.2.2.2:0, label: imp-null
  lib entry: 10.0.23.0/24, rev 18
	no local binding
	remote binding: lsr: 2.2.2.2:0, label: imp-null
  lib entry: 10.0.34.0/24, rev 19
	no local binding
	remote binding: lsr: 2.2.2.2:0, label: 19
  lib entry: 10.255.0.0/24, rev 8
	local binding:  label: imp-null
	remote binding: lsr: 2.2.2.2:0, label: imp-null
  lib entry: 192.168.1.0/24, rev 10
	local binding:  label: imp-null
	remote binding: lsr: 2.2.2.2:0, label: 20
  lib entry: 192.168.2.0/24, rev 12
	local binding:  label: 16
	remote binding: lsr: 2.2.2.2:0, label: imp-null
  lib entry: 192.168.3.0/24, rev 14
	local binding:  label: 17
	remote binding: lsr: 2.2.2.2:0, label: 21
```

**P9a RT01**

```
Local      Outgoing   Prefix           Bytes Label   Outgoing   Next Hop    
Label      Label      or Tunnel Id     Switched      interface              
16         No Label   192.168.2.0/24   0             Tu0        10.255.0.2  
17         No Label   192.168.3.0/24   0             Tu0        10.255.0.2
```

**P9a RT01**

```
  0.0.0.0/0 
	in label:     imp-null  
  1.1.1.1/32 
	in label:     imp-null  
	out label:    16        lsr: 2.2.2.2:0       
  2.2.2.2/32 
	no local binding
	out label:    imp-null  lsr: 2.2.2.2:0       
  3.3.3.3/32 
	no local binding
	out label:    17        lsr: 2.2.2.2:0       
  4.4.4.4/32 
	no local binding
	out label:    18        lsr: 2.2.2.2:0       
  10.0.12.0/24 
	in label:     imp-null  
	out label:    imp-null  lsr: 2.2.2.2:0       
  10.0.23.0/24 
	no local binding
	out label:    imp-null  lsr: 2.2.2.2:0       
  10.0.34.0/24 
	no local binding
	out label:    19        lsr: 2.2.2.2:0       
  10.255.0.0/24 
	in label:     imp-null  
	out label:    imp-null  lsr: 2.2.2.2:0       
  192.168.1.0/24 
	in label:     imp-null  
	out label:    20        lsr: 2.2.2.2:0       
  192.168.2.0/24 
	in label:     16        
	out label:    imp-null  lsr: 2.2.2.2:0       
  192.168.3.0/24 
	in label:     17        
	out label:    21        lsr: 2.2.2.2:0
```

**P9a RT01**

```
	State: Oper; Msgs sent/rcvd: 10/14; Downstream
```

**P9a RT02 show mpls ldp neighbor**

```
    Peer LDP Ident: 1.1.1.1:0; Local LDP Ident 2.2.2.2:0
	TCP connection: 1.1.1.1.646 - 2.2.2.2.43444
	State: Oper; Msgs sent/rcvd: 14/10; Downstream
	Up time: 00:00:03
	LDP discovery sources:
	  Ethernet0/0, Src IP addr: 10.0.12.1
        Addresses bound to peer LDP Ident:
          10.0.12.1       1.1.1.1         192.168.1.1     10.255.0.1
```

**P9a RT02 show mpls ldp bindings**

```
  lib entry: 0.0.0.0/0, rev 23
	no local binding
	remote binding: lsr: 1.1.1.1:0, label: imp-null
  lib entry: 1.1.1.1/32, rev 4
	local binding:  label: 16
	remote binding: lsr: 1.1.1.1:0, label: imp-null
  lib entry: 2.2.2.2/32, rev 6
	local binding:  label: imp-null
  lib entry: 3.3.3.3/32, rev 8
	local binding:  label: 17
  lib entry: 4.4.4.4/32, rev 10
	local binding:  label: 18
  lib entry: 10.0.12.0/24, rev 2
	local binding:  label: imp-null
	remote binding: lsr: 1.1.1.1:0, label: imp-null
  lib entry: 10.0.23.0/24, rev 12
	local binding:  label: imp-null
  lib entry: 10.0.34.0/24, rev 14
	local binding:  label: 19
  lib entry: 10.255.0.0/24, rev 16
	local binding:  label: imp-null
	remote binding: lsr: 1.1.1.1:0, label: imp-null
  lib entry: 192.168.1.0/24, rev 18
	local binding:  label: 20
	remote binding: lsr: 1.1.1.1:0, label: imp-null
  lib entry: 192.168.2.0/24, rev 20
	local binding:  label: imp-null
	remote binding: lsr: 1.1.1.1:0, label: 16
  lib entry: 192.168.3.0/24, rev 22
	local binding:  label: 21
	remote binding: lsr: 1.1.1.1:0, label: 17
```

**P9b-0 RT04 show ip route 172.31.3.3 (OSPF のみ・after 41.541643142700195s)**

```
Routing entry for 172.31.3.3/32
  Known via "ospf 9", distance 110, metric 11, type intra area
  Last update from 10.0.34.3 on Ethernet0/0, 00:00:01 ago
  Routing Descriptor Blocks:
  * 10.0.34.3, from 3.3.3.9, 00:00:01 ago, via Ethernet0/0
      Route metric is 11, traffic share count is 1
```

**P9b static AD110 = OSPF 110(同値) 投入**

```
ip route 172.31.3.3 255.255.255.255 10.0.34.3 110
---
(応答なし)
```

**P9b static AD110 = OSPF 110(同値) — RT04 show ip route 172.31.3.3**

```
Routing entry for 172.31.3.3/32
  Known via "static", distance 110, metric 0
  Routing Descriptor Blocks:
  * 10.0.34.3
      Route metric is 0, traffic share count is 1
```

**P9b static AD110 = OSPF 110(同値) — RT04 show ip route | include 172.31.3.3**

```
S        172.31.3.3 [110/0] via 10.0.34.3
```

**P9b static AD110 = OSPF 110(同値) — RT04 show ip route static**

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

Gateway of last resort is 10.0.34.3 to network 0.0.0.0

S*    0.0.0.0/0 [1/0] via 10.0.34.3
      172.31.0.0/32 is subnetted, 1 subnets
S        172.31.3.3 [110/0] via 10.0.34.3
```

**P9b static AD110 = OSPF 110(同値) — RT04 show ip ospf rib 172.31.3.3**

```

            OSPF Router with ID (4.4.4.9) (Process ID 9)


		Base Topology (MTID 0)

OSPF local RIB
Codes: * - Best, > - Installed in global RIB
LSA: type/LSID/originator

*   172.31.3.3/32, Intra, cost 11, area 0
     SPF Instance 4, age 00:00:08
     Flags: HiPrio
      via 10.0.34.3, Ethernet0/0, label 1048578, strict label 1048578
       Flags: none
       LSA: 1/3.3.3.9/3.3.3.9
       Source: 3.3.3.9 (area 0)
```

**P9b static AD110 = OSPF 110(同値) — clear ip route * 後 RT04 show ip route 172.31.3.3**

```
Routing entry for 172.31.3.3/32
  Known via "static", distance 110, metric 0
  Routing Descriptor Blocks:
  * 10.0.34.3
      Route metric is 0, traffic share count is 1
```

**P9b static AD110 = OSPF 110(同値) — OSPF shutdown 中 RT04 show ip route 172.31.3.3**

```
Routing entry for 172.31.3.3/32
  Known via "static", distance 110, metric 0
  Routing Descriptor Blocks:
  * 10.0.34.3
      Route metric is 0, traffic share count is 1
```

**P9b static AD110 = OSPF 110(同値) — OSPF 復帰後 RT04 show ip route 172.31.3.3**

```
Routing entry for 172.31.3.3/32
  Known via "static", distance 110, metric 0
  Routing Descriptor Blocks:
  * 10.0.34.3
      Route metric is 0, traffic share count is 1
```

**P9b static AD109 < 110 投入**

```
ip route 172.31.3.3 255.255.255.255 10.0.34.3 109
---
(応答なし)
```

**P9b static AD109 < 110 — RT04 show ip route 172.31.3.3**

```
Routing entry for 172.31.3.3/32
  Known via "static", distance 109, metric 0
  Routing Descriptor Blocks:
  * 10.0.34.3
      Route metric is 0, traffic share count is 1
```

**P9b static AD109 < 110 — RT04 show ip route | include 172.31.3.3**

```
S        172.31.3.3 [109/0] via 10.0.34.3
```

**P9b static AD109 < 110 — RT04 show ip route static**

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

Gateway of last resort is 10.0.34.3 to network 0.0.0.0

S*    0.0.0.0/0 [1/0] via 10.0.34.3
      172.31.0.0/32 is subnetted, 1 subnets
S        172.31.3.3 [109/0] via 10.0.34.3
```

**P9b static AD109 < 110 — RT04 show ip ospf rib 172.31.3.3**

```

            OSPF Router with ID (4.4.4.9) (Process ID 9)


		Base Topology (MTID 0)

OSPF local RIB
Codes: * - Best, > - Installed in global RIB
LSA: type/LSID/originator

*   172.31.3.3/32, Intra, cost 11, area 0
     SPF Instance 10, age 00:00:06
     Flags: HiPrio
      via 10.0.34.3, Ethernet0/0, label 1048578, strict label 1048578
       Flags: none
       LSA: 1/3.3.3.9/3.3.3.9
       Source: 3.3.3.9 (area 0)
```

**P9b static AD111 > 110 投入**

```
ip route 172.31.3.3 255.255.255.255 10.0.34.3 111
---
(応答なし)
```

**P9b static AD111 > 110 — RT04 show ip route 172.31.3.3**

```
Routing entry for 172.31.3.3/32
  Known via "ospf 9", distance 110, metric 11, type intra area
  Last update from 10.0.34.3 on Ethernet0/0, 00:00:06 ago
  Routing Descriptor Blocks:
  * 10.0.34.3, from 3.3.3.9, 00:00:06 ago, via Ethernet0/0
      Route metric is 11, traffic share count is 1
```

**P9b static AD111 > 110 — RT04 show ip route | include 172.31.3.3**

```
O        172.31.3.3 [110/11] via 10.0.34.3, 00:00:07, Ethernet0/0
```

**P9b static AD111 > 110 — RT04 show ip route static**

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

Gateway of last resort is 10.0.34.3 to network 0.0.0.0

S*    0.0.0.0/0 [1/0] via 10.0.34.3
```

**P9b static AD111 > 110 — RT04 show ip ospf rib 172.31.3.3**

```

            OSPF Router with ID (4.4.4.9) (Process ID 9)


		Base Topology (MTID 0)

OSPF local RIB
Codes: * - Best, > - Installed in global RIB
LSA: type/LSID/originator

*>  172.31.3.3/32, Intra, cost 11, area 0
     SPF Instance 10, age 00:00:06
     Flags: RIB, HiPrio
      via 10.0.34.3, Ethernet0/0, label 1048578, strict label 1048578
       Flags: RIB
       LSA: 1/3.3.3.9/3.3.3.9
       Source: 3.3.3.9 (area 0)
```

**P9b-e0 RT04 show ip route 172.31.3.3 (EIGRP のみ・after 0.3759193420410156s)**

```
Routing entry for 172.31.3.3/32
  Known via "eigrp 200", distance 90, metric 409600, precedence routine (0), type internal
  Redistributing via eigrp 200
  Last update from 10.0.34.3 on Ethernet0/0, 00:00:00 ago
  Routing Descriptor Blocks:
  * 10.0.34.3, from 10.0.34.3, 00:00:00 ago, via Ethernet0/0
      Route metric is 409600, traffic share count is 1
      Total delay is 6000 microseconds, minimum bandwidth is 10000 Kbit
      Reliability 255/255, minimum MTU 1500 bytes
      Loading 1/255, Hops 1
```

**P9b-e static AD90 = EIGRP 90(同値) 投入**

```
ip route 172.31.3.3 255.255.255.255 10.0.34.3 90
---
(応答なし)
```

**P9b-e static AD90 — RT04 show ip route 172.31.3.3**

```
Routing entry for 172.31.3.3/32
  Known via "static", distance 90, metric 0
  Routing Descriptor Blocks:
  * 10.0.34.3
      Route metric is 0, traffic share count is 1
```

**P9b-e static AD90 — RT04 show ip route | include 172.31.3.3**

```
S        172.31.3.3 [90/0] via 10.0.34.3
```

**P9b-e static AD90 — clear 後 RT04 show ip route 172.31.3.3**

```
Routing entry for 172.31.3.3/32
  Known via "static", distance 90, metric 0
  Routing Descriptor Blocks:
  * 10.0.34.3
      Route metric is 0, traffic share count is 1
```
