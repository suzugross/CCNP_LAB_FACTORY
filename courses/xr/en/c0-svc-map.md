# The services side by side — the outer label is the road, the inner label is the container

From M9 to M11 you built four services one at a time: L3VPN, VPWS (E-Line), VPLS and EVPN. All of them "put labels on the
customer's traffic and carry it across the core", so side by side they look alike. Reading them unit by unit, it gets hard to
see how they differ and which piece of configuration belongs to which service.

This page lays the four out on **one topology, with the same pairs of CEs**, and narrows the differences down to a few
questions. Nothing new is introduced.

| Page | Contents |
|---|---|
| This page | How the four services differ: what the customer sees, what the PE learns, how PEs find each other, what the inner label means. Why the RR stays off the road |
| Build order | Building all four in the same five steps. A configuration example and the checks for each step |
| Practice | In lab XRT-13, build five services from a network that has only a core (tasks S-1 to S-5) |
| What EVPN-VPWS buys you | The same E-Line as an LDP pseudowire and as EVPN-VPWS: when a site is on two PEs, and when the road moves to SR |

This page uses the following topology. Label values change from one build to the next.

:::topo
nodes:
  CE1: {at: [0, 0.3], label: "CE1 (site 1)"}
  CE2: {at: [0, 2.9], label: "CE2 (site 2)"}
  XE1: {at: [1.9, 0.3], label: "XE1 (PE)"}
  XE2: {at: [1.9, 2.9], label: "XE2 (PE)"}
  P1: {at: [3.8, 1.6], label: "P1 (P)"}
  RR1: {at: [3.8, 0.3], label: "RR1 (RR)"}
  XE3: {at: [5.7, 0.3], label: "XE3 (PE)"}
  XR01: {at: [5.7, 2.9], label: "XR01 (PE, IOS XR)"}
  CE3: {at: [7.6, 0.3], label: "CE3 (site 3)"}
  CE4: {at: [7.6, 2.9], label: "CE4 (site 4)"}
links:
  - [CE1, XE1, "VLAN 100 130 200 210"]
  - [CE2, XE2, "VLAN 100 140 200 210"]
  - [XE1, P1, ""]
  - [XE2, P1, ""]
  - [P1, XE3, ""]
  - [P1, XR01, ""]
  - [P1, RR1, "IS-IS only"]
  - [XE3, CE3, "VLAN 140 200 210"]
  - [XR01, CE4, "VLAN 100 130"]
frames:
  - {label: "AS 65000 (IS-IS CORE, LDP)", nodes: [XE1, XE2, P1, RR1, XE3, XR01]}
:::

Each CE carries the services on one link, separated by VLAN. Every CE has one subinterface per service.

| VLAN | Service | Sites | CE addresses |
|---|---|---|---|
| 100 | L3VPN (VRF A) | 1, 2, 4 | A subnet per site towards the PE, 172.16.<site>.0/24. The site LAN is 10.100.<site>.0/24 |
| 130 | VPWS (LDP pseudowire) | 1 ⇔ 4 | 192.168.130.<site> |
| 140 | VPWS (EVPN-VPWS) | 2 ⇔ 3 | 192.168.140.<site> |
| 200 | EVPN E-LAN | 1, 2, 3 | 192.168.200.<site> |
| 210 | VPLS | 1, 2, 3 | 192.168.210.<site> |

## 1. Why bother

### 1.1 The problem: the four look the same

All four services follow the same flow. The PE puts a label on traffic it receives from the CE, the P routers carry it by the
label, and the remote PE removes the label and hands the traffic to the CE. The configuration keeps repeating the same words,
too: `l2vpn`, `evpn`, `bgp`, `route-target`.

So when you learn them one by one, they blur. "Does VPLS need BGP?", "Where did the RT go for EVPN?", "How is an L3VPN label
different from a pseudowire label?" become hard to answer once you are across units.

### 1.2 How to read this page: four questions

The differences between the four services show up when you answer four questions.

1. What does the network look like to the customer?
2. What does the PE learn?
3. How does a PE find the other PEs in the same service?
4. What does the inner label point to?

To give the answer first: **the outer label is the same "road" for every service, and every difference lives in the inner
label and the "container" behind it**. The sections below check each question on the topology.

## 2. The four side by side

### 2.1 What the customer sees: a router, a cable or a switch

CE1's ARP table shows the difference straight away.

```console
CE1#show ip arp
Protocol  Address          Age (min)  Hardware Addr   Type   Interface
Internet  172.16.1.254           11   5254.00b5.ceb7  ARPA   Ethernet0/0.100
Internet  192.168.130.4           8   aabb.cc00.8e00  ARPA   Ethernet0/0.130
Internet  192.168.200.2           5   aabb.cc00.8c00  ARPA   Ethernet0/0.200
Internet  192.168.200.3           5   aabb.cc00.8d00  ARPA   Ethernet0/0.200
Internet  192.168.210.2           6   aabb.cc00.8c00  ARPA   Ethernet0/0.210
Internet  192.168.210.3           6   aabb.cc00.8d00  ARPA   Ethernet0/0.210
```

(CE1's own entries are left out.)

- **L3VPN (VLAN 100)**: CE1's neighbour is the PE (XE1's MAC `5254.00b5.ceb7`). CE1 speaks eBGP with XE1 and receives the
  other sites' LANs from XE1 as routes. To the customer the network is **one big router**.
- **VPWS (VLAN 130)**: the neighbour is CE4 at the far site 4 (`aabb.cc00.8e00`). The PE is invisible.
  The network is **one cable**.
- **VPLS (VLAN 210) and EVPN (VLAN 200)**: both CE2 and CE3 are neighbours. Three sites sit on one subnet.
  The network is **one switch**.

With L3VPN each site has its own subnet (172.16.1.0/24, 172.16.2.0/24, …); with the L2 services all sites share one subnet
(192.168.210.0/24). This is where the difference shows: in L3VPN the PE takes part in the routing, and in the L2 services the
PE only carries frames.

```console
CE1#show ip bgp | begin Network
     Network          Next Hop            Metric LocPrf Weight Path
 *>   10.100.1.0/24    0.0.0.0                  0         32768 i
 *>   10.100.2.0/24    172.16.1.254                           0 65000 65002 i
 *>   10.100.4.0/24    172.16.1.254                           0 65000 65004 i
```

On L3VPN, CE1 receives the LANs of sites 2 and 4 both from XE1 (172.16.1.254), through AS 65000. Site 4 sits behind the
IOS XR PE, but CE1 cannot tell.

### 2.2 What the PE learns

Because the customer sees different things, the PE learns different things.

| Service | What the PE learns | Show command (IOS XE) |
|---|---|---|
| L3VPN | The customer's routes (a routing table per VRF) | `show ip route vrf A` |
| VPWS | Nothing. Only that this AC and that pseudowire are a pair | `show l2vpn atom vc` |
| VPLS | MAC addresses, learned from the source of arriving frames | `show bridge-domain 210` |
| EVPN | MAC addresses, taught to each other in BGP | `show l2vpn evpn evi 200 detail`, `show bgp l2vpn evpn route-type 2` |

On L3VPN, XE1 holds the LANs of three sites in VRF A's routing table. Its own site 1 came from CE1 in eBGP; sites 2 and 4
came from the other PEs in iBGP.

```console
XE1#show ip route vrf A | begin Gateway
Gateway of last resort is not set
      10.0.0.0/24 is subnetted, 3 subnets
B        10.100.1.0 [20/0] via 172.16.1.1, 00:02:26
B        10.100.2.0 [200/0] via 10.255.0.42, 00:02:14
B        10.100.4.0 [200/0] via 10.255.0.1, 00:01:32
```

On VPLS, XE1 keeps a MAC table just like a switch. The difference is that the remote sites' MACs sit behind a
**pseudowire**, not a port. XE1 has learned that CE2 (`8c00`) at site 2 is behind the pseudowire to XE2, and CE3 (`8d00`) at
site 3 is behind the pseudowire to XE3.

```console
XE1#show bridge-domain 210
Bridge-domain 210 (3 ports in all)
State: UP                    Mac learning: Enabled
    GigabitEthernet2 service instance 210
    vfi VPLS210 neighbor 10.255.0.42 210
    vfi VPLS210 neighbor 10.255.0.43 210
   AED MAC address    Policy  Tag       Age  Pseudoport
   0   AABB.CC00.8C00 forward dynamic   295  VPLS210.404012, VPLS
                                             VC_LABEL: 27, Intf: GigabitEthernet1
   0   AABB.CC00.8D00 forward dynamic   297  VPLS210.404013, VPLS
                                             VC_LABEL: 26, Intf: GigabitEthernet1
   0   AABB.CC00.8B00 forward dynamic   298  GigabitEthernet2.EFP210
```

On EVPN, XE1 also keeps the MACs in a bridge domain, but the remote MACs arrived **in BGP**, before any frame did. There is
a line per remote PE counting the routes received by type (MAC and MAC/IP are type 2, IMET is type 3).

```console
XE1#show l2vpn evpn evi 200 detail
EVPN instance:       200 (VLAN Based)
  RD:                10.255.0.41:200 (auto)
  Import-RTs:        65000:200
  Export-RTs:        65000:200
  Bridge Domain:     200
    BUM Label:       29
    Per-BD Label:    30
    Pseudoports:
      GigabitEthernet2 service instance 200
        Routes: 1 MAC, 1 MAC/IP
    Peers:
      10.255.0.42
        Routes: 1 MAC, 1 MAC/IP, 1 IMET, 0 EAD
      10.255.0.43
        Routes: 1 MAC, 1 MAC/IP, 1 IMET, 0 EAD
```

VPLS and EVPN both look like a switch to the customer, and both are a bridge domain inside the PE. The only difference is
**how the remote MACs are learned**. VPLS learns them from arriving frames, just as a switch does; EVPN teaches them in BGP.
EVPN multihoming, and knowing a destination before any frame arrives, both grow out of this difference (M11 add-on).

### 2.3 How a PE finds the others: name them, or find each other in BGP

How does a PE know the other PEs that take part in the same service? This is what shapes the configuration most.

| How | Services | What you write | How labels are passed |
|---|---|---|---|
| **Name them** | VPWS (LDP), VPLS | The remote PE's address, inside the container | Targeted LDP between the PEs, set up automatically once written |
| **Find each other in BGP** | L3VPN, EVPN (E-LAN, EVPN-VPWS) | An address family on the iBGP session to the RR, and an RT on the container | Carried on BGP routes |

When you name them, you get one session per PE you name. XE1 runs targeted LDP with three PEs, the pseudowire peer (XR01)
and the VPLS peers (XE2, XE3), on top of the link LDP session with P1.

```console
XE1#show mpls ldp neighbor | include Peer|Targeted|Src
    Peer LDP Ident: 10.255.0.51:0; Local LDP Ident 10.255.0.41:0
	  GigabitEthernet1, Src IP addr: 10.0.41.51
    Peer LDP Ident: 10.255.0.1:0; Local LDP Ident 10.255.0.41:0
	  Targeted Hello 10.255.0.41 -> 10.255.0.1, active, passive
    Peer LDP Ident: 10.255.0.42:0; Local LDP Ident 10.255.0.41:0
	  Targeted Hello 10.255.0.41 -> 10.255.0.42, active, passive
    Peer LDP Ident: 10.255.0.43:0; Local LDP Ident 10.255.0.41:0
	  Targeted Hello 10.255.0.41 -> 10.255.0.43, active, passive
```

With BGP, a PE has just one session, to the RR (RR1). Membership is decided by the RT. The PEs that import VRF A's RT
65000:100 are the L3VPN's members, and the PEs that import EVI 200's RT 65000:200 are the E-LAN's members. Adding a site
does not change any other PE's configuration.

```console
XE1#show bgp vpnv4 unicast all summary | begin Neighbor
Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.255.0.52     4        65000      34      23        6    0    0 00:13:17        2
172.16.1.1      4        65001      18      17        6    0    0 00:11:49        1
XE1#show bgp l2vpn evpn summary | begin Neighbor
Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.255.0.52     4        65000      34      23       20    0    0 00:13:17        6
```

There were two ways to build an E-Line. The LDP pseudowire names the peer; EVPN-VPWS uses BGP. To the customer both are the
same cable; only the way the PEs find each other differs. VPLS and the EVPN E-LAN are related in the same way. What EVPN-VPWS buys
you shows when a site is attached to two PEs, and when LDP is removed from the core (the page *What EVPN-VPWS buys you*).

## 3. How it works: hop by hop

### 3.1 The same road for three services

Compare the packets on the XE1 → P1 and P1 → XE2 links (CML link capture) when CE1 pings CE2 the same way over L3VPN,
VPLS and EVPN. All three take the same road: CE1 → XE1 → P1 → XE2 → CE2.

:::topo
nodes:
  CE1: [0, 1]
  XE1: [1.6, 1]
  P1: [3.2, 1]
  XE2: [4.8, 1]
  CE2: [6.4, 1]
links:
  - [CE1, XE1, "tagged"]
  - [XE1, P1, "18 | inner | payload"]
  - [P1, XE2, "inner | payload"]
  - [XE2, CE2, "tagged"]
:::

| Link | L3VPN (VLAN 100) | VPLS (VLAN 210) | EVPN (VLAN 200) |
|---|---|---|---|
| CE1 → XE1 | tag 100, IP | tag 210, frame | tag 200, frame |
| XE1 → P1 | **18** \| 25 \| IP | **18** \| 27 \| CW \| frame | **18** \| 30 \| frame |
| P1 → XE2 | 25 \| IP | 27 \| CW \| frame | 30 \| frame |
| XE2 → CE2 | tag 100, IP | tag 210, frame | tag 200, frame |

(CW is the control word. Section 3.4)

The packets look like this (lines shortened).

```console
# XE1 → P1 link
MPLS (label 18, ttl 254) (label 25, [S], ttl 254) 10.100.1.1 > 10.100.2.1: ICMP echo request
MPLS (label 18, ttl 255) (label 27, [S], ttl 255)
MPLS (label 18, ttl 255) (label 30, [S], ttl 255)
# P1 → XE2 link
MPLS (label 25, [S], ttl 253) 10.100.1.1 > 10.100.2.1: ICMP echo request
MPLS (label 27, [S], ttl 254)
MPLS (label 30, [S], ttl 254)
```

The outer label is **18** for all three. 18 is the value P1 told XE1 in LDP, "send to XE2 (10.255.0.42) with this label",
and it has nothing to do with the service.

```console
XE1#show mpls forwarding-table 10.255.0.42 32
Local      Outgoing   Prefix           Bytes Label   Outgoing   Next Hop
Label      Label      or Tunnel Id     Switched      interface
22         18         10.255.0.42/32   0             Gi1        10.0.41.51
```

P1 looks only at the outer 18 and sends the packet to XE2. P1 is one hop before XE2, so it removes 18 before sending (PHP).
P1 never looks at the inner label and does not know which service a packet belongs to. No service appears anywhere in P1's
configuration, and P1 does not even run BGP (section 3.5). P1's label table holds only the roads to the loopbacks of the PEs and RR1.

```console
P1#show mpls forwarding-table
Local      Outgoing   Prefix           Bytes Label   Outgoing   Next Hop
Label      Label      or Tunnel Id     Switched      interface
16         No Label   10.255.0.52/32   18630         Et1/1      10.0.52.52
17         Pop Label  10.255.0.41/32   14277         Et0/0      10.0.41.41
18         Pop Label  10.255.0.42/32   7446          Et0/1      10.0.42.42
19         Pop Label  10.255.0.43/32   6858          Et0/2      10.0.43.43
20         Pop Label  10.255.0.1/32    5610          Et1/0      10.0.1.1
```

16 is the road to RR1's loopback. RR1 does not run LDP, so the outgoing label is `No Label` (remove the label and send a
plain IP packet). Section 3.5 looks at what RR1 does.

The outer label is the **road**: "which PE to carry this to". M8's LDP, the M8 add-on's BGP labelled unicast and M10's SR were
all different ways of building this road. Whichever way you build it, the services on top stay the same.

### 3.2 The inner label is the number of a container on the receiving PE

When the packet reaches XE2, one label is left: the inner one. XE2 reads it to decide where the packet goes.
XE2's label table shows what 25, 27 and 30 each point to.

```console
XE2#show mpls forwarding-table
Local      Outgoing   Prefix           Bytes Label   Outgoing   Next Hop
Label      Label      or Tunnel Id     Switched      interface
25         No Label   10.100.2.0/24[V] 826           Gi2.100    172.16.2.1
26         No Label   l2ckt(1)         646           Gi2        point2point
27         No Label   l2ckt(2)         708           none       point2point
28         No Label   l2ckt(3)         0             none       point2point
29         No Label   evpn(mc:bd 200)  120           none       point2point
30         No Label   evpn(uc:bd 200)  456           none       point2point
```

(The core entries are left out.)

- **25** is the VRF A route 10.100.2.0/24 (`[V]` marks a VRF). XE2 removes the label and sends the packet to CE2 as a VRF A route.
- **27** is one pseudowire: the VPLS pseudowire coming from XE1. Its exit is `none`, meaning bridge domain 210.
  XE2 puts the frame into the bridge domain and picks the exit port from the MAC table.
- **30** is the unicast label of EVPN bridge domain 200 (`uc`). 29 is for broadcast and other BUM traffic (`mc`).

Each of these is a number XE2 picked itself and told XE1: "for this container, put this number on". It is passed by the same
means as in section 2.3.

| Service | What the inner label points to | How it reaches XE1 | Show command on XE1 |
|---|---|---|---|
| L3VPN | A route in XE2's VRF (or the VRF itself) | On the BGP VPNv4 route | `show bgp vpnv4 unicast all labels` (`nolabel/25`) |
| VPWS | One AC behind the pseudowire | Targeted LDP | `show l2vpn atom vc vcid <ID> detail` |
| VPLS | A VPLS pseudowire (→ bridge domain) | Targeted LDP | `show bridge-domain <BD>` (`VC_LABEL`) |
| EVPN | The EVI's bridge domain | On BGP EVPN routes (types 2 and 3) | `show bgp l2vpn evpn route-type 2` (`Label1`) |

The numbers mean different things on different PEs. On this topology XE1 also used 25 for a route in its own VRF A, but XE1's
25 and XE2's 25 are unrelated. A label number only has meaning inside the PE that picked it.

### 3.3 VPWS: one wire

The VPWS from CE1 to CE4 goes XE1 → P1 → XR01.

| Link | VPWS (VLAN 130) |
|---|---|
| CE1 → XE1 | tag 130, frame |
| XE1 → P1 | **20** \| 24010 \| frame |
| P1 → XR01 | 24010 \| frame |
| XR01 → CE4 | tag 130, frame |

The outer 20 is the road to XR01. The inner 24010 is a number XR01 picked; in XR01's label table it points from the
pseudowire straight to the subinterface towards CE4. No MAC table and no routing table are consulted; the frame just goes out.

```console
RP/0/RP0/CPU0:XR01#show mpls forwarding
Local  Outgoing    Prefix             Outgoing     Next Hop        Bytes
Label  Label       or ID              Interface                    Switched
------ ----------- ------------------ ------------ --------------- ------------
24009  Unlabelled  10.100.4.0/24[V]   Gi0/0/0/1.100 172.16.4.1      0
24010  Pop         PW(10.255.0.41:130)   \
                                      Gi0/0/0/1.130 point2point     516
```

(The core entries are left out.)

24009 is a route in L3VPN VRF A. The label table reads the same way on IOS XR and on IOS XE.

### 3.4 What sits under the label: an IP packet or a frame

What sits under the inner label also differs by service.

- **L3VPN** carries an IP packet. XE1 strips the Ethernet header of the frame it received from CE1 and carries only the IP.
  XE2 looks up its routing table and then puts on a new Ethernet header towards CE2.
- **The L2 services** carry the customer's Ethernet frame itself. The destination and source MACs are those of CE1 and the
  remote CE. On the VPWS link, the frame begins with an Ethernet header to `aabb.cc00.8e00` (CE4) from `aabb.cc00.8b00` (CE1).

In all four L2 services the frames travelled with the VLAN tag removed, because the PE does
`rewrite ingress tag pop 1 symmetric` on the AC. A tag is a marker only within each site's link and never appears in the core (M11).

:::note
VPLS and EVPN-VPWS (both between Catalyst 8000V) put a 4-byte control word in front of the frame. The EVPN E-LAN, and the LDP
pseudowire between Catalyst 8000V and IOS XR, did not. The PEs agree between themselves whether to use it (M11, section 2.4).
Also, EVPN-VPWS on Catalyst 8000V carried the frames with a VLAN 0 tag added.
:::

From an L3VPN CE, traceroute also shows the labels per hop: two at the second hop, P1, and one at the third hop, XR01.
This is the same shape as the table in section 3.1.

```console
CE1#traceroute 10.100.4.1 source Loopback100 probe 1 timeout 2
  1 172.16.1.254 16 msec
  2 10.0.41.51 [MPLS: Labels 20/24009 Exp 0] 2 msec
  3 10.0.1.1 [MPLS: Label 24009 Exp 0] 7 msec
  4 172.16.4.1 2 msec
```

### 3.5 Keep the RR off the road: a core without BGP

As section 3.1 showed, P1 carries packets on the outer label alone and does not know which service they belong to. P1 does
not run BGP either.

```console
P1#show running-config | include ^router
router isis CORE
P1#show ip bgp summary
% BGP not active
```

**Why it helps.** Only the PEs that attach a customer hold that customer's routes (VRF routes or MACs). A P router's table has
one entry per PE loopback, so it does not grow however many customers and sites are added, and the P router's configuration
does not change. This is called a **BGP-free core**. That the core routers need not know the VPN routes is where MPLS VPNs
start from (RFC 4364).

The PEs still need an RR (or a session between every pair of PEs) to exchange routes in BGP. A P router can double as the RR.
It still would not forward on those routes, but it would hold every customer's VPN routes in its BGP table and spend memory and
processing on them. That undoes the benefit above, so on this topology the RR is a separate box, RR1, attached to P1 by one link.

**How it works.** RR1 passes the routes it receives from a PE on to the other PEs. RR1's BGP table lists the routes of every
site, but RR1 has no VRF, so none of them goes into a forwarding table.

```console
RR1#show bgp vpnv4 unicast all
BGP table version is 4, local router ID is 10.255.0.52
     Network          Next Hop            Metric LocPrf Weight Path
Route Distinguisher: 10.255.0.1:100
 *>i  10.100.4.0/24    10.255.0.1               0    100      0 65004 i
Route Distinguisher: 10.255.0.41:100
 *>i  10.100.1.0/24    10.255.0.41              0    100      0 65001 i
Route Distinguisher: 10.255.0.42:100
 *>i  10.100.2.0/24    10.255.0.42              0    100      0 65002 i
```

(The legend lines are omitted.)

RR1 does not rewrite the next hop when it passes a route on. The site 2 route that XE1 received from RR1 has XE2 as its
`Originator`, and its next hop is still XE2 (10.255.0.42).

```console
XE1#show bgp vpnv4 unicast all 10.100.2.0/24
BGP routing table entry for 10.255.0.41:100:10.100.2.0/24, version 4
Paths: (1 available, best #1, table A)
  Flag: 0x100
  Advertised to update-groups:
     3
  Refresh Epoch 2
  65002, imported path from 10.255.0.42:100:10.100.2.0/24 (global)
    10.255.0.42 (metric 30) (via default) from 10.255.0.52 (10.255.0.52)
      Origin IGP, metric 0, localpref 100, valid, internal, best
      Extended Community: RT:65000:100
      Originator: 10.255.0.42, Cluster list: 10.255.0.52
      mpls labels in/out nolabel/25
      rx pathid: 0, tx pathid: 0x0
      Updated on Nov 4 2026 21:45:12 UTC
```

(The entry for RD 10.255.0.42:100 is omitted.)

So XE1 puts packets for this route on the road to XE2 (outer 18, inner 25) and sends them to P1. They never pass RR1, just as
in the packets in section 3.1.

```console
XE1#show ip cef vrf A 10.100.2.0 255.255.255.0 detail
10.100.2.0/24, epoch 0, flags [rib defined all labels]
  recursive via 10.255.0.42 label 25
    nexthop 10.0.41.51 GigabitEthernet1 label 18-(local:22)
```

All that passes RR1 is the BGP sessions between the PEs and RR1. Up to P1, even these ride the road to RR1's loopback
(label 16); P1 removes the label and hands them to RR1 (line 16 of P1's table in section 3.1). On the XE1 → P1 link they look
like this:

```console
# XE1 → P1 link
MPLS (label 16, [S], ttl 255) 10.255.0.41.20034 > 10.255.0.52.179: Flags [.], ack 3955820421, win 15900, length 0
```

RR1 itself does not run MPLS. It only hands out routes and never carries customer packets.

```console
RR1#show mpls interfaces
Interface              IP            Tunnel   BGP Static Operational
```

:::note
Separating the RR from the P routers and keeping it off the customers' path is a design used in real networks too. Cisco
offers IOS XRv 9000 as a virtual RR (vRR) that is not part of the forwarding path. RR1 is attached to P1 by a single link,
so it cannot be on the path anyway.
:::

## 4. Summary

| | L3VPN | VPWS | VPLS | EVPN (E-LAN) |
|---|---|---|---|---|
| What the customer sees | One router | One cable | One switch | One switch |
| The CE's neighbour | The PE | One remote CE | All remote CEs | All remote CEs |
| What the PE learns | The customer's routes (VRF) | Nothing (an AC–pseudowire pair) | MACs (from arriving frames) | MACs (in BGP) |
| How PEs find each other | BGP (RT) | Named (LDP). EVPN-VPWS uses BGP | Named (LDP) | BGP (RT) |
| What the inner label points to | A route in the VRF | One AC | A pseudowire (→ bridge domain) | A bridge domain |
| What sits under the label | An IP packet | An Ethernet frame | An Ethernet frame | An Ethernet frame |
| The outer label | The same for all four: the road to the egress PE (LDP, SR, …) | | | |

In a sentence: **the outer label is the road, and the inner label is the number of a container on the PE it arrives at**.
The four services differ in just two things: what the container is (a VRF, an AC, a bridge domain), and how its number is
passed (BGP or LDP).

A P router looks only at the outer label, so it needs no service configuration and no BGP. The RR only hands out routes, so
it can stay off the road.

The next page looks at where these differences show up in the configuration, in build order.

:::note
The outputs on this page were taken on a topology built for it: the PEs are three Catalyst 8000V (IOS XE 17.15.1a) and one
IOS XRv 9000 (26.1.1), and P1, RR1 and the CEs are IOL running IOS XE 17.15.
:::
