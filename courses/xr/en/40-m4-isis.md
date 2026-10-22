# M4 — IS-IS

The CCNP Enterprise track teaches OSPF and EIGRP and barely mentions IS-IS. Most service provider cores run IS-IS,
and the later units of this track (MPLS, segment routing) build on it. So this unit does what the others do not:
it explains the protocol itself first, comparing it with OSPF where that helps, and then shows how IOS XR writes it.

The outputs in this unit were captured on IOS XRd 26.1.1 and IOS XE 17.15 on IOL (lab XRT-04). The same IS-IS commands gave
the same results on IOS XRv 9000 26.1.1.

## 1. What is different about IS-IS

IS-IS is a link-state protocol like OSPF: every router floods a description of itself, every router holds the same
database, and every router runs SPF on it. The differences are in the details, and many of them follow from one fact:
**IS-IS does not run over IP.** Its packets are carried directly in the Layer 2 frame. It was written for the OSI
protocol stack, and IP was added later as one more kind of information it can carry.

That has consequences you will meet in this unit:

- A router is identified by an OSI address, not by an IP address (section 2).
- Adding a protocol does not need a new version of IS-IS. IPv6 is carried by the same process, in new fields (section 8).
  There is no "IS-ISv3".
- Everything a router advertises is a list of typed fields, **TLVs** (type, length, value). New features are new TLV types.
  Routers skip TLV types they do not understand. That makes extension easy, and it also makes some mismatches silent
  (section 7).

## 2. Addresses: the NET

Each IS-IS router has a **NET** (network entity title), an OSI address written in hexadecimal groups separated by dots:

```console
49.0001.0102.5500.0001.00
\_____/ \____________/ \/
 area     system ID    NSEL
```

| Part | Size | Meaning |
|---|---|---|
| Area address | 1–13 bytes | The area the router belongs to: everything before the system ID. It begins with an AFI; `49` is the value conventionally used for private addressing. |
| System ID | 6 bytes | Identifies the router. Must be unique in the whole IS-IS domain. Plays the part of the OSPF router ID. |
| NSEL | 1 byte | Always `00` in a NET (it means "the router itself"). |

The NET is one case of an **NSAP** (network service access point) address, the general OSI network-layer address.
In an NSAP the last octet, the selector, says which entity on the node a packet is for. A NET is an NSAP whose
selector is `00`: the router itself. Many blogs write "NSAP address" where they mean the NET.

Names you will meet for the same things:

| Name | Means | Where you meet it |
|---|---|---|
| NET (network entity title) | the router's address, selector `00` | Cisco IOS and IOS XR (the `net` command), RFC 1142 |
| NSAP address | any OSI network-layer address; often used for the NET | OSI standards, many blogs |
| ISO address | the NET | Juniper, which configures it on an interface, preferably the loopback (`family iso address`) |
| NSEL, N-selector, SEL | the last octet | Cisco, Juniper, RFC 1142 |
| system ID, SysID | the six octets before the selector | everywhere |

The area is also described in two ways. The OSI address format divides the part before the system ID into an AFI,
an IDI and a high-order DSP (RFC 1237), so some documents say "49 is the AFI and 0001 is the area ID". IS-IS itself
treats everything before the system ID as one value, the **area address** (RFC 1142, 7.1.1). Two routers are in the
same area when they have an area address in common (a router can be given more than one NET, differing only in the
area address), and IOS XR shows `Area Address: 49.0001`. In this track, "area"
means the area address.

The system ID is often derived from the loopback address so that it can be read back: write each octet with three
digits and regroup the twelve digits in fours.

```console
10.255.0.1  →  010.255.000.001  →  0102.5500.0001
```

This is one convention, not a rule. Juniper's guides recommend deriving the system ID from a MAC address or another
hardware identifier in production. Either works, as long as every system ID in the domain is unique.

Note what the NET implies: **a router belongs to one area as a whole.** In OSPF an area is a property of an interface,
and the border between two areas runs through a router (the ABR). In IS-IS the area is a property of the router,
and the border between two areas runs along a link.

## 3. Levels and adjacencies

IS-IS has two levels of routing instead of OSPF's backbone area and other areas.

| Level | Knows | Comparable OSPF role |
|---|---|---|
| Level 1 (L1) | The topology of its own area only | Internal router of a non-backbone area |
| Level 2 (L2) | The topology of the backbone, and the prefixes of every area | Backbone router |
| Level 1-2 (L1/L2) | Both: it keeps two databases and runs SPF for each | ABR |

The **backbone** is not an area number. It is the connected chain of every router that runs Level 2, whatever area
those routers are in. A backbone can span many areas.

Adjacencies follow from that:

| Two neighbours that both run… | Form |
|---|---|
| Level 1, and share an area | an L1 adjacency |
| Level 1, in different areas | nothing at Level 1 |
| Level 2 | an L2 adjacency, whatever their areas |
| Levels 1 and 2, in the same area | an L1 and an L2 adjacency |

A router runs both levels by default, on IOS and on IOS XR. The levels can be narrowed for the whole router (the
*IS type*) or for one interface (the *circuit type*). A router that runs both levels sends hellos for both levels on
every interface unless told otherwise, even where no neighbour will ever answer at one of them.

## 4. Hellos, point-to-point links and the DIS

On a broadcast network (Ethernet, by default) IS-IS elects a **DIS** (designated intermediate system) per level, which
plays the part of the OSPF DR. There is no backup DIS, the election is pre-emptive (a better router takes over at once),
and every router forms an adjacency with every other router on the segment, not only with the DIS.

Most links in a provider network have exactly two routers on them. Configuring them as **point-to-point** removes the
DIS election and the extra database entry (the *pseudonode*) that the DIS creates for the segment. Both ends must agree.
A point-to-point hello and a broadcast hello are different packet types, and a router does not accept the type it does
not expect. IOS XR says so in the interface view, as the last PDU it rejected:

```console
RP/0/RP0/CPU0:XR01#show isis interface GigabitEthernet0/0/0/0 | include "Media|Rejected|DIS"
  Media Type:               LAN
  Last PDU Rejected:        15:00:22 (0.31 sec ago), 1496 octets, P2P IIH, P2P IIH on LAN Interface
    Priority (Local/DIS):   64/none (no DIS elected)
    Priority (Local/DIS):   64/none (no DIS elected)
```

Here XR01 treats the link as a LAN while RT01 sends point-to-point hellos (IIH, IS-IS hello). Neither side lists the
other as a neighbour.

## 5. The database: LSPs and TLVs

Each router floods one **LSP** (link-state PDU) per level, split into fragments when it grows. The LSP ID is the system ID,
a pseudonode number (`00` for the router itself) and a fragment number:

```console
0102.5500.0001.00-00
```

IOS and IOS XR show the router's hostname in place of the system ID wherever they know it, because routers advertise
their hostname in their LSP (TLV 137). `show isis hostname` lists the mapping. An LSP lives 1200 seconds by default,
and its owner refreshes it before then.

The TLVs you will read most often:

| TLV | Carries |
|---|---|
| 1 | Area addresses of the router |
| 129 | Protocols supported (shown as NLPID: `0xcc` IPv4, `0x8e` IPv6) |
| 137 | Hostname |
| 2 / 22 | Neighbours (IS reachability), narrow / wide form |
| 128, 130 / 135 | IPv4 prefixes, narrow / wide form |
| 236 | IPv6 prefixes |
| 229, 222, 237 | Multi-topology: the topologies a router runs, and its neighbours and IPv6 prefixes per topology |

Prefixes are leaves of the SPF tree. When a prefix changes but the topology does not, routers recompute the routes
for that prefix only (a partial route calculation), not the whole SPF.

## 6. Between the levels: the ATT bit and route leaking

**Level 1 to Level 2** happens by itself: an L1/L2 router puts the prefixes of its area into its L2 LSP.

**Level 2 to Level 1** does not happen by default. An L1 router knows nothing outside its area. Instead, an L1/L2 router
that reaches other areas through the backbone sets the **ATT (attached) bit** in its L1 LSP, and L1 routers install a
default route towards the nearest router that sets it. This resembles a totally stubby area in OSPF, without any
configuration. The bit is shown in the `ATT/P/OL` column of `show isis database`.

The ATT bit depends on Level 2 actually working. An L1/L2 router whose Level 2 adjacencies are up, but which cannot use
anything it learns at Level 2 (section 7 shows how that happens), clears the bit, and the default route disappears from
every L1 router of the area.

A default route is not always enough. MPLS needs a label for each remote loopback (M8), and an exit chosen by a
default route may not be the best one. Copying selected L2 prefixes into L1 is called **route leaking**. A leaked prefix
is marked with the **up/down bit** ("this came down from Level 2"), and an L1/L2 router never sends a marked prefix
back up into Level 2. That bit is what prevents a loop between two L1/L2 routers of the same area. IOS shows leaked
routes as `ia` (inter-area).

## 7. Metrics: narrow and wide

Every interface has metric **10** by default, whatever its bandwidth. Unlike OSPF, IS-IS does not derive the cost from
the bandwidth unless told to.

The metric is the cost of **leaving** a router through an interface. Each end of a link sets its own value; a link can
cost 10 one way and 1000 the other.

The original IS-IS gave a metric 6 bits. These **narrow** metrics allow 1 to 63 per link and 1023 per path. **Wide**
metrics (24 bits per link, up to 16,777,214) came later, in new TLVs (22 for neighbours, 135 for IPv4 prefixes).
Traffic engineering and segment routing need wide metrics, so provider networks have moved to them. Both IOS and
IOS XR still generate narrow metrics by default.

The two forms are not translated. A router that accepts only narrow metrics skips TLV 22 and 135, and one that accepts
only wide metrics skips TLV 2, 128 and 130. Two such routers still form an adjacency (hellos carry no metrics) and still
exchange LSPs, but each ignores what the other says about its neighbours and prefixes. In the lab, XR01 still on
narrow metrics holds RT02's LSP, written in the wide form:

```console
RP/0/RP0/CPU0:XR01#show isis database detail level 2 RT02.00-00

IS-IS CORE (Level-2) Link State Database
LSPID                 LSP Seq Num  LSP Checksum  LSP Holdtime/Rcvd  ATT/P/OL
RT02.00-00            0x00000023   0x5afe        1097 /1200         0/0/0
  Area Address:   49.0002
  NLPID:          0xcc
  NLPID:          0x8e
  Hostname:       RT02
  Metric: 10         IS-Extended RT03.00
  Metric: 10         IS-Extended XR01.00
  IP Address:     10.255.0.2
  Metric: 10         IP-Extended 10.0.12.0/24
  Metric: 10         IP-Extended 10.0.23.0/24
  Metric: 10         IP-Extended 10.255.0.2/32
  Metric: 10         IP-Extended 10.20.0.0/16
  IPv6 Address:   2001:db8:255::2
  Metric: 10         IPv6 2001:db8:12::/64
  Metric: 10         IPv6 2001:db8:23::/64
  Metric: 10         IPv6 2001:db8:255::2/128
  Metric: 10         IPv6 2001:db8:1020::/64
```

and cannot place RT02 or RT03 in its Level 2 topology (`**` means unreachable), although both adjacencies are up:

```console
RP/0/RP0/CPU0:XR01#show isis topology

IS-IS CORE paths to IPv4 Unicast (Level-1) routers
System Id          Metric    Next-Hop           Interface       SNPA
XR01               --
RT01               10        RT01               Gi0/0/0/0       *PtoP*

IS-IS CORE paths to IPv4 Unicast (Level-2) routers
System Id          Metric    Next-Hop           Interface       SNPA
XR01               --
RT02               **
RT03               **
```

In the same state XR01 sends its Level 1 LSP with the ATT bit cleared (section 6), so RT01 has no default route.

The metric style is chosen per level, so an area can stay narrow while the backbone moves to wide. `show isis` shows
what a router generates and accepts at each level.

A value above 63 at a narrow level is not refused. IOS XR commits it, advertises 63, and logs a warning:

```console
RP/0/RP0/CPU0:Oct 21 15:28:01.197 UTC: isis[1003]: %ROUTING-ISIS-4-WD_METRIC_NOT_CONF : ISIS (CORE): In the topology IPv4 Unicast GigabitEthernet0/0/0/0 has a wide metric of 100 but level L1 is configured to generate narrow metrics.  Maximum narrow value 63 is used instead
```

## 8. IPv6: one topology or several

IS-IS can carry IPv6 in two ways.

| | Single topology | Multi-topology |
|---|---|---|
| SPF | One SPF for IPv4 and IPv6 together | One SPF per topology (IPv6 is topology 2) |
| IPv6 prefixes in | TLV 236, next to the IPv4 TLVs | TLV 237, with neighbours in TLV 222 |
| Requirement | Every interface must run the same set of protocols, or IPv6 packets follow paths that cannot carry them | Wide metrics (the multi-topology TLVs exist in the wide form only) |
| IOS | the default | must be configured |
| IOS XR | must be configured | the default |

Read the last two lines again: **IOS and IOS XR have opposite defaults.**

With the defaults on both sides, the adjacency comes up and IPv6 is still not exchanged. IOS XR says which topologies
an adjacency carries:

```console
RP/0/RP0/CPU0:XR01#show isis adjacency detail
...
RT01           Gi0/0/0/0                *PtoP*         Up    29   00:00:37 Yes None None
  Area Address:           49.0001
  Neighbor IPv4 Address:  10.0.11.2*
  Topology:               IPv4 Unicast
  Topology (not running): [IPv6 Unicast (neighbor doesn't participate)]
```

and IOS marks a neighbour that announces topologies as `M-ISIS`:

```console
RT01#show clns neighbors
System Id       Interface     SNPA                State  Holdtime  Type Protocol
XR01            Et0/0         5254.00d3.7fa0      Up     25        L1   M-ISIS
```

The rule that every interface runs the same protocols in single topology is enforced by IOS at the adjacency.
An IOS router that runs IPv4 and IPv6 does not accept a neighbour whose hellos announce IPv4 only: the neighbour stays
in `Init` on the IOS XR side and does not appear at all on the IOS side. `debug isis adj-packets` on the IOS router
gives the reason (`No usable IPv6 linklocal addresses in serial IIH`).

On IOS one interface metric serves both protocols in single topology. **IOS XR keeps a metric per address family
on each interface, in both modes.** In single topology the shared SPF uses the IPv4 neighbour metrics, but the IPv6
prefix of a link is still advertised with the IPv6 metric of the interface.

## 9. IS-IS on IOS XR

As with OSPF (M3), everything lives under one block, `router isis <instance>`, and the instance name is required.
The block has three kinds of address-family sections:

```console
router isis CORE
 net 49.0001.0102.5500.0001.00
 address-family ipv4 unicast        ← the IPv4 topology as a whole
 !
 interface GigabitEthernet0/0/0/1
  point-to-point
  address-family ipv4 unicast       ← IPv4 on this interface
  !
 !
```

| Place | Holds |
|---|---|
| process | NET, IS type, timers, authentication of LSPs |
| `address-family` under the process | settings for a whole topology: metric style, single topology, route leaking, redistribution |
| interface | network type, circuit type, hello settings, passive |
| `address-family` under the interface | **whether the protocol runs on that interface at all**, and its metric |

The last line is the one that IOS habits miss. An interface listed under `router isis` with no address family under it
does nothing:

```console
RP/0/RP0/CPU0:XR01#show isis interface GigabitEthernet0/0/0/0
GigabitEthernet0/0/0/0      Disabled (No topologies cfg on the intf)
```

On IOS, `ip router isis` on the interface is the same decision. On release 26.1.1 an address family under the interface
was enough to form adjacencies and exchange routes; the process-level address family is where its settings go.

`show isis interface brief` is the overview. The two `Adjs` columns count adjacencies per level (`-` means the level is
off on that interface), and the `Topos` columns count the address families running and configured:

```console
RP/0/RP0/CPU0:XR01#show isis interface brief

IS-IS CORE Interfaces
    Interface      All     Adjs    Adj Topos  Adv Topos  CLNS   MTU    Prio
                   OK    L1   L2    Run/Cfg    Run/Cfg                L1   L2
-----------------  ---  ---------  ---------  ---------  ----  ----  --------
Lo0                Yes    0    0      2/2        2/2     Up    1500    -    -
Gi0/0/0/0          Yes    1    -      2/2        2/2     Up    1497    -    -
Gi0/0/0/1          Yes    -    1      2/2        2/2     Up    1497    -    -
Gi0/0/0/2          Yes    -    1      2/2        2/2     Up    1497    -    -
```

A few more things measured in the lab:

- A loopback never sends hellos (its media type is `Loop`). `passive` on it is common practice, not a requirement.
- Adjacency changes are not logged by default (`log adjacency changes` turns that on).
- Changing the NET resets every adjacency. The old LSP is purged: it stays in the database for a short while with
  `Purge Originator` and a remaining lifetime of 0.

## 10. Leaking with a route policy

On IOS XR, route leaking is an attach point for a route policy (M5): under an address family of the process,
`propagate level 2 into level 1 route-policy <name>` copies into Level 1 the Level 2 routes that the policy passes.
There is no form without a policy. Each address family has its own `propagate` statement, and both may use the same
policy, because a prefix-set may hold IPv4 and IPv6 entries.

`show rpl route-policy <name> attachpoints` lists the attach point as `inter-area-propagate`. In XR01's Level 1 LSP a
leaked prefix is marked:

```console
RP/0/RP0/CPU0:XR01#show isis database detail level 1 XR01.00-00
...
  Metric: 10         IP 10.0.11.0/24
  Metric: 10         IP 10.255.0.1/32
  Metric: 20         IP-Interarea 10.255.0.2/32
  Metric: 30         IP-Interarea 10.255.0.3/32
  Metric: 10         IS RT01.00
  Metric: 10         IPv6 2001:db8:11::/64
  Metric: 10         IPv6 2001:db8:255::1/128
  Metric: 20         IPv6-Interarea 2001:db8:255::2/128
  Metric: 30         IPv6-Interarea 2001:db8:255::3/128
```

and RT01 installs it as an inter-area route, next to the default route that the ATT bit still provides:

```console
RT01#show ip route isis
...
i*L1  0.0.0.0/0 [115/10] via 10.0.11.1, 00:02:44, Ethernet0/0
      10.0.0.0/8 is variably subnetted, 8 subnets, 3 masks
i L1     10.255.0.1/32 [115/20] via 10.0.11.1, 00:02:44, Ethernet0/0
i ia     10.255.0.2/32 [115/30] via 10.0.11.1, 00:00:29, Ethernet0/0
i ia     10.255.0.3/32 [115/40] via 10.0.11.1, 00:00:29, Ethernet0/0
```

A prefix-set entry `<prefix> eq <length>` matches the prefixes of exactly that length inside the range, as `ge` and
`le` do for ranges of lengths (M5).

## 11. Command names

| On IOS | On IOS XR |
|---|---|
| `show clns neighbors`, `show isis neighbors` | `show isis adjacency`, `show isis neighbors` |
| `show clns interface`, `show isis interface` | `show isis interface [brief]` |
| `show isis protocol`, `show clns protocol` | `show isis` |
| `show isis database [detail]` | `show isis database [detail] [level 1 \| 2] [LSP ID]` |
| `show isis topology` | `show isis topology` (IPv4), `show isis ipv6 topology` |
| `show ip route isis` | `show route isis` |
| `show ipv6 route isis` | `show route ipv6 isis` |
| `debug isis adj-packets` | `show isis interface <name>` (the last rejected PDU and why) |
| `ip router isis` / `ipv6 router isis` on the interface | `address-family ipv4 unicast` / `ipv6 unicast` under the interface in `router isis` |
| `isis network point-to-point` | `point-to-point` under the interface in `router isis` |
| `isis circuit-type …` | `circuit-type …` under the interface in `router isis` |
| `isis metric …` | `metric …` under the interface's address family |

## Practice

Go to lab **XRT-04** and do the M4 tasks.

<p class="tolab"><a href="/_learn?id=XRT-04">Open lab XRT-04 in the workspace</a> — <a href="41-m4-practice.html">The tasks</a></p>

:::note
Sources: RFC 1142 (the text of ISO 10589; the area address in 7.1.1), RFC 1237 (the NSAP format), the IOS
*IS-IS Overview and Basic Configuration* guide (the NET and its selector), the Junos *IS-IS User Guide* (Juniper's
names and placement, and its advice on system IDs), the IOS XR *Routing Configuration Guide* for the ASR 9000, *Implementing IS-IS* (defaults: every instance is
Level 1 and Level 2; IPv6 is multi-topology unless single topology is configured; single topology needs the same address
families on every interface) and *Implementing Routing Policy* (the inter-area-propagate attach point), checked
October 2026; RFC 5305 (wide metrics), RFC 5308 (IPv6), RFC 5120 (multi-topology) and RFC 5302 (the up/down bit).
The following come from measurement on IOS XRd 26.1.1 and IOS XE 17.15: the rejected-PDU message, the interface address
family alone being enough, the ATT bit cleared by a metric-style mismatch, the 63 cap with its warning, the IOS adjacency
check and its debug message, the per-address-family interface metric in single topology, and the logging default.
That `49` is the private AFI is how explanatory material describes it; this unit did not find it in the standards
or in Cisco's documentation.
:::
