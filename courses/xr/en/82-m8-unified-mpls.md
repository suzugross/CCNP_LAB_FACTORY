# M8 — Unified MPLS

The core of the first M8 page was a single IGP domain with a single LDP domain. A provider with thousands of access
routers cannot keep all of them in one IS-IS and one LDP. **Unified MPLS** splits the network into IGP domains and
joins them with BGP, which carries the loopbacks of the provider edges together with labels. This page covers item
3.1.d of the CCNP Service Provider blueprint. It continues lab XRT-07: the core is the same, and a new access network
hangs off XR01.

<p class="tolab"><a href="84-m8-appendix.html">An easier start with pictures: M8 — Appendix: Unified MPLS in pictures</a></p>

## 1. One network, several IGP domains

### 1.1 Why the IGP is split

In an IGP, every router keeps every loopback and every link of its domain, and runs SPF again whenever any of them
changes. LDP then binds a label to every prefix that the IGP brings. That is fine for a core of a few dozen routers,
and it does not scale to the access rings of a mobile or broadband network. The Seamless MPLS architecture draft
(draft-ietf-mpls-seamless-mpls) was written for "10k to 100k MPLS nodes". Cisco's TAC document on Unified MPLS for
IOS XR puts it in two sentences: "The purpose of Unified MPLS is all about scaling", and "In order to scale, you cannot
distribute the IGP prefixes from one IGP into the other."

The services still need a label switched path from one provider edge (PE) to another, across the domains.
Redistributing the loopbacks between the IGPs would bring the scale problem back, so the IGPs stay apart, and BGP
carries the loopbacks with labels: **BGP labeled unicast** (RFC 8277). The router between two domains is the **border**
(the draft calls it an area border router, ABR). It runs both IGPs and reflects the labeled routes from one domain into
the other, with itself as the next hop.

:::topo
nodes:
  RT05: {at: [0, 0.8], label: "RT05 (PE)"}
  RT04: {at: [1.3, 0.8], label: "RT04 (P)"}
  XR01: {at: [2.6, 0.8], label: "XR01 (border)"}
  RT01: {at: [3.9, 0], label: "RT01 (P)"}
  RT03: {at: [3.9, 1.6], label: "RT03 (P)"}
  RT02: {at: [5.2, 0.8], label: "RT02 (PE)"}
links:
  - [RT05, RT04, "ACCESS-2"]
  - [RT04, XR01, "ACCESS-1"]
  - [XR01, RT01, "PRIMARY"]
  - [XR01, RT03, "BACKUP"]
  - [RT01, RT02, "CORE-A"]
  - [RT03, RT02, "CORE-B"]
frames:
  - {label: "IS-IS ACCESS (49.0002)", nodes: [RT05, RT04]}
  - {label: "IS-IS CORE (49.0001)", nodes: [RT01, RT03, RT02]}
:::

In the lab, RT05 is a PE in the access network with a new site of customer A (10.50.0.0/16), RT04 is an access router
without BGP, and XR01 is the border. RT02 is the PE in the core with customer A's other site (10.20.0.0/16). RT01 and
RT03 know nothing of the access network, and RT04 knows nothing of the core.

### 1.2 A path in two parts

RT02 learns RT05's loopback, 10.255.0.15/32, in BGP from XR01, with XR01 (10.255.0.1) as the next hop and a label that
XR01 chose. To send a packet there, RT02 pushes two labels: XR01's BGP label for 10.255.0.15/32 at the bottom, and on
top the LDP label that takes the packet to XR01. The core routers switch on the top label only, exactly as in the first
M8 page. XR01 receives the BGP label and replaces it with the LDP label that leads to RT05 through the access network.
This path, made of an LDP path in each domain and BGP labels at the border, is called a **hierarchical LSP**.

An ordinary traceroute from customer A's site behind RT02 shows the two labels:

```console
RT02#traceroute 10.50.0.1 source Loopback100 timeout 1 probe 1
  1 10.0.12.11 [MPLS: Labels 20/24003 Exp 0] 3 msec
  2 10.0.1.1 [MPLS: Labels 0/24003 Exp 0] 15 msec
  3  *
  4 10.0.45.15 2 msec
```

RT01 (hop 1) receives label 20, its LDP label for XR01's loopback, above XR01's BGP label 24003. It swaps 20 for 0
because XR01 asks for explicit null since Task M8-5, and XR01 (hop 2) receives `0/24003`. XR01 sends the packet on to
RT04 with RT04's LDP label for 10.255.0.15/32; RT05's own BGP label is implicit null, so nothing remains below it. RT04
(hop 3) pops that label, because RT05 is the next router, and its answer does not come back, as RT01's did not before
Task M8-5.

## 2. The border in two IGP domains

### 2.1 Two IS-IS instances

IOS XR runs several IS-IS instances side by side. Each `router isis <tag>` has its own NET, its own interfaces, its own
link-state database and its own SPF. Nothing passes from one instance to another unless it is redistributed, so two
instances are a clean way to keep two IGP domains apart on the border. In the lab the access network uses area 49.0002.
Two instances never exchange LSPs anyway, so a different area is a convention here, not a requirement.

`show isis adjacency` lists the adjacencies of every instance:

```console
RP/0/RP0/CPU0:XR01#show isis adjacency

IS-IS CORE Level-2 adjacencies:
System Id      Interface                SNPA           State Hold Changed  NSF IPv4 IPv6
RT01           Gi0/0/0/0                *PtoP*         Up    29   00:04:30 Yes None None
RT03           Gi0/0/0/1                *PtoP*         Up    26   00:04:30 Yes None None

IS-IS ACCESS Level-2 adjacencies:
System Id      Interface                SNPA           State Hold Changed  NSF IPv4 IPv6
RT04           Gi0/0/0/2                *PtoP*         Up    27   00:00:37 Yes None None
```

XR01's routing table holds the routes of both instances; `show route` names the instance (`Known via "isis ACCESS"`).
RT04's table has only the access network, and RT01's only the core.

:::note
Whether one interface can belong to two IS-IS instances is not described the same way in every guide. The IS-IS
configuration guides for the Cisco 8000 (releases 24.x and the cumulative guide of 2026) say that an interface can be
associated with only one instance. Those for the ASR 9000 from release 7.8, the NCS 5500 and the NCS 540 say that
several instances can share an interface if they have different instance IDs. IOS XRd 26.1.1 accepts Loopback0
(passive) under both instances without an instance ID, and both advertise it. This page uses the form of
Cisco's Unified MPLS document instead (section 2.2).
:::

### 2.2 The border's own loopback

The access routers need one address of XR01: its Loopback0. LDP opens its TCP session to the neighbour's transport
address, which is XR01's Loopback0 (first M8 page, section 2.3), and RT05 peers with XR01's Loopback0 in BGP. With
ACCESS-1 alone in the new instance, the adjacency with RT04 comes up and the LDP hellos are exchanged, but RT04 has no
route to 10.255.0.1 and the session does not form.

Cisco's Unified MPLS document brings the border's loopback into the other IGP by redistributing the connected routes
with a route policy that passes that loopback only. In IS-IS:

```text
route-policy ABR-LOOPBACK
  if destination in (10.255.0.1/32) then
    pass
  endif
end-policy
router isis ACCESS
 address-family ipv4 unicast
  redistribute connected route-policy ABR-LOOPBACK
```

XR01's LSP in the access instance then carries the loopback with the external flag set, and RT04 installs it as an
ordinary Level 2 route:

```console
RP/0/RP0/CPU0:XR01#show isis instance ACCESS database verbose XR01.00-00
  Metric: 10         IS-Extended RT04.00
  Metric: 10         IP-Extended 10.0.14.0/24
    Prefix Attribute Flags: X:0 R:0 N:0 E:0 A:0
  Metric: 0          IP-Extended 10.255.0.1/32
    Prefix Attribute Flags: X:1 R:0 N:0 E:0 A:0

RT04#show ip route | include ^i
i L2     10.255.0.1/32 [115/10] via 10.0.14.1, 00:00:36, Ethernet0/0
i L2     10.255.0.15/32 [115/20] via 10.0.45.15, 00:05:18, Ethernet0/1
```

Once LDP is up on ACCESS-1, XR01 also binds labels to RT04's and RT05's loopbacks and advertises them to RT01 and RT03.
They keep those bindings (liberal retention) but have no route to use them with.

:::try
See what the access network does without XR01's loopback. Do it after Task M8-6.

1. On XR01, under `router isis ACCESS` → `address-family ipv4 unicast`, remove `redistribute connected` and commit.
2. Right away and again five minutes later, run `show mpls ldp neighbor brief` on XR01, and
   `show mpls ldp discovery detail` and `show ip route 10.255.0.1` on RT04.
3. Put the line back and commit. Check that the session with RT04 returns.

An example result: RT04 lost its route to 10.255.0.1 at once, and its discovery showed
`LDP Id: 10.255.0.1:0; no route to transport addr`. The LDP session that already existed did not end at once: it was
still `Oper` on both sides two and a half minutes later, and gone after four and a half. The BGP session between XR01
and RT05 closed after about two and a half minutes. Customer A's traffic stopped at once, because RT05 could no longer
reach 10.255.0.1, the next hop of RT02's loopback. After the line went back, the LDP and BGP sessions with RT04 and
RT05 came up within seconds, and the iBGP session between RT02 and RT05 with them.
:::

## 3. BGP labeled unicast

### 3.1 The address family

RFC 8277 binds a label to a prefix in BGP: the address family is AFI 1 (IPv4) with SAFI 4, and the label travels
together with the prefix in the NLRI. It replaced RFC 3107. Two rules matter at the border: a speaker that passes a
route on with the next hop unchanged must leave the label unchanged too, and a speaker that sets itself as the next
hop must advertise a label that it has bound itself.

On IOS XR, labeled unicast is a neighbour address family, `address-family ipv4 labeled-unicast`, and it requires the
router address family `ipv4 unicast`. There is only one table: `show bgp ipv4 unicast` lists the labeled routes as
well, and `show bgp ipv4 labeled-unicast labels` adds the received and the local label. Since release 6.2.1 the same
neighbour can have both families. XR01's session with RT02 does, because XR01's own customer site, 10.30.0.0/16, has no
label and goes in plain unicast:

```console
RP/0/RP0/CPU0:XR01#show bgp neighbor 10.255.0.12 | include family
    Address family IPv4 Unicast: advertised and received
    Address family IPv4 Labeled-unicast: advertised and received
```

On IOS, `neighbor <address> send-label` under `address-family ipv4` turns the session to labeled unicast for every
route that it sends. In the lab, RT02 and RT05 send their Loopback0 and customer A's networks that way, each with
implicit null as the label because the route is its own (`show ip bgp labels` shows `imp-null` as the in label). When
RT02 got `send-label`, it reset the session with XR01, and from then on sent only labeled routes.

### 3.2 Next hop self on a route reflector

XR01 is the route reflector for RT02 and RT05. A route reflector passes routes on with their next hop unchanged
(RFC 4456). For Unified MPLS that is wrong: RT02 would get RT05's loopback with RT05's loopback as the next hop, which
nothing in the core can reach. The border has to set itself as the next hop.

On IOS XR, `next-hop-self` under the neighbour address family is not applied to the routes that the router reflects.
Cisco's TAC document lists "next-hop-self does not work" among the solutions that do not work, and starts its working
list with `ibgp policy out enforce-modifications`, a global line under `router bgp` that lets outbound changes apply
to reflected iBGP routes. It is disabled by default. With `route-reflector-client` and `next-hop-self` but without
that line, RT02 receives the route unchanged:

```console
RT02#show ip bgp 10.255.0.15
BGP routing table entry for 10.255.0.15/32, version 0
Paths: (1 available, no best path)
  Local
    10.255.0.15 (inaccessible) from 10.255.0.1 (10.255.0.1)
      Origin IGP, metric 0, localpref 100, valid, internal
      Originator: 10.255.0.15, Cluster list: 10.255.0.1
      mpls labels in/out nolabel/imp-null
```

The label is RT05's own, implicit null, passed on unchanged as RFC 8277 requires for an unchanged next hop. On IOS the
same job is `neighbor <address> next-hop-self all`, where `all` includes the reflected routes.

:::try
Take the enforcement away once everything works. Do it after Task M8-7.

1. On XR01, under `router bgp 65000`, remove `ibgp policy out enforce-modifications` and commit.
2. On RT02, run `show ip bgp 10.255.0.15`, `show ip bgp summary` and `ping 10.50.0.1 source Loopback100`.
3. Put the line back and commit. Check the same three commands again.

An example result: RT02 kept one path for 10.255.0.15/32, with next hop 10.255.0.15 and label `imp-null`.
This time IOS showed it as `best` (in the initial state of Task M8-7 the same path was `(inaccessible)`), but the ping
lost every packet: a route whose next hop is its own destination leads nowhere. The session between RT02 and RT05
still showed as up, because its hold time had not run out. After the line went back, RT02 had next hop 10.255.0.1 and
label 24003 again within seconds, and the ping went through.
:::

### 3.3 Allocating labels

When XR01 sets itself as the next hop, it has to advertise a label of its own. IOS XR does not allocate BGP labels by
default. `allocate-label all` under `router bgp` → `address-family ipv4 unicast` gives a local label to every route in
the table, and `allocate-label route-policy <name>` only to the routes that the policy passes. A labeled route without
a local label is not advertised to a labeled-unicast neighbour that gets XR01 as the next hop. With
`enforce-modifications` but without `allocate-label`, the loopbacks therefore disappeared from RT02 and RT05:

```console
RP/0/RP0/CPU0:XR01#show bgp ipv4 labeled-unicast 10.255.0.15/32
Paths: (1 available, best #1)
  Not advertised to any peer
  Path #1: Received by speaker 0
  Not advertised to any peer
  Local, (Received from a RR-client)
    10.255.0.15 (metric 30) from 10.255.0.15 (10.255.0.15)
      Received Label 3
      Origin IGP, metric 0, localpref 100, valid, internal, best, group-best, labeled-unicast
```

Without `enforce-modifications`, `allocate-label` alone changes nothing that the neighbours see: the next hop stays
unchanged, and so does the label. Only the two lines together work. With both, XR01 has a local label for every route:

```console
RP/0/RP0/CPU0:XR01#show bgp ipv4 labeled-unicast labels
   Network            Next Hop        Rcvd Label      Local Label
*>i10.20.0.0/16       10.255.0.12     3               24005
*> 10.30.0.0/16       0.0.0.0         nolabel         3
*>i10.50.0.0/16       10.255.0.15     3               24006
*>i10.255.0.12/32     10.255.0.12     3               24001
*>i10.255.0.15/32     10.255.0.15     3               24003
```

:::try
Take the label allocation away once everything works. Do it after Task M8-7.

1. On XR01, under `router bgp 65000` → `address-family ipv4 unicast`, remove `allocate-label` and commit.
2. On XR01, run `show bgp ipv4 labeled-unicast 10.255.0.15/32`. On RT02, run `show ip bgp labels` and
   `ping 10.50.0.1 source Loopback100`.
3. Put the line back and commit.

An example result: XR01 showed `Not advertised to any peer` for 10.255.0.15/32, and RT02's
`show ip bgp labels` no longer had the loopback. 10.50.0.0/16 was left with the path from RT05, whose next hop RT02 could
not reach, and the ping lost every packet. After the line went back, both returned with XR01's labels (24003 and 24006),
and the ping went through.
:::

### 3.4 Following the labels

XR01's BGP label for each loopback had the same number as its LDP label for that prefix (24003 for 10.255.0.15/32,
24001 for 10.255.0.12/32), and the forwarding table has a single entry for it. The route itself stays an IS-IS route in
XR01's routing table: IS-IS has the lower administrative distance (115) than iBGP (200). The entry swaps to the LDP
label that leads to the PE:

```console
RP/0/RP0/CPU0:XR01#show mpls forwarding
Local  Outgoing    Prefix             Outgoing     Next Hop        Bytes
Label  Label       or ID              Interface                    Switched
------ ----------- ------------------ ------------ --------------- ------------
24001  16          10.255.0.12/32     Gi0/0/0/0    10.0.1.11       3627
24003  16          10.255.0.15/32     Gi0/0/0/2    10.0.14.14      1673
24005  Pop         10.20.0.0/16                    10.255.0.12     0
24006  Pop         10.50.0.0/16                    10.255.0.15     0
```

The two customer networks have labels too, with `allocate-label all`: XR01 removes its label and sends the packet on
toward the PE's loopback, with the labels of that path. On RT02, the route to RT05's loopback resolves recursively:
XR01's label 24003 at the bottom, RT01's label 20 for XR01 on top.

```console
RT02#show ip cef 10.255.0.15 detail
10.255.0.15/32, epoch 0, flags [rib defined all labels]
  recursive via 10.255.0.1 label 24003
    nexthop 10.0.12.11 Ethernet0/0 label 20-(local:20)
```

## 4. Services on top

### 4.1 Customer routes between the provider edges

Labeled unicast carries the transport, the loopbacks of the PEs. The services are exchanged between the PEs themselves:
in the lab, RT02 and RT05 run iBGP directly between their loopbacks for customer A's networks, with the next hop
unchanged. RT02 learns 10.50.0.0/16 with next hop 10.255.0.15 and resolves that next hop through the labeled route
from XR01:

```console
RT02#show ip cef 10.50.0.0 detail
10.50.0.0/16, epoch 0, flags [rib only nolabel, rib defined all labels]
  recursive via 10.255.0.15
    recursive via 10.255.0.1 label 24003
      nexthop 10.0.12.11 Ethernet0/0 label 20-(local:20)
```

The TCP session between RT02 and RT05 itself crosses XR01 with labels. Before Task M8-7 the session cannot form, because
neither PE has a usable route to the other's loopback.

A PE must not send its own loopback in that session. If RT05 sends its loopback there, RT02 gets a second path to
10.255.0.15/32, from RT05, with 10.255.0.15 as its own next hop. RT02's routing then points the loopback at itself, and
customer A's traffic stops (`recursive via 10.255.0.15, unresolved` and `recursive-looped` in `show ip cef`). The
fixed routers of the lab send only the customer routes in that session.

Why not let XR01 reflect the customer routes as well, with the next hop unchanged? Because IOS sends every route with a
label once `send-label` is set, and a labeled route that XR01 reflects gets XR01 as next hop like the loopbacks. That is
what `allocate-label all` did in section 3.3: XR01 reflected customer A's networks with itself as next hop. The usual
answer for services is a separate address family, such as VPNv4 for Layer 3 VPNs (unit M9).

### 4.2 Labels for the loopbacks only

With `allocate-label route-policy`, XR01 allocates labels only for what the border has to carry. A policy that passes
the /32 routes in 10.255.0.0/24 leaves the customer networks without a local label, and XR01 stops reflecting them:

```console
RP/0/RP0/CPU0:XR01#show bgp ipv4 labeled-unicast labels
   Network            Next Hop        Rcvd Label      Local Label
*>i10.20.0.0/16       10.255.0.12     3               nolabel
*>i10.50.0.0/16       10.255.0.15     3               nolabel
*>i10.255.0.12/32     10.255.0.12     3               24001
*>i10.255.0.15/32     10.255.0.15     3               24003

RP/0/RP0/CPU0:XR01#show bgp ipv4 labeled-unicast neighbors 10.255.0.12 advertised-routes
Network            Next Hop        From            AS Path
10.255.0.12/32     10.255.0.1      10.255.0.12     i
10.255.0.15/32     10.255.0.1      10.255.0.15     i
```

XR01's own 10.30.0.0/16 loses its label as well. It still reaches RT02 in the plain unicast family of the same session,
which is how the two families on one neighbour work on IOS XR. The Seamless MPLS draft states the border's job in the
same terms: the border "MUST set then BGP NEXT-HOP to its own loopback" and "MUST allocate a new local MPLS label for
each labeled iBGP FEC that it reflects".

## 5. Checking the path

### 5.1 LSP ping for a BGP FEC

An MPLS LSP ping names the FEC that it tests (first M8 page, section 6.1). On IOS the default is an LDP FEC, and RT02
has no LDP label for 10.255.0.15/32, so the request is not sent (`Q`). `fec-type bgp` tests the BGP labeled FEC:

```console
RT02#ping mpls ipv4 10.255.0.15/32 fec-type bgp repeat 3
Sending 3, 72-byte MPLS Echos to BGP + Label IP FEC 10.255.0.15/32,
...
Success rate is 0 percent (0/3)

RT02#ping mpls ipv4 10.255.0.15/32 fec-type bgp source 10.255.0.12 repeat 3
Sending 3, 72-byte MPLS Echos to BGP + Label IP FEC 10.255.0.15/32,
!!!
Success rate is 100 percent (3/3), round-trip min/avg/max = 1/2/3 ms
```

The first test got no replies. The egress sends its reply as a plain UDP packet to the source address of the request,
by default the address of RT02's outgoing interface, 10.0.12.12, and RT05 has no route to the core's links. With RT02's
Loopback0 as the source, the replies came back along the labeled route. An LSP traceroute
shows each router's view of the labels, and `.` at the access router RT04, which has no route back to RT02 at all:

```console
RT02#traceroute mpls ipv4 10.255.0.15/32 fec-type bgp source 10.255.0.12 timeout 1 ttl 6
  0 10.0.12.12 MRU 1500 [Labels: 20/24003 Exp: 0/0]
L 1 10.0.12.11 MRU 1500 [Labels: explicit-null/24003 Exp: 0/0] 1 ms
L 2 10.0.1.1 MRU 1500 [Labels: 16 Exp: 0] 2 ms
. 3 *
! 4 10.0.45.15 3 ms
```

On XR01 itself, the route to 10.255.0.15/32 is an IS-IS route with an LDP label, and `fec-type bgp` was not sent (`Q`);
the default LDP FEC and `fec-type generic` worked. XR01 answers at hop 2 because `mpls oam` is configured since Task
M8-5.

:::try
Test the path from RT05 to RT02 with MPLS OAM. Do it after Task M8-7.

1. On RT05, run `ping mpls ipv4 10.255.0.12/32 repeat 3`, then the same with `fec-type bgp`, then with
   `fec-type bgp source 10.255.0.15`.
2. Run `traceroute mpls ipv4 10.255.0.12/32 fec-type bgp source 10.255.0.15 timeout 1 ttl 6`.

An example result: the ping without a FEC type was not sent (`QQQ`), because RT05 has no LDP label for
10.255.0.12/32. With `fec-type bgp` the requests went out and no reply came back; with the source 10.255.0.15 all three
succeeded. The traceroute showed `21/24001` leaving RT05, `explicit-null/24001` at RT04, label 16 at XR01, `.` at RT01,
which has no route back to RT05, and `!` at RT02.
:::

### 5.2 Two labels and the MTU

Two labels add 8 bytes. With the 1500-byte links of the lab, the largest IP packet with the DF bit that crossed from
RT02 to RT05 was 1492 bytes; 1496 bytes failed. The labels are two on both sides of XR01: the LDP label and the BGP
label in the core, and in the access network RT05 also pushes two, its LDP label for XR01 and XR01's BGP label for
RT02's loopback.

```console
RT02#ping 10.50.0.1 source Loopback100 size 1496 df-bit repeat 2
..
Success rate is 0 percent (0/2)

RT02#ping 10.50.0.1 source Loopback100 size 1492 df-bit repeat 2
!!
Success rate is 100 percent (2/2), round-trip min/avg/max = 2/2/3 ms
```

## 6. Command names

| On IOS | On IOS XR |
|---|---|
| `router isis <tag>` | `router isis <tag>` (several instances, each with its own interfaces) |
| `redistribute connected route-map <name>` | `redistribute connected route-policy <name>` |
| `neighbor <address> send-label` under `address-family ipv4` | `address-family ipv4 labeled-unicast` under the neighbour |
| `neighbor <address> next-hop-self all` | `next-hop-self` under the neighbour's address family, with `ibgp policy out enforce-modifications` |
| — | `allocate-label {all \| route-policy <name>}` under `address-family ipv4 unicast` |
| `show ip bgp labels` | `show bgp ipv4 labeled-unicast labels` |
| `ping mpls ipv4 <prefix> fec-type bgp [source <address>]` | `ping mpls ipv4 <prefix> fec-type bgp` |

## Practice

Go to lab **XRT-08** and do the M8 tasks of this page. The lab uses IOS XRd, which takes about four minutes to build,
and starts where lab XRT-07 ended.

<p class="tolab"><a href="/_learn?id=XRT-08">Open lab XRT-08 in the workspace</a> — <a href="83-m8-practice-2.html">The tasks</a></p>

:::note
The outputs on this page were captured on IOS XRd 26.1.1 with five IOS XE 17.15 routers on IOL (lab XRT-08). Times in
seconds are measured in that lab, not guaranteed values.

Sources: Cisco TAC documents "Configure Unified MPLS in Cisco IOS XR" (2015, revised 2017; the purpose of Unified MPLS,
next-hop-self and `ibgp policy out enforce-modifications`, `allocate-label`, the redistribution of the border's
loopback with RPL), "Labeled and Unlabeled Together on one BGP Neighbor on IOS-XR" (2020; one table, both families on
one neighbour, which family carries which route) and "Cisco IOS-XR BGP with MPLS Designs" (2021); the BGP command
reference for the Cisco 8000 (2026; labeled unicast as a neighbour address family, `allocate-label`,
`ibgp policy out enforce-modifications`); the IS-IS configuration guides for the Cisco 8000 (24.x and cumulative), the
ASR 9000 (7.8.x, 24.x), the NCS 5500 (24.x) and the NCS 540 (26.x) on interfaces in several instances; the Catalyst 9500
17.14 guide "Configuring Seamless MPLS" (`next-hop-self all`) and the Catalyst 9400 17.12 guide on BGP label
distribution (`send-label`); RFC 8277 (BGP labeled unicast) and draft-ietf-mpls-seamless-mpls-07 (2014, expired). All
checked October 2026. The following come from measurement in lab XRT-08 and its PoC: two instances on the border and
the loopback in both, the external flag on the redistributed loopback, the reflected route without
`enforce-modifications`, the withdrawal without `allocate-label`, the shared label numbers of BGP and LDP, the session
reset after `send-label`, the recursion through the PE's own loopback, the LSP ping and its source address, and the MTU
with two labels.
:::
