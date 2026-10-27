# M9 — L3VPN

A provider sells each customer a private network across its core, and keeps the customers apart even when they use
the same addresses. That is an MPLS Layer 3 VPN (L3VPN). This page covers section 4.3 of the CCNP Service Provider
blueprint: an L3VPN inside one provider (4.3.a) and shared services, an extranet and Internet access (4.3.b). The VPNs
between providers (Inter-AS, 4.1.b) and a provider's customer that is itself a provider (CSC, 4.1.c) are described at
the end. You know L3VPN on IOS from the Enterprise track; this page concentrates on what IOS XR does in its own way.

The lab is XRT-09. Its core is the one of lab XRT-07: XR01 and RT02 are the provider edges (PEs), RT01 and RT03 the
core routers, with IS-IS and LDP. XR02 is new: a route reflector for VPN routes. The outputs on this page were captured
on IOS XRv 9000 26.1.1 (XR01), IOS XRd 26.1.1 (XR02) and IOS XE 17.15 on IOL (the other routers). The same steps with
XRd as XR01 gave the same control plane; section 2.3 says why XR01 is an XRv 9000 here.

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
SVC holds the provider's shared servers, and INET stands for the Internet. The route reflector XR02 hangs off RT03 and
is not on the path of any customer packet.

## 1. A VRF on IOS XR

### 1.1 The parts

The parts are the same on every platform. A **VRF** (VPN routing and forwarding instance) is a separate routing table
on a PE, with the interfaces of one customer in it. A **route distinguisher** (RD) is eight bytes put in front of each
customer prefix when it leaves the VRF, so that two customers' 10.0.0.0/24 stay two different routes in BGP. The result
is a VPN-IPv4 (VPNv4) route, which RFC 4364 defines in section 4.2. A **route target** (RT) is an extended community
attached to the route on export. A PE imports a route into each VRF that imports one of the route's targets (RFC 4364,
section 4.3.1). The RD makes a route unique; the RT decides where it goes.

A packet of customer A from CEA1 to site 2 carries two labels across the core. The bottom one is the **VPN label**:
RT02 chose it and advertised it in BGP with the route, and it tells RT02 which VRF the packet belongs to. The top one is
the transport label from LDP, which takes the packet to RT02's loopback, exactly as in unit M8. The core routers switch
on the top label only and never see the customer's address.

### 1.2 Where each part goes

On IOS, the RD and the RTs are written together under `vrf definition`. IOS XR splits them:

- the RTs belong to the VRF: `vrf <name>` → `address-family ipv4 unicast` → `import route-target` and
  `export route-target`, each a sub-mode that takes one route target per line;
- the interface joins the VRF with `vrf <name>`;
- the RD belongs to BGP: `router bgp <AS>` → `vrf <name>` → `rd`, with the CE neighbours of that VRF under the same
  `vrf`.

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

:::note
The L3VPN configuration guides for the NCS 5500 and the ASR 9000 (release 7.11) say that an interface must lose its
IPv4 and IPv6 addresses before its VRF is assigned, removed or changed, and that the change is rejected otherwise. In
the lab, IOS XR 26.1.1 (both XRv 9000 and XRd) accepted the change with the address in place, and kept the address.
Moving an interface from the global table into a VRF, back again, or into another existing VRF worked after a few
seconds; moving it into a VRF created in the same commit left it unable to reach its neighbour in one test. Follow the
guides: in lab XRT-09 the customer interfaces have no address, so `vrf` and `ipv4 address` go in together.
:::

### 1.3 The session with the CE

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

What the lab measured: the session stayed up and was not reset (its up time kept counting). XR01 showed `0!` and
counted CEB1's route under `No policy: 1`, and CEB1's BGP routes were gone: it received nothing either
(`State/PfxRcd 0`). Within 30 seconds of the lines going back, XR01 accepted the route again and CEB1 had its routes
back.
:::

## 2. VPN routes between the provider edges

### 2.1 VPNv4

The PEs exchange the VPN routes in iBGP, in the VPNv4 address family, between their loopbacks. A VPNv4 route carries the
RD, the prefix, the route targets and the VPN label; its next hop is the PE's Loopback0, which LDP has a label for.

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
      Extended community: RT:65000:101
      Originator: 10.255.0.12, Cluster list: 10.255.0.21
```

This is site 2 of customer A as XR01 received it: RT02's RD, RT02's loopback as the next hop, RT02's VPN label 22,
and the route target 65000:101. It came from XR02 (`Cluster list`). `not-in-vrf` marks the received copy; XR01 imports
it into CUST-A as a copy under its own RD, 10.255.0.1:101, which is what `show bgp vrf CUST-A` lists.

IOS XR allocates a VPN label for each prefix by default (**per-prefix**). `label mode per-vrf` under the VRF's address
family in BGP gives one label for the whole VRF; the PE then looks up the destination in the VRF's table, as for the
routes that IOS XR always labels per VRF (connected, aggregated and local ones). `show mpls forwarding` shows the
difference:

```console
RP/0/RP0/CPU0:XR01#show bgp vrf CUST-A labels
   Network            Next Hop        Rcvd Label      Local Label
Route Distinguisher: 10.255.0.1:101 (default for vrf CUST-A)
*> 0.0.0.0/0          192.0.2.2       nolabel         24009
*> 10.101.1.0/24      172.16.11.2     nolabel         24004
*>i10.101.2.0/24      10.255.0.12     22              nolabel
*> 198.51.100.0/25    172.16.11.2     nolabel         24005
*>i198.51.100.128/25  10.255.0.12     23              nolabel

RP/0/RP0/CPU0:XR01#show mpls forwarding
Local  Outgoing    Prefix             Outgoing     Next Hop        Bytes
Label  Label       or ID              Interface                    Switched
------ ----------- ------------------ ------------ --------------- ------------
24000  20          10.255.0.21/32     Gi0/0/0/1    10.0.3.13       5123
24001  Pop         10.255.0.13/32     Gi0/0/0/1    10.0.3.13       4106
24002  16          10.255.0.12/32     Gi0/0/0/0    10.0.1.11       16120
24003  Pop         10.255.0.11/32     Gi0/0/0/0    10.0.1.11       2986
24004  Unlabelled  10.101.1.0/24[V]   Gi0/0/0/2    172.16.11.2     0
24005  Unlabelled  198.51.100.0/25[V] Gi0/0/0/2    172.16.11.2     0
24006  Unlabelled  10.102.1.0/24[V]   Gi0/0/0/3    172.16.21.2     0
24007  Unlabelled  10.99.1.0/24[V]    Gi0/0/0/4    172.16.91.2     500
24008  Unlabelled  10.99.2.0/24[V]    Gi0/0/0/4    172.16.91.2     0
24009  Aggregate   CUST-A: Per-VRF Aggr[V]   \
                                      CUST-A                       2500
```

This is the lab after all four tasks. Each route from a CE has its own label, which XR01 removes and sends unlabelled
to the CE (`[V]` marks a VRF prefix). The default route that XR01 imports from the global table in Task M9-4 does not
come from a CE, so it gets the VRF's aggregate label 24009 even in per-prefix mode.

:::try
Give CUST-A a single label. Do it after Task M9-2 (the lab measured it after Task M9-4).

1. On XR01, under `router bgp 65000` → `vrf CUST-A` → `address-family ipv4 unicast`, configure `label mode per-vrf`
   and commit.
2. On XR01, run `show bgp vrf CUST-A labels` and `show mpls forwarding`. On RT02, run
   `show ip bgp vpnv4 vrf CUST-A labels`; on CEA2, `ping 10.101.1.1 source Loopback10`.
3. Remove `label mode` and commit.

What the lab measured: every route that XR01 learned from CEA1 took label 24009, the one that the VRF already had for
the imported default route, and 24004 and 24005 disappeared from `show mpls forwarding`. Within 20 seconds RT02 showed
`nolabel/24009` for them, and the ping went through. After `label mode` went away, the routes had 24004 and 24005
again.
:::

### 2.2 Route-target filtering

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
PE holds no routes for, IOS XR asks its neighbours to send their routes again (a BGP **route refresh**). In the lab the
routes of customer B arrived within five seconds of the VRF's commit, and `show bgp vpnv4 unicast neighbors` counted
the refresh:

```console
RP/0/RP0/CPU0:XR01#show bgp vpnv4 unicast neighbors 10.255.0.21 | include "refresh request|Failed RT"
  Route refresh request: received 0, sent 3
    No policy: 0, Failed RT match: 2
```

Here 65000:102 had just been added back to CUST-B's import route targets. In the PoC, configuring the VRF CUST-B from
scratch did the same: one route refresh, and customer B's routes within five seconds.

:::try
Watch XR01 drop routes and ask for them again. Do it after Task M9-2 and before Task M9-3: from Task M9-3 on, VRF
SVC imports 65000:102 too, and XR01 keeps customer B's routes for it.

1. On XR01, run `show bgp vpnv4 unicast neighbors 10.255.0.21 | include "refresh request|Failed RT"`.
2. Remove 65000:102 from the import route targets of CUST-B and commit. Run
   `show bgp vpnv4 unicast rd 10.255.0.12:102`.
3. Run `clear bgp vpnv4 unicast 10.255.0.21 soft in`, which makes XR02 send its routes again, and then the command of
   step 1.
4. Put 65000:102 back and commit. Run the command of step 1 and `show bgp vrf CUST-B`.

What the lab measured: XR01 dropped 10.102.2.0/24 at once; the table of RD 10.255.0.12:102 was empty. After the soft
refresh, the neighbour detail showed `Failed RT match: 2`, and the refresh requests sent had gone from 0 to 2. With
65000:102 back, the counter went to 3 and 10.102.2.0/24 was in CUST-B again within five seconds; CEB1 reached CEB2.
:::

### 2.3 A route reflector for VPNv4

A full mesh of VPNv4 sessions between the PEs grows with the square of their number, so providers use route reflectors.
A route reflector is the one router that must keep every VPNv4 route, whether or not it has a VRF that imports it. On
IOS XR it does that by default, and it is a route reflector as soon as it has one client. A client is a property of a
neighbour's address family: `route-reflector-client` goes under `neighbor` → `address-family vpnv4 unicast`. Written under
another address family, it does nothing for VPNv4.

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
neighbour, and only clients change that. The command is for an Inter-AS option B border router (section 6), which must
keep routes it has no VRF for; the `route-policy` form lets a route reflector keep only some route targets, to split
the VPNs between several reflectors.

XR02 runs IOS XRd. Cisco offers XRd in a control-plane form for route reflectors and other roles off the forwarding
path. It is not suitable as XR01 in this lab: in the PoC with XRd as XR01, ping passed both ways, but TCP and UDP
packets that XRd received from a CE and sent on with labels, or routed between two VRFs or between a VRF and the global
table, arrived with a bad checksum. Traceroutes from CEA1 stopped after the first hops. Packets that XRd received with
labels and sent to a CE were intact. IOS XRv 9000 forwarded all of them correctly.

## 3. Two sites in one AS

### 3.1 AS override

Customer A uses AS 65101 at both sites. The route of site 2 reaches XR01 with AS path 65101, and CEA1 would drop it as a
loop. IOS and IOS XR handle this differently. An IOS PE sends the route and the CE drops it. IOS XR does not send it at
all: it checks the AS path against the neighbour's AS before sending.

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
the route goes out with `65000 65000`. The alternative, `allowas-in`, is configured on the receiving router, the CE,
which belongs to the customer. When a site is attached to two PEs, a replaced AS no longer stops a route from going back
into the site it came from; `site-of-origin` under the same neighbour marks the routes of a site with an extended
community, and IOS XR does not send a route with that mark back to a neighbour with the same mark.

:::try
Take the override away. Do it after Task M9-2.

1. On XR01, remove `as-override` from the neighbour 172.16.11.2 in CUST-A and commit.
2. On XR01, run `show bgp vrf CUST-A 10.101.2.0/24` and
   `show bgp vrf CUST-A neighbors 172.16.11.2 advertised-routes`. On CEA1, run `show ip bgp`.
3. Put `as-override` back and commit.

What the lab measured: within 20 seconds, XR01 showed `Not advertised to any peer` for the routes of site 2, they were
missing from `advertised-routes`, and CEA1 no longer had them: XR01 withdrew them rather than send them with 65101 in
the path. After the line went back, CEA1 had them again with `65000 65000`.
:::

## 4. Shared services

### 4.1 Route policies on import and export

An **extranet** lets VPNs share some routes and not others. With route targets alone, a VRF exports every route with the
same targets. To give one route an extra target, IOS XR attaches a route policy to the VRF's address family:
`export route-policy` acts on the routes leaving the VRF, `import route-policy` on the routes entering it.

In the lab, every route of the shared services carries 65000:999, the VRF's export route target, and 10.99.1.0/24 carries
65000:900 in addition, which the customers' VRFs import. The policy sets the extra target on that prefix only:

```text
route-policy SVC-EXPORT
  if destination in (10.99.1.0/24) then
    set extcommunity rt (65000:900) additive
  endif
  pass
end-policy
```

`additive` matters. Without it, `set extcommunity rt` replaces the route targets that the route already has, and
10.99.1.0/24 leaves with 65000:900 alone:

```console
RP/0/RP0/CPU0:XR01#show bgp vrf SVC 10.99.1.0/24 | include Extended
      Extended community: RT:65000:900

RP/0/RP0/CPU0:XR01#show bgp vrf SVC 10.99.1.0/24 | include Extended
      Extended community: RT:65000:900 RT:65000:999
```

The first output is the policy without `additive`, the second with it.

An export policy cannot hold a route back: the command reference says so, and in the lab a route that the policy did
not pass still left the VRF with the VRF's route targets. 10.99.2.0/24 is kept from the customers by its route target,
which no customer imports, not by the policy. An import policy is the second of two filters: it sees only the routes
that already match an import route target of the VRF.

### 4.2 Several VRFs on one PE

The shared services and customers A and B all have a VRF on XR01. Route targets work between them as between two PEs:
XR01 imports 10.99.1.0/24 from SVC into CUST-A and CUST-B itself, with no remote PE involved, and SVC imports both
customers' routes, so the return traffic has a path. The customers still do not see each other: a route of customer B
that SVC imports keeps its own route target, 65000:102, and is not exported again with SVC's.

```console
RP/0/RP0/CPU0:XR01#show bgp vrf CUST-A
   Network            Next Hop            Metric LocPrf Weight Path
Route Distinguisher: 10.255.0.1:101 (default for vrf CUST-A)
*> 0.0.0.0/0          192.0.2.2                              0 64500 i
*> 10.99.1.0/24       172.16.91.2              0         32768 ?
*> 10.101.1.0/24      172.16.11.2              0             0 65101 i
*>i10.101.2.0/24      10.255.0.12              0    100      0 65101 i
*> 198.51.100.0/25    172.16.11.2              0             0 65101 i
*>i198.51.100.128/25  10.255.0.12              0    100      0 65101 i

RP/0/RP0/CPU0:XR01#show route vrf CUST-B bgp
B    10.99.1.0/24 [200/0] via 172.16.91.2 (nexthop in vrf SVC), 00:04:01
B    10.102.2.0/24 [200/0] via 10.255.0.12 (nexthop in vrf default), 00:17:29
```

In CUST-A, 10.99.1.0/24 has SVC's address as its next hop and the weight of a local route: it was imported from VRF
SVC on the same router. The routing table says where the next hop lives: in VRF SVC for the shared servers, in the
global table (`vrf default`) for a route from RT02, whose next hop is RT02's loopback.

:::try
Take `additive` away. Do it after Task M9-3.

1. On XR01, enter the route policy SVC-EXPORT again with `set extcommunity rt (65000:900)`, without `additive`, and
   commit.
2. On XR01, run `show bgp vrf SVC 10.99.1.0/24`. On RT02, run `show ip bgp vpnv4 all 10.99.1.0`; on CEA2,
   `ping 10.99.1.1 source Loopback10`.
3. Put `additive` back and commit.

What the lab measured: 10.99.1.0/24 left with `RT:65000:900` alone, and RT02's copies showed the same. The ping still
went through: the customers import 65000:900, so nothing that they see changes. What broke is the provider's
convention, which anything that relies on 65000:999 would notice. With `additive` back, the route carried both route
targets again.
:::

## 5. Internet access

### 5.1 Between a VRF and the global table

Customer A's public segments must reach the Internet, which XR01 learns in its global table from INET. IOS XR leaks BGP
routes between a VRF and the global table (the default VRF) with two commands under the VRF's address family, each with
a mandatory route policy:

- `import from default-vrf route-policy <name>` brings global routes into the VRF. They go to the VRF's CEs, and with
  `advertise-as-vpn` also to the other PEs, as VPNv4 routes with the VRF's route target. Without it, CEA1 had a default
  route and CEA2, behind RT02, had none.
- `export to default-vrf route-policy <name>` copies VRF routes into the global table, where they can be sent to INET.
  By default only the routes that XR01 learned from its own CEs are exported. A route learned from another PE, such as
  site 2's 198.51.100.128/25, needs `allow-imported-vpn`.

```console
RP/0/RP0/CPU0:XR01#show route vrf CUST-A 0.0.0.0/0
Routing entry for 0.0.0.0/0
  Known via "bgp 65000", distance 20, metric 0, candidate default path
  Tag 64500, type external
  ...
  Routing Descriptor Blocks
    192.0.2.2, from 192.0.2.2, BGP external
      Nexthop in Vrf: "default", Table: "default", IPv4 Unicast, Table Id: 0xe0000000

RP/0/RP0/CPU0:XR01#show bgp ipv4 unicast 198.51.100.128/25
BGP routing table entry for 198.51.100.128/25
...
  Advertised IPv4 Unicast paths to peers (in unique update groups):
    192.0.2.2
  65101
    10.255.0.12 (metric 30) from 10.255.0.21 (10.255.0.12)
      Received Label 23
      Origin IGP, metric 0, localpref 100, valid, internal, best, group-best, import-candidate, imported
      Extended community: RT:65000:101
      Originator: 10.255.0.12, Cluster list: 10.255.0.21
      Source AFI: VPNv4 Unicast, Source VRF: CUST-A, Source Route Distinguisher: 10.255.0.1:101
      Original Source AFI: VPNv4 Unicast, Original Source Route Distinguisher: 10.255.0.12:101
```

The default route in CUST-A points to INET in the global table. Site 2's public segment is in the global BGP table,
exported from CUST-A, and XR01 sends it to INET.

A static route can do the same for one prefix: inside `router static` → `vrf CUST-A`, a route such as
`0.0.0.0/0 vrf default 192.0.2.2` has its next hop in the global table. Unlike the BGP leak, it reaches only XR01's CEs
unless it is redistributed into the VRF's BGP.

### 5.2 Following a packet

In the global table, site 2's segment keeps its VPN next hop and labels. A packet from INET to 198.51.100.129 is labelled
at XR01 with the transport label for RT02 and RT02's VPN label, and RT02 delivers it in CUST-A:

```console
RP/0/RP0/CPU0:XR01#show cef 198.51.100.128/25
198.51.100.128/25, version 61, internal 0x5000001 0x40 (ptr 0xf7974e8) [1], 0x600 (0xf92fd58), 0xa08 (0xf3357b8)
...
   via 10.255.0.12/32, 5 dependencies, recursive [flags 0x6000]
    path-idx 0 NHID 0x0 [0xedbdd90 0x0]
    recursion-via-/32
    next hop 10.255.0.12/32 via 24002/0/21
     next hop 10.0.1.11/32 GigabitEthernet0/0/0/0 labels imposed {16 23}

INET#traceroute 198.51.100.129 source Loopback10 numeric timeout 1 probe 1
  1 192.0.2.1 4 msec
  2 10.0.1.11 [MPLS: Labels 16/23 Exp 0] 2 msec
  3 172.16.12.1 [MPLS: Label 23 Exp 0] 1 msec
  4 172.16.12.2 2 msec
```

16 is RT01's LDP label for RT02's loopback, and 23 is RT02's VPN label for 198.51.100.128/25. RT01 pops the top label
because RT02 is the next router, so RT02 (hop 3) receives the VPN label alone. The other way, from CEA2 to INET, RT02
sends the packet to XR01 with XR01's aggregate label 24009 at the bottom; XR01 looks up the destination in CUST-A,
finds the default route with its next hop in the global table, and sends the packet to INET:

```console
CEA2#traceroute 203.0.113.10 source Loopback11 numeric timeout 1 probe 1
  1 172.16.12.1 [AS 64500] 0 msec
  2 10.0.12.11 [AS 64500] [MPLS: Labels 22/24009 Exp 0] 2 msec
  3 10.0.1.1 [AS 64500] 3 msec
  4 192.0.2.2 [AS 64500] 2 msec
```

:::try
Take `advertise-as-vpn` away. Do it after Task M9-4.

1. On XR01, under `vrf CUST-A` → `address-family ipv4 unicast`, enter the `import from default-vrf` line again
   without `advertise-as-vpn` and commit.
2. On XR01, run `show bgp vrf CUST-A 0.0.0.0/0`. On RT02, run `show ip route vrf CUST-A 0.0.0.0`. On CEA1 and CEA2,
   run `show ip route 0.0.0.0`, and on CEA2 `ping 203.0.113.10 source Loopback11`.
3. Put `advertise-as-vpn` back and commit.

What the lab measured: XR01 showed the default route as advertised to its CE only (`Advertised to CE peers`, no
`PE peers`). RT02 and CEA2 lost it (`% Network not in table`), CEA1 kept it, and the ping from CEA2 failed. Within a
minute of the keyword going back, CEA2 had the default route again and the ping went through.
:::

## 6. Between providers

When a VPN spans two providers, RFC 4364 (section 10) gives three ways to join them.

- **Option A**: the border routers (ASBRs) of the two providers meet as PE and CE, with one VRF and one interface or
  subinterface per VPN, and plain IP between them. Simple, and it scales with the number of VPNs.
- **Option B**: the ASBRs exchange VPNv4 routes in eBGP, with labels, and keep no VRFs. On IOS XR the ASBR needs
  `retain route-target all` (or a policy) to keep VPNv4 routes it has no VRF for, route policies on the eBGP VPNv4
  session, and a static /32 route to the other ASBR so that the labelled traffic is forwarded.
- **Option C**: the ASBRs carry only the PEs' loopbacks, as BGP labeled unicast (unit M8, Unified MPLS), and the route
  reflectors of the two providers exchange VPNv4 routes in multihop eBGP.

In **Carrier Supporting Carrier** (CSC, section 9 of RFC 4364), the customer of a VPN is itself a provider. The VPN
carries only the customer carrier's loopbacks, with labels (labeled unicast towards the CSC-CE, or LDP in the VRF), and
the customer carrier runs its own VPNs on top.

## 7. Command names

| On IOS | On IOS XR |
|---|---|
| `vrf definition <name>` with `rd` and `route-target` | `vrf <name>` with `import route-target` / `export route-target`; `rd` under `router bgp` → `vrf <name>` |
| `vrf forwarding <name>` (removes the addresses) | `vrf <name>` under the interface |
| `address-family vpnv4` + `neighbor … activate` | `address-family vpnv4 unicast` at the top of BGP and under the neighbour |
| `address-family ipv4 vrf <name>` | `vrf <name>` → `address-family ipv4 unicast` under `router bgp` |
| `neighbor … as-override` | `as-override` under the neighbour's address family |
| `route-target export` + `export map <route-map>` | `export route-target` + `export route-policy <name>` |
| `bgp default route-target filter` (on by default) | always on; `retain route-target` |
| `show ip bgp vpnv4 all` / `vrf <name>` | `show bgp vpnv4 unicast` / `show bgp vrf <name>` |
| `show ip route vrf <name>` | `show route vrf <name>` |

## Practice

Go to lab **XRT-09** and do the M9 tasks. XR01 is an IOS XRv 9000, so the lab takes about ten minutes to build.

<p class="tolab"><a href="/_learn?id=XRT-09">Open lab XRT-09 in the workspace</a> — <a href="91-m9-practice.html">The tasks</a></p>

:::note
Sources: the BGP command references for the Cisco 8000 (cumulative, 2026) and the NCS 5500 (route distinguisher and
`rd auto`, `retain route-target`, `as-override`, `allowas-in`, `site-of-origin`, `label mode`, `export route-policy`); the
Routing Configuration Guide for the ASR 9000, IOS XR 24.x (2026: address families, route reflectors and
`retain route-target`, route refresh for a new VRF, VRF dynamic route leaking with `advertise-as-vpn` and
`allow-imported-vpn`, the routing policy for VRF import and export, static routes into another VRF); the L3VPN
configuration guides for the NCS 5500 and the Cisco 8000 and the MPLS L3VPN guide for the ASR 9000, release 7.11 (VRF
on an interface, Inter-AS option B, CSC); the Cisco 8000 guide "BGP Route Distinguisher"; Cisco TAC documents "Cisco
IOS-XR BGP with MPLS Designs" (2021) and "Configure Route Leak between GRT and VRF with IOS XR"; the IOS XRd data sheet;
RFC 4364. All checked October 2026. The following come from measurement in lab XRT-09 and its PoC: the commit errors,
the interface address kept in a VRF change, the dropped routes and their counters, the route refresh, the route
reflector without clients and with `retain`, the AS path check before sending, the labels, the replaced route targets
without `additive`, the export of routes that the policy does not pass, the leaking, and the forwarding of XRd as a PE.
:::
