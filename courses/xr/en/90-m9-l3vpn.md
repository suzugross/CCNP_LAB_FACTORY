# M9 — How L3VPN works

In this unit the provider builds a private network for each customer on top of its core: an MPLS Layer 3 VPN (L3VPN).
It covers section 4.3 of the CCNP Service Provider blueprint: an L3VPN inside one provider (4.3.a) and shared
services, an extranet and Internet access (4.3.b). VPNs between providers (4.1.b) and CSC (4.1.c) are described in the
appendix. The unit has three pages and an appendix:

| Page | Contents | Tasks |
|---|---|---|
| This page | What L3VPN is good for, how it works hop by hop, how to build it on IOS XR | M9-1 |
| Route reflectors and sites in the same AS | Joining the PEs in one place, connecting sites with the same AS number | M9-2 |
| Shared services and the Internet | Showing a shared server while keeping the customers apart, leaving a VPN for the Internet | M9-3, M9-4 |
| Appendix | Label allocation, VPNs between providers, command names | — |

Chapter C0, *The MPLS services side by side*, set L3VPN next to the other services and looked at its outer label (the
path) and its inner label (the container). This unit looks at L3VPN alone, one level deeper.

The lab is XRT-09. Its core is the one of lab XRT-07: XR01 and RT02 are the provider edges (PEs), RT01 and RT03 the
core routers (Ps), with IS-IS and LDP. XR02 is new: a route reflector for VPN routes.

:::topo
nodes:
  CEA1: {at: [0, 0], label: "CEA1 (A, site 1)"}
  CEB1: {at: [0, 0.9], label: "CEB1 (B, site 1)"}
  SVC: {at: [0, 1.8], label: "SVC (shared)"}
  INET: {at: [1.6, -0.8], label: "INET (Internet)"}
  XR01: {at: [1.6, 0.9], label: "XR01 (PE)"}
  RT01: {at: [3.2, 0.2], label: "RT01 (P)"}
  RT03: {at: [3.2, 1.6], label: "RT03 (P)"}
  XR02: {at: [3.2, 2.7], label: "XR02 (RR)"}
  RT02: {at: [4.8, 0.9], label: "RT02 (PE)"}
  CEA2: {at: [6.4, 0.4], label: "CEA2 (A, site 2)"}
  CEB2: {at: [6.4, 1.4], label: "CEB2 (B, site 2)"}
links:
  - [CEA1, XR01, "CUST-A"]
  - [CEB1, XR01, "CUST-B"]
  - [SVC, XR01, "SVC"]
  - [INET, XR01, "global"]
  - [XR01, RT01, "PRIMARY"]
  - [XR01, RT03, "BACKUP"]
  - [RT01, RT02, "CORE-A"]
  - [RT03, RT02, "CORE-B"]
  - [RT03, XR02, "RR-LINK"]
  - [RT02, CEA2, "CUST-A"]
  - [RT02, CEB2, "CUST-B"]
frames:
  - {label: "AS 65000 (IS-IS CORE, LDP)", nodes: [XR01, RT01, RT03, RT02, XR02]}
:::

Customer A has two sites, one behind each PE, both in AS 65101. Customer B has two sites too, in AS 65201 and 65202.
SVC holds the provider's shared servers, and INET stands for the Internet (both on page *Shared services and the
Internet*). The route reflector XR02 hangs off RT03 and is not on the path of any customer packet.

## 1. What it is good for

### 1.1 The problem: a network per customer, on one core

Customer A has two sites and wants them joined; so does customer B. Each customer chooses its own internal addresses.
Private addresses such as 10.0.0.0/8 are free for anyone to use, so two customers often use the same ones.

The provider is asked for three things:

- **Keep them apart**: a packet of customer A must never reach a site of customer B, and B must not see A's routes.
- **Allow overlaps**: two customers may use the same addresses, and each packet still reaches its own site.
- **Grow**: more customers and sites should mean few devices to touch, and no more work for the core routers.

### 1.2 What came before

Before L3VPN there were two main approaches:

- **Circuits between the sites**: the provider sells leased lines, or Frame Relay or ATM virtual circuits, and the
  customer does the routing on its own routers. The provider never looks at the customer's addresses, so separation
  and overlaps are no problem. But joining every site directly takes N(N−1)/2 circuits for N sites (RFC 4110, section
  1.3.3), and each new site means new circuits to the existing ones.
- **The provider's routers carry the customer's routes**: if the provider's routers learn the customer's routes and route
  for it, a new site is configured in one place. But a single routing table cannot hold the same address twice.
  Keeping customers apart means writing filters for each customer forever, or a dedicated router for each customer, and
  every router in the core ends up carrying every customer's routes.

### 1.3 How L3VPN answers

L3VPN is the second approach (the provider carries the customer's routes) with its problems taken away. RFC 4364 calls
it a "peer model", and says that the CEs do not peer with each other in routing (section 1).

| Problem | The L3VPN answer | Section |
|---|---|---|
| Keep the customers apart | the PE keeps a separate routing table (a VRF) for each customer | 2.1 |
| Tell the same address apart inside BGP | a number (the RD) in front of the route | 2.2 |
| Decide which routes go into which VRF | a tag (the RT) on the route, and import by tag | 2.3 |
| Touch few devices for a new site | the PEs distribute routes in BGP (VPNv4); only the PE that connects the site is touched | 2.4 |
| Keep customer routes out of the core | the core carries the packets on labels alone (two labels) | 2.5 |

## 2. How it works: one packet, hop by hop

### 2.1 A separate table in the PE: the VRF

Besides the global routing table, a PE keeps a routing table for each customer. That is a **VRF** (VPN routing and
forwarding instance; RFC 4364, section 3). Once a customer interface is in a VRF, a packet that comes in on it is looked
up in that VRF's table.

On XR01, the interface to CEA1 is in VRF CUST-A and the interface to CEB1 is in VRF CUST-B. The table of CUST-A holds
customer A's routes only (after all four tasks, with only the lines for customer A's sites):

```console
RP/0/RP0/CPU0:XR01#show route vrf CUST-A
...
B    10.101.1.0/24 [20/0] via 172.16.11.2, 00:02:33
B    10.101.2.0/24 [200/0] via 10.255.0.12 (nexthop in vrf default), 00:02:33
C    172.16.11.0/24 is directly connected, 00:02:51, GigabitEthernet0/0/0/2
L    172.16.11.1/32 is directly connected, 00:02:51, GigabitEthernet0/0/0/2
```

10.101.1.0/24 is site 1, learned from CEA1 in eBGP; 10.101.2.0/24 is site 2, with RT02's loopback 10.255.0.12 as the next
hop. `nexthop in vrf default` says that the next hop is looked up in the global table. The customer's route is in the
VRF, and the way to it (RT02's loopback) is in the global table: these two steps become the two labels of section 2.5.

Customer B's routes are not in CUST-A, and XR01's global table holds no customer routes at all:

```console
RP/0/RP0/CPU0:XR01#show route 10.101.2.0/24
% Network not in table
```

### 2.2 A number on the route: the RD

The PEs distribute the routes of all the customers in a single BGP. If two customers use the same 10.101.2.0/24, BGP
sees two paths for one prefix and picks only one of them.

So when a PE puts a VRF route into BGP, it puts an 8-byte
**route distinguisher** (RD) in front of it. The RD and the IPv4 address together, 12 bytes, make a VPN-IPv4 address,
defined in section 4.1 of RFC 4364. Inside BGP, a different RD makes a different prefix.

An RD can be written in a few forms (section 4.2); "AS number:number" and "IP address:number" are the common ones. The
lab uses "the PE's loopback:number": XR01's CUST-A is 10.255.0.1:101 and RT02's CUST-A is 10.255.0.12:101. The RFC says
that the RD exists only to make distinct routes for a common prefix, and tells neither where the route came from nor
which VPNs it goes to (section 4.1). Which VRF imports a route is not decided by the RD (section 2.3).

Here customer B's site 2 (CEB2) has been given the same 10.101.2.0/24 as customer A's site 2 (a loopback advertised in
BGP; the *Try it* below adds it and removes it again). The route reflector XR02 holds the two apart by their RDs:

```console
RP/0/RP0/CPU0:XR02#show bgp vpnv4 unicast | include "Route Distinguisher|10.101.2.0"
...
Route Distinguisher: 10.255.0.12:101
*>i10.101.2.0/24      10.255.0.12              0    100      0 65101 i
Route Distinguisher: 10.255.0.12:102
*>i10.101.2.0/24      10.255.0.12              0    100      0 65202 i
```

XR01 imports customer A's route into CUST-A and customer B's into CUST-B. RT02 gave the two routes different VPN labels
(22 and 26), so a packet to the same address reaches a different site for each customer:

```console
RP/0/RP0/CPU0:XR01#show cef vrf CUST-A 10.101.2.0/24
...
     next hop 10.0.1.11/32 GigabitEthernet0/0/0/0 labels imposed {16 22}
RP/0/RP0/CPU0:XR01#show cef vrf CUST-B 10.101.2.0/24
...
     next hop 10.0.1.11/32 GigabitEthernet0/0/0/0 labels imposed {16 26}

CEA1#traceroute 10.101.2.1 source Loopback10 numeric timeout 1 probe 1
  1 172.16.11.1 [AS 64500] 7 msec
  2 10.0.1.11 [AS 64500] [MPLS: Labels 16/22 Exp 0] 10 msec
  3 172.16.12.1 [AS 64500] [MPLS: Label 22 Exp 0] 10 msec
  4 172.16.12.2 [AS 64500] 9 msec
CEB1#traceroute 10.101.2.1 source Loopback10 numeric timeout 1 probe 1
  1 172.16.21.1 6 msec
  2 10.0.1.11 [MPLS: Labels 16/26 Exp 0] 8 msec
  3 172.16.22.1 [MPLS: Label 26 Exp 0] 9 msec
  4 172.16.22.2 10 msec
```

The last hop is CEA2 (172.16.12.2) for customer A and CEB2 (172.16.22.2) for customer B. To the core router RT01 both
are packets "to RT02, 16"; only the inner label differs.

:::try
Put the same address in two customers. Do it after Task M9-2, and always undo it at the end (CEB2 is a fixed router).

1. On CEB2, give `interface Loopback11` the address `ip address 10.101.2.1 255.255.255.0`, and add
   `network 10.101.2.0 mask 255.255.255.0` under `router bgp 65202` → `address-family ipv4`.
2. Wait a minute. Run `show bgp vpnv4 unicast` on XR02, and `show cef vrf CUST-A 10.101.2.0/24` and
   `show cef vrf CUST-B 10.101.2.0/24` on XR01. On CEA1 and on CEB1, run
   `traceroute 10.101.2.1 source Loopback10 numeric`.
3. Remove the `network` line and Loopback11 from CEB2.

An example result: within a minute XR02 held 10.101.2.0/24 twice, under RDs 10.255.0.12:101 and 10.255.0.12:102.
XR01 imposed 22 in CUST-A and 26 in CUST-B; the traceroute from CEA1 ended at CEA2 and the one from CEB1 at CEB2. Within
30 seconds of the removal, CUST-B's 10.101.2.0/24 was gone.
:::

### 2.3 A tag on the route: the RT

Which VRF a route goes into is decided by the **route target** (RT). An RT is a BGP extended community. When a PE puts a
VRF route into BGP it attaches the VRF's **export** RTs; a PE that receives the route imports it into a VRF when one of
the route's RTs is one of the VRF's **import** RTs (RFC 4364, section 4.3.1).

```console
RP/0/RP0/CPU0:XR01#show vrf CUST-A detail
VRF CUST-A; RD 10.255.0.1:101; VPN ID not set
VRF mode: Regular
Description not set
Interfaces:
  GigabitEthernet0/0/0/2
Address family IPV4 Unicast
  Import VPN route-target communities:
    RT:65000:101
    RT:65000:900
  Export VPN route-target communities:
    RT:65000:101
  No import route policy
  No export route policy
...
```

CUST-A sends its routes out with 65000:101 and takes in routes that carry 65000:101. RT02's CUST-A has the same values,
so each site's routes enter the other site's VRF. 65000:900 is the tag for the shared services (page *Shared services
and the Internet*).

An RD and an RT look alike — two numbers with a colon — but they do different jobs:

| | RD | RT |
|---|---|---|
| What for | to tell routes for the same address apart inside BGP | to decide which VRFs a route goes into |
| Where it sits | in the route's address (the head of the VPN-IPv4 address) | in the route's attributes (an extended community) |
| Per route | one | any number |
| How the lab picks them | per PE and VRF (10.255.0.1:101, 10.255.0.12:101) | per customer (A is 65000:101, B 65000:102) |

A PE drops, on receipt, a route that none of its VRFs imports (RFC 4364, section 4.3.2). A PE without a site of a customer
holds none of that customer's routes (section 3.4).

### 2.4 Between the PEs: VPNv4 and the VPN label

The PEs distribute the routes in iBGP between their loopbacks, in the VPN-IPv4 address family (VPNv4). A VPNv4 route
carries the prefix with its RD, the RTs, a next hop and a **VPN label**. Here is site 2 as XR01 received it:

```console
RP/0/RP0/CPU0:XR01#show bgp vpnv4 unicast rd 10.255.0.12:101 10.101.2.0/24
BGP routing table entry for 10.101.2.0/24, Route Distinguisher: 10.255.0.12:101
...
Paths: (1 available, best #1)
  Not advertised to any peer
  Path #1: Received by speaker 0
  Not advertised to any peer
  65101
    10.255.0.12 (metric 30) from 10.255.0.21 (10.255.0.12)
      Received Label 22
      Origin IGP, metric 0, localpref 100, valid, internal, best, group-best, import-candidate, not-in-vrf
      Received Path ID 0, Local Path ID 1, version 8
      Extended community: RT:65000:101
      Originator: 10.255.0.12, Cluster list: 10.255.0.21
```

- RD 10.255.0.12:101 is the RD of RT02's CUST-A, and the next hop 10.255.0.12 is RT02's loopback.
- `Received Label 22` is the VPN label, chosen by RT02 and sent with the route.
- `RT:65000:101` is customer A's tag.
- `from 10.255.0.21` and `Cluster list` say that it came through the route reflector XR02 (next page).
- `not-in-vrf` marks the copy as received. XR01 copies it under its own RD, 10.255.0.1:101, into CUST-A, and that copy
  is what `show bgp vrf CUST-A` lists.

The VPN label is chosen by the PE that advertised the route, which is the PE where the packet will leave the core
(RFC 4364, section 4.3.2). RT02's label table shows what 22 stands for (only the VPN label lines are shown):

```console
RT02#show mpls forwarding-table
Local      Outgoing   Prefix           Bytes Label   Outgoing   Next Hop
Label      Label      or Tunnel Id     Switched      interface
...
22         No Label   10.101.2.0/24[V] 5230          Et0/2      172.16.12.2
23         No Label   198.51.100.128/25[V]   \
                                       2280          Et0/2      172.16.12.2
24         No Label   10.102.2.0/24[V] 4788          Et1/0      172.16.22.2
```

22 is CUST-A's 10.101.2.0/24 (`[V]` marks a VRF prefix). RT02 removes the label of a packet that arrives with 22 and
sends it to CEA2 without looking the destination up again. This is one label per route, the default on IOS XR and IOS
XE (appendix, section 1). 24 is the route of customer B's site 2.

### 2.5 Following a packet: two labels

Follow a packet of customer A from CEA1 (10.101.1.1) to CEA2 (10.101.2.1):

1. CEA1 sends the packet to XR01, as a plain IP packet.
2. XR01 picks VRF CUST-A from the interface the packet came in on, and finds 10.101.2.0/24: next hop RT02, VPN label 22.
   It then looks up the way to RT02's loopback in the global table. The next hop on the shortest path is RT01, and RT01
   has told it in LDP to use 16 for RT02. XR01 puts 16 on top of 22 and sends the packet to RT01.
3. RT01 looks only at the top label, 16. It is the hop before RT02, so it removes 16 (PHP; unit M8) and sends the packet
   to RT02.
4. RT02 looks at the remaining 22, removes it and sends the packet to CEA2.

:::topo
nodes:
  CEA1: {at: [0, 1], kind: host}
  XR01: [1.3, 1]
  RT01: [2.6, 0.15]
  RT03: [2.6, 1.85]
  RT02: [3.9, 1]
  CEA2: {at: [5.2, 1], kind: host}
links:
  - [CEA1, XR01, "IP"]
  - [XR01, RT01, "16 | 22"]
  - [RT01, RT02, "22"]
  - [RT02, CEA2, "IP"]
  - {a: XR01, b: RT03, style: dashed}
  - {a: RT03, b: RT02, style: dashed}
:::

The numbers on a link are the labels the packet carries on it, the top one on the left. XR01's forwarding table, the
packets captured on the CML links (lines shortened) and a traceroute from CEA1 all show the same:

```console
RP/0/RP0/CPU0:XR01#show cef vrf CUST-A 10.101.2.0/24
10.101.2.0/24, version 7, internal 0x5000001 0x30 (ptr 0xf79a398) [1], 0x600 (0xf92f398), 0xa08 (0xf318218)
...
   via 10.255.0.12/32, 5 dependencies, recursive [flags 0x6000]
    path-idx 0 NHID 0x0 [0xeda0c10 0x0]
    recursion-via-/32
    next hop VRF - 'default', table - 0xe0000000
    next hop 10.255.0.12/32 via 24002/0/21
     next hop 10.0.1.11/32 GigabitEthernet0/0/0/0 labels imposed {16 22}

# the XR01 → RT01 link
MPLS (label 16, ttl 254) (label 22, [S], ttl 254) 10.101.1.1 > 10.101.2.1: ICMP echo request
# the RT01 → RT02 link
MPLS (label 22, [S], ttl 253) 10.101.1.1 > 10.101.2.1: ICMP echo request

CEA1#traceroute 10.101.2.1 source Loopback10 numeric timeout 1 probe 1
  1 172.16.11.1 [AS 64500] 4 msec
  2 10.0.1.11 [AS 64500] [MPLS: Labels 16/22 Exp 0] 1 msec
  3 172.16.12.1 [AS 64500] [MPLS: Label 22 Exp 0] 3 msec
  4 172.16.12.2 [AS 64500] 1 msec
```

`next hop VRF - 'default'` is the two-step arrangement of section 2.1: the next hop of the VRF route (RT02) is looked up
in the global table. `[AS 64500]` is an AS number that IOS's traceroute adds from CEA1's BGP table (the Internet's
AS); it has nothing to do with the labels.

The packet back, from CEA2 to CEA1, has the same shape. RT02 puts RT01's label for XR01's loopback, 22, on top of
24004, the VPN label XR01 gave to CEA1's route. RT01 does not remove 22 but replaces it with 0 and sends the packet to
XR01. 0 is explicit null: XR01 asks for it, "give it to me with a 0 rather than removing the label", since a task in M8
(MPLS OAM and explicit null).

:::topo
nodes:
  CEA2: {at: [0, 1], kind: host}
  RT02: [1.3, 1]
  RT01: [2.6, 0.15]
  RT03: [2.6, 1.85]
  XR01: [3.9, 1]
  CEA1: {at: [5.2, 1], kind: host}
links:
  - [CEA2, RT02, "IP"]
  - [RT02, RT01, "22 | 24004"]
  - [RT01, XR01, "0 | 24004"]
  - [XR01, CEA1, "IP"]
  - {a: RT02, b: RT03, style: dashed}
  - {a: RT03, b: XR01, style: dashed}
:::

```console
# the RT02 → RT01 link
MPLS (label 22, ttl 254) (label 24004, [S], ttl 254) 10.101.2.1 > 10.101.1.1: ICMP echo reply
# the RT01 → XR01 link
MPLS (label 0, ttl 253) (label 24004, [S], ttl 254) 10.101.2.1 > 10.101.1.1: ICMP echo reply
```

The 22 going and the 22 coming back are different things. Going, 22 is the VPN label that RT02 chose for CUST-A's route;
coming back, 22 is the LDP label that RT01 chose for XR01's loopback. A label value means something only inside the
router that chose it.

### 2.6 What to remember

- **The core knows nothing about the customers.** RT01 has no customer routes and no BGP, and its label table holds only
  loopbacks and links. RFC 4364 says that the P routers need no per-VPN routing information whatsoever (section 1.5).

  ```console
  RT01#show ip route 10.101.2.1
  % Subnet not in table
  RT01#show ip bgp summary
  % BGP not active
  ```

- **The outer label is the path; the inner label is the egress PE's container.** The outer one (16) comes from LDP and
  takes the packet to RT02; the inner one (22) comes from RT02 in BGP and decides where the packet goes inside RT02. Change
  the path from LDP to SR (unit M10) and the inner label stays the same.
- **The RD tells routes apart; the RT says where they go.** The RD makes a route unique inside BGP, and the RT decides
  which VRFs it enters.

## 3. Building it on IOS XR

### 3.1 Where each part goes

The parts are the same on every OS, but IOS XR puts them in different places. On IOS, the RD and the RTs are written
together under `vrf definition`.

- **The RTs belong to the VRF**: `vrf <name>` → `address-family ipv4 unicast` → `import route-target` and
  `export route-target`, each a sub-mode that takes one route target per line.
- **The interface** joins the VRF with `vrf <name>`.
- **The RD belongs to BGP**: `router bgp <AS>` → `vrf <name>` → `rd`, with the CE neighbours of that VRF under the same
  `vrf`.
- **Between the PEs** it is `address-family vpnv4 unicast` at the top of BGP and the same address family under the
  neighbour.

This configuration connects customer A's site 1 to XR01. Customer B has the same shape with other values.

:::config fold XR01 — customer A's site 1 in its VRF
vrf CUST-A                                    ## the container; the RTs go under the VRF
 address-family ipv4 unicast
  import route-target                         ## take in routes that carry these tags
   65000:101
   65000:900                                  ## the shared services' tag (page "Shared services and the Internet")
  !
  export route-target                         ## the tag put on this VRF's routes
   65000:101
  !
 !
!
interface GigabitEthernet0/0/0/2              ## the interface to CEA1
 vrf CUST-A                                   ## into the VRF first, then the address
 ipv4 address 172.16.11.1 255.255.255.0
!
route-policy PASS                             ## eBGP exchanges nothing without a policy (unit M5)
  pass
end-policy
!
router bgp 65000
 bgp router-id 10.255.0.1
 address-family vpnv4 unicast                 ## VPNv4 at the top; without it the two below are refused (section 3.2)
 !
 neighbor 10.255.0.21                         ## VPNv4 with the route reflector XR02 only
  remote-as 65000
  update-source Loopback0
  address-family vpnv4 unicast
  !
 !
 vrf CUST-A
  rd 10.255.0.1:101                           ## the RD goes under the VRF in BGP (on IOS, under vrf definition)
  address-family ipv4 unicast                 ## needs the RD first (section 3.2)
  !
  neighbor 172.16.11.2                        ## eBGP with CEA1
   remote-as 65101
   address-family ipv4 unicast
    route-policy PASS in
    route-policy PASS out
   !
  !
 !
!
:::

RT02 writes the same thing in IOS XE as follows (from the lab's fixed configuration). The RD and the RTs are together
under `vrf definition`, and the CE neighbour is under BGP's `address-family ipv4 vrf`.

:::config RT02 (IOS XE) — customer A's site 2 (from the lab's fixed configuration)
vrf definition CUST-A
 rd 10.255.0.12:101                           ## on IOS XE the RD goes under the VRF
 address-family ipv4
  route-target export 65000:101
  route-target import 65000:101
  route-target import 65000:900
 exit-address-family
!
interface Ethernet0/2
 description CUST-A site 2 (CEA2)
 vrf forwarding CUST-A                        ## on IOS XE, changing the VRF removes the address
 ip address 172.16.12.1 255.255.255.0
!
router bgp 65000
 neighbor 10.255.0.21 remote-as 65000
 neighbor 10.255.0.21 update-source Loopback0
 address-family ipv4
  no neighbor 10.255.0.21 activate            ## no IPv4 unicast with the route reflector
 exit-address-family
 address-family vpnv4
  neighbor 10.255.0.21 activate
  neighbor 10.255.0.21 send-community extended   ## RTs are extended communities
 exit-address-family
 address-family ipv4 vrf CUST-A
  neighbor 172.16.12.2 remote-as 65101
  neighbor 172.16.12.2 activate
  neighbor 172.16.12.2 as-override             ## next page
 exit-address-family
!
:::

:::note
The L3VPN configuration guides for the NCS 5500 and the ASR 9000 (release 7.11) say that an interface must lose its
IPv4 and IPv6 addresses before its VRF is assigned, removed or changed, and that the change is rejected otherwise.
IOS XR 26.1.1 (both XRv 9000 and XRd) accepts the change with the address in place, and keeps the address. Moving an
interface from the global table into a VRF, back again, or into another existing VRF works after a few seconds; moving
it into a VRF created in the same commit can leave it unable to reach its neighbour. Follow the guides: in lab XRT-09
the customer interfaces have no address, so `vrf` and `ipv4 address` go in together.
:::

### 3.2 The commit checks the order

IOS XR checks the order of these parts when you commit. BGP needs `address-family vpnv4 unicast` at its top before any
VPNv4 neighbour or any VRF address family can exist, and a VRF's address family in BGP needs the RD first. The errors
read:

```console
!!% 'BGP' detected the 'warning' condition 'The address family has not been initialized'
!!% 'BGP' detected the 'warning' condition 'The parent address family has not been initialized'
!!% 'BGP' detected the 'warning' condition 'The RD for the VRF must be present before an address family is activated'
```

The first comes from a VPNv4 neighbour, the second from a VRF's address family, both without the VPNv4 family at the
top. A failed commit is undone as a whole, so a VRF without an RD never sits there advertising nothing. Newer guides
also show `rd` directly under `vrf <name>`, and IOS XR 26.1.1 accepts it there too; this page keeps the RD in BGP, the
form of the command references.

### 3.3 The session with the CE

A PE usually learns the customer's routes from the CE in eBGP, inside the VRF. Everything from unit M5 still holds: an
eBGP neighbour of IOS XR exchanges no routes until it has a route policy in each direction, and a VRF is no exception.
The session comes up, and the routes are dropped:

```console
RP/0/RP0/CPU0:XR01#show bgp vrf CUST-B summary
...
Some configured eBGP neighbors (under default or non-default vrfs)
do not have both inbound and outbound policies configured for IPv4 Unicast
address family. These neighbors will default to sending and/or
receiving no routes and are marked with '!' in the output below.
Use the 'show bgp neighbor <nbr_address>' command for details.

Neighbor        Spk    AS MsgRcvd MsgSent       TblVer  InQ OutQ  Up/Down  St/PfxRcd
172.16.21.2       0 65201      27      33          113    0    0 00:19:49          0!

RP/0/RP0/CPU0:XR01#show bgp vrf CUST-B neighbors 172.16.21.2 | include "policy|accepted|denied"
  eBGP neighbor with no inbound or outbound policy; defaults to 'drop'
  0 accepted prefixes, 0 are bestpaths
  Exact no. of prefixes denied: 0
  Cumulative no. of prefixes denied: 1
    No policy: 1, Failed RT match: 0
```

With a policy in and out, the routes enter the VRF's BGP table and its routing table. `show route vrf CUST-A` lists
them as BGP routes, and `show bgp vrf CUST-A` shows the RD in front of the table.

:::try
See what the session with a CE does without policies. Do it after Task M9-1.

1. On XR01, under `router bgp 65000` → `vrf CUST-B` → `neighbor 172.16.21.2` → `address-family ipv4 unicast`, remove
   both `route-policy` lines and commit.
2. On XR01, run `show bgp vrf CUST-B summary` and `show bgp vrf CUST-B neighbors 172.16.21.2`. On CEB1, run
   `show ip bgp summary` and `show ip route bgp`.
3. Put the two lines back and commit, and run the same commands again.

An example result: the session stayed up and was not reset (its up time kept counting). XR01 showed `0!` and
counted CEB1's route under `No policy: 1`, and CEB1's BGP routes were gone: it received nothing either
(`State/PfxRcd 0`). Within 30 seconds of the lines going back, XR01 accepted the route again and CEB1 had its routes
back.
:::

### 3.4 Route-target filtering

A PE keeps only the VPN routes that it can use. A route whose route targets match no import route target of a local VRF
is dropped on receipt, without any policy, and the neighbour's detail counts it:

```console
RP/0/RP0/CPU0:XR01#show bgp vpnv4 unicast neighbors 10.255.0.21 | include "refresh request|Failed RT|denied"
  Route refresh request: received 0, sent 2
  Exact no. of prefixes denied: 0
  Cumulative no. of prefixes denied: 2
    No policy: 0, Failed RT match: 2
```

A PE that drops routes may need them later. When a new VRF is configured, or an import route target is added that the
PE holds no routes for, IOS XR asks its neighbours to send their routes again (a BGP **route refresh**). The routes of
customer B arrive within five seconds of the VRF's commit, and `show bgp vpnv4 unicast neighbors` counts the refresh:

```console
RP/0/RP0/CPU0:XR01#show bgp vpnv4 unicast neighbors 10.255.0.21 | include "refresh request|Failed RT"
  Route refresh request: received 0, sent 3
    No policy: 0, Failed RT match: 2
```

Here 65000:102 had just been added back to CUST-B's import route targets. Configuring the VRF CUST-B from scratch does
the same: one route refresh, and customer B's routes within five seconds.

:::try
Watch XR01 drop routes and ask for them again. Do it after Task M9-2 and before Task M9-3: from Task M9-3 on, VRF
SVC imports 65000:102 too, and XR01 keeps customer B's routes for it.

1. On XR01, run `show bgp vpnv4 unicast neighbors 10.255.0.21 | include "refresh request|Failed RT"`.
2. Remove 65000:102 from the import route targets of CUST-B and commit. Run
   `show bgp vpnv4 unicast rd 10.255.0.12:102`.
3. Run `clear bgp vpnv4 unicast 10.255.0.21 soft in`, which makes XR02 send its routes again, and then the command of
   step 1.
4. Put 65000:102 back and commit. Run the command of step 1 and `show bgp vrf CUST-B`.

An example result: XR01 dropped 10.102.2.0/24 at once; the table of RD 10.255.0.12:102 was empty. After the soft
refresh, the neighbour detail showed `Failed RT match: 2`, and the refresh requests sent had gone from 0 to 2. With
65000:102 back, the counter went to 3 and 10.102.2.0/24 was in CUST-B again within five seconds; CEB1 reached CEB2.
:::

### 3.5 The order to check in

When something does not work, check from the bottom up (the same idea as step 4 of *The order of assembly* in chapter
C0). A symptom in an upper row usually comes from a mistake in a lower one.

| Layer | What to check | On XR01 |
|---|---|---|
| Path | a label to the egress PE's loopback | `show mpls forwarding` (the 10.255.0.12/32 line) |
| Between the PEs | the VPNv4 session is up and receiving routes | `show bgp vpnv4 unicast summary` |
| Container | the VRF's RTs are right | `show vrf CUST-A detail` |
| Attachment | the CE session is up, with no `!` | `show bgp vrf CUST-A summary` |
| Routes | the other site's routes arrived and are in the VRF | `show bgp vpnv4 unicast rd <the other RD>`, `show bgp vrf CUST-A` |
| Forwarding | two labels are imposed | `show cef vrf CUST-A <destination>` (`labels imposed`) |
| End to end | the customer's sites reach each other | `ping` and `traceroute` from a CE (sourced from the LAN address) |

## Practice

Go to lab **XRT-09** and do Task M9-1. XR01 is an IOS XRv 9000, so the lab takes about ten minutes to build.

<p class="tolab"><a href="/_learn?id=XRT-09">Open lab XRT-09 in the workspace</a> — <a href="91-m9-practice.html">Task M9-1</a></p>

:::note
The outputs on this page were captured on IOS XRv 9000 26.1.1 (XR01), IOS XRd 26.1.1 (XR02) and IOS XE 17.15 on IOL (the
other routers). Sources: RFC 4364 (sections 1, 1.5, 3 and 4.1 to 4.3) and RFC 4110 (section 1.3.3). The BGP command
references for the Cisco 8000 (cumulative, 2026) and the NCS 5500 (route distinguisher and `rd auto`,
`retain route-target`, `as-override`, `allowas-in`, `site-of-origin`, `label mode`, `export route-policy`); the Routing
Configuration Guide for the ASR 9000, IOS XR 24.x (2026: address families, route reflectors and `retain route-target`,
route refresh for a new VRF, VRF dynamic route leaking with `advertise-as-vpn` and `allow-imported-vpn`, the routing
policy for VRF import and export, static routes into another VRF); the L3VPN configuration guides for the NCS 5500 and
the Cisco 8000 and the MPLS L3VPN guide for the ASR 9000, release 7.11 (VRF on an interface, Inter-AS option B, CSC);
the Cisco 8000 guide "BGP Route Distinguisher"; Cisco TAC documents "Cisco IOS-XR BGP with MPLS Designs" (2021) and
"Configure Route Leak between GRT and VRF with IOS XR"; the IOS XRd data sheet. All checked October and November 2026.
The following come from measurement in lab XRT-09 and its PoC: the commit errors, the interface address kept in a VRF
change, the dropped routes and their counters, the route refresh, the labels and the packets on the links (CML link
capture), and the handling of overlapping addresses.
:::
