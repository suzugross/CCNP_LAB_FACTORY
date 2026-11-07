# M9 — Shared services and the Internet

This page shows how to exchange some routes between VPNs, or between a VPN and the global table, while keeping the
customers apart. It covers blueprint 4.3.b (extranet and Internet access) and is for Tasks M9-3 and M9-4. Read
section 2.3 of the page *How L3VPN works* (route targets) first.

## 1. What it is good for

### 1.1 A shared server, with the customers still apart

A provider offers services such as DNS, monitoring or a gateway to a cloud to many customers. It wants the servers in
one place, but the customers' VPNs must stay apart from each other. A copy of the servers per customer, or a circuit per
customer to reach them, multiplies the work by the number of customers.

### 1.2 The Internet for VPN customers too

VPN customers want the Internet as well. A separate Internet circuit at each site would do, but it doubles the circuits
and the CE configuration. If the same PE can provide both, the customer uses one circuit for both.

### 1.3 The answers

Both come from combining the route targets that decide where routes are imported, and from copying routes between a
VRF and the global table.

| Problem | Answer | Section |
|---|---|---|
| Show a shared server to every customer | the customer VRFs import a tag that the server VRF puts on its routes | 2.1 |
| Keep the customers invisible to each other | the customer VRFs do not import each other's tags; importing is not passed on | 2.2 |
| Share only some routes | an export policy adds the tag to those routes only | 2.3 |
| Bring Internet routes into a VRF | import from the global table into the VRF (import from default-vrf) | 2.5 |
| Send customer routes to the Internet | export from the VRF to the global table (export to default-vrf) | 2.5 |

## 2. How it works

### 2.1 Route targets decide who is connected to whom

So far each VRF used one RT for both export and import: customer A's two sites import each other with 65000:101, and
customer B uses 65000:102. RFC 4364 says that one RT used for both export and import makes a closed VPN, and that
different RTs for export and import build other shapes such as hub and spoke (section 4.3.5).

Shared services are built from such a combination. The lab's convention:

| VRF | Exports | Imports |
|---|---|---|
| CUST-A (XR01 and RT02) | 65000:101 | 65000:101, 65000:900 |
| CUST-B (XR01 and RT02) | 65000:102 | 65000:102, 65000:900 |
| SVC (XR01) | 65000:999 (and 65000:900 on 10.99.1.0/24) | 65000:101, 65000:102 |

- The customer VRFs import 65000:900, so they see the route that SVC tags with 900 (10.99.1.0/24).
- SVC imports 65000:101 and 65000:102, so it sees both customers' routes, and the servers' replies have a path back.
- Customer A's VRF does not import 65000:102, so it does not see customer B's routes, and the other way round.

In the lab with all four tasks done, SVC's table lists the sites of both customers, and customer B's table has only the
shared server (10.99.1.0/24) added:

```console
RP/0/RP0/CPU0:XR01#show route vrf SVC
...
S    10.99.1.0/24 [1/0] via 172.16.91.2, 00:13:36
S    10.99.2.0/24 [1/0] via 172.16.91.2, 00:13:36
B    10.101.1.0/24 [20/0] via 172.16.11.2 (nexthop in vrf CUST-A), 00:02:53
B    10.101.2.0/24 [200/0] via 10.255.0.12 (nexthop in vrf default), 00:06:25
B    10.102.1.0/24 [20/0] via 172.16.21.2 (nexthop in vrf CUST-B), 00:13:30
B    10.102.2.0/24 [200/0] via 10.255.0.12 (nexthop in vrf default), 00:00:24
...
RP/0/RP0/CPU0:XR01#show route vrf CUST-B
...
B    10.99.1.0/24 [200/0] via 172.16.91.2 (nexthop in vrf SVC), 00:13:17
B    10.102.1.0/24 [20/0] via 172.16.21.2, 00:13:48
B    10.102.2.0/24 [200/0] via 10.255.0.12 (nexthop in vrf default), 00:00:24
C    172.16.21.0/24 is directly connected, 00:14:06, GigabitEthernet0/0/0/3
L    172.16.21.1/32 is directly connected, 00:14:06, GigabitEthernet0/0/0/3
```

### 2.2 Importing is not passed on

SVC imports customer B's routes, but never hands them to customer A. A VRF exports its own routes (learned from CEs or
static routes), and a route imported from another VRF keeps its original RT (65000:102 for customer B). It never gets
SVC's export RT 65000:999, so customer A does not learn customer B through SVC. From CEA1 the shared server is reachable,
and customer B and the internal segment of SVC are not:

```console
CEA1#ping 10.99.1.1 source Loopback10 repeat 3
...
Success rate is 100 percent (3/3), round-trip min/avg/max = 1/2/3 ms
CEA1#ping 10.102.1.1 source Loopback10 repeat 3
...
Success rate is 0 percent (0/3)
CEA1#ping 10.99.2.1 source Loopback10 repeat 3
...
Success rate is 0 percent (0/3)
```

Shared services come with one more condition. SVC imports both customers' routes into one table, so if the customers'
addresses overlap, SVC cannot tell them apart. When customer B was given 10.101.2.0/24 too (section 2.2 of the previous
page), CUST-A and CUST-B each had their own 10.101.2.0/24, but SVC's table chose only one of them (customer A's).
Customers that use a shared service must have addresses that do not overlap, or NAT has to resolve the overlap.

### 2.3 A tag on one route only

With route targets alone, a VRF exports every route with the same targets. To give one route an extra target, IOS XR
attaches a route policy to the VRF's address family: `export route-policy` acts on the routes leaving the VRF,
`import route-policy` on the routes entering it.

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

The first output is the policy without `additive`, the second with it. 10.99.2.0/24, which does not match the policy's
condition, leaves with the VRF's RT only:

```console
RP/0/RP0/CPU0:XR01#show bgp vrf SVC 10.99.2.0/24
BGP routing table entry for 10.99.2.0/24, Route Distinguisher: 10.255.0.1:900
...
      Extended community: RT:65000:999
```

An export policy cannot hold a route back: the command reference says so, and in the lab a route that the policy did
not pass still left the VRF with the VRF's route targets. 10.99.2.0/24 is kept from the customers by its route target,
which no customer imports, not by the policy. An import policy is the second of two filters: it sees only the routes
that already match an import route target of the VRF.

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

### 2.4 Several VRFs on one PE

The shared services and customers A and B all have a VRF on XR01. Route targets work between them as between two PEs
(RFC 4364, section 4.3.6): XR01 imports 10.99.1.0/24 from SVC into CUST-A and CUST-B itself, with no remote PE involved.

```console
RP/0/RP0/CPU0:XR01#show bgp vrf CUST-A 10.99.1.0/24
BGP routing table entry for 10.99.1.0/24, Route Distinguisher: 10.255.0.1:101
...
  Local
    172.16.91.2 from 0.0.0.0 (10.255.0.1)
      Origin incomplete, metric 0, localpref 100, weight 32768, valid, extranet, best, group-best, import-candidate, imported
      Received Path ID 0, Local Path ID 1, version 41
      Extended community: RT:65000:900 RT:65000:999
      Origin-AS validity: not-found
      Source AFI: VPNv4 Unicast, Source VRF: SVC, Source Route Distinguisher: 10.255.0.1:900
```

`extranet` and `Source VRF: SVC` say that the route was imported from VRF SVC on the same router. Its next hop is SVC's
address and its weight that of a local route. The routing table says where the next hop lives (`show route vrf CUST-B`
in section 2.1): in VRF SVC for the shared servers, in the global table (`vrf default`) for a route from RT02, whose
next hop is RT02's loopback.

### 2.5 Between a VRF and the global table

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
exported from CUST-A, and XR01 sends it to INET. XR01's global BGP table holds only the Internet's routes and customer
A's two public segments: neither the customer's LANs (10.101.0.0/16) nor customer B are in it.

```console
RP/0/RP0/CPU0:XR01#show bgp ipv4 unicast
...
   Network            Next Hop            Metric LocPrf Weight Path
*> 0.0.0.0/0          192.0.2.2                              0 64500 i
*> 198.51.100.0/25    172.16.11.2              0             0 65101 i
*>i198.51.100.128/25  10.255.0.12              0    100      0 65101 i
*> 203.0.113.0/24     192.0.2.2                0             0 64500 i
```

A static route can do the same for one prefix: inside `router static` → `vrf CUST-A`, a route such as
`0.0.0.0/0 vrf default 192.0.2.2` has its next hop in the global table. Unlike the BGP leak, it reaches only XR01's CEs
unless it is redistributed into the VRF's BGP.

### 2.6 Following a packet

In the global table, site 2's segment keeps its VPN next hop and labels. A packet from INET to 198.51.100.129 is labelled
at XR01 with the transport label for RT02 and RT02's VPN label, and RT02 delivers it in CUST-A:

:::topo
nodes:
  INET: {at: [0, 1], kind: host}
  XR01: [1.3, 1]
  RT01: [2.6, 0.15]
  RT03: [2.6, 1.85]
  RT02: [3.9, 1]
  CEA2: {at: [5.2, 1], kind: host}
links:
  - [INET, XR01, "IP (global)"]
  - [XR01, RT01, "16 | 23"]
  - [RT01, RT02, "23"]
  - [RT02, CEA2, "IP (CUST-A)"]
  - {a: XR01, b: RT03, style: dashed}
  - {a: RT03, b: RT02, style: dashed}
:::

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
because RT02 is the next router, so RT02 (hop 3) receives the VPN label alone. The key of this path is that a packet of
the global table gets a VPN label at XR01 and enters CUST-A.

The other way, from CEA2 to INET, RT02 sends the packet to XR01 with XR01's aggregate label 24009 at the bottom; XR01
looks up the destination in CUST-A, finds the default route with its next hop in the global table, and sends the packet
to INET:

```console
CEA2#traceroute 203.0.113.10 source Loopback11 numeric timeout 1 probe 1
  1 172.16.12.1 [AS 64500] 0 msec
  2 10.0.12.11 [AS 64500] [MPLS: Labels 22/24009 Exp 0] 2 msec
  3 10.0.1.1 [AS 64500] 3 msec
  4 192.0.2.2 [AS 64500] 2 msec
```

24009 is not the label of a route learned from a CE, so XR01 looks the destination up again in the VRF table (appendix,
section 1).

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

## 3. Building it on IOS XR

### 3.1 Shared services

This configuration connects SVC to XR01 and adds the customers' tag to 10.99.1.0/24 only.

:::config fold XR01 — the shared services' VRF, with a tag added to one route only
interface GigabitEthernet0/0/0/4              ## the interface to SVC
 vrf SVC
 ipv4 address 172.16.91.1 255.255.255.0
!
route-policy SVC-EXPORT                       ## the export policy
  if destination in (10.99.1.0/24) then
    set extcommunity rt (65000:900) additive  ## additive: add 900 to the VRF's RT (999)
  endif
  pass
end-policy
!
vrf SVC
 address-family ipv4 unicast
  import route-target                         ## import both customers (the path back)
   65000:101
   65000:102
  !
  export route-policy SVC-EXPORT
  export route-target                         ## the RT on every route
   65000:999
  !
 !
!
router static
 vrf SVC
  address-family ipv4 unicast                 ## SVC runs no routing protocol
   10.99.1.0/24 172.16.91.2
   10.99.2.0/24 172.16.91.2
  !
 !
!
router bgp 65000
 vrf SVC
  rd 10.255.0.1:900
  address-family ipv4 unicast
   redistribute static                        ## the static routes into the VRF's BGP, and out in VPNv4
  !
 !
!
:::

### 3.2 Internet access

This configuration runs eBGP with INET in the global table and leaks routes between CUST-A and the global table.

:::config fold XR01 — Internet routes into the VRF, public segments to the Internet
interface GigabitEthernet0/0/0/5              ## the interface to INET (global table)
 ipv4 address 192.0.2.1 255.255.255.0
!
route-policy TO-INTERNET                      ## only the public segments go to INET
  if destination in (198.51.100.0/25, 198.51.100.128/25) then
    pass
  endif
end-policy
!
route-policy DEFAULT-ONLY                     ## only the default route comes into the VRF
  if destination in (0.0.0.0/0) then
    pass
  endif
end-policy
!
route-policy CUST-A-PUBLIC                    ## only the public segments go out to the global table
  if destination in (198.51.100.0/25, 198.51.100.128/25) then
    pass
  endif
end-policy
!
vrf CUST-A
 address-family ipv4 unicast
  import from default-vrf route-policy DEFAULT-ONLY advertise-as-vpn     ## to the other PEs (RT02) too
  export to default-vrf route-policy CUST-A-PUBLIC allow-imported-vpn    ## routes learned from RT02 too
 !
!
router bgp 65000
 address-family ipv4 unicast                  ## IPv4 unicast in the global table
 !
 neighbor 192.0.2.2                           ## eBGP with INET
  remote-as 64500
  address-family ipv4 unicast
   route-policy PASS in
   route-policy TO-INTERNET out
  !
 !
!
:::

### 3.3 Handing over with a static route

For a single prefix, a VRF's static route can have its next hop in the global table:

:::config XR01 — the VRF's default route, to INET in the global table
router static
 vrf CUST-A
  address-family ipv4 unicast
   0.0.0.0/0 vrf default 192.0.2.2            ## the next hop is looked up in the global table (vrf default)
  !
 !
!
:::

In this form the default route only enters XR01's routing table for CUST-A: unless it is redistributed into the VRF's
BGP, it does not reach the sites behind RT02. The way back (the public segments into the global table) has to be
provided separately.

## Practice

Go to lab **XRT-09** and do Tasks M9-3 and M9-4. They start where Task M9-2 ended.

<p class="tolab"><a href="/_learn?id=XRT-09">Open lab XRT-09 in the workspace</a> — <a href="95-m9-practice-3.html">Tasks M9-3 and M9-4</a></p>

:::note
The sources are those of the unit's pages (listed at the end of page *How L3VPN works*). The points of this page follow
sections 4.3.5 and 4.3.6 of RFC 4364; the BGP command references for the Cisco 8000 and the NCS 5500
(`export route-policy`); the Routing Configuration Guide for the ASR 9000 (IOS XR 24.x: VRF dynamic route leaking with
`advertise-as-vpn` and `allow-imported-vpn`, the routing policy for VRF import and export, static routes into another
VRF); and the TAC document "Configure Route Leak between GRT and VRF with IOS XR". The following come from measurement in
lab XRT-09 and its PoC: the route targets replaced without `additive`, the export of routes that the policy does not
pass, the import between VRFs of one PE, the shared service that cannot tell overlapping addresses apart, the leaking,
the handover with a static route, and the labels.
:::
