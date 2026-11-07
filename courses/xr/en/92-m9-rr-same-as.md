# M9 — Route reflectors and sites in the same AS

This page deals with the scale of distributing VPN routes between the PEs, and with joining two sites that use the same
AS number. It is for Task M9-2. Read section 2.4 of the previous page, *How L3VPN works* (VPNv4 and the VPN label),
first.

## 1. What it is good for

### 1.1 A full mesh of PEs

VPNv4 routes travel in iBGP. An iBGP speaker does not send a route learned in iBGP to another iBGP neighbour, so without
a route reflector every pair of PEs needs a session. N PEs need N(N−1)/2 sessions, and each new PE means new
configuration on every existing one.

A **route reflector** (RR) sends the routes it receives from a client on to its other clients (it reflects them). Each
PE has a session with the RR only, and a new PE means touching the new PE and the RR. RFC 4364 also says that route
reflectors, instead of a full iBGP mesh between the PEs, improve scalability (section 4.3.3).

### 1.2 Sites with the same AS number

Customer A uses AS 65101 at both sites. Private AS numbers are scarce, and VPN customers often use one number for all
their sites. But BGP treats its own AS number in an AS path as a loop and drops the route. The route of site 2 arrives
at site 1 with AS path 65101, so as it stands CEA1 will not accept it.

RFC 4364 says that such sites may share an AS number, that the PE strips it out, and that loops are prevented by the
Site of Origin attribute (section 7).

### 1.3 The answers

| Problem | Answer | Section |
|---|---|---|
| Sessions between PEs grow with the square of their number | a route reflector; each PE talks to the RR only | 2.1 to 2.3 |
| Sites with the same AS number do not accept each other's routes | the PE replaces the customer's number in the AS path (as-override) | 2.4 |
| With the number replaced, the AS path no longer shows a loop | a mark of the site of origin on the route (site-of-origin) | 2.5 |

## 2. How it works

### 2.1 A VPNv4 route reflector keeps everything

A PE drops a route that none of its VRFs imports (previous page, section 2.3). A route reflector does not: it keeps
every VPNv4 route, with no VRF of its own, and reflects it to its clients. RFC 4364 says that a PE, unless it is a route
reflector or an Inter-AS border router, should not install a route that no VRF of it imports (section 4.3.2), and that
route reflectors are the only systems that need routing information for VPNs they are not attached to (section 4.3.3).

This is XR02 in the lab with all four tasks done. XR02 has no VRF at all, yet it holds the routes of every RD of both
PEs:

```console
RP/0/RP0/CPU0:XR02#show bgp vpnv4 unicast
...
   Network            Next Hop            Metric LocPrf Weight Path
Route Distinguisher: 10.255.0.1:101
*>i0.0.0.0/0          10.255.0.1                    100      0 64500 i
*>i10.101.1.0/24      10.255.0.1               0    100      0 65101 i
*>i198.51.100.0/25    10.255.0.1               0    100      0 65101 i
Route Distinguisher: 10.255.0.1:102
*>i10.102.1.0/24      10.255.0.1               0    100      0 65201 i
Route Distinguisher: 10.255.0.1:900
*>i10.99.1.0/24       10.255.0.1               0    100      0 ?
*>i10.99.2.0/24       10.255.0.1               0    100      0 ?
Route Distinguisher: 10.255.0.12:101
*>i10.101.2.0/24      10.255.0.12              0    100      0 65101 i
*>i198.51.100.128/25  10.255.0.12              0    100      0 65101 i
Route Distinguisher: 10.255.0.12:102
*>i10.102.2.0/24      10.255.0.12              0    100      0 65202 i
Processed 9 prefixes, 9 paths
```

10.99.2.0/24 is an internal route of the shared services that no customer VRF imports (page *Shared services and the
Internet*). XR02 holds it; RT02 does not. RT02 is a PE, so it drops routes that no VRF imports:

```console
RT02#show ip bgp vpnv4 all
...
Route Distinguisher: 10.255.0.1:900
 *>i  10.99.1.0/24     10.255.0.1               0    100      0 ?
...
```

### 2.2 A client per address family

IOS XR becomes a route reflector as soon as it has one client, and by default it then keeps every route. A client is a
property of a neighbour's address family: `route-reflector-client` goes under `neighbor` → `address-family vpnv4 unicast`.
Written under another address family, it does nothing for VPNv4.

An iBGP speaker without VRFs and without VPNv4 clients keeps nothing at all. XR02 in that state accepted none of the
routes it was sent, and did not count them as denied:

```console
RP/0/RP0/CPU0:XR02#show bgp vpnv4 unicast summary
...
Neighbor        Spk    AS MsgRcvd MsgSent       TblVer  InQ OutQ  Up/Down  St/PfxRcd
10.255.0.1        0 65000       4       3            1    0    0 00:00:37          0
10.255.0.12       0 65000       6       3            1    0    0 00:00:39          0

RP/0/RP0/CPU0:XR02#show bgp vpnv4 unicast neighbors 10.255.0.1 | include "accepted|denied"
  0 accepted prefixes, 0 are bestpaths
  Exact no. of prefixes denied: 0
  Cumulative no. of prefixes denied: 0
```

This was captured in the PoC, with XR02 configured without any route reflector line and without `retain`, while XR01
was sending it two routes. Once XR02 is a route reflector, `show bgp vpnv4 unicast neighbors` prints
`Route-Reflector Client` in the part of each address family where it is configured, so look at the one under VPNv4.

`retain route-target all` under `address-family vpnv4 unicast` makes a router keep VPNv4 routes that no VRF imports.
XR02 then held every route, and still passed none on: an iBGP speaker does not send an iBGP route to another iBGP
neighbour, and only clients change that.

The command is for an Inter-AS option B border router (appendix, section 2),
which must keep routes it has no VRF for; the `route-policy` form lets a route reflector keep only some route targets,
to split the VPNs between several reflectors.

### 2.3 The route reflector stays off the path

XR02 does not change the next hop when it reflects a route. Site 2's route reaches XR01 from XR02 with RT02's loopback
still as the next hop; `Originator` names the PE it came from and `Cluster list` the reflectors it passed (previous
page, section 2.4). The customer's packets therefore flow from PE to PE and never through XR02; the traceroutes on the
previous page did not show it.

XR02 carries no customer packets, so it needs no labels either. RR-LINK has no LDP, and XR02's label table is empty. It
holds the VPN routes in its BGP table only, not in its own routing table:

```console
RP/0/RP0/CPU0:XR02#show mpls forwarding
RP/0/RP0/CPU0:XR02#show route 10.101.1.0/24
% Network not in table
```

Keeping the route reflector off the path was the shape seen in chapter C0, *Keep the RR off the path*, where the P
router does not double as one. XR02 in this lab also sits at a dead end beyond RT03.

XR02 runs IOS XRd. Cisco offers XRd in a control-plane form for route reflectors and other roles off the forwarding
path.

It is not suitable as XR01 in this lab: in the PoC with XRd as XR01, ping passed both ways, but TCP and UDP
packets that XRd received from a CE and sent on with labels, or routed between two VRFs or between a VRF and the global
table, arrived with a bad checksum. Traceroutes from CEA1 stopped after the first hops. Packets that XRd received with
labels and sent to a CE were intact. IOS XRv 9000 forwarded all of them correctly.

### 2.4 The AS path check, and AS override

The route of site 2 reaches XR01 with AS path 65101, and CEA1 would drop it as a loop. An IOS XR PE does not wait for
the receiver to drop it; it does not send it at all. It checks the AS path against the neighbour's AS before sending.

```console
RP/0/RP0/CPU0:XR01#show bgp vrf CUST-A 10.101.2.0/24
BGP routing table entry for 10.101.2.0/24, Route Distinguisher: 10.255.0.1:101
...
Paths: (1 available, best #1)
  Not advertised to any peer
  Path #1: Received by speaker 0
  Not advertised to any peer
  65101
    10.255.0.12 (metric 30) from 10.255.0.21 (10.255.0.12)
...
RP/0/RP0/CPU0:XR01#show bgp vrf CUST-A neighbors 172.16.11.2 advertised-routes
Network            Next Hop        From            AS Path
Route Distinguisher: 10.255.0.1:101 (default for vrf CUST-A)
0.0.0.0/0          172.16.11.1     192.0.2.2       65000 64500i
10.99.1.0/24       172.16.11.1     0.0.0.0         65000?
```

The two routes from site 2 (10.101.2.0/24 and 198.51.100.128/25, both with path 65101) are missing from what XR01 sends
to CEA1; the routes without 65101 in their path go out. This was captured after Task M9-4 with `as-override` removed.

`as-override` under the CE neighbour's address family replaces the customer's AS in the path with the provider's, and
the route goes out with `65000 65000`. That is how site 2's routes look in CEA1's BGP table:

```console
CEA1#show ip bgp
...
     Network          Next Hop            Metric LocPrf Weight Path
 *>   10.101.1.0/24    0.0.0.0                  0         32768 i
 *>   10.101.2.0/24    172.16.11.1                            0 65000 65000 i
...
```

The alternative, `allowas-in`, is configured on the receiving router, the CE, which belongs to the customer.
`as-override` is the one the provider can settle on its own PE.

### 2.5 A mark of the site: site-of-origin

With the AS replaced, the AS path can no longer show a loop. That is no problem while a site is attached to one PE
only; but when a site is attached to two PEs, a route that left the site can come back into the same site through the
other PE.

**Site-of-origin** (SoO) marks a route with the site it came from, in an extended community. A PE adds the neighbour's
SoO to the routes it receives from a CE, and does not send a route with that mark to a neighbour with the same SoO. RFC
4364 says that a route must never be distributed to a CE of the site that its Site of Origin attribute identifies
(section 8).

In the lab, with SoO 65101:1 on XR01's neighbour CEA1, site 1's route arrived at RT02 with the mark:

```console
RT02#show ip bgp vpnv4 vrf CUST-A 10.101.1.0
BGP routing table entry for 10.255.0.12:101:10.101.1.0/24, version 20
Paths: (1 available, best #1, table CUST-A)
  Advertised to update-groups:
     1
  Refresh Epoch 1
  65101, imported path from 10.255.0.1:101:10.101.1.0/24 (global)
    10.255.0.1 (metric 20) (via default) from 10.255.0.21 (10.255.0.21)
      Origin IGP, metric 0, localpref 100, valid, internal, best
      Extended Community: SoO:65101:1 RT:65000:101
      Originator: 10.255.0.1, Cluster list: 10.255.0.21
      mpls labels in/out nolabel/24004
```

Then RT02's neighbour CEA2 was given the same 65101:1, as if CEA2 were a CE of the same site as site 1. RT02 stopped
sending site 1's routes to CEA2:

```console
RT02#show ip bgp vpnv4 vrf CUST-A 10.101.1.0
...
  Not advertised to any peer
...
      Extended Community: SoO:65101:1 RT:65000:101
RT02#show ip bgp vpnv4 vrf CUST-A neighbors 172.16.12.2 advertised-routes
...
Route Distinguisher: 10.255.0.12:101 (default for vrf CUST-A)
 *>i  0.0.0.0          10.255.0.1                    100      0 64500 i
 *>i  10.99.1.0/24     10.255.0.1               0    100      0 ?
Total number of prefixes 2
```

Each site in the lab is attached to one PE only, so an SoO normally changes nothing here. The same value on two sites
was only to watch the mark work (it was removed after the measurement).

## 3. Building it on IOS XR

### 3.1 The route reflector

This configuration makes XR02 the VPNv4 route reflector of the two PEs.

:::config fold XR02 — VPNv4 route reflector for the two PEs
router bgp 65000
 bgp router-id 10.255.0.21
 address-family vpnv4 unicast                ## VPNv4 at the top; no retain needed (an RR keeps everything by default)
 !
 neighbor 10.255.0.1                         ## the PE XR01
  remote-as 65000
  update-source Loopback0
  address-family vpnv4 unicast
   route-reflector-client                    ## the client goes under the VPNv4 address family
  !
 !
 neighbor 10.255.0.12                        ## the PE RT02
  remote-as 65000
  update-source Loopback0
  address-family vpnv4 unicast
   route-reflector-client
  !
 !
!
:::

The PEs have the route reflector as their only neighbour (XR01 and RT02 in section 3.1 of the previous page). Nothing
about clients is configured on the PEs.

### 3.2 AS override

The configuration of XR01's neighbour CEA1:

:::config fold XR01 — send to a site with the same AS number, with the AS replaced
router bgp 65000
 vrf CUST-A
  neighbor 172.16.11.2
   address-family ipv4 unicast
    as-override                              ## replace 65101 in the path with 65000 when sending to CEA1
   !
  !
 !
!
:::

:::try
Take the override away. Do it after Task M9-2.

1. On XR01, remove `as-override` from the neighbour 172.16.11.2 in CUST-A and commit.
2. On XR01, run `show bgp vrf CUST-A 10.101.2.0/24` and
   `show bgp vrf CUST-A neighbors 172.16.11.2 advertised-routes`. On CEA1, run `show ip bgp`.
3. Put `as-override` back and commit.

What the lab measured: within 20 seconds, XR01 showed `Not advertised to any peer` for the routes of site 2, they were
gone from `advertised-routes`, and CEA1 no longer had them. XR01 withdrew them, rather than sending them with 65101 in
the path. With the line back, CEA1 had them again with `65000 65000`.
:::

### 3.3 Site-of-origin

The SoO goes under the CE neighbour's address family, with one value per site. A site attached to two PEs gets the same
value on both PEs.

:::config XR01 — mark CEA1's routes with their site
router bgp 65000
 vrf CUST-A
  neighbor 172.16.11.2
   address-family ipv4 unicast
    site-of-origin 65101:1                   ## added to the routes from CEA1; routes with this mark are not sent to CEA1
   !
  !
 !
!
:::

:::config RT02 (IOS XE) — the same on IOS XE
router bgp 65000
 address-family ipv4 vrf CUST-A
  neighbor 172.16.12.2 soo 65101:1           ## on IOS XE, soo on the neighbour line
 exit-address-family
!
:::

## Practice

Go to lab **XRT-09** and do Task M9-2. It starts where Task M9-1 ended.

<p class="tolab"><a href="/_learn?id=XRT-09">Open lab XRT-09 in the workspace</a> — <a href="93-m9-practice-2.html">Task M9-2</a></p>

:::note
The sources are those of the unit's pages (listed at the end of page *How L3VPN works*). The points of this page follow
sections 4.3.2, 4.3.3, 7 and 8 of RFC 4364; the BGP command references for the Cisco 8000 and the NCS 5500
(`retain route-target`, `as-override`, `allowas-in`, `site-of-origin`); the Routing Configuration Guide for the ASR 9000
(IOS XR 24.x: route reflectors and `retain route-target`); the TAC document "Cisco IOS-XR BGP with MPLS Designs"; and
the IOS XRd data sheet. The following come from measurement in lab XRT-09 and its PoC: the route reflector without
clients and with `retain`, the AS path check before sending, the SoO mark and its effect, and the forwarding of XRd as a
PE.
:::
