# M10 — How segment routing works

In this unit the core moves its labels from LDP to **segment routing** (SR), and then uses SR to reroute around a failure
and to send some of the traffic along another path. It covers section 3.3 of the CCNP Service Provider blueprint. The
unit has three pages and an appendix:

| Page | Contents | Tasks |
|---|---|---|
| This page | What SR is good for, how labels write a path, the move from LDP | M10-1, M10-2 |
| TI-LFA | Rerouting at once when a link fails | M10-3 |
| SR policies and the PCE | Sending some of the traffic along another path, and computing paths centrally | M10-4, M10-5 |
| Appendix | The flexible algorithm, SRv6, SID conflicts | — |

The lab is XRT-10. It continues lab XRT-09: the same square core, the same VPN customers, and XR01 and XR02 with the M9
tasks done. The IOS routers are already running SR; XR01 is the last router to move from LDP.

:::topo
nodes:
  CEA1: {at: [0, 0.3], label: "CEA1 (A, site 1)"}
  CEB1: {at: [0, 1.5], label: "CEB1 (B, site 1)"}
  XR01: {at: [1.6, 0.9], label: "XR01 (PE) idx 1"}
  RT01: {at: [3.2, 0.2], label: "RT01 (P) idx 11"}
  RT03: {at: [3.2, 1.6], label: "RT03 (P) idx 13"}
  XR02: {at: [3.2, 2.7], label: "XR02 (RR, PCE)"}
  RT02: {at: [4.8, 0.9], label: "RT02 (PE) idx 12"}
  CEA2: {at: [6.4, 0.4], label: "CEA2 (A, site 2)"}
  CEB2: {at: [6.4, 1.4], label: "CEB2 (B, site 2)"}
links:
  - [CEA1, XR01, "CUST-A"]
  - [CEB1, XR01, "CUST-B"]
  - [XR01, RT01, "PRIMARY 10"]
  - [XR01, RT03, "BACKUP 100"]
  - [RT01, RT02, "CORE-A 10"]
  - [RT03, RT02, "CORE-B 100"]
  - [RT03, XR02, "RR-LINK 10"]
  - [RT02, CEA2, "CUST-A"]
  - [RT02, CEB2, "CUST-B"]
frames:
  - {label: "AS 65000 (IS-IS CORE, SR-MPLS)", nodes: [XR01, RT01, RT03, RT02, XR02]}
:::

The numbers on the core links are the IS-IS metrics, and "idx" is the number given to each router's loopback (the
prefix-SID index, section 2.1). The shared services and the Internet of lab XRT-09 are still there, behind XR01; they
play no part in this unit.

## 1. What it is good for

### 1.1 The trouble with LDP: two protocols carry the routes and the labels

In the cores of units M8 and M9, IS-IS computed the routes and LDP handed out the labels used on them. They are two
protocols, and they run separately. So IS-IS can start using a new link while the LDP session on that link is not up
yet, and packets without a label are dropped in the core. The LDP-IGP synchronisation and session protection of unit M8
were there to close that gap.

The other trouble is that the label values differ from router to router. With LDP, each router picks its own labels. In
the lab of unit M8, the label for RT02's loopback was 16 on RT01 and 24002 on XR01. To find out where a packet is going,
you look up a table at every hop.

With SR, IS-IS carries the labels together with the routes. A route without its label cannot happen, and LDP is no
longer needed at all. There is one label value per destination, the same on every router (section 2).

### 1.2 The IGP chooses only one path per destination

The IGP computes one shortest path per destination, and all the traffic to that destination takes it. In the lab, the
traffic from XR01 to RT02, customer A's and customer B's alike, goes over PRIMARY and RT01 (metric 20; through RT03 it
is 200).

Yet sometimes different traffic should take different paths. In Task M10-4, customer A alone moves to a path through
RT03 for maintenance on RT01, and customer B stays where it is. In Task M10-5, you set up two paths that share no link.

Before SR, every way of doing this was heavy:

- **Changing a metric** moves everybody. The routes of customer A and customer B have the same next hop, RT02's
  loopback, so one cannot move without the other.
- **Policy-based routing** needs configuration hop by hop, on every router along the path.
- **RSVP-TE tunnels**: the ingress router signals a tunnel, and every router along it keeps state for that tunnel and
  refreshes it. With a full mesh between PEs, the number of tunnels grows roughly with the square of the number of PEs.

With SR, the ingress router writes "which points to pass through" into the packet as labels. The routers along the way
keep no state per path; they forward on labels as they always do (section 2.3).

### 1.3 The outage after a failure

When a link fails, the IGP must notice, tell every router, recompute the shortest paths on each of them and rewrite the
forwarding tables. Packets are lost until that is done. A way to have the router next to the failure prepare a repair
path in advance (LFA) existed before, but in some topologies it finds none. Even in the square of this lab, it finds none
for RT01's loopback. **TI-LFA**, which uses SR, can prepare a repair path in any topology (page "TI-LFA").

### 1.4 The troubles and SR's answers

| Trouble | SR's answer | Where |
|---|---|---|
| Two protocols carry the routes and the labels, and they drift apart | IS-IS carries the labels too (prefix SIDs) | This page, Tasks M10-1 and M10-2 |
| Sometimes there is no repair path for a failure | Write the repair path in labels in advance (TI-LFA) | "TI-LFA", Task M10-3 |
| Some of the traffic should take another path | Name a path and pick it by color (SR policies) | "SR policies and the PCE", Task M10-4 |
| Paths that do not overlap, computed with the whole network in view | A central path computer (PCE) | "SR policies and the PCE", Task M10-5 |
| Shortest paths on another criterion too, such as delay | Shortest paths per criterion (flexible algorithm) | Appendix |

## 2. How it works: writing a path in labels

### 2.1 Giving each router a number

With SR, each router's loopback gets a number, its **index**. In the lab it is the last octet of the loopback address:
RT02 (10.255.0.12) is 12. You configure the number once, on RT02, and IS-IS carries it to every router together with the
loopback prefix.

Each router turns the number into a label by adding it to the start of a range reserved for labels, the **SR global
block** (SRGB). The default block is 16000–23999 on both IOS XR and IOS XE, so RT02's label is 16000 + 12 = **16012** on
every router. 16012 means "go to RT02 along the shortest path". Such an instruction is a **segment**, and the value that
names it is a **segment identifier** (SID). One given to a loopback prefix is a **prefix SID**.

Each router finds its own next hop towards RT02 on its IS-IS shortest path, and puts an entry in its forwarding table:
"received with 16012, send to the next hop with 16012". The difference from LDP is that nobody has to be asked for the
label value.

| Label accepted for RT02 | LDP | SR |
|---|---|---|
| XR01 | Chosen by XR01 (24002 in the lab of unit M8) | 16012 |
| RT01 | Chosen by RT01 (16 in the lab of unit M8) | 16012 |
| RT03 | Chosen by RT03 | 16012 |

### 2.2 One label: the shortest path to that router

Follow a packet of customer B from CEB1 to CEB2. The next hop of the VPN route 10.102.2.0/24 is RT02, so XR01 puts RT02's
label 16012 on top of the VPN label (unit M9) and sends the packet to RT01, the next hop on the shortest path. RT01 is
the router before RT02, so it pops 16012 (PHP, as in unit M8). RT02 reads the VPN label and hands the packet to customer
B's VRF.

:::topo
nodes:
  CEB1: {at: [0, 1], kind: host}
  XR01: [1.3, 1]
  RT01: [2.6, 0.15]
  RT03: [2.6, 1.85]
  RT02: [3.9, 1]
  CEB2: {at: [5.2, 1], kind: host}
links:
  - [CEB1, XR01, "IP"]
  - [XR01, RT01, "16012 | 24"]
  - [RT01, RT02, "24"]
  - [RT02, CEB2, "IP"]
  - {a: XR01, b: RT03, style: dashed}
  - {a: RT03, b: RT02, style: dashed}
:::

The numbers on a link are the labels the packet carries on it, the top one on the left. 24 is customer B's VPN label; its
value changes from build to build. A traceroute from CEB1 shows the same:

```console
CEB1#traceroute 10.102.2.1 source 10.102.1.1 numeric timeout 1 probe 1
Type escape sequence to abort.
Tracing the route to 10.102.2.1
VRF info: (vrf in name/id, vrf out name/id)
  1 172.16.21.1 3 msec
  2 10.0.1.11 [MPLS: Labels 16012/24 Exp 0] 2 msec
  3 172.16.22.1 [MPLS: Label 24 Exp 0] 1 msec
  4 172.16.22.2 1 msec
```

The second hop (RT01) received two labels, 16012 and 24; the third hop (RT02) received 24 only. So far this works just as
LDP does; only the label value is different.

### 2.3 Stacking labels to write waypoints

Now say customer A's packets should go through RT03 (Task M10-4). XR01 stacks labels: on top, 16013, "to RT03 along the
shortest path"; under it, 16012, "to RT02 along the shortest path"; at the bottom, the VPN label. Each router forwards on
**the top label only**, and the router before that label's destination pops it (PHP). The next label is then on top.

1. XR01: the top label is 16013. RT03 is XR01's neighbour, so XR01 itself is "the router before". XR01 sends the packet to
   RT03 without 16013. On the link it carries 16012 and the VPN label.
2. RT03: reads the top label, 16012. RT03's shortest path to RT02 is the direct CORE-B link (100; back through XR01 and
   RT01 it is 120), so it sends the packet there. It is the router before RT02, so it pops 16012.
3. RT02: reads the VPN label and hands the packet to customer A's VRF.

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
  - {a: XR01, b: RT01, style: dashed}
  - {a: RT01, b: RT02, style: dashed}
  - [XR01, RT03, "16012 | 22"]
  - [RT03, RT02, "22"]
  - [RT02, CEA2, "IP"]
:::

```console
CEA1#traceroute 10.101.2.1 source 10.101.1.1 numeric timeout 1 probe 1
Type escape sequence to abort.
Tracing the route to 10.101.2.1
VRF info: (vrf in name/id, vrf out name/id)
  1 172.16.11.1 [AS 64500] 2 msec
  2 10.0.3.13 [AS 64500] [MPLS: Labels 16012/22 Exp 0] 2 msec
  3 172.16.12.1 [AS 64500] [MPLS: Label 22 Exp 0] 1 msec
  4 172.16.12.2 [AS 64500] 2 msec
```

22 is customer A's VPN label. `[AS 64500]` is an AS number that IOS's traceroute adds from CEA1's BGP table (the AS of the
Internet in unit M9); it has nothing to do with the labels. Three points matter:

- XR01 alone decided the path. RT03 and RT02 forwarded on their usual table, "16012 goes to RT02", and know nothing about
  customer A's path. They need no configuration and keep no state per path.
- Between two waypoints the path is the shortest one. Equal-cost paths in that stretch share the load, and when a link
  fails, the IGP repairs it.
- Customer B's packets are as in section 2.2. XR01 stacks labels only on the packets it has chosen.

### 2.4 Naming a link: adjacency SIDs

A waypoint written as a router is followed by the shortest path from there. To send a packet over one particular link,
use an **adjacency SID**: the instruction "leave through this link". It belongs to one link of one router, and it works only
on that router (it is local). IS-IS allocates and advertises one per link automatically. XR01's link to RT01
is 24011, its link to RT03 is 24013 (section 3.2).

Why advertise a label that works on one router only? So that other routers can write it into a path. Every router in the area learns which router, which link and which number, but only the owner installs it in its forwarding table. The numbers are assigned router by router, so another router may use the same number for one of its own links (the IOL routers of the lab use small numbers such as 22 to 27).

A stack can mix prefix SIDs and adjacency SIDs. "Go to RT03, then leave through RT03's link to RT02", for example, puts
the adjacency SID of RT03's link to RT02 under 16013. TI-LFA uses this when shortest paths alone cannot get around a
failure (page "TI-LFA").

An adjacency SID therefore works only when it reaches its owner as the top label. In the example above, 16013 comes first to carry the packet to RT03. RT03 is XR01's neighbour, so PHP removes 16013. With BACKUP at metric 10, the TI-LFA repair indeed pushed `{ImplNull 23 16011}`, 23 being RT03's link to RT02 (page "TI-LFA", section 2.3). Reaching another router on top, 23 would be read as that router's own label 23.

### 2.5 Who writes which path on which packets

The router that writes the labels is the one where the path starts, the **head end**: XR01 in the lab. Three questions
remain, and the other pages of this unit answer them:

- **When a link fails**: the repair path is computed in advance and put in the forwarding table. That is TI-LFA.
- **Which packets**: without anything else, a packet takes the shortest path (one label). Only packets steered into an
  **SR policy** get another path. What steers them is a **color** on their BGP route.
- **Who decides the path**: a person writes it in the configuration (explicit), the head end computes it from the
  topology and constraints (dynamic), or a central **PCE** computes it.

### 2.6 Kinds of segment

RFC 8402 divides segments as follows. The blueprint asks you to describe them:

- **Prefix segment**: takes the packet along the shortest path to a prefix. It is global: every router in the domain
  uses the same value. A **node segment** is a prefix segment on a router's own loopback, with the N flag set ("this
  prefix is this node").
- **Anycast segment**: several routers advertise the same SID for the same prefix, and the packet goes to the nearest
  one. The N flag is clear.
- **Adjacency segment**: takes the packet out of one link of one router. It is local.
- **BGP segments**: a BGP prefix SID gives a SID to a BGP route (RFC 8669, for example with labelled unicast as in unit
  M8's Unified MPLS). BGP peering SIDs (PeerNode, PeerAdj, PeerSet) name an exit towards a peer in another AS; that is
  how SR does egress peer engineering.
- **Binding segment** (binding SID): names a whole SR policy. A packet that arrives with this label is steered into the
  policy.

In SR-MPLS a SID is an MPLS label, and the data plane is that of unit M8: push, swap, pop. In SRv6 a SID is an IPv6
address (appendix). The IGP carries the SIDs: IS-IS (RFC 8667) and OSPF have extensions for it, and BGP can carry them too.

### 2.7 Details of the block

Blocks may differ from router to router. A router then computes the label it sends with the next hop's block, and the
label it receives with its own block (RFC 8660). In practice every router gets the same block, so that a label means the
same prefix everywhere. Adjacency SIDs and binding SIDs come from another range: those allocated dynamically or
configured by hand come from the **SR local block** (SRLB, 15000–15999 by default).

A prefix SID uses flags to tell the router before it what to do. **N** marks a node SID, **P** (no PHP) asks it not to
pop the label, and **E** asks it to put an explicit null instead (RFC 8667). On IOS XR, `explicit-null` on the prefix SID
sets them. With none of them set, PHP applies, and the label is popped one hop early, as in section 2.2.

## 3. Running SR in IS-IS on IOS XR

### 3.1 Where the configuration goes

Three places:

- the block: `segment-routing` → `global-block <first> <last>`. Without it, the default applies. The guides recommend
  setting it here rather than under the IGP;
- SR in the IGP: `router isis <instance>` → `address-family ipv4 unicast` → `segment-routing mpls`. The SR information
  travels in the extended TLVs of IS-IS, so wide metrics (`metric-style wide`) are needed;
- the prefix SID: `router isis <instance>` → `interface Loopback0` → `address-family ipv4 unicast` →
  `prefix-sid index <n>` (or `absolute <label>`).

IOS XR checks the order at commit time. A prefix SID is refused while SR is not enabled in the address family:

```console
router isis CORE
 interface Loopback0
  address-family ipv4 unicast
   prefix-sid index 1
!!% Feature not supported: Segment-routing is not enabled for IPv4 Unicast
```

IOS XE does it differently. SR is enabled in a global mode, `segment-routing mpls`, and the prefix SIDs of the router's
own loopbacks are written in a table there, `connected-prefix-sid-map` → `address-family ipv4`, as
`10.255.0.12/32 index 12 range 1`. IS-IS then needs only `segment-routing mpls` under `router isis`. The IOS routers of
the lab are configured that way.

Put together as XR01's configuration, the places above look like this. The right-hand column says what each line does. The block stays at the default (16000–23999), so no `segment-routing` line is needed. Below it is the SR part of an IOS XE router of the lab (RT02): the same parts, in other places.

:::config fold XR01 (IOS XR) — the smallest form of SR in IS-IS
router isis CORE
 is-type level-2-only
 net 49.0001.0100.0000.0001.00
 address-family ipv4 unicast
  metric-style wide      ## SR information rides in the extended TLVs of IS-IS, so wide metrics are required (already set in the lab)
  segment-routing mpls   ## SR in this IS-IS: advertise the block and the SIDs, and install SR labels in the forwarding table
 !
 interface Loopback0
  passive                ## no adjacency on the loopback (its address is still advertised)
  address-family ipv4 unicast
   prefix-sid index 1    ## XR01's number: every router uses the start of its block plus this, 16001, as the label to XR01
  !
 !
!
:::

:::config RT02 (IOS XE) — the SR part of the lab's fixed configuration
segment-routing mpls                 ## SR-MPLS for the whole router; on IOS XE it is needed before SR in the IGP
 !
 set-attributes
  address-family ipv4
   sr-label-preferred                ## with both an LDP and an SR label, push the SR one (section 4.1)
  exit-address-family
 !
 connected-prefix-sid-map
  address-family ipv4
   10.255.0.12/32 index 12 range 1   ## the number of its own loopback (16012); range 1 = this one prefix only
  exit-address-family
!
router isis CORE
 net 49.0001.0100.0000.0012.00
 is-type level-2-only
 metric-style wide                   ## required, as on IOS XR
 segment-routing mpls                ## advertise the SR information in this IS-IS
!
:::

OSPF has the same three parts on IOS XR (`segment-routing mpls` under `router ospf`, the prefix SID under the loopback in
the area). BGP is the third control plane of the blueprint: it can attach a prefix SID to a labelled unicast route
(`segment-routing` and a label index in a route policy), which carries SR across IGP domains.

### 3.2 What the routers advertise

Each router advertises its block in the Router Capability TLV, its prefix SIDs with its prefixes and its adjacency SIDs
with its links. XR01, after Task M10-1:

```console
RP/0/RP0/CPU0:XR01#show isis database verbose XR01.00-00
...
  Router Cap:     10.255.0.1 D:0 S:0
    Segment Routing: I:1 V:0
    SRGB Base: 16000 Range: 8000
    Node Maximum SID Depth:
      Label Imposition: 10
  Metric: 10         IS-Extended RT01.00
    ADJ-SID: F:0 B:0 V:1 L:1 S:0 P:0 weight:0 Adjacency-sid:24011
  Metric: 100        IS-Extended RT03.00
    ADJ-SID: F:0 B:0 V:1 L:1 S:0 P:0 weight:0 Adjacency-sid:24013
  Metric: 0          IP-Extended 10.255.0.1/32
    Prefix-SID Index: 1, Algorithm:0, R:0 N:1 P:0 E:0 V:0 L:0
```

`SRGB Base: 16000 Range: 8000` is the block, `Prefix-SID Index: 1` is XR01's number, and `N:1` marks the node SID. The
adjacency SIDs of IOS XR are dynamic labels (24011, 24013); those of the IOL routers are small numbers (22 to 27), from
IOS's dynamic range. XR01 builds a label table from every router's number and puts the entries in its forwarding table.
This is the table of section 2.1 as XR01 actually built it:

```console
RP/0/RP0/CPU0:XR01#show isis segment-routing label table
IS-IS CORE  IPv4 Unicast  IS Label Table
Label         Prefix                   Algorithm    Interface
----------    ----------------         ---------    ---------
16001         10.255.0.1/32            SPF          Loopback0
16011         10.255.0.11/32           SPF
16012         10.255.0.12/32           SPF
16013         10.255.0.13/32           SPF

RP/0/RP0/CPU0:XR01#show mpls forwarding | include "160[0-9][0-9]"
16001  Aggregate   SR Pfx (idx 1)     default                      0
16011  Pop         SR Pfx (idx 11)    Gi0/0/0/0    10.0.1.11       0
16012  16012       SR Pfx (idx 12)    Gi0/0/0/0    10.0.1.11       0
16013  Pop         SR Pfx (idx 13)    Gi0/0/0/1    10.0.3.13       0
```

"Received with 16012, send to RT01 with 16012" is the entry of section 2.1. The labels of the neighbours (16011 and 16013)
are `Pop`, because XR01 itself is the router before them (as in step 1 of section 2.3).

### 3.3 A block too small

The block must hold every number of the domain, because a router turns every router's number into a label with its own
block. If a number does not fit, IOS XR builds no SR entry for that prefix at all.

Lab XRT-10 starts with such a block, left by change CHG-1301: 16000–16009, "ten labels for ten routers". The numbers 11
to 13 of the IOS routers do not fit. XR01's label table then lists only its own prefix, and XR01 keeps sending on LDP
labels. No log on XR01 says why. The neighbours complain instead: they try to compute the labels they send to XR01 with
XR01's block, and find the small range in XR01's LSP.

```console
RT01#show logging | include SID
*Oct 29 22:49:45.984: %CLNS-4-SIDRANGE: Prefix-sid index 13 for 10.255.0.13/32 is out of SRGB range 10 via 10.0.1.1
```

Changing the block takes effect at once, without a reload, as long as the new labels are free. IS-IS logs the change:

```console
%ROUTING-ISIS-6-SRGB_INFO : ISIS (CORE): SRGB (index 0, 16000 23999, SRGB_ALLOCATED, 0x1) modified to (16000 16009), global cfg change, disabling SR
%ROUTING-BGP-2-SR_CFG_CHANGED : SRGB range config has been changed. BGP's labels have to be re-programmed as per new range, 'process restart bgp' needed
%ROUTING-ISIS-6-SRGB_INFO : ISIS (CORE): SRGB (index 0, 16000 16009, SRGB_ALLOCATED, 0x0) allocation complete, enabling SR
```

The BGP line matters only when BGP uses prefix SIDs. The guides warn that a change of block disrupts traffic and needs a
reload when the new labels are already in use; in the lab, the labels are free and the change takes about five seconds.

:::try
Shrink the block again once LDP is gone. Do it after Task M10-2.

1. On XR01, under `segment-routing`, set `global-block 16000 16009` and commit.
2. On XR01, run `show isis segment-routing label table`, `show cef vrf CUST-A 10.101.2.0/24 detail` and
   `show logging last 10`. On CEA1, run `ping 10.101.2.1 source Loopback10`. On RT01, run `show logging | include SID`.
3. Remove the line (`no global-block`) and commit, and run the same commands again.

An example result: within 15 seconds XR01's label table held only its own prefix (16001). In CEF, the VPN routes of
both customers became `unresolved` with a `drop adjacency`, and customer A's SR policy went down with
`Last error: unresolved first label (16013)`. The pings from CEA1 and CEB1 to site 2 failed (0 percent), and RT01 logged
`%CLNS-4-SIDRANGE: Prefix-sid index 13 for 10.255.0.13/32 is out of SRGB range 10 via 10.0.1.1`. With the line removed,
the label table was complete again within 15 seconds and the pings succeeded.
:::

## 4. From LDP to SR

### 4.1 Two labels for one prefix

SR and LDP run side by side without trouble: they take labels from different ranges and advertise them in different
protocols. But a router that has both labels for a prefix must choose which one to put on a packet. RFC 8661 says that by
default the LDP label should be chosen, and IOS XR does that.

So enabling SR in IS-IS is not enough: XR01 keeps sending on LDP labels. Towards RT02 it keeps RT01's LDP label
(`labels imposed {18}` in one build; LDP labels change from build to build). `segment-routing mpls sr-prefer` in the
IS-IS address family reverses the choice:

```console
RP/0/RP0/CPU0:XR01#show cef 10.255.0.12/32 detail
10.255.0.12/32, version 118, labeled SR, internal 0x1000001 0x8310 (ptr 0x1063c048) [1], 0x600 (0x107d52d8), 0xa28 (0xf1546f8)
...
   via 10.0.1.11/32, GigabitEthernet0/0/0/0, 6 dependencies, weight 0, class 0 [flags 0x0]
    next hop 10.0.1.11/32
    remote adjacency
     local label 16012      labels imposed {16012}
```

On IOS XE the same switch is `segment-routing mpls` → `set-attributes` → `address-family ipv4` → `sr-label-preferred`. The
VPN routes follow on their own: a VPN route is resolved through the label to its next hop's loopback, so customer A's
traffic to site 2 goes out with RT02's prefix SID on top of the VPN label (`{16012 26}` in that build).

During a migration both protocols coexist for a while, and the two directions do not have to switch at the same time.
An IOS router whose next hop does not run SR yet even joins the two by itself: before XR01 ran SR, RT01 sent the traffic
for RT03 that went through XR01 with XR01's LDP label.

The other way round, a router that runs only SR cannot reach a router that has no SID. A **mapping server** solves that
by advertising SIDs on behalf of routers that cannot (`segment-routing` → `mapping-server` → `prefix-sid-map`, advertised
in IS-IS with `segment-routing prefix-sid-map advertise-local`). The IOS XR guide and RFC 8661 say it is needed only in the
SR-to-LDP direction.

:::try
See the default preference. Do it after Task M10-1, while LDP is still running.

1. On XR01, under `router isis CORE` → `address-family ipv4 unicast`, replace `segment-routing mpls sr-prefer` with
   `segment-routing mpls`, and commit.
2. On XR01, run `show cef 10.255.0.12/32 detail` and `show cef vrf CUST-A 10.101.2.0/24 detail`.
3. Put `sr-prefer` back, commit, and run the same commands.

An example result: within 15 seconds of the commit, XR01 went back to RT01's LDP label: `labels imposed {18}`
towards RT02, and `{18 26}` for customer A's route. With `sr-prefer` back, it showed `{16012}` and `{16012 26}` again
(the LDP label and the VPN label are those of one build of the lab; they change from build to build).
:::

### 4.2 Switching LDP off

Once nothing uses LDP labels any more, LDP can go. One line, `no mpls ldp`, stops it on XR01, and the VPN traffic keeps
flowing on SR labels.

But the LDP-IGP synchronisation of unit M8 stays configured under IS-IS, and it keeps working. Synchronisation advertises
a link with its normal metric only while LDP is up on that link. With LDP gone everywhere on XR01, IOS XR advertises both
core links with the maximum metric:

```console
RP/0/RP0/CPU0:XR01#show isis database verbose XR01.00-00 | include IS-Extended
  Metric: 16777214   IS-Extended RT01.00
  Metric: 16777214   IS-Extended RT03.00
```

Nothing breaks in the lab, because XR01 has no other way in, and the customers' traffic still goes through. In a larger
network the other routers would avoid XR01's links, and TI-LFA's repair paths would be computed on wrong metrics.
Removing `mpls ldp sync` from the two interfaces brings back 10 and 100.

IOS behaves differently. Its synchronisation leaves out a link on which LDP is not configured: with `no mpls ip` on the
interface, `show mpls ldp igp sync` says "LDP not configured" and the metric stays normal. While the link still has LDP
configured but has lost its neighbour, the metric goes to the maximum, as on IOS XR. The IOS routers of the lab were
prepared with `no mpls ldp igp sync` on their links to XR01, so that XR01 could stop LDP first.

This is XR01's IS-IS after the migration (Tasks M10-1 and M10-2 done). The whole `mpls ldp` block is gone, and `mpls ldp sync` has left the interfaces. The BFD lines come from unit M7.

:::config fold XR01 — IS-IS after the migration
router isis CORE
 is-type level-2-only
 net 49.0001.0100.0000.0001.00
 log adjacency changes
 address-family ipv4 unicast
  metric-style wide
  segment-routing mpls sr-prefer    ## SR on, and while LDP labels exist too, push the SR one (section 4.1)
 !
 interface Loopback0
  passive
  address-family ipv4 unicast
   prefix-sid index 1               ## 16001 to reach XR01
  !
 !
 interface GigabitEthernet0/0/0/0   ## PRIMARY (to RT01)
  bfd minimum-interval 100          ## BFD from unit M7: sets how fast a failure is noticed (page TI-LFA, section 3)
  bfd multiplier 3
  bfd fast-detect ipv4
  point-to-point
  address-family ipv4 unicast
   metric 10                        ## no more `mpls ldp sync`; left in, the link is advertised at 16777214
  !
 !
 interface GigabitEthernet0/0/0/1   ## BACKUP (to RT03)
  bfd minimum-interval 100
  bfd multiplier 3
  bfd fast-detect ipv4
  point-to-point
  address-family ipv4 unicast
   metric 100
  !
 !
!
:::

:::try
Leave the synchronisation behind on purpose. Do it after Task M10-2.

1. On XR01, under `router isis CORE` → `interface GigabitEthernet0/0/0/1` → `address-family ipv4 unicast`, add
   `mpls ldp sync` and commit.
2. On XR01, run `show isis database verbose XR01.00-00`. On RT02, run `show isis database verbose XR01.00-00` and
   `show ip route 10.255.0.1`.
3. Remove the line and commit.

An example result: XR01 advertised the link to RT03 with 16777214 and the link to RT01 with 10. RT02 saw the same
in XR01's LSP and kept its route to 10.255.0.1 through RT01 at metric 20, with its own TI-LFA repair path through RT03.
With the line removed, the metric of the link to RT03 went back to 100.
:::

## 5. Command names

| On IOS XE | On IOS XR |
|---|---|
| `segment-routing mpls` (global, needed before SR in the IGP) | `segment-routing` (block) + `segment-routing mpls` in the IS-IS address family |
| `segment-routing mpls` → `global-block` | `segment-routing` → `global-block` |
| `connected-prefix-sid-map` → `address-family ipv4` → `<prefix> index <n> range 1` | `prefix-sid index <n>` under the loopback in IS-IS |
| `set-attributes` → `address-family ipv4` → `sr-label-preferred` | `segment-routing mpls sr-prefer` in the IS-IS address family |
| `show isis segment-routing` | `show isis segment-routing label table` |
| `show mpls forwarding-table labels <label>` | `show mpls forwarding labels <label>` |

## Practice

Go to lab **XRT-10** and do Tasks M10-1 and M10-2. XR01 is an IOS XRv 9000, so the lab takes about ten minutes to build.
When you are done, go on to the next page, "TI-LFA".

<p class="tolab"><a href="/_learn?id=XRT-10">Open lab XRT-10 in the workspace</a> — <a href="a1-m10-practice.html">The tasks</a></p>

:::note
The outputs on this page come from IOS XRv 9000 26.1.1 (XR01), IOS XRd 26.1.1 (XR02) and IOS XE 17.15 on IOL (the other
routers). Sources: the Segment Routing Configuration Guide for the ASR 9000, IOS XR 26.1.x–26.3.x (2026: SRGB and SRLB, SR for
IS-IS, mapping server) and its command reference (2025); the Cisco 8000 SR guide, release 24.x (IS-IS); the IOS XE Segment
Routing Configuration Guide (2026: SR with IS-IS); TAC document "Segment Routing Overview and Migration Guidelines"
(2020); RFC 8402, 8660, 8661, 8667 and 8669. All checked October 2026. The following come from measurement in lab XRT-10
and its PoC: the labels in the traceroutes, the commit error, the outputs, the block that is too small and the time a
change of block takes, the default preference of LDP, and the synchronisation left behind.
:::
